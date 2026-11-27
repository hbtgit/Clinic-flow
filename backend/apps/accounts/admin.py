from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "clinic", "role", "is_active"]
    list_filter = ["role", "clinic", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Clinic", {"fields": ["clinic", "role", "preferred_language"]}),
    )
