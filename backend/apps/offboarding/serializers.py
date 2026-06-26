from django.utils import timezone
from rest_framework import serializers
from apps.accounts.permissions import HR_ROLES, MANAGER_ROLES, PAYROLL_ROLES, ASSET_ROLES, get_role
from apps.hr.models import Employee
from .models import OffboardingCase, OffboardingClearanceTask, FinalSettlement, OffboardingDocument


class OffboardingCaseSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_email = serializers.EmailField(source='employee.user.email', read_only=True)
    department_name = serializers.CharField(source='employee.department.name', read_only=True)
    manager_name = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True)
    clearance_total = serializers.SerializerMethodField()
    clearance_pending = serializers.SerializerMethodField()
    assigned_assets_count = serializers.SerializerMethodField()
    final_settlement_status = serializers.SerializerMethodField()
    final_net_payable = serializers.SerializerMethodField()

    class Meta:
        model = OffboardingCase
        fields = [
            'id', 'organization', 'employee', 'employee_name', 'employee_code', 'employee_email',
            'department_name', 'manager_name', 'exit_type', 'status', 'resignation_date',
            'requested_last_working_day', 'approved_last_working_day', 'notice_period_days',
            'reason', 'employee_notes', 'manager_notes', 'hr_notes', 'created_by', 'created_by_email',
            'approved_by', 'approved_by_email', 'approved_at', 'completed_by', 'completed_at',
            'login_deactivated_at', 'clearance_total', 'clearance_pending', 'assigned_assets_count',
            'final_settlement_status', 'final_net_payable', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'created_by', 'approved_by', 'approved_at', 'completed_by',
            'completed_at', 'login_deactivated_at', 'created_at', 'updated_at'
        ]
        extra_kwargs = {'employee': {'required': False}}

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def get_manager_name(self, obj):
        if not obj.employee.manager:
            return None
        return f'{obj.employee.manager.user.first_name} {obj.employee.manager.user.last_name}'.strip() or obj.employee.manager.user.email

    def get_clearance_total(self, obj):
        return obj.clearance_tasks.count()

    def get_clearance_pending(self, obj):
        return obj.clearance_tasks.filter(status=OffboardingClearanceTask.STATUS_PENDING).count()

    def get_assigned_assets_count(self, obj):
        return obj.employee.assigned_assets.filter(status='ASSIGNED').count()

    def get_final_settlement_status(self, obj):
        return obj.final_settlement.status if hasattr(obj, 'final_settlement') else None

    def get_final_net_payable(self, obj):
        return obj.final_settlement.net_payable if hasattr(obj, 'final_settlement') else None

    def validate_employee(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Employee must belong to the current organization.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        role = get_role(request.user) if request else None
        employee = attrs.get('employee')
        if request and not employee and role not in HR_ROLES:
            try:
                attrs['employee'] = request.user.employee_profile
            except Employee.DoesNotExist:
                raise serializers.ValidationError({'employee': 'Current user does not have an employee profile.'})
        if request and employee and role not in HR_ROLES:
            try:
                current_employee = request.user.employee_profile
            except Employee.DoesNotExist:
                current_employee = None
            if not current_employee or employee.pk != current_employee.pk:
                raise serializers.ValidationError({'employee': 'Employees can create offboarding only for themselves.'})
        return attrs


class OffboardingCaseActionSerializer(serializers.Serializer):
    approved_last_working_day = serializers.DateField(required=False, allow_null=True)
    notice_period_days = serializers.IntegerField(required=False, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)


class OffboardingRejectionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class ClearanceTaskSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    case_status = serializers.CharField(source='case.status', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)
    cleared_by_email = serializers.EmailField(source='cleared_by.email', read_only=True)

    class Meta:
        model = OffboardingClearanceTask
        fields = [
            'id', 'organization', 'case', 'employee_name', 'case_status', 'department', 'title',
            'description', 'status', 'assigned_to', 'assigned_to_email', 'due_date', 'cleared_by',
            'cleared_by_email', 'cleared_at', 'remarks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'cleared_by', 'cleared_at', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return f'{obj.case.employee.user.first_name} {obj.case.employee.user.last_name}'.strip() or obj.case.employee.user.email

    def validate_case(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Case must belong to the current organization.')
        return value


class ClearanceTaskActionSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True)


class FinalSettlementSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='case.employee.employee_code', read_only=True)
    case_status = serializers.CharField(source='case.status', read_only=True)
    prepared_by_email = serializers.EmailField(source='prepared_by.email', read_only=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True)
    paid_by_email = serializers.EmailField(source='paid_by.email', read_only=True)

    class Meta:
        model = FinalSettlement
        fields = [
            'id', 'organization', 'case', 'employee_name', 'employee_code', 'case_status', 'status',
            'salary_days', 'basic_pay', 'leave_encashment', 'bonus', 'expense_reimbursement',
            'notice_recovery', 'asset_recovery', 'tax_deduction', 'other_deductions', 'net_payable',
            'prepared_by', 'prepared_by_email', 'approved_by', 'approved_by_email', 'paid_by',
            'paid_by_email', 'approved_at', 'paid_at', 'payment_reference', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'net_payable', 'prepared_by', 'approved_by', 'paid_by',
            'approved_at', 'paid_at', 'created_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        return f'{obj.case.employee.user.first_name} {obj.case.employee.user.last_name}'.strip() or obj.case.employee.user.email

    def validate_case(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Case must belong to the current organization.')
        return value


class SettlementPaymentSerializer(serializers.Serializer):
    payment_reference = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class OffboardingDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    employee_name = serializers.SerializerMethodField()
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)

    class Meta:
        model = OffboardingDocument
        fields = [
            'id', 'organization', 'case', 'employee_name', 'title', 'document_type', 'file',
            'file_name', 'content_type', 'size', 'uploaded_by', 'uploaded_by_email', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'file_name', 'content_type', 'size', 'uploaded_by',
            'created_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        return f'{obj.case.employee.user.first_name} {obj.case.employee.user.last_name}'.strip() or obj.case.employee.user.email

    def validate_case(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Case must belong to the current organization.')
        return value

    def create(self, validated_data):
        request = self.context['request']
        uploaded = validated_data.pop('file', None)
        if not uploaded:
            raise serializers.ValidationError({'file': 'File is required.'})
        return OffboardingDocument.objects.create(
            organization=request.user.current_organization,
            uploaded_by=request.user,
            file_name=uploaded.name,
            content_type=getattr(uploaded, 'content_type', '') or '',
            size=uploaded.size,
            data=uploaded.read(),
            **validated_data
        )
