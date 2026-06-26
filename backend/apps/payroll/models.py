from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class PayrollRecord(TenantModel):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('HOLD', 'Hold'),
    )
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='payroll_records')
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    basic = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('organization', 'employee', 'month', 'year')
        ordering = ['-year', '-month']

    def save(self, *args, **kwargs):
        self.net_pay = self.basic + self.allowances - self.deductions
        super().save(*args, **kwargs)


class PayrollComponent(TenantModel):
    TYPE_CHOICES = (
        ('EARNING', 'Earning'),
        ('DEDUCTION', 'Deduction'),
    )
    CALCULATION_CHOICES = (
        ('FIXED', 'Fixed Amount'),
        ('PERCENT_BASIC', 'Percent of Basic'),
        ('PERCENT_GROSS', 'Percent of Gross'),
    )
    name = models.CharField(max_length=140)
    component_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    calculation_type = models.CharField(max_length=30, choices=CALCULATION_CHOICES, default='FIXED')
    default_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    default_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_taxable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'name')
        ordering = ['component_type', 'name']

    def __str__(self):
        return f'{self.name} - {self.component_type}'


class EmployeeSalaryComponent(TenantModel):
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='salary_components')
    component = models.ForeignKey(PayrollComponent, on_delete=models.CASCADE, related_name='employee_components')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'employee', 'component', 'effective_from')
        ordering = ['employee__employee_code', 'component__name']

    def __str__(self):
        return f'{self.employee} - {self.component.name}'

    def clean(self):
        if self.employee_id and self.component_id and self.employee.organization_id != self.component.organization_id:
            from django.core.exceptions import ValidationError
            raise ValidationError('Employee and payroll component must belong to the same organization.')


class PayrollRun(TenantModel):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('GENERATED', 'Generated'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
    )
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    generated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_payroll_runs')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payroll_runs')
    generated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('organization', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f'{self.organization} payroll {self.month}/{self.year}'


class Payslip(TenantModel):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
    )
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='payslips')
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='payslips')
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    basic = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expected_work_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    present_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    paid_leave_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    unpaid_leave_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    absent_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    half_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    payable_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    loss_of_pay_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    worked_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    overtime_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lop_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('organization', 'employee', 'month', 'year')
        ordering = ['-year', '-month', 'employee__employee_code']

    def save(self, *args, **kwargs):
        self.net_pay = Decimal(self.gross_earnings or 0) - Decimal(self.total_deductions or 0)
        super().save(*args, **kwargs)

    def approve(self):
        self.status = 'APPROVED'
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'approved_at', 'net_pay', 'updated_at'])

    def mark_paid(self):
        self.status = 'PAID'
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'paid_at', 'net_pay', 'updated_at'])


class PayslipLine(TenantModel):
    LINE_TYPE_CHOICES = (
        ('EARNING', 'Earning'),
        ('DEDUCTION', 'Deduction'),
    )
    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name='lines')
    component = models.ForeignKey(PayrollComponent, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=140)
    line_type = models.CharField(max_length=20, choices=LINE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['line_type', 'name']

    def __str__(self):
        return f'{self.payslip} - {self.name}'
