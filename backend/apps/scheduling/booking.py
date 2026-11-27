"""Availability checks, free slots and the booking transaction (FR-010 to FR-013).

Every write that places an appointment in time goes through `place()`, which locks the
practitioner row first. Two receptionists booking the same practitioner therefore queue up,
and the second one sees the first one's appointment. On PostgreSQL an exclusion constraint
(migration 0003) backs this up at the database level.
"""

import secrets
from datetime import date, datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Appointment, Practitioner, Service, TimeOff, WorkingHours

SLOT_STEP = timedelta(minutes=15)
REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, easy to read aloud
REFERENCE_LENGTH = 6


class SlotUnavailable(Exception):
    """The requested time cannot be booked. `code` is stable for the web app to translate."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _local(dt: datetime) -> datetime:
    return timezone.localtime(dt)


def within_working_hours(practitioner: Practitioner, starts_at: datetime, ends_at: datetime):
    start, end = _local(starts_at), _local(ends_at)
    if start.date() != end.date():
        return False
    return WorkingHours.objects.filter(
        practitioner=practitioner,
        weekday=start.weekday(),
        start_time__lte=start.time(),
        end_time__gte=end.time(),
    ).exists()


def _overlapping(qs, starts_at, ends_at):
    return qs.filter(starts_at__lt=ends_at, ends_at__gt=starts_at)


def check_slot(
    practitioner: Practitioner,
    starts_at: datetime,
    ends_at: datetime,
    *,
    exclude: Appointment | None = None,
    allow_outside_hours: bool = False,
) -> bool:
    """Raise SlotUnavailable if the time cannot be booked. Return True if it is outside hours."""
    if not practitioner.is_active:
        raise SlotUnavailable("practitioner_inactive", "This practitioner is not taking bookings.")
    if starts_at < timezone.now():
        raise SlotUnavailable("in_past", "That time has already passed.")

    if _overlapping(TimeOff.objects.filter(practitioner=practitioner), starts_at, ends_at).exists():
        raise SlotUnavailable("time_off", "The practitioner is unavailable at that time.")

    clashes = _overlapping(
        Appointment.objects.filter(practitioner=practitioner, status__in=Appointment.ACTIVE),
        starts_at,
        ends_at,
    )
    if exclude is not None:
        clashes = clashes.exclude(pk=exclude.pk)
    if clashes.exists():
        raise SlotUnavailable("conflict", "The practitioner already has an appointment then.")

    outside = not within_working_hours(practitioner, starts_at, ends_at)
    if outside and not allow_outside_hours:
        raise SlotUnavailable("outside_hours", "That time is outside the practitioner's hours.")
    return outside


def _new_reference(clinic_id: int) -> str:
    while True:
        ref = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(REFERENCE_LENGTH))
        if not Appointment.objects.filter(clinic_id=clinic_id, reference=ref).exists():
            return ref


def place(
    appointment: Appointment,
    *,
    practitioner: Practitioner,
    service: Service,
    starts_at: datetime,
    allow_outside_hours: bool = False,
) -> Appointment:
    """Book a new appointment, or move an existing one, without ever double-booking."""
    if not service.is_active:
        raise SlotUnavailable("service_inactive", "This service is no longer offered.")
    ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    with transaction.atomic():
        # The lock serialises bookings per practitioner (FR-012).
        practitioner = Practitioner.objects.select_for_update().get(pk=practitioner.pk)
        existing = appointment if appointment.pk else None
        outside = check_slot(
            practitioner,
            starts_at,
            ends_at,
            exclude=existing,
            allow_outside_hours=allow_outside_hours,
        )
        appointment.practitioner = practitioner
        appointment.service = service
        appointment.starts_at = starts_at
        appointment.ends_at = ends_at
        appointment.outside_hours = outside
        if existing is None:
            appointment.reference = _new_reference(appointment.clinic_id)
        else:
            appointment.status = Appointment.Status.BOOKED  # a new time needs confirming again
        try:
            with transaction.atomic():
                appointment.save()
        except IntegrityError as exc:
            if "appointment_no_overlap" in str(exc):
                raise SlotUnavailable(
                    "conflict", "The practitioner already has an appointment then."
                ) from exc
            raise
    return appointment


def free_slots(practitioner: Practitioner, service: Service, day: date) -> list[datetime]:
    """Start times on `day` when `service` fits with this practitioner, in clinic local time."""
    if not practitioner.is_active or not service.is_active:
        return []
    tz = timezone.get_current_timezone()
    length = timedelta(minutes=service.duration_minutes)
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    busy = [
        (a.starts_at, a.ends_at)
        for a in _overlapping(
            Appointment.objects.filter(practitioner=practitioner, status__in=Appointment.ACTIVE),
            day_start,
            day_end,
        )
    ]
    busy += [
        (t.starts_at, t.ends_at)
        for t in _overlapping(TimeOff.objects.filter(practitioner=practitioner), day_start, day_end)
    ]
    now = timezone.now()

    slots = []
    for block in WorkingHours.objects.filter(practitioner=practitioner, weekday=day.weekday()):
        t = datetime.combine(day, block.start_time, tzinfo=tz)
        block_end = datetime.combine(day, block.end_time, tzinfo=tz)
        while t + length <= block_end:
            end = t + length
            if t >= now and not any(b0 < end and b1 > t for b0, b1 in busy):
                slots.append(t)
            t += SLOT_STEP
    return sorted(set(slots))
