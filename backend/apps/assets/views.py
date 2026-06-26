from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import get_valid_filename
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import ASSET_ROLES, MANAGER_ROLES, IsITOrAssetAdmin, IsOrganizationMember, get_role
from apps.hr.models import Employee
from apps.notifications.services import notify_employee, notify_roles
from .models import Asset, AssetAssignment, AssetCategory, AssetDocument, AssetMaintenance
from .serializers import (
    AssetAssignSerializer,
    AssetAssignmentSerializer,
    AssetCategorySerializer,
    AssetDocumentSerializer,
    AssetMaintenanceSerializer,
    AssetReturnSerializer,
    AssetSerializer,
    AssetStatusSerializer,
)


class AssetAccessMixin:
    def _current_employee(self):
        return Employee.objects.filter(organization=self.request.user.current_organization, user=self.request.user).first()

    def _can_admin_assets(self):
        return get_role(self.request.user) in ASSET_ROLES

    def _visible_asset_queryset(self, qs):
        role = get_role(self.request.user)
        if role in ASSET_ROLES:
            return qs
        current_employee = self._current_employee()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(assigned_to=current_employee) | qs.filter(assigned_to__manager=current_employee)
        if current_employee:
            return qs.filter(assigned_to=current_employee)
        return qs.none()


class AssetCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = AssetCategorySerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        return AssetCategory.objects.filter(organization=self.request.user.current_organization).prefetch_related('assets')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsITOrAssetAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)


