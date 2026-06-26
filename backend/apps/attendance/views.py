from django.utils import timezone
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from apps.accounts.permissions import IsOrganizationMember, IsHR, MANAGER_ROLES, get_role
from apps.hr.models import Employee
from .models import Shift, Holiday, EmployeeShiftAssignment, Attendance
from .serializers import ShiftSerializer, HolidaySerializer, EmployeeShiftAssignmentSerializer, AttendanceSerializer


def get_employee_shift(employee, target_date):
    from django.db.models import Q

    assignment = EmployeeShiftAssignment.objects.filter(
        organization=employee.organization,
        employee=employee,
        is_active=True,
        start_date__lte=target_date,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=target_date)
    ).select_related('shift').order_by('-start_date').first()

    if assignment:
        return assignment.shift

    return Shift.objects.filter(organization=employee.organization, is_default=True, is_active=True).first()


def get_holiday(org, target_date):
    return Holiday.objects.filter(organization=org, date=target_date, is_optional=False).first()


class ShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        return Shift.objects.filter(organization=self.request.user.current_organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()


class HolidayViewSet(viewsets.ModelViewSet):
    serializer_class = HolidaySerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        return Holiday.objects.filter(organization=self.request.user.current_organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()


class EmployeeShiftAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeShiftAssignmentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = EmployeeShiftAssignment.objects.filter(
            organization=self.request.user.current_organization
        ).select_related('employee__user', 'shift')
        role = get_role(self.request.user)
        if role in MANAGER_ROLES:
            return qs
        return qs.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = Attendance.objects.filter(
            organization=self.request.user.current_organization
        ).select_related('employee__user', 'employee__manager', 'employee__manager__user', 'shift', 'holiday')
        role = get_role(self.request.user)
        if role in MANAGER_ROLES:
            return qs
        return qs.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        employee = serializer.validated_data['employee']
        target_date = serializer.validated_data['date']
        shift = serializer.validated_data.get('shift') or get_employee_shift(employee, target_date)
        holiday = serializer.validated_data.get('holiday') or get_holiday(self.request.user.current_organization, target_date)
        serializer.save(organization=self.request.user.current_organization, shift=shift, holiday=holiday)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()


class CheckInView(generics.GenericAPIView):
    permission_classes = [IsOrganizationMember]

    def post(self, request):
        employee = Employee.objects.filter(user=request.user, organization=request.user.current_organization).first()
        if not employee:
            return Response({'detail': 'Employee profile not found'}, status=400)
        now = timezone.now()
        target_date = timezone.localdate(now)
        shift = get_employee_shift(employee, target_date)
        holiday = get_holiday(request.user.current_organization, target_date)
        record, _ = Attendance.objects.get_or_create(
            organization=request.user.current_organization,
            employee=employee,
            date=target_date,
            defaults={'check_in': now, 'shift': shift, 'holiday': holiday, 'status': 'PRESENT'}
        )
        changed = False
        if not record.check_in:
            record.check_in = now
            changed = True
        if not record.shift_id and shift:
            record.shift = shift
            changed = True
        if not record.holiday_id and holiday:
            record.holiday = holiday
            changed = True
        if changed:
            record.save()
        return Response(AttendanceSerializer(record).data, status=status.HTTP_200_OK)


class CheckOutView(generics.GenericAPIView):
    permission_classes = [IsOrganizationMember]

    def post(self, request):
        employee = Employee.objects.filter(user=request.user, organization=request.user.current_organization).first()
        if not employee:
            return Response({'detail': 'Employee profile not found'}, status=400)
        now = timezone.now()
        target_date = timezone.localdate(now)
        record = Attendance.objects.filter(organization=request.user.current_organization, employee=employee, date=target_date).first()
        if not record:
            return Response({'detail': 'Check-in record not found'}, status=400)
        if not record.shift_id:
            record.shift = get_employee_shift(employee, target_date)
        if not record.holiday_id:
            record.holiday = get_holiday(request.user.current_organization, target_date)
        record.check_out = now
        record.save()
        return Response(AttendanceSerializer(record).data, status=status.HTTP_200_OK)


class MyShiftView(generics.GenericAPIView):
    permission_classes = [IsOrganizationMember]

    def get(self, request):
        employee = Employee.objects.filter(user=request.user, organization=request.user.current_organization).first()
        if not employee:
            return Response({'detail': 'Employee profile not found'}, status=400)
        today = timezone.localdate()
        shift = get_employee_shift(employee, today)
        holiday = get_holiday(request.user.current_organization, today)
        data = {
            'date': today,
            'shift': ShiftSerializer(shift).data if shift else None,
            'holiday': HolidaySerializer(holiday).data if holiday else None,
        }
        return Response(data)
