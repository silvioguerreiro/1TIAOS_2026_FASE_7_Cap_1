# -*- coding: utf-8 -*-
"""
fase7_alertas/alerta_aws.py
===========================
Serviço de mensageria na AWS (Fase 7).

Monitora leituras (Fases 1/3) e resultados da visão (Fase 6); ao ultrapassar os
limiares de config/settings.LIMIARES, dispara alerta por **e-mail e/ou SMS** via
**Amazon SNS** (boto3), sugerindo a ação corretiva.

Recursos:
  - enviar_alerta(origem, leitura, acao, canais, ...) -> publica no SNS.
  - avaliar_leitura(leitura) -> aplica a tabela de limiares e retorna disparos.
  - processar_e_alertar(leitura) -> avalia e envia tudo de uma vez.
  - MODO SIMULADO automático quando não há credenciais AWS (demo offline).
  - Tratamento de exceções, logging e auditoria em ALERTAS_LOG.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from config import settings

logger = logging.getLogger("fase7.alerta")
logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)


# --------------------------------------------------------------------------- #
# Normalização da leitura -> chaves usadas pelos limiares
# --------------------------------------------------------------------------- #
def _normalizar_leitura(leitura: dict) -> dict:
    """
    Aceita leituras no formato do banco (UMIDADE, PH, TEMPERATURA_C) ou já no
    formato dos limiares (umidade, ph, temperatura, prob_chuva_6h, confianca_praga)
    e devolve um dicionário unificado.
    """
    mapa = {
        "UMIDADE": "umidade", "PH": "ph", "TEMPERATURA_C": "temperatura",
        "umidade": "umidade", "ph": "ph", "temperatura": "temperatura",
        "prob_chuva_6h": "prob_chuva_6h", "confianca_praga": "confianca_praga",
    }
    out: dict = {}
    for chave, valor in leitura.items():
        destino = mapa.get(chave)
        if destino and valor is not None:
            try:
                out[destino] = float(valor)
            except (TypeError, ValueError):
                pass
    return out


# --------------------------------------------------------------------------- #
# Avaliação de limiares
# --------------------------------------------------------------------------- #
def avaliar_leitura(leitura: dict) -> list[dict]:
    """
    Aplica todas as regras de settings.LIMIARES à leitura.
    Retorna a lista de regras disparadas (cada uma com o valor que disparou).
    """
    norm = _normalizar_leitura(leitura)
    disparos: list[dict] = []
    for regra in settings.LIMIARES:
        valor = norm.get(regra["variavel"])
        if valor is None:
            continue
        try:
            if regra["condicao"](valor):
                disparos.append({**regra, "valor": valor})
        except Exception as exc:  # regra malformada não derruba o serviço
            logger.error("Erro avaliando regra %s: %s", regra["id"], exc)
    return disparos


# --------------------------------------------------------------------------- #
# Montagem da mensagem
# --------------------------------------------------------------------------- #
def montar_mensagem(origem: str, leitura, acao: str, severidade: str) -> tuple[str, str]:
    assunto = f"[FarmTech][{severidade}] Alerta: {origem}"
    corpo = (
        f"ALERTA FARMTECH SOLUTIONS\n"
        f"-------------------------------------------\n"
        f"Severidade : {severidade}\n"
        f"Origem     : {origem}\n"
        f"Leitura    : {leitura}\n"
        f"Ação sugerida: {acao}\n"
        f"Data/Hora  : {datetime.now():%Y-%m-%d %H:%M:%S}\n"
        f"Fazenda    : {settings.FAZENDA_NOME}\n"
        f"-------------------------------------------\n"
        f"Mensagem automática do sistema de monitoramento."
    )
    return assunto, corpo


# --------------------------------------------------------------------------- #
# Publicação via boto3 / SNS
# --------------------------------------------------------------------------- #
def _cliente_sns():
    import boto3  # import tardio
    return boto3.client(
        "sns",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def _enviar_real(assunto: str, corpo: str, canais: list[str]) -> dict:
    cliente = _cliente_sns()
    resultados = {}

    # E-mail via tópico SNS (assinantes recebem)
    if "email" in canais and settings.SNS_TOPIC_ARN:
        resp = cliente.publish(
            TopicArn=settings.SNS_TOPIC_ARN,
            Subject=assunto[:100],   # SNS limita o Subject a 100 chars
            Message=corpo,
        )
        resultados["email"] = resp.get("MessageId")

    # SMS direto para o número configurado
    if "sms" in canais and settings.PHONE_DEST:
        resp = cliente.publish(
            PhoneNumber=settings.PHONE_DEST,
            Message=f"{assunto}\n{corpo[:280]}",
        )
        resultados["sms"] = resp.get("MessageId")

    return resultados


def _enviar_simulado(assunto: str, corpo: str, canais: list[str]) -> dict:
    print("\n" + "=" * 60)
    print(" MODO SIMULADO — nenhuma mensagem real foi enviada à AWS")
    print("=" * 60)
    print(f" Canais : {', '.join(canais)}")
    print(f" E-mail destino: {settings.EMAIL_DEST}")
    print(f" SMS destino   : {settings.PHONE_DEST}")
    print(f" Assunto: {assunto}")
    print("-" * 60)
    print(corpo)
    print("=" * 60 + "\n")
    return {canal: "SIMULADO" for canal in canais}


# --------------------------------------------------------------------------- #
# API principal
# --------------------------------------------------------------------------- #
def enviar_alerta(
    origem: str,
    leitura,
    acao: str,
    canais: list[str] | None = None,
    severidade: str = "ALERTA",
    regra_id: str = "MANUAL",
) -> dict:
    """
    Envia um alerta pelos canais informados. Usa SNS quando há credenciais;
    caso contrário, modo simulado. Sempre registra em ALERTAS_LOG. Nunca lança:
    em erro, faz fallback para simulado e loga.
    """
    canais = canais or ["email"]
    assunto, corpo = montar_mensagem(origem, leitura, acao, severidade)

    modo = "AWS" if settings.aws_credenciais_ok() else "SIMULADO"
    try:
        if modo == "AWS":
            logger.info("Publicando alerta no SNS (%s)...", canais)
            envio = _enviar_real(assunto, corpo, canais)
            if not envio:  # nada publicado (faltou ARN/telefone) -> simula
                logger.warning("Nada publicado no SNS; caindo para simulado.")
                modo = "SIMULADO"
                envio = _enviar_simulado(assunto, corpo, canais)
        else:
            envio = _enviar_simulado(assunto, corpo, canais)
    except Exception as exc:
        logger.error("Falha ao enviar via AWS (%s). Fallback simulado.", exc)
        modo = "SIMULADO"
        envio = _enviar_simulado(assunto, corpo, canais)

    _registrar_log(origem, regra_id, severidade, leitura, acao, canais, modo)
    return {"modo": modo, "canais": canais, "envio": envio,
            "assunto": assunto, "acao": acao}


def processar_e_alertar(leitura: dict, enviar: bool = True) -> list[dict]:
    """
    Avalia a leitura e dispara um alerta para cada limiar ultrapassado.
    Retorna a lista de resultados (ou apenas as regras, se enviar=False).
    """
    disparos = avaliar_leitura(leitura)
    if not disparos:
        logger.info("Nenhum limiar ultrapassado — sem alertas.")
        return []

    resultados = []
    for regra in disparos:
        if enviar:
            res = enviar_alerta(
                origem=regra["origem"],
                leitura=f"{regra['descricao']} (valor={regra['valor']})",
                acao=regra["acao"],
                canais=regra["canais"],
                severidade=regra["severidade"],
                regra_id=regra["id"],
            )
            resultados.append(res)
        else:
            resultados.append(regra)
    return resultados


# --------------------------------------------------------------------------- #
# Auditoria em ALERTAS_LOG
# --------------------------------------------------------------------------- #
def _registrar_log(origem, regra_id, severidade, leitura, acao, canais, modo) -> None:
    try:
        from fase2_banco_dados import db
        db.criar_schema()
        conn = db.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO ALERTAS_LOG
                   (DATA_ALERTA, ORIGEM, REGRA_ID, SEVERIDADE, LEITURA, ACAO, CANAIS, MODO)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), origem, regra_id,
                 severidade, str(leitura), acao, ",".join(canais), modo),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:  # auditoria não pode derrubar o alerta
        logger.debug("Não foi possível registrar ALERTAS_LOG: %s", exc)


# --------------------------------------------------------------------------- #
# Teste manual
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    print("=== Fase 7 — Teste do serviço de alertas ===")
    print("Credenciais AWS válidas? ", settings.aws_credenciais_ok())

    # 1) Alerta manual (botão "testar disparo")
    enviar_alerta(
        origem="Teste manual (CLI)",
        leitura="umidade=22%",
        acao="Acionar irrigação imediata no setor de teste.",
        canais=["email", "sms"],
        severidade="EMERGENCIA",
        regra_id="TESTE",
    )

    # 2) Avaliação automática de uma leitura crítica
    leitura_critica = {"UMIDADE": 22, "PH": 4.9, "TEMPERATURA_C": 41,
                       "prob_chuva_6h": 90, "confianca_praga": 0.82}
    print(">> Limiares disparados:",
          [d["id"] for d in avaliar_leitura(leitura_critica)])
    processar_e_alertar(leitura_critica)
