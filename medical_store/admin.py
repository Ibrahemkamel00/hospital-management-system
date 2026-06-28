from django.contrib import admin
from .models import (
    StoreProduct, StoreBatch, StoreRequest, StoreRequestItem,
    StoreIssueAllocation, StoreAuditLog
)


class StoreBatchInline(admin.TabularInline):
    model = StoreBatch
    extra = 0
    readonly_fields = ("current_quantity", "received_by", "created_at")


@admin.register(StoreProduct)
class StoreProductAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "manufacturer", "shelf", "minimum_stock", "display_stock", "is_active")
    search_fields = ("name", "code", "manufacturer", "category")
    list_filter = ("is_active", "category")
    inlines = [StoreBatchInline]


@admin.register(StoreBatch)
class StoreBatchAdmin(admin.ModelAdmin):
    list_display = ("product", "batch_number", "supplier_name", "received_display", "received_total_quantity", "current_quantity", "expiry_date", "received_by")
    search_fields = ("product__name", "product__code", "batch_number", "supplier_name")
    list_filter = ("expiry_date", "received_date")


class StoreRequestItemInline(admin.TabularInline):
    model = StoreRequestItem
    extra = 0


@admin.register(StoreRequest)
class StoreRequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "requested_by", "department", "status", "created_at")
    search_fields = ("request_number", "requested_by__username", "department", "reason")
    list_filter = ("status", "created_at")
    inlines = [StoreRequestItemInline]


@admin.register(StoreIssueAllocation)
class StoreIssueAllocationAdmin(admin.ModelAdmin):
    list_display = ("request_item", "batch", "quantity", "created_at")


@admin.register(StoreAuditLog)
class StoreAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "user", "store_request", "product")
    search_fields = ("action", "details", "user__username", "store_request__request_number", "product__name")
    list_filter = ("action", "created_at")
    readonly_fields = ("created_at",)
