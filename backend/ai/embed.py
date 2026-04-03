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
from tqdm import tqdm
from ai.preprocess import preprocess_image
from app.database import SessionLocal
from app.models.admin import Admin
from app.models.categories import (
    Material, Style, Finish,
    SizeFormat, Application, ColorFamily, Origin
)
from app.models.tile import Tile
from app.models.tile_image import TileImage, TileEmbedding
from app.models.inventory import Inventory, WarehouseLocation
from app.models.search_log import SearchLog

DATASET_PATH    = os.path.join(os.path.dirname(__file__), "..", "dataset", "train")
MODEL_VERSION   = "clip-base-laion2b"
DEVICE          = "cuda" if torch.cuda.is_available() else "cpu"

# ── Load Model ──────────────────────────────────────────
def load_model():
    print("Loading base CLIP model...")
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k"
    )
    model = model.to(DEVICE)
    model.eval()
    print(f"✅ Model loaded on {DEVICE}")
    return model, preprocess

# ── Generate Single Embedding ───────────────────────────
def get_embedding(model, preprocess, image_input) -> list:
    """
    image_input: file path (str) or raw bytes
    Returns: list of floats (512 dimensions)
    """
    pil_image = preprocess_image(image_input)
    tensor = preprocess(pil_image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        features = model.encode_image(tensor)
        # Normalize to unit vector
        features = features / features.norm(dim=-1, keepdim=True)

    return features.cpu().numpy()[0].tolist()

# ── Find Original Image for a Tile Folder ───────────────
def get_original_image(tile_folder: str, tile_number: str) -> str:
    """
    Returns path to original image.
    Prefers img_X_orig.jpg, falls back to img_X.jpg
    """
    orig_path = os.path.join(tile_folder, f"img_{tile_number}_orig.jpg")
    base_path = os.path.join(tile_folder, f"img_{tile_number}.jpg")

    if os.path.exists(orig_path):
        return orig_path
    elif os.path.exists(base_path):
        return base_path
    else:
        # Fallback: take first image in folder
        images = [
            f for f in os.listdir(tile_folder)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if images:
            return os.path.join(tile_folder, sorted(images)[0])
    return None

# ── Batch Embed All Tiles ───────────────────────────────
def embed_all_tiles():
    db = SessionLocal()
    model, preprocess = load_model()

    # Get all tile folders
    tile_folders = sorted([
        f for f in os.listdir(DATASET_PATH)
        if os.path.isdir(os.path.join(DATASET_PATH, f))
        and f.startswith("tile_")
    ])

    print(f"\nEmbedding {len(tile_folders)} tiles...\n")

    success = 0
    skipped = 0
    failed  = 0

    for folder in tqdm(tile_folders, desc="Embedding tiles"):
        tile_number = folder.split("_")[1]
        sku         = f"MRB-{tile_number.zfill(3)}"
        folder_path = os.path.join(DATASET_PATH, folder)

        # Find tile in DB
        tile = db.query(Tile).filter(Tile.sku == sku).first()
        if not tile:
            print(f"\n⚠️  SKU {sku} not found in DB, skipping")
            skipped += 1
            continue

        # Skip if already embedded
        existing = db.query(TileEmbedding).filter(
            TileEmbedding.tile_id == tile.id
        ).first()
        if existing:
            skipped += 1
            continue

        # Get original image path
        img_path = get_original_image(folder_path, tile_number)
        if not img_path:
            print(f"\n❌ No image found for {folder}")
            failed += 1
            continue

        try:
            # Generate embedding
            embedding_vector = get_embedding(model, preprocess, img_path)

            # Save image record
            image_url = f"/static/train/{folder}/{os.path.basename(img_path)}"
            tile_image = TileImage(
                tile_id    = tile.id,
                image_url  = image_url,
                is_primary = True
            )
            db.add(tile_image)
            db.flush()

            # Save embedding record
            embedding_record = TileEmbedding(
                tile_id       = tile.id,
                image_id      = tile_image.id,
                embedding     = json.dumps(embedding_vector),
                model_version = MODEL_VERSION
            )
            db.add(embedding_record)
            db.commit()
            success += 1

        except Exception as e:
            print(f"\n❌ Failed {folder}: {e}")
            db.rollback()
            failed += 1

    db.close()
    print(f"\n✅ Embedded:  {success} tiles")
    print(f"⏭️  Skipped:  {skipped} tiles")
    print(f"❌ Failed:   {failed} tiles")
    print(f"\n🎉 All tiles ready for visual search!")

if __name__ == "__main__":
    embed_all_tiles()