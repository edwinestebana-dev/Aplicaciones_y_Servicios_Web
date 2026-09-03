#print ("Hola mundo")

import json
import csv
import pandas as pd
from pathlib import Path

Base_dir = Path(__file__).parent
ruta_csv = Base_dir / "Datos" / "estudiantes.csv"

with open(ruta_csv, encoding="utf-8") as archivo:
    lector=csv.DictReader(archivo)
    estudiantes = list(lector)

    print(estudiantes[0])  # Imprime el primer estudiante de la lista
    print(f"total leido: {len(estudiantes)}")  # Imprime el total de estudiantes leídos

# Reemplazar ruta del archivo

df = pd.read_csv("Datos/estudiantes.csv")

# Ver primeras filas

print(df.head())

#Tomamos el primer estudiante  de la lista

#estudiante = estudiantes[0]

#estudiante_transformado = {
#   "id": estudiante["codigo"],
#  "nombre_completo": f"{estudiante['nombre']} {estudiante['apellido']}",
# "semestre": int(estudiante["semestre"]),
#"promedio": float(estudiante["promedio"]),
# "estado": "Activo" if estudiante["activo"].lower() == "true" else "Inactivo",
#}

#print(estudiante_transformado)  # Imprime el estudiante transformado

def transformar_estudiante(estudiante: dict) -> dict:
    #Transforma un registro del csv al otro formato
    return {
        "id": estudiante["codigo"],
        "nombre_completo": f"{estudiante['nombre']} {estudiante['apellido']}",
        "semestre": int(estudiante["semestre"]),
        "promedio": float(estudiante["promedio"]),
        "estado": "Activo" if estudiante["activo"].lower() == "true" else "Inactivo",
    }

def serializar_estudiantes(ruta: Path, estudiantes: list[dict]) -> None:
    """Serializa una lista de diccionarios Python a un archivo JSON UTF-8."""
    ruta.parent.mkdir(exist_ok=True)

    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(estudiantes, archivo, indent=2, ensure_ascii=False)

def deserializar_estudiantes(ruta: Path) -> list[dict]:
    """Deserializa un archivo JSON UTF-8 a una lista de diccionarios Python."""
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)

estudiantes_transformados = []

for estudiante in estudiantes:
    estudiante_transformado = transformar_estudiante(estudiante)
    estudiantes_transformados.append(estudiante_transformado)

print(f"Total transformados: {len(estudiantes_transformados)}")#muestra el total de estudiantes transformados
print(estudiantes_transformados[0])# muestra el primer estudiante transformado

RUTA_json = Base_dir / "Salida" / "estudiantes_Resumen.json"

serializar_estudiantes(RUTA_json, estudiantes_transformados)
print(f"Archivo JSON generado en: {RUTA_json}")  # Muestra la ruta del archivo JSON generado

estudiantes_recuperados = deserializar_estudiantes(RUTA_json)

print("\nDatos recuperados del archivo JSON:")
print(estudiantes_recuperados[0])  # Muestra el primer estudiante recuperado del archivo JSON
print(f"Total recuperados: {len(estudiantes_recuperados)}")  # Muestra el total de estudiantes recuperados 