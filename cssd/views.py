from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.auth.models import User, Group
from django.db.models import Count
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

import qrcode
import base64
import json
from io import BytesIO

from datetime import date, timedelta
from datetime import timedelta

from .models import Notification
from .notifications_utils import notify_event, notifications_for_user

@login_required
def notifications(request):

    notifications_qs = notifications_for_user(request.user).order_by("-created_at")

    # Opening the notifications page clears the red counter only.
    # The blue unread marker remains until the user clicks the notification itself.
    request.session["notifications_seen_at"] = timezone.now().isoformat()

    return render(
        request,
        "cssd/notifications.html",
        {
            "notifications": notifications_qs,
            "system_mode": request.GET.get("system", "cssd")
        }
    )


@login_required
def open_notification(request, notification_id):
    notification = get_object_or_404(
        notifications_for_user(request.user),
        id=notification_id
    )
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect(notification.url or "notifications")


@login_required
def notifications_count(request):
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

    return JsonResponse({
        "unread_count": unread_qs.count()
    })

from .forms import NewCSSDRequestForm
from .models import (
    CSSDTemplate,
    CSSDTemplateItem,
    CSSDRequest,
    CSSDRequestTemplate,
    CSSDRequestItem,
    Notification,
    Asset,
    MaintenanceRequest,
    PMHistory,
    MaintenanceSparePart,
    Location,
    MaintenanceRequestTimeline,
    PMHistoryItem,
    InquiryMessage,
    RequestAttachment,
    InfectionCleaningAssignment,
    InfectionCleaningTask,
    InfectionProcedureTemplate,
    InfectionProcedureTemplateItem,
    
)


def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def is_admin(user):
    return (
        user.is_superuser
        or user.groups.filter(name__in=["ADMIN", "MAINTENANCE_MANAGER", "Maintenance Manager"]).exists()
    )


def is_cssd(user):
    return user_in_group(user, "CSSD")

def is_engineer(user):
    return user.groups.filter(name="ENGINEER").exists()
def is_maintenance_manager(user):
    return (
        user.is_superuser
        or user.groups.filter(name__in=["ADMIN", "MAINTENANCE_MANAGER", "Maintenance Manager"]).exists()
    )

def is_hospital_manager(user):
    return user.groups.filter(name__in=["HOSPITAL_MANAGER", "Hospital Manager"]).exists()

def is_manager_or_hospital(user):
    return is_maintenance_manager(user) or is_hospital_manager(user)


def is_infection_manager(user):
    return (
        user.is_superuser
        or user.groups.filter(name__in=[
            "ADMIN", "MAINTENANCE_MANAGER", "Maintenance Manager",
            "HOSPITAL_MANAGER", "Hospital Manager",
            "INFECTION_CONTROL_MANAGER", "Infection Control Manager"
        ]).exists()
    )

def is_nurse_user(user):
    return user.groups.filter(name__in=["NURSE", "CLINIC", "MALE", "FEMALE", "SPECIALTY", "EMERGENCY"]).exists()

def is_medical_store_manager(user):
    return user.groups.filter(name__in=["MEDICAL_STORE_MANAGER", "Medical Store Manager", "STORE_MANAGER"]).exists()

def last_timeline_date(maintenance_request, actions):
    item = maintenance_request.timeline.filter(action__in=actions).order_by("-created_at").first()
    return item.created_at if item else None

def set_asset_status_after_repair(asset):

    has_waiting_spare_request = MaintenanceRequest.objects.filter(
        asset=asset,
        status="WAITING_PARTS",
        needs_spare_parts=True
    ).exists()

    if has_waiting_spare_request:
        asset.status = "ACTIVE_NEED_SPARE"
    else:
        asset.status = "ACTIVE"

    asset.save()

def visible_assets_for_user(user):
    if user.is_superuser or is_admin(user) or is_hospital_manager(user):
        return Asset.objects.all()

    if is_engineer(user):
        return Asset.objects.filter(
            location__engineers=user
        ).distinct()

    user_groups = user_location_groups(user)

    return Asset.objects.filter(
        location__group_type__in=user_groups
    ).distinct()


def visible_maintenance_requests_for_user(user):
    if user.is_superuser or is_admin(user) or is_hospital_manager(user):
        return MaintenanceRequest.objects.all()

    if is_engineer(user):
        return MaintenanceRequest.objects.filter(
            asset__location__engineers=user
        ).distinct()

    user_groups = user_location_groups(user)

    return MaintenanceRequest.objects.filter(
        asset__location__group_type__in=user_groups
    ).distinct()


def calculate_maintenance_kpis(requests_qs=None, assets_qs=None):
    if requests_qs is None:
        requests_qs = MaintenanceRequest.objects.all()
    if assets_qs is None:
        assets_qs = Asset.objects.all()

    total_assets = assets_qs.count()
    active_assets = assets_qs.filter(status__in=["ACTIVE", "ACTIVE_NEED_SPARE"]).count()
    availability = round((active_assets / total_assets) * 100, 1) if total_assets else 0

    closed = requests_qs.filter(status="CLOSED", closed_at__isnull=False)
    mttr_values = []
    for req in closed:
        if req.reported_at and req.closed_at:
            mttr_values.append((req.closed_at - req.reported_at).total_seconds() / 86400)
    mttr_days = round(sum(mttr_values) / len(mttr_values), 1) if mttr_values else 0

    mtbf_values = []
    for asset in assets_qs.filter(maintenance_requests__status="CLOSED").distinct():
        history = asset.maintenance_requests.filter(
            status="CLOSED",
            closed_at__isnull=False
        ).order_by("closed_at")
        dates = [r.closed_at for r in history]
        if len(dates) >= 2:
            gaps = [(dates[i] - dates[i - 1]).total_seconds() / 86400 for i in range(1, len(dates))]
            if gaps:
                mtbf_values.append(sum(gaps) / len(gaps))
    mtbf_days = round(sum(mtbf_values) / len(mtbf_values), 1) if mtbf_values else 0

    return {
        "availability": availability,
        "mttr_days": mttr_days,
        "mtbf_days": mtbf_days,
    }


def monthly_closed_requests(requests_qs):
    today = timezone.localdate()
    labels = []
    values = []
    for i in range(5, -1, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        labels.append(f"{year}-{month:02d}")
        values.append(requests_qs.filter(status="CLOSED", closed_at__year=year, closed_at__month=month).count())
    return labels, values

def user_location_groups(user):
    groups = ["MALE", "FEMALE", "SPECIALTY", "EMERGENCY"]
    return [g for g in groups if user_in_group(user, g)]


def visible_requests_for_user(user):
    if is_admin(user) or is_cssd(user) or is_hospital_manager(user):
        return CSSDRequest.objects.all()

    user_groups = user_location_groups(user)
    return CSSDRequest.objects.filter(location__group_type__in=user_groups)


def can_access_request(user, cssd_request):
    if is_admin(user) or is_cssd(user) or is_hospital_manager(user):
        return True

    return cssd_request.location.group_type in user_location_groups(user)

from datetime import date, timedelta

@login_required
def asset_list(request):

    assets = visible_assets_for_user(request.user).order_by("asset_number")
    search_by = request.GET.get("search_by", "")
    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "")

    if status_filter:
        assets = assets.filter(status=status_filter)

    if search:
        if search_by == "serial_number":
            assets = assets.filter(serial_number__icontains=search)
        elif search_by == "device_name":
            assets = assets.filter(device_name__icontains=search)
        elif search_by == "location":
            assets = assets.filter(location__name__icontains=search)
        elif search_by == "status":
            assets = assets.filter(status__icontains=search)
        else:
            assets = assets.filter(asset_number__icontains=search)

    today = date.today()
    pm_due_date = today + timedelta(days=4)
    pm_soon_date = today + timedelta(days=30)

    total_assets = Asset.objects.count()
    active_assets = Asset.objects.filter(status="ACTIVE").count()
    active_need_spare = Asset.objects.filter(status="ACTIVE_NEED_SPARE").count()
    out_of_service_assets = Asset.objects.filter(status="OUT_OF_SERVICE").count()

    locations_count = Location.objects.count()

    engineers_count = User.objects.filter(
        groups__name="ENGINEER"
    ).distinct().count()

    total_requests = MaintenanceRequest.objects.count()
    open_requests = MaintenanceRequest.objects.filter(status="OPEN").count()
    under_maintenance = MaintenanceRequest.objects.filter(status="IN_PROGRESS").count()
    waiting_parts = MaintenanceRequest.objects.filter(status="WAITING_PARTS").count()
    waiting_part_approval = MaintenanceRequest.objects.filter(status="WAITING_PART_APPROVAL").count()
    waiting_confirmation = MaintenanceRequest.objects.filter(status="WAITING_CONFIRMATION").count()
    completed_requests = MaintenanceRequest.objects.filter(status="CLOSED").count()
    pending_approval = MaintenanceRequest.objects.filter(status="CLOSED", report_approved=False).count()

    qr_reports = MaintenanceRequest.objects.filter(
        request_source="QR"
    ).count()

    pm_due_assets = Asset.objects.filter(
        next_pm_date__lte=pm_due_date
    ).exclude(
        next_pm_date__isnull=True
    ).order_by("next_pm_date")

    pm_due = pm_due_assets.count()

    completed_pm_month = PMHistory.objects.filter(
        status="CLOSED",
        performed_at__year=today.year,
        performed_at__month=today.month
    ).count()

    availability = round(
        (active_assets / total_assets) * 100,
        1
    ) if total_assets else 0

    pm_total = completed_pm_month + pm_due

    pm_compliance = round(
        (completed_pm_month / pm_total) * 100,
        1
    ) if pm_total else 100

    closed_requests_qs = MaintenanceRequest.objects.filter(
        status="CLOSED",
        closed_at__isnull=False
    )

    total_repair_days = 0
    mttr_count = 0

    for req in closed_requests_qs:
        repair_time = req.closed_at - req.reported_at
        total_repair_days += repair_time.total_seconds() / 86400
        mttr_count += 1

    mttr_days = round(
        total_repair_days / mttr_count,
        1
    ) if mttr_count else 0

    mtbf_days = 0

    assets_with_requests = Asset.objects.filter(
        maintenance_requests__status="CLOSED"
    ).distinct()

    mtbf_values = []

    for asset in assets_with_requests:
        closed_history = asset.maintenance_requests.filter(
            status="CLOSED",
            closed_at__isnull=False
        ).order_by("closed_at")

        dates = [req.closed_at for req in closed_history]

        if len(dates) >= 2:
            gaps = []

            for i in range(1, len(dates)):
                diff = dates[i] - dates[i - 1]
                gaps.append(diff.total_seconds() / 86400)

            if gaps:
                mtbf_values.append(sum(gaps) / len(gaps))

    if mtbf_values:
        mtbf_days = round(
            sum(mtbf_values) / len(mtbf_values),
            1
        )

    top_faulty_devices = Asset.objects.annotate(
    faults_count=Count("maintenance_requests")
).filter(
    faults_count__gt=0
).order_by("-faults_count")[:10]


    return render(
        request,
        "cssd/asset_list.html",
        {
            "assets": assets,

            "total_assets": total_assets,
            "active_assets": active_assets,
            "active_need_spare": active_need_spare,
            "out_of_service_assets": out_of_service_assets,
            "top_faulty_devices": top_faulty_devices,

            "locations_count": locations_count,
            "engineers_count": engineers_count,

            "total_requests": total_requests,
            "open_requests": open_requests,
            "under_maintenance": under_maintenance,
            "waiting_parts": waiting_parts,
            "waiting_part_approval": waiting_part_approval,
            "waiting_confirmation": waiting_confirmation,
            "completed_requests": completed_requests,
            "pending_approval": pending_approval,
            "qr_reports": qr_reports,

            "pm_due": pm_due,
            "pm_due_assets": pm_due_assets,
            "completed_pm_month": completed_pm_month,

            "availability": availability,
            "pm_compliance": pm_compliance,
            "mttr_days": mttr_days,
            "mtbf_days": mtbf_days,

            "today": today,
            "pm_due_date": pm_due_date,
            "pm_soon_date": pm_soon_date,
            "search_by": search_by,
            "search": search,
            "status_filter": status_filter,
        }
    )
