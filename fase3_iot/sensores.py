# -*- coding: utf-8 -*-
"""
fase3_iot/sensores.py
=====================
Leitura de sensores (Fase 3) — pH (LDR), umidade/temperatura (DHT22) e
nutrientes N/P/K (botões no ESP32).

Dois modos:
  - SIMULADO (padrão): gera leituras realistas baseadas nas faixas das culturas
    e na estatística do histórico. Ideal para rodar offline / no vídeo.
  - REAL (opcional): lê o Serial do Wokwi/ESP32 via RFC2217 (pyserial), usando
    o mesmo padrão de parsing do coletor original.

A leitura é anotada com a decisão de irrigação (logica_irrigacao) e pode ser
gravada no banco (Fase 2).
"""

from __future__ import annotations

import logging
import random
import re
from datetime import datetime

from config import settings
from fase2_banco_dados import db
from fase3_iot.logica_irrigacao import decidir_irrigacao

logger = logging.getLogger("fase3.sensores")


# --------------------------------------------------------------------------- #
# Modo SIMULADO
# --------------------------------------------------------------------------- #
def gerar_leitura_simulada(cultura: str = settings.CULTURA_PADRAO) -> dict:
    """
    Gera uma leitura plausível. Ocasionalmente produz valores fora da faixa
    (pH ácido, umidade baixa, calor) para exercitar a lógica e os alertas.
    """
    params = settings.CULTURAS.get(cultura, settings.CULTURAS[settings.CULTURA_PADRAO])

    # 25% das vezes força um cenário "crítico" para demonstração
    critico = random.random() < 0.25

    if critico:
        ph = round(random.choice([random.uniform(4.5, 5.4),
                                  random.uniform(7.6, 8.6)]), 2)
        umidade = round(random.uniform(18, 29), 1)
        temperatura = round(random.uniform(38, 45), 1)
    else:
        ph = round(random.uniform(params["ph_min"], params["ph_max"]), 2)
        umidade = round(random.uniform(params["umi_min"], params["umi_max"]), 1)
        temperatura = round(random.uniform(params["t_min"], params["t_max"]), 1)

    n = random.randint(0, 1)
    p = random.randint(0, 1)
    k = random.randint(0, 1)
    ajuste_ph = round(max(0.0, (params["ph_min"] - ph)) + random.uniform(0, 0.6), 2)

    decisao = decidir_irrigacao(ph, umidade, temperatura, cultura)

    return {
        "DATA_REGISTRO": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "N": n, "P": p, "K": k,
        "PH": ph, "AJUSTE_PH": ajuste_ph,
        "UMIDADE": umidade, "TEMPERATURA_C": temperatura,
        "MENSAGEM": decisao.mensagem,
        # campos auxiliares (não persistidos diretamente, úteis no dashboard)
        "_bomba_ligada": decisao.bomba_ligada,
        "_motivo": decisao.motivo,
        "_cultura": cultura,
    }


# --------------------------------------------------------------------------- #
# Modo REAL (Wokwi/ESP32 via Serial RFC2217)
# --------------------------------------------------------------------------- #
_PADRAO_SERIAL = re.compile(
    r"N=(?P<n>\d+)\s+P=(?P<p>\d+)\s+K=(?P<k>\d+).*?"
    r"pH=\s*(?P<ph>[\d\.]+).*?"
    r"Ajuste pH=\s*(?P<ajuste>[-\d\.]+).*?"
    r"Umi=\s*(?P<umi>[\d\.]+).*?"
    r"Temp=\s*(?P<temp>[\d\.]+).*?"
    r"Bomba=(?P<bomba>.+)$"
)


def ler_leitura_real(porta: str = "rfc2217://127.0.0.1:4000", baud: int = 115200) -> dict | None:
    """
    Lê UMA linha válida do Serial do ESP32/Wokwi e devolve a leitura.
    Requer pyserial e o simulador Wokwi rodando (Diagram + RFC2217).
    """
    try:
        import serial
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Modo real requer pyserial (pip install pyserial).") from exc

    ser = serial.serial_for_url(porta, baudrate=baud, timeout=3)
    try:
        for _ in range(50):  # tenta algumas linhas até casar o padrão
            linha = ser.readline().decode(errors="ignore").strip()
            if not linha:
                continue
            m = _PADRAO_SERIAL.search(linha)
            if m:
                d = m.groupdict()
                return {
                    "DATA_REGISTRO": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "N": int(d["n"]), "P": int(d["p"]), "K": int(d["k"]),
                    "PH": float(d["ph"]), "AJUSTE_PH": float(d["ajuste"]),
                    "UMIDADE": float(d["umi"]), "TEMPERATURA_C": float(d["temp"]),
                    "MENSAGEM": "Bomba=" + d["bomba"].strip(),
                }
        return None
    finally:
        ser.close()


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #
def ler_sensores(
    modo: str = "simulado",
    cultura: str = settings.CULTURA_PADRAO,
    salvar_no_banco: bool = True,
) -> dict:
    """
    Lê os sensores no modo escolhido e (opcionalmente) grava no banco.
    Retorna a leitura como dict.
    """
    if modo == "real":
        leitura = ler_leitura_real()
        if leitura is None:
            logger.warning("Sem leitura válida no Serial; gerando simulada.")
            leitura = gerar_leitura_simulada(cultura)
    else:
        leitura = gerar_leitura_simulada(cultura)

    if salvar_no_banco:
        try:
            db.inicializar_banco()
            persistir = {k: v for k, v in leitura.items() if not k.startswith("_")}
            novo_id = db.inserir_leitura(persistir)
            leitura["_id"] = novo_id
        except Exception as exc:  # não derruba a leitura por erro de banco
            logger.error("Falha ao gravar leitura no banco: %s", exc)

    return leitura


def _demo() -> None:
    logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
    print("=== Fase 3 — Leitura de sensores (simulada) ===")
    for _ in range(5):
        leitura = ler_sensores(modo="simulado", salvar_no_banco=False)
        print(
            f"  pH={leitura['PH']:.2f} | Umi={leitura['UMIDADE']:.1f}% | "
            f"T={leitura['TEMPERATURA_C']:.1f}°C | NPK={leitura['N']}{leitura['P']}{leitura['K']} "
            f"| {leitura['MENSAGEM']}"
        )


if __name__ == "__main__":
    _demo()
