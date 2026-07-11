import os
import uuid

import pytest
import requests


# Requested feature regressions: bootstrap payload, premium masking, item schema, friends actions, and chat messages
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
        pytest.skip("EXPO_PUBLIC_BACKEND_URL is not configured")
    return BASE_URL.rstrip("/")


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def test_bootstrap_includes_social_trade_match_and_usd_plan_labels(api_client, base_url):
    response = api_client.get(f"{base_url}/api/bootstrap")
    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload.get("friends"), list)
    assert isinstance(payload.get("trade_history"), list)
    assert isinstance(payload.get("suggested_matches"), list)

    plans = payload.get("plans", [])
    assert isinstance(plans, list)
    labels = {plan.get("monthly_label") for plan in plans}
    assert "5 USD/mes" in labels
    assert "10 USD/mes" in labels
    assert "20 USD/mes" in labels


def test_free_bootstrap_masks_premium_item_details_over_2000(api_client, base_url):
    response = api_client.get(f"{base_url}/api/bootstrap")
    assert response.status_code == 200
    feed = response.json().get("feed", [])
    target = next((item for item in feed if item.get("estimated_value", 0) > 2000), None)
    assert target is not None

    assert target["requires_premium_contact"] is True
    assert target["description"].startswith("Contenido premium")
    assert target["exchange_for"] == "Disponible para miembros Premium"
    assert target["images"] == []


def test_items_accept_images_tags_and_optional_exchange_for(api_client, base_url):
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "title": f"TEST_item_images_tags_{suffix}",
        "description": "TEST item with images and tags",
        "kind": "producto",
        "listing_type": "oferta",
        "category": "General",
        "condition": "Usado",
        "pricing_model": "valor estimado",
        "estimated_value": 900,
        "currency": "MXN",
        "exchange_for": "",
        "location": "Centro",
        "image_key": "box",
        "images": ["https://example.com/test-image.jpg"],
        "tags": ["test", "etiqueta", "regresion"],
    }
    create_response = api_client.post(f"{base_url}/api/items", json=payload)
    assert create_response.status_code == 200
    created = create_response.json()

    assert created["title"] == payload["title"]
    assert created["images"] == payload["images"]
    assert created["tags"] == payload["tags"]
    assert created["exchange_for"] == ""

    list_response = api_client.get(f"{base_url}/api/items")
    assert list_response.status_code == 200
    all_items = list_response.json()
    persisted = next((item for item in all_items if item.get("id") == created["id"]), None)
    assert persisted is not None
    assert persisted["images"] == payload["images"]
    assert persisted["tags"] == payload["tags"]


def test_friend_action_accepts_agregar_bloquear_reportar(api_client, base_url):
    for action in ["agregar", "bloquear", "reportar"]:
        response = api_client.post(f"{base_url}/api/friends/ana/action?action={action}")
        assert response.status_code == 200
        assert response.json().get("ok") is True


def test_chat_get_and_post_messages_work(api_client, base_url):
    get_response = api_client.get(f"{base_url}/api/chats/chat-ana/messages")
    assert get_response.status_code == 200
    messages_before = get_response.json()
    assert isinstance(messages_before, list)

    text = f"TEST mensaje regression {uuid.uuid4().hex[:6]}"
    post_response = api_client.post(
        f"{base_url}/api/chats/chat-ana/messages",
        json={"text": text},
    )
    assert post_response.status_code == 200
    posted = post_response.json()
    assert posted["chat_id"] == "chat-ana"
    assert posted["text"] == text

    get_after = api_client.get(f"{base_url}/api/chats/chat-ana/messages")
    assert get_after.status_code == 200
    messages_after = get_after.json()
    assert any(m.get("id") == posted["id"] and m.get("text") == text for m in messages_after)
