from rest_framework import viewsets
from apps.accounts.permissions import IsOwnerOrAdmin
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        return AuditLog.objects.filter(organization=self.request.user.current_organization).select_related('actor')
