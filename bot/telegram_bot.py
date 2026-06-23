"""
bot/telegram_bot.py — ORAM Quant Systems Bot v3
Cubre el 100% de las capacidades de la aplicación:
  Análisis en Vivo · Multi-Timeframe · Diario de Trades · Performance & IA
  Backtesting · Risk Manager (Kelly+Ruina) · Watchlist · Panel de Señales
  Calendario Económico · Dashboard completo
"""
import os, sys, json, logging
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass

try:
    from telegram import Update
    from telegram.ext import (Application, CommandHandler,
                               MessageHandler, filters, ContextTypes)
    TELEGRAM_OK = True
except ImportError:
    TELEGRAM_OK = False

from utils.market_data       import obtener_datos
from utils.smc_engine        import analisis_completo, calcular_riesgo
from utils.multi_timeframe   import analisis_mtf, MTF_COMBOS
from utils.backtesting       import ejecutar_backtest
from utils.economic_calendar import (obtener_eventos_hoy, obtener_proximos_eventos,
                                      hay_evento_alto_impacto_pronto, impacto_emoji)
from utils.ai_engine         import analizar_performance_ia, calcular_drawdown, calcular_sharpe
from database.db import (
    obtener_todas_configs_bot, obtener_todas_alertas_activas,
    disparar_alerta, registrar_señal, marcar_señal_enviada,
    obtener_señales_recientes, inicializar_db,
    obtener_todos_usuarios, obtener_usuario_por_id,
    obtener_trades, obtener_watchlist,
    registrar_trade_confirmado, obtener_trade_activo,
    obtener_trades_activos_chat, obtener_todos_trades_activos,
    cerrar_trade_confirmado,
)

import pandas as pd

TZ_MX  = ZoneInfo("America/Mexico_City")
TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
MD     = "Markdown"

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

UMBRAL_ALERTA_ALTA  = 75
UMBRAL_ALERTA_MEDIA = 60
UMBRAL_MTF_ALINEADO = 65

# Deduplicación de alertas de noticias — evita enviar el mismo evento múltiples veces
_eventos_ya_alertados: set = set()

# Última señal enviada por chat — permite que /tomar la confirme sin especificar ticker
# Clave: chat_id → última señal general | (chat_id, ticker) → última señal de ese ticker
_ultimas_senales: dict = {}

# Persistencia MTF — dos niveles:
#   clave (chat_id, ticker, dir)       → checks consecutivos ≥63% para alerta de acción
#   clave (chat_id, ticker, dir, "w")  → checks consecutivos 60-62% para alerta de vigilancia
_mtf_persistencia: dict = {}
# Timestamp del último envío de alerta de vigilancia — dedup 2h
_watch_enviados: dict = {}

# Alerta de mercado en rango — dedup 2h por chat
_ultima_alerta_rango: dict = {}
_checks_sin_senal:    dict = {}   # chat_id → checks consecutivos sin señal


def _normalizar_ticker(s: str) -> str:
    """Convierte alias cortos al ticker real de yfinance/TwelveData."""
    _map = {
        "EURUSD": "EURUSD=X", "EUR":    "EURUSD=X",
        "GBPUSD": "GBPUSD=X", "GBP":    "GBPUSD=X",
        "USDJPY": "USDJPY=X", "JPY":    "USDJPY=X",
        "USDCHF": "USDCHF=X", "CHF":    "USDCHF=X",
        "AUDUSD": "AUDUSD=X", "AUD":    "AUDUSD=X",
        "USDCAD": "USDCAD=X", "CAD":    "USDCAD=X",
        "NZDUSD": "NZDUSD=X", "NZD":    "NZDUSD=X",
        "BTCUSD": "BTC-USD",  "BTC":    "BTC-USD",
        "ETHUSD": "ETH-USD",  "ETH":    "ETH-USD",
        "XAUUSD": "GC=F",     "GOLD":   "GC=F",   "XAU": "GC=F",
        "XAGUSD": "SI=F",     "SILVER": "SI=F",   "XAG": "SI=F",
        "WTIUSD": "CL=F",     "OIL":    "CL=F",   "WTI": "CL=F",
    }
    t = s.upper().replace("/", "")
    if t in _map: return _map[t]
    if t.endswith("=X") or "-" in t or t in ("GC=F", "CL=F", "SI=F", "NG=F"): return t
    return t + "=X"


def _calcular_pips(ticker: str, p1: float, p2: float) -> float:
    diff = abs(p1 - p2)
    if "JPY" in ticker: return round(diff * 100, 1)
    if "=X" in ticker or "/" in ticker: return round(diff * 10000, 1)
    return round(diff, 5)


# ─── Helpers de comunicación ──────────────────────────────────────────────────

async def _reply(update, text: str):
    try:
        if len(text) > 4000:
            text = text[:3990] + "\n_...truncado_"
        await update.message.reply_text(text, parse_mode=MD)
    except Exception:
        try:
            plain = text.replace("*","").replace("_","").replace("`","")
            await update.message.reply_text(plain[:4000])
        except Exception as e:
            logger.error(f"reply error: {e}")

async def _send(bot, chat_id: str, text: str):
    try:
        if len(text) > 4000:
            text = text[:3990] + "\n_...truncado_"
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=MD)
    except Exception:
        try:
            plain = text.replace("*","").replace("_","").replace("`","")
            await bot.send_message(chat_id=chat_id, text=plain[:4000])
        except Exception as e:
            logger.error(f"send error: {e}")


# ─── Helpers de análisis ──────────────────────────────────────────────────────

def _calcular_contexto(df) -> dict:
    """Evalúa si el mercado está en tendencia, lateral o comprimido usando ATR y EMAs."""
    try:
        atr_serie = df["ATR"].dropna()
        if len(atr_serie) < 10:
            return {}
        atr_actual = atr_serie.iloc[-1]
        atr_prom   = atr_serie.iloc[-20:].mean() if len(atr_serie) >= 20 else atr_serie.mean()
        atr_ratio  = atr_actual / atr_prom if atr_prom > 0 else 1.0
        e9  = df["EMA9"].iloc[-1]
        e20 = df["EMA20"].iloc[-1]
        e50 = df["EMA50"].iloc[-1]
        emas_alineadas = (e9 > e20 > e50) or (e9 < e20 < e50)
        if atr_ratio >= 1.15 and emas_alineadas:
            return {"tipo": "tendencia",  "icono": "✅", "texto": "Contexto: Tendencia activa — entrada favorable"}
        elif atr_ratio < 0.70:
            return {"tipo": "compresion", "icono": "⚠️", "texto": "Contexto: ATR muy comprimido — validar ruptura visualmente antes de entrar"}
        elif not emas_alineadas or atr_ratio < 0.90:
            return {"tipo": "lateral",    "icono": "⚠️", "texto": "Contexto: Mercado lateral — confirmar setup visualmente antes de entrar"}
        else:
            return {"tipo": "normal",     "icono": "📊", "texto": "Contexto: Volatilidad normal"}
    except Exception:
        return {}


def _analizar_activo(ticker: str, tf: str = "15m"):
    try:
        df, status = obtener_datos(ticker, tf)
        if df is None:
            return None, status
        smc = analisis_completo(df, ticker)
        smc["_contexto_mercado"] = _calcular_contexto(df)
        if "yfinance" in status:
            smc["_data_warning"] = "⚠️ Datos con 15min delay (yfinance) — Twelve Data no disponible"
        return smc, status
    except Exception as e:
        return None, str(e)

def _conf_bar(pct: float) -> str:
    filled = int(pct / 10)
    return "█" * filled + "░" * (10 - filled) + f" {pct:.0f}%"

def _emoji_dir(dir_: str) -> str:
    return "🟢" if dir_ == "LONG" else "🔴" if dir_ == "SHORT" else "⚪"

def _prioridad(conf: float) -> str:
    if conf >= 80: return "🔥 ALTA"
    if conf >= 65: return "⚡ MEDIA"
    return "💡 BAJA"

def _hora_mx() -> str:
    return datetime.now(TZ_MX).strftime("%H:%M")

def _en_horario_trading() -> bool:
    # Forex cierra viernes 22:00 UTC y abre domingo 22:00 UTC
    # Se compara en UTC para evitar bugs de DST entre CDMX y New York
    from datetime import timezone as _tz
    now_utc = datetime.now(_tz.utc)
    wd  = now_utc.weekday()  # 0=lun 4=vie 5=sáb 6=dom
    hut = now_utc.hour
    if wd == 5: return False                      # sábado completo cerrado
    if wd == 6 and hut < 22: return False         # domingo hasta las 22:00 UTC
    if wd == 4 and hut >= 22: return False        # viernes desde 22:00 UTC
    return True

def _get_user_by_chat(chat_id: str):
    """Obtiene usuario vinculado a este chat_id."""
    try:
        configs = obtener_todas_configs_bot()
        cfg = next((c for c in configs if c.get("telegram_chat_id") == chat_id), None)
        if not cfg: return None, None
        user = obtener_usuario_por_id(cfg["user_id"])
        return user, cfg
    except Exception:
        return None, None

def _formato_senal_completo(smc: dict, ticker: str, tf: str,
                              capital: float = 10000.0, riesgo_pct: float = 1.0) -> str:
    est      = smc.get("estructura", {})
    conf     = smc.get("confluencia", {})
    dir_     = est.get("direccion", "neutral")
    tipo     = est.get("tipo", "Sin señal")
    pct      = conf.get("confianza", 0)
    precio   = smc.get("precio", 0)
    sl       = smc.get("sl_sugerido", 0)
    tp       = smc.get("tp_sugerido", 0)
    atr      = smc.get("atr", 0)
    rsi      = smc.get("rsi", 0) or 0
    ema50    = smc.get("ema50", 0) or 0
    factores = conf.get("factores", [])
    emoji    = _emoji_dir(dir_)
    prio     = _prioridad(pct)

    riesgo_info = {}
    if sl and tp and precio:
        riesgo_info = calcular_riesgo(precio, sl, tp, capital, riesgo_pct) or {}

    rr       = riesgo_info.get("rr", 0)
    lote     = riesgo_info.get("lot_size", 0)
    ganancia = riesgo_info.get("ganancia_pot", 0)

    tipo_entrada    = smc.get("tipo_entrada", "mercado")
    entrada_ideal   = smc.get("precio_entrada_ideal")
    retroceso_pips  = smc.get("retroceso_pips", 0)

    if tipo_entrada == "limite_ob" and entrada_ideal:
        entrada_txt = f"📍 *Entrada:* Límite en OB `{entrada_ideal:.5f}` (~{retroceso_pips:.0f} pips ↓)"
    elif tipo_entrada == "limite_fvg" and entrada_ideal:
        entrada_txt = f"📍 *Entrada:* Límite en FVG `{entrada_ideal:.5f}` (~{retroceso_pips:.0f} pips ↓)"
    else:
        entrada_txt = f"📍 *Entrada:* Mercado (precio ya en zona)"

    ctx     = smc.get("_contexto_mercado", {})
    ctx_txt = f"{ctx.get('icono','')} _{ctx.get('texto','')}_" if ctx.get("texto") else ""

    lineas = [
        f"{'🚨' if pct >= 75 else '📡'} *SEÑAL SMC — {prio}*",
        f"{emoji} *{ticker}* · {tf}",
        "━━━━━━━━━━━━━━━━",
        f"📌 *Señal:* {tipo}",
        f"💰 *Precio actual:* `{precio:.5f}`",
        f"📊 *Dirección:* {emoji} {dir_}",
        entrada_txt,
        f"🎯 *Confianza:* {_conf_bar(pct)}",
        ctx_txt,
        "",
    ]
    if sl and tp:
        lineas += [
            f"🛑 *SL:* `{sl:.5f}`",
            f"✅ *TP:* `{tp:.5f}`",
            f"⚖️ *RR:* {rr:.1f}:1" if rr else "",
        ]
    if lote:
        lineas += [
            "",
            f"💼 *Gestión ({riesgo_pct}% riesgo):*",
            f"   Lote: {lote:.3f}",
            f"   Riesgo: ${capital * riesgo_pct / 100:.0f}",
            f"   Ganancia pot.: ${ganancia:.0f}",
        ]
    lineas += [
        "",
        f"📉 *RSI:* {rsi:.1f}  |  📏 *ATR:* {atr:.5f}",
        f"📈 *EMA50:* {ema50:.5f}" if ema50 else "",
    ]
    if factores:
        lineas += ["", "⚡ *Confluencias:*"]
        for f in factores:
            lineas.append(f"  ✔ {f}")
    lineas += ["", f"🕐 *{_hora_mx()} CDMX*", "⚠️ _Señal orientativa. Usa SL siempre._"]
    data_warning = smc.get("_data_warning")
    if data_warning:
        lineas.append(f"\n_{data_warning}_")
    return "\n".join(l for l in lineas if l)

