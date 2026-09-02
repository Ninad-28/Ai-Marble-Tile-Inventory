from sqlalchemy.orm import Session
from app.models.tile import Tile
from app.models.inventory import Inventory
from ai.search import search_tile


def run_visual_search(db: Session, image_bytes: bytes, top_k: int = 5,
                      min_confidence: float = 0.0, material_id=None,
                      color_family_id=None):
    return search_tile(
        image_input=image_bytes,
        db=db,
        top_k=top_k,
        min_confidence=min_confidence,
        material_id=material_id,
        color_family_id=color_family_id,
    )
