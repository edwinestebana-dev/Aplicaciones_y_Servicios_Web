"""Normalización de registros de proveedores al contrato institucional."""

from __future__ import annotations

from datetime import datetime
from typing import Any


ORIGENES_PERMITIDOS = {"proveedor_a", "proveedor_b"}
CAMPOS_CONTRATO = (
    "ciudad",
    "pais",
    "latitud",
    "longitud",
    "temperatura_c",
    "humedad",
    "viento_kmh",
    "fecha_hora",
    "origen",
)


class ErrorNormalizacion(Exception):
    """El registro no puede representarse según el contrato institucional."""


def fahrenheit_a_celsius(fahrenheit: float) -> float:
    """Convierte temperatura de Fahrenheit a Celsius."""
    return round((fahrenheit - 32) * 5 / 9, 2)


def ms_a_kmh(metros_por_segundo: float) -> float:
    """Convierte velocidad de m/s a km/h."""
    return round(metros_por_segundo * 3.6, 2)


def a_numero(valor: Any, nombre: str) -> float:
    """Convierte un valor al tipo numérico exigido por el contrato."""
    if valor is None:
        raise ErrorNormalizacion(f"{nombre} está vacío y no puede convertirse a número")
    if isinstance(valor, bool):
        raise ErrorNormalizacion(f"{nombre} no es un número válido")
    if isinstance(valor, (int, float)):
        numero = float(valor)
        if numero != numero:  # NaN
            raise ErrorNormalizacion(f"{nombre} no es un número válido")
        return numero
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            raise ErrorNormalizacion(f"{nombre} está vacío y no puede convertirse a número")
        try:
            return float(texto)
        except ValueError as exc:
            raise ErrorNormalizacion(
                f"{nombre}='{valor}' no puede convertirse a número"
            ) from exc
    raise ErrorNormalizacion(f"{nombre} tiene un tipo no convertible a número")


def a_texto(valor: Any, nombre: str) -> str:
    """Convierte un valor a cadena. None se considera error de normalización."""
    if valor is None:
        raise ErrorNormalizacion(f"{nombre} está vacío y no puede convertirse a texto")
    return str(valor).strip()


def a_iso8601(valor: Any) -> str:
    """Normaliza una fecha/hora a ISO 8601."""
    if valor is None:
        raise ErrorNormalizacion("fecha_hora está vacía y no puede convertirse")
    texto = str(valor).strip()
    if not texto:
        raise ErrorNormalizacion("fecha_hora está vacía y no puede convertirse")

    try:
        datetime.fromisoformat(texto)
        return texto
    except ValueError:
        pass

    for formato in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            fecha = datetime.strptime(texto, formato)
            return fecha.isoformat(timespec="seconds") + "-05:00"
        except ValueError:
            continue

    raise ErrorNormalizacion(f"fecha_hora='{texto}' no es una fecha válida")


def extraer(registro: dict, *claves: str, nombre: str) -> Any:
    """Obtiene un valor anidado; si falta la estructura, es error de normalización."""
    actual: Any = registro
    for clave in claves:
        if not isinstance(actual, dict) or clave not in actual:
            raise ErrorNormalizacion(f"No se encontró el campo {nombre}")
        actual = actual[clave]
    return actual


def cuerpo_contrato(medicion: dict) -> dict:
    """Devuelve únicamente los campos del contrato institucional."""
    return {campo: medicion[campo] for campo in CAMPOS_CONTRATO}


def normalizar_proveedor_a(registro: dict, posicion: int) -> dict:
    """Transforma un registro del proveedor A al contrato institucional."""
    if not isinstance(registro, dict):
        raise ErrorNormalizacion("El registro no es un objeto JSON")

    trazabilidad = a_texto(
        registro.get("provider_record_id") or f"proveedor_a-{posicion}",
        "id_trazabilidad",
    )

    ciudad = a_texto(extraer(registro, "station", "city_name", nombre="ciudad"), "ciudad")
    pais = a_texto(extraer(registro, "station", "country_code", nombre="pais"), "pais")
    latitud = a_numero(extraer(registro, "location", "lat", nombre="latitud"), "latitud")
    longitud = a_numero(extraer(registro, "location", "lon", nombre="longitud"), "longitud")
    temperatura_f = a_numero(
        extraer(registro, "measurements", "temperature_f", nombre="temperatura_c"),
        "temperatura_c",
    )
    humedad = a_numero(
        extraer(registro, "measurements", "relative_humidity", nombre="humedad"),
        "humedad",
    )
    viento_ms = a_numero(
        extraer(registro, "measurements", "wind_speed_ms", nombre="viento_kmh"),
        "viento_kmh",
    )
    fecha_hora = a_iso8601(extraer(registro, "observed_at", nombre="fecha_hora"))

    return {
        "id_trazabilidad": trazabilidad,
        "ciudad": ciudad,
        "pais": pais,
        "latitud": latitud,
        "longitud": longitud,
        "temperatura_c": fahrenheit_a_celsius(temperatura_f),
        "humedad": round(humedad, 2),
        "viento_kmh": ms_a_kmh(viento_ms),
        "fecha_hora": fecha_hora,
        "origen": "proveedor_a",
    }


def normalizar_proveedor_b(registro: dict, posicion: int) -> dict:
    """Transforma un registro del proveedor B al contrato institucional."""
    if not isinstance(registro, dict):
        raise ErrorNormalizacion("La fila CSV no es un registro válido")

    trazabilidad = a_texto(
        registro.get("record_code") or f"proveedor_b-{posicion}",
        "id_trazabilidad",
    )

    ciudad = a_texto(registro.get("municipality"), "ciudad")
    pais = a_texto(registro.get("country"), "pais")
    latitud = a_numero(registro.get("latitude_deg"), "latitud")
    longitud = a_numero(registro.get("longitude_deg"), "longitud")
    temperatura_c = a_numero(registro.get("temp_celsius"), "temperatura_c")
    humedad = a_numero(registro.get("humidity_pct"), "humedad")
    viento_kmh = a_numero(registro.get("wind_kmh"), "viento_kmh")
    fecha_hora = a_iso8601(registro.get("measurement_time"))

    return {
        "id_trazabilidad": trazabilidad,
        "ciudad": ciudad,
        "pais": pais,
        "latitud": latitud,
        "longitud": longitud,
        "temperatura_c": round(temperatura_c, 2),
        "humedad": round(humedad, 2),
        "viento_kmh": round(viento_kmh, 2),
        "fecha_hora": fecha_hora,
        "origen": "proveedor_b",
    }
