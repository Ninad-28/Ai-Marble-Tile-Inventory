"""
Fine-tune DINOv2 on marble tile dataset using Triplet Margin Loss.

Key improvements:
1. Uses ALL pre-augmented images per tile folder (bright, dim, flip, rot, etc.)
2. Triplet loss (anchor, positive, negative) directly optimises cosine similarity
3. No projection head – backbone embeddings are exactly what search.py uses
4. Gradients flow through ALL branches (anchor, positive, negative)
5. Freezes early transformer layers to prevent overfitting on small dataset
6. Cosine annealing LR schedule for smooth convergence
"""

import os
import sys
import random
import torch
import torch.nn as nn
import numpy as np
from PIL import Image
from transformers import AutoImageProcessor, Dinov2Model
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

# ── Cache setup ─────────────────────────────────────────
_CACHE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_cache"
)
os.makedirs(_CACHE, exist_ok=True)
os.environ["HF_HOME"] = _CACHE
os.environ["TORCH_HOME"] = _CACHE
os.environ["TRANSFORMERS_CACHE"] = _CACHE

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Hyperparameters ─────────────────────────────────────
DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "dataset", "train")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 8
LEARNING_RATE = 2e-5
EPOCHS = 8
MODEL_NAME = "facebook/dinov2-base"
EMBEDDING_DIM = 768
TRIPLET_MARGIN = 0.3
FREEZE_LAYERS = 8  # Keep more capacity trainable for fine-grained texture learning


# ── Dataset ─────────────────────────────────────────────
class TileTripletDataset(Dataset):
    """
    Loads ALL images from each tile folder in the dataset.
    Returns (anchor, positive, negative) triplets where:
      - anchor:   one image from tile X
      - positive: a DIFFERENT image from the SAME tile X
      - negative: a random image from a DIFFERENT tile Y
    """

    def __init__(self, base_path, processor):
        self.processor = processor
        self.tile_images = {}   # tile_id -> [list of image paths]
        self.samples = []       # flat list of (image_path, tile_id)
        self.tile_ids = []

        tile_folders = sorted([
            f for f in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, f))
            and f.startswith("tile_")
        ])

        for folder in tile_folders:
            folder_path = os.path.join(base_path, folder)
            tile_id = folder  # e.g. "tile_10"

            images = sorted([
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ])

            # Need at least 2 images for anchor + positive
            if len(images) >= 2:
                self.tile_images[tile_id] = images
                # Use all available images as anchors so the model learns
                # invariance across lighting, angle and augmentations.
                for image_path in images:
                    self.samples.append((image_path, tile_id))

        self.tile_ids = list(self.tile_images.keys())
        print(f"Loaded {len(self.tile_ids)} tiles ({sum(len(v) for v in self.tile_images.values())} total images available for positive pairs)")

    def __len__(self):
        return len(self.samples)

    def _load_image(self, img_path):
        """Load image and run through DINOv2 processor."""
        try:
            pil_img = Image.open(img_path).convert("RGB")
            inputs = self.processor(pil_img, return_tensors="pt")
            return inputs["pixel_values"][0]
        except Exception as e:
            print(f"Error loading {img_path}: {e}")
            return torch.zeros(3, 224, 224)

    def __getitem__(self, idx):
        anchor_path, tile_id = self.samples[idx]

        # Anchor
        anchor = self._load_image(anchor_path)

        # Positive: different image from the SAME tile
        positive_candidates = [p for p in self.tile_images[tile_id] if p != anchor_path]
        if not positive_candidates:
            positive_candidates = self.tile_images[tile_id]
        positive_path = random.choice(positive_candidates)
        positive = self._load_image(positive_path)

        # Negative: image from a DIFFERENT tile
        neg_tile_id = tile_id
        while neg_tile_id == tile_id:
            neg_tile_id = random.choice(self.tile_ids)
        negative_path = random.choice(self.tile_images[neg_tile_id])
        negative = self._load_image(negative_path)

        return {
            "anchor": anchor,
            "positive": positive,
            "negative": negative,
            "tile_id": tile_id,
        }


# ── Helpers ─────────────────────────────────────────────
def freeze_early_layers(model, num_freeze=FREEZE_LAYERS):
    """Freeze patch embeddings and the first *num_freeze* transformer blocks."""
    # Freeze patch embeddings
    for param in model.embeddings.parameters():
        param.requires_grad = False

    # Freeze early encoder layers
    for i, layer in enumerate(model.encoder.layer):
        if i < num_freeze:
            for param in layer.parameters():
                param.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Trainable parameters: {trainable:,} / {total:,} ({100 * trainable / total:.1f}%)")


