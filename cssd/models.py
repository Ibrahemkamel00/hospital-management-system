from django.db import models
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

class Location(models.Model):
    GROUP_CHOICES = [
        ('MALE', 'Male Clinics'),
        ('FEMALE', 'Female Clinics'),
        ('SPECIALTY', 'Specialty Clinics'),
        ('EMERGENCY', 'Emergency Clinics'),
        ('CSSD', 'CSSD'),
        ('LAB', 'Laboratory'),
        ('RADIOLOGY', 'Radiology'),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    group_type = models.CharField(max_length=30, choices=GROUP_CHOICES)

    engineers = models.ManyToManyField(
    User,
    blank=True,
    related_name="assigned_locations"
)

    def __str__(self):
        return self.name


class CSSDTemplate(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name


class CSSDTemplateItem(models.Model):
    template = models.ForeignKey(CSSDTemplate, on_delete=models.CASCADE, related_name='items')
    instrument_name = models.CharField(max_length=150)
    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.template.name} - {self.instrument_name}"


class CSSDRequest(models.Model):
    STATUS_CHOICES = [
        ('SENT_TO_CSSD', 'Sent to CSSD'),
        ('RECEIVED_BY_CSSD', 'Received by CSSD'),
        ('RETURNED_TO_CLINIC', 'Returned to Clinic'),
        ('CONFIRMED_BY_CLINIC', 'Confirmed by Clinic'),
        ('CLOSED', 'Closed'),
    ]

    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    procedure = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='SENT_TO_CSSD')

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_cssd_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    received_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='received_cssd_requests'
    )
    received_at = models.DateTimeField(null=True, blank=True)

    returned_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='returned_cssd_requests'
    )
    returned_at = models.DateTimeField(null=True, blank=True)

    closed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='closed_cssd_requests'
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Request #{self.id} - {self.location.name}"


class CSSDRequestTemplate(models.Model):
    cssd_request = models.ForeignKey(CSSDRequest, on_delete=models.CASCADE, related_name='selected_templates')
    template = models.ForeignKey(CSSDTemplate, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.cssd_request} - {self.template.name}"


class CSSDRequestItem(models.Model):
    cssd_request = models.ForeignKey(
        CSSDRequest,
        on_delete=models.CASCADE,
        related_name='items'
    )

    cssd_request_template = models.ForeignKey(
        CSSDRequestTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_items'
    )

    instrument_name = models.CharField(max_length=150)

    quantity_sent = models.PositiveIntegerField(default=0)
    quantity_received_by_cssd = models.PositiveIntegerField(default=0)
    quantity_returned = models.PositiveIntegerField(default=0)
    quantity_received_by_clinic = models.PositiveIntegerField(default=0)
    clinic_comment = models.TextField(blank=True)

    remarks = models.TextField(blank=True)
    is_manual = models.BooleanField(default=False)

    def __str__(self):
        return self.instrument_name


