"""Cliente HTTP para registrar y consultar mediciones en la API institucional."""

from __future__ import annotations

import time
from typing import Any

import requests


MAX_INTENTOS = 3
TIMEOUT_SEGUNDOS = 8
ESPERA_REINTENTO = 0.4


class ResultadoHttp:
    """Resultado interpretado de una operación HTTP."""

    def __init__(
        self,
        categoria: str,
        codigo: int | None = None,
        cuerpo: Any = None,
        mensaje: str = "",
        intentos: int = 1,
    ) -> None:
        self.categoria = categoria
        self.codigo = codigo
        self.cuerpo = cuerpo
        self.mensaje = mensaje
        self.intentos = intentos


def _interpretar_cuerpo(respuesta: requests.Response) -> Any:
    try:
        return respuesta.json()
    except ValueError:
        texto = (respuesta.text or "").strip()
        return {"respuesta_no_json": texto[:500]}


def _es_reintentable(exc: Exception | None, codigo: int | None) -> bool:
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if codigo is not None and 500 <= codigo <= 599:
        return True
    return False


def registrar_medicion(url_base: str, equipo: str, medicion: dict) -> ResultadoHttp:
    """Envía una medición con reintentos ante 5xx, timeout o pérdida de conexión."""
    url = f"{url_base.rstrip('/')}/api/v1/mediciones"
    encabezados = {
        "Content-Type": "application/json",
        "X-Equipo": equipo,
    }

    ultimo: ResultadoHttp | None = None
    for intento in range(1, MAX_INTENTOS + 1):
        try:
            respuesta = requests.post(
                url,
                json=medicion,
                headers=encabezados,
                timeout=TIMEOUT_SEGUNDOS,
            )
        except requests.Timeout as exc:
            ultimo = ResultadoHttp(
                categoria="error_comunicacion",
                mensaje=f"Timeout al registrar la medición: {exc}",
                intentos=intento,
            )
            if intento < MAX_INTENTOS:
                time.sleep(ESPERA_REINTENTO)
                continue
            return ultimo
        except requests.ConnectionError as exc:
            ultimo = ResultadoHttp(
                categoria="error_comunicacion",
                mensaje=f"Pérdida de conexión al registrar la medición: {exc}",
                intentos=intento,
            )
            if intento < MAX_INTENTOS:
                time.sleep(ESPERA_REINTENTO)
                continue
            return ultimo
        except requests.RequestException as exc:
            return ResultadoHttp(
                categoria="error_comunicacion",
                mensaje=f"Error HTTP inesperado: {exc}",
                intentos=intento,
            )

        codigo = respuesta.status_code
        cuerpo = _interpretar_cuerpo(respuesta)

        if codigo == 201:
            return ResultadoHttp(
                categoria="aceptado_api",
                codigo=codigo,
                cuerpo=cuerpo,
                mensaje="Registro aceptado por la API",
                intentos=intento,
            )

        if codigo in (400, 409, 422) or 400 <= codigo < 500:
            return ResultadoHttp(
                categoria="rechazado_api",
                codigo=codigo,
                cuerpo=cuerpo,
                mensaje=f"La API rechazó el registro con HTTP {codigo}",
                intentos=intento,
            )

        if 500 <= codigo <= 599:
            ultimo = ResultadoHttp(
                categoria="error_comunicacion",
                codigo=codigo,
                cuerpo=cuerpo,
                mensaje=f"Error transitorio del servidor HTTP {codigo}",
                intentos=intento,
            )
            if intento < MAX_INTENTOS and _es_reintentable(None, codigo):
                time.sleep(ESPERA_REINTENTO)
                continue
            return ultimo

        return ResultadoHttp(
            categoria="error_comunicacion",
            codigo=codigo,
            cuerpo=cuerpo,
            mensaje=f"Código HTTP inesperado {codigo}",
            intentos=intento,
        )

    return ultimo or ResultadoHttp(
        categoria="error_comunicacion",
        mensaje="No fue posible completar el registro",
        intentos=MAX_INTENTOS,
    )


def consultar_mediciones(url_base: str, equipo: str) -> ResultadoHttp:
    """Consulta las mediciones asociadas al equipo."""
    url = f"{url_base.rstrip('/')}/api/v1/mediciones"
    try:
        respuesta = requests.get(
            url,
            params={"equipo": equipo},
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.Timeout as exc:
        return ResultadoHttp(
            categoria="error_comunicacion",
            mensaje=f"Timeout al consultar mediciones: {exc}",
        )
    except requests.ConnectionError as exc:
        return ResultadoHttp(
            categoria="error_comunicacion",
            mensaje=f"Pérdida de conexión al consultar mediciones: {exc}",
        )
    except requests.RequestException as exc:
        return ResultadoHttp(
            categoria="error_comunicacion",
            mensaje=f"Error HTTP inesperado al consultar: {exc}",
        )

    cuerpo = _interpretar_cuerpo(respuesta)
    if respuesta.status_code == 200:
        return ResultadoHttp(
            categoria="consulta_ok",
            codigo=200,
            cuerpo=cuerpo,
            mensaje="Consulta realizada correctamente",
        )

    return ResultadoHttp(
        categoria="error_comunicacion",
        codigo=respuesta.status_code,
        cuerpo=cuerpo,
        mensaje=f"La consulta devolvió HTTP {respuesta.status_code}",
    )
