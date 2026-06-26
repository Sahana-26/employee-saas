from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.permissions import MANAGER_ROLES, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles
from .models import LeaveType, LeaveBalance, LeaveRequest


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'organization', 'name', 'days_per_year', 'requires_approval', 'is_paid', 'created_at']
        read_only_fields = ['id', 'organization', 'created_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    employee_name = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ['id', 'organization', 'employee', 'employee_name', 'leave_type', 'leave_type_name', 'year', 'allocated', 'used', 'remaining']
        read_only_fields = ['id', 'organization', 'remaining']

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'organization', 'employee', 'employee_name', 'leave_type', 'leave_type_name',
            'start_date', 'end_date', 'total_days', 'reason', 'status', 'approver', 'approved_at',
            'rejection_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'approver', 'approved_at', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def validate_employee(self, value):
        request = self.context.get('request')
        if request and value.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Employee must belong to the current organization.')
        return value

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        start_date = attrs.get('start_date') or getattr(instance, 'start_date', None)
        end_date = attrs.get('end_date') or getattr(instance, 'end_date', None)
        total_days = attrs.get('total_days') or getattr(instance, 'total_days', None)
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date cannot be before start date.'})
        if total_days is not None and Decimal(total_days) <= 0:
            raise serializers.ValidationError({'total_days': 'Total days must be greater than zero.'})
        return attrs

    def _get_balance(self, leave_request):
        balance, _ = LeaveBalance.objects.get_or_create(
            organization=leave_request.organization,
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            year=leave_request.start_date.year,
            defaults={
                'allocated': leave_request.leave_type.days_per_year,
                'used': Decimal('0'),
            }
        )
        return balance

    def _apply_approved_leave(self, leave_request):
        balance = self._get_balance(leave_request)
        days = Decimal(leave_request.total_days)
        if balance.remaining < days:
            raise serializers.ValidationError({
                'total_days': f'Insufficient leave balance. Remaining balance is {balance.remaining} day(s).'
            })
        balance.used = balance.used + days
        balance.save(update_fields=['used', 'updated_at'])

    def _reverse_approved_leave(self, leave_request):
        balance = self._get_balance(leave_request)
        days = Decimal(leave_request.total_days)
        balance.used = max(balance.used - days, Decimal('0'))
        balance.save(update_fields=['used', 'updated_at'])

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        role = get_role(request.user)
        if role not in MANAGER_ROLES:
            employee = Employee.objects.filter(user=request.user, organization=request.user.current_organization).first()
            if not employee:
                raise serializers.ValidationError({'employee': 'Employee profile not found for current user.'})
            validated_data['employee'] = employee
            validated_data['status'] = 'PENDING'

        instance = super().create(validated_data)
        if instance.status == 'APPROVED':
            approver = Employee.objects.filter(user=request.user, organization=request.user.current_organization).first() if request else None
            instance.approver = approver
            instance.approved_at = timezone.now()
            instance.save(update_fields=['approver', 'approved_at'])
            self._apply_approved_leave(instance)
            notify_employee(
                instance.employee,
                title='Leave approved',
                message=f'Your leave request from {instance.start_date} to {instance.end_date} has been approved.',
                notification_type='SUCCESS',
                related_module='leave-requests',
                related_object_id=instance.pk,
                action_url='/leaves',
                created_by=request.user if request else None,
            )
        else:
            notify_roles(
                instance.organization,
                ['OWNER', 'ADMIN', 'HR'],
                title='Leave request submitted',
                message=f'{instance.employee.user.email} submitted a leave request from {instance.start_date} to {instance.end_date}.',
                notification_type='ACTION',
                related_module='leave-requests',
                related_object_id=instance.pk,
                action_url='/leaves',
                created_by=request.user if request else None,
                exclude_user_ids=[request.user.id] if request else None,
            )
            if instance.employee.manager:
                notify_employee(
                    instance.employee.manager,
                    title='Team leave awaiting review',
                    message=f'{instance.employee.user.email} submitted a leave request.',
                    notification_type='ACTION',
                    related_module='leave-requests',
                    related_object_id=instance.pk,
                    action_url='/leaves',
                    created_by=request.user if request else None,
                )
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get('request')
        was_approved = instance.status == 'APPROVED'
        old_copy = LeaveRequest(
            organization=instance.organization,
            employee=instance.employee,
            leave_type=instance.leave_type,
            start_date=instance.start_date,
            end_date=instance.end_date,
            total_days=instance.total_days,
            status=instance.status,
        )

        if was_approved:
            self._reverse_approved_leave(old_copy)

        instance = super().update(instance, validated_data)

        if instance.status == 'APPROVED':
            if not instance.approved_at:
                employee = Employee.objects.filter(user=request.user, organization=request.user.current_organization).first() if request else None
                instance.approver = employee
                instance.approved_at = timezone.now()
                instance.save(update_fields=['approver', 'approved_at'])
            self._apply_approved_leave(instance)
        elif was_approved:
            instance.approver = None
            instance.approved_at = None
            instance.save(update_fields=['approver', 'approved_at'])

        old_status = old_copy.status
        if old_status != instance.status:
            if instance.status == 'APPROVED':
                notify_employee(
                    instance.employee,
                    title='Leave approved',
                    message=f'Your leave request from {instance.start_date} to {instance.end_date} has been approved.',
                    notification_type='SUCCESS',
                    related_module='leave-requests',
                    related_object_id=instance.pk,
                    action_url='/leaves',
                    created_by=request.user if request else None,
                )
            elif instance.status == 'REJECTED':
                notify_employee(
                    instance.employee,
                    title='Leave rejected',
                    message=f'Your leave request from {instance.start_date} to {instance.end_date} was rejected. {instance.rejection_reason}',
                    notification_type='WARNING',
                    related_module='leave-requests',
                    related_object_id=instance.pk,
                    action_url='/leaves',
                    created_by=request.user if request else None,
                )

        return instance
