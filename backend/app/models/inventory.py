from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Inventory(Base):
    __tablename__ = "inventory"

    id              = Column(Integer, primary_key=True, index=True)
    tile_id         = Column(Integer, ForeignKey("tiles.id"),
                             unique=True, nullable=False)
    quantity        = Column(Integer, default=0)
    unit            = Column(String, default="pieces")  # pieces or sqm
    low_stock_threshold = Column(Integer, default=10)
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    tile            = relationship("Tile", back_populates="inventory")


class WarehouseLocation(Base):
    __tablename__ = "warehouse_locations"

    id          = Column(Integer, primary_key=True, index=True)
    tile_id     = Column(Integer, ForeignKey("tiles.id"),
                         unique=True, nullable=True)
    aisle       = Column(String, nullable=False)   # e.g. "A", "B", "7"
    rack        = Column(String, nullable=False)   # e.g. "Rack-1"
    bin         = Column(String, nullable=False)   # e.g. "Bin-3B"
    notes       = Column(String, nullable=True)
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    tile        = relationship("Tile", back_populates="location")