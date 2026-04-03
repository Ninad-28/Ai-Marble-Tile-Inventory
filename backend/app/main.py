from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine

from app.models import admin, categories, tile, tile_image, inventory, search_log

from app.routers import auth
from app.routers import categories as cat_router
from app.routers import tiles
from app.routers.inventory import router as inv_router
from app.routers.inventory import loc_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Marble AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cat_router.router)
app.include_router(tiles.router)
app.include_router(inv_router)
app.include_router(loc_router)

@app.get("/")
def health_check():
    return {"status": "Marble AI API is running"}