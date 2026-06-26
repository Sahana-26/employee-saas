from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class WorkProject(TenantModel):
    STATUS_PLANNED = 'PLANNED'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_ON_HOLD = 'ON_HOLD'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = (
        (STATUS_PLANNED, 'Planned'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ON_HOLD, 'On Hold'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    project_code = models.CharField(max_length=60)
    name = models.CharField(max_length=180)
    client_name = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)
    project_manager = models.ForeignKey(
        'hr.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_work_projects',
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    is_billable = models.BooleanField(default=True)
    budget_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ('organization', 'project_code')
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'project_manager']),
        ]

    def __str__(self):
        return f'{self.project_code} - {self.name}'


class ProjectMembership(TenantModel):
    ROLE_MEMBER = 'MEMBER'
    ROLE_LEAD = 'LEAD'
    ROLE_MANAGER = 'MANAGER'
    ROLE_QA = 'QA'
    ROLE_CHOICES = (
        (ROLE_MEMBER, 'Member'),
        (ROLE_LEAD, 'Lead'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_QA, 'QA'),
    )

    project = models.ForeignKey(WorkProject, on_delete=models.CASCADE, related_name='memberships')
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='project_memberships')
    project_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateField(default=timezone.localdate)
    released_at = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('organization', 'project', 'employee')
        ordering = ['project__name', 'employee__employee_code']
        indexes = [
            models.Index(fields=['organization', 'project', 'is_active']),
            models.Index(fields=['organization', 'employee', 'is_active']),
        ]

    def __str__(self):
        return f'{self.project.name} - {self.employee.employee_code}'


class ProjectTask(TenantModel):
    STATUS_TODO = 'TODO'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_REVIEW = 'REVIEW'
    STATUS_DONE = 'DONE'
    STATUS_BLOCKED = 'BLOCKED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = (
        (STATUS_TODO, 'To Do'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_REVIEW, 'Review'),
        (STATUS_DONE, 'Done'),
        (STATUS_BLOCKED, 'Blocked'),
        (STATUS_CANCELLED, 'Cancelled'),
    )
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )

    project = models.ForeignKey(WorkProject, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_project_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'project', 'status']),
            models.Index(fields=['organization', 'assigned_to', 'status']),
        ]

    def __str__(self):
        return f'{self.project.project_code} - {self.title}'


class TimesheetEntry(TenantModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    )

    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='timesheet_entries')
    project = models.ForeignKey(WorkProject, on_delete=models.CASCADE, related_name='timesheet_entries')
    task = models.ForeignKey(ProjectTask, on_delete=models.SET_NULL, null=True, blank=True, related_name='timesheet_entries')
    work_date = models.DateField(default=timezone.localdate)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    approved_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_billable = models.BooleanField(default=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_timesheets')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-work_date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'employee', 'work_date']),
            models.Index(fields=['organization', 'project', 'work_date']),
            models.Index(fields=['organization', 'status']),
        ]

    def submit(self):
        self.status = self.STATUS_SUBMITTED
        self.submitted_at = timezone.now()
        self.rejection_reason = ''

    def approve(self, user, approved_hours=None):
        self.status = self.STATUS_APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.rejection_reason = ''
        self.approved_hours = approved_hours if approved_hours is not None else self.hours

    def reject(self, user, reason=''):
        self.status = self.STATUS_REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.approved_hours = Decimal('0')

    def reopen(self):
        self.status = self.STATUS_DRAFT
        self.reviewed_by = None
        self.reviewed_at = None
        self.rejection_reason = ''
        self.approved_hours = Decimal('0')

    def __str__(self):
        return f'{self.employee.employee_code} - {self.project.project_code} - {self.work_date}'
