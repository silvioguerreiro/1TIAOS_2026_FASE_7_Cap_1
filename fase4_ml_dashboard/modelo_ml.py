# -*- coding: utf-8 -*-
"""
fase4_ml_dashboard/modelo_ml.py
===============================
Machine Learning (Fase 4) — modelos preditivos de manejo.

Treina dois regressores Random Forest (scikit-learn) a partir do histórico de
sensores no banco (Fase 2):
  - modelo_umidade -> prevê UMIDADE a partir de N,P,K,PH,AJUSTE_PH,TEMPERATURA_C
  - modelo_ph      -> prevê PH a partir de N,P,K,UMIDADE,TEMPERATURA_C

Salva pipelines (.pkl) e métricas (MAE/MSE/RMSE/R²) em fase4_ml_dashboard/modelos/.
Expõe `treinar_modelos`, `carregar_modelos` e `prever` para o dashboard e o CLI.
"""

from __future__ import annotations

import json
import logging

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import settings
from fase2_banco_dados import db

logger = logging.getLogger("fase4.ml")

FEATURES = {
    "UMIDADE": ["N", "P", "K", "PH", "AJUSTE_PH", "TEMPERATURA_C"],
    "PH": ["N", "P", "K", "UMIDADE", "TEMPERATURA_C"],
}

ARQ_MODELO = {
    "UMIDADE": settings.MODELS_DIR / "modelo_umidade.pkl",
    "PH": settings.MODELS_DIR / "modelo_ph.pkl",
}
ARQ_METRICAS = {
    "UMIDADE": settings.MODELS_DIR / "modelo_umidade_metrics.json",
    "PH": settings.MODELS_DIR / "modelo_ph_metrics.json",
}


# --------------------------------------------------------------------------- #
# Preparação dos dados
# --------------------------------------------------------------------------- #
def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["N", "P", "K", "PH", "AJUSTE_PH", "UMIDADE", "TEMPERATURA_C"]
    df = df.copy()
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
    return df.dropna(subset=cols)


# --------------------------------------------------------------------------- #
# Treino
# --------------------------------------------------------------------------- #
def _treinar_um(df: pd.DataFrame, alvo: str) -> tuple[Pipeline, dict]:
    features = FEATURES[alvo]
    X = df[features]
    y = df[alvo]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("modelo", RandomForestRegressor(
            n_estimators=200, random_state=42, n_jobs=-1
        )),
    ])
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    metricas = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "MSE": float(mse),
        "RMSE": float(np.sqrt(mse)),
        "R2": float(r2_score(y_test, y_pred)),
        "n_treino": int(len(X_train)),
        "n_teste": int(len(X_test)),
    }

    joblib.dump(pipe, ARQ_MODELO[alvo])
    with open(ARQ_METRICAS[alvo], "w", encoding="utf-8") as fh:
        json.dump(metricas, fh, ensure_ascii=False, indent=2)

    logger.info("Modelo %s treinado | R²=%.3f RMSE=%.3f",
                alvo, metricas["R2"], metricas["RMSE"])
    return pipe, metricas


def treinar_modelos(df: pd.DataFrame | None = None) -> dict[str, dict]:
    """Treina os dois modelos e devolve as métricas de cada um."""
    if df is None:
        db.inicializar_banco()
        df = db.listar_leituras()
    df = _preparar(df)

    if len(df) < 20:
        raise RuntimeError(
            f"Poucos registros para treinar ({len(df)}). Colete mais leituras."
        )

    resultado = {}
    for alvo in ("UMIDADE", "PH"):
        _, metricas = _treinar_um(df, alvo)
        resultado[alvo] = metricas
    return resultado


# --------------------------------------------------------------------------- #
# Carga / predição
# --------------------------------------------------------------------------- #
def modelos_existem() -> bool:
    return all(p.exists() for p in ARQ_MODELO.values())


def carregar_modelos(treinar_se_faltar: bool = True):
    """
    Carrega (umidade, ph, metricas_umi, metricas_ph). Treina se não existirem.
    """
    if not modelos_existem():
        if treinar_se_faltar:
            logger.info("Modelos ausentes — treinando agora...")
            treinar_modelos()
        else:
            raise FileNotFoundError("Modelos não treinados. Rode treinar_modelos().")

    modelo_umi = joblib.load(ARQ_MODELO["UMIDADE"])
    modelo_ph = joblib.load(ARQ_MODELO["PH"])
    with open(ARQ_METRICAS["UMIDADE"], encoding="utf-8") as fh:
        met_umi = json.load(fh)
    with open(ARQ_METRICAS["PH"], encoding="utf-8") as fh:
        met_ph = json.load(fh)
    return modelo_umi, modelo_ph, met_umi, met_ph


def prever(
    n: float, p: float, k: float,
    ph_atual: float, ajuste_ph: float,
    umidade_atual: float, temperatura: float,
) -> dict:
    """Faz a predição de umidade e pH para uma condição informada."""
    modelo_umi, modelo_ph, _, _ = carregar_modelos()

    X_umi = pd.DataFrame([{
        "N": n, "P": p, "K": k, "PH": ph_atual,
        "AJUSTE_PH": ajuste_ph, "TEMPERATURA_C": temperatura,
    }])
    X_ph = pd.DataFrame([{
        "N": n, "P": p, "K": k, "UMIDADE": umidade_atual,
        "TEMPERATURA_C": temperatura,
    }])

    return {
        "umidade_prevista": float(modelo_umi.predict(X_umi)[0]),
        "ph_previsto": float(modelo_ph.predict(X_ph)[0]),
    }


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
    print("=== Fase 4 — Treinando modelos de ML ===")
    met = treinar_modelos()
    for alvo, m in met.items():
        print(f"  {alvo}: MAE={m['MAE']:.3f} RMSE={m['RMSE']:.3f} R²={m['R2']:.3f}")
    print("\nExemplo de predição:")
    print(" ", prever(0, 0, 0, ph_atual=5.0, ajuste_ph=0.6,
                       umidade_atual=28, temperatura=39))
