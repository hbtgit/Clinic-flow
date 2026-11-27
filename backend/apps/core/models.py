from django.conf import settings
from django.db import models


class ClinicQuerySet(models.QuerySet):
    def for_clinic(self, clinic):
        return self.filter(clinic=clinic)


class TenantScopedModel(models.Model):
    """Base for every record that belongs to one clinic.

    Always read these through ClinicScopedViewSet or `.for_clinic()`, never `.all()` in a view.
    """

    clinic = models.ForeignKey("tenants.Clinic", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ClinicQuerySet.as_manager()

    class Meta:
        abstract = True


class AuditEvent(models.Model):
    """Who did what, in which clinic, to which record, and when (FR-004, NFR-05)."""

    clinic = models.ForeignKey(
        "tenants.Clinic", null=True, on_delete=models.PROTECT, related_name="+"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["clinic", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action}"
