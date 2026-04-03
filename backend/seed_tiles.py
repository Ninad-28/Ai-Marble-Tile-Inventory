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

        tile = Tile(
            sku=sku,
            name=name,
            material_id=1,   # Marble (first material seeded)
            is_active=True
        )
        db.add(tile)
        db.flush()

        # Auto create inventory
        inv = Inventory(tile_id=tile.id, quantity=0, low_stock_threshold=10)
        db.add(inv)

        created += 1

    db.commit()
    db.close()

    print(f"✅ Created: {created} tiles")
    print(f"⏭️  Skipped: {skipped} (already existed)")
    print(f"📦 Total tiles in DB ready for embedding")

if __name__ == "__main__":
    seed_tiles()