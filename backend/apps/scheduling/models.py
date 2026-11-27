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


class WorkingHours(TenantScopedModel):
    """One block of weekly working time. Two blocks on the same day leave a break between them.

    Times are clinic local time (Africa/Addis_Ababa). Time outside every block is not bookable
    (FR-010).
    """

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    practitioner = models.ForeignKey(
        Practitioner, on_delete=models.CASCADE, related_name="working_hours"
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["practitioner", "weekday", "start_time"]
        verbose_name_plural = "working hours"
        constraints = [
            models.CheckConstraint(
                name="working_hours_end_after_start",
                condition=models.Q(end_time__gt=models.F("start_time")),
            )
        ]

    def __str__(self) -> str:
        return f"{self.practitioner} {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class TimeOff(TenantScopedModel):
    """A stretch when a practitioner cannot be booked: leave, a meeting, running late (FR-010)."""

    practitioner = models.ForeignKey(
        Practitioner, on_delete=models.CASCADE, related_name="time_off"
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["starts_at"]
        verbose_name_plural = "time off"
        constraints = [
            models.CheckConstraint(
                name="time_off_end_after_start",
                condition=models.Q(ends_at__gt=models.F("starts_at")),
            )
        ]

    def __str__(self) -> str:
        return f"{self.practitioner} off {self.starts_at:%Y-%m-%d %H:%M}"


class Appointment(TenantScopedModel):
    """A booked visit with one practitioner for one service (FR-011 to FR-016).

    Only the minimum patient details are kept: a name or alias and, if needed, a phone number
    (BRD 7.2). Never add clinical fields here (FR-023).
    """

    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    # Appointments in these states hold their slot. Cancelled and no-show ones release it.
    ACTIVE = (Status.BOOKED, Status.CONFIRMED)

    reference = models.CharField(max_length=8, editable=False)
    practitioner = models.ForeignKey(
        Practitioner, on_delete=models.PROTECT, related_name="appointments"
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="appointments")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.BOOKED)
    patient_name = models.CharField(max_length=120)
    patient_phone = models.CharField(max_length=16, blank=True)
    outside_hours = models.BooleanField(
        default=False, help_text="Booked outside working hours by a manager override."
    )
    cancel_reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "reference"], name="unique_appointment_reference_per_clinic"
            ),
            models.CheckConstraint(
                name="appointment_end_after_start",
                condition=models.Q(ends_at__gt=models.F("starts_at")),
            ),
        ]
        indexes = [
            models.Index(fields=["clinic", "starts_at"]),
            models.Index(fields=["practitioner", "starts_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference} {self.starts_at:%Y-%m-%d %H:%M}"

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE
