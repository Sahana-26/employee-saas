from calendar import monthrange
from datetime import date
from decimal import Decimal
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.permissions import HR_ROLES, IsManagerLevel, IsOrganizationMember, MANAGER_ROLES, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles, notify_user
from .models import ProjectMembership, ProjectTask, TimesheetEntry, WorkProject
from .serializers import (
    ProjectMembershipSerializer,
    ProjectTaskSerializer,
    TimesheetEntrySerializer,
    TimesheetMonthlySummarySerializer,
    TimesheetReviewSerializer,
    WorkProjectSerializer,
)

TIMESHEET_MANAGER_ROLES = HR_ROLES | MANAGER_ROLES


def current_employee(user):
    return Employee.objects.filter(organization=user.current_organization, user=user).first()


def can_manage_project(user, project):
    role = get_role(user)
    if role in HR_ROLES:
        return True
    employee = current_employee(user)
    if not employee:
        return False
    if project.project_manager_id == employee.pk:
        return True
    return ProjectMembership.objects.filter(project=project, employee=employee, project_role__in=['LEAD', 'MANAGER'], is_active=True).exists()


def managed_employee_ids(user):
    role = get_role(user)
    org = user.current_organization
    if role in HR_ROLES:
        return list(Employee.objects.filter(organization=org).values_list('id', flat=True))
    employee = current_employee(user)
    if not employee:
        return []
    ids = {employee.pk}
    ids.update(Employee.objects.filter(organization=org, manager=employee).values_list('id', flat=True))
    ids.update(ProjectMembership.objects.filter(
        organization=org,
        project__project_manager=employee,
        is_active=True,
    ).values_list('employee_id', flat=True))
    ids.update(ProjectMembership.objects.filter(
        organization=org,
        project__memberships__employee=employee,
        project__memberships__project_role__in=['LEAD', 'MANAGER'],
        project__memberships__is_active=True,
        is_active=True,
    ).values_list('employee_id', flat=True))
    return list(ids)


