"""Cliente integrador de mediciones meteorológicas hacia la API institucional."""

from __future__ import annotations

import sys
from pathlib import Path

from cliente_http import consultar_mediciones, registrar_medicion
from lectura import ErrorLectura, leer_proveedor_a, leer_proveedor_b
from normalizacion import (
    ErrorNormalizacion,
    cuerpo_contrato,
    normalizar_proveedor_a,
    normalizar_proveedor_b,
)
from persistencia import serializar_json
from validacion import ErrorValidacion, validar_medicion

# Configuración del equipo. Ajuste estos valores con los suministrados por el docente.
URL_BASE = "https://api-institucional.example.com"
EQUIPO = "equipo-01"

BASE_DIR = Path(__file__).resolve().parent
RUTA_PROVEEDOR_A = BASE_DIR / "datos" / "proveedor_a.json"
RUTA_PROVEEDOR_B = BASE_DIR / "datos" / "proveedor_b.csv"
RUTA_NORMALIZADAS = BASE_DIR / "salida" / "normalizadas.json"
RUTA_REPORTE = BASE_DIR / "salida" / "reporte.json"

FALLOS_CONSECUTIVOS_PARA_ABORTAR = 5


def _detalle(
    trazabilidad: str,
    origen: str,
    resultado: str,
    motivo: str,
    extra: dict | None = None,
) -> dict:
    item = {
        "id_trazabilidad": trazabilidad,
        "origen": origen,
        "resultado": resultado,
        "motivo": motivo,
    }
    if extra:
        item.update(extra)
    return item


def procesar_registros(registros: list, origen: str, normalizador) -> tuple[list, list]:
    """Normaliza y valida una lista de registros. No envía a la API."""
    normalizadas = []
    detalles = []

    for posicion, registro in enumerate(registros, start=1):
        trazabilidad = f"{origen}-{posicion}"
        try:
            if isinstance(registro, dict):
                trazabilidad = str(
                    registro.get("provider_record_id")
                    or registro.get("record_code")
                    or trazabilidad
                )
            medicion = normalizador(registro, posicion)
            trazabilidad = medicion["id_trazabilidad"]
        except ErrorNormalizacion as exc:
            detalles.append(
                _detalle(trazabilidad, origen, "error_normalizacion", str(exc))
            )
            continue
        except Exception as exc:  # noqa: BLE001 — una fila defectuosa no debe abortar el lote
            detalles.append(
                _detalle(
                    trazabilidad,
                    origen,
                    "error_normalizacion",
                    f"Fila o registro defectuoso: {exc}",
                )
            )
            continue

        try:
            validar_medicion(medicion)
            valido = True
            motivo_validacion = "Cumple las reglas locales del contrato"
        except ErrorValidacion as exc:
            valido = False
            motivo_validacion = str(exc)

        normalizadas.append(medicion)
        detalles.append(
            {
                "id_trazabilidad": trazabilidad,
                "origen": origen,
                "resultado": "pendiente_envio" if valido else "rechazado_localmente",
                "motivo": motivo_validacion,
                "medicion": medicion,
                "valido_localmente": valido,
            }
        )

    return normalizadas, detalles


def enviar_validos(detalles: list[dict], url_base: str, equipo: str) -> None:
    """Envía a la API los registros que superaron la validación local."""
    fallos_consecutivos = 0
    api_disponible = True

    for item in detalles:
        if item["resultado"] != "pendiente_envio":
            continue

        medicion = cuerpo_contrato(item["medicion"])

        if not api_disponible:
            item["resultado"] = "error_comunicacion"
            item["motivo"] = (
                "Envío omitido: la API no respondió en registros anteriores"
            )
            item.pop("medicion", None)
            continue

        resultado = registrar_medicion(url_base, equipo, medicion)
        item["resultado"] = resultado.categoria
        item["motivo"] = resultado.mensaje
        item["http_codigo"] = resultado.codigo
        item["http_cuerpo"] = resultado.cuerpo
        item["intentos"] = resultado.intentos
        item.pop("medicion", None)

        if resultado.categoria == "error_comunicacion":
            fallos_consecutivos += 1
            if fallos_consecutivos >= FALLOS_CONSECUTIVOS_PARA_ABORTAR:
                api_disponible = False
        else:
            fallos_consecutivos = 0


