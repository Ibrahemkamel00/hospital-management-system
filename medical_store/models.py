from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class StoreProduct(models.Model):
    UNIT_CHOICES = [
        ("Piece", "Piece"),
        ("Box", "Box"),
        ("Pack", "Pack"),
        ("Carton", "Carton"),
        ("Roll", "Roll"),
        ("Bottle", "Bottle"),
        ("Tube", "Tube"),
        ("Set", "Set"),
    ]
    CONVERTIBLE_UNITS = ["Pack", "Carton", "Set"]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=80, unique=True)
    manufacturer = models.CharField(max_length=150, blank=True)
    unit = models.CharField(max_length=40, choices=UNIT_CHOICES, default="Piece")
    allowed_units = models.JSONField(default=list, blank=True)
    unit_pieces = models.JSONField(default=dict, blank=True)
    shelf = models.CharField(max_length=100)
    minimum_stock = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Medical Store Product"
        verbose_name_plural = "Medical Store Products"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.allowed_units:
            self.allowed_units = [self.unit or "Piece"]
        if not self.unit and self.allowed_units:
            self.unit = self.allowed_units[0]
        super().save(*args, **kwargs)

    def get_allowed_units(self):
        return self.allowed_units or [self.unit or "Piece"]

    def conversion_for(self, unit):
        """Return how many base pieces/units are inside the selected unit."""
        if not unit:
            return 1
        try:
            return int((self.unit_pieces or {}).get(unit) or 1)
        except (TypeError, ValueError):
            return 1

    @property
    def total_available(self):
        return self.batches.aggregate(total=Sum("current_quantity"))["total"] or 0

    @property
    def is_low_stock(self):
        return self.total_available <= self.minimum_stock

    @property
    def display_stock(self):
        total = int(self.total_available or 0)
        units = self.get_allowed_units()
        convertible = []
        for unit in ["Carton", "Pack", "Set"]:
            if unit in units:
                conv = self.conversion_for(unit)
                if conv > 1:
                    convertible.append((unit, conv))
        convertible.sort(key=lambda x: x[1], reverse=True)
        parts = []
        remaining = total
        for unit, conv in convertible:
            count, remaining = divmod(remaining, conv)
            if count:
                parts.append(f"{count} {unit}")
        base_unit = "Piece" if "Piece" in units or convertible else (self.unit or (units[0] if units else "Piece"))
        if remaining or not parts:
            parts.append(f"{remaining} {base_unit}")
        return " + ".join(parts)


class StoreBatch(models.Model):
    product = models.ForeignKey(StoreProduct, on_delete=models.CASCADE, related_name="batches")
    supplier_name = models.CharField(max_length=150)
    batch_number = models.CharField(max_length=120, blank=True)
    received_date = models.DateField(default=timezone.localdate)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    received_quantity = models.PositiveIntegerField(default=0)
    received_unit = models.CharField(max_length=40, blank=True, default="")
    received_unit_pieces = models.PositiveIntegerField(default=1)
    received_total_quantity = models.PositiveIntegerField(default=0)
    current_quantity = models.PositiveIntegerField(default=0)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="store_received_batches")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["expiry_date", "created_at"]
        verbose_name = "Stock Batch"
        verbose_name_plural = "Stock Batches"
        indexes = [models.Index(fields=["product", "expiry_date"])]

    def __str__(self):
        batch = self.batch_number or "No Batch"
        return f"{self.product.name} - {batch}"

    @property
    def near_expiry(self):
        if not self.expiry_date:
            return False
        today = timezone.localdate()
        return today <= self.expiry_date <= today + timezone.timedelta(days=60)

    @property
    def received_display(self):
        unit = self.received_unit or self.product.unit
        return f"{self.received_quantity} {unit}"

    @property
    def current_display(self):
        return f"{self.current_quantity} Piece/Base"


