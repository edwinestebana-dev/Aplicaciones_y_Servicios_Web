"""Lectura de los datasets de los proveedores, sin modificar los archivos originales."""

from __future__ import annotations

import csv
import json
from pathlib import Path


class ErrorLectura(Exception):
    """Fallo controlado al leer un dataset."""


def leer_proveedor_a(ruta: Path) -> list[dict]:
    """Lee todos los registros del JSON del proveedor A."""
    if not ruta.exists():
        raise ErrorLectura(f"No existe el archivo: {ruta}")

    try:
        with open(ruta, encoding="utf-8") as archivo:
            contenido = json.load(archivo)
    except json.JSONDecodeError as exc:
        raise ErrorLectura(f"JSON no interpretable en {ruta}: {exc}") from exc
    except OSError as exc:
        raise ErrorLectura(f"No fue posible leer {ruta}: {exc}") from exc

    registros = contenido.get("records") if isinstance(contenido, dict) else None
    if not isinstance(registros, list):
        raise ErrorLectura(f"El archivo {ruta} no contiene una lista de records")

    return registros


def leer_proveedor_b(ruta: Path) -> list[dict]:
    """Lee todos los registros del CSV del proveedor B."""
    if not ruta.exists():
        raise ErrorLectura(f"No existe el archivo: {ruta}")

    try:
        with open(ruta, encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo, delimiter=";")
            if lector.fieldnames is None:
                raise ErrorLectura(f"El CSV {ruta} no tiene encabezados")
            return list(lector)
    except ErrorLectura:
        raise
    except OSError as exc:
        raise ErrorLectura(f"No fue posible leer {ruta}: {exc}") from exc
    except csv.Error as exc:
        raise ErrorLectura(f"Fila CSV defectuosa en {ruta}: {exc}") from exc
