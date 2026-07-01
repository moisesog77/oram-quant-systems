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
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
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
from utils.news_feed import (formatear_noticias_telegram, obtener_noticias_ticker,
                              contexto_noticia_ticker, contexto_noticias_activos)
from utils.ai_engine         import analizar_performance_ia, calcular_drawdown, calcular_sharpe
from database.db import (
    obtener_todas_configs_bot, obtener_todas_alertas_activas,
    disparar_alerta, registrar_señal, marcar_señal_enviada,
    obtener_señales_recientes, inicializar_db,
    obtener_todos_usuarios, obtener_usuario_por_id,
    obtener_trades, obtener_watchlist,
    registrar_trade_confirmado, obtener_trade_activo,
    obtener_trades_activos_chat, obtener_todos_trades_activos,
    cerrar_trade_confirmado, insertar_trade,
)

import pandas as pd

TZ_MX  = ZoneInfo("America/Mexico_City")
TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
MD     = "Markdown"

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

UMBRAL_ALERTA_ALTA  = 75
UMBRAL_ALERTA_MEDIA = 65
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

# Persistencia señales regulares — si se mantiene 60-64% por 3 checks seguidos (~15 min) → alerta excepción
# clave: (chat_id, ticker, dir)  → checks consecutivos en zona 60-umbral
_persistencia_senales: dict = {}
_watch_senales_enviados: dict = {}   # dedup 2h para alertas de excepción por señal
_dedup_scalp: dict = {}              # (chat_id, ticker, dir) → timestamp último envío scalp

# Alerta de mercado en rango — dedup 2h por chat
_ultima_alerta_rango: dict = {}
_checks_sin_senal:    dict = {}   # chat_id → checks consecutivos sin señal

# Trades pendientes de confirmar desde Telegram — sig_id → datos de la señal
_pending_trades: dict = {}


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


# ─── Helpers de formato ───────────────────────────────────────────────────────

def _fmt_precio(precio: float, ticker: str) -> str:
    """Formatea el precio con los decimales correctos según el broker."""
    t = ticker.upper()
    if any(x in t for x in ("GC=F", "XAUUSD", "GOLD", "CL=F", "WTIUSD", "OIL")):
        return f"{precio:.2f}"
    elif "JPY" in t:
        return f"{precio:.3f}"
    else:
        return f"{precio:.5f}"


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
            smc["_data_source"] = "⚠️ yfinance — 15min delay"
        else:
            smc["_data_source"] = "🟢 Twelve Data — Tiempo real"
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

_DIAS_ES = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

def _dia_es(dt=None) -> str:
    if dt is None: dt = datetime.now(TZ_MX)
    return _DIAS_ES[dt.weekday()]

def _fecha_es(dt=None, hora: bool = True) -> str:
    """Fecha en español: 'Miércoles 25/06/2026 — 07:00'"""
    if dt is None: dt = datetime.now(TZ_MX)
    base = f"{_dia_es(dt)} {dt.strftime('%d/%m/%Y')}"
    return f"{base} — {dt.strftime('%H:%M')}" if hora else base

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

def _en_horario_alertas() -> bool:
    """Alertas automáticas: 6:30–17:00 CDMX, lunes a viernes."""
    if not _en_horario_trading():
        return False
    ahora = datetime.now(TZ_MX)
    hora_dec = ahora.hour + ahora.minute / 60
    return 6.5 <= hora_dec < 17

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

    # Acción clara: COMPRAR / VENDER
    accion = "🟢 *COMPRAR*" if dir_ == "LONG" else "🔴 *VENDER*" if dir_ == "SHORT" else "⚪ *NEUTRAL*"

    # Tipo de orden sugerido según tipo de señal y entrada
    fp = lambda p: _fmt_precio(p, ticker)

    if tipo_entrada in ("limite_ob", "limite_fvg"):
        orden_tipo = "Límite"
        if tipo_entrada == "limite_ob":
            entrada_txt = f"📍 *Entrada:* Límite en OB `{fp(entrada_ideal)}` (~{retroceso_pips:.0f} pips)"
        else:
            entrada_txt = f"📍 *Entrada:* Límite en FVG `{fp(entrada_ideal)}` (~{retroceso_pips:.0f} pips)"
    elif "BOS" in tipo:
        orden_tipo = "Stop Limit"
        entrada_txt = f"📍 *Entrada:* Stop Limit en `{fp(precio)}` (ruptura de nivel)"
    else:
        orden_tipo = "Mercado"
        entrada_txt = f"📍 *Entrada:* Mercado (precio ya en zona)"

    ctx     = smc.get("_contexto_mercado", {})
    ctx_txt = f"{ctx.get('icono','')} _{ctx.get('texto','')}_" if ctx.get("texto") else ""

    lineas = [
        f"{'🚨' if pct >= 75 else '📡'} *SEÑAL SMC — {prio}*",
        f"{emoji} *{ticker}* · {tf}",
        "━━━━━━━━━━━━━━━━",
        f"📌 *Señal:* {tipo}",
        f"👉 *Acción:* {accion}  |  📋 *Orden:* {orden_tipo}",
        f"💰 *Precio actual:* `{fp(precio)}`",
        entrada_txt,
        f"🎯 *Confianza:* {_conf_bar(pct)}",
        ctx_txt,
        "",
    ]
    if sl and tp:
        lineas += [
            f"✅ *TP:* `{fp(tp)}`",
            f"🛑 *SL:* `{fp(sl)}`",
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
        f"📉 *RSI:* {rsi:.1f}  |  📏 *ATR:* {fp(atr)}",
        f"📈 *EMA50:* {fp(ema50)}" if ema50 else "",
    ]
    if factores:
        lineas += ["", "⚡ *Confluencias:*"]
        for f in factores:
            lineas.append(f"  ✔ {f}")
    lineas += ["", f"🕐 *{_hora_mx()} CDMX*", "⚠️ _Señal orientativa. Usa SL siempre._"]
    data_source = smc.get("_data_source")
    if data_source:
        lineas.append(f"📡 _Fuente: {data_source}_")
    return "\n".join(l for l in lineas if l)

