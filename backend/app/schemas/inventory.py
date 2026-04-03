from pydantic import BaseModel
from typing import Optional

class InventoryUpdate(BaseModel):
    quantity: int
    unit: Optional[str] = "pieces"
    low_stock_threshold: Optional[int] = 10

class InventoryOut(BaseModel):
    id: int
    tile_id: int
    quantity: int
    unit: str
    low_stock_threshold: int

    class Config:
        from_attributes = True

class LocationCreate(BaseModel):
    tile_id: int
    aisle: str
    rack: str
    bin: str
    notes: Optional[str] = None

class LocationUpdate(BaseModel):
    aisle: Optional[str] = None
    rack: Optional[str] = None
    bin: Optional[str] = None
    notes: Optional[str] = None

class LocationOut(BaseModel):
    id: int
    tile_id: Optional[int]
    aisle: str
    rack: str
    bin: str
    notes: Optional[str]

    class Config:
        from_attributes = True