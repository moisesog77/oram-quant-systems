"""
utils/market_data.py — ORAM Quant Systems — Capa de Datos de Mercado
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fuente principal : Twelve Data API (tiempo real, latencia ~1 min)
Fuente de respaldo: yfinance (latencia 15 min, solo si Twelve Data falla)
Fuente demo      : datos sintéticos cuando ninguna API está disponible

Función pública:
  obtener_datos(ticker, timeframe) → (DataFrame | None, str_status)

Ticker mapping Twelve Data:
  yfinance usa sufijos (EURUSD=X, ^GSPC) — Twelve Data usa símbolos limpios.
  La función _td_symbol() convierte automáticamente.
"""
import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo
import warnings
warnings.filterwarnings("ignore")

# ── Caché en memoria con TTL por timeframe ────────────────────────────────────
# Evita rate limits de Twelve Data (8 req/min en plan gratuito) y acelera
# el panel multi-activo que llama obtener_datos() para cada ticker+timeframe.
_DATA_CACHE: dict = {}

def _cache_ttl(timeframe: str) -> int:
    """
    TTL dinámico que distribuye las 800 llamadas/día de Twelve Data (plan gratuito)
    concentrando la frescura en las horas de mayor calidad de mercado.

    Presupuesto recalculado con job_monitoreo_scalp activo (c/90s pide 5m+15m x3):
      GOLDEN   UTC 13-16  (CDMX 07-10): NY open — 5m c/~3min, 15m c/~4.5min → ~354 calls
      ACTIVE   UTC 07-13  (CDMX 01-07): London + pre-NY                     → ~245 calls
               UTC 16-19  (CDMX 10-13): continuación NY
      MODERATE UTC 19-22  (CDMX 13-16): tarde NY                            → ~102 calls
      QUIET    UTC 22-07  (CDMX 16-01): cierre/asiática                     →  ~40 calls
                                                              Total estimado: ~741/800
    (base15=90 en GOLDEN agotaba la cuota ~4 PM CDMX y forzaba yfinance el resto del día)
    """
    from datetime import datetime, timezone
    h = datetime.now(timezone.utc).hour

    if 13 <= h < 16:                        # GOLDEN: NY open
        base15, base1h = 180, 600
    elif (7 <= h < 13) or (16 <= h < 19):  # ACTIVE: London + continuación NY
        base15, base1h = 420, 1800
    elif 19 <= h < 22:                      # MODERATE: tarde NY
        base15, base1h = 900, 3600
    else:                                    # QUIET: asiática / madrugada
        base15, base1h = 1800, 7200

    return {
        "1m":  max(30,  base15 // 3),
        "5m":  max(60,  base15 // 2),
        "15m": base15,
        "30m": base15 * 2,
        "1h":  base1h,
        "4h":  base1h * 2,
        "1d":  7200,
        "1wk": 14400,
    }.get(timeframe, base15)

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

# ── Configuración Twelve Data ─────────────────────────────────────────────────
# El API key se carga desde variable de entorno TWELVE_DATA_KEY o desde
# el archivo .streamlit/secrets.toml (clave: TWELVE_DATA_KEY).
# Si no está configurado, el sistema cae automáticamente a yfinance.

def _get_td_key():
    """Obtiene el API key de Twelve Data desde secrets o env."""
    try:
        import streamlit as st
        key = st.secrets.get("TWELVE_DATA_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("TWELVE_DATA_KEY", "")

TZ_MX = ZoneInfo("America/Mexico_City")

# ── Mapeo de timeframes ────────────────────────────────────────────────────────
# Twelve Data usa intervalos específicos; yfinance usa period+interval.
TIMEFRAME_CONFIG = {
    "1m":  {"td_interval": "1min",  "td_outputsize": 390,  "yf_interval": "1m",  "yf_period": "1d"},
    "5m":  {"td_interval": "5min",  "td_outputsize": 288,  "yf_interval": "5m",  "yf_period": "2d"},
    "15m": {"td_interval": "15min", "td_outputsize": 300,  "yf_interval": "15m", "yf_period": "5d"},
    "30m": {"td_interval": "30min", "td_outputsize": 200,  "yf_interval": "30m", "yf_period": "10d"},
    "1h":  {"td_interval": "1h",    "td_outputsize": 200,  "yf_interval": "60m", "yf_period": "30d"},
    "4h":  {"td_interval": "4h",    "td_outputsize": 200,  "yf_interval": "1h",  "yf_period": "60d"},
    "1d":  {"td_interval": "1day",  "td_outputsize": 300,  "yf_interval": "1d",  "yf_period": "1y"},
    "1wk": {"td_interval": "1week", "td_outputsize": 100,  "yf_interval": "1wk", "yf_period": "5y"},
}

ACTIVOS_DEFAULT = {
    "Forex":    ["EURUSD=X", "GBPUSD=X"],
    "Materias": ["GC=F"],
}

# ── Mapeo de símbolos yfinance → Twelve Data ──────────────────────────────────
_TD_SYMBOL_MAP = {
    # Forex
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "USDCHF=X": "USD/CHF", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD",
    "NZDUSD=X": "NZD/USD", "EURGBP=X": "EUR/GBP", "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY", "USDMXN=X": "USD/MXN",
    # Índices
    "^GSPC": "SPX", "^NDX": "NDX", "^DJI": "DJI",
    "^FTSE": "FTSE", "^N225": "N225",
    # Cripto
    "BTC-USD": "BTC/USD", "ETH-USD": "ETH/USD",
    "SOL-USD": "SOL/USD", "BNB-USD": "BNB/USD",
    # Materias primas
    "GC=F": "XAU/USD", "SI=F": "XAG/USD", "CL=F": "WTI/USD", "NG=F": "NATGAS/USD",
}

def _td_symbol(ticker: str) -> str:
    """Convierte símbolo yfinance al formato Twelve Data."""
    return _TD_SYMBOL_MAP.get(ticker, ticker.replace("=X", "").replace("-", "/").replace("^", ""))


def mercado_cerrado() -> bool:
    """True si los mercados Forex y materias están cerrados (sábado completo, domingo antes 22h UTC, viernes después 22h UTC)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    wd, h = now.weekday(), now.hour
    if wd == 5: return True
    if wd == 6 and h < 22: return True
    if wd == 4 and h >= 22: return True
    return False


# ── Indicadores técnicos (compartido entre ambas fuentes) ─────────────────────
def _agregar_indicadores(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Calcula EMA9/20/50/200, ATR, RSI, MACD y Bandas de Bollinger.
    Operación inplace-safe: trabaja sobre una copia y la retorna.
    """
    c = df["Close"]
    df["EMA9"]   = c.ewm(span=9,   adjust=False).mean()
    df["EMA20"]  = c.ewm(span=20,  adjust=False).mean()
    df["EMA50"]  = c.ewm(span=50,  adjust=False).mean()
    df["EMA200"] = c.ewm(span=200, adjust=False).mean()
    # ATR
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"]  - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    # RSI
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    # MACD
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    # Histograma MACD = MACD - Signal (usado en la gráfica de live_analysis)
    df["MACD_hist"]   = df["MACD"] - df["MACD_signal"]
    # Bollinger Bands
    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    df["BB_upper"] = sma20 + 2 * std20
    df["BB_lower"] = sma20 - 2 * std20
    df["BB_mid"]   = sma20
    # Ratio de volumen (volumen actual / promedio 20 velas)
    # Usado por smc_engine para validar OBs institucionales
    if "Volume" in df.columns:
        vol_avg = df["Volume"].rolling(20).mean()
        df["Vol_ratio"] = df["Volume"] / vol_avg.replace(0, float("nan"))
    return df


def _validar_datos(df: pd.DataFrame, ticker: str) -> tuple[bool, str]:
    """Valida integridad del DataFrame OHLCV."""
    if df is None or df.empty:
        return False, f"Sin datos para {ticker}"
    required = {"Open", "High", "Low", "Close"}
    missing  = required - set(df.columns)
    if missing:
        return False, f"Columnas faltantes: {missing}"
    if len(df) < 10:
        return False, f"Muy pocas velas ({len(df)}), datos insuficientes"
    bad = df[df["High"] < df["Low"]].shape[0]
    if bad > 0:
        return False, f"{bad} velas con High < Low (datos corruptos)"
    return True, "OK"


# ── Fuente 1: Twelve Data API (tiempo real) ───────────────────────────────────
def _obtener_twelve_data(ticker: str, timeframe: str) -> pd.DataFrame | None:
    """
    Descarga datos OHLCV desde Twelve Data API.

    Twelve Data retorna las velas más recientes en orden descendente (newest first).
    Las convertimos a orden ascendente para compatibilidad con el engine SMC.

    Retorna DataFrame o None si falla.
    """
    api_key = _get_td_key()
    if not api_key:
        return None

    cfg    = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["15m"])
    symbol = _td_symbol(ticker)

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol":     symbol,
        "interval":   cfg["td_interval"],
        "outputsize": cfg["td_outputsize"],
        "apikey":     api_key,
        "format":     "JSON",
        "order":      "ASC",     # más antigua primero
        "timezone":   "UTC",     # forzar UTC para conversión CDMX consistente
    }

    import logging as _log
    _logger = _log.getLogger(__name__)

    for intento in range(2):  # 1 reintento si hay timeout
        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            # Twelve Data retorna {"code": 4xx, "message": "..."} en errores
            if "code" in data or ("status" in data and data.get("status") == "error"):
                _logger.warning(
                    f"Twelve Data error [{ticker}]: code={data.get('code')} msg={data.get('message','')}"
                )
                return None

            values = data.get("values", [])
            if not values:
                return None

            df = pd.DataFrame(values)
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.set_index("datetime")
            df = df.rename(columns={
                "open": "Open", "high": "High",
                "low":  "Low",  "close": "Close", "volume": "Volume"
            })
            for col in ["Open", "High", "Low", "Close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            if "Volume" in df.columns:
                df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)

            df = df.dropna(subset=["Open", "High", "Low", "Close"])

            # Localizar a CDMX para consistencia con el resto del sistema
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            df.index = df.index.tz_convert(TZ_MX)

            return df

        except requests.exceptions.Timeout:
            _logger.warning(f"Twelve Data timeout [{ticker}] intento {intento+1}/2")
            if intento == 0:
                time.sleep(3)   # esperar 3s antes del reintento
                continue
            return None
        except Exception as e:
            _logger.warning(f"Twelve Data excepción [{ticker}]: {e}")
            return None


# ── Fuente 2: yfinance (respaldo) ─────────────────────────────────────────────
def _aplanar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas MultiIndex que genera yfinance."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    standard = {"open": "Open", "high": "High", "low": "Low",
                "close": "Close", "volume": "Volume"}
    rename = {col: standard[str(col).strip().lower()]
              for col in df.columns if str(col).strip().lower() in standard}
    return df.rename(columns=rename) if rename else df


