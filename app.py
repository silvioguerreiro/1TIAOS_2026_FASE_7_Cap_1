# -*- coding: utf-8 -*-
"""
app.py
======
Dashboard integradora (Streamlit) — ORQUESTRADOR CENTRAL da Fase 7.

A partir de uma única pasta de projeto, dispara/integra os serviços das Fases
1, 2, 3, 4, 6 e 7 por meio de botões na interface. Estado compartilhado via
st.session_state.

Execução:
    streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Raiz do projeto no path (permite os imports de pacote)
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import settings
from fase1_base_dados import calculo_area, manejo_insumos, api_meteorologica
from fase2_banco_dados import db
from fase3_iot import sensores
from fase4_ml_dashboard import modelo_ml, graficos
from fase6_visao import detector_yolo
from fase7_alertas import alerta_aws

# --------------------------------------------------------------------------- #
# Configuração da página
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="FarmTech Solutions — Sistema Integrado (Fase 7)",
    page_icon="🌱",
    layout="wide",
)

# Impede a tradução automática do navegador (Google Tradutor) de alterar o DOM
# e quebrar a renderização do React — causa do "NotFoundError: insertBefore".
components.html(
    """
    <script>
      const doc = window.parent.document;
      doc.documentElement.setAttribute("translate", "no");
      doc.documentElement.classList.add("notranslate");
      let m = doc.querySelector('meta[name="google"]');
      if (!m) {
        m = doc.createElement("meta");
        m.name = "google";
        m.content = "notranslate";
        doc.head.appendChild(m);
      }
    </script>
    """,
    height=0,
)


@st.cache_resource
def _inicializar():
    """Inicializa o banco uma única vez por sessão."""
    return db.inicializar_banco()


_info_db = _inicializar()

# Estado compartilhado
ss = st.session_state
ss.setdefault("previsao", None)
ss.setdefault("ultimas_leituras", [])
ss.setdefault("deteccoes", [])
ss.setdefault("alertas", [])

# --------------------------------------------------------------------------- #
# Cabeçalho + navegação
# --------------------------------------------------------------------------- #
st.title("🌱 FarmTech Solutions — Sistema Integrado de Agronegócio")
st.caption(
    f"{settings.PROJETO['fase']}  •  Grupo {settings.PROJETO['grupo']}  •  "
    f"{', '.join(settings.PROJETO['integrantes'])}"
)

with st.sidebar:
    st.header("⚙️ Navegação")
    pagina = st.radio(
        "Selecione a fase / serviço:",
        [
            "🏠 Visão Geral",
            "🌾 Fase 1 — Área, Insumos & Meteo",
            "🗄️ Fase 2 — Banco de Dados",
            "📡 Fase 3 — Sensores & Irrigação",
            "🧠 Fase 4 — ML & Previsões",
            "👁️ Fase 6 — Visão (YOLO)",
            "🔔 Fase 7 — Alertas (AWS)",
        ],
    )
    st.divider()
    st.metric("Leituras no banco", db.contar_leituras())
    modo_aws = "AWS (real)" if settings.aws_credenciais_ok() else "Simulado"
    st.metric("Modo de alertas", modo_aws)
    st.caption(f"Banco: {settings.DB_BACKEND.upper()}  •  Meteo: {settings.METEO_PROVIDER}")


# =========================================================================== #
# PÁGINA: VISÃO GERAL
# =========================================================================== #
if pagina == "🏠 Visão Geral":
    st.subheader("Do sensor ao alerta — visão integrada")
    col1, col2, col3, col4 = st.columns(4)
    stats = db.estatisticas()
    col1.metric("Registros", int(stats.get("TOTAL", 0)))
    col2.metric("pH médio", stats.get("PH_MEDIO", "—"))
    col3.metric("Umidade média (%)", stats.get("UMIDADE_MEDIA", "—"))
    col4.metric("Temp. média (°C)", stats.get("TEMP_MEDIA", "—"))

    st.markdown(
        """
        Esta dashboard é o **orquestrador central**: cada fase abaixo pode ser
        executada por um botão. Equivalente em terminal no `run.py`.

        **Fluxo de dados:** Fase 1 (base/meteo) → Fase 2 (banco) → Fase 3 (IoT)
        → Fase 4 (ML) → Fase 6 (visão) → **Fase 7 (alertas AWS)**.
        """
    )

    df = db.listar_leituras()
    if not df.empty:
        st.altair_chart(graficos.serie_temporal(df), use_container_width=True)

    st.info(
        "Use o menu lateral para acessar cada fase. O serviço de alertas roda "
        f"em modo **{modo_aws}** — configure o `.env` para enviar via AWS SNS."
    )

# =========================================================================== #
# PÁGINA: FASE 1
# =========================================================================== #
elif pagina == "🌾 Fase 1 — Área, Insumos & Meteo":
    st.subheader("🌾 Fase 1 — Cálculo de área, manejo de insumos e meteorologia")

    st.markdown("#### 1) Área de plantio")
    c1, c2, c3 = st.columns(3)
    figura = c1.selectbox("Figura geométrica", list(calculo_area.DIMENSOES.keys()))
    dims = {}
    for i, dim in enumerate(calculo_area.DIMENSOES[figura]):
        col = [c2, c3][i % 2]
        dims[dim] = col.number_input(f"{dim} (m)", min_value=0.0, value=100.0, key=f"a_{dim}")
    if st.button("Calcular área", type="primary"):
        area = calculo_area.calcular_area(figura, **dims)
        ss["area_calculada"] = area
        st.success(f"Área de plantio: **{area:,.2f} m²** ({area/10000:,.4f} ha)")

    st.divider()
    st.markdown("#### 2) Manejo de insumos")
    c1, c2, c3, c4 = st.columns(4)
    produto = c1.selectbox("Produto", list(settings.PRODUTOS_INSUMOS.values()))
    num_ruas = c2.number_input("Nº de ruas", min_value=0, value=50)
    comp = c3.number_input("Comprimento/rua (m)", min_value=0.0, value=120.0)
    dose = c4.number_input("Dose (mL ou g / m)", min_value=0.0, value=15.0)
    if st.button("Calcular insumo"):
        r = manejo_insumos.calcular_insumo(produto, int(num_ruas), comp, dose)
        st.success(r.resumo())
        st.json(r.to_dict())

    st.divider()
    st.markdown("#### 3) Previsão meteorológica (API pública)")
    if st.button("🌦️ Buscar previsão", type="primary"):
        with st.spinner("Consultando API meteorológica..."):
            ss["previsao"] = api_meteorologica.obter_previsao()
    if ss["previsao"]:
        p = ss["previsao"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Temperatura", f"{p['temperatura_atual']} °C")
        c2.metric("Umidade do ar", f"{p['umidade_atual']} %")
        c3.metric("Chuva próx. 6h", f"{p['prob_chuva_6h']:.0f} %")
        st.caption(f"Fonte: {p['provider']} • {p['local']} • {p['atualizado_em']}"
                   + (" • (simulado)" if p["simulado"] else ""))
        if p["prob_chuva_6h"] > 80:
            st.warning("⚠️ Chuva muito provável — considere **suspender a irrigação** "
                       "(este evento dispara alerta na Fase 7).")

# =========================================================================== #
# PÁGINA: FASE 2
# =========================================================================== #
elif pagina == "🗄️ Fase 2 — Banco de Dados":
    st.subheader("🗄️ Fase 2 — Banco de dados relacional")
    st.write(f"Backend: **{settings.DB_BACKEND.upper()}**  •  "
             f"Tabela: `{settings.TABELA_SENSORES}`  •  "
             f"Registros: **{db.contar_leituras()}**")

    c1, c2, c3 = st.columns(3)
    if c1.button("🔄 (Re)inicializar banco"):
        info = db.inicializar_banco(forcar_seed=db.contar_leituras() == 0)
        st.success(f"Banco pronto. Total: {info['total_no_banco']}")
    if c2.button("📊 Estatísticas gerais"):
        st.json(db.estatisticas())
    if c3.button("⬇️ Exportar CSV (p/ R)"):
        destino = settings.DATA_DIR / "sensores_export.csv"
        db.listar_leituras().to_csv(destino, index=False)
        st.success(f"CSV salvo em: {destino}")

    st.markdown("##### Consultas analíticas (espelham as queries SQL da Fase 3)")
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**Leituras com pH fora da faixa (5.5–6.8)**")
        st.dataframe(db.leituras_ph_fora_faixa().head(20), use_container_width=True)
    with cc2:
        st.markdown("**Situações de emergência (T ≥ 40°C e Umidade < 55%)**")
        st.dataframe(db.situacoes_emergencia().head(20), use_container_width=True)

    st.markdown("##### Tabela completa de leituras")
    st.dataframe(db.listar_leituras(), use_container_width=True, height=300)

# =========================================================================== #
# PÁGINA: FASE 3
# =========================================================================== #
elif pagina == "📡 Fase 3 — Sensores & Irrigação":
    st.subheader("📡 Fase 3 — IoT: leitura de sensores e acionamento da bomba")
    st.caption("ESP32/Wokwi: DHT22 (umidade/temp), LDR (pH), botões (NPK), relé (bomba). "
               "Aqui usamos o modo simulado; o `diagram.json` e o `.ino` estão em `fase3_iot/`.")

    c1, c2 = st.columns([1, 1])
    cultura = c1.selectbox("Cultura", list(settings.CULTURAS.keys()))
    qtd = c2.slider("Quantas leituras gerar?", 1, 20, 5)

    if st.button("📥 Ler sensores e gravar no banco", type="primary"):
        novas = [sensores.ler_sensores(modo="simulado", cultura=cultura,
                                       salvar_no_banco=True) for _ in range(qtd)]
        ss["ultimas_leituras"] = novas
        st.success(f"{qtd} leitura(s) registrada(s).")

    if ss["ultimas_leituras"]:
        df_novas = pd.DataFrame([
            {k: v for k, v in l.items() if not k.startswith("_")}
            for l in ss["ultimas_leituras"]
        ])
        st.dataframe(df_novas, use_container_width=True)
        ligadas = sum(1 for l in ss["ultimas_leituras"] if l.get("_bomba_ligada"))
        st.metric("Bomba acionada (ON) nas leituras geradas", f"{ligadas}/{len(ss['ultimas_leituras'])}")

    st.divider()
    st.markdown("##### Atuação histórica da bomba")
    df = db.listar_leituras()
    if not df.empty:
        st.altair_chart(graficos.status_bomba(df), use_container_width=True)

# =========================================================================== #
# PÁGINA: FASE 4
# =========================================================================== #
elif pagina == "🧠 Fase 4 — ML & Previsões":
    st.subheader("🧠 Fase 4 — Machine Learning (Scikit-Learn)")

    c1, c2 = st.columns(2)
    if c1.button("🏋️ Treinar / atualizar modelos", type="primary"):
        with st.spinner("Treinando Random Forest (umidade e pH)..."):
            met = modelo_ml.treinar_modelos()
        st.success("Modelos treinados.")
        ss["metricas_ml"] = met

    if c2.button("📈 Carregar métricas"):
        try:
            _, _, met_umi, met_ph = modelo_ml.carregar_modelos()
            ss["metricas_ml"] = {"UMIDADE": met_umi, "PH": met_ph}
        except Exception as exc:
            st.error(f"Erro ao carregar modelos: {exc}")

    if ss.get("metricas_ml"):
        cu, cp = st.columns(2)
        with cu:
            st.markdown("**Modelo de Umidade**")
            m = ss["metricas_ml"]["UMIDADE"]
            st.metric("MAE", f"{m['MAE']:.2f}")
            st.metric("RMSE", f"{m['RMSE']:.2f}")
            st.metric("R²", f"{m['R2']:.3f}")
        with cp:
            st.markdown("**Modelo de pH**")
            m = ss["metricas_ml"]["PH"]
            st.metric("MAE", f"{m['MAE']:.2f}")
            st.metric("RMSE", f"{m['RMSE']:.2f}")
            st.metric("R²", f"{m['R2']:.3f}")

    st.divider()
    st.markdown("##### Previsão e recomendação de manejo")
    cultura = st.selectbox("Cultura", list(settings.CULTURAS.keys()), key="ml_cult")
    params = settings.CULTURAS[cultura]
    c1, c2, c3 = st.columns(3)
    n = c1.number_input("N", 0.0, 300.0, 0.0)
    p = c1.number_input("P", 0.0, 300.0, 0.0)
    k = c1.number_input("K", 0.0, 300.0, 0.0)
    ph_atual = c2.number_input("pH atual", 3.0, 9.0, 5.0)
    ajuste = c2.number_input("Ajuste de pH", -20.0, 20.0, 0.6)
    umi = c3.number_input("Umidade atual (%)", 0.0, 100.0, 28.0)
    temp = c3.number_input("Temperatura (°C)", -5.0, 60.0, 39.0)

    if st.button("🔮 Gerar previsão", type="primary"):
        try:
            pred = modelo_ml.prever(n, p, k, ph_atual, ajuste, umi, temp)
            st.success(
                f"Umidade prevista: **{pred['umidade_prevista']:.2f}%**  •  "
                f"pH previsto: **{pred['ph_previsto']:.2f}**"
            )
            recs = []
            if min(umi, pred["umidade_prevista"]) < params["umi_min"]:
                recs.append("💧 Umidade abaixo do ideal → irrigação recomendada.")
            if ph_atual < params["ph_min"]:
                recs.append("🧪 Solo ácido → aplicar calcário/dolomita.")
            elif ph_atual > params["ph_max"]:
                recs.append("🧪 Solo alcalino → corrigir adubação.")
            if temp > params["t_max"]:
                recs.append("🌡️ Calor acima do ideal → risco de estresse térmico.")
            for r in recs or ["✅ Condições dentro das faixas ideais."]:
                st.write("•", r)
        except Exception as exc:
            st.error(f"Erro na predição: {exc}")

# =========================================================================== #
# PÁGINA: FASE 6
# =========================================================================== #
elif pagina == "👁️ Fase 6 — Visão (YOLO)":
    st.subheader("👁️ Fase 6 — Visão computacional (YOLO)")
    st.caption(f"Imagens em: `{settings.IMAGENS_DIR.relative_to(settings.BASE_DIR)}`. "
               "Em produção, use um modelo treinado em pragas/doenças (best.pt).")

    if st.button("🔍 Rodar detecção nas imagens", type="primary"):
        with st.spinner("Executando YOLO..."):
            ss["deteccoes"] = detector_yolo.detectar()

    if ss["deteccoes"]:
        df_det = pd.DataFrame(ss["deteccoes"])
        st.dataframe(df_det[["imagem", "classe", "confianca", "simulado"]],
                     use_container_width=True)
        resumo = detector_yolo.resumo_pragas(ss["deteccoes"])
        if resumo["praga_detectada"]:
            st.error(
                f"🐛 Praga/doença de maior confiança: **{resumo['classe']}** "
                f"({resumo['confianca_praga']:.2f}) em `{resumo['imagem']}`"
            )
            if resumo["confianca_praga"] > 0.6:
                st.warning("Confiança > 0.6 → este evento dispara alerta na Fase 7.")
        else:
            st.success("Nenhuma praga/doença relevante detectada.")

        # Mostra imagens anotadas (se YOLO real) ou as originais
        cols = st.columns(3)
        for i, d in enumerate(ss["deteccoes"][:6]):
            caminho = d.get("anotada") or str(settings.IMAGENS_DIR / d["imagem"])
            if Path(caminho).exists():
                cols[i % 3].image(caminho, caption=f"{d['classe']} ({d['confianca']:.2f})",
                                  use_container_width=True)

# =========================================================================== #
# PÁGINA: FASE 7
# =========================================================================== #
elif pagina == "🔔 Fase 7 — Alertas (AWS)":
    st.subheader("🔔 Fase 7 — Serviço de mensageria (Amazon SNS)")
    st.write(f"Modo atual: **{'AWS (real)' if settings.aws_credenciais_ok() else 'SIMULADO'}**  "
             f"•  Região: `{settings.AWS_REGION}`  •  E-mail: `{settings.EMAIL_DEST}`  "
             f"•  SMS: `{settings.PHONE_DEST}`")
    if not settings.aws_credenciais_ok():
        st.info("Sem credenciais AWS válidas → os alertas são **simulados** "
                "(impressos abaixo). Configure o `.env` para enviar de verdade.")

    st.markdown("#### Tabela de limiares → ação corretiva → canal")
    tabela = pd.DataFrame([{
        "Origem": r["origem"], "Limiar": r["descricao"],
        "Ação corretiva": r["acao"], "Canais": ", ".join(r["canais"]),
        "Severidade": r["severidade"],
    } for r in settings.LIMIARES])
    st.dataframe(tabela, use_container_width=True)

    st.divider()
    st.markdown("#### 1) Avaliar a última leitura + meteo + visão e alertar")
    if st.button("🚨 Avaliar e disparar alertas automáticos", type="primary"):
        leitura = db.ultima_leitura() or {}
        leitura["prob_chuva_6h"] = (ss["previsao"] or
                                    api_meteorologica.obter_previsao())["prob_chuva_6h"]
        resumo = detector_yolo.resumo_pragas(ss["deteccoes"] or detector_yolo.detectar())
        leitura["confianca_praga"] = resumo["confianca_praga"]

        disparos = alerta_aws.avaliar_leitura(leitura)
        if not disparos:
            st.success("Nenhum limiar ultrapassado — nada a alertar. ✅")
        else:
            resultados = alerta_aws.processar_e_alertar(leitura)
            ss["alertas"] = resultados
            st.error(f"{len(resultados)} alerta(s) disparado(s) "
                     f"(modo: {resultados[0]['modo']}).")
            for res in resultados:
                with st.expander(f"📨 {res['assunto']}"):
                    st.write("**Ação corretiva:**", res["acao"])
                    st.write("**Canais:**", ", ".join(res["canais"]))
                    st.json(res["envio"])

    st.divider()
    st.markdown("#### 2) Disparo de teste manual")
    c1, c2 = st.columns(2)
    canais = c1.multiselect("Canais", ["email", "sms"], default=["email", "sms"])
    sev = c2.selectbox("Severidade", ["ALERTA", "EMERGENCIA"])
    msg = st.text_input("Mensagem/leitura", "umidade=22%")
    acao = st.text_input("Ação corretiva", "Acionar irrigação imediata no setor X.")
    if st.button("✉️ Enviar alerta de teste"):
        res = alerta_aws.enviar_alerta(
            origem="Teste manual (dashboard)", leitura=msg, acao=acao,
            canais=canais, severidade=sev, regra_id="TESTE_UI",
        )
        st.success(f"Alerta processado (modo: {res['modo']}).")
        st.json(res["envio"])
        if res["modo"] == "SIMULADO":
            st.caption("💡 Em modo simulado, o conteúdo também é impresso no terminal.")
