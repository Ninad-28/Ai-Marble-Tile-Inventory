from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.inventory import Inventory, WarehouseLocation
from app.models.tile import Tile
from app.schemas.inventory import (
    InventoryUpdate, InventoryOut,
    LocationCreate, LocationUpdate, LocationOut
)

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])
loc_router = APIRouter(prefix="/api/locations", tags=["Warehouse"])

# ── Get All Inventory ────────────────────────────────────
@router.get("/", response_model=list[InventoryOut])
def get_all_inventory(db: Session = Depends(get_db),
                      _=Depends(get_current_admin)):
    return db.query(Inventory).all()

# ── Get Inventory for One Tile ───────────────────────────
@router.get("/{tile_id}", response_model=InventoryOut)
def get_inventory(tile_id: int, db: Session = Depends(get_db),
                  _=Depends(get_current_admin)):
    inv = db.query(Inventory).filter(Inventory.tile_id == tile_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inv

# ── Update Stock ─────────────────────────────────────────
@router.put("/{tile_id}", response_model=InventoryOut)
def update_stock(tile_id: int, body: InventoryUpdate,
                 db: Session = Depends(get_db),
                 _=Depends(get_current_admin)):
    inv = db.query(Inventory).filter(Inventory.tile_id == tile_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory not found")

    inv.quantity = body.quantity
    inv.unit = body.unit
    inv.low_stock_threshold = body.low_stock_threshold
    db.commit()
    db.refresh(inv)
    return inv

# ── Low Stock Alert ──────────────────────────────────────
@router.get("/alerts/low-stock")
def low_stock(db: Session = Depends(get_db),
              _=Depends(get_current_admin)):
    items = db.query(Inventory).filter(
        Inventory.quantity <= Inventory.low_stock_threshold
    ).all()
    return {
        "count": len(items),
        "items": [{"tile_id": i.tile_id,
                   "quantity": i.quantity,
                   "threshold": i.low_stock_threshold} for i in items]
    }

# ── Warehouse Locations ──────────────────────────────────
@loc_router.post("/", response_model=LocationOut)
def create_location(body: LocationCreate, db: Session = Depends(get_db),
                    _=Depends(get_current_admin)):
    existing = db.query(WarehouseLocation).filter(
        WarehouseLocation.tile_id == body.tile_id
    ).first()
    if existing:
        raise HTTPException(status_code=400,
                            detail="Location already assigned for this tile")

    loc = WarehouseLocation(**body.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc

@loc_router.get("/", response_model=list[LocationOut])
def get_locations(db: Session = Depends(get_db),
                  _=Depends(get_current_admin)):
    return db.query(WarehouseLocation).all()

@loc_router.put("/{tile_id}", response_model=LocationOut)
def update_location(tile_id: int, body: LocationUpdate,
                    db: Session = Depends(get_db),
                    _=Depends(get_current_admin)):
    loc = db.query(WarehouseLocation).filter(
        WarehouseLocation.tile_id == tile_id
    ).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(loc, field, value)

    db.commit()
    db.refresh(loc)
    return loc