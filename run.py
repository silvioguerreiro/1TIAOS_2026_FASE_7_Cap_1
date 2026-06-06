# -*- coding: utf-8 -*-
"""
run.py
======
CLI orquestrador da Fase 7 — dispara os serviços de cada fase pelo terminal
do VS Code (equivalente em linha de comando ao dashboard app.py).

Exemplos:
    python run.py --init-db                 # cria/semeia o banco (Fase 2)
    python run.py --fase 1                   # área + insumos + meteorologia
    python run.py --fase 2                   # consultas ao banco
    python run.py --fase 3 --n 5             # lê 5 leituras de sensores (Fase 3)
    python run.py --fase 4 --treinar         # treina os modelos de ML (Fase 4)
    python run.py --fase 6                   # roda a visão computacional (YOLO)
    python run.py --fase 7                   # avalia última leitura e alerta
    python run.py --alerta                   # dispara um alerta de TESTE manual
    python run.py --export-csv               # exporta CSV para a análise em R
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Garante que a raiz do projeto esteja no path (imports de pacote funcionam
# independentemente do diretório de execução).
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import settings  # noqa: E402

logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
log = logging.getLogger("run")


# --------------------------------------------------------------------------- #
def cabecalho(titulo: str) -> None:
    print("\n" + "=" * 64)
    print(f" {titulo}")
    print("=" * 64)


# --------------------------------------------------------------------------- #
def cmd_init_db(_args) -> None:
    cabecalho("Fase 2 — Inicializando banco de dados")
    from fase2_banco_dados import db
    info = db.inicializar_banco()
    print(f"Registros inseridos agora: {info['inseridos_agora']}")
    print(f"Total no banco           : {info['total_no_banco']}")
    print("Estatísticas:", db.estatisticas())


def cmd_export_csv(_args) -> None:
    cabecalho("Exportando CSV para análise em R")
    from fase2_banco_dados import db
    db.inicializar_banco()
    df = db.listar_leituras()
    destino = settings.DATA_DIR / "sensores_export.csv"
    df.to_csv(destino, index=False)
    print(f"CSV salvo em: {destino}  ({len(df)} linhas)")
    print("Rode a análise em R com: Rscript fase1_base_dados/analise_estatistica.R")


def cmd_fase1(_args) -> None:
    cabecalho("Fase 1 — Área de plantio, insumos e meteorologia")
    from fase1_base_dados import calculo_area, manejo_insumos, api_meteorologica

    area = calculo_area.calcular_area("retangulo", base=120, altura=80)
    print(f"Área de plantio (120x80 m): {area:,.2f} m²")

    insumo = manejo_insumos.calcular_insumo(
        produto=settings.PRODUTOS_INSUMOS["2"],
        num_ruas=50, comprimento_rua_m=120, dose_por_metro=15,
    )
    print("Manejo de insumos:", insumo.resumo())

    print("\nConsultando meteorologia...")
    previsao = api_meteorologica.obter_previsao()
    print(f"  Provider : {previsao['provider']}")
    print(f"  Temp     : {previsao['temperatura_atual']} °C")
    print(f"  Umidade  : {previsao['umidade_atual']} %")
    print(f"  Chuva 6h : {previsao['prob_chuva_6h']:.0f} %")


def cmd_fase2(_args) -> None:
    cabecalho("Fase 2 — Consultas ao banco de dados")
    from fase2_banco_dados import db
    db.inicializar_banco()
    print("Estatísticas gerais:", db.estatisticas())
    print(f"\nLeituras com pH fora da faixa (5.5–6.8): "
          f"{len(db.leituras_ph_fora_faixa())}")
    print(f"Situações de emergência (T≥40 e Umi<55): "
          f"{len(db.situacoes_emergencia())}")
    print("\nÚltimas 5 leituras:")
    print(db.listar_leituras().tail(5).to_string(index=False))

    # Painel-resumo em PNG (docs/)
    try:
        from fase4_ml_dashboard import graficos
        destino = settings.DOCS_DIR / "resumo_sensores.png"
        graficos.exportar_resumo_png(db.listar_leituras(), destino)
        print(f"\nPainel-resumo salvo em: {destino}")
    except Exception as exc:
        log.warning("Não foi possível gerar o painel PNG: %s", exc)


def cmd_fase3(args) -> None:
    cabecalho("Fase 3 — Leitura de sensores e lógica de irrigação")
    from fase3_iot import sensores
    n = max(1, args.n or 3)
    for i in range(n):
        leitura = sensores.ler_sensores(modo="simulado", salvar_no_banco=True)
        print(f"  [{i+1}/{n}] pH={leitura['PH']:.2f} | "
              f"Umi={leitura['UMIDADE']:.1f}% | T={leitura['TEMPERATURA_C']:.1f}°C "
              f"| {leitura['MENSAGEM']}")


def cmd_fase4(args) -> None:
    cabecalho("Fase 4 — Machine Learning")
    from fase4_ml_dashboard import modelo_ml
    if args.treinar or not modelo_ml.modelos_existem():
        met = modelo_ml.treinar_modelos()
        for alvo, m in met.items():
            print(f"  {alvo}: MAE={m['MAE']:.3f} RMSE={m['RMSE']:.3f} R²={m['R2']:.3f}")
    pred = modelo_ml.prever(0, 0, 0, ph_atual=5.0, ajuste_ph=0.6,
                            umidade_atual=28, temperatura=39)
    print("\nPredição (exemplo crítico):")
    print(f"  Umidade prevista: {pred['umidade_prevista']:.2f}%")
    print(f"  pH previsto     : {pred['ph_previsto']:.2f}")


def cmd_fase6(_args) -> None:
    cabecalho("Fase 6 — Visão computacional (YOLO)")
    from fase6_visao import detector_yolo
    dets = detector_yolo.detectar()
    for d in dets:
        flag = " [SIMULADO]" if d["simulado"] else ""
        print(f"  {d['imagem']}: {d['classe']} ({d['confianca']:.2f}){flag}")
    print("\nResumo p/ alertas:", detector_yolo.resumo_pragas(dets))


def cmd_fase7(_args) -> None:
    cabecalho("Fase 7 — Avaliação de limiares e alertas (última leitura)")
    from fase2_banco_dados import db
    from fase1_base_dados import api_meteorologica
    from fase6_visao import detector_yolo
    from fase7_alertas import alerta_aws

    db.inicializar_banco()
    leitura = db.ultima_leitura() or {}

    # Enrique a leitura com meteorologia (Fase 1) e visão (Fase 6)
    leitura["prob_chuva_6h"] = api_meteorologica.obter_previsao()["prob_chuva_6h"]
    leitura["confianca_praga"] = detector_yolo.resumo_pragas(
        detector_yolo.detectar()
    )["confianca_praga"]

    print("Leitura avaliada:", {k: leitura.get(k) for k in
          ("UMIDADE", "PH", "TEMPERATURA_C", "prob_chuva_6h", "confianca_praga")})
    resultados = alerta_aws.processar_e_alertar(leitura)
    print(f"\nAlertas disparados: {len(resultados)} "
          f"(modo: {resultados[0]['modo'] if resultados else 'n/a'})")


def cmd_alerta(_args) -> None:
    cabecalho("Fase 7 — Alerta de TESTE manual")
    from fase7_alertas import alerta_aws
    alerta_aws.enviar_alerta(
        origem="Teste manual via run.py",
        leitura="umidade=22%",
        acao="Acionar irrigação imediata no setor de teste.",
        canais=["email", "sms"],
        severidade="EMERGENCIA",
        regra_id="TESTE",
    )


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Orquestrador CLI — FarmTech Solutions (Fase 7).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--fase", type=int, choices=[1, 2, 3, 4, 6, 7],
                        help="Executa o serviço da fase indicada.")
    parser.add_argument("--alerta", action="store_true",
                        help="Dispara um alerta de teste manual (Fase 7).")
    parser.add_argument("--init-db", action="store_true",
                        help="Cria e semeia o banco de dados (Fase 2).")
    parser.add_argument("--export-csv", action="store_true",
                        help="Exporta CSV das leituras para a análise em R.")
    parser.add_argument("--treinar", action="store_true",
                        help="(Fase 4) força o re-treino dos modelos de ML.")
    parser.add_argument("--n", type=int, default=3,
                        help="(Fase 3) número de leituras a gerar.")
    args = parser.parse_args(argv)

    if args.init_db:
        cmd_init_db(args)
    if args.export_csv:
        cmd_export_csv(args)

    if args.fase == 1:
        cmd_fase1(args)
    elif args.fase == 2:
        cmd_fase2(args)
    elif args.fase == 3:
        cmd_fase3(args)
    elif args.fase == 4:
        cmd_fase4(args)
    elif args.fase == 6:
        cmd_fase6(args)
    elif args.fase == 7:
        cmd_fase7(args)

    if args.alerta:
        cmd_alerta(args)

    if not any([args.fase, args.alerta, args.init_db, args.export_csv]):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
