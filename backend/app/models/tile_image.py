from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class TileImage(Base):
    __tablename__ = "tile_images"

    id          = Column(Integer, primary_key=True, index=True)
    tile_id     = Column(Integer, ForeignKey("tiles.id"), nullable=False)
    image_url   = Column(String, nullable=False)   # S3 URL
    is_primary  = Column(Boolean, default=False)   # Main display image
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    tile        = relationship("Tile", back_populates="images")
    embedding   = relationship("TileEmbedding", back_populates="image",
                               uselist=False, cascade="all, delete-orphan")


class TileEmbedding(Base):
    __tablename__ = "tile_embeddings"

    id          = Column(Integer, primary_key=True, index=True)
    tile_id     = Column(Integer, ForeignKey("tiles.id"), nullable=False)
    image_id    = Column(Integer, ForeignKey("tile_images.id"), nullable=False)
    embedding   = Column(Text, nullable=False)  # JSON array of floats
    model_version = Column(String, default="clip-base")
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    image       = relationship("TileImage", back_populates="embedding")
    