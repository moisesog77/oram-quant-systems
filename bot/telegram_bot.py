"""
bot/telegram_bot.py — ORAM Quant Systems Bot v2
Comandos completos + alertas automáticas inteligentes de compra/venta.
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
from utils.economic_calendar import (obtener_eventos_hoy, obtener_proximos_eventos,
                                      hay_evento_alto_impacto_pronto, impacto_emoji)
from database.db import (
    obtener_todas_configs_bot, obtener_todas_alertas_activas,
    disparar_alerta, registrar_señal, marcar_señal_enviada,
    obtener_señales_recientes, inicializar_db,
    obtener_todos_usuarios, obtener_trades,
)

TZ_MX  = ZoneInfo("America/Mexico_City")
TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
MD     = "Markdown"

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Umbrales de señal ────────────────────────────────────────────────────────
UMBRAL_ALERTA_ALTA    = 75   # Señal de alta prioridad — notificar inmediato
UMBRAL_ALERTA_MEDIA   = 60   # Señal media — incluir en escaneo periódico
UMBRAL_MTF_ALINEADO   = 65   # MTF: confianza mínima para alerta


# ─── Helpers de comunicación ─────────────────────────────────────────────────

async def _reply(update, text: str):
    try:
        if len(text) > 4000:
            text = text[:3990] + "\n_...truncado_"
        await update.message.reply_text(text, parse_mode=MD)
    except Exception as e:
        logger.error(f"Markdown error: {e}")
        try:
            plain = text.replace("*","").replace("_","").replace("`","")
            await update.message.reply_text(plain)
        except Exception as e2:
            logger.error(f"Plain error: {e2}")

async def _send(bot, chat_id: str, text: str):
    try:
        if len(text) > 4000:
            text = text[:3990] + "\n_...truncado_"
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=MD)
    except Exception as e:
        logger.error(f"send Markdown error: {e}")
        try:
            plain = text.replace("*","").replace("_","").replace("`","")
            await bot.send_message(chat_id=chat_id, text=plain)
        except Exception as e2:
            logger.error(f"send plain error: {e2}")


# ─── Helpers de análisis ──────────────────────────────────────────────────────

def _analizar_activo(ticker: str, tf: str = "15m"):
    try:
        df, status = obtener_datos(ticker, tf)
        if df is None:
            return None, status
        return analisis_completo(df, ticker), status
    except Exception as e:
        logger.error(f"Error analizando {ticker}: {e}")
        return None, str(e)

def _conf_bar(pct: float) -> str:
    filled = int(pct / 10)
    bar    = "█" * filled + "░" * (10 - filled)
    return f"{bar} {pct:.0f}%"

def _emoji_dir(dir_: str) -> str:
    return "🟢" if dir_ == "LONG" else "🔴" if dir_ == "SHORT" else "⚪"

def _prioridad(conf: float) -> str:
    if conf >= 80: return "🔥 ALTA"
    if conf >= 65: return "⚡ MEDIA"
    return "💡 BAJA"

def _hora_mx() -> str:
    return datetime.now(TZ_MX).strftime("%H:%M")

def _en_horario_trading() -> bool:
    """Filtra horas sin liquidez (cierre de mercado forex)."""
    h = datetime.now(TZ_MX).hour
    # Forex cierra viernes 4pm NY (5pm CDMX) hasta domingo 4pm NY (5pm CDMX)
    wd = datetime.now(TZ_MX).weekday()  # 0=lunes, 5=sábado, 6=domingo
    if wd == 5: return False            # sábado completo
    if wd == 6 and h < 17: return False # domingo hasta 5pm
    if wd == 4 and h >= 17: return False # viernes desde 5pm
    return True


def _formato_senal_completo(smc: dict, ticker: str, tf: str, capital: float = 10000.0, riesgo_pct: float = 1.0) -> str:
    """Formato premium de señal con SL/TP/RR y gestión de riesgo."""
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

    emoji = _emoji_dir(dir_)
    prio  = _prioridad(pct)

    # Cálculo de riesgo
    riesgo_info = {}
    if sl and tp and precio:
        riesgo_info = calcular_riesgo(precio, sl, tp, capital, riesgo_pct)

    rr  = riesgo_info.get("rr", 0)
    lote = riesgo_info.get("lot_size", 0)
    ganancia = riesgo_info.get("ganancia_pot", 0)

    lineas = [
        f"{'🚨' if pct >= 75 else '📡'} *SEÑAL SMC — {prio}*",
        f"{emoji} *{ticker}* · {tf}",
        "━━━━━━━━━━━━━━━━",
        f"📌 *Señal:* {tipo}",
        f"💰 *Precio entrada:* `{precio:.5f}`",
        f"📊 *Dirección:* {emoji} {dir_}",
        f"🎯 *Confianza:* {_conf_bar(pct)}",
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
            f"💼 *Gestión de riesgo ({riesgo_pct}%):*",
            f"   Lote sugerido: {lote:.3f}",
            f"   Riesgo: ${capital * riesgo_pct / 100:.0f} USD",
            f"   Ganancia potencial: ${ganancia:.0f} USD",
        ]

    lineas += [
        "",
        f"📉 *RSI:* {rsi:.1f}  |  📏 *ATR:* {atr:.5f}",
        f"📈 *EMA50:* {ema50:.5f}" if ema50 else "",
    ]

    if factores:
        lineas.append("")
        lineas.append("⚡ *Confluencias confirmadas:*")
        for f in factores:
            lineas.append(f"  ✔ {f}")

    lineas += [
        "",
        f"🕐 *{_hora_mx()} CDMX*",
        "⚠️ _Señal orientativa. Usa SL siempre._",
    ]

    return "\n".join(l for l in lineas if l is not None)


def _formato_mtf(mtf: dict, ticker: str) -> str:
    """Formato completo de análisis Multi-Timeframe."""
    smc_alto  = mtf.get("smc_alto") or {}
    smc_bajo  = mtf.get("smc_bajo") or {}
    tf_alto   = mtf.get("tf_alto", "?")
    tf_bajo   = mtf.get("tf_bajo", "?")
    alineado  = mtf.get("alineacion", False)
    señal     = mtf.get("señal_mtf", "")
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

    estado = "✅ *ALINEADO*" if alineado else "⚠️ *No alineado*"

    lineas = [
        f"🔭 *ANÁLISIS MULTI-TIMEFRAME*",
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
            f"✅ *TP:* `{tp:.5f}`"  if tp else "",
        ]

    lineas += [
        "",
        f"📝 _{desc}_",
        "",
        f"🕐 {_hora_mx()} CDMX",
    ]
    return "\n".join(l for l in lineas if l is not None)


# ─── Comandos del bot ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    await _reply(update,
        "👋 *Bienvenido a ORAM Quant Systems* 🤖\n\n"
        "Soy tu asistente de trading institucional basado en SMC.\n\n"
        "📋 *Comandos disponibles:*\n\n"
        "🔍 *Análisis:*\n"
        "/mercado — Resumen rápido del mercado\n"
        "/senales — Señales SMC activas ahora\n"
        "/mtf — Análisis Multi-Timeframe\n"
        "/analizar EURUSD — Análisis completo de un par\n\n"
        "⚙️ *Configuración:*\n"
        "/capital — Ver/configurar tu capital\n"
        "/riesgo — Calcular lote y riesgo\n\n"
        "📰 *Información:*\n"
        "/noticias — Eventos económicos hoy\n"
        "/proximos — Próximos eventos (2h)\n"
        "/sesiones — Horarios de sesiones\n\n"
        "📊 *Historial:*\n"
        "/alertas — Señales de las últimas 24h\n"
        "/resumen — Reporte diario completo\n\n"
        "❓ /ayuda — Lista completa de comandos\n\n"
        f"🔑 *Tu Chat ID:* `{chat_id}`\n"
        "_(Cópialo en la app → Bot Telegram → Chat ID)_"
    )


async def cmd_mercado(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Analizando mercado... espera un momento.")

    activos = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X",
               "USDCAD=X", "BTC-USD", "GC=F", "CL=F"]

    lineas = [
        "📊 *RESUMEN DE MERCADO*",
        f"_{datetime.now(TZ_MX).strftime('%d/%m/%Y %H:%M')} CDMX_",
        "━━━━━━━━━━━━━━━━",
        "",
        "🔵 *Forex:*",
    ]

    categorias = {
        "Forex":      ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","AUDUSD=X","USDCAD=X"],
        "Cripto":     ["BTC-USD"],
        "Materias primas": ["GC=F","CL=F"],
    }

    for cat, tickers in categorias.items():
        if cat != "Forex":
            lineas.append(f"\n{'🟡' if cat=='Cripto' else '🟠'} *{cat}:*")
        for ticker in tickers:
            try:
                smc, _ = _analizar_activo(ticker, "1h")
                if smc and "error" not in smc:
                    dir_   = smc.get("estructura", {}).get("direccion", "neutral")
                    conf   = smc.get("confluencia", {}).get("confianza", 0)
                    precio = smc.get("precio", 0)
                    tipo   = smc.get("estructura", {}).get("tipo", "?")
                    rsi    = smc.get("rsi", 0) or 0
                    emoji  = _emoji_dir(dir_)
                    prio   = "🔥" if conf >= 75 else ""
                    lineas.append(
                        f"{emoji}{prio} *{ticker}* `{precio:.4f}` — {tipo} ({conf:.0f}%) RSI:{rsi:.0f}"
                    )
                else:
                    lineas.append(f"⚫ {ticker} — Sin datos")
            except Exception as e:
                lineas.append(f"⚫ {ticker} — Error")
                logger.error(f"cmd_mercado {ticker}: {e}")

    try:
        proximos = obtener_proximos_eventos(2)
        if proximos:
            lineas += ["", "📰 *Próximos eventos (2h):*"]
            for ev in proximos:
                lineas.append(f"{impacto_emoji(ev['impacto'])} {ev['titulo']} — {ev['hora_mx']} CDMX")
    except Exception as e:
        logger.error(f"cmd_mercado eventos: {e}")

    lineas += ["", f"🕐 _Actualizado: {_hora_mx()} CDMX_"]
    await _reply(update, "\n".join(lineas))


async def cmd_senales(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ Buscando señales SMC de alta confianza...")

    # Bloquear si hay evento de alto impacto próximo
    try:
        hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=30)
        if hay_ev and ev_info:
            await _reply(update,
                f"⚠️ *PRECAUCIÓN — Evento de alto impacto en {ev_info['minutos_restantes']} min*\n"
                f"📰 {ev_info['titulo']} ({ev_info['moneda']}) — {ev_info['hora_mx']} CDMX\n\n"
                "❌ No es buen momento para entrar al mercado.\n"
                "Espera al menos 30 min después del evento."
            )
            return
    except Exception:
        pass

    # Escanear todos los activos por defecto
    activos = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X",
               "USDCAD=X", "USDJPY=X", "XAUUSD=X"]
    altas   = []
    medias  = []

    for ticker in activos:
        try:
            smc, _ = _analizar_activo(ticker, "15m")
            if not smc or "error" in smc:
                continue
            conf = smc.get("confluencia", {}).get("confianza", 0)
            dir_ = smc.get("estructura",  {}).get("direccion", "neutral")
            if dir_ == "neutral":
                continue
            if conf >= UMBRAL_ALERTA_ALTA:
                altas.append((ticker, smc, conf))
            elif conf >= UMBRAL_ALERTA_MEDIA:
                medias.append((ticker, smc, conf))
        except Exception as e:
            logger.error(f"cmd_senales {ticker}: {e}")

    if not altas and not medias:
        await _reply(update,
            "⚪ *Sin señales de alta confianza en este momento*\n\n"
            f"Umbral alto: {UMBRAL_ALERTA_ALTA}% · Umbral medio: {UMBRAL_ALERTA_MEDIA}%\n\n"
            "💡 *Mejores horarios de trading:*\n"
            "🟡 London Open: 02:00-04:00 CDMX\n"
            "🟠 NY Open: 07:30-09:30 CDMX\n"
            "🔵 Overlap: 07:00-10:00 CDMX\n\n"
            "💡 Prueba /mtf para análisis multi-timeframe."
        )
        return

    # Enviar señales de alta prioridad primero
    if altas:
        await update.message.reply_text(f"🔥 *{len(altas)} señal(es) de ALTA PRIORIDAD:*", parse_mode=MD)
        for ticker, smc, conf in sorted(altas, key=lambda x: -x[2]):
            await _reply(update, _formato_senal_completo(smc, ticker, "15m"))

    if medias:
        await update.message.reply_text(f"⚡ *{len(medias)} señal(es) de prioridad media:*", parse_mode=MD)
        for ticker, smc, conf in sorted(medias, key=lambda x: -x[2]):
            tipo  = smc.get("estructura", {}).get("tipo", "?")
            dir_  = smc.get("estructura", {}).get("direccion", "neutral")
            prec  = smc.get("precio", 0)
            emoji = _emoji_dir(dir_)
            await _reply(update,
                f"{emoji} *{ticker}* · `{prec:.5f}` — {tipo} ({conf:.0f}%)"
            )


async def cmd_mtf(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Análisis Multi-Timeframe — misma funcionalidad que la app."""
    args = ctx.args
    ticker = args[0].upper() if args else "EURUSD=X"
    if not ticker.endswith("=X") and ticker not in ["BTC-USD","ETH-USD","GC=F","CL=F"]:
        ticker = ticker + "=X"

    combo = args[1] if len(args) > 1 else "Intraday (1h/15m)"
    tf_alto, tf_bajo = MTF_COMBOS.get(combo, ("1h", "15m"))

    await update.message.reply_text(f"🔭 Analizando {ticker} MTF ({tf_alto}/{tf_bajo})...")

    try:
        mtf = analisis_mtf(ticker, tf_alto, tf_bajo)
        await _reply(update, _formato_mtf(mtf, ticker))
    except Exception as e:
        logger.error(f"cmd_mtf {ticker}: {e}")
        await update.message.reply_text(f"❌ Error analizando {ticker}: {str(e)[:100]}")


