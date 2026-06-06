# -*- coding: utf-8 -*-
"""
fase4_ml_dashboard/graficos.py
==============================
Visualizações (Fase 4).

- Construtores de gráficos Altair usados pelo dashboard (app.py).
- Exportação de um painel-resumo em PNG (matplotlib) para o CLI/docs.

Mantém a lógica de gráficos separada do app.py, facilitando reuso e testes.
"""

from __future__ import annotations

import pandas as pd

try:
    import altair as alt
    _ALT = True
except Exception:  # pragma: no cover
    _ALT = False


# --------------------------------------------------------------------------- #
# Gráficos Altair (para o Streamlit)
# --------------------------------------------------------------------------- #
def serie_temporal(df: pd.DataFrame):
    """Linhas de Umidade, pH e Temperatura ao longo do tempo."""
    base = df.dropna(subset=["DATA_REGISTRO"]).sort_values("DATA_REGISTRO")
    base = base[["DATA_REGISTRO", "UMIDADE", "PH", "TEMPERATURA_C"]].melt(
        "DATA_REGISTRO", var_name="Variável", value_name="Valor"
    )
    return (
        alt.Chart(base)
        .mark_line()
        .encode(
            x=alt.X("DATA_REGISTRO:T", title="Data/Hora"),
            y=alt.Y("Valor:Q", title="Valor"),
            color=alt.Color("Variável:N"),
            tooltip=["DATA_REGISTRO:T", "Variável:N", "Valor:Q"],
        )
        .properties(height=320)
    )


def correlacao(df: pd.DataFrame):
    """Heatmap de correlação entre as variáveis numéricas."""
    cols = ["N", "P", "K", "PH", "AJUSTE_PH", "UMIDADE", "TEMPERATURA_C"]
    corr = df[cols].corr().reset_index().melt("index")
    return (
        alt.Chart(corr)
        .mark_rect()
        .encode(
            x=alt.X("variable:N", title="Variável"),
            y=alt.Y("index:N", title="Variável"),
            color=alt.Color("value:Q", title="Correlação"),
            tooltip=["index", "variable", alt.Tooltip("value:Q", format=".2f")],
        )
        .properties(height=320)
    )


def histograma(df: pd.DataFrame, coluna: str, titulo: str):
    """Histograma de uma variável."""
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{coluna}:Q", bin=alt.Bin(maxbins=30), title=titulo),
            y=alt.Y("count():Q", title="Frequência"),
        )
        .properties(height=250)
    )


def status_bomba(df: pd.DataFrame):
    """Barras com a contagem de bomba ON/OFF a partir da coluna MENSAGEM."""
    d = df.copy()
    d["STATUS_BOMBA"] = d["MENSAGEM"].fillna("").apply(
        lambda x: "ON" if "ON" in str(x).upper() else "OFF"
    )
    cont = d["STATUS_BOMBA"].value_counts().reset_index()
    cont.columns = ["Status", "Quantidade"]
    return (
        alt.Chart(cont)
        .mark_bar()
        .encode(
            x=alt.X("Status:N", title="Status da bomba"),
            y=alt.Y("Quantidade:Q", title="Registros"),
            color="Status:N",
            tooltip=["Status", "Quantidade"],
        )
        .properties(height=260)
    )


# --------------------------------------------------------------------------- #
# Exportação em PNG (matplotlib) — usada pelo CLI/docs
# --------------------------------------------------------------------------- #
def exportar_resumo_png(df: pd.DataFrame, caminho) -> str:
    """
    Gera um painel 2x2 (séries de pH/umidade, histograma de umidade e
    contagem da bomba) e salva como PNG. Retorna o caminho do arquivo.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = df.dropna(subset=["DATA_REGISTRO"]).sort_values("DATA_REGISTRO")
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("FarmTech — Resumo dos Sensores", fontsize=14, fontweight="bold")

    axes[0, 0].plot(d["DATA_REGISTRO"], d["PH"], color="tab:green")
    axes[0, 0].axhspan(5.5, 6.8, color="green", alpha=0.1)
    axes[0, 0].set_title("pH ao longo do tempo")
    axes[0, 0].set_ylabel("pH")

    axes[0, 1].plot(d["DATA_REGISTRO"], d["UMIDADE"], color="tab:blue")
    axes[0, 1].set_title("Umidade ao longo do tempo")
    axes[0, 1].set_ylabel("Umidade (%)")

    axes[1, 0].hist(d["UMIDADE"].dropna(), bins=30, color="tab:cyan")
    axes[1, 0].set_title("Distribuição da umidade")
    axes[1, 0].set_xlabel("Umidade (%)")

    status = d["MENSAGEM"].fillna("").apply(
        lambda x: "ON" if "ON" in str(x).upper() else "OFF"
    ).value_counts()
    axes[1, 1].bar(status.index, status.values, color=["tab:orange", "tab:gray"])
    axes[1, 1].set_title("Acionamentos da bomba")

    for ax in (axes[0, 0], axes[0, 1]):
        ax.tick_params(axis="x", rotation=30, labelsize=8)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(caminho, dpi=120)
    plt.close(fig)
    return str(caminho)
