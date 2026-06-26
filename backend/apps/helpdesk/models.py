from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class TicketCategory(TenantModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    default_assignee = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_helpdesk_categories',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'name')
        ordering = ['name']
        indexes = [models.Index(fields=['organization', 'is_active'])]

    def __str__(self):
        return self.name


class SupportTicket(TenantModel):
    STATUS_OPEN = 'OPEN'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_PENDING_USER = 'PENDING_USER'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = (
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_PENDING_USER, 'Pending User'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_CANCELLED, 'Cancelled'),
    )
    PRIORITY_LOW = 'LOW'
    PRIORITY_MEDIUM = 'MEDIUM'
    PRIORITY_HIGH = 'HIGH'
    PRIORITY_CRITICAL = 'CRITICAL'
    PRIORITY_CHOICES = (
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_CRITICAL, 'Critical'),
    )
    SOURCE_CHOICES = (
        ('EMPLOYEE_PORTAL', 'Employee Portal'),
        ('HR', 'HR'),
        ('IT', 'IT'),
        ('OTHER', 'Other'),
    )

    ticket_number = models.CharField(max_length=60, blank=True)
    requested_by = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='support_tickets')
    category = models.ForeignKey(TicketCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_support_tickets')
    subject = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='EMPLOYEE_PORTAL')
    due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    last_response_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'priority']),
            models.Index(fields=['organization', 'assigned_to']),
            models.Index(fields=['organization', 'requested_by']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.ticket_number:
            self.ticket_number = f'TKT-{self.organization_id}-{self.pk:06d}'
            super().save(update_fields=['ticket_number'])

    @property
    def is_overdue(self):
        return bool(self.due_at and self.status not in [self.STATUS_RESOLVED, self.STATUS_CLOSED, self.STATUS_CANCELLED] and timezone.now() > self.due_at)

    def __str__(self):
        return f'{self.ticket_number or self.pk} - {self.subject}'


class TicketComment(TenantModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='helpdesk_comments')
    message = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['organization', 'ticket'])]

    def __str__(self):
        return f'Comment on {self.ticket_id}'


class TicketAttachment(TenantModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='helpdesk_attachments')
    title = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    file_data = models.BinaryField(editable=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['organization', 'ticket'])]

    def __str__(self):
        return self.file_name
