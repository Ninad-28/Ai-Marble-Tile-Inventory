from sqlalchemy import (
    Column, Integer, String,
    DateTime, Float, ForeignKey
)
from sqlalchemy.sql import func
from app.database import Base

class SearchLog(Base):
    __tablename__ = "search_logs"

    id              = Column(Integer, primary_key=True, index=True)
    query_image_url = Column(String, nullable=True)   # uploaded search photo
    matched_tile_id = Column(Integer, ForeignKey("tiles.id"), nullable=True)
    confidence      = Column(Float, nullable=True)    # 0.0 - 1.0
    response_time_ms= Column(Integer, nullable=True)  # milliseconds
    status          = Column(String, default="matched")
                    # matched / low_confidence / no_match
    searched_at     = Column(DateTime(timezone=True), server_default=func.now())