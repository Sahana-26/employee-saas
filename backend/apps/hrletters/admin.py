from django.contrib import admin
from .models import GeneratedLetter, LetterAudit, LetterTemplate


@admin.register(LetterTemplate)
class LetterTemplateAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'version', 'organization', 'is_active', 'requires_approval')
    list_filter = ('category', 'is_active', 'requires_approval')
    search_fields = ('code', 'name')


@admin.register(GeneratedLetter)
class GeneratedLetterAdmin(admin.ModelAdmin):
    list_display = ('letter_number', 'title', 'employee', 'category', 'status', 'organization', 'generated_at')
    list_filter = ('category', 'status')
    search_fields = ('letter_number', 'title', 'employee__employee_code', 'employee__user__email')


@admin.register(LetterAudit)
class LetterAuditAdmin(admin.ModelAdmin):
    list_display = ('letter', 'action', 'actor', 'organization', 'created_at')
    list_filter = ('action',)
    search_fields = ('letter__letter_number', 'actor__email')
