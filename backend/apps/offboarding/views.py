from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import (
    ASSET_ROLES,
    HR_ROLES,
    MANAGER_ROLES,
    PAYROLL_ROLES,
    IsHR,
    IsOrganizationMember,
    get_role,
)
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles
from .models import OffboardingCase, OffboardingClearanceTask, FinalSettlement, OffboardingDocument
from .serializers import (
    ClearanceTaskActionSerializer,
    ClearanceTaskSerializer,
    FinalSettlementSerializer,
    OffboardingCaseActionSerializer,
    OffboardingCaseSerializer,
    OffboardingDocumentSerializer,
    OffboardingRejectionSerializer,
    SettlementPaymentSerializer,
)
from .services import create_default_clearance_tasks, deactivate_login, ensure_final_settlement, notify_offboarding_stakeholders


class IsHRPayroll(BasePermission):
    def has_permission(self, request, view):
        return get_role(request.user) in set(HR_ROLES) | set(PAYROLL_ROLES)


class OffboardingVisibilityMixin:
    def current_employee(self):
        try:
            return self.request.user.employee_profile
        except Employee.DoesNotExist:
            return None

    def visible_case_queryset(self, qs):
        role = get_role(self.request.user)
        if role in set(HR_ROLES) | set(PAYROLL_ROLES) | set(ASSET_ROLES):
            return qs
        employee = self.current_employee()
        if role in MANAGER_ROLES and employee:
            return qs.filter(Q(employee=employee) | Q(employee__manager=employee))
        if employee:
            return qs.filter(employee=employee)
        return qs.none()


class OffboardingCaseViewSet(OffboardingVisibilityMixin, viewsets.ModelViewSet):
    serializer_class = OffboardingCaseSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = (
            OffboardingCase.objects
            .filter(organization=self.request.user.current_organization)
            .select_related('employee__user', 'employee__department', 'employee__manager__user', 'created_by', 'approved_by', 'completed_by')
            .prefetch_related('clearance_tasks')
        )
        return self.visible_case_queryset(qs).distinct()

    def get_permissions(self):
        if self.action in ['destroy', 'approve', 'reject', 'cancel', 'complete', 'deactivate_login']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        case = self.get_object()
        if case.status not in [OffboardingCase.STATUS_DRAFT, OffboardingCase.STATUS_REJECTED]:
            return Response({'detail': 'Only draft or rejected cases can be submitted.'}, status=status.HTTP_400_BAD_REQUEST)
        case.status = OffboardingCase.STATUS_SUBMITTED
        case.save(update_fields=['status', 'updated_at'])
        notify_offboarding_stakeholders(
            case,
            title='Offboarding request submitted',
            message=f'{case.employee.employee_code} submitted an offboarding request.',
            created_by=request.user,
        )
        return Response(self.get_serializer(case).data)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        case = self.get_object()
        serializer = OffboardingCaseActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        case.status = OffboardingCase.STATUS_CLEARANCE_IN_PROGRESS
        case.approved_by = request.user
        case.approved_at = timezone.now()
        case.approved_last_working_day = data.get('approved_last_working_day') or case.requested_last_working_day
        if 'notice_period_days' in data:
            case.notice_period_days = data['notice_period_days']
        if data.get('notes'):
            case.hr_notes = data['notes']
        case.save()
        case.employee.status = 'NOTICE'
        case.employee.save(update_fields=['status', 'updated_at'])
        create_default_clearance_tasks(case, created_by=request.user)
        notify_employee(
            case.employee,
            title='Offboarding approved',
            message='Your offboarding request has been approved and clearance has started.',
            notification_type='SUCCESS',
            related_module='offboarding',
            related_object_id=case.pk,
            action_url='/offboarding',
            created_by=request.user,
        )
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        case = self.get_object()
        serializer = OffboardingRejectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case.status = OffboardingCase.STATUS_REJECTED
        reason = serializer.validated_data.get('reason', '')
        if reason:
            case.hr_notes = reason
        case.save(update_fields=['status', 'hr_notes', 'updated_at'])
        notify_employee(
            case.employee,
            title='Offboarding request rejected',
            message=reason or 'Your offboarding request has been rejected.',
            notification_type='WARNING',
            related_module='offboarding',
            related_object_id=case.pk,
            action_url='/offboarding',
            created_by=request.user,
        )
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        case = self.get_object()
        serializer = OffboardingRejectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case.status = OffboardingCase.STATUS_CANCELLED
        reason = serializer.validated_data.get('reason', '')
        if reason:
            case.hr_notes = reason
        case.save(update_fields=['status', 'hr_notes', 'updated_at'])
        if case.employee.status == 'NOTICE':
            case.employee.status = 'ACTIVE'
            case.employee.save(update_fields=['status', 'updated_at'])
        notify_employee(
            case.employee,
            title='Offboarding cancelled',
            message=reason or 'Your offboarding process has been cancelled.',
            notification_type='INFO',
            related_module='offboarding',
            related_object_id=case.pk,
            action_url='/offboarding',
            created_by=request.user,
        )
        return Response(self.get_serializer(case).data)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        case = self.get_object()
        pending = case.clearance_tasks.filter(status=OffboardingClearanceTask.STATUS_PENDING).count()
        if pending:
            return Response({'detail': f'{pending} clearance task(s) are still pending.'}, status=status.HTTP_400_BAD_REQUEST)
        settlement = getattr(case, 'final_settlement', None)
        if settlement and settlement.status != FinalSettlement.STATUS_PAID:
            return Response({'detail': 'Final settlement must be paid before completing offboarding.'}, status=status.HTTP_400_BAD_REQUEST)
        case.status = OffboardingCase.STATUS_COMPLETED
        case.completed_by = request.user
        case.completed_at = timezone.now()
        case.save(update_fields=['status', 'completed_by', 'completed_at', 'updated_at'])
        case.employee.status = 'EXITED'
        case.employee.save(update_fields=['status', 'updated_at'])
        notify_employee(
            case.employee,
            title='Offboarding completed',
            message='Your offboarding process has been completed.',
            notification_type='SUCCESS',
            related_module='offboarding',
            related_object_id=case.pk,
            action_url='/offboarding',
            created_by=request.user,
        )
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=['post'], url_path='deactivate-login')
    def deactivate_login(self, request, pk=None):
        case = self.get_object()
        deactivate_login(case, request.user)
        return Response({'detail': 'Employee login access deactivated.'})