class StoreRequest(models.Model):
    STATUS_DRAFT = "DRAFT"
    STATUS_PENDING_HM = "PENDING_HOSPITAL_MANAGER"
    STATUS_REJECTED = "REJECTED"
    STATUS_APPROVED = "APPROVED_WAITING_STORE"
    STATUS_ISSUED = "ISSUED_WAITING_NURSE_CONFIRM"
    STATUS_CLOSED = "CLOSED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING_HM, "Pending Hospital Manager Approval"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_APPROVED, "Approved - Waiting Store Issue"),
        (STATUS_ISSUED, "Issued - Waiting Nurse Confirmation"),
        (STATUS_CLOSED, "Closed"),
    ]

    request_number = models.CharField(max_length=30, unique=True, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="medical_store_requests")
    department = models.CharField(max_length=150, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    hospital_manager_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="store_approved_requests")
    hospital_manager_at = models.DateTimeField(null=True, blank=True)
    hospital_manager_comment = models.TextField(blank=True)

    store_issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="store_issued_requests")
    store_issued_at = models.DateTimeField(null=True, blank=True)
    store_comment = models.TextField(blank=True)

    nurse_confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="store_confirmed_receipts")
    nurse_confirmed_at = models.DateTimeField(null=True, blank=True)
    nurse_comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Medical Store Request"
        verbose_name_plural = "Medical Store Requests"

    def __str__(self):
        return self.request_number or f"Store Request #{self.id}"

    def save(self, *args, **kwargs):
        if not self.request_number and self.pk:
            self.request_number = f"MSR-{timezone.localdate().year}-{self.pk:06d}"
        super().save(*args, **kwargs)
        if not self.request_number:
            self.request_number = f"MSR-{timezone.localdate().year}-{self.pk:06d}"
            super().save(update_fields=["request_number"])


class StoreRequestItem(models.Model):
    store_request = models.ForeignKey(StoreRequest, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(StoreProduct, on_delete=models.PROTECT, related_name="request_items")
    requested_quantity = models.PositiveIntegerField(default=1)
    requested_unit = models.CharField(max_length=40, default="Piece")
    requested_unit_pieces = models.PositiveIntegerField(default=1)
    requested_total_quantity = models.PositiveIntegerField(default=1)
    issued_quantity = models.PositiveIntegerField(default=0)
    issued_unit = models.CharField(max_length=40, blank=True, default="")
    issued_unit_pieces = models.PositiveIntegerField(default=1)
    issued_total_quantity = models.PositiveIntegerField(default=0)
    issue_adjustment_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Medical Store Request Item"
        verbose_name_plural = "Medical Store Request Items"

    def __str__(self):
        return f"{self.store_request} - {self.product.name}"

    @property
    def requested_display(self):
        text = f"{self.requested_quantity} {self.requested_unit}"
        if self.requested_unit_pieces > 1:
            text += f" = {self.requested_total_quantity} Pieces"
        return text

    @property
    def issued_display(self):
        if not self.issued_quantity:
            return "-"
        unit = self.issued_unit or self.requested_unit
        text = f"{self.issued_quantity} {unit}"
        if self.issued_unit_pieces > 1:
            text += f" = {self.issued_total_quantity} Pieces"
        return text

    @property
    def quantity_changed(self):
        return bool(self.issued_total_quantity and self.issued_total_quantity != self.requested_total_quantity)


class StoreIssueAllocation(models.Model):
    request_item = models.ForeignKey(StoreRequestItem, on_delete=models.CASCADE, related_name="allocations")
    batch = models.ForeignKey(StoreBatch, on_delete=models.PROTECT, related_name="issue_allocations")
    quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.batch} x {self.quantity}"


class StoreAuditLog(models.Model):
    action = models.CharField(max_length=120)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    store_request = models.ForeignKey(StoreRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    product = models.ForeignKey(StoreProduct, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Medical Store Audit Log"
        verbose_name_plural = "Medical Store Audit Logs"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} - {self.action}"
