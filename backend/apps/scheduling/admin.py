from django.contrib import admin

from .models import Practitioner, Service


@admin.register(Practitioner)
class PractitionerAdmin(admin.ModelAdmin):
    list_display = ["display_name", "title", "clinic", "is_active"]
    list_filter = ["clinic", "is_active"]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "duration_minutes", "clinic", "is_active"]
    list_filter = ["clinic", "is_active"]
