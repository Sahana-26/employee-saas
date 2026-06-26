from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class TrainingCourse(TenantModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_PUBLISHED = 'PUBLISHED'
    STATUS_ARCHIVED = 'ARCHIVED'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_ARCHIVED, 'Archived'),
    )
    LEVEL_CHOICES = (
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('COMPLIANCE', 'Compliance'),
    )

    code = models.CharField(max_length=80)
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=120, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='BEGINNER')
    description = models.TextField(blank=True)
    skills_covered = models.TextField(blank=True)
    duration_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_mandatory = models.BooleanField(default=False)
    audience_roles = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_training_courses')

    class Meta:
        unique_together = ('organization', 'code')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'category']),
        ]

    def __str__(self):
        return f'{self.code} - {self.title}'

    @property
    def material_count(self):
        return self.materials.count()

    @property
    def enrollment_count(self):
        return self.enrollments.count()


class TrainingMaterial(TenantModel):
    TYPE_DOCUMENT = 'DOCUMENT'
    TYPE_VIDEO = 'VIDEO'
    TYPE_LINK = 'LINK'
    TYPE_SLIDE = 'SLIDE'
    TYPE_OTHER = 'OTHER'
    TYPE_CHOICES = (
        (TYPE_DOCUMENT, 'Document'),
        (TYPE_VIDEO, 'Video'),
        (TYPE_LINK, 'Link'),
        (TYPE_SLIDE, 'Slide'),
        (TYPE_OTHER, 'Other'),
    )

    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=180)
    material_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_DOCUMENT)
    external_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    file_data = models.BinaryField(editable=False, null=True, blank=True)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_training_materials')

    class Meta:
        ordering = ['course', 'created_at']
        indexes = [models.Index(fields=['organization', 'course'])]

    def __str__(self):
        return self.title

    @property
    def has_file(self):
        return bool(self.file_data)


class TrainingEnrollment(TenantModel):
    STATUS_ASSIGNED = 'ASSIGNED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = (
        (STATUS_ASSIGNED, 'Assigned'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name='enrollments')
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='training_enrollments')
    assigned_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_training_enrollments')
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ASSIGNED)
    progress_percent = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('organization', 'course', 'employee')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'employee']),
            models.Index(fields=['organization', 'course']),
        ]

    def __str__(self):
        return f'{self.employee.employee_code} - {self.course.code}'


class TrainingAssessment(TenantModel):
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name='assessments')
    title = models.CharField(max_length=180)
    instructions = models.TextField(blank=True)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    passing_score = models.DecimalField(max_digits=8, decimal_places=2, default=60)
    questions = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_training_assessments')

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['organization', 'course', 'is_published'])]

    def __str__(self):
        return self.title


class TrainingSubmission(TenantModel):
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_PASSED = 'PASSED'
    STATUS_FAILED = 'FAILED'
    STATUS_REVIEWED = 'REVIEWED'
    STATUS_CHOICES = (
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_PASSED, 'Passed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REVIEWED, 'Reviewed'),
    )

    assessment = models.ForeignKey(TrainingAssessment, on_delete=models.CASCADE, related_name='submissions')
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='training_submissions')
    enrollment = models.ForeignKey(TrainingEnrollment, on_delete=models.SET_NULL, null=True, blank=True, related_name='submissions')
    answers = models.JSONField(default=dict, blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_training_submissions')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['organization', 'assessment']),
            models.Index(fields=['organization', 'employee']),
            models.Index(fields=['organization', 'status']),
        ]

    def __str__(self):
        return f'{self.employee.employee_code} - {self.assessment.title}'


class TrainingCertificate(TenantModel):
    certificate_number = models.CharField(max_length=120)
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='training_certificates')
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name='certificates')
    enrollment = models.OneToOneField(TrainingEnrollment, on_delete=models.CASCADE, related_name='certificate')
    issued_at = models.DateTimeField(default=timezone.now)
    issued_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_training_certificates')

    class Meta:
        unique_together = ('organization', 'certificate_number')
        ordering = ['-issued_at']
        indexes = [models.Index(fields=['organization', 'employee'])]

    def __str__(self):
        return self.certificate_number
