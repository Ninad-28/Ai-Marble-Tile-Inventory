import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

# Ensure pgvector extension exists before creating table with vector type
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as e:
        print(f"WARNING: pgvector extension not available: {e}")

Base.metadata.create_all(bind=engine)

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset", "train")

def seed_tiles():
    db = SessionLocal()

    # Get all tile folders sorted
    tile_folders = sorted([
        f for f in os.listdir(DATASET_PATH)
        if os.path.isdir(os.path.join(DATASET_PATH, f))
        and f.startswith("tile_")
    ])

    print(f"Found {len(tile_folders)} tile folders")

    created = 0
    skipped = 0

    for folder in tile_folders:
        # tile_5 → SKU = MRB-005
        number = folder.split("_")[1].zfill(3)
        sku = f"MRB-{number}"
        name = f"Marble Tile {number}"

        # Skip if already exists
        if db.query(Tile).filter(Tile.sku == sku).first():
            skipped += 1
            continue

        n = int(number)
        size_presets = [
            (30, 30, 1.0, 1),
            (30, 60, 1.0, 2),
            (60, 60, 1.2, 2),
            (60, 120, 1.5, 3),
            (80, 80, 1.5, 3),
            (120, 240, 2.0, 4),
        ]
        w, h, th, size_id = size_presets[n % len(size_presets)]

        tile = Tile(
            sku=sku,
            name=name,
            material_id=1 + (n % 9),  # cycle materials 1-9 (skip bogus ids)
            style_id=1 + (n % 6),
            finish_id=1 + (n % 6),
            color_family_id=1 + (n % 10),
            size_format_id=size_id,
            application_id=1 + (n % 5),
            origin_id=1 + (n % 5),
            width_cm=w,
            height_cm=h,
            thickness_cm=th,
            price_per_sqm=float(18 + (n % 7) * 8),
            description="Natural stone tile seeded for catalog and visual search testing.",
            is_active=True,
        )
        db.add(tile)
        db.flush()

        # Auto create inventory with realistic stock
        initial_stock = 20 + (n % 30)
        inv = Inventory(tile_id=tile.id, quantity=initial_stock,
                        low_stock_threshold=5)
        db.add(inv)

        created += 1

    db.commit()
    db.close()

    print(f"Created: {created} tiles")
    print(f"Skipped: {skipped} (already existed)")
    print(f"Total tiles in DB ready for embedding")

if __name__ == "__main__":
    seed_tiles()