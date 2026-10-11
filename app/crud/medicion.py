from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.medicion import Medicion
from app.models.sensor_magnitud import SensorMagnitud


def crear_mediciones(
    db: Session,
    timestamp_utc: datetime,
    registros: list[tuple[int, float]],
) -> list[Medicion]:
    """Guarda varias mediciones en una sola transacción.

    registros: lista de (sensor_magnitud_id, valor).
    Todas conservan el mismo timestamp_utc. Si algo falla, no se guarda ninguna.
    """
    nuevas = [
        Medicion(
            sensor_magnitud_id=sm_id,
            valor=valor,
            timestamp_utc=timestamp_utc,
        )
        for sm_id, valor in registros
    ]
    try:
        db.add_all(nuevas)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return nuevas


def get_medicion(db: Session, medicion_id: int) -> Medicion | None:
    return (
        db.query(Medicion)
        .options(joinedload(Medicion.sensor_magnitud))
        .filter(Medicion.id == medicion_id)
        .first()
    )


def _consulta_base(db: Session, sensor_id: int):
    return (
        db.query(Medicion)
        .join(SensorMagnitud, Medicion.sensor_magnitud_id == SensorMagnitud.id)
        .options(joinedload(Medicion.sensor_magnitud))
        .filter(SensorMagnitud.sensor_id == sensor_id)
    )


def get_mediciones_por_sensor(
    db: Session,
    sensor_id: int,
    magnitud: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limit: int | None = None,
) -> list[Medicion]:
    consulta = _consulta_base(db, sensor_id)

    if magnitud:
        consulta = consulta.filter(SensorMagnitud.magnitud == magnitud)
    if desde:
        consulta = consulta.filter(Medicion.timestamp_utc >= desde)
    if hasta:
        consulta = consulta.filter(Medicion.timestamp_utc <= hasta)

    consulta = consulta.order_by(Medicion.timestamp_utc.desc(), Medicion.id.desc())

    if limit:
        consulta = consulta.limit(limit)

    return consulta.all()


def get_ultima_medicion(db: Session, sensor_id: int) -> list[Medicion]:
    """Devuelve las mediciones del último timestamp registrado (una por magnitud)."""
    ultimo = (
        db.query(Medicion.timestamp_utc)
        .join(SensorMagnitud, Medicion.sensor_magnitud_id == SensorMagnitud.id)
        .filter(SensorMagnitud.sensor_id == sensor_id)
        .order_by(Medicion.timestamp_utc.desc())
        .limit(1)
        .scalar()
    )
    if ultimo is None:
        return []

    return (
        _consulta_base(db, sensor_id)
        .filter(Medicion.timestamp_utc == ultimo)
        .order_by(Medicion.id)
        .all()
    )