def _formato_mtf(mtf: dict, ticker: str, contexto: dict = None) -> str:
    smc_alto  = mtf.get("smc_alto") or {}
    smc_bajo  = mtf.get("smc_bajo") or {}
    tf_alto   = mtf.get("tf_alto", "?")
    tf_bajo   = mtf.get("tf_bajo", "?")
    alineado  = mtf.get("alineacion", False)
    desc      = mtf.get("descripcion", "")
    conf_mtf  = mtf.get("confianza_mtf", 0)
    entrada   = mtf.get("entrada_sugerida")
    sl        = mtf.get("sl_sugerido")
    tp        = mtf.get("tp_sugerido")
    dir_alto  = smc_alto.get("estructura", {}).get("direccion", "neutral")
    dir_bajo  = smc_bajo.get("estructura", {}).get("direccion", "neutral")
    conf_alto = smc_alto.get("confluencia", {}).get("confianza", 0)
    conf_bajo = smc_bajo.get("confluencia", {}).get("confianza", 0)
    tipo_alto = smc_alto.get("estructura", {}).get("tipo", "?")
    tipo_bajo = smc_bajo.get("estructura", {}).get("tipo", "?")
    estado    = "✅ *ALINEADO*" if alineado else "⚠️ *No alineado*"

    lineas = [
        "🔭 *ANÁLISIS MULTI-TIMEFRAME*",
        f"🎯 *{ticker}* — {tf_alto}/{tf_bajo}",
        "━━━━━━━━━━━━━━━━",
        f"📐 Estado MTF: {estado}",
        f"🎯 Confianza MTF: {_conf_bar(conf_mtf)}",
        "",
        f"*TF Alto ({tf_alto}) — Estructura:*",
        f"  {_emoji_dir(dir_alto)} {tipo_alto} ({conf_alto:.0f}%)",
        "",
        f"*TF Bajo ({tf_bajo}) — Entrada:*",
        f"  {_emoji_dir(dir_bajo)} {tipo_bajo} ({conf_bajo:.0f}%)",
    ]
    if alineado and entrada:
        lineas += [
            "",
            f"💰 *Entrada sugerida:* `{entrada:.5f}`",
            f"🛑 *SL:* `{sl:.5f}`" if sl else "",
            f"✅ *TP:* `{tp:.5f}`" if tp else "",
        ]
    ctx_txt = ""
    if contexto and contexto.get("texto"):
        ctx_txt = f"{contexto.get('icono','')} _{contexto.get('texto','')}_"
    lineas += ["", f"📝 _{desc}_", ctx_txt, "", f"🕐 {_hora_mx()} CDMX"]
    return "\n".join(l for l in lineas if l)


def _formato_reversal(smc_alto: dict, smc_bajo: dict, ticker: str,
                       tf_alto: str, tf_bajo: str, nivel_redondo: bool = False) -> str:
    dir_      = smc_bajo.get("estructura", {}).get("direccion", "neutral")
    tipo_bajo = smc_bajo.get("estructura", {}).get("tipo", "")
    tipo_alto = smc_alto.get("estructura", {}).get("tipo", "")
    conf_bajo = smc_bajo.get("confluencia", {}).get("confianza", 0)
    conf_alto = smc_alto.get("confluencia", {}).get("confianza", 0)
    entrada   = smc_bajo.get("precio", 0)
    sl        = smc_bajo.get("sl_sugerido", 0)
    tp        = smc_bajo.get("tp_sugerido", 0)
    dist_sl   = abs(entrada - sl) if sl else 0
    dist_tp   = abs(tp - entrada) if tp else 0
    rr        = round(dist_tp / dist_sl, 1) if dist_sl > 0 else 0
    emoji     = "🟢" if dir_ == "LONG" else "🔴"
    extras = []
    if smc_bajo.get("barrido_liquidez"):
        extras.append("💧 Barrido de liquidez previo ✅")
    if nivel_redondo:
        extras.append("🔵 Nivel redondo institucional ✅")
    lineas = [
        f"🎯 *REVERSIÓN EN ZONA HTF — {emoji} {dir_}*",
        f"📌 *{ticker}* · {tf_alto}/{tf_bajo}",
        "━━━━━━━━━━━━━━━━",
        f"*{tf_alto} — Estructura:* {tipo_alto} ({conf_alto:.0f}%) · OB zona ✅",
        f"*{tf_bajo} — Entrada:*    {tipo_bajo} ({conf_bajo:.0f}%) · CHoCH ✅ · Barrido ✅",
        "",
        f"💰 *Entrada:* `{entrada:.5f}`",
        f"🛑 *SL:*     `{sl:.5f}`" if sl else "",
        f"✅ *TP:*     `{tp:.5f}`" if tp else "",
        f"📊 *RR:*     `{rr:.1f}:1`",
    ]
    if extras:
        lineas += [""] + extras
    lineas += [
        "",
        "⚡ _Stop hunt + CHoCH + zona HTF — setup institucional completo_",
        f"🕐 {_hora_mx()} CDMX",
    ]
    return "\n".join(l for l in lineas if l)


# ─── COMANDOS ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    await _reply(update,
        "👋 *Bienvenido a ORAM Quant Systems* 🤖\n\n"
        "Soy tu asistente de trading institucional basado en SMC.\n\n"
        "📋 Usa /ayuda para ver todos los comandos.\n\n"
        f"🔑 *Tu Chat ID:* `{chat_id}`\n"
        "_(Cópialo en la app → Bot Telegram → Configuración)_"
    )


