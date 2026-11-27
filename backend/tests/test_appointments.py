"""FR-010 to FR-016: working hours, booking without double-booking, reschedule and cancel."""

import threading

import pytest
from django.db import IntegrityError, connection, connections

from apps.accounts.models import Role
from apps.core.models import AuditEvent
from apps.scheduling import booking
from apps.scheduling.models import Appointment, Practitioner, TimeOff


def book(client, dr, svc, starts_at, **extra):
    return client.post(
        "/api/appointments/",
        {
            "practitioner": dr.pk,
            "service": svc.pk,
            "starts_at": starts_at.isoformat(),
            "patient_name": "Almaz T.",
            **extra,
        },
        format="json",
    )


# FR-011: booking


def test_receptionist_books_and_gets_a_reference(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    res = book(client_for(receptionist_a), dr, svc, at("09:00"), patient_phone="0911 234 567")

    assert res.status_code == 201, res.data
    assert len(res.data["reference"]) == 6
    assert res.data["status"] == "booked"
    assert res.data["patient_phone"] == "+251911234567"
    appt = Appointment.objects.get(pk=res.data["id"])
    assert appt.ends_at == at("09:30")
    assert appt.created_by == receptionist_a
    assert AuditEvent.objects.filter(action="appointment.create", target_id=str(appt.pk)).exists()


def test_references_are_unique(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    client = client_for(receptionist_a)
    refs = {book(client, dr, svc, at(f"{h}:00")).data["reference"] for h in (9, 10, 11, 13)}
    assert len(refs) == 4


def test_bad_phone_is_rejected(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    res = book(client_for(receptionist_a), dr, svc, at("09:00"), patient_phone="12345")
    assert res.status_code == 400
    assert "patient_phone" in res.data


def test_booking_appears_in_day_and_week_views(
    schedule, at, next_monday, receptionist_a, client_for
):
    dr, svc = schedule
    client = client_for(receptionist_a)
    book(client, dr, svc, at("09:00"))
    book(client, dr, svc, at("10:00", days=-1 + 7))  # the following Sunday: outside the day view

    day = client.get(f"/api/appointments/?date_from={next_monday}")
    assert [a["starts_at"][11:16] for a in day.data] == ["09:00"]
    assert day.data[0]["practitioner_name"] == "Dr Abebe"


def test_list_needs_a_date_range(receptionist_a, client_for, db):
    client = client_for(receptionist_a)
    assert client.get("/api/appointments/").status_code == 400
    res = client.get("/api/appointments/?date_from=2026-12-01&date_to=2027-03-01")
    assert res.status_code == 400


# FR-010: working hours, breaks and time off


@pytest.mark.parametrize(
    ("start", "code"),
    [("08:30", "outside_hours"), ("11:45", "outside_hours"), ("12:15", "outside_hours")],
)
def test_time_outside_hours_or_in_the_break_is_refused(
    schedule, at, receptionist_a, client_for, start, code
):
    dr, svc = schedule
    res = book(client_for(receptionist_a), dr, svc, at(start))
    assert res.status_code == 409
    assert res.data["code"] == code


def test_time_off_is_not_bookable(schedule, at, clinic_a, receptionist_a, client_for):
    dr, svc = schedule
    TimeOff.objects.create(
        clinic=clinic_a, practitioner=dr, starts_at=at("10:00"), ends_at=at("11:00")
    )
    res = book(client_for(receptionist_a), dr, svc, at("10:30"))
    assert res.status_code == 409
    assert res.data["code"] == "time_off"


def test_past_time_is_refused(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    res = book(client_for(receptionist_a), dr, svc, at("09:00", days=-21))
    assert res.status_code == 409
    assert res.data["code"] == "in_past"


def test_slots_skip_break_time_off_and_bookings(
    schedule, at, next_monday, clinic_a, receptionist_a, client_for
):
    dr, svc = schedule
    client = client_for(receptionist_a)
    book(client, dr, svc, at("09:00"))
    TimeOff.objects.create(
        clinic=clinic_a, practitioner=dr, starts_at=at("14:00"), ends_at=at("17:00")
    )

    res = client.get(f"/api/practitioners/{dr.pk}/slots/?date={next_monday}&service={svc.pk}")

    times = [s[11:16] for s in res.data["slots"]]
    assert times[:3] == ["09:30", "09:45", "10:00"]
    assert "09:15" not in times  # would overlap the 09:00 booking
    assert "11:30" in times and "11:45" not in times  # must finish by the 12:00 break
    assert "12:30" not in times
    assert times[-1] == "13:30"  # time off from 14:00


def test_inactive_practitioner_has_no_slots(schedule, next_monday, receptionist_a, client_for):
    dr, svc = schedule
    dr.is_active = False
    dr.save()
    res = client_for(receptionist_a).get(
        f"/api/practitioners/{dr.pk}/slots/?date={next_monday}&service={svc.pk}"
    )
    assert res.data["slots"] == []


def test_manager_can_override_hours_and_it_is_flagged(schedule, at, manager_a, client_for):
    dr, svc = schedule
    res = book(client_for(manager_a), dr, svc, at("18:00"), allow_outside_hours=True)

    assert res.status_code == 201
    assert res.data["outside_hours"] is True
    event = AuditEvent.objects.get(action="appointment.create")
    assert event.detail["outside_hours"] is True


def test_receptionist_cannot_override_hours(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    res = book(client_for(receptionist_a), dr, svc, at("18:00"), allow_outside_hours=True)
    assert res.status_code == 403


def test_overlapping_working_hours_are_rejected(schedule, manager_a, client_for):
    dr, _ = schedule
    res = client_for(manager_a).post(
        "/api/working-hours/",
        {"practitioner": dr.pk, "weekday": 0, "start_time": "11:00", "end_time": "14:00"},
    )
    assert res.status_code == 400


def test_time_off_lists_appointments_to_move(schedule, at, manager_a, client_for):
    dr, svc = schedule
    client = client_for(manager_a)
    ref = book(client, dr, svc, at("10:00")).data["reference"]

    res = client.post(
        "/api/time-off/",
        {
            "practitioner": dr.pk,
            "starts_at": at("09:00").isoformat(),
            "ends_at": at("12:00").isoformat(),
            "reason": "Conference",
        },
        format="json",
    )

    assert res.status_code == 201
    assert res.data["clashing_appointments"] == [ref]
    assert TimeOff.objects.get().created_by == manager_a
    assert AuditEvent.objects.filter(action="timeoff.create").exists()


@pytest.mark.parametrize("role", [Role.RECEPTIONIST, Role.PRACTITIONER])
def test_only_managers_change_schedules(schedule, role, clinic_a, make_user, client_for):
    dr, _ = schedule
    client = client_for(make_user(clinic_a, role))
    assert client.get("/api/working-hours/").status_code == 200
    res = client.post(
        "/api/working-hours/",
        {"practitioner": dr.pk, "weekday": 1, "start_time": "09:00", "end_time": "12:00"},
    )
    assert res.status_code == 403


# FR-012: no double-booking


def test_same_slot_twice_is_refused(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    client = client_for(receptionist_a)
    assert book(client, dr, svc, at("09:00")).status_code == 201

    res = book(client, dr, svc, at("09:15"))

    assert res.status_code == 409
    assert res.data["code"] == "conflict"
    assert Appointment.objects.count() == 1


def test_back_to_back_is_fine(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    client = client_for(receptionist_a)
    assert book(client, dr, svc, at("09:00")).status_code == 201
    assert book(client, dr, svc, at("09:30")).status_code == 201


def test_other_practitioner_same_time_is_fine(schedule, at, clinic_a, receptionist_a, client_for):
    dr, svc = schedule
    other = Practitioner.objects.create(clinic=clinic_a, display_name="Dr Hana")
    for wh in dr.working_hours.all():
        wh.pk = None
        wh.practitioner = other
        wh.save()
    client = client_for(receptionist_a)
    assert book(client, dr, svc, at("09:00")).status_code == 201
    assert book(client, other, svc, at("09:00")).status_code == 201


postgres_only = pytest.mark.skipif(
    connection.vendor != "postgresql", reason="needs PostgreSQL row locks and constraints"
)


@postgres_only
@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_of_one_slot_make_one_appointment(schedule, at, clinic_a):
    dr, svc = schedule
    barrier = threading.Barrier(4)
    outcomes = []

    def attempt(i):
        try:
            barrier.wait()
            booking.place(
                Appointment(clinic=clinic_a, patient_name=f"P{i}"),
                practitioner=dr,
                service=svc,
                starts_at=at("09:00"),
            )
            outcomes.append("booked")
        except booking.SlotUnavailable:
            outcomes.append("refused")
        finally:
            connections.close_all()

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(outcomes) == ["booked", "refused", "refused", "refused"]
    assert Appointment.objects.filter(practitioner=dr).count() == 1


@postgres_only
def test_database_refuses_overlap_even_without_the_app_check(schedule, at, clinic_a):
    dr, svc = schedule
    common = {"clinic": clinic_a, "practitioner": dr, "service": svc, "patient_name": "X"}
    Appointment.objects.create(
        reference="AAAAAA", starts_at=at("09:00"), ends_at=at("09:30"), **common
    )

    with pytest.raises(IntegrityError):
        Appointment.objects.create(
            reference="BBBBBB", starts_at=at("09:15"), ends_at=at("09:45"), **common
        )


# FR-013: reschedule and cancel


def test_reschedule_releases_old_slot_and_records_history(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    client = client_for(receptionist_a)
    appt = book(client, dr, svc, at("09:00")).data
    client.post(f"/api/appointments/{appt['id']}/confirm/")

    res = client.post(
        f"/api/appointments/{appt['id']}/reschedule/",
        {"starts_at": at("10:00").isoformat()},
        format="json",
    )

    assert res.status_code == 200, res.data
    assert res.data["starts_at"][11:16] == "10:00"
    assert res.data["status"] == "booked"  # the new time needs confirming again
    assert res.data["reference"] == appt["reference"]
    assert book(client, dr, svc, at("09:00")).status_code == 201  # old slot is free

    history = client.get(f"/api/appointments/{appt['id']}/history/").data
    assert [h["action"] for h in history] == [
        "appointment.create",
        "appointment.status",
        "appointment.reschedule",
    ]
    assert history[2]["detail"]["from_starts_at"].startswith(at("09:00").isoformat()[:16])


def test_reschedule_into_a_taken_slot_changes_nothing(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    client = client_for(receptionist_a)
    first = book(client, dr, svc, at("09:00")).data
    book(client, dr, svc, at("10:00"))

    res = client.post(
        f"/api/appointments/{first['id']}/reschedule/",
        {"starts_at": at("10:00").isoformat()},
        format="json",
    )

    assert res.status_code == 409
    assert Appointment.objects.get(pk=first["id"]).starts_at == at("09:00")


def test_reschedule_into_own_slot_overlap_is_fine(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    client = client_for(receptionist_a)
    appt = book(client, dr, svc, at("09:00")).data
    res = client.post(
        f"/api/appointments/{appt['id']}/reschedule/",
        {"starts_at": at("09:15").isoformat()},
        format="json",
    )
    assert res.status_code == 200


def test_cancel_releases_the_slot(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    client = client_for(receptionist_a)
    appt = book(client, dr, svc, at("09:00")).data

    res = client.post(f"/api/appointments/{appt['id']}/cancel/", {"reason": "Patient called"})

    assert res.status_code == 200
    assert res.data["status"] == "cancelled"
    assert res.data["cancel_reason"] == "Patient called"
    assert book(client, dr, svc, at("09:00")).status_code == 201
    # A cancelled appointment cannot be cancelled or moved again.
    assert client.post(f"/api/appointments/{appt['id']}/cancel/").status_code == 400


def test_appointments_cannot_be_deleted(schedule, at, manager_a, client_for):
    dr, svc = schedule
    client = client_for(manager_a)
    appt = book(client, dr, svc, at("09:00")).data
    assert client.delete(f"/api/appointments/{appt['id']}/").status_code == 405


def test_no_show_only_after_start(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    client = client_for(receptionist_a)
    appt = book(client, dr, svc, at("09:00")).data
    assert client.post(f"/api/appointments/{appt['id']}/no-show/").status_code == 400


def test_practitioner_reads_own_appointments_only_and_cannot_book(
    schedule, at, next_monday, clinic_a, make_user, receptionist_a, client_for
):
    dr, svc = schedule
    book(client_for(receptionist_a), dr, svc, at("09:00"))
    other_user = make_user(clinic_a, Role.PRACTITIONER, username="dr-hana")
    Practitioner.objects.create(clinic=clinic_a, display_name="Dr Hana", user=other_user)
    own_user = make_user(clinic_a, Role.PRACTITIONER, username="dr-abebe")
    dr.user = own_user
    dr.save()

    assert len(client_for(own_user).get(f"/api/appointments/?date_from={next_monday}").data) == 1
    assert client_for(other_user).get(f"/api/appointments/?date_from={next_monday}").data == []
    assert book(client_for(own_user), dr, svc, at("10:00")).status_code == 403


def test_find_by_reference(schedule, at, receptionist_a, client_for):
    dr, svc = schedule
    client = client_for(receptionist_a)
    ref = book(client, dr, svc, at("09:00")).data["reference"]
    res = client.get(f"/api/appointments/?reference={ref.lower()}")
    assert [a["reference"] for a in res.data] == [ref]


# FR-016: status flags and counts


def test_summary_counts_reconcile_with_the_list(
    schedule, at, next_monday, receptionist_a, client_for
):
    dr, svc = schedule
    client = client_for(receptionist_a)
    ids = [book(client, dr, svc, at(t)).data["id"] for t in ("09:00", "10:00", "11:00")]
    client.post(f"/api/appointments/{ids[0]}/confirm/")
    client.post(f"/api/appointments/{ids[1]}/cancel/")

    summary = client.get(f"/api/appointments/summary/?date_from={next_monday}").data
    listed = client.get(f"/api/appointments/?date_from={next_monday}").data

    assert summary == {"booked": 1, "confirmed": 1, "cancelled": 1, "no_show": 0, "total": 3}
    assert summary["total"] == len(listed)


def test_me_includes_linked_practitioner(schedule, clinic_a, make_user, client_for):
    dr, _ = schedule
    user = make_user(clinic_a, Role.PRACTITIONER)
    dr.user = user
    dr.save()
    assert client_for(user).get("/api/auth/me/").data["practitioner"] == dr.pk
