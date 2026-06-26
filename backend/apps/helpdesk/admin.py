from django.contrib import admin
from .models import SupportTicket, TicketAttachment, TicketCategory, TicketComment


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'default_assignee', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'subject', 'organization', 'requested_by', 'assigned_to', 'priority', 'status', 'due_at')
    search_fields = ('ticket_number', 'subject', 'requested_by__user__email', 'assigned_to__email')
    list_filter = ('status', 'priority')


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal', 'created_at')
    search_fields = ('ticket__ticket_number', 'message')
    list_filter = ('is_internal',)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'file_name', 'file_size', 'uploaded_by', 'created_at')
    search_fields = ('ticket__ticket_number', 'file_name')
