from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.categories.router import router as categories_router
from src.database import init_db
from src.game.router import router as game_router
from src.words.router import router as words_router
from src.rooms.router import router as rooms_router
from src.redis.client import redis_client
from src.sockets.redis_listener import redis_listener
from src.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and Redis on application startup."""
    await init_db()
    
    # Connect to Redis
    await redis_client.connect()
    
    # Start Redis Pub/Sub listener in background
    asyncio.create_task(redis_listener())
    
    yield
    
    # Cleanup on shutdown
    await redis_client.disconnect()


app = FastAPI(
    title="RAT API",
    description="API for managing categories and words",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(words_router)
app.include_router(game_router)
app.include_router(rooms_router)

# Mount Socket.IO ASGI app
from src.sockets.server import socket_app
app.mount("/socket.io", socket_app)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
