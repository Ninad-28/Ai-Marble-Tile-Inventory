"""
Minimal non-destructive tests for the Gatekeeper validation layer.
"""
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch
from PIL import Image

# Ensure backend package is importable
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


def _make_test_image() -> bytes:
    arr = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    img = Image.fromarray(arr, "RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestGatekeeperModule(unittest.TestCase):
    def setUp(self):
        os.environ["GATEKEEPER_ENABLED"] = "false"
        import ai.gatekeeper as gk
        gk._gatekeeper = None

    def tearDown(self):
        os.environ.pop("GATEKEEPER_ENABLED", None)
        os.environ.pop("GATEKEEPER_THRESHOLD", None)
        os.environ.pop("GATEKEEPER_CHECKPOINT_PATH", None)
        import ai.gatekeeper as gk
        gk._gatekeeper = None

    def test_disabled_returns_pass_through(self):
        from ai.gatekeeper import validate_tile_image

        result = validate_tile_image(_make_test_image())
        self.assertTrue(result["is_tile"])
        self.assertEqual(result["score"], 1.0)

    def test_enabled_missing_checkpoint_fails_open(self):
        from ai.gatekeeper import Gatekeeper, validate_tile_image

        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "missing_gatekeeper.pt")
            os.environ["GATEKEEPER_ENABLED"] = "true"
            os.environ["GATEKEEPER_CHECKPOINT_PATH"] = missing

            import ai.gatekeeper as gk
            gk._gatekeeper = None

            result = validate_tile_image(_make_test_image())
            self.assertTrue(result["is_tile"])
            self.assertEqual(result["score"], 1.0)

            keeper = Gatekeeper(checkpoint_path=missing)
            self.assertFalse(keeper.load())
            self.assertFalse(keeper.is_ready)

    def test_validate_returns_expected_keys(self):
        from ai.gatekeeper import Gatekeeper

        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            checkpoint_path = f.name

        try:
            from torchvision import models
            import torch.nn as nn

            model = models.mobilenet_v3_small(weights=None)
            in_features = model.classifier[-1].in_features
            model.classifier[-1] = nn.Linear(in_features, 2)
            torch.save({"model_state_dict": model.state_dict()}, checkpoint_path)

            keeper = Gatekeeper(checkpoint_path=checkpoint_path)
            self.assertTrue(keeper.load())
            result = keeper.validate(_make_test_image(), threshold=0.70)
            self.assertIn("is_tile", result)
            self.assertIn("score", result)
            self.assertIsInstance(result["is_tile"], bool)
            self.assertIsInstance(result["score"], float)
        finally:
            os.remove(checkpoint_path)

    def test_rejection_when_score_below_threshold(self):
        from ai.gatekeeper import Gatekeeper

        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            checkpoint_path = f.name

        try:
            from torchvision import models
            import torch.nn as nn

            model = models.mobilenet_v3_small(weights=None)
            in_features = model.classifier[-1].in_features
            model.classifier[-1] = nn.Linear(in_features, 2)
            # Bias class 0 (not_tile) heavily so tile score stays low
            with torch.no_grad():
                model.classifier[-1].bias.copy_(torch.tensor([5.0, -5.0]))
            torch.save({"model_state_dict": model.state_dict()}, checkpoint_path)

            keeper = Gatekeeper(checkpoint_path=checkpoint_path)
            keeper.load()
            result = keeper.validate(_make_test_image(), threshold=0.70)
            self.assertFalse(result["is_tile"])
            self.assertLess(result["score"], 0.70)
        finally:
            os.remove(checkpoint_path)


class TestSearchRouterGatekeeper(unittest.TestCase):
    def setUp(self):
        os.environ["GATEKEEPER_ENABLED"] = "false"

    def tearDown(self):
        os.environ.pop("GATEKEEPER_ENABLED", None)
        import ai.gatekeeper as gk
        gk._gatekeeper = None

    def test_app_starts(self):
        from app.main import app

        self.assertIsNotNone(app)
        self.assertEqual(app.title, "Marble AI API")

    @patch("app.routers.search.run_visual_search")
    @patch("app.routers.search.validate_tile_image")
    def test_gatekeeper_disabled_search_unchanged(self, mock_validate, mock_search):
        from fastapi.testclient import TestClient
        from app.main import app

        mock_validate.return_value = {"is_tile": True, "score": 1.0}
        mock_search.return_value = {
            "results": [],
            "validation": {"is_valid": True, "is_tile": True, "confidence": 100.0, "message": ""},
        }

        client = TestClient(app)
        image_bytes = _make_test_image()
        response = client.post(
            "/api/search/image?top_k=3",
            files={"file": ("test.jpg", image_bytes, "image/jpeg")},
        )

        mock_validate.assert_called_once()
        mock_search.assert_called_once()
        self.assertIn(response.status_code, (200, 500))

    @patch("app.routers.search.run_visual_search")
    @patch("app.routers.search.validate_tile_image")
    def test_gatekeeper_rejection_returns_400(self, mock_validate, mock_search):
        from fastapi.testclient import TestClient
        from app.main import app

        mock_validate.return_value = {"is_tile": False, "score": 0.12}
        client = TestClient(app)
        image_bytes = _make_test_image()
        response = client.post(
            "/api/search/image?top_k=3",
            files={"file": ("test.jpg", image_bytes, "image/jpeg")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "Please upload a valid marble, tile, or stone surface image.",
        )
        mock_search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
