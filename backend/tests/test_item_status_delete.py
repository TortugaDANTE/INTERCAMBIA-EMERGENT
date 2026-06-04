import os
import uuid

import pytest
import requests


# Item ownership/status/delete flows for Intercambia bodega management
def _read_frontend_backend_url() -> str:
    env_path = "/app/frontend/.env"
    if not os.path.exists(env_path):
        return ""
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or _read_frontend_backend_url()


@pytest.fixture(scope="session")
def base_url():
    if not BASE_URL:
        pytest.skip("EXPO_PUBLIC_BACKEND_URL is not configured in environment")
    return BASE_URL.rstrip("/")


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def _create_demo_offer(api_client, base_url):
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "title": f"TEST_status_item_{suffix}",
        "description": "TEST item for status/delete regression",
        "kind": "producto",
        "listing_type": "oferta",
        "category": "General",
        "condition": "Usado",
        "pricing_model": "valor estimado",
        "estimated_value": 1000,
        "currency": "MXN",
        "exchange_for": "TEST intercambio",
        "location": "Centro",
        "image_key": "box",
    }
    response = api_client.post(f"{base_url}/api/items", json=payload)
    assert response.status_code == 200
    created = response.json()
    assert created["title"] == payload["title"]
    return created


def test_patch_status_accepts_pausado_vendido_truequeado_activo(api_client, base_url):
    item = _create_demo_offer(api_client, base_url)
    item_id = item["id"]

    for expected_status in ["pausado", "vendido", "truequeado", "activo"]:
        response = api_client.patch(
            f"{base_url}/api/items/{item_id}/status",
            json={"status": expected_status},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == item_id
        assert payload["status"] == expected_status

    delete_response = api_client.delete(f"{base_url}/api/items/{item_id}")
    assert delete_response.status_code == 200
    assert delete_response.json().get("ok") is True


def test_patch_status_invalid_value_returns_400(api_client, base_url):
    item = _create_demo_offer(api_client, base_url)
    item_id = item["id"]

    bad_response = api_client.patch(
        f"{base_url}/api/items/{item_id}/status",
        json={"status": "archivado"},
    )
    assert bad_response.status_code == 400
    assert "Estado no válido" in bad_response.json().get("detail", "")

    delete_response = api_client.delete(f"{base_url}/api/items/{item_id}")
    assert delete_response.status_code == 200


def test_soft_delete_hides_item_from_bootstrap_offers(api_client, base_url):
    item = _create_demo_offer(api_client, base_url)
    item_id = item["id"]

    pre_bootstrap = api_client.get(f"{base_url}/api/bootstrap")
    assert pre_bootstrap.status_code == 200
    pre_data = pre_bootstrap.json()
    pre_offer_ids = {offer["id"] for offer in pre_data.get("offers", [])}
    assert item_id in pre_offer_ids

    delete_response = api_client.delete(f"{base_url}/api/items/{item_id}")
    assert delete_response.status_code == 200
    assert delete_response.json().get("ok") is True

    patch_after_delete = api_client.patch(
        f"{base_url}/api/items/{item_id}/status",
        json={"status": "activo"},
    )
    assert patch_after_delete.status_code == 404

    post_bootstrap = api_client.get(f"{base_url}/api/bootstrap")
    assert post_bootstrap.status_code == 200
    post_data = post_bootstrap.json()
    post_offer_ids = {offer["id"] for offer in post_data.get("offers", [])}
    assert item_id not in post_offer_ids
