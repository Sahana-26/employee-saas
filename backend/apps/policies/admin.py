from django.contrib import admin
from .models import CompanyPolicy, PolicyAcknowledgement


@admin.register(CompanyPolicy)
class CompanyPolicyAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'version', 'category', 'organization', 'is_published', 'requires_acknowledgement', 'created_at']
    list_filter = ['category', 'is_published', 'requires_acknowledgement', 'organization']
    search_fields = ['title', 'code', 'summary', 'content']
    exclude = ['document_data']


@admin.register(PolicyAcknowledgement)
class PolicyAcknowledgementAdmin(admin.ModelAdmin):
    list_display = ['policy', 'user', 'organization', 'acknowledged_at']
    list_filter = ['organization', 'acknowledged_at']
    search_fields = ['policy__title', 'policy__code', 'user__email']
