from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base


class QuotationHistory(Base):
    __tablename__ = "quotations_history"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
