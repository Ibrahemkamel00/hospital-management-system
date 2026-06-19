from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from cssd.views import (
    home,
    dashboard,
    new_request,
    get_template_items,
    cssd_pending_requests,
    cssd_request_details,
    cssd_received_requests,
    return_to_clinic,
    clinic_pending_returns,
    confirm_by_clinic,
    close_request,
    print_request,
    all_requests,
    notifications,
    notifications_count,
    reports,
    my_requests,
    clinic_confirm_details,
    asset_list,
    asset_details,
    report_fault,
    maintenance_requests,
    maintenance_request_details,
    my_maintenance_requests,
    complete_maintenance_request,
    pending_spare_parts,
    part_received,
    system_selection,
    start_maintenance_request,
    pm_dashboard,
    perform_pm,
    spare_parts_tracking,
    service_report,
    engineer_dashboard,
    clinic_dashboard,
    maintenance_entry,
    back_to_dashboard,
    clinic_waiting_parts_assets,
    clinic_assets,
    clinic_confirm_maintenance,
    public_report_fault,
    asset_qr_access,
    asset_qr_sticker,
    approve_spare_parts,
    reject_spare_parts,
    pm_pending_confirmation,
    pm_review,
    ppm_service_report,
    engineers_performance,
    reports_center,
    daily_report,
    period_report,
    approve_report,
    reject_report,
    approve_pm_report,
    reject_pm_report,
    open_notification,
    add_maintenance_inquiry,
    add_maintenance_attachment,
    reassign_maintenance_request,
    manager_take_over_request,
    hospital_maintenance_dashboard,
    hospital_cssd_dashboard,
    locations_overview,
    location_assets,
    maintenance_kpi_detail,
    infection_entry,
    infection_nurse_dashboard,
    infection_manager_dashboard,
    infection_tasks,
    infection_task_detail,
    infection_cleaning_report,
    infection_assignments,

)

