from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, Float, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Tile(Base):
    __tablename__ = "tiles"

    id            = Column(Integer, primary_key=True, index=True)
    sku           = Column(String, unique=True, index=True, nullable=False)
    name          = Column(String, nullable=False)
    description   = Column(Text, nullable=True)

    # Category FKs
    material_id   = Column(Integer, ForeignKey("materials.id"), nullable=False)
    style_id      = Column(Integer, ForeignKey("styles.id"), nullable=True)
    finish_id     = Column(Integer, ForeignKey("finishes.id"), nullable=True)
    size_format_id= Column(Integer, ForeignKey("size_formats.id"), nullable=True)
    application_id= Column(Integer, ForeignKey("applications.id"), nullable=True)
    color_family_id=Column(Integer, ForeignKey("color_families.id"), nullable=True)
    origin_id     = Column(Integer, ForeignKey("origins.id"), nullable=True)

    # Physical dimensions
    width_cm      = Column(Float, nullable=True)
    height_cm     = Column(Float, nullable=True)
    thickness_cm  = Column(Float, nullable=True)

    # Pricing
    price_per_sqm = Column(Float, nullable=True)

    # Status
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    material      = relationship("Material")
    style         = relationship("Style")
    finish        = relationship("Finish")
    size_format   = relationship("SizeFormat")
    application   = relationship("Application")
    color_family  = relationship("ColorFamily")
    origin        = relationship("Origin")
    images        = relationship("TileImage", back_populates="tile",
                                 cascade="all, delete-orphan")
    inventory     = relationship("Inventory", back_populates="tile",
                                 uselist=False)
    location      = relationship("WarehouseLocation", back_populates="tile",
                                 uselist=False)