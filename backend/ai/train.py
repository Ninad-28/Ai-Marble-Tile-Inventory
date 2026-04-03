import os
import sys

# ── Redirect ALL cache away from .cache (Windows permission fix) ──
_CACHE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "model_cache"
)
os.makedirs(_CACHE, exist_ok=True)
os.environ["HF_HOME"]            = _CACHE
os.environ["TORCH_HOME"]         = _CACHE
os.environ["TRANSFORMERS_CACHE"] = _CACHE
os.environ["XDG_CACHE_HOME"]     = _CACHE
os.environ["HUGGINGFACE_HUB_CACHE"] = _CACHE

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import open_clip
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
import random
from ai.preprocess import preprocess_image

DATASET_PATH  = os.path.join(os.path.dirname(__file__), "..", "dataset", "train")
MODEL_SAVE_PATH = os.path.join(os.path.dirname(__file__), "fine_tuned_model.pt")
EPOCHS        = 10
BATCH_SIZE    = 16
LEARNING_RATE = 1e-5
DEVICE        = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Training on: {DEVICE}")
print(f"Cache folder: {_CACHE}")

# ── Dataset ──────────────────────────────────────────────
class TileDataset(Dataset):
    """
    Returns (anchor, positive, label) pairs.
    Anchor + Positive = same tile (contrastive learning)
    """
    def __init__(self, dataset_path, transform):
        self.transform = transform
        self.tile_images = {}  # {tile_id: [image_paths]}

        folders = sorted([
            f for f in os.listdir(dataset_path)
            if os.path.isdir(os.path.join(dataset_path, f))
            and f.startswith("tile_")
        ])

        for folder in folders:
            tile_id = int(folder.split("_")[1])
            folder_path = os.path.join(dataset_path, folder)
            images = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]
            if len(images) >= 2:
                self.tile_images[tile_id] = images

        # Build pairs list
        self.pairs = []
        tile_ids = list(self.tile_images.keys())

        for tile_id in tile_ids:
            imgs = self.tile_images[tile_id]
            # Positive pairs (same tile)
            for i in range(len(imgs)):
                for j in range(i + 1, len(imgs)):
                    self.pairs.append((imgs[i], imgs[j], 1))

            # Negative pairs (different tiles)
            other_ids = [t for t in tile_ids if t != tile_id]
            for _ in range(len(imgs)):
                other_id = random.choice(other_ids)
                other_img = random.choice(self.tile_images[other_id])
                anchor = random.choice(imgs)
                self.pairs.append((anchor, other_img, 0))

        random.shuffle(self.pairs)
        print(f"✅ Dataset: {len(self.pairs)} pairs from {len(tile_ids)} tiles")

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        img1_path, img2_path, label = self.pairs[idx]
        img1 = self.transform(preprocess_image(img1_path))
        img2 = self.transform(preprocess_image(img2_path))
        return img1, img2, torch.tensor(label, dtype=torch.float32)


# ── Training ─────────────────────────────────────────────
def train():
    # Load base CLIP model
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="openai"
    )
    model = model.to(DEVICE)

    # Only fine-tune the visual encoder
    for name, param in model.named_parameters():
        param.requires_grad = "visual" in name

    dataset = TileDataset(DATASET_PATH, preprocess)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE,
                        shuffle=True, num_workers=0)

    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE
    )

    # Contrastive loss
    loss_fn = torch.nn.CosineEmbeddingLoss(margin=0.3)

    print(f"\n🚀 Starting fine-tuning for {EPOCHS} epochs...\n")

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for img1, img2, labels in tqdm(loader, desc=f"Epoch {epoch+1}/{EPOCHS}"):
            img1 = img1.to(DEVICE)
            img2 = img2.to(DEVICE)
            # CosineEmbeddingLoss expects labels: 1 (similar) or -1 (dissimilar)
            targets = labels.to(DEVICE) * 2 - 1

            # Get embeddings
            feat1 = model.encode_image(img1)
            feat2 = model.encode_image(img2)

            loss = loss_fn(feat1, feat2, targets)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

            # Accuracy: cosine similarity > 0.5 = match
            with torch.no_grad():
                sim = torch.nn.functional.cosine_similarity(feat1, feat2)
                predicted = (sim > 0.5).float()
                original_labels = labels.to(DEVICE)
                correct += (predicted == original_labels).sum().item()
                total += len(labels)

        avg_loss = total_loss / len(loader)
        accuracy = correct / total * 100
        print(f"Epoch {epoch+1}: Loss={avg_loss:.4f} | Accuracy={accuracy:.1f}%")

    # Save fine-tuned weights
    torch.save(model.state_dict(), MODEL_SAVE_PATH)
    print(f"\n✅ Model saved to {MODEL_SAVE_PATH}")

if __name__ == "__main__":
    train()