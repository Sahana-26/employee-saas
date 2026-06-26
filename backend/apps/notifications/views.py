from django.db.models import Count, Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import HR_ROLES, IsHR, IsOrganizationMember, get_role
from .models import Announcement, AnnouncementRead, Notification
from .serializers import AnnouncementSerializer, NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = Notification.objects.filter(
            organization=self.request.user.current_organization,
            recipient=self.request.user,
        ).select_related('recipient', 'created_by')
        is_read = self.request.query_params.get('is_read')
        if is_read in ['true', 'True', '1']:
            qs = qs.filter(is_read=True)
        if is_read in ['false', 'False', '0']:
            qs = qs.filter(is_read=False)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response(NotificationSerializer(notification, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='mark-unread')
    def mark_unread(self, request, pk=None):
        notification = self.get_object()
        notification.mark_unread()
        return Response(NotificationSerializer(notification, context={'request': request}).data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        qs = self.get_queryset().filter(is_read=False)
        count = qs.count()
        for notification in qs:
            notification.mark_read()
        return Response({'detail': 'All notifications marked as read.', 'updated_count': count})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        org = self.request.user.current_organization
        role = get_role(self.request.user)
        qs = Announcement.objects.filter(organization=org).annotate(read_count=Count('reads')).select_related('created_by').prefetch_related(
            Prefetch('reads', queryset=AnnouncementRead.objects.filter(user=self.request.user), to_attr='my_reads')
        )
        if role in HR_ROLES:
            return qs
        ids = [item.id for item in qs if item.is_active_now() and item.applies_to_role(role)]
        return qs.filter(id__in=ids)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'publish', 'archive']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        announcement = self.get_object()
        AnnouncementRead.objects.get_or_create(
            organization=request.user.current_organization,
            announcement=announcement,
            user=request.user,
        )
        return Response({'detail': 'Announcement marked as read.'})

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        announcement = self.get_object()
        announcement.is_published = True
        announcement.save(update_fields=['is_published', 'updated_at'])
        return Response(AnnouncementSerializer(announcement, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        announcement = self.get_object()
        announcement.is_published = False
        announcement.save(update_fields=['is_published', 'updated_at'])
        return Response(AnnouncementSerializer(announcement, context={'request': request}).data)
