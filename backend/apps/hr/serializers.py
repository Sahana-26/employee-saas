from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from apps.accounts.models import User, Membership
from .models import Department, Employee


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'organization', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']


class EmployeeSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, required=True)
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=8)
    role = serializers.ChoiceField(choices=Membership.ROLE_CHOICES, write_only=True, required=False, default=Membership.ROLE_EMPLOYEE)
    full_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    account_role = serializers.SerializerMethodField()
    login_enabled = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'organization', 'user', 'email', 'first_name', 'last_name', 'password', 'role',
            'full_name', 'user_email', 'user_first_name', 'user_last_name', 'account_role', 'login_enabled',
            'employee_code', 'department', 'department_name', 'designation', 'manager', 'manager_name',
            'phone', 'personal_email', 'address', 'permanent_address', 'date_of_birth', 'gender', 'blood_group',
            'marital_status', 'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
            'bank_name', 'bank_account_number', 'bank_ifsc', 'bank_branch', 'tax_id',
            'date_of_joining', 'employment_type', 'status', 'salary_basic',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'user', 'created_at', 'updated_at']

    def get_full_name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'.strip() or obj.user.email

    def get_account_role(self, obj):
        membership = obj.user.memberships.filter(organization=obj.organization, is_active=True).first()
        return membership.role if membership else None

    def get_login_enabled(self, obj):
        return obj.user.has_usable_password() and obj.user.is_active

    def get_manager_name(self, obj):
        if not obj.manager:
            return None
        return f'{obj.manager.user.first_name} {obj.manager.user.last_name}'.strip() or obj.manager.user.email

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def validate_manager(self, value):
        request = self.context.get('request')
        if value and request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Manager must belong to the current organization.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        org = request.user.current_organization
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        password = validated_data.pop('password', '')
        role = validated_data.pop('role', Membership.ROLE_EMPLOYEE)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'current_organization': org,
                'is_active': True,
            }
        )

        if not created and hasattr(user, 'employee_profile'):
            raise serializers.ValidationError({'email': 'This user already has an employee profile.'})

        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        user.current_organization = org
        user.is_active = True
        if password:
            user.set_password(password)
        elif created:
            user.set_unusable_password()
        user.save()

        membership, _ = Membership.objects.get_or_create(organization=org, user=user)
        membership.role = role
        membership.is_active = True
        membership.save()

        return Employee.objects.create(user=user, organization=org, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        email = validated_data.pop('email', None)
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        password = validated_data.pop('password', None)
        role = validated_data.pop('role', None)

        user = instance.user
        if email and email != user.email:
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                raise serializers.ValidationError({'email': 'This email is already used by another user.'})
            user.email = email
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if password:
            user.set_password(password)
        user.save()

        if role:
            membership, _ = Membership.objects.get_or_create(organization=instance.organization, user=user)
            membership.role = role
            membership.is_active = True
            membership.save()

        return super().update(instance, validated_data)


class EmployeePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value
