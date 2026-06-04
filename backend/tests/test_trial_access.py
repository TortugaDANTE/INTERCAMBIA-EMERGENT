import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient


# Trial entitlement flows: auth payload, high-value publish/contact bypass, multi-business registration
def _read_env_value(path: str, key: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or _read_env_value("/app/frontend/.env", "EXPO_PUBLIC_BACKEND_URL")
MONGO_URL = os.environ.get("MONGO_URL") or _read_env_value("/app/backend/.env", "MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or _read_env_value("/app/backend/.env", "DB_NAME")


@pytest.fixture(scope="session")
def base_url():
    if not BASE_URL:
        pytest.skip("EXPO_PUBLIC_BACKEND_URL is not configured")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def mongo_db():
    if not MONGO_URL or not DB_NAME:
        pytest.skip("MONGO_URL/DB_NAME missing for trial regression setup")
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def trial_identity(mongo_db):
    suffix = uuid.uuid4().hex[:10]
    user_id = f"TEST_trial_user_{suffix}"
    email = f"test_trial_{suffix}@example.com"
    session_token = f"TEST_trial_token_{suffix}"
    now = datetime.now(timezone.utc)
    trial_ends_at = (now + timedelta(days=6, hours=20)).isoformat()

    mongo_db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "email": email,
                "name": f"TEST Trial {suffix}",
                "plan": "free",
                "trial_ends_at": trial_ends_at,
                "updated_at": now.isoformat(),
            },
            "$setOnInsert": {"created_at": now.isoformat()},
        },
        upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": session_token},
        {
            "$set": {
                "session_token": session_token,
                "user_id": user_id,
                "created_at": now,
                "expires_at": now + timedelta(days=6),
            }
        },
        upsert=True,
    )

    yield {"user_id": user_id, "email": email, "session_token": session_token}

    mongo_db.items.delete_many({"user_id": user_id})
    mongo_db.interests.delete_many({"from_user_id": user_id})
    mongo_db.businesses.delete_many({"owner_user_id": user_id})
    mongo_db.user_sessions.delete_many({"user_id": user_id})
    mongo_db.users.delete_many({"user_id": user_id})


def test_auth_me_includes_trial_fields_and_entitlements(api_client, base_url, trial_identity):
    response = api_client.get(
        f"{base_url}/api/auth/me",
        headers={"Authorization": f"Bearer {trial_identity['session_token']}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["trial_active"] is True
    assert payload["trial_days_left"] >= 1
    assert payload["trial_ends_at"]
    assert payload["advanced_access"] is True
    assert payload["is_premium"] is True
    assert payload["business_limit"] is None


def test_trial_user_can_publish_high_value_item(api_client, base_url, trial_identity):
    response = api_client.post(
        f"{base_url}/api/items",
        headers={"Authorization": f"Bearer {trial_identity['session_token']}"},
        json={
            "title": "TEST_trial_publish_over_limit",
            "description": "Debe permitir más de 2000 durante prueba",
            "kind": "producto",
            "listing_type": "oferta",
            "category": "General",
            "condition": "Usado",
            "pricing_model": "valor estimado",
            "estimated_value": 3500,
            "currency": "MXN",
            "exchange_for": "TEST intercambio",
            "location": "Centro",
            "image_key": "box",
        },
    )
    assert response.status_code == 200
    created = response.json()
    assert created["estimated_value"] == 3500
    assert created["user_id"] == trial_identity["user_id"]


def test_trial_user_can_contact_high_value_item(api_client, base_url, trial_identity):
    bootstrap = api_client.get(f"{base_url}/api/bootstrap")
    assert bootstrap.status_code == 200
    feed = bootstrap.json().get("feed", [])
    high_value = next((item for item in feed if item.get("estimated_value", 0) > 2000), None)
    assert high_value is not None

    response = api_client.post(
        f"{base_url}/api/interests",
        headers={"Authorization": f"Bearer {trial_identity['session_token']}"},
        json={"item_id": high_value["id"], "message": "TEST contacto prueba"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["item_id"] == high_value["id"]
    assert payload["from_user_id"] == trial_identity["user_id"]


def test_trial_user_can_register_multiple_businesses(api_client, base_url, trial_identity):
    headers = {"Authorization": f"Bearer {trial_identity['session_token']}"}
    first = api_client.post(
        f"{base_url}/api/businesses",
        headers=headers,
        json={
            "name": "TEST negocio trial 1",
            "category": "Cafetería",
            "address": "TEST calle 1",
            "description": "TEST desc 1",
        },
    )
    second = api_client.post(
        f"{base_url}/api/businesses",
        headers=headers,
        json={
            "name": "TEST negocio trial 2",
            "category": "Taller",
            "address": "TEST calle 2",
            "description": "TEST desc 2",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200

    listed = api_client.get(f"{base_url}/api/businesses", headers=headers)
    assert listed.status_code == 200
    businesses = listed.json()
    names = {biz["name"] for biz in businesses}
    assert "TEST negocio trial 1" in names
    assert "TEST negocio trial 2" in names
