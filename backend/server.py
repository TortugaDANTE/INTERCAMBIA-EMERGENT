from fastapi import FastAPI, APIRouter, Header, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import httpx
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta, timezone
import stripe


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
FREE_VALUE_LIMIT_MXN = 2000
TRIAL_DAYS = 7
BUSINESS_TEST_EMAILS = {"diantrejimemez@gmail.com"}
PLAN_CONFIG = {
    "premium": {
        "label": "Premium Intercambia",
        "monthly_label": "5 USD/mes",
        "amount_cents_mxn": 10000,
        "features": ["Ver detalles premium", "Contactar trueques mayores a $2,000", "Ofertas destacadas"],
    },
    "advanced": {
        "label": "Cruce de datos",
        "monthly_label": "10 USD/mes",
        "amount_cents_mxn": 20000,
        "features": ["Premium incluido", "Intercambios sugeridos por categoría", "Cadenas de trueque sin IA"],
    },
    "business": {
        "label": "Premium Puntos de Trueque",
        "monthly_label": "20 USD/mes",
        "amount_cents_mxn": 40000,
        "features": ["Cruce de datos incluido", "Registro de negocio", "Publicidad local como punto seguro"],
    },
}

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Helpers
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Define Models
class Profile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    handle: str
    city: str
    bio: str
    avatar_key: str = "avatar_woman"
    friends: int = 0
    completed_trades: int = 0
    circular_impact: str = "0 kg reutilizados"
    email: str = ""
    picture_url: str = ""
    phone: str = ""
    phone_verified: bool = False
    reputation_score: float = 0
    plan: str = "free"
    plan_label: str = "Gratis"
    is_premium: bool = False
    advanced_access: bool = False
    free_value_limit: float = FREE_VALUE_LIMIT_MXN
    trial_active: bool = False
    trial_ends_at: str = ""
    trial_days_left: int = 0
    created_at: str = Field(default_factory=now_iso)


class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "demo-user"
    owner_type: str = "user"
    business_id: str = ""
    owner_name: str = "Mariana Ríos"
    title: str
    description: str
    kind: str = "producto"
    listing_type: str = "oferta"
    category: str = "General"
    condition: str = "Usado"
    pricing_model: str = "valor estimado"
    estimated_value: float = 0
    currency: str = "MXN"
    exchange_for: str = ""
    location: str = "Centro"
    image_key: str = "camera"
    images: List[str] = []
    tags: List[str] = []
    accepts_higher_value: bool = False
    opportunity_trade: bool = False
    prefers_sale: bool = False
    accepts_partial_cash: bool = False
    negotiable: bool = True
    search_radius_km: int = 25
    city: str = "CDMX"
    status: str = "activo"
    likes: int = 0
    comments: int = 0
    requires_premium_contact: bool = False
    created_at: str = Field(default_factory=now_iso)


class ItemCreate(BaseModel):
    title: str
    description: str
    kind: str = "producto"
    listing_type: str = "oferta"
    category: str = "General"
    condition: str = "Usado"
    pricing_model: str = "valor estimado"
    estimated_value: float = 0
    currency: str = "MXN"
    exchange_for: str = ""
    location: str = "Centro"
    image_key: str = "box"
    images: List[str] = []
    tags: List[str] = []
    accepts_higher_value: bool = False
    opportunity_trade: bool = False
    prefers_sale: bool = False
    accepts_partial_cash: bool = False
    negotiable: bool = True
    search_radius_km: int = 25
    city: str = "CDMX"


class ItemStatusUpdate(BaseModel):
    status: str


class BarterPoint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    business_type: str
    address: str
    zone: str
    latitude: float
    longitude: float
    accepts: List[str] = []
    perks: str
    is_premium: bool = True
    image_key: str = "cafe"
    created_at: str = Field(default_factory=now_iso)


class BarterPointCreate(BaseModel):
    name: str
    business_type: str
    address: str
    zone: str
    latitude: float = 19.4326
    longitude: float = -99.1332
    accepts: List[str] = []
    perks: str = "Acepta trueque parcial"


class BusinessPage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_user_id: str
    name: str
    public_handle: str = ""
    profile_type: str = "persona_moral"
    category: str
    address: str
    description: str
    logo_key: str = "store"
    is_barter_store: bool = True
    status: str = "activo"
    items: List[Item] = []
    created_at: str = Field(default_factory=now_iso)


class BusinessCreate(BaseModel):
    name: str
    category: str
    address: str
    description: str
    profile_type: str = "persona_moral"
    logo_key: str = "store"


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    profile_type: Optional[str] = None


class PhoneUpdate(BaseModel):
    phone: str


class PhoneVerify(BaseModel):
    code: str


class FriendPhoneRequest(BaseModel):
    phone: str


