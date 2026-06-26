from django.contrib import admin
from .models import ProjectMembership, ProjectTask, TimesheetEntry, WorkProject


@admin.register(WorkProject)
class WorkProjectAdmin(admin.ModelAdmin):
    list_display = ['project_code', 'name', 'organization', 'client_name', 'project_manager', 'status', 'is_billable']
    list_filter = ['organization', 'status', 'is_billable']
    search_fields = ['project_code', 'name', 'client_name']


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ['project', 'employee', 'project_role', 'is_active', 'assigned_at', 'released_at']
    list_filter = ['organization', 'project_role', 'is_active']
    search_fields = ['project__name', 'project__project_code', 'employee__employee_code', 'employee__user__email']


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'assigned_to', 'status', 'priority', 'due_date']
    list_filter = ['organization', 'status', 'priority']
    search_fields = ['title', 'project__name', 'project__project_code', 'assigned_to__user__email']


@admin.register(TimesheetEntry)
class TimesheetEntryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'project', 'work_date', 'hours', 'approved_hours', 'is_billable', 'status']
    list_filter = ['organization', 'status', 'is_billable', 'work_date']
    search_fields = ['employee__employee_code', 'employee__user__email', 'project__project_code', 'project__name', 'description']
