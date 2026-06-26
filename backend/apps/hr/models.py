from django.db import models
from apps.core.models import TenantModel


class Department(TenantModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ('organization', 'name')

    def __str__(self):
        return self.name


class Employee(TenantModel):
    EMPLOYMENT_TYPE_CHOICES = (
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('INTERN', 'Intern'),
    )
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('PROBATION', 'Probation'),
        ('NOTICE', 'Notice'),
        ('EXITED', 'Exited'),
    )
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='employee_profile')
    employee_code = models.CharField(max_length=50)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    designation = models.CharField(max_length=120, blank=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='team_members')
    phone = models.CharField(max_length=20, blank=True)
    personal_email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    permanent_address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True)
    blood_group = models.CharField(max_length=10, blank=True)
    marital_status = models.CharField(max_length=30, blank=True)
    emergency_contact_name = models.CharField(max_length=120, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relation = models.CharField(max_length=80, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=80, blank=True)
    bank_ifsc = models.CharField(max_length=30, blank=True)
    bank_branch = models.CharField(max_length=120, blank=True)
    tax_id = models.CharField(max_length=80, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='FULL_TIME')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    salary_basic = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ('organization', 'employee_code')

    def __str__(self):
        return f'{self.employee_code} - {self.user.email}'
