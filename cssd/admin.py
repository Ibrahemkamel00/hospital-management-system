from django.contrib import admin
from .models import (
    Location,
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
    PMTemplate,
    PMTemplateItem,
    PMHistoryItem,
)
admin.site.register(PMHistory)
admin.site.register(MaintenanceSparePart)
admin.site.register(PMTemplate)
admin.site.register(PMTemplateItem)
admin.site.register(PMHistoryItem)


class CSSDRequestTemplateInline(admin.TabularInline):
    model = CSSDRequestTemplate
    extra = 1


@admin.register(CSSDRequest)
class CSSDRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'location', 'procedure', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'location')
    search_fields = ('procedure',)
    inlines = [CSSDRequestTemplateInline]
    readonly_fields = ('status', 'created_by', 'created_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
            obj.status = 'SENT_TO_CSSD'
        super().save_model(request, obj, form, change)


admin.site.register(Location)
admin.site.register(CSSDTemplate)
admin.site.register(CSSDTemplateItem)
admin.site.register(CSSDRequestItem)
admin.site.register(Notification)
admin.site.register(Asset)
@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'asset',
        'reported_by',
        'assigned_to',
        'priority',
        'status',
        'reported_at',
    )

    list_filter = (
        'status',
        'priority',
    )

    search_fields = (
        'asset__asset_number',
        'asset__device_name',
        'fault_description',
    )

from .models import InfectionCleaningAssignment, InfectionCleaningTask, InfectionProcedureTemplate, InfectionProcedureTemplateItem

class InfectionProcedureTemplateItemInline(admin.TabularInline):
    model = InfectionProcedureTemplateItem
    extra = 0


@admin.register(InfectionProcedureTemplate)
class InfectionProcedureTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = [InfectionProcedureTemplateItemInline]


@admin.register(InfectionProcedureTemplateItem)
class InfectionProcedureTemplateItemAdmin(admin.ModelAdmin):
    list_display = ('template', 'label', 'field_name', 'sort_order', 'is_active')
    list_filter = ('template', 'is_active')
    search_fields = ('label', 'field_name')


@admin.register(InfectionCleaningAssignment)
class InfectionCleaningAssignmentAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'asset', 'nurse', 'weekday', 'is_active')
    list_filter = ('weekday', 'is_active', 'asset__location')
    search_fields = ('asset__asset_number', 'asset__department', 'asset__serial_number', 'nurse__username', 'nurse__first_name', 'nurse__last_name')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'asset':
            assigned_assets = InfectionCleaningAssignment.objects.filter(
                is_active=True,
                asset__isnull=False
            ).values_list('asset_id', flat=True)
            object_id = request.resolver_match.kwargs.get('object_id') if request.resolver_match else None
            if object_id:
                current = InfectionCleaningAssignment.objects.filter(pk=object_id).values_list('asset_id', flat=True).first()
                kwargs['queryset'] = Asset.objects.exclude(id__in=[a for a in assigned_assets if a != current]).order_by('department', 'asset_number')
            else:
                kwargs['queryset'] = Asset.objects.exclude(id__in=assigned_assets).order_by('department', 'asset_number')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(InfectionCleaningTask)
class InfectionCleaningTaskAdmin(admin.ModelAdmin):
    list_display = ('clinic_name', 'asset', 'nurse', 'due_date', 'status', 'completed_at')
    list_filter = ('status', 'due_date', 'asset__location')
    search_fields = ('asset__asset_number', 'asset__department', 'asset__serial_number', 'nurse__username', 'responsible_employee')
