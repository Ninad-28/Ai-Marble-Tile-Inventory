from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.tile import Tile
from app.models.inventory import Inventory
from app.schemas.tile import TileCreate, TileUpdate, TileOut

router = APIRouter(prefix="/api/tiles", tags=["Tiles"])

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