from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SensorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    categoria: str
    ubicacion: str
    activo: bool
    fecha_registro: datetime