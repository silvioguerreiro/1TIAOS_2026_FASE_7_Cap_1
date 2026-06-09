/* =====================================================================
 * fase3_iot/esp32_irrigacao.ino
 * Sistema de irrigação inteligente - FarmTech Solutions (Grupo 1TIAO)
 * Plataforma: ESP32 (Wokwi) - ver diagram.json nesta mesma pasta.
 * ---------------------------------------------------------------------
 * Sensores e atuadores:
 *   - DHT22  (GPIO 15)  -> umidade e temperatura do ar/solo
 *   - LDR    (GPIO 34)  -> proxy de pH do solo (leitura analógica)
 *   - Botões (GPIO 18/19/21) -> presença de N, P, K (entrada digital)
 *   - Relé   (GPIO 27)  -> bomba de irrigação
 *   - LCD I2C 16x2 (SDA 22 / SCL 23, addr 0x27) -> métricas em tempo real (Fase 4)
 *
 * Saída Serial (115200) em formato lido por fase3_iot/sensores.py:
 *   N=.. P=.. K=.. | pH=.. | Ajuste pH=.. | Umi=.. | Temp=.. | Bomba=..
 *
 * Também imprime as variáveis para o Serial Plotter (Fase 4).
 * ===================================================================== */

#include "DHT.h"
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ----------------------- Pinos -----------------------
#define PIN_DHT     15
#define PIN_LDR     34
#define PIN_BTN_N   18
#define PIN_BTN_P   19
#define PIN_BTN_K   21
#define PIN_RELE    27
#define PIN_SDA     22   // I2C do LCD
#define PIN_SCL     23   // I2C do LCD

#define DHTTYPE DHT22
DHT dht(PIN_DHT, DHTTYPE);

// LCD I2C 16x2 (Fase 4): exibe pH, umidade, temperatura e estado da bomba
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ----------------- Faixa ideal (Soja) ----------------
const float PH_MIN  = 5.5;
const float PH_MAX  = 6.8;
const float UMI_MIN = 35.0;   // % - abaixo disso, irriga

void setup() {
  Serial.begin(115200);
  dht.begin();

  // --- LCD I2C 16x2 (Fase 4) ---
  Wire.begin(PIN_SDA, PIN_SCL);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("FarmTech ESP32");
  lcd.setCursor(0, 1);
  lcd.print("Iniciando...");
  delay(1500);

  pinMode(PIN_BTN_N, INPUT_PULLUP);
  pinMode(PIN_BTN_P, INPUT_PULLUP);
  pinMode(PIN_BTN_K, INPUT_PULLUP);
  pinMode(PIN_RELE, OUTPUT);
  digitalWrite(PIN_RELE, LOW);

  Serial.println("FarmTech ESP32 - irrigacao inteligente iniciada.");
}

// Converte a leitura do LDR (0..4095) em um valor de pH simulado (4.5..8.5)
float lerPh() {
  int bruto = analogRead(PIN_LDR);
  float ph = 4.5 + (bruto / 4095.0) * (8.5 - 4.5);
  return ph;
}

void loop() {
  // --- Nutrientes via botões (pressionado = LOW por causa do PULLUP) ---
  int N = (digitalRead(PIN_BTN_N) == LOW) ? 1 : 0;
  int P = (digitalRead(PIN_BTN_P) == LOW) ? 1 : 0;
  int K = (digitalRead(PIN_BTN_K) == LOW) ? 1 : 0;

  // --- DHT22: umidade e temperatura ---
  float umidade = dht.readHumidity();
  float temperatura = dht.readTemperature();
  if (isnan(umidade))     umidade = 0;
  if (isnan(temperatura)) temperatura = 0;

  // --- pH via LDR ---
  float ph = lerPh();
  float ajustePh = (ph < PH_MIN) ? (PH_MIN - ph) : 0.0;

  // --- Lógica de irrigação (igual a logica_irrigacao.py) ---
  bool bombaLigada = false;
  String estado;
  if (ph < PH_MIN || ph > PH_MAX) {
    bombaLigada = false;
    estado = "OFF -> pH fora (alvo 5.5-6.8)";
  } else if (umidade < UMI_MIN) {
    bombaLigada = true;
    estado = "ON -> umidade baixa";
  } else {
    bombaLigada = false;
    estado = "OFF -> condicao adequada";
  }
  digitalWrite(PIN_RELE, bombaLigada ? HIGH : LOW);

  // --- Saída formatada (lida pelo Python) ---
  Serial.print("N="); Serial.print(N);
  Serial.print(" P="); Serial.print(P);
  Serial.print(" K="); Serial.print(K);
  Serial.print(" | pH="); Serial.print(ph, 2);
  Serial.print(" | Ajuste pH="); Serial.print(ajustePh, 2);
  Serial.print(" | Umi="); Serial.print(umidade, 1);
  Serial.print(" | Temp="); Serial.print(temperatura, 1);
  Serial.print(" | Bomba="); Serial.println(estado);

  // --- Saída para o Serial Plotter (Fase 4) ---
  // Formato "rotulo:valor" separado por tab.
  Serial.print("pH:");   Serial.print(ph, 2);     Serial.print('\t');
  Serial.print("Umi:");  Serial.print(umidade, 1); Serial.print('\t');
  Serial.print("Temp:"); Serial.println(temperatura, 1);

  // --- Atualiza o display LCD 16x2 (Fase 4) ---
  // Linha 0: pH, umidade e temperatura | Linha 1: bomba e nutrientes (NPK)
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("pH"); lcd.print(ph, 1);
  lcd.print(" U"); lcd.print(umidade, 0);
  lcd.print("% T"); lcd.print(temperatura, 0);
  lcd.setCursor(0, 1);
  lcd.print("Bomba:");
  lcd.print(bombaLigada ? "ON " : "OFF");
  lcd.print(N ? "N" : "-");
  lcd.print(P ? "P" : "-");
  lcd.print(K ? "K" : "-");

  delay(2000);
}
