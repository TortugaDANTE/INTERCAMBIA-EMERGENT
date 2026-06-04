import os
import uuid
from datetime import datetime, timedelta, timezone

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

if not mongo_url or not db_name:
    raise RuntimeError("MONGO_URL/DB_NAME missing")

client = MongoClient(mongo_url)
db = client[db_name]

suffix = uuid.uuid4().hex[:10]
user_id = f"TEST_ui_trial_{suffix}"
email = f"test_ui_trial_{suffix}@example.com"
token = f"TEST_ui_trial_token_{suffix}"
now = datetime.now(timezone.utc)

db.users.update_one(
    {"user_id": user_id},
    {
        "$set": {
            "user_id": user_id,
            "email": email,
            "name": f"TEST UI Trial {suffix}",
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

print(token)
