from django.utils import timezone
from apps.accounts.models import Membership
from apps.accounts.permissions import HR_ROLES, PAYROLL_ROLES, ASSET_ROLES
from apps.notifications.services import notify_employee, notify_roles, notify_user
from .models import OffboardingClearanceTask, FinalSettlement


def notify_offboarding_stakeholders(case, title, message, created_by=None):
    roles = set(HR_ROLES) | set(PAYROLL_ROLES) | set(ASSET_ROLES)
    notify_roles(
        organization=case.organization,
        roles=list(roles),
        title=title,
        message=message,
        notification_type='INFO',
        related_module='offboarding',
        related_object_id=case.pk,
        action_url='/offboarding',
        created_by=created_by,
        exclude_user_ids=[case.employee.user_id],
    )
    if case.employee.manager:
        notify_employee(
            case.employee.manager,
            title=title,
            message=message,
            notification_type='INFO',
            related_module='offboarding',
            related_object_id=case.pk,
            action_url='/offboarding',
            created_by=created_by,
        )


def create_default_clearance_tasks(case, created_by=None):
    if case.clearance_tasks.exists():
        return []
    manager_user = case.employee.manager.user if case.employee.manager else None
    tasks = [
        OffboardingClearanceTask(
            organization=case.organization,
            case=case,
            department=OffboardingClearanceTask.DEPT_MANAGER,
            title='Manager project handover',
            description='Confirm project handover, knowledge transfer, and pending task closure.',
            assigned_to=manager_user,
            due_date=case.last_working_day,
        ),
        OffboardingClearanceTask(
            organization=case.organization,
            case=case,
            department=OffboardingClearanceTask.DEPT_HR,
            title='HR exit formalities',
            description='Complete exit interview, document verification, and relieving checklist.',
            due_date=case.last_working_day,
        ),
        OffboardingClearanceTask(
            organization=case.organization,
            case=case,
            department=OffboardingClearanceTask.DEPT_FINANCE,
            title='Finance final settlement inputs',
            description='Confirm recoveries, reimbursements, payroll inputs, and final payable amount.',
            due_date=case.last_working_day,
        ),
    ]
    if case.employee.assigned_assets.filter(status='ASSIGNED').exists():
        tasks.append(OffboardingClearanceTask(
            organization=case.organization,
            case=case,
            department=OffboardingClearanceTask.DEPT_IT,
            title='IT asset return and access checklist',
            description='Collect assigned assets and confirm system access closure readiness.',
            due_date=case.last_working_day,
        ))
    created = OffboardingClearanceTask.objects.bulk_create(tasks)
    return created


def ensure_final_settlement(case, prepared_by=None):
    settlement, created = FinalSettlement.objects.get_or_create(
        organization=case.organization,
        case=case,
        defaults={
            'prepared_by': prepared_by,
            'basic_pay': case.employee.salary_basic or 0,
        }
    )
    return settlement, created


def deactivate_login(case, user):
    employee_user = case.employee.user
    employee_user.is_active = False
    employee_user.save(update_fields=['is_active'])
    Membership.objects.filter(organization=case.organization, user=employee_user).update(is_active=False)
    case.login_deactivated_at = timezone.now()
    case.save(update_fields=['login_deactivated_at', 'updated_at'])
    notify_user(
        user=user,
        organization=case.organization,
        title='Employee login deactivated',
        message=f'Login access for {case.employee.employee_code} has been deactivated.',
        notification_type='SUCCESS',
        related_module='offboarding',
        related_object_id=case.pk,
        action_url='/offboarding',
        created_by=user,
    )
