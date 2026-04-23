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
from transformers import AutoImageProcessor, Dinov2Model
import json
import numpy as np
from tqdm import tqdm
from ai.preprocess import preprocess_image
from app.database import SessionLocal
from app.models.admin import Admin
from app.models.tile_image import use_pgvector
from app.models.categories import (
    Material, Style, Finish,
    SizeFormat, Application, ColorFamily, Origin
)
from app.models.tile import Tile
from app.models.tile_image import TileImage, TileEmbedding
from app.models.inventory import Inventory, WarehouseLocation
from app.models.search_log import SearchLog

DATASET_PATH    = os.path.join(os.path.dirname(__file__), "..", "dataset", "train")
MODEL_VERSION   = "facebook/dinov2-base"
DEVICE          = "cuda" if torch.cuda.is_available() else "cpu"


def resolve_model_version(model_name: str = MODEL_VERSION) -> str:
    """Build a stable model version label (base model + fine-tune checkpoint tag)."""
    checkpoint_name = os.getenv("EMBEDDING_MODEL_CHECKPOINT", "finetune_dinov2_best.pt")
    checkpoint_path = os.path.join(_CACHE, checkpoint_name)
    if os.path.exists(checkpoint_path):
        return f"{model_name}+{os.path.splitext(checkpoint_name)[0]}"
    return model_name

# ── Load Model ──────────────────────────────────────────
def load_model():
    model_path = os.getenv("EMBEDDING_MODEL_PATH")
    model_name = os.getenv("EMBEDDING_MODEL_NAME", MODEL_VERSION)

    # First try to load fine-tuned model
    finetune_checkpoint = os.path.join(_CACHE, "finetune_dinov2_best.pt")
    
    if os.path.exists(finetune_checkpoint):
        print(f"Loading fine-tuned DINO v2 model from {finetune_checkpoint}...")
        model = Dinov2Model.from_pretrained(model_name)
        model.load_state_dict(torch.load(finetune_checkpoint, map_location=DEVICE))
        model.to(DEVICE)
        model.eval()
        processor = AutoImageProcessor.from_pretrained(model_name)
    else:
        print(f"Loading pre-trained DINO v2 model {model_name}...")
        model = Dinov2Model.from_pretrained(model_name)
        model.to(DEVICE)
        model.eval()
        processor = AutoImageProcessor.from_pretrained(model_name)
    
    print(f"[OK] Model loaded on {DEVICE} (version={model_name})")
    return model, processor

# ── Generate Single Embedding ───────────────────────────
def get_embedding(model, processor, image_input, mode: str = "db") -> list:
    """
    image_input: file path (str) or raw bytes
    Returns: list of floats (768 dimensions for DINO v2 base)
    """
    pil_image = preprocess_image(image_input, mode=mode)
    inputs = processor(images=pil_image, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = model(**inputs)
        # Pool the last hidden state
        features = outputs.last_hidden_state.mean(dim=1)
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
            print(f"\nWARNING: SKU {sku} not found in DB, skipping")
            skipped += 1
            continue

        # Get all image paths in the folder
        images = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        
        if not images:
            print(f"\n❌ No image found for {folder}")
            failed += 1
            continue

        try:
            for img_name in images:
                img_path = os.path.join(folder_path, img_name)
                
                # Check if this specific image was already embedded
                image_url = f"/static/train/{folder}/{img_name}"
                existing_image = db.query(TileImage).filter(TileImage.image_url == image_url).first()
                
                if existing_image:
                    existing_emb = db.query(TileEmbedding).filter(TileEmbedding.image_id == existing_image.id).first()
                    if existing_emb:
                        continue # Already embedded
                else:
                    # Save image record
                    is_primary = img_name == f"img_{tile_number}_orig.jpg" or img_name == f"img_{tile_number}.jpg"
                    existing_image = TileImage(
                        tile_id    = tile.id,
                        image_url  = image_url,
                        is_primary = is_primary
                    )
                    db.add(existing_image)
                    db.flush()

                # Generate embedding
                embedding_vector = get_embedding(model, preprocess, img_path, mode="db")

                # Serialize embedding based on PGVector configuration
                embedding_payload = embedding_vector
                if not use_pgvector:
                    embedding_payload = json.dumps(embedding_vector)

                # Save embedding record
                embedding_record = TileEmbedding(
                    tile_id       = tile.id,
                    image_id      = existing_image.id,
                    embedding     = embedding_payload,
                    model_version = os.getenv("EMBEDDING_MODEL_VERSION", resolve_model_version(model_name=os.getenv("EMBEDDING_MODEL_NAME", MODEL_VERSION)))
                )
                db.add(embedding_record)
            
            db.commit()
            success += 1

        except Exception as e:
            print(f"\n❌ Failed {folder}: {e}")
            db.rollback()
            failed += 1

    db.close()
    print(f"\nDone: Embedded {success} tiles")
    print(f"⏭️  Skipped:  {skipped} tiles")
    print(f"❌ Failed:   {failed} tiles")
    print(f"\n🎉 All tiles ready for visual search!")

if __name__ == "__main__":
    embed_all_tiles()