class ClearanceTaskViewSet(OffboardingVisibilityMixin, viewsets.ModelViewSet):
    serializer_class = ClearanceTaskSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = (
            OffboardingClearanceTask.objects
            .filter(organization=self.request.user.current_organization)
            .select_related('case__employee__user', 'case__employee__manager__user', 'assigned_to', 'cleared_by')
        )
        visible_cases = self.visible_case_queryset(OffboardingCase.objects.filter(organization=self.request.user.current_organization))
        return qs.filter(case__in=visible_cases).distinct()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)

    def _complete_task(self, request, task, next_status):
        serializer = ClearanceTaskActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task.status = next_status
        task.remarks = serializer.validated_data.get('remarks', task.remarks)
        task.cleared_by = request.user
        task.cleared_at = timezone.now()
        task.save(update_fields=['status', 'remarks', 'cleared_by', 'cleared_at', 'updated_at'])
        if not task.case.clearance_tasks.filter(status=OffboardingClearanceTask.STATUS_PENDING).exists():
            task.case.status = OffboardingCase.STATUS_FINAL_SETTLEMENT
            task.case.save(update_fields=['status', 'updated_at'])
            ensure_final_settlement(task.case, prepared_by=request.user)
            notify_roles(
                task.organization,
                list(PAYROLL_ROLES),
                title='Final settlement ready',
                message=f'All clearance tasks are completed for {task.case.employee.employee_code}.',
                notification_type='INFO',
                related_module='offboarding',
                related_object_id=task.case.pk,
                action_url='/offboarding',
                created_by=request.user,
            )
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        return self._complete_task(request, self.get_object(), OffboardingClearanceTask.STATUS_CLEARED)

    @action(detail=True, methods=['post'])
    def waive(self, request, pk=None):
        return self._complete_task(request, self.get_object(), OffboardingClearanceTask.STATUS_WAIVED)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._complete_task(request, self.get_object(), OffboardingClearanceTask.STATUS_REJECTED)


class FinalSettlementViewSet(OffboardingVisibilityMixin, viewsets.ModelViewSet):
    serializer_class = FinalSettlementSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = (
            FinalSettlement.objects
            .filter(organization=self.request.user.current_organization)
            .select_related('case__employee__user', 'case__employee__manager__user', 'prepared_by', 'approved_by', 'paid_by')
        )
        visible_cases = self.visible_case_queryset(OffboardingCase.objects.filter(organization=self.request.user.current_organization))
        return qs.filter(case__in=visible_cases).distinct()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'approve', 'mark_paid']:
            return [IsHRPayroll()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, prepared_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(prepared_by=serializer.instance.prepared_by or self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        settlement = self.get_object()
        settlement.status = FinalSettlement.STATUS_APPROVED
        settlement.approved_by = request.user
        settlement.approved_at = timezone.now()
        settlement.save(update_fields=['status', 'approved_by', 'approved_at', 'net_payable', 'updated_at'])
        notify_employee(
            settlement.case.employee,
            title='Final settlement approved',
            message=f'Your final settlement of {settlement.net_payable} has been approved.',
            notification_type='SUCCESS',
            related_module='offboarding',
            related_object_id=settlement.case.pk,
            action_url='/offboarding',
            created_by=request.user,
        )
        return Response(self.get_serializer(settlement).data)

    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        settlement = self.get_object()
        serializer = SettlementPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settlement.status = FinalSettlement.STATUS_PAID
        settlement.paid_by = request.user
        settlement.paid_at = timezone.now()
        settlement.payment_reference = serializer.validated_data.get('payment_reference', settlement.payment_reference)
        if serializer.validated_data.get('notes'):
            settlement.notes = serializer.validated_data['notes']
        settlement.save(update_fields=['status', 'paid_by', 'paid_at', 'payment_reference', 'notes', 'net_payable', 'updated_at'])
        notify_employee(
            settlement.case.employee,
            title='Final settlement paid',
            message=f'Your final settlement payment has been marked as paid. Reference: {settlement.payment_reference or "N/A"}.',
            notification_type='SUCCESS',
            related_module='offboarding',
            related_object_id=settlement.case.pk,
            action_url='/offboarding',
            created_by=request.user,
        )
        return Response(self.get_serializer(settlement).data)


class OffboardingDocumentViewSet(OffboardingVisibilityMixin, viewsets.ModelViewSet):
    serializer_class = OffboardingDocumentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = (
            OffboardingDocument.objects
            .filter(organization=self.request.user.current_organization)
            .select_related('case__employee__user', 'case__employee__manager__user', 'uploaded_by')
        )
        visible_cases = self.visible_case_queryset(OffboardingCase.objects.filter(organization=self.request.user.current_organization))
        return qs.filter(case__in=visible_cases).distinct()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, uploaded_by=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        document = self.get_object()
        response = HttpResponse(document.data, content_type=document.content_type or 'application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
        return response
