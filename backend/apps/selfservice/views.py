from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.permissions import IsOrganizationMember, IsHR, HR_ROLES, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles
from .models import ProfileChangeRequest
from .serializers import (
    EmployeeSelfProfileSerializer,
    ProfileChangeRequestSerializer,
    ProfileChangeReviewSerializer,
    apply_profile_change,
)


class MyProfileView(APIView):
    permission_classes = [IsOrganizationMember]

    def get_employee(self, request):
        try:
            return Employee.objects.select_related('user', 'department', 'manager', 'manager__user').get(user=request.user, organization=request.user.current_organization)
        except Employee.DoesNotExist:
            return None

    def get(self, request):
        employee = self.get_employee(request)
        if not employee:
            return Response({'detail': 'Employee profile not found for this user.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(EmployeeSelfProfileSerializer(employee).data)

    def patch(self, request):
        employee = self.get_employee(request)
        if not employee:
            return Response({'detail': 'Employee profile not found for this user.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = EmployeeSelfProfileSerializer(employee, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProfileChangeRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileChangeRequestSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = ProfileChangeRequest.objects.filter(
            organization=self.request.user.current_organization
        ).select_related('employee', 'employee__user', 'reviewed_by')
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        employee = Employee.objects.filter(user=self.request.user, organization=self.request.user.current_organization).first()
        if not employee:
            return qs.none()
        return qs.filter(employee=employee)

    def get_permissions(self):
        if self.action in ['approve', 'reject', 'destroy']:
            return [IsHR()]
        return super().get_permissions()


    def perform_create(self, serializer):
        profile_request = serializer.save()
        notify_roles(
            profile_request.organization,
            ['OWNER', 'ADMIN', 'HR'],
            title='Profile change request submitted',
            message=f'{profile_request.employee.user.email} submitted a profile change request.',
            notification_type='ACTION',
            related_module='profile-change-requests',
            related_object_id=profile_request.pk,
            action_url='/profile',
            created_by=self.request.user,
            exclude_user_ids=[self.request.user.id],
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        profile_request = self.get_object()
        if profile_request.status != ProfileChangeRequest.STATUS_PENDING:
            return Response({'detail': 'Only pending requests can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ProfileChangeReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile_request = apply_profile_change(
            profile_request,
            reviewer=request.user,
            review_note=serializer.validated_data.get('review_note', ''),
        )
        notify_employee(
            profile_request.employee,
            title='Profile change approved',
            message='Your profile change request has been approved and applied.',
            notification_type='SUCCESS',
            related_module='profile-change-requests',
            related_object_id=profile_request.pk,
            action_url='/profile',
            created_by=request.user,
        )
        return Response(ProfileChangeRequestSerializer(profile_request).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        profile_request = self.get_object()
        if profile_request.status != ProfileChangeRequest.STATUS_PENDING:
            return Response({'detail': 'Only pending requests can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ProfileChangeReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile_request.status = ProfileChangeRequest.STATUS_REJECTED
        profile_request.reviewed_by = request.user
        profile_request.reviewed_at = timezone.now()
        profile_request.review_note = serializer.validated_data.get('review_note', '')
        profile_request.save()
        notify_employee(
            profile_request.employee,
            title='Profile change rejected',
            message=f'Your profile change request was rejected. {profile_request.review_note}',
            notification_type='WARNING',
            related_module='profile-change-requests',
            related_object_id=profile_request.pk,
            action_url='/profile',
            created_by=request.user,
        )
        return Response(ProfileChangeRequestSerializer(profile_request).data)
