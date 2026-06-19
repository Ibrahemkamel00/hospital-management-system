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
    target_groups = target_groups or []
    users = list(users or [])

    # add users from target groups
    if target_groups:
        group_users = User.objects.filter(groups__name__in=target_groups).distinct()
        users.extend(list(group_users))

    # add managers
    users.extend(list(manager_users()))

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


def notifications_for_user(user):
    if not user.is_authenticated:
        return Notification.objects.none()

    return Notification.objects.filter(recipient=user)