async def cmd_analizar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Análisis SMC completo de un activo específico. Uso: /analizar EURUSD 1h"""
    args   = ctx.args
    if not args:
        await _reply(update,
            "💡 *Uso:* `/analizar EURUSD` o `/analizar EURUSD 1h`\n\n"
            "Timeframes disponibles: 1m, 5m, 15m, 30m, 1h, 4h, 1d"
        )
        return

    ticker = args[0].upper()
    if not ticker.endswith("=X") and ticker not in ["BTC-USD","ETH-USD","GC=F","CL=F"]:
        ticker = ticker + "=X"
    tf = args[1] if len(args) > 1 else "15m"

    await update.message.reply_text(f"🔍 Analizando {ticker} en {tf}...")

    try:
        smc, status = _analizar_activo(ticker, tf)
        if not smc or "error" in smc:
            await _reply(update, f"❌ Sin datos para {ticker} en {tf}.\n_{status}_")
            return

        conf = smc.get("confluencia", {}).get("confianza", 0)
        dir_ = smc.get("estructura",  {}).get("direccion", "neutral")

        # Análisis completo con gestión de riesgo
        msg = _formato_senal_completo(smc, ticker, tf)

        # Añadir niveles SMC adicionales
        obs  = smc.get("order_blocks", [])
        fvgs = smc.get("fvgs", [])
        liq  = smc.get("liquidez", {})

        extras = ["\n━━━━━━━━━━━━━━━━", "📐 *Niveles SMC detectados:*"]
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

        await _reply(update, msg + "\n".join(extras))

        # Si la señal es buena, sugerir MTF
        if conf >= 60 and dir_ != "neutral":
            await _reply(update,
                f"💡 _Señal interesante. Usa_ `/mtf {ticker.replace('=X','')}` _para confirmar con Multi-Timeframe._"
            )

    except Exception as e:
        logger.error(f"cmd_analizar {ticker}: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def cmd_riesgo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Calcula lote y gestión de riesgo. Uso: /riesgo EURUSD 1.0850 1.0800 1.0950"""
    args = ctx.args
    if len(args) < 4:
        await _reply(update,
            "💼 *Calculadora de Riesgo*\n\n"
            "*Uso:* `/riesgo TICKER ENTRADA SL TP`\n\n"
            "*Ejemplo:* `/riesgo EURUSD 1.0850 1.0800 1.0950`\n\n"
            "Usa tu capital configurado en la app (Bot Telegram)."
        )
        return

    try:
        ticker  = args[0].upper()
        entrada = float(args[1])
        sl      = float(args[2])
        tp      = float(args[3])
        capital = 10000.0  # default — se podría obtener del DB si el usuario está configurado
        riesgo_pct = 1.0

        res = calcular_riesgo(entrada, sl, tp, capital, riesgo_pct)
        if not res:
            await update.message.reply_text("❌ Error en los datos. Verifica que SL ≠ entrada.")
            return

        dir_ = "LONG" if tp > entrada else "SHORT"
        emoji = _emoji_dir(dir_)

        await _reply(update,
            f"💼 *CALCULADORA DE RIESGO*\n"
            f"{emoji} *{ticker}* — {dir_}\n"
            "━━━━━━━━━━━━━━━━\n"
            f"💰 Entrada: `{entrada:.5f}`\n"
            f"🛑 SL: `{sl:.5f}` ({res['pips_sl']:.1f} pips)\n"
            f"✅ TP: `{tp:.5f}` ({res['pips_tp']:.1f} pips)\n"
            f"⚖️ RR: *{res['rr']:.1f}:1*\n"
            "\n"
            f"💼 *Con capital ${capital:,.0f} y riesgo {riesgo_pct}%:*\n"
            f"   Riesgo USD: ${res['riesgo_usd']:.2f}\n"
            f"   Lote sugerido: *{res['lot_size']:.3f}*\n"
            f"   Ganancia potencial: *${res['ganancia_pot']:.2f}*\n"
            "\n"
            "⚠️ _Ajusta el lote según tu broker y spread._"
        )
    except (ValueError, IndexError):
        await _reply(update, "❌ Formato inválido. Ejemplo: `/riesgo EURUSD 1.0850 1.0800 1.0950`")


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
        lineas.append(
            f"{estado} {impacto_emoji(ev['impacto'])} *{ev['hora_mx']}* — {ev['titulo']} ({ev['moneda']})"
        )

    lineas += ["", "⚠️ _Evita operar ±30 min alrededor de eventos 🔴_"]
    await _reply(update, "\n".join(lineas))


