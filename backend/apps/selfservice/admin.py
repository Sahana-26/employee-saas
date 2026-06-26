from django.contrib import admin
from .models import ProfileChangeRequest


@admin.register(ProfileChangeRequest)
class ProfileChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'organization', 'status', 'reviewed_by', 'created_at', 'reviewed_at')
    list_filter = ('status', 'organization')
    search_fields = ('employee__employee_code', 'employee__user__email')
