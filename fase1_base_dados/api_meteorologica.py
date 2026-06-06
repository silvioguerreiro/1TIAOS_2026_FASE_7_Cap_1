# -*- coding: utf-8 -*-
"""
fase1_base_dados/api_meteorologica.py
=====================================
Conexão com API meteorológica pública (Fase 1).

Provider padrão: **Open-Meteo** (gratuito, SEM chave de API).
Provider opcional: **OpenWeatherMap** (precisa de OWM_API_KEY no .env).

Expõe `obter_previsao()` que retorna um dicionário padronizado, incluindo
`prob_chuva_6h` — usado pelo serviço de alertas (Fase 7) para sugerir
"suspender irrigação programada" quando a chuva é muito provável.

Funciona offline: se a rede falhar, cai em um modo SIMULADO determinístico
(não quebra a demo/vídeo).
"""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from config import settings

logger = logging.getLogger("fase1.meteo")

TIMEOUT = 10


# --------------------------------------------------------------------------- #
# Open-Meteo (padrão — sem chave)
# --------------------------------------------------------------------------- #
def _open_meteo(lat: float, lon: float) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability",
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "forecast_days": 1,
        "timezone": "America/Sao_Paulo",
    }
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    dados = resp.json()

    atual = dados.get("current", {})
    horas = dados.get("hourly", {})
    probs = horas.get("precipitation_probability", []) or []

    # Probabilidade máxima de chuva nas próximas 6 horas
    prob_chuva_6h = max(probs[:6]) if probs else 0

    return {
        "provider": "open-meteo",
        "local": settings.FAZENDA_NOME,
        "lat": lat,
        "lon": lon,
        "temperatura_atual": atual.get("temperature_2m"),
        "umidade_atual": atual.get("relative_humidity_2m"),
        "precipitacao_atual_mm": atual.get("precipitation"),
        "prob_chuva_6h": float(prob_chuva_6h),
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "simulado": False,
    }


# --------------------------------------------------------------------------- #
# OpenWeatherMap (opcional — precisa de chave)
# --------------------------------------------------------------------------- #
def _openweathermap(lat: float, lon: float) -> dict:
    if not settings.OWM_API_KEY:
        raise RuntimeError("OWM_API_KEY ausente para o provider OpenWeatherMap.")
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat, "lon": lon,
        "appid": settings.OWM_API_KEY,
        "units": "metric", "lang": "pt_br",
    }
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    dados = resp.json()

    blocos = dados.get("list", [])[:2]   # 2 blocos de 3h = 6h
    prob = max((b.get("pop", 0) * 100 for b in blocos), default=0)
    primeiro = blocos[0] if blocos else {}
    main = primeiro.get("main", {})

    return {
        "provider": "openweathermap",
        "local": dados.get("city", {}).get("name", settings.FAZENDA_NOME),
        "lat": lat, "lon": lon,
        "temperatura_atual": main.get("temp"),
        "umidade_atual": main.get("humidity"),
        "precipitacao_atual_mm": primeiro.get("rain", {}).get("3h", 0),
        "prob_chuva_6h": float(prob),
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "simulado": False,
    }


# --------------------------------------------------------------------------- #
# Modo simulado (fallback offline determinístico)
# --------------------------------------------------------------------------- #
def _simulado(lat: float, lon: float) -> dict:
    # Valor determinístico baseado na hora -> reprodutível no vídeo
    hora = datetime.now().hour
    prob = 85 if hora % 4 == 0 else 35     # ocasionalmente dispara o limiar
    return {
        "provider": "simulado",
        "local": settings.FAZENDA_NOME,
        "lat": lat, "lon": lon,
        "temperatura_atual": 29.5,
        "umidade_atual": 60,
        "precipitacao_atual_mm": 0.0,
        "prob_chuva_6h": float(prob),
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "simulado": True,
    }


# --------------------------------------------------------------------------- #
# API pública do módulo
# --------------------------------------------------------------------------- #
def obter_previsao(
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """
    Retorna a previsão padronizada para a fazenda. Nunca lança exceção de rede:
    em caso de falha, retorna o modo simulado.
    """
    lat = settings.FAZENDA_LAT if lat is None else lat
    lon = settings.FAZENDA_LON if lon is None else lon

    try:
        if settings.METEO_PROVIDER == "owm" and settings.OWM_API_KEY:
            previsao = _openweathermap(lat, lon)
        else:
            previsao = _open_meteo(lat, lon)
        logger.info(
            "Meteo (%s): %s°C, chuva 6h=%.0f%%",
            previsao["provider"], previsao["temperatura_atual"],
            previsao["prob_chuva_6h"],
        )
        return previsao
    except Exception as exc:  # rede indisponível / erro de API
        logger.warning("Falha ao consultar meteo (%s). Usando modo simulado.", exc)
        return _simulado(lat, lon)


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
    p = obter_previsao()
    print("=== Fase 1 — Previsão meteorológica ===")
    for chave, valor in p.items():
        print(f"  {chave}: {valor}")