def get_embeddings(model, pixel_values):
    """Forward pass → mean-pool → L2-normalise.  Matches embed.py exactly."""
    outputs = model(pixel_values=pixel_values)
    features = outputs.last_hidden_state.mean(dim=1)
    features = features / features.norm(dim=-1, keepdim=True)
    return features


# ── Main training loop ──────────────────────────────────
def finetune_dino_on_tiles(num_epochs=EPOCHS, batch_size=BATCH_SIZE, lr=LEARNING_RATE):
    """Fine-tune DINOv2 on marble tiles using Triplet Margin Loss."""

    print("=" * 70)
    print("  DINO v2 FINE-TUNING — TRIPLET MARGIN LOSS")
    print("=" * 70)
    print(f"  Model:          {MODEL_NAME}")
    print(f"  Device:         {DEVICE}")
    print(f"  Batch Size:     {batch_size}")
    print(f"  Learning Rate:  {lr}")
    print(f"  Epochs:         {num_epochs}")
    print(f"  Triplet Margin: {TRIPLET_MARGIN}")
    print(f"  Frozen Layers:  first {FREEZE_LAYERS} of 12")
    print("=" * 70 + "\n")

    # ── Load model ──────────────────────────────────────
    print(f"Loading DINOv2 ({MODEL_NAME})...")
    model = Dinov2Model.from_pretrained(MODEL_NAME).to(DEVICE)
    processor = AutoImageProcessor.from_pretrained(MODEL_NAME)

    # Freeze early layers to prevent overfitting on small dataset
    freeze_early_layers(model, FREEZE_LAYERS)
    model.train()

    # ── Loss & optimizer ────────────────────────────────
    criterion = nn.TripletMarginLoss(margin=TRIPLET_MARGIN, p=2)
    optimizer = AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr,
        weight_decay=1e-4,
    )

    # ── Dataset ─────────────────────────────────────────
    print(f"\nLoading dataset from {DATASET_PATH}...")
    dataset = TileTripletDataset(DATASET_PATH, processor)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        drop_last=True,
    )

    scheduler = CosineAnnealingLR(optimizer, T_max=num_epochs * len(dataloader))

    # ── Checkpoints ─────────────────────────────────────
    best_loss = float("inf")
    best_path = os.path.join(_CACHE, "finetune_dinov2_best.pt")
    last_path = os.path.join(_CACHE, "finetune_dinov2_last.pt")

    print(f"\nStarting training for {num_epochs} epochs...\n")

    for epoch in range(num_epochs):
        total_loss = 0.0
        num_batches = 0
        pbar = tqdm(dataloader, desc=f"Epoch {epoch + 1}/{num_epochs}")

        for batch in pbar:
            anchor   = batch["anchor"].to(DEVICE)
            positive = batch["positive"].to(DEVICE)
            negative = batch["negative"].to(DEVICE)

            # Forward — all three branches receive gradients
            emb_a = get_embeddings(model, anchor)
            emb_p = get_embeddings(model, positive)
            emb_n = get_embeddings(model, negative)

            loss = criterion(emb_a, emb_p, emb_n)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            num_batches += 1
            pbar.set_postfix({
                "loss": f"{total_loss / num_batches:.4f}",
                "lr": f"{scheduler.get_last_lr()[0]:.2e}",
            })

        avg_loss = total_loss / max(num_batches, 1)
        print(f"\nEpoch {epoch + 1} — Avg Loss: {avg_loss:.6f}")

        # Save best checkpoint
        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save(model.state_dict(), best_path)
            print(f"  ✓ Saved BEST checkpoint (loss {avg_loss:.6f})")

        # Always save last checkpoint
        torch.save(model.state_dict(), last_path)

    print("\n" + "=" * 70)
    print("  ✅ FINE-TUNING COMPLETE!")
    print("=" * 70)
    print(f"  Best model:  {best_path}")
    print(f"  Best loss:   {best_loss:.6f}")
    print()
    print("  Next steps:")
    print("    1. Run:  python regenerate_embeddings.py")
    print("    2. Restart the backend server")
    print("    3. Search accuracy should now be significantly higher")
    print("=" * 70)

    return model


if __name__ == "__main__":
    finetune_dino_on_tiles()
