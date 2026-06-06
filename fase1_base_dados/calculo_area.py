# -*- coding: utf-8 -*-
"""
fase1_base_dados/calculo_area.py
================================
Cálculo de área de plantio (Fase 1).

Refatorado a partir do farm.py original para ser **importável** (funções puras
usadas pelo dashboard e pelo run.py) e também executável via CLI.

Figuras suportadas: retângulo, quadrado, círculo, triângulo.
"""

from __future__ import annotations

import math
from typing import Callable

# Mapa figura -> função de cálculo. Cada função recebe **kwargs nomeados.
_FIGURAS: dict[str, Callable[..., float]] = {
    "retangulo": lambda base, altura: base * altura,
    "quadrado": lambda lado: lado * lado,
    "circulo": lambda raio: math.pi * (raio ** 2),
    "triangulo": lambda base, altura: (base * altura) / 2.0,
}

# Dimensões exigidas por figura (para validação/entrada de dados)
DIMENSOES = {
    "retangulo": ["base", "altura"],
    "quadrado": ["lado"],
    "circulo": ["raio"],
    "triangulo": ["base", "altura"],
}


def calcular_area(figura: str, **dimensoes: float) -> float:
    """
    Calcula a área (m²) para a figura informada.

    Exemplos:
        calcular_area("retangulo", base=100, altura=50) -> 5000.0
        calcular_area("circulo", raio=20)               -> 1256.63
    """
    figura = figura.strip().lower()
    if figura not in _FIGURAS:
        raise ValueError(
            f"Figura inválida: {figura!r}. Use uma de {list(_FIGURAS)}."
        )
    faltando = [d for d in DIMENSOES[figura] if d not in dimensoes]
    if faltando:
        raise ValueError(f"Dimensões faltando para {figura}: {faltando}")
    valor = _FIGURAS[figura](**{d: float(dimensoes[d]) for d in DIMENSOES[figura]})
    return round(valor, 2)


# Atalhos explícitos (compatibilidade com o farm.py original)
def calcular_area_retangulo(base: float, altura: float) -> float:
    return calcular_area("retangulo", base=base, altura=altura)


def calcular_area_quadrado(lado: float) -> float:
    return calcular_area("quadrado", lado=lado)


def calcular_area_circulo(raio: float) -> float:
    return calcular_area("circulo", raio=raio)


def calcular_area_triangulo(base: float, altura: float) -> float:
    return calcular_area("triangulo", base=base, altura=altura)


def _demo() -> None:
    print("=== Fase 1 — Cálculo de área de plantio ===")
    exemplos = [
        ("retangulo", {"base": 120, "altura": 80}),
        ("quadrado", {"lado": 90}),
        ("circulo", {"raio": 30}),
        ("triangulo", {"base": 100, "altura": 60}),
    ]
    for figura, dims in exemplos:
        area = calcular_area(figura, **dims)
        print(f"  {figura.capitalize():10s} {dims} -> {area:,.2f} m²")


if __name__ == "__main__":
    _demo()
