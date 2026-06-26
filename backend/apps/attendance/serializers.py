from rest_framework import serializers
from .models import Shift, Holiday, EmployeeShiftAssignment, Attendance


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            'id', 'organization', 'name', 'start_time', 'end_time', 'break_minutes',
            'grace_minutes', 'half_day_hours', 'full_day_hours', 'overtime_after_minutes',
            'weekly_off_days', 'is_default', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = [
            'id', 'organization', 'name', 'date', 'holiday_type', 'is_optional',
            'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']


class EmployeeShiftAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    shift_name = serializers.CharField(source='shift.name', read_only=True)

    class Meta:
        model = EmployeeShiftAssignment
        fields = [
            'id', 'organization', 'employee', 'employee_name', 'shift', 'shift_name',
            'start_date', 'end_date', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def validate(self, attrs):
        request = self.context.get('request')
        org = request.user.current_organization if request else None
        employee = attrs.get('employee') or getattr(self.instance, 'employee', None)
        shift = attrs.get('shift') or getattr(self.instance, 'shift', None)
        if org:
            if employee and employee.organization_id != org.id:
                raise serializers.ValidationError({'employee': 'Employee must belong to the current organization.'})
            if shift and shift.organization_id != org.id:
                raise serializers.ValidationError({'shift': 'Shift must belong to the current organization.'})
        return attrs


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    shift_name = serializers.CharField(source='shift.name', read_only=True)
    holiday_name = serializers.CharField(source='holiday.name', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id', 'organization', 'employee', 'employee_name', 'shift', 'shift_name',
            'holiday', 'holiday_name', 'date', 'check_in', 'check_out', 'status',
            'work_mode', 'duration_minutes', 'late_minutes', 'overtime_minutes',
            'is_holiday', 'is_weekly_off', 'remarks', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'duration_minutes', 'late_minutes', 'overtime_minutes',
            'is_holiday', 'is_weekly_off', 'created_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def validate(self, attrs):
        request = self.context.get('request')
        org = request.user.current_organization if request else None
        employee = attrs.get('employee') or getattr(self.instance, 'employee', None)
        shift = attrs.get('shift') or getattr(self.instance, 'shift', None)
        holiday = attrs.get('holiday') or getattr(self.instance, 'holiday', None)
        if org:
            if employee and employee.organization_id != org.id:
                raise serializers.ValidationError({'employee': 'Employee must belong to the current organization.'})
            if shift and shift.organization_id != org.id:
                raise serializers.ValidationError({'shift': 'Shift must belong to the current organization.'})
            if holiday and holiday.organization_id != org.id:
                raise serializers.ValidationError({'holiday': 'Holiday must belong to the current organization.'})
        return attrs
