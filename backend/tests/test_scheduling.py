from apps.scheduling.models import Service


def test_duplicate_service_name_is_a_clear_error(clinic_a, manager_a, client_for):
    client = client_for(manager_a)
    assert client.post("/api/services/", {"name": "Check-up"}).status_code == 201

    res = client.post("/api/services/", {"name": "check-up"})

    assert res.status_code == 400
    assert "already has a service" in str(res.data["name"])


def test_same_service_name_allowed_in_another_clinic(clinic_a, clinic_b, manager_a, client_for):
    Service.objects.create(clinic=clinic_b, name="Check-up")

    assert client_for(manager_a).post("/api/services/", {"name": "Check-up"}).status_code == 201


def test_renaming_service_to_its_own_name_is_fine(clinic_a, manager_a, client_for):
    svc = Service.objects.create(clinic=clinic_a, name="Check-up")

    res = client_for(manager_a).patch(f"/api/services/{svc.pk}/", {"name": "Check-up"})

    assert res.status_code == 200
