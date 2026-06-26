from django.utils import timezone
from rest_framework import serializers
from apps.hr.models import Employee
from .models import ProfileChangeRequest

BASIC_PROFILE_FIELDS = [
    'phone', 'personal_email', 'address', 'permanent_address',
    'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
]

APPROVABLE_PROFILE_FIELDS = [
    'phone', 'personal_email', 'address', 'permanent_address', 'date_of_birth', 'gender', 'blood_group',
    'marital_status', 'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
    'bank_name', 'bank_account_number', 'bank_ifsc', 'bank_branch', 'tax_id',
]

PROFILE_COMPLETION_FIELDS = [
    'phone', 'personal_email', 'address', 'permanent_address', 'date_of_birth', 'gender', 'blood_group',
    'marital_status', 'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
    'bank_name', 'bank_account_number', 'bank_ifsc', 'bank_branch', 'tax_id', 'date_of_joining',
]


class EmployeeSelfProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    full_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    manager_name = serializers.SerializerMethodField()
    profile_completion_percent = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_code', 'email', 'first_name', 'last_name', 'full_name',
            'department_name', 'designation', 'manager_name', 'phone', 'personal_email',
            'address', 'permanent_address', 'date_of_birth', 'gender', 'blood_group', 'marital_status',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
            'bank_name', 'bank_account_number', 'bank_ifsc', 'bank_branch', 'tax_id',
            'date_of_joining', 'employment_type', 'status', 'profile_completion_percent',
        ]
        read_only_fields = [
            'id', 'employee_code', 'email', 'full_name', 'department_name', 'designation', 'manager_name',
            'date_of_birth', 'gender', 'blood_group', 'marital_status',
            'bank_name', 'bank_account_number', 'bank_ifsc', 'bank_branch', 'tax_id',
            'date_of_joining', 'employment_type', 'status', 'profile_completion_percent',
        ]

    def get_full_name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'.strip() or obj.user.email

    def get_manager_name(self, obj):
        if not obj.manager:
            return None
        return f'{obj.manager.user.first_name} {obj.manager.user.last_name}'.strip() or obj.manager.user.email

    def get_profile_completion_percent(self, obj):
        completed = 0
        for field in PROFILE_COMPLETION_FIELDS:
            if getattr(obj, field, None):
                completed += 1
        return round((completed / len(PROFILE_COMPLETION_FIELDS)) * 100) if PROFILE_COMPLETION_FIELDS else 0

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        user.save()
        for field in BASIC_PROFILE_FIELDS:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance


class ProfileChangeRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = ProfileChangeRequest
        fields = [
            'id', 'organization', 'employee', 'employee_name', 'employee_code', 'requested_data', 'reason',
            'status', 'reviewed_by', 'reviewed_by_email', 'reviewed_at', 'review_note', 'applied_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'employee', 'employee_name', 'employee_code', 'status',
            'reviewed_by', 'reviewed_by_email', 'reviewed_at', 'review_note', 'applied_at',
            'created_at', 'updated_at',
        ]

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def validate_requested_data(self, value):
        if not isinstance(value, dict) or not value:
            raise serializers.ValidationError('requested_data must be a non-empty object.')
        invalid = [key for key in value.keys() if key not in APPROVABLE_PROFILE_FIELDS]
        if invalid:
            raise serializers.ValidationError(f'Invalid profile fields: {", ".join(invalid)}')
        cleaned = {}
        for key, item in value.items():
            cleaned[key] = '' if item is None else str(item).strip()
        return cleaned

    def create(self, validated_data):
        request = self.context['request']
        employee = Employee.objects.filter(user=request.user, organization=request.user.current_organization).first()
        if not employee:
            raise serializers.ValidationError('Only employees can create profile change requests.')
        return ProfileChangeRequest.objects.create(
            organization=request.user.current_organization,
            employee=employee,
            **validated_data,
        )


class ProfileChangeReviewSerializer(serializers.Serializer):
    review_note = serializers.CharField(required=False, allow_blank=True)


def apply_profile_change(profile_request, reviewer, review_note=''):
    employee = profile_request.employee
    for field, value in profile_request.requested_data.items():
        if field in APPROVABLE_PROFILE_FIELDS and hasattr(employee, field):
            setattr(employee, field, value)
    employee.save()
    now = timezone.now()
    profile_request.status = ProfileChangeRequest.STATUS_APPROVED
    profile_request.reviewed_by = reviewer
    profile_request.reviewed_at = now
    profile_request.review_note = review_note
    profile_request.applied_at = now
    profile_request.save()
    return profile_request
