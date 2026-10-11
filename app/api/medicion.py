from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import medicion as crud_medicion
from app.crud import sensor as crud_sensor
from app.database.connection import get_db
from app.schemas.medicion import MedicionRead

router = APIRouter(tags=["Mediciones"])

ZONA_COLOMBIA = ZoneInfo("America/Bogota")


def _a_utc(fecha: datetime | None) -> datetime | None:
    """Convierte la fecha recibida a UTC.

    Si llega sin zona horaria, se interpreta como hora de Colombia.
    """
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=ZONA_COLOMBIA)
    return fecha.astimezone(timezone.utc)


def _exigir_sensor(db: Session, sensor_id: int):
    sensor = crud_sensor.get_sensor(db, sensor_id)
    if sensor is None:
        raise HTTPException(
            status_code=404, detail=f"Sensor con id {sensor_id} no encontrado"
        )
    return sensor


@router.get("/mediciones/{medicion_id}", response_model=MedicionRead)
def obtener_medicion(medicion_id: int, db: Session = Depends(get_db)):
    medicion = crud_medicion.get_medicion(db, medicion_id)
    if medicion is None:
        raise HTTPException(
            status_code=404, detail=f"Medición con id {medicion_id} no encontrada"
        )
    return medicion


@router.get("/sensores/{sensor_id}/mediciones", response_model=list[MedicionRead])
def listar_mediciones(
    sensor_id: int,
    magnitud: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limit: int | None = Query(default=None, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    _exigir_sensor(db, sensor_id)

    desde_utc = _a_utc(desde)
    hasta_utc = _a_utc(hasta)
    if desde_utc and hasta_utc and desde_utc > hasta_utc:
        raise HTTPException(
            status_code=400,
            detail="El parámetro 'desde' no puede ser posterior a 'hasta'",
        )

    return crud_medicion.get_mediciones_por_sensor(
        db,
        sensor_id,
        magnitud=magnitud,
        desde=desde_utc,
        hasta=hasta_utc,
        limit=limit,
    )


@router.get("/sensores/{sensor_id}/ultima-medicion", response_model=list[MedicionRead])
def obtener_ultima_medicion(sensor_id: int, db: Session = Depends(get_db)):
    _exigir_sensor(db, sensor_id)
    mediciones = crud_medicion.get_ultima_medicion(db, sensor_id)
    if not mediciones:
        raise HTTPException(
            status_code=404, detail="El sensor aún no tiene mediciones registradas"
        )
    return mediciones