class GoogleSessionRequest(BaseModel):
    session_id: str


class AuthUser(BaseModel):
    user_id: str
    email: str
    name: str
    picture_url: str = ""
    plan: str = "free"
    plan_label: str = "Gratis"
    is_premium: bool = False
    advanced_access: bool = False
    business_limit: Optional[int] = 1
    trial_active: bool = False
    trial_ends_at: str = ""
    trial_days_left: int = 0
    session_token: Optional[str] = None


class CheckoutCreate(BaseModel):
    tier: str
    return_url: str = ""


class CheckoutResponse(BaseModel):
    url: str


class PlanOption(BaseModel):
    tier: str
    label: str
    monthly_label: str
    features: List[str]


class Friend(BaseModel):
    id: str
    name: str
    handle: str
    status: str = "amigo"
    city: str = "CDMX"


class TradeHistory(BaseModel):
    id: str
    title: str
    gave: str
    received: str
    gave_value: float
    received_value: float
    result_value: float
    status: str = "truequeado"
    created_at: str = Field(default_factory=now_iso)


class SuggestedMatch(BaseModel):
    id: str
    source_item_id: str
    source_title: str
    matched_item_id: str
    matched_title: str
    matched_owner: str
    reason: str
    value_delta: float = 0


class InterestCreate(BaseModel):
    item_id: str
    message: str = "Me interesa intercambiar contigo."


class Interest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str
    from_user_id: str = "demo-user"
    message: str
    status: str = "nuevo"
    created_at: str = Field(default_factory=now_iso)


class ChatPreview(BaseModel):
    id: str
    with_user: str
    avatar_key: str
    last_message: str
    related_item: str
    unread: int = 0


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chat_id: str
    sender_id: str = "demo-user"
    sender_name: str = "Mariana Ríos"
    text: str
    created_at: str = Field(default_factory=now_iso)


class ChatMessageCreate(BaseModel):
    text: str


class TradeChain(BaseModel):
    id: str
    title: str
    steps: List[str]
    estimated_gain: str
    distance: str
    premium: bool = True


class Bootstrap(BaseModel):
    profile: Profile
    feed: List[Item]
    offers: List[Item]
    wishes: List[Item]
    barter_points: List[BarterPoint]
    businesses: List[BusinessPage] = []
    friends: List[Friend] = []
    trade_history: List[TradeHistory] = []
    suggested_matches: List[SuggestedMatch] = []
    chats: List[ChatPreview]
    trade_chains: List[TradeChain]
    plans: List[PlanOption] = []

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Intercambia API lista"}


def plan_label(plan: str) -> str:
    if plan == "business":
        return "Premium Puntos"
    if plan == "advanced":
        return "Cruce de datos"
    if plan == "premium":
        return "Premium"
    return "Gratis"


def parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def trial_info(doc: Optional[dict]) -> dict:
    trial_end = parse_dt((doc or {}).get("trial_ends_at"))
    now = datetime.now(timezone.utc)
    active = bool(trial_end and trial_end > now)
    days_left = max(0, (trial_end - now).days + (1 if active and (trial_end - now).seconds > 0 else 0)) if trial_end else 0
    return {
        "trial_active": active,
        "trial_ends_at": trial_end.isoformat() if trial_end else "",
        "trial_days_left": days_left,
    }


def has_full_access(doc: Optional[dict]) -> bool:
    return (doc or {}).get("plan", "free") in {"premium", "advanced", "business"} or trial_info(doc)["trial_active"]


def has_advanced_access(doc: Optional[dict]) -> bool:
    return (doc or {}).get("plan", "free") in {"advanced", "business"} or trial_info(doc)["trial_active"]


def has_business_access(doc: Optional[dict]) -> bool:
    return (doc or {}).get("plan", "free") == "business" or trial_info(doc)["trial_active"]


def is_premium_plan(plan: str) -> bool:
    return plan in {"premium", "advanced", "business"}


def public_user(doc: dict, session_token: Optional[str] = None) -> AuthUser:
    plan = doc.get("plan", "free")
    trial = trial_info(doc)
    return AuthUser(
        user_id=doc["user_id"],
        email=doc.get("email", ""),
        name=doc.get("name", "Usuario Intercambia"),
        picture_url=doc.get("picture_url", ""),
        plan=plan,
        plan_label="Prueba completa" if trial["trial_active"] and plan == "free" else plan_label(plan),
        is_premium=has_full_access(doc),
        advanced_access=has_advanced_access(doc),
        business_limit=None if has_full_access(doc) else 1,
        **trial,
        session_token=session_token,
    )


async def get_optional_user(authorization: Optional[str]) -> Optional[dict]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        return None
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        await db.user_sessions.delete_one({"session_token": token})
        return None
    return await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})


