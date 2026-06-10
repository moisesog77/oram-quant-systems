"""
utils/market_data.py — Descarga y validación de datos de mercado.
Usa yfinance con verificación de integridad de datos.
Sin pytz — usa zoneinfo (stdlib Python 3.9+).
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import warnings
warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

TZ_MX = ZoneInfo("America/Mexico_City")

TIMEFRAME_CONFIG = {
    "1m":  {"interval": "1m",  "period": "1d"},
    "5m":  {"interval": "5m",  "period": "2d"},
    "15m": {"interval": "15m", "period": "5d"},
    "30m": {"interval": "30m", "period": "10d"},
    "1h":  {"interval": "60m", "period": "30d"},
    "4h":  {"interval": "1h",  "period": "60d"},
    "1d":  {"interval": "1d",  "period": "1y"},
    "1wk": {"interval": "1wk", "period": "5y"},
}

ACTIVOS_DEFAULT = {
    "Forex":    ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", "USDCAD=X", "NZDUSD=X"],
    "Índices":  ["^GSPC", "^NDX", "^DJI", "^FTSE", "^N225"],
    "Cripto":   ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"],
    "Materias": ["GC=F", "SI=F", "CL=F", "NG=F"],
}


def _aplanar_columnas(df):
    """Normaliza columnas de yfinance (MultiIndex o nombres variados)."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    standard = {'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'}
    rename = {col: standard[str(col).strip().lower()]
              for col in df.columns if str(col).strip().lower() in standard}
    return df.rename(columns=rename) if rename else df

def _validar_datos(df: pd.DataFrame, ticker: str) -> tuple[bool, str]:
    if df is None or df.empty:
        return False, f"Sin datos para {ticker}"
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        return False, f"Columnas faltantes: {missing}"
    if len(df) < 10:
        return False, f"Muy pocas velas ({len(df)}), datos insuficientes"
    bad_candles = df[df['High'] < df['Low']].shape[0]
    if bad_candles > 0:
        return False, f"{bad_candles} velas con High < Low (datos corruptos)"
    nan_pct = df[list(required)].isna().mean().max()
    if nan_pct > 0.1:
        return False, f"Más del 10% de datos NaN ({nan_pct:.0%})"
    last_dt = df.index[-1]
    if hasattr(last_dt, 'tzinfo') and last_dt.tzinfo:
        last_dt = last_dt.replace(tzinfo=None)
    age = datetime.now() - last_dt
    if age > timedelta(days=5):
        return False, f"Datos muy antiguos (último: {last_dt.strftime('%Y-%m-%d')})"
    return True, "OK"


def _agregar_indicadores(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    c = df['Close'].astype(float)
    h = df['High'].astype(float)
    l = df['Low'].astype(float)
    df['EMA9']   = c.ewm(span=9,   adjust=False).mean()
    df['EMA20']  = c.ewm(span=20,  adjust=False).mean()
    df['EMA50']  = c.ewm(span=50,  adjust=False).mean()
    df['EMA200'] = c.ewm(span=200, adjust=False).mean()
    tr1 = h - l
    tr2 = (h - c.shift(1)).abs()
    tr3 = (l - c.shift(1)).abs()
    df['TR']  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = df['TR'].ewm(span=14, adjust=False).mean()
    delta = c.diff()
    gain  = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    rs    = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df['MACD']        = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist']   = df['MACD'] - df['MACD_signal']
    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    df['BB_upper'] = sma20 + 2 * std20
    df['BB_lower'] = sma20 - 2 * std20
    df['BB_mid']   = sma20
    if 'Volume' in df.columns:
        vol = df['Volume'].astype(float)
        df['Vol_SMA20'] = vol.rolling(20).mean()
        df['Vol_ratio'] = vol / df['Vol_SMA20'].replace(0, np.nan)
    df['return_1']  = c.pct_change(1)
    df['return_5']  = c.pct_change(5)
    df['return_10'] = c.pct_change(10)
    if timeframe == "4h":
        df.attrs['resampled'] = True
    return df


def obtener_datos(ticker: str, timeframe: str = "15m") -> tuple:
    if not YF_AVAILABLE:
        return _generar_datos_demo(ticker, timeframe), "⚠️ Modo demo (yfinance no instalado)"
    cfg = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["15m"])
    try:
        raw = yf.download(ticker, period=cfg["period"], interval=cfg["interval"],
                          progress=False, auto_adjust=True, multi_level_index=False)
        if raw.empty:
            # Retry without multi_level_index param (older yfinance)
            raw = yf.download(ticker, period=cfg["period"], interval=cfg["interval"],
                              progress=False, auto_adjust=True)
        raw = _aplanar_columnas(raw)
        # Ensure standard column names exist
        rename_map = {}
        for col in raw.columns:
            col_lower = str(col).lower().strip()
            for standard in ["Open","High","Low","Close","Volume"]:
                if col_lower == standard.lower():
                    rename_map[col] = standard
        if rename_map:
            raw = raw.rename(columns=rename_map)
        if timeframe == "4h" and not raw.empty:
            agg_dict = {}
            if "Open"   in raw.columns: agg_dict["Open"]   = "first"
            if "High"   in raw.columns: agg_dict["High"]   = "max"
            if "Low"    in raw.columns: agg_dict["Low"]    = "min"
            if "Close"  in raw.columns: agg_dict["Close"]  = "last"
            if "Volume" in raw.columns: agg_dict["Volume"] = "sum"
            raw = raw.resample('4h').agg(agg_dict).dropna()
        if not raw.empty:
            try:
                raw.index = raw.index.tz_convert('America/Mexico_City')
            except Exception:
                pass
        valid, msg = _validar_datos(raw, ticker)
        if not valid:
            return None, f"❌ {msg}"
        df = _agregar_indicadores(raw.copy(), timeframe)
        last_price = df['Close'].iloc[-1]
        last_time  = df.index[-1]
        return df, f"✅ {len(df)} velas · Último: {last_price:.5f} · {last_time.strftime('%Y-%m-%d %H:%M')}"
    except Exception as e:
        return None, f"❌ Error descargando {ticker}: {str(e)[:80]}"


def _generar_datos_demo(ticker: str, timeframe: str) -> pd.DataFrame:
    np.random.seed(abs(hash(ticker)) % 9999)
    n = 200
    freq_map = {"1m": "1min", "5m": "5min", "15m": "15min",
                "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D"}
    freq = freq_map.get(timeframe, "15min")
    idx  = pd.date_range(end=datetime.now(), periods=n, freq=freq)
    base = {"EURUSD=X": 1.08, "GBPUSD=X": 1.27, "USDJPY=X": 149.5,
            "BTC-USD": 65000, "ETH-USD": 3200, "^GSPC": 5200}.get(ticker, 100.0)
    log_returns = np.random.randn(n) * 0.0008
    close = base * np.exp(np.cumsum(log_returns))
    noise = base * 0.001
    high  = close + abs(np.random.randn(n)) * noise
    low   = close - abs(np.random.randn(n)) * noise
    open_ = np.roll(close, 1); open_[0] = close[0]
    vol   = np.random.randint(500, 5000, n).astype(float)
    df = pd.DataFrame({'Open': open_, 'High': high, 'Low': low,
                       'Close': close, 'Volume': vol}, index=idx)
    return _agregar_indicadores(df, timeframe)

