from rest_framework import serializers
from .models import BackupLog, OrganizationSetting


class OrganizationSettingSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = OrganizationSetting
        fields = [
            'id', 'organization', 'organization_name', 'app_name', 'country', 'timezone', 'date_format', 'currency',
            'fiscal_year_start_month', 'leave_year_start_month', 'standard_working_hours_per_day',
            'attendance_grace_minutes', 'half_day_threshold_hours', 'overtime_rate_per_hour', 'weekly_off_days',
            'default_notice_period_days', 'default_probation_days', 'payroll_lock_day', 'document_max_upload_mb',
            'data_retention_days', 'support_email', 'allow_employee_profile_edit', 'allow_employee_self_attendance',
            'allow_employee_expense_submission', 'allow_employee_self_enrollment', 'enable_ip_restriction',
            'allowed_ip_ranges', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization', 'organization_name', 'created_at', 'updated_at']

    def validate_fiscal_year_start_month(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError('Fiscal year start month must be between 1 and 12.')
        return value

    def validate_leave_year_start_month(self, value):
        if value < 1 or value > 12:
            raise serializers.ValidationError('Leave year start month must be between 1 and 12.')
        return value

    def validate_payroll_lock_day(self, value):
        if value < 1 or value > 31:
            raise serializers.ValidationError('Payroll lock day must be between 1 and 31.')
        return value

    def validate_weekly_off_days(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Weekly off days must be a list.')
        allowed = {'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'}
        invalid = [day for day in value if day not in allowed]
        if invalid:
            raise serializers.ValidationError(f'Invalid weekly off days: {invalid}')
        return value

    def validate_allowed_ip_ranges(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Allowed IP ranges must be a list.')
        return value


class BackupLogSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(source='requested_by.email', read_only=True)

    class Meta:
        model = BackupLog
        fields = [
            'id', 'organization', 'backup_type', 'status', 'requested_by', 'requested_by_email', 'file_name',
            'command_used', 'notes', 'started_at', 'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'requested_by', 'requested_by_email', 'command_used',
            'started_at', 'completed_at', 'created_at', 'updated_at'
        ]
