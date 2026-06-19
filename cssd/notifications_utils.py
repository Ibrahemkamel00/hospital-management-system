from django.contrib.auth.models import User
from django.db.models import Q

from .models import Notification


MANAGER_GROUP_NAMES = [
    "ADMIN",
    "MAINTENANCE_MANAGER",
    "HOSPITAL_MANAGER",
    "Maintenance Manager",
    "Hospital Manager",
]


def manager_users():
    return User.objects.filter(
        Q(is_superuser=True) | Q(groups__name__in=MANAGER_GROUP_NAMES)
    ).distinct()


def notify_event(title, message, url="", target_groups=None, users=None, cssd_request=None):
    """
    Creates clickable notifications for:
    - selected groups/departments
    - selected users, like assigned engineer
    - all Maintenance/Hospital managers automatically
    """
    target_groups = target_groups or []
    users = list(users or [])

    for manager in manager_users():
        users.append(manager)

    created_user_ids = set()

    for user in users:
        if not user or not getattr(user, "id", None):
            continue
        if user.id in created_user_ids:
            continue
        created_user_ids.add(user.id)
        Notification.objects.create(
            recipient=user,
            target_group="USER",
            title=title,
            message=message,
            cssd_request=cssd_request,
            url=url,
        )

    for group in target_groups:
        if not group:
            continue
        Notification.objects.create(
            target_group=group,
            title=title,
            message=message,
            cssd_request=cssd_request,
            url=url,
        )


def notifications_for_user(user):
    if not user.is_authenticated:
        return Notification.objects.none()

    user_groups = list(user.groups.values_list("name", flat=True))

    return Notification.objects.filter(
        Q(recipient=user) |
        Q(recipient__isnull=True, target_group__in=user_groups)
    ).distinct()
