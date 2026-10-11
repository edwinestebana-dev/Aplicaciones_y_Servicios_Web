import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import medicion, sensor, sensor_magnitud
from app.mqtt.client import BROKER, KEEPALIVE, PORT, crear_cliente

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mqtt.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("mqtt")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranca el cliente MQTT junto con la API y lo detiene al cerrar."""
    cliente = crear_cliente()
    cliente.connect_async(BROKER, PORT, KEEPALIVE)
    cliente.loop_start()
    logger.info("Cliente MQTT iniciado junto con la API")
    yield
    cliente.loop_stop()
    cliente.disconnect()
    logger.info("Cliente MQTT detenido")


app = FastAPI(
    title="API IoT - Taller 2",
    description="Adquisición, validación y consulta de datos IoT (FastAPI, MQTT y PostgreSQL)",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(sensor.router)
app.include_router(sensor_magnitud.router)
app.include_router(medicion.router)