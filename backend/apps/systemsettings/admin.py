from django.contrib import admin
from .models import BackupLog, OrganizationSetting


@admin.register(OrganizationSetting)
class OrganizationSettingAdmin(admin.ModelAdmin):
    list_display = ['organization', 'app_name', 'timezone', 'currency', 'updated_at']
    search_fields = ['organization__name', 'app_name', 'support_email']


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ['organization', 'backup_type', 'status', 'file_name', 'requested_by', 'created_at']
    list_filter = ['backup_type', 'status']
    search_fields = ['organization__name', 'file_name', 'requested_by__email']
