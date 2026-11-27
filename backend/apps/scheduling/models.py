from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel


class Practitioner(TenantScopedModel):
    """A doctor or other provider patients can be booked with or queued for."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="practitioner",
    )
    display_name = models.CharField(max_length=120)
    title = models.CharField(max_length=80, blank=True, help_text="For example: Dentist, GP")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name


class Service(TenantScopedModel):
    """A bookable service with a default length (FR-005, FR-015)."""

    name = models.CharField(max_length=120)
    duration_minutes = models.PositiveSmallIntegerField(default=15)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["clinic", "name"], name="unique_service_per_clinic")
        ]

    def __str__(self) -> str:
        return self.name