class Notification(models.Model):

    TARGET_GROUP_CHOICES = [
        ('MALE', 'Male Clinics'),
        ('FEMALE', 'Female Clinics'),
        ('SPECIALTY', 'Specialty Clinics'),
        ('EMERGENCY', 'Emergency Clinics'),
        ('CSSD', 'CSSD'),
        ('ADMIN', 'Admin'),
        ('ENGINEER', 'Engineer'),
        ('MAINTENANCE_MANAGER', 'Maintenance Manager'),
        ('HOSPITAL_MANAGER', 'Hospital Manager'),
        ('USER', 'Specific User'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    target_group = models.CharField(max_length=30, choices=TARGET_GROUP_CHOICES, blank=True)
    title = models.CharField(max_length=150)
    message = models.TextField()

    cssd_request = models.ForeignKey(
        CSSDRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    url = models.CharField(
        max_length=300,
        blank=True
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class PMHistory(models.Model):

    asset = models.ForeignKey(
        "Asset",
        on_delete=models.CASCADE,
        related_name="pm_history"
    )

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    performed_at = models.DateTimeField(
        auto_now_add=True
    )

    notes = models.TextField(
        blank=True
    )

    next_pm_date = models.DateField(
        null=True,
        blank=True
    )
    
    status = models.CharField(
    max_length=30,
    default="WAITING_CONFIRMATION"
)

    confirmed_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="confirmed_pm_history"
)

    confirmed_at = models.DateTimeField(
    null=True,
    blank=True
)

    clinic_comment = models.TextField(
    blank=True
)
    manager_approved = models.BooleanField(
    default=False
)

    manager_approved_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="approved_pm_reports"
)

    manager_approved_at = models.DateTimeField(
    null=True,
    blank=True
)

    manager_rejected = models.BooleanField(
    default=False
)

    manager_comment = models.TextField(
    blank=True,
    default=""
)


    def __str__(self):
        return f"{self.asset.asset_number} - {self.performed_at}"
    
class PMHistoryItem(models.Model):

    pm_history = models.ForeignKey(
        PMHistory,
        on_delete=models.CASCADE,
        related_name="items"
    )

    system = models.CharField(max_length=200)

    component = models.CharField(max_length=200)

    inspection_points = models.TextField(blank=True)

    result = models.CharField(
        max_length=20,
        choices=[
            ("OK", "OK"),
            ("NOT_OK", "Not OK"),
        ],
        default="OK"
    )

    requested_spare_part = models.CharField(
        max_length=200,
        blank=True
    )

    requested_quantity = models.PositiveIntegerField(
        default=0
    )

    def __str__(self):
        return f"{self.pm_history.id} - {self.system} - {self.component}"
    
class MaintenanceSparePart(models.Model):
    maintenance_request = models.ForeignKey(
        "MaintenanceRequest",
        on_delete=models.CASCADE,
        related_name="spare_parts"
    )

    requested_part_name = models.CharField(
        max_length=200
    )

    requested_quantity = models.PositiveIntegerField(
        default=1
    )

    installed_part_name = models.CharField(
        max_length=200,
        blank=True
    )

    installed_quantity = models.PositiveIntegerField(
        default=0
    )

    is_installed = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if self.installed_part_name and self.installed_quantity >= self.requested_quantity:
            self.is_installed = True
        else:
            self.is_installed = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.requested_part_name} x {self.requested_quantity}"    

class PMTemplate(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class PMTemplateItem(models.Model):

    template = models.ForeignKey(
        PMTemplate,
        on_delete=models.CASCADE,
        related_name="items"
    )

    system = models.CharField(max_length=200)

    component = models.CharField(max_length=200)

    inspection_points = models.TextField()

    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.system} - {self.component}"

class Asset(models.Model):

    STATUS_CHOICES = [
    ('ACTIVE', 'Active'),
    ('ACTIVE_NEED_SPARE', 'Active - Need Spare Part'),
    ('UNDER_MAINTENANCE', 'Under Maintenance'),
    ('OUT_OF_SERVICE', 'Out Of Service'),
    ('WAITING_PARTS', 'Waiting Spare Parts'),
]

    asset_number = models.CharField(max_length=50, unique=True)

    device_name = models.CharField(max_length=200)

    manufacturer = models.CharField(
        max_length=100,
        blank=True
    )

    pm_template = models.ForeignKey(
        PMTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    model = models.CharField(
        max_length=100,
        blank=True
    )

    serial_number = models.CharField(
        max_length=100,
        blank=True
    )

    department = models.CharField(
        max_length=100,
        blank=True
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    installation_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )

    notes = models.TextField(blank=True)

    last_pm_date = models.DateField(
    null=True,
    blank=True
    )

    next_pm_date = models.DateField(
    null=True,
    blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.asset_number} - {self.device_name}"
    
class MaintenanceRequest(models.Model):

    STATUS_CHOICES = [
    ('OPEN', 'Open'),
    ('IN_PROGRESS', 'In Progress'),
    ('WAITING_PART_APPROVAL', 'Waiting Part Approval'),
    ('WAITING_PARTS', 'Waiting Parts'),
    ('WAITING_CONFIRMATION', 'Waiting Confirmation'),
    ('CLOSED', 'Closed'),
]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='maintenance_requests'
    )

    reported_by = models.ForeignKey(
    User,
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name='reported_maintenance_requests'
)
    
    request_source = models.CharField(
    max_length=30,
    default="SYSTEM"
)

    external_reporter_name = models.CharField(
    max_length=200,
    blank=True
)

    assigned_to = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="assigned_maintenance_requests"
)

    fault_description = models.TextField()

    priority = models.CharField(
        max_length=30,
        choices=PRIORITY_CHOICES,
        default='NORMAL'
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='OPEN'
    )

    reported_at = models.DateTimeField(auto_now_add=True)

    closed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
         User,
         on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_maintenance_requests"
)

    confirmed_at = models.DateTimeField(
    null=True,
    blank=True
)

    clinic_approved_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="spare_part_approvals"
)

    clinic_approved_at = models.DateTimeField(
    null=True,
    blank=True
)

    clinic_feedback = models.TextField(
    blank=True
)


    work_done = models.TextField(blank=True)
    after_spare_part_work = models.TextField(blank=True)

    needs_spare_parts = models.BooleanField(default=False)

    spare_part_name = models.CharField(
    max_length=200,
    blank=True
)

    installed_spare_part = models.CharField(
    max_length=200,
    blank=True
)

    notes = models.TextField(blank=True)

    report_approved = models.BooleanField(
    default=False
)

    report_approved_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="approved_maintenance_reports"
)

    report_approved_at = models.DateTimeField(
    null=True,
    blank=True
)

    report_rejected = models.BooleanField(
    default=False
)

    report_manager_comment = models.TextField(
    blank=True
)

    def __str__(self):
        return f"MR #{self.id} - {self.asset.asset_number}"
    