def _formato_mtf(mtf: dict, ticker: str, contexto: dict = None, data_source: str = None) -> str:
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
        accion_mtf = "🟢 *COMPRAR*" if dir_bajo == "LONG" else "🔴 *VENDER*" if dir_bajo == "SHORT" else "⚪ *NEUTRAL*"
        orden_mtf  = "Stop Limit" if "BOS" in tipo_bajo else "Límite" if "CHoCH" in tipo_bajo else "Mercado"
        lineas += [
            "",
            f"👉 *Acción:* {accion_mtf}  |  📋 *Orden:* {orden_mtf}",
            f"💰 *Entrada sugerida:* `{_fmt_precio(entrada, ticker)}`",
            f"✅ *TP:* `{_fmt_precio(tp, ticker)}`" if tp else "",
            f"🛑 *SL:* `{_fmt_precio(sl, ticker)}`" if sl else "",
        ]

    # Entrada discrecional cuando solo TF bajo tiene señal (≥60%) sin confirmación HTF
    entrada_disc = mtf.get("entrada_discrecional")
    sl_disc      = mtf.get("sl_discrecional")
    tp_disc      = mtf.get("tp_discrecional")
    dir_disc     = mtf.get("dir_discrecional", "neutral")
    conf_disc    = mtf.get("conf_discrecional", 0)
    if not alineado and entrada_disc and conf_disc >= 60:
        accion_disc = "🟢 *COMPRAR*" if dir_disc == "LONG" else "🔴 *VENDER*"
        orden_disc  = "Stop Limit" if "BOS" in tipo_bajo else "Límite" if "CHoCH" in tipo_bajo else "Mercado"
        dist_sl_d   = abs(entrada_disc - sl_disc) if sl_disc else 0
        dist_tp_d   = abs(tp_disc - entrada_disc) if tp_disc else 0
        rr_d        = round(dist_tp_d / dist_sl_d, 1) if dist_sl_d > 0 else 0
        lineas += [
            "",
            "──────────────",
            f"⚡ *ENTRADA DISCRECIONAL ({tf_bajo} solo)*",
            f"👉 *Acción:* {accion_disc}  |  📋 *Orden:* {orden_disc}",
            f"💰 *Entrada:* `{_fmt_precio(entrada_disc, ticker)}`",
            f"✅ *TP:* `{_fmt_precio(tp_disc, ticker)}`"  if tp_disc else "",
            f"🛑 *SL:* `{_fmt_precio(sl_disc, ticker)}`"  if sl_disc else "",
            f"📊 *RR estimado:* {rr_d}:1"                 if rr_d > 0 else "",
            f"⚠️ _Sin confirmación {tf_alto} — opera con tamaño reducido_",
        ]

    ctx_txt = ""
    if contexto and contexto.get("texto"):
        ctx_txt = f"{contexto.get('icono','')} _{contexto.get('texto','')}_"
    lineas += ["", f"📝 _{desc}_", ctx_txt, ""]
    if data_source:
        lineas.append(f"📡 _Fuente: {data_source}_")
    lineas.append(f"🕐 {_hora_mx()} CDMX")
    return "\n".join(l for l in lineas if l)


def _formato_reversal(smc_alto: dict, smc_bajo: dict, ticker: str,
                       tf_alto: str, tf_bajo: str, nivel_redondo: bool = False,
                       data_source: str = None) -> str:
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
        f"💰 *Entrada:* `{_fmt_precio(entrada, ticker)}`",
        f"✅ *TP:*     `{_fmt_precio(tp, ticker)}`" if tp else "",
        f"🛑 *SL:*     `{_fmt_precio(sl, ticker)}`" if sl else "",
        f"📊 *RR:*     `{rr:.1f}:1`",
    ]
    if extras:
        lineas += [""] + extras
    lineas += [
        "",
        "⚡ _Stop hunt + CHoCH + zona HTF — setup institucional completo_",
    ]
    if data_source:
        lineas.append(f"📡 _Fuente: {data_source}_")
    lineas.append(f"🕐 {_hora_mx()} CDMX")
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
    _fuentes_mercado = set()
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
                    _ds_merc = smc.get("_data_source", "")
                    if _ds_merc: _fuentes_mercado.add(_ds_merc)
                    lineas.append(
                        f"{_emoji_dir(dir_)}{prio} *{ticker}* `{_fmt_precio(precio, ticker)}` — {tipo} ({conf:.0f}%) RSI:{rsi:.0f}"
                    )
                    try:
                        _noticia_merc = contexto_noticia_ticker(ticker)
                        if _noticia_merc:
                            lineas.append(f"   {_noticia_merc}")
                    except Exception:
                        pass
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
    if _fuentes_mercado:
        lineas += ["", f"📡 _Fuente: {' | '.join(_fuentes_mercado)}_"]
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

    umbral = float(cfg.get("umbral_confianza", 65)) if cfg else 65
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
        _ctx_sin_senal = ""
        try:
            _ctx_sin_senal = contexto_noticias_activos(activos, max_items=2)
        except Exception:
            pass
        await _reply(update,
            f"⚪ *Sin señales ≥{umbral:.0f}% en este momento*\n\n"
            + (_ctx_sin_senal + "\n\n" if _ctx_sin_senal else "")
            + "💡 *Mejores horarios:*\n"
            "🟡 London Open: 02:00-04:00 CDMX\n"
            "🔥 Overlap L+NY: 07:00-10:00 CDMX\n"
            "🟠 NY Open: 07:30-09:30 CDMX\n\n"
            "💡 Prueba /mtf para análisis multi-timeframe."
        )
        return

    capital    = float(cfg.get("capital_cuenta") or 0) or float(user.get("capital_inicial", 10000) if user else 10000.0) if cfg else 10000.0
    riesgo_pct = float(cfg.get("riesgo_pct", 2.0)) if cfg else 2.0

    if altas:
        await update.message.reply_text(f"🔥 *{len(altas)} señal(es) ALTA PRIORIDAD:*", parse_mode=MD)
        for ticker, smc, conf in sorted(altas, key=lambda x: -x[2]):
            _msg_alta = _formato_senal_completo(smc, ticker, tf, capital, riesgo_pct)
            try:
                _noticia_alta = contexto_noticia_ticker(ticker)
                if _noticia_alta:
                    _msg_alta += f"\n{_noticia_alta}"
            except Exception:
                pass
            await _reply(update, _msg_alta)
    if medias:
        await update.message.reply_text(f"⚡ *{len(medias)} señal(es) media:*", parse_mode=MD)
        for ticker, smc, conf in sorted(medias, key=lambda x: -x[2]):
            tipo  = smc.get("estructura", {}).get("tipo", "?")
            dir_  = smc.get("estructura", {}).get("direccion", "neutral")
            prec  = smc.get("precio", 0)
            sl    = smc.get("sl_sugerido", 0)
            tp    = smc.get("tp_sugerido", 0)
            _ds_sm = smc.get("_data_source", "")
            await _reply(update,
                f"{_emoji_dir(dir_)} *{ticker}* `{_fmt_precio(prec, ticker)}` — {tipo} ({conf:.0f}%)\n"
                f"   TP:`{_fmt_precio(tp, ticker)}` SL:`{_fmt_precio(sl, ticker)}`"
                + (f"\n📡 _{_ds_sm}_" if _ds_sm else "")
            )


