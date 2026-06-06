# 🛠️ Como colocar tudo para rodar no VS Code

Guia rápido e completo para executar o projeto **FarmTech Solutions — Fase 7**
no Visual Studio Code, do zero até a dashboard rodando.

> Tempo estimado: ~10 minutos (a maior parte é o `pip install`).

---

## 0. Pré-requisitos (instalar uma vez)

1. **Python 3.10 ou superior** — https://www.python.org/downloads/
   - No Windows, marque **“Add Python to PATH”** durante a instalação.
   - Teste no terminal: `python --version` (ou `python3 --version`).
2. **Visual Studio Code** — https://code.visualstudio.com/
3. (Opcional) **R** para a análise estatística da Fase 1 — https://cran.r-project.org/

---

## 1. Abrir o projeto no VS Code

1. Abra o VS Code.
2. **File → Open Folder…** e selecione a pasta **`1TIAO_Fase7_FarmTech`**
   (a pasta que contém o `app.py`).
3. Ao abrir, o VS Code vai sugerir **instalar as extensões recomendadas**
   (já configuradas em `.vscode/extensions.json`). Clique em **Install**:
   - **Python** (Microsoft) — obrigatória
   - **Pylance** — autocompletar
   - **Jupyter** e **R** — opcionais

---

## 2. Criar o ambiente virtual (venv) e selecionar o interpretador

O jeito mais fácil é pela paleta de comandos:

1. Pressione **`Ctrl+Shift+P`** (macOS: **`Cmd+Shift+P`**).
2. Digite e escolha **“Python: Create Environment”**.
3. Selecione **`Venv`** → escolha sua versão do **Python 3.10+**.
4. Quando perguntar sobre dependências, marque **`requirements.txt`** (se
   aparecer) — isso já instala tudo. Senão, instale no passo 3.

> Isso cria a pasta **`.venv/`** na raiz e já a define como interpretador.
> Para conferir/trocar: `Ctrl+Shift+P` → **“Python: Select Interpreter”** →
> escolha o que tem **`.venv`** no caminho.

---

## 3. Abrir o terminal integrado e instalar as dependências

1. Abra o terminal: **`Ctrl+``** (a tecla de crase, abaixo do Esc) ou
   menu **Terminal → New Terminal**.
2. Confirme que o venv está ativo — o início da linha mostra **`(.venv)`**.
   Se não estiver, feche e reabra o terminal.
3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

   > Demora alguns minutos (baixa Streamlit, scikit-learn, etc.). É normal.

---

## 4. (Opcional) Configurar variáveis de ambiente — `.env`

O projeto **roda sem isso** (banco SQLite, meteo sem chave, alertas em modo
simulado). Configure apenas se quiser AWS/Oracle/OpenWeatherMap reais.

1. Copie o modelo:
   - macOS/Linux: `cp .env.example .env`
   - Windows (PowerShell): `Copy-Item .env.example .env`
2. Abra o **`.env`** no VS Code e preencha o que precisar (ex.: `AWS_*`,
   `SNS_TOPIC_ARN`, `EMAIL_DEST`, `PHONE_DEST`). Veja o detalhamento em
   `fase5_cloud/README_cloud.md`.

---

## 5. Inicializar o banco de dados (cria e popula com os dados reais)

No terminal integrado:

```bash
python run.py --init-db
```

Saída esperada: `Registros inseridos agora: 1021` e as estatísticas gerais.
Isso cria o arquivo `data/farmtech.db` a partir da planilha real.

---

## 6. Rodar a DASHBOARD (Streamlit)

Você tem **duas formas** — escolha uma:

### Forma A — pela tecla F5 (recomendada)
1. Pressione **`F5`**.
2. No seletor que aparece no topo, escolha **“▶ Dashboard (Streamlit)”**.
3. O VS Code abre o terminal e sobe o servidor; o navegador abre em
   `http://localhost:8501`.

