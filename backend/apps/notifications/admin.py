from django.contrib import admin
from .models import Announcement, AnnouncementRead, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'organization', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'organization']
    search_fields = ['title', 'message', 'recipient__email']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'organization', 'is_published', 'starts_at', 'expires_at', 'created_at']
    list_filter = ['is_published', 'organization']
    search_fields = ['title', 'message']


@admin.register(AnnouncementRead)
class AnnouncementReadAdmin(admin.ModelAdmin):
    list_display = ['announcement', 'user', 'organization', 'read_at']
    list_filter = ['organization']
