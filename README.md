# SMC Quant Terminal — v4.0 FINAL

Terminal de trading profesional con Smart Money Concepts, multi-usuario, bot de Telegram, backtesting, análisis multi-timeframe y gestión de riesgo avanzada.

---

## Instalación rápida

```bash
pip install -r requirements.txt
cp .env.example .env          # rellena tu token de Telegram
streamlit run app.py          # arranca la app
```

Para el bot (terminal separada):
```bash
export TELEGRAM_BOT_TOKEN="tu_token_aqui"
python bot/telegram_bot.py
```

Usuario demo listo: **demo** / **demo123**

---

## Estructura del proyecto

```
SMC_FINAL_v4/
├── app.py                          # Entrada principal — 10 páginas
├── requirements.txt
├── .env.example                    # Plantilla de variables de entorno
│
├── bot/
│   └── telegram_bot.py             # Bot de Telegram completo
│
├── database/
│   └── db.py                       # SQLite multi-usuario (6 tablas)
│
├── modules/                        # Páginas de la app Streamlit
│   ├── auth.py                     # Login y registro
│   ├── dashboard.py                # Equity curve + métricas globales
│   ├── live_analysis.py            # Gráfica SMC en vivo
│   ├── multi_tf.py                 # Análisis multi-timeframe
│   ├── journal.py                  # Diario de trades
│   ├── performance.py              # Estadísticas + IA RandomForest
│   ├── backtesting.py              # Backtest sobre datos históricos
│   ├── risk_manager.py             # Kelly + Monte Carlo
│   ├── calendar.py                 # Calendario económico semanal
│   ├── bot_config.py               # Configuración del bot Telegram
│   └── education.py                # Guía SMC interactiva
│
├── utils/                          # Lógica de negocio
│   ├── market_data.py              # yfinance + validación de datos
│   ├── smc_engine.py               # BOS, CHoCH, OB, FVG, Liquidez
│   ├── ai_engine.py                # RandomForest + métricas
│   ├── backtesting.py              # Motor de backtesting
│   ├── multi_timeframe.py          # Análisis MTF
│   ├── economic_calendar.py        # Eventos económicos semanales
│   └── time_utils.py               # Zona horaria CDMX (sin pytz)
│
└── ui/
    └── styles.py                   # Tema oscuro + claro
```

---

## Módulos — qué hace cada uno

### 📊 Dashboard
Resumen general de tu cuenta: capital actual, curva de equity, win rate, profit factor, Sharpe ratio y rendimiento por activo. Permite ajustar el capital inicial desde la interfaz.

### 🔴 Análisis en Vivo
Gráfica de velas profesional con EMA 20/50/200, Bollinger Bands, RSI y MACD. Detecta y visualiza Order Blocks, Fair Value Gaps y zonas de liquidez en tiempo real. Incluye panel lateral con precio, señal SMC, recomendación directa (LONG/SHORT/ESPERA), SL/TP sugeridos por ATR y calculadora de riesgo. Muestra alertas si hay evento económico de alto impacto en los próximos 90 minutos.

### 🔭 Multi-Timeframe
Analiza el mismo activo en dos temporalidades simultáneamente. El timeframe alto define la estructura y dirección; el bajo busca la entrada precisa. Muestra señal de alineación, confianza combinada y niveles sugeridos cuando ambos TF están alineados. Incluye gráficas mini de cada timeframe.

Combos disponibles: Scalping (5m/1m), Intraday (1h/15m), Swing (4h/1h), Posicional (1d/4h).

### 📓 Diario de Trades
Registro enriquecido de operaciones: activo, timeframe, dirección, setup SMC, estado emocional, entrada/SL/TP, resultado y tags. Preview automático del RR al llenar precios. Historial con filtros por activo, dirección, setup y estado. Tabla coloreada por resultado.

### 📈 Performance & IA
Análisis estadístico completo: win rate, profit factor, expectancy, racha máxima de ganancias y pérdidas, Sharpe ratio y drawdown máximo. Modelo RandomForest con validación cruzada para identificar patrones en tu historial. Gráficas de distribución de PnL, rendimiento por setup y por estado emocional.

### 🧪 Backtesting
Prueba la estrategia SMC sobre datos históricos reales descargados de yfinance. Ventana deslizante de 60 velas para el análisis. Calcula equity curve, win rate, profit factor, Sharpe, drawdown máximo y expectancy. Muestra todos los trades simulados con detalle. Los resultados se guardan en historial por usuario.

### 🛡️ Risk Manager
Tres herramientas en una:

**Calculadora de posición** — ingresa entrada, SL, TP, capital y riesgo % para obtener el tamaño de lote exacto, pips de SL/TP y ganancia potencial.

**Kelly Criterion** — calcula el porcentaje óptimo de capital a arriesgar según tu win rate y RR históricos. Muestra Full Kelly, Half Kelly (recomendado) y Quarter Kelly.

**Simulación Monte Carlo** — simula N sesiones de trading con tu win rate y RR para calcular la probabilidad de ruina. Grafica 50 trayectorias de capital y muestra percentiles.

