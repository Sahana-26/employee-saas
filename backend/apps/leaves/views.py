from rest_framework import viewsets
from apps.accounts.permissions import IsOrganizationMember, IsHR, IsManagerLevel
from .models import LeaveType, LeaveBalance, LeaveRequest
from .serializers import LeaveTypeSerializer, LeaveBalanceSerializer, LeaveRequestSerializer


class LeaveTypeViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        return LeaveType.objects.filter(organization=self.request.user.current_organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsHR]

    def get_queryset(self):
        return LeaveBalance.objects.filter(organization=self.request.user.current_organization).select_related('employee__user', 'leave_type')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = LeaveRequest.objects.filter(organization=self.request.user.current_organization).select_related('employee__user', 'leave_type', 'approver__user')
        role = self.request.user.memberships.filter(organization=self.request.user.current_organization, is_active=True).first().role
        if role in ['OWNER', 'ADMIN', 'HR', 'MANAGER']:
            return qs
        return qs.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsManagerLevel()]
        return super().get_permissions()
