import os
import sys

# ── Cache fix ──────────────────────────────────────────
_CACHE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "model_cache"
)
os.makedirs(_CACHE, exist_ok=True)
os.environ["HF_HOME"]               = _CACHE
os.environ["TORCH_HOME"]            = _CACHE
os.environ["TRANSFORMERS_CACHE"]    = _CACHE
os.environ["HUGGINGFACE_HUB_CACHE"] = _CACHE

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import open_clip
import json
import numpy as np
from typing import List, Dict
from ai.preprocess import preprocess_image
from ai.embed import load_model, get_embedding

# ── Singleton Model (load once, reuse) ──────────────────
_model      = None
_preprocess = None

def get_model():
    global _model, _preprocess
    if _model is None:
        _model, _preprocess = load_model()
    return _model, _preprocess

# ── Cosine Similarity ────────────────────────────────────
def cosine_similarity(vec1: list, vec2: list) -> float:
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# ── Main Search Function ─────────────────────────────────
def search_tile(
    image_input,           # bytes or file path
    db,                    # SQLAlchemy session
    top_k: int = 5,
    min_confidence: float = 0.0,
    material_id: int = None,   # optional pre-filter
    color_family_id: int = None
) -> List[Dict]:
    """
    Returns top_k matches as list of dicts:
    {tile_id, sku, name, confidence, location, stock, image_url}
    """
    from app.models.tile import Tile
    from app.models.tile_image import TileEmbedding, TileImage
    from app.models.inventory import Inventory, WarehouseLocation

    # Step 1 — Generate embedding for query image
    model, preprocess = get_model()
    query_vector = get_embedding(model, preprocess, image_input)

    # Step 2 — Load all embeddings from DB
    query = db.query(TileEmbedding)

    # Optional category pre-filter (narrows search space)
    if material_id or color_family_id:
        query = query.join(Tile, TileEmbedding.tile_id == Tile.id)
        if material_id:
            query = query.filter(Tile.material_id == material_id)
        if color_family_id:
            query = query.filter(Tile.color_family_id == color_family_id)

    all_embeddings = query.all()

    if not all_embeddings:
        return []

    # Step 3 — Compute cosine similarity for each
    scores = []
    for record in all_embeddings:
        stored_vector = json.loads(record.embedding)
        similarity    = cosine_similarity(query_vector, stored_vector)
        scores.append((similarity, record.tile_id, record.image_id))

    # Step 4 — Sort by similarity descending
    scores.sort(key=lambda x: x[0], reverse=True)
    top_results = scores[:top_k]

    # Step 5 — Build response with full tile details
    results = []
    for confidence, tile_id, image_id in top_results:

        if confidence < min_confidence:
            continue

        tile      = db.query(Tile).filter(Tile.id == tile_id).first()
        inventory = db.query(Inventory).filter(
            Inventory.tile_id == tile_id
        ).first()
        location  = db.query(WarehouseLocation).filter(
            WarehouseLocation.tile_id == tile_id
        ).first()
        image     = db.query(TileImage).filter(
            TileImage.id == image_id
        ).first()

        results.append({
            "tile_id":    tile_id,
            "sku":        tile.sku if tile else None,
            "name":       tile.name if tile else None,
            "confidence": round(confidence * 100, 2),  # 0.94 → 94.0%
            "location": {
                "aisle": location.aisle if location else None,
                "rack":  location.rack  if location else None,
                "bin":   location.bin   if location else None,
            },
            "stock": {
                "quantity": inventory.quantity          if inventory else 0,
                "unit":     inventory.unit              if inventory else "pieces",
                "is_low":   (
                    inventory.quantity <= inventory.low_stock_threshold
                ) if inventory else False,
            },
            "image_url": image.image_url if image else None,
        })

    return results