### 📰 Calendario Económico
19 eventos recurrentes semanales (NFP, CPI, FOMC, Jobless Claims, ECB, BoE, ISM, ADP, etc.) con hora en CDMX. Filtros por moneda, impacto y "solo hoy". Panel de próximos eventos. Alerta automática cuando hay evento de alto impacto en los próximos 90 minutos. Link directo a Forex Factory para datos en tiempo real.

### 🤖 Bot Telegram
Panel de configuración del bot: Chat ID, umbral de confianza, timeframe a monitorear, activos a vigilar, activar/desactivar resumen diario y alertas automáticas. Gestión de alertas de precio (sobre/bajo un nivel). Historial de señales de las últimas 72 horas.

### 📚 Guía SMC
Manual de referencia interactivo con explicaciones de BOS, CHoCH, IPDA, Order Blocks, FVG, zonas de liquidez, sesiones de mayor liquidez y checklist completo antes de entrar a un trade.

---

## Bot de Telegram — Configuración

### Paso 1 — Crear el bot
1. Abre Telegram y busca **@BotFather**
2. Envía `/newbot` y sigue los pasos
3. Copia el **TOKEN** que te da BotFather

### Paso 2 — Obtener tu Chat ID
1. Habla con tu bot recién creado
2. Envía `/start`
3. El bot te responde con tu **Chat ID**

### Paso 3 — Configurar en la app
1. En la app, ve a **🤖 Bot Telegram**
2. Pega tu Chat ID en el campo correspondiente
3. Haz clic en **Guardar configuración**

### Paso 4 — Ejecutar el bot
```bash
# En .env pon:
TELEGRAM_BOT_TOKEN=tu_token_aqui

# Luego ejecuta:
python bot/telegram_bot.py
```

### Comandos disponibles
| Comando | Función |
|---|---|
| `/start` | Bienvenida y tu Chat ID |
| `/mercado` | Resumen de 5 activos en tiempo real |
| `/señales` | Señales SMC activas (≥ umbral configurado) |
| `/noticias` | Eventos económicos del día en hora CDMX |
| `/alertas` | Historial de señales de las últimas 24h |
| `/resumen` | Reporte diario completo con sesiones |
| `/ayuda` | Lista de todos los comandos |

### Jobs automáticos del bot
- **Cada 5 min** — verifica alertas de precio configuradas
- **Cada 15 min** — escanea activos en busca de señales SMC de alta confianza
- **8:00 AM CDMX** — envía resumen diario con estado del mercado y eventos del día
- **Bloqueo automático** — no envía señales ±30 min de eventos High Impact

---

## Base de datos — Tablas

| Tabla | Contenido |
|---|---|
| `users` | Usuarios con capital inicial y configuración |
| `trades` | Historial de operaciones enriquecido |
| `watchlist` | Lista de activos favoritos por usuario |
| `price_alerts` | Alertas de precio (sobre/bajo nivel) |
| `bot_config` | Configuración del bot Telegram por usuario |
| `signal_log` | Log de señales generadas por el motor SMC |
| `backtest_results` | Resultados de backtests guardados |

---

## Activos disponibles

| Categoría | Tickers |
|---|---|
| Forex | EURUSD=X, GBPUSD=X, USDJPY=X, USDCHF=X, AUDUSD=X, USDCAD=X, NZDUSD=X |
| Índices | ^GSPC, ^NDX, ^DJI, ^FTSE, ^N225 |
| Cripto | BTC-USD, ETH-USD, SOL-USD, BNB-USD |
| Materias | GC=F (Oro), SI=F (Plata), CL=F (Petróleo), NG=F (Gas) |

---

## Temporalidades disponibles

1m · 5m · 15m · 30m · 1h · 4h · 1d · 1wk

El timeframe 4h se construye resampleando desde 1h (yfinance no lo tiene nativo).

---

## Indicadores técnicos calculados

EMA 9 · EMA 20 · EMA 50 · EMA 200 · ATR (14) · RSI (14) · MACD (12/26/9) · Bollinger Bands (20,2) · Volumen relativo · Retornos 1/5/10 períodos

---

## Motor SMC — Qué detecta

- **BOS** (Break of Structure) — ruptura en dirección de la tendencia
- **CHoCH** (Change of Character) — posible reversión de tendencia
- **Order Blocks** — zonas institucionales filtradas por impulso ATR
- **Fair Value Gaps** — desequilibrios de precio con tamaño mínimo relativo al ATR
- **Equal Highs / Equal Lows** — trampas de liquidez
- **Score de confluencia** — puntuación 0-100% combinando EMA, RSI, MACD y volumen

---

## Dependencias

```
streamlit>=1.35.0
yfinance>=0.2.40
pandas>=2.0.0
numpy>=1.26.0
plotly>=5.20.0
scikit-learn>=1.4.0
python-telegram-bot>=20.0
```

Python 3.9+ requerido. No se usa `pytz` — la zona horaria CDMX se maneja con `zoneinfo` de la stdlib.

---

## ⚠️ Aviso importante

Esta herramienta es un apoyo para el análisis, no un sistema automático de trading. Las señales son orientativas y deben validarse antes de operar. Los mercados financieros implican riesgo real de pérdida de capital. Se recomienda practicar en cuenta demo al menos 3 meses antes de usar capital real. El modelo de IA requiere mínimo 20 trades registrados para ser estadísticamente relevante.
