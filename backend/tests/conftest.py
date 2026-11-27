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
