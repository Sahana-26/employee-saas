from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class JobOpening(TenantModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_OPEN = 'OPEN'
    STATUS_ON_HOLD = 'ON_HOLD'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_OPEN, 'Open'),
        (STATUS_ON_HOLD, 'On Hold'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_CANCELLED, 'Cancelled'),
    )
    EMPLOYMENT_TYPE_CHOICES = (
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('INTERN', 'Intern'),
    )
    WORK_MODE_CHOICES = (
        ('OFFICE', 'Office'),
        ('REMOTE', 'Remote'),
        ('HYBRID', 'Hybrid'),
        ('FIELD', 'Field'),
    )

    job_code = models.CharField(max_length=60)
    title = models.CharField(max_length=180)
    department = models.ForeignKey('hr.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='job_openings')
    hiring_manager = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_job_openings')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='FULL_TIME')
    work_mode = models.CharField(max_length=20, choices=WORK_MODE_CHOICES, default='OFFICE')
    location = models.CharField(max_length=180, blank=True)
    openings_count = models.PositiveIntegerField(default=1)
    min_experience = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_experience = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    target_start_date = models.DateField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_job_openings')

    class Meta:
        unique_together = ('organization', 'job_code')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'department']),
            models.Index(fields=['organization', 'hiring_manager']),
        ]

    def __str__(self):
        return f'{self.job_code} - {self.title}'

    @property
    def candidate_count(self):
        return self.candidates.count()


class Candidate(TenantModel):
    STATUS_NEW = 'NEW'
    STATUS_SCREENING = 'SCREENING'
    STATUS_SHORTLISTED = 'SHORTLISTED'
    STATUS_INTERVIEW = 'INTERVIEW'
    STATUS_OFFERED = 'OFFERED'
    STATUS_HIRED = 'HIRED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_ON_HOLD = 'ON_HOLD'
    STATUS_CHOICES = (
        (STATUS_NEW, 'New'),
        (STATUS_SCREENING, 'Screening'),
        (STATUS_SHORTLISTED, 'Shortlisted'),
        (STATUS_INTERVIEW, 'Interview'),
        (STATUS_OFFERED, 'Offered'),
        (STATUS_HIRED, 'Hired'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_ON_HOLD, 'On Hold'),
    )
    SOURCE_CHOICES = (
        ('JOB_PORTAL', 'Job Portal'),
        ('LINKEDIN', 'LinkedIn'),
        ('REFERRAL', 'Referral'),
        ('AGENCY', 'Agency'),
        ('WALK_IN', 'Walk-in'),
        ('CAREERS_PAGE', 'Careers Page'),
        ('OTHER', 'Other'),
    )

    job_opening = models.ForeignKey(JobOpening, on_delete=models.SET_NULL, null=True, blank=True, related_name='candidates')
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='OTHER')
    current_company = models.CharField(max_length=180, blank=True)
    current_designation = models.CharField(max_length=180, blank=True)
    experience_years = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    current_ctc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expected_ctc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notice_period_days = models.PositiveIntegerField(default=0)
    skills = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    resume_file_name = models.CharField(max_length=255, blank=True)
    resume_content_type = models.CharField(max_length=120, blank=True)
    resume_size = models.PositiveIntegerField(default=0)
    resume_data = models.BinaryField(editable=False, null=True, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_candidates')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'job_opening']),
            models.Index(fields=['organization', 'email']),
        ]

    def __str__(self):
        return f'{self.full_name} - {self.email}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class InterviewRound(TenantModel):
    TYPE_HR = 'HR'
    TYPE_TECHNICAL = 'TECHNICAL'
    TYPE_MANAGERIAL = 'MANAGERIAL'
    TYPE_FINAL = 'FINAL'
    TYPE_CHOICES = (
        (TYPE_HR, 'HR'),
        (TYPE_TECHNICAL, 'Technical'),
        (TYPE_MANAGERIAL, 'Managerial'),
        (TYPE_FINAL, 'Final'),
    )
    STATUS_SCHEDULED = 'SCHEDULED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_NO_SHOW = 'NO_SHOW'
    STATUS_CHOICES = (
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_NO_SHOW, 'No Show'),
    )
    RESULT_PENDING = 'PENDING'
    RESULT_SELECTED = 'SELECTED'
    RESULT_REJECTED = 'REJECTED'
    RESULT_HOLD = 'HOLD'
    RESULT_CHOICES = (
        (RESULT_PENDING, 'Pending'),
        (RESULT_SELECTED, 'Selected'),
        (RESULT_REJECTED, 'Rejected'),
        (RESULT_HOLD, 'Hold'),
    )
    MODE_CHOICES = (
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
        ('PHONE', 'Phone'),
    )

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='interviews')
    job_opening = models.ForeignKey(JobOpening, on_delete=models.SET_NULL, null=True, blank=True, related_name='interviews')
    round_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default=TYPE_HR)
    interviewer = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='interview_rounds')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='ONLINE')
    meeting_link = models.URLField(blank=True)
    location = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default=RESULT_PENDING)
    rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    feedback = models.TextField(blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_interviews')
    completed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_interviews')
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-scheduled_at', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'candidate']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'interviewer']),
        ]

    def __str__(self):
        return f'{self.candidate.full_name} - {self.round_type}'


class OfferLetter(TenantModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SENT = 'SENT'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_WITHDRAWN = 'WITHDRAWN'
    STATUS_CONVERTED = 'CONVERTED'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SENT, 'Sent'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
        (STATUS_CONVERTED, 'Converted'),
    )

    offer_number = models.CharField(max_length=80)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='offers')
    job_opening = models.ForeignKey(JobOpening, on_delete=models.SET_NULL, null=True, blank=True, related_name='offers')
    department = models.ForeignKey('hr.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='offer_letters')
    offered_designation = models.CharField(max_length=180)
    joining_date = models.DateField(null=True, blank=True)
    salary_basic = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ctc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    notes = models.TextField(blank=True)
    document_file_name = models.CharField(max_length=255, blank=True)
    document_content_type = models.CharField(max_length=120, blank=True)
    document_size = models.PositiveIntegerField(default=0)
    document_data = models.BinaryField(editable=False, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_offer_letters')
    converted_employee = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_offer_letters')

    class Meta:
        unique_together = ('organization', 'offer_number')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'candidate']),
            models.Index(fields=['organization', 'job_opening']),
        ]

    def __str__(self):
        return f'{self.offer_number} - {self.candidate.full_name}'

    @property
    def is_expired(self):
        return bool(self.valid_until and self.valid_until < timezone.localdate())
