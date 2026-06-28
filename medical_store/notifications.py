from django.contrib.auth.models import User
from django.db.models import Q

from cssd.models import Notification

MANAGER_GROUPS = ["ADMIN", "HOSPITAL_MANAGER", "Hospital Manager"]
STORE_MANAGER_GROUPS = ["MEDICAL_STORE_MANAGER", "Medical Store Manager", "STORE_MANAGER"]


def users_in_groups(groups):
    return User.objects.filter(Q(is_superuser=True) | Q(groups__name__in=groups)).distinct()


def notify_users(title, message, url="", users=None, groups=None):
    recipients = list(users or [])
    if groups:
        recipients.extend(list(users_in_groups(groups)))

    seen = set()
    for user in recipients:
        if not user or not getattr(user, "id", None) or user.id in seen:
            continue
        seen.add(user.id)
        Notification.objects.create(
            recipient=user,
            target_group="USER",
            title=title,
            message=message,
            url=url,
        )
