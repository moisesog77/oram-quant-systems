"""
utils/news_feed.py — ORAM Quant Systems — Noticias de Mercado en Tiempo Real
Fuente: Yahoo Finance (yfinance) — mismas fuentes que TradingView (Reuters, Bloomberg, etc.)
Cache 15 min para no saturar peticiones. Titulares traducidos al español automáticamente.
"""
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TZ_MX = ZoneInfo("America/Mexico_City")

_TRAD_CACHE: dict = {}   # cache de traducciones: texto_en → texto_es


def _traducir_es(texto: str) -> str:
    """Traduce al español con Google (gratuito, sin API key). Falla silenciosamente."""
    if not texto:
        return texto
    if texto in _TRAD_CACHE:
        return _TRAD_CACHE[texto]
    try:
        from deep_translator import GoogleTranslator
        resultado = GoogleTranslator(source="auto", target="es").translate(texto) or texto
        _TRAD_CACHE[texto] = resultado
        return resultado
    except Exception:
        return texto


_TICKERS_NOTICIAS = {
    "Forex":    ["EURUSD=X", "GBPUSD=X", "USDJPY=X"],
    "Oro":      ["GC=F"],
    "Mercados": ["^GSPC", "^DJI"],
}

_CACHE: dict = {}
_TTL = 900  # 15 minutos


def _relativo(ts: int) -> str:
    diff = max(0, int(time.time()) - ts)
    if diff < 60:    return "hace un momento"
    if diff < 3600:  return f"hace {diff // 60}min"
    if diff < 86400: return f"hace {diff // 3600}h"
    return f"hace {diff // 86400}d"


def _parsear_item(item: dict) -> dict | None:
    """Normaliza un item de yfinance (soporta formato antiguo y nuevo)."""
    try:
        # Formato nuevo: item["content"]["title"]
        content = item.get("content", {})
        titulo  = content.get("title") or item.get("title", "")
        fuente  = (content.get("provider", {}).get("displayName")
                   or item.get("publisher", ""))
        # Timestamp: string ISO o unix int
        pub_raw = content.get("pubDate") or ""
        if pub_raw:
            try:
                dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                ts = int(dt.timestamp())
            except Exception:
                ts = int(item.get("providerPublishTime", 0))
        else:
            ts = int(item.get("providerPublishTime", 0))

        if not titulo:
            return None
        titulo = _traducir_es(titulo)
        return {"titulo": titulo, "fuente": fuente, "tiempo": _relativo(ts), "ts": ts}
    except Exception:
        return None


def obtener_noticias_ticker(ticker: str, max_items: int = 4) -> list:
    """Noticias recientes de un ticker via yfinance. Cacheadas 15 min."""
    ahora = time.time()
    cached = _CACHE.get(ticker)
    if cached and ahora - cached["ts"] < _TTL:
        return cached["data"]
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker).news or []
        items = [n for item in raw if (n := _parsear_item(item)) is not None]
        items.sort(key=lambda x: x["ts"], reverse=True)
        result = items[:max_items]
        _CACHE[ticker] = {"ts": ahora, "data": result}
        return result
    except Exception:
        return []


def obtener_noticias_mercado(max_por_cat: int = 3) -> dict:
    """Noticias por categoría, deduplicadas por título."""
    resultado = {}
    vistos: set = set()
    for categoria, tickers in _TICKERS_NOTICIAS.items():
        items_cat = []
        for ticker in tickers:
            for n in obtener_noticias_ticker(ticker, max_por_cat + 2):
                clave = n["titulo"][:60].lower()
                if clave not in vistos:
                    vistos.add(clave)
                    items_cat.append(n)
        items_cat.sort(key=lambda x: x["ts"], reverse=True)
        if items_cat:
            resultado[categoria] = items_cat[:max_por_cat]
    return resultado


def formatear_noticias_telegram(max_por_cat: int = 3) -> str:
    """Bloque de noticias formateado para Telegram Markdown."""
    noticias = obtener_noticias_mercado(max_por_cat)
    if not noticias:
        return ""
    iconos = {"Forex": "🔵", "Oro": "🟡", "Mercados": "📈"}
    lineas = ["📰 *NOTICIAS DEL MERCADO*", "━━━━━━━━━━━━━━━━"]
    for cat, items in noticias.items():
        lineas.append(f"\n{iconos.get(cat,'📊')} *{cat}:*")
        for n in items:
            fuente = f" — _{n['fuente']}_" if n["fuente"] else ""
            tiempo = f" ({n['tiempo']})"   if n["tiempo"]  else ""
            lineas.append(f"• {n['titulo']}{fuente}{tiempo}")
    return "\n".join(lineas)


def contexto_noticia_ticker(ticker: str) -> str:
    """Una línea de contexto para adjuntar a una señal. Vacío si no hay noticias."""
    items = obtener_noticias_ticker(ticker, max_items=1)
    if not items:
        return ""
    n = items[0]
    fuente = f" — {n['fuente']}"  if n["fuente"] else ""
    tiempo = f" ({n['tiempo']})"  if n["tiempo"]  else ""
    return f"📰 _{n['titulo']}{fuente}{tiempo}_"


def contexto_noticias_activos(tickers: list, max_items: int = 2) -> str:
    """Titulares recientes de los tickers activos para justificar el estado del mercado."""
    items = []
    seen: set = set()
    for ticker in tickers:
        for n in obtener_noticias_ticker(ticker, max_items=3):
            clave = n["titulo"][:60].lower()
            if clave not in seen:
                seen.add(clave)
                items.append(n)
    items.sort(key=lambda x: x["ts"], reverse=True)
    if not items:
        return ""
    lineas = ["📰 *Contexto de mercado:*"]
    for n in items[:max_items]:
        fuente = f" — _{n['fuente']}_" if n["fuente"] else ""
        tiempo = f" ({n['tiempo']})"   if n["tiempo"]  else ""
        lineas.append(f"• {n['titulo']}{fuente}{tiempo}")
    return "\n".join(lineas)
