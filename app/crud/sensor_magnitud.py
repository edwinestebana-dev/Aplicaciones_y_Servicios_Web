from sqlalchemy.orm import Session

from app.models.sensor_magnitud import SensorMagnitud


def get_sensor_magnitud(db: Session, sensor_magnitud_id: int) -> SensorMagnitud | None:
    return (
        db.query(SensorMagnitud)
        .filter(SensorMagnitud.id == sensor_magnitud_id)
        .first()
    )


def get_magnitudes_por_sensor(db: Session, sensor_id: int) -> list[SensorMagnitud]:
    return (
        db.query(SensorMagnitud)
        .filter(SensorMagnitud.sensor_id == sensor_id)
        .order_by(SensorMagnitud.id)
        .all()
    )