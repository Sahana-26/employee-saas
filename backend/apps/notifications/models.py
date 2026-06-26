from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class Notification(TenantModel):
    TYPE_INFO = 'INFO'
    TYPE_SUCCESS = 'SUCCESS'
    TYPE_WARNING = 'WARNING'
    TYPE_ACTION = 'ACTION'
    TYPE_CHOICES = (
        (TYPE_INFO, 'Info'),
        (TYPE_SUCCESS, 'Success'),
        (TYPE_WARNING, 'Warning'),
        (TYPE_ACTION, 'Action Required'),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_notifications')
    title = models.CharField(max_length=180)
    message = models.TextField(blank=True)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_INFO)
    related_module = models.CharField(max_length=80, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    action_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'recipient', 'is_read']),
            models.Index(fields=['organization', 'related_module']),
        ]

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])

    def mark_unread(self):
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])

    def __str__(self):
        return f'{self.recipient.email} - {self.title}'


class Announcement(TenantModel):
    title = models.CharField(max_length=180)
    message = models.TextField()
    audience_roles = models.JSONField(default=list, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_announcements')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'is_published']),
            models.Index(fields=['organization', 'starts_at', 'expires_at']),
        ]

    def is_active_now(self):
        now = timezone.now()
        if not self.is_published:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    def applies_to_role(self, role):
        if not self.audience_roles:
            return True
        return role in self.audience_roles

    def __str__(self):
        return self.title


class AnnouncementRead(TenantModel):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcement_reads')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('announcement', 'user')
        ordering = ['-read_at']

    def __str__(self):
        return f'{self.user.email} read {self.announcement_id}'
