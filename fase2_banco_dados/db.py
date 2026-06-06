# -*- coding: utf-8 -*-
"""
fase2_banco_dados/db.py
=======================
Camada de banco de dados reaproveitável (Fase 2).

- Backend padrão: SQLite (portátil, roda offline).
- Backend opcional: Oracle (DB_BACKEND=oracle no .env), usando oracledb.
- Cria o schema (schema.sql), semeia com dados reais do Sensores_limpo.xlsx
  (gerado no ESP32/Wokwi da Fase 3) e expõe CRUD usado por todas as fases.

Uso rápido:
    from fase2_banco_dados import db
    db.inicializar_banco()                 # cria tabelas + popula se vazio
    df = db.listar_leituras()              # pandas.DataFrame
    db.inserir_leitura({...})              # CREATE
    db.atualizar_leitura(id, {...})        # UPDATE
    db.deletar_leitura(id)                 # DELETE
    stats = db.estatisticas()             # médias gerais
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from config import settings

logger = logging.getLogger("fase2.db")

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# Colunas canônicas da tabela de sensores (ordem de exibição)
COLUNAS = [
    "ID", "DATA_REGISTRO", "N", "P", "K",
    "PH", "AJUSTE_PH", "UMIDADE", "TEMPERATURA_C", "MENSAGEM",
]


# --------------------------------------------------------------------------- #
# Conexão
# --------------------------------------------------------------------------- #
def get_connection():
    """Abre conexão conforme o backend configurado (sqlite | oracle)."""
    if settings.DB_BACKEND == "oracle":
        try:
            import oracledb
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "DB_BACKEND=oracle requer o pacote 'oracledb' (pip install oracledb)."
            ) from exc
        logger.info("Conectando ao Oracle (%s)...", settings.ORACLE_DSN)
        return oracledb.connect(
            user=settings.ORACLE_USER,
            password=settings.ORACLE_PWD,
            dsn=settings.ORACLE_DSN,
        )
    # Padrão: SQLite
    conn = sqlite3.connect(settings.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------------------------------- #
# Inicialização / seed
# --------------------------------------------------------------------------- #
def criar_schema() -> None:
    """Executa o schema.sql (apenas SQLite cria tudo automaticamente)."""
    if settings.DB_BACKEND == "oracle":
        logger.warning(
            "Backend Oracle: crie o schema manualmente via schema.sql (ver notas)."
        )
        return
    conn = get_connection()
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
            conn.executescript(fh.read())
        conn.commit()
        logger.info("Schema SQLite criado/verificado em %s", settings.SQLITE_PATH)
    finally:
        conn.close()


def _tabela_vazia() -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {settings.TABELA_SENSORES}")
        total = cur.fetchone()[0]
        return total == 0
    except Exception:
        return True
    finally:
        conn.close()


def semear_de_xlsx(caminho: Path | None = None) -> int:
    """
    Popula SENSORES_HIST a partir da planilha real (Sensores_limpo.xlsx).
    Gera DATA_REGISTRO sintética (intervalos de 1 min) para habilitar séries
    temporais no dashboard. Retorna o número de linhas inseridas.
    """
    caminho = caminho or settings.SEED_XLSX
    if not Path(caminho).exists():
        logger.warning("Planilha de seed não encontrada: %s", caminho)
        return 0

    df = pd.read_excel(caminho)

    # Normaliza nomes de coluna vindos da planilha
    renomear = {
        "N": "N", "P": "P", "K": "K",
        "pH": "PH", "Ajuste pH": "AJUSTE_PH",
        "Umidade ": "UMIDADE", "Umidade": "UMIDADE",
        "Temperatura C": "TEMPERATURA_C", "Temperatura_C": "TEMPERATURA_C",
        "Mensagem": "MENSAGEM",
    }
    df = df.rename(columns={c: renomear.get(c, c) for c in df.columns})

    base_dt = datetime.now() - timedelta(minutes=len(df))
    registros = []
    for i, row in df.iterrows():
        registros.append((
            (base_dt + timedelta(minutes=int(i))).strftime("%Y-%m-%d %H:%M:%S"),
            int(row.get("N", 0) or 0),
            int(row.get("P", 0) or 0),
            int(row.get("K", 0) or 0),
            float(row.get("PH", 0) or 0),
            float(row.get("AJUSTE_PH", 0) or 0),
            float(row.get("UMIDADE", 0) or 0),
            float(row.get("TEMPERATURA_C", 0) or 0),
            str(row.get("MENSAGEM", "") or ""),
        ))

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany(
            f"""INSERT INTO {settings.TABELA_SENSORES}
                (DATA_REGISTRO, N, P, K, PH, AJUSTE_PH, UMIDADE, TEMPERATURA_C, MENSAGEM)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            registros,
        )
        conn.commit()
        logger.info("Seed concluído: %d registros inseridos.", len(registros))
        return len(registros)
    finally:
        conn.close()


