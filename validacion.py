"""Validación local según las reglas del contrato institucional."""

from __future__ import annotations

from datetime import datetime

from normalizacion import ORIGENES_PERMITIDOS, CAMPOS_CONTRATO


class ErrorValidacion(Exception):
    """El registro está bien representado, pero incumple una regla del contrato."""


def _es_numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def validar_medicion(medicion: dict) -> None:
    """Valida un registro ya normalizado. Lanza ErrorValidacion si incumple el contrato."""
    faltantes = [campo for campo in CAMPOS_CONTRATO if campo not in medicion]
    if faltantes:
        raise ErrorValidacion(f"Faltan campos del contrato: {', '.join(faltantes)}")

    ciudad = medicion["ciudad"]
    if not isinstance(ciudad, str) or not ciudad.strip():
        raise ErrorValidacion("ciudad no puede estar vacía")

    pais = medicion["pais"]
    if not isinstance(pais, str) or not pais.strip():
        raise ErrorValidacion("pais no puede estar vacío")

    latitud = medicion["latitud"]
    if not _es_numero(latitud):
        raise ErrorValidacion("latitud debe ser numérica")
    if not -90 <= float(latitud) <= 90:
        raise ErrorValidacion("latitud debe estar entre -90 y 90")

    longitud = medicion["longitud"]
    if not _es_numero(longitud):
        raise ErrorValidacion("longitud debe ser numérica")
    if not -180 <= float(longitud) <= 180:
        raise ErrorValidacion("longitud debe estar entre -180 y 180")

    temperatura = medicion["temperatura_c"]
    if not _es_numero(temperatura):
        raise ErrorValidacion("temperatura_c debe ser numérica")

    humedad = medicion["humedad"]
    if not _es_numero(humedad):
        raise ErrorValidacion("humedad debe ser numérica")
    if not 0 <= float(humedad) <= 100:
        raise ErrorValidacion("humedad debe estar entre 0 y 100")

    viento = medicion["viento_kmh"]
    if not _es_numero(viento):
        raise ErrorValidacion("viento_kmh debe ser numérico")
    if float(viento) < 0:
        raise ErrorValidacion("viento_kmh debe ser mayor o igual a 0")

    fecha_hora = medicion["fecha_hora"]
    if not isinstance(fecha_hora, str) or not fecha_hora.strip():
        raise ErrorValidacion("fecha_hora no puede estar vacía")
    try:
        datetime.fromisoformat(fecha_hora)
    except ValueError as exc:
        raise ErrorValidacion("fecha_hora no es una fecha y hora válida") from exc

    origen = medicion["origen"]
    if origen not in ORIGENES_PERMITIDOS:
        raise ErrorValidacion(
            f"origen debe ser uno de: {', '.join(sorted(ORIGENES_PERMITIDOS))}"
        )
