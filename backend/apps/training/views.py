from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import get_valid_filename
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from apps.accounts.permissions import HR_ROLES, MANAGER_ROLES, IsHR, IsOrganizationMember, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles
from .models import (
    TrainingAssessment,
    TrainingCertificate,
    TrainingCourse,
    TrainingEnrollment,
    TrainingMaterial,
    TrainingSubmission,
)
from .serializers import (
    TrainingAssessmentSerializer,
    TrainingCertificateSerializer,
    TrainingCourseSerializer,
    TrainingEnrollmentSerializer,
    TrainingMaterialSerializer,
    TrainingSubmissionReviewSerializer,
    TrainingSubmissionSerializer,
)


class TrainingCourseViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingCourseSerializer
    permission_classes = [IsOrganizationMember]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = TrainingCourse.objects.filter(organization=org).select_related('created_by')
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        visible = qs.filter(status=TrainingCourse.STATUS_PUBLISHED)
        if role:
            visible = visible.filter(audience_roles=[] ) | visible.filter(audience_roles__contains=[role])
        return visible.distinct()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'publish', 'archive']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        course = self.get_object()
        course.status = TrainingCourse.STATUS_PUBLISHED
        course.published_at = timezone.now()
        course.archived_at = None
        course.save(update_fields=['status', 'published_at', 'archived_at', 'updated_at'])
        notify_roles(
            course.organization,
            ['OWNER', 'ADMIN', 'HR', 'MANAGER', 'EMPLOYEE'],
            title='New training course published',
            message=f'{course.title} is now available in Training.',
            notification_type='INFO',
            related_module='training',
            related_object_id=course.pk,
            action_url='/training',
            created_by=request.user,
        )
        return Response({'detail': 'Course published.'})

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        course = self.get_object()
        course.status = TrainingCourse.STATUS_ARCHIVED
        course.archived_at = timezone.now()
        course.save(update_fields=['status', 'archived_at', 'updated_at'])
        return Response({'detail': 'Course archived.'})

    @action(detail=True, methods=['post'], url_path='self-enroll')
    def self_enroll(self, request, pk=None):
        course = self.get_object()
        if course.status != TrainingCourse.STATUS_PUBLISHED:
            return Response({'detail': 'Only published courses can be enrolled.'}, status=status.HTTP_400_BAD_REQUEST)
        employee = Employee.objects.filter(organization=course.organization, user=request.user).first()
        if not employee:
            return Response({'detail': 'Employee profile not found.'}, status=status.HTTP_400_BAD_REQUEST)
        enrollment, created = TrainingEnrollment.objects.get_or_create(
            organization=course.organization,
            course=course,
            employee=employee,
            defaults={'assigned_by': request.user},
        )
        if not created:
            return Response({'detail': 'You are already enrolled in this course.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TrainingEnrollmentSerializer(enrollment, context={'request': request}).data, status=status.HTTP_201_CREATED)


class TrainingMaterialViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingMaterialSerializer
    permission_classes = [IsOrganizationMember]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = TrainingMaterial.objects.filter(organization=org).select_related('course', 'uploaded_by').defer('file_data')
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        return qs.filter(course__status=TrainingCourse.STATUS_PUBLISHED)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, uploaded_by=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        material = TrainingMaterial.objects.filter(organization=request.user.current_organization, pk=pk).first()
        if not material or not material.file_data:
            return Response({'detail': 'Training material file not found.'}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(material.file_data, content_type=material.content_type or 'application/octet-stream')
        file_name = get_valid_filename(material.file_name or f'training-material-{material.pk}')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response


class TrainingEnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingEnrollmentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = TrainingEnrollment.objects.filter(organization=org).select_related('course', 'employee__user', 'assigned_by')
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(employee=current_employee) | qs.filter(employee__manager=current_employee)
        if current_employee:
            return qs.filter(employee=current_employee)
        return qs.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'cancel', 'issue_certificate']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        enrollment = serializer.save(organization=self.request.user.current_organization, assigned_by=self.request.user)
        notify_employee(
            enrollment.employee,
            title='Training assigned',
            message=f'You have been assigned to {enrollment.course.title}.',
            notification_type='ACTION',
            related_module='training',
            related_object_id=enrollment.pk,
            action_url='/training',
            created_by=self.request.user,
        )

    def _can_update_own_progress(self, enrollment):
        employee = Employee.objects.filter(organization=enrollment.organization, user=self.request.user).first()
        return bool(employee and employee.pk == enrollment.employee_id)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        enrollment = self.get_object()
        if not self._can_update_own_progress(enrollment) and get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'You can start only your own training.'}, status=status.HTTP_403_FORBIDDEN)
        if enrollment.status not in [TrainingEnrollment.STATUS_ASSIGNED, TrainingEnrollment.STATUS_IN_PROGRESS]:
            return Response({'detail': 'Only assigned training can be started.'}, status=status.HTTP_400_BAD_REQUEST)
        enrollment.status = TrainingEnrollment.STATUS_IN_PROGRESS
        enrollment.started_at = enrollment.started_at or timezone.now()
        if enrollment.progress_percent == 0:
            enrollment.progress_percent = 1
        enrollment.save(update_fields=['status', 'started_at', 'progress_percent', 'updated_at'])
        return Response(TrainingEnrollmentSerializer(enrollment, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='update-progress')
    def update_progress(self, request, pk=None):
        enrollment = self.get_object()
        if not self._can_update_own_progress(enrollment) and get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'You can update only your own training progress.'}, status=status.HTTP_403_FORBIDDEN)
        progress = int(request.data.get('progress_percent', enrollment.progress_percent))
        if progress < 0 or progress > 100:
            return Response({'detail': 'Progress must be between 0 and 100.'}, status=status.HTTP_400_BAD_REQUEST)
        enrollment.progress_percent = progress
        if progress > 0 and not enrollment.started_at:
            enrollment.started_at = timezone.now()
        enrollment.status = TrainingEnrollment.STATUS_COMPLETED if progress == 100 else TrainingEnrollment.STATUS_IN_PROGRESS
        if progress == 100:
            enrollment.completed_at = timezone.now()
        enrollment.save(update_fields=['progress_percent', 'started_at', 'completed_at', 'status', 'updated_at'])
        return Response(TrainingEnrollmentSerializer(enrollment, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        enrollment = self.get_object()
        if not self._can_update_own_progress(enrollment) and get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'You can complete only your own training.'}, status=status.HTTP_403_FORBIDDEN)
        enrollment.status = TrainingEnrollment.STATUS_COMPLETED
        enrollment.progress_percent = 100
        enrollment.started_at = enrollment.started_at or timezone.now()
        enrollment.completed_at = timezone.now()
        enrollment.save(update_fields=['status', 'progress_percent', 'started_at', 'completed_at', 'updated_at'])
        certificate = self._create_certificate(enrollment, request.user)
        data = TrainingEnrollmentSerializer(enrollment, context={'request': request}).data
        data['certificate_number'] = certificate.certificate_number if certificate else None
        return Response(data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.status = TrainingEnrollment.STATUS_CANCELLED
        enrollment.save(update_fields=['status', 'updated_at'])
        return Response({'detail': 'Training enrollment cancelled.'})

    @action(detail=True, methods=['post'], url_path='issue-certificate')
    def issue_certificate(self, request, pk=None):
        enrollment = self.get_object()
        if enrollment.status != TrainingEnrollment.STATUS_COMPLETED:
            return Response({'detail': 'Certificate can be issued only after completion.'}, status=status.HTTP_400_BAD_REQUEST)
        certificate = self._create_certificate(enrollment, request.user)
        return Response(TrainingCertificateSerializer(certificate, context={'request': request}).data)

    def _create_certificate(self, enrollment, issued_by):
        certificate = getattr(enrollment, 'certificate', None)
        if certificate:
            return certificate
        prefix = f'CERT-{enrollment.organization_id}-{enrollment.course_id}-{enrollment.employee_id}'
        number = f'{prefix}-{timezone.now().strftime("%Y%m%d%H%M%S")}'
        certificate = TrainingCertificate.objects.create(
            organization=enrollment.organization,
            certificate_number=number,
            employee=enrollment.employee,
            course=enrollment.course,
            enrollment=enrollment,
            issued_by=issued_by,
        )
        notify_employee(
            enrollment.employee,
            title='Training certificate issued',
            message=f'Certificate issued for {enrollment.course.title}.',
            notification_type='SUCCESS',
            related_module='training',
            related_object_id=certificate.pk,
            action_url='/training',
            created_by=issued_by,
        )
        return certificate


class TrainingAssessmentViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingAssessmentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = TrainingAssessment.objects.filter(organization=org).select_related('course', 'created_by')
        if get_role(self.request.user) in HR_ROLES:
            return qs
        return qs.filter(is_published=True, course__status=TrainingCourse.STATUS_PUBLISHED)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'publish', 'archive']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        assessment = self.get_object()
        assessment.is_published = True
        assessment.save(update_fields=['is_published', 'updated_at'])
        return Response({'detail': 'Assessment published.'})

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        assessment = self.get_object()
        assessment.is_published = False
        assessment.save(update_fields=['is_published', 'updated_at'])
        return Response({'detail': 'Assessment archived.'})


class TrainingSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingSubmissionSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = TrainingSubmission.objects.filter(organization=org).select_related(
            'assessment__course', 'employee__user', 'enrollment', 'reviewed_by'
        )
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(employee=current_employee) | qs.filter(employee__manager=current_employee)
        if current_employee:
            return qs.filter(employee=current_employee)
        return qs.none()

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy', 'review']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        assessment = serializer.validated_data['assessment']
        employee = Employee.objects.filter(organization=self.request.user.current_organization, user=self.request.user).first()
        if not employee:
            raise serializers.ValidationError('Employee profile not found.')
        enrollment = TrainingEnrollment.objects.filter(
            organization=self.request.user.current_organization,
            course=assessment.course,
            employee=employee,
        ).first()
        submission = serializer.save(
            organization=self.request.user.current_organization,
            employee=employee,
            enrollment=enrollment,
            score=0,
            status=TrainingSubmission.STATUS_SUBMITTED,
        )
        notify_roles(
            submission.organization,
            ['OWNER', 'ADMIN', 'HR'],
            title='Training assessment submitted',
            message=f'{employee.user.email} submitted {assessment.title}.',
            notification_type='INFO',
            related_module='training',
            related_object_id=submission.pk,
            action_url='/training',
            created_by=self.request.user,
            exclude_user_ids=[self.request.user.id],
        )

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        submission = self.get_object()
        serializer = TrainingSubmissionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        score = serializer.validated_data['score']
        submission.score = score
        submission.feedback = serializer.validated_data.get('feedback', '')
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.status = TrainingSubmission.STATUS_PASSED if score >= submission.assessment.passing_score else TrainingSubmission.STATUS_FAILED
        submission.save(update_fields=['score', 'feedback', 'reviewed_by', 'reviewed_at', 'status', 'updated_at'])
        if submission.enrollment and submission.status == TrainingSubmission.STATUS_PASSED:
            submission.enrollment.status = TrainingEnrollment.STATUS_COMPLETED
            submission.enrollment.progress_percent = 100
            submission.enrollment.completed_at = timezone.now()
            submission.enrollment.save(update_fields=['status', 'progress_percent', 'completed_at', 'updated_at'])
        notify_employee(
            submission.employee,
            title='Training assessment reviewed',
            message=f'{submission.assessment.title} reviewed. Score: {submission.score}. Status: {submission.status}.',
            notification_type='SUCCESS' if submission.status == TrainingSubmission.STATUS_PASSED else 'WARNING',
            related_module='training',
            related_object_id=submission.pk,
            action_url='/training',
            created_by=request.user,
        )
        return Response(TrainingSubmissionSerializer(submission, context={'request': request}).data)


class TrainingCertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrainingCertificateSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = TrainingCertificate.objects.filter(organization=org).select_related('employee__user', 'course', 'enrollment', 'issued_by')
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(employee=current_employee) | qs.filter(employee__manager=current_employee)
        if current_employee:
            return qs.filter(employee=current_employee)
        return qs.none()

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        certificate = self.get_object()
        body = (
            f'Training Certificate\n\n'
            f'Certificate Number: {certificate.certificate_number}\n'
            f'Employee: {certificate.employee.user.first_name} {certificate.employee.user.last_name} ({certificate.employee.employee_code})\n'
            f'Course: {certificate.course.title}\n'
            f'Issued At: {certificate.issued_at.strftime("%Y-%m-%d %H:%M")}\n'
            f'Organization: {certificate.organization.name}\n'
        )
        response = HttpResponse(body, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{get_valid_filename(certificate.certificate_number)}.txt"'
        return response
