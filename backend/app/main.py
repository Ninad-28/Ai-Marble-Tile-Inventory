import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine

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

# Create tables
Base.metadata.create_all(bind=engine)

# ── Create app FIRST ────────────────────────────────────
app = FastAPI(title="Marble AI API", version="1.0.0")

# ── CORS ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
app.include_router(inv_router)
app.include_router(loc_router)
app.include_router(search.router)

@app.get("/")
def health_check():
    return {"status": "Marble AI API is running"}