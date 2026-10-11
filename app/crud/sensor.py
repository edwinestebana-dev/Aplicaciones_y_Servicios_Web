from sqlalchemy.orm import Session

from app.models.sensor import Sensor


def get_sensores(db: Session) -> list[Sensor]:
    return db.query(Sensor).order_by(Sensor.id).all()


def get_sensor(db: Session, sensor_id: int) -> Sensor | None:
    return db.query(Sensor).filter(Sensor.id == sensor_id).first()


def get_sensor_por_codigo(db: Session, codigo: str) -> Sensor | None:
    return db.query(Sensor).filter(Sensor.codigo == codigo).first()