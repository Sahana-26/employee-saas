from rest_framework import serializers
from .models import (
    EmployeeSalaryComponent,
    PayrollComponent,
    PayrollRecord,
    PayrollRun,
    Payslip,
    PayslipLine,
)


def employee_name(employee):
    return f'{employee.user.first_name} {employee.user.last_name}'.strip() or employee.user.email


class PayrollRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = PayrollRecord
        fields = ['id', 'organization', 'employee', 'employee_name', 'month', 'year', 'basic', 'allowances', 'deductions', 'net_pay', 'status', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'organization', 'net_pay', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return employee_name(obj.employee)


class PayrollComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollComponent
        fields = [
            'id', 'organization', 'name', 'component_type', 'calculation_type',
            'default_amount', 'default_percent', 'is_taxable', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']


class EmployeeSalaryComponentSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    component_name = serializers.CharField(source='component.name', read_only=True)
    component_type = serializers.CharField(source='component.component_type', read_only=True)

    class Meta:
        model = EmployeeSalaryComponent
        fields = [
            'id', 'organization', 'employee', 'employee_name', 'component', 'component_name',
            'component_type', 'amount', 'percent', 'effective_from', 'effective_to',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return employee_name(obj.employee)

    def validate(self, attrs):
        request = self.context.get('request')
        org_id = getattr(getattr(request, 'user', None), 'current_organization_id', None)
        employee = attrs.get('employee') or getattr(self.instance, 'employee', None)
        component = attrs.get('component') or getattr(self.instance, 'component', None)
        if employee and org_id and employee.organization_id != org_id:
            raise serializers.ValidationError({'employee': 'Employee must belong to the current organization.'})
        if component and org_id and component.organization_id != org_id:
            raise serializers.ValidationError({'component': 'Component must belong to the current organization.'})
        return attrs


class PayslipLineSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source='component.name', read_only=True)

    class Meta:
        model = PayslipLine
        fields = ['id', 'component', 'component_name', 'name', 'line_type', 'amount', 'notes']
        read_only_fields = ['id']


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    department = serializers.CharField(source='employee.department.name', read_only=True)
    designation = serializers.CharField(source='employee.designation', read_only=True)
    lines = PayslipLineSerializer(many=True, read_only=True)

    class Meta:
        model = Payslip
        fields = [
            'id', 'organization', 'payroll_run', 'employee', 'employee_name', 'employee_code',
            'department', 'designation', 'month', 'year', 'basic', 'gross_earnings',
            'total_deductions', 'net_pay', 'expected_work_days', 'present_days',
            'paid_leave_days', 'unpaid_leave_days', 'absent_days', 'half_days',
            'payable_days', 'loss_of_pay_days', 'worked_minutes', 'overtime_minutes',
            'overtime_amount', 'lop_amount', 'status', 'approved_at', 'paid_at',
            'notes', 'lines', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_employee_name(self, obj):
        return employee_name(obj.employee)


class PayrollRunSerializer(serializers.ModelSerializer):
    generated_by_email = serializers.EmailField(source='generated_by.email', read_only=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True)
    payslip_count = serializers.IntegerField(read_only=True)
    total_gross = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_net = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = PayrollRun
        fields = [
            'id', 'organization', 'month', 'year', 'status', 'generated_by',
            'generated_by_email', 'approved_by', 'approved_by_email', 'generated_at',
            'approved_at', 'paid_at', 'notes', 'payslip_count', 'total_gross',
            'total_deductions', 'total_net', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'generated_by', 'approved_by',
            'generated_at', 'approved_at', 'paid_at', 'payslip_count',
            'total_gross', 'total_deductions', 'total_net', 'created_at', 'updated_at'
        ]

    def validate_month(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError('Month must be between 1 and 12.')
        return value
