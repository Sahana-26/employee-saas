from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import get_valid_filename
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import IsOrganizationMember, IsHR, IsPayroll, HR_ROLES, MANAGER_ROLES, PAYROLL_ROLES, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles
from .models import ExpenseCategory, ExpenseClaim
from .serializers import ExpenseCategorySerializer, ExpenseClaimSerializer, ExpensePaymentSerializer, ExpenseRejectSerializer


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        return ExpenseCategory.objects.filter(organization=self.request.user.current_organization)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)


class ExpenseClaimViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseClaimSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = (
            ExpenseClaim.objects
            .filter(organization=org)
            .select_related('employee__user', 'employee__manager', 'employee__manager__user', 'category', 'approved_by', 'rejected_by', 'paid_by')
            .defer('receipt_data')
        )
        role = get_role(self.request.user)
        if role in HR_ROLES or role in PAYROLL_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(employee=current_employee) | qs.filter(employee__manager=current_employee)
        if current_employee:
            return qs.filter(employee=current_employee)
        return qs.none()

    def perform_create(self, serializer):
        claim = serializer.save(organization=self.request.user.current_organization)
        notify_roles(
            claim.organization,
            ['OWNER', 'ADMIN', 'HR'],
            title='New expense submitted',
            message=f'{claim.employee.user.email} submitted expense {claim.claim_number or claim.pk} for {claim.currency} {claim.amount}.',
            notification_type='ACTION',
            related_module='expenses',
            related_object_id=claim.pk,
            action_url='/expenses',
            created_by=self.request.user,
            exclude_user_ids=[self.request.user.id],
        )
        if claim.employee.manager:
            notify_employee(
                claim.employee.manager,
                title='Team expense awaiting review',
                message=f'{claim.employee.user.email} submitted expense {claim.claim_number or claim.pk}.',
                notification_type='ACTION',
                related_module='expenses',
                related_object_id=claim.pk,
                action_url='/expenses',
                created_by=self.request.user,
            )

    def _can_manage_claim(self, claim):
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return True
        current_employee = Employee.objects.filter(organization=claim.organization, user=self.request.user).first()
        return bool(role in MANAGER_ROLES and current_employee and claim.employee.manager_id == current_employee.pk)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        claim = self.get_object()
        if claim.status not in [ExpenseClaim.STATUS_DRAFT, ExpenseClaim.STATUS_REJECTED]:
            return Response({'detail': 'Only draft or rejected claims can be submitted again.'}, status=status.HTTP_400_BAD_REQUEST)
        if claim.employee.user != request.user and get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'You can submit only your own expense claim.'}, status=status.HTTP_403_FORBIDDEN)
        claim.status = ExpenseClaim.STATUS_SUBMITTED
        claim.submitted_at = timezone.now()
        claim.rejection_reason = ''
        claim.rejected_by = None
        claim.rejected_at = None
        claim.save(update_fields=['status', 'submitted_at', 'rejection_reason', 'rejected_by', 'rejected_at', 'updated_at'])
        return Response({'detail': 'Expense claim submitted.'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        claim = self.get_object()
        if not self._can_manage_claim(claim):
            return Response({'detail': 'You do not have permission to approve this expense.'}, status=status.HTTP_403_FORBIDDEN)
        if claim.status != ExpenseClaim.STATUS_SUBMITTED:
            return Response({'detail': 'Only submitted claims can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        claim.status = ExpenseClaim.STATUS_APPROVED
        claim.approved_by = request.user
        claim.approved_at = timezone.now()
        claim.rejection_reason = ''
        claim.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_reason', 'updated_at'])
        notify_employee(
            claim.employee,
            title='Expense approved',
            message=f'Your expense {claim.claim_number or claim.pk} has been approved.',
            notification_type='SUCCESS',
            related_module='expenses',
            related_object_id=claim.pk,
            action_url='/expenses',
            created_by=request.user,
        )
        notify_roles(
            claim.organization,
            ['OWNER', 'ADMIN', 'PAYROLL'],
            title='Approved expense ready for payment',
            message=f'Expense {claim.claim_number or claim.pk} is ready to be marked paid.',
            notification_type='ACTION',
            related_module='expenses',
            related_object_id=claim.pk,
            action_url='/expenses',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )
        return Response({'detail': 'Expense claim approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        claim = self.get_object()
        if not self._can_manage_claim(claim):
            return Response({'detail': 'You do not have permission to reject this expense.'}, status=status.HTTP_403_FORBIDDEN)
        if claim.status not in [ExpenseClaim.STATUS_SUBMITTED, ExpenseClaim.STATUS_APPROVED]:
            return Response({'detail': 'Only submitted or approved claims can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ExpenseRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim.status = ExpenseClaim.STATUS_REJECTED
        claim.rejected_by = request.user
        claim.rejected_at = timezone.now()
        claim.rejection_reason = serializer.validated_data.get('reason', '')
        claim.approved_by = None
        claim.approved_at = None
        claim.save(update_fields=['status', 'rejected_by', 'rejected_at', 'rejection_reason', 'approved_by', 'approved_at', 'updated_at'])
        notify_employee(
            claim.employee,
            title='Expense rejected',
            message=f'Your expense {claim.claim_number or claim.pk} was rejected. {claim.rejection_reason}',
            notification_type='WARNING',
            related_module='expenses',
            related_object_id=claim.pk,
            action_url='/expenses',
            created_by=request.user,
        )
        return Response({'detail': 'Expense claim rejected.'})

    @action(detail=True, methods=['post'], url_path='mark-paid', permission_classes=[IsPayroll])
    def mark_paid(self, request, pk=None):
        claim = self.get_object()
        if claim.status != ExpenseClaim.STATUS_APPROVED:
            return Response({'detail': 'Only approved expenses can be marked as paid.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ExpensePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim.status = ExpenseClaim.STATUS_PAID
        claim.paid_by = request.user
        claim.paid_at = timezone.now()
        claim.payment_mode = serializer.validated_data.get('payment_mode', '')
        claim.payment_reference = serializer.validated_data.get('payment_reference', '')
        claim.finance_notes = serializer.validated_data.get('finance_notes', '')
        claim.save(update_fields=['status', 'paid_by', 'paid_at', 'payment_mode', 'payment_reference', 'finance_notes', 'updated_at'])
        notify_employee(
            claim.employee,
            title='Expense paid',
            message=f'Your expense {claim.claim_number or claim.pk} has been marked as paid.',
            notification_type='SUCCESS',
            related_module='expenses',
            related_object_id=claim.pk,
            action_url='/expenses',
            created_by=request.user,
        )
        return Response({'detail': 'Expense claim marked as paid.'})

    @action(detail=True, methods=['get'], url_path='download-receipt')
    def download_receipt(self, request, pk=None):
        claim = get_object_or_404(ExpenseClaim, pk=pk, organization=request.user.current_organization)
        role = get_role(request.user)
        current_employee = Employee.objects.filter(organization=claim.organization, user=request.user).first()
        can_access = role in HR_ROLES or role in PAYROLL_ROLES or (current_employee and claim.employee_id == current_employee.pk) or (current_employee and claim.employee.manager_id == current_employee.pk)
        if not can_access:
            return Response({'detail': 'You do not have permission to download this receipt.'}, status=status.HTTP_403_FORBIDDEN)
        if not claim.receipt_data:
            return Response({'detail': 'No receipt is attached to this expense.'}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(bytes(claim.receipt_data), content_type=claim.receipt_content_type or 'application/octet-stream')
        file_name = get_valid_filename(claim.receipt_file_name or f'expense-{claim.pk}-receipt')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