@login_required
def asset_details(request, asset_id):

    asset = Asset.objects.filter(id=asset_id).first()

    if not asset:
        return render(request, "cssd/access_denied.html")

    allowed_assets = visible_assets_for_user(request.user)

    if not allowed_assets.filter(id=asset.id).exists():
        return render(request, "cssd/access_denied.html")

    return render(
        request,
        "cssd/asset_details.html",
        {
            "asset": asset
        }
    )

    return render(
        request,
        "cssd/asset_details.html",
        {"asset": asset}
    )



@login_required
def maintenance_entry(request):

    if is_engineer(request.user):
        return redirect("engineer_dashboard")

    if is_hospital_manager(request.user):
        return redirect("hospital_maintenance_dashboard")

    if is_admin(request.user):
        return redirect("asset_list")

    return redirect("clinic_dashboard")


@login_required
def back_to_dashboard(request):

    referer = request.META.get("HTTP_REFERER", "")

    cssd_paths = [
        "/cssd", "/new-request", "/get-template-items", "/return-to-clinic",
        "/clinic-pending-returns", "/clinic-confirm-details", "/confirm-by-clinic",
        "/close-request", "/print-request", "/all-requests", "/notifications",
        "/reports", "/my-requests", "/hospital-cssd-dashboard",
    ]

    maintenance_paths = [
        "/assets", "/maintenance", "/maintenance-requests", "/my-maintenance",
        "/pending-spare-parts", "/spare-parts-tracking", "/pm",
        "/engineer-dashboard", "/clinic-dashboard", "/clinic-assets",
        "/clinic-waiting-parts-assets", "/hospital-maintenance-dashboard",
    ]

    if any(path in referer for path in cssd_paths):
        if is_hospital_manager(request.user):
            return redirect("hospital_cssd_dashboard")
        return redirect("dashboard")

    if any(path in referer for path in maintenance_paths):
        return redirect("maintenance_entry")

    return redirect("system_selection")

@login_required
def report_fault(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)

    if request.method == "POST":
        fault_description = request.POST.get("fault_description")
        priority = request.POST.get("priority")

        maintenance_request = MaintenanceRequest.objects.create(
        asset=asset,
        reported_by=request.user,
        assigned_to=asset.location.engineers.first() if asset.location else None,
        fault_description=fault_description,
        priority=priority,
        status="OPEN"
)
        
        MaintenanceRequestTimeline.objects.create(
    maintenance_request=maintenance_request,
    action="Request Created",
    note=fault_description,
    created_by=request.user
)
        notify_event(
            title="New Maintenance Request",
            message=f"New fault reported for {asset.device_name} - {asset.location}",
            url=f"/maintenance-requests/{maintenance_request.id}/",
            target_groups=["ENGINEER"],
            users=[maintenance_request.assigned_to]
        )

        asset.status = "UNDER_MAINTENANCE"
        asset.save()

        return redirect("asset_details", asset_id=asset.id)

    return render(request, "cssd/report_fault.html", {
        "asset": asset
    })
def public_report_fault(request, asset_id):

    asset = get_object_or_404(Asset, id=asset_id)

    if request.method == "POST":

        reporter_name = request.POST.get("reporter_name", "").strip()
        fault_description = request.POST.get("fault_description", "").strip()
        priority = request.POST.get("priority", "NORMAL")

        if not reporter_name or not fault_description:
            return render(
                request,
                "cssd/public_report_fault.html",
                {
                    "asset": asset,
                    "error": "Please enter your full name and fault description."
                }
            )

        maintenance_request = MaintenanceRequest.objects.create(
            asset=asset,
            reported_by=None,
            external_reporter_name=reporter_name,
            request_source="QR",
            assigned_to=asset.location.engineers.first() if asset.location else None,
            fault_description=fault_description,
            priority=priority,
            status="OPEN"
        )

        MaintenanceRequestTimeline.objects.create(
            maintenance_request=maintenance_request,
            action="Request Created",
            note=fault_description,
            created_by=None
        )

        notify_event(
            title="New QR Fault Report",
            message=f"New QR fault report for {asset.device_name} - {asset.location}",
            url=f"/maintenance-requests/{maintenance_request.id}/",
            target_groups=["ENGINEER"],
            users=[maintenance_request.assigned_to]
        )

        if asset.location:
            notify_event(
                title="New Fault Report",
                message=f"New QR fault report for {asset.device_name} by {reporter_name}",
                url=f"/maintenance-requests/{maintenance_request.id}/",
                target_groups=[asset.location.group_type],
                users=list(asset.location.engineers.all())
            )

        asset.status = "UNDER_MAINTENANCE"
        asset.save()

        return render(
            request,
            "cssd/public_report_success.html",
            {
                "maintenance_request": maintenance_request
            }
        )

    return render(
        request,
        "cssd/public_report_fault.html",
        {
            "asset": asset
        }
    )
def asset_qr_access(request, asset_id):

    asset = get_object_or_404(Asset, id=asset_id)

    return render(
        request,
        "cssd/asset_qr_access.html",
        {
            "asset": asset
        }
    )

@login_required
def maintenance_requests(request):

    status = request.GET.get("status")
    source = request.GET.get("source")
    confirm_type = request.GET.get("confirm_type")
    approval = request.GET.get("approval")
    search_by = request.GET.get("search_by", "")
    search = request.GET.get("search", "").strip()

    requests = visible_maintenance_requests_for_user(request.user)

    if status:
        requests = requests.filter(status=status)

    if source:
        requests = requests.filter(request_source=source)

    if confirm_type == "service":
        requests = requests.filter(status="WAITING_CONFIRMATION", needs_spare_parts=False)

    if confirm_type == "spare":
        requests = requests.filter(status="WAITING_CONFIRMATION", spare_parts__is_installed=True).distinct()

    if approval == "pending":
        requests = requests.filter(status="CLOSED", report_approved=False)

    if search:
        if search_by == "request_number":
            requests = requests.filter(id__icontains=search)
        elif search_by == "serial_number":
            requests = requests.filter(asset__serial_number__icontains=search)
        elif search_by == "device_name":
            requests = requests.filter(asset__device_name__icontains=search)
        elif search_by == "engineer":
            requests = requests.filter(assigned_to__username__icontains=search)
        elif search_by == "status":
            requests = requests.filter(status__icontains=search)
        else:
            requests = requests.filter(asset__asset_number__icontains=search)

    requests = requests.order_by("-reported_at")

    return render(
        request,
        "cssd/maintenance_requests.html",
        {
            "requests": requests,
            "current_status": status,
            "source": source,
            "confirm_type": confirm_type,
            "approval": approval,
            "search_by": search_by,
            "search": search,
        }
    )

@login_required
def approve_report(request, request_id):

    if not is_maintenance_manager(request.user):
        return HttpResponseForbidden("Only Maintenance Manager can approve reports.")

    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id
    )

    maintenance_request.report_approved = True
    maintenance_request.report_rejected = False
    maintenance_request.report_approved_by = request.user
    maintenance_request.report_approved_at = timezone.now()
    maintenance_request.save()

    MaintenanceRequestTimeline.objects.create(
        maintenance_request=maintenance_request,
        action="Report Approved By Maintenance Manager",
        created_by=request.user
    )

    notify_event(
        title="Maintenance Report Approved",
        message=f"Report approved for {maintenance_request.asset.device_name}",
        url=f"/maintenance-requests/{maintenance_request.id}/",
        users=[maintenance_request.assigned_to, maintenance_request.reported_by]
    )

    messages.success(request, "Report approved successfully.")

    return redirect(
        "service_report",
        request_id=maintenance_request.id
    )

@login_required
def reject_report(request, request_id):

    if not is_maintenance_manager(request.user):
        return HttpResponseForbidden("Only Maintenance Manager can reject reports.")

    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id
    )

    maintenance_request.report_approved = False
    maintenance_request.report_rejected = True
    maintenance_request.report_approved_by = None
    maintenance_request.report_approved_at = None

    maintenance_request.status = "IN_PROGRESS"
    maintenance_request.closed_at = None

    maintenance_request.asset.status = "UNDER_MAINTENANCE"
    maintenance_request.asset.save()

    maintenance_request.save()

    MaintenanceRequestTimeline.objects.create(
        maintenance_request=maintenance_request,
        action="Report Rejected By Maintenance Manager",
        note="Report rejected and returned to engineer for rework.",
        created_by=request.user
    )

    notify_event(
        title="Maintenance Report Rejected",
        message=f"Report rejected for {maintenance_request.asset.device_name}. Returned to engineer.",
        url=f"/maintenance-requests/{maintenance_request.id}/",
        users=[maintenance_request.assigned_to]
    )

    messages.warning(
        request,
        "Report rejected. Request returned to engineer."
    )

    return redirect(
        "maintenance_request_details",
        request_id=maintenance_request.id
    )