def inicializar_banco(forcar_seed: bool = False) -> dict[str, Any]:
    """
    Cria o schema e, se a tabela estiver vazia (ou forcar_seed=True), popula a
    partir da planilha. Idempotente — pode ser chamada a cada execução.
    """
    criar_schema()
    inseridos = 0
    if forcar_seed or _tabela_vazia():
        inseridos = semear_de_xlsx()
    total = contar_leituras()
    return {"inseridos_agora": inseridos, "total_no_banco": total}


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #
def inserir_leitura(leitura: dict[str, Any]) -> int:
    """CREATE — insere uma leitura de sensor. Retorna o ID gerado."""
    data_reg = leitura.get("DATA_REGISTRO") or datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""INSERT INTO {settings.TABELA_SENSORES}
                (DATA_REGISTRO, N, P, K, PH, AJUSTE_PH, UMIDADE, TEMPERATURA_C, MENSAGEM)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data_reg,
                leitura.get("N", 0), leitura.get("P", 0), leitura.get("K", 0),
                leitura.get("PH"), leitura.get("AJUSTE_PH", 0),
                leitura.get("UMIDADE"), leitura.get("TEMPERATURA_C"),
                leitura.get("MENSAGEM", ""),
            ),
        )
        conn.commit()
        novo_id = cur.lastrowid
        logger.info("Leitura inserida (ID=%s).", novo_id)
        return int(novo_id)
    finally:
        conn.close()


def listar_leituras(limite: int | None = None) -> pd.DataFrame:
    """READ — retorna as leituras como DataFrame, ordenadas por data."""
    conn = get_connection()
    try:
        sql = f"""
            SELECT ID, DATA_REGISTRO, N, P, K, PH, AJUSTE_PH,
                   UMIDADE, TEMPERATURA_C, MENSAGEM
            FROM {settings.TABELA_SENSORES}
            ORDER BY DATA_REGISTRO
        """
        if limite:
            sql += f" LIMIT {int(limite)}"
        df = pd.read_sql_query(sql, conn)
        if not df.empty:
            df["DATA_REGISTRO"] = pd.to_datetime(df["DATA_REGISTRO"], errors="coerce")
        return df
    finally:
        conn.close()


def ultima_leitura() -> dict[str, Any] | None:
    """READ — devolve a leitura mais recente como dict (ou None)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""SELECT ID, DATA_REGISTRO, N, P, K, PH, AJUSTE_PH,
                       UMIDADE, TEMPERATURA_C, MENSAGEM
                FROM {settings.TABELA_SENSORES}
                ORDER BY DATA_REGISTRO DESC LIMIT 1"""
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(COLUNAS, row))
    finally:
        conn.close()


def atualizar_leitura(id_leitura: int, campos: dict[str, Any]) -> bool:
    """UPDATE — atualiza campos de uma leitura. Retorna True se afetou linha."""
    permitidos = {"N", "P", "K", "PH", "AJUSTE_PH", "UMIDADE", "TEMPERATURA_C", "MENSAGEM"}
    sets, valores = [], []
    for chave, valor in campos.items():
        if chave.upper() in permitidos:
            sets.append(f"{chave.upper()} = ?")
            valores.append(valor)
    if not sets:
        return False
    valores.append(id_leitura)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE {settings.TABELA_SENSORES} SET {', '.join(sets)} WHERE ID = ?",
            valores,
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def deletar_leitura(id_leitura: int) -> bool:
    """DELETE — remove uma leitura pelo ID. Retorna True se afetou linha."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"DELETE FROM {settings.TABELA_SENSORES} WHERE ID = ?", (id_leitura,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def contar_leituras() -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {settings.TABELA_SENSORES}")
        return int(cur.fetchone()[0])
    except Exception:
        return 0
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Consultas analíticas (espelham as queries SQL da Fase 3)
# --------------------------------------------------------------------------- #
def estatisticas() -> dict[str, float]:
    """Médias gerais (indicadores sintéticos)."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            f"""SELECT ROUND(AVG(PH),2) PH_MEDIO,
                       ROUND(AVG(UMIDADE),2) UMIDADE_MEDIA,
                       ROUND(AVG(TEMPERATURA_C),2) TEMP_MEDIA,
                       COUNT(*) TOTAL
                FROM {settings.TABELA_SENSORES}""",
            conn,
        )
        return df.iloc[0].to_dict() if not df.empty else {}
    finally:
        conn.close()


def leituras_ph_fora_faixa(ph_min: float = 5.5, ph_max: float = 6.8) -> pd.DataFrame:
    """Leituras com pH fora da faixa ideal (consulta da Fase 3)."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            f"""SELECT ID, DATA_REGISTRO, N, P, K, PH, AJUSTE_PH, MENSAGEM
                FROM {settings.TABELA_SENSORES}
                WHERE PH < ? OR PH > ?
                ORDER BY DATA_REGISTRO""",
            conn, params=(ph_min, ph_max),
        )
    finally:
        conn.close()


def situacoes_emergencia(temp_min: float = 40, umi_max: float = 55) -> pd.DataFrame:
    """Situações de emergência: temperatura alta e umidade baixa simultâneas."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            f"""SELECT ID, DATA_REGISTRO, PH, UMIDADE, TEMPERATURA_C, MENSAGEM
                FROM {settings.TABELA_SENSORES}
                WHERE TEMPERATURA_C >= ? AND UMIDADE < ?
                ORDER BY DATA_REGISTRO""",
            conn, params=(temp_min, umi_max),
        )
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Execução direta: inicializa e mostra um resumo
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
    info = inicializar_banco()
    print("Banco inicializado:", info)
    print("Estatísticas:", estatisticas())
    print("\nÚltimas 5 leituras:")
    print(listar_leituras().tail(5).to_string(index=False))
