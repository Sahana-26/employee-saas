from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class OffboardingCase(TenantModel):
    EXIT_RESIGNATION = 'RESIGNATION'
    EXIT_TERMINATION = 'TERMINATION'
    EXIT_END_OF_CONTRACT = 'END_OF_CONTRACT'
    EXIT_RETIREMENT = 'RETIREMENT'
    EXIT_OTHER = 'OTHER'
    EXIT_TYPE_CHOICES = (
        (EXIT_RESIGNATION, 'Resignation'),
        (EXIT_TERMINATION, 'Termination'),
        (EXIT_END_OF_CONTRACT, 'End of Contract'),
        (EXIT_RETIREMENT, 'Retirement'),
        (EXIT_OTHER, 'Other'),
    )

    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_HR_REVIEW = 'HR_REVIEW'
    STATUS_CLEARANCE_IN_PROGRESS = 'CLEARANCE_IN_PROGRESS'
    STATUS_FINAL_SETTLEMENT = 'FINAL_SETTLEMENT'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_HR_REVIEW, 'HR Review'),
        (STATUS_CLEARANCE_IN_PROGRESS, 'Clearance In Progress'),
        (STATUS_FINAL_SETTLEMENT, 'Final Settlement'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='offboarding_cases')
    exit_type = models.CharField(max_length=30, choices=EXIT_TYPE_CHOICES, default=EXIT_RESIGNATION)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    resignation_date = models.DateField(null=True, blank=True)
    requested_last_working_day = models.DateField(null=True, blank=True)
    approved_last_working_day = models.DateField(null=True, blank=True)
    notice_period_days = models.PositiveIntegerField(default=0)
    reason = models.TextField(blank=True)
    employee_notes = models.TextField(blank=True)
    manager_notes = models.TextField(blank=True)
    hr_notes = models.TextField(blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_offboarding_cases')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_offboarding_cases')
    completed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_offboarding_cases')
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    login_deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'employee']),
            models.Index(fields=['organization', 'approved_last_working_day']),
        ]

    def __str__(self):
        return f'{self.employee.employee_code} - {self.exit_type} - {self.status}'

    @property
    def last_working_day(self):
        return self.approved_last_working_day or self.requested_last_working_day

    @property
    def is_terminal(self):
        return self.status in [self.STATUS_COMPLETED, self.STATUS_REJECTED, self.STATUS_CANCELLED]


class OffboardingClearanceTask(TenantModel):
    DEPT_HR = 'HR'
    DEPT_IT = 'IT'
    DEPT_FINANCE = 'FINANCE'
    DEPT_MANAGER = 'MANAGER'
    DEPT_ADMIN = 'ADMIN'
    DEPT_OTHER = 'OTHER'
    DEPARTMENT_CHOICES = (
        (DEPT_HR, 'HR'),
        (DEPT_IT, 'IT'),
        (DEPT_FINANCE, 'Finance'),
        (DEPT_MANAGER, 'Manager'),
        (DEPT_ADMIN, 'Admin'),
        (DEPT_OTHER, 'Other'),
    )

    STATUS_PENDING = 'PENDING'
    STATUS_CLEARED = 'CLEARED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_WAIVED = 'WAIVED'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_CLEARED, 'Cleared'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_WAIVED, 'Waived'),
    )

    case = models.ForeignKey(OffboardingCase, on_delete=models.CASCADE, related_name='clearance_tasks')
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES, default=DEPT_HR)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_offboarding_tasks')
    due_date = models.DateField(null=True, blank=True)
    cleared_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='cleared_offboarding_tasks')
    cleared_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['status', 'due_date', 'created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'case']),
        ]

    def __str__(self):
        return f'{self.case.employee.employee_code} - {self.title}'


class FinalSettlement(TenantModel):
    STATUS_DRAFT = 'DRAFT'
    STATUS_APPROVED = 'APPROVED'
    STATUS_PAID = 'PAID'
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_PAID, 'Paid'),
    )

    case = models.OneToOneField(OffboardingCase, on_delete=models.CASCADE, related_name='final_settlement')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    salary_days = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    basic_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    leave_encashment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expense_reimbursement = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notice_recovery = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    asset_recovery = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prepared_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='prepared_final_settlements')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_final_settlements')
    paid_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='paid_final_settlements')
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['organization', 'status'])]

    def save(self, *args, **kwargs):
        earnings = self.basic_pay + self.leave_encashment + self.bonus + self.expense_reimbursement
        deductions = self.notice_recovery + self.asset_recovery + self.tax_deduction + self.other_deductions
        self.net_payable = earnings - deductions
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.case.employee.employee_code} - {self.net_payable}'


class OffboardingDocument(TenantModel):
    TYPE_RESIGNATION = 'RESIGNATION'
    TYPE_RELIEVING = 'RELIEVING'
    TYPE_EXPERIENCE = 'EXPERIENCE'
    TYPE_SETTLEMENT = 'SETTLEMENT'
    TYPE_CLEARANCE = 'CLEARANCE'
    TYPE_OTHER = 'OTHER'
    TYPE_CHOICES = (
        (TYPE_RESIGNATION, 'Resignation'),
        (TYPE_RELIEVING, 'Relieving Letter'),
        (TYPE_EXPERIENCE, 'Experience Letter'),
        (TYPE_SETTLEMENT, 'Settlement'),
        (TYPE_CLEARANCE, 'Clearance'),
        (TYPE_OTHER, 'Other'),
    )

    case = models.ForeignKey(OffboardingCase, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=180)
    document_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default=TYPE_OTHER)
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    data = models.BinaryField(editable=False)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_offboarding_documents')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['organization', 'case'])]

    def __str__(self):
        return f'{self.case.employee.employee_code} - {self.title}'
