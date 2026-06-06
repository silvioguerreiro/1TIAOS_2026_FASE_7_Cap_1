# -*- coding: utf-8 -*-
"""
fase6_visao/detector_yolo.py
============================
Visão computacional com YOLO (Fase 6) — inspeção da saúde da lavoura.

Roda inferência YOLO sobre as imagens estáticas em fase6_visao/imagens/ e
retorna as detecções (classe, confiança, caixa). O resultado de maior confiança
alimenta o serviço de alertas (Fase 7): praga/doença com confiança > 0.6
dispara "inspeção e tratamento fitossanitário".

Modos:
  - REAL: usa Ultralytics YOLO (yolov8n por padrão). Em produção, troque o
    peso por um modelo treinado em pragas/doenças (best.pt).
  - SIMULADO (fallback): se a Ultralytics não estiver instalada, devolve
    detecções determinísticas — a demo/vídeo roda offline sem quebrar.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

from config import settings

logger = logging.getLogger("fase6.yolo")

EXTENSOES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SAIDAS_DIR = settings.BASE_DIR / "fase6_visao" / "saidas"
SAIDAS_DIR.mkdir(parents=True, exist_ok=True)

# Pseudo-classes agronômicas para o modo simulado
_CLASSES_SIM = [
    "folha_saudavel", "praga_lagarta", "ferrugem_asiatica",
    "deficiencia_nutricional", "crescimento_irregular",
]


def _listar_imagens(pasta: Path) -> list[Path]:
    if not pasta.exists():
        return []
    return sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES)


# --------------------------------------------------------------------------- #
# Modo REAL (Ultralytics)
# --------------------------------------------------------------------------- #
def _detectar_real(imagens: list[Path], peso: str, conf: float) -> list[dict]:
    from ultralytics import YOLO  # import tardio (pesado)

    modelo = YOLO(peso)
    deteccoes: list[dict] = []
    for img in imagens:
        resultados = modelo.predict(source=str(img), conf=conf, verbose=False)
        for r in resultados:
            # salva imagem anotada
            destino = SAIDAS_DIR / f"anotada_{img.name}"
            try:
                r.save(filename=str(destino))
            except Exception:
                destino = None
            nomes = r.names
            for box in r.boxes:
                cls_id = int(box.cls[0])
                deteccoes.append({
                    "imagem": img.name,
                    "classe": nomes.get(cls_id, str(cls_id)),
                    "confianca": float(box.conf[0]),
                    "bbox": [float(x) for x in box.xyxy[0].tolist()],
                    "anotada": str(destino) if destino else None,
                    "simulado": False,
                })
    if not deteccoes:
        logger.info("YOLO real não encontrou objetos acima de conf=%.2f.", conf)
    return deteccoes


# --------------------------------------------------------------------------- #
# Modo SIMULADO
# --------------------------------------------------------------------------- #
# Mapeia palavra-chave no nome do arquivo -> (classe, confiança). Assim o
# rótulo simulado bate com o que a imagem mostra (ver fase6_visao/gerar_amostras.py).
_PALAVRAS_CLASSE = {
    "saudavel": ("folha_saudavel", 0.93),
    "lagarta": ("praga_lagarta", 0.82),
    "praga": ("praga_lagarta", 0.82),
    "ferrugem": ("ferrugem_asiatica", 0.71),
    "deficiencia": ("deficiencia_nutricional", 0.68),
    "irregular": ("crescimento_irregular", 0.64),
}
# Nomes genéricos das amostras desta demo (amostra_lavoura_1..4.jpeg).
_MAPA_AMOSTRAS = {
    "amostra_lavoura_1": ("folha_saudavel", 0.93),
    "amostra_lavoura_2": ("praga_lagarta", 0.82),
    "amostra_lavoura_3": ("ferrugem_asiatica", 0.71),
    "amostra_lavoura_4": ("deficiencia_nutricional", 0.68),
}


def _classe_simulada(stem: str):
    """Deriva (classe, confiança) a partir do nome do arquivo; None se não casar."""
    nome = stem.lower()
    for chave, valor in _PALAVRAS_CLASSE.items():
        if chave in nome:
            return valor
    return _MAPA_AMOSTRAS.get(nome)


def _detectar_simulado(imagens: list[Path]) -> list[dict]:
    rng = random.Random(42)  # determinístico (fallback)
    deteccoes = []
    for img in imagens:
        achado = _classe_simulada(img.stem)
        if achado:
            classe, confianca = achado
        else:  # imagem sem pista no nome: rótulo determinístico de fallback
            classe = rng.choice(_CLASSES_SIM)
            confianca = round(rng.uniform(0.45, 0.9), 2)
        deteccoes.append({
            "imagem": img.name,
            "classe": classe,
            "confianca": confianca,
            "bbox": [0, 0, 100, 100],
            "anotada": None,
            "simulado": True,
        })
    return deteccoes


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #
def detectar(
    pasta: Path | None = None,
    peso: str = "yolov8n.pt",
    conf: float = 0.25,
) -> list[dict]:
    """
    Roda a detecção sobre as imagens da pasta. Tenta o modo real (Ultralytics)
    e cai no simulado se a biblioteca/peso não estiverem disponíveis.
    """
    pasta = Path(pasta) if pasta else settings.IMAGENS_DIR
    imagens = _listar_imagens(pasta)
    if not imagens:
        logger.warning("Nenhuma imagem encontrada em %s.", pasta)
        return []

    try:
        import ultralytics  # noqa: F401
        logger.info("Rodando YOLO (Ultralytics) em %d imagens...", len(imagens))
        return _detectar_real(imagens, peso, conf)
    except Exception as exc:
        logger.warning("Ultralytics indisponível (%s). Modo simulado.", exc)
        return _detectar_simulado(imagens)


def resumo_pragas(deteccoes: list[dict]) -> dict:
    """
    Consolida as detecções para o serviço de alertas: identifica a praga/doença
    de maior confiança (ignora classes 'saudável').
    """
    pragas = [
        d for d in deteccoes
        if "saud" not in d["classe"].lower()
    ]
    if not pragas:
        return {"praga_detectada": False, "confianca_praga": 0.0,
                "classe": None, "imagem": None, "total_deteccoes": len(deteccoes)}

    top = max(pragas, key=lambda d: d["confianca"])
    return {
        "praga_detectada": True,
        "confianca_praga": top["confianca"],
        "classe": top["classe"],
        "imagem": top["imagem"],
        "total_deteccoes": len(deteccoes),
    }


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
    print("=== Fase 6 — Detecção YOLO ===")
    dets = detectar()
    for d in dets:
        print(f"  {d['imagem']}: {d['classe']} ({d['confianca']:.2f})"
              f"{' [SIMULADO]' if d['simulado'] else ''}")
    print("\nResumo para alertas:", resumo_pragas(dets))