async def require_user(authorization: Optional[str]) -> dict:
    user = await get_optional_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Inicia sesión con Google")
    return user


async def profile_for_user(user: Optional[dict]) -> Profile:
    if not user:
        doc = await db.profiles.find_one({"id": "demo-user"}, {"_id": 0})
        return Profile(**doc)
    plan = user.get("plan", "free")
    trial = trial_info(user)
    history_docs = await db.trade_history.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(200)
    impact_value = sum(float(doc.get("received_value", 0)) - float(doc.get("gave_value", 0)) for doc in history_docs)
    impact_label = f"${impact_value:,.0f} MXN beneficio" if impact_value >= 0 else f"-${abs(impact_value):,.0f} MXN pérdida"
    return Profile(
        id=user["user_id"],
        name=user.get("name", "Usuario Intercambia"),
        handle="@" + user.get("email", "usuario").split("@")[0].replace(".", ""),
        city=user.get("city", "Mi comunidad"),
        bio=user.get("bio", "Perfil listo para publicar ofertas, deseos y tiendas de trueque."),
        avatar_key="avatar_woman",
        friends=user.get("friends", 0),
        completed_trades=user.get("completed_trades", 0),
        circular_impact=impact_label,
        email=user.get("email", ""),
        picture_url=user.get("picture_url", ""),
        phone=user.get("phone", ""),
        phone_verified=user.get("phone_verified", False),
        reputation_score=float(user.get("reputation_score", 82 if user.get("phone_verified") else 60)),
        plan=plan,
        plan_label="Prueba completa" if trial["trial_active"] and plan == "free" else plan_label(plan),
        is_premium=has_full_access(user),
        advanced_access=has_advanced_access(user),
        **trial,
    )


def add_item_entitlements(item: dict, user: Optional[dict]) -> dict:
    item = dict(item)
    premium_locked = item.get("estimated_value", 0) > FREE_VALUE_LIMIT_MXN and not has_full_access(user)
    item["requires_premium_contact"] = premium_locked
    if premium_locked:
        item["description"] = "Contenido premium: actualiza tu plan para ver detalles completos y ofertar."
        item["exchange_for"] = "Disponible para miembros Premium"
        item["images"] = []
    return item


async def suggested_matches_for(user_id: str) -> List[SuggestedMatch]:
    my_items = await db.items.find({"user_id": user_id, "status": "activo", "listing_type": "oferta"}, {"_id": 0}).to_list(50)
    matches: List[SuggestedMatch] = []
    for source in my_items:
        candidates = await db.items.find({
            "status": "activo",
            "listing_type": "deseo",
            "user_id": {"$ne": user_id},
            "$or": [
                {"category": source.get("category")},
                {"tags": {"$in": source.get("tags", [])}},
            ],
        }, {"_id": 0}).limit(5).to_list(5)
        for candidate in candidates:
            matches.append(SuggestedMatch(
                id=f"match_{source['id']}_{candidate['id']}",
                source_item_id=source["id"],
                source_title=source["title"],
                matched_item_id=candidate["id"],
                matched_title=candidate["title"],
                matched_owner=candidate.get("owner_name", "Usuario"),
                reason=f"Coinciden por categoría/tag: {source.get('category', 'General')}",
                value_delta=float(candidate.get("estimated_value", 0)) - float(source.get("estimated_value", 0)),
            ))
    return matches[:10]


def business_handle(name: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return "@" + (normalized or "tienda_trueque")[:28]


async def attach_business_items(business_docs: List[dict]) -> List[BusinessPage]:
    pages = []
    for doc in business_docs:
        item_docs = await db.items.find(
            {"business_id": doc["id"], "owner_type": "business", "status": {"$ne": "eliminado"}},
            {"_id": 0},
        ).sort("created_at", -1).to_list(30)
        doc = dict(doc)
        doc["items"] = [Item(**item) for item in item_docs]
        pages.append(BusinessPage(**doc))
    return pages


@api_router.post("/auth/google-session", response_model=AuthUser)
async def create_google_session(input: GoogleSessionRequest):
    async with httpx.AsyncClient(timeout=12) as http:
        response = await http.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": input.session_id})
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="No se pudo validar Google")
    payload = response.json()
    session_token = payload["session_token"]
    email = payload["email"].lower()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    user_id = existing["user_id"] if existing else f"user_{uuid.uuid4().hex[:12]}"
    trial_ends_at = (existing or {}).get("trial_ends_at") or (datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)).isoformat()
    assigned_plan = "business" if email in BUSINESS_TEST_EMAILS else (existing or {}).get("plan", "free")
    user_doc = {
        "user_id": user_id,
        "email": email,
        "name": payload.get("name") or email.split("@")[0],
        "picture_url": payload.get("picture", ""),
        "plan": assigned_plan,
        "trial_ends_at": trial_ends_at,
        "updated_at": now_iso(),
    }
    await db.users.update_one(
        {"email": email},
        {"$set": user_doc, "$setOnInsert": {"created_at": now_iso()}},
        upsert=True,
    )
    await db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": {"session_token": session_token, "user_id": user_id, "created_at": datetime.now(timezone.utc), "expires_at": datetime.now(timezone.utc) + timedelta(days=7)}},
        upsert=True,
    )
    return public_user({**user_doc, "plan": user_doc["plan"]}, session_token=session_token)


