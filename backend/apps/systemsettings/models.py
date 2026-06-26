from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class OrganizationSetting(TenantModel):
    DATE_FORMAT_CHOICES = (
        ('DD-MM-YYYY', 'DD-MM-YYYY'),
        ('MM-DD-YYYY', 'MM-DD-YYYY'),
        ('YYYY-MM-DD', 'YYYY-MM-DD'),
    )
    app_name = models.CharField(max_length=120, default='EmployeeHub')
    country = models.CharField(max_length=80, default='India')
    timezone = models.CharField(max_length=80, default='Asia/Kolkata')
    date_format = models.CharField(max_length=20, choices=DATE_FORMAT_CHOICES, default='DD-MM-YYYY')
    currency = models.CharField(max_length=10, default='INR')
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=4)
    leave_year_start_month = models.PositiveSmallIntegerField(default=1)
    standard_working_hours_per_day = models.DecimalField(max_digits=4, decimal_places=2, default=8)
    attendance_grace_minutes = models.PositiveIntegerField(default=10)
    half_day_threshold_hours = models.DecimalField(max_digits=4, decimal_places=2, default=4)
    overtime_rate_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    weekly_off_days = models.JSONField(default=list, blank=True)
    default_notice_period_days = models.PositiveIntegerField(default=30)
    default_probation_days = models.PositiveIntegerField(default=90)
    payroll_lock_day = models.PositiveSmallIntegerField(default=7)
    document_max_upload_mb = models.PositiveIntegerField(default=10)
    data_retention_days = models.PositiveIntegerField(default=2555)
    support_email = models.EmailField(blank=True)
    allow_employee_profile_edit = models.BooleanField(default=True)
    allow_employee_self_attendance = models.BooleanField(default=True)
    allow_employee_expense_submission = models.BooleanField(default=True)
    allow_employee_self_enrollment = models.BooleanField(default=True)
    enable_ip_restriction = models.BooleanField(default=False)
    allowed_ip_ranges = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('organization',)

    def __str__(self):
        return f'Settings - {self.organization.name}'


class BackupLog(TenantModel):
    BACKUP_TYPE_CHOICES = (
        ('FULL_DB', 'Full Database'),
        ('SCHEMA_ONLY', 'Schema Only'),
        ('DATA_ONLY', 'Data Only'),
        ('MANUAL_EXPORT', 'Manual Export'),
    )
    STATUS_CHOICES = (
        ('REQUESTED', 'Requested'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    backup_type = models.CharField(max_length=30, choices=BACKUP_TYPE_CHOICES, default='FULL_DB')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')
    requested_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='backup_logs')
    file_name = models.CharField(max_length=255, blank=True)
    command_used = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def mark_running(self):
        self.status = 'RUNNING'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])

    def mark_completed(self):
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def mark_failed(self, notes=''):
        self.status = 'FAILED'
        self.notes = notes or self.notes
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'notes', 'completed_at', 'updated_at'])

    def __str__(self):
        return f'{self.organization.name} - {self.backup_type} - {self.status}'
