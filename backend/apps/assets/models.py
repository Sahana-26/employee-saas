from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class AssetCategory(TenantModel):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class Asset(TenantModel):
    TYPE_LAPTOP = 'LAPTOP'
    TYPE_DESKTOP = 'DESKTOP'
    TYPE_MOBILE = 'MOBILE'
    TYPE_TABLET = 'TABLET'
    TYPE_SIM = 'SIM'
    TYPE_ACCESSORY = 'ACCESSORY'
    TYPE_SOFTWARE = 'SOFTWARE'
    TYPE_NETWORK = 'NETWORK'
    TYPE_OTHER = 'OTHER'
    TYPE_CHOICES = (
        (TYPE_LAPTOP, 'Laptop'),
        (TYPE_DESKTOP, 'Desktop'),
        (TYPE_MOBILE, 'Mobile'),
        (TYPE_TABLET, 'Tablet'),
        (TYPE_SIM, 'SIM Card'),
        (TYPE_ACCESSORY, 'Accessory'),
        (TYPE_SOFTWARE, 'Software License'),
        (TYPE_NETWORK, 'Network Device'),
        (TYPE_OTHER, 'Other'),
    )

    STATUS_AVAILABLE = 'AVAILABLE'
    STATUS_ASSIGNED = 'ASSIGNED'
    STATUS_MAINTENANCE = 'MAINTENANCE'
    STATUS_DAMAGED = 'DAMAGED'
    STATUS_LOST = 'LOST'
    STATUS_RETIRED = 'RETIRED'
    STATUS_CHOICES = (
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_ASSIGNED, 'Assigned'),
        (STATUS_MAINTENANCE, 'Under Maintenance'),
        (STATUS_DAMAGED, 'Damaged'),
        (STATUS_LOST, 'Lost'),
        (STATUS_RETIRED, 'Retired'),
    )

    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='assets')
    category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    asset_code = models.CharField(max_length=60)
    name = models.CharField(max_length=180)
    asset_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default=TYPE_LAPTOP)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)
    brand = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_end_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vendor = models.CharField(max_length=180, blank=True)
    location = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets')
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_assets')

    class Meta:
        unique_together = ('organization', 'asset_code')
        ordering = ['asset_code']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'asset_type']),
            models.Index(fields=['organization', 'assigned_to']),
        ]

    def __str__(self):
        return f'{self.asset_code} - {self.name}'

    @property
    def is_warranty_active(self):
        return bool(self.warranty_end_date and self.warranty_end_date >= timezone.localdate())


class AssetAssignment(TenantModel):
    STATUS_ASSIGNED = 'ASSIGNED'
    STATUS_RETURNED = 'RETURNED'
    STATUS_CHOICES = (
        (STATUS_ASSIGNED, 'Assigned'),
        (STATUS_RETURNED, 'Returned'),
    )

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='assignments')
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='asset_assignments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ASSIGNED)
    assigned_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='asset_assignments_done')
    returned_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='asset_returns_done')
    assigned_at = models.DateTimeField(default=timezone.now)
    expected_return_date = models.DateField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    condition_at_issue = models.TextField(blank=True)
    condition_at_return = models.TextField(blank=True)
    issue_notes = models.TextField(blank=True)
    return_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'employee']),
            models.Index(fields=['organization', 'asset']),
        ]

    def __str__(self):
        return f'{self.asset.asset_code} -> {self.employee.employee_code}'


class AssetDocument(TenantModel):
    CATEGORY_INVOICE = 'INVOICE'
    CATEGORY_WARRANTY = 'WARRANTY'
    CATEGORY_HANDOVER = 'HANDOVER'
    CATEGORY_PHOTO = 'PHOTO'
    CATEGORY_OTHER = 'OTHER'
    CATEGORY_CHOICES = (
        (CATEGORY_INVOICE, 'Invoice'),
        (CATEGORY_WARRANTY, 'Warranty'),
        (CATEGORY_HANDOVER, 'Handover'),
        (CATEGORY_PHOTO, 'Photo'),
        (CATEGORY_OTHER, 'Other'),
    )

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    data = models.BinaryField(editable=False)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_asset_documents')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['organization', 'asset'])]

    def __str__(self):
        return f'{self.asset.asset_code} - {self.title}'


class AssetMaintenance(TenantModel):
    STATUS_OPEN = 'OPEN'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = (
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='maintenance_records')
    maintenance_type = models.CharField(max_length=120)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_OPEN)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    vendor = models.CharField(max_length=180, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_asset_maintenance')

    class Meta:
        ordering = ['-start_date']
        indexes = [models.Index(fields=['organization', 'status'])]

    def __str__(self):
        return f'{self.asset.asset_code} - {self.maintenance_type}'
