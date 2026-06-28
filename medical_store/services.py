from django.db import transaction
from django.utils import timezone
from .models import StoreBatch, StoreIssueAllocation, StoreAuditLog


def _to_int(value, default=0):
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


@transaction.atomic
def issue_request(store_request, issued_by, issue_quantities, reasons=None, comment="", issued_units=None):
    reasons = reasons or {}
    issued_units = issued_units or {}
    for item in store_request.items.select_related("product"):
        qty = _to_int(issue_quantities.get(str(item.id)), 0)
        if qty < 0:
            qty = 0
        unit = issued_units.get(str(item.id)) or item.requested_unit or item.product.unit
        unit_pieces = item.product.conversion_for(unit)
        total_qty = qty * unit_pieces

        item.issued_quantity = qty
        item.issued_unit = unit
        item.issued_unit_pieces = unit_pieces
        item.issued_total_quantity = total_qty
        item.issue_adjustment_reason = reasons.get(str(item.id), "") or ""
        item.save(update_fields=[
            "issued_quantity", "issued_unit", "issued_unit_pieces", "issued_total_quantity", "issue_adjustment_reason"
        ])

        remaining = total_qty
        batches = StoreBatch.objects.select_for_update().filter(
            product=item.product,
            current_quantity__gt=0,
        ).order_by("expiry_date", "created_at")
        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.current_quantity, remaining)
            batch.current_quantity -= take
            batch.save(update_fields=["current_quantity"])
            StoreIssueAllocation.objects.create(request_item=item, batch=batch, quantity=take)
            remaining -= take

    store_request.status = "ISSUED_WAITING_NURSE_CONFIRM"
    store_request.store_issued_by = issued_by
    store_request.store_issued_at = timezone.now()
    store_request.store_comment = comment
    store_request.save(update_fields=["status", "store_issued_by", "store_issued_at", "store_comment", "updated_at"])
    StoreAuditLog.objects.create(
        action="ISSUE_REQUEST",
        user=issued_by,
        store_request=store_request,
        details=f"Issued items. {comment}",
    )
