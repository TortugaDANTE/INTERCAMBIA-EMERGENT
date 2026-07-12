import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient


# Requested regressions: business PATCH/DELETE, phone register/verify, friend request by phone, item negotiation/city/radius persistence
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
        pytest.skip("MONGO_URL/DB_NAME missing")
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
def seeded_auth_users(mongo_db):
    suffix = uuid.uuid4().hex[:8]
    digit_suffix = str(uuid.uuid4().int)[-8:]
    now = datetime.now(timezone.utc)

    owner_user_id = f"TEST_owner_{suffix}"
    owner_token = f"TEST_owner_token_{suffix}"
    target_user_id = f"TEST_target_{suffix}"
    verified_phone = f"+52551{digit_suffix}"

    mongo_db.users.update_one(
        {"user_id": owner_user_id},
        {
            "$set": {
                "user_id": owner_user_id,
                "email": f"test_owner_{suffix}@example.com",
                "name": f"TEST Owner {suffix}",
                "plan": "business",
                "phone_verified": False,
                "trial_ends_at": (now + timedelta(days=5)).isoformat(),
                "updated_at": now.isoformat(),
            },
            "$setOnInsert": {"created_at": now.isoformat()},
        },
        upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": owner_token},
        {
            "$set": {
                "session_token": owner_token,
                "user_id": owner_user_id,
                "created_at": now,
                "expires_at": now + timedelta(days=7),
            }
        },
        upsert=True,
    )

    mongo_db.users.update_one(
        {"user_id": target_user_id},
        {
            "$set": {
                "user_id": target_user_id,
                "email": f"test_target_{suffix}@example.com",
                "name": f"TEST Target {suffix}",
                "plan": "free",
                "phone": verified_phone,
                "phone_verified": True,
                "updated_at": now.isoformat(),
            },
            "$setOnInsert": {"created_at": now.isoformat()},
        },
        upsert=True,
    )

    created_tracker = {"business_id": "", "business_item_id": "", "user_item_id": ""}

    yield {
        "owner_user_id": owner_user_id,
        "owner_token": owner_token,
        "target_user_id": target_user_id,
        "verified_phone": verified_phone,
        "created_tracker": created_tracker,
    }

    if created_tracker["business_item_id"]:
        mongo_db.items.delete_many({"id": created_tracker["business_item_id"]})
    if created_tracker["user_item_id"]:
        mongo_db.items.delete_many({"id": created_tracker["user_item_id"]})
    if created_tracker["business_id"]:
        mongo_db.businesses.delete_many({"id": created_tracker["business_id"]})

    mongo_db.friend_requests.delete_many({"user_id": owner_user_id})
    mongo_db.user_sessions.delete_many({"user_id": owner_user_id})
    mongo_db.users.delete_many({"user_id": owner_user_id})
    mongo_db.users.delete_many({"user_id": target_user_id})


def test_business_patch_and_delete_supported(api_client, base_url, seeded_auth_users):
    token = seeded_auth_users["owner_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = api_client.post(
        f"{base_url}/api/businesses",
        headers=headers,
        json={
            "name": "TEST Taller Inicial",
            "category": "Taller",
            "address": "TEST Calle 100",
            "description": "TEST descripcion inicial",
            "profile_type": "persona_moral",
        },
    )
    assert create_res.status_code == 200
    created = create_res.json()
    business_id = created["id"]
    seeded_auth_users["created_tracker"]["business_id"] = business_id

    patch_res = api_client.patch(
        f"{base_url}/api/businesses/{business_id}",
        headers=headers,
        json={"name": "TEST Taller Editado", "address": "TEST Calle 200"},
    )
    assert patch_res.status_code == 200
    patched = patch_res.json()
    assert patched["name"] == "TEST Taller Editado"
    assert patched["address"] == "TEST Calle 200"
    assert patched["public_handle"].startswith("@")

    get_before_delete = api_client.get(f"{base_url}/api/businesses", headers=headers)
    assert get_before_delete.status_code == 200
    assert any(b.get("id") == business_id for b in get_before_delete.json())

    delete_res = api_client.delete(f"{base_url}/api/businesses/{business_id}", headers=headers)
    assert delete_res.status_code == 200
    assert delete_res.json().get("ok") is True

    get_after_delete = api_client.get(f"{base_url}/api/businesses", headers=headers)
    assert get_after_delete.status_code == 200
    assert all(b.get("id") != business_id for b in get_after_delete.json())