class AssetViewSet(AssetAccessMixin, viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = (
            Asset.objects
            .filter(organization=self.request.user.current_organization)
            .select_related('category', 'assigned_to__user', 'assigned_to__manager', 'created_by')
            .prefetch_related('assignments', 'documents', 'maintenance_records')
        )
        return self._visible_asset_queryset(qs).distinct()

    def get_permissions(self):
        if self.action in [
            'create', 'update', 'partial_update', 'destroy', 'assign', 'return_asset',
            'mark_available', 'mark_maintenance', 'mark_damaged', 'mark_lost', 'mark_retired'
        ]:
            return [IsITOrAssetAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        asset = self.get_object()
        if asset.status == Asset.STATUS_ASSIGNED or asset.assigned_to_id:
            return Response({'detail': 'This asset is already assigned.'}, status=status.HTTP_400_BAD_REQUEST)
        if asset.status in [Asset.STATUS_LOST, Asset.STATUS_RETIRED]:
            return Response({'detail': 'Lost or retired assets cannot be assigned.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AssetAssignSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        employee = serializer.validated_data['employee']
        assignment = AssetAssignment.objects.create(
            organization=asset.organization,
            asset=asset,
            employee=employee,
            assigned_by=request.user,
            expected_return_date=serializer.validated_data.get('expected_return_date'),
            condition_at_issue=serializer.validated_data.get('condition_at_issue', ''),
            issue_notes=serializer.validated_data.get('issue_notes', ''),
        )
        asset.assigned_to = employee
        asset.assigned_at = assignment.assigned_at
        asset.status = Asset.STATUS_ASSIGNED
        asset.save(update_fields=['assigned_to', 'assigned_at', 'status', 'updated_at'])
        notify_employee(
            employee,
            title='Asset assigned',
            message=f'{asset.asset_code} - {asset.name} has been assigned to you.',
            notification_type='INFO',
            related_module='assets',
            related_object_id=asset.pk,
            action_url='/assets',
            created_by=request.user,
        )
        return Response(AssetAssignmentSerializer(assignment, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='return')
    def return_asset(self, request, pk=None):
        asset = self.get_object()
        if not asset.assigned_to_id:
            return Response({'detail': 'Only currently assigned assets can be returned.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AssetReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = AssetAssignment.objects.filter(asset=asset, status=AssetAssignment.STATUS_ASSIGNED).order_by('-assigned_at').first()
        if assignment:
            assignment.status = AssetAssignment.STATUS_RETURNED
            assignment.returned_by = request.user
            assignment.returned_at = timezone.now()
            assignment.condition_at_return = serializer.validated_data.get('condition_at_return', '')
            assignment.return_notes = serializer.validated_data.get('return_notes', '')
            assignment.save(update_fields=['status', 'returned_by', 'returned_at', 'condition_at_return', 'return_notes', 'updated_at'])
        previous_employee = asset.assigned_to
        asset.assigned_to = None
        asset.assigned_at = None
        asset.status = serializer.validated_data.get('next_status', Asset.STATUS_AVAILABLE)
        asset.save(update_fields=['assigned_to', 'assigned_at', 'status', 'updated_at'])
        notify_employee(
            previous_employee,
            title='Asset returned',
            message=f'{asset.asset_code} - {asset.name} has been marked as returned.',
            notification_type='SUCCESS',
            related_module='assets',
            related_object_id=asset.pk,
            action_url='/assets',
            created_by=request.user,
        )
        return Response({'detail': 'Asset returned successfully.'})

    def _mark_status(self, request, asset, next_status, message):
        serializer = AssetStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if next_status in [Asset.STATUS_LOST, Asset.STATUS_RETIRED] and asset.assigned_to_id:
            open_assignment = AssetAssignment.objects.filter(asset=asset, status=AssetAssignment.STATUS_ASSIGNED).order_by('-assigned_at').first()
            if open_assignment:
                open_assignment.status = AssetAssignment.STATUS_RETURNED
                open_assignment.returned_by = request.user
                open_assignment.returned_at = timezone.now()
                open_assignment.return_notes = serializer.validated_data.get('notes', message)
                open_assignment.save(update_fields=['status', 'returned_by', 'returned_at', 'return_notes', 'updated_at'])
            asset.assigned_to = None
            asset.assigned_at = None
        if serializer.validated_data.get('notes'):
            asset.notes = (asset.notes + '\n' if asset.notes else '') + serializer.validated_data['notes']
        asset.status = next_status
        asset.save(update_fields=['status', 'assigned_to', 'assigned_at', 'notes', 'updated_at'])
        return Response({'detail': message})

    @action(detail=True, methods=['post'], url_path='mark-available')
    def mark_available(self, request, pk=None):
        asset = self.get_object()
        if asset.assigned_to_id:
            return Response({'detail': 'Assigned assets must be returned before they can be marked available.'}, status=status.HTTP_400_BAD_REQUEST)
        return self._mark_status(request, asset, Asset.STATUS_AVAILABLE, 'Asset marked as available.')

    @action(detail=True, methods=['post'], url_path='mark-maintenance')
    def mark_maintenance(self, request, pk=None):
        asset = self.get_object()
        if asset.assigned_to_id:
            return Response({'detail': 'Assigned assets must be returned before maintenance status can be set.'}, status=status.HTTP_400_BAD_REQUEST)
        return self._mark_status(request, asset, Asset.STATUS_MAINTENANCE, 'Asset marked under maintenance.')

    @action(detail=True, methods=['post'], url_path='mark-damaged')
    def mark_damaged(self, request, pk=None):
        asset = self.get_object()
        return self._mark_status(request, asset, Asset.STATUS_DAMAGED, 'Asset marked as damaged.')

    @action(detail=True, methods=['post'], url_path='mark-lost')
    def mark_lost(self, request, pk=None):
        asset = self.get_object()
        return self._mark_status(request, asset, Asset.STATUS_LOST, 'Asset marked as lost.')

    @action(detail=True, methods=['post'], url_path='mark-retired')
    def mark_retired(self, request, pk=None):
        asset = self.get_object()
        return self._mark_status(request, asset, Asset.STATUS_RETIRED, 'Asset retired successfully.')


class AssetAssignmentViewSet(AssetAccessMixin, viewsets.ModelViewSet):
    serializer_class = AssetAssignmentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = (
            AssetAssignment.objects
            .filter(organization=self.request.user.current_organization)
            .select_related('asset', 'employee__user', 'employee__manager', 'assigned_by', 'returned_by')
        )
        role = get_role(self.request.user)
        if role in ASSET_ROLES:
            return qs
        current_employee = self._current_employee()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(employee=current_employee) | qs.filter(employee__manager=current_employee)
        if current_employee:
            return qs.filter(employee=current_employee)
        return qs.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsITOrAssetAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        assignment = serializer.save(organization=self.request.user.current_organization, assigned_by=self.request.user)
        asset = assignment.asset
        asset.assigned_to = assignment.employee
        asset.assigned_at = assignment.assigned_at
        asset.status = Asset.STATUS_ASSIGNED
        asset.save(update_fields=['assigned_to', 'assigned_at', 'status', 'updated_at'])


class AssetDocumentViewSet(AssetAccessMixin, viewsets.ModelViewSet):
    serializer_class = AssetDocumentSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = (
            AssetDocument.objects
            .filter(organization=self.request.user.current_organization)
            .select_related('asset', 'asset__assigned_to__user', 'asset__assigned_to__manager', 'uploaded_by')
            .defer('data')
        )
        role = get_role(self.request.user)
        if role in ASSET_ROLES:
            return qs
        current_employee = self._current_employee()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(asset__assigned_to=current_employee) | qs.filter(asset__assigned_to__manager=current_employee)
        if current_employee:
            return qs.filter(asset__assigned_to=current_employee)
        return qs.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsITOrAssetAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization, uploaded_by=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        document = get_object_or_404(AssetDocument, pk=pk, organization=request.user.current_organization)
        role = get_role(request.user)
        current_employee = Employee.objects.filter(organization=document.organization, user=request.user).first()
        can_access = role in ASSET_ROLES or (
            current_employee and document.asset.assigned_to_id == current_employee.pk
        ) or (
            current_employee and document.asset.assigned_to and document.asset.assigned_to.manager_id == current_employee.pk
        )
        if not can_access:
            return Response({'detail': 'You do not have permission to download this document.'}, status=status.HTTP_403_FORBIDDEN)
        response = HttpResponse(bytes(document.data), content_type=document.content_type or 'application/octet-stream')
        file_name = get_valid_filename(document.file_name or f'asset-document-{document.pk}')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response


class AssetMaintenanceViewSet(AssetAccessMixin, viewsets.ModelViewSet):
    serializer_class = AssetMaintenanceSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        qs = (
            AssetMaintenance.objects
            .filter(organization=self.request.user.current_organization)
            .select_related('asset', 'asset__assigned_to__user', 'asset__assigned_to__manager', 'created_by')
        )
        role = get_role(self.request.user)
        if role in ASSET_ROLES:
            return qs
        current_employee = self._current_employee()
        if role in MANAGER_ROLES and current_employee:
            return qs.filter(asset__assigned_to=current_employee) | qs.filter(asset__assigned_to__manager=current_employee)
        if current_employee:
            return qs.filter(asset__assigned_to=current_employee)
        return qs.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsITOrAssetAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        maintenance = serializer.save(organization=self.request.user.current_organization, created_by=self.request.user)
        asset = maintenance.asset
        if maintenance.status in [AssetMaintenance.STATUS_OPEN, AssetMaintenance.STATUS_IN_PROGRESS]:
            asset.status = Asset.STATUS_MAINTENANCE
            asset.save(update_fields=['status', 'updated_at'])
        notify_roles(
            maintenance.organization,
            ['OWNER', 'ADMIN', 'HR', 'IT'],
            title='Asset maintenance record created',
            message=f'Maintenance record added for {asset.asset_code} - {asset.name}.',
            notification_type='INFO',
            related_module='assets',
            related_object_id=asset.pk,
            action_url='/assets',
            created_by=self.request.user,
            exclude_user_ids=[self.request.user.id],
        )
