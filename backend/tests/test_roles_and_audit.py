"""FR-003 role limits and FR-004 audit trail."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.core.models import AuditEvent


@pytest.mark.parametrize("role", [Role.RECEPTIONIST, Role.PRACTITIONER])
def test_front_line_staff_can_read_but_not_change_services(role, clinic_a, make_user, client_for):
    client = client_for(make_user(clinic_a, role))

    assert client.get("/api/services/").status_code == 200
    assert client.post("/api/services/", {"name": "Cleaning"}).status_code == 403


@pytest.mark.parametrize("role", [Role.CLINIC_MANAGER, Role.TENANT_ADMIN])
def test_managers_can_create_services(role, clinic_a, make_user, client_for):
    res = client_for(make_user(clinic_a, role)).post(
        "/api/services/", {"name": "Cleaning", "duration_minutes": 30}
    )
    assert res.status_code == 201


def test_writes_are_audited(clinic_a, manager_a, client_for):
    client_for(manager_a).post("/api/services/", {"name": "Check-up"})

    event = AuditEvent.objects.get(action="service.create")
    assert event.actor == manager_a
    assert event.clinic == clinic_a
    assert event.target_id


def test_disabled_user_cannot_log_in(clinic_a, make_user):
    user = make_user(clinic_a, Role.RECEPTIONIST)
    user.is_active = False
    user.save()

    res = APIClient().post(
        "/api/auth/login/", {"username": user.username, "password": "correct-horse-battery"}
    )
    assert res.status_code == 400


def test_login_then_me(clinic_a, make_user):
    user = make_user(clinic_a, Role.RECEPTIONIST)
    client = APIClient()

    res = client.post(
        "/api/auth/login/", {"username": user.username, "password": "correct-horse-battery"}
    )
    assert res.status_code == 200
    me = client.get("/api/auth/me/")
    assert me.data["clinic_name"] == "Bole Dental"
    assert AuditEvent.objects.filter(action="auth.login", actor=user).exists()


def test_health_is_public(db):
    assert APIClient().get("/api/health/").data == {"status": "ok"}


def test_login_requires_csrf_token(clinic_a, make_user):
    user = make_user(clinic_a, Role.RECEPTIONIST)
    client = APIClient(enforce_csrf_checks=True)

    res = client.post(
        "/api/auth/login/", {"username": user.username, "password": "correct-horse-battery"}
    )
    assert res.status_code == 403

    client.get("/api/auth/csrf/")
    res = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "correct-horse-battery"},
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert res.status_code == 200
