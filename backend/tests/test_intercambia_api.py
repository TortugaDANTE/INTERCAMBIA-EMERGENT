import os
import pytest
import requests


# Core Intercambia API flows: bootstrap, plans, free-limit enforcement, auth gating, billing auth requirement
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


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def test_bootstrap_includes_profile_plan_businesses_and_plans(api_client, base_url):
    response = api_client.get(f"{base_url}/api/bootstrap")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data.get("profile"), dict)
    assert data["profile"].get("plan") in {"free", "premium", "advanced"}
    assert "plan_label" in data["profile"]
    assert isinstance(data.get("businesses"), list)
    assert isinstance(data.get("plans"), list)
    tiers = {plan.get("tier") for plan in data["plans"]}
    assert {"premium", "advanced"}.issubset(tiers)


def test_plans_exposes_premium_and_advanced_tiers(api_client, base_url):
    response = api_client.get(f"{base_url}/api/plans")
    assert response.status_code == 200

    plans = response.json()
    tiers = {plan.get("tier") for plan in plans}
    assert "premium" in tiers
    assert "advanced" in tiers


def test_create_item_free_user_above_limit_returns_402(api_client, base_url):
    payload = {
        "title": "TEST_item_over_limit",
        "description": "Intento de publicación por encima de límite gratis",
        "kind": "producto",
        "listing_type": "oferta",
        "category": "General",
        "condition": "Usado",
        "pricing_model": "valor estimado",
        "estimated_value": 2501,
        "currency": "MXN",
        "exchange_for": "TEST_intercambio",
        "location": "Centro",
        "image_key": "box",
    }
    response = api_client.post(f"{base_url}/api/items", json=payload)
    assert response.status_code == 402
    assert "$2,000" in response.json().get("detail", "")


def test_business_creation_without_auth_returns_401(api_client, base_url):
    payload = {
        "name": "TEST_negocio_sin_auth",
        "category": "Cafetería",
        "address": "TEST_direccion",
        "description": "TEST_descripcion",
    }
    response = api_client.post(f"{base_url}/api/businesses", json=payload)
    assert response.status_code == 401
    assert "Google" in response.json().get("detail", "")


def test_billing_checkout_requires_auth(api_client, base_url):
    response = api_client.post(
        f"{base_url}/api/billing/create-checkout-session",
        json={"tier": "premium", "return_url": base_url},
    )
    assert response.status_code == 401
    assert "Google" in response.json().get("detail", "")
