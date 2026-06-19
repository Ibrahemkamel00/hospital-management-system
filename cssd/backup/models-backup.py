from django.db import models
from django.contrib.auth.models import User


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

        
    ]

    

    target_group = models.CharField(max_length=30, choices=TARGET_GROUP_CHOICES)
    title = models.CharField(max_length=150)
    message = models.TextField()
    cssd_request = models.ForeignKey(CSSDRequest, on_delete=models.CASCADE, null=True, blank=True)
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

    def __str__(self):
        return f"{self.asset.asset_number} - {self.performed_at}"
    
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

    item_name = models.CharField(max_length=200)

    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.item_name

class Asset(models.Model):

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('UNDER_MAINTENANCE', 'Under Maintenance'),
        ('OUT_OF_SERVICE', 'Out Of Service'),
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
    ('WAITING_PARTS', 'Waiting Parts'),
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
        related_name='reported_maintenance_requests'
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
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='NORMAL'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='OPEN'
    )

    reported_at = models.DateTimeField(auto_now_add=True)

    closed_at = models.DateTimeField(null=True, blank=True)

    work_done = models.TextField(blank=True)

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

    def __str__(self):
        return f"MR #{self.id} - {self.asset.asset_number}"
    

