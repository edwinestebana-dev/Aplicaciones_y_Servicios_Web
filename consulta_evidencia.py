from sqlalchemy import func

from app.database.connection import SessionLocal
from app.models.medicion import Medicion
from app.models.sensor import Sensor
from app.models.sensor_magnitud import SensorMagnitud

db = SessionLocal()

total = (
    db.query(func.count(Medicion.id))
    .join(SensorMagnitud, Medicion.sensor_magnitud_id == SensorMagnitud.id)
    .filter(SensorMagnitud.sensor_id == 10)
    .scalar()
)
print(f"Total de mediciones del sensor WQ-002 en PostgreSQL: {total}\n")

filas = (
    db.query(Medicion, SensorMagnitud, Sensor)
    .join(SensorMagnitud, Medicion.sensor_magnitud_id == SensorMagnitud.id)
    .join(Sensor, SensorMagnitud.sensor_id == Sensor.id)
    .filter(Sensor.id == 10)
    .order_by(Medicion.id.desc())
    .limit(6)
    .all()
)
for m, sm, s in filas:
    print(
        f"mediciones.id={m.id} | sensor_magnitud_id={m.sensor_magnitud_id} "
        f"-> sensor_magnitudes.id={sm.id} ({sm.magnitud}, {sm.unidad}) "
        f"| sensor_id={sm.sensor_id} -> sensores.id={s.id} ({s.codigo}) "
        f"| valor={m.valor} | timestamp_utc={m.timestamp_utc}"
    )

db.close()