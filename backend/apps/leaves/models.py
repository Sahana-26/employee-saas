from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class LeaveType(TenantModel):
    name = models.CharField(max_length=120)
    days_per_year = models.PositiveIntegerField(default=12)
    requires_approval = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'name')

    def __str__(self):
        return self.name


class LeaveBalance(TenantModel):
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveIntegerField(default=timezone.now().year)
    allocated = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        unique_together = ('organization', 'employee', 'leave_type', 'year')

    @property
    def remaining(self):
        return self.allocated - self.used


class LeaveRequest(TenantModel):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    )
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=6, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approver = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
