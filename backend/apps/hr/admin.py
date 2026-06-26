from django.contrib import admin
from .models import Department, Employee


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'created_at')
    search_fields = ('name',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_code', 'user', 'organization', 'department', 'designation', 'status')
    list_filter = ('status', 'employment_type', 'organization')
    search_fields = ('employee_code', 'user__email', 'user__first_name', 'user__last_name', 'phone')
