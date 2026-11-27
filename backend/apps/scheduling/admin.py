from django.contrib import admin

from .models import Appointment, Practitioner, Service, TimeOff, WorkingHours


@admin.register(Practitioner)
class PractitionerAdmin(admin.ModelAdmin):
    list_display = ["display_name", "title", "clinic", "is_active"]
    list_filter = ["clinic", "is_active"]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "duration_minutes", "clinic", "is_active"]
    list_filter = ["clinic", "is_active"]


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ["practitioner", "weekday", "start_time", "end_time", "clinic"]
    list_filter = ["clinic", "weekday"]


@admin.register(TimeOff)
class TimeOffAdmin(admin.ModelAdmin):
    list_display = ["practitioner", "starts_at", "ends_at", "reason", "clinic"]
    list_filter = ["clinic"]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Shows no patient name or phone in the list, so support browsing stays de-identified."""

    list_display = ["reference", "practitioner", "service", "starts_at", "status", "clinic"]
    list_filter = ["clinic", "status"]
    search_fields = ["reference"]
    readonly_fields = ["reference"]
