from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Marble, Granite etc.
    is_active = Column(Boolean, default=True)

class Style(Base):
    __tablename__ = "styles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Veined, Solid etc.
    is_active = Column(Boolean, default=True)

class Finish(Base):
    __tablename__ = "finishes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Polished, Honed etc.
    is_active = Column(Boolean, default=True)

class SizeFormat(Base):
    __tablename__ = "size_formats"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # 60x60, Large Format etc.
    is_active = Column(Boolean, default=True)

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Flooring, Wall etc.
    is_active = Column(Boolean, default=True)

class ColorFamily(Base):
    __tablename__ = "color_families"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # White, Black etc.
    hex_code = Column(String, nullable=True)             # Optional color preview
    is_active = Column(Boolean, default=True)

class Origin(Base):
    __tablename__ = "origins"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Italy, Turkey etc.
    is_active = Column(Boolean, default=True)