@login_required
def maintenance_request_details(request, request_id):
    maintenance_request = get_object_or_404(
    visible_maintenance_requests_for_user(request.user),
    id=request_id
)

    return render(
        request,
        "cssd/maintenance_request_details.html",
        {
            "maintenance_request": maintenance_request,
            "engineers": User.objects.filter(groups__name="ENGINEER").distinct(),
            "can_start_inquiry": is_manager_or_hospital(request.user),
            "can_reply_inquiry": is_manager_or_hospital(request.user) or maintenance_request.inquiries.exists(),
        }
    )

@login_required
def start_maintenance_request(request, request_id):
    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id
    )

    maintenance_request.status = "IN_PROGRESS"
    maintenance_request.asset.status = "UNDER_MAINTENANCE"

    maintenance_request.save()
    MaintenanceRequestTimeline.objects.create(
    maintenance_request=maintenance_request,
    action="Engineer Started Work",
    created_by=request.user
)
    maintenance_request.asset.save()

    notify_event(
        title="Engineer Started Maintenance",
        message=f"Engineer started work for {maintenance_request.asset.device_name}",
        url=f"/maintenance-requests/{maintenance_request.id}/",
        target_groups=[maintenance_request.asset.location.group_type if maintenance_request.asset.location else None],
        users=[maintenance_request.assigned_to, maintenance_request.reported_by]
    )

    return redirect(
        "maintenance_request_details",
        request_id=maintenance_request.id
    )

@login_required
def home(request):
    return redirect("dashboard")


@login_required
def dashboard(request):



    requests_qs = visible_requests_for_user(request.user)

    total_requests = requests_qs.count()
    pending_requests = requests_qs.filter(status="SENT_TO_CSSD").count()
    received_requests = requests_qs.filter(status="RECEIVED_BY_CSSD").count()
    returned_requests = requests_qs.filter(status="RETURNED_TO_CLINIC").count()
    confirmed_requests = requests_qs.filter(status="CONFIRMED_BY_CLINIC").count()
    closed_requests = requests_qs.filter(status="CLOSED").count()
    latest_requests = requests_qs.order_by("-created_at")[:5]

    return render(request, "cssd/dashboard.html", {
    "total_requests": total_requests,
    "pending_requests": pending_requests,
    "received_requests": received_requests,
    "returned_requests": returned_requests,
    "confirmed_requests": confirmed_requests,
    "closed_requests": closed_requests,
    "latest_requests": latest_requests,

    "is_cssd_user": is_cssd(request.user),
    "is_admin_user": is_admin(request.user),
    "is_clinic_user": bool(user_location_groups(request.user)),
})

@login_required
def engineer_dashboard(request):

    assets = visible_assets_for_user(request.user)
    requests = visible_maintenance_requests_for_user(request.user)

    my_locations = request.user.assigned_locations.all()

    today = date.today()

    total_assets = assets.count()
    active_assets = assets.filter(status="ACTIVE").count()
    active_need_spare = assets.filter(status="ACTIVE_NEED_SPARE").count()
    out_of_service_assets = assets.filter(status="OUT_OF_SERVICE").count()

    total_requests = requests.count()

    open_requests = requests.filter(status="OPEN").count()
    in_progress = requests.filter(status="IN_PROGRESS").count()
    waiting_parts = requests.filter(status="WAITING_PARTS").count()
    waiting_confirmation = requests.filter(status="WAITING_CONFIRMATION").count()
    waiting_part_approval = requests.filter(status="WAITING_PART_APPROVAL").count()
    closed_requests = requests.filter(status="CLOSED").count()

   
    today = date.today()
    pm_due_date = today + timedelta(days=6)

    pm_due = assets.filter(
        next_pm_date__lte=pm_due_date
    ).exclude(
    next_pm_date__isnull=True
    ).count()

    completed_pm_month = PMHistory.objects.filter(
        asset__in=assets,
        status="CLOSED",
        performed_at__year=today.year,
        performed_at__month=today.month
    ).count()

    latest_requests = requests.order_by("-reported_at")[:10]
    latest_assets = assets.order_by("asset_number")[:10]

    return render(
        request,
        "cssd/engineer_dashboard.html",
        {
            "my_locations": my_locations,
            "latest_assets": latest_assets,
            "latest_requests": latest_requests,

            "total_assets": total_assets,
            "active_assets": active_assets,
            "active_need_spare": active_need_spare,
            "out_of_service_assets": out_of_service_assets,

            "total_requests": total_requests,
            "open_requests": open_requests,
            "in_progress": in_progress,
            "waiting_parts": waiting_parts,
            "waiting_part_approval": waiting_part_approval,
            "waiting_confirmation": waiting_confirmation,
            "closed_requests": closed_requests,

            "pm_due": pm_due,
            "completed_pm_month": completed_pm_month,
        }
    )
@login_required
def clinic_dashboard(request):

    assets = visible_assets_for_user(request.user)
    requests = visible_maintenance_requests_for_user(request.user)

    my_groups = user_location_groups(request.user)

    my_locations = Location.objects.filter(
        group_type__in=my_groups
    )

    total_assets = assets.count()
    total_requests = requests.count()

    open_requests = requests.filter(status="OPEN").count()
    in_progress = requests.filter(status="IN_PROGRESS").count()
    waiting_parts = requests.filter(status="WAITING_PARTS").count()
    waiting_part_approval = requests.filter(status="WAITING_PART_APPROVAL").count()
    waiting_parts_assets = assets.filter(status="WAITING_PARTS").count()
    waiting_confirmation = requests.filter(status="WAITING_CONFIRMATION").count()
    waiting_service_confirm = requests.filter(status="WAITING_CONFIRMATION", needs_spare_parts=False).count()
    waiting_spare_confirm = requests.filter(status="WAITING_CONFIRMATION", spare_parts__is_installed=True).distinct().count()
    closed_requests = requests.filter(status="CLOSED").count()


    latest_requests = requests.order_by("-reported_at")[:10]
    latest_assets = assets.order_by("asset_number")[:10]

    return render(
        request,
        "cssd/clinic_dashboard.html",
        {
            "my_locations": my_locations,
            "total_assets": total_assets,
            "total_requests": total_requests,
            "open_requests": open_requests,
            "in_progress": in_progress,
            "waiting_parts": waiting_parts,
            "waiting_parts_assets": waiting_parts_assets,
            "waiting_confirmation": waiting_confirmation,
            "closed_requests": closed_requests,
            "latest_requests": latest_requests,
            "latest_assets": latest_assets,
            "waiting_part_approval": waiting_part_approval,
            "waiting_service_confirm": waiting_service_confirm,
            "waiting_spare_confirm": waiting_spare_confirm,
        }
    )

@login_required
def new_request(request):
    form = NewCSSDRequestForm()

    if request.method == "POST":
        location_id = request.POST.get("location")
        procedure_note = request.POST.get("procedure", "")

        cssd_request = CSSDRequest.objects.create(
            location_id=location_id,
            procedure=procedure_note,
            created_by=request.user,
            status="SENT_TO_CSSD"
        )

        if not can_access_request(request.user, cssd_request):
            cssd_request.delete()
            return HttpResponseForbidden("You are not allowed to create request for this location.")

        used_templates = []

        for key, template_id in request.POST.items():
            if key.startswith("template_") and template_id:
                index = key.split("_")[1]
                template = get_object_or_404(CSSDTemplate, id=template_id)

                request_template = CSSDRequestTemplate.objects.create(
                    cssd_request=cssd_request,
                    template=template
                )

                used_templates.append(template.name)
                prefix = f"qty_{index}_"

                for qty_key, qty_value in request.POST.items():
                    if qty_key.startswith(prefix):
                        item_id = qty_key.replace(prefix, "")
                        quantity = int(qty_value or 0)

                        if quantity > 0:
                            item = get_object_or_404(CSSDTemplateItem, id=item_id)

                            CSSDRequestItem.objects.create(
                                cssd_request=cssd_request,
                                cssd_request_template=request_template,
                                instrument_name=item.instrument_name,
                                quantity_sent=quantity,
                                is_manual=False
                            )

        manual_names = request.POST.getlist("manual_name[]")
        manual_quantities = request.POST.getlist("manual_qty[]")

        for name, qty in zip(manual_names, manual_quantities):
            name = name.strip()
            quantity = int(qty or 0)

            if name and quantity > 0:
                CSSDRequestItem.objects.create(
                    cssd_request=cssd_request,
                    cssd_request_template=None,
                    instrument_name=name,
                    quantity_sent=quantity,
                    is_manual=True
                )

        notify_event(
            title="New CSSD Request",
            message=f"New request from {cssd_request.location.name}: {', '.join(used_templates)}",
            cssd_request=cssd_request,
            url=f"/cssd-request/{cssd_request.id}/",
            target_groups=["CSSD"]
        )

        return redirect("cssd_pending_requests")

    templates = CSSDTemplate.objects.all()

    return render(request, "cssd/new_request.html", {
        "form": form,
        "templates": templates,
    })

from datetime import date
from dateutil.relativedelta import relativedelta

