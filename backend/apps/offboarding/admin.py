from django.contrib import admin
from .models import OffboardingCase, OffboardingClearanceTask, FinalSettlement, OffboardingDocument


@admin.register(OffboardingCase)
class OffboardingCaseAdmin(admin.ModelAdmin):
    list_display = ('employee', 'exit_type', 'status', 'requested_last_working_day', 'approved_last_working_day', 'organization')
    search_fields = ('employee__employee_code', 'employee__user__email', 'reason')
    list_filter = ('exit_type', 'status', 'organization')


@admin.register(OffboardingClearanceTask)
class OffboardingClearanceTaskAdmin(admin.ModelAdmin):
    list_display = ('case', 'department', 'title', 'status', 'due_date', 'organization')
    search_fields = ('case__employee__employee_code', 'title')
    list_filter = ('department', 'status', 'organization')


@admin.register(FinalSettlement)
class FinalSettlementAdmin(admin.ModelAdmin):
    list_display = ('case', 'status', 'net_payable', 'payment_reference', 'organization')
    search_fields = ('case__employee__employee_code', 'payment_reference')
    list_filter = ('status', 'organization')


@admin.register(OffboardingDocument)
class OffboardingDocumentAdmin(admin.ModelAdmin):
    list_display = ('case', 'title', 'document_type', 'file_name', 'size', 'organization')
    search_fields = ('case__employee__employee_code', 'title', 'file_name')
    list_filter = ('document_type', 'organization')