urlpatterns = [


path("infection-control/", infection_entry, name="infection_entry"),
path("infection-control/nurse-dashboard/", infection_nurse_dashboard, name="infection_nurse_dashboard"),
path("infection-control/manager-dashboard/", infection_manager_dashboard, name="infection_manager_dashboard"),
path("infection-control/tasks/", infection_tasks, name="infection_tasks"),
path("infection-control/tasks/<int:task_id>/", infection_task_detail, name="infection_task_detail"),
path("infection-control/tasks/<int:task_id>/report/", infection_cleaning_report, name="infection_cleaning_report"),
path("infection-control/assignments/", infection_assignments, name="infection_assignments"),


path("maintenance-locations/", locations_overview, name="locations_overview"),
path("maintenance-locations/<int:location_id>/", location_assets, name="location_assets"),
path("maintenance-kpi/<str:metric>/", maintenance_kpi_detail, name="maintenance_kpi_detail"),


path(
    'notifications/<int:notification_id>/open/',
    open_notification,
    name='open_notification'
),

path(
    'maintenance-requests/<int:request_id>/inquiry/add/',
    add_maintenance_inquiry,
    name='add_maintenance_inquiry'
),

path(
    'maintenance-requests/<int:request_id>/attachments/add/',
    add_maintenance_attachment,
    name='add_maintenance_attachment'
),

path(
    'maintenance-requests/<int:request_id>/reassign/',
    reassign_maintenance_request,
    name='reassign_maintenance_request'
),

path(
    'maintenance-requests/<int:request_id>/manager-take-over/',
    manager_take_over_request,
    name='manager_take_over_request'
),

path(
    'hospital-maintenance-dashboard/',
    hospital_maintenance_dashboard,
    name='hospital_maintenance_dashboard'
),

path(
    'hospital-cssd-dashboard/',
    hospital_cssd_dashboard,
    name='hospital_cssd_dashboard'
),

    

   path(
    'maintenance-requests/<int:request_id>/approve-report/',
    approve_report,
    name='approve_report'
),

    path(
    'maintenance-requests/<int:request_id>/reject-report/',
    reject_report,
    name='reject_report'
), 

    path(
    "reports-center/",
    reports_center,
    name="reports_center"
),

path(
    "daily-report/",
    daily_report,
    name="daily_report"
),

path(
    "period-report/",
    period_report,
    name="period_report"
),
    path(
    "engineers-performance/",
    engineers_performance,
    name="engineers_performance"
),

    path(
    "maintenance-requests/<int:request_id>/approve-spare-parts/",
    approve_spare_parts,
    name="approve_spare_parts"
),

path(
    "maintenance-requests/<int:request_id>/reject-spare-parts/",
    reject_spare_parts,
    name="reject_spare_parts"
),

    path(
    "assets/<int:asset_id>/qr-sticker/",
    asset_qr_sticker,
    name="asset_qr_sticker"
),

    path(
    "asset-qr/<int:asset_id>/",
    asset_qr_access,
    name="asset_qr_access"
),

    path(
    "public-report-fault/<int:asset_id>/",
    public_report_fault,
    name="public_report_fault"
),

    path(
    "clinic-dashboard/",
    clinic_dashboard,
    name="clinic_dashboard"
),

path(
    "maintenance-requests/<int:request_id>/clinic-confirm/",
    clinic_confirm_maintenance,
    name="clinic_confirm_maintenance"
),

path(
    "clinic-assets/",
    clinic_assets,
    name="clinic_assets"
),

path(
    "clinic-waiting-parts-assets/",
    clinic_waiting_parts_assets,
    name="clinic_waiting_parts_assets"
),

path(
    "maintenance/",
    maintenance_entry,
    name="maintenance_entry"
),

    path(
    "engineer-dashboard/",
    engineer_dashboard,
    name="engineer_dashboard"
),

    path(
    "maintenance-requests/<int:request_id>/start/",
    start_maintenance_request,
    name="start_maintenance_request"
),

    path(
    "pm/<int:asset_id>/perform/",
    perform_pm,
    name="perform_pm"
),
    
    path(
    "spare-parts-tracking/",
    spare_parts_tracking,
    name="spare_parts_tracking"
),

    path(
        "pm/",
        pm_dashboard,
        name="pm_dashboard"
),

    path(
    "pm-pending-confirmation/",
    pm_pending_confirmation,
    name="pm_pending_confirmation"
),

    path(
    "pm-review/<int:pm_id>/",
    pm_review,
    name="pm_review"
),

path(
    "pm-report/<int:pm_id>/",
    ppm_service_report,
    name="ppm_service_report"
),

    path(
    "pm-report/<int:pm_id>/approve/",
    approve_pm_report,
    name="approve_pm_report"
),

    path(
    "pm-report/<int:pm_id>/reject/",
    reject_pm_report,
    name="reject_pm_report"
),

    path(
    'pending-spare-parts/',
    pending_spare_parts,
    name='pending_spare_parts'
),

path(
    'systems/',
    system_selection,
    name='system_selection'
),

    path(
    'maintenance-requests/<int:req_id>/part-received/',
    part_received,
    name='part_received'
),

path(
    'change-password/',
    auth_views.PasswordChangeView.as_view(
        template_name='cssd/change_password.html',
        success_url='/login/'
    ),
    name='change_password'
),

path(
    'maintenance-requests/',
    maintenance_requests,
    name='maintenance_requests'
),

path(
    'my-maintenance-requests/',
    my_maintenance_requests,
    name='my_maintenance_requests'
),

path(
    'maintenance-requests/<int:request_id>/service-report/',
    service_report,
    name='service_report'
),

path(
    'maintenance-requests/<int:request_id>/',
    maintenance_request_details,
    name='maintenance_request_details'
),

path(
    'maintenance-requests/<int:request_id>/complete/',
    complete_maintenance_request,
    name='complete_maintenance_request'
),


path(
    'assets/<int:asset_id>/report-fault/',
    report_fault,
    name='report_fault'
),

    path(
    'assets/',
    asset_list,
    name='asset_list'
),
path(
    'assets/<int:asset_id>/',
    asset_details,
    name='asset_details'
),

    path('admin/', admin.site.urls),

    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='cssd/login.html'
        ),
        name='login'
    ),

    path(
        'logout/',
        auth_views.LogoutView.as_view(
            next_page='login'
        ),
        name='logout'
    ),

    path('', dashboard, name='dashboard'),

    path('home/', home, name='home'),

    path('new-request/', new_request, name='new_request'),

    path(
        'get-template-items/<int:template_id>/',
        get_template_items,
        name='get_template_items'
    ),

    path(
        'cssd-pending/',
        cssd_pending_requests,
        name='cssd_pending_requests'
    ),

    path(
        'cssd-request/<int:request_id>/',
        cssd_request_details,
        name='cssd_request_details'
    ),

    path(
        'cssd-received/',
        cssd_received_requests,
        name='cssd_received_requests'
    ),

    path(
        'return-to-clinic/<int:request_id>/',
        return_to_clinic,
        name='return_to_clinic'
    ),

    path(
        'clinic-pending-returns/',
        clinic_pending_returns,
        name='clinic_pending_returns'
    ),
    path(
    'clinic-confirm-details/<int:request_id>/',
    clinic_confirm_details,
    name='clinic_confirm_details'
    ),

    path(
        'confirm-by-clinic/<int:request_id>/',
        confirm_by_clinic,
        name='confirm_by_clinic'
    ),

    path(
        'close-request/<int:request_id>/',
        close_request,
        name='close_request'
    ),

    path(
        'print-request/<int:request_id>/',
        print_request,
        name='print_request'
    ),
    path(
    'all-requests/',
    all_requests,
    name='all_requests'
),

path(
    'notifications/',
    notifications,
    name='notifications'
),

path(
    'notifications-count/',
    notifications_count,
    name='notifications_count'
),

path(
    "back-to-dashboard/",
    back_to_dashboard,
    name="back_to_dashboard"
),



path(
    'reports/',
    reports,
    name='reports'
),
path(
    'my-requests/',
    my_requests,
    name='my_requests'
),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
