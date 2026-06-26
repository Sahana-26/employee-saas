from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import get_valid_filename
from rest_framework import viewsets
from rest_framework.decorators import action
from apps.accounts.permissions import IsOrganizationMember, IsHR, HR_ROLES, get_role
from .models import EmployeeDocument
from .serializers import EmployeeDocumentSerializer


class EmployeeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = (
            EmployeeDocument.objects
            .filter(organization=self.request.user.current_organization)
            .select_related('employee__user', 'uploaded_by')
            .defer('data')
        )
        if get_role(self.request.user) in HR_ROLES:
            return qs
        return qs.filter(employee__user=self.request.user)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsHR()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, uploaded_by=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        document = get_object_or_404(EmployeeDocument, pk=pk, organization=request.user.current_organization)
        response = HttpResponse(bytes(document.data), content_type=document.content_type)
        file_name = get_valid_filename(document.file_name)
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
