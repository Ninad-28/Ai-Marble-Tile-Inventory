"""
Regenerate all tile embeddings with DINO v2 model.
This script clears old embeddings and regenerates them with the new model.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ── Cache fix ──────────────────────────────────────────
_CACHE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "model_cache"
)
os.makedirs(_CACHE, exist_ok=True)
os.environ["HF_HOME"]               = _CACHE
os.environ["TORCH_HOME"]            = _CACHE
os.environ["TRANSFORMERS_CACHE"]    = _CACHE
os.environ["HUGGINGFACE_HUB_CACHE"] = _CACHE

# ── MUST import all models so SQLAlchemy registry is complete ──
from app.database import SessionLocal, engine, Base
from app.models.admin import Admin
from app.models.categories import (
    Material, Style, Finish,
    SizeFormat, Application, ColorFamily, Origin
)
from app.models.tile import Tile
from app.models.tile_image import TileImage, TileEmbedding
from app.models.inventory import Inventory, WarehouseLocation
from app.models.search_log import SearchLog

# Ensure pgvector extension exists
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as e:
        print(f"WARNING: pgvector extension not available: {e}")

Base.metadata.create_all(bind=engine)

# ── Import AI modules ──────────────────────────────────
import torch
from ai.embed import load_model, get_embedding, resolve_model_version, MODEL_VERSION
from tqdm import tqdm

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset", "train")

def regenerate_embeddings():
    """Load DINO v2, clear old embeddings, regenerate all"""
    max_images_per_tile = int(os.getenv("REGENERATE_MAX_IMAGES_PER_TILE", "1"))
    primary_only = os.getenv("REGENERATE_PRIMARY_ONLY", "1") == "1"
    
    print("\n" + "="*60)
    print("REGENERATING TILE EMBEDDINGS WITH DINO v2")
    print("="*60)
    
    # Load model
    model, processor = load_model()
    model_version = os.getenv("EMBEDDING_MODEL_VERSION", resolve_model_version(os.getenv("EMBEDDING_MODEL_NAME", MODEL_VERSION)))
    
    db = SessionLocal()
    
    try:
        # Clear all old embeddings
        print("\nClearing old embeddings...")
        db.query(TileEmbedding).delete()
        db.commit()
        print("[OK] Old embeddings cleared")
        
        # Get all tiles with images
        print("\nFetching tiles with images...")
        tiles_with_images = db.query(Tile).join(TileImage).all()
        print(f"[OK] Found {len(tiles_with_images)} tiles with images")
        
        if not tiles_with_images:
            print("WARNING: No tiles with images found!")
            return
        
        # Process each tile
        processed = 0
        errors = 0
        
        for tile in tqdm(tiles_with_images, desc="Generating embeddings"):
            images_query = db.query(TileImage).filter(TileImage.tile_id == tile.id)
            if primary_only:
                images_query = images_query.order_by(TileImage.is_primary.desc(), TileImage.id.asc())
            images = images_query.all()
            if max_images_per_tile > 0:
                images = images[:max_images_per_tile]
            
            for img in images:
                try:
                    # Convert image_url to file path
                    # image_url is like "/static/train/tile_5/img_5.jpg"
                    # We need to map it to DATASET_PATH/tile_5/img_5.jpg
                    url_parts = img.image_url.split("/")
                    # Find "train" index and get everything after it
                    if "train" in url_parts:
                        train_idx = url_parts.index("train")
                        relative_path = os.path.join(*url_parts[train_idx+1:])
                    else:
                        relative_path = img.image_url.lstrip("/")
                    
                    file_path = os.path.join(DATASET_PATH, relative_path)
                    
                    if not os.path.exists(file_path):
                        raise FileNotFoundError(f"Image file not found: {file_path}")
                    
                    # Get embedding from model
                    embedding = get_embedding(model, processor, file_path, mode="db")
                    
                    # Store in database
                    tile_emb = TileEmbedding(
                        tile_id=tile.id,
                        image_id=img.id,
                        embedding=embedding,
                        model_version=model_version
                    )
                    db.add(tile_emb)
                    processed += 1
                    
                except Exception as e:
                    print(f"\nERROR processing {img.image_url}: {e}")
                    errors += 1
        
        db.commit()
        print(f"\n" + "="*60)
        print(f"EMBEDDING REGENERATION COMPLETE")
        print(f"  Processed: {processed}")
        print(f"  Errors: {errors}")
        print(f"="*60)
        
    finally:
        db.close()

if __name__ == "__main__":
    regenerate_embeddings()
