from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import HR_ROLES, IsOrganizationMember, MANAGER_ROLES, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles
from .models import GeneratedLetter, LetterAudit, LetterTemplate
from .rendering import DEFAULT_VARIABLES, render_letter
from .serializers import (
    GeneratedLetterSerializer,
    LetterActionSerializer,
    LetterAuditSerializer,
    LetterRenderPreviewSerializer,
    LetterTemplateSerializer,
)

LETTER_MANAGER_ROLES = HR_ROLES
LETTER_VIEW_ROLES = HR_ROLES | MANAGER_ROLES


def current_employee(user):
    return Employee.objects.filter(organization=user.current_organization, user=user).first()


def managed_employee_ids(user):
    role = get_role(user)
    org = user.current_organization
    if role in HR_ROLES:
        return list(Employee.objects.filter(organization=org).values_list('id', flat=True))
    employee = current_employee(user)
    if not employee:
        return []
    ids = {employee.pk}
    ids.update(Employee.objects.filter(organization=org, manager=employee).values_list('id', flat=True))
    return list(ids)


def log_letter(letter, action, user, note=''):
    return LetterAudit.objects.create(
        organization=letter.organization,
        letter=letter,
        action=action,
        actor=user,
        note=note or '',
    )


class LetterTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = LetterTemplateSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = LetterTemplate.objects.filter(organization=self.request.user.current_organization).select_related('created_by')
        role = get_role(self.request.user)
        if role not in HR_ROLES:
            qs = qs.filter(is_active=True)
        category = self.request.query_params.get('category')
        active = self.request.query_params.get('active')
        search = self.request.query_params.get('search')
        if category:
            qs = qs.filter(category=category)
        if active in ['true', 'false']:
            qs = qs.filter(is_active=(active == 'true'))
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='variables')
    def variables(self, request):
        return Response({'variables': DEFAULT_VARIABLES})

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        template = self.get_object()
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can activate templates.'}, status=status.HTTP_403_FORBIDDEN)
        template.activate()
        return Response(self.get_serializer(template).data)

    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        template = self.get_object()
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can archive templates.'}, status=status.HTTP_403_FORBIDDEN)
        template.archive()
        return Response(self.get_serializer(template).data)

    @action(detail=True, methods=['post'], url_path='render-preview')
    def render_preview(self, request, pk=None):
        template = self.get_object()
        serializer = LetterRenderPreviewSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        content = render_letter(
            template,
            serializer.validated_data['employee'],
            serializer.validated_data.get('custom_variables', {}),
        )
        return Response({'rendered_content': content})


class GeneratedLetterViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratedLetterSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        role = get_role(self.request.user)
        qs = GeneratedLetter.objects.filter(organization=org).select_related(
            'employee', 'employee__user', 'employee__department', 'template',
            'generated_by', 'approved_by', 'signed_by', 'issued_by'
        )
        if role in HR_ROLES:
            pass
        elif role in MANAGER_ROLES:
            qs = qs.filter(employee_id__in=managed_employee_ids(self.request.user))
        else:
            employee = current_employee(self.request.user)
            if not employee:
                return qs.none()
            qs = qs.filter(employee=employee, status__in=[
                GeneratedLetter.STATUS_APPROVED,
                GeneratedLetter.STATUS_SIGNED,
                GeneratedLetter.STATUS_ISSUED,
            ])
        employee_id = self.request.query_params.get('employee')
        category = self.request.query_params.get('category')
        status_value = self.request.query_params.get('status')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if category:
            qs = qs.filter(category=category)
        if status_value:
            qs = qs.filter(status=status_value)
        return qs

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can create letters.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can update letters.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can update letters.'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can delete letters.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='generate')
    def generate(self, request, pk=None):
        letter = self.get_object()
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can generate letters.'}, status=status.HTTP_403_FORBIDDEN)
        if not letter.template:
            return Response({'detail': 'A template is required for generation.'}, status=status.HTTP_400_BAD_REQUEST)
        if letter.status in [GeneratedLetter.STATUS_SIGNED, GeneratedLetter.STATUS_ISSUED, GeneratedLetter.STATUS_CANCELLED]:
            return Response({'detail': 'Signed, issued, or cancelled letters cannot be regenerated.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            content = render_letter(letter.template, letter.employee, letter.custom_variables)
            letter.generated_by = request.user
            letter.set_generated_document(content)
            letter.save()
            log_letter(letter, 'GENERATED', request.user)
        return Response(self.get_serializer(letter).data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        letter = self.get_object()
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can approve letters.'}, status=status.HTTP_403_FORBIDDEN)
        if letter.status not in [GeneratedLetter.STATUS_GENERATED, GeneratedLetter.STATUS_REJECTED, GeneratedLetter.STATUS_DRAFT]:
            return Response({'detail': 'Only draft/generated/rejected letters can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        if not letter.document_data and letter.template:
            content = render_letter(letter.template, letter.employee, letter.custom_variables)
            letter.set_generated_document(content)
        letter.approve(request.user)
        letter.save()
        log_letter(letter, 'APPROVED', request.user)
        notify_employee(
            letter.employee,
            'HR letter approved',
            f'{letter.title} has been approved.',
            notification_type='SUCCESS',
            related_module='hrletters',
            related_object_id=letter.pk,
            action_url='/letters',
            created_by=request.user,
        )
        return Response(self.get_serializer(letter).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        letter = self.get_object()
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can reject letters.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = LetterActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('rejection_reason') or serializer.validated_data.get('note', '')
        letter.reject(request.user, reason)
        letter.save()
        log_letter(letter, 'REJECTED', request.user, reason)
        return Response(self.get_serializer(letter).data)

    @action(detail=True, methods=['post'], url_path='sign')
    def sign(self, request, pk=None):
        letter = self.get_object()
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can sign letters.'}, status=status.HTTP_403_FORBIDDEN)
        if letter.status != GeneratedLetter.STATUS_APPROVED:
            return Response({'detail': 'Only approved letters can be signed.'}, status=status.HTTP_400_BAD_REQUEST)
        letter.sign(request.user)
        letter.save()
        log_letter(letter, 'SIGNED', request.user)
        return Response(self.get_serializer(letter).data)

    @action(detail=True, methods=['post'], url_path='issue')
    def issue(self, request, pk=None):
        letter = self.get_object()
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can issue letters.'}, status=status.HTTP_403_FORBIDDEN)
        if letter.status not in [GeneratedLetter.STATUS_APPROVED, GeneratedLetter.STATUS_SIGNED]:
            return Response({'detail': 'Only approved or signed letters can be issued.'}, status=status.HTTP_400_BAD_REQUEST)
        letter.issue(request.user)
        letter.save()
        log_letter(letter, 'ISSUED', request.user)
        notify_employee(
            letter.employee,
            'HR letter issued',
            f'{letter.title} is now available for download.',
            notification_type='ACTION',
            related_module='hrletters',
            related_object_id=letter.pk,
            action_url='/letters',
            created_by=request.user,
        )
        return Response(self.get_serializer(letter).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        letter = self.get_object()
        if get_role(request.user) not in HR_ROLES:
            return Response({'detail': 'Only HR/Admin/Owner can cancel letters.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = LetterActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = serializer.validated_data.get('note', '')
        letter.cancel()
        letter.save(update_fields=['status', 'updated_at'])
        log_letter(letter, 'CANCELLED', request.user, note)
        return Response(self.get_serializer(letter).data)

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        letter = self.get_object()
        role = get_role(request.user)
        employee = current_employee(request.user)
        is_owner = employee and letter.employee_id == employee.pk
        if role not in HR_ROLES and not is_owner:
            return Response({'detail': 'You do not have access to this letter.'}, status=status.HTTP_403_FORBIDDEN)
        if not letter.document_data:
            return Response({'detail': 'No generated document is available.'}, status=status.HTTP_404_NOT_FOUND)
        if role not in HR_ROLES and letter.status not in [GeneratedLetter.STATUS_APPROVED, GeneratedLetter.STATUS_SIGNED, GeneratedLetter.STATUS_ISSUED]:
            return Response({'detail': 'This letter is not available to employee yet.'}, status=status.HTTP_403_FORBIDDEN)
        response = HttpResponse(bytes(letter.document_data), content_type=letter.document_content_type or 'text/html')
        filename = letter.document_filename or f'{letter.letter_number or letter.pk}.html'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        letter = self.get_object()
        serializer = LetterAuditSerializer(letter.history.select_related('actor'), many=True)
        return Response(serializer.data)
