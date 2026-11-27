import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.tenants.models import Clinic


@pytest.fixture
def clinic_a(db):
    return Clinic.objects.create(name="Bole Dental", slug="bole-dental")


@pytest.fixture
def clinic_b(db):
    return Clinic.objects.create(name="Kazanchis Family Clinic", slug="kazanchis")


@pytest.fixture
def make_user(db):
    def _make(clinic, role, username=None):
        return User.objects.create_user(
            username=username or f"{role}-{clinic.slug if clinic else 'platform'}",
            password="correct-horse-battery",
            clinic=clinic,
            role=role,
        )

    return _make


@pytest.fixture
def client_for():
    def _client(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    return _client


@pytest.fixture
def manager_a(make_user, clinic_a):
    return make_user(clinic_a, Role.CLINIC_MANAGER)


@pytest.fixture
def next_monday():
    """A Monday at least a week ahead, so booked times are always in the future."""
    from datetime import timedelta

    from django.utils import timezone

    today = timezone.localdate()
    return today + timedelta(days=7 + (7 - today.weekday()) % 7)


@pytest.fixture
def at(next_monday):
    """at("09:30") or at("09:30", days=1): an aware clinic-local datetime on next Monday."""
    from datetime import datetime, time, timedelta

    from django.utils import timezone

    def _at(hhmm, days=0):
        h, m = map(int, hhmm.split(":"))
        return datetime.combine(
            next_monday + timedelta(days=days),
            time(h, m),
            tzinfo=timezone.get_current_timezone(),
        )

    return _at


@pytest.fixture
def schedule(clinic_a):
    """Dr Abebe works Monday 09:00-12:00 and 13:00-17:00 (lunch break 12-13). Check-up is 30 min."""
    from datetime import time

    from apps.scheduling.models import Practitioner, Service, WorkingHours

    dr = Practitioner.objects.create(clinic=clinic_a, display_name="Dr Abebe")
    WorkingHours.objects.create(
        clinic=clinic_a, practitioner=dr, weekday=0, start_time=time(9), end_time=time(12)
    )
    WorkingHours.objects.create(
        clinic=clinic_a, practitioner=dr, weekday=0, start_time=time(13), end_time=time(17)
    )
    svc = Service.objects.create(clinic=clinic_a, name="Check-up", duration_minutes=30)
    return dr, svc


@pytest.fixture
def receptionist_a(make_user, clinic_a):
    return make_user(clinic_a, Role.RECEPTIONIST)
