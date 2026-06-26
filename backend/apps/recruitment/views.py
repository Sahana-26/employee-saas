from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import get_valid_filename
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import HR_ROLES, MANAGER_ROLES, IsHR, IsOrganizationMember, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles
from .models import Candidate, InterviewRound, JobOpening, OfferLetter
from .serializers import (
    CandidateSerializer,
    CandidateStatusSerializer,
    ConvertOfferSerializer,
    InterviewCancelSerializer,
    InterviewCompleteSerializer,
    InterviewRoundSerializer,
    JobOpeningSerializer,
    OfferLetterSerializer,
)


class JobOpeningViewSet(viewsets.ModelViewSet):
    serializer_class = JobOpeningSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = (
            JobOpening.objects.filter(organization=org)
            .select_related('department', 'hiring_manager__user', 'created_by')
            .prefetch_related('candidates', 'interviews', 'offers')
        )
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(hiring_manager=current_employee) | qs.filter(status=JobOpening.STATUS_OPEN)
        return qs.filter(status=JobOpening.STATUS_OPEN)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'publish', 'hold', 'close', 'cancel']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        job = self.get_object()
        if job.status not in [JobOpening.STATUS_DRAFT, JobOpening.STATUS_ON_HOLD]:
            return Response({'detail': 'Only draft or on-hold jobs can be published.'}, status=status.HTTP_400_BAD_REQUEST)
        job.status = JobOpening.STATUS_OPEN
        job.published_at = timezone.now()
        job.closed_at = None
        job.save(update_fields=['status', 'published_at', 'closed_at', 'updated_at'])
        notify_roles(
            job.organization,
            ['OWNER', 'ADMIN', 'HR', 'MANAGER'],
            title='Job opening published',
            message=f'{job.title} is now open for recruitment.',
            notification_type='INFO',
            related_module='recruitment',
            related_object_id=job.pk,
            action_url='/recruitment',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )
        return Response({'detail': 'Job opening published.'})

    @action(detail=True, methods=['post'])
    def hold(self, request, pk=None):
        job = self.get_object()
        if job.status not in [JobOpening.STATUS_OPEN, JobOpening.STATUS_DRAFT]:
            return Response({'detail': 'Only open or draft jobs can be put on hold.'}, status=status.HTTP_400_BAD_REQUEST)
        job.status = JobOpening.STATUS_ON_HOLD
        job.save(update_fields=['status', 'updated_at'])
        return Response({'detail': 'Job opening put on hold.'})

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        job = self.get_object()
        if job.status == JobOpening.STATUS_CLOSED:
            return Response({'detail': 'Job opening is already closed.'}, status=status.HTTP_400_BAD_REQUEST)
        job.status = JobOpening.STATUS_CLOSED
        job.closed_at = timezone.now()
        job.save(update_fields=['status', 'closed_at', 'updated_at'])
        return Response({'detail': 'Job opening closed.'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status in [JobOpening.STATUS_CLOSED, JobOpening.STATUS_CANCELLED]:
            return Response({'detail': 'Closed or cancelled jobs cannot be cancelled again.'}, status=status.HTTP_400_BAD_REQUEST)
        job.status = JobOpening.STATUS_CANCELLED
        job.closed_at = timezone.now()
        job.save(update_fields=['status', 'closed_at', 'updated_at'])
        return Response({'detail': 'Job opening cancelled.'})


class CandidateViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = (
            Candidate.objects.filter(organization=org)
            .select_related('job_opening', 'created_by')
            .defer('resume_data')
        )
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(job_opening__hiring_manager=current_employee)
        return qs.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'screen', 'shortlist', 'reject', 'hold']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        candidate = serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)
        notify_roles(
            candidate.organization,
            ['OWNER', 'ADMIN', 'HR'],
            title='New candidate added',
            message=f'{candidate.full_name} was added for {candidate.job_opening.title if candidate.job_opening else "general hiring"}.',
            notification_type='INFO',
            related_module='recruitment',
            related_object_id=candidate.pk,
            action_url='/recruitment',
            created_by=self.request.user,
            exclude_user_ids=[self.request.user.id],
        )
        if candidate.job_opening and candidate.job_opening.hiring_manager:
            notify_employee(
                candidate.job_opening.hiring_manager,
                title='Candidate added to your opening',
                message=f'{candidate.full_name} was added for {candidate.job_opening.title}.',
                notification_type='INFO',
                related_module='recruitment',
                related_object_id=candidate.pk,
                action_url='/recruitment',
                created_by=self.request.user,
            )

    def _set_status(self, candidate, new_status, message):
        serializer = CandidateStatusSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        candidate.status = new_status
        notes = serializer.validated_data.get('notes', '')
        reason = serializer.validated_data.get('reason', '')
        if notes:
            candidate.notes = f'{candidate.notes}\n{timezone.localdate()}: {notes}'.strip()
        if new_status == Candidate.STATUS_REJECTED:
            candidate.rejection_reason = reason
        else:
            candidate.rejection_reason = ''
        candidate.save(update_fields=['status', 'notes', 'rejection_reason', 'updated_at'])
        return Response({'detail': message})

    @action(detail=True, methods=['post'])
    def screen(self, request, pk=None):
        return self._set_status(self.get_object(), Candidate.STATUS_SCREENING, 'Candidate moved to screening.')

    @action(detail=True, methods=['post'])
    def shortlist(self, request, pk=None):
        return self._set_status(self.get_object(), Candidate.STATUS_SHORTLISTED, 'Candidate shortlisted.')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._set_status(self.get_object(), Candidate.STATUS_REJECTED, 'Candidate rejected.')

    @action(detail=True, methods=['post'])
    def hold(self, request, pk=None):
        return self._set_status(self.get_object(), Candidate.STATUS_ON_HOLD, 'Candidate put on hold.')

    @action(detail=True, methods=['get'], url_path='download-resume')
    def download_resume(self, request, pk=None):
        candidate = Candidate.objects.filter(organization=request.user.current_organization, pk=pk).first()
        if not candidate or not candidate.resume_data:
            return Response({'detail': 'Resume not found.'}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(candidate.resume_data, content_type=candidate.resume_content_type or 'application/octet-stream')
        file_name = get_valid_filename(candidate.resume_file_name or f'candidate-{candidate.pk}-resume')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response


class InterviewRoundViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewRoundSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = (
            InterviewRound.objects.filter(organization=org)
            .select_related('candidate', 'job_opening', 'interviewer__user', 'created_by', 'completed_by')
        )
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(interviewer=current_employee) | qs.filter(job_opening__hiring_manager=current_employee)
        return qs.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        interview = serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)
        candidate = interview.candidate
        candidate.status = Candidate.STATUS_INTERVIEW
        candidate.save(update_fields=['status', 'updated_at'])
        if interview.interviewer:
            notify_employee(
                interview.interviewer,
                title='Interview scheduled',
                message=f'{interview.round_type} interview scheduled for {candidate.full_name}.',
                notification_type='ACTION',
                related_module='recruitment',
                related_object_id=interview.pk,
                action_url='/recruitment',
                created_by=self.request.user,
            )

    def _can_complete(self, interview):
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return True
        current_employee = Employee.objects.filter(organization=interview.organization, user=self.request.user).first()
        return bool(current_employee and (interview.interviewer_id == current_employee.pk or interview.job_opening and interview.job_opening.hiring_manager_id == current_employee.pk))

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        interview = self.get_object()
        if not self._can_complete(interview):
            return Response({'detail': 'You do not have permission to complete this interview.'}, status=status.HTTP_403_FORBIDDEN)
        if interview.status != InterviewRound.STATUS_SCHEDULED:
            return Response({'detail': 'Only scheduled interviews can be completed.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = InterviewCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview.status = InterviewRound.STATUS_COMPLETED
        interview.result = serializer.validated_data['result']
        interview.rating = serializer.validated_data.get('rating', interview.rating)
        interview.feedback = serializer.validated_data.get('feedback', '')
        interview.completed_by = request.user
        interview.completed_at = timezone.now()
        interview.save(update_fields=['status', 'result', 'rating', 'feedback', 'completed_by', 'completed_at', 'updated_at'])
        if interview.result == InterviewRound.RESULT_REJECTED:
            interview.candidate.status = Candidate.STATUS_REJECTED
        elif interview.result == InterviewRound.RESULT_SELECTED:
            interview.candidate.status = Candidate.STATUS_SHORTLISTED
        elif interview.result == InterviewRound.RESULT_HOLD:
            interview.candidate.status = Candidate.STATUS_ON_HOLD
        interview.candidate.save(update_fields=['status', 'updated_at'])
        notify_roles(
            interview.organization,
            ['OWNER', 'ADMIN', 'HR'],
            title='Interview completed',
            message=f'{interview.round_type} interview for {interview.candidate.full_name} is completed with result {interview.result}.',
            notification_type='INFO',
            related_module='recruitment',
            related_object_id=interview.pk,
            action_url='/recruitment',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )
        return Response({'detail': 'Interview completed.'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        interview = self.get_object()
        if not self._can_complete(interview):
            return Response({'detail': 'You do not have permission to cancel this interview.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = InterviewCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview.status = InterviewRound.STATUS_NO_SHOW if serializer.validated_data.get('no_show') else InterviewRound.STATUS_CANCELLED
        reason = serializer.validated_data.get('reason', '')
        if reason:
            interview.feedback = reason
        interview.save(update_fields=['status', 'feedback', 'updated_at'])
        return Response({'detail': 'Interview updated.'})


class OfferLetterViewSet(viewsets.ModelViewSet):
    serializer_class = OfferLetterSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = (
            OfferLetter.objects.filter(organization=org)
            .select_related('candidate', 'job_opening', 'department', 'created_by', 'converted_employee')
            .defer('document_data')
        )
        role = get_role(self.request.user)
        if role in HR_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(job_opening__hiring_manager=current_employee)
        return qs.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'send', 'accept', 'reject', 'withdraw', 'convert_to_employee']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        offer = serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)
        offer.candidate.status = Candidate.STATUS_OFFERED
        offer.candidate.save(update_fields=['status', 'updated_at'])

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        offer = self.get_object()
        if offer.status not in [OfferLetter.STATUS_DRAFT, OfferLetter.STATUS_SENT]:
            return Response({'detail': 'Only draft or sent offers can be sent.'}, status=status.HTTP_400_BAD_REQUEST)
        offer.status = OfferLetter.STATUS_SENT
        offer.sent_at = timezone.now()
        offer.save(update_fields=['status', 'sent_at', 'updated_at'])
        return Response({'detail': 'Offer marked as sent.'})

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        offer = self.get_object()
        if offer.status not in [OfferLetter.STATUS_SENT, OfferLetter.STATUS_DRAFT]:
            return Response({'detail': 'Only draft or sent offers can be accepted.'}, status=status.HTTP_400_BAD_REQUEST)
        offer.status = OfferLetter.STATUS_ACCEPTED
        offer.accepted_at = timezone.now()
        offer.save(update_fields=['status', 'accepted_at', 'updated_at'])
        offer.candidate.status = Candidate.STATUS_OFFERED
        offer.candidate.save(update_fields=['status', 'updated_at'])
        notify_roles(
            offer.organization,
            ['OWNER', 'ADMIN', 'HR'],
            title='Offer accepted',
            message=f'{offer.candidate.full_name} accepted offer {offer.offer_number}.',
            notification_type='SUCCESS',
            related_module='recruitment',
            related_object_id=offer.pk,
            action_url='/recruitment',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )
        return Response({'detail': 'Offer accepted.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        offer = self.get_object()
        if offer.status in [OfferLetter.STATUS_CONVERTED, OfferLetter.STATUS_WITHDRAWN]:
            return Response({'detail': 'Converted or withdrawn offers cannot be rejected.'}, status=status.HTTP_400_BAD_REQUEST)
        offer.status = OfferLetter.STATUS_REJECTED
        offer.rejected_at = timezone.now()
        offer.save(update_fields=['status', 'rejected_at', 'updated_at'])
        return Response({'detail': 'Offer rejected.'})

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        offer = self.get_object()
        if offer.status == OfferLetter.STATUS_CONVERTED:
            return Response({'detail': 'Converted offers cannot be withdrawn.'}, status=status.HTTP_400_BAD_REQUEST)
        offer.status = OfferLetter.STATUS_WITHDRAWN
        offer.save(update_fields=['status', 'updated_at'])
        return Response({'detail': 'Offer withdrawn.'})

    @action(detail=True, methods=['post'], url_path='convert-to-employee')
    def convert_to_employee(self, request, pk=None):
        offer = self.get_object()
        serializer = ConvertOfferSerializer(data=request.data, context={'request': request, 'offer': offer})
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        notify_employee(
            employee,
            title='Welcome to the company',
            message='Your employee profile and login account have been created.',
            notification_type='SUCCESS',
            related_module='employees',
            related_object_id=employee.pk,
            action_url='/profile',
            created_by=request.user,
        )
        return Response({'detail': 'Candidate converted to employee.', 'employee_id': employee.pk, 'employee_code': employee.employee_code})

    @action(detail=True, methods=['get'], url_path='download-document')
    def download_document(self, request, pk=None):
        offer = OfferLetter.objects.filter(organization=request.user.current_organization, pk=pk).first()
        if not offer or not offer.document_data:
            return Response({'detail': 'Offer document not found.'}, status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(offer.document_data, content_type=offer.document_content_type or 'application/octet-stream')
        file_name = get_valid_filename(offer.document_file_name or f'offer-{offer.pk}-document')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
