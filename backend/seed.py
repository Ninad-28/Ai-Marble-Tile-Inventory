import sys
import os

# Ensure the app module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.admin import Admin
from app.middleware.auth import hash_password

# Import all the new category models
from app.models.categories import (
    Material, Style, Finish,
    SizeFormat, Application, ColorFamily, Origin
)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)


def seed_admin():
    db = SessionLocal()

    existing = db.query(Admin).filter(Admin.email == "admin@marble.com").first()
    if existing:
        print("✅ Admin already exists")
        db.close()
        return

    admin = Admin(
        name="Super Admin",
        email="admin@marble.com",
        password_hash=hash_password("admin123"),
        is_active=True
    )

    db.add(admin)
    db.commit()
    print("✅ Admin created successfully")
    print("   Email:    admin@marble.com")
    print("   Password: admin123")
    db.close()


def seed_categories():
    db = SessionLocal()

    # Helper function to bulk insert simple name-based categories
    def insert(model, items):
        for name in items:
            exists = db.query(model).filter(model.name == name).first()
            if not exists:
                db.add(model(name=name))
        db.commit()

    insert(Material, [
        "Marble", "Granite", "Quartzite", "Travertine",
        "Limestone", "Onyx", "Slate", "Porcelain", "Ceramic"
    ])

    insert(Style, [
        "Solid / Uniform", "Veined", "Heavily Veined",
        "Bookmatched", "Fossil / Embedded", "Multicolor / Breccia"
    ])

    insert(Finish, [
        "Polished", "Honed", "Brushed",
        "Tumbled", "Sandblasted", "Leathered"
    ])

    insert(SizeFormat, [
        "Small Format (up to 30x30)",
        "Medium Format (30x60 / 60x60)",
        "Large Format (60x120 / 80x80)",
        "Slab", "Mosaic", "Border / Listello", "Custom Cut"
    ])

    insert(Application, [
        "Flooring", "Wall Cladding", "Bathroom / Wet Areas",
        "Kitchen Countertop", "Outdoor / Exterior",
        "Pool Surrounds", "Feature / Accent Wall"
    ])

    # Color requires a custom loop because it has a hex_code
    colors = [
        ("White / Cream", "#F5F5F0"),
        ("Grey / Silver",  "#A8A8A8"),
        ("Beige / Ivory",  "#F5F0DC"),
        ("Black / Charcoal","#2C2C2C"),
        ("Green",          "#4A7C59"),
        ("Brown / Walnut", "#8B6343"),
        ("Gold / Yellow",  "#D4AF37"),
        ("Red / Burgundy", "#800020"),
        ("Blue",           "#4A6FA5"),
        ("Multi / Mixed",  "#CCCCCC"),
    ]

    for name, hex_code in colors:
        exists = db.query(ColorFamily).filter(ColorFamily.name == name).first()
        if not exists:
            db.add(ColorFamily(name=name, hex_code=hex_code))
    db.commit()

    insert(Origin, [
        "Italy", "Turkey", "India", "Spain",
        "Greece", "Brazil", "China", "Portugal", "Iran"
    ])

    print("✅ All categories seeded successfully")
    db.close()


if __name__ == "__main__":
    print("Starting database seeding process...")
    seed_admin()
    seed_categories()
    print("Seeding complete!")