class WorkProjectViewSet(viewsets.ModelViewSet):
    serializer_class = WorkProjectSerializer
    permission_classes = [IsOrganizationMember]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'activate', 'hold', 'complete']:
            return [IsManagerLevel()]
        return super().get_permissions()

    def get_queryset(self):
        org = self.request.user.current_organization
        role = get_role(self.request.user)
        qs = WorkProject.objects.filter(organization=org).select_related('project_manager', 'project_manager__user').annotate(
            member_count=Count('memberships', filter=Q(memberships__is_active=True), distinct=True),
            task_count=Count('tasks', distinct=True),
            approved_hours_total=Coalesce(Sum('timesheet_entries__approved_hours', filter=Q(timesheet_entries__status=TimesheetEntry.STATUS_APPROVED)), Decimal('0')),
        )
        if role in HR_ROLES:
            return qs
        employee = current_employee(self.request.user)
        if not employee:
            return qs.none()
        return qs.filter(Q(project_manager=employee) | Q(memberships__employee=employee, memberships__is_active=True)).distinct()

    def perform_create(self, serializer):
        project = serializer.save(organization=self.request.user.current_organization)
        if project.project_manager:
            ProjectMembership.objects.get_or_create(
                organization=project.organization,
                project=project,
                employee=project.project_manager,
                defaults={'project_role': ProjectMembership.ROLE_MANAGER, 'is_active': True},
            )
            notify_employee(
                project.project_manager,
                title='Project assigned',
                message=f'You have been assigned as project manager for {project.project_code} - {project.name}.',
                notification_type='ACTION',
                related_module='timesheets',
                related_object_id=project.pk,
                action_url='/timesheets',
                created_by=self.request.user,
            )

    def perform_update(self, serializer):
        project = serializer.save()
        if project.project_manager:
            ProjectMembership.objects.get_or_create(
                organization=project.organization,
                project=project,
                employee=project.project_manager,
                defaults={'project_role': ProjectMembership.ROLE_MANAGER, 'is_active': True},
            )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        project = self.get_object()
        if not can_manage_project(request.user, project):
            return Response({'detail': 'You do not have permission to update this project.'}, status=status.HTTP_403_FORBIDDEN)
        project.status = WorkProject.STATUS_ACTIVE
        project.save(update_fields=['status', 'updated_at'])
        return Response(WorkProjectSerializer(project, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='hold')
    def hold(self, request, pk=None):
        project = self.get_object()
        if not can_manage_project(request.user, project):
            return Response({'detail': 'You do not have permission to update this project.'}, status=status.HTTP_403_FORBIDDEN)
        project.status = WorkProject.STATUS_ON_HOLD
        project.save(update_fields=['status', 'updated_at'])
        return Response(WorkProjectSerializer(project, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        project = self.get_object()
        if not can_manage_project(request.user, project):
            return Response({'detail': 'You do not have permission to update this project.'}, status=status.HTTP_403_FORBIDDEN)
        project.status = WorkProject.STATUS_COMPLETED
        project.save(update_fields=['status', 'updated_at'])
        return Response(WorkProjectSerializer(project, context={'request': request}).data)


class ProjectMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMembershipSerializer
    permission_classes = [IsOrganizationMember]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'release', 'reactivate']:
            return [IsManagerLevel()]
        return super().get_permissions()

    def get_queryset(self):
        org = self.request.user.current_organization
        role = get_role(self.request.user)
        qs = ProjectMembership.objects.filter(organization=org).select_related('project', 'employee', 'employee__user')
        if role in HR_ROLES:
            return qs
        employee = current_employee(self.request.user)
        if not employee:
            return qs.none()
        return qs.filter(Q(employee=employee) | Q(project__project_manager=employee)).distinct()

    def perform_create(self, serializer):
        membership = serializer.save(organization=self.request.user.current_organization)
        notify_employee(
            membership.employee,
            title='Added to project',
            message=f'You have been added to {membership.project.project_code} - {membership.project.name}.',
            notification_type='INFO',
            related_module='timesheets',
            related_object_id=membership.project_id,
            action_url='/timesheets',
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        membership = self.get_object()
        if not can_manage_project(request.user, membership.project):
            return Response({'detail': 'You do not have permission to release this member.'}, status=status.HTTP_403_FORBIDDEN)
        membership.is_active = False
        membership.released_at = timezone.localdate()
        membership.save(update_fields=['is_active', 'released_at', 'updated_at'])
        return Response(ProjectMembershipSerializer(membership, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        membership = self.get_object()
        if not can_manage_project(request.user, membership.project):
            return Response({'detail': 'You do not have permission to reactivate this member.'}, status=status.HTTP_403_FORBIDDEN)
        membership.is_active = True
        membership.released_at = None
        membership.save(update_fields=['is_active', 'released_at', 'updated_at'])
        return Response(ProjectMembershipSerializer(membership, context={'request': request}).data)


class ProjectTaskViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectTaskSerializer
    permission_classes = [IsOrganizationMember]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsManagerLevel()]
        return super().get_permissions()

    def get_queryset(self):
        org = self.request.user.current_organization
        role = get_role(self.request.user)
        qs = ProjectTask.objects.filter(organization=org).select_related('project', 'assigned_to', 'assigned_to__user')
        if role in HR_ROLES:
            return qs
        employee = current_employee(self.request.user)
        if not employee:
            return qs.none()
        return qs.filter(Q(assigned_to=employee) | Q(project__project_manager=employee) | Q(project__memberships__employee=employee, project__memberships__is_active=True)).distinct()

    def perform_create(self, serializer):
        task = serializer.save(organization=self.request.user.current_organization)
        if task.assigned_to:
            notify_employee(
                task.assigned_to,
                title='Project task assigned',
                message=f'You have been assigned task: {task.title}.',
                notification_type='ACTION',
                related_module='timesheets',
                related_object_id=task.pk,
                action_url='/timesheets',
                created_by=self.request.user,
            )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        task.status = ProjectTask.STATUS_IN_PROGRESS
        task.save(update_fields=['status', 'updated_at'])
        return Response(ProjectTaskSerializer(task, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        task = self.get_object()
        task.status = ProjectTask.STATUS_REVIEW
        task.save(update_fields=['status', 'updated_at'])
        return Response(ProjectTaskSerializer(task, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def done(self, request, pk=None):
        task = self.get_object()
        task.status = ProjectTask.STATUS_DONE
        task.save(update_fields=['status', 'updated_at'])
        return Response(ProjectTaskSerializer(task, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def blocked(self, request, pk=None):
        task = self.get_object()
        task.status = ProjectTask.STATUS_BLOCKED
        task.save(update_fields=['status', 'updated_at'])
        return Response(ProjectTaskSerializer(task, context={'request': request}).data)


class TimesheetEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimesheetEntrySerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        role = get_role(self.request.user)
        qs = TimesheetEntry.objects.filter(organization=org).select_related(
            'employee', 'employee__user', 'project', 'task', 'reviewed_by'
        )
        employee_param = self.request.query_params.get('employee')
        project_param = self.request.query_params.get('project')
        status_param = self.request.query_params.get('status')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if employee_param:
            qs = qs.filter(employee_id=employee_param)
        if project_param:
            qs = qs.filter(project_id=project_param)
        if status_param:
            qs = qs.filter(status=status_param)
        if start_date:
            qs = qs.filter(work_date__gte=start_date)
        if end_date:
            qs = qs.filter(work_date__lte=end_date)
        if role in HR_ROLES:
            return qs
        allowed_ids = managed_employee_ids(self.request.user)
        return qs.filter(employee_id__in=allowed_ids)

    def perform_create(self, serializer):
        entry = serializer.save(organization=self.request.user.current_organization)
        if entry.project.project_manager:
            notify_employee(
                entry.project.project_manager,
                title='Timesheet entry created',
                message=f'{entry.employee.user.email} logged {entry.hours} hours on {entry.project.project_code}.',
                notification_type='INFO',
                related_module='timesheets',
                related_object_id=entry.pk,
                action_url='/timesheets',
                created_by=self.request.user,
            )

    def _can_review(self, entry):
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return True
        employee = current_employee(self.request.user)
        if not employee:
            return False
        if entry.project.project_manager_id == employee.pk:
            return True
        if entry.employee.manager_id == employee.pk:
            return True
        return ProjectMembership.objects.filter(
            project=entry.project,
            employee=employee,
            project_role__in=['LEAD', 'MANAGER'],
            is_active=True,
        ).exists()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        entry = self.get_object()
        employee = current_employee(request.user)
        role = get_role(request.user)
        if role not in TIMESHEET_MANAGER_ROLES and (not employee or entry.employee_id != employee.pk):
            return Response({'detail': 'You can submit only your own timesheet entries.'}, status=status.HTTP_403_FORBIDDEN)
        if entry.status not in [TimesheetEntry.STATUS_DRAFT, TimesheetEntry.STATUS_REJECTED]:
            return Response({'detail': 'Only draft or rejected entries can be submitted.'}, status=status.HTTP_400_BAD_REQUEST)
        entry.submit()
        entry.save(update_fields=['status', 'submitted_at', 'rejection_reason', 'updated_at'])
        if entry.project.project_manager:
            notify_employee(
                entry.project.project_manager,
                title='Timesheet submitted',
                message=f'{entry.employee.user.email} submitted {entry.hours} hours for {entry.work_date}.',
                notification_type='ACTION',
                related_module='timesheets',
                related_object_id=entry.pk,
                action_url='/timesheets',
                created_by=request.user,
            )
        notify_roles(
            entry.organization,
            ['OWNER', 'ADMIN', 'HR'],
            title='Timesheet submitted',
            message=f'{entry.employee.user.email} submitted timesheet hours for approval.',
            notification_type='ACTION',
            related_module='timesheets',
            related_object_id=entry.pk,
            action_url='/timesheets',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )
        return Response(TimesheetEntrySerializer(entry, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        entry = self.get_object()
        if not self._can_review(entry):
            return Response({'detail': 'You do not have permission to approve this timesheet.'}, status=status.HTTP_403_FORBIDDEN)
        if entry.status != TimesheetEntry.STATUS_SUBMITTED:
            return Response({'detail': 'Only submitted timesheets can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = TimesheetReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry.approve(request.user, serializer.validated_data.get('approved_hours'))
        entry.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'approved_hours', 'updated_at'])
        notify_employee(
            entry.employee,
            title='Timesheet approved',
            message=f'Your timesheet for {entry.work_date} was approved.',
            notification_type='SUCCESS',
            related_module='timesheets',
            related_object_id=entry.pk,
            action_url='/timesheets',
            created_by=request.user,
        )
        return Response(TimesheetEntrySerializer(entry, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        entry = self.get_object()
        if not self._can_review(entry):
            return Response({'detail': 'You do not have permission to reject this timesheet.'}, status=status.HTTP_403_FORBIDDEN)
        if entry.status != TimesheetEntry.STATUS_SUBMITTED:
            return Response({'detail': 'Only submitted timesheets can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = TimesheetReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('rejection_reason', '')
        entry.reject(request.user, reason)
        entry.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'approved_hours', 'updated_at'])
        notify_employee(
            entry.employee,
            title='Timesheet rejected',
            message=f'Your timesheet for {entry.work_date} was rejected. {reason}',
            notification_type='WARNING',
            related_module='timesheets',
            related_object_id=entry.pk,
            action_url='/timesheets',
            created_by=request.user,
        )
        return Response(TimesheetEntrySerializer(entry, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        entry = self.get_object()
        if not self._can_review(entry):
            return Response({'detail': 'You do not have permission to reopen this timesheet.'}, status=status.HTTP_403_FORBIDDEN)
        if entry.status not in [TimesheetEntry.STATUS_APPROVED, TimesheetEntry.STATUS_REJECTED]:
            return Response({'detail': 'Only approved or rejected timesheets can be reopened.'}, status=status.HTTP_400_BAD_REQUEST)
        entry.reopen()
        entry.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'approved_hours', 'updated_at'])
        notify_employee(
            entry.employee,
            title='Timesheet reopened',
            message=f'Your timesheet for {entry.work_date} has been reopened for correction.',
            notification_type='ACTION',
            related_module='timesheets',
            related_object_id=entry.pk,
            action_url='/timesheets',
            created_by=request.user,
        )
        return Response(TimesheetEntrySerializer(entry, context={'request': request}).data)


class TimesheetMonthlySummaryView(APIView):
    permission_classes = [IsOrganizationMember]

    def get(self, request):
        org = request.user.current_organization
        today = timezone.localdate()
        try:
            month = int(request.query_params.get('month', today.month))
            year = int(request.query_params.get('year', today.year))
        except ValueError:
            return Response({'detail': 'month and year must be numbers.'}, status=status.HTTP_400_BAD_REQUEST)
        if month < 1 or month > 12:
            return Response({'detail': 'month must be between 1 and 12.'}, status=status.HTTP_400_BAD_REQUEST)
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        entries = TimesheetEntry.objects.filter(organization=org, work_date__range=[start_date, end_date]).select_related('employee', 'employee__user')
        role = get_role(request.user)
        if role not in HR_ROLES:
            entries = entries.filter(employee_id__in=managed_employee_ids(request.user))
        rows = []
        aggregates = entries.values(
            'employee_id', 'employee__employee_code', 'employee__user__email', 'employee__user__first_name', 'employee__user__last_name'
        ).annotate(
            submitted_hours=Coalesce(Sum('hours'), Decimal('0')),
            approved_hours=Coalesce(Sum('approved_hours', filter=Q(status=TimesheetEntry.STATUS_APPROVED)), Decimal('0')),
            billable_hours=Coalesce(Sum('approved_hours', filter=Q(status=TimesheetEntry.STATUS_APPROVED, is_billable=True)), Decimal('0')),
            non_billable_hours=Coalesce(Sum('approved_hours', filter=Q(status=TimesheetEntry.STATUS_APPROVED, is_billable=False)), Decimal('0')),
            draft_count=Count('id', filter=Q(status=TimesheetEntry.STATUS_DRAFT)),
            submitted_count=Count('id', filter=Q(status=TimesheetEntry.STATUS_SUBMITTED)),
            approved_count=Count('id', filter=Q(status=TimesheetEntry.STATUS_APPROVED)),
            rejected_count=Count('id', filter=Q(status=TimesheetEntry.STATUS_REJECTED)),
        ).order_by('employee__employee_code')
        for item in aggregates:
            first = item.pop('employee__user__first_name') or ''
            last = item.pop('employee__user__last_name') or ''
            rows.append({
                'employee_id': item['employee_id'],
                'employee_code': item['employee__employee_code'],
                'employee_email': item['employee__user__email'],
                'employee_name': f'{first} {last}'.strip() or item['employee__user__email'],
                'submitted_hours': item['submitted_hours'],
                'approved_hours': item['approved_hours'],
                'billable_hours': item['billable_hours'],
                'non_billable_hours': item['non_billable_hours'],
                'draft_count': item['draft_count'],
                'submitted_count': item['submitted_count'],
                'approved_count': item['approved_count'],
                'rejected_count': item['rejected_count'],
            })
        serializer = TimesheetMonthlySummarySerializer(rows, many=True)
        totals = {
            'submitted_hours': sum(Decimal(str(row['submitted_hours'])) for row in serializer.data),
            'approved_hours': sum(Decimal(str(row['approved_hours'])) for row in serializer.data),
            'billable_hours': sum(Decimal(str(row['billable_hours'])) for row in serializer.data),
            'non_billable_hours': sum(Decimal(str(row['non_billable_hours'])) for row in serializer.data),
        }
        return Response({
            'month': month,
            'year': year,
            'start_date': start_date,
            'end_date': end_date,
            'totals': totals,
            'results': serializer.data,
        })
