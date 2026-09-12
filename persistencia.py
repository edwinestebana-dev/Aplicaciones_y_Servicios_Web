"""Serialización y deserialización JSON, siguiendo el patrón de la práctica anterior."""

from __future__ import annotations

import json
from pathlib import Path


def serializar_json(ruta: Path, datos) -> None:
    """Serializa estructuras de Python a un archivo JSON UTF-8."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)


def deserializar_json(ruta: Path):
    """Deserializa un archivo JSON UTF-8 a estructuras de Python."""
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)
