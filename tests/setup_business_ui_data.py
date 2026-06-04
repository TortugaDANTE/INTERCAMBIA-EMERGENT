import os
import uuid
from datetime import datetime, timedelta, timezone

import requests
from pymongo import MongoClient


def read_env_value(path: str, key: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


mongo_url = os.environ.get("MONGO_URL") or read_env_value("/app/backend/.env", "MONGO_URL")
db_name = os.environ.get("DB_NAME") or read_env_value("/app/backend/.env", "DB_NAME")
base_url = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or read_env_value("/app/frontend/.env", "EXPO_PUBLIC_BACKEND_URL")

if not mongo_url or not db_name or not base_url:
    raise RuntimeError("Missing MONGO_URL/DB_NAME/EXPO_PUBLIC_BACKEND_URL")

client = MongoClient(mongo_url)
db = client[db_name]

suffix = uuid.uuid4().hex[:8]
user_id = f"TEST_ui_business_user_{suffix}"
email = f"test_ui_business_{suffix}@example.com"
token = f"TEST_ui_business_token_{suffix}"
now = datetime.now(timezone.utc)

db.users.update_one(
    {"user_id": user_id},
    {
        "$set": {
            "user_id": user_id,
            "email": email,
            "name": f"TEST UI Business {suffix}",
            "plan": "free",
            "trial_ends_at": (now + timedelta(days=6, hours=20)).isoformat(),
            "updated_at": now.isoformat(),
        },
        "$setOnInsert": {"created_at": now.isoformat()},
    },
    upsert=True,
)

db.user_sessions.update_one(
    {"session_token": token},
    {
        "$set": {
            "session_token": token,
            "user_id": user_id,
            "created_at": now,
            "expires_at": now + timedelta(days=6),
        }
    },
    upsert=True,
)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

business_resp = requests.post(
    f"{base_url.rstrip('/')}/api/businesses",
    headers=headers,
    json={
        "name": f"TEST Página Circular {suffix}",
        "category": "Cafetería",
        "address": "TEST Calle Principal 123",
        "description": "TEST Página de negocio para flujo subperfil",
        "profile_type": "persona_moral",
    },
    timeout=20,
)
business_resp.raise_for_status()
business = business_resp.json()

requests.post(
    f"{base_url.rstrip('/')}/api/businesses/{business['id']}/items",
    headers=headers,
    json={
        "title": "TEST Oferta de pan artesanal",
        "description": "TEST Oferta desde página",
        "kind": "producto",
        "listing_type": "oferta",
        "category": "Alimentos",
        "condition": "Usado",
        "pricing_model": "valor estimado",
        "estimated_value": 450,
        "currency": "MXN",
        "exchange_for": "TEST café local",
        "location": "ignorado",
        "image_key": "box",
    },
    timeout=20,
).raise_for_status()

requests.post(
    f"{base_url.rstrip('/')}/api/businesses/{business['id']}/items",
    headers=headers,
    json={
        "title": "TEST Necesidad de insumos",
        "description": "TEST Necesidad desde página",
        "kind": "producto",
        "listing_type": "deseo",
        "category": "General",
        "condition": "Usado",
        "pricing_model": "valor estimado",
        "estimated_value": 300,
        "currency": "MXN",
        "exchange_for": "TEST harina orgánica",
        "location": "ignorado",
        "image_key": "box",
    },
    timeout=20,
).raise_for_status()

print(token)
