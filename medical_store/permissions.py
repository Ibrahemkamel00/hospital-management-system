def in_group(user, names):
    if not user.is_authenticated:
        return False
    if isinstance(names, str):
        names = [names]
    return user.groups.filter(name__in=names).exists()


def is_store_manager(user):
    return in_group(user, ["MEDICAL_STORE_MANAGER", "Medical Store Manager", "STORE_MANAGER"])


def is_hospital_manager(user):
    return user.is_superuser or in_group(user, ["HOSPITAL_MANAGER", "Hospital Manager"])


def is_admin_user(user):
    return user.is_superuser or in_group(user, ["ADMIN", "MAINTENANCE_MANAGER", "Maintenance Manager"])


def is_engineer(user):
    return in_group(user, ["ENGINEER"])


def can_see_stock(user):
    return is_store_manager(user) or is_hospital_manager(user) or is_admin_user(user)


def can_enter_medical_store(user):
    return user.is_authenticated and not is_engineer(user)
