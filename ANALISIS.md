# Análisis del Taller 1 — Integración de datos

## 1. Diferencias entre los contratos de los proveedores

Los dos proveedores describen el mismo fenómeno meteorológico, pero no comparten ni estructura, ni nombres, ni unidades, ni formato de fecha.

| Aspecto | Proveedor A (JSON) | Proveedor B (CSV `;`) | Contrato institucional |
|---|---|---|---|
| Identificador | `provider_record_id` | `record_code` | No se envía |
| Ciudad | `station.city_name` | `municipality` | `ciudad` (string no vacío) |
| País | `station.country_code` | `country` | `pais` (string no vacío) |
| Latitud | `location.lat` (number) | `latitude_deg` (texto) | `latitud` (−90 a 90) |
| Longitud | `location.lon` (number) | `longitude_deg` (texto) | `longitud` (−180 a 180) |
| Temperatura | `measurements.temperature_f` (°F) | `temp_celsius` (°C) | `temperatura_c` (number) |
| Humedad | `measurements.relative_humidity` (%) | `humidity_pct` (%) | `humedad` (0 a 100) |
| Viento | `measurements.wind_speed_ms` (m/s) | `wind_kmh` (km/h) | `viento_kmh` (≥ 0) |
| Fecha | `observed_at` (ISO 8601) | `measurement_time` (`dd/mm/aaaa HH:MM`) | `fecha_hora` ISO 8601 |
| Origen | `source` = `weather_provider_a` | `origin_code` = `PB` | `proveedor_a` / `proveedor_b` |

El proveedor A entrega un documento anidado; el B, una fila plana. En A los números ya vienen tipados (salvo errores como `"N/A"` o `null`); en B todo llega como texto y hay que convertirlo.

## 2. Transformaciones necesarias

- Mapear nombres y aplanar la jerarquía de A.
- Convertir °F a °C: `(F − 32) × 5/9`.
- Convertir m/s a km/h: `× 3.6`.
- Parsear la fecha de B (`01/09/2026 06:00`) a ISO 8601 con offset de Colombia (`2026-09-01T06:00:00-05:00`).
- Conservar la fecha ISO de A cuando ya es válida.
- Forzar `origen` a los únicos valores institucionales, ignorando `weather_provider_a` y `PB`.
- Convertir textos numéricos de B a `float`.

La serialización y deserialización JSON se implementó con el mismo patrón de la práctica anterior (`json.dump` / `json.load` en UTF-8), para generar `salida/normalizadas.json` y `salida/reporte.json`. El cliente HTTP se apoyó en el uso de `requests`, códigos de estado y `.json()` visto en el cliente de geocodificación.

## 3. Errores encontrados antes de enviar

Se procesaron 400 registros (200 + 200). Antes de cualquier `POST` ocurrieron dos familias de error.

**Errores de normalización (9):** el dato no pudo representarse con el contrato. No se enviaron ni se escribieron en `normalizadas.json`.

| ID | Motivo |
|---|---|
| A-0040 | Falta el campo `observed_at` |
| A-0082 | `temperature_f = "N/A"` |
| A-0150 | Falta `country_code` |
| A-0173 | `temperature_f = null` |
| A-0174 | Fecha `09-XX-2026 25:61` |
| B-0076 | Fecha vacía |
| B-0114 | `temp_celsius = error` |
| B-0146 | Temperatura vacía |
| B-0171 | Fecha `31/13/2026 28:75` |

**Rechazados localmente (11):** sí se normalizaron, quedaron en `normalizadas.json` y no se enviaron.

| ID | Regla incumplida |
|---|---|
| A-0015, B-0004 | Humedad > 100 |
| A-0031, B-0006 | Latitud fuera de [−90, 90] |
| A-0088, B-0115 | Viento negativo |
| A-0136, B-0128 | Ciudad vacía |
| B-0135 | País vacío |
| A-0175, B-0190 | Longitud fuera de [−180, 180] |

Un mismo tipo de defecto se clasifica distinto según si el campo es convertible: país ausente en A-0150 es error de normalización; país presente pero vacío en B-0135 es rechazo local.

## 4. Validación local frente a validación del servidor

La validación local aplica únicamente las reglas publicadas en `CONTRATO_API.md` (rangos, no vacíos, tipos, origen permitido). El servidor valida de nuevo e independiente: puede devolver `400`, `409` o `422` sobre un registro que aquí se consideró válido, por ejemplo por duplicados o por restricciones no documentadas.

En esta ejecución los 380 registros válidos localmente no llegaron a compararse con el servidor porque `URL_BASE` y `EQUIPO` siguen como constantes de configuración. Hasta que el docente entregue esos valores, el cliente registra el fallo como error de comunicación (DNS/conexión), sin reintentar errores `4xx` y con hasta 3 intentos ante `5xx`, timeout o pérdida de conexión.

## 5. Decisión de implementación más importante

Separar **normalización** de **validación de negocio**. Convertir un `"N/A"` a número no es lo mismo que rechazar una humedad de 108.4. Esa separación determina qué entra a `normalizadas.json`, qué se envía y cómo se cuenta cada registro en el reporte. También se conservó un `id_trazabilidad` interno (el identificador original del proveedor) que nunca viaja en el body del `POST`.

Otra decisión práctica: si varios envíos consecutivos fallan por conexión, se dejan de martillar la API y el resto se marca como error de comunicación. El programa no se cae; cada registro queda identificado.

## Evidencia de una ejecución real

Comando: `python integrador.py`

| Indicador | Cantidad |
|---|---:|
| Procesados | 400 |
| Normalizados | 391 |
| Rechazados localmente | 11 |
| Enviados | 380 |
| Aceptados por la API | 0 |
| Rechazados por la API | 0 |
| Errores de comunicación | 380 |

Caso de error de normalización (fragmento de `salida/reporte.json`):

```json
{
  "id_trazabilidad": "A-0082",
  "origen": "proveedor_a",
  "resultado": "error_normalizacion",
  "motivo": "temperatura_c='N/A' no puede convertirse a número"
}
```

Caso de rechazo local:

```json
{
  "id_trazabilidad": "B-0004",
  "origen": "proveedor_b",
  "resultado": "rechazado_localmente",
  "motivo": "humedad debe estar entre 0 y 100"
}
```

Consulta final `GET /api/v1/mediciones?equipo=equipo-01`: no hubo HTTP 200. El cliente recibió un error de resolución de nombre hacia `api-institucional.example.com` y lo registró en `consulta_final` sin abortar el proceso.

Cuando se configuren `URL_BASE` y `EQUIPO` al inicio de `integrador.py`, la misma corrida dejará en el reporte los códigos `201`/`4xx` reales y el cuerpo de la consulta `GET`.
