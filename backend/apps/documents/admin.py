from django.contrib import admin
from .models import EmployeeDocument


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'employee', 'category', 'file_name', 'size', 'uploaded_by', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'file_name', 'employee__employee_code', 'employee__user__email')
    readonly_fields = ('file_name', 'content_type', 'size', 'uploaded_by', 'created_at', 'updated_at')
