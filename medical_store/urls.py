from django.urls import path
from . import views

app_name = "medical_store"

urlpatterns = [
    path("", views.entry, name="entry"),
    path("store-dashboard/", views.store_dashboard, name="store_dashboard"),
    path("nurse-dashboard/", views.nurse_dashboard, name="nurse_dashboard"),
    path("hospital-dashboard/", views.hospital_dashboard, name="hospital_dashboard"),
    path("products/add/", views.add_product, name="add_product"),
    path("stock/receive/", views.receive_stock, name="receive_stock"),
    path("inventory/", views.inventory, name="inventory"),
    path("products/<int:product_id>/", views.product_detail, name="product_detail"),
    path("requests/new/", views.new_request, name="new_request"),
    path("products/search/", views.product_search, name="product_search"),
    path("requests/", views.request_list, name="request_list"),
    path("requests/status/<str:status>/", views.request_list, name="request_list_status"),
    path("requests/<int:request_id>/", views.request_detail, name="request_detail"),
    path("requests/<int:request_id>/approve/", views.approve_request, name="approve_request"),
    path("requests/<int:request_id>/issue/", views.issue_request_view, name="issue_request"),
    path("requests/<int:request_id>/confirm/", views.confirm_receipt, name="confirm_receipt"),
    path("low-stock/", views.low_stock, name="low_stock"),
    path("near-expiry/", views.near_expiry, name="near_expiry"),
    path("reports/", views.reports_center, name="reports_center"),
    path("reports/department-requests/", views.department_requests_report, name="department_requests_report"),
    path("reports/inventory.csv", views.export_inventory_csv, name="export_inventory_csv"),
    path("import-products/", views.import_products, name="import_products"),
]
