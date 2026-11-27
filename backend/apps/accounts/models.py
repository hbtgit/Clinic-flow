from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    """Staff roles from BRD section 3.1."""

    RECEPTIONIST = "receptionist", "Receptionist"
    PRACTITIONER = "practitioner", "Practitioner"
    CLINIC_MANAGER = "clinic_manager", "Clinic manager"
    TENANT_ADMIN = "tenant_admin", "Tenant admin"
    PLATFORM_SUPPORT = "platform_support", "Platform support"


class User(AbstractUser):
    """A staff account. Clinic staff belong to exactly one clinic; platform support to none."""

    clinic = models.ForeignKey(
        "tenants.Clinic", null=True, blank=True, on_delete=models.PROTECT, related_name="staff"
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.RECEPTIONIST)
    preferred_language = models.CharField(
        max_length=8, choices=[("en", "English"), ("am", "Amharic")], default="en"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="clinic_staff_have_clinic",
                condition=models.Q(role="platform_support") | models.Q(clinic__isnull=False),
            )
        ]

    def has_role(self, *roles: str) -> bool:
        return self.is_active and self.role in roles