async def cmd_proximos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Próximos eventos en las próximas 2 horas."""
    try:
        eventos = obtener_proximos_eventos(2)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        return

    if not eventos:
        await _reply(update,
            f"✅ *Sin eventos de alto impacto en las próximas 2 horas.*\n"
            f"Mercado despejado para operar — {_hora_mx()} CDMX"
        )
        return

    lineas = ["⚠️ *EVENTOS PRÓXIMOS (2h)*", "━━━━━━━━━━━━━━━━"]
    for ev in eventos:
        lineas.append(
            f"{impacto_emoji(ev['impacto'])} *{ev['hora_mx']}* — {ev['titulo']} ({ev['moneda']})\n"
            f"   Restante: {ev['minutos_restantes']} min"
        )

    lineas.append("\n⚠️ _Evita abrir posiciones. Cierra las abiertas si son de corto plazo._")
    await _reply(update, "\n".join(lineas))


async def cmd_sesiones(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Informa las sesiones de trading con hora CDMX."""
    ahora = datetime.now(TZ_MX)
    h     = ahora.hour

    def estado(inicio, fin):
        activa = inicio <= h < fin
        return "🟢 *ACTIVA AHORA*" if activa else "⚫ Cerrada"

    await _reply(update,
        "🌍 *SESIONES DE TRADING — CDMX*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🌏 *Tokio (Asia):*        00:00-09:00  {estado(0,9)}\n"
        f"🌍 *Londres (Europa):*    02:00-11:00  {estado(2,11)}\n"
        f"🔥 *Overlap L+NY:*        07:00-10:00  {estado(7,10)}\n"
        f"🌎 *Nueva York:*          07:30-16:00  {estado(7,16)}\n"
        f"📡 *Sydney:*              20:00-05:00  {'🟢 ACTIVA' if h >= 20 or h < 5 else '⚫ Cerrada'}\n"
        "\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🕐 _Ahora: {ahora.strftime('%H:%M')} CDMX ({ahora.strftime('%A')}), "
        f"hora {'de trading' if _en_horario_trading() else 'sin liquidez'}_\n\n"
        "💡 *Mejores momentos:*\n"
        "  🔥 Overlap (07:00-10:00): mayor volatilidad\n"
        "  🟡 London Open (02:00-04:00): señales SMC fuertes\n"
        "  🟠 NY Open (07:30-09:30): breakouts frecuentes"
    )


