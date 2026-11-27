from datetime import date, datetime, timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.core.audit import record
from apps.core.models import AuditEvent
from apps.core.permissions import FRONT_DESK, MANAGERS, roles_can_write
from apps.core.viewsets import ClinicScopedViewSet

from . import booking
from .models import Appointment, Practitioner, Service, TimeOff, WorkingHours
from .serializers import (
    AppointmentSerializer,
    BookSerializer,
    CancelSerializer,
    PractitionerSerializer,
    RescheduleSerializer,
    ServiceSerializer,
    TimeOffSerializer,
    WorkingHoursSerializer,
)

MAX_RANGE_DAYS = 42


def _parse_date(value: str | None, name: str) -> date:
    try:
        return date.fromisoformat(value or "")
    except ValueError:
        raise ValidationError({name: "Use a date like 2026-12-01."}) from None


def _day_start(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=timezone.get_current_timezone())


class PractitionerViewSet(ClinicScopedViewSet):
    queryset = Practitioner.objects.all()
    serializer_class = PractitionerSerializer
    permission_classes = [roles_can_write(*MANAGERS)]

    @action(detail=True, methods=["get"])
    def slots(self, request, pk=None):
        """Free start times for one service on one day: ?date=YYYY-MM-DD&service=ID."""
        practitioner = self.get_object()
        day = _parse_date(request.query_params.get("date"), "date")
        service = Service.objects.filter(
            clinic_id=request.user.clinic_id, pk=request.query_params.get("service") or 0
        ).first()
        if service is None:
            raise ValidationError({"service": "Choose a service from this clinic."})
        slots = booking.free_slots(practitioner, service, day)
        field = serializers.DateTimeField()
        return Response({"date": day, "slots": [field.to_representation(s) for s in slots]})