async def cmd_analizar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Análisis SMC completo. Sin args → analiza los 3 activos. /analizar EURUSD [TF] → par específico."""
    args    = ctx.args
    chat_id = str(update.effective_chat.id)
    user, cfg = _get_user_by_chat(chat_id)
    capital    = float(cfg.get("capital_cuenta") or 0) or float(user.get("capital_inicial", 10000) if user else 10000.0) if cfg else 10000.0
    riesgo_pct = float(cfg.get("riesgo_pct", 2.0)) if cfg else 2.0

    if not args:
        # Sin argumentos: analizar todos los activos configurados
        try:
            activos = json.loads(cfg.get("activos_monitor", "[]")) if cfg else []
        except Exception:
            activos = []
        if not activos:
            activos = ["EURUSD=X", "GBPUSD=X", "GC=F"]
        tf = "15m"
        await update.message.reply_text(f"🔍 Analizando {len(activos)} activos en {tf}...")
        for tkr in activos:
            try:
                smc, status = _analizar_activo(tkr, tf)
                if not smc or "error" in smc:
                    await _reply(update, f"⚪ *{tkr}* — Sin datos suficientes\n_{status}_")
                    continue
                msg  = _formato_senal_completo(smc, tkr, tf, capital, riesgo_pct)
                obs  = smc.get("order_blocks", [])
                fvgs = smc.get("fvgs", [])
                liq  = smc.get("liquidez", {})
                extras = ["\n━━━━━━━━━━━━━━━━", "📐 *Niveles SMC:*"]
                if obs:
                    ob = obs[0]
                    extras.append(f"  🟦 OB: `{_fmt_precio(ob.precio_bot, tkr)}` – `{_fmt_precio(ob.precio_top, tkr)}` (fuerza: {ob.fuerza:.0%})")
                if fvgs:
                    fvg = fvgs[0]
                    extras.append(f"  🟨 FVG: `{_fmt_precio(fvg.precio_bot, tkr)}` – `{_fmt_precio(fvg.precio_top, tkr)}`")
                if liq:
                    res_lvls = liq.get("resistance_levels", [])
                    sup_lvls = liq.get("support_levels", [])
                    if res_lvls: extras.append(f"  🔴 Resistencias: {', '.join([f'`{_fmt_precio(x, tkr)}`' for x in res_lvls[:2]])}")
                    if sup_lvls: extras.append(f"  🟢 Soportes: {', '.join([f'`{_fmt_precio(x, tkr)}`' for x in sup_lvls[:2]])}")
                try:
                    _noticia_an = contexto_noticia_ticker(tkr)
                    if _noticia_an:
                        extras += ["", _noticia_an]
                except Exception:
                    pass
                await _reply(update, msg + "\n" + "\n".join(extras))
            except Exception as e:
                logger.error(f"cmd_analizar {tkr}: {e}")
                await update.message.reply_text(f"❌ {tkr}: {str(e)[:80]}")
        return

    ticker = _normalizar_ticker(args[0])
    tf = args[1] if len(args) > 1 else "15m"

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
            extras.append(f"  🟦 OB: `{_fmt_precio(ob.precio_bot, ticker)}` – `{_fmt_precio(ob.precio_top, ticker)}` (fuerza: {ob.fuerza:.0%})")
        if fvgs:
            fvg = fvgs[0]
            extras.append(f"  🟨 FVG: `{_fmt_precio(fvg.precio_bot, ticker)}` – `{_fmt_precio(fvg.precio_top, ticker)}`")
        if liq:
            res = liq.get("resistance_levels", [])
            sup = liq.get("support_levels", [])
            if res: extras.append(f"  🔴 Resistencias: {', '.join([f'`{_fmt_precio(x, ticker)}`' for x in res[:2]])}")
            if sup: extras.append(f"  🟢 Soportes: {', '.join([f'`{_fmt_precio(x, ticker)}`' for x in sup[:2]])}")
        try:
            _noticia_an1 = contexto_noticia_ticker(ticker)
            if _noticia_an1:
                extras += ["", _noticia_an1]
        except Exception:
            pass
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
                _, _st = obtener_datos(tkr, tf_alto)
                _ds = "⚠️ yfinance — 15min delay" if "yfinance" in _st else "🟢 Twelve Data — Tiempo real"
                _mtf_txt = _formato_mtf(mtf, tkr, data_source=_ds)
                try:
                    _noticia_mtf = contexto_noticia_ticker(tkr)
                    if _noticia_mtf:
                        _mtf_txt += f"\n{_noticia_mtf}"
                except Exception:
                    pass
                await _reply(update, _mtf_txt)
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
        _, _st = obtener_datos(ticker, tf_alto)
        _ds = "⚠️ yfinance — 15min delay" if "yfinance" in _st else "🟢 Twelve Data — Tiempo real"
        _mtf_msg = _formato_mtf(mtf, ticker, data_source=_ds)
        try:
            _noticia_mtf1 = contexto_noticia_ticker(ticker)
            if _noticia_mtf1:
                _mtf_msg += f"\n{_noticia_mtf1}"
        except Exception:
            pass
        await _reply(update, _mtf_msg)
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
        capital    = float(cfg.get("capital_cuenta") or 0) or float(user.get("capital_inicial", 10000) if user else 10000.0) if cfg else 10000.0
        riesgo_pct = float(cfg.get("riesgo_pct", 2.0)) if cfg else 2.0

        res = calcular_riesgo(entrada, sl, tp, capital, riesgo_pct)
        if not res:
            await update.message.reply_text("❌ Error en los datos. Verifica que SL ≠ entrada.")
            return

        dir_  = "LONG" if tp > entrada else "SHORT"
        await _reply(update,
            f"💼 *CALCULADORA DE RIESGO*\n"
            f"{_emoji_dir(dir_)} *{ticker}* — {dir_}\n"
            "━━━━━━━━━━━━━━━━\n"
            f"💰 Entrada: `{_fmt_precio(entrada, ticker)}`\n"
            f"✅ TP: `{_fmt_precio(tp, ticker)}` ({res['pips_tp']:.1f} pips)\n"
            f"🛑 SL: `{_fmt_precio(sl, ticker)}` ({res['pips_sl']:.1f} pips)\n"
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
                    f"{_emoji_dir(dir_)}{prio} *{nombre}* `{_fmt_precio(precio, ticker)}`\n"
                    f"   {tipo} ({conf:.0f}%) · RSI:{rsi:.0f}"
                )
                try:
                    _noticia_wl = contexto_noticia_ticker(ticker)
                    if _noticia_wl:
                        lineas.append(f"   {_noticia_wl}")
                except Exception:
                    pass
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
            f"⚙️ Umbral señales: {cfg.get('umbral_confianza', 65):.0f}%\n"
            f"⏱ TF monitor: {cfg.get('tf_monitor', '15m')}\n"
            f"🕐 {_hora_mx()} CDMX"
        )
    except Exception as e:
        await _reply(update, f"❌ Error: {str(e)[:100]}")


async def cmd_setcapital(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Actualiza el capital de cuenta para cálculo de volumen. Uso: /setcapital 100"""
    chat_id = str(update.effective_chat.id)
    user, cfg = _get_user_by_chat(chat_id)
    if not user:
        await _reply(update, "⚙️ Vincula tu Chat ID primero en la app → Bot Telegram.")
        return
    args = ctx.args or []
    if not args:
        capital_actual = float(cfg.get("capital_cuenta") or 0) if cfg else 0
        riesgo_actual  = float(cfg.get("riesgo_pct", 2.0)) if cfg else 2.0
        await _reply(update,
            f"💼 *Capital configurado:* ${capital_actual:.2f}\n"
            f"📊 *Riesgo por trade:* {riesgo_actual:.2f}%\n"
            f"💡 Riesgo por operación: *${capital_actual * riesgo_actual / 100:.2f}*\n\n"
            f"_Uso: /setcapital 150 — para actualizar a $150_"
        )
        return
    try:
        nuevo_capital = float(args[0])
        if nuevo_capital < 0:
            raise ValueError
    except (ValueError, IndexError):
        await _reply(update, "❌ Uso correcto: `/setcapital 100` (monto en USD)")
        return
    from database.db import actualizar_bot_config
    actualizar_bot_config(user["id"], capital_cuenta=nuevo_capital)
    riesgo_pct = float(cfg.get("riesgo_pct", 2.0)) if cfg else 2.0
    riesgo_usd = nuevo_capital * riesgo_pct / 100
    await _reply(update,
        f"✅ *Capital actualizado: ${nuevo_capital:.2f}*\n"
        f"📊 Riesgo por trade ({riesgo_pct:.1f}%): *${riesgo_usd:.2f} USD*\n\n"
        f"_Las próximas señales calcularán el volumen con este capital._"
    )