async def cmd_mercado(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _en_horario_trading():
        await _reply(update,
            "🔒 *MERCADO CERRADO — FIN DE SEMANA*\n"
            "━━━━━━━━━━━━━━━━\n"
            "Los mercados Forex y Oro están cerrados.\n\n"
            "⏰ *Reapertura:* Domingo 16:00 CDMX\n"
            "🔥 *Mejor sesión:* Lunes 02:00-10:00 CDMX\n\n"
            "💡 Usa este tiempo para planificar la semana en la app."
        )
        return
    await update.message.reply_text("🔍 Analizando mercado... espera.")
    categorias = {
        "Forex":    ["EURUSD=X", "GBPUSD=X"],
        "Materias": ["GC=F"],
    }
    lineas = [
        "📊 *RESUMEN DE MERCADO*",
        f"_{datetime.now(TZ_MX).strftime('%d/%m/%Y %H:%M')} CDMX_",
        "━━━━━━━━━━━━━━━━",
    ]
    for cat, tickers in categorias.items():
        icons = {"Forex": "🔵", "Materias": "🟠"}
        lineas.append(f"\n{icons.get(cat, '📊')} *{cat}:*")
        for ticker in tickers:
            try:
                smc, _ = _analizar_activo(ticker, "1h")
                if smc and "error" not in smc:
                    dir_   = smc.get("estructura", {}).get("direccion", "neutral")
                    conf   = smc.get("confluencia", {}).get("confianza", 0)
                    precio = smc.get("precio", 0)
                    tipo   = smc.get("estructura", {}).get("tipo", "?")
                    rsi    = smc.get("rsi", 0) or 0
                    prio   = "🔥" if conf >= 75 else ""
                    lineas.append(
                        f"{_emoji_dir(dir_)}{prio} *{ticker}* `{precio:.4f}` — {tipo} ({conf:.0f}%) RSI:{rsi:.0f}"
                    )
                else:
                    lineas.append(f"⚫ {ticker} — Sin datos")
            except Exception:
                lineas.append(f"⚫ {ticker} — Error")
    try:
        proximos = obtener_proximos_eventos(2)
        if proximos:
            lineas += ["", "📰 *Próximos eventos (2h):*"]
            for ev in proximos:
                lineas.append(f"{impacto_emoji(ev['impacto'])} {ev['titulo']} — {ev['hora_mx']} CDMX")
    except Exception:
        pass
    lineas += ["", f"🕐 _{_hora_mx()} CDMX_"]
    await _reply(update, "\n".join(lineas))


async def cmd_senales(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Panel de señales SMC multi-activo."""
    chat_id = str(update.effective_chat.id)
    user, cfg = _get_user_by_chat(chat_id)

    try:
        hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=30)
        if hay_ev and ev_info:
            await _reply(update,
                f"⚠️ *PRECAUCIÓN — Evento en {ev_info['minutos_restantes']} min*\n"
                f"📰 {ev_info['titulo']} — {ev_info['hora_mx']} CDMX\n"
                "❌ No es buen momento para entrar. Espera 30 min post-evento."
            )
            return
    except Exception:
        pass

    umbral = float(cfg.get("umbral_confianza", 60)) if cfg else 60
    tf     = cfg.get("tf_monitor", "15m") if cfg else "15m"
    try:
        activos = json.loads(cfg.get("activos_monitor", "[]")) if cfg else []
    except Exception:
        activos = []
    if not _en_horario_trading():
        await _reply(update,
            "🔒 *MERCADO CERRADO — FIN DE SEMANA*\n"
            "━━━━━━━━━━━━━━━━\n"
            "No hay señales activas. Los mercados reabren el domingo 16:00 CDMX."
        )
        return
    if not activos:
        activos = ["EURUSD=X", "GBPUSD=X", "GC=F"]

    await update.message.reply_text(f"⚡ Escaneando {len(activos)} activos en {tf}...")

    altas, medias = [], []
    for ticker in activos:
        try:
            smc, _ = _analizar_activo(ticker, tf)
            if not smc or "error" in smc: continue
            conf  = smc.get("confluencia", {}).get("confianza", 0)
            dir_  = smc.get("estructura",  {}).get("direccion", "neutral")
            precio_s = smc.get("precio", 0)
            sl_s     = smc.get("sl_sugerido", 0)
            tp_s     = smc.get("tp_sugerido", 0)
            if dir_ == "neutral" or conf < umbral: continue
            if not smc.get("señal_valida", False): continue
            if precio_s > 0 and sl_s > 0 and tp_s > 0:
                dist_sl = abs(precio_s - sl_s)
                dist_tp = abs(tp_s - precio_s)
                if dist_sl > 0 and (dist_tp / dist_sl) < 1.5: continue
            if conf >= UMBRAL_ALERTA_ALTA:
                altas.append((ticker, smc, conf))
            else:
                medias.append((ticker, smc, conf))
        except Exception as e:
            logger.error(f"cmd_senales {ticker}: {e}")

    if not altas and not medias:
        await _reply(update,
            f"⚪ *Sin señales ≥{umbral:.0f}% en este momento*\n\n"
            "💡 *Mejores horarios:*\n"
            "🟡 London Open: 02:00-04:00 CDMX\n"
            "🔥 Overlap L+NY: 07:00-10:00 CDMX\n"
            "🟠 NY Open: 07:30-09:30 CDMX\n\n"
            "💡 Prueba /mtf para análisis multi-timeframe."
        )
        return

    capital    = float(user.get("capital_inicial", 10000)) if user else 10000.0
    riesgo_pct = float(cfg.get("riesgo_pct", 1.0)) if cfg else 1.0

    if altas:
        await update.message.reply_text(f"🔥 *{len(altas)} señal(es) ALTA PRIORIDAD:*", parse_mode=MD)
        for ticker, smc, conf in sorted(altas, key=lambda x: -x[2]):
            await _reply(update, _formato_senal_completo(smc, ticker, tf, capital, riesgo_pct))
    if medias:
        await update.message.reply_text(f"⚡ *{len(medias)} señal(es) media:*", parse_mode=MD)
        for ticker, smc, conf in sorted(medias, key=lambda x: -x[2]):
            tipo  = smc.get("estructura", {}).get("tipo", "?")
            dir_  = smc.get("estructura", {}).get("direccion", "neutral")
            prec  = smc.get("precio", 0)
            sl    = smc.get("sl_sugerido", 0)
            tp    = smc.get("tp_sugerido", 0)
            await _reply(update,
                f"{_emoji_dir(dir_)} *{ticker}* `{prec:.5f}` — {tipo} ({conf:.0f}%)\n"
                f"   SL:`{sl:.5f}` TP:`{tp:.5f}`"
            )


async def cmd_analizar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Análisis SMC completo. Uso: /analizar EURUSD [TF]"""
    args = ctx.args
    if not args:
        await _reply(update,
            "💡 *Uso:* `/analizar EURUSD` o `/analizar EURUSD 1h`\n\n"
            "Timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d"
        )
        return
    ticker = _normalizar_ticker(args[0])
    tf = args[1] if len(args) > 1 else "15m"
    chat_id = str(update.effective_chat.id)
    user, cfg = _get_user_by_chat(chat_id)
    capital    = float(user.get("capital_inicial", 10000)) if user else 10000.0
    riesgo_pct = float(cfg.get("riesgo_pct", 1.0)) if cfg else 1.0

    await update.message.reply_text(f"🔍 Analizando {ticker} en {tf}...")
    try:
        smc, status = _analizar_activo(ticker, tf)
        if not smc or "error" in smc:
            await _reply(update, f"❌ Sin datos para {ticker} en {tf}.\n_{status}_")
            return
        conf = smc.get("confluencia", {}).get("confianza", 0)
        dir_ = smc.get("estructura",  {}).get("direccion", "neutral")
        msg  = _formato_senal_completo(smc, ticker, tf, capital, riesgo_pct)

        # Añadir niveles SMC
        obs  = smc.get("order_blocks", [])
        fvgs = smc.get("fvgs", [])
        liq  = smc.get("liquidez", {})
        extras = ["\n━━━━━━━━━━━━━━━━", "📐 *Niveles SMC:*"]
        if obs:
            ob = obs[0]
            extras.append(f"  🟦 OB: `{ob.precio_bot:.5f}` – `{ob.precio_top:.5f}` (fuerza: {ob.fuerza:.0%})")
        if fvgs:
            fvg = fvgs[0]
            extras.append(f"  🟨 FVG: `{fvg.precio_bot:.5f}` – `{fvg.precio_top:.5f}`")
        if liq:
            res = liq.get("resistance_levels", [])
            sup = liq.get("support_levels", [])
            if res: extras.append(f"  🔴 Resistencias: {', '.join([f'`{x:.5f}`' for x in res[:2]])}")
            if sup: extras.append(f"  🟢 Soportes: {', '.join([f'`{x:.5f}`' for x in sup[:2]])}")

        await _reply(update, msg + "\n" + "\n".join(extras))
        if conf >= 60 and dir_ != "neutral":
            await _reply(update, f"💡 _Usa_ `/mtf {ticker.replace('=X','')}` _para confirmar con MTF._")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def cmd_mtf(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Multi-Timeframe.
    Sin args → escanea todos tus activos configurados.
    /mtf EURUSD [combo]  → par específico.
    Combos: scalping, intraday, swing, posicional"""
    args    = ctx.args
    chat_id = str(update.effective_chat.id)

    combo_map = {
        "scalping":   "Scalping (5m/1m)",
        "intraday":   "Intraday (1h/15m)",
        "swing":      "Swing (4h/1h)",
        "posicional": "Posicional (1d/4h)",
    }

    if not args:
        # ── Sin argumentos: escanear todos los activos configurados ──────────
        _, cfg = _get_user_by_chat(chat_id)
        try:
            activos = json.loads(cfg.get("activos_monitor", "[]")) if cfg else []
        except Exception:
            activos = []
        if not activos:
            activos = ["EURUSD=X", "GBPUSD=X", "GC=F"]
        tf_alto, tf_bajo = MTF_COMBOS.get("Intraday (1h/15m)", ("1h", "15m"))
        await update.message.reply_text(
            f"🔭 Analizando {len(activos)} activos MTF ({tf_alto}/{tf_bajo})..."
        )
        for tkr in activos:
            try:
                mtf = analisis_mtf(tkr, tf_alto, tf_bajo)
                await _reply(update, _formato_mtf(mtf, tkr))
            except Exception as e:
                await update.message.reply_text(f"❌ {tkr}: {str(e)[:80]}")
        return

    # ── Con argumento: par específico ─────────────────────────────────────────
    ticker    = _normalizar_ticker(args[0])
    combo_key = args[1].lower() if len(args) > 1 else "intraday"
    combo     = combo_map.get(combo_key, "Intraday (1h/15m)")
    tf_alto, tf_bajo = MTF_COMBOS.get(combo, ("1h", "15m"))

    await update.message.reply_text(f"🔭 Analizando {ticker} MTF ({tf_alto}/{tf_bajo})...")
    try:
        mtf = analisis_mtf(ticker, tf_alto, tf_bajo)
        await _reply(update, _formato_mtf(mtf, ticker))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def cmd_riesgo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Calculadora de riesgo. Uso: /riesgo EURUSD 1.0850 1.0800 1.0950"""
    args = ctx.args
    if len(args) < 4:
        await _reply(update,
            "💼 *Calculadora de Riesgo*\n\n"
            "*Uso:* `/riesgo TICKER ENTRADA SL TP`\n"
            "*Ejemplo:* `/riesgo EURUSD 1.0850 1.0800 1.0950`"
        )
        return
    try:
        ticker  = args[0].upper()
        entrada = float(args[1])
        sl      = float(args[2])
        tp      = float(args[3])
        chat_id = str(update.effective_chat.id)
        user, cfg = _get_user_by_chat(chat_id)
        capital    = float(user.get("capital_inicial", 10000)) if user else 10000.0
        riesgo_pct = float(cfg.get("riesgo_pct", 1.0)) if cfg else 1.0

        res = calcular_riesgo(entrada, sl, tp, capital, riesgo_pct)
        if not res:
            await update.message.reply_text("❌ Error en los datos. Verifica que SL ≠ entrada.")
            return

        dir_  = "LONG" if tp > entrada else "SHORT"
        await _reply(update,
            f"💼 *CALCULADORA DE RIESGO*\n"
            f"{_emoji_dir(dir_)} *{ticker}* — {dir_}\n"
            "━━━━━━━━━━━━━━━━\n"
            f"💰 Entrada: `{entrada:.5f}`\n"
            f"🛑 SL: `{sl:.5f}` ({res['pips_sl']:.1f} pips)\n"
            f"✅ TP: `{tp:.5f}` ({res['pips_tp']:.1f} pips)\n"
            f"⚖️ RR: *{res['rr']:.1f}:1*\n\n"
            f"💼 *Capital ${capital:,.0f} · Riesgo {riesgo_pct}%:*\n"
            f"   Riesgo USD: ${res['riesgo_usd']:.2f}\n"
            f"   Lote sugerido: *{res['lot_size']:.3f}*\n"
            f"   Ganancia potencial: *${res['ganancia_pot']:.2f}*\n\n"
            "⚠️ _Ajusta según tu broker y spread._"
        )
    except (ValueError, IndexError):
        await _reply(update, "❌ Formato: `/riesgo EURUSD 1.0850 1.0800 1.0950`")


async def cmd_kelly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kelly Criterion. Uso: /kelly 55 2.0 [capital]
    WinRate% RR_promedio [capital_USD]"""
    args = ctx.args
    if len(args) < 2:
        await _reply(update,
            "📊 *Kelly Criterion*\n\n"
            "*Uso:* `/kelly WinRate RR [Capital]`\n"
            "*Ejemplo:* `/kelly 55 2.0 10000`\n\n"
            "WinRate en %, RR promedio de tus trades."
        )
        return
    try:
        wr    = float(args[0]) / 100
        rr    = float(args[1])
        chat_id = str(update.effective_chat.id)
        user, _ = _get_user_by_chat(chat_id)
        cap   = float(args[2]) if len(args) > 2 else (float(user.get("capital_inicial", 10000)) if user else 10000.0)

        kelly_full = max(0, wr - (1 - wr) / rr)
        kelly_half = kelly_full / 2
        kelly_qrt  = kelly_full / 4

        verdict = ""
        if kelly_full <= 0:
            verdict = "❌ *Estrategia con pérdida esperada.* Mejora tu WR o RR."
        elif kelly_full > 0.25:
            verdict = "⚠️ Kelly alto — usa Half o Quarter Kelly para proteger capital."
        else:
            verdict = "✅ Estrategia con expectativa positiva."

        await _reply(update,
            f"📊 *KELLY CRITERION*\n"
            f"Win Rate: {wr*100:.1f}% · RR promedio: {rr:.1f} · Capital: ${cap:,.0f}\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🔥 Full Kelly (agresivo):  {kelly_full*100:.1f}% = *${cap*kelly_full:,.0f}* por trade\n"
            f"✅ Half Kelly (recomendado): {kelly_half*100:.1f}% = *${cap*kelly_half:,.0f}* por trade\n"
            f"🛡️ Quarter Kelly (conservador): {kelly_qrt*100:.1f}% = *${cap*kelly_qrt:,.0f}* por trade\n\n"
            f"{verdict}\n\n"
            "💡 _Kelly% = W - (1-W)/R_"
        )
    except (ValueError, IndexError):
        await _reply(update, "❌ Formato: `/kelly 55 2.0 10000`")


async def cmd_trades(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Ver últimos trades del diario. Uso: /trades [N]"""
    chat_id = str(update.effective_chat.id)
    user, _ = _get_user_by_chat(chat_id)
    if not user:
        await _reply(update, "⚙️ Vincula tu Chat ID en la app → Bot Telegram.")
        return
    try:
        n      = int(ctx.args[0]) if ctx.args else 10
        trades = obtener_trades(user["id"])
        if not trades:
            await _reply(update, "📭 Sin trades registrados aún.\n\nRegistra trades en la app → Diario de Trades.")
            return
        trades = trades[-n:]
        pnl    = sum(t.get("resultado_usd", 0) or 0 for t in trades)
        win    = sum(1 for t in trades if (t.get("resultado_usd") or 0) > 0)
        wr     = win / len(trades) * 100

        lineas = [
            f"📋 *ÚLTIMOS {len(trades)} TRADES*",
            f"P&L: {'🟢' if pnl >= 0 else '🔴'} ${pnl:+,.2f} · WR: {wr:.1f}%",
            "━━━━━━━━━━━━━━━━",
        ]
        for t in reversed(trades):
            res   = t.get("resultado_usd", 0) or 0
            emoji = "🟢" if res > 0 else "🔴" if res < 0 else "⚪"
            dir_  = t.get("direccion", "?")
            lineas.append(
                f"{emoji} *{t.get('activo','?')}* {t.get('timeframe','?')} {dir_} — "
                f"${res:+.2f} | {t.get('setup','?')[:20]}"
            )
        lineas.append(f"\n💡 _Registra trades en la app → Diario de Trades_")
        await _reply(update, "\n".join(lineas))
    except Exception as e:
        await _reply(update, f"❌ Error: {str(e)[:100]}")


async def cmd_performance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Análisis de performance e IA. Uso: /performance"""
    chat_id = str(update.effective_chat.id)
    user, _ = _get_user_by_chat(chat_id)
    if not user:
        await _reply(update, "⚙️ Vincula tu Chat ID en la app → Bot Telegram.")
        return
    try:
        trades = obtener_trades(user["id"])
        if len(trades) < 3:
            await _reply(update, "📊 Necesitas al menos 3 trades para el análisis.\n\nRegistra trades en la app → Diario de Trades.")
            return

        df = pd.DataFrame(trades)
        pnl_serie = pd.Series([t.get("resultado_usd", 0) or 0 for t in trades])
        capital   = float(user.get("capital_inicial", 10000))

        # Métricas base
        total   = len(df)
        ganados = int((pnl_serie > 0).sum())
        perdidos= int((pnl_serie < 0).sum())
        wr      = ganados / total * 100
        pnl_tot = float(pnl_serie.sum())
        pf      = abs(float(pnl_serie[pnl_serie>0].sum())) / max(abs(float(pnl_serie[pnl_serie<0].sum())), 0.01)

        # Drawdown y Sharpe
        dd  = calcular_drawdown(pnl_serie)
        sr  = calcular_sharpe(pnl_serie)
        max_dd = dd.get("max_drawdown_usd", 0)

        lineas = [
            "📊 *PERFORMANCE & IA*",
            f"_Capital: ${capital:,.0f} · {total} trades_",
            "━━━━━━━━━━━━━━━━",
            f"✅ Ganadores: {ganados} ({wr:.1f}%)",
            f"❌ Perdedores: {perdidos} ({100-wr:.1f}%)",
            f"💰 P&L total: {'🟢' if pnl_tot >= 0 else '🔴'} ${pnl_tot:+,.2f}",
            f"📈 Capital actual: ${capital + pnl_tot:,.2f}",
            f"📉 Max Drawdown: ${max_dd:.2f}",
            f"⚡ Profit Factor: {pf:.2f}",
            f"📐 Sharpe Ratio: {sr:.2f}",
            "",
        ]

        # Análisis IA si hay datos suficientes
        if len(df) >= 5:
            try:
                ia = analizar_performance_ia(df)
                if "error" not in ia:
                    lineas.append("🤖 *Análisis IA:*")
                    mejor_setup   = ia.get("mejor_setup", "?")
                    mejor_dir     = ia.get("mejor_direccion", "?")
                    mejor_tf      = ia.get("mejor_timeframe", "?")
                    recom         = ia.get("recomendaciones", [])
                    if mejor_setup:
                        lineas.append(f"  🎯 Mejor setup: *{mejor_setup}*")
                    if mejor_dir:
                        emoji_d = "🟢" if "LONG" in str(mejor_dir) else "🔴"
                        lineas.append(f"  {emoji_d} Mejor dirección: *{mejor_dir}*")
                    if mejor_tf:
                        lineas.append(f"  ⏱ Mejor timeframe: *{mejor_tf}*")
                    if recom:
                        lineas.append("")
                        lineas.append("💡 *Recomendaciones IA:*")
                        for r in recom[:3]:
                            lineas.append(f"  • {r}")
            except Exception:
                pass

        lineas.append(f"\n🕐 _{_hora_mx()} CDMX_")
        await _reply(update, "\n".join(lineas))
    except Exception as e:
        await _reply(update, f"❌ Error: {str(e)[:100]}")


async def cmd_backtest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Backtest SMC. Uso: /backtest EURUSD [TF] [umbral]"""
    args = ctx.args
    if not args:
        await _reply(update,
            "🧪 *Backtest SMC*\n\n"
            "*Uso:* `/backtest TICKER [TF] [umbral%]`\n"
            "*Ejemplo:* `/backtest EURUSD 1h 50`\n\n"
            "TF: 15m, 30m, 1h, 4h, 1d\n"
            "Umbral: 30-85 (confianza mínima de señales)\n\n"
            "⚠️ _Puede tardar 30-90 segundos_"
        )
        return
    ticker = _normalizar_ticker(args[0])
    tf     = args[1] if len(args) > 1 else "1h"
    umbral = int(args[2]) if len(args) > 2 else 50
    chat_id = str(update.effective_chat.id)
    user, _ = _get_user_by_chat(chat_id)
    capital    = float(user.get("capital_inicial", 10000)) if user else 10000.0

    await update.message.reply_text(f"🧪 Ejecutando backtest {ticker} {tf} umbral:{umbral}%...\n⏳ Espera 30-90 seg.")
    try:
        res = ejecutar_backtest(ticker, tf, 1.0, umbral, capital)
        if "error" in res:
            await _reply(update, f"❌ {res['error']}\n💡 Prueba umbral más bajo (40-50%) o TF con más historia (1h/4h).")
            return

        pf      = res.get("profit_factor", 0)
        wr      = res.get("win_rate", 0)
        pnl     = res.get("total_pnl", 0)
        trades  = res.get("total_trades", 0)
        dd      = res.get("max_drawdown", 0)
        sharpe  = res.get("sharpe", 0)
        cap_fin = res.get("capital_final", capital)
        exp     = res.get("expectancy_r", 0)
        f_ini   = res.get("fecha_inicio", "")[:10]
        f_fin   = res.get("fecha_fin", "")[:10]
        senales = res.get("señales_analizadas", 0)

        veredicto = "✅ Estrategia rentable" if pnl > 0 and wr > 45 else "⚠️ Estrategia marginal" if pnl > 0 else "❌ Estrategia con pérdidas en este período"

        await _reply(update,
            f"🧪 *BACKTEST SMC — {ticker} {tf}*\n"
            f"_{f_ini} → {f_fin}_\n"
            "━━━━━━━━━━━━━━━━\n"
            f"📊 Trades: {trades} de {senales} señales\n"
            f"✅ Win Rate: *{wr:.1f}%*\n"
            f"⚡ Profit Factor: *{pf:.2f}*\n"
            f"💰 P&L: {'🟢' if pnl >= 0 else '🔴'} *${pnl:+,.0f}*\n"
            f"📈 Capital final: *${cap_fin:,.0f}*\n"
            f"📉 Max Drawdown: ${dd:.0f}\n"
            f"📐 Sharpe: {sharpe:.2f}\n"
            f"🎯 Expectancy: {exp:.3f}R\n"
            "━━━━━━━━━━━━━━━━\n"
            f"{veredicto}\n\n"
            "⚠️ _Resultados orientativos. El mercado real incluye spread y slippage._"
        )

        # Por tipo de señal
        por_tipo = res.get("por_tipo", {})
        if por_tipo:
            lineas = ["", "📋 *Por tipo de señal:*"]
            for tipo, data in sorted(por_tipo.items(), key=lambda x: -x[1]["total"]):
                wr_t = data["ganados"] / data["total"] * 100 if data["total"] else 0
                lineas.append(f"  • {tipo or 'Otro'}: {data['total']} trades ({wr_t:.0f}% WR)")
            await _reply(update, "\n".join(lineas))

    except Exception as e:
        await _reply(update, f"❌ Error: {str(e)[:100]}")


async def cmd_watchlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Watchlist — precios y señales de tus activos monitoreados."""
    chat_id = str(update.effective_chat.id)
    user, cfg = _get_user_by_chat(chat_id)
    if not user:
        await _reply(update, "⚙️ Vincula tu Chat ID en la app → Bot Telegram.")
        return
    tf = cfg.get("tf_monitor", "1h") if cfg else "1h"
    try:
        wl = obtener_watchlist(user["id"])
    except Exception:
        wl = []

    if not wl:
        await _reply(update, "👁️ Tu watchlist está vacía.\nAgrega activos en la app → Watchlist → Agregar.")
        return

    await update.message.reply_text(f"👁️ Actualizando {len(wl)} activos de tu watchlist...")
    lineas = [
        "👁️ *TU WATCHLIST*",
        f"_TF: {tf} · {_hora_mx()} CDMX_",
        "━━━━━━━━━━━━━━━━",
    ]
    for item in wl:
        ticker = item.get("ticker", "?")
        alias  = item.get("alias", "")
        nombre = alias if alias else ticker
        try:
            smc, _ = _analizar_activo(ticker, tf)
            if smc and "error" not in smc:
                dir_   = smc.get("estructura", {}).get("direccion", "neutral")
                conf   = smc.get("confluencia", {}).get("confianza", 0)
                precio = smc.get("precio", 0)
                rsi    = smc.get("rsi", 0) or 0
                tipo   = smc.get("estructura", {}).get("tipo", "?")
                prio   = "🔥" if conf >= 75 else ""
                lineas.append(
                    f"{_emoji_dir(dir_)}{prio} *{nombre}* `{precio:.5f}`\n"
                    f"   {tipo} ({conf:.0f}%) · RSI:{rsi:.0f}"
                )
            else:
                lineas.append(f"⚫ *{nombre}* — Sin datos")
        except Exception:
            lineas.append(f"⚫ *{nombre}* — Error")

    lineas.append(f"\n💡 _Usa /analizar TICKER para análisis detallado_")
    await _reply(update, "\n".join(lineas))


async def cmd_capital(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Dashboard completo de la cuenta."""
    chat_id = str(update.effective_chat.id)
    user, cfg = _get_user_by_chat(chat_id)
    if not user:
        await _reply(update,
            "⚙️ *Sin configuración vinculada*\n\n"
            "Vincula tu Chat ID en:\nApp → Bot Telegram → Chat ID → Guardar"
        )
        return
    try:
        capital = float(user.get("capital_inicial", 10000))
        trades  = obtener_trades(user["id"])
        pnl     = sum(t.get("resultado_usd", 0) or 0 for t in trades)
        n       = len(trades)
        win     = sum(1 for t in trades if (t.get("resultado_usd") or 0) > 0)
        wr      = win / n * 100 if n else 0

        # Sharpe y Drawdown
        pnl_serie = pd.Series([t.get("resultado_usd", 0) or 0 for t in trades])
        sharpe    = calcular_sharpe(pnl_serie) if n >= 3 else 0
        dd        = calcular_drawdown(pnl_serie).get("max_drawdown_usd", 0) if n >= 2 else 0
        pf_num    = abs(float(pnl_serie[pnl_serie>0].sum()))
        pf_den    = max(abs(float(pnl_serie[pnl_serie<0].sum())), 0.01)
        pf        = pf_num / pf_den if n >= 2 else 0

        await _reply(update,
            f"💼 *TU CUENTA ORAM*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"💰 Capital inicial: *${capital:,.2f}*\n"
            f"📊 Capital actual: *${capital + pnl:,.2f}*\n"
            f"{'🟢' if pnl >= 0 else '🔴'} P&L total: *${pnl:+,.2f}*\n"
            f"📉 Max Drawdown: ${dd:.2f}\n"
            f"📐 Sharpe: {sharpe:.2f}\n"
            f"⚡ Profit Factor: {pf:.2f}\n\n"
            f"📈 Trades: {n}\n"
            f"✅ Win Rate: {wr:.1f}%\n\n"
            f"⚙️ Umbral señales: {cfg.get('umbral_confianza', 70):.0f}%\n"
            f"⏱ TF monitor: {cfg.get('tf_monitor', '15m')}\n"
            f"🕐 {_hora_mx()} CDMX"
        )
    except Exception as e:
        await _reply(update, f"❌ Error: {str(e)[:100]}")


async def cmd_noticias(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        eventos = obtener_eventos_hoy()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        return
    if not eventos:
        await update.message.reply_text("📰 Sin eventos económicos importantes hoy.")
        return
    lineas = [
        "📰 *EVENTOS ECONÓMICOS HOY*",
        f"_{datetime.now(TZ_MX).strftime('%d/%m/%Y')}_",
        "━━━━━━━━━━━━━━━━",
    ]
    for ev in eventos:
        estado = "✅" if ev["ya_paso"] else "⏳"
        lineas.append(f"{estado} {impacto_emoji(ev['impacto'])} *{ev['hora_mx']}* — {ev['titulo']} ({ev['moneda']})")
    lineas += ["", "⚠️ _Evita operar ±30 min alrededor de eventos 🔴_"]
    await _reply(update, "\n".join(lineas))


async def cmd_proximos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        eventos = obtener_proximos_eventos(2)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        return
    if not eventos:
        await _reply(update, f"✅ *Sin eventos de alto impacto en las próximas 2 horas.*\nMercado despejado — {_hora_mx()} CDMX")
        return
    lineas = ["⚠️ *EVENTOS PRÓXIMOS (2h)*", "━━━━━━━━━━━━━━━━"]
    for ev in eventos:
        lineas.append(f"{impacto_emoji(ev['impacto'])} *{ev['hora_mx']}* — {ev['titulo']} ({ev['moneda']})\n   Restante: {ev['minutos_restantes']} min")
    lineas.append("\n⚠️ _Evita abrir posiciones. Cierra las de corto plazo._")
    await _reply(update, "\n".join(lineas))


async def cmd_sesiones(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ahora = datetime.now(TZ_MX)
    h     = ahora.hour
    def est(ini, fin): return "🟢 *ACTIVA*" if ini <= h < fin else "⚫ Cerrada"
    await _reply(update,
        "🌍 *SESIONES DE TRADING — CDMX*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🌏 *Tokio (Asia):*     00:00-09:00  {est(0,9)}\n"
        f"🌍 *Londres:*          02:00-11:00  {est(2,11)}\n"
        f"🔥 *Overlap L+NY:*     07:00-10:00  {est(7,10)}\n"
        f"🌎 *Nueva York:*       07:30-16:00  {est(7,16)}\n"
        f"📡 *Sydney:*           20:00-05:00  {'🟢 ACTIVA' if h>=20 or h<5 else '⚫ Cerrada'}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🕐 _Ahora: {ahora.strftime('%H:%M')} CDMX ({ahora.strftime('%A')})_\n"
        f"_Mercado: {'en horario de trading' if _en_horario_trading() else 'sin liquidez'}_\n\n"
        "💡 *Mejores momentos:*\n"
        "  🔥 Overlap (07:00-10:00): mayor volatilidad\n"
        "  🟡 London Open (02:00-04:00): señales SMC fuertes\n"
        "  🟠 NY Open (07:30-09:30): breakouts frecuentes"
    )


async def cmd_alertas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(ctx.args[0]) if ctx.args else 24
        senales = obtener_señales_recientes(horas=n)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        return
    if not senales:
        await update.message.reply_text(f"📭 Sin señales en las últimas {ctx.args[0] if ctx.args else 24}h.")
        return
    lineas = [f"⚡ *SEÑALES — ÚLTIMAS {n}H*", "━━━━━━━━━━━━━━━━"]
    for s in senales[:12]:
        hora = str(s.get("created_at", ""))[-8:-3] if s.get("created_at") else "?"
        conf = s.get("confianza", 0)
        prio = "🔥" if conf >= 75 else ""
        lineas.append(
            f"{_emoji_dir(s.get('direccion','neutral'))}{prio} *{s['ticker']}* "
            f"{s.get('timeframe','?')} — {s['tipo']} ({conf:.0f}%) @ {hora}"
        )
    longs  = sum(1 for s in senales if s.get("direccion") == "LONG")
    shorts = sum(1 for s in senales if s.get("direccion") == "SHORT")
    lineas += ["", f"📊 _Total: {len(senales)} · 🟢 {longs} LONG · 🔴 {shorts} SHORT_"]
    await _reply(update, "\n".join(lineas))


async def cmd_resumen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Generando reporte completo...")
    try:
        await _reply(update, await _generar_resumen_diario())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def cmd_ayuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _reply(update,
        "🤖 *ORAM Quant Systems v3 — Comandos completos*\n\n"

        "📡 *ANÁLISIS:*\n"
        "/mercado — Resumen de todos los pares (1H)\n"
        "/senales — Señales SMC activas (usa tu config)\n"
        "/analizar EURUSD [1h] — Análisis SMC completo\n"
        "/mtf EURUSD [swing] — Multi-Timeframe\n"
        "   combos: scalping · intraday · swing · posicional\n\n"

        "💼 *GESTIÓN DE RIESGO:*\n"
        "/riesgo EURUSD 1.085 1.080 1.095 — Calcula lote y RR\n"
        "/kelly 55 2.0 [10000] — Kelly Criterion\n"
        "/capital — Dashboard completo de tu cuenta\n\n"

        "📋 *DIARIO & PERFORMANCE:*\n"
        "/trades [N] — Últimos N trades (def: 10)\n"
        "/performance — Análisis estadístico + IA\n\n"

        "🧪 *BACKTESTING:*\n"
        "/backtest EURUSD [1h] [50] — Backtest SMC histórico\n\n"

        "👁️ *WATCHLIST:*\n"
        "/watchlist — Precios y señales de tus activos\n\n"

        "📰 *CALENDARIO:*\n"
        "/noticias — Eventos económicos hoy\n"
        "/proximos — Próximos eventos (2h)\n"
        "/sesiones — Horarios de sesiones CDMX\n\n"

        "📊 *HISTORIAL:*\n"
        "/alertas [N] — Señales de las últimas Nh (def: 24)\n"
        "/resumen — Reporte diario completo\n\n"

        "✅ *TRADES CONFIRMADOS:*\n"
        "/tomar [EURUSD] — Confirma que tomaste la última señal\n"
        "/activos — Ver trades abiertos con P&L en tiempo real\n"
        "/cerrar [EURUSD] — Cierra trade manualmente\n\n"

        "🤖 *AUTOMÁTICO (sin comandos):*\n"
        "• 🚨 Alertas compra/venta cuando confianza ≥umbral\n"
        "• 🔭 MTF alineado → notificación automática\n"
        "• 🎯 TP/SL alcanzado → notificación automática\n"
        "• 🔔 Alertas de precio en tus niveles\n"
        "• ⚠️ Aviso 30 min antes de noticias alto impacto\n"
        "• 🌅 Reporte diario a las 7AM CDMX\n\n"

        "⚠️ _Las señales son orientativas. Siempre usa SL._"
    )


async def cmd_tomar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Confirma que el usuario tomó la última señal enviada (o la de un ticker específico)."""
    chat_id = str(update.effective_chat.id)
    args = ctx.args or []

    if args:
        ticker_input = args[0].upper().replace("/", "")
        # Normalizar: EURUSD → EURUSD=X, BTCUSD → BTC-USD, etc.
        _map = {"EURUSD":"EURUSD=X","GBPUSD":"GBPUSD=X","USDJPY":"USDJPY=X",
                "USDCHF":"USDCHF=X","AUDUSD":"AUDUSD=X","USDCAD":"USDCAD=X",
                "NZDUSD":"NZDUSD=X","BTCUSD":"BTC-USD","ETHUSD":"ETH-USD",
                "XAUUSD":"GC=F","GOLD":"GC=F"}
        ticker = _map.get(ticker_input, ticker_input + "=X" if "=" not in ticker_input and "-" not in ticker_input else ticker_input)
        senal = _ultimas_senales.get((chat_id, ticker))
    else:
        senal = _ultimas_senales.get(chat_id)

    if not senal:
        await _reply(update,
            "⚠️ No hay señal reciente registrada.\n"
            "Espera la próxima alerta del bot y luego usa /tomar."
        )
        return

    ticker = senal["ticker"]
    if obtener_trade_activo(chat_id, ticker):
        await _reply(update,
            f"⚠️ Ya tienes un trade activo en *{ticker}*.\n"
            f"Usa /cerrar {ticker.replace('=X','')} para cerrarlo primero."
        )
        return

    trade_id = registrar_trade_confirmado(
        chat_id, ticker, senal.get("tf","15m"), senal["direccion"],
        senal["entrada"], senal["sl"], senal["tp"], senal.get("confianza", 0)
    )
    emoji = _emoji_dir(senal["direccion"])
    await _reply(update,
        f"✅ *TRADE CONFIRMADO* (ID #{trade_id})\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{emoji} *{ticker}* · {senal.get('tf','?')}\n"
        f"💰 Entrada: `{senal['entrada']:.5f}`\n"
        f"🛑 SL: `{senal['sl']:.5f}`\n"
        f"✅ TP: `{senal['tp']:.5f}`\n\n"
        f"🔭 Monitoreando TP/SL automáticamente.\n"
        f"Señales de *{ticker}* pausadas hasta que cierre.\n"
        f"Usa /cerrar {ticker.replace('=X','')} para salida manual."
    )


async def cmd_cerrar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Cierra manualmente un trade confirmado activo."""
    chat_id = str(update.effective_chat.id)
    args = ctx.args or []

    if args:
        ticker_input = args[0].upper()
        _map = {"EURUSD":"EURUSD=X","GBPUSD":"GBPUSD=X","USDJPY":"USDJPY=X",
                "USDCHF":"USDCHF=X","AUDUSD":"AUDUSD=X","USDCAD":"USDCAD=X",
                "BTCUSD":"BTC-USD","ETHUSD":"ETH-USD","XAUUSD":"GC=F","GOLD":"GC=F"}
        ticker = _map.get(ticker_input, ticker_input + "=X" if "=" not in ticker_input and "-" not in ticker_input else ticker_input)
        trade = obtener_trade_activo(chat_id, ticker)
    else:
        trades = obtener_trades_activos_chat(chat_id)
        if len(trades) > 1:
            lista = "\n".join(f"  • {t['ticker'].replace('=X','')} ({t['direccion']})" for t in trades)
            await _reply(update, f"Tienes varios trades activos:\n{lista}\n\nEspecifica: /cerrar EURUSD")
            return
        trade = trades[0] if trades else None

    if not trade:
        await _reply(update, "⚠️ No hay trade activo para cerrar.")
        return

    try:
        df_c, _ = obtener_datos(trade["ticker"], "5m")
        precio_actual = float(df_c["Close"].iloc[-1]) if df_c is not None else None
    except Exception:
        precio_actual = None

    cerrar_trade_confirmado(trade["id"], "manual")
    pips_txt = ""
    if precio_actual:
        pips = _calcular_pips(trade["ticker"], precio_actual, trade["entrada"])
        signo = "+" if ((trade["direccion"]=="SHORT" and precio_actual < trade["entrada"]) or
                        (trade["direccion"]=="LONG"  and precio_actual > trade["entrada"])) else "-"
        pips_txt = f"\n📏 P&L aprox: {signo}{pips} pips"

    await _reply(update,
        f"🔒 *TRADE CERRADO MANUALMENTE*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"*{trade['ticker']}* · {trade['direccion']}\n"
        f"Entrada: `{trade['entrada']:.5f}`\n"
        + (f"Precio cierre: `{precio_actual:.5f}`" if precio_actual else "") + pips_txt + "\n\n"
        f"✅ Señales de *{trade['ticker']}* reactivadas."
    )


async def cmd_activos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Muestra los trades confirmados activos del usuario."""
    chat_id = str(update.effective_chat.id)
    trades = obtener_trades_activos_chat(chat_id)
    if not trades:
        await _reply(update, "📭 No tienes trades activos.\nUsa /tomar después de recibir una señal.")
        return
    lineas = [f"📊 *TRADES ACTIVOS ({len(trades)})*", "━━━━━━━━━━━━━━━━"]
    for t in trades:
        try:
            df_a, _ = obtener_datos(t["ticker"], "5m")
            precio_actual = float(df_a["Close"].iloc[-1]) if df_a is not None else None
        except Exception:
            precio_actual = None
        emoji = _emoji_dir(t["direccion"])
        pnl_txt = ""
        if precio_actual:
            pips = _calcular_pips(t["ticker"], precio_actual, t["entrada"])
            signo = "+" if ((t["direccion"]=="SHORT" and precio_actual < t["entrada"]) or
                            (t["direccion"]=="LONG"  and precio_actual > t["entrada"])) else "-"
            pnl_txt = f" · P&L: {signo}{pips}p"
        lineas += [
            f"\n{emoji} *{t['ticker']}* ({t['timeframe']}){pnl_txt}",
            f"  Entrada: `{t['entrada']:.5f}`  SL: `{t['sl']:.5f}`  TP: `{t['tp']:.5f}`",
            f"  Precio: `{precio_actual:.5f}`" if precio_actual else "",
        ]
    lineas += ["", "Usa /cerrar TICKER para salida manual."]
    await _reply(update, "\n".join(l for l in lineas if l is not None))


async def cmd_desconocido(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Comando no reconocido.\nUsa /ayuda para ver todos los comandos.")


# ─── JOBS AUTOMÁTICOS ─────────────────────────────────────────────────────────

async def _generar_resumen_diario() -> str:
    if not _en_horario_trading():
        return (
            "🔒 *MERCADO CERRADO — FIN DE SEMANA*\n"
            f"_{datetime.now(TZ_MX).strftime('%A %d/%m/%Y — %H:%M')} CDMX_\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "Los mercados Forex y Oro están cerrados.\n"
            "⏰ *Reapertura:* Domingo 16:00 CDMX\n\n"
            "💡 *Úsalo para prepararte:*\n"
            "   • Revisa tus trades de la semana en la app\n"
            "   • Identifica zonas clave para el lunes\n"
            "   • Descansa — el mercado reabre el domingo\n"
            "━━━━━━━━━━━━━━━━\n"
            "🤖 _ORAM Quant Systems_"
        )
    activos = ["EURUSD=X", "GBPUSD=X", "GC=F"]
    lineas  = [
        "🌅 *REPORTE DIARIO SMC — ORAM*",
        f"_{datetime.now(TZ_MX).strftime('%A %d/%m/%Y — %H:%M')} CDMX_",
        "━━━━━━━━━━━━━━━━",
        "",
        "📊 *Estado del mercado (1H):*",
    ]
    señales_activas = 0
    for ticker in activos:
        try:
            smc, _ = _analizar_activo(ticker, "1h")
            if smc and "error" not in smc:
                dir_   = smc.get("estructura", {}).get("direccion", "neutral")
                conf   = smc.get("confluencia", {}).get("confianza", 0)
                precio = smc.get("precio", 0)
                tipo   = smc.get("estructura", {}).get("tipo", "?")
                rsi    = smc.get("rsi", 0) or 0
                prio   = "🔥" if conf >= 75 else ""
                lineas.append(
                    f"{_emoji_dir(dir_)}{prio} *{ticker}* `{precio:.4f}` — {tipo} ({conf:.0f}%) RSI:{rsi:.0f}"
                )
                if conf >= 60 and dir_ != "neutral":
                    señales_activas += 1
            else:
                lineas.append(f"⚫ {ticker} — Sin datos")
        except Exception:
            lineas.append(f"⚫ {ticker} — Error")

    try:
        senales_24h = obtener_señales_recientes(horas=24)
        longs  = sum(1 for s in senales_24h if s.get("direccion") == "LONG")
        shorts = sum(1 for s in senales_24h if s.get("direccion") == "SHORT")
        lineas += ["", "⚡ *Actividad de señales (24h):*",
                   f"  🟢 LONG: {longs}  |  🔴 SHORT: {shorts}  |  Total: {len(senales_24h)}"]
    except Exception:
        pass

    try:
        eventos = obtener_eventos_hoy()
        if eventos:
            lineas += ["", "📰 *Eventos económicos hoy:*"]
            for ev in eventos:
                estado = "✅" if ev["ya_paso"] else "⏳"
                lineas.append(f"{estado} {impacto_emoji(ev['impacto'])} {ev['hora_mx']} {ev['titulo']}")
    except Exception:
        pass

    lineas += [
        "", "💡 *Sesiones clave (CDMX):*",
        "  🟡 London Open: 02:00-04:00",
        "  🔥 Overlap L+NY: 07:00-10:00",
        "  🟠 NY Open: 07:30-09:30",
        "", f"📡 *Señales activas ahora: {señales_activas}*",
        "━━━━━━━━━━━━━━━━",
        "⚠️ _Max 1-2% riesgo por trade_",
        "🤖 _ORAM Quant Systems_",
    ]
    return "\n".join(lineas)


async def job_resumen_diario(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        configs = obtener_todas_configs_bot()
        txt     = await _generar_resumen_diario()
        for cfg in configs:
            if cfg.get("resumen_diario") and cfg.get("telegram_chat_id"):
                await _send(ctx.bot, cfg["telegram_chat_id"], txt)
    except Exception as e:
        logger.error(f"job_resumen_diario: {e}")


async def _generar_reporte_cierre() -> str:
    """Reporte de cierre de día — NY close (22:00 UTC / 16:00 CDMX)."""
    categorias = {"Forex": ["EURUSD=X", "GBPUSD=X"], "Materias": ["GC=F"]}
    ahora      = datetime.now(TZ_MX)

    senales_hoy = obtener_señales_recientes(horas=24)
    longs_hoy   = sum(1 for s in senales_hoy if s.get("direccion") == "LONG"  and s.get("enviada_bot"))
    shorts_hoy  = sum(1 for s in senales_hoy if s.get("direccion") == "SHORT" and s.get("enviada_bot"))
    total_hoy   = longs_hoy + shorts_hoy

    lineas = [
        "🌆 *REPORTE DE CIERRE — NY CLOSE*",
        f"_{ahora.strftime('%A %d/%m/%Y')} — {ahora.strftime('%H:%M')} CDMX_",
        "━━━━━━━━━━━━━━━━",
        "", "📊 *Estructura de cierre (1H):*",
    ]
    for cat, tickers in categorias.items():
        icons = {"Forex": "🔵", "Materias": "🟠"}
        lineas.append(f"\n{icons.get(cat, '📊')} *{cat}:*")
        for ticker in tickers:
            try:
                smc, _ = _analizar_activo(ticker, "1h")
                if smc and "error" not in smc:
                    dir_   = smc.get("estructura", {}).get("direccion", "neutral")
                    conf   = smc.get("confluencia", {}).get("confianza", 0)
                    precio = smc.get("precio", 0)
                    tipo   = smc.get("estructura", {}).get("tipo", "?")
                    rsi    = smc.get("rsi", 0) or 0
                    lineas.append(
                        f"{_emoji_dir(dir_)} *{ticker}* `{precio:.4f}` — {tipo} ({conf:.0f}%) RSI:{rsi:.0f}"
                    )
                else:
                    lineas.append(f"⚫ {ticker} — Sin datos")
            except Exception:
                lineas.append(f"⚫ {ticker} — Error")

    lineas += [
        "", "⚡ *Actividad de señales (día):*",
        f"  🟢 LONG: {longs_hoy}  |  🔴 SHORT: {shorts_hoy}  |  Total: {total_hoy}",
    ]
    if total_hoy == 0:
        lineas.append("  _Mercado en rango — sin setups de alta probabilidad hoy._")

    try:
        proximos = obtener_proximos_eventos(16)
        if proximos:
            lineas += ["", "📰 *Eventos importantes mañana:*"]
            for ev in proximos[:5]:
                lineas.append(f"{impacto_emoji(ev['impacto'])} {ev['titulo']} — {ev['hora_mx']} CDMX")
    except Exception:
        pass

    lineas += [
        "", "🌅 *Sesiones de mañana (CDMX):*",
        "  🟡 London Open: 02:00-04:00",
        "  🔥 Overlap L+NY: 07:00-10:00",
        "  🟠 NY Open: 07:30-09:30",
        "", "━━━━━━━━━━━━━━━━",
        "⚠️ _Max 1-2% riesgo por trade_",
        "🤖 _ORAM Quant Systems_",
    ]
    return "\n".join(lineas)


async def job_reporte_cierre(ctx: ContextTypes.DEFAULT_TYPE):
    """Reporte de fin de día al NY close (22:00 UTC = 16:00 CDMX)."""
    try:
        configs = obtener_todas_configs_bot()
        txt     = await _generar_reporte_cierre()
        for cfg in configs:
            if cfg.get("resumen_diario") and cfg.get("telegram_chat_id"):
                await _send(ctx.bot, cfg["telegram_chat_id"], txt)
    except Exception as e:
        logger.error(f"job_reporte_cierre: {e}")


async def job_alerta_noticias(ctx: ContextTypes.DEFAULT_TYPE):
    global _eventos_ya_alertados
    try:
        hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=35)
        if not hay_ev or not ev_info:
            return
        mins = ev_info.get("minutos_restantes", 99)
        if not (25 <= mins <= 35):
            return

        # Deduplicación: una sola alerta por evento (título + hora)
        clave = f"{ev_info.get('titulo','')}|{ev_info.get('hora_mx','')}"
        if clave in _eventos_ya_alertados:
            return
        _eventos_ya_alertados.add(clave)
        # Limitar tamaño del set (máx 50 eventos guardados)
        if len(_eventos_ya_alertados) > 50:
            _eventos_ya_alertados.clear()

        configs = obtener_todas_configs_bot()
        msg = (
            f"⚠️ *AVISO — EVENTO ALTO IMPACTO EN {mins} MIN*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"📰 {ev_info['titulo']}\n"
            f"🌍 Moneda: {ev_info['moneda']}\n"
            f"🕐 Hora: {ev_info['hora_mx']} CDMX\n\n"
            "❌ *No abrir nuevas posiciones.*\n"
            "Cierra posiciones de corto plazo.\n"
            "Espera 30 min después del evento.\n"
            "_ORAM Quant Systems_"
        )
        for cfg in configs:
            if cfg.get("alertas_activas") and cfg.get("telegram_chat_id"):
                await _send(ctx.bot, cfg["telegram_chat_id"], msg)
    except Exception as e:
        logger.error(f"job_alerta_noticias: {e}")


async def job_monitoreo_senales(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not _en_horario_trading():
            return
        try:
            hay_ev, _ = hay_evento_alto_impacto_pronto(minutos=20)
            if hay_ev: return
        except Exception:
            pass

        configs = obtener_todas_configs_bot()
        activos_default = ["EURUSD=X", "GBPUSD=X", "GC=F"]

        for cfg in configs:
            chat_id = cfg.get("telegram_chat_id", "")
            if not chat_id or not cfg.get("alertas_activas"):
                continue
            umbral = max(float(cfg.get("umbral_confianza", 70)), 65.0)
            tf     = cfg.get("tf_monitor", "15m")
            try:
                activos = json.loads(cfg.get("activos_monitor", "[]")) or activos_default
            except Exception:
                activos = activos_default

            user_id = cfg.get("user_id")
            user    = obtener_usuario_por_id(user_id)
            capital    = float(user.get("capital_inicial", 10000)) if user else 10000.0
            riesgo_pct = float(cfg.get("riesgo_pct", 1.0))

            altas, medias = [], []
            # Deduplicación: no re-enviar la misma señal (ticker+dirección) en la última 1h
            senales_recientes = [s for s in obtener_señales_recientes(horas=1) if s.get("enviada_bot")]
            tickers_ya_enviados = {
                (s.get("ticker", ""), s.get("direccion", ""))
                for s in senales_recientes
            }

            for ticker in activos:
                try:
                    smc, _ = _analizar_activo(ticker, tf)
                    if not smc or "error" in smc: continue
                    conf  = smc.get("confluencia", {}).get("confianza", 0)
                    dir_  = smc.get("estructura",  {}).get("direccion", "neutral")
                    tipo  = smc.get("estructura",  {}).get("tipo", "")
                    precio = smc.get("precio", 0)
                    sl    = smc.get("sl_sugerido", 0)
                    tp_   = smc.get("tp_sugerido", 0)
                    if dir_ == "neutral" or conf < umbral: continue
                    # FILTRO v2: señal_valida requiere OB activo + mínimo SMC score
                    if not smc.get("señal_valida", False): continue
                    # FILTRO v3: RR mínimo 1.5:1 — señales con RR <1.5 no son operables
                    if precio > 0 and sl > 0 and tp_ > 0:
                        dist_sl = abs(precio - sl)
                        dist_tp = abs(tp_ - precio)
                        rr = dist_tp / dist_sl if dist_sl > 0 else 0
                        if rr < 1.5: continue
                    # Deduplicación: no re-enviar si misma señal en últimos 18 min
                    if (ticker, dir_) in tickers_ya_enviados: continue
                    sig_id = registrar_señal(ticker, tf, tipo, dir_, conf, precio, sl, tp_)
                    if conf >= UMBRAL_ALERTA_ALTA:
                        altas.append((ticker, smc, conf, sig_id))
                    else:
                        medias.append((ticker, smc, conf, sig_id))
                except Exception as e:
                    logger.error(f"job_monitoreo {ticker}: {e}")

            for ticker, smc, conf, sig_id in sorted(altas, key=lambda x: -x[2]):
                try:
                    # Saltar si ya hay trade confirmado activo para este ticker
                    if obtener_trade_activo(chat_id, ticker): continue
                    msg = "🚨 *SEÑAL ALTA PRIORIDAD*\n" + _formato_senal_completo(smc, ticker, tf, capital, riesgo_pct)
                    await _send(ctx.bot, chat_id, msg)
                    marcar_señal_enviada(sig_id)
                    _senal = {"ticker": ticker, "tf": tf, "direccion": smc.get("estructura",{}).get("direccion",""), "entrada": smc.get("precio",0), "sl": smc.get("sl_sugerido",0), "tp": smc.get("tp_sugerido",0), "confianza": conf}
                    _ultimas_senales[(chat_id, ticker)] = _senal
                    _ultimas_senales[chat_id] = _senal
                except Exception as e:
                    logger.error(f"send alta {ticker}: {e}")

            if medias:
                lineas = [f"⚡ *SEÑALES MEDIAS — {tf} · {_hora_mx()} CDMX*", ""]
                _primera_media = True
                for ticker, smc, conf, sig_id in sorted(medias, key=lambda x: -x[2]):
                    if obtener_trade_activo(chat_id, ticker): continue
                    dir_  = smc.get("estructura", {}).get("direccion", "neutral")
                    tipo  = smc.get("estructura", {}).get("tipo", "?")
                    precio = smc.get("precio", 0)
                    sl    = smc.get("sl_sugerido", 0)
                    tp_   = smc.get("tp_sugerido", 0)
                    lineas.append(
                        f"{_emoji_dir(dir_)} *{ticker}* `{precio:.5f}` — {tipo} ({conf:.0f}%)\n"
                        f"   SL:`{sl:.5f}` TP:`{tp_:.5f}`"
                    )
                    marcar_señal_enviada(sig_id)
                    _senal = {"ticker": ticker, "tf": tf, "direccion": dir_, "entrada": precio, "sl": sl, "tp": tp_, "confianza": conf}
                    _ultimas_senales[(chat_id, ticker)] = _senal
                    if _primera_media:
                        _ultimas_senales[chat_id] = _senal  # solo la de mayor confianza
                        _primera_media = False
                if len(lineas) > 2:  # solo enviar si hay señales reales (no solo el header)
                    try:
                        await _send(ctx.bot, chat_id, "\n".join(lineas))
                    except Exception as e:
                        logger.error(f"send medias: {e}")

            # ── Alerta de mercado en rango ────────────────────────────────────
            if not altas and not medias:
                _checks_sin_senal[chat_id] = _checks_sin_senal.get(chat_id, 0) + 1
                ahora_ts = datetime.now(TZ_MX).timestamp()
                # Enviar después de 12 checks (~60 min) sin señal y sin haberlo avisado en 2h
                if (_checks_sin_senal.get(chat_id, 0) >= 12 and
                        ahora_ts - _ultima_alerta_rango.get(chat_id, 0) > 7200):
                    _checks_sin_senal[chat_id]   = 0
                    _ultima_alerta_rango[chat_id] = ahora_ts
                    lineas_r = [
                        "⚪ *MERCADO EN RANGO — Sin setups activos*",
                        "━━━━━━━━━━━━━━━━",
                    ]
                    for tkr in activos:
                        try:
                            smc_r, _ = _analizar_activo(tkr, tf)
                            if smc_r and "error" not in smc_r:
                                dir_r  = smc_r.get("estructura", {}).get("direccion", "neutral")
                                conf_r = smc_r.get("confluencia", {}).get("confianza", 0)
                                tipo_r = smc_r.get("estructura", {}).get("tipo", "Sin señal")
                                lineas_r.append(f"{_emoji_dir(dir_r)} *{tkr}*: {tipo_r} ({conf_r:.0f}%)")
                        except Exception:
                            pass
                    lineas_r += [
                        "",
                        f"💡 _Ningún activo supera el umbral {umbral:.0f}% — mercado lateral o comprimido._",
                        "_No hay setup de alta probabilidad ahora. El bot alertará cuando aparezca uno._",
                        f"🕐 _{_hora_mx()} CDMX_",
                    ]
                    await _send(ctx.bot, chat_id, "\n".join(lineas_r))
            else:
                _checks_sin_senal[chat_id] = 0  # reset si apareció señal

    except Exception as e:
        logger.error(f"job_monitoreo_senales: {e}")


async def job_monitoreo_mtf(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not _en_horario_trading(): return
        try:
            hay_ev, _ = hay_evento_alto_impacto_pronto(minutos=20)
            if hay_ev: return
        except Exception:
            pass
        configs = obtener_todas_configs_bot()
        activos_default = ["EURUSD=X", "GBPUSD=X", "GC=F"]
        for cfg in configs:
            chat_id = cfg.get("telegram_chat_id", "")
            if not chat_id or not cfg.get("alertas_activas"): continue
            tf_bajo = cfg.get("tf_monitor", "15m")
            tf_map  = {"1m":"5m","5m":"1h","15m":"1h","30m":"4h","1h":"4h","4h":"1d"}
            tf_alto = tf_map.get(tf_bajo, "1h")
            try:
                activos = json.loads(cfg.get("activos_monitor", "[]")) or activos_default
            except Exception:
                activos = activos_default
            # Deduplicación MTF: misma lógica que señales estándar
            mtf_recientes = {
                (s.get("ticker", ""), s.get("direccion", ""))
                for s in obtener_señales_recientes(horas=1) if s.get("enviada_bot")
            }
            for ticker in activos:
                try:
                    mtf = analisis_mtf(ticker, tf_alto, tf_bajo)
                    if not mtf.get("alineacion"): continue
                    confianza_mtf = mtf.get("confianza_mtf", 0)
                    dir_mtf = mtf.get("direccion", "neutral")
                    clave_acc = (chat_id, ticker, dir_mtf)
                    clave_vig = (chat_id, ticker, dir_mtf, "w")
                    if confianza_mtf < 60:
                        _mtf_persistencia.pop(clave_acc, None)
                        _mtf_persistencia.pop(clave_vig, None)
                        continue
                    # Verificar que AMBOS timeframes tienen señal válida SMC
                    smc_alto = mtf.get("smc_alto", {})
                    smc_bajo = mtf.get("smc_bajo", {})
                    if not smc_alto.get("señal_valida") or not smc_bajo.get("señal_valida"):
                        _mtf_persistencia.pop(clave_acc, None)
                        _mtf_persistencia.pop(clave_vig, None)
                        continue
                    # FILTRO v4 MTF: RR mínimo 1.5:1 en los niveles calculados
                    entrada_m = mtf.get("entrada_sugerida") or 0
                    sl_m      = mtf.get("sl_sugerido")      or 0
                    tp_m      = mtf.get("tp_sugerido")      or 0
                    if entrada_m > 0 and sl_m > 0 and tp_m > 0:
                        _dsl = abs(entrada_m - sl_m)
                        _dtp = abs(tp_m - entrada_m)
                        if _dsl > 0 and (_dtp / _dsl) < 1.5:
                            _mtf_persistencia.pop(clave_acc, None)
                            _mtf_persistencia.pop(clave_vig, None)
                            continue
                    if confianza_mtf < 63:
                        # ── Alerta de vigilancia 60-62%: 3 checks (~45 min) + dedup 2h ──
                        _mtf_persistencia.pop(clave_acc, None)
                        _mtf_persistencia[clave_vig] = _mtf_persistencia.get(clave_vig, 0) + 1
                        if _mtf_persistencia[clave_vig] < 3: continue
                        if obtener_trade_activo(chat_id, ticker): continue
                        ahora_ts = datetime.now(TZ_MX).timestamp()
                        if ahora_ts - _watch_enviados.get(clave_acc, 0) < 7200: continue
                        _mtf_persistencia.pop(clave_vig, None)
                        _watch_enviados[clave_acc] = ahora_ts
                        icono = "🔴" if "SHORT" in dir_mtf else "🟢"
                        msg_w = (
                            f"👁 *SETUP EN FORMACIÓN — VIGILAR*\n"
                            f"📊 *{ticker}* — {tf_alto}/{tf_bajo}\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"⚠️ Confianza MTF: {confianza_mtf}% (zona de formación)\n"
                            f"{icono} Dirección: *{dir_mtf}* — ambos TF alineados\n\n"
                            f"💡 *No entrar aún* — espera en {tf_bajo}:\n"
                            f"   • Retroceso a OB/FVG con rechazo claro\n"
                            f"   • Cuando suba a ≥63% el bot alertará automáticamente\n"
                            f"   • O usa /mtf para revisar el setup manualmente\n\n"
                            f"🕐 {datetime.now(TZ_MX).strftime('%H:%M')} CDMX"
                        )
                        await _send(ctx.bot, chat_id, msg_w)
                        continue
                    # ── Alerta de acción ≥63%: 2 checks consecutivos (~30 min) ──
                    _mtf_persistencia.pop(clave_vig, None)
                    _mtf_persistencia[clave_acc] = _mtf_persistencia.get(clave_acc, 0) + 1
                    if _mtf_persistencia[clave_acc] < 2: continue
                    if (ticker, dir_mtf) in mtf_recientes: continue
                    if obtener_trade_activo(chat_id, ticker): continue
                    _mtf_persistencia.pop(clave_acc, None)
                    df_bajo_ctx, _ = obtener_datos(ticker, tf_bajo)
                    ctx_bajo = _calcular_contexto(df_bajo_ctx) if df_bajo_ctx is not None else {}
                    await _send(ctx.bot, chat_id, "🔭 *MTF ALINEADO — SEÑAL CONFIRMADA*\n" + _formato_mtf(mtf, ticker, contexto=ctx_bajo))
                    _senal_mtf = {"ticker": ticker, "tf": tf_bajo, "direccion": dir_mtf, "entrada": entrada_m, "sl": sl_m, "tp": tp_m, "confianza": confianza_mtf}
                    _ultimas_senales[(chat_id, ticker)] = _senal_mtf
                    _ultimas_senales[chat_id] = _senal_mtf
                except Exception as e:
                    logger.error(f"job_mtf {ticker}: {e}")
    except Exception as e:
        logger.error(f"job_monitoreo_mtf: {e}")


def _en_sesion_premium() -> bool:
    """Londres open (07-10 UTC) o NY open (13-16 UTC) — mayor actividad institucional."""
    from datetime import datetime, timezone
    h = datetime.now(timezone.utc).hour
    return (7 <= h < 10) or (13 <= h < 16)


def _cerca_nivel_redondo(precio: float) -> bool:
    """True si el precio está dentro de 15 pips de un nivel x.xx00 o x.xx50."""
    try:
        pips  = round(precio * 10000)
        resto = pips % 100
        return resto <= 15 or resto >= 85 or abs(resto - 50) <= 15
    except Exception:
        return False


async def job_monitoreo_reversal(ctx: ContextTypes.DEFAULT_TYPE):
    """
    Detecta el fin de correcciones dentro de zonas OB del HTF.
    7 capas de validación — la alerta de mayor probabilidad del sistema.
    """
    try:
        if not _en_horario_trading(): return
        if not _en_sesion_premium(): return   # Solo en apertura Londres/NY
        try:
            hay_ev, _ = hay_evento_alto_impacto_pronto(minutos=20)
            if hay_ev: return
        except Exception:
            pass

        tf_map         = {"1m": "5m", "5m": "1h", "15m": "1h", "30m": "4h", "1h": "4h", "4h": "1d"}
        configs        = obtener_todas_configs_bot()
        activos_default = ["EURUSD=X", "GBPUSD=X", "GC=F"]

        for cfg in configs:
            chat_id = cfg.get("telegram_chat_id", "")
            if not chat_id or not cfg.get("alertas_activas"): continue
            tf_bajo = cfg.get("tf_monitor", "15m")
            tf_alto = tf_map.get(tf_bajo, "1h")
            try:
                activos = json.loads(cfg.get("activos_monitor", "[]")) or activos_default
            except Exception:
                activos = activos_default

            reversal_recientes = {
                (s.get("ticker", ""), s.get("direccion", ""))
                for s in obtener_señales_recientes(horas=1) if s.get("enviada_bot")
            }

            for ticker in activos:
                try:
                    smc_alto, _ = _analizar_activo(ticker, tf_alto)
                    smc_bajo, _ = _analizar_activo(ticker, tf_bajo)
                    if not smc_alto or not smc_bajo: continue
                    if "error" in smc_alto or "error" in smc_bajo: continue

                    # CAPA 1: HTF precio EN zona OB institucional
                    if smc_alto.get("tipo_entrada", "limite_ob") != "mercado": continue

                    # CAPA 2: LTF muestra CHoCH — cambio de carácter, no solo BOS
                    tipo_bajo = smc_bajo.get("estructura", {}).get("tipo", "")
                    if "CHoCH" not in tipo_bajo: continue

                    # CAPA 3: Direcciones alineadas HTF == LTF
                    dir_alto = smc_alto.get("estructura", {}).get("direccion", "neutral")
                    dir_bajo = smc_bajo.get("estructura", {}).get("direccion", "neutral")
                    if dir_alto == "neutral" or dir_alto != dir_bajo: continue

                    # CAPA 4: LTF señal_valida y precio EN zona OB del retroceso
                    if not smc_bajo.get("señal_valida", False): continue
                    if smc_bajo.get("tipo_entrada", "limite_ob") != "mercado": continue

                    # CAPA 5: Confianza LTF >= 65%
                    conf_bajo = smc_bajo.get("confluencia", {}).get("confianza", 0)
                    if conf_bajo < 65: continue

                    # CAPA 6: RR >= 2.0 — esta es la entrada óptima, exigimos más
                    entrada = smc_bajo.get("precio", 0)
                    sl      = smc_bajo.get("sl_sugerido", 0)
                    tp      = smc_bajo.get("tp_sugerido", 0)
                    if entrada > 0 and sl > 0 and tp > 0:
                        dist_sl = abs(entrada - sl)
                        dist_tp = abs(tp - entrada)
                        if dist_sl > 0 and (dist_tp / dist_sl) < 2.0: continue

                    # CAPA 7: Barrido de liquidez previo al CHoCH
                    if not smc_bajo.get("barrido_liquidez", False): continue

                    if (ticker, dir_bajo) in reversal_recientes: continue

                    nivel_redondo = _cerca_nivel_redondo(entrada)
                    sig_id = registrar_señal(ticker, tf_bajo, tipo_bajo, dir_bajo, conf_bajo, entrada, sl, tp)
                    msg = "🎯 *REVERSIÓN EN ZONA HTF*\n" + _formato_reversal(
                        smc_alto, smc_bajo, ticker, tf_alto, tf_bajo, nivel_redondo
                    )
                    await _send(ctx.bot, chat_id, msg)
                    marcar_señal_enviada(sig_id)

                except Exception as e:
                    logger.error(f"job_reversal {ticker}: {e}")

    except Exception as e:
        logger.error(f"job_monitoreo_reversal: {e}")


async def job_verificar_alertas_precio(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        alertas = obtener_todas_alertas_activas()
        precios_cache = {}
        for alerta in alertas:
            ticker = alerta["ticker"]
            if ticker not in precios_cache:
                try:
                    df, _ = obtener_datos(ticker, "5m")
                    if df is not None:
                        precios_cache[ticker] = float(df["Close"].iloc[-1])
                except Exception:
                    continue
            precio_actual = precios_cache.get(ticker)
            if precio_actual is None: continue
            disparar = (
                (alerta["tipo"] == "above" and precio_actual >= alerta["precio"]) or
                (alerta["tipo"] == "below" and precio_actual <= alerta["precio"])
            )
            if not disparar: continue
            configs  = obtener_todas_configs_bot()
            chat_id  = next((c.get("telegram_chat_id") for c in configs if c["user_id"] == alerta["user_id"]), None)
            if not chat_id: continue
            emoji    = "📈" if alerta["tipo"] == "above" else "📉"
            dir_str  = "superó al alza" if alerta["tipo"] == "above" else "cayó por debajo de"
            diff     = abs(precio_actual - alerta["precio"])
            msg = (
                f"🔔 *ALERTA DE PRECIO DISPARADA*\n"
                "━━━━━━━━━━━━━━━━\n"
                f"{emoji} *{ticker}* {dir_str} `{alerta['precio']:.5f}`\n"
                f"💰 Precio actual: `{precio_actual:.5f}`\n"
                f"📏 Diferencia: {diff:.5f}\n"
                f"{alerta['mensaje'] or ''}\n"
                f"🕐 {_hora_mx()} CDMX\n\n"
                f"💡 _Usa /analizar {ticker.replace('=X','')} para análisis completo_"
            )
            await _send(ctx.bot, chat_id, msg)
            disparar_alerta(alerta["id"])

        # ── Monitoreo de trades confirmados (TP/SL) ──────────────────────────
        for trade in obtener_todos_trades_activos():
            ticker = trade["ticker"]
            if ticker not in precios_cache:
                try:
                    df_t, _ = obtener_datos(ticker, "5m")
                    if df_t is not None:
                        precios_cache[ticker] = float(df_t["Close"].iloc[-1])
                except Exception:
                    continue
            precio_actual = precios_cache.get(ticker)
            if precio_actual is None: continue
            dir_    = trade["direccion"]
            sl, tp  = trade["sl"], trade["tp"]
            entrada = trade["entrada"]
            tp_hit  = (dir_ == "SHORT" and precio_actual <= tp) or (dir_ == "LONG"  and precio_actual >= tp)
            sl_hit  = (dir_ == "SHORT" and precio_actual >= sl) or (dir_ == "LONG"  and precio_actual <= sl)
            if not tp_hit and not sl_hit: continue
            pips = _calcular_pips(ticker, tp if tp_hit else sl, entrada)
            resultado_trade = "tp" if tp_hit else "sl"
            if tp_hit:
                msg = (
                    f"🎯 *OBJETIVO ALCANZADO — TP HIT*\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{_emoji_dir(dir_)} *{ticker}* {dir_}\n"
                    f"💰 Entrada: `{entrada:.5f}`\n"
                    f"✅ TP: `{tp:.5f}` alcanzado\n"
                    f"📈 +{pips} pips\n"
                    f"🕐 {_hora_mx()} CDMX\n\n"
                    f"✅ Señales de *{ticker}* reactivadas."
                )
            else:
                msg = (
                    f"🛑 *STOP LOSS ALCANZADO*\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{_emoji_dir(dir_)} *{ticker}* {dir_}\n"
                    f"💰 Entrada: `{entrada:.5f}`\n"
                    f"🛑 SL: `{sl:.5f}` alcanzado\n"
                    f"📉 -{pips} pips\n"
                    f"🕐 {_hora_mx()} CDMX\n\n"
                    f"✅ Señales de *{ticker}* reactivadas."
                )
            try:
                await _send(ctx.bot, trade["chat_id"], msg)
                cerrar_trade_confirmado(trade["id"], resultado_trade)
            except Exception as e:
                logger.error(f"job_confirmed_trade notify {ticker}: {e}")
    except Exception as e:
        logger.error(f"job_verificar_alertas: {e}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_OK:
        print("ERROR: pip install python-telegram-bot APScheduler")
        return
    if not TOKEN:
        print("ERROR: Define TELEGRAM_BOT_TOKEN en .env")
        return
    try:
        inicializar_db()
    except Exception as e:
        logger.warning(f"DB init: {e}")

    print("🤖 Iniciando ORAM Quant Bot v3...")
    app = Application.builder().token(TOKEN).build()

    for cmd, handler in [
        ("start",       cmd_start),
        ("mercado",     cmd_mercado),
        ("senales",     cmd_senales),
        ("analizar",    cmd_analizar),
        ("mtf",         cmd_mtf),
        ("riesgo",      cmd_riesgo),
        ("kelly",       cmd_kelly),
        ("trades",      cmd_trades),
        ("performance", cmd_performance),
        ("backtest",    cmd_backtest),
        ("watchlist",   cmd_watchlist),
        ("capital",     cmd_capital),
        ("noticias",    cmd_noticias),
        ("proximos",    cmd_proximos),
        ("sesiones",    cmd_sesiones),
        ("alertas",     cmd_alertas),
        ("resumen",     cmd_resumen),
        ("ayuda",       cmd_ayuda),
        ("tomar",       cmd_tomar),
        ("cerrar",      cmd_cerrar),
        ("activos",     cmd_activos),
    ]:
        app.add_handler(CommandHandler(cmd, handler))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_desconocido))

    jq = app.job_queue
    if jq is not None:
        jq.run_daily(job_resumen_diario,  time=dtime(hour=13, minute=0))   # 7AM CDMX
        jq.run_daily(job_reporte_cierre,  time=dtime(hour=22, minute=0))   # 4PM CDMX / NY close
        jq.run_repeating(job_monitoreo_senales,       interval=300, first=60)
        jq.run_repeating(job_monitoreo_mtf,           interval=900, first=120)
        jq.run_repeating(job_monitoreo_reversal,      interval=60,  first=90)
        jq.run_repeating(job_verificar_alertas_precio, interval=300, first=30)
        jq.run_repeating(job_alerta_noticias,         interval=300, first=60)
        print("✅ Jobs activos: Apertura 7AM · Cierre 4PM · Señales c/5m · MTF c/15m · Reversal c/1m · Alertas precio c/5m · Noticias c/5m")
    else:
        print("⚠️  Sin jobs. Instala: pip install APScheduler")

    print("\n✅ Bot v3 activo. Ctrl+C para detener.")
    import time as _time_mod
    _retry_delay = 5
    while True:
        try:
            app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            break  # salida limpia (Ctrl+C / señal de SO)
        except KeyboardInterrupt:
            break
        except Exception as _e:
            logger.error(f"Polling interrumpido: {_e}. Reconectando en {_retry_delay}s...")
            _time_mod.sleep(_retry_delay)
            _retry_delay = min(_retry_delay * 2, 60)  # backoff exponencial hasta 60s


if __name__ == "__main__":
    main()
