from pydantic import BaseModel, ConfigDict


class SensorMagnitudRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    magnitud: str
    unidad: str
    valor_minimo: float
    valor_maximo: float