@login_required
def perform_pm(request, asset_id):

    asset = get_object_or_404(Asset, id=asset_id)
    today = date.today()

    pm_due_date = today + timedelta(days=4)

    if asset.next_pm_date and asset.next_pm_date > pm_due_date:
      return redirect("asset_details", asset_id=asset.id)

    already_done = PMHistory.objects.filter(
    asset=asset,
    performed_at__date=today
).exclude(
    status="REJECTED"
).exists()
    


    if already_done:
        return render(request, "cssd/perform_pm.html", {
            "asset": asset,
            "pm_items": asset.pm_template.items.all().order_by("sort_order") if asset.pm_template else [],
            "error": "PPM already performed today for this asset."
        })

    if not asset.pm_template:
        return render(request, "cssd/perform_pm.html", {
            "asset": asset,
            "pm_items": [],
            "error": "No PM template assigned to this asset."
        })

    pm_items = asset.pm_template.items.all().order_by("sort_order")

    if request.method == "POST":

        ppm_sticker_applied = request.POST.get("ppm_sticker_applied")

        if not ppm_sticker_applied:
            return render(request, "cssd/perform_pm.html", {
                "asset": asset,
                "pm_items": pm_items,
                "error": "Please confirm that PPM sticker has been applied."
            })

        failed_items = []
        spare_parts_notes = []

        for item in pm_items:

            check_value = request.POST.get(
                f"check_{item.id}",
                "OK"
            )

            if check_value == "NOT_OK":

                spare_parts = (
                    request.POST.getlist(f"spare_part_{item.id}")
                    or request.POST.getlist(f"spare_part_{item.id}[]")
                )

                quantities = (
                    request.POST.getlist(f"spare_qty_{item.id}")
                    or request.POST.getlist(f"spare_qty_{item.id}[]")
                )

                valid_parts = []

                for part_name, qty in zip(spare_parts, quantities):
                    part_name = part_name.strip()

                    try:
                        qty = int(qty)
                    except:
                        qty = 1

                    if part_name and qty > 0:
                        valid_parts.append({
                            "part": part_name,
                            "qty": qty
                        })

                if not valid_parts:
                    return render(request, "cssd/perform_pm.html", {
                        "asset": asset,
                        "pm_items": pm_items,
                        "error": f"Please enter spare part needed for {item.system} - {item.component}."
                    })

                failed_items.append(
                    f"{item.system} - {item.component}"
                )

                for part in valid_parts:
                    spare_parts_notes.append({
                        "item": f"{item.system} - {item.component}",
                        "part": part["part"],
                        "qty": part["qty"],
                    })

        asset.last_pm_date = today
        asset.next_pm_date = today + relativedelta(months=6)
        asset.save()

        if failed_items:
            notes = (
                "PPM Completed with spare parts required. "
                + " | ".join([
                    f"{p['item']}: {p['part']} x {p['qty']}"
                    for p in spare_parts_notes
                ])
            )
        else:
            notes = "PPM Checklist Completed - All items OK"

        pm_history = PMHistory.objects.create(
            asset=asset,
            performed_by=request.user,
            notes=notes,
            next_pm_date=asset.next_pm_date,
            status="WAITING_CONFIRMATION"
)
        target_group = None

        if asset.location:
            target_group = asset.location.group_type

        notify_event(
    title="PPM Waiting Clinic Confirmation",
    message=f"PPM for {asset.asset_number} is waiting for clinic confirmation.",
    url=f"/pm-review/{pm_history.id}/",
    target_groups=[target_group] if target_group else [],
)
        for item in pm_items:

            check_value = request.POST.get(
                f"check_{item.id}",
                "OK"
    )

            spare_parts = (
                request.POST.getlist(f"spare_part_{item.id}")
                or request.POST.getlist(f"spare_part_{item.id}[]")
    )

            quantities = (
                request.POST.getlist(f"spare_qty_{item.id}")
                 or request.POST.getlist(f"spare_qty_{item.id}[]")
    )

            part_name = ""
            qty = 0

            if spare_parts:
                part_name = spare_parts[0].strip()

            if quantities:
                try:
                    qty = int(quantities[0])
                except:
                    qty = 0

            PMHistoryItem.objects.create(
                pm_history=pm_history,
                system=item.system,
                component=item.component,
                inspection_points=item.inspection_points,
                result=check_value,
                requested_spare_part=part_name,
                requested_quantity=qty
    )

            if failed_items:
             maintenance_request = MaintenanceRequest.objects.create(
                asset=asset,
                reported_by=request.user,
                assigned_to=asset.location.engineers.first() if asset.location else None,
                fault_description=(
                    "PPM Spare Parts Required - "
                    + " | ".join(failed_items)
                ),
                priority="NORMAL",
                status="WAITING_PARTS",
                needs_spare_parts=True,
                work_done="SOURCE:PM | PPM completed. Spare parts required."
            )

            for part in spare_parts_notes:
                MaintenanceSparePart.objects.create(
                    maintenance_request=maintenance_request,
                    requested_part_name=part["part"],
                    requested_quantity=part["qty"]
                )

        return redirect("asset_details", asset_id=asset.id)

    return render(request, "cssd/perform_pm.html", {
        "asset": asset,
        "pm_items": pm_items
    })

@login_required
def my_maintenance_requests(request):

    if request.user.is_superuser:

        requests = MaintenanceRequest.objects.extra(
            select={
                "status_order": """
                CASE
                    WHEN status='WAITING_PARTS' THEN 1
                    WHEN status='OPEN' THEN 2
                    WHEN status='IN_PROGRESS' THEN 3
                    WHEN status='CLOSED' THEN 4
                END
                """
            }
        ).order_by("status_order", "-reported_at")

    else:

        requests = MaintenanceRequest.objects.filter(
            asset__location__engineers=request.user
        ).extra(
            select={
                "status_order": """
                CASE
                    WHEN status='WAITING_PARTS' THEN 1
                    WHEN status='OPEN' THEN 2
                    WHEN status='IN_PROGRESS' THEN 3
                    WHEN status='CLOSED' THEN 4
                END
                """
            }
        ).order_by("status_order", "-reported_at").distinct()

    return render(
        request,
        "cssd/my_maintenance_requests.html",
        {
            "requests": requests
        }
    )

@login_required
def pending_spare_parts(request):
    requests = MaintenanceRequest.objects.filter(
        status="WAITING_PARTS"
    ).order_by("-reported_at")

    return render(
        request,
        "cssd/pending_spare_parts.html",
        {"requests": requests}
    )

@login_required
def part_received(request, req_id):

    req = get_object_or_404(
        MaintenanceRequest,
        id=req_id
    )

    req.status = "IN_PROGRESS"
    req.save()

    notify_event(
        title="Spare Parts Received",
        message=f"Spare parts received for {req.asset.device_name}",
        url=f"/maintenance-requests/{req.id}/",
        users=[req.assigned_to, req.reported_by]
    )

    return redirect(
        "complete_maintenance_request",
        request_id=req.id
    )

@login_required
def system_selection(request):

    if is_engineer(request.user):
        return redirect("engineer_dashboard")

    if is_medical_store_manager(request.user):
        return redirect("medical_store:store_dashboard")

    return render(
        request,
        "cssd/system_selection.html",
        {
            "is_hospital_manager_user": is_hospital_manager(request.user),
            "show_medical_store": not is_engineer(request.user),
            "show_management_center": is_maintenance_manager(request.user),
            "show_ai_assistant": is_maintenance_manager(request.user) or is_hospital_manager(request.user),
        }
    )


@login_required
def management_center(request):
    if not is_maintenance_manager(request.user):
        return HttpResponseForbidden("You are not allowed to access Management Center.")

    stats = {
        "users": User.objects.count(),
        "locations": Location.objects.count(),
        "assets": Asset.objects.count(),
        "pm_templates": PMHistory.objects.count(),
    }

    return render(request, "cssd/management_center.html", {"stats": stats})


@login_required
def ai_assistant(request):
    if not (is_maintenance_manager(request.user) or is_hospital_manager(request.user)):
        return HttpResponseForbidden("You are not allowed to access AI Assistant.")

    quick_stats = {
        "assets": Asset.objects.count(),
        "open_maintenance": MaintenanceRequest.objects.exclude(status="CLOSED").count(),
        "closed_maintenance": MaintenanceRequest.objects.filter(status="CLOSED").count(),
        "cssd_open": CSSDRequest.objects.exclude(status="CLOSED").count(),
    }

    return render(request, "cssd/ai_assistant.html", {"quick_stats": quick_stats})

from django.utils import timezone

@login_required
def pm_dashboard(request):

    today = date.today()
    pm_due_date = today + timedelta(days=4)

    assets = Asset.objects.filter(
        next_pm_date__lte=pm_due_date
    ).exclude(
        next_pm_date__isnull=True
    ).order_by("next_pm_date")

    return render(
        request,
        "cssd/pm_dashboard.html",
        {
            "assets": assets,
            "today": today,
            "pm_due_date": pm_due_date,
        }
    )

@login_required
def complete_maintenance_request(request, request_id):
    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id
    )

    if request.method == "POST":

        work_done = request.POST.get("work_done", "")
        action = request.POST.get("action")
        after_spare_part_work = request.POST.get(
            "after_spare_part_work",
            ""
        )

        if action in ["need_spare_part_working","need_spare_part_stopped","repaired_without_spare"]:
            maintenance_request.work_done = work_done

        if action in ["need_spare_part_working", "need_spare_part_stopped"]:

            part_names = request.POST.getlist("requested_part_name[]")
            quantities = request.POST.getlist("requested_quantity[]")

            valid_parts = []

            for name, qty in zip(part_names, quantities):
                name = name.strip()

                try:
                    qty = int(qty)
                except:
                    qty = 0

                if name and qty > 0:
                    valid_parts.append((name, qty))

            if not valid_parts:
                return render(
                    request,
                    "cssd/complete_maintenance_request.html",
                    {
                        "maintenance_request": maintenance_request,
                        "error": "Please enter at least one spare part with quantity."
                    }
                )

            maintenance_request.spare_parts.all().delete()

            for name, qty in valid_parts:
                MaintenanceSparePart.objects.create(
                    maintenance_request=maintenance_request,
                    requested_part_name=name,
                    requested_quantity=qty
                )

            maintenance_request.needs_spare_parts = True
            maintenance_request.status = "WAITING_PART_APPROVAL"
            maintenance_request.closed_at = None
            maintenance_request.report_approved = False
            maintenance_request.report_rejected = False
            maintenance_request.report_approved_by = None
            maintenance_request.report_approved_at = None
            maintenance_request.report_manager_comment = ""

            if action == "need_spare_part_working":
                maintenance_request.asset.status = "ACTIVE_NEED_SPARE"

            elif action == "need_spare_part_stopped":
                maintenance_request.asset.status = "OUT_OF_SERVICE"

            MaintenanceRequestTimeline.objects.create(
                maintenance_request=maintenance_request,
                action="Waiting Clinic Approval For Spare Parts",
                note=work_done,
                created_by=request.user
            )

            if maintenance_request.asset.location:
              notify_event(
                    title="Spare Parts Approval Required",
                    message=f"Spare parts approval required for {maintenance_request.asset.device_name}",
                    url=f"/maintenance-requests/{maintenance_request.id}/",
                    target_groups=[maintenance_request.asset.location.group_type],
                    users=list(maintenance_request.asset.location.engineers.all())
    )
            

        elif action == "spare_part_installed":\

            spare_parts = maintenance_request.spare_parts.all()

            if not spare_parts.exists():
                return render(
                    request,
                    "cssd/complete_maintenance_request.html",
                    {
                        "maintenance_request": maintenance_request,
                        "error": "No requested spare parts found."
                    }
                )

            all_installed = True

            for part in spare_parts:
                installed_name = request.POST.get(
                    f"installed_part_name_{part.id}",
                    ""
                ).strip()

                installed_qty = request.POST.get(
                    f"installed_quantity_{part.id}",
                    "0"
                )

                try:
                    installed_qty = int(installed_qty)
                except:
                    installed_qty = 0

                if not installed_name or installed_qty < part.requested_quantity:
                    all_installed = False

                part.installed_part_name = installed_name
                part.installed_quantity = installed_qty
                part.save()

            if not all_installed:
                return render(
                    request,
                    "cssd/complete_maintenance_request.html",
                    {
                        "maintenance_request": maintenance_request,
                        "error": "Please install all requested spare parts with the required quantities."
                    }
                )

            maintenance_request.after_spare_part_work = after_spare_part_work
            maintenance_request.needs_spare_parts = False
            maintenance_request.status = "WAITING_CONFIRMATION"
            maintenance_request.closed_at = None
            maintenance_request.report_approved = False
            maintenance_request.report_rejected = False
            maintenance_request.report_approved_by = None
            maintenance_request.report_approved_at = None
            maintenance_request.report_manager_comment = ""
            set_asset_status_after_repair(
    maintenance_request.asset
)

            MaintenanceRequestTimeline.objects.create(
                maintenance_request=maintenance_request,
                action="Engineer Completed Work",
                note=after_spare_part_work,
                created_by=request.user
            )

            if maintenance_request.asset.location:
                notify_event(
                title="Repair Waiting Confirmation",
                message=f"Repair completed for {maintenance_request.asset.device_name}. Please confirm.",
                url=f"/maintenance-requests/{maintenance_request.id}/",
                target_groups=[maintenance_request.asset.location.group_type]
    )

        elif action == "repaired_without_spare":

            maintenance_request.status = "WAITING_CONFIRMATION"
            maintenance_request.closed_at = None
            set_asset_status_after_repair(
    maintenance_request.asset
)

            MaintenanceRequestTimeline.objects.create(
                maintenance_request=maintenance_request,
                action="Engineer Completed Work",
                note=work_done,
                created_by=request.user
            )

            if maintenance_request.asset.location:
                notify_event(
                title="Repair Waiting Confirmation",
                message=f"Repair completed for {maintenance_request.asset.device_name}. Please confirm.",
                url=f"/maintenance-requests/{maintenance_request.id}/",
                target_groups=[maintenance_request.asset.location.group_type]
    )

        else:
            return render(
                request,
                "cssd/complete_maintenance_request.html",
                {
                    "maintenance_request": maintenance_request,
                    "error": "Please select action."
                }
            )

        maintenance_request.asset.save()
        maintenance_request.save()

        return redirect(
            "maintenance_request_details",
            request_id=maintenance_request.id
        )

    return render(
        request,
        "cssd/complete_maintenance_request.html",
        {
            "maintenance_request": maintenance_request
        }
    )
