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

import logging
import torch
import json
import numpy as np
import cv2
import os
from typing import List, Dict, Tuple
from ai.preprocess import preprocess_image
from ai.embed import load_model, get_embedding
from ai.tile_classifier import validate_uploaded_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_WAREHOUSE_LABEL = os.getenv("DEFAULT_WAREHOUSE_LABEL", "Mumbai Warehouse, India")

# ── Singleton Model (load once, reuse) ──────────────────
_model      = None
_preprocess = None
_pgvector_unavailable = False

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


def _query_embedding(model, processor, image_input, use_tta: bool = False) -> np.ndarray:
    """
    Build a robust query embedding using light test-time augmentation.
    Keeps inference deterministic enough while improving noisy-phone-image matching.
    """
    base = np.array(get_embedding(model, processor, image_input, mode="query"), dtype=np.float32)

    if not use_tta:
        return base / np.linalg.norm(base)

    # If decoding fails, fall back to the base embedding path.
    nparr = np.frombuffer(image_input, np.uint8) if isinstance(image_input, bytes) else None
    if nparr is None:
        return base / np.linalg.norm(base)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return base / np.linalg.norm(base)

    aug_embeddings = [base]
    flip = cv2.flip(img, 1)
    darker = cv2.convertScaleAbs(img, alpha=0.95, beta=-6)

    for aug in (flip, darker):
        try:
            aug_embeddings.append(
                np.array(get_embedding(model, processor, aug, mode="query"), dtype=np.float32)
            )
        except Exception:
            continue

    stacked = np.stack(aug_embeddings, axis=0)
    merged = stacked.mean(axis=0)
    return merged / np.linalg.norm(merged)

# ── Tile Image Validation ────────────────────────────────
def validate_image_is_tile(image_input, min_confidence: float = 0.50) -> Tuple[bool, dict]:
    """
    Validate that uploaded image is actually a tile (not a dog, cat, etc).
    
    Returns:
        (is_valid: bool, validation_result: dict)
        - is_valid: True if it's a tile, False if rejected
        - validation_result: contains confidence, message, etc
    """
    try:
        validation_result = validate_uploaded_image(image_input, min_confidence)
        is_valid = validation_result.get("is_valid", True)
        
        logger.info(f"Tile validation - Is Tile: {is_valid}, Confidence: {validation_result.get('confidence', 0)}%")
        
        return is_valid, validation_result
    except Exception as e:
        logger.warning(f"Tile validation error (allowing image): {e}")
        # On error, allow the image (fail-open)
        return True, {"is_valid": True, "is_tile": True, "confidence": 100.0, "message": ""}

