from .models import Notification
from django.utils import timezone
from .views import is_engineer, is_admin, is_cssd
from .notifications_utils import notifications_for_user


def notification_count(request):

    if not request.user.is_authenticated:
        return {
            "unread_notifications_count": 0
        }

    unread_qs = notifications_for_user(request.user).filter(is_read=False)
    seen_at = request.session.get("notifications_seen_at")
    if seen_at:
        try:
            seen_dt = timezone.datetime.fromisoformat(seen_at)
            if timezone.is_naive(seen_dt):
                seen_dt = timezone.make_aware(seen_dt)
            unread_qs = unread_qs.filter(created_at__gt=seen_dt)
        except Exception:
            pass

    return {
        "unread_notifications_count": unread_qs.count()
    }


def system_header(request):

    path = request.path
    system = request.GET.get("system", "")

    is_engineer_user = (
        request.user.is_authenticated
        and is_engineer(request.user)
    )

    is_admin_user = (
        request.user.is_authenticated
        and is_admin(request.user)
    )

    is_cssd_user = (
        request.user.is_authenticated
        and is_cssd(request.user)
    )

    maintenance_paths = (
        "/assets",
        "/maintenance",
        "/maintenance-requests",
        "/my-maintenance",
        "/spare-parts-tracking",
        "/pending-spare-parts",
        "/pm",
        "/engineer-dashboard",
        "/clinic-dashboard",
        "/clinic-assets",
        "/clinic-waiting-parts-assets",
        "/hospital-maintenance-dashboard",
        "/maintenance-locations",
        "/maintenance-kpi",
    )

    cssd_paths = (
        "/cssd",
        "/new-request",
        "/get-template-items",
        "/return-to-clinic",
        "/clinic-pending-returns",
        "/clinic-confirm-details",
        "/confirm-by-clinic",
        "/close-request",
        "/print-request",
        "/all-requests",
        "/reports",
        "/my-requests",
        "/cssd-received",
        "/cssd-pending",
        "/request",
        "/hospital-cssd-dashboard",
    )

    if path.startswith("/notifications") and system == "maintenance":
        return {
            "system_title": "Maintenance Management System",
            "system_subtitle": "Biomedical Engineering Department",
            "back_dashboard_url": "/maintenance/",
            "is_engineer_user": is_engineer_user,
            "is_admin_user": is_admin_user,
            "is_cssd_user": is_cssd_user,
        }

    if path.startswith("/notifications") and system == "cssd":
        return {
            "system_title": "CSSD Tracking System",
            "system_subtitle": "Central Sterilization Department",
            "back_dashboard_url": "/",
            "is_engineer_user": is_engineer_user,
            "is_admin_user": is_admin_user,
            "is_cssd_user": is_cssd_user,
        }

    if path.startswith("/infection-control"):
        return {
            "system_title": "Infection Control System",
            "system_subtitle": "Clinic Cleaning Management",
            "back_dashboard_url": "/infection-control/",
            "is_engineer_user": is_engineer_user,
            "is_admin_user": is_admin_user,
            "is_cssd_user": is_cssd_user,
        }

    if path.startswith("/systems"):
        return {
            "system_title": "Hospital Management Systems",
            "system_subtitle": "UMM ALQURA Dental Teaching Hospital",
            "back_dashboard_url": "/systems/",
            "is_engineer_user": is_engineer_user,
            "is_admin_user": is_admin_user,
            "is_cssd_user": is_cssd_user,
        }

    if path.startswith(maintenance_paths):
        return {
            "system_title": "Maintenance Management System",
            "system_subtitle": "Biomedical Engineering Department",
            "back_dashboard_url": "/maintenance/",
            "is_engineer_user": is_engineer_user,
            "is_admin_user": is_admin_user,
            "is_cssd_user": is_cssd_user,
        }

    if path.startswith(cssd_paths):
        return {
            "system_title": "CSSD Tracking System",
            "system_subtitle": "Central Sterilization Department",
            "back_dashboard_url": "/",
            "is_engineer_user": is_engineer_user,
            "is_admin_user": is_admin_user,
            "is_cssd_user": is_cssd_user,
        }

    return {
        "system_title": "Hospital Management Systems",
        "system_subtitle": "UMM ALQURA Dental Teaching Hospital",
        "back_dashboard_url": "/systems/",
        "is_engineer_user": is_engineer_user,
        "is_admin_user": is_admin_user,
        "is_cssd_user": is_cssd_user,
    }