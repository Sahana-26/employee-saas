import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import MANAGER_ROLES, get_role
from apps.attendance.models import Attendance
from apps.attendance.views import get_employee_shift, get_holiday
from apps.hr.models import Department, Employee
from apps.leaves.models import LeaveBalance, LeaveRequest
from apps.payroll.models import Payslip, PayrollRun


def daterange(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def decimal_to_float(value):
    return float(value or Decimal('0'))



def month_bounds(year, month):
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def get_visible_employees(request):
    org = request.user.current_organization
    role = get_role(request.user)
    employees = Employee.objects.filter(organization=org).select_related('user', 'department', 'manager', 'manager__user')
    current_employee = employees.filter(user=request.user).first()

    if role in MANAGER_ROLES:
        if role == 'MANAGER' and current_employee:
            employees = employees.filter(Q(manager=current_employee) | Q(pk=current_employee.pk))
    else:
        employees = employees.filter(user=request.user)

    return employees.distinct(), current_employee, role


def get_approved_leave_for_date(org, employee, target_date):
    return LeaveRequest.objects.filter(
        organization=org,
        employee=employee,
        status='APPROVED',
        start_date__lte=target_date,
        end_date__gte=target_date,
    ).select_related('leave_type').first()


def summarize_day_for_employees(org, employees, target_date):
    attendance_by_employee = {
        record.employee_id: record
        for record in Attendance.objects.filter(
            organization=org,
            employee__in=employees,
            date=target_date,
        ).select_related('shift', 'holiday', 'employee')
    }

    summary = {
        'date': target_date,
        'employees': employees.count(),
        'present': 0,
        'late': 0,
        'half_day': 0,
        'on_leave': 0,
        'absent': 0,
        'holiday': 0,
        'weekly_off': 0,
        'records': len(attendance_by_employee),
    }

    for employee in employees:
        shift = get_employee_shift(employee, target_date)
        holiday = get_holiday(org, target_date)
        is_weekly_off = bool(shift and shift.is_weekly_off(target_date))
        record = attendance_by_employee.get(employee.id)
        approved_leave = get_approved_leave_for_date(org, employee, target_date)

        if holiday:
            summary['holiday'] += 1
            if not record:
                continue
        if is_weekly_off:
            summary['weekly_off'] += 1
            if not record:
                continue
        if approved_leave:
            summary['on_leave'] += 1
            continue

        if record:
            if record.status == 'LATE':
                summary['late'] += 1
                summary['present'] += 1
            elif record.status == 'HALF_DAY':
                summary['half_day'] += 1
                summary['present'] += 0.5
            elif record.status == 'PRESENT':
                summary['present'] += 1
            elif record.status == 'ON_LEAVE':
                summary['on_leave'] += 1
            elif record.status == 'ABSENT':
                summary['absent'] += 1
        else:
            summary['absent'] += 1

    return summary


def summarize_month_for_employees(org, employees, start_date, end_date):
    totals = {
        'employees': employees.count(),
        'expected_work_days': 0,
        'present_days': Decimal('0'),
        'half_days': 0,
        'leave_days': Decimal('0'),
        'absent_days': Decimal('0'),
        'holiday_days': 0,
        'weekly_off_days': 0,
        'late_count': 0,
        'worked_minutes': 0,
        'late_minutes': 0,
        'overtime_minutes': 0,
    }

    daily = {}
    for item_date in daterange(start_date, end_date):
        daily[item_date] = {
            'date': item_date,
            'present': Decimal('0'),
            'leave': Decimal('0'),
            'absent': Decimal('0'),
            'late': 0,
            'half_day': 0,
            'holiday': 0,
            'weekly_off': 0,
        }

    for employee in employees:
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

        leave_days_by_date = {}
        for leave in approved_leaves:
            overlap_start = max(leave.start_date, start_date)
            overlap_end = min(leave.end_date, end_date)
            for item_date in daterange(overlap_start, overlap_end):
                leave_days_by_date[item_date] = leave

        for item_date in daterange(start_date, end_date):
            shift = get_employee_shift(employee, item_date)
            holiday = get_holiday(org, item_date)
            is_weekly_off = bool(shift and shift.is_weekly_off(item_date))
            record = attendance_by_date.get(item_date)
            approved_leave = leave_days_by_date.get(item_date)
            day = daily[item_date]

            if holiday:
                totals['holiday_days'] += 1
                day['holiday'] += 1
            if is_weekly_off:
                totals['weekly_off_days'] += 1
                day['weekly_off'] += 1

            is_expected_workday = not holiday and not is_weekly_off
            if is_expected_workday:
                totals['expected_work_days'] += 1

            if record:
                totals['worked_minutes'] += record.duration_minutes or 0
                totals['late_minutes'] += record.late_minutes or 0
                totals['overtime_minutes'] += record.overtime_minutes or 0
                if record.late_minutes:
                    totals['late_count'] += 1
                    day['late'] += 1

            if approved_leave and is_expected_workday:
                totals['leave_days'] += Decimal('1')
                day['leave'] += Decimal('1')
                continue

            if record:
                if record.status == 'HALF_DAY':
                    totals['half_days'] += 1
                    totals['present_days'] += Decimal('0.5')
                    day['half_day'] += 1
                    day['present'] += Decimal('0.5')
                elif record.status in ['PRESENT', 'LATE']:
                    totals['present_days'] += Decimal('1')
                    day['present'] += Decimal('1')
                elif record.status == 'ON_LEAVE' and is_expected_workday:
                    totals['leave_days'] += Decimal('1')
                    day['leave'] += Decimal('1')
                elif record.status == 'ABSENT' and is_expected_workday:
                    totals['absent_days'] += Decimal('1')
                    day['absent'] += Decimal('1')
            elif is_expected_workday:
                totals['absent_days'] += Decimal('1')
                day['absent'] += Decimal('1')

    for key in ['present_days', 'leave_days', 'absent_days']:
        totals[key] = decimal_to_float(totals[key])

    daily_rows = []
    for item in daily.values():
        daily_rows.append({
            'date': item['date'],
            'present': decimal_to_float(item['present']),
            'leave': decimal_to_float(item['leave']),
            'absent': decimal_to_float(item['absent']),
            'late': item['late'],
            'half_day': item['half_day'],
            'holiday': item['holiday'],
            'weekly_off': item['weekly_off'],
        })

    return totals, daily_rows


def money_to_float(value):
    return float(value or Decimal('0'))


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = request.user.current_organization
        if not org:
            return Response({'detail': 'Current organization not found.'}, status=400)

        today = timezone.localdate()
        month = int(request.query_params.get('month') or today.month)
        year = int(request.query_params.get('year') or today.year)
        if month < 1 or month > 12:
            return Response({'detail': 'Month must be between 1 and 12.'}, status=400)

        start_date, end_date = month_bounds(year, month)
        employees, current_employee, role = get_visible_employees(request)
        employee_ids = list(employees.values_list('id', flat=True))

        monthly_totals, daily_trend = summarize_month_for_employees(org, employees, start_date, end_date)
        today_summary = summarize_day_for_employees(org, employees, today)

        active_employees = employees.filter(status='ACTIVE').count()
        department_count = Department.objects.filter(organization=org, employees__in=employees).distinct().count()

        leave_status_rows = LeaveRequest.objects.filter(
            organization=org,
            employee_id__in=employee_ids,
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).values('status').annotate(count=Count('id')).order_by('status')
        leave_status_summary = {row['status']: row['count'] for row in leave_status_rows}

        pending_leaves = LeaveRequest.objects.filter(
            organization=org,
            employee_id__in=employee_ids,
            status='PENDING',
        ).count()

        payroll_qs = Payslip.objects.filter(
            organization=org,
            employee_id__in=employee_ids,
            month=month,
            year=year,
        )
        payroll_totals = payroll_qs.aggregate(
            payslip_count=Count('id'),
            gross=Sum('gross_earnings'),
            deductions=Sum('total_deductions'),
            net=Sum('net_pay'),
        )
        payroll_status_rows = payroll_qs.values('status').annotate(count=Count('id'), net=Sum('net_pay')).order_by('status')
        payroll_status_summary = [
            {'status': row['status'], 'count': row['count'], 'net': money_to_float(row['net'])}
            for row in payroll_status_rows
        ]

        payroll_run = PayrollRun.objects.filter(organization=org, month=month, year=year).first()

        department_rows = []
        for department in Department.objects.filter(organization=org, employees__in=employees).distinct().order_by('name'):
            dept_employees = employees.filter(department=department)
            dept_ids = list(dept_employees.values_list('id', flat=True))
            dept_attendance = Attendance.objects.filter(
                organization=org,
                employee_id__in=dept_ids,
                date__gte=start_date,
                date__lte=end_date,
            ).aggregate(
                attendance_records=Count('id'),
                worked_minutes=Sum('duration_minutes'),
                overtime_minutes=Sum('overtime_minutes'),
                late_count=Count('id', filter=Q(late_minutes__gt=0)),
            )
            department_rows.append({
                'department_id': department.id,
                'department': department.name,
                'employees': dept_employees.count(),
                'active_employees': dept_employees.filter(status='ACTIVE').count(),
                'attendance_records': dept_attendance['attendance_records'] or 0,
                'late_count': dept_attendance['late_count'] or 0,
                'worked_minutes': dept_attendance['worked_minutes'] or 0,
                'overtime_minutes': dept_attendance['overtime_minutes'] or 0,
            })

        attendance_mix = [
            {'label': 'Present', 'value': monthly_totals['present_days']},
            {'label': 'Leave', 'value': monthly_totals['leave_days']},
            {'label': 'Absent', 'value': monthly_totals['absent_days']},
            {'label': 'Half Day', 'value': monthly_totals['half_days']},
            {'label': 'Late Count', 'value': monthly_totals['late_count']},
        ]

        return Response({
            'scope': role or 'EMPLOYEE',
            'month': month,
            'year': year,
            'start_date': start_date,
            'end_date': end_date,
            'cards': {
                'total_employees': employees.count(),
                'active_employees': active_employees,
                'departments': department_count,
                'today_present': today_summary['present'],
                'today_late': today_summary['late'],
                'today_absent': today_summary['absent'],
                'pending_leaves': pending_leaves,
                'month_present_days': monthly_totals['present_days'],
                'month_absent_days': monthly_totals['absent_days'],
                'month_leave_days': monthly_totals['leave_days'],
                'month_late_count': monthly_totals['late_count'],
                'worked_minutes': monthly_totals['worked_minutes'],
                'overtime_minutes': monthly_totals['overtime_minutes'],
                'payslip_count': payroll_totals['payslip_count'] or 0,
                'payroll_gross': money_to_float(payroll_totals['gross']),
                'payroll_deductions': money_to_float(payroll_totals['deductions']),
                'payroll_net': money_to_float(payroll_totals['net']),
                'payroll_status': payroll_run.status if payroll_run else 'NOT_GENERATED',
            },
            'today_attendance': today_summary,
            'monthly_attendance': monthly_totals,
            'attendance_mix': attendance_mix,
            'daily_trend': daily_trend,
            'department_summary': department_rows,
            'leave_status_summary': leave_status_summary,
            'payroll_status_summary': payroll_status_summary,
        })


class MonthlyAttendanceReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = request.user.current_organization
        if not org:
            return Response({'detail': 'Current organization not found.'}, status=400)

        today = timezone.localdate()
        month = int(request.query_params.get('month') or today.month)
        year = int(request.query_params.get('year') or today.year)
        employee_id = request.query_params.get('employee')

        if month < 1 or month > 12:
            return Response({'detail': 'Month must be between 1 and 12.'}, status=400)

        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])
        role = get_role(request.user)

        employees = Employee.objects.filter(organization=org).select_related('user', 'department', 'manager', 'manager__user')
        current_employee = employees.filter(user=request.user).first()

        if employee_id:
            employees = employees.filter(id=employee_id)
        elif role in MANAGER_ROLES:
            if role == 'MANAGER' and current_employee:
                employees = employees.filter(manager=current_employee) | employees.filter(pk=current_employee.pk)
        else:
            employees = employees.filter(user=request.user)

        records = []
        totals = {
            'employees': 0,
            'expected_work_days': 0,
            'present_days': 0,
            'leave_days': 0,
            'absent_days': 0,
            'late_count': 0,
            'worked_minutes': 0,
            'overtime_minutes': 0,
        }

        for employee in employees.order_by('employee_code'):
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

            leave_days_by_date = {}
            for leave in approved_leaves:
                overlap_start = max(leave.start_date, start_date)
                overlap_end = min(leave.end_date, end_date)
                for item_date in daterange(overlap_start, overlap_end):
                    leave_days_by_date[item_date] = leave

            summary = {
                'employee_id': employee.id,
                'employee_code': employee.employee_code,
                'employee_name': f'{employee.user.first_name} {employee.user.last_name}'.strip() or employee.user.email,
                'department': employee.department.name if employee.department else None,
                'designation': employee.designation,
                'month': month,
                'year': year,
                'calendar_days': (end_date - start_date).days + 1,
                'expected_work_days': 0,
                'present_days': 0,
                'half_days': 0,
                'leave_days': 0,
                'absent_days': 0,
                'holiday_days': 0,
                'weekly_off_days': 0,
                'late_count': 0,
                'worked_minutes': 0,
                'late_minutes': 0,
                'overtime_minutes': 0,
                'attendance_records': len(attendance_by_date),
            }

            for item_date in daterange(start_date, end_date):
                shift = get_employee_shift(employee, item_date)
                holiday = get_holiday(org, item_date)
                is_weekly_off = bool(shift and shift.is_weekly_off(item_date))
                record = attendance_by_date.get(item_date)
                approved_leave = leave_days_by_date.get(item_date)

                if holiday:
                    summary['holiday_days'] += 1
                if is_weekly_off:
                    summary['weekly_off_days'] += 1

                is_expected_workday = not holiday and not is_weekly_off
                if is_expected_workday:
                    summary['expected_work_days'] += 1

                if record:
                    summary['worked_minutes'] += record.duration_minutes or 0
                    summary['late_minutes'] += record.late_minutes or 0
                    summary['overtime_minutes'] += record.overtime_minutes or 0
                    if record.late_minutes:
                        summary['late_count'] += 1

                if approved_leave and is_expected_workday:
                    summary['leave_days'] += Decimal('1')
                    continue

                if record:
                    if record.status == 'HALF_DAY':
                        summary['half_days'] += 1
                        summary['present_days'] += Decimal('0.5')
                    elif record.status in ['PRESENT', 'LATE']:
                        summary['present_days'] += Decimal('1')
                    elif record.status == 'ON_LEAVE' and is_expected_workday:
                        summary['leave_days'] += Decimal('1')
                    elif record.status == 'ABSENT' and is_expected_workday:
                        summary['absent_days'] += Decimal('1')
                elif is_expected_workday:
                    summary['absent_days'] += Decimal('1')

            summary['present_days'] = decimal_to_float(summary['present_days'])
            summary['leave_days'] = decimal_to_float(summary['leave_days'])
            summary['absent_days'] = decimal_to_float(summary['absent_days'])

            records.append(summary)
            totals['employees'] += 1
            totals['expected_work_days'] += summary['expected_work_days']
            totals['present_days'] += summary['present_days']
            totals['leave_days'] += summary['leave_days']
            totals['absent_days'] += summary['absent_days']
            totals['late_count'] += summary['late_count']
            totals['worked_minutes'] += summary['worked_minutes']
            totals['overtime_minutes'] += summary['overtime_minutes']

        return Response({
            'month': month,
            'year': year,
            'start_date': start_date,
            'end_date': end_date,
            'totals': totals,
            'results': records,
        })


class LeaveBalanceReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = request.user.current_organization
        if not org:
            return Response({'detail': 'Current organization not found.'}, status=400)

        today = timezone.localdate()
        year = int(request.query_params.get('year') or today.year)
        role = get_role(request.user)

        balances = LeaveBalance.objects.filter(
            organization=org,
            year=year,
        ).select_related('employee__user', 'employee__department', 'leave_type')

        current_employee = Employee.objects.filter(user=request.user, organization=org).first()
        if role not in MANAGER_ROLES:
            balances = balances.filter(employee__user=request.user)
        elif role == 'MANAGER' and current_employee:
            balances = balances.filter(employee__manager=current_employee) | balances.filter(employee=current_employee)

        rows = []
        for balance in balances.order_by('employee__employee_code', 'leave_type__name'):
            rows.append({
                'employee_id': balance.employee_id,
                'employee_code': balance.employee.employee_code,
                'employee_name': f'{balance.employee.user.first_name} {balance.employee.user.last_name}'.strip() or balance.employee.user.email,
                'department': balance.employee.department.name if balance.employee.department else None,
                'leave_type': balance.leave_type.name,
                'year': balance.year,
                'allocated': decimal_to_float(balance.allocated),
                'used': decimal_to_float(balance.used),
                'remaining': decimal_to_float(balance.remaining),
            })

        return Response({'year': year, 'results': rows})
