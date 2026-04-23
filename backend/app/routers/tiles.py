import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.tile import Tile
from app.models.inventory import Inventory
from app.models.tile_image import TileImage, TileEmbedding, use_pgvector
from app.schemas.tile import TileCreate, TileUpdate, TileOut
from ai.embed import load_model, get_embedding, resolve_model_version, MODEL_VERSION
import json

router = APIRouter(prefix="/api/tiles", tags=["Tiles"])
public_router = APIRouter(prefix="/tiles", tags=["Public Tiles"])

_embed_model = None
_embed_processor = None


def _get_embedder():
    global _embed_model, _embed_processor
    if _embed_model is None:
        _embed_model, _embed_processor = load_model()
    return _embed_model, _embed_processor

# ── Add New Tile ─────────────────────────────────────────
@router.post("/", response_model=TileOut)
def create_tile(body: TileCreate, db: Session = Depends(get_db),
                _=Depends(get_current_admin)):
    # Check duplicate SKU
    if db.query(Tile).filter(Tile.sku == body.sku).first():
        raise HTTPException(status_code=400, detail="SKU already exists")

    tile = Tile(**body.model_dump())
    db.add(tile)
    db.flush()  # get tile.id before commit

    # Auto-create inventory record with 0 stock
    inventory = Inventory(tile_id=tile.id, quantity=0)
    db.add(inventory)
    db.commit()
    db.refresh(tile)
    return tile


@router.post("/with-image", response_model=TileOut)
async def create_tile_with_image(
    sku: str = Form(...),
    name: str = Form(...),
    material_id: int = Form(...),
    description: Optional[str] = Form(None),
    style_id: Optional[int] = Form(None),
    finish_id: Optional[int] = Form(None),
    size_format_id: Optional[int] = Form(None),
    application_id: Optional[int] = Form(None),
    color_family_id: Optional[int] = Form(None),
    origin_id: Optional[int] = Form(None),
    width_cm: Optional[float] = Form(None),
    height_cm: Optional[float] = Form(None),
    thickness_cm: Optional[float] = Form(None),
    price_per_sqm: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    if db.query(Tile).filter(Tile.sku == sku).first():
        raise HTTPException(status_code=400, detail="SKU already exists")

    tile = Tile(
        sku=sku,
        name=name,
        description=description,
        material_id=material_id,
        style_id=style_id,
        finish_id=finish_id,
        size_format_id=size_format_id,
        application_id=application_id,
        color_family_id=color_family_id,
        origin_id=origin_id,
        width_cm=width_cm,
        height_cm=height_cm,
        thickness_cm=thickness_cm,
        price_per_sqm=price_per_sqm,
    )
    db.add(tile)
    db.flush()

    inventory = Inventory(tile_id=tile.id, quantity=0)
    db.add(inventory)

    if image is not None:
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded image is empty")

        ext = os.path.splitext(image.filename or "")[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg"

        uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "uploads", "tiles")
        os.makedirs(uploads_dir, exist_ok=True)
        safe_sku = "".join(ch for ch in sku if ch.isalnum() or ch in {"-", "_"}).strip() or f"tile_{tile.id}"
        file_name = f"{safe_sku}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
        file_path = os.path.join(uploads_dir, file_name)

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        image_url = f"/static/uploads/tiles/{file_name}"
        tile_image = TileImage(tile_id=tile.id, image_url=image_url, is_primary=True)
        db.add(tile_image)
        db.flush()

        try:
            model, processor = _get_embedder()
            embedding_vector = get_embedding(model, processor, image_bytes, mode="db")
            embedding_payload = embedding_vector if use_pgvector else json.dumps(embedding_vector)
            db.add(
                TileEmbedding(
                    tile_id=tile.id,
                    image_id=tile_image.id,
                    embedding=embedding_payload,
                    model_version=os.getenv(
                        "EMBEDDING_MODEL_VERSION",
                        resolve_model_version(os.getenv("EMBEDDING_MODEL_NAME", MODEL_VERSION)),
                    ),
                )
            )
        except Exception:
            # Keep tile creation successful even if embedding generation fails.
            pass

    db.commit()
    db.refresh(tile)
    return tile

# ── List All Tiles (with filters) ───────────────────────
@router.get("/", response_model=list[TileOut])
def list_tiles(
    material_id: Optional[int] = Query(None),
    finish_id: Optional[int] = Query(None),
    color_family_id: Optional[int] = Query(None),
    application_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(True),
    search: Optional[str] = Query(None),   # search by name or SKU
    skip: int = Query(0),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin)
):
    query = db.query(Tile)

    if is_active is not None:
        query = query.filter(Tile.is_active == is_active)
    if material_id:
        query = query.filter(Tile.material_id == material_id)
    if finish_id:
        query = query.filter(Tile.finish_id == finish_id)
    if color_family_id:
        query = query.filter(Tile.color_family_id == color_family_id)
    if application_id:
        query = query.filter(Tile.application_id == application_id)
    if search:
        query = query.filter(
            Tile.name.ilike(f"%{search}%") | Tile.sku.ilike(f"%{search}%")
        )

    return query.offset(skip).limit(limit).all()

# ── Get Single Tile ──────────────────────────────────────
@router.get("/{tile_id}", response_model=TileOut)
def get_tile(tile_id: int, db: Session = Depends(get_db),
             _=Depends(get_current_admin)):
    tile = db.query(Tile).filter(Tile.id == tile_id).first()
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")
    return tile

# ── Update Tile ──────────────────────────────────────────
@router.put("/{tile_id}", response_model=TileOut)
def update_tile(tile_id: int, body: TileUpdate,
                db: Session = Depends(get_db),
                _=Depends(get_current_admin)):
    tile = db.query(Tile).filter(Tile.id == tile_id).first()
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tile, field, value)

    db.commit()
    db.refresh(tile)
    return tile

# ── Deactivate Tile (soft delete) ────────────────────────
@router.delete("/{tile_id}")
def deactivate_tile(tile_id: int, db: Session = Depends(get_db),
                    _=Depends(get_current_admin)):
    tile = db.query(Tile).filter(Tile.id == tile_id).first()
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")

    tile.is_active = False
    db.commit()
    return {"message": f"Tile {tile.sku} deactivated"}


# ── Public endpoints (no auth required) ─────────────────
@public_router.get("/", response_model=list[TileOut])
def list_tiles_public(skip: int = 0,
                      limit: int = 100,
                      db: Session = Depends(get_db)):
    tiles = db.query(Tile).filter(Tile.is_active == True).offset(skip).limit(limit).all()
    return tiles


@public_router.get("/{tile_id}", response_model=TileOut)
def get_tile_public(tile_id: int, db: Session = Depends(get_db)):
    tile = db.query(Tile).filter(Tile.id == tile_id, Tile.is_active == True).first()
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")
    return tile