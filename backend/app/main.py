import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.routers import quote
from app.routers import analytics

from app.database import Base, engine, get_db
from app.schemas.inventory import StockUpdate
from app.services.inventory_service import update_stock as update_stock_service

# Import ALL models
from app.models import admin
from app.models import categories
from app.models import tile
from app.models import tile_image
from app.models import inventory
from app.models import search_log

# Import routers
from app.routers import auth
from app.routers import categories as cat_router
from app.routers import tiles
from app.routers import search
from app.routers.inventory import router as inv_router
from app.routers.inventory import loc_router
from ai.search import get_model

# Ensure pgvector extension and index exist (PostgreSQL)
with engine.connect() as connection:
    try:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as e:
        print(f"Warning: pgvector extension not available: {e}")

# Create tables
Base.metadata.create_all(bind=engine)

# Create pgvector index only if extension is available
pgvector_enabled = os.getenv("PGVECTOR_ENABLED", "false").lower() in ("1", "true", "yes")
if pgvector_enabled:
    with engine.connect() as connection:
        try:
            connection.execute(text(
                """
                CREATE INDEX IF NOT EXISTS idx_tile_embeddings_vector
                ON tile_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                """
            ))
        except Exception as e:
            print(f"Warning: Could not create pgvector index: {e}")
else:
    print("Info: pgvector disabled, skipping index creation")

# ── Create app FIRST ────────────────────────────────────
app = FastAPI(title="Marble AI API", version="1.0.0")

# ── CORS ────────────────────────────────────────────────
# Allow only local development origins with credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Files (AFTER app is created) ─────────────────
dataset_path = os.path.join(os.path.dirname(__file__), "..", "dataset")
app.mount("/static", StaticFiles(directory=dataset_path), name="static")

# ── Routers ──────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(cat_router.router)
app.include_router(tiles.router)
app.include_router(tiles.public_router)
app.include_router(inv_router)
app.include_router(loc_router)
app.include_router(search.router)
# Add this line alongside your other include_router definitions
app.include_router(quote.router)
app.include_router(analytics.router)

@app.on_event("startup")
def warmup_search_model():
    """
    Warm up DINO model once at startup so first search request is fast.
    """
    try:
        get_model()
        print("Info: search model warmup complete")
    except Exception as e:
        print(f"Warning: search model warmup failed: {e}")

@app.get("/")
def health_check():
    return {"status": "Marble AI API is running"}


@app.post("/update-stock")
def update_stock_endpoint(body: StockUpdate, db=Depends(get_db)):
    """Public-friendly stock update endpoint for quick deployments."""
    updated = update_stock_service(
        db, body.tile_id, body.quantity, body.unit, body.low_stock_threshold
    )
    return {
        "message": "Stock updated",
        "tile_id": updated.tile_id,
        "quantity": updated.quantity,
        "unit": updated.unit,
        "low_stock_threshold": updated.low_stock_threshold,
    }