def test_phone_register_and_verify_endpoints(api_client, base_url, seeded_auth_users):
    token = seeded_auth_users["owner_token"]
    headers = {"Authorization": f"Bearer {token}"}
    phone = "+525511223344"

    phone_res = api_client.post(
        f"{base_url}/api/auth/phone",
        headers=headers,
        json={"phone": phone},
    )
    assert phone_res.status_code == 200
    phone_payload = phone_res.json()
    assert phone_payload.get("ok") is True
    assert phone_payload.get("test_code") == "123456"

    bad_verify = api_client.post(
        f"{base_url}/api/auth/phone/verify",
        headers=headers,
        json={"code": "000000"},
    )
    assert bad_verify.status_code == 400

    verify_res = api_client.post(
        f"{base_url}/api/auth/phone/verify",
        headers=headers,
        json={"code": "123456"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json().get("ok") is True

    me_res = api_client.get(f"{base_url}/api/bootstrap", headers=headers)
    assert me_res.status_code == 200
    profile = me_res.json().get("profile", {})
    assert profile.get("phone_verified") is True


def test_friend_request_by_phone_endpoint(api_client, base_url, seeded_auth_users):
    token = seeded_auth_users["owner_token"]
    headers = {"Authorization": f"Bearer {token}"}
    verified_phone = seeded_auth_users["verified_phone"]

    res = api_client.post(
        f"{base_url}/api/friends/by-phone",
        headers=headers,
        json={"phone": verified_phone},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload.get("ok") is True
    assert payload.get("status") == "solicitud_enviada"


def test_create_item_persists_negotiation_flags_city_radius(api_client, base_url, seeded_auth_users):
    token = seeded_auth_users["owner_token"]
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:6]

    create_res = api_client.post(
        f"{base_url}/api/items",
        headers=headers,
        json={
            "title": f"TEST flags item {suffix}",
            "description": "TEST item to validate negotiation flags",
            "kind": "producto",
            "listing_type": "oferta",
            "category": "General",
            "condition": "Usado",
            "pricing_model": "valor estimado",
            "estimated_value": 1500,
            "currency": "MXN",
            "exchange_for": "TEST exchange",
            "location": "Monterrey",
            "city": "Monterrey",
            "search_radius_km": 42,
            "accepts_higher_value": True,
            "opportunity_trade": True,
            "prefers_sale": True,
            "accepts_partial_cash": False,
            "negotiable": True,
            "image_key": "box",
            "tags": ["test", "flags", "ciudad"],
            "images": [],
        },
    )
    assert create_res.status_code == 200
    created = create_res.json()
    seeded_auth_users["created_tracker"]["user_item_id"] = created["id"]

    assert created["city"] == "Monterrey"
    assert created["search_radius_km"] == 42
    assert created["accepts_higher_value"] is True
    assert created["opportunity_trade"] is True
    assert created["prefers_sale"] is True
    assert created["accepts_partial_cash"] is False
    assert created["negotiable"] is True

    list_res = api_client.get(f"{base_url}/api/bootstrap", headers=headers)
    assert list_res.status_code == 200
    offers = list_res.json().get("offers", [])
    persisted = next((item for item in offers if item.get("id") == created["id"]), None)
    assert persisted is not None
    assert persisted["city"] == "Monterrey"
    assert persisted["search_radius_km"] == 42
    assert persisted["opportunity_trade"] is True