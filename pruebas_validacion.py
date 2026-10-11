import copy
import json
import logging
import sys

from app.mqtt.client import procesar_mensaje

logging.basicConfig(level=logging.WARNING, format="   Motivo: %(message)s", stream=sys.stdout)

BASE = {
    "sensor_id": "WQ-002",
    "timestamp": "2026-10-10T23:46:37Z",
    "measurements": {
        "conductivity": {"value": 832.82, "unit": "uS/cm"},
        "temperature": {"value": 21.66, "unit": "C"},
    },
}


def variante(cambio):
    datos = copy.deepcopy(BASE)
    cambio(datos)
    return json.dumps(datos).encode()


casos = {
    "Mensaje válido (solo se valida, no se guarda)": json.dumps(BASE).encode(),
    "Sensor inexistente": variante(lambda d: d.update(sensor_id="XX-999")),
    "Unidad incorrecta": variante(
        lambda d: d["measurements"]["temperature"].update(unit="F")
    ),
    "Tipo de dato incorrecto": variante(
        lambda d: d["measurements"]["temperature"].update(value="abc")
    ),
    "Magnitud incorrecta": variante(
        lambda d: d["measurements"].update(ph={"value": 7.0, "unit": "pH"})
    ),
    "Timestamp inválido": variante(lambda d: d.update(timestamp="ayer")),
    "Valor fuera de rango": variante(
        lambda d: d["measurements"]["temperature"].update(value=99)
    ),
    "JSON roto": b"{esto no es json",
}

for nombre, raw in casos.items():
    print(f"PRUEBA: {nombre}")
    print(f"   Entrada: {raw.decode()}")
    aceptado, _ = procesar_mensaje(raw, guardar=False)
    print(f"   Resultado: {'ACEPTADO' if aceptado else 'RECHAZADO'}\n")