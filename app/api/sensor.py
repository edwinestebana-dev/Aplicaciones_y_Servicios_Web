from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sm
from app.database.connection import get_db
from app.schemas.sensor import SensorRead
from app.schemas.sensor_magnitud import SensorMagnitudRead

router = APIRouter(prefix="/sensores", tags=["Sensores"])


@router.get("", response_model=list[SensorRead])
def listar_sensores(db: Session = Depends(get_db)):
    return crud_sensor.get_sensores(db)


# Esta ruta debe ir ANTES de "/{sensor_id}" para que no se confunda con un id.
@router.get("/por-codigo/{codigo}", response_model=SensorRead)
def obtener_sensor_por_codigo(codigo: str, db: Session = Depends(get_db)):
    sensor = crud_sensor.get_sensor_por_codigo(db, codigo)
    if sensor is None:
        raise HTTPException(
            status_code=404, detail=f"Sensor con código '{codigo}' no encontrado"
        )
    return sensor


@router.get("/{sensor_id}", response_model=SensorRead)
def obtener_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = crud_sensor.get_sensor(db, sensor_id)
    if sensor is None:
        raise HTTPException(
            status_code=404, detail=f"Sensor con id {sensor_id} no encontrado"
        )
    return sensor


@router.get("/{sensor_id}/magnitudes", response_model=list[SensorMagnitudRead])
def listar_magnitudes_del_sensor(sensor_id: int, db: Session = Depends(get_db)):
    if crud_sensor.get_sensor(db, sensor_id) is None:
        raise HTTPException(
            status_code=404, detail=f"Sensor con id {sensor_id} no encontrado"
        )
    return crud_sm.get_magnitudes_por_sensor(db, sensor_id)