def _obtener_yfinance(ticker: str, timeframe: str) -> pd.DataFrame | None:
    """
    Descarga datos desde yfinance como fuente de respaldo.
    Latencia: ~15 minutos en intradía.
    """
    if not YF_AVAILABLE:
        return None
    cfg = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["15m"])
    try:
        raw = yf.download(
            ticker, period=cfg["yf_period"], interval=cfg["yf_interval"],
            progress=False, auto_adjust=True, multi_level_index=False
        )
        if raw.empty:
            raw = yf.download(
                ticker, period=cfg["yf_period"], interval=cfg["yf_interval"],
                progress=False, auto_adjust=True
            )
        raw = _aplanar_columnas(raw)

        # Resamplear a 4h si es necesario (yfinance no ofrece 4h directo)
        if timeframe == "4h" and not raw.empty:
            agg = {}
            if "Open"   in raw.columns: agg["Open"]   = "first"
            if "High"   in raw.columns: agg["High"]   = "max"
            if "Low"    in raw.columns: agg["Low"]    = "min"
            if "Close"  in raw.columns: agg["Close"]  = "last"
            if "Volume" in raw.columns: agg["Volume"] = "sum"
            raw = raw.resample("4h").agg(agg).dropna()

        if not raw.empty:
            try:
                if raw.index.tz is None:
                    raw.index = raw.index.tz_localize("UTC")
                raw.index = raw.index.tz_convert(TZ_MX)
            except Exception:
                pass

        return raw if not raw.empty else None
    except Exception:
        return None


# ── Fuente 3: datos demo sintéticos ───────────────────────────────────────────
def _generar_datos_demo(ticker: str, timeframe: str) -> pd.DataFrame:
    """
    Genera datos OHLCV sintéticos realistas cuando ninguna API está disponible.
    Usado en modo demo / desarrollo sin conexión.
    """
    np.random.seed(abs(hash(ticker)) % 9999)
    n    = 200
    freq_map = {"1m": "1min", "5m": "5min", "15m": "15min",
                "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D"}
    freq = freq_map.get(timeframe, "15min")
    idx  = pd.date_range(end=datetime.now(), periods=n, freq=freq)
    base = {
        "EURUSD=X": 1.08, "GBPUSD=X": 1.27, "USDJPY=X": 149.5,
        "BTC-USD": 65000,  "ETH-USD": 3200,  "^GSPC":    5200,
    }.get(ticker, 100.0)
    log_ret = np.random.randn(n) * 0.0008
    close   = base * np.exp(np.cumsum(log_ret))
    noise   = base * 0.001
    high    = close + abs(np.random.randn(n)) * noise
    low     = close - abs(np.random.randn(n)) * noise
    open_   = np.roll(close, 1); open_[0] = close[0]
    vol     = np.random.randint(500, 5000, n).astype(float)
    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=idx
    )
    return _agregar_indicadores(df, timeframe)


# ── Función pública principal ─────────────────────────────────────────────────
def obtener_datos(ticker: str, timeframe: str = "15m") -> tuple:
    """
    Descarga y valida datos OHLCV con fallback en cascada y caché TTL:

    Prioridad:
      1. Caché en memoria   — devuelve datos frescos si están dentro del TTL
      2. Twelve Data API    — tiempo real, latencia ~1 min (requiere TWELVE_DATA_KEY)
      3. yfinance           — respaldo, latencia ~15 min
      4. datos demo         — sintéticos, sin conexión

    Retorna:
      (DataFrame con indicadores, str con status/mensaje)
    """
    cache_key = (ticker, timeframe)
    ttl       = _cache_ttl(timeframe)
    now       = time.time()

    # ── Intento 0: caché ─────────────────────────────────────────────────────
    if cache_key in _DATA_CACHE:
        ts, df_cached, status_cached = _DATA_CACHE[cache_key]
        if now - ts < ttl:
            return df_cached, status_cached

    # ── Intento 1: Twelve Data ────────────────────────────────────────────────
    td_key = _get_td_key()
    if td_key:
        df_td = _obtener_twelve_data(ticker, timeframe)
        if df_td is not None:
            valid, msg = _validar_datos(df_td, ticker)
            if valid:
                df_td = _agregar_indicadores(df_td.copy(), timeframe)
                last_price = df_td["Close"].iloc[-1]
                last_time  = df_td.index[-1]
                n_velas    = len(df_td)
                status = (
                    f"✅ {n_velas} velas · Último: {last_price:.5f} · "
                    f"{last_time.strftime('%Y-%m-%d %H:%M')} CDMX · 🟢 Tiempo real"
                )
                _DATA_CACHE[cache_key] = (now, df_td, status)
                return df_td, status

    # ── Intento 2: yfinance ───────────────────────────────────────────────────
    if YF_AVAILABLE:
        df_yf = _obtener_yfinance(ticker, timeframe)
        if df_yf is not None:
            valid, msg = _validar_datos(df_yf, ticker)
            if valid:
                df_yf = _agregar_indicadores(df_yf.copy(), timeframe)
                last_price = df_yf["Close"].iloc[-1]
                last_time  = df_yf.index[-1]
                n_velas    = len(df_yf)
                status = (
                    f"✅ {n_velas} velas · Último: {last_price:.5f} · "
                    f"{last_time.strftime('%Y-%m-%d %H:%M')} CDMX · ⚠️ yfinance (15min delay)"
                )
                _DATA_CACHE[cache_key] = (now, df_yf, status)
                return df_yf, status

    # ── Intento 3: datos demo ─────────────────────────────────────────────────
    df_demo = _generar_datos_demo(ticker, timeframe)
    return df_demo, "🔴 DEMO — Sin conexión a APIs. Datos sintéticos, NO usar para operar."
