from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class PerformanceCycle(TenantModel):
    PERIOD_ANNUAL = 'ANNUAL'
    PERIOD_HALF_YEARLY = 'HALF_YEARLY'
    PERIOD_QUARTERLY = 'QUARTERLY'
    PERIOD_PROBATION = 'PROBATION'
    PERIOD_PROJECT = 'PROJECT'
    PERIOD_CHOICES = (
        (PERIOD_ANNUAL, 'Annual'),
        (PERIOD_HALF_YEARLY, 'Half Yearly'),
        (PERIOD_QUARTERLY, 'Quarterly'),
        (PERIOD_PROBATION, 'Probation'),
        (PERIOD_PROJECT, 'Project'),
    )

    STATUS_DRAFT = 'DRAFT'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CLOSED, 'Closed'),
    )

    name = models.CharField(max_length=160)
    year = models.PositiveIntegerField()
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default=PERIOD_ANNUAL)
    start_date = models.DateField()
    end_date = models.DateField()
    self_review_start = models.DateField(null=True, blank=True)
    self_review_end = models.DateField(null=True, blank=True)
    manager_review_start = models.DateField(null=True, blank=True)
    manager_review_end = models.DateField(null=True, blank=True)
    hr_calibration_start = models.DateField(null=True, blank=True)
    hr_calibration_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_performance_cycles')
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('organization', 'name', 'year')
        ordering = ['-year', '-start_date']

    def __str__(self):
        return f'{self.name} - {self.year}'

    def publish(self):
        self.status = self.STATUS_ACTIVE
        self.published_at = timezone.now()
        self.closed_at = None
        self.save(update_fields=['status', 'published_at', 'closed_at', 'updated_at'])

    def close(self):
        self.status = self.STATUS_CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at', 'updated_at'])


class PerformanceGoal(TenantModel):
    CATEGORY_KRA = 'KRA'
    CATEGORY_SKILL = 'SKILL'
    CATEGORY_BEHAVIOR = 'BEHAVIOR'
    CATEGORY_PROJECT = 'PROJECT'
    CATEGORY_LEADERSHIP = 'LEADERSHIP'
    CATEGORY_CHOICES = (
        (CATEGORY_KRA, 'KRA'),
        (CATEGORY_SKILL, 'Skill Development'),
        (CATEGORY_BEHAVIOR, 'Behaviour'),
        (CATEGORY_PROJECT, 'Project'),
        (CATEGORY_LEADERSHIP, 'Leadership'),
    )

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

    cycle = models.ForeignKey(PerformanceCycle, on_delete=models.CASCADE, related_name='goals')
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='performance_goals')
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_KRA)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    target_value = models.CharField(max_length=120, blank=True)
    measurement_unit = models.CharField(max_length=80, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    self_rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
    self_comment = models.TextField(blank=True)
    manager_rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
    manager_comment = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_performance_goals')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_performance_goals')
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['cycle', 'employee', 'id']

    def __str__(self):
        return f'{self.employee} - {self.title}'


class PerformanceReview(TenantModel):
    STATUS_NOT_STARTED = 'NOT_STARTED'
    STATUS_SELF_REVIEW = 'SELF_REVIEW'
    STATUS_MANAGER_REVIEW = 'MANAGER_REVIEW'
    STATUS_HR_REVIEW = 'HR_REVIEW'
    STATUS_FINALIZED = 'FINALIZED'
    STATUS_CHOICES = (
        (STATUS_NOT_STARTED, 'Not Started'),
        (STATUS_SELF_REVIEW, 'Self Review Submitted'),
        (STATUS_MANAGER_REVIEW, 'Manager Review Submitted'),
        (STATUS_HR_REVIEW, 'HR Calibration'),
        (STATUS_FINALIZED, 'Finalized'),
    )

    cycle = models.ForeignKey(PerformanceCycle, on_delete=models.CASCADE, related_name='reviews')
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='performance_reviews')
    manager = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_performance_reviews')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_NOT_STARTED)
    self_summary = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    improvement_areas = models.TextField(blank=True)
    career_goals = models.TextField(blank=True)
    self_submitted_at = models.DateTimeField(null=True, blank=True)
    manager_summary = models.TextField(blank=True)
    manager_rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
    manager_submitted_at = models.DateTimeField(null=True, blank=True)
    hr_comments = models.TextField(blank=True)
    final_rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
    final_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    finalized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='finalized_performance_reviews')
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('organization', 'cycle', 'employee')
        ordering = ['-cycle__year', 'employee__employee_code']

    def __str__(self):
        return f'{self.employee} - {self.cycle}'
