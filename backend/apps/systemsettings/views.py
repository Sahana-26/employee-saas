from django.apps import apps
from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.permissions import IsOwnerOrAdmin
from apps.audit.models import AuditLog
from .models import BackupLog, OrganizationSetting
from .serializers import BackupLogSerializer, OrganizationSettingSerializer


class OrganizationSettingView(APIView):
    permission_classes = [IsOwnerOrAdmin]

    def get_object(self, request):
        setting, _ = OrganizationSetting.objects.get_or_create(
            organization=request.user.current_organization,
            defaults={
                'weekly_off_days': ['SATURDAY', 'SUNDAY'],
                'support_email': request.user.email,
            }
        )
        return setting

    def get(self, request):
        serializer = OrganizationSettingSerializer(self.get_object(request))
        return Response(serializer.data)

    def patch(self, request):
        setting = self.get_object(request)
        serializer = OrganizationSettingSerializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        AuditLog.objects.create(
            organization=request.user.current_organization,
            actor=request.user,
            action='UPDATED',
            entity='OrganizationSetting',
            entity_id=str(setting.id),
            metadata={'updated_fields': list(request.data.keys())}
        )
        return Response(serializer.data)


class SystemHealthView(APIView):
    permission_classes = [IsOwnerOrAdmin]

    def get(self, request):
        db_status = 'OK'
        db_error = ''
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except Exception as exc:
            db_status = 'ERROR'
            db_error = str(exc)
        return Response({
            'status': 'OK' if db_status == 'OK' else 'ERROR',
            'database': db_status,
            'database_error': db_error,
            'debug_mode': settings.DEBUG,
            'application_time': timezone.now(),
            'organization': request.user.current_organization.name,
        })


class SystemOverviewView(APIView):
    permission_classes = [IsOwnerOrAdmin]

    MODEL_MAP = {
        'employees': ('hr', 'Employee'),
        'departments': ('hr', 'Department'),
        'attendance_records': ('attendance', 'Attendance'),
        'leave_requests': ('leaves', 'LeaveRequest'),
        'payroll_runs': ('payroll', 'PayrollRun'),
        'payslips': ('payroll', 'Payslip'),
        'documents': ('documents', 'EmployeeDocument'),
        'expenses': ('expenses', 'ExpenseClaim'),
        'notifications': ('notifications', 'Notification'),
        'announcements': ('notifications', 'Announcement'),
        'policies': ('policies', 'CompanyPolicy'),
        'assets': ('assets', 'Asset'),
        'offboarding_cases': ('offboarding', 'OffboardingCase'),
        'job_openings': ('recruitment', 'JobOpening'),
        'candidates': ('recruitment', 'Candidate'),
        'training_courses': ('training', 'TrainingCourse'),
        'support_tickets': ('helpdesk', 'SupportTicket'),
        'work_projects': ('timesheets', 'WorkProject'),
        'generated_letters': ('hrletters', 'GeneratedLetter'),
        'audit_logs': ('audit', 'AuditLog'),
    }

    def get_count(self, app_label, model_name, organization):
        try:
            model = apps.get_model(app_label, model_name)
            return model.objects.filter(organization=organization).count()
        except Exception:
            return 0

    def get(self, request):
        org = request.user.current_organization
        counts = {
            key: self.get_count(app_label, model_name, org)
            for key, (app_label, model_name) in self.MODEL_MAP.items()
        }
        latest_backups = BackupLog.objects.filter(organization=org).order_by('-created_at')[:5]
        latest_audits = AuditLog.objects.filter(organization=org).select_related('actor')[:10]
        return Response({
            'organization': {'id': org.id, 'name': org.name, 'slug': org.slug, 'is_active': org.is_active},
            'counts': counts,
            'latest_backups': BackupLogSerializer(latest_backups, many=True).data,
            'latest_audits': [
                {
                    'id': audit.id,
                    'actor': audit.actor.email if audit.actor else None,
                    'action': audit.action,
                    'entity': audit.entity,
                    'entity_id': audit.entity_id,
                    'created_at': audit.created_at,
                }
                for audit in latest_audits
            ]
        })


class BackupLogViewSet(viewsets.ModelViewSet):
    serializer_class = BackupLogSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        return BackupLog.objects.filter(organization=self.request.user.current_organization).select_related('requested_by')

    def perform_create(self, serializer):
        org = self.request.user.current_organization
        backup = serializer.save(organization=org, requested_by=self.request.user)
        backup.file_name = backup.file_name or f'{org.slug}-{backup.backup_type.lower()}-{timezone.now().strftime("%Y%m%d-%H%M%S")}.dump'
        backup.command_used = self.build_backup_command(backup)
        backup.save(update_fields=['file_name', 'command_used', 'updated_at'])
        AuditLog.objects.create(
            organization=org,
            actor=self.request.user,
            action='REQUESTED',
            entity='BackupLog',
            entity_id=str(backup.id),
            metadata={'backup_type': backup.backup_type, 'file_name': backup.file_name}
        )

    def build_backup_command(self, backup):
        options = ''
        if backup.backup_type == 'SCHEMA_ONLY':
            options = '--schema-only'
        elif backup.backup_type == 'DATA_ONLY':
            options = '--data-only'
        return f'docker compose exec db pg_dump -U employeehub -d employeehub -Fc {options} -f /backups/{backup.file_name}'.replace('  ', ' ')

    @action(detail=True, methods=['post'], url_path='mark-running')
    def mark_running(self, request, pk=None):
        backup = self.get_object()
        backup.mark_running()
        return Response(self.get_serializer(backup).data)

    @action(detail=True, methods=['post'], url_path='mark-completed')
    def mark_completed(self, request, pk=None):
        backup = self.get_object()
        backup.mark_completed()
        return Response(self.get_serializer(backup).data)

    @action(detail=True, methods=['post'], url_path='mark-failed')
    def mark_failed(self, request, pk=None):
        backup = self.get_object()
        backup.mark_failed(request.data.get('notes', ''))
        return Response(self.get_serializer(backup).data)

    @action(detail=False, methods=['get'], url_path='backup-command')
    def backup_command(self, request):
        org = request.user.current_organization
        file_name = f'{org.slug}-full-db-{timezone.now().strftime("%Y%m%d-%H%M%S")}.dump'
        return Response({
            'file_name': file_name,
            'command': f'docker compose exec db pg_dump -U employeehub -d employeehub -Fc -f /backups/{file_name}',
            'restore_command': f'docker compose exec db pg_restore -U employeehub -d employeehub --clean --if-exists /backups/{file_name}',
            'note': 'The API records backup requests. Run the command on the server where Docker Compose is running.'
        })
