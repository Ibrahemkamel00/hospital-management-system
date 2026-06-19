from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.models import User, Group

import qrcode
import base64
from io import BytesIO

from datetime import date

from .models import Notification

@login_required
def notifications(request):

    user_groups = list(
        request.user.groups.values_list("name", flat=True)
    )

    notifications = Notification.objects.filter(
        target_group__in=user_groups
    ).order_by("-created_at")

    # تصفير الإشعارات غير المقروءة
    Notification.objects.filter(
        target_group__in=user_groups,
        is_read=False
    ).update(is_read=True)

    return render(
        request,
        "cssd/notifications.html",
        {
            "notifications": notifications
        }
    )

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
)


def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def is_admin(user):
    return user.is_superuser or user_in_group(user, "ADMIN")


def is_cssd(user):
    return user_in_group(user, "CSSD")


def user_location_groups(user):
    groups = ["MALE", "FEMALE", "SPECIALTY", "EMERGENCY"]
    return [g for g in groups if user_in_group(user, g)]


def visible_requests_for_user(user):
    if is_admin(user) or is_cssd(user):
        return CSSDRequest.objects.all()

    user_groups = user_location_groups(user)
    return CSSDRequest.objects.filter(location__group_type__in=user_groups)


def can_access_request(user, cssd_request):
    if is_admin(user) or is_cssd(user):
        return True

    return cssd_request.location.group_type in user_location_groups(user)

from datetime import date, timedelta

def asset_list(request):

    assets = Asset.objects.all().order_by("asset_number")

    open_requests = MaintenanceRequest.objects.filter(
        status="OPEN"
    ).count()

    under_maintenance = MaintenanceRequest.objects.filter(
        status="IN_PROGRESS"
    ).count()

    waiting_parts = MaintenanceRequest.objects.filter(
        status="WAITING_PARTS"
    ).count()

    completed_requests = MaintenanceRequest.objects.filter(
        status="CLOSED"
    ).count()

    total_requests = MaintenanceRequest.objects.count()

    total_assets = Asset.objects.count()

    today = date.today()
    pm_soon_date = today + timedelta(days=30)

    pm_due_assets = Asset.objects.filter(
        next_pm_date__lte=today
    )

    pm_due = pm_due_assets.count()

    return render(
        request,
        "cssd/asset_list.html",
        {
            "assets": assets,
            "total_assets": total_assets,
            "open_requests": open_requests,
            "under_maintenance": under_maintenance,
            "waiting_parts": waiting_parts,
            "completed_requests": completed_requests,
            "total_requests": total_requests,
            "pm_due": pm_due,
            "pm_due_assets": pm_due_assets,
            "today": today,
            "pm_soon_date": pm_soon_date,
        }
    )

def asset_details(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)

    return render(
        request,
        "cssd/asset_details.html",
        {"asset": asset}
    )

@login_required
def report_fault(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)

    if request.method == "POST":
        fault_description = request.POST.get("fault_description")
        priority = request.POST.get("priority")

        MaintenanceRequest.objects.create(
        asset=asset,
        reported_by=request.user,
        assigned_to=asset.location.engineers.first() if asset.location else None,
        fault_description=fault_description,
        priority=priority,
        status="OPEN"
)

        asset.status = "UNDER_MAINTENANCE"
        asset.save()

        return redirect("asset_details", asset_id=asset.id)

    return render(request, "cssd/report_fault.html", {
        "asset": asset
    })

@login_required
def maintenance_requests(request):

    status = request.GET.get("status")

    requests = MaintenanceRequest.objects.all()

    if status:
        requests = requests.filter(status=status)

    requests = requests.order_by("-reported_at")

    return render(
        request,
        "cssd/maintenance_requests.html",
        {
            "requests": requests,
            "current_status": status
        }
    )