@api_router.get("/auth/me", response_model=AuthUser)
async def get_me(authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    return public_user(user)


@api_router.post("/auth/phone")
async def update_phone(input: PhoneUpdate, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    normalized = "".join(ch for ch in input.phone if ch.isdigit() or ch == "+")[:18]
    if len(normalized) < 8:
        raise HTTPException(status_code=400, detail="Teléfono no válido")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"phone": normalized, "phone_verified": False, "phone_code": "123456"}})
    return {"ok": True, "message": "Código de prueba enviado", "test_code": "123456"}


@api_router.post("/auth/phone/verify")
async def verify_phone(input: PhoneVerify, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    if input.code != user.get("phone_code", "123456"):
        raise HTTPException(status_code=400, detail="Código incorrecto")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"phone_verified": True, "reputation_score": 82}, "$unset": {"phone_code": ""}})
    return {"ok": True}


@api_router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        await db.user_sessions.delete_one({"session_token": token})
    return {"ok": True}


@api_router.get("/plans", response_model=List[PlanOption])
async def get_plans():
    return [PlanOption(tier=tier, **data) for tier, data in PLAN_CONFIG.items()]


@api_router.get("/friends", response_model=List[Friend])
async def get_friends(authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    user_id = user["user_id"] if user else "demo-user"
    docs = await db.friends.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    return [Friend(**doc) for doc in docs]


@api_router.post("/friends/{friend_id}/action")
async def friend_action(friend_id: str, action: str, authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    user_id = user["user_id"] if user else "demo-user"
    if action not in {"agregar", "bloquear", "reportar"}:
        raise HTTPException(status_code=400, detail="Acción no válida")
    await db.friend_actions.insert_one({"user_id": user_id, "friend_id": friend_id, "action": action, "created_at": now_iso()})
    if action == "bloquear":
        await db.friends.update_one({"user_id": user_id, "id": friend_id}, {"$set": {"status": "bloqueado"}})
    if action == "reportar":
        await db.friends.update_one({"user_id": user_id, "id": friend_id}, {"$set": {"status": "reportado"}})
    return {"ok": True}


@api_router.post("/friends/by-phone")
async def add_friend_by_phone(input: FriendPhoneRequest, authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    user_id = user["user_id"] if user else "demo-user"
    normalized = "".join(ch for ch in input.phone if ch.isdigit() or ch == "+")[:18]
    target = await db.users.find_one({"phone": normalized, "phone_verified": True}, {"_id": 0})
    request_doc = {
        "id": f"friend_req_{uuid.uuid4().hex[:10]}",
        "user_id": user_id,
        "phone": normalized,
        "target_user_id": target.get("user_id") if target else "pendiente",
        "status": "solicitud_enviada" if target else "pendiente_por_registro",
        "created_at": now_iso(),
    }
    await db.friend_requests.insert_one(request_doc)
    return {"ok": True, "status": request_doc["status"]}


@api_router.get("/trade-history", response_model=List[TradeHistory])
async def get_trade_history(authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    user_id = user["user_id"] if user else "demo-user"
    docs = await db.trade_history.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [TradeHistory(**doc) for doc in docs]


@api_router.get("/matches", response_model=List[SuggestedMatch])
async def get_matches(authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    user_id = user["user_id"] if user else "demo-user"
    return await suggested_matches_for(user_id)


@api_router.get("/bootstrap", response_model=Bootstrap)
async def get_bootstrap(authorization: Optional[str] = Header(None)):
    await seed_demo_data()
    user = await get_optional_user(authorization)
    profile = await profile_for_user(user)
    user_id = user["user_id"] if user else "demo-user"
    feed_docs = await db.items.find({"status": "activo"}, {"_id": 0}).sort("created_at", -1).to_list(50)
    visible_owner_query = {"user_id": user_id, "status": {"$ne": "eliminado"}}
    offer_docs = await db.items.find({**visible_owner_query, "listing_type": "oferta"}, {"_id": 0}).sort("created_at", -1).to_list(50)
    wish_docs = await db.items.find({**visible_owner_query, "listing_type": "deseo"}, {"_id": 0}).sort("created_at", -1).to_list(50)
    point_docs = await db.barter_points.find({}, {"_id": 0}).to_list(50)
    business_docs = await db.businesses.find({"owner_user_id": user_id, "status": {"$ne": "eliminado"}}, {"_id": 0}).to_list(50)
    friend_docs = await db.friends.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    history_docs = await db.trade_history.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    chat_docs = await db.chats.find({}, {"_id": 0}).to_list(20)
    chain_docs = await db.trade_chains.find({}, {"_id": 0}).to_list(20)
    return Bootstrap(
        profile=profile,
        feed=[Item(**add_item_entitlements(doc, user)) for doc in feed_docs],
        offers=[Item(**doc) for doc in offer_docs],
        wishes=[Item(**doc) for doc in wish_docs],
        barter_points=[BarterPoint(**doc) for doc in point_docs],
        businesses=await attach_business_items(business_docs),
        friends=[Friend(**doc) for doc in friend_docs],
        trade_history=[TradeHistory(**doc) for doc in history_docs],
        suggested_matches=await suggested_matches_for(user_id),
        chats=[ChatPreview(**doc) for doc in chat_docs],
        trade_chains=[TradeChain(**doc) for doc in chain_docs],
        plans=[PlanOption(tier=tier, **data) for tier, data in PLAN_CONFIG.items()],
    )


@api_router.get("/items", response_model=List[Item])
async def get_items(listing_type: Optional[str] = None, category: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    query = {"status": "activo"}
    if listing_type:
        query["listing_type"] = listing_type
    if category and category != "Todo":
        query["category"] = category
    docs = await db.items.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [Item(**add_item_entitlements(doc, user)) for doc in docs]


@api_router.post("/items", response_model=Item)
async def create_item(input: ItemCreate, authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    if input.estimated_value > FREE_VALUE_LIMIT_MXN and not has_full_access(user):
        raise HTTPException(status_code=402, detail="Los usuarios gratis no pueden publicar artículos mayores a $2,000 MXN")
    item = Item(**input.model_dump())
    if user:
        item.user_id = user["user_id"]
        item.owner_name = user.get("name", "Usuario Intercambia")
    await db.items.insert_one(item.model_dump())
    return item


@api_router.patch("/items/{item_id}/status", response_model=Item)
async def update_item_status(item_id: str, input: ItemStatusUpdate, authorization: Optional[str] = Header(None)):
    allowed_statuses = {"activo", "pausado", "vendido", "truequeado"}
    if input.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Estado no válido")
    user = await get_optional_user(authorization)
    owner_id = user["user_id"] if user else "demo-user"
    result = await db.items.update_one(
        {"id": item_id, "user_id": owner_id, "status": {"$ne": "eliminado"}},
        {"$set": {"status": input.status, "updated_at": now_iso()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Publicación no encontrada en tu bodega")
    doc = await db.items.find_one({"id": item_id}, {"_id": 0})
    return Item(**doc)


@api_router.delete("/items/{item_id}")
async def delete_item(item_id: str, authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    owner_id = user["user_id"] if user else "demo-user"
    result = await db.items.update_one(
        {"id": item_id, "user_id": owner_id, "status": {"$ne": "eliminado"}},
        {"$set": {"status": "eliminado", "deleted_at": now_iso(), "updated_at": now_iso()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Publicación no encontrada en tu bodega")
    return {"ok": True}


@api_router.get("/businesses", response_model=List[BusinessPage])
async def get_businesses(authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    docs = await db.businesses.find({"owner_user_id": user["user_id"], "status": {"$ne": "eliminado"}}, {"_id": 0}).to_list(100)
    return [BusinessPage(**doc) for doc in docs]


@api_router.post("/businesses", response_model=BusinessPage)
async def create_business(input: BusinessCreate, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    count = await db.businesses.count_documents({"owner_user_id": user["user_id"]})
    if not has_full_access(user) and count >= 1:
        raise HTTPException(status_code=402, detail="El plan gratis permite registrar 1 tienda de trueque")
    business = BusinessPage(
        owner_user_id=user["user_id"],
        public_handle=business_handle(input.name),
        **input.model_dump(),
    )
    business_doc = business.model_dump()
    business_doc.pop("items", None)
    await db.businesses.insert_one(business_doc)
    await db.barter_points.insert_one(BarterPoint(
        name=business.name,
        business_type=business.category,
        address=business.address,
        zone="Registrado por usuario",
        latitude=19.4326,
        longitude=-99.1332,
        accepts=["Intercambios locales", "Punto seguro", "Prueba de aparatos"],
        perks=f"{business.description} Punto seguro para trueques; puede ofrecer electricidad, descuentos o trueque parcial según disponibilidad.",
        image_key="store",
    ).model_dump())
    return business


@api_router.patch("/businesses/{business_id}", response_model=BusinessPage)
async def update_business(business_id: str, input: BusinessUpdate, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    updates = {k: v for k, v in input.model_dump().items() if v is not None}
    if "name" in updates:
        updates["public_handle"] = business_handle(updates["name"])
    if not updates:
        raise HTTPException(status_code=400, detail="Sin cambios")
    result = await db.businesses.update_one({"id": business_id, "owner_user_id": user["user_id"], "status": {"$ne": "eliminado"}}, {"$set": {**updates, "updated_at": now_iso()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    doc = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    pages = await attach_business_items([doc])
    return pages[0]


@api_router.delete("/businesses/{business_id}")
async def delete_business(business_id: str, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    result = await db.businesses.update_one({"id": business_id, "owner_user_id": user["user_id"], "status": {"$ne": "eliminado"}}, {"$set": {"status": "eliminado", "deleted_at": now_iso()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    await db.items.update_many({"business_id": business_id}, {"$set": {"status": "eliminado", "updated_at": now_iso()}})
    await db.barter_points.update_many({"name": (await db.businesses.find_one({"id": business_id}, {"_id": 0}) or {}).get("name", "")}, {"$set": {"is_premium": False}})
    return {"ok": True}


@api_router.get("/businesses/{business_id}", response_model=BusinessPage)
async def get_business_page(business_id: str):
    doc = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Página de negocio no encontrada")
    pages = await attach_business_items([doc])
    return pages[0]


@api_router.post("/businesses/{business_id}/items", response_model=Item)
async def create_business_item(business_id: str, input: ItemCreate, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    business = await db.businesses.find_one({"id": business_id, "owner_user_id": user["user_id"]}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Página de negocio no encontrada en tu cuenta")
    if input.estimated_value > FREE_VALUE_LIMIT_MXN and not has_full_access(user):
        raise HTTPException(status_code=402, detail="Necesitas prueba/premium para publicar valores mayores a $2,000 MXN")
    item_data = input.model_dump()
    item_data["location"] = business.get("address") or input.location
    item = Item(
        **item_data,
        user_id=user["user_id"],
        owner_type="business",
        business_id=business_id,
        owner_name=business["name"],
    )
    await db.items.insert_one(item.model_dump())
    return item


@api_router.post("/billing/create-checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(input: CheckoutCreate, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    if input.tier not in PLAN_CONFIG:
        raise HTTPException(status_code=400, detail="Plan no válido")
    if not os.environ.get("STRIPE_SECRET_KEY"):
        raise HTTPException(status_code=503, detail="Stripe no está configurado todavía")
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(email=user.get("email"), name=user.get("name"), metadata={"app_user_id": user["user_id"]})
        customer_id = customer.id
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"stripe_customer_id": customer_id}})
    plan = PLAN_CONFIG[input.tier]
    return_url = input.return_url or os.environ.get("FRONTEND_URL", "")
    if not return_url:
        raise HTTPException(status_code=400, detail="return_url requerido para iniciar checkout")
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{
            "quantity": 1,
            "price_data": {
                "currency": "mxn",
                "unit_amount": plan["amount_cents_mxn"],
                "recurring": {"interval": "month"},
                "product_data": {"name": plan["label"]},
            },
        }],
        success_url=f"{return_url}?billing=success",
        cancel_url=f"{return_url}?billing=cancel",
        subscription_data={"metadata": {"app_user_id": user["user_id"], "tier": input.tier}},
    )
    await db.billing_events.insert_one({"user_id": user["user_id"], "tier": input.tier, "checkout_session_id": session.id, "created_at": now_iso()})
    return CheckoutResponse(url=session.url)


@api_router.get("/barter-points", response_model=List[BarterPoint])
async def get_barter_points():
    docs = await db.barter_points.find({}, {"_id": 0}).to_list(100)
    return [BarterPoint(**doc) for doc in docs]


@api_router.post("/barter-points", response_model=BarterPoint)
async def create_barter_point(input: BarterPointCreate):
    point = BarterPoint(**input.model_dump())
    await db.barter_points.insert_one(point.model_dump())
    return point


@api_router.post("/interests", response_model=Interest)
async def create_interest(input: InterestCreate, authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    item = await db.items.find_one({"id": input.item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    if item.get("estimated_value", 0) > FREE_VALUE_LIMIT_MXN and not has_full_access(user):
        raise HTTPException(status_code=402, detail="Necesitas Premium para contactar trueques mayores a $2,000 MXN")
    interest = Interest(**input.model_dump())
    if user:
        interest.from_user_id = user["user_id"]
    await db.interests.insert_one(interest.model_dump())
    await db.items.update_one({"id": input.item_id}, {"$inc": {"likes": 1}})
    return interest


@api_router.get("/trade-chains", response_model=List[TradeChain])
async def get_trade_chains():
    docs = await db.trade_chains.find({}, {"_id": 0}).to_list(20)
    return [TradeChain(**doc) for doc in docs]


@api_router.get("/chats/{chat_id}/messages", response_model=List[ChatMessage])
async def get_chat_messages(chat_id: str):
    docs = await db.chat_messages.find({"chat_id": chat_id}, {"_id": 0}).sort("created_at", 1).to_list(100)
    return [ChatMessage(**doc) for doc in docs]


@api_router.post("/chats/{chat_id}/messages", response_model=ChatMessage)
async def send_chat_message(chat_id: str, input: ChatMessageCreate, authorization: Optional[str] = Header(None)):
    user = await get_optional_user(authorization)
    message = ChatMessage(
        chat_id=chat_id,
        sender_id=user["user_id"] if user else "demo-user",
        sender_name=user.get("name", "Mariana Ríos") if user else "Mariana Ríos",
        text=input.text.strip(),
    )
    if not message.text:
        raise HTTPException(status_code=400, detail="Mensaje vacío")
    await db.chat_messages.insert_one(message.model_dump())
    await db.chats.update_one({"id": chat_id}, {"$set": {"last_message": message.text}})
    return message


@app.on_event("startup")
async def startup_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)


async def seed_demo_data():
    if await db.profiles.count_documents({"id": "demo-user"}) == 0:
        await db.profiles.insert_one(Profile(
            id="demo-user",
            name="Mariana Ríos",
            handle="@mariana.circular",
            city="CDMX Centro",
            bio="Diseñadora, fan de reparar antes que comprar. Intercambio objetos, talleres y asesorías.",
            friends=128,
            completed_trades=34,
            circular_impact="82 kg reutilizados",
        ).model_dump())

    if await db.items.count_documents({}) == 0:
        demo_items = [
            Item(
                title="Cámara analógica Pentax",
                description="Funciona perfecto, incluye correa. Ideal para fotografía creativa.",
                kind="producto",
                listing_type="oferta",
                category="Tecnología",
                condition="Usado",
                estimated_value=2200,
                exchange_for="Bicicleta urbana, clases de guitarra o reparación de laptop",
                location="Roma Norte",
                image_key="camera",
                tags=["cámara", "fotografía", "analógica", "pentax"],
                likes=18,
                comments=5,
            ),
            Item(
                title="Taller de huerto urbano",
                description="Sesión de 2 horas para montar un huerto en balcón o azotea.",
                kind="servicio",
                listing_type="oferta",
                category="Oficios",
                condition="Servicio",
                pricing_model="por hora",
                estimated_value=650,
                exchange_for="Diseño de logo, café de especialidad o libros de cocina",
                location="Coyoacán",
                image_key="plants",
                tags=["huerto", "plantas", "taller", "oficio"],
                likes=31,
                comments=9,
            ),
            Item(
                title="Colección de libros de cocina",
                description="8 libros en buen estado sobre panadería, comida mexicana y fermentos.",
                kind="producto",
                listing_type="oferta",
                category="Hogar",
                condition="Usado",
                estimated_value=900,
                exchange_for="Macetas, plantas aromáticas o lámpara de escritorio",
                location="Del Valle",
                image_key="books",
                tags=["libros", "cocina", "hogar", "panadería"],
                likes=12,
                comments=2,
            ),
            Item(
                title="Busco bicicleta plegable",
                description="La necesito para moverme entre puntos de entrega y trueque.",
                kind="producto",
                listing_type="deseo",
                category="Movilidad",
                condition="Nuevo o usado",
                estimated_value=3500,
                exchange_for="Puedo ofrecer cámara, diseño gráfico o taller de huerto",
                location="Centro",
                image_key="bike",
                tags=["bicicleta", "movilidad", "plegable", "transporte"],
                likes=6,
                comments=1,
            ),
            Item(
                title="Busco reparación de laptop",
                description="Necesito diagnóstico y cambio de teclado para equipo de trabajo.",
                kind="servicio",
                listing_type="deseo",
                category="Tecnología",
                condition="Servicio",
                pricing_model="a destajo",
                estimated_value=1200,
                exchange_for="Diseño de identidad, libros o asesoría de redes sociales",
                location="Narvarte",
                image_key="laptop",
                tags=["laptop", "reparación", "tecnología", "teclado"],
                likes=9,
                comments=4,
            ),
        ]
        await db.items.insert_many([item.model_dump() for item in demo_items])
    else:
        await db.items.update_many({"tags": {"$exists": False}}, {"$set": {"tags": ["trueque", "intercambia"]}})
        await db.items.update_many({"images": {"$exists": False}}, {"$set": {"images": []}})

    if await db.barter_points.count_documents({}) == 0:
        points = [
            BarterPoint(
                name="Café Semilla",
                business_type="Cafetería",
                address="Calle Colima 143, Roma Norte",
                zone="Roma Norte",
                latitude=19.4196,
                longitude=-99.1605,
                accepts=["Libros", "Plantas", "Tazas", "Servicios creativos"],
                perks="Acepta hasta 30% del consumo en trueque y organiza mesas cada viernes.",
            ),
            BarterPoint(
                name="Mercado Circular Centro",
                business_type="Plaza local",
                address="República de Uruguay 52, Centro",
                zone="Centro",
                latitude=19.4319,
                longitude=-99.1362,
                accepts=["Herramientas", "Ropa", "Electrónica", "Oficios"],
                perks="Punto premium para cadenas de trueque y encuentros seguros.",
                image_key="market",
            ),
            BarterPoint(
                name="Taller La Tuerca",
                business_type="Taller de reparación",
                address="Av. Universidad 900, Del Valle",
                zone="Del Valle",
                latitude=19.3769,
                longitude=-99.1638,
                accepts=["Refacciones", "Bicicletas", "Servicios digitales"],
                perks="Recibe trueque parcial por mantenimiento de bicis y electrodomésticos.",
                image_key="workshop",
            ),
        ]
        await db.barter_points.insert_many([point.model_dump() for point in points])

    if await db.chats.count_documents({}) == 0:
        chats = [
            ChatPreview(id="chat-ana", with_user="Ana Paredes", avatar_key="avatar_woman", last_message="Tengo una bici plegable, ¿te interesa verla en Café Semilla?", related_item="Busco bicicleta plegable", unread=2),
            ChatPreview(id="chat-luis", with_user="Luis Torres", avatar_key="avatar_man", last_message="Puedo reparar tu laptop a cambio del diseño del menú.", related_item="Busco reparación de laptop", unread=0),
        ]
        await db.chats.insert_many([chat.model_dump() for chat in chats])

    if await db.chat_messages.count_documents({}) == 0:
        messages = [
            ChatMessage(chat_id="chat-ana", sender_id="ana", sender_name="Ana Paredes", text="Hola, vi que buscas una bici plegable."),
            ChatMessage(chat_id="chat-ana", sender_id="demo-user", sender_name="Mariana Ríos", text="Sí, puedo cambiar cámara o diseño gráfico."),
            ChatMessage(chat_id="chat-luis", sender_id="luis", sender_name="Luis Torres", text="Puedo revisar la laptop en Taller La Tuerca."),
        ]
        await db.chat_messages.insert_many([message.model_dump() for message in messages])

    if await db.friends.count_documents({"user_id": "demo-user"}) == 0:
        friends = [
            Friend(id="ana", name="Ana Paredes", handle="@ana.bici", city="Roma Norte"),
            Friend(id="luis", name="Luis Torres", handle="@luis.repara", city="Del Valle"),
            Friend(id="sofia", name="Sofía Mercado", handle="@sofi.circular", city="Coyoacán"),
        ]
        await db.friends.insert_many([{**friend.model_dump(), "user_id": "demo-user"} for friend in friends])

    if await db.trade_history.count_documents({"user_id": "demo-user"}) == 0:
        history = [
            TradeHistory(id="hist-1", title="Libros por lámpara", gave="Libros de cocina", received="Lámpara de escritorio", gave_value=700, received_value=950, result_value=250),
            TradeHistory(id="hist-2", title="Diseño por reparación", gave="Diseño de menú", received="Reparación de tablet", gave_value=1200, received_value=1000, result_value=-200),
        ]
        await db.trade_history.insert_many([{**trade.model_dump(), "user_id": "demo-user"} for trade in history])

    if await db.trade_chains.count_documents({}) == 0:
        chains = [
            TradeChain(
                id="chain-clip-bike",
                title="De cámara a bicicleta en 3 pasos",
                steps=["Cámara Pentax → sesión de fotos", "Sesión → reparación de bici", "Bici reparada → bicicleta plegable"],
                estimated_gain="+42% valor percibido",
                distance="4.8 km entre participantes",
            ),
            TradeChain(
                id="chain-local-food",
                title="Triangulación productiva local",
                steps=["Taller de huerto → cafetería", "Café molido → panadería", "Pan artesanal → libros de cocina"],
                estimated_gain="Red local fortalecida",
                distance="2.1 km circuito completo",
            ),
        ]
        await db.trade_chains.insert_many([chain.model_dump() for chain in chains])

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
