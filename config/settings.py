# -*- coding: utf-8 -*-
"""
config/settings.py
==================
Configuração central da Fase 7 — FarmTech Solutions (Grupo 1TIAO).

Tudo que é parametrizável do sistema vive aqui:
- metadados do projeto / grupo;
- caminhos de arquivos (banco, modelos, imagens);
- configuração do banco (SQLite padrão; Oracle opcional via .env);
- configuração da API meteorológica (Open-Meteo, sem chave);
- parâmetros agronômicos por cultura;
- TABELA DE LIMIARES -> AÇÃO CORRETIVA -> CANAL (guia o serviço de alertas);
- configuração da mensageria AWS (SNS), com MODO SIMULADO.

A arquitetura é genérica: para aplicar a outro setor, basta trocar os
parâmetros das culturas e os limiares — o código não muda.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Carregamento opcional do .env (python-dotenv). Se não existir, segue com
# variáveis de ambiente do sistema e/ou os defaults abaixo.
# --------------------------------------------------------------------------- #
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - ambiente sem python-dotenv
    pass


def _env(nome: str, padrao: str = "") -> str:
    """Lê variável de ambiente como string, com valor padrão."""
    return os.getenv(nome, padrao)


def _env_bool(nome: str, padrao: bool = False) -> bool:
    """Lê variável de ambiente como booleano (1/true/yes/on)."""
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "yes", "y", "on", "sim"}


# --------------------------------------------------------------------------- #
# 1. METADADOS DO PROJETO
# --------------------------------------------------------------------------- #
PROJETO = {
    "nome": "FarmTech Solutions — Sistema Integrado de Agronegócio",
    "grupo": "1TIAO",
    "integrantes": [
        "Silvio Prestes Guerreiro Junior — RM567958",
    ],
    "fase": "Fase 7 — Consolidação (Fases 1 a 6) + Dashboard + Mensageria AWS",
    "setor": "Agronegócio (arquitetura genérica e parametrizável)",
}

# --------------------------------------------------------------------------- #
# 2. CAMINHOS (sempre relativos à raiz do projeto, independem do diretório
#    de onde o script é chamado)
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent.parent      # raiz do projeto
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "fase4_ml_dashboard" / "modelos"
IMAGENS_DIR = BASE_DIR / "fase6_visao" / "imagens"
DOCS_DIR = BASE_DIR / "docs"

DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Planilha real exportada do ESP32/Wokwi (Fase 3) — usada para semear o banco.
SEED_XLSX = DATA_DIR / "Sensores_limpo.xlsx"

# --------------------------------------------------------------------------- #
# 3. BANCO DE DADOS
#    Padrão: SQLite (portátil, roda offline). Oracle opcional via .env.
# --------------------------------------------------------------------------- #
DB_BACKEND = _env("DB_BACKEND", "sqlite").lower()       # "sqlite" | "oracle"
# Caminho do arquivo SQLite. Pode ser sobrescrito por .env (SQLITE_PATH),
# útil quando a pasta do projeto está em um drive de rede/sync que não
# suporta o lock de arquivo do SQLite.
SQLITE_PATH = Path(_env("SQLITE_PATH", str(DATA_DIR / "farmtech.db")))

# Oracle (opcional — só usado se DB_BACKEND=oracle)
ORACLE_USER = _env("ORACLE_USER", "")
ORACLE_PWD = _env("ORACLE_PWD", "")
ORACLE_DSN = _env("ORACLE_DSN", "oracle.fiap.com.br:1521/ORCL")

# Nome lógico da tabela de histórico de sensores (igual em ambos backends).
TABELA_SENSORES = "SENSORES_HIST"

# --------------------------------------------------------------------------- #
# 4. API METEOROLÓGICA (Fase 1)
#    Open-Meteo é gratuita e NÃO exige chave -> ideal para demo/vídeo offline.
#    OpenWeatherMap é opcional (precisa de OWM_API_KEY).
# --------------------------------------------------------------------------- #
METEO_PROVIDER = _env("METEO_PROVIDER", "open-meteo").lower()  # "open-meteo" | "owm"
OWM_API_KEY = _env("OWM_API_KEY", "")

# Local padrão: Sorriso/MT (região agrícola). Sobrescrevível por .env.
FAZENDA_LAT = float(_env("FAZENDA_LAT", "-12.5453"))
FAZENDA_LON = float(_env("FAZENDA_LON", "-55.7110"))
FAZENDA_NOME = _env("FAZENDA_NOME", "Fazenda Modelo - Sorriso/MT")

# --------------------------------------------------------------------------- #
# 5. PARÂMETROS AGRONÔMICOS POR CULTURA (valores didáticos)
#    Faixas ideais usadas em recomendações de manejo e nos gráficos.
# --------------------------------------------------------------------------- #
CULTURAS = {
    "Soja": {
        "umi_min": 35, "umi_max": 60,
        "ph_min": 5.5, "ph_max": 6.8,
        "n_min": 30, "p_min": 20, "k_min": 30,
        "t_min": 20, "t_max": 32,
    },
    "Milho": {
        "umi_min": 30, "umi_max": 55,
        "ph_min": 5.8, "ph_max": 7.0,
        "n_min": 40, "p_min": 25, "k_min": 35,
        "t_min": 18, "t_max": 30,
    },
    "Algodão": {
        "umi_min": 25, "umi_max": 45,
        "ph_min": 5.5, "ph_max": 7.0,
        "n_min": 35, "p_min": 20, "k_min": 30,
        "t_min": 22, "t_max": 35,
    },
}
CULTURA_PADRAO = "Soja"

# Produtos para o módulo de manejo de insumos (Fase 1)
PRODUTOS_INSUMOS = {
    "1": "Fosfato",
    "2": "Ureia",
    "3": "Cloreto de Potássio",
    "4": "Calcário",
}

# --------------------------------------------------------------------------- #
# 6. TABELA DE LIMIARES -> AÇÃO CORRETIVA -> CANAL
#    Coração do serviço de mensageria (Fase 7).
#    Cada regra é avaliada por fase7_alertas/alerta_aws.py::avaliar_leitura().
#
#    Campos:
#      id        -> identificador único da regra
#      origem    -> fase/sensor de origem
#      variavel  -> chave da leitura avaliada
#      condicao  -> função (valor) -> bool (True = dispara alerta)
#      descricao -> texto humano do limiar
#      acao      -> ação corretiva sugerida (vai no corpo do alerta)
#      canais    -> lista de canais ["sms", "email"]
#      severidade-> "ALERTA" | "EMERGENCIA"
# --------------------------------------------------------------------------- #
LIMIARES = [
    {
        "id": "UMIDADE_BAIXA",
        "origem": "Fase 3 — Umidade (DHT22)",
        "variavel": "umidade",
        "condicao": lambda v: v is not None and v < 30,
        "descricao": "Umidade do solo < 30%",
        "acao": "Acionar irrigação imediata no setor monitorado.",
        "canais": ["sms", "email"],
        "severidade": "EMERGENCIA",
    },
    {
        "id": "PH_FORA_FAIXA",
        "origem": "Fase 3 — pH (sensor LDR)",
        "variavel": "ph",
        "condicao": lambda v: v is not None and (v < 5.5 or v > 7.5),
        "descricao": "pH do solo < 5.5 ou > 7.5",
        "acao": "Aplicar correção de pH (calcário se ácido / enxofre se alcalino) e verificar solo.",
        "canais": ["email"],
        "severidade": "ALERTA",
    },
    {
        "id": "TEMPERATURA_ALTA",
        "origem": "Fase 3 — Temperatura (DHT22)",
        "variavel": "temperatura",
        "condicao": lambda v: v is not None and v >= 40,
        "descricao": "Temperatura >= 40°C",
        "acao": "Risco de estresse térmico: reforçar irrigação e monitorar a lavoura.",
        "canais": ["sms", "email"],
        "severidade": "EMERGENCIA",
    },
    {
        "id": "CHUVA_ALTA",
        "origem": "Fase 1 — Meteorologia (Open-Meteo)",
        "variavel": "prob_chuva_6h",
        "condicao": lambda v: v is not None and v > 80,
        "descricao": "Probabilidade de chuva > 80% nas próximas 6h",
        "acao": "Suspender irrigação programada para economizar água e evitar encharcamento.",
        "canais": ["email"],
        "severidade": "ALERTA",
    },
    {
        "id": "PRAGA_DETECTADA",
        "origem": "Fase 6 — Visão Computacional (YOLO)",
        "variavel": "confianca_praga",
        "condicao": lambda v: v is not None and v > 0.6,
        "descricao": "Praga/doença detectada com confiança > 0.6",
        "acao": "Inspeção e tratamento fitossanitário no talhão identificado.",
        "canais": ["sms", "email"],
        "severidade": "EMERGENCIA",
    },
]

# --------------------------------------------------------------------------- #
# 7. MENSAGERIA AWS (Fase 7)
#    SNS para SMS e e-mail (via tópico). MODO SIMULADO quando não há credencial.
# --------------------------------------------------------------------------- #
AWS_REGION = _env("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = _env("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = _env("AWS_SECRET_ACCESS_KEY", "")

# Tópico SNS que entrega e-mail (e/ou SMS) aos funcionários inscritos.
SNS_TOPIC_ARN = _env("SNS_TOPIC_ARN", "")
# Destinatários diretos (usados no corpo/log e para SMS direto via SNS Publish).
EMAIL_DEST = _env("EMAIL_DEST", "funcionario@fazenda.com.br")
PHONE_DEST = _env("PHONE_DEST", "+5511999999999")

# Força modo simulado mesmo com credenciais (útil para o vídeo/demo offline).
ALERTA_SIMULADO = _env_bool("ALERTA_SIMULADO", False)


def aws_credenciais_ok() -> bool:
    """Retorna True se há o mínimo para tentar publicar no SNS de verdade."""
    if ALERTA_SIMULADO:
        return False
    tem_chaves = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
    tem_destino = bool(SNS_TOPIC_ARN or PHONE_DEST)
    return tem_chaves and tem_destino


# --------------------------------------------------------------------------- #
# 8. LOGGING
# --------------------------------------------------------------------------- #
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_LEVEL = _env("LOG_LEVEL", "INFO").upper()
