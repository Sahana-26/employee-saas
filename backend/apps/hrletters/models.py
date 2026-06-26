from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class LetterTemplate(TenantModel):
    CATEGORY_OFFER = 'OFFER'
    CATEGORY_APPOINTMENT = 'APPOINTMENT'
    CATEGORY_CONFIRMATION = 'CONFIRMATION'
    CATEGORY_INCREMENT = 'INCREMENT'
    CATEGORY_SALARY = 'SALARY'
    CATEGORY_EXPERIENCE = 'EXPERIENCE'
    CATEGORY_RELIEVING = 'RELIEVING'
    CATEGORY_WARNING = 'WARNING'
    CATEGORY_NOC = 'NOC'
    CATEGORY_OTHER = 'OTHER'
    CATEGORY_CHOICES = (
        (CATEGORY_OFFER, 'Offer Letter'),
        (CATEGORY_APPOINTMENT, 'Appointment Letter'),
        (CATEGORY_CONFIRMATION, 'Confirmation Letter'),
        (CATEGORY_INCREMENT, 'Increment Letter'),
        (CATEGORY_SALARY, 'Salary Certificate'),
        (CATEGORY_EXPERIENCE, 'Experience Letter'),
        (CATEGORY_RELIEVING, 'Relieving Letter'),
        (CATEGORY_WARNING, 'Warning Letter'),
        (CATEGORY_NOC, 'NOC'),
        (CATEGORY_OTHER, 'Other'),
    )

    code = models.CharField(max_length=60)
    name = models.CharField(max_length=180)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    version = models.CharField(max_length=30, default='1.0')
    description = models.TextField(blank=True)
    content = models.TextField(help_text='Use Django-style variables like {{ employee.employee_code }} or {{ custom.amount }}.')
    available_variables = models.JSONField(default=list, blank=True)
    requires_approval = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_letter_templates')

    class Meta:
        unique_together = ('organization', 'code', 'version')
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['organization', 'is_active']),
        ]

    def archive(self):
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def activate(self):
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])

    def __str__(self):
        return f'{self.code} v{self.version}'


class GeneratedLetter(TenantModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_GENERATED = 'GENERATED'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_SIGNED = 'SIGNED'
    STATUS_ISSUED = 'ISSUED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_GENERATED, 'Generated'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_SIGNED, 'Signed'),
        (STATUS_ISSUED, 'Issued'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='generated_letters')
    template = models.ForeignKey(LetterTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_letters')
    letter_number = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=220)
    category = models.CharField(max_length=30, choices=LetterTemplate.CATEGORY_CHOICES, default=LetterTemplate.CATEGORY_OTHER)
    custom_variables = models.JSONField(default=dict, blank=True)
    rendered_content = models.TextField(blank=True)
    document_data = models.BinaryField(null=True, blank=True)
    document_filename = models.CharField(max_length=255, blank=True)
    document_content_type = models.CharField(max_length=120, blank=True)
    document_size = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_letters')
    generated_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_letters')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_letters')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    signed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='signed_letters')
    signed_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_letters')
    issued_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ('organization', 'letter_number')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'employee', 'status']),
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['organization', 'status']),
        ]

    def set_generated_document(self, content):
        content = content or ''
        safe_number = self.letter_number or f'letter-{self.pk or "draft"}'
        self.rendered_content = content
        self.document_data = content.encode('utf-8')
        self.document_content_type = 'text/html; charset=utf-8'
        self.document_filename = f'{safe_number}.html'.replace('/', '-').replace(' ', '-')
        self.document_size = len(self.document_data)
        self.generated_at = timezone.now()
        if self.status in [self.STATUS_DRAFT, self.STATUS_REJECTED]:
            self.status = self.STATUS_GENERATED

    def approve(self, user):
        self.status = self.STATUS_APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.rejection_reason = ''

    def reject(self, user, reason=''):
        self.status = self.STATUS_REJECTED
        self.rejected_by = user
        self.rejected_at = timezone.now()
        self.rejection_reason = reason

    def sign(self, user):
        self.status = self.STATUS_SIGNED
        self.signed_by = user
        self.signed_at = timezone.now()

    def issue(self, user):
        self.status = self.STATUS_ISSUED
        self.issued_by = user
        self.issued_at = timezone.now()

    def cancel(self):
        self.status = self.STATUS_CANCELLED

    def __str__(self):
        return self.letter_number or self.title


class LetterAudit(TenantModel):
    letter = models.ForeignKey(GeneratedLetter, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=80)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='letter_audit_events')
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['organization', 'letter', 'action'])]

    def __str__(self):
        return f'{self.letter_id} - {self.action}'
