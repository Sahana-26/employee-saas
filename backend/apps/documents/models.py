from django.db import models
from apps.core.models import TenantModel


class EmployeeDocument(TenantModel):
    CATEGORY_CHOICES = (
        ('ID', 'Identity'),
        ('CONTRACT', 'Contract'),
        ('CERTIFICATE', 'Certificate'),
        ('PAYSLIP', 'Payslip'),
        ('OTHER', 'Other'),
    )
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='OTHER')
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, default='application/octet-stream')
    size = models.PositiveIntegerField(default=0)
    data = models.BinaryField(editable=False)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.title} - {self.file_name}'
