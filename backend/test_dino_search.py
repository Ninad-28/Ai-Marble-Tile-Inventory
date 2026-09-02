"""
Test DINO v2 search and tile validation
"""

import requests
import json
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
DATASET_PATH = Path("d:\\MajorProject\\Ai-Marble-Tile-Inventory\\backend\\dataset\\train")

def test_tile_search():
    """Test searching with a real tile image"""
    print("\n" + "="*60)
    print("TEST 1: SEARCH WITH TILE IMAGE (DINO v2)")
    print("="*60)
    
    # Use first tile image from dataset
    tile_img = DATASET_PATH / "tile_5" / "img_5_orig.jpg"
    
    if not tile_img.exists():
        print(f"ERROR: Test image not found: {tile_img}")
        return False
    
    try:
        with open(tile_img, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{BACKEND_URL}/api/search/image?top_k=3",
                files=files,
                timeout=30
            )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Time: {data.get('response_time_ms', 'N/A')}ms")
            print(f"Results Found: {len(data.get('results', []))}")
            
            results = data.get("results", [])
            if results:
                print("\n✓ TOP 3 MATCHES:")
                for i, r in enumerate(results, 1):
                    print(f"  {i}. Tile {r['sku']} - Confidence: {r['confidence']}%")
                return True
            else:
                print("✗ No results returned")
                return False
        else:
            print(f"✗ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

def test_non_tile_rejection():
    """Test that non-tile images are rejected"""
    print("\n" + "="*60)
    print("TEST 2: NON-TILE IMAGE REJECTION")
    print("="*60)
    print("(Simulating with random noise image)")
    
    import numpy as np
    from PIL import Image
    import io
    
    # Create a random noise image (non-tile)
    random_img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    pil_img = Image.fromarray(random_img.astype('uint8'), 'RGB')
    
    img_bytes = io.BytesIO()
    pil_img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    try:
        files = {"file": ("random.jpg", img_bytes, "image/jpeg")}
        response = requests.post(
            f"{BACKEND_URL}/api/search/image?top_k=3",
            files=files,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                print("✓ Non-tile image correctly rejected (no matches)")
                return True
            elif all(r['confidence'] < 50 for r in results):
                print("✓ Low confidence results for non-tile (validation working)")
                print(f"  Max confidence: {max(r['confidence'] for r in results)}%")
                return True
            else:
                print(f"⚠ Unexpected match with high confidence: {results[0]['confidence']}%")
                return False
        else:
            print(f"Server error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False

def test_various_tile_angles():
    """Test search with different tile image variations"""
    print("\n" + "="*60)
    print("TEST 3: VARIOUS TILE ANGLES & VARIATIONS")
    print("="*60)
    
    test_images = [
        ("orig", "img_5_orig.jpg"),
        ("rotated", "img_5_rot1.jpg"),
        ("dark", "img_5_dim.jpg"),
        ("bright", "img_5_bright.jpg"),
        ("blurry", "img_5_blur.jpg"),
    ]
    
    results_summary = []
    
    for name, filename in test_images:
        img_path = DATASET_PATH / "tile_5" / filename
        
        if not img_path.exists():
            continue
        
        try:
            with open(img_path, "rb") as f:
                files = {"file": f}
                response = requests.post(
                    f"{BACKEND_URL}/api/search/image?top_k=3",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    top_confidence = results[0]['confidence']
                    results_summary.append((name, top_confidence, "✓"))
                else:
                    results_summary.append((name, 0, "✗ No results"))
            else:
                results_summary.append((name, 0, "✗ Error"))
                
        except Exception as e:
            results_summary.append((name, 0, f"✗ {str(e)[:20]}"))
    
    print("\nResults by image variation:")
    for name, conf, status in results_summary:
        print(f"  {name:12} → Confidence: {conf:5.1f}%  {status}")
    
    # Check if all had reasonable confidence
    all_confident = all(conf >= 70 for _, conf, _ in results_summary)
    return all_confident

if __name__ == "__main__":
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║         DINO v2 TILE SEARCH VALIDATION TESTS              ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    test1 = test_tile_search()
    test2 = test_non_tile_rejection()
    test3 = test_various_tile_angles()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Test 1 (Tile Search):         {'✓ PASS' if test1 else '✗ FAIL'}")
    print(f"Test 2 (Non-tile Rejection):  {'✓ PASS' if test2 else '✗ FAIL'}")
    print(f"Test 3 (Various Angles):      {'✓ PASS' if test3 else '✗ FAIL'}")
    print("="*60)
