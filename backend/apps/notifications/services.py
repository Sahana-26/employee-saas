from apps.accounts.models import Membership
from .models import Notification


def notify_user(user, organization, title, message='', notification_type='INFO', related_module='', related_object_id=None, action_url='', created_by=None):
    if not user or not organization:
        return None
    return Notification.objects.create(
        organization=organization,
        recipient=user,
        created_by=created_by,
        title=title,
        message=message,
        notification_type=notification_type,
        related_module=related_module,
        related_object_id=related_object_id,
        action_url=action_url,
    )


def notify_employee(employee, title, message='', notification_type='INFO', related_module='', related_object_id=None, action_url='', created_by=None):
    if not employee:
        return None
    return notify_user(
        user=employee.user,
        organization=employee.organization,
        title=title,
        message=message,
        notification_type=notification_type,
        related_module=related_module,
        related_object_id=related_object_id,
        action_url=action_url,
        created_by=created_by,
    )


def notify_roles(organization, roles, title, message='', notification_type='INFO', related_module='', related_object_id=None, action_url='', created_by=None, exclude_user_ids=None):
    exclude_user_ids = set(exclude_user_ids or [])
    memberships = Membership.objects.filter(
        organization=organization,
        role__in=roles,
        is_active=True,
        user__is_active=True,
    ).select_related('user')
    notifications = []
    seen = set()
    for membership in memberships:
        user_id = membership.user_id
        if user_id in seen or user_id in exclude_user_ids:
            continue
        seen.add(user_id)
        notifications.append(Notification(
            organization=organization,
            recipient=membership.user,
            created_by=created_by,
            title=title,
            message=message,
            notification_type=notification_type,
            related_module=related_module,
            related_object_id=related_object_id,
            action_url=action_url,
        ))
    if notifications:
        Notification.objects.bulk_create(notifications)
    return notifications