@login_required
def clinic_confirm_maintenance(request, request_id):

    maintenance_request = get_object_or_404(
        visible_maintenance_requests_for_user(request.user),
        id=request_id,
        status="WAITING_CONFIRMATION"
    )

    if request.method == "POST":

        action = request.POST.get("action")
        note = request.POST.get("note", "").strip()

        maintenance_request.confirmed_by = request.user
        maintenance_request.confirmed_at = timezone.now()

        if action == "fixed":
            MaintenanceRequestTimeline.objects.create(
            maintenance_request=maintenance_request,
            action="Clinic Confirmed & Request Closed",
            note=note,
            created_by=request.user
)
            
            notify_event(
                title="Repair Confirmed",
                message=f"Clinic confirmed repair for {maintenance_request.asset.device_name}",
                url=f"/maintenance-requests/{maintenance_request.id}/",
                target_groups=["ENGINEER"],
                users=[maintenance_request.assigned_to]
)    
            maintenance_request.clinic_feedback = note
            maintenance_request.status = "CLOSED"
            maintenance_request.closed_at = timezone.now()
            set_asset_status_after_repair(
    maintenance_request.asset
)

        elif action == "not_fixed":

            if not note:
                return render(
                    request,
                    "cssd/clinic_confirm_maintenance.html",
                    {
                        "maintenance_request": maintenance_request,
                        "error": "Please write why the device is still not working."
                    }
                )

            maintenance_request.clinic_feedback = note
            MaintenanceRequestTimeline.objects.create(
            maintenance_request=maintenance_request,
            action="Clinic Rejected Repair",
            note=note,
            created_by=request.user
)
            notify_event(
                    title="Repair Rejected",
                    message=f"Clinic rejected repair for {maintenance_request.asset.device_name}",
                    url=f"/maintenance-requests/{maintenance_request.id}/",
                    target_groups=["ENGINEER"],
                    users=[maintenance_request.assigned_to]
)
                
            maintenance_request.status = "OPEN"
            maintenance_request.closed_at = None
            maintenance_request.asset.status = "UNDER_MAINTENANCE"

        maintenance_request.asset.save()
        maintenance_request.save()

        return redirect(
            "maintenance_request_details",
            request_id=maintenance_request.id
        )

    return render(
        request,
        "cssd/clinic_confirm_maintenance.html",
        {
            "maintenance_request": maintenance_request
        }
    )

@login_required
def spare_parts_tracking(request):

    spare_parts = MaintenanceSparePart.objects.select_related(
        "maintenance_request",
        "maintenance_request__asset",
        "maintenance_request__assigned_to"
    ).order_by("-created_at")

    return render(
        request,
        "cssd/spare_parts_tracking.html",
        {
            "spare_parts": spare_parts
        }
    )

@login_required
def get_template_items(request, template_id):
    items = CSSDTemplateItem.objects.filter(
        template_id=template_id
    ).order_by("sort_order").values("id", "instrument_name")

    return JsonResponse(list(items), safe=False)


@login_required
def cssd_pending_requests(request):
    requests = visible_requests_for_user(request.user).filter(
        status="SENT_TO_CSSD"
    ).order_by("-created_at")

    return render(request, "cssd/cssd_pending.html", {"requests": requests})


@login_required
def cssd_request_details(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to access this request.")

    if request.method == "POST":
        if not (is_admin(request.user) or is_cssd(request.user)):
            return HttpResponseForbidden("Only CSSD can receive requests.")

        for item in cssd_request.items.all():
            received_qty = request.POST.get(f"received_{item.id}", 0)
            comment = request.POST.get(f"comment_{item.id}", "")

            item.quantity_received_by_cssd = int(received_qty or 0)
            item.remarks = comment
            item.save()

        cssd_request.status = "RECEIVED_BY_CSSD"
        cssd_request.received_by = request.user
        cssd_request.received_at = timezone.now()
        cssd_request.save()

        notify_event(
            title="CSSD Received Request",
            message=f"CSSD received request #{cssd_request.id}",
            cssd_request=cssd_request,
            url=f"/cssd-request/{cssd_request.id}/",
            target_groups=[cssd_request.location.group_type],
            users=[cssd_request.created_by]
)

        return redirect("cssd_pending_requests")

    return render(request, "cssd/request_details.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
    })

@login_required
def clinic_assets(request):

    assets = visible_assets_for_user(request.user)

    status = request.GET.get("status") or request.GET.get("current_status")
    search_by = request.GET.get("search_by", "asset_number")
    search = request.GET.get("search", "").strip()

    if status:
        assets = assets.filter(status=status)

    if search:
        if search_by == "serial_number":
            assets = assets.filter(serial_number__icontains=search)
        elif search_by == "device_name":
            assets = assets.filter(device_name__icontains=search)
        elif search_by == "location":
            assets = assets.filter(location__name__icontains=search)
        elif search_by == "status":
            assets = assets.filter(status__icontains=search)
        else:
            assets = assets.filter(asset_number__icontains=search)

    assets = assets.order_by("asset_number")

    return render(
        request,
        "cssd/clinic_assets.html",
        {
            "assets": assets,
            "current_status": status,
            "status": status,
            "search_by": search_by,
            "search": search,
        }
    )

@login_required
def cssd_received_requests(request):
    requests = visible_requests_for_user(request.user).filter(
        status="RECEIVED_BY_CSSD"
    ).order_by("-created_at")

    return render(request, "cssd/cssd_received.html", {"requests": requests})


@login_required
def return_to_clinic(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to access this request.")

    if request.method == "POST":
        if not (is_admin(request.user) or is_cssd(request.user)):
            return HttpResponseForbidden("Only CSSD can return requests.")

        for item in cssd_request.items.all():
            returned_qty = request.POST.get(f"returned_{item.id}", 0)
            item.quantity_returned = int(returned_qty or 0)
            item.save()

        cssd_request.status = "RETURNED_TO_CLINIC"
        cssd_request.returned_by = request.user
        cssd_request.returned_at = timezone.now()
        cssd_request.save()

        notify_event(
            title="Instruments Returned",
            message=f"CSSD returned request #{cssd_request.id} to clinic",
            cssd_request=cssd_request,
            url=f"/clinic-confirm-details/{cssd_request.id}/",
            target_groups=[cssd_request.location.group_type],
            users=[cssd_request.created_by]
)

        return redirect("cssd_received_requests")

    return render(request, "cssd/return_to_clinic.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
    })


@login_required
def clinic_pending_returns(request):
    requests = visible_requests_for_user(request.user).filter(
        status="RETURNED_TO_CLINIC"
    ).order_by("-created_at")

    return render(request, "cssd/clinic_pending_returns.html", {"requests": requests})

@login_required
def clinic_waiting_parts_assets(request):

    assets = visible_assets_for_user(request.user).filter(
        status="WAITING_PARTS"
    )

    return render(
        request,
        "cssd/clinic_waiting_parts_assets.html",
        {
            "assets": assets,
        }
    )

@login_required
def confirm_by_clinic(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to access this request.")

    if is_cssd(request.user) and not is_admin(request.user):
        return HttpResponseForbidden("CSSD cannot confirm clinic receipt.")

    cssd_request.status = "CLOSED"
    cssd_request.closed_by = request.user
    cssd_request.closed_at = timezone.now()
    cssd_request.save()

    notify_event(
        title="Clinic Confirmed Receipt",
        message=f"Clinic confirmed receiving request #{cssd_request.id}",
        cssd_request=cssd_request,
        url=f"/cssd-request/{cssd_request.id}/",
        target_groups=["CSSD"]
)

    return redirect("clinic_pending_returns")


@login_required
def close_request(request, request_id):
    if not is_admin(request.user):
        return HttpResponseForbidden("Only Admin can close requests.")

    cssd_request = get_object_or_404(CSSDRequest, id=request_id)
    cssd_request.status = "CLOSED"
    cssd_request.closed_by = request.user
    cssd_request.closed_at = timezone.now()
    cssd_request.save()

    return redirect("clinic_pending_returns")


@login_required
def print_request(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to print this request.")

    request_url = request.build_absolute_uri(
        f"/cssd-request/{cssd_request.id}/"
    )

    qr = qrcode.make(request_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    qr_code = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "cssd/print_request.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
        "qr_code": qr_code,
        "request_url": request_url,
    })
@login_required
def all_requests(request):
    requests = visible_requests_for_user(request.user)

    search = request.GET.get("search", "").strip()
    search_by = request.GET.get("search_by", "")
    status = request.GET.get("status", "")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")

    if search:
        if search_by == "request_number":
            requests = requests.filter(id__icontains=search)
        elif search_by == "created_by":
            requests = requests.filter(created_by__username__icontains=search)
        elif search_by == "status":
            requests = requests.filter(status__icontains=search)
        else:
            requests = requests.filter(location__name__icontains=search)

    if status:
        requests = requests.filter(status=status)

    if from_date:
        parsed_from = parse_date(from_date)
        if parsed_from:
            requests = requests.filter(created_at__date__gte=parsed_from)

    if to_date:
        parsed_to = parse_date(to_date)
        if parsed_to:
            requests = requests.filter(created_at__date__lte=parsed_to)

    requests = requests.order_by("-created_at")

    return render(request, "cssd/all_requests.html", {
        "requests": requests,
        "search": search,
        "search_by": search_by,
        "status": status,
        "from_date": from_date,
        "to_date": to_date,
    })
@login_required
def reports(request):

    requests_qs = visible_requests_for_user(request.user)

    total_requests = requests_qs.count()
    pending_requests = requests_qs.filter(status="SENT_TO_CSSD").count()
    received_requests = requests_qs.filter(status="RECEIVED_BY_CSSD").count()
    returned_requests = requests_qs.filter(status="RETURNED_TO_CLINIC").count()
    closed_requests = requests_qs.filter(status="CLOSED").count()

    locations = requests_qs.values(
        "location__name"
    ).annotate(
        total=Count("id")
    ).order_by("-total")

    users = requests_qs.values(
        "created_by__username"
    ).annotate(
        total=Count("id")
    ).order_by("-total")

    return render(request, "cssd/reports.html", {
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "received_requests": received_requests,
        "returned_requests": returned_requests,
        "closed_requests": closed_requests,
        "locations": locations,
        "users": users,
    })
@login_required
def my_requests(request):
    requests = CSSDRequest.objects.filter(
        created_by=request.user
    ).order_by("-created_at")

    return render(request, "cssd/my_requests.html", {
        "requests": requests
    })


@login_required
def clinic_confirm_details(request, request_id):
    cssd_request = get_object_or_404(CSSDRequest, id=request_id)

    if not can_access_request(request.user, cssd_request):
        return HttpResponseForbidden("You are not allowed to access this request.")

    if cssd_request.status != "RETURNED_TO_CLINIC":
        return HttpResponseForbidden("This request is not ready for clinic confirmation.")

    if is_cssd(request.user) and not is_admin(request.user):
        return HttpResponseForbidden("CSSD cannot confirm clinic receipt.")

    if request.method == "POST":
        for item in cssd_request.items.all():
            received_qty = request.POST.get(f"received_by_clinic_{item.id}")
            clinic_comment = request.POST.get(f"clinic_comment_{item.id}", "")
            if received_qty not in (None, ""):
                try:
                    item.quantity_received_by_clinic = max(0, int(received_qty))
                except ValueError:
                    item.quantity_received_by_clinic = item.quantity_returned
            else:
                item.quantity_received_by_clinic = item.quantity_returned
            item.clinic_comment = clinic_comment
            item.save()

        cssd_request.status = "CLOSED"
        cssd_request.closed_by = request.user
        cssd_request.closed_at = timezone.now()
        cssd_request.save()

        notify_event(
            title="Clinic Confirmed Receipt",
            message=f"Clinic confirmed receiving request #{cssd_request.id}",
            cssd_request=cssd_request,
            url=f"/cssd-request/{cssd_request.id}/",
            target_groups=["CSSD"]
        )

        return redirect("clinic_pending_returns")

    return render(request, "cssd/clinic_confirm_details.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
    })

@login_required
def service_report(request, request_id):

    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id
    )

    if not maintenance_request.report_approved:
        messages.warning(
            request,
            "This report is pending Maintenance Manager approval."
        )

        return redirect(
            "maintenance_request_details",
            request_id=request_id
        )

    spare_parts = maintenance_request.spare_parts.all()
    timeline = maintenance_request.timeline.all().order_by("created_at")

    return render(
        request,
        "cssd/service_report.html",
        {
            "maintenance_request": maintenance_request,
            "spare_parts": spare_parts,
            "timeline": timeline,
            "engineer_final_date": last_timeline_date(maintenance_request, ["Engineer Completed Work", "Waiting Clinic Approval For Spare Parts"]),
        }
    )


@login_required
def add_maintenance_inquiry(request, request_id):
    maintenance_request = get_object_or_404(
        visible_maintenance_requests_for_user(request.user),
        id=request_id
    )

    if request.method != "POST":
        return redirect("maintenance_request_details", request_id=request_id)

    message = request.POST.get("message", "").strip()
    if message:
        if not is_manager_or_hospital(request.user) and not maintenance_request.inquiries.exists():
            messages.warning(request, "Only Maintenance Manager or Hospital Manager can start a new inquiry.")
            return redirect("maintenance_request_details", request_id=request_id)

        InquiryMessage.objects.create(
            maintenance_request=maintenance_request,
            message=message,
            created_by=request.user
        )
        MaintenanceRequestTimeline.objects.create(
            maintenance_request=maintenance_request,
            action="Inquiry Added",
            note=message,
            created_by=request.user
        )
        users = [maintenance_request.assigned_to, maintenance_request.reported_by]
        if request.user == maintenance_request.assigned_to:
            users.append(maintenance_request.reported_by)
        notify_event(
            title="New Inquiry Message",
            message=f"New inquiry message for MR #{maintenance_request.id}",
            url=f"/maintenance-requests/{maintenance_request.id}/",
            users=users,
            target_groups=[maintenance_request.asset.location.group_type if maintenance_request.asset.location else None]
        )

    return redirect("maintenance_request_details", request_id=request_id)


@login_required
def add_maintenance_attachment(request, request_id):
    maintenance_request = get_object_or_404(
        visible_maintenance_requests_for_user(request.user),
        id=request_id
    )

    if request.method == "POST" and request.FILES.get("file"):
        attachment = RequestAttachment.objects.create(
            maintenance_request=maintenance_request,
            file=request.FILES["file"],
            description=request.POST.get("description", "").strip(),
            uploaded_by=request.user
        )
        MaintenanceRequestTimeline.objects.create(
            maintenance_request=maintenance_request,
            action="Attachment Uploaded",
            note=attachment.description or attachment.file.name,
            created_by=request.user
        )

    return redirect("maintenance_request_details", request_id=request_id)


@login_required
def reassign_maintenance_request(request, request_id):
    if not is_maintenance_manager(request.user):
        return HttpResponseForbidden("Only Maintenance Manager can reassign requests.")

    maintenance_request = get_object_or_404(MaintenanceRequest, id=request_id)

    if request.method == "POST":
        engineer_id = request.POST.get("engineer")
        old_engineer = maintenance_request.assigned_to
        new_engineer = get_object_or_404(User, id=engineer_id)
        maintenance_request.assigned_to = new_engineer
        maintenance_request.save(update_fields=["assigned_to"])
        MaintenanceRequestTimeline.objects.create(
            maintenance_request=maintenance_request,
            action="Engineer Reassigned",
            note=f"From {old_engineer or '-'} to {new_engineer}",
            created_by=request.user
        )
        notify_event(
            title="Request Reassigned",
            message=f"MR #{maintenance_request.id} assigned to {new_engineer}",
            url=f"/maintenance-requests/{maintenance_request.id}/",
            users=[old_engineer, new_engineer]
        )

    return redirect("maintenance_request_details", request_id=request_id)


@login_required
def manager_take_over_request(request, request_id):
    if not is_maintenance_manager(request.user):
        return HttpResponseForbidden("Only Maintenance Manager can take over requests.")

    maintenance_request = get_object_or_404(MaintenanceRequest, id=request_id)
    maintenance_request.assigned_to = request.user
    maintenance_request.status = "IN_PROGRESS"
    maintenance_request.asset.status = "UNDER_MAINTENANCE"
    maintenance_request.asset.save()
    maintenance_request.save()
    MaintenanceRequestTimeline.objects.create(
        maintenance_request=maintenance_request,
        action="Maintenance Manager Took Over Request",
        created_by=request.user
    )
    return redirect("complete_maintenance_request", request_id=request_id)


@login_required
def hospital_maintenance_dashboard(request):
    if not is_hospital_manager(request.user) and not is_maintenance_manager(request.user):
        return HttpResponseForbidden("Hospital Manager access only.")

    today = date.today()
    requests = MaintenanceRequest.objects.all()
    assets = Asset.objects.all()
    kpis = calculate_maintenance_kpis(requests, assets)
    context = {
        "total_assets": assets.count(),
        "total_requests": requests.count(),
        "closed_requests": requests.filter(status="CLOSED").count(),
        "open_requests": requests.exclude(status="CLOSED").count(),
        "in_progress": requests.filter(status="IN_PROGRESS").count(),
        "out_of_service": assets.filter(status="OUT_OF_SERVICE").count(),
        "waiting_spare_parts": requests.filter(status="WAITING_PARTS").count(),
        "pending_approval": requests.filter(status="CLOSED", report_approved=False).count(),
        "pm_due": assets.filter(next_pm_date__lte=today + timedelta(days=4)).exclude(next_pm_date__isnull=True).count(),
        "qr_reports": requests.filter(request_source="QR").count(),
        "availability": kpis["availability"],
        "mttr_days": kpis["mttr_days"],
        "mtbf_days": kpis["mtbf_days"],
    }
    return render(request, "cssd/hospital_maintenance_dashboard.html", context)


@login_required
def hospital_cssd_dashboard(request):
    if not is_hospital_manager(request.user) and not is_maintenance_manager(request.user):
        return HttpResponseForbidden("Hospital Manager access only.")

    today = timezone.localdate()
    requests = CSSDRequest.objects.all()
    context = {
        "open_requests": requests.exclude(status="CLOSED").count(),
        "sent": requests.filter(status="SENT_TO_CSSD").count(),
        "received": requests.filter(status="RECEIVED_BY_CSSD").count(),
        "returned": requests.filter(status="RETURNED_TO_CLINIC").count(),
        "closed_today": requests.filter(status="CLOSED", closed_at__date=today).count(),
        "total_requests": requests.count(),
    }
    return render(request, "cssd/hospital_cssd_dashboard.html", context)


