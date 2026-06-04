from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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
    chats: List[ChatPreview]
    trade_chains: List[TradeChain]

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Intercambia API lista"}


@api_router.get("/bootstrap", response_model=Bootstrap)
async def get_bootstrap():
    await seed_demo_data()
    profile_doc = await db.profiles.find_one({"id": "demo-user"}, {"_id": 0})
    feed_docs = await db.items.find({"status": "activo"}, {"_id": 0}).sort("created_at", -1).to_list(50)
    offer_docs = await db.items.find({"listing_type": "oferta", "user_id": "demo-user"}, {"_id": 0}).sort("created_at", -1).to_list(50)
    wish_docs = await db.items.find({"listing_type": "deseo", "user_id": "demo-user"}, {"_id": 0}).sort("created_at", -1).to_list(50)
    point_docs = await db.barter_points.find({}, {"_id": 0}).to_list(50)
    chat_docs = await db.chats.find({}, {"_id": 0}).to_list(20)
    chain_docs = await db.trade_chains.find({}, {"_id": 0}).to_list(20)
    return Bootstrap(
        profile=Profile(**profile_doc),
        feed=[Item(**doc) for doc in feed_docs],
        offers=[Item(**doc) for doc in offer_docs],
        wishes=[Item(**doc) for doc in wish_docs],
        barter_points=[BarterPoint(**doc) for doc in point_docs],
        chats=[ChatPreview(**doc) for doc in chat_docs],
        trade_chains=[TradeChain(**doc) for doc in chain_docs],
    )


@api_router.get("/items", response_model=List[Item])
async def get_items(listing_type: Optional[str] = None, category: Optional[str] = None):
    query = {"status": "activo"}
    if listing_type:
        query["listing_type"] = listing_type
    if category and category != "Todo":
        query["category"] = category
    docs = await db.items.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [Item(**doc) for doc in docs]


@api_router.post("/items", response_model=Item)
async def create_item(input: ItemCreate):
    item = Item(**input.model_dump())
    await db.items.insert_one(item.model_dump())
    return item


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
async def create_interest(input: InterestCreate):
    item = await db.items.find_one({"id": input.item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Publicación no encontrada")
    interest = Interest(**input.model_dump())
    await db.interests.insert_one(interest.model_dump())
    await db.items.update_one({"id": input.item_id}, {"$inc": {"likes": 1}})
    return interest


@api_router.get("/trade-chains", response_model=List[TradeChain])
async def get_trade_chains():
    docs = await db.trade_chains.find({}, {"_id": 0}).to_list(20)
    return [TradeChain(**doc) for doc in docs]


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
