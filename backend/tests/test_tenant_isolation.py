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
