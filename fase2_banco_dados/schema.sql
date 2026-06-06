-- =====================================================================
-- fase2_banco_dados/schema.sql
-- DDL do banco relacional - FarmTech Solutions (Grupo 1TIAO)
-- Dialeto padrão: SQLite. Notas para Oracle ao final.
-- =====================================================================

-- Tabela de culturas (catálogo) -------------------------------------------------
CREATE TABLE IF NOT EXISTS CULTURAS (
    ID            INTEGER PRIMARY KEY AUTOINCREMENT,
    NOME          TEXT    NOT NULL UNIQUE,
    UMI_MIN       REAL,
    UMI_MAX       REAL,
    PH_MIN        REAL,
    PH_MAX        REAL,
    T_MIN         REAL,
    T_MAX         REAL
);

-- Tabela de talhões / setores da fazenda ---------------------------------------
CREATE TABLE IF NOT EXISTS TALHOES (
    ID            INTEGER PRIMARY KEY AUTOINCREMENT,
    NOME          TEXT    NOT NULL,
    AREA_M2       REAL,
    CULTURA_ID    INTEGER,
    FOREIGN KEY (CULTURA_ID) REFERENCES CULTURAS (ID)
);

-- Histórico de leituras dos sensores (núcleo do sistema) -----------------------
-- Alimentada pela Fase 3 (ESP32/Wokwi -> sensores.py) e consumida pela Fase 4
-- (ML/dashboard) e pela Fase 7 (alertas).
CREATE TABLE IF NOT EXISTS SENSORES_HIST (
    ID            INTEGER PRIMARY KEY AUTOINCREMENT,
    DATA_REGISTRO TEXT    NOT NULL,         -- ISO 8601 (YYYY-MM-DD HH:MM:SS)
    TALHAO_ID     INTEGER,
    N             INTEGER,                  -- presença de Nitrogênio (0/1) ou nível
    P             INTEGER,                  -- presença de Fósforo
    K             INTEGER,                  -- presença de Potássio
    PH            REAL    NOT NULL,         -- pH do solo (0..14)
    AJUSTE_PH     REAL,                     -- correção de pH aplicada
    UMIDADE       REAL,                     -- umidade do solo (%)
    TEMPERATURA_C REAL,                     -- temperatura (°C)
    MENSAGEM      TEXT,                     -- diagnóstico/estado da bomba
    FOREIGN KEY (TALHAO_ID) REFERENCES TALHOES (ID)
);

-- Índice para acelerar consultas por data --------------------------------------
CREATE INDEX IF NOT EXISTS IDX_SENSORES_DATA
    ON SENSORES_HIST (DATA_REGISTRO);

-- Log de alertas disparados (Fase 7) -------------------------------------------
CREATE TABLE IF NOT EXISTS ALERTAS_LOG (
    ID            INTEGER PRIMARY KEY AUTOINCREMENT,
    DATA_ALERTA   TEXT    NOT NULL,
    ORIGEM        TEXT,
    REGRA_ID      TEXT,
    SEVERIDADE    TEXT,
    LEITURA       TEXT,
    ACAO          TEXT,
    CANAIS        TEXT,
    MODO          TEXT                       -- 'AWS' ou 'SIMULADO'
);

-- =====================================================================
-- NOTAS PARA ORACLE (caso DB_BACKEND=oracle)
-- ---------------------------------------------------------------------
-- - Trocar INTEGER PRIMARY KEY AUTOINCREMENT por:
--       ID NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY
-- - TEXT  -> VARCHAR2(n) / CLOB ; REAL -> NUMBER(p,s)
-- - DATA_REGISTRO pode ser TIMESTAMP.
-- - Antes de importar planilha, ajustar:
--       ALTER SESSION SET NLS_NUMERIC_CHARACTERS = '.,';
-- =====================================================================