### Forma B — pelo terminal
```bash
python -m streamlit run app.py
```
Depois **`Ctrl+clique`** no link `http://localhost:8501` que aparece.

> Use sempre `python -m streamlit ...` (e não só `streamlit ...`): funciona
> mesmo que o atalho `streamlit` não esteja no PATH.

**Para parar o servidor:** clique no terminal e pressione **`Ctrl+C`**.

---

## 7. Rodar os serviços pelo TERMINAL (CLI `run.py`)

Equivalente da dashboard, útil para o vídeo e para testar fase a fase:

```bash
python run.py --fase 1            # área + insumos + meteorologia
python run.py --fase 2            # consultas ao banco (+ gera docs/resumo_sensores.png)
python run.py --fase 3 --n 5      # gera 5 leituras de sensores
python run.py --fase 4 --treinar  # treina os modelos de ML
python run.py --fase 6            # roda a visão computacional (YOLO)
python run.py --fase 7            # avalia a última leitura e dispara alertas
python run.py --alerta            # alerta de TESTE manual (e-mail + SMS)
python run.py --export-csv        # exporta CSV para a análise em R
```

> Ou pressione **`F5`** e escolha qualquer uma das configurações **“CLI: …”**
> já prontas no `.vscode/launch.json`.

---

## 8. (Opcional) Análise estatística em R (Fase 1)

```bash
python run.py --export-csv
Rscript fase1_base_dados/analise_estatistica.R
```

Gera estatísticas no terminal e o gráfico `docs/hist_ph_R.png`.

---

## 9. (Opcional) Visão computacional YOLO “de verdade”

Por padrão a Fase 6 roda em **modo simulado** (offline). Para usar o YOLO real:

```bash
pip install ultralytics
python run.py --fase 6
```

Na primeira vez, baixa o modelo `yolov8n.pt`. As imagens anotadas vão para
`fase6_visao/saidas/`. (Em produção, substitua por um modelo treinado em
pragas/doenças, `best.pt`.)

---

## 10. Solução de problemas (troubleshooting)

**“`streamlit` não é reconhecido / command not found”**
→ Use `python -m streamlit run app.py`. Confirme que o `(.venv)` está ativo.

**“ModuleNotFoundError: No module named 'streamlit' / 'sklearn'…”**
→ O interpretador errado está selecionado. `Ctrl+Shift+P` → **Python: Select
Interpreter** → escolha o do `.venv`. Reabra o terminal e rode `pip install -r
requirements.txt` de novo.

**“sqlite3.OperationalError: disk I/O error” ou “database is locked”**
→ Acontece quando a pasta está em um drive de **sincronização/rede** (OneDrive,
iCloud, Google Drive) que trava o arquivo. Soluções:
  1. Pause a sincronização do OneDrive enquanto desenvolve, **ou**
  2. No `.env`, aponte o banco para um caminho local fora da sincronização:
     ```
     SQLITE_PATH=/Users/seu_usuario/farmtech.db        # macOS/Linux
     # SQLITE_PATH=C:\Users\seu_usuario\farmtech.db     # Windows
     ```
  3. Se o `data/farmtech.db` ficou corrompido, apague-o — ele se recria com
     `python run.py --init-db`.

**“Port 8501 is already in use”**
→ Outra instância está rodando. Pare com `Ctrl+C` no terminal antigo, ou rode em
outra porta: `python -m streamlit run app.py --server.port 8502`.

**F5 não mostra as opções de execução**
→ Instale a extensão **Python (Microsoft)** e selecione o interpretador (passo 2).

**No Windows, o venv não ativa no terminal (PowerShell)**
→ Rode uma vez, como admin: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

---

## 11. Sequência mínima (resumo “copia e cola”)

```bash
# 1) já com a pasta aberta no VS Code e o .venv selecionado:
pip install -r requirements.txt
python run.py --init-db
python -m streamlit run app.py
```

Pronto — a dashboard abre no navegador e você navega pelas Fases 1 a 7 pelo
menu lateral. 🌱
