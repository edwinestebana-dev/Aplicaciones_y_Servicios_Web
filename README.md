# API IoT con FastAPI, MQTT y PostgreSQL — Taller 2

## 1. Información General

| Campo | Valor |
|---|---|
| Proyecto | API para adquisición, validación y consulta de datos IoT |
| Integrantes | Edwin Esteban Arias Escobar |
| Asignatura | Aplicaciones y Servicios Web |
| Programa | Tecnología en Desarrollo de Software |
| Fecha | 10-10-2026 |
| Sensor asignado | WQ-002 (Sensor de conductividad, categoría AGUA, ubicación "Canal de entrada") |
| Tópico MQTT | `iot/sensors/WQ-002/data` |
| Rama de trabajo | `Taller_2` |

## 2. Descripción del Sistema

### Problema resuelto
Una infraestructura IoT publica mediciones por MQTT. La aplicación se suscribe al tópico del sensor asignado, valida cada mensaje, guarda en PostgreSQL únicamente los válidos y expone endpoints REST de consulta.

### Arquitectura

```
Sensor -> Broker MQTT -> Cliente MQTT (suscriptor)
                              |
                      Pydantic (estructura)
                              |
              SQLAlchemy ORM (sensor, magnitud, unidad, rango)
                              |
                         PostgreSQL <- FastAPI <- Cliente HTTP
```

El cliente MQTT arranca junto con FastAPI (evento `lifespan` en `app/main.py`) y corre en un hilo aparte.

### Magnitudes y unidades

| id | Magnitud | Unidad | Mínimo | Máximo |
|---|---|---|---|---|
| 27 | temperature | C | 0 | 50 |
| 28 | conductivity | uS/cm | 0 | 3000 |

### Payload real del sensor
El sensor publica un mensaje cada 5 segundos aproximadamente. Siempre trae las dos magnitudes. El `timestamp` está en UTC (formato ISO 8601 con `Z`) y `value` es numérico.

```json
{
  "sensor_id": "WQ-002",
  "timestamp": "2026-10-10T23:46:37Z",
  "measurements": {
    "conductivity": {"value": 832.82, "unit": "uS/cm"},
    "temperature": {"value": 21.66, "unit": "C"}
  }
}
```

El `sensor_id` del mensaje corresponde al campo `codigo` de la tabla `sensores`, no a su `id` numérico (el sensor WQ-002 tiene `id` 10).

### Datos recolectados
- Mediciones guardadas del sensor: 1112
- Duración de la recolección: 40 minutos

El servicio también publica mensajes inválidos de forma intencional (unidad incorrecta, magnitud que no existe, timestamp inválido, valor fuera de rango y campos ausentes). Se rechazan y quedan registrados en el log.

## 3. Configuración del Entorno

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1      # Windows (PowerShell)
pip install -r requirements.txt
```

Se crea un archivo `.env` en la raíz a partir de `.env.example`. Variables requeridas (sin valores sensibles):

| Variable | Descripción |
|---|---|
| `MQTT_BROKER` | Host del broker MQTT |
| `MQTT_PORT` | Puerto del broker |
| `MQTT_TOPIC` | Tópico del sensor asignado |
| `MQTT_USERNAME`, `MQTT_PASSWORD` | Credenciales MQTT (si aplican) |
| `MQTT_KEEPALIVE` | Segundos de keepalive |
| `DB_HOST`, `DB_PORT`, `DB_NAME` | Conexión a PostgreSQL |
| `DB_USER`, `DB_PASSWORD` | Credenciales de PostgreSQL |

El archivo `.env` está en `.gitignore` y no se sube al repositorio.

Para ejecutar la aplicación (API y cliente MQTT juntos):

```bash
uvicorn app.main:app --reload
```

La documentación interactiva queda en `http://127.0.0.1:8000/docs`.

## 4. Base de Datos

Conexión mediante SQLAlchemy con el driver `psycopg2`, usando las variables de entorno anteriores (`app/database/connection.py`). El catálogo ya existía; la aplicación solo lo consulta y únicamente escribe en `mediciones`.

| Tabla | Uso en la aplicación |
|---|---|
| `sensores` | Solo lectura |
| `sensor_magnitudes` | Solo lectura |
| `mediciones` | Escritura (mediciones válidas) y lectura |

Relaciones implementadas:
- `sensores` 1:N `sensor_magnitudes` (clave foránea `sensor_id`).
- `sensor_magnitudes` 1:N `mediciones` (clave foránea `sensor_magnitud_id`).

Los modelos ORM de `app/models/` replican `data-model.md`. Al momento de la práctica la base tenía 25 sensores (el documento indica 15 en su estado inicial).

## 5. Organización del Código

| Carpeta | Función |
|---|---|
| `schemas/` | Modelos Pydantic: validan el mensaje MQTT y dan forma a las respuestas de la API |
| `models/` | Clases SQLAlchemy ORM que representan las tablas |
| `crud/` | Consultas a la base de datos (solo las operaciones permitidas por entidad) |
| `api/` | Endpoints FastAPI y manejo de errores HTTP |
| `mqtt/` | Cliente MQTT y lógica de validación y almacenamiento de mensajes |
| `database/` | Conexión, sesión y clase base del ORM |

## 6. Endpoints Implementados

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/sensores` | Lista todos los sensores |
| GET | `/sensores/{id}` | Sensor por id |
| GET | `/sensores/por-codigo/{codigo}` | Sensor por código |
| GET | `/sensores/{id}/magnitudes` | Magnitudes de un sensor |
| GET | `/sensor-magnitudes/{id}` | Sensor-magnitud por id |
| GET | `/mediciones/{id}` | Medición por id |
| GET | `/sensores/{id}/mediciones` | Histórico con filtros `magnitud`, `desde`, `hasta` y `limit` (combinables) |
| GET | `/sensores/{id}/ultima-medicion` | Última medición (una por magnitud) |

Notas:
- Las respuestas muestran `fecha_hora_colombia` (hora local) en lugar del timestamp UTC, que se almacena sin modificar.
- Las fechas `desde` y `hasta` que llegan sin zona horaria se interpretan como hora de Colombia.
- `limit` devuelve las últimas N mediciones (ordenadas de la más reciente a la más antigua).

## 7. Evidencias de Funcionamiento

Todas las evidencias están en la carpeta `evidencias/`. Los rechazos de los puntos 4, 6 y 7 provienen del log real del servicio; los puntos 3 y 5 no aparecieron en el log y se evidencian con el script `pruebas_validacion.py`, que simula esos mensajes.

| # | Prueba | Evidencia | Entrada y resultado | Archivo y función |
|---|---|---|---|---|
| 1 | Recepción MQTT | `01_recepcion_mqtt.png` | Mensajes del tópico `iot/sensors/WQ-002/data` | `app/mqtt/client.py` → `on_connect`, `on_message` |
| 2 | Medición válida | `mqtt_aceptados.txt`, `registros_postgresql.txt` | Mensaje válido: 2 filas guardadas en `mediciones` | `app/mqtt/client.py` → `procesar_mensaje`; `app/crud/medicion.py` → `crear_mediciones` |
| 3 | Sensor inexistente | `rechazos_validacion.txt` | `sensor_id` = XX-999: rechazado | `app/mqtt/client.py` → `procesar_mensaje` |
| 4 | Unidad incorrecta | `mqtt_rechazados.txt` | `INVALID_UNIT` en conductivity: rechazado | `app/mqtt/client.py` → `procesar_mensaje` |
| 5 | Tipo de dato incorrecto | `rechazos_validacion.txt` | `value` = "abc": rechazado | `app/schemas/medicion.py` → `ValorMedido` |
| 6 | Magnitud incorrecta | `mqtt_rechazados.txt` | Magnitud `humidity` no pertenece al sensor: rechazado | `app/mqtt/client.py` → `procesar_mensaje` |
| 7 | Timestamp inválido | `mqtt_rechazados.txt` | timestamp con formato inválido: rechazado | `app/schemas/medicion.py` → `MQTTPayload` (validadores del timestamp) |
| 8 | Consulta por ID existente | `08_sensor_id_existente.png` | GET `/sensores/10` → 200 | `app/api/sensor.py` → `obtener_sensor` |
| 9 | Consulta por ID inexistente | `09_sensor_id_inexistente.png` | GET `/sensores/9999` → 404 | `app/api/sensor.py` → `obtener_sensor` |
| 10 | Consulta histórica | `10_historico.png` | GET `/sensores/10/mediciones?limit=20` → 200 | `app/api/medicion.py` → `listar_mediciones`; `app/crud/medicion.py` → `get_mediciones_por_sensor` |
| 11 | Rango de fechas | `11_rango_fechas.png` | `desde` y `hasta` → 200 con datos filtrados | `app/api/medicion.py` → `listar_mediciones` |
| 12 | `desde` > `hasta` | `12_desde_mayor_hasta.png` | Rango invertido → 400 | `app/api/medicion.py` → `listar_mediciones` |
| 13 | Validación HTTP incorrecta | `13_validacion_422.png` | GET `/sensores/abc` → 422 | FastAPI (tipo `int` del parámetro) en `app/api/sensor.py` → `obtener_sensor` |
| 14 | Última medición | `14_ultima_medicion.png` | GET `/sensores/10/ultima-medicion` → 200 | `app/api/medicion.py` → `obtener_ultima_medicion`; `app/crud/medicion.py` → `get_ultima_medicion` |
| 15 | Últimas N mediciones | `15_ultimas_n.png` | `limit=5` → 5 registros | `app/api/medicion.py` → `listar_mediciones` |
| 16 | Filtro por magnitud | `16_filtro_magnitud.png` | `magnitud=temperature` → solo temperature | `app/crud/medicion.py` → `get_mediciones_por_sensor` |
| 17 | Claves foráneas | `registros_postgresql.txt`, `08b_magnitudes_del_sensor.png` | Cadena mediciones → sensor_magnitudes → sensores | `app/models/` → `ForeignKey` y `relationship` |
| 18 | Separación de responsabilidades | Estructura del repositorio | Código dividido en `schemas`, `models`, `crud`, `api`, `mqtt` y `database` | Sección 5 |

Los demás rechazos reales registrados (valor fuera de rango y campo `unit` ausente) están en `mqtt_rechazados.txt`.

## 8. Control de Versiones

- Repositorio: https://github.com/edwinestebana-dev/Aplicaciones_y_Servicios_Web (rama `Taller_2`)
- Los commits son descriptivos y están identificados por integrante en el historial de GitHub.
- Aporte de cada integrante:
  - Edwin Esteban Arias Escobar: [todo]
  

## 9. Conclusiones

### Principales aprendizajes
Aprendimos cómo se conectan las partes de una aplicación real: el sensor envía los datos, la aplicación los recibe, revisa que estén bien, los guarda en la base de datos y luego permite consultarlos desde una API. También aprendimos a dividir el código en carpetas, cada una con una tarea clara, y a usar Git y GitHub para guardar el avance.

### Dificultades encontradas
Al principio fue difícil usar Git, porque descargamos el proyecto como archivo comprimido y no se podía subir a GitHub. También costó entender que el código del sensor (WQ-002) no es lo mismo que su número de id en la base de datos. Otra dificultad fue cuidar que las contraseñas no se subieran al repositorio.

### Soluciones aplicadas
Se clono el repositorio correctamente y pase el trabajo a esa carpeta. Revisamos el archivo `.gitignore` para que el archivo `.env` con las contraseñas quedara fuera. Para las validaciones hicimos pruebas con mensajes buenos y malos, hasta comprobar que solo se guardaban los correctos. Además, fuimos subiendo el avance en pasos pequeños.