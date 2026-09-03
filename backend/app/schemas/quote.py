from pydantic import BaseModel
from typing import List

class QuoteItem(BaseModel):
    tile_name: str
    material: str
    sku: str
    quantity: int
    length_cm: float
    width_cm: float
    price_per_sqm: float

class QuoteRequest(BaseModel):
    client_name: str
    company_name: str
    items: List[QuoteItem]