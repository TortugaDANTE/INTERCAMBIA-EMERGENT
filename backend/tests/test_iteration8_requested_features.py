import os
import uuid

import pytest
import requests


# Iteration 8 requested checks: plan MXN pricing and item create payload requirements
def _read_env_value(path: str, key: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or _read_env_value(
    "/app/frontend/.env", "EXPO_PUBLIC_BACKEND_URL"
)


@pytest.fixture(scope="session")
def base_url():
    if not BASE_URL:
        pytest.skip("EXPO_PUBLIC_BACKEND_URL is not configured")
    return BASE_URL.rstrip("/")


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def test_plans_show_mxn_prices_requested(api_client, base_url):
    response = api_client.get(f"{base_url}/api/plans")
    assert response.status_code == 200
    plans = response.json()
    by_tier = {plan.get("tier"): plan for plan in plans}

    assert by_tier["premium"]["monthly_label"] == "$50 MXN/mes"
    assert by_tier["advanced"]["monthly_label"] == "$100 MXN/mes"
    assert by_tier["business"]["monthly_label"] == "$150 MXN/mes por punto físico"
    assert by_tier["digital_seller"]["monthly_label"] == "$50 MXN/mes"


def test_item_create_accepts_gift_and_location_without_search_radius(api_client, base_url):
    payload = {
        "title": f"TEST_iter8_gift_{uuid.uuid4().hex[:8]}",
        "description": "TEST item create without search radius",
        "kind": "producto",
        "listing_type": "oferta",
        "category": "General",
        "condition": "Usado",
        "pricing_model": "valor estimado",
        "estimated_value": 250,
        "currency": "MXN",
        "exchange_for": "",
        "location": "Centro",
        "city": "Monterrey",
        "country": "México",
        "state": "Nuevo León",
        "municipality": "Monterrey",
        "is_gift": True,
        "image_key": "box",
        "tags": ["test", "gift", "location"],
        "images": [],
    }

    create_response = api_client.post(f"{base_url}/api/items", json=payload)
    assert create_response.status_code == 200
    created = create_response.json()

    assert created["is_gift"] is True
    assert created["country"] == "México"
    assert created["state"] == "Nuevo León"
    assert created["city"] == "Monterrey"
    assert created["municipality"] == "Monterrey"
    assert "search_radius_km" not in created

    item_id = created["id"]
    list_response = api_client.get(f"{base_url}/api/bootstrap")
    assert list_response.status_code == 200
    offers = list_response.json().get("offers", [])
    persisted = next((item for item in offers if item.get("id") == item_id), None)
    assert persisted is not None
    assert persisted["is_gift"] is True
    assert persisted["country"] == "México"
    assert persisted["state"] == "Nuevo León"
    assert persisted["city"] == "Monterrey"
    assert persisted["municipality"] == "Monterrey"

    delete_response = api_client.delete(f"{base_url}/api/items/{item_id}")
    assert delete_response.status_code == 200
    assert delete_response.json().get("ok") is True
