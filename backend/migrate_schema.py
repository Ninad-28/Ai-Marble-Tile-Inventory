"""
Migration: Update tile_embeddings table for DINO v2 (768 dimensions)
This drops and recreates the table with the new schema.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ── Cache fix ──────────────────────────────────────────
_CACHE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "model_cache"
)
os.makedirs(_CACHE, exist_ok=True)

from app.database import engine, Base, SessionLocal
from sqlalchemy import text, inspect

# ── Import all models ──────────────────────────────────
from app.models.admin import Admin
from app.models.categories import (
    Material, Style, Finish,
    SizeFormat, Application, ColorFamily, Origin
)
from app.models.tile import Tile
from app.models.tile_image import TileImage, TileEmbedding
from app.models.inventory import Inventory, WarehouseLocation
from app.models.search_log import SearchLog

def migrate():
    """Migrate to new 768-dim embedding schema"""
    
    print("\n" + "="*60)
    print("MIGRATING DATABASE SCHEMA FOR DINO v2")
    print("="*60)
    
    with engine.connect() as conn:
        # Check if pgvector extension exists
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            has_pgvector = True
        except:
            has_pgvector = False
            print("[WARNING] pgvector not available, using TEXT for embeddings")
        
        conn.commit()
        
        # Drop old embeddings table if exists
        print("\nDropping old tile_embeddings table...")
        try:
            conn.execute(text("DROP TABLE IF EXISTS tile_embeddings;"))
            conn.commit()
            print("[OK] Old table dropped")
        except Exception as e:
            print(f"[WARNING] Could not drop table: {e}")
            conn.commit()
    
    # Recreate tables with new schema
    print("\nRecreating tables with new schema...")
    Base.metadata.create_all(bind=engine)
    print("[OK] New tables created")
    
    # Verify schema
    inspector = inspect(engine)
    if 'tile_embeddings' in inspector.get_table_names():
        columns = {col['name']: col for col in inspector.get_columns('tile_embeddings')}
        print(f"\n[OK] tile_embeddings table created with columns:")
        for name, col in columns.items():
            print(f"     - {name}: {col['type']}")
    
    print("\n" + "="*60)
    print("MIGRATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    migrate()