@login_required
def locations_overview(request):
    if not is_maintenance_manager(request.user) and not is_hospital_manager(request.user):
        return HttpResponseForbidden("Manager access only.")

    locations = Location.objects.all().order_by("name")
    rows = []
    for location in locations:
        assets = Asset.objects.filter(location=location)
        requests = MaintenanceRequest.objects.filter(asset__location=location)
        kpis = calculate_maintenance_kpis(requests, assets)
        rows.append({
            "location": location,
            "assets_count": assets.count(),
            "open_requests": requests.exclude(status="CLOSED").count(),
            "availability": kpis["availability"],
            "mttr_days": kpis["mttr_days"],
            "mtbf_days": kpis["mtbf_days"],
        })

    return render(request, "cssd/locations_overview.html", {"rows": rows})


@login_required
def location_assets(request, location_id):
    if not is_maintenance_manager(request.user) and not is_hospital_manager(request.user):
        return HttpResponseForbidden("Manager access only.")

    location = get_object_or_404(Location, id=location_id)
    assets = Asset.objects.filter(location=location).order_by("asset_number")
    requests = MaintenanceRequest.objects.filter(asset__location=location)
    kpis = calculate_maintenance_kpis(requests, assets)

    return render(request, "cssd/location_assets.html", {
        "location": location,
        "assets": assets,
        **kpis,
        "open_requests": requests.exclude(status="CLOSED").count(),
    })


@login_required
def maintenance_kpi_detail(request, metric):
    if not is_maintenance_manager(request.user) and not is_hospital_manager(request.user):
        return HttpResponseForbidden("Manager access only.")

    from_date = parse_date(request.GET.get("from_date", "") or "")
    to_date = parse_date(request.GET.get("to_date", "") or "")
    location_id = request.GET.get("location", "")

    requests = MaintenanceRequest.objects.all()
    assets = Asset.objects.all()

    if location_id:
        requests = requests.filter(asset__location_id=location_id)
        assets = assets.filter(location_id=location_id)
    if from_date:
        requests = requests.filter(reported_at__date__gte=from_date)
    if to_date:
        requests = requests.filter(reported_at__date__lte=to_date)

    kpis = calculate_maintenance_kpis(requests, assets)
    labels, values = monthly_closed_requests(requests)

    location_rows = []
    for loc in Location.objects.all().order_by("name"):
        loc_assets = assets.filter(location=loc) if location_id else Asset.objects.filter(location=loc)
        loc_requests = requests.filter(asset__location=loc)
        loc_kpis = calculate_maintenance_kpis(loc_requests, loc_assets)
        location_rows.append({
            "name": loc.name,
            "value": loc_kpis.get(metric, 0),
            "assets": loc_assets.count(),
            "open": loc_requests.exclude(status="CLOSED").count(),
        })

    metric_titles = {
        "availability": "Availability",
        "mttr_days": "MTTR",
        "mtbf_days": "MTBF",
    }

    return render(request, "cssd/maintenance_kpi_detail.html", {
        "metric": metric,
        "metric_title": metric_titles.get(metric, metric),
        "metric_value": kpis.get(metric, 0),
        "locations": Location.objects.all().order_by("name"),
        "selected_location": location_id,
        "from_date": request.GET.get("from_date", ""),
        "to_date": request.GET.get("to_date", ""),
        "chart_labels": json.dumps(labels),
        "chart_values": json.dumps(values),
        "location_rows": location_rows,
    })

@login_required
def asset_qr_sticker(request, asset_id):

    asset = get_object_or_404(Asset, id=asset_id)

    qr_url = request.build_absolute_uri(
        reverse("asset_qr_access", args=[asset.id])
    )

    qr = qrcode.make(qr_url)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    qr_code = base64.b64encode(buffer.getvalue()).decode()

    return render(
        request,
        "cssd/asset_qr_sticker.html",
        {
            "asset": asset,
            "qr_code": qr_code,
            "qr_url": qr_url,
        }
    )

@login_required
def approve_spare_parts(request, request_id):

    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id
    )

    maintenance_request.status = "WAITING_PARTS"
    maintenance_request.clinic_approved_by = request.user
    maintenance_request.clinic_approved_at = timezone.now()
    maintenance_request.save()

    MaintenanceRequestTimeline.objects.create(
        maintenance_request=maintenance_request,
        action="Clinic Approved Spare Parts Request",
        created_by=request.user
    )

    notify_event(
        title="Spare Parts Approved",
        message=f"Clinic approved spare parts for {maintenance_request.asset.device_name}",
        url=f"/maintenance-requests/{maintenance_request.id}/",
        users=[maintenance_request.assigned_to]
    )

    return redirect(
        "maintenance_request_details",
        request_id=maintenance_request.id
    )

@login_required
def reject_spare_parts(request, request_id):

    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id
    )

    maintenance_request.status = "IN_PROGRESS"
    maintenance_request.save()

    MaintenanceRequestTimeline.objects.create(
        maintenance_request=maintenance_request,
        action="Clinic Rejected Spare Parts Request",
        created_by=request.user
    )

    notify_event(
        title="Spare Parts Rejected",
        message=f"Clinic rejected spare parts for {maintenance_request.asset.device_name}. Returned to engineer.",
        url=f"/maintenance-requests/{maintenance_request.id}/",
        users=[maintenance_request.assigned_to]
    )

    return redirect(
        "maintenance_request_details",
        request_id=maintenance_request.id
    )

@login_required
def pm_pending_confirmation(request):

    pm_histories = PMHistory.objects.filter(
        status="WAITING_CONFIRMATION"
    ).order_by("-performed_at")

    return render(
        request,
        "cssd/pm_pending_confirmation.html",
        {
            "pm_histories": pm_histories
        }
    )

@login_required
def pm_review(request, pm_id):

    pm = get_object_or_404(
        PMHistory,
        id=pm_id
    )

    if request.method == "POST":

        action = request.POST.get("action")
        clinic_comment = request.POST.get("clinic_comment", "").strip()

        if action == "reject" and not clinic_comment:
            return render(
                request,
                "cssd/pm_review.html",
                {
                    "pm": pm,
                    "items": pm.items.all().order_by("id"),
                    "error": "Please write rejection comment."
                }
            )

        pm.clinic_comment = clinic_comment

        if action == "confirm":
            pm.status = "CLOSED"
            pm.confirmed_by = request.user
            pm.confirmed_at = timezone.now()

            # Manager approval must be done after clinic confirmation
            pm.manager_approved = False
            pm.manager_rejected = False
            pm.manager_approved_by = None
            pm.manager_approved_at = None
            pm.manager_comment = ""

        elif action == "reject":
            pm.status = "REJECTED"
            pm.confirmed_by = request.user
            pm.confirmed_at = timezone.now()

            pm.manager_approved = False
            pm.manager_rejected = False
            pm.manager_approved_by = None
            pm.manager_approved_at = None

        pm.save()

        return redirect("pm_pending_confirmation")

    return render(
        request,
        "cssd/pm_review.html",
        {
            "pm": pm,
            "items": pm.items.all().order_by("id")
        }
    )

@login_required
def approve_pm_report(request, pm_id):

    if not request.user.is_superuser:
        return HttpResponseForbidden(
            "Only Maintenance Manager can approve PPM reports."
        )

    pm = get_object_or_404(
        PMHistory,
        id=pm_id
    )

    pm.manager_approved = True
    pm.manager_rejected = False
    pm.manager_approved_by = request.user
    pm.manager_approved_at = timezone.now()
    pm.save()

    notify_event(
        title="PPM Report Approved",
        message=f"PPM report approved for {pm.asset.device_name}",
        url=f"/pm-report/{pm.id}/",
        users=[pm.performed_by]
    )

    messages.success(
        request,
        "PPM report approved successfully."
    )

    return redirect("asset_details", asset_id=pm.asset.id)

@login_required
def reject_pm_report(request, pm_id):

    if not request.user.is_superuser:
        return redirect("home")

    pm = get_object_or_404(
        PMHistory,
        id=pm_id
    )

    asset = pm.asset

    pm.manager_approved = False
    pm.manager_rejected = True
    pm.manager_approved_by = request.user
    pm.manager_approved_at = timezone.now()
    pm.manager_comment = "PPM Report rejected and returned to engineer."

    pm.status = "REJECTED"
    pm.save()

    asset.last_pm_date = None
    asset.next_pm_date = date.today()
    asset.save()

    notify_event(
        title="PPM Report Rejected",
        message=f"PPM report rejected for {asset.device_name}. Returned to engineer.",
        url=f"/pm-review/{pm.id}/",
        users=[pm.performed_by]
    )

    messages.warning(
        request,
        "PPM Report Rejected and returned to PM Due."
    )

    return redirect(
        "asset_details",
        asset_id=asset.id
    )


@login_required
def ppm_service_report(request, pm_id):

    pm = get_object_or_404(
        PMHistory,
        id=pm_id
    )

    if not pm.manager_approved:
        messages.warning(
            request,
            "PPM Report is pending Maintenance Manager approval."
        )

        return redirect("asset_details", asset_id=pm.asset.id)

    items = pm.items.all().order_by("id")

    spare_items = pm.items.filter(
        result="NOT_OK"
    ).exclude(
        requested_spare_part=""
    ).order_by("id")

    return render(
        request,
        "cssd/ppm_service_report.html",
        {
            "pm": pm,
            "items": items,
            "spare_items": spare_items,
        }
    )

@login_required
def engineers_performance(request):

    engineers = User.objects.filter(
        groups__name="ENGINEER"
    ).distinct()

    engineer_stats = []

    for engineer in engineers:

        total = MaintenanceRequest.objects.filter(
            assigned_to=engineer
        ).count()

        open_count = MaintenanceRequest.objects.filter(
            assigned_to=engineer,
            status="OPEN"
        ).count()

        in_progress = MaintenanceRequest.objects.filter(
            assigned_to=engineer,
            status="IN_PROGRESS"
        ).count()

        waiting_parts = MaintenanceRequest.objects.filter(
            assigned_to=engineer,
            status="WAITING_PARTS"
        ).count()

        closed = MaintenanceRequest.objects.filter(
            assigned_to=engineer,
            status="CLOSED"
        ).count()

        completion_rate = round((closed / total) * 100, 1) if total else 0

        engineer_stats.append({
            "engineer": engineer,
            "total": total,
            "open": open_count,
            "in_progress": in_progress,
            "waiting_parts": waiting_parts,
            "closed": closed,
            "completion_rate": completion_rate,
        })

    engineer_stats = sorted(
        engineer_stats,
        key=lambda x: x["completion_rate"],
        reverse=True
    )

    engineers_count = len(engineer_stats)

    best_engineer = "-"
    average_performance = 0

    if engineer_stats:
        best_engineer_obj = engineer_stats[0]["engineer"]
        best_engineer = best_engineer_obj.get_full_name() or best_engineer_obj.username

        average_performance = round(
            sum(row["completion_rate"] for row in engineer_stats) / engineers_count,
            1
        )

    return render(
        request,
        "cssd/engineers_performance.html",
        {
            "engineer_stats": engineer_stats,
            "engineers_count": engineers_count,
            "best_engineer": best_engineer,
            "average_performance": average_performance,
        }
    )

