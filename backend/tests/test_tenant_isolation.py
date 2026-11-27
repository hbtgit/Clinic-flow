"""FR-001 / NFR-04: one clinic must never see or change another clinic's records."""

from apps.accounts.models import Role
from apps.scheduling.models import Practitioner


def test_list_only_shows_own_clinic(clinic_a, clinic_b, make_user, client_for):
    Practitioner.objects.create(clinic=clinic_a, display_name="Dr Abebe")
    Practitioner.objects.create(clinic=clinic_b, display_name="Dr Hana")

    res = client_for(make_user(clinic_a, Role.RECEPTIONIST)).get("/api/practitioners/")

    assert res.status_code == 200
    assert [p["display_name"] for p in res.data["results"]] == ["Dr Abebe"]


def test_other_clinic_record_by_id_is_404(clinic_a, clinic_b, manager_a, client_for):
    other = Practitioner.objects.create(clinic=clinic_b, display_name="Dr Hana")
    client = client_for(manager_a)

    assert client.get(f"/api/practitioners/{other.pk}/").status_code == 404
    assert client.patch(f"/api/practitioners/{other.pk}/", {"title": "x"}).status_code == 404
    assert client.delete(f"/api/practitioners/{other.pk}/").status_code == 404
    other.refresh_from_db()
    assert other.title == ""


def test_create_is_stamped_with_own_clinic_even_if_another_is_sent(
    clinic_a, clinic_b, manager_a, client_for
):
    res = client_for(manager_a).post(
        "/api/practitioners/", {"display_name": "Dr Meron", "clinic": clinic_b.pk}
    )

    assert res.status_code == 201
    assert Practitioner.objects.get(pk=res.data["id"]).clinic == clinic_a


def test_cannot_link_staff_account_from_another_clinic(clinic_b, manager_a, make_user, client_for):
    outsider = make_user(clinic_b, Role.PRACTITIONER)

    res = client_for(manager_a).post(
        "/api/practitioners/", {"display_name": "Dr X", "user": outsider.pk}
    )

    assert res.status_code == 400


def test_platform_support_cannot_read_clinic_data(clinic_a, make_user, client_for):
    Practitioner.objects.create(clinic=clinic_a, display_name="Dr Abebe")
    support = make_user(None, Role.PLATFORM_SUPPORT)

    assert client_for(support).get("/api/practitioners/").status_code == 403


# Schedules and appointments (FR-010 to FR-014)


def _other_clinic_schedule(clinic_b):
    from datetime import time, timedelta

    from django.utils import timezone

    from apps.scheduling.models import Appointment, Service, TimeOff, WorkingHours

    dr = Practitioner.objects.create(clinic=clinic_b, display_name="Dr Hana")
    svc = Service.objects.create(clinic=clinic_b, name="Check-up")
    hours = WorkingHours.objects.create(
        clinic=clinic_b, practitioner=dr, weekday=0, start_time=time(9), end_time=time(17)
    )
    start = timezone.now() + timedelta(days=10)
    off = TimeOff.objects.create(
        clinic=clinic_b, practitioner=dr, starts_at=start, ends_at=start + timedelta(hours=1)
    )
    appt = Appointment.objects.create(
        clinic=clinic_b,
        reference="HANA01",
        practitioner=dr,
        service=svc,
        starts_at=start + timedelta(hours=2),
        ends_at=start + timedelta(hours=3),
        patient_name="Other clinic patient",
    )
    return dr, svc, hours, off, appt


def test_schedules_and_appointments_stay_in_their_clinic(clinic_a, clinic_b, manager_a, client_for):
    _, _, hours, off, appt = _other_clinic_schedule(clinic_b)
    client = client_for(manager_a)
    day = appt.starts_at.date().isoformat()

    assert client.get("/api/working-hours/").data == []
    assert client.get("/api/time-off/").data["results"] == []
    assert client.get(f"/api/appointments/?date_from={day}").data == []
    assert client.get("/api/appointments/?reference=HANA01").data == []
    assert client.get(f"/api/appointments/summary/?date_from={day}").data["total"] == 0

    for url in (
        f"/api/working-hours/{hours.pk}/",
        f"/api/time-off/{off.pk}/",
        f"/api/appointments/{appt.pk}/",
        f"/api/appointments/{appt.pk}/history/",
    ):
        assert client.get(url).status_code == 404, url
    assert client.patch(f"/api/working-hours/{hours.pk}/", {"end_time": "18:00"}).status_code == 404
    assert client.delete(f"/api/time-off/{off.pk}/").status_code == 404
    for verb in ("cancel", "confirm", "reschedule"):
        res = client.post(f"/api/appointments/{appt.pk}/{verb}/", {"starts_at": "2030-01-01T10:00"})
        assert res.status_code == 404, verb
    assert client.patch(f"/api/appointments/{appt.pk}/", {"patient_name": "x"}).status_code == 404

    appt.refresh_from_db()
    assert appt.status == "booked" and appt.patient_name == "Other clinic patient"


def test_cannot_schedule_or_book_another_clinics_practitioner(
    clinic_a, clinic_b, manager_a, client_for
):
    from apps.scheduling.models import Service

    dr, svc_b, *_ = _other_clinic_schedule(clinic_b)
    own_svc = Service.objects.create(clinic=clinic_a, name="Check-up")
    client = client_for(manager_a)

    res = client.post(
        "/api/working-hours/",
        {"practitioner": dr.pk, "weekday": 1, "start_time": "09:00", "end_time": "12:00"},
    )
    assert res.status_code == 400
    res = client.post(
        "/api/time-off/",
        {"practitioner": dr.pk, "starts_at": "2030-01-01T09:00", "ends_at": "2030-01-01T10:00"},
    )
    assert res.status_code == 400
    res = client.post(
        "/api/appointments/",
        {
            "practitioner": dr.pk,
            "service": own_svc.pk,
            "starts_at": "2030-01-07T09:00",
            "patient_name": "X",
        },
    )
    assert res.status_code == 400
    own_dr = Practitioner.objects.create(clinic=clinic_a, display_name="Dr Abebe")
    res = client.post(
        "/api/appointments/",
        {
            "practitioner": own_dr.pk,
            "service": svc_b.pk,
            "starts_at": "2030-01-07T09:00",
            "patient_name": "X",
        },
    )
    assert res.status_code == 400
    assert client.get(f"/api/practitioners/{dr.pk}/slots/?date=2030-01-07").status_code == 404
    res = client.get(f"/api/practitioners/{own_dr.pk}/slots/?date=2030-01-07&service={svc_b.pk}")
    assert res.status_code == 400
