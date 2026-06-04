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
PLAN_CONFIG = {
    "premium": {
        "label": "Premium Intercambia",
        "monthly_label": "≈ 2 USD/mes en moneda local",
        "amount_cents_mxn": 4000,
        "features": ["Contactar trueques mayores a $2,000", "Registrar negocios ilimitados", "Ver puntos premium"],
    },
    "advanced": {
        "label": "Cruce de datos",
        "monthly_label": "≈ 10 USD/mes en moneda local",
        "amount_cents_mxn": 20000,
        "features": ["Cadenas de trueque avanzadas", "Triangulación geográfica", "Sugerencias productivas locales"],
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
    plan: str = "free"
    plan_label: str = "Gratis"
    is_premium: bool = False
    advanced_access: bool = False
    free_value_limit: float = FREE_VALUE_LIMIT_MXN
    created_at: str = Field(default_factory=now_iso)


class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "demo-user"
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
    exchange_for: str
    location: str = "Centro"
    image_key: str = "camera"
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
    exchange_for: str
    location: str = "Centro"
    image_key: str = "box"


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
    category: str
    address: str
    description: str
    logo_key: str = "store"
    is_barter_store: bool = True
    created_at: str = Field(default_factory=now_iso)


class BusinessCreate(BaseModel):
    name: str
    category: str
    address: str
    description: str
    logo_key: str = "store"


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
    chats: List[ChatPreview]
    trade_chains: List[TradeChain]
    plans: List[PlanOption] = []

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Intercambia API lista"}


def plan_label(plan: str) -> str:
    if plan == "advanced":
        return "Cruce de datos"
    if plan == "premium":
        return "Premium"
    return "Gratis"


def is_premium_plan(plan: str) -> bool:
    return plan in {"premium", "advanced"}


def public_user(doc: dict, session_token: Optional[str] = None) -> AuthUser:
    plan = doc.get("plan", "free")
    return AuthUser(
        user_id=doc["user_id"],
        email=doc.get("email", ""),
        name=doc.get("name", "Usuario Intercambia"),
        picture_url=doc.get("picture_url", ""),
        plan=plan,
        plan_label=plan_label(plan),
        is_premium=is_premium_plan(plan),
        advanced_access=plan == "advanced",
        business_limit=None if is_premium_plan(plan) else 1,
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
    return Profile(
        id=user["user_id"],
        name=user.get("name", "Usuario Intercambia"),
        handle="@" + user.get("email", "usuario").split("@")[0].replace(".", ""),
        city=user.get("city", "Mi comunidad"),
        bio=user.get("bio", "Perfil listo para publicar ofertas, deseos y tiendas de trueque."),
        avatar_key="avatar_woman",
        friends=user.get("friends", 0),
        completed_trades=user.get("completed_trades", 0),
        circular_impact=user.get("circular_impact", "0 kg reutilizados"),
        email=user.get("email", ""),
        picture_url=user.get("picture_url", ""),
        plan=plan,
        plan_label=plan_label(plan),
        is_premium=is_premium_plan(plan),
        advanced_access=plan == "advanced",
    )


def add_item_entitlements(item: dict, user: Optional[dict]) -> dict:
    item = dict(item)
    item["requires_premium_contact"] = (
        item.get("estimated_value", 0) > FREE_VALUE_LIMIT_MXN
        and not is_premium_plan((user or {}).get("plan", "free"))
    )
    return item


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
    user_doc = {
        "user_id": user_id,
        "email": email,
        "name": payload.get("name") or email.split("@")[0],
        "picture_url": payload.get("picture", ""),
        "plan": (existing or {}).get("plan", "free"),
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


@api_router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        await db.user_sessions.delete_one({"session_token": token})
    return {"ok": True}


@api_router.get("/plans", response_model=List[PlanOption])
async def get_plans():
    return [PlanOption(tier=tier, **data) for tier, data in PLAN_CONFIG.items()]


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
    business_docs = await db.businesses.find({"owner_user_id": user_id}, {"_id": 0}).to_list(50)
    chat_docs = await db.chats.find({}, {"_id": 0}).to_list(20)
    chain_docs = await db.trade_chains.find({}, {"_id": 0}).to_list(20)
    return Bootstrap(
        profile=profile,
        feed=[Item(**add_item_entitlements(doc, user)) for doc in feed_docs],
        offers=[Item(**doc) for doc in offer_docs],
        wishes=[Item(**doc) for doc in wish_docs],
        barter_points=[BarterPoint(**doc) for doc in point_docs],
        businesses=[BusinessPage(**doc) for doc in business_docs],
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
    if input.estimated_value > FREE_VALUE_LIMIT_MXN and not is_premium_plan((user or {}).get("plan", "free")):
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
    docs = await db.businesses.find({"owner_user_id": user["user_id"]}, {"_id": 0}).to_list(100)
    return [BusinessPage(**doc) for doc in docs]


@api_router.post("/businesses", response_model=BusinessPage)
async def create_business(input: BusinessCreate, authorization: Optional[str] = Header(None)):
    user = await require_user(authorization)
    count = await db.businesses.count_documents({"owner_user_id": user["user_id"]})
    if not is_premium_plan(user.get("plan", "free")) and count >= 1:
        raise HTTPException(status_code=402, detail="El plan gratis permite registrar 1 tienda de trueque")
    business = BusinessPage(owner_user_id=user["user_id"], **input.model_dump())
    await db.businesses.insert_one(business.model_dump())
    await db.barter_points.insert_one(BarterPoint(
        name=business.name,
        business_type=business.category,
        address=business.address,
        zone="Registrado por usuario",
        latitude=19.4326,
        longitude=-99.1332,
        accepts=["Intercambios locales"],
        perks=business.description,
        image_key="store",
    ).model_dump())
    return business


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
    if item.get("estimated_value", 0) > FREE_VALUE_LIMIT_MXN and not is_premium_plan((user or {}).get("plan", "free")):
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
                likes=9,
                comments=4,
            ),
        ]
        await db.items.insert_many([item.model_dump() for item in demo_items])

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
