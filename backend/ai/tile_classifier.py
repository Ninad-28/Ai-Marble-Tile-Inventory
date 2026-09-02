"""
Tile Image Classifier using DINO v2.
Detects whether an uploaded image is a tile or non-tile (dog, cat, random objects).
Uses DINO v2 features + SVM or simple threshold-based classification.
"""
import os
import sys
import torch
import numpy as np
from pathlib import Path

# Cache setup
_CACHE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "model_cache"
)
os.makedirs(_CACHE, exist_ok=True)
os.environ["HF_HOME"] = _CACHE
os.environ["TORCH_HOME"] = _CACHE
os.environ["TRANSFORMERS_CACHE"] = _CACHE

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transformers import AutoImageProcessor, Dinov2Model
from PIL import Image
from typing import Tuple

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "facebook/dinov2-base"


class TileClassifier:
    """
    Classifies whether an image is a tile or not.
    
    Strategy:
    1. Extract DINO v2 features from input image
    2. Compare against known tile embeddings to estimate "tile-ness"
    3. If matches well with tile dataset, it's a TILE
    4. If fails to match, it's NOT A TILE (reject)
    """
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.tile_embeddings_cache = None
        self.max_reference_images = 400
        self.tile_threshold = 0.50  # Adjustable - tiles above 50% similarity to tile dataset
        
    def load_model(self):
        """Load DINO v2 model."""
        if self.model is None:
            print(f"Loading DINO v2 model for tile classification...")
            self.model = Dinov2Model.from_pretrained(MODEL_NAME).to(DEVICE)
            self.processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
            self.model.eval()
    
    def get_embedding(self, image_input) -> np.ndarray:
        """Extract DINO v2 embedding from image."""
        self.load_model()
        
        if isinstance(image_input, str):
            image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, bytes):
            from io import BytesIO
            image = Image.open(BytesIO(image_input)).convert("RGB")
        else:
            image = image_input
        
        inputs = self.processor(images=image, return_tensors="pt").to(DEVICE)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            features = outputs.last_hidden_state.mean(dim=1)
            features = features / features.norm(dim=-1, keepdim=True)
        
        return features.cpu().numpy()[0]
    
    def get_tile_reference_embeddings(self, db_session=None):
        """
        Get reference embeddings from known tiles in database.
        Returns a matrix of reference tile embeddings.
        """
        if self.tile_embeddings_cache is not None:
            return self.tile_embeddings_cache
        
        if db_session is None:
            # Load from disk or generate
            print("Loading tile reference embeddings...")
            dataset_path = os.path.join(
                os.path.dirname(__file__), "..", "dataset", "train"
            )
            
            tile_embeddings = []
            tile_folders = sorted([
                f for f in os.listdir(dataset_path)
                if os.path.isdir(os.path.join(dataset_path, f))
                and f.startswith("tile_")
            ])
            
            print(f"Building tile reference set from {len(tile_folders)} tile folders...")
            for folder in tile_folders:
                folder_path = os.path.join(dataset_path, folder)
                image_paths = sorted([
                    os.path.join(folder_path, name)
                    for name in os.listdir(folder_path)
                    if name.lower().endswith((".jpg", ".jpeg", ".png"))
                ])[:3]  # keep it fast: a few exemplars per tile

                for img_path in image_paths:
                    try:
                        emb = self.get_embedding(img_path)
                        tile_embeddings.append(emb)
                    except Exception as e:
                        print(f"Error embedding {folder}: {e}")
                if len(tile_embeddings) >= self.max_reference_images:
                    break
            
            if tile_embeddings:
                self.tile_embeddings_cache = np.array(tile_embeddings, dtype=np.float32)
            else:
                # Fallback: none available
                self.tile_embeddings_cache = None
        
        return self.tile_embeddings_cache
    
    def is_tile(self, image_input, threshold: float = None) -> Tuple[bool, float]:
        """
        Determine if image is a tile.
        
        Returns:
            (is_tile: bool, confidence: float)
            - is_tile: True if image is a tile, False otherwise
            - confidence: similarity score to tile dataset (0-1)
        """
        if threshold is None:
            threshold = self.tile_threshold
        
        try:
            query_embedding = self.get_embedding(image_input)
            reference_embeddings = self.get_tile_reference_embeddings()
            
            if reference_embeddings is None:
                # No reference data, allow everything
                print("Warning: No reference tile embeddings available, allowing image")
                return True, 1.0
            
            # Compute similarities and use mean top-k to avoid overfitting to one centroid.
            similarities = np.dot(reference_embeddings, query_embedding)
            top_k = min(10, similarities.shape[0])
            top_similarities = np.sort(similarities)[-top_k:]
            similarity = float(np.mean(top_similarities))
            similarity = max(0.0, min(similarity, 1.0))
            
            # Decision: if similarity > threshold, it's a tile
            is_tile_pred = similarity >= threshold
            
            return is_tile_pred, similarity
        
        except Exception as e:
            print(f"Error in tile classification: {e}")
            # On error, allow image (fail-open for now)
            return True, 0.5
    
    def validate_tile_image(self, image_input, min_confidence: float = 0.50) -> dict:
        """
        Full validation pipeline for tile images.
        
        Returns dict:
            {
                "is_valid": bool,
                "is_tile": bool,
                "confidence": float,
                "message": str
            }
        """
        is_tile, confidence = self.is_tile(image_input, threshold=min_confidence)
        
        result = {
            "is_valid": is_tile,
            "is_tile": is_tile,
            "confidence": round(confidence * 100, 2),
            "message": ""
        }
        
        if not is_tile:
            result["message"] = (
                f"Image does not appear to be a tile. "
                f"Confidence: {result['confidence']}%. "
                f"Please upload a tile image (not a dog, cat, or other object)."
            )
        else:
            result["message"] = f"Valid tile image detected (confidence: {result['confidence']}%)"
        
        return result


# Global classifier instance
_classifier = None

def get_classifier() -> TileClassifier:
    """Get or create global tile classifier."""
    global _classifier
    if _classifier is None:
        _classifier = TileClassifier()
    return _classifier

def validate_uploaded_image(image_input, min_confidence: float = 0.50) -> dict:
    """Quick API to validate if uploaded image is a tile."""
    classifier = get_classifier()
    return classifier.validate_tile_image(image_input, min_confidence)