class ServiceViewSet(ClinicScopedViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [roles_can_write(*MANAGERS)]


class WorkingHoursViewSet(ClinicScopedViewSet):
    """Weekly working hours. Managers set them; all clinic staff can read them (FR-010)."""

    queryset = WorkingHours.objects.select_related("practitioner")
    serializer_class = WorkingHoursSerializer
    permission_classes = [roles_can_write(*MANAGERS)]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        if practitioner := self.request.query_params.get("practitioner"):
            qs = qs.filter(practitioner_id=practitioner)
        return qs


class TimeOffViewSet(ClinicScopedViewSet):
    """Unavailability. Lists current and future time off unless ?include_past=1 (FR-010)."""

    queryset = TimeOff.objects.select_related("practitioner")
    serializer_class = TimeOffSerializer
    permission_classes = [roles_can_write(*MANAGERS)]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if practitioner := params.get("practitioner"):
            qs = qs.filter(practitioner_id=practitioner)
        if self.action == "list" and not params.get("include_past"):
            qs = qs.filter(ends_at__gt=timezone.now())
        return qs


class AppointmentViewSet(ClinicScopedViewSet):
    """Book, list, reschedule and cancel appointments (FR-011 to FR-016).

    Appointments are never deleted; they are cancelled, so the history stays complete.
    List calls need ?date_from= (and optionally ?date_to=, ?practitioner=, ?status=), or
    ?reference= to find one booking. Practitioners only see their own appointments (FR-014).
    """

    queryset = Appointment.objects.select_related("practitioner", "service")
    serializer_class = AppointmentSerializer
    permission_classes = [roles_can_write(*FRONT_DESK)]
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == Role.PRACTITIONER:
            qs = qs.filter(practitioner__user=user)
        if self.action not in ("list", "summary"):
            return qs

        params = self.request.query_params
        if ref := params.get("reference"):
            return qs.filter(reference=ref.strip().upper())
        start = _parse_date(params.get("date_from"), "date_from")
        end = _parse_date(params.get("date_to"), "date_to") if params.get("date_to") else start
        if end < start or (end - start).days >= MAX_RANGE_DAYS:
            raise ValidationError({"date_to": f"Pick a range of 1 to {MAX_RANGE_DAYS} days."})
        qs = qs.filter(
            starts_at__gte=_day_start(start), starts_at__lt=_day_start(end + timedelta(days=1))
        )
        if practitioner := params.get("practitioner"):
            qs = qs.filter(practitioner_id=practitioner)
        if statuses := params.get("status"):
            qs = qs.filter(status__in=statuses.split(","))
        return qs

    def _check_override(self, allow_outside_hours: bool):
        if allow_outside_hours and not self.request.user.has_role(*MANAGERS):
            raise PermissionDenied("Only a clinic manager can book outside working hours.")

    def _place(self, appointment, **kwargs):
        try:
            return booking.place(appointment, **kwargs)
        except booking.SlotUnavailable as exc:
            return Response(
                {"detail": exc.message, "code": exc.code}, status=status.HTTP_409_CONFLICT
            )

    def create(self, request, *args, **kwargs):
        data = BookSerializer(data=request.data, context=self.get_serializer_context())
        data.is_valid(raise_exception=True)
        v = data.validated_data
        self._check_override(v["allow_outside_hours"])
        appt = Appointment(
            clinic_id=request.user.clinic_id,
            patient_name=v["patient_name"],
            patient_phone=v.get("patient_phone", ""),
            created_by=request.user,
        )
        result = self._place(
            appt,
            practitioner=v["practitioner"],
            service=v["service"],
            starts_at=v["starts_at"],
            allow_outside_hours=v["allow_outside_hours"],
        )
        if isinstance(result, Response):
            return result
        record(
            request,
            "appointment.create",
            target=appt,
            practitioner=appt.practitioner_id,
            starts_at=timezone.localtime(appt.starts_at).isoformat(),
            outside_hours=appt.outside_hours,
        )
        return Response(self.get_serializer(appt).data, status=status.HTTP_201_CREATED)

    def _require_active(self, appt):
        if not appt.is_active:
            raise ValidationError({"status": "This appointment is already closed."})

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        appt = self.get_object()
        self._require_active(appt)
        data = RescheduleSerializer(data=request.data, context=self.get_serializer_context())
        data.is_valid(raise_exception=True)
        v = data.validated_data
        self._check_override(v["allow_outside_hours"])
        before = (appt.practitioner_id, timezone.localtime(appt.starts_at).isoformat(), appt.status)
        result = self._place(
            appt,
            practitioner=v.get("practitioner", appt.practitioner),
            service=appt.service,
            starts_at=v["starts_at"],
            allow_outside_hours=v["allow_outside_hours"],
        )
        if isinstance(result, Response):
            appt.refresh_from_db()
            return result
        record(
            request,
            "appointment.reschedule",
            target=appt,
            from_practitioner=before[0],
            from_starts_at=before[1],
            from_status=before[2],
            practitioner=appt.practitioner_id,
            starts_at=timezone.localtime(appt.starts_at).isoformat(),
            outside_hours=appt.outside_hours,
        )
        return Response(self.get_serializer(appt).data)

    def _set_status(self, request, appt, new_status, **detail):
        old = appt.status
        appt.status = new_status
        appt.save(update_fields=["status", "cancel_reason", "updated_at"])
        record(request, "appointment.status", target=appt, from_status=old, to=new_status, **detail)
        return Response(self.get_serializer(appt).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        appt = self.get_object()
        self._require_active(appt)
        data = CancelSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        appt.cancel_reason = data.validated_data.get("reason", "")
        return self._set_status(request, appt, Appointment.Status.CANCELLED)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        appt = self.get_object()
        if appt.status != Appointment.Status.BOOKED:
            raise ValidationError({"status": "Only a booked appointment can be confirmed."})
        return self._set_status(request, appt, Appointment.Status.CONFIRMED)

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        appt = self.get_object()
        self._require_active(appt)
        if appt.starts_at > timezone.now():
            raise ValidationError({"status": "An appointment can't be missed before it starts."})
        return self._set_status(request, appt, Appointment.Status.NO_SHOW)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Every recorded change to this appointment, oldest first (FR-013)."""
        appt = self.get_object()
        events = (
            AuditEvent.objects.filter(
                clinic_id=request.user.clinic_id,
                target_type=Appointment._meta.label,
                target_id=str(appt.pk),
            )
            .select_related("actor")
            .order_by("created_at")
        )
        return Response(
            [
                {
                    "action": e.action,
                    "actor": (e.actor.get_full_name() or e.actor.username) if e.actor else None,
                    "at": serializers.DateTimeField().to_representation(e.created_at),
                    "detail": e.detail,
                }
                for e in events
            ]
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Counts by status for the same filters as the list, so totals reconcile (FR-016)."""
        counts = dict(self.get_queryset().order_by().values_list("status").annotate(n=Count("id")))
        result = {s: counts.get(s, 0) for s in Appointment.Status.values}
        result["total"] = sum(result.values())
        return Response(result)