def construir_reporte(procesados: int, detalles: list[dict], consulta) -> dict:
    def contar(resultado: str) -> int:
        return sum(1 for item in detalles if item["resultado"] == resultado)

    aceptados = contar("aceptado_api")
    rechazados_api = contar("rechazado_api")
    errores_com = contar("error_comunicacion")
    rechazados_local = contar("rechazado_localmente")
    errores_norm = contar("error_normalizacion")
    normalizados = procesados - errores_norm
    validos_local = normalizados - rechazados_local
    enviados = aceptados + rechazados_api + errores_com

    consulta_info = {
        "ok": consulta.categoria == "consulta_ok" if consulta else False,
        "codigo": consulta.codigo if consulta else None,
        "mensaje": consulta.mensaje if consulta else "Consulta no realizada",
        "cuerpo": consulta.cuerpo if consulta else None,
    }

    return {
        "resumen": {
            "procesados": procesados,
            "normalizados": normalizados,
            "errores_normalizacion": errores_norm,
            "validos_localmente": validos_local,
            "rechazados_localmente": rechazados_local,
            "enviados": enviados,
            "aceptados_api": aceptados,
            "rechazados_api": rechazados_api,
            "errores_comunicacion": errores_com,
        },
        "consulta_final": consulta_info,
        "detalle": [
            {k: v for k, v in item.items() if k != "valido_localmente"}
            for item in detalles
        ],
    }


def imprimir_resumen(reporte: dict) -> None:
    resumen = reporte["resumen"]
    print("=== Resumen de integración ===")
    for clave, valor in resumen.items():
        print(f"{clave}: {valor}")
    consulta = reporte["consulta_final"]
    print(f"consulta_final: HTTP {consulta.get('codigo')} — {consulta.get('mensaje')}")


def main() -> int:
    try:
        registros_a = leer_proveedor_a(RUTA_PROVEEDOR_A)
        registros_b = leer_proveedor_b(RUTA_PROVEEDOR_B)
    except ErrorLectura as exc:
        print(f"Error de lectura: {exc}")
        return 1

    normalizadas_a, detalles_a = procesar_registros(
        registros_a, "proveedor_a", normalizar_proveedor_a
    )
    normalizadas_b, detalles_b = procesar_registros(
        registros_b, "proveedor_b", normalizar_proveedor_b
    )

    normalizadas = [cuerpo_contrato(item) for item in normalizadas_a + normalizadas_b]
    detalles = detalles_a + detalles_b
    procesados = len(registros_a) + len(registros_b)

    try:
        serializar_json(RUTA_NORMALIZADAS, normalizadas)
    except OSError as exc:
        print(f"No fue posible escribir {RUTA_NORMALIZADAS}: {exc}")
        return 1

    enviar_validos(detalles, URL_BASE, EQUIPO)

    consulta = consultar_mediciones(URL_BASE, EQUIPO)
    reporte = construir_reporte(procesados, detalles, consulta)

    try:
        serializar_json(RUTA_REPORTE, reporte)
    except OSError as exc:
        print(f"No fue posible escribir {RUTA_REPORTE}: {exc}")
        return 1

    imprimir_resumen(reporte)
    print(f"Archivo de normalizadas: {RUTA_NORMALIZADAS}")
    print(f"Archivo de reporte: {RUTA_REPORTE}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — no mostrar traceback en ejecución normal
        print(f"Error no controlado durante la ejecución: {exc}")
        sys.exit(1)
