from sqlalchemy.orm import Session
from app.models.inventory import Inventory


def update_stock(db: Session, tile_id: int, quantity: int, unit: str = "pieces",
                 low_stock_threshold: int = 10):
    inv = db.query(Inventory).filter(Inventory.tile_id == tile_id).first()
    if not inv:
        raise ValueError("Inventory not found")

    inv.quantity = quantity
    inv.unit = unit
    inv.low_stock_threshold = low_stock_threshold
    db.commit()
    db.refresh(inv)
    return inv
