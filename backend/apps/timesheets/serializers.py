from decimal import Decimal
from rest_framework import serializers
from apps.accounts.permissions import HR_ROLES, MANAGER_ROLES, get_role
from apps.hr.models import Employee
from .models import ProjectMembership, ProjectTask, TimesheetEntry, WorkProject

TIMESHEET_MANAGER_ROLES = HR_ROLES | MANAGER_ROLES


def current_employee(request):
    if not request or not request.user.is_authenticated:
        return None
    return Employee.objects.filter(organization=request.user.current_organization, user=request.user).first()


class WorkProjectSerializer(serializers.ModelSerializer):
    project_manager_name = serializers.SerializerMethodField()
    project_manager_email = serializers.EmailField(source='project_manager.user.email', read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    task_count = serializers.IntegerField(read_only=True)
    approved_hours_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = WorkProject
        fields = [
            'id', 'organization', 'project_code', 'name', 'client_name', 'description', 'project_manager',
            'project_manager_name', 'project_manager_email', 'start_date', 'end_date', 'status',
            'is_billable', 'budget_hours', 'member_count', 'task_count', 'approved_hours_total',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'project_manager_name', 'project_manager_email', 'member_count',
            'task_count', 'approved_hours_total', 'created_at', 'updated_at'
        ]

    def get_project_manager_name(self, obj):
        if not obj.project_manager:
            return ''
        user = obj.project_manager.user
        return f'{user.first_name} {user.last_name}'.strip() or user.email

    def validate_project_manager(self, value):
        request = self.context.get('request')
        if value and request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Project manager must belong to the current organization.')
        return value

    def validate(self, attrs):
        start_date = attrs.get('start_date') or getattr(self.instance, 'start_date', None)
        end_date = attrs.get('end_date') or getattr(self.instance, 'end_date', None)
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date cannot be before start date.'})
        return attrs


class ProjectMembershipSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source='project.project_code', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_email = serializers.EmailField(source='employee.user.email', read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMembership
        fields = [
            'id', 'organization', 'project', 'project_code', 'project_name', 'employee', 'employee_code',
            'employee_email', 'employee_name', 'project_role', 'hourly_rate', 'is_active', 'assigned_at',
            'released_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'project_code', 'project_name', 'employee_code', 'employee_email',
            'employee_name', 'created_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        user = obj.employee.user
        return f'{user.first_name} {user.last_name}'.strip() or user.email

    def validate_project(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Project must belong to the current organization.')
        return value

    def validate_employee(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Employee must belong to the current organization.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        project = attrs.get('project') or getattr(self.instance, 'project', None)
        employee = attrs.get('employee') or getattr(self.instance, 'employee', None)
        if project and employee and project.organization_id != employee.organization_id:
            raise serializers.ValidationError('Project and employee must belong to the same organization.')
        assigned_at = attrs.get('assigned_at') or getattr(self.instance, 'assigned_at', None)
        released_at = attrs.get('released_at') or getattr(self.instance, 'released_at', None)
        if assigned_at and released_at and released_at < assigned_at:
            raise serializers.ValidationError({'released_at': 'Released date cannot be before assigned date.'})
        role = get_role(request.user) if request else None
        if self.instance is None and role not in TIMESHEET_MANAGER_ROLES:
            raise serializers.ValidationError('Only managers, HR, admins, or owners can add project members.')
        return attrs


class ProjectTaskSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source='project.project_code', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    assigned_to_code = serializers.CharField(source='assigned_to.employee_code', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.user.email', read_only=True)

    class Meta:
        model = ProjectTask
        fields = [
            'id', 'organization', 'project', 'project_code', 'project_name', 'title', 'description',
            'assigned_to', 'assigned_to_code', 'assigned_to_email', 'status', 'priority',
            'estimated_hours', 'due_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'project_code', 'project_name', 'assigned_to_code', 'assigned_to_email',
            'created_at', 'updated_at'
        ]

    def validate_project(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Project must belong to the current organization.')
        return value

    def validate_assigned_to(self, value):
        request = self.context.get('request')
        if value and request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Assigned employee must belong to the current organization.')
        return value

    def validate(self, attrs):
        project = attrs.get('project') or getattr(self.instance, 'project', None)
        assigned_to = attrs.get('assigned_to') or getattr(self.instance, 'assigned_to', None)
        if project and assigned_to and not ProjectMembership.objects.filter(project=project, employee=assigned_to, is_active=True).exists():
            raise serializers.ValidationError({'assigned_to': 'Assigned employee must be an active member of this project.'})
        return attrs


class TimesheetEntrySerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_email = serializers.EmailField(source='employee.user.email', read_only=True)
    employee_name = serializers.SerializerMethodField()
    project_code = serializers.CharField(source='project.project_code', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = TimesheetEntry
        fields = [
            'id', 'organization', 'employee', 'employee_code', 'employee_email', 'employee_name',
            'project', 'project_code', 'project_name', 'task', 'task_title', 'work_date', 'start_time',
            'end_time', 'hours', 'approved_hours', 'is_billable', 'description', 'status', 'submitted_at',
            'reviewed_by', 'reviewed_by_email', 'reviewed_at', 'rejection_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'employee_code', 'employee_email', 'employee_name', 'project_code',
            'project_name', 'task_title', 'approved_hours', 'status', 'submitted_at', 'reviewed_by',
            'reviewed_by_email', 'reviewed_at', 'rejection_reason', 'created_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        user = obj.employee.user
        return f'{user.first_name} {user.last_name}'.strip() or user.email

    def validate_employee(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Employee must belong to the current organization.')
        role = get_role(request.user) if request else None
        if role not in TIMESHEET_MANAGER_ROLES:
            employee = current_employee(request)
            if not employee or employee.pk != value.pk:
                raise serializers.ValidationError('Employees can create timesheets only for themselves.')
        return value

    def validate_project(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Project must belong to the current organization.')
        return value

    def validate_task(self, value):
        request = self.context.get('request')
        if value and request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Task must belong to the current organization.')
        return value

    def validate_hours(self, value):
        if value <= 0:
            raise serializers.ValidationError('Hours must be greater than zero.')
        if value > Decimal('24'):
            raise serializers.ValidationError('Hours cannot exceed 24 in a day.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if self.instance and self.instance.status == TimesheetEntry.STATUS_APPROVED:
            raise serializers.ValidationError('Approved timesheets cannot be edited. Reopen first if correction is needed.')
        if self.instance and self.instance.status == TimesheetEntry.STATUS_SUBMITTED:
            role = get_role(request.user) if request else None
            if role not in TIMESHEET_MANAGER_ROLES:
                raise serializers.ValidationError('Submitted timesheets cannot be edited by employee. Reopen or request rejection.')
        if self.instance is None and not attrs.get('employee'):
            employee = current_employee(request)
            if not employee:
                raise serializers.ValidationError({'employee': 'No employee profile is linked to this user.'})
            attrs['employee'] = employee
        project = attrs.get('project') or getattr(self.instance, 'project', None)
        employee = attrs.get('employee') or getattr(self.instance, 'employee', None)
        task = attrs.get('task') or getattr(self.instance, 'task', None)
        if project and employee:
            if project.organization_id != employee.organization_id:
                raise serializers.ValidationError('Project and employee must belong to the same organization.')
            if not ProjectMembership.objects.filter(project=project, employee=employee, is_active=True).exists():
                raise serializers.ValidationError({'project': 'Employee must be an active member of this project.'})
        if task and project and task.project_id != project.pk:
            raise serializers.ValidationError({'task': 'Task must belong to the selected project.'})
        if task and employee and task.assigned_to and task.assigned_to_id != employee.pk:
            role = get_role(request.user) if request else None
            if role not in TIMESHEET_MANAGER_ROLES:
                raise serializers.ValidationError({'task': 'You can log work only against tasks assigned to you.'})
        start_time = attrs.get('start_time') or getattr(self.instance, 'start_time', None)
        end_time = attrs.get('end_time') or getattr(self.instance, 'end_time', None)
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        return attrs


class TimesheetReviewSerializer(serializers.Serializer):
    approved_hours = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, min_value=Decimal('0.01'))
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate_approved_hours(self, value):
        if value > Decimal('24'):
            raise serializers.ValidationError('Approved hours cannot exceed 24 in a day.')
        return value


class TimesheetMonthlySummarySerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    employee_code = serializers.CharField()
    employee_email = serializers.EmailField()
    employee_name = serializers.CharField()
    submitted_hours = serializers.DecimalField(max_digits=12, decimal_places=2)
    approved_hours = serializers.DecimalField(max_digits=12, decimal_places=2)
    billable_hours = serializers.DecimalField(max_digits=12, decimal_places=2)
    non_billable_hours = serializers.DecimalField(max_digits=12, decimal_places=2)
    draft_count = serializers.IntegerField()
    submitted_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()
