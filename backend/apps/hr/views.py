from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import IsOrganizationMember, IsHR, HR_ROLES, ASSET_ROLES, MANAGER_ROLES, get_role
from .models import Department, Employee
from .serializers import DepartmentSerializer, EmployeeSerializer, EmployeePasswordSerializer


class TenantQuerysetMixin:
    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)


class DepartmentViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        return Department.objects.filter(organization=self.request.user.current_organization)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = Employee.objects.filter(
            organization=self.request.user.current_organization
        ).select_related('user', 'department', 'manager', 'manager__user')
        role = get_role(self.request.user)
        if role in HR_ROLES or role in ASSET_ROLES:
            return qs
        current_employee = qs.filter(user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(manager=current_employee) | qs.filter(pk=current_employee.pk)
        return qs.filter(user=self.request.user)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'set_password', 'disable_login', 'enable_login']:
            return [IsHR()]
        return super().get_permissions()

    @action(detail=True, methods=['post'], url_path='set-password')
    def set_password(self, request, pk=None):
        employee = self.get_object()
        serializer = EmployeePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee.user.set_password(serializer.validated_data['password'])
        employee.user.is_active = True
        employee.user.save()
        return Response({'detail': 'Employee password updated and login enabled.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='disable-login')
    def disable_login(self, request, pk=None):
        employee = self.get_object()
        employee.user.is_active = False
        employee.user.save()
        return Response({'detail': 'Employee login disabled.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='enable-login')
    def enable_login(self, request, pk=None):
        employee = self.get_object()
        employee.user.is_active = True
        employee.user.save()
        return Response({'detail': 'Employee login enabled.'}, status=status.HTTP_200_OK)