@login_required
def maintenance_request_details(request, request_id):
    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id
    )

    return render(
        request,
        "cssd/maintenance_request_details.html",
        {"maintenance_request": maintenance_request}
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
    maintenance_request.asset.save()

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

        Notification.objects.create(
            target_group="CSSD",
            title="New CSSD Request",
            message=f"New request from {cssd_request.location.name}: {', '.join(used_templates)}",
            cssd_request=cssd_request
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

    asset = get_object_or_404(
        Asset,
        id=asset_id
    )

    today = date.today()

    if asset.next_pm_date and asset.next_pm_date > today:
        return redirect(
            "asset_details",
            asset_id=asset.id
        )

    already_done = PMHistory.objects.filter(
        asset=asset,
        performed_at__date=today
    ).exists()

    if already_done:
        return render(
            request,
            "cssd/perform_pm.html",
            {
                "asset": asset,
                "error": "PPM already performed today for this asset."
            }
        )

    if request.method == "POST":

        ppm_sticker_applied = request.POST.get(
             "ppm_sticker_applied"
        )

        if not ppm_sticker_applied:
            return render(
                request,
                "cssd/perform_pm.html",
                {
                    "asset": asset,
                    "error": "Please confirm that PPM sticker has been applied."
                }
            )
        checklist_items = [
            {
                "field": "power_check",
                "label": "Power Check",
                "spare_field": "power_spare_part",
            },
            {
                "field": "function_check",
                "label": "Function Check",
                "spare_field": "function_spare_part",
            },
            {
                "field": "air_water_check",
                "label": "Air / Water Check",
                "spare_field": "air_water_spare_part",
            },
            {
                "field": "safety_check",
                "label": "Safety Check",
                "spare_field": "safety_spare_part",
            },
            {
                "field": "cleaning_check",
                "label": "Cleaning Check",
                "spare_field": "cleaning_spare_part",
            },
        ]

        failed_items = []
        spare_parts_notes = []

        for item in checklist_items:

            check_value = request.POST.get(
                item["field"],
                "OK"
            )

            if check_value == "NOT_OK":

                spare_part = request.POST.get(
                    item["spare_field"],
                    ""
                ).strip()

                if not spare_part:
                    return render(
                        request,
                        "cssd/perform_pm.html",
                        {
                            "asset": asset,
                            "error": f"Please enter spare part needed for {item['label']}."
                        }
                    )

                failed_items.append(item["label"])

                spare_parts_notes.append(
                    f"{item['label']}: {spare_part}"
                )

        asset.last_pm_date = today
        asset.next_pm_date = today + relativedelta(months=6)

        # مهم: لا نغير حالة الجهاز هنا
        asset.save()

        if failed_items:
            notes = (
                "PPM Completed with spare parts required. "
                + " | ".join(spare_parts_notes)
            )
        else:
            notes = "PPM Checklist Completed - All items OK"

        PMHistory.objects.create(
            asset=asset,
            performed_by=request.user,
            notes=notes,
            next_pm_date=asset.next_pm_date
        )

        if failed_items:
            MaintenanceRequest.objects.create(
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
                spare_part_name=" | ".join(spare_parts_notes),
                work_done="PPM completed. Spare parts required."
            )

        return redirect(
            "asset_details",
            asset_id=asset.id
        )

    return render(
        request,
        "cssd/perform_pm.html",
        {
            "asset": asset
        }
    )

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

    return redirect(
        "complete_maintenance_request",
        request_id=req.id
    )

@login_required
def system_selection(request):
    return render(request, "cssd/system_selection.html")

from django.utils import timezone

@login_required
def pm_dashboard(request):

    assets = Asset.objects.all().order_by("asset_number")

    return render(
        request,
        "cssd/pm_dashboard.html",
        {
            "assets": assets
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

        is_pm_request = maintenance_request.work_done.startswith("SOURCE:PM")

        maintenance_request.work_done = work_done

        if action == "need_spare_part":

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
            maintenance_request.status = "WAITING_PARTS"
            maintenance_request.closed_at = None

            if not is_pm_request:
                maintenance_request.asset.status = "UNDER_MAINTENANCE"

        elif action == "spare_part_installed":

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

            maintenance_request.needs_spare_parts = False
            maintenance_request.status = "CLOSED"
            maintenance_request.closed_at = timezone.now()
            maintenance_request.asset.status = "ACTIVE"

        elif action == "repaired_without_spare":

            maintenance_request.needs_spare_parts = False
            maintenance_request.status = "CLOSED"
            maintenance_request.closed_at = timezone.now()
            maintenance_request.asset.status = "ACTIVE"

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

        Notification.objects.create(
            target_group=cssd_request.location.group_type,
            title="CSSD Received Request",
            message=f"CSSD received request #{cssd_request.id}",
            cssd_request=cssd_request
        )

        return redirect("cssd_pending_requests")

    return render(request, "cssd/request_details.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
    })


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

        Notification.objects.create(
            target_group=cssd_request.location.group_type,
            title="Instruments Returned",
            message=f"CSSD returned request #{cssd_request.id} to clinic",
            cssd_request=cssd_request
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

    Notification.objects.create(
        target_group="CSSD",
        title="Clinic Confirmed Receipt",
        message=f"Clinic confirmed receiving request #{cssd_request.id}",
        cssd_request=cssd_request
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

    search = request.GET.get("search", "")
    status = request.GET.get("status", "")

    if search:
        requests = requests.filter(
            location__name__icontains=search
        ) | requests.filter(
            created_by__username__icontains=search
        ) | requests.filter(
            id__icontains=search
        )

    if status:
        requests = requests.filter(status=status)

    requests = requests.order_by("-created_at")

    return render(request, "cssd/all_requests.html", {
        "requests": requests,
        "search": search,
        "status": status,
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
        cssd_request.status = "CLOSED"
        cssd_request.closed_by = request.user
        cssd_request.closed_at = timezone.now()
        cssd_request.save()

        Notification.objects.create(
            target_group="CSSD",
            title="Clinic Confirmed Receipt",
            message=f"Clinic confirmed receiving request #{cssd_request.id}",
            cssd_request=cssd_request
        )

        return redirect("clinic_pending_returns")

    return render(request, "cssd/clinic_confirm_details.html", {
        "request_obj": cssd_request,
        "items": cssd_request.items.all(),
    })