async def cmd_alertas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        senales = obtener_señales_recientes(horas=24)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
        return

    if not senales:
        await update.message.reply_text("📭 Sin señales registradas en las últimas 24h.")
        return

    lineas = ["⚡ *SEÑALES — ÚLTIMAS 24H*", "━━━━━━━━━━━━━━━━"]
    for s in senales[:12]:
        emoji = _emoji_dir(s.get("direccion", "neutral"))
        conf  = s.get("confianza", 0)
        hora  = str(s.get("created_at", ""))[-8:-3] if s.get("created_at") else "?"
        prio  = "🔥" if conf >= 75 else ""
        lineas.append(
            f"{emoji}{prio} *{s['ticker']}* {s.get('timeframe','?')} — "
            f"{s['tipo']} ({conf:.0f}%) @ {hora}"
        )

    # Resumen estadístico
    longs  = sum(1 for s in senales if s.get("direccion") == "LONG")
    shorts = sum(1 for s in senales if s.get("direccion") == "SHORT")
    lineas += [
        "",
        f"📊 _Total: {len(senales)} · 🟢 {longs} LONG · 🔴 {shorts} SHORT_",
        f"🕐 _{_hora_mx()} CDMX_",
    ]
    await _reply(update, "\n".join(lineas))


async def cmd_resumen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Generando reporte completo...")
    try:
        txt = await _generar_resumen_diario()
        await _reply(update, txt)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def cmd_capital(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Muestra el capital configurado y métricas básicas."""
    chat_id = str(update.effective_chat.id)
    try:
        configs = obtener_todas_configs_bot()
        cfg = next((c for c in configs if c.get("telegram_chat_id") == chat_id), None)
        if not cfg:
            await _reply(update,
                "⚙️ *Sin configuración vinculada*\n\n"
                "Vincula tu Chat ID en la app:\n"
                "App → Bot Telegram → Chat ID → Guardar configuración"
            )
            return

        user_id = cfg.get("user_id")
        # Obtener el capital del usuario
        users = obtener_todos_usuarios()
        user  = next((u for u in users if u["id"] == user_id), None)
        capital = user.get("capital_inicial", 10000.0) if user else 10000.0

        trades = obtener_trades(user_id) if user_id else []
        pnl    = sum(t.get("resultado_usd", 0) or 0 for t in trades)
        n_trades = len(trades)
        ganadores = sum(1 for t in trades if (t.get("resultado_usd") or 0) > 0)
        wr = ganadores / n_trades * 100 if n_trades else 0

        await _reply(update,
            f"💼 *TU CUENTA ORAM*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"💰 Capital inicial: *${capital:,.2f}*\n"
            f"📊 Capital actual: *${capital + pnl:,.2f}*\n"
            f"{'🟢' if pnl >= 0 else '🔴'} P&L total: *${pnl:+,.2f}*\n"
            "\n"
            f"📈 Trades registrados: {n_trades}\n"
            f"✅ Win rate: {wr:.1f}%\n"
            "\n"
            f"⚙️ Umbral señales: {cfg.get('umbral_confianza', 70):.0f}%\n"
            f"⏱ Timeframe monitor: {cfg.get('tf_monitor', '15m')}\n"
            f"🕐 {_hora_mx()} CDMX"
        )
    except Exception as e:
        logger.error(f"cmd_capital: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")


async def cmd_ayuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _reply(update,
        "🤖 *ORAM Quant Systems — Guía completa*\n\n"

        "🔍 *ANÁLISIS DE MERCADO:*\n"
        "/mercado — Resumen de todos los pares (1H)\n"
        "/senales — Señales SMC activas ≥60% confianza\n"
        "/mtf [TICKER] — Multi-Timeframe (Ej: `/mtf EURUSD`)\n"
        "/analizar [TICKER] [TF] — Análisis completo (Ej: `/analizar GBPUSD 1h`)\n\n"

        "💼 *GESTIÓN DE RIESGO:*\n"
        "/riesgo [TICKER] [ENTRADA] [SL] [TP] — Calcula lote y RR\n"
        "/capital — Tu cuenta y métricas\n\n"

        "📰 *INFORMACIÓN:*\n"
        "/noticias — Eventos económicos hoy\n"
        "/proximos — Próximos eventos (2h)\n"
        "/sesiones — Horarios de sesiones CDMX\n\n"

        "📊 *HISTORIAL:*\n"
        "/alertas — Señales últimas 24h\n"
        "/resumen — Reporte diario completo\n\n"

        "🤖 *AUTOMÁTICO (sin comandos):*\n"
        "• 🚨 Alertas de compra/venta cuando confianza ≥75%\n"
        "• ⚡ Escaneo c/15min en tu timeframe configurado\n"
        "• 🔔 Alertas de precio cuando el par toca tu nivel\n"
        "• 🌅 Reporte diario a las 7AM CDMX\n"
        "• ⚠️ Aviso automático antes de noticias de alto impacto\n\n"

        "💡 *Tips:*\n"
        "• Señales 🔥 ALTA (≥75%) = mayor probabilidad\n"
        "• Usa /mtf para confirmar dirección antes de entrar\n"
        "• Configura tus activos favoritos en la app\n\n"

        "⚠️ _Las señales son orientativas. Siempre usa SL._"
    )


async def cmd_desconocido(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Comando no reconocido.\n"
        "Usa /ayuda para ver todos los comandos disponibles."
    )


# ─── Jobs automáticos (el corazón del sistema) ───────────────────────────────

async def _generar_resumen_diario() -> str:
    activos = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "BTC-USD", "GC=F"]
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
                emoji  = _emoji_dir(dir_)
                flag   = "🔥" if conf >= 75 else ""
                lineas.append(
                    f"{emoji}{flag} *{ticker}* `{precio:.4f}` — {tipo} ({conf:.0f}%) RSI:{rsi:.0f}"
                )
                if conf >= 60 and dir_ != "neutral":
                    señales_activas += 1
        except Exception:
            lineas.append(f"⚫ {ticker} — Sin datos")

    # Resumen de señales del día
    try:
        senales_24h = obtener_señales_recientes(horas=24)
        longs  = sum(1 for s in senales_24h if s.get("direccion") == "LONG")
        shorts = sum(1 for s in senales_24h if s.get("direccion") == "SHORT")
        lineas += [
            "",
            "⚡ *Actividad de señales (24h):*",
            f"  🟢 LONG: {longs}  |  🔴 SHORT: {shorts}  |  Total: {len(senales_24h)}",
        ]
    except Exception:
        pass

    # Eventos del día
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
        "",
        "💡 *Sesiones clave (CDMX):*",
        "  🟡 London Open: 02:00-04:00",
        "  🔥 Overlap L+NY: 07:00-10:00",
        "  🟠 NY Open: 07:30-09:30",
        "",
        f"📡 *Señales activas ahora: {señales_activas}*",
        "━━━━━━━━━━━━━━━━",
        "⚠️ _Max 1-2% riesgo por trade_",
        "🤖 _ORAM Quant Systems_",
    ]
    return "\n".join(lineas)


async def job_resumen_diario(ctx: ContextTypes.DEFAULT_TYPE):
    """Envía reporte diario a las 7AM CDMX."""
    try:
        configs = obtener_todas_configs_bot()
        txt     = await _generar_resumen_diario()
        for cfg in configs:
            if cfg.get("resumen_diario") and cfg.get("telegram_chat_id"):
                await _send(ctx.bot, cfg["telegram_chat_id"], txt)
    except Exception as e:
        logger.error(f"job_resumen_diario: {e}")


async def job_alerta_noticias(ctx: ContextTypes.DEFAULT_TYPE):
    """
    Avisa 30 min antes de eventos de alto impacto.
    Se ejecuta cada 5 minutos.
    """
    try:
        hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=35)
        if not hay_ev or not ev_info:
            return

        # Solo avisar si faltan entre 25 y 35 minutos (ventana de 10 min para evitar spam)
        mins = ev_info.get("minutos_restantes", 99)
        if not (25 <= mins <= 35):
            return

        configs = obtener_todas_configs_bot()
        msg = (
            f"⚠️ *AVISO — EVENTO DE ALTO IMPACTO EN {mins} MIN*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📰 {ev_info['titulo']}\n"
            f"🌍 Moneda: {ev_info['moneda']}\n"
            f"🕐 Hora: {ev_info['hora_mx']} CDMX\n\n"
            "❌ *Recomendación:* No abrir nuevas posiciones.\n"
            "Cierra posiciones de corto plazo si tienes.\n"
            "Espera 30 min después del evento.\n"
            "_ORAM Quant Systems_"
        )
        for cfg in configs:
            if cfg.get("alertas_activas") and cfg.get("telegram_chat_id"):
                await _send(ctx.bot, cfg["telegram_chat_id"], msg)
    except Exception as e:
        logger.error(f"job_alerta_noticias: {e}")


async def job_monitoreo_senales(ctx: ContextTypes.DEFAULT_TYPE):
    """
    Escaneo periódico (cada 15 min) — envía alertas de compra/venta
    cuando la confianza supera el umbral configurado por el usuario.
    Prioriza señales de alta confianza (≥75%) sobre las medias (≥60%).
    """
    try:
        if not _en_horario_trading():
            return  # No molestar fuera de horario de mercado

        configs = obtener_todas_configs_bot()
        if not configs:
            return

        # Bloquear si hay evento de alto impacto en los próximos 20 min
        try:
            hay_ev, _ = hay_evento_alto_impacto_pronto(minutos=20)
            if hay_ev:
                return
        except Exception:
            pass

        activos_default = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X"]

        for cfg in configs:
            chat_id = cfg.get("telegram_chat_id", "")
            if not chat_id or not cfg.get("alertas_activas"):
                continue

            umbral = float(cfg.get("umbral_confianza", 70))
            tf     = cfg.get("tf_monitor", "15m")
            try:
                activos = json.loads(cfg.get("activos_monitor", "[]")) or activos_default
            except Exception:
                activos = activos_default

            alertas_alta   = []
            alertas_media  = []

            for ticker in activos:
                try:
                    smc, _ = _analizar_activo(ticker, tf)
                    if not smc or "error" in smc:
                        continue

                    conf  = smc.get("confluencia", {}).get("confianza", 0)
                    dir_  = smc.get("estructura",  {}).get("direccion", "neutral")
                    tipo  = smc.get("estructura",  {}).get("tipo", "")
                    precio = smc.get("precio", 0)
                    sl    = smc.get("sl_sugerido", 0)
                    tp_   = smc.get("tp_sugerido", 0)

                    if dir_ == "neutral" or conf < umbral:
                        continue

                    # Registrar en DB para historial
                    sig_id = registrar_señal(ticker, tf, tipo, dir_, conf, precio, sl, tp_)

                    if conf >= UMBRAL_ALERTA_ALTA:
                        alertas_alta.append((ticker, smc, conf, sig_id))
                    elif conf >= umbral:
                        alertas_media.append((ticker, smc, conf, sig_id))

                except Exception as e:
                    logger.error(f"job_monitoreo {ticker}: {e}")

            # Enviar alertas de ALTA prioridad con formato completo
            for ticker, smc, conf, sig_id in sorted(alertas_alta, key=lambda x: -x[2]):
                try:
                    msg = "🚨 *SEÑAL DE ALTA PRIORIDAD*\n" + _formato_senal_completo(smc, ticker, tf)
                    await _send(ctx.bot, chat_id, msg)
                    marcar_señal_enviada(sig_id)
                    logger.info(f"Señal ALTA enviada: {ticker} conf={conf:.0f}%")
                except Exception as e:
                    logger.error(f"send alta {ticker}: {e}")

            # Enviar alertas MEDIAS como resumen compacto (agrupar para no spamear)
            if alertas_media:
                lineas = ["⚡ *SEÑALES MEDIAS DETECTADAS*", f"_TF: {tf} · {_hora_mx()} CDMX_", ""]
                for ticker, smc, conf, sig_id in sorted(alertas_media, key=lambda x: -x[2]):
                    dir_  = smc.get("estructura", {}).get("direccion", "neutral")
                    tipo  = smc.get("estructura", {}).get("tipo", "?")
                    precio = smc.get("precio", 0)
                    sl    = smc.get("sl_sugerido", 0)
                    tp_   = smc.get("tp_sugerido", 0)
                    emoji = _emoji_dir(dir_)
                    lineas.append(
                        f"{emoji} *{ticker}* `{precio:.5f}` — {tipo} ({conf:.0f}%)\n"
                        f"   SL:`{sl:.5f}` TP:`{tp_:.5f}`"
                    )
                    marcar_señal_enviada(sig_id)
                try:
                    await _send(ctx.bot, chat_id, "\n".join(lineas))
                except Exception as e:
                    logger.error(f"send medias: {e}")

    except Exception as e:
        logger.error(f"job_monitoreo_senales: {e}")


async def job_monitoreo_mtf(ctx: ContextTypes.DEFAULT_TYPE):
    """
    Escaneo MTF cada 30 min — detecta alineaciones de alta confianza.
    Solo avisa cuando AMBOS timeframes apuntan en la misma dirección.
    """
    try:
        if not _en_horario_trading():
            return

        try:
            hay_ev, _ = hay_evento_alto_impacto_pronto(minutos=20)
            if hay_ev:
                return
        except Exception:
            pass

        configs = obtener_todas_configs_bot()
        activos_default = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]

        for cfg in configs:
            chat_id = cfg.get("telegram_chat_id", "")
            if not chat_id or not cfg.get("alertas_activas"):
                continue

            tf_bajo = cfg.get("tf_monitor", "15m")
            # Mapear TF bajo a TF alto para MTF
            tf_map  = {"1m":"5m","5m":"1h","15m":"1h","30m":"4h","1h":"4h","4h":"1d"}
            tf_alto = tf_map.get(tf_bajo, "1h")

            try:
                activos = json.loads(cfg.get("activos_monitor", "[]")) or activos_default
            except Exception:
                activos = activos_default

            for ticker in activos:
                try:
                    mtf = analisis_mtf(ticker, tf_alto, tf_bajo)
                    if not mtf.get("alineacion"):
                        continue

                    conf_mtf = mtf.get("confianza_mtf", 0)
                    if conf_mtf < UMBRAL_MTF_ALINEADO:
                        continue

                    msg = "🔭 *MTF ALINEADO — SEÑAL CONFIRMADA*\n" + _formato_mtf(mtf, ticker)
                    await _send(ctx.bot, chat_id, msg)
                    logger.info(f"MTF enviado: {ticker} {tf_alto}/{tf_bajo} conf={conf_mtf:.0f}%")

                except Exception as e:
                    logger.error(f"job_mtf {ticker}: {e}")

    except Exception as e:
        logger.error(f"job_monitoreo_mtf: {e}")


async def job_verificar_alertas_precio(ctx: ContextTypes.DEFAULT_TYPE):
    """
    Verifica alertas de precio cada 5 min.
    Envía notificación cuando el precio toca el nivel configurado.
    """
    try:
        alertas = obtener_todas_alertas_activas()
        if not alertas:
            return

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
            if precio_actual is None:
                continue

            disparar = (
                (alerta["tipo"] == "above" and precio_actual >= alerta["precio"]) or
                (alerta["tipo"] == "below" and precio_actual <= alerta["precio"])
            )

            if not disparar:
                continue

            configs = obtener_todas_configs_bot()
            chat_id = next(
                (c.get("telegram_chat_id") for c in configs if c["user_id"] == alerta["user_id"]),
                None
            )
            if not chat_id:
                continue

            emoji   = "📈" if alerta["tipo"] == "above" else "📉"
            dir_str = "superó al alza" if alerta["tipo"] == "above" else "cayó por debajo de"
            diff    = abs(precio_actual - alerta["precio"])

            msg = (
                f"🔔 *ALERTA DE PRECIO DISPARADA*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"{emoji} *{ticker}* {dir_str} `{alerta['precio']:.5f}`\n"
                f"💰 Precio actual: `{precio_actual:.5f}`\n"
                f"📏 Diferencia: {diff:.5f}\n"
                f"{alerta['mensaje'] or ''}\n"
                f"🕐 {_hora_mx()} CDMX\n\n"
                f"💡 _Usa /analizar {ticker.replace('=X','')} para análisis completo_"
            )
            await _send(ctx.bot, chat_id, msg)
            disparar_alerta(alerta["id"])
            logger.info(f"Alerta precio disparada: {ticker} @ {precio_actual:.5f}")

    except Exception as e:
        logger.error(f"job_verificar_alertas: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────

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

    print("🤖 Iniciando ORAM Quant Bot v2...")
    app = Application.builder().token(TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("mercado",  cmd_mercado))
    app.add_handler(CommandHandler("senales",  cmd_senales))
    app.add_handler(CommandHandler("mtf",      cmd_mtf))
    app.add_handler(CommandHandler("analizar", cmd_analizar))
    app.add_handler(CommandHandler("riesgo",   cmd_riesgo))
    app.add_handler(CommandHandler("noticias", cmd_noticias))
    app.add_handler(CommandHandler("proximos", cmd_proximos))
    app.add_handler(CommandHandler("sesiones", cmd_sesiones))
    app.add_handler(CommandHandler("alertas",  cmd_alertas))
    app.add_handler(CommandHandler("resumen",  cmd_resumen))
    app.add_handler(CommandHandler("capital",  cmd_capital))
    app.add_handler(CommandHandler("ayuda",    cmd_ayuda))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_desconocido))

    # Jobs automáticos
    jq = app.job_queue
    if jq is not None:
        # Reporte diario 7AM CDMX (13:00 UTC)
        jq.run_daily(
            job_resumen_diario,
            time=dtime(hour=13, minute=0)  # 13:00 UTC = 07:00 CDMX
        )
        # Monitoreo de señales cada 15 min
        jq.run_repeating(job_monitoreo_senales, interval=900, first=60)
        # Análisis MTF cada 30 min
        jq.run_repeating(job_monitoreo_mtf, interval=1800, first=120)
        # Verificación de alertas de precio cada 5 min
        jq.run_repeating(job_verificar_alertas_precio, interval=300, first=30)
        # Aviso de noticias cada 5 min
        jq.run_repeating(job_alerta_noticias, interval=300, first=60)

        print("✅ Jobs activos:")
        print("   🌅 Reporte diario → 7AM CDMX")
        print("   🚨 Señales SMC   → cada 15 min")
        print("   🔭 MTF alineado  → cada 30 min")
        print("   🔔 Alertas precio → cada 5 min")
        print("   📰 Aviso noticias → cada 5 min")
    else:
        print("⚠️ Sin jobs. Instala: pip install APScheduler")

    print("\n✅ Bot activo. Ctrl+C para detener.")
    print("Comandos: /start /mercado /senales /mtf /analizar /riesgo")
    print("          /noticias /proximos /sesiones /alertas /resumen /capital /ayuda")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
