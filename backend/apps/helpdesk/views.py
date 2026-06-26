from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import get_valid_filename
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import HR_ROLES, IT_ROLES, MANAGER_ROLES, IsOrganizationMember, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles, notify_user
from .models import SupportTicket, TicketAttachment, TicketCategory, TicketComment
from .serializers import (
    SUPPORT_ROLES,
    SupportTicketSerializer,
    TicketAssignSerializer,
    TicketAttachmentSerializer,
    TicketCategorySerializer,
    TicketCommentSerializer,
    TicketRejectLikeSerializer,
    TicketResolutionSerializer,
)


class IsSupportUser(IsOrganizationMember):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and get_role(request.user) in SUPPORT_ROLES


class TicketCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = TicketCategorySerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        return TicketCategory.objects.filter(organization=self.request.user.current_organization).select_related('default_assignee')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSupportUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)


class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = (
            SupportTicket.objects
            .filter(organization=org)
            .select_related('requested_by__user', 'requested_by__manager', 'requested_by__manager__user', 'category', 'assigned_to')
            .annotate(comment_count=Count('comments', distinct=True), attachment_count=Count('attachments', distinct=True))
        )
        role = get_role(self.request.user)
        if role in SUPPORT_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(requested_by=current_employee) | qs.filter(requested_by__manager=current_employee)
        if current_employee:
            return qs.filter(requested_by=current_employee)
        return qs.none()

    def _current_employee(self):
        return Employee.objects.filter(organization=self.request.user.current_organization, user=self.request.user).first()

    def _can_manage_ticket(self, ticket):
        role = get_role(self.request.user)
        if role in SUPPORT_ROLES:
            return True
        return bool(ticket.assigned_to_id == self.request.user.id)

    def _can_comment_ticket(self, ticket):
        if self._can_manage_ticket(ticket):
            return True
        employee = self._current_employee()
        if not employee:
            return False
        if ticket.requested_by_id == employee.pk:
            return True
        return get_role(self.request.user) in MANAGER_ROLES and ticket.requested_by.manager_id == employee.pk

    def perform_create(self, serializer):
        ticket = serializer.save(organization=self.request.user.current_organization)
        notify_roles(
            ticket.organization,
            ['OWNER', 'ADMIN', 'HR', 'IT'],
            title='New support ticket',
            message=f'{ticket.requested_by.user.email} created ticket {ticket.ticket_number or ticket.pk}: {ticket.subject}.',
            notification_type='ACTION',
            related_module='helpdesk',
            related_object_id=ticket.pk,
            action_url='/helpdesk',
            created_by=self.request.user,
            exclude_user_ids=[self.request.user.id],
        )
        if ticket.assigned_to:
            notify_user(
                ticket.assigned_to,
                ticket.organization,
                title='Support ticket assigned',
                message=f'Ticket {ticket.ticket_number or ticket.pk} has been assigned to you.',
                notification_type='ACTION',
                related_module='helpdesk',
                related_object_id=ticket.pk,
                action_url='/helpdesk',
                created_by=self.request.user,
            )

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        if not self._can_manage_ticket(ticket):
            return Response({'detail': 'You do not have permission to assign this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TicketAssignSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        ticket.assigned_to = serializer.validated_data.get('assigned_to', ticket.assigned_to)
        if 'due_at' in serializer.validated_data:
            ticket.due_at = serializer.validated_data.get('due_at')
        if ticket.status == SupportTicket.STATUS_OPEN:
            ticket.status = SupportTicket.STATUS_IN_PROGRESS
        ticket.save(update_fields=['assigned_to', 'due_at', 'status', 'updated_at'])
        if ticket.assigned_to:
            notify_user(
                ticket.assigned_to,
                ticket.organization,
                title='Support ticket assigned',
                message=f'Ticket {ticket.ticket_number or ticket.pk} has been assigned to you.',
                notification_type='ACTION',
                related_module='helpdesk',
                related_object_id=ticket.pk,
                action_url='/helpdesk',
                created_by=request.user,
            )
        return Response(SupportTicketSerializer(ticket, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        ticket = self.get_object()
        if not self._can_manage_ticket(ticket):
            return Response({'detail': 'You do not have permission to start this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        ticket.status = SupportTicket.STATUS_IN_PROGRESS
        ticket.save(update_fields=['status', 'updated_at'])
        notify_employee(
            ticket.requested_by,
            title='Support ticket in progress',
            message=f'Your ticket {ticket.ticket_number or ticket.pk} is now in progress.',
            notification_type='INFO',
            related_module='helpdesk',
            related_object_id=ticket.pk,
            action_url='/helpdesk',
            created_by=request.user,
        )
        return Response({'detail': 'Ticket moved to in progress.'})

    @action(detail=True, methods=['post'], url_path='pending-user')
    def pending_user(self, request, pk=None):
        ticket = self.get_object()
        if not self._can_manage_ticket(ticket):
            return Response({'detail': 'You do not have permission to update this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TicketRejectLikeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket.status = SupportTicket.STATUS_PENDING_USER
        ticket.last_response_at = timezone.now()
        ticket.save(update_fields=['status', 'last_response_at', 'updated_at'])
        message = serializer.validated_data.get('message') or 'Support team is waiting for your response.'
        TicketComment.objects.create(organization=ticket.organization, ticket=ticket, author=request.user, message=message, is_internal=False)
        notify_employee(
            ticket.requested_by,
            title='Support ticket needs your response',
            message=f'Ticket {ticket.ticket_number or ticket.pk}: {message}',
            notification_type='ACTION',
            related_module='helpdesk',
            related_object_id=ticket.pk,
            action_url='/helpdesk',
            created_by=request.user,
        )
        return Response({'detail': 'Ticket marked as pending user response.'})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        ticket = self.get_object()
        if not self._can_manage_ticket(ticket):
            return Response({'detail': 'You do not have permission to resolve this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TicketResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket.status = SupportTicket.STATUS_RESOLVED
        ticket.resolution_notes = serializer.validated_data.get('resolution_notes', ticket.resolution_notes)
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=['status', 'resolution_notes', 'resolved_at', 'updated_at'])
        notify_employee(
            ticket.requested_by,
            title='Support ticket resolved',
            message=f'Your ticket {ticket.ticket_number or ticket.pk} has been resolved.',
            notification_type='SUCCESS',
            related_module='helpdesk',
            related_object_id=ticket.pk,
            action_url='/helpdesk',
            created_by=request.user,
        )
        return Response({'detail': 'Ticket resolved.'})

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        ticket = self.get_object()
        employee = self._current_employee()
        can_close = self._can_manage_ticket(ticket) or (employee and ticket.requested_by_id == employee.pk)
        if not can_close:
            return Response({'detail': 'You do not have permission to close this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        if ticket.status not in [SupportTicket.STATUS_RESOLVED, SupportTicket.STATUS_PENDING_USER, SupportTicket.STATUS_IN_PROGRESS]:
            return Response({'detail': 'Only active or resolved tickets can be closed.'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.status = SupportTicket.STATUS_CLOSED
        ticket.closed_at = timezone.now()
        ticket.save(update_fields=['status', 'closed_at', 'updated_at'])
        return Response({'detail': 'Ticket closed.'})

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        ticket = self.get_object()
        employee = self._current_employee()
        can_reopen = self._can_manage_ticket(ticket) or (employee and ticket.requested_by_id == employee.pk)
        if not can_reopen:
            return Response({'detail': 'You do not have permission to reopen this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        if ticket.status not in [SupportTicket.STATUS_RESOLVED, SupportTicket.STATUS_CLOSED, SupportTicket.STATUS_CANCELLED]:
            return Response({'detail': 'Only resolved, closed, or cancelled tickets can be reopened.'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.status = SupportTicket.STATUS_OPEN
        ticket.resolved_at = None
        ticket.closed_at = None
        ticket.cancelled_at = None
        ticket.save(update_fields=['status', 'resolved_at', 'closed_at', 'cancelled_at', 'updated_at'])
        notify_roles(
            ticket.organization,
            ['OWNER', 'ADMIN', 'HR', 'IT'],
            title='Support ticket reopened',
            message=f'Ticket {ticket.ticket_number or ticket.pk} has been reopened.',
            notification_type='ACTION',
            related_module='helpdesk',
            related_object_id=ticket.pk,
            action_url='/helpdesk',
            created_by=request.user,
            exclude_user_ids=[request.user.id],
        )
        return Response({'detail': 'Ticket reopened.'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        ticket = self.get_object()
        employee = self._current_employee()
        can_cancel = self._can_manage_ticket(ticket) or (employee and ticket.requested_by_id == employee.pk)
        if not can_cancel:
            return Response({'detail': 'You do not have permission to cancel this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        if ticket.status in [SupportTicket.STATUS_CLOSED, SupportTicket.STATUS_RESOLVED]:
            return Response({'detail': 'Closed or resolved tickets cannot be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.status = SupportTicket.STATUS_CANCELLED
        ticket.cancelled_at = timezone.now()
        ticket.save(update_fields=['status', 'cancelled_at', 'updated_at'])
        return Response({'detail': 'Ticket cancelled.'})

    @action(detail=True, methods=['post'], url_path='add-comment')
    def add_comment(self, request, pk=None):
        ticket = self.get_object()
        if not self._can_comment_ticket(ticket):
            return Response({'detail': 'You do not have permission to comment on this ticket.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TicketCommentSerializer(data={**request.data, 'ticket': ticket.pk}, context={'request': request})
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(organization=ticket.organization, ticket=ticket, author=request.user)
        ticket.last_response_at = timezone.now()
        if ticket.status == SupportTicket.STATUS_PENDING_USER and ticket.requested_by.user_id == request.user.id:
            ticket.status = SupportTicket.STATUS_IN_PROGRESS
        ticket.save(update_fields=['last_response_at', 'status', 'updated_at'])
        if comment.is_internal:
            notify_roles(
                ticket.organization,
                ['OWNER', 'ADMIN', 'HR', 'IT'],
                title='Internal helpdesk comment added',
                message=f'Internal comment added on {ticket.ticket_number or ticket.pk}.',
                notification_type='INFO',
                related_module='helpdesk',
                related_object_id=ticket.pk,
                action_url='/helpdesk',
                created_by=request.user,
                exclude_user_ids=[request.user.id],
            )
        elif request.user.id != ticket.requested_by.user_id:
            notify_employee(
                ticket.requested_by,
                title='New response on support ticket',
                message=f'New response on {ticket.ticket_number or ticket.pk}.',
                notification_type='INFO',
                related_module='helpdesk',
                related_object_id=ticket.pk,
                action_url='/helpdesk',
                created_by=request.user,
            )
        elif ticket.assigned_to:
            notify_user(
                ticket.assigned_to,
                ticket.organization,
                title='Employee replied to support ticket',
                message=f'Employee replied to {ticket.ticket_number or ticket.pk}.',
                notification_type='ACTION',
                related_module='helpdesk',
                related_object_id=ticket.pk,
                action_url='/helpdesk',
                created_by=request.user,
            )
        return Response(TicketCommentSerializer(comment, context={'request': request}).data, status=status.HTTP_201_CREATED)


class TicketCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TicketCommentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = TicketComment.objects.filter(organization=org).select_related('ticket__requested_by__user', 'ticket__requested_by__manager', 'author')
        role = get_role(self.request.user)
        if role in SUPPORT_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if not current_employee:
            return qs.none()
        base = qs.filter(is_internal=False)
        if role in MANAGER_ROLES:
            return base.filter(ticket__requested_by=current_employee) | base.filter(ticket__requested_by__manager=current_employee)
        return base.filter(ticket__requested_by=current_employee)

    def perform_create(self, serializer):
        ticket = serializer.validated_data['ticket']
        temp_view = SupportTicketViewSet()
        temp_view.request = self.request
        if not temp_view._can_comment_ticket(ticket):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have permission to comment on this ticket.')
        serializer.save(organization=self.request.user.current_organization, author=self.request.user)


class TicketAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = TicketAttachmentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        qs = TicketAttachment.objects.filter(organization=org).select_related('ticket__requested_by__user', 'ticket__requested_by__manager', 'uploaded_by').defer('file_data')
        role = get_role(self.request.user)
        if role in SUPPORT_ROLES:
            return qs
        current_employee = Employee.objects.filter(organization=org, user=self.request.user).first()
        if not current_employee:
            return qs.none()
        if role in MANAGER_ROLES:
            return qs.filter(ticket__requested_by=current_employee) | qs.filter(ticket__requested_by__manager=current_employee)
        return qs.filter(ticket__requested_by=current_employee)

    def perform_create(self, serializer):
        ticket = serializer.validated_data['ticket']
        temp_view = SupportTicketViewSet()
        temp_view.request = self.request
        if not temp_view._can_comment_ticket(ticket):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have permission to upload attachments on this ticket.')
        serializer.save(organization=self.request.user.current_organization, uploaded_by=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        attachment = get_object_or_404(TicketAttachment, pk=pk, organization=request.user.current_organization)
        role = get_role(request.user)
        current_employee = Employee.objects.filter(organization=attachment.organization, user=request.user).first()
        can_access = role in SUPPORT_ROLES or (current_employee and attachment.ticket.requested_by_id == current_employee.pk) or (current_employee and attachment.ticket.requested_by.manager_id == current_employee.pk)
        if not can_access:
            return Response({'detail': 'You do not have permission to download this attachment.'}, status=status.HTTP_403_FORBIDDEN)
        response = HttpResponse(bytes(attachment.file_data), content_type=attachment.content_type or 'application/octet-stream')
        file_name = get_valid_filename(attachment.file_name or f'ticket-attachment-{attachment.pk}')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
