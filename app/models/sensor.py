from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Sensor(Base):
    __tablename__ = "sensores"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    categoria = Column(String(30), nullable=False)
    ubicacion = Column(String(100), nullable=False)
    activo = Column(Boolean, nullable=False)
    fecha_registro = Column(DateTime(timezone=True), nullable=False)

    magnitudes = relationship("SensorMagnitud", back_populates="sensor")