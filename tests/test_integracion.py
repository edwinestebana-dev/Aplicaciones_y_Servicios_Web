"""Pruebas automatizadas independientes de la API institucional."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from cliente_http import registrar_medicion
from normalizacion import (
    ErrorNormalizacion,
    fahrenheit_a_celsius,
    ms_a_kmh,
    normalizar_proveedor_a,
    normalizar_proveedor_b,
)
from validacion import ErrorValidacion, validar_medicion


def registro_a(**overrides):
    base = {
        "provider_record_id": "A-TEST",
        "station": {"code": "STA-01", "city_name": "Bogota", "country_code": "CO"},
        "location": {"lat": 4.71, "lon": -74.07},
        "measurements": {
            "temperature_f": 68.0,
            "relative_humidity": 70.0,
            "wind_speed_ms": 5.0,
        },
        "observed_at": "2026-09-01T00:00:00-05:00",
        "source": "weather_provider_a",
    }
    for clave, valor in overrides.items():
        if clave in ("station", "location", "measurements") and isinstance(valor, dict):
            base[clave] = {**base[clave], **valor}
        else:
            base[clave] = valor
    return base


def registro_b(**overrides):
    base = {
        "record_code": "B-TEST",
        "municipality": "Medellin",
        "country": "CO",
        "latitude_deg": "6.25",
        "longitude_deg": "-75.56",
        "temp_celsius": "21.55",
        "humidity_pct": "50.7",
        "wind_kmh": "21.85",
        "measurement_time": "01/09/2026 06:00",
        "origin_code": "PB",
    }
    base.update(overrides)
    return base


def test_transformacion_correcta_proveedor_a():
    """Una transformación correcta: estructura anidada del proveedor A al contrato."""
    medicion = normalizar_proveedor_a(registro_a(), posicion=1)

    assert medicion["ciudad"] == "Bogota"
    assert medicion["pais"] == "CO"
    assert medicion["latitud"] == 4.71
    assert medicion["longitud"] == -74.07
    assert medicion["origen"] == "proveedor_a"
    assert medicion["id_trazabilidad"] == "A-TEST"
    assert set(medicion) >= {
        "ciudad",
        "pais",
        "latitud",
        "longitud",
        "temperatura_c",
        "humedad",
        "viento_kmh",
        "fecha_hora",
        "origen",
    }


def test_conversion_unidades_fahrenheit_y_ms():
    """Conversión de unidades: °F → °C y m/s → km/h."""
    assert fahrenheit_a_celsius(32) == 0.0
    assert fahrenheit_a_celsius(68) == 20.0
    assert ms_a_kmh(1) == 3.6
    assert ms_a_kmh(5) == 18.0

    medicion = normalizar_proveedor_a(registro_a(measurements={"temperature_f": 68.0, "wind_speed_ms": 5.0}), 1)
    assert medicion["temperatura_c"] == 20.0
    assert medicion["viento_kmh"] == 18.0


def test_registro_valido():
    """Un registro válido supera la validación local."""
    medicion = normalizar_proveedor_b(registro_b(), posicion=1)
    validar_medicion(medicion)
    assert medicion["origen"] == "proveedor_b"
    assert medicion["fecha_hora"].startswith("2026-09-01T06:00:00")


def test_registro_invalido_humedad_fuera_de_rango():
    """Un registro normalizable pero inválido: humedad mayor a 100."""
    medicion = normalizar_proveedor_b(registro_b(humidity_pct="117.5"), posicion=1)
    with pytest.raises(ErrorValidacion, match="humedad"):
        validar_medicion(medicion)


def test_caso_limite_temperatura_no_convertible():
    """Caso límite: temperatura 'N/A' produce error de normalización, no de validación."""
    with pytest.raises(ErrorNormalizacion, match="temperatura_c"):
        normalizar_proveedor_a(
            registro_a(measurements={"temperature_f": "N/A"}),
            posicion=1,
        )


def test_caso_limite_latitud_en_el_borde_es_valida():
    """Caso límite: latitud exactamente 90 se acepta; 90.1 se rechaza."""
    en_borde = normalizar_proveedor_b(registro_b(latitude_deg="90"), posicion=1)
    validar_medicion(en_borde)

    fuera = normalizar_proveedor_b(registro_b(latitude_deg="90.1"), posicion=1)
    with pytest.raises(ErrorValidacion, match="latitud"):
        validar_medicion(fuera)


def test_fecha_invalida_es_error_de_normalizacion():
    with pytest.raises(ErrorNormalizacion, match="fecha_hora"):
        normalizar_proveedor_a(registro_a(observed_at="09-XX-2026 25:61"), posicion=1)


def test_no_reintenta_errores_4xx():
    """Las respuestas 4xx no se reintentan automáticamente."""
    respuesta = Mock()
    respuesta.status_code = 422
    respuesta.json.return_value = {"detalle": "datos no aceptados"}
    respuesta.text = ""

    with patch("cliente_http.requests.post", return_value=respuesta) as mock_post:
        resultado = registrar_medicion("https://ejemplo.test", "equipo-01", {"ciudad": "Cali"})

    assert resultado.categoria == "rechazado_api"
    assert resultado.codigo == 422
    assert mock_post.call_count == 1


def test_reintenta_errores_5xx_hasta_tres_intentos():
    respuesta = Mock()
    respuesta.status_code = 503
    respuesta.json.return_value = {"detalle": "no disponible"}
    respuesta.text = ""

    with patch("cliente_http.requests.post", return_value=respuesta) as mock_post:
        with patch("cliente_http.time.sleep"):
            resultado = registrar_medicion("https://ejemplo.test", "equipo-01", {"ciudad": "Cali"})

    assert resultado.categoria == "error_comunicacion"
    assert resultado.codigo == 503
    assert mock_post.call_count == 3


def test_ciudad_vacia_se_normaliza_pero_se_rechaza_localmente():
    medicion = normalizar_proveedor_a(registro_a(station={"city_name": ""}), posicion=1)
    assert medicion["ciudad"] == ""
    with pytest.raises(ErrorValidacion, match="ciudad"):
        validar_medicion(medicion)


def test_fromisoformat_acepta_fecha_ya_iso():
    medicion = normalizar_proveedor_a(registro_a(), posicion=1)
    datetime.fromisoformat(medicion["fecha_hora"])
