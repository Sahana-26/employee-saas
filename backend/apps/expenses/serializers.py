from django.utils import timezone
from rest_framework import serializers
from apps.accounts.permissions import HR_ROLES, MANAGER_ROLES, PAYROLL_ROLES, get_role
from apps.hr.models import Employee
from .models import ExpenseCategory, ExpenseClaim


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'organization', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']


class ExpenseClaimSerializer(serializers.ModelSerializer):
    receipt = serializers.FileField(write_only=True, required=False, allow_empty_file=False)
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True)
    rejected_by_email = serializers.EmailField(source='rejected_by.email', read_only=True)
    paid_by_email = serializers.EmailField(source='paid_by.email', read_only=True)
    receipt_download_url = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseClaim
        fields = [
            'id', 'organization', 'employee', 'employee_name', 'employee_code', 'category', 'category_name',
            'claim_number', 'title', 'expense_date', 'amount', 'currency', 'description', 'status',
            'receipt', 'receipt_file_name', 'receipt_content_type', 'receipt_size', 'receipt_download_url',
            'submitted_at', 'approved_by', 'approved_by_email', 'approved_at',
            'rejected_by', 'rejected_by_email', 'rejected_at', 'rejection_reason',
            'paid_by', 'paid_by_email', 'paid_at', 'payment_mode', 'payment_reference', 'finance_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'claim_number', 'receipt_file_name', 'receipt_content_type', 'receipt_size',
            'receipt_download_url', 'submitted_at', 'approved_by', 'approved_by_email', 'approved_at',
            'rejected_by', 'rejected_by_email', 'rejected_at', 'paid_by', 'paid_by_email', 'paid_at',
            'created_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def get_receipt_download_url(self, obj):
        if not obj.receipt_size:
            return None
        request = self.context.get('request')
        path = f'/api/expenses/{obj.pk}/download-receipt/'
        return request.build_absolute_uri(path) if request else path

    def validate_employee(self, value):
        request = self.context.get('request')
        if not request:
            return value
        if value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Employee must belong to the current organization.')
        role = get_role(request.user)
        if role not in HR_ROLES and role not in PAYROLL_ROLES:
            current_employee = Employee.objects.filter(user=request.user, organization=request.user.current_organization).first()
            if not current_employee or value.pk != current_employee.pk:
                raise serializers.ValidationError('You can submit expenses only for yourself.')
        return value

    def validate_category(self, value):
        request = self.context.get('request')
        if value and request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Category must belong to the current organization.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request and self.instance is None and not attrs.get('employee'):
            employee = Employee.objects.filter(user=request.user, organization=request.user.current_organization).first()
            if not employee:
                raise serializers.ValidationError({'employee': 'No employee profile is linked to this user.'})
            attrs['employee'] = employee
        if attrs.get('amount') is not None and attrs['amount'] <= 0:
            raise serializers.ValidationError({'amount': 'Expense amount must be greater than zero.'})
        return attrs

    def _attach_receipt_data(self, validated_data):
        uploaded_file = validated_data.pop('receipt', None)
        if uploaded_file:
            data = uploaded_file.read()
            validated_data['receipt_file_name'] = uploaded_file.name
            validated_data['receipt_content_type'] = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
            validated_data['receipt_size'] = getattr(uploaded_file, 'size', None) or len(data)
            validated_data['receipt_data'] = data
        return validated_data

    def create(self, validated_data):
        validated_data = self._attach_receipt_data(validated_data)
        if not validated_data.get('submitted_at') and validated_data.get('status', ExpenseClaim.STATUS_SUBMITTED) == ExpenseClaim.STATUS_SUBMITTED:
            validated_data['submitted_at'] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._attach_receipt_data(validated_data)
        return super().update(instance, validated_data)


class ExpenseRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class ExpensePaymentSerializer(serializers.Serializer):
    payment_mode = serializers.ChoiceField(choices=ExpenseClaim.PAYMENT_MODE_CHOICES, required=False, allow_blank=True)
    payment_reference = serializers.CharField(required=False, allow_blank=True, max_length=120)
    finance_notes = serializers.CharField(required=False, allow_blank=True)
