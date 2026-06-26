from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class CompanyPolicy(TenantModel):
    CATEGORY_HR = 'HR'
    CATEGORY_ATTENDANCE = 'ATTENDANCE'
    CATEGORY_LEAVE = 'LEAVE'
    CATEGORY_PAYROLL = 'PAYROLL'
    CATEGORY_EXPENSE = 'EXPENSE'
    CATEGORY_IT = 'IT'
    CATEGORY_SECURITY = 'SECURITY'
    CATEGORY_CONDUCT = 'CONDUCT'
    CATEGORY_OTHER = 'OTHER'
    CATEGORY_CHOICES = (
        (CATEGORY_HR, 'HR'),
        (CATEGORY_ATTENDANCE, 'Attendance'),
        (CATEGORY_LEAVE, 'Leave'),
        (CATEGORY_PAYROLL, 'Payroll'),
        (CATEGORY_EXPENSE, 'Expense'),
        (CATEGORY_IT, 'IT'),
        (CATEGORY_SECURITY, 'Security'),
        (CATEGORY_CONDUCT, 'Code of Conduct'),
        (CATEGORY_OTHER, 'Other'),
    )

    title = models.CharField(max_length=180)
    code = models.CharField(max_length=60)
    version = models.CharField(max_length=30, default='1.0')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_HR)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    audience_roles = models.JSONField(default=list, blank=True)
    requires_acknowledgement = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    document_file_name = models.CharField(max_length=255, blank=True)
    document_content_type = models.CharField(max_length=120, blank=True)
    document_size = models.PositiveIntegerField(default=0)
    document_data = models.BinaryField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_policies')

    class Meta:
        ordering = ['-created_at']
        unique_together = ('organization', 'code', 'version')
        indexes = [
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['organization', 'is_published']),
            models.Index(fields=['organization', 'code', 'version']),
        ]

    def publish(self):
        self.is_published = True
        self.published_at = timezone.now()
        self.archived_at = None
        self.save(update_fields=['is_published', 'published_at', 'archived_at', 'updated_at'])

    def archive(self):
        self.is_published = False
        self.archived_at = timezone.now()
        self.save(update_fields=['is_published', 'archived_at', 'updated_at'])

    def applies_to_role(self, role):
        if not self.audience_roles:
            return True
        return role in self.audience_roles

    def __str__(self):
        return f'{self.code} v{self.version} - {self.title}'


class PolicyAcknowledgement(TenantModel):
    policy = models.ForeignKey(CompanyPolicy, on_delete=models.CASCADE, related_name='acknowledgements')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='policy_acknowledgements')
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        unique_together = ('policy', 'user')
        ordering = ['-acknowledged_at']
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['organization', 'policy']),
        ]

    def __str__(self):
        return f'{self.user.email} acknowledged {self.policy_id}'
