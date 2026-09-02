"""
Lightweight Gatekeeper for tile/marble/stone surface validation.

Runs before the DINOv2 search pipeline to reject obviously invalid uploads.
Uses MobileNetV3-Small (torchvision) when a trained checkpoint is available.
"""
import io
import logging
import os
from pathlib import Path
from typing import Optional, Union

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

logger = logging.getLogger(__name__)

_CACHE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "model_cache",
)
DEFAULT_CHECKPOINT = os.path.join(_CACHE, "gatekeeper_mobilenetv3_best.pt")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

INPUT_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

_TRANSFORM = transforms.Compose([
    transforms.Resize(INPUT_SIZE),
    transforms.CenterCrop(INPUT_SIZE),
    transforms.ToTensor(),
    transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])


def _build_model() -> nn.Module:
    """Build MobileNetV3-Small with a 2-class head (not_tile, tile)."""
    model = models.mobilenet_v3_small(weights=None)
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, 2)
    return model


class Gatekeeper:
    """Binary tile-surface classifier with lazy checkpoint loading."""

    def __init__(self, checkpoint_path: str = DEFAULT_CHECKPOINT):
        self.checkpoint_path = checkpoint_path
        self._model: Optional[nn.Module] = None
        self._load_failed = False

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def _resolve_checkpoint_path(self) -> str:
        path = self.checkpoint_path
        if not os.path.isabs(path):
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                path,
            )
        return path

    def load(self) -> bool:
        """Load checkpoint if available. Returns True on success."""
        if self._model is not None:
            return True
        if self._load_failed:
            return False

        checkpoint_path = self._resolve_checkpoint_path()
        if not os.path.isfile(checkpoint_path):
            logger.warning(
                "Gatekeeper checkpoint not found at %s — validation skipped (fail-open)",
                checkpoint_path,
            )
            self._load_failed = True
            return False

        try:
            model = _build_model()
            checkpoint = torch.load(checkpoint_path, map_location=DEVICE)

            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                state_dict = checkpoint["model_state_dict"]
            elif isinstance(checkpoint, dict) and "state_dict" in checkpoint:
                state_dict = checkpoint["state_dict"]
            else:
                state_dict = checkpoint

            model.load_state_dict(state_dict)
            model.to(DEVICE)
            model.eval()
            self._model = model
            logger.info("Gatekeeper model loaded from %s", checkpoint_path)
            return True
        except Exception as exc:
            logger.warning(
                "Gatekeeper checkpoint could not be loaded from %s: %s — validation skipped (fail-open)",
                checkpoint_path,
                exc,
            )
            self._load_failed = True
            return False

    def _load_image(self, image_input: Union[str, bytes, Image.Image]) -> Image.Image:
        if isinstance(image_input, Image.Image):
            return image_input.convert("RGB")
        if isinstance(image_input, str):
            return Image.open(image_input).convert("RGB")
        if isinstance(image_input, bytes):
            return Image.open(io.BytesIO(image_input)).convert("RGB")
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    def validate(self, image_input: Union[str, bytes, Image.Image], threshold: float) -> dict:
        """
        Validate whether an image is a tile/marble/stone surface.

        Returns:
            {"is_tile": bool, "score": float}
        """
        if not self.load():
            return {"is_tile": True, "score": 1.0}

        try:
            image = self._load_image(image_input)
            tensor = _TRANSFORM(image).unsqueeze(0).to(DEVICE)

            with torch.no_grad():
                logits = self._model(tensor)
                probs = torch.softmax(logits, dim=1)
                tile_score = float(probs[0, 1].item())

            is_tile = tile_score >= threshold
            return {"is_tile": is_tile, "score": round(tile_score, 4)}
        except Exception as exc:
            logger.warning("Gatekeeper inference failed: %s — validation skipped (fail-open)", exc)
            return {"is_tile": True, "score": 1.0}


_gatekeeper: Optional[Gatekeeper] = None


def get_gatekeeper() -> Gatekeeper:
    global _gatekeeper
    if _gatekeeper is None:
        checkpoint = os.getenv("GATEKEEPER_CHECKPOINT_PATH", DEFAULT_CHECKPOINT)
        _gatekeeper = Gatekeeper(checkpoint_path=checkpoint)
    return _gatekeeper


def is_gatekeeper_enabled() -> bool:
    return os.getenv("GATEKEEPER_ENABLED", "false").lower() in ("1", "true", "yes")


def get_gatekeeper_threshold() -> float:
    return float(os.getenv("GATEKEEPER_THRESHOLD", "0.70"))


def validate_tile_image(image_input: Union[str, bytes, Image.Image]) -> dict:
    """
    Public API for gatekeeper validation.

    When GATEKEEPER_ENABLED=false, returns pass-through without loading the model.
    When enabled but checkpoint is missing, fails open (is_tile=True).
    """
    if not is_gatekeeper_enabled():
        return {"is_tile": True, "score": 1.0}

    threshold = get_gatekeeper_threshold()
    return get_gatekeeper().validate(image_input, threshold=threshold)
