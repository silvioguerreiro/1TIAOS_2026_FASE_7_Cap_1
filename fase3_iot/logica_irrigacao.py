# -*- coding: utf-8 -*-
"""
fase3_iot/logica_irrigacao.py
=============================
Regra de acionamento automático da bomba de irrigação (Fase 3).

Espelha a lógica embarcada no ESP32 (esp32_irrigacao.ino): decide LIGAR ou
DESLIGAR a bomba a partir do pH, umidade e temperatura, considerando as faixas
ideais da cultura. Retorna uma decisão estruturada + mensagem de diagnóstico.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import settings


@dataclass
class DecisaoIrrigacao:
    bomba_ligada: bool
    motivo: str
    mensagem: str          # texto curto compatível com a coluna MENSAGEM


def decidir_irrigacao(
    ph: float,
    umidade: float,
    temperatura: float,
    cultura: str = settings.CULTURA_PADRAO,
) -> DecisaoIrrigacao:
    """
    Decide o acionamento da bomba.

    Regra (didática, alinhada ao .ino):
      - Se pH FORA da faixa ideal -> NÃO irriga (corrige solo antes). Bomba OFF.
      - Senão, se umidade < limite inferior ideal -> Bomba ON (irrigar).
      - Senão -> Bomba OFF (umidade adequada).
      - Temperatura muito alta reforça a necessidade de irrigação.
    """
    params = settings.CULTURAS.get(cultura, settings.CULTURAS[settings.CULTURA_PADRAO])
    ph_min, ph_max = params["ph_min"], params["ph_max"]
    umi_min = params["umi_min"]
    t_max = params["t_max"]

    # 1) pH fora da faixa -> prioriza correção de solo, não irriga
    if ph < ph_min or ph > ph_max:
        return DecisaoIrrigacao(
            bomba_ligada=False,
            motivo=f"pH {ph:.2f} fora da faixa ideal ({ph_min}-{ph_max})",
            mensagem=f"Bomba=OFF -> pH fora (alvo {ph_min}-{ph_max})",
        )

    # 2) Umidade baixa -> liga a bomba
    if umidade < umi_min:
        reforco = " + calor" if temperatura >= t_max else ""
        return DecisaoIrrigacao(
            bomba_ligada=True,
            motivo=f"Umidade {umidade:.1f}% < {umi_min}%{reforco}",
            mensagem=f"Bomba=ON -> umidade baixa ({umidade:.1f}%)",
        )

    # 3) Condição adequada
    return DecisaoIrrigacao(
        bomba_ligada=False,
        motivo=f"Umidade {umidade:.1f}% adequada e pH ok",
        mensagem=f"Bomba=OFF -> condicao adequada",
    )


def _demo() -> None:
    print("=== Fase 3 — Lógica de irrigação ===")
    casos = [
        (4.6, 43, 28.8),   # pH baixo
        (6.0, 25, 41.0),   # umidade baixa + calor
        (6.2, 45, 27.0),   # ok
    ]
    for ph, umi, temp in casos:
        d = decidir_irrigacao(ph, umi, temp, "Soja")
        print(f"  pH={ph} umi={umi}% T={temp}°C -> {d.mensagem}  [{d.motivo}]")


if __name__ == "__main__":
    _demo()
