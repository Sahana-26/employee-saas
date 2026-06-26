from rest_framework import serializers
from apps.accounts.permissions import ASSET_ROLES, MANAGER_ROLES, get_role
from apps.hr.models import Employee
from .models import Asset, AssetAssignment, AssetCategory, AssetDocument, AssetMaintenance


class AssetCategorySerializer(serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetCategory
        fields = ['id', 'organization', 'name', 'description', 'is_active', 'asset_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'organization', 'asset_count', 'created_at', 'updated_at']

    def get_asset_count(self, obj):
        return obj.assets.count()


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    assigned_to_code = serializers.CharField(source='assigned_to.employee_code', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    assignment_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    maintenance_count = serializers.SerializerMethodField()
    is_warranty_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'organization', 'category', 'category_name', 'asset_code', 'name', 'asset_type', 'status',
            'brand', 'model', 'serial_number', 'purchase_date', 'warranty_end_date', 'is_warranty_active',
            'purchase_cost', 'vendor', 'location', 'notes', 'assigned_to', 'assigned_to_name', 'assigned_to_code',
            'assigned_at', 'created_by', 'created_by_email', 'assignment_count', 'document_count',
            'maintenance_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'assigned_to', 'assigned_to_name', 'assigned_to_code', 'assigned_at',
            'created_by', 'created_by_email', 'assignment_count', 'document_count', 'maintenance_count',
            'is_warranty_active', 'created_at', 'updated_at',
        ]

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return ''
        return f'{obj.assigned_to.user.first_name} {obj.assigned_to.user.last_name}'.strip() or obj.assigned_to.user.email

    def get_assignment_count(self, obj):
        return obj.assignments.count()

    def get_document_count(self, obj):
        return obj.documents.count()

    def get_maintenance_count(self, obj):
        return obj.maintenance_records.count()

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs
        org = request.user.current_organization
        category = attrs.get('category', getattr(self.instance, 'category', None))
        if category and category.organization_id != org.id:
            raise serializers.ValidationError('Asset category must belong to your organization.')
        return attrs


class AssetAssignSerializer(serializers.Serializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    expected_return_date = serializers.DateField(required=False, allow_null=True)
    condition_at_issue = serializers.CharField(required=False, allow_blank=True)
    issue_notes = serializers.CharField(required=False, allow_blank=True)

    def validate_employee(self, employee):
        request = self.context.get('request')
        if request and employee.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Employee must belong to your organization.')
        return employee


class AssetReturnSerializer(serializers.Serializer):
    condition_at_return = serializers.CharField(required=False, allow_blank=True)
    return_notes = serializers.CharField(required=False, allow_blank=True)
    next_status = serializers.ChoiceField(
        choices=[Asset.STATUS_AVAILABLE, Asset.STATUS_MAINTENANCE, Asset.STATUS_DAMAGED, Asset.STATUS_RETIRED],
        default=Asset.STATUS_AVAILABLE,
        required=False,
    )


class AssetStatusSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


class AssetAssignmentSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source='asset.asset_code', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    assigned_by_email = serializers.EmailField(source='assigned_by.email', read_only=True)
    returned_by_email = serializers.EmailField(source='returned_by.email', read_only=True)

    class Meta:
        model = AssetAssignment
        fields = [
            'id', 'organization', 'asset', 'asset_code', 'asset_name', 'employee', 'employee_name', 'employee_code',
            'status', 'assigned_by', 'assigned_by_email', 'returned_by', 'returned_by_email', 'assigned_at',
            'expected_return_date', 'returned_at', 'condition_at_issue', 'condition_at_return', 'issue_notes',
            'return_notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'assigned_by', 'assigned_by_email', 'returned_by', 'returned_by_email',
            'assigned_at', 'returned_at', 'created_at', 'updated_at',
        ]

    def get_employee_name(self, obj):
        return f'{obj.employee.user.first_name} {obj.employee.user.last_name}'.strip() or obj.employee.user.email

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs
        org = request.user.current_organization
        asset = attrs.get('asset', getattr(self.instance, 'asset', None))
        employee = attrs.get('employee', getattr(self.instance, 'employee', None))
        if asset and asset.organization_id != org.id:
            raise serializers.ValidationError('Asset must belong to your organization.')
        if employee and employee.organization_id != org.id:
            raise serializers.ValidationError('Employee must belong to your organization.')
        return attrs


class AssetDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    asset_code = serializers.CharField(source='asset.asset_code', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = AssetDocument
        fields = [
            'id', 'organization', 'asset', 'asset_code', 'asset_name', 'title', 'category', 'file', 'file_name',
            'content_type', 'size', 'download_url', 'uploaded_by', 'uploaded_by_email', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'file_name', 'content_type', 'size', 'download_url', 'uploaded_by',
            'uploaded_by_email', 'created_at', 'updated_at',
        ]

    def get_download_url(self, obj):
        request = self.context.get('request')
        path = f'/api/asset-documents/{obj.pk}/download/'
        return request.build_absolute_uri(path) if request else path

    def validate(self, attrs):
        request = self.context.get('request')
        asset = attrs.get('asset', getattr(self.instance, 'asset', None))
        if request and asset and asset.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Asset must belong to your organization.')
        if self.instance is None and not attrs.get('file'):
            raise serializers.ValidationError({'file': 'A file is required.'})
        return attrs

    def _attach_file_data(self, validated_data):
        uploaded_file = validated_data.pop('file', None)
        if uploaded_file:
            data = uploaded_file.read()
            validated_data['file_name'] = uploaded_file.name
            validated_data['content_type'] = getattr(uploaded_file, 'content_type', None) or 'application/octet-stream'
            validated_data['size'] = getattr(uploaded_file, 'size', None) or len(data)
            validated_data['data'] = data
        return validated_data

    def create(self, validated_data):
        validated_data = self._attach_file_data(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._attach_file_data(validated_data)
        return super().update(instance, validated_data)


class AssetMaintenanceSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source='asset.asset_code', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = AssetMaintenance
        fields = [
            'id', 'organization', 'asset', 'asset_code', 'asset_name', 'maintenance_type', 'status', 'start_date',
            'end_date', 'vendor', 'cost', 'notes', 'created_by', 'created_by_email', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_by', 'created_by_email', 'created_at', 'updated_at']

    def validate(self, attrs):
        request = self.context.get('request')
        asset = attrs.get('asset', getattr(self.instance, 'asset', None))
        if request and asset and asset.organization_id != request.user.current_organization_id:
            raise serializers.ValidationError('Asset must belong to your organization.')
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError('end_date cannot be before start_date.')
        return attrs