@login_required
def reports_center(request):

    return render(
        request,
        "cssd/reports_center.html"
    )

@login_required
def daily_report(request):

    report_date = parse_date(
        request.GET.get("date")
    )

    if not report_date:
        report_date = date.today()

    requests = MaintenanceRequest.objects.filter(
        reported_at__date=report_date
    )

    context = {
        "report_date": report_date,
        "total_requests": requests.count(),
        "open_requests": requests.filter(status="OPEN").count(),
        "in_progress": requests.filter(status="IN_PROGRESS").count(),
        "waiting_parts": requests.filter(status="WAITING_PARTS").count(),
        "waiting_confirmation": requests.filter(
            status="WAITING_CONFIRMATION"
        ).count(),
        "closed_requests": requests.filter(
            status="CLOSED"
        ).count(),

        "pm_completed": PMHistory.objects.filter(
            performed_at__date=report_date
        ).count(),
    }

    return render(
        request,
        "cssd/daily_report.html",
        context
    )

@login_required
def period_report(request):

    from_date = parse_date(
        request.GET.get("from_date")
    )

    to_date = parse_date(
        request.GET.get("to_date")
    )

    requests = MaintenanceRequest.objects.all()

    if from_date:
        requests = requests.filter(
            reported_at__date__gte=from_date
        )

    if to_date:
        requests = requests.filter(
            reported_at__date__lte=to_date
        )

    engineer_stats = User.objects.filter(
        groups__name="ENGINEER"
    ).distinct()

    context = {
        "from_date": from_date,
        "to_date": to_date,

        "total_requests": requests.count(),
        "open_requests": requests.filter(
            status="OPEN"
        ).count(),

        "in_progress": requests.filter(
            status="IN_PROGRESS"
        ).count(),

        "waiting_parts": requests.filter(
            status="WAITING_PARTS"
        ).count(),

        "waiting_confirmation": requests.filter(
            status="WAITING_CONFIRMATION"
        ).count(),

        "closed_requests": requests.filter(
            status="CLOSED"
        ).count(),

        "engineers": engineer_stats,
    }

    return render(
        request,
        "cssd/period_report.html",
        context
    )

# ==============================
# Infection Control System
# ==============================

INFECTION_PROCEDURE_ITEMS = [
    ("surface_cleaning", "تنظيف وتطهير الأسطح"),
    ("chair_cleaning", "تنظيف وتطهير كرسي الأسنان"),
    ("spittoon_cleaning", "تنظيف وتطهير مصفاة المبصقة"),
    ("suction_filter_cleaning", "تنظيف وتطهير فلاتر وحدات الشفط"),
    ("handwash_basin_cleaning", "تنظيف وتطهير حوض غسل اليدين"),
    ("ppe_drawers_refill", "تعبئة الأدراج بأدوات الحماية الشخصية"),
    ("soap_refill", "تعبئة حاويات الصابون"),
    ("sanitizer_refill", "تعبئة حاويات مطهر اليدين"),
]


def get_infection_procedure_items():
    template = InfectionProcedureTemplate.objects.filter(is_active=True).prefetch_related('items').first()
    if template:
        items = [(item.field_name, item.label) for item in template.items.filter(is_active=True).order_by('sort_order', 'id')]
        if items:
            return items
    return INFECTION_PROCEDURE_ITEMS


def _week_start(target_date=None):
    target_date = target_date or date.today()
    return target_date - timedelta(days=target_date.weekday())


def _assignment_due_date(assignment, base_date=None):
    start = _week_start(base_date)
    return start + timedelta(days=assignment.weekday)


def ensure_infection_tasks_for_week(base_date=None):
    base_date = base_date or date.today()
    for assignment in InfectionCleaningAssignment.objects.filter(is_active=True).select_related("asset", "asset__location", "clinic", "nurse"):
        due_date = _assignment_due_date(assignment, base_date)
        InfectionCleaningTask.objects.get_or_create(
            assignment=assignment,
            asset=assignment.asset,
            clinic=assignment.clinic or (assignment.asset.location if assignment.asset else None),
            nurse=assignment.nurse,
            due_date=due_date,
            defaults={"status": "PENDING"}
        )
    InfectionCleaningTask.objects.filter(
        status="PENDING",
        due_date__lt=date.today()
    ).update(status="OVERDUE")


def _infection_tasks_for_user(user):
    qs = InfectionCleaningTask.objects.select_related("asset", "asset__location", "clinic", "nurse", "completed_by")
    if is_infection_manager(user):
        return qs
    return qs.filter(nurse=user)


@login_required
def infection_entry(request):
    if is_engineer(request.user):
        return redirect("engineer_dashboard")
    if is_infection_manager(request.user):
        return redirect("infection_manager_dashboard")
    return redirect("infection_nurse_dashboard")


@login_required
def infection_nurse_dashboard(request):
    ensure_infection_tasks_for_week()
    today = date.today()
    tomorrow = today + timedelta(days=1)
    tasks = _infection_tasks_for_user(request.user)
    context = {
        "today": today,
        "assigned_count": InfectionCleaningAssignment.objects.filter(nurse=request.user, is_active=True).count(),
        "due_today_count": tasks.filter(due_date=today, status__in=["PENDING", "OVERDUE"]).count(),
        "due_tomorrow_count": tasks.filter(due_date=tomorrow, status="PENDING").count(),
        "overdue_count": tasks.filter(status="OVERDUE").count(),
        "completed_count": tasks.filter(status="COMPLETED", completed_at__date__gte=_week_start()).count(),
    }
    return render(request, "cssd/infection_nurse_dashboard.html", context)


@login_required
def infection_manager_dashboard(request):
    if not is_infection_manager(request.user):
        return render(request, "cssd/access_denied.html")
    ensure_infection_tasks_for_week()
    today = date.today()
    tomorrow = today + timedelta(days=1)
    tasks = InfectionCleaningTask.objects.all()
    total = tasks.count() or 1
    completed = tasks.filter(status="COMPLETED").count()
    context = {
        "total_clinics": InfectionCleaningAssignment.objects.filter(is_active=True).count(),
        "due_today_count": tasks.filter(due_date=today, status__in=["PENDING", "OVERDUE"]).count(),
        "due_tomorrow_count": tasks.filter(due_date=tomorrow, status="PENDING").count(),
        "overdue_count": tasks.filter(status="OVERDUE").count(),
        "completed_count": completed,
        "completion_percent": round((completed / total) * 100, 1),
    }
    return render(request, "cssd/infection_manager_dashboard.html", context)


@login_required
def infection_tasks(request):
    ensure_infection_tasks_for_week()
    status_filter = request.GET.get("status", "")
    view_filter = request.GET.get("view", "")
    from_date = parse_date(request.GET.get("from", "") or "")
    to_date = parse_date(request.GET.get("to", "") or "")

    tasks = _infection_tasks_for_user(request.user)
    today = date.today()
    if view_filter == "today":
        tasks = tasks.filter(due_date=today)
    elif view_filter == "tomorrow":
        tasks = tasks.filter(due_date=today + timedelta(days=1))
    elif view_filter == "overdue":
        tasks = tasks.filter(status="OVERDUE")
    elif view_filter == "completed":
        tasks = tasks.filter(status="COMPLETED")
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if from_date:
        tasks = tasks.filter(due_date__gte=from_date)
    if to_date:
        tasks = tasks.filter(due_date__lte=to_date)

    return render(request, "cssd/infection_tasks.html", {
        "tasks": tasks.order_by("due_date", "asset__department", "asset__asset_number", "clinic__name"),
        "procedure_items": get_infection_procedure_items(),
        "view_filter": view_filter,
        "status_filter": status_filter,
        "from_date": request.GET.get("from", ""),
        "to_date": request.GET.get("to", ""),
    })


@login_required
def infection_task_detail(request, task_id):
    ensure_infection_tasks_for_week()
    task = get_object_or_404(_infection_tasks_for_user(request.user), id=task_id)

    if request.method == "POST":
        if task.nurse != request.user and not is_infection_manager(request.user):
            return render(request, "cssd/access_denied.html")

        validation_errors = []
        for field, label in get_infection_procedure_items():
            status_value = request.POST.get(f"{field}_status")
            reason_value = request.POST.get(f"{field}_reason", "").strip()

            if status_value not in ["done", "not_done"]:
                validation_errors.append(f"Please select Done or Not Done for: {label}")
                continue

            is_done = status_value == "done"
            setattr(task, field, is_done)
            setattr(task, f"{field}_reason", "" if is_done else reason_value)

            if not is_done and not reason_value:
                validation_errors.append(f"Please write the reason for Not Done: {label}")

        task.responsible_employee = request.user.get_full_name() or request.user.username
        task.general_comment = request.POST.get("general_comment", "").strip()

        if validation_errors:
            task.save()
            for error in validation_errors:
                messages.warning(request, error)
            return redirect("infection_task_detail", task_id=task.id)

        task.status = "COMPLETED"
        task.completed_by = request.user
        task.completed_at = timezone.now()
        task.save()
        notify_event(
            title="Infection Control Cleaning Completed",
            message=f"{task.clinic_name} cleaning checklist completed by {request.user.get_full_name() or request.user.username}.",
            url=f"/infection-control/tasks/{task.id}/report/",
            target_groups=["MAINTENANCE_MANAGER", "HOSPITAL_MANAGER", "INFECTION_CONTROL_MANAGER"]
        )
        return redirect("infection_cleaning_report", task_id=task.id)

    return render(request, "cssd/infection_task_detail.html", {
        "task": task,
        "procedure_items": get_infection_procedure_items(),
    })


@login_required
def infection_cleaning_report(request, task_id):
    task = get_object_or_404(_infection_tasks_for_user(request.user), id=task_id)
    return render(request, "cssd/infection_cleaning_report.html", {
        "task": task,
        "procedure_items": get_infection_procedure_items(),
    })


@login_required
def infection_assignments(request):
    if not is_infection_manager(request.user):
        return render(request, "cssd/access_denied.html")
    assignments = InfectionCleaningAssignment.objects.select_related("asset", "asset__location", "clinic", "nurse").order_by("clinic__group_type", "clinic__name")
    return render(request, "cssd/infection_assignments.html", {"assignments": assignments})
