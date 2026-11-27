import re

from rest_framework import serializers

from .models import Appointment, Practitioner, Service, TimeOff, WorkingHours


class ClinicRelatedField(serializers.PrimaryKeyRelatedField):
    """A foreign key that only accepts records from the signed-in user's clinic (FR-001)."""

    def get_queryset(self):
        return super().get_queryset().filter(clinic_id=self.context["request"].user.clinic_id)


class PractitionerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Practitioner
        fields = ["id", "display_name", "title", "is_active", "user"]

    def validate_user(self, user):
        if user and user.clinic_id != self.context["request"].user.clinic_id:
            raise serializers.ValidationError("That staff account is not in this clinic.")
        return user


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "duration_minutes", "is_active"]

    def validate_name(self, name):
        clinic_id = self.context["request"].user.clinic_id
        clash = Service.objects.filter(clinic_id=clinic_id, name__iexact=name)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("This clinic already has a service with that name.")
        return name


class WorkingHoursSerializer(serializers.ModelSerializer):
    practitioner = ClinicRelatedField(queryset=Practitioner.objects.all())

    class Meta:
        model = WorkingHours
        fields = ["id", "practitioner", "weekday", "start_time", "end_time"]

    def validate(self, attrs):
        get = lambda f: attrs.get(f, getattr(self.instance, f, None))  # noqa: E731
        start, end = get("start_time"), get("end_time")
        if start >= end:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        overlap = WorkingHours.objects.filter(
            practitioner=get("practitioner"),
            weekday=get("weekday"),
            start_time__lt=end,
            end_time__gt=start,
        )
        if self.instance is not None:
            overlap = overlap.exclude(pk=self.instance.pk)
        if overlap.exists():
            raise serializers.ValidationError(
                {"start_time": "This overlaps other working hours on that day."}
            )
        return attrs


class TimeOffSerializer(serializers.ModelSerializer):
    practitioner = ClinicRelatedField(queryset=Practitioner.objects.all())
    clashing_appointments = serializers.SerializerMethodField(
        help_text="References of active appointments inside this time off, to reschedule."
    )

    class Meta:
        model = TimeOff
        fields = [
            "id",
            "practitioner",
            "starts_at",
            "ends_at",
            "reason",
            "created_by",
            "clashing_appointments",
        ]
        read_only_fields = ["created_by"]

    def validate(self, attrs):
        get = lambda f: attrs.get(f, getattr(self.instance, f, None))  # noqa: E731
        if get("starts_at") >= get("ends_at"):
            raise serializers.ValidationError({"ends_at": "End must be after start."})
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def get_clashing_appointments(self, obj):
        return list(
            Appointment.objects.filter(
                practitioner=obj.practitioner,
                status__in=Appointment.ACTIVE,
                starts_at__lt=obj.ends_at,
                ends_at__gt=obj.starts_at,
            ).values_list("reference", flat=True)
        )


PHONE_RE = re.compile(r"^(?:\+?251|0)?([79]\d{8})$")


def normalise_phone(value: str) -> str:
    """Accept 09.., 07.., 2519.. or +2519.. and store +251XXXXXXXXX."""
    if not value:
        return ""
    digits = re.sub(r"[\s\-()]", "", value)
    match = PHONE_RE.match(digits)
    if not match:
        raise serializers.ValidationError("Enter an Ethiopian mobile number, like 0911 234 567.")
    return f"+251{match.group(1)}"


class AppointmentSerializer(serializers.ModelSerializer):
    """Read view of an appointment. Only the patient's name and phone can be edited here."""

    practitioner_name = serializers.CharField(source="practitioner.display_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "reference",
            "practitioner",
            "practitioner_name",
            "service",
            "service_name",
            "starts_at",
            "ends_at",
            "status",
            "patient_name",
            "patient_phone",
            "outside_hours",
            "cancel_reason",
            "created_at",
        ]
        read_only_fields = [f for f in fields if f not in ("patient_name", "patient_phone")]

    def validate_patient_phone(self, value):
        return normalise_phone(value)


class BookSerializer(serializers.Serializer):
    practitioner = ClinicRelatedField(queryset=Practitioner.objects.all())
    service = ClinicRelatedField(queryset=Service.objects.all())
    starts_at = serializers.DateTimeField()
    patient_name = serializers.CharField(max_length=120)
    patient_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    allow_outside_hours = serializers.BooleanField(default=False)

    def validate_patient_phone(self, value):
        return normalise_phone(value)


class RescheduleSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    practitioner = ClinicRelatedField(queryset=Practitioner.objects.all(), required=False)
    allow_outside_hours = serializers.BooleanField(default=False)


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)