async def cmd_noticias(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lineas = [
        "📰 *NOTICIAS Y EVENTOS DEL MERCADO*",
        f"_{_fecha_es()} CDMX_",
        "━━━━━━━━━━━━━━━━",
    ]

    # ── Noticias en tiempo real (mismas fuentes que TradingView) ──
    try:
        bloque_news = formatear_noticias_telegram(max_por_cat=3)
        if bloque_news:
            # Quitar encabezado propio del bloque (ya lo tenemos arriba)
            for linea in bloque_news.split("\n")[2:]:
                lineas.append(linea)
        else:
            lineas.append("_Sin noticias recientes disponibles._")
    except Exception:
        lineas.append("_Sin noticias recientes disponibles._")

    # ── Eventos económicos del día ──
    lineas += ["", "📅 *EVENTOS ECONÓMICOS HOY:*", "━━━━━━━━━━━━━━━━"]
    try:
        eventos = obtener_eventos_hoy()
        if eventos:
            for ev in eventos:
                estado = "✅" if ev["ya_paso"] else "⏳"
                lineas.append(
                    f"{estado} {impacto_emoji(ev['impacto'])} *{ev['hora_mx']}* — {ev['titulo']} ({ev['moneda']})"
                )
            lineas.append("\n⚠️ _Evita operar ±30 min alrededor de eventos 🔴_")
        else:
            lineas.append("_Sin eventos de alto impacto hoy._")
    except Exception:
        lineas.append("_Sin eventos disponibles._")

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
        f"🕐 _Ahora: {ahora.strftime('%H:%M')} CDMX ({_dia_es(ahora)})_\n"
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
        "/analizar — Análisis SMC (3 activos) o /analizar EURUSD [1h]\n"
        "/mtf — Multi-Timeframe (3 activos) o /mtf EURUSD [swing]\n"
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
        f"💰 Entrada: `{_fmt_precio(senal['entrada'], ticker)}`\n"
        f"✅ TP: `{_fmt_precio(senal['tp'], ticker)}`\n"
        f"🛑 SL: `{_fmt_precio(senal['sl'], ticker)}`\n\n"
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
        f"Entrada: `{_fmt_precio(trade['entrada'], trade['ticker'])}`\n"
        + (f"Precio cierre: `{_fmt_precio(precio_actual, trade['ticker'])}`" if precio_actual else "") + pips_txt + "\n\n"
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
            f"  Entrada: `{_fmt_precio(t['entrada'], t['ticker'])}`  TP: `{_fmt_precio(t['tp'], t['ticker'])}`  SL: `{_fmt_precio(t['sl'], t['ticker'])}`",
            f"  Precio: `{_fmt_precio(precio_actual, t['ticker'])}`" if precio_actual else "",
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
            f"_{_fecha_es()} CDMX_\n"
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
        f"_{_fecha_es()} CDMX_",
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
                    f"{_emoji_dir(dir_)}{prio} *{ticker}* `{_fmt_precio(precio, ticker)}` — {tipo} ({conf:.0f}%) RSI:{rsi:.0f}"
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
    ]
    try:
        bloque_news = formatear_noticias_telegram(max_por_cat=2)
        if bloque_news:
            lineas.append("")
            lineas += bloque_news.split("\n")
    except Exception:
        pass
    lineas += [
        "━━━━━━━━━━━━━━━━",
        "⚠️ _Max 1-2% riesgo por trade_",
        "🤖 _ORAM Quant Systems_",
    ]
    return "\n".join(lineas)


async def job_resumen_diario(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        from datetime import timezone as _tz
        wd = datetime.now(_tz.utc).weekday()
        if wd in (5, 6):   # sábado o domingo — sin mensaje
            return
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
        f"_{_fecha_es(ahora)} CDMX_",
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
                        f"{_emoji_dir(dir_)} *{ticker}* `{_fmt_precio(precio, ticker)}` — {tipo} ({conf:.0f}%) RSI:{rsi:.0f}"
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
    ]
    try:
        bloque_news = formatear_noticias_telegram(max_por_cat=2)
        if bloque_news:
            lineas.append("")
            lineas += bloque_news.split("\n")
    except Exception:
        pass
    lineas += [
        "━━━━━━━━━━━━━━━━",
        "⚠️ _Max 1-2% riesgo por trade_",
        "🤖 _ORAM Quant Systems_",
    ]
    return "\n".join(lineas)


