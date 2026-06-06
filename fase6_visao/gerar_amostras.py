# -*- coding: utf-8 -*-
"""
fase6_visao/gerar_amostras.py
=============================
Gera imagens ILUSTRATIVAS (sintéticas, via PIL) de folhas de lavoura para a
demonstração da Fase 6 (visão computacional). NÃO são fotos reais — são
ilustrações que representam claramente cada condição, para a demo/vídeo:

    lavoura_01_folha_saudavel.jpg
    lavoura_02_praga_lagarta.jpg
    lavoura_03_ferrugem_asiatica.jpg
    lavoura_04_deficiencia_nutricional.jpg

Em PRODUÇÃO, substitua estas imagens por FOTOS REAIS de pragas/doenças e use
um modelo YOLO treinado (best.pt) — o detector (detector_yolo.py) já roda em
modo real quando a Ultralytics está instalada.

Uso:
    python fase6_visao/gerar_amostras.py
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

BASE = Path(__file__).resolve().parent
OUT = BASE / "imagens"
W = H = 760

CORES = {
    "saudavel": ((44, 118, 40), (90, 170, 74)),
    "lagarta": ((52, 124, 46), (96, 166, 74)),
    "ferrugem": ((66, 120, 52), (120, 160, 84)),
    "deficiencia": ((160, 168, 80), (212, 208, 128)),
}


def _fundo() -> Image.Image:
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=(int(233 - 30 * t), int(230 - 33 * t), int(222 - 35 * t)))
    return img


def _mascara(cx, curva, larg, topo, base) -> Image.Image:
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    R, L = [], []
    n = 90
    for i in range(n + 1):
        s = i / n
        y = base + (topo - base) * s
        w = larg * (math.sin(math.pi * s) ** 0.8)
        off = curva * math.sin(math.pi * s)
        R.append((cx + off + w / 2, y))
        L.append((cx + off - w / 2, y))
    d.polygon(R + L[::-1], fill=255)
    return m


def _camada_cor(c1, c2) -> Image.Image:
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(c1[k] * (1 - t) + c2[k] * t) for k in range(3)))
    return img


def _nervuras(d, cx, curva, larg, topo, base, cor, w=4):
    pts = []
    n = 40
    for i in range(n + 1):
        s = i / n
        y = base + (topo - base) * s
        pts.append((cx + curva * math.sin(math.pi * s), y))
    d.line(pts, fill=cor, width=w)
    altura = base - topo
    for k in range(1, 8):
        s = k / 8.5
        y = base + (topo - base) * s
        off = curva * math.sin(math.pi * s)
        ww = larg * (math.sin(math.pi * s) ** 0.8)
        bx = cx + off
        d.line([(bx, y), (bx + ww * 0.45, y - altura * 0.05)], fill=cor, width=max(1, w - 2))
        d.line([(bx, y), (bx - ww * 0.45, y - altura * 0.05)], fill=cor, width=max(1, w - 2))


def _dentro(px, x, y):
    return 0 <= x < W and 0 <= y < H and px[x, y] > 128


def _ferrugem(d, px):
    n = t = 0
    while n < 300 and t < 9000:
        t += 1
        x, y = random.randint(0, W - 1), random.randint(0, H - 1)
        if _dentro(px, x, y):
            r = random.randint(2, 5)
            d.ellipse([x - r - 2, y - r - 2, x + r + 2, y + r + 2], fill=(198, 180, 72))
            d.ellipse([x - r, y - r, x + r, y + r],
                      fill=random.choice([(150, 78, 30), (168, 92, 38), (128, 60, 26)]))
            n += 1


def _buracos(d, px):
    n = t = 0
    while n < 7 and t < 5000:
        t += 1
        x, y = random.randint(40, W - 40), random.randint(160, H - 120)
        if _dentro(px, x, y):
            rad = random.randint(13, 30)
            pts = [(x + rad * random.uniform(0.55, 1.25) * math.cos(math.radians(a)),
                    y + rad * random.uniform(0.55, 1.25) * math.sin(math.radians(a)))
                   for a in range(0, 360, 36)]
            d.polygon(pts, fill=(224, 220, 211))
            d.line(pts + [pts[0]], fill=(120, 82, 42), width=3)
            n += 1


def _lagarta(d, cx, topo, base):
    x0, y0, n = cx - 70, (topo + base) // 2 + 25, 9
    corpo, listra, borda = (158, 186, 62), (98, 132, 38), (72, 96, 26)
    for i in range(n):
        x = x0 + i * 27
        y = y0 + int(24 * math.sin(i * 0.7))
        r = max(10, 17 - abs(i - n // 2))
        d.ellipse([x - r, y - r, x + r, y + r], fill=corpo, outline=borda, width=2)
        d.arc([x - r, y - r, x + r, y + r], 200, 340, fill=listra, width=3)
        d.line([(x, y + r - 2), (x - 5, y + r + 9)], fill=borda, width=2)
    hx = x0 + n * 27
    hy = y0 + int(24 * math.sin(n * 0.7))
    d.ellipse([hx - 13, hy - 13, hx + 13, hy + 13], fill=(116, 146, 44), outline=borda, width=2)
    d.ellipse([hx + 2, hy - 5, hx + 7, hy], fill=(28, 28, 28))
    d.line([(hx + 8, hy - 10), (hx + 16, hy - 22)], fill=borda, width=2)
    d.line([(hx + 11, hy - 7), (hx + 21, hy - 15)], fill=borda, width=2)


def _clorose(d, px, cx, curva, larg, topo, base):
    n = t = 0
    while n < 38 and t < 4500:
        t += 1
        x, y = random.randint(0, W - 1), random.randint(0, H - 1)
        if _dentro(px, x, y):
            r = random.randint(6, 16)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(218, 208, 122))
            n += 1
    for _ in range(70):
        s = random.uniform(0.55, 0.98)
        y = base + (topo - base) * s
        off = curva * math.sin(math.pi * s)
        ww = larg * (math.sin(math.pi * s) ** 0.8)
        x = cx + off + random.choice([-1, 1]) * ww / 2 * random.uniform(0.82, 1.0)
        r = random.randint(3, 7)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(150, 110, 60))


def gerar(condicao: str, seed: int) -> Image.Image:
    random.seed(seed)
    cx, larg, topo, base = W // 2, 320, 110, H - 95
    curva = random.uniform(-22, 22)
    mask = _mascara(cx, curva, larg, topo, base)

    bg = _fundo()
    sombra = Image.new("L", (W, H), 0)
    sombra.paste(mask.filter(ImageFilter.GaussianBlur(16)), (12, 18))
    sombra = sombra.point(lambda p: int(p * 0.40))
    bg = Image.composite(Image.new("RGB", (W, H), (70, 64, 58)), bg, sombra)

    c1, c2 = CORES[condicao]
    img = Image.composite(_camada_cor(c1, c2), bg, mask)
    d = ImageDraw.Draw(img)

    cor_nerv = (74, 130, 56) if condicao == "deficiencia" else (212, 226, 182)
    _nervuras(d, cx, curva, larg, topo, base, cor_nerv, w=4)

    px = mask.load()
    if condicao == "ferrugem":
        _ferrugem(d, px)
    elif condicao == "lagarta":
        _buracos(d, px)
        _lagarta(d, cx, topo, base)
    elif condicao == "deficiencia":
        _clorose(d, px, cx, curva, larg, topo, base)

    d.line([(cx, base), (cx - curva * 0.2, base + 55)], fill=(96, 142, 70), width=9)
    return img.filter(ImageFilter.SMOOTH)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Sobrescreve as 4 imagens existentes (mantém os nomes; não apaga arquivos).
    plano = [
        ("amostra_lavoura_1.jpeg", "saudavel", 11),
        ("amostra_lavoura_2.jpeg", "lagarta", 23),
        ("amostra_lavoura_3.jpeg", "ferrugem", 37),
        ("amostra_lavoura_4.jpeg", "deficiencia", 51),
    ]
    for nome, cond, seed in plano:
        gerar(cond, seed).save(OUT / nome, quality=88)
        print("gerada:", nome)


if __name__ == "__main__":
    main()
