import json
import logging
import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from pydantic import ValidationError

from app.crud import medicion as crud_medicion
from app.crud import sensor as crud_sensor
from app.crud import sensor_magnitud as crud_sm
from app.database.connection import SessionLocal
from app.schemas.medicion import MQTTPayload

load_dotenv()

logger = logging.getLogger("mqtt")

BROKER = os.getenv("MQTT_BROKER")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC")
USERNAME = os.getenv("MQTT_USERNAME")
PASSWORD = os.getenv("MQTT_PASSWORD")
KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))


_partes = (TOPIC or "").split("/")
SENSOR_ASIGNADO = _partes[2] if len(_partes) >= 4 else None


def _rechazar(motivo: str) -> tuple[bool, str]:
    logger.warning("MENSAJE RECHAZADO: %s", motivo)
    return False, motivo


def procesar_mensaje(raw: bytes, guardar: bool = True) -> tuple[bool, str]:
    """Valida un mensaje MQTT y, si es válido, lo guarda.

    Devuelve (aceptado, motivo). Con guardar=False solo valida (para pruebas).
    """
    # 1. Decodificar JSON
    try:
        datos = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return _rechazar(f"JSON inválido: {error}")

    # 2. Validar estructura, tipos y timestamp con Pydantic
    try:
        payload = MQTTPayload.model_validate(datos)
    except ValidationError as error:
        detalle = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
            for e in error.errors()
        )
        return _rechazar(f"Estructura inválida: {detalle}")

    db = SessionLocal()
    try:
        # 3. Sensor: existencia, estado y pertenencia al grupo
        sensor = crud_sensor.get_sensor_por_codigo(db, payload.sensor_id)
        if sensor is None:
            return _rechazar(f"Sensor inexistente: '{payload.sensor_id}'")
        if not sensor.activo:
            return _rechazar(f"Sensor inactivo: '{sensor.codigo}'")
        if SENSOR_ASIGNADO and sensor.codigo != SENSOR_ASIGNADO:
            return _rechazar(
                f"El sensor '{sensor.codigo}' no es el asignado ({SENSOR_ASIGNADO})"
            )

        # 4. Magnitud, unidad y rango de cada medición
        magnitudes = {
            m.magnitud: m for m in crud_sm.get_magnitudes_por_sensor(db, sensor.id)
        }
        registros = []
        for nombre, medida in payload.measurements.items():
            config = magnitudes.get(nombre)
            if config is None:
                return _rechazar(
                    f"Magnitud '{nombre}' no pertenece al sensor {sensor.codigo}"
                )
            if medida.unit != config.unidad:
                return _rechazar(
                    f"Unidad incorrecta en '{nombre}': recibida '{medida.unit}', "
                    f"esperada '{config.unidad}'"
                )
            valor = float(medida.value)
            minimo = float(config.valor_minimo)
            maximo = float(config.valor_maximo)
            if not (minimo <= valor <= maximo):
                return _rechazar(
                    f"Valor fuera de rango en '{nombre}': {valor} "
                    f"(permitido {minimo} a {maximo})"
                )
            registros.append((config.id, valor))

        # 5. Guardar solo si todas las magnitudes fueron válidas
        if guardar:
            crud_medicion.crear_mediciones(db, payload.timestamp, registros)
            logger.info(
                "MENSAJE ACEPTADO: %s | %s | %d mediciones guardadas",
                sensor.codigo,
                payload.timestamp.isoformat(),
                len(registros),
            )
        return True, "ok"

    except Exception as error:
        logger.exception("Error inesperado procesando el mensaje")
        return False, f"error inesperado: {error}"
    finally:
        db.close()


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        logger.error("Error de conexión MQTT: %s", reason_code)
        return
    logger.info("Conectado al broker %s:%s", BROKER, PORT)
    client.subscribe(TOPIC)
    logger.info("Suscrito al tópico: %s", TOPIC)


def on_message(client, userdata, message):
    logger.info("Mensaje recibido en %s", message.topic)
    procesar_mensaje(message.payload)


def crear_cliente() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD or "")
    client.on_connect = on_connect
    client.on_message = on_message
    return client


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("mqtt.log", encoding="utf-8"),
        ],
    )
    client = crear_cliente()
    client.connect(BROKER, PORT, KEEPALIVE)
    client.loop_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Cliente MQTT detenido por el usuario")