from datetime import datetime, timedelta
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class Shift(TenantModel):
    WEEKDAY_CHOICES = (
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    )
    name = models.CharField(max_length=120)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=60)
    grace_minutes = models.PositiveIntegerField(default=10)
    half_day_hours = models.DecimalField(max_digits=4, decimal_places=2, default=4)
    full_day_hours = models.DecimalField(max_digits=4, decimal_places=2, default=8)
    overtime_after_minutes = models.PositiveIntegerField(default=30)
    weekly_off_days = models.CharField(max_length=40, default='SUN', help_text='Comma-separated day codes like SUN or SAT,SUN')
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'name')
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.start_time} - {self.end_time})'

    def save(self, *args, **kwargs):
        if self.is_default:
            Shift.objects.filter(organization=self.organization, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def weekday_codes(self):
        return {item.strip().upper() for item in self.weekly_off_days.split(',') if item.strip()}

    def is_weekly_off(self, target_date):
        codes = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        return codes[target_date.weekday()] in self.weekday_codes()

    def scheduled_start_datetime(self, target_date):
        return timezone.make_aware(datetime.combine(target_date, self.start_time), timezone.get_current_timezone())

    def scheduled_end_datetime(self, target_date):
        start = self.scheduled_start_datetime(target_date)
        end = timezone.make_aware(datetime.combine(target_date, self.end_time), timezone.get_current_timezone())
        if end <= start:
            end += timedelta(days=1)
        return end

    def scheduled_work_minutes(self):
        today = timezone.localdate()
        total = int((self.scheduled_end_datetime(today) - self.scheduled_start_datetime(today)).total_seconds() // 60)
        return max(total - int(self.break_minutes), 0)


class Holiday(TenantModel):
    HOLIDAY_TYPE_CHOICES = (
        ('PUBLIC', 'Public Holiday'),
        ('COMPANY', 'Company Holiday'),
        ('FESTIVAL', 'Festival'),
        ('OPTIONAL', 'Optional Holiday'),
    )
    name = models.CharField(max_length=160)
    date = models.DateField()
    holiday_type = models.CharField(max_length=20, choices=HOLIDAY_TYPE_CHOICES, default='PUBLIC')
    is_optional = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ('organization', 'date', 'name')
        ordering = ['date']

    def __str__(self):
        return f'{self.name} - {self.date}'


class EmployeeShiftAssignment(TenantModel):
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='shift_assignments')
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='employee_assignments')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.employee} -> {self.shift.name}'

    def clean(self):
        if self.employee_id and self.shift_id and self.employee.organization_id != self.shift.organization_id:
            from django.core.exceptions import ValidationError
            raise ValidationError('Employee and shift must belong to the same organization.')


class Attendance(TenantModel):
    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('HALF_DAY', 'Half Day'),
        ('LATE', 'Late'),
        ('ON_LEAVE', 'On Leave'),
        ('HOLIDAY', 'Holiday'),
        ('WEEK_OFF', 'Weekly Off'),
    )
    WORK_MODE_CHOICES = (
        ('OFFICE', 'Office'),
        ('REMOTE', 'Remote'),
        ('HYBRID', 'Hybrid'),
        ('FIELD', 'Field'),
    )
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='attendance_records')
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')
    holiday = models.ForeignKey(Holiday, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')
    date = models.DateField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PRESENT')
    work_mode = models.CharField(max_length=20, choices=WORK_MODE_CHOICES, default='OFFICE')
    duration_minutes = models.PositiveIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    is_holiday = models.BooleanField(default=False)
    is_weekly_off = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ('organization', 'employee', 'date')
        ordering = ['-date']

    def __str__(self):
        return f'{self.employee} - {self.date}'

    def recalculate(self):
        self.is_holiday = bool(self.holiday_id)
        self.is_weekly_off = bool(self.shift and self.shift.is_weekly_off(self.date))

        if self.check_in and self.check_out:
            self.duration_minutes = max(int((self.check_out - self.check_in).total_seconds() // 60), 0)
        else:
            self.duration_minutes = 0

        self.late_minutes = 0
        self.overtime_minutes = 0

        if not self.check_in:
            if self.is_holiday:
                self.status = 'HOLIDAY'
            elif self.is_weekly_off:
                self.status = 'WEEK_OFF'
            else:
                self.status = 'ABSENT'
            return

        if self.shift:
            scheduled_start = self.shift.scheduled_start_datetime(self.date) + timedelta(minutes=self.shift.grace_minutes)
            if self.check_in > scheduled_start:
                self.late_minutes = int((self.check_in - scheduled_start).total_seconds() // 60)

            scheduled_minutes = self.shift.scheduled_work_minutes()
            overtime_threshold = scheduled_minutes + int(self.shift.overtime_after_minutes)
            if self.duration_minutes > overtime_threshold:
                self.overtime_minutes = self.duration_minutes - scheduled_minutes

            half_day_minutes = int(float(self.shift.half_day_hours) * 60)
            full_day_minutes = int(float(self.shift.full_day_hours) * 60)

            if self.check_out:
                if self.duration_minutes < half_day_minutes:
                    self.status = 'HALF_DAY'
                elif self.duration_minutes < full_day_minutes:
                    self.status = 'HALF_DAY'
                elif self.late_minutes > 0:
                    self.status = 'LATE'
                else:
                    self.status = 'PRESENT'
            else:
                self.status = 'LATE' if self.late_minutes > 0 else 'PRESENT'
        else:
            self.status = 'PRESENT'

    def save(self, *args, **kwargs):
        self.recalculate()
        super().save(*args, **kwargs)
