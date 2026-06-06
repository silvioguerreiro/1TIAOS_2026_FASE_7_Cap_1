# =====================================================================
# fase1_base_dados/analise_estatistica.R
# Análise estatística em R (Fase 1) - FarmTech Solutions (Grupo 1TIAO)
# ---------------------------------------------------------------------
# Lê as leituras de sensores e produz estatísticas descritivas,
# correlações e um histograma. Compatível com VS Code (extensão R) e
# RStudio.
#
# Fontes de dados aceitas (na ordem):
#   1) data/sensores_export.csv   (gerado por: python run.py --export-csv)
#   2) data/Sensores_limpo.xlsx   (planilha original, via pacote readxl)
#
# Execução no terminal:
#   Rscript fase1_base_dados/analise_estatistica.R
# =====================================================================

# --- Localiza a raiz do projeto a partir deste script -----------------
args_full <- commandArgs(trailingOnly = FALSE)
file_arg  <- sub("--file=", "", args_full[grep("--file=", args_full)])
if (length(file_arg) > 0) {
  script_dir <- dirname(normalizePath(file_arg))
} else {
  script_dir <- getwd()
}
root_dir <- normalizePath(file.path(script_dir, ".."))
data_dir <- file.path(root_dir, "data")

csv_path  <- file.path(data_dir, "sensores_export.csv")
xlsx_path <- file.path(data_dir, "Sensores_limpo.xlsx")

# --- Carrega os dados -------------------------------------------------
carregar_dados <- function() {
  if (file.exists(csv_path)) {
    message("Lendo CSV: ", csv_path)
    return(read.csv(csv_path, stringsAsFactors = FALSE))
  }
  if (file.exists(xlsx_path)) {
    if (!requireNamespace("readxl", quietly = TRUE)) {
      stop("Instale o pacote readxl (install.packages('readxl')) ou gere o CSV com: python run.py --export-csv")
    }
    message("Lendo XLSX: ", xlsx_path)
    return(as.data.frame(readxl::read_excel(xlsx_path)))
  }
  stop("Nenhuma fonte de dados encontrada em ", data_dir)
}

df <- carregar_dados()

# --- Padroniza nomes de colunas --------------------------------------
names(df) <- toupper(trimws(names(df)))
names(df)[names(df) == "PH"]            <- "PH"
names(df)[names(df) == "AJUSTE PH"]     <- "AJUSTE_PH"
names(df)[names(df) == "UMIDADE"]       <- "UMIDADE"
names(df)[names(df) == "TEMPERATURA C"] <- "TEMPERATURA_C"

cols_num <- intersect(c("N","P","K","PH","AJUSTE_PH","UMIDADE","TEMPERATURA_C"),
                      names(df))
for (c in cols_num) df[[c]] <- as.numeric(df[[c]])

cat("\n==============================================\n")
cat("ANÁLISE ESTATÍSTICA - SENSORES DA FAZENDA (R)\n")
cat("==============================================\n")
cat("Registros:", nrow(df), " | Variáveis:", length(cols_num), "\n\n")

# --- 1) Estatísticas descritivas -------------------------------------
cat(">>> Estatísticas descritivas (summary):\n")
print(summary(df[cols_num]))

cat("\n>>> Desvio-padrão por variável:\n")
print(round(sapply(df[cols_num], sd, na.rm = TRUE), 3))

# --- 2) Matriz de correlação -----------------------------------------
cat("\n>>> Matriz de correlação (Pearson):\n")
print(round(cor(df[cols_num], use = "complete.obs"), 2))

# --- 3) Indicadores agronômicos --------------------------------------
cat("\n>>> Indicadores sintéticos:\n")
cat(sprintf("   pH médio        : %.2f\n", mean(df$PH, na.rm = TRUE)))
cat(sprintf("   Umidade média   : %.2f %%\n", mean(df$UMIDADE, na.rm = TRUE)))
cat(sprintf("   Temperatura média: %.2f C\n", mean(df$TEMPERATURA_C, na.rm = TRUE)))

fora_faixa <- sum(df$PH < 5.5 | df$PH > 6.8, na.rm = TRUE)
cat(sprintf("   Leituras com pH fora da faixa (5.5-6.8): %d (%.1f%%)\n",
            fora_faixa, 100 * fora_faixa / nrow(df)))

# --- 4) Histograma do pH (salvo em docs/) ----------------------------
out_png <- file.path(root_dir, "docs", "hist_ph_R.png")
tryCatch({
  png(out_png, width = 800, height = 500)
  hist(df$PH, breaks = 30, col = "darkseagreen",
       main = "Distribuição do pH do solo",
       xlab = "pH", ylab = "Frequência")
  abline(v = c(5.5, 6.8), col = "red", lwd = 2, lty = 2)
  dev.off()
  cat("\nHistograma salvo em:", out_png, "\n")
}, error = function(e) message("Não foi possível salvar o gráfico: ", e$message))

cat("\nAnálise estatística (R) concluída.\n")