async def job_reporte_cierre(ctx: ContextTypes.DEFAULT_TYPE):
    """Reporte de fin de día al NY close (22:00 UTC = 16:00 CDMX). Solo lunes-viernes."""
    try:
        from datetime import timezone as _tz
        wd = datetime.now(_tz.utc).weekday()
        if wd in (5, 6):   # sábado o domingo — sin reporte
            return
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
        if not _en_horario_trading():
            return
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
        if not _en_horario_alertas():
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
            umbral = max(float(cfg.get("umbral_confianza", 65)), 65.0)
            tf     = cfg.get("tf_monitor", "15m")
            try:
                activos = json.loads(cfg.get("activos_monitor", "[]")) or activos_default
            except Exception:
                activos = activos_default

            user_id = cfg.get("user_id")
            user    = obtener_usuario_por_id(user_id)
            capital    = float(cfg.get("capital_cuenta") or 0) or float(user.get("capital_inicial", 10000) if user else 10000.0)
            riesgo_pct = float(cfg.get("riesgo_pct", 2.0))

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

                    if dir_ == "neutral" or conf < 60:
                        # Por debajo del mínimo absoluto — limpiar persistencia
                        _persistencia_senales.pop((chat_id, ticker, dir_), None)
                        continue

                    if conf < umbral:
                        # Zona de persistencia: 60% ≤ conf < umbral configurado
                        # Si se mantiene sostenido 3 checks (~15 min) → alerta de excepción
                        clave_p = (chat_id, ticker, dir_)
                        _persistencia_senales[clave_p] = _persistencia_senales.get(clave_p, 0) + 1
                        ahora_ts = datetime.now(TZ_MX).timestamp()
                        if (_persistencia_senales[clave_p] >= 3 and
                                smc.get("señal_valida", False) and
                                ahora_ts - _watch_senales_enviados.get(clave_p, 0) > 7200):
                            _persistencia_senales[clave_p] = 0
                            _watch_senales_enviados[clave_p] = ahora_ts
                            accion = "🟢 *COMPRAR*" if dir_ == "LONG" else "🔴 *VENDER*"
                            _ds_sos = smc.get("_data_source", "")
                            _sos_noticia = ""
                            try:
                                _sos_noticia = contexto_noticia_ticker(ticker)
                            except Exception:
                                pass
                            await _send(ctx.bot, chat_id,
                                f"👁 *SETUP SOSTENIDO — VIGILAR*\n"
                                f"━━━━━━━━━━━━━━━━\n"
                                f"{accion} *{ticker}* · {tf}\n"
                                f"Confianza: {conf:.0f}% — sostenida ~15 min\n"
                                f"💰 `{_fmt_precio(precio, ticker)}` · TP `{_fmt_precio(tp_, ticker)}` · SL `{_fmt_precio(sl, ticker)}`\n"
                                + (f"{_sos_noticia}\n" if _sos_noticia else "")
                                + f"⚠️ _Señal por debajo del umbral ({umbral:.0f}%) pero persistente. Valida en chart._\n"
                                + (f"📡 _{_ds_sos}_\n" if _ds_sos else "")
                                + f"🕐 {_hora_mx()} CDMX"
                            )
                        continue

                    # Confianza ≥ umbral — flujo normal
                    _persistencia_senales.pop((chat_id, ticker, dir_), None)
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
                    dir_  = smc.get("estructura", {}).get("direccion", "")
                    tipo  = smc.get("estructura", {}).get("tipo", "SMC Signal")
                    msg   = "🚨 *SEÑAL ALTA PRIORIDAD*\n" + _formato_senal_completo(smc, ticker, tf, capital, riesgo_pct)
                    try:
                        noticia_ctx = contexto_noticia_ticker(ticker)
                        if noticia_ctx:
                            msg += f"\n{noticia_ctx}"
                    except Exception:
                        pass
                    # Guardar datos para registro rápido desde Telegram
                    _pending_trades[sig_id] = {
                        "ticker": ticker, "tf": tf, "direccion": dir_,
                        "entrada": smc.get("precio", 0), "sl": smc.get("sl_sugerido", 0),
                        "tp": smc.get("tp_sugerido", 0), "confianza": conf,
                        "setup": tipo, "fecha": datetime.now(TZ_MX).strftime("%Y-%m-%d"),
                    }
                    if len(_pending_trades) > 50:
                        _pending_trades.pop(next(iter(_pending_trades)))
                    kbd = InlineKeyboardMarkup([[InlineKeyboardButton(
                        "📝 Registrar en diario", callback_data=f"reg_{sig_id}"
                    )]])
                    try:
                        await ctx.bot.send_message(chat_id=chat_id, text=msg, parse_mode=MD, reply_markup=kbd)
                    except Exception:
                        plain = msg.replace("*","").replace("_","").replace("`","")
                        await ctx.bot.send_message(chat_id=chat_id, text=plain[:4000], reply_markup=kbd)
                    marcar_señal_enviada(sig_id)
                    _senal = {"ticker": ticker, "tf": tf, "direccion": dir_, "entrada": smc.get("precio",0), "sl": smc.get("sl_sugerido",0), "tp": smc.get("tp_sugerido",0), "confianza": conf, "setup": tipo}
                    _ultimas_senales[(chat_id, ticker)] = _senal
                    _ultimas_senales[chat_id] = _senal
                except Exception as e:
                    logger.error(f"send alta {ticker}: {e}")

            if medias:
                lineas = [f"⚡ *SEÑALES MEDIAS — {tf} · {_hora_mx()} CDMX*", ""]
                _primera_media = True
                _fuentes_medias = set()
                for ticker, smc, conf, sig_id in sorted(medias, key=lambda x: -x[2]):
                    if obtener_trade_activo(chat_id, ticker): continue
                    dir_  = smc.get("estructura", {}).get("direccion", "neutral")
                    tipo  = smc.get("estructura", {}).get("tipo", "?")
                    precio = smc.get("precio", 0)
                    sl    = smc.get("sl_sugerido", 0)
                    tp_   = smc.get("tp_sugerido", 0)
                    lineas.append(
                        f"{_emoji_dir(dir_)} *{ticker}* `{_fmt_precio(precio, ticker)}` — {tipo} ({conf:.0f}%)\n"
                        f"   TP:`{_fmt_precio(tp_, ticker)}` SL:`{_fmt_precio(sl, ticker)}`"
                    )
                    _ds_m = smc.get("_data_source", "")
                    if _ds_m: _fuentes_medias.add(_ds_m)
                    marcar_señal_enviada(sig_id)
                    _senal = {"ticker": ticker, "tf": tf, "direccion": dir_, "entrada": precio, "sl": sl, "tp": tp_, "confianza": conf}
                    _ultimas_senales[(chat_id, ticker)] = _senal
                    if _primera_media:
                        _ultimas_senales[chat_id] = _senal  # solo la de mayor confianza
                        _primera_media = False
                if _fuentes_medias:
                    lineas.append(f"\n📡 _Fuente: {' | '.join(_fuentes_medias)}_")
                if len(lineas) > 2:  # solo enviar si hay señales reales (no solo el header)
                    try:
                        await _send(ctx.bot, chat_id, "\n".join(lineas))
                    except Exception as e:
                        logger.error(f"send medias: {e}")

            # ── Alerta de mercado en rango ────────────────────────────────────
            if not altas and not medias:
                _checks_sin_senal[chat_id] = _checks_sin_senal.get(chat_id, 0) + 1
                ahora_ts = datetime.now(TZ_MX).timestamp()
                hora_mx  = datetime.now(TZ_MX).hour
                # Solo enviar en horario activo: 5am–5pm CDMX (fuera de sesión asiática)
                en_horario_activo = 5 <= hora_mx < 17
                # Enviar después de 12 checks (~60 min) sin señal y sin haberlo avisado en 2h
                if (en_horario_activo and
                        _checks_sin_senal.get(chat_id, 0) >= 12 and
                        ahora_ts - _ultima_alerta_rango.get(chat_id, 0) > 7200):
                    _checks_sin_senal[chat_id]   = 0
                    _ultima_alerta_rango[chat_id] = ahora_ts
                    lineas_r = ["━━━━━━━━━━━━━━━━"]
                    bloqueados = []   # conf >= umbral pero filtrado por OB/RR
                    sin_senal  = []   # conf < umbral
                    _fuentes_rango = set()
                    for tkr in activos:
                        try:
                            smc_r, _ = _analizar_activo(tkr, tf)
                            if not smc_r or "error" in smc_r:
                                continue
                            dir_r   = smc_r.get("estructura", {}).get("direccion", "neutral")
                            conf_r  = smc_r.get("confluencia", {}).get("confianza", 0)
                            tipo_r  = smc_r.get("estructura", {}).get("tipo", "Sin señal")
                            valid_r = smc_r.get("señal_valida", False)
                            _ds_r = smc_r.get("_data_source", "")
                            if _ds_r: _fuentes_rango.add(_ds_r)
                            # Calcular RR
                            p_r  = smc_r.get("precio", 0)
                            sl_r = smc_r.get("sl_sugerido", 0)
                            tp_r = smc_r.get("tp_sugerido", 0)
                            rr_r = 0.0
                            if p_r > 0 and sl_r > 0 and tp_r > 0:
                                d_sl = abs(p_r - sl_r)
                                rr_r = abs(tp_r - p_r) / d_sl if d_sl > 0 else 0
                            lineas_r.append(f"{_emoji_dir(dir_r)} *{tkr}*: {tipo_r} ({conf_r:.0f}%)")
                            if conf_r >= umbral:
                                motivo = []
                                if not valid_r:     motivo.append("sin OB activo")
                                if rr_r < 1.5:      motivo.append(f"RR {rr_r:.1f}:1 < 1.5")
                                bloqueados.append((tkr, conf_r, motivo))
                            else:
                                sin_senal.append(tkr)
                        except Exception:
                            pass

                    if bloqueados:
                        titulo = "⚠️ *SETUP DETECTADO — Condiciones insuficientes*"
                        lineas_r.insert(0, titulo)
                        lineas_r.append("")
                        for tkr_b, conf_b, motivos in bloqueados:
                            razon = ", ".join(motivos) if motivos else "filtro secundario"
                            lineas_r.append(f"⚠️ _{tkr_b} {conf_b:.0f}% bloqueado: {razon}_")
                        lineas_r.append(f"\n💡 _Confianza alcanzada pero sin condiciones operables. Revisa el chart._")
                    else:
                        lineas_r.insert(0, "⚪ *MERCADO EN RANGO — Sin setups activos*")
                        lineas_r.append(f"\n💡 _Ningún activo supera el umbral {umbral:.0f}% — mercado lateral._")

                    try:
                        _ctx_rango = contexto_noticias_activos(activos, max_items=2)
                        if _ctx_rango:
                            lineas_r += ["", _ctx_rango]
                    except Exception:
                        pass
                    lineas_r.append(f"_El bot alertará cuando aparezca una entrada válida._")
                    if _fuentes_rango:
                        lineas_r.append(f"📡 _Fuente: {' | '.join(_fuentes_rango)}_")
                    lineas_r.append(f"🕐 _{_hora_mx()} CDMX_")
                    await _send(ctx.bot, chat_id, "\n".join(lineas_r))
            else:
                _checks_sin_senal[chat_id] = 0  # reset si apareció señal

    except Exception as e:
        logger.error(f"job_monitoreo_senales: {e}")


