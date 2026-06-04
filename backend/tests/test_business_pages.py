import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient


# Business page subprofile flows: create page, publish page item, bootstrap nested business items
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
        pytest.skip("MONGO_URL/DB_NAME missing for business page tests")
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
def business_identity(mongo_db):
    suffix = uuid.uuid4().hex[:10]
    user_id = f"TEST_biz_user_{suffix}"
    email = f"test_biz_{suffix}@example.com"
    session_token = f"TEST_biz_token_{suffix}"
    now = datetime.now(timezone.utc)
    trial_ends_at = (now + timedelta(days=5)).isoformat()

    mongo_db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "email": email,
                "name": f"TEST Biz Owner {suffix}",
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

    yield {"user_id": user_id, "session_token": session_token}

    mongo_db.items.delete_many({"user_id": user_id})
    mongo_db.businesses.delete_many({"owner_user_id": user_id})
    mongo_db.user_sessions.delete_many({"user_id": user_id})
    mongo_db.users.delete_many({"user_id": user_id})


def test_create_business_page_sets_public_handle_profile_type_and_owner(api_client, base_url, business_identity):
    headers = {"Authorization": f"Bearer {business_identity['session_token']}"}
    business_name = "TEST Café Circular Legal"
    payload = {
        "name": business_name,
        "category": "Cafetería",
        "address": "TEST Calle Comercio 101",
        "description": "TEST Negocio para trueque",
        "profile_type": "persona_fisica",
    }

    response = api_client.post(f"{base_url}/api/businesses", headers=headers, json=payload)
    assert response.status_code == 200

    created = response.json()
    assert created["name"] == business_name
    assert created["owner_user_id"] == business_identity["user_id"]
    assert created["profile_type"] == "persona_fisica"
    assert created["public_handle"].startswith("@")


def test_create_business_item_sets_business_ownership_fields(api_client, base_url, business_identity):
    headers = {"Authorization": f"Bearer {business_identity['session_token']}"}
    business_response = api_client.post(
        f"{base_url}/api/businesses",
        headers=headers,
        json={
            "name": "TEST Taller del Barrio",
            "category": "Taller",
            "address": "TEST Calle Taller 202",
            "description": "TEST Herramientas y servicios",
            "profile_type": "persona_moral",
        },
    )
    assert business_response.status_code == 200
    business = business_response.json()

    item_response = api_client.post(
        f"{base_url}/api/businesses/{business['id']}/items",
        headers=headers,
        json={
            "title": "TEST Servicio de ajuste",
            "description": "TEST Ajuste técnico",
            "kind": "servicio",
            "listing_type": "oferta",
            "category": "Oficios",
            "condition": "Servicio",
            "pricing_model": "por hora",
            "estimated_value": 800,
            "currency": "MXN",
            "exchange_for": "TEST insumos",
            "location": "Este valor debe sobreescribirse",
            "image_key": "box",
        },
    )
    assert item_response.status_code == 200
    item = item_response.json()
    assert item["owner_type"] == "business"
    assert item["owner_name"] == business["name"]
    assert item["business_id"] == business["id"]
    assert item["user_id"] == business_identity["user_id"]
    assert item["location"] == business["address"]


def test_bootstrap_includes_business_pages_with_nested_items(api_client, base_url, business_identity):
    headers = {"Authorization": f"Bearer {business_identity['session_token']}"}
    business_name = f"TEST Mercado Circular {uuid.uuid4().hex[:5]}"
    create_business = api_client.post(
        f"{base_url}/api/businesses",
        headers=headers,
        json={
            "name": business_name,
            "category": "Mercado",
            "address": "TEST Avenida trueque 303",
            "description": "TEST Perfil para validar bootstrap",
            "profile_type": "persona_moral",
        },
    )
    assert create_business.status_code == 200
    business = create_business.json()

    create_item = api_client.post(
        f"{base_url}/api/businesses/{business['id']}/items",
        headers=headers,
        json={
            "title": "TEST Insumo de cafetería",
            "description": "TEST publicación desde página",
            "kind": "producto",
            "listing_type": "deseo",
            "category": "General",
            "condition": "Usado",
            "pricing_model": "valor estimado",
            "estimated_value": 500,
            "currency": "MXN",
            "exchange_for": "TEST café local",
            "location": "se reemplaza",
            "image_key": "box",
        },
    )
    assert create_item.status_code == 200

    bootstrap = api_client.get(f"{base_url}/api/bootstrap", headers=headers)
    assert bootstrap.status_code == 200
    payload = bootstrap.json()
    businesses = payload.get("businesses", [])
    target = next((b for b in businesses if b.get("id") == business["id"]), None)
    assert target is not None
    assert target["name"] == business_name
    assert target["profile_type"] == "persona_moral"
    assert isinstance(target.get("items"), list)
    assert any(item.get("business_id") == business["id"] and item.get("owner_type") == "business" for item in target["items"])
