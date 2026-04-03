from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth import get_current_admin
from app.models.categories import (
    Material, Style, Finish, SizeFormat,
    Application, ColorFamily, Origin
)
from app.schemas.category import CategoryBase, CategoryOut, ColorFamilyOut

router = APIRouter(prefix="/api/categories", tags=["Categories"])

# ── Helper ──────────────────────────────────────────────
def get_all(model, db):
    return db.query(model).filter(model.is_active == True).all()

def add_item(model, name, db):
    exists = db.query(model).filter(model.name == name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Already exists")
    item = model(name=name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

# ── Materials ───────────────────────────────────────────
@router.get("/materials", response_model=list[CategoryOut])
def get_materials(db: Session = Depends(get_db),
                  _=Depends(get_current_admin)):
    return get_all(Material, db)

@router.post("/materials", response_model=CategoryOut)
def add_material(body: CategoryBase, db: Session = Depends(get_db),
                 _=Depends(get_current_admin)):
    return add_item(Material, body.name, db)

# ── Styles ──────────────────────────────────────────────
@router.get("/styles", response_model=list[CategoryOut])
def get_styles(db: Session = Depends(get_db),
               _=Depends(get_current_admin)):
    return get_all(Style, db)

@router.post("/styles", response_model=CategoryOut)
def add_style(body: CategoryBase, db: Session = Depends(get_db),
              _=Depends(get_current_admin)):
    return add_item(Style, body.name, db)

# ── Finishes ────────────────────────────────────────────
@router.get("/finishes", response_model=list[CategoryOut])
def get_finishes(db: Session = Depends(get_db),
                 _=Depends(get_current_admin)):
    return get_all(Finish, db)

@router.post("/finishes", response_model=CategoryOut)
def add_finish(body: CategoryBase, db: Session = Depends(get_db),
               _=Depends(get_current_admin)):
    return add_item(Finish, body.name, db)

# ── Size Formats ────────────────────────────────────────
@router.get("/sizes", response_model=list[CategoryOut])
def get_sizes(db: Session = Depends(get_db),
              _=Depends(get_current_admin)):
    return get_all(SizeFormat, db)

@router.post("/sizes", response_model=CategoryOut)
def add_size(body: CategoryBase, db: Session = Depends(get_db),
             _=Depends(get_current_admin)):
    return add_item(SizeFormat, body.name, db)

# ── Applications ────────────────────────────────────────
@router.get("/applications", response_model=list[CategoryOut])
def get_applications(db: Session = Depends(get_db),
                     _=Depends(get_current_admin)):
    return get_all(Application, db)

@router.post("/applications", response_model=CategoryOut)
def add_application(body: CategoryBase, db: Session = Depends(get_db),
                    _=Depends(get_current_admin)):
    return add_item(Application, body.name, db)

# ── Color Families ──────────────────────────────────────
@router.get("/colors", response_model=list[ColorFamilyOut])
def get_colors(db: Session = Depends(get_db),
               _=Depends(get_current_admin)):
    return db.query(ColorFamily).filter(ColorFamily.is_active == True).all()

@router.post("/colors", response_model=ColorFamilyOut)
def add_color(body: CategoryBase, db: Session = Depends(get_db),
              _=Depends(get_current_admin)):
    return add_item(ColorFamily, body.name, db)

# ── Origins ─────────────────────────────────────────────
@router.get("/origins", response_model=list[CategoryOut])
def get_origins(db: Session = Depends(get_db),
                _=Depends(get_current_admin)):
    return get_all(Origin, db)

@router.post("/origins", response_model=CategoryOut)
def add_origin(body: CategoryBase, db: Session = Depends(get_db),
               _=Depends(get_current_admin)):
    return add_item(Origin, body.name, db)

# ── All Categories in one call (for frontend dropdowns) ─
@router.get("/all")
def get_all_categories(db: Session = Depends(get_db),
                       _=Depends(get_current_admin)):
    return {
        "materials":    get_all(Material, db),
        "styles":       get_all(Style, db),
        "finishes":     get_all(Finish, db),
        "sizes":        get_all(SizeFormat, db),
        "applications": get_all(Application, db),
        "colors":       db.query(ColorFamily)
                          .filter(ColorFamily.is_active == True).all(),
        "origins":      get_all(Origin, db),
    }