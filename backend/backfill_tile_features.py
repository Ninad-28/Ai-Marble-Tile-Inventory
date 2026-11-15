"""
Fill missing style / finish / color / size / dimensions / etc. on existing tiles
so catalog + inventory have realistic test data.
"""
import sys
import os
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.tile import Tile
from app.models.categories import (
    Material, Style, Finish, SizeFormat, Application, ColorFamily, Origin,
)

# Common slab / tile sizes (width_cm, height_cm, thickness_cm, size_format_id hint)
SIZE_PRESETS = [
    (30, 30, 1.0, 1),
    (30, 60, 1.0, 2),
    (60, 60, 1.2, 2),
    (60, 120, 1.5, 3),
    (80, 80, 1.5, 3),
    (120, 240, 2.0, 4),  # slab
]

DESCRIPTIONS = [
    "Natural stone with subtle veining suitable for flooring and feature walls.",
    "Premium polished surface with consistent tone across the batch.",
    "Characterful geological movement; best paired with neutral grout.",
    "Dense structure with low porosity after factory sealing.",
    "Bookmatch-ready slab with dramatic continuous veins.",
]


def main():
    db = SessionLocal()
    styles = db.query(Style).order_by(Style.id).all()
    finishes = db.query(Finish).order_by(Finish.id).all()
    colors = db.query(ColorFamily).order_by(ColorFamily.id).all()
    sizes = db.query(SizeFormat).order_by(SizeFormat.id).all()
    apps = db.query(Application).order_by(Application.id).all()
    origins = db.query(Origin).order_by(Origin.id).all()
    materials = [
        m for m in db.query(Material).order_by(Material.id).all()
        if m.name.lower() != "string"
    ]

    if not all([styles, finishes, colors, sizes, apps, origins, materials]):
        print("ERROR: Run seed.py first to create categories.")
        db.close()
        return

    size_by_id = {s.id: s for s in sizes}
    tiles = db.query(Tile).order_by(Tile.id).all()
    updated = 0

    for i, tile in enumerate(tiles):
        # Fix bogus "string" material
        if tile.material and tile.material.name.lower() == "string":
            tile.material_id = materials[i % len(materials)].id
        elif tile.material_id is None:
            tile.material_id = materials[i % len(materials)].id

        if tile.style_id is None:
            tile.style_id = styles[i % len(styles)].id
        if tile.finish_id is None:
            tile.finish_id = finishes[i % len(finishes)].id
        if tile.color_family_id is None:
            tile.color_family_id = colors[i % len(colors)].id
        if tile.application_id is None:
            tile.application_id = apps[i % len(apps)].id
        if tile.origin_id is None:
            tile.origin_id = origins[i % len(origins)].id

        w, h, th, size_hint = SIZE_PRESETS[i % len(SIZE_PRESETS)]
        if tile.width_cm is None:
            tile.width_cm = w
        if tile.height_cm is None:
            tile.height_cm = h
        if tile.thickness_cm is None:
            tile.thickness_cm = th
        if tile.size_format_id is None:
            tile.size_format_id = size_hint if size_hint in size_by_id else sizes[min(i % len(sizes), len(sizes) - 1)].id

        if tile.price_per_sqm is None:
            # Realistic-ish B2B rates by cycling
            base = [18, 25, 32, 45, 55, 72, 90][i % 7]
            tile.price_per_sqm = float(base + (i % 5))

        if not tile.description:
            tile.description = DESCRIPTIONS[i % len(DESCRIPTIONS)]

        updated += 1

    db.commit()
    print(f"Updated {updated} tiles with style/finish/color/size/dimensions.")
    sample = db.query(Tile).filter(Tile.sku == "MRB-010").first()
    if sample:
        print(
            f"Sample {sample.sku}: "
            f"{sample.width_cm}x{sample.height_cm}x{sample.thickness_cm} cm | "
            f"style={sample.style_id} finish={sample.finish_id} color={sample.color_family_id}"
        )
    db.close()


if __name__ == "__main__":
    random.seed(42)
    main()