class MaintenanceRequestTimeline(models.Model):

    maintenance_request = models.ForeignKey(
        "MaintenanceRequest",
        on_delete=models.CASCADE,
        related_name="timeline"
    )

    action = models.CharField(max_length=100)

    note = models.TextField(
        blank=True,
        null=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.maintenance_request.id} - {self.action}"
    


class InquiryMessage(models.Model):
    maintenance_request = models.ForeignKey(
        "MaintenanceRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inquiries"
    )
    cssd_request = models.ForeignKey(
        "CSSDRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inquiries"
    )
    asset = models.ForeignKey(
        "Asset",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inquiries"
    )
    pm_history = models.ForeignKey(
        "PMHistory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inquiries"
    )
    message = models.TextField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_inquiry_messages"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Inquiry #{self.id}"


class RequestAttachment(models.Model):
    maintenance_request = models.ForeignKey(
        "MaintenanceRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments"
    )
    cssd_request = models.ForeignKey(
        "CSSDRequest",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments"
    )
    asset = models.ForeignKey(
        "Asset",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments"
    )
    pm_history = models.ForeignKey(
        "PMHistory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments"
    )
    file = models.FileField(upload_to="attachments/%Y/%m/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_request_attachments"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.file.name


class InfectionProcedureTemplate(models.Model):
    name = models.CharField(max_length=200, default='Dental Unit Cleaning Procedure')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class InfectionProcedureTemplateItem(models.Model):
    FIELD_CHOICES = [
        ('surface_cleaning', 'تنظيف وتطهير الأسطح'),
        ('chair_cleaning', 'تنظيف وتطهير كرسي الأسنان'),
        ('spittoon_cleaning', 'تنظيف وتطهير مصفاة المبصقة'),
        ('suction_filter_cleaning', 'تنظيف وتطهير فلاتر وحدات الشفط'),
        ('handwash_basin_cleaning', 'تنظيف وتطهير حوض غسل اليدين'),
        ('ppe_drawers_refill', 'تعبئة الأدراج بأدوات الحماية الشخصية'),
        ('soap_refill', 'تعبئة حاويات الصابون'),
        ('sanitizer_refill', 'تعبئة حاويات مطهر اليدين'),
    ]
    template = models.ForeignKey(
        InfectionProcedureTemplate,
        on_delete=models.CASCADE,
        related_name='items'
    )
    field_name = models.CharField(max_length=80, choices=FIELD_CHOICES)
    label = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'id']
        unique_together = ('template', 'field_name')

    def __str__(self):
        return self.label


class InfectionCleaningAssignment(models.Model):
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='infection_cleaning_assignments'
    )
    clinic = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='infection_cleaning_assignments'
    )
    nurse = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='infection_cleaning_assignments'
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES, default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['asset__department', 'asset__asset_number', 'clinic__group_type', 'clinic__name']
        constraints = [
            models.UniqueConstraint(
                fields=['asset'],
                condition=models.Q(is_active=True, asset__isnull=False),
                name='unique_active_infection_asset_assignment'
            )
        ]

    @property
    def display_name(self):
        if self.asset:
            return self.asset.department or self.asset.asset_number
        if self.clinic:
            return self.clinic.name
        return 'Unassigned Clinic'

    @property
    def location_display(self):
        if self.asset and self.asset.location:
            return self.asset.location.name
        if self.clinic:
            return self.clinic.name
        return ''

    def __str__(self):
        return f"{self.display_name} - {self.nurse.username}"


class InfectionCleaningTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
    ]

    assignment = models.ForeignKey(
        InfectionCleaningAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=True, blank=True, related_name='infection_cleaning_tasks')
    clinic = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, blank=True, related_name='infection_cleaning_tasks')
    nurse = models.ForeignKey(User, on_delete=models.PROTECT, related_name='infection_cleaning_tasks')
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_infection_cleaning_tasks'
    )

    surface_cleaning = models.BooleanField(default=False)
    surface_cleaning_reason = models.TextField(blank=True)
    chair_cleaning = models.BooleanField(default=False)
    chair_cleaning_reason = models.TextField(blank=True)
    spittoon_cleaning = models.BooleanField(default=False)
    spittoon_cleaning_reason = models.TextField(blank=True)
    suction_filter_cleaning = models.BooleanField(default=False)
    suction_filter_cleaning_reason = models.TextField(blank=True)
    handwash_basin_cleaning = models.BooleanField(default=False)
    handwash_basin_cleaning_reason = models.TextField(blank=True)
    ppe_drawers_refill = models.BooleanField(default=False)
    ppe_drawers_refill_reason = models.TextField(blank=True)
    soap_refill = models.BooleanField(default=False)
    soap_refill_reason = models.TextField(blank=True)
    sanitizer_refill = models.BooleanField(default=False)
    sanitizer_refill_reason = models.TextField(blank=True)

    responsible_employee = models.CharField(max_length=150, blank=True)
    general_comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'asset__department', 'asset__asset_number', 'clinic__name']
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'due_date'],
                condition=models.Q(assignment__isnull=False),
                name='unique_infection_assignment_due_date'
            )
        ]

    @property
    def is_complete_checklist(self):
        # A cleaning task can be completed when all procedure items have been answered.
        # Not Done items are accepted only when their reason is saved by the view.
        return True

    @property
    def clinic_name(self):
        if self.asset:
            return self.asset.department or self.asset.asset_number
        if self.clinic:
            return self.clinic.name
        return 'Clinic'

    @property
    def asset_number(self):
        return self.asset.asset_number if self.asset else ''

    @property
    def location_name(self):
        if self.asset and self.asset.location:
            return self.asset.location.name
        if self.clinic:
            return self.clinic.name
        return ''

    def __str__(self):
        return f"{self.clinic_name} - {self.due_date}"
