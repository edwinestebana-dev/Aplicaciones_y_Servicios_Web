from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class SensorMagnitud(Base):
    __tablename__ = "sensor_magnitudes"

    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensores.id"), nullable=False)
    magnitud = Column(String(50), nullable=False)
    unidad = Column(String(20), nullable=False)
    valor_minimo = Column(Numeric(12, 4), nullable=False)
    valor_maximo = Column(Numeric(12, 4), nullable=False)

    sensor = relationship("Sensor", back_populates="magnitudes")
    mediciones = relationship("Medicion", back_populates="sensor_magnitud")