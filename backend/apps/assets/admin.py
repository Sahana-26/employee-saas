from django.contrib import admin
from .models import Asset, AssetAssignment, AssetCategory, AssetDocument, AssetMaintenance


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('asset_code', 'name', 'asset_type', 'status', 'assigned_to', 'organization')
    search_fields = ('asset_code', 'name', 'serial_number', 'brand', 'model')
    list_filter = ('asset_type', 'status', 'organization')


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = ('asset', 'employee', 'status', 'assigned_at', 'returned_at', 'organization')
    search_fields = ('asset__asset_code', 'employee__employee_code', 'employee__user__email')
    list_filter = ('status', 'organization')


@admin.register(AssetDocument)
class AssetDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'asset', 'category', 'file_name', 'size', 'organization')
    search_fields = ('title', 'file_name', 'asset__asset_code')
    list_filter = ('category', 'organization')


@admin.register(AssetMaintenance)
class AssetMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('asset', 'maintenance_type', 'status', 'start_date', 'end_date', 'cost', 'organization')
    search_fields = ('asset__asset_code', 'maintenance_type', 'vendor')
    list_filter = ('status', 'organization')
