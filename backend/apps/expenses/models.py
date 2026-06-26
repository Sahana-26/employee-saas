from django.db import models
from apps.core.models import TenantModel


class ExpenseCategory(TenantModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class ExpenseClaim(TenantModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_PAID = 'PAID'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_PAID, 'Paid'),
    )

    PAYMENT_MODE_CHOICES = (
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH', 'Cash'),
        ('UPI', 'UPI'),
        ('CHEQUE', 'Cheque'),
        ('OTHER', 'Other'),
    )

    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='expense_claims')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='claims')
    claim_number = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=180)
    expense_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)

    receipt_file_name = models.CharField(max_length=255, blank=True)
    receipt_content_type = models.CharField(max_length=120, blank=True)
    receipt_size = models.PositiveIntegerField(default=0)
    receipt_data = models.BinaryField(editable=False, null=True, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_expenses')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    paid_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='paid_expenses')
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_mode = models.CharField(max_length=30, choices=PAYMENT_MODE_CHOICES, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    finance_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'expense_date']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.claim_number:
            self.claim_number = f'EXP-{self.organization_id}-{self.pk:06d}'
            super().save(update_fields=['claim_number'])

    def __str__(self):
        return f'{self.claim_number or self.pk} - {self.employee}'
