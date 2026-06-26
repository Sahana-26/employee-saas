import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import MANAGER_ROLES, PAYROLL_ROLES, IsPayroll, get_role
from apps.attendance.models import Attendance
from apps.attendance.views import get_employee_shift, get_holiday
from apps.hr.models import Employee
from apps.leaves.models import LeaveRequest
from apps.notifications.services import notify_employee, notify_roles
from .models import (
    EmployeeSalaryComponent,
    PayrollComponent,
    PayrollRecord,
    PayrollRun,
    Payslip,
    PayslipLine,
)
from .serializers import (
    EmployeeSalaryComponentSerializer,
    PayrollComponentSerializer,
    PayrollRecordSerializer,
    PayrollRunSerializer,
    PayslipSerializer,
)

TWO_PLACES = Decimal('0.01')
ONE_DAY = Decimal('1')
HALF_DAY = Decimal('0.5')


def money(value):
    return Decimal(value or 0).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def daterange(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def month_bounds(year, month):
    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])
    return start_date, end_date


def get_payroll_queryset_totals(queryset):
    summary = queryset.aggregate(
        payslip_count=Count('id'),
        total_gross=Sum('gross_earnings'),
        total_deductions=Sum('total_deductions'),
        total_net=Sum('net_pay'),
    )
    return {
        'payslip_count': summary['payslip_count'] or 0,
        'total_gross': money(summary['total_gross']),
        'total_deductions': money(summary['total_deductions']),
        'total_net': money(summary['total_net']),
    }


def attendance_summary(employee, org, start_date, end_date):
    attendance_qs = Attendance.objects.filter(
        organization=org,
        employee=employee,
        date__gte=start_date,
        date__lte=end_date,
    ).select_related('shift', 'holiday')
    attendance_by_date = {item.date: item for item in attendance_qs}

    approved_leaves = LeaveRequest.objects.filter(
        organization=org,
        employee=employee,
        status='APPROVED',
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).select_related('leave_type')

    leave_by_date = {}
    for leave in approved_leaves:
        overlap_start = max(leave.start_date, start_date)
        overlap_end = min(leave.end_date, end_date)
        for item_date in daterange(overlap_start, overlap_end):
            leave_by_date[item_date] = leave

    summary = {
        'expected_work_days': Decimal('0'),
        'present_days': Decimal('0'),
        'paid_leave_days': Decimal('0'),
        'unpaid_leave_days': Decimal('0'),
        'absent_days': Decimal('0'),
        'half_days': Decimal('0'),
        'payable_days': Decimal('0'),
        'loss_of_pay_days': Decimal('0'),
        'worked_minutes': 0,
        'overtime_minutes': 0,
    }

    for item_date in daterange(start_date, end_date):
        shift = get_employee_shift(employee, item_date)
        holiday = get_holiday(org, item_date)
        is_weekly_off = bool(shift and shift.is_weekly_off(item_date))
        is_expected_workday = not holiday and not is_weekly_off
        record = attendance_by_date.get(item_date)
        leave = leave_by_date.get(item_date)

        if not is_expected_workday:
            if record:
                summary['worked_minutes'] += record.duration_minutes or 0
                summary['overtime_minutes'] += record.overtime_minutes or 0
            continue

        summary['expected_work_days'] += ONE_DAY

        if record:
            summary['worked_minutes'] += record.duration_minutes or 0
            summary['overtime_minutes'] += record.overtime_minutes or 0

        if leave:
            if leave.leave_type.is_paid:
                summary['paid_leave_days'] += ONE_DAY
            else:
                summary['unpaid_leave_days'] += ONE_DAY
            continue

        if record:
            if record.status == 'HALF_DAY':
                summary['present_days'] += HALF_DAY
                summary['half_days'] += ONE_DAY
            elif record.status in ['PRESENT', 'LATE']:
                summary['present_days'] += ONE_DAY
            elif record.status == 'ABSENT':
                summary['absent_days'] += ONE_DAY
            elif record.status == 'ON_LEAVE':
                summary['paid_leave_days'] += ONE_DAY
        else:
            summary['absent_days'] += ONE_DAY

    summary['loss_of_pay_days'] = summary['unpaid_leave_days'] + summary['absent_days'] + (summary['half_days'] * HALF_DAY)
    summary['payable_days'] = max(summary['expected_work_days'] - summary['loss_of_pay_days'], Decimal('0'))
    return summary


def active_salary_components(employee, org, end_date):
    return EmployeeSalaryComponent.objects.filter(
        organization=org,
        employee=employee,
        is_active=True,
        component__is_active=True,
    ).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=end_date),
        Q(effective_to__isnull=True) | Q(effective_to__gte=end_date),
    )


