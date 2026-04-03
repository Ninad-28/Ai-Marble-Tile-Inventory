from pydantic import BaseModel

class CategoryBase(BaseModel):
    name: str

class CategoryOut(BaseModel):
    id: int
    name: str
    is_active: bool

    class Config:
        from_attributes = True

class ColorFamilyOut(BaseModel):
    id: int
    name: str
    hex_code: str | None
    is_active: bool

    class Config:
        from_attributes = True