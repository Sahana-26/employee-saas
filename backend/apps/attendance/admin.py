from django.contrib import admin
from .models import Shift, Holiday, EmployeeShiftAssignment, Attendance


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'start_time', 'end_time', 'weekly_off_days', 'is_default', 'is_active']
    list_filter = ['organization', 'is_default', 'is_active']
    search_fields = ['name']


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'date', 'holiday_type', 'is_optional']
    list_filter = ['organization', 'holiday_type', 'is_optional', 'date']
    search_fields = ['name']


@admin.register(EmployeeShiftAssignment)
class EmployeeShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'shift', 'organization', 'start_date', 'end_date', 'is_active']
    list_filter = ['organization', 'shift', 'is_active']
    search_fields = ['employee__user__email', 'shift__name']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'shift', 'status', 'duration_minutes', 'late_minutes', 'overtime_minutes']
    list_filter = ['organization', 'status', 'work_mode', 'date']
    search_fields = ['employee__user__email', 'employee__employee_code']