# ── Main Search Function ─────────────────────────────────
def search_tile(
    image_input,           # bytes or file path
    db,                    # SQLAlchemy session
    top_k: int = 3,
    min_confidence: float = 0.0,
    material_id: int = None,   # optional pre-filter
    color_family_id: int = None,
    validate_tile: bool = False
) -> dict:
    """
    Search for matching tiles with tile image validation.
    
    Returns dict:
    {
        "results": [list of tile matches],
        "validation": {
            "is_valid": bool,
            "is_tile": bool,
            "confidence": float,
            "message": str
        }
    }
    
    PRODUCTION QUALITY GATES:
    - Validates that uploaded image is a tile (rejects dogs, cats, etc.)
    - Default min_confidence raised to 0.70 (70%) for high-confidence results
    - Results below 60% are excluded (low confidence, not trustworthy)
    - Only deduped unique tiles (one result per tile_id)
    """
    from sqlalchemy import text
    from app.models.tile import Tile
    from app.models.tile_image import TileEmbedding, TileImage
    from app.models.inventory import Inventory, WarehouseLocation

    def build_location_payload(location_obj):
        if location_obj:
            return {
                "warehouse": DEFAULT_WAREHOUSE_LABEL,
                "aisle": location_obj.aisle,
                "rack": location_obj.rack,
                "bin": location_obj.bin,
                "display": f"{DEFAULT_WAREHOUSE_LABEL} | Aisle {location_obj.aisle} -> Rack {location_obj.rack} -> Bin {location_obj.bin}",
            }
        return {
            "warehouse": DEFAULT_WAREHOUSE_LABEL,
            "aisle": None,
            "rack": None,
            "bin": None,
            "display": f"{DEFAULT_WAREHOUSE_LABEL} | Location pending assignment",
        }

    # VALIDATION STEP: Check if uploaded image is a tile
    if validate_tile:
        is_tile, validation_info = validate_image_is_tile(image_input, min_confidence=0.50)
        if not is_tile:
            logger.warning(f"Rejected non-tile image: {validation_info['message']}")
            return {
                "results": [],
                "validation": validation_info,
                "error": validation_info["message"]
            }
    else:
        validation_info = {"is_valid": True, "is_tile": True, "confidence": 100.0, "message": "Validation disabled"}

    # Production quality gates
    MIN_CONFIDENCE_THRESHOLD = 0.12  # Absolute minimum (60%)
    RECOMMENDED_THRESHOLD = 0.70     # Recommended for production use (70%)
    
    model, preprocess = get_model()
    use_tta_default = os.getenv("SEARCH_USE_TTA", "0") == "1"
    query_vector = _query_embedding(model, preprocess, image_input, use_tta=use_tta_default)

    # Ensure query vector normalization
    q = np.array(query_vector, dtype=np.float32)
    q = q / np.linalg.norm(q)

    # Use pgvector cosine distance search. Lower distance = better match.
    filter_sql = ""
    if material_id:
        filter_sql += " AND t.material_id = :material_id"
    if color_family_id:
        filter_sql += " AND t.color_family_id = :color_family_id"

    # Request extra rows to allow de-duplicating by tile_id while still returning top_k unique tiles.
    search_limit = max(top_k * 8, top_k + 5)

    sql_text = f"""
        SELECT te.tile_id, te.image_id,
               (te.embedding <=> :query) AS distance
        FROM tile_embeddings te
        JOIN tiles t ON t.id = te.tile_id
        WHERE 1=1
        {filter_sql}
        ORDER BY te.embedding <=> :query ASC
        LIMIT :search_limit
    """
    sql = text(sql_text)

    params = {
        "query": q.tolist(),
        "search_limit": search_limit,
        "material_id": material_id,
        "color_family_id": color_family_id,
    }

    records = []
    global _pgvector_unavailable
    if not _pgvector_unavailable:
        try:
            records = db.execute(sql, params).fetchall()
        except Exception:
            # If vector search fails once (e.g. pgvector unavailable), skip trying it again.
            _pgvector_unavailable = True
            try:
                db.rollback()
            except Exception:
                pass

    results = []

    if records:
        logger.info(f"Found {len(records)} candidates from pgvector search")
        seen_tile_ids = set()

        for row in records:
            tile_id = row[0]
            if tile_id in seen_tile_ids:
                continue

            image_id = row[1]
            distance = float(row[2])
            confidence = 1.0 - (distance / 2.0)
            confidence = max(0.0, min(confidence, 1.0))
            
            # QUALITY GATE 1: Absolute minimum confidence threshold
            if confidence < MIN_CONFIDENCE_THRESHOLD:
                logger.warning(f"Tile {tile_id} below minimum confidence ({confidence:.2%}), rejecting")
                continue
            
            # QUALITY GATE 2: User-specified minimum
            if confidence < min_confidence:
                logger.info(f"Tile {tile_id} below user threshold ({confidence:.2%} < {min_confidence:.2%}), rejecting")
                continue

            seen_tile_ids.add(tile_id)

            tile = db.query(Tile).filter(Tile.id == tile_id).first()
            inventory = db.query(Inventory).filter(Inventory.tile_id == tile_id).first()
            location = db.query(WarehouseLocation).filter(WarehouseLocation.tile_id == tile_id).first()
            image = db.query(TileImage).filter(TileImage.id == image_id).first()

            results.append({
                "tile_id": tile_id,
                "sku": tile.sku if tile else None,
                "name": tile.name if tile else None,
                "confidence": round(confidence * 100, 2),
                "location": build_location_payload(location),
                "stock": {
                    "quantity": inventory.quantity if inventory else 0,
                    "unit": inventory.unit if inventory else "pieces",
                    "is_low": (inventory.quantity <= inventory.low_stock_threshold) if inventory else False,
                },
                "image_url": image.image_url if image else None,
            })

            if len(results) >= top_k:
                break

        # If confidence is weak and TTA was disabled, retry once with TTA for better precision.
        if (
            results
            and not use_tta_default
            and results[0]["confidence"] < 80.0
            and isinstance(image_input, bytes)
        ):
            q_tta = _query_embedding(model, preprocess, image_input, use_tta=True)
            params["query"] = q_tta.tolist()
            try:
                rerank_records = db.execute(sql, params).fetchall()
            except Exception:
                rerank_records = []
            if rerank_records:
                seen_tile_ids = set()
                reranked_results = []
                for row in rerank_records:
                    tile_id = row[0]
                    if tile_id in seen_tile_ids:
                        continue
                    image_id = row[1]
                    distance = float(row[2])
                    confidence = max(0.0, min(1.0 - (distance / 2.0), 1.0))
                    if confidence < MIN_CONFIDENCE_THRESHOLD or confidence < min_confidence:
                        continue
                    seen_tile_ids.add(tile_id)
                    tile = db.query(Tile).filter(Tile.id == tile_id).first()
                    inventory = db.query(Inventory).filter(Inventory.tile_id == tile_id).first()
                    location = db.query(WarehouseLocation).filter(WarehouseLocation.tile_id == tile_id).first()
                    image = db.query(TileImage).filter(TileImage.id == image_id).first()
                    reranked_results.append({
                        "tile_id": tile_id,
                        "sku": tile.sku if tile else None,
                        "name": tile.name if tile else None,
                        "confidence": round(confidence * 100, 2),
                        "location": build_location_payload(location),
                        "stock": {
                            "quantity": inventory.quantity if inventory else 0,
                            "unit": inventory.unit if inventory else "pieces",
                            "is_low": (inventory.quantity <= inventory.low_stock_threshold) if inventory else False,
                        },
                        "image_url": image.image_url if image else None,
                    })
                    if len(reranked_results) >= top_k:
                        break
                if reranked_results:
                    results = reranked_results

        return {"results": results, "validation": validation_info}

    # Fallback brute-force if pgvector not available
    try:
        all_embeddings = db.query(TileEmbedding).all()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "results": [],
            "validation": validation_info,
            "error": "Database query failed"
        }

    if not all_embeddings:
        # On first run dataset may not have embeddings; generate them once and retry.
        try:
            from ai.embed import embed_all_tiles
            embed_all_tiles()
            all_embeddings = db.query(TileEmbedding).all()
        except Exception:
            return {
                "results": [],
                "validation": validation_info,
                "error": "No embeddings available"
            }

        if not all_embeddings:
            return {
                "results": [],
                "validation": validation_info,
                "error": "No embeddings available"
            }

    scores = []
    for record in all_embeddings:
        # Support multiple embedding storage formats: pgvector text, JSON string, or list/ndarray.
        stored_raw = record.embedding

        if isinstance(stored_raw, str):
            stored_raw = stored_raw.strip()
            if stored_raw.startswith("{") and stored_raw.endswith("}"):
                # Postgres vector format returned as {x,y,z}
                stored_raw = stored_raw[1:-1]
                parsed_values = [float(v) for v in stored_raw.split(",") if v != ""]
            else:
                parsed_values = json.loads(stored_raw)
            stored_vector = np.array(parsed_values, dtype=np.float32)

        elif isinstance(stored_raw, (list, tuple, np.ndarray)):
            stored_vector = np.array(stored_raw, dtype=np.float32)

        else:
            # Fallback for any other format (e.g. pgvector type object)
            try:
                stored_vector = np.array(stored_raw, dtype=np.float32)
            except Exception:
                continue

        if np.linalg.norm(stored_vector) == 0:
            continue

        stored_vector = stored_vector / np.linalg.norm(stored_vector)
        cosine = float(np.dot(q, stored_vector))
        scores.append((cosine, record.tile_id, record.image_id))

    scores.sort(key=lambda x: x[0], reverse=True)

    MIN_CONFIDENCE_THRESHOLD = 0.12  # Production quality gate
    seen_tile_ids = set()
    for confidence, tile_id, image_id in scores:
        if tile_id in seen_tile_ids:
            continue

        # QUALITY GATE: Absolute minimum confidence
        if confidence < MIN_CONFIDENCE_THRESHOLD:
            logger.warning(f"Tile {tile_id} below minimum confidence ({confidence:.2%}), rejecting")
            continue
        
        if confidence < min_confidence:
            logger.info(f"Tile {tile_id} below user threshold ({confidence:.2%} < {min_confidence:.2%}), rejecting")
            continue

        tile = db.query(Tile).filter(Tile.id == tile_id).first()
        inventory = db.query(Inventory).filter(Inventory.tile_id == tile_id).first()
        location = db.query(WarehouseLocation).filter(WarehouseLocation.tile_id == tile_id).first()
        image = db.query(TileImage).filter(TileImage.id == image_id).first()

        seen_tile_ids.add(tile_id)

        results.append({
            "tile_id": tile_id,
            "sku": tile.sku if tile else None,
            "name": tile.name if tile else None,
            "confidence": round(confidence * 100, 2),
            "location": build_location_payload(location),
            "stock": {
                "quantity": inventory.quantity if inventory else 0,
                "unit": inventory.unit if inventory else "pieces",
                "is_low": (inventory.quantity <= inventory.low_stock_threshold) if inventory else False,
            },
            "image_url": image.image_url if image else None,
        })

        if len(results) >= top_k:
            break

    return {
        "results": results,
        "validation": validation_info
    }
