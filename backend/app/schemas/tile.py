from pydantic import BaseModel
from typing import Optional
from app.schemas.category import CategoryOut, ColorFamilyOut

class TileCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    material_id: int
    style_id: Optional[int] = None
    finish_id: Optional[int] = None
    size_format_id: Optional[int] = None
    application_id: Optional[int] = None
    color_family_id: Optional[int] = None
    origin_id: Optional[int] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    thickness_cm: Optional[float] = None
    price_per_sqm: Optional[float] = None

class TileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    material_id: Optional[int] = None
    style_id: Optional[int] = None
    finish_id: Optional[int] = None
    size_format_id: Optional[int] = None
    application_id: Optional[int] = None
    color_family_id: Optional[int] = None
    origin_id: Optional[int] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    thickness_cm: Optional[float] = None
    price_per_sqm: Optional[float] = None

class TileImageOut(BaseModel):
    id: int
    image_url: str
    is_primary: bool

    class Config:
        from_attributes = True

class TileOut(BaseModel):
    id: int
    sku: str
    name: str
    description: Optional[str]
    width_cm: Optional[float]
    height_cm: Optional[float]
    thickness_cm: Optional[float]
    price_per_sqm: Optional[float]
    is_active: bool
    material: Optional[CategoryOut]
    style: Optional[CategoryOut]
    finish: Optional[CategoryOut]
    size_format: Optional[CategoryOut]
    application: Optional[CategoryOut]
    color_family: Optional[ColorFamilyOut]
    origin: Optional[CategoryOut]
    images: list[TileImageOut] = []

    class Config:
        from_attributes = True