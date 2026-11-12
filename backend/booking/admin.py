from django.contrib import admin

from .models import Appointment, DayOff, Service, WorkingHours


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "duration_minutes", "price", "active", "position"]
    list_editable = ["active", "position"]
    search_fields = ["name"]


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ["weekday", "opens", "closes"]
    list_filter = ["weekday"]


@admin.register(DayOff)
class DayOffAdmin(admin.ModelAdmin):
    list_display = ["date", "reason"]
    date_hierarchy = "date"


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Samo pregled: termini nastaju i otkazuju se kroz aplikaciju, gdje vrijede pravila."""

    list_display = ["starts_at", "service", "customer_name", "customer_phone", "status"]
    list_filter = ["status", "service"]
    search_fields = ["customer_name", "customer_phone", "customer_email"]
    date_hierarchy = "starts_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
