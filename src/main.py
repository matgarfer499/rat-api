from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.categories.router import router as categories_router
from src.database import init_db
from src.words.router import router as words_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on application startup."""
    await init_db()
    yield


app = FastAPI(
    title="RAT API",
    description="API for managing categories and words",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(categories_router)
app.include_router(words_router)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