def component_amount(item, basic, gross_base):
    component = item.component
    amount = Decimal(item.amount or 0)
    percent = Decimal(item.percent or 0)
    if amount == 0:
        amount = Decimal(component.default_amount or 0)
    if percent == 0:
        percent = Decimal(component.default_percent or 0)

    if component.calculation_type == 'FIXED':
        return money(amount)
    if component.calculation_type == 'PERCENT_BASIC':
        return money(basic * percent / Decimal('100'))
    if component.calculation_type == 'PERCENT_GROSS':
        return money(gross_base * percent / Decimal('100'))
    return money(0)


def generate_payslip_for_employee(payroll_run, employee):
    org = payroll_run.organization
    start_date, end_date = month_bounds(payroll_run.year, payroll_run.month)
    summary = attendance_summary(employee, org, start_date, end_date)

    basic = money(employee.salary_basic)
    lines = []
    gross_earnings = basic

    if basic > 0:
        lines.append({
            'name': 'Basic Salary',
            'line_type': 'EARNING',
            'amount': basic,
            'notes': 'Monthly basic salary from employee profile.',
        })

    components = active_salary_components(employee, org, end_date).select_related('component')
    earning_items = [item for item in components if item.component.component_type == 'EARNING']
    deduction_items = [item for item in components if item.component.component_type == 'DEDUCTION']

    for item in earning_items:
        amount = component_amount(item, basic, gross_earnings)
        if amount > 0:
            gross_earnings += amount
            lines.append({
                'component': item.component,
                'name': item.component.name,
                'line_type': 'EARNING',
                'amount': amount,
            })

    overtime_amount = money(0)
    expected_minutes = int(summary['expected_work_days'] or 0) * 8 * 60
    if summary['overtime_minutes'] and expected_minutes:
        overtime_amount = money(gross_earnings * Decimal(summary['overtime_minutes']) / Decimal(expected_minutes))
        if overtime_amount > 0:
            gross_earnings += overtime_amount
            lines.append({
                'name': 'Overtime Pay',
                'line_type': 'EARNING',
                'amount': overtime_amount,
                'notes': f"Auto-calculated from {summary['overtime_minutes']} overtime minutes.",
            })

    deductions = money(0)
    for item in deduction_items:
        amount = component_amount(item, basic, gross_earnings)
        if amount > 0:
            deductions += amount
            lines.append({
                'component': item.component,
                'name': item.component.name,
                'line_type': 'DEDUCTION',
                'amount': amount,
            })

    lop_amount = money(0)
    if summary['loss_of_pay_days'] and summary['expected_work_days']:
        lop_amount = money(gross_earnings * summary['loss_of_pay_days'] / summary['expected_work_days'])
        if lop_amount > 0:
            deductions += lop_amount
            lines.append({
                'name': 'Loss of Pay',
                'line_type': 'DEDUCTION',
                'amount': lop_amount,
                'notes': f"Auto-calculated for {summary['loss_of_pay_days']} LOP days.",
            })

    payslip, _ = Payslip.objects.update_or_create(
        organization=org,
        employee=employee,
        month=payroll_run.month,
        year=payroll_run.year,
        defaults={
            'payroll_run': payroll_run,
            'basic': basic,
            'gross_earnings': money(gross_earnings),
            'total_deductions': money(deductions),
            'expected_work_days': summary['expected_work_days'],
            'present_days': summary['present_days'],
            'paid_leave_days': summary['paid_leave_days'],
            'unpaid_leave_days': summary['unpaid_leave_days'],
            'absent_days': summary['absent_days'],
            'half_days': summary['half_days'],
            'payable_days': summary['payable_days'],
            'loss_of_pay_days': summary['loss_of_pay_days'],
            'worked_minutes': summary['worked_minutes'],
            'overtime_minutes': summary['overtime_minutes'],
            'overtime_amount': overtime_amount,
            'lop_amount': lop_amount,
            'status': 'DRAFT',
        }
    )

    payslip.lines.all().delete()
    for line in lines:
        PayslipLine.objects.create(
            organization=org,
            payslip=payslip,
            component=line.get('component'),
            name=line['name'],
            line_type=line['line_type'],
            amount=money(line['amount']),
            notes=line.get('notes', ''),
        )
    payslip.save()
    return payslip


class PayrollRecordViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollRecordSerializer
    permission_classes = [IsPayroll]

    def get_queryset(self):
        return PayrollRecord.objects.filter(organization=self.request.user.current_organization).select_related('employee__user')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)


class PayrollComponentViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollComponentSerializer
    permission_classes = [IsPayroll]

    def get_queryset(self):
        return PayrollComponent.objects.filter(organization=self.request.user.current_organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)


class EmployeeSalaryComponentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSalaryComponentSerializer
    permission_classes = [IsPayroll]

    def get_queryset(self):
        return EmployeeSalaryComponent.objects.filter(
            organization=self.request.user.current_organization
        ).select_related('employee__user', 'component')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)


class PayrollRunViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollRunSerializer
    permission_classes = [IsPayroll]

    def get_queryset(self):
        org = self.request.user.current_organization
        return PayrollRun.objects.filter(organization=org).annotate(
            payslip_count=Count('payslips'),
            total_gross=Sum('payslips__gross_earnings'),
            total_deductions=Sum('payslips__total_deductions'),
            total_net=Sum('payslips__net_pay'),
        ).select_related('generated_by', 'approved_by')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)

    @action(detail=True, methods=['post'], url_path='generate')
    @transaction.atomic
    def generate(self, request, pk=None):
        payroll_run = self.get_object()
        if payroll_run.status in ['APPROVED', 'PAID']:
            return Response({'detail': 'Approved or paid payroll runs cannot be regenerated.'}, status=400)

        employees = Employee.objects.filter(
            organization=payroll_run.organization,
            status__in=['ACTIVE', 'PROBATION', 'NOTICE'],
        ).select_related('user', 'department')
        employee_id = request.data.get('employee') or request.query_params.get('employee')
        if employee_id:
            employees = employees.filter(id=employee_id)

        generated = []
        for employee in employees.order_by('employee_code'):
            generated.append(generate_payslip_for_employee(payroll_run, employee))

        payroll_run.status = 'GENERATED'
        payroll_run.generated_by = request.user
        payroll_run.generated_at = timezone.now()
        payroll_run.save(update_fields=['status', 'generated_by', 'generated_at', 'updated_at'])

        notify_roles(
            payroll_run.organization,
            ['OWNER', 'ADMIN', 'PAYROLL'],
            title='Payroll generated',
            message=f'Payroll for {payroll_run.month}/{payroll_run.year} has been generated with {len(generated)} payslip(s).',
            notification_type='INFO',
            related_module='payroll',
            related_object_id=payroll_run.pk,
            action_url='/payroll',
            created_by=request.user,
        )
        totals = get_payroll_queryset_totals(Payslip.objects.filter(payroll_run=payroll_run))
        return Response({
            'detail': 'Payslips generated successfully.',
            'generated_count': len(generated),
            'payroll_run': PayrollRunSerializer(payroll_run, context={'request': request}).data,
            'totals': totals,
        })

    @action(detail=True, methods=['post'], url_path='approve')
    @transaction.atomic
    def approve(self, request, pk=None):
        payroll_run = self.get_object()
        if payroll_run.status == 'PAID':
            return Response({'detail': 'Paid payroll runs cannot be changed.'}, status=400)
        payslips = payroll_run.payslips.all()
        if not payslips.exists():
            return Response({'detail': 'Generate payslips before approval.'}, status=400)
        now = timezone.now()
        payslips.update(status='APPROVED', approved_at=now)
        payroll_run.status = 'APPROVED'
        payroll_run.approved_by = request.user
        payroll_run.approved_at = now
        payroll_run.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        for payslip in payslips.select_related('employee__user'):
            notify_employee(
                payslip.employee,
                title='Payslip approved',
                message=f'Your payslip for {payroll_run.month}/{payroll_run.year} has been approved.',
                notification_type='SUCCESS',
                related_module='payroll',
                related_object_id=payslip.pk,
                action_url='/payroll',
                created_by=request.user,
            )
        return Response({'detail': 'Payroll run approved successfully.'})

    @action(detail=True, methods=['post'], url_path='mark-paid')
    @transaction.atomic
    def mark_paid(self, request, pk=None):
        payroll_run = self.get_object()
        if payroll_run.status != 'APPROVED':
            return Response({'detail': 'Only approved payroll runs can be marked as paid.'}, status=400)
        now = timezone.now()
        payroll_run.payslips.all().update(status='PAID', paid_at=now)
        payroll_run.status = 'PAID'
        payroll_run.paid_at = now
        payroll_run.save(update_fields=['status', 'paid_at', 'updated_at'])
        for payslip in payroll_run.payslips.select_related('employee__user'):
            notify_employee(
                payslip.employee,
                title='Salary marked as paid',
                message=f'Your salary for {payroll_run.month}/{payroll_run.year} has been marked as paid.',
                notification_type='SUCCESS',
                related_module='payroll',
                related_object_id=payslip.pk,
                action_url='/payroll',
                created_by=request.user,
            )
        return Response({'detail': 'Payroll run marked as paid.'})

    @action(detail=True, methods=['get'], url_path='payslips')
    def payslips(self, request, pk=None):
        payroll_run = self.get_object()
        payslips = payroll_run.payslips.select_related('employee__user', 'employee__department').prefetch_related('lines')
        return Response(PayslipSerializer(payslips, many=True, context={'request': request}).data)


class PayslipViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = self.request.user.current_organization
        role = get_role(self.request.user)
        qs = Payslip.objects.filter(organization=org).select_related(
            'employee__user', 'employee__department', 'payroll_run'
        ).prefetch_related('lines')

        if role in PAYROLL_ROLES:
            return qs

        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(employee__manager=current_employee) | qs.filter(employee=current_employee)
        return qs.filter(employee__user=self.request.user)
