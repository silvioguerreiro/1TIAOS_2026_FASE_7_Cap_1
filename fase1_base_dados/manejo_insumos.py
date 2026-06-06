# -*- coding: utf-8 -*-
"""
fase1_base_dados/manejo_insumos.py
==================================
Manejo / cálculo de insumos (Fase 1).

Calcula a quantidade total de insumo necessária a partir do número de ruas,
comprimento das ruas e dose por metro linear. Importável e executável.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

from config import settings

PRODUTOS = settings.PRODUTOS_INSUMOS


@dataclass
class ResultadoInsumo:
    """Resultado estruturado do cálculo de insumos."""
    produto: str
    num_ruas: int
    comprimento_rua_m: float
    dose_por_metro: float            # mL/m ou g/m
    total_metros_lineares: float
    total_unidade: float             # mL ou g
    total_litros_kg: float           # L ou Kg

    def resumo(self) -> str:
        return (
            f"{self.produto}: {self.total_unidade:,.2f} mL/g "
            f"({self.total_litros_kg:,.3f} L/Kg) "
            f"para {self.total_metros_lineares:,.0f} m lineares"
        )

    def to_dict(self) -> dict:
        return asdict(self)


def calcular_insumo(
    produto: str,
    num_ruas: int,
    comprimento_rua_m: float,
    dose_por_metro: float,
) -> ResultadoInsumo:
    """
    Calcula o total de insumo necessário.

    total_metros = num_ruas * comprimento_rua
    total (mL/g) = total_metros * dose_por_metro
    total (L/Kg) = total (mL/g) / 1000
    """
    if num_ruas < 0 or comprimento_rua_m < 0 or dose_por_metro < 0:
        raise ValueError("Valores de manejo de insumos não podem ser negativos.")

    total_metros = num_ruas * comprimento_rua_m
    total_unidade = total_metros * dose_por_metro
    total_litros_kg = total_unidade / 1000.0

    return ResultadoInsumo(
        produto=produto,
        num_ruas=num_ruas,
        comprimento_rua_m=comprimento_rua_m,
        dose_por_metro=dose_por_metro,
        total_metros_lineares=total_metros,
        total_unidade=round(total_unidade, 2),
        total_litros_kg=round(total_litros_kg, 3),
    )


def _demo() -> None:
    print("=== Fase 1 — Manejo de insumos ===")
    print("Produtos disponíveis:")
    for codigo, nome in PRODUTOS.items():
        print(f"  {codigo}. {nome}")
    r = calcular_insumo(
        produto=PRODUTOS["2"],          # Ureia
        num_ruas=50,
        comprimento_rua_m=120.0,
        dose_por_metro=15.0,            # mL/m
    )
    print("\nExemplo:", r.resumo())


if __name__ == "__main__":
    _demo()