async def job_monitoreo_mtf(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not _en_horario_alertas(): return
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
                        _, _st_form = obtener_datos(ticker, tf_alto)
                        _ds_form = "⚠️ yfinance — 15min delay" if "yfinance" in (_st_form or "") else "🟢 Twelve Data — Tiempo real"
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
                            f"📡 _Fuente: {_ds_form}_\n"
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
                    df_bajo_ctx, _st_bajo = obtener_datos(ticker, tf_bajo)
                    ctx_bajo = _calcular_contexto(df_bajo_ctx) if df_bajo_ctx is not None else {}
                    _ds_mtf = "⚠️ yfinance — 15min delay" if "yfinance" in (_st_bajo or "") else "🟢 Twelve Data — Tiempo real"
                    await _send(ctx.bot, chat_id, "🔭 *MTF ALINEADO — SEÑAL CONFIRMADA*\n" + _formato_mtf(mtf, ticker, contexto=ctx_bajo, data_source=_ds_mtf))
                    _senal_mtf = {"ticker": ticker, "tf": tf_bajo, "direccion": dir_mtf, "entrada": entrada_m, "sl": sl_m, "tp": tp_m, "confianza": confianza_mtf}
                    _ultimas_senales[(chat_id, ticker)] = _senal_mtf
                    _ultimas_senales[chat_id] = _senal_mtf
                except Exception as e:
                    logger.error(f"job_mtf {ticker}: {e}")
    except Exception as e:
        logger.error(f"job_monitoreo_mtf: {e}")


def _en_sesion_premium() -> bool:
    """Londres open (07-10 UTC) o NY open (12:30-16 UTC = 6:30-10 AM CDMX)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    h, m = now.hour, now.minute
    london = 7 <= h < 10
    ny     = (h == 12 and m >= 30) or (13 <= h < 16)
    return london or ny


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
        if not _en_horario_alertas(): return
        if not _en_sesion_premium(): return   # Solo en apertura Londres/NY

        # Detecta si hay evento próximo — NO bloquea, agrega advertencia al mensaje
        _noticia_proxima = ""
        try:
            hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=20)
            if hay_ev and ev_info:
                mins = ev_info.get("minutos_restantes", "~")
                nombre = ev_info.get("nombre", "Evento alto impacto")
                _noticia_proxima = f"⚠️ _Noticia en ~{mins} min: {nombre} — ajusta SL o espera post-noticia_"
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
                    _ds_rev = smc_bajo.get("_data_source", "")
                    msg = "🎯 *REVERSIÓN EN ZONA HTF*\n" + _formato_reversal(
                        smc_alto, smc_bajo, ticker, tf_alto, tf_bajo, nivel_redondo, data_source=_ds_rev
                    )
                    if _noticia_proxima:
                        msg += f"\n{_noticia_proxima}"
                    await _send(ctx.bot, chat_id, msg)
                    marcar_señal_enviada(sig_id)

                except Exception as e:
                    logger.error(f"job_reversal {ticker}: {e}")

    except Exception as e:
        logger.error(f"job_monitoreo_reversal: {e}")


async def job_monitoreo_scalp(ctx: ContextTypes.DEFAULT_TYPE):
    """
    Detecta señales rápidas usando el par 15m/5m.
    SCALP normal     : 15m + 5m alineados (confianza MTF ≥ 60%)
    SCALP DISCRECIONAL: solo 5m con dirección, 15m neutral (conf 5m ≥ 60%)
    Corre cada 90 s. Filtro noticias relajado a 10 min. Dedup 30 min por señal.
    """
    try:
        if not _en_horario_alertas():
            return
        try:
            hay_ev, _ = hay_evento_alto_impacto_pronto(minutos=10)
            if hay_ev:
                return
        except Exception:
            pass

        configs          = obtener_todas_configs_bot()
        activos_default  = ["EURUSD=X", "GBPUSD=X", "GC=F"]
        ahora_ts         = datetime.now(TZ_MX).timestamp()

        for cfg in configs:
            chat_id = cfg.get("telegram_chat_id", "")
            if not chat_id or not cfg.get("alertas_activas"):
                continue
            try:
                activos = json.loads(cfg.get("activos_monitor", "[]")) or activos_default
            except Exception:
                activos = activos_default

            for ticker in activos:
                try:
                    mtf       = analisis_mtf(ticker, "15m", "5m")
                    alineado  = mtf.get("alineacion", False)
                    conf_mtf  = mtf.get("confianza_mtf", 0)
                    smc_5m    = mtf.get("smc_bajo") or {}
                    entrada_d = mtf.get("entrada_discrecional")

                    # ── Determinar modo de señal ──────────────────────────
                    if alineado and conf_mtf >= 60:
                        modo      = "normal"
                        dir_      = smc_5m.get("estructura", {}).get("direccion", "neutral")
                        entrada   = mtf.get("entrada_sugerida")
                        sl        = mtf.get("sl_sugerido")
                        tp        = mtf.get("tp_sugerido")
                        tipo_5m   = smc_5m.get("estructura", {}).get("tipo", "")
                        conf_show = conf_mtf
                    elif not alineado and entrada_d:
                        modo      = "discrecional"
                        dir_      = mtf.get("dir_discrecional", "neutral")
                        conf_disc = mtf.get("conf_discrecional", 0)
                        if conf_disc < 60:
                            continue
                        entrada   = entrada_d
                        sl        = mtf.get("sl_discrecional")
                        tp        = mtf.get("tp_discrecional")
                        tipo_5m   = smc_5m.get("estructura", {}).get("tipo", "")
                        conf_show = conf_disc
                    else:
                        continue

                    if dir_ == "neutral" or not entrada or not sl or not tp:
                        continue

                    # ── Dedup 30 min ──────────────────────────────────────
                    clave_dd = (chat_id, ticker, dir_)
                    if ahora_ts - _dedup_scalp.get(clave_dd, 0) < 1800:
                        continue

                    # ── Construir mensaje ─────────────────────────────────
                    fp       = lambda p: _fmt_precio(p, ticker)
                    accion   = "🟢 *COMPRAR*" if dir_ == "LONG" else "🔴 *VENDER*"
                    if "BOS" in tipo_5m:
                        orden = "Stop Limit"
                    elif "CHoCH" in tipo_5m:
                        orden = "Límite"
                    else:
                        orden = "Mercado"

                    dist_sl = abs(entrada - sl)
                    dist_tp = abs(tp - entrada)
                    rr      = round(dist_tp / dist_sl, 1) if dist_sl > 0 else 0

                    _, _st_5m = obtener_datos(ticker, "5m")
                    _ds = ("⚠️ yfinance — 15min delay"
                           if "yfinance" in (_st_5m or "")
                           else "🟢 Twelve Data — Tiempo real")

                    if modo == "normal":
                        header  = f"⚡ *SCALP — {ticker}* (15m/5m)"
                        subtipo = f"15m + 5m alineados · {conf_show:.0f}%"
                        warn    = ""
                    else:
                        header  = f"⚡ *SCALP DISCRECIONAL — {ticker}* (5m solo)"
                        subtipo = f"Solo 5m · {conf_show:.0f}% · sin confirmación 15m"
                        warn    = "⚠️ _Sin confirmación 15m — opera con tamaño muy reducido_"

                    lineas = [
                        header,
                        "━━━━━━━━━━━━━━━━",
                        f"👉 *Acción:* {accion}  |  📋 *Orden:* {orden}",
                        f"💰 *Entrada:* `{fp(entrada)}`",
                        f"✅ *TP:* `{fp(tp)}`",
                        f"🛑 *SL:* `{fp(sl)}`",
                        f"⚖️ *RR:* {rr}:1" if rr > 0 else "",
                        f"📊 _{subtipo}_",
                        f"⏱ _Objetivo: {'15-30' if modo == 'normal' else '10-20'} min_",
                    ]
                    if warn:
                        lineas.append(warn)
                    lineas += [
                        f"📡 _{_ds}_",
                        f"🕐 {datetime.now(TZ_MX).strftime('%H:%M')} CDMX",
                    ]

                    msg = "\n".join(l for l in lineas if l)
                    await _send(ctx.bot, chat_id, msg)

                    _dedup_scalp[clave_dd] = ahora_ts
                    _ultimas_senales[chat_id] = {
                        "ticker":    ticker,
                        "direccion": dir_,
                        "entrada":   entrada,
                        "sl":        sl,
                        "tp":        tp,
                        "tf":        "5m",
                        "setup":     f"Scalp {'Discrecional' if modo == 'discrecional' else 'SMC'}",
                    }

                except Exception as e:
                    logger.error(f"job_scalp {ticker}: {e}")

    except Exception as e:
        logger.error(f"job_monitoreo_scalp: {e}")


async def job_cierre_nocturno(ctx: ContextTypes.DEFAULT_TYPE):
    """
    11:59 PM CDMX: cierra en el REGISTRO del bot todos los trades activos.
    No toca posiciones reales en el broker — solo limpia el registro interno
    para que no bloqueen señales al día siguiente.
    Envía aviso al usuario para que cierre manualmente en TradingView/IC Markets.
    """
    try:
        trades = obtener_todos_trades_activos()
        if not trades:
            return

        por_chat: dict = {}
        for t in trades:
            cid = t.get("chat_id", "")
            if cid:
                por_chat.setdefault(cid, []).append(t)

        for chat_id, trades_chat in por_chat.items():
            lineas = [
                "🔔 *CIERRE NOCTURNO — REGISTRO DEL BOT*",
                "━━━━━━━━━━━━━━━━",
                f"Se encontraron *{len(trades_chat)} posición(es) abiertas* en el registro.",
                "",
                "*Trades cerrados en el registro interno:*",
            ]
            for t in trades_chat:
                ticker  = t.get("ticker", "")
                dir_    = t.get("direccion", "")
                entrada = t.get("entrada", 0)
                emoji   = "🟢" if dir_ == "LONG" else "🔴"
                fp      = lambda p: _fmt_precio(p, ticker)
                lineas.append(f"  {emoji} {ticker} {dir_} @ `{fp(entrada)}`")
                cerrar_trade_confirmado(t["id"], "auto-cierre nocturno")

            lineas += [
                "",
                "⚠️ *ACCIÓN REQUERIDA:*",
                "_El bot limpió su registro, pero las posiciones reales en_",
                "_TradingView / IC Markets siguen abiertas si no las cerraste._",
                "_Verifica y cierra manualmente las que ya no quieras mantener._",
                "",
                f"🕐 {datetime.now(TZ_MX).strftime('%H:%M')} CDMX · ORAM Quant Systems",
            ]
            msg = "\n".join(l for l in lineas if l is not None)
            await _send(ctx.bot, chat_id, msg)

    except Exception as e:
        logger.error(f"job_cierre_nocturno: {e}")


async def job_apertura_semana(ctx: ContextTypes.DEFAULT_TYPE):
    """Aviso de reapertura del mercado cada domingo a las 22:05 UTC (16:05 CDMX)."""
    try:
        from datetime import timezone as _tz
        now_utc = datetime.now(_tz.utc)
        if not (now_utc.weekday() == 6 and now_utc.hour == 22):
            return
        configs = obtener_todas_configs_bot()
        msg = (
            "🔓 *¡EL MERCADO ABRE!*\n"
            "━━━━━━━━━━━━━━━━\n"
            "Los mercados Forex y Oro están abiertos.\n\n"
            "⏰ _Domingo 16:00 CDMX — Inicio de semana_\n\n"
            "💡 *Próximas sesiones:*\n"
            "  🟡 London Open: lunes 02:00 CDMX\n"
            "  🔥 Overlap L+NY: lunes 07:00-10:00 CDMX\n\n"
            "📡 El bot comenzará a enviar señales automáticamente.\n"
            "🤖 _ORAM Quant Systems_"
        )
        for cfg in configs:
            if cfg.get("alertas_activas") and cfg.get("telegram_chat_id"):
                await _send(ctx.bot, cfg["telegram_chat_id"], msg)
    except Exception as e:
        logger.error(f"job_apertura_semana: {e}")


async def job_verificar_alertas_precio(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if not _en_horario_trading():
            return
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
                f"{emoji} *{ticker}* {dir_str} `{_fmt_precio(alerta['precio'], ticker)}`\n"
                f"💰 Precio actual: `{_fmt_precio(precio_actual, ticker)}`\n"
                f"📏 Diferencia: {_fmt_precio(diff, ticker)}\n"
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
                    f"💰 Entrada: `{_fmt_precio(entrada, ticker)}`\n"
                    f"✅ TP: `{_fmt_precio(tp, ticker)}` alcanzado\n"
                    f"📈 +{pips} pips\n"
                    f"🕐 {_hora_mx()} CDMX\n\n"
                    f"✅ Señales de *{ticker}* reactivadas."
                )
            else:
                msg = (
                    f"🛑 *STOP LOSS ALCANZADO*\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{_emoji_dir(dir_)} *{ticker}* {dir_}\n"
                    f"💰 Entrada: `{_fmt_precio(entrada, ticker)}`\n"
                    f"🛑 SL: `{_fmt_precio(sl, ticker)}` alcanzado\n"
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


# ─── REGISTRAR TRADE DESDE TELEGRAM ─────────────────────────────────────────

async def cmd_registrar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Registra un trade en el diario.
    Sin args → usa la última señal del chat.
    Con args → /registrar EURUSD LONG 1.0850 1.0800 1.0950 [15m]
    """
    chat_id = str(update.effective_chat.id)
    user, cfg = _get_user_by_chat(chat_id)
    if not user:
        await _reply(update, "⚙️ Vincula tu Chat ID en la app → Configuración Bot.")
        return

    args = ctx.args
    if not args:
        senal = _ultimas_senales.get(chat_id)
        if not senal:
            await _reply(update,
                "❌ Sin señal reciente en este chat.\n\n"
                "Uso manual:\n`/registrar EURUSD LONG 1.0850 1.0800 1.0950 15m`"
            )
            return
        ticker  = senal["ticker"]
        dir_    = senal["direccion"]
        entrada = senal["entrada"]
        sl      = senal["sl"]
        tp      = senal["tp"]
        tf_     = senal.get("tf", "15m")
        tipo    = senal.get("setup", "SMC Signal")
    else:
        if len(args) < 5:
            await _reply(update, "❌ Faltan campos.\nUso: `/registrar EURUSD LONG 1.0850 1.0800 1.0950 [15m]`")
            return
        try:
            ticker  = _normalizar_ticker(args[0])
            dir_    = args[1].upper()
            if dir_ not in ("LONG", "SHORT"):
                raise ValueError("Dirección debe ser LONG o SHORT")
            entrada = float(args[2])
            sl      = float(args[3])
            tp      = float(args[4])
            tf_     = args[5] if len(args) > 5 else "15m"
            tipo    = "Manual"
        except (ValueError, IndexError) as e:
            await _reply(update, f"❌ Formato inválido: {e}\nUso: `/registrar EURUSD LONG 1.0850 1.0800 1.0950 15m`")
            return

    capital    = float(cfg.get("capital_cuenta") or 0) or 10000.0
    riesgo_pct = float(cfg.get("riesgo_pct") or 2.0)
    riesgo_usd = round(capital * riesgo_pct / 100, 2)

    trade_id = insertar_trade(user["id"], {
        "fecha":        datetime.now(TZ_MX).strftime("%Y-%m-%d"),
        "activo":       ticker,
        "timeframe":    tf_,
        "direccion":    dir_,
        "entrada":      entrada,
        "sl":           sl,
        "tp":           tp,
        "riesgo_usd":   riesgo_usd,
        "resultado_usd": 0.0,
        "setup":        tipo,
        "emocion":      "Neutral",
        "notas":        "Registrado desde Telegram",
        "estado":       "Abierto",
    })

    fp = lambda p: _fmt_precio(p, ticker)
    await _reply(update,
        f"✅ *Trade registrado en el diario*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{_emoji_dir(dir_)} *{ticker}* {dir_} · {tf_}\n"
        f"💰 Entrada: `{fp(entrada)}`\n"
        f"✅ TP: `{fp(tp)}`\n"
        f"🛑 SL: `{fp(sl)}`\n"
        f"💼 Riesgo: ${riesgo_usd:.2f}\n\n"
        f"📝 _Completa setup, emoción y notas en la app_\n"
        f"🆔 Trade *#{trade_id}*"
    )


async def callback_registrar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Callback del botón 'Registrar en diario' en señales ALTA."""
    query   = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat_id)

    try:
        sig_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.answer("❌ Datos inválidos", show_alert=True)
        return

    pending = _pending_trades.get(sig_id)
    if not pending:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.answer("⏱ La señal ya expiró. Usa /registrar para registrar manualmente.", show_alert=True)
        return

    user, cfg = _get_user_by_chat(chat_id)
    if not user:
        await query.answer("⚙️ Vincula tu Chat ID en la app primero.", show_alert=True)
        return

    capital    = float(cfg.get("capital_cuenta") or 0) or 10000.0
    riesgo_pct = float(cfg.get("riesgo_pct") or 2.0)
    riesgo_usd = round(capital * riesgo_pct / 100, 2)
    ticker  = pending["ticker"]
    dir_    = pending["direccion"]
    entrada = pending["entrada"]
    sl      = pending["sl"]
    tp      = pending["tp"]
    tf_     = pending.get("tf", "15m")
    conf    = pending.get("confianza", 0)
    tipo    = pending.get("setup", "SMC Signal")

    trade_id = insertar_trade(user["id"], {
        "fecha":        pending.get("fecha", datetime.now(TZ_MX).strftime("%Y-%m-%d")),
        "activo":       ticker,
        "timeframe":    tf_,
        "direccion":    dir_,
        "entrada":      entrada,
        "sl":           sl,
        "tp":           tp,
        "riesgo_usd":   riesgo_usd,
        "resultado_usd": 0.0,
        "setup":        tipo,
        "emocion":      "Neutral",
        "notas":        f"Registrado desde Telegram | Confianza: {conf:.0f}%",
        "estado":       "Abierto",
    })
    _pending_trades.pop(sig_id, None)

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    fp = lambda p: _fmt_precio(p, ticker)
    await _send(ctx.bot, chat_id,
        f"✅ *Trade registrado en el diario*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{_emoji_dir(dir_)} *{ticker}* {dir_} · {tf_}\n"
        f"💰 Entrada: `{fp(entrada)}`\n"
        f"✅ TP: `{fp(tp)}`\n"
        f"🛑 SL: `{fp(sl)}`\n"
        f"💼 Riesgo: ${riesgo_usd:.2f}\n\n"
        f"📝 _Completa setup, emoción y notas en la app_\n"
        f"🆔 Trade *#{trade_id}*"
    )


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

    # ── Webhook TradingView ───────────────────────────────────────────────────
    try:
        from utils.webhook_server import iniciar_servidor, set_chat_ids
        _wh_port = int(os.getenv("PORT", "8080"))
        iniciar_servidor(_wh_port)
        try:
            _wh_configs = obtener_todas_configs_bot()
            _wh_chats   = [
                c["telegram_chat_id"] for c in _wh_configs
                if c.get("telegram_chat_id") and c.get("alertas_activas")
            ]
            set_chat_ids(_wh_chats)
            print(f"📺 Webhook TV activo en :{_wh_port} — {len(_wh_chats)} chat(s)")
        except Exception as _e:
            logger.warning(f"Webhook chat_ids: {_e}")
    except Exception as _e:
        logger.warning(f"Webhook no iniciado: {_e}")

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
        ("setcapital",  cmd_setcapital),
        ("noticias",    cmd_noticias),
        ("proximos",    cmd_proximos),
        ("sesiones",    cmd_sesiones),
        ("alertas",     cmd_alertas),
        ("resumen",     cmd_resumen),
        ("ayuda",       cmd_ayuda),
        ("tomar",       cmd_tomar),
        ("cerrar",      cmd_cerrar),
        ("activos",     cmd_activos),
        ("registrar",   cmd_registrar),
    ]:
        app.add_handler(CommandHandler(cmd, handler))
    app.add_handler(CallbackQueryHandler(callback_registrar, pattern=r"^reg_\d+$"))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_desconocido))

    jq = app.job_queue
    if jq is not None:
        jq.run_daily(job_resumen_diario,   time=dtime(hour=13, minute=0))   # 7AM CDMX (lun-vie)
        jq.run_daily(job_reporte_cierre,   time=dtime(hour=22, minute=0))   # 4PM CDMX (lun-vie)
        jq.run_daily(job_apertura_semana,  time=dtime(hour=22, minute=5))   # Dom 16:05 CDMX
        jq.run_daily(job_cierre_nocturno,  time=dtime(hour=5,  minute=59))  # 11:59 PM CDMX
        jq.run_repeating(job_monitoreo_senales,        interval=300, first=60)
        jq.run_repeating(job_monitoreo_mtf,            interval=900, first=120)
        jq.run_repeating(job_monitoreo_reversal,       interval=60,  first=90)
        jq.run_repeating(job_monitoreo_scalp,          interval=90,  first=45)
        jq.run_repeating(job_verificar_alertas_precio, interval=300, first=30)
        jq.run_repeating(job_alerta_noticias,          interval=300, first=60)
        print("✅ Jobs activos: Apertura 7AM · Cierre 4PM · Dom apertura 4:05PM · Señales c/5m · MTF c/15m · Reversal c/1m · Scalp c/90s · Alertas precio c/5m · Noticias c/5m")
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
