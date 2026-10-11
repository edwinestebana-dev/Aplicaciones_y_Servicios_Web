from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    computed_field,
    field_validator,
)

from app.schemas.sensor_magnitud import SensorMagnitudRead

ZONA_COLOMBIA = ZoneInfo("America/Bogota")


# ---------- Validación del mensaje MQTT ----------

class ValorMedido(BaseModel):
    """Una magnitud dentro del mensaje: {"value": 21.66, "unit": "C"}."""

    value: StrictInt | StrictFloat
    unit: StrictStr


class MQTTPayload(BaseModel):
    """Estructura completa del mensaje que publica el sensor."""

    sensor_id: StrictStr = Field(min_length=1)
    timestamp: datetime
    measurements: dict[str, ValorMedido] = Field(min_length=1)

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_debe_ser_texto(cls, v):
        if not isinstance(v, str):
            raise ValueError("timestamp debe ser un texto en formato ISO 8601")
        return v

    @field_validator("timestamp")
    @classmethod
    def timestamp_debe_tener_zona(cls, v):
        if v.tzinfo is None:
            raise ValueError("timestamp debe incluir zona horaria (por ejemplo 'Z')")
        return v.astimezone(timezone.utc)


# ---------- Respuesta de la API ----------

class MedicionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    valor: float
    timestamp_utc: datetime = Field(exclude=True)
    sensor_magnitud: SensorMagnitudRead

    @computed_field
    @property
    def fecha_hora_colombia(self) -> str:
        local = self.timestamp_utc.astimezone(ZONA_COLOMBIA)
        return local.strftime("%Y-%m-%d %H:%M:%S")