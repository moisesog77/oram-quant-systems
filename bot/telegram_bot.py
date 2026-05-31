"""
bot/telegram_bot.py — ORAM Quant Systems Bot
Sin MarkdownV2 — usa Markdown v1 simple para evitar errores de escape.
"""
import os, sys, json, logging
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_OK = True
except ImportError:
    TELEGRAM_OK = False

from utils.market_data       import obtener_datos, ACTIVOS_DEFAULT
from utils.smc_engine        import analisis_completo
from utils.economic_calendar import (obtener_eventos_hoy, obtener_proximos_eventos,
                                      hay_evento_alto_impacto_pronto, impacto_emoji)
from database.db import (obtener_todas_configs_bot, obtener_todas_alertas_activas,
                          disparar_alerta, registrar_señal, marcar_señal_enviada,
                          obtener_señales_recientes, inicializar_db)

TZ_MX  = ZoneInfo("America/Mexico_City")
TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

MD = "Markdown"   # Markdown v1 — solo escapa ` * _ [


# ─── Helpers ──────────────────────────────────────────────────────────────────



def _analizar_activo(ticker, tf="15m"):
    try:
        df, status = obtener_datos(ticker, tf)
        if df is None:
            return None, status
        return analisis_completo(df, ticker), status
    except Exception as e:
        logger.error(f"Error analizando {ticker}: {e}")
        return None, str(e)


def _conf_bar(pct):
    filled = int(pct / 10)
    return "█" * filled + "░" * (10 - filled) + f" {pct:.0f}%"


def _formato_senal(smc, ticker, tf):
    est    = smc.get("estructura", {})
    conf   = smc.get("confluencia", {})
    dir_   = est.get("direccion", "neutral")
    tipo   = est.get("tipo", "Sin señal")
    pct    = conf.get("confianza", 0)
    precio = smc.get("precio", 0)
    sl     = smc.get("sl_sugerido", 0)
    tp_    = smc.get("tp_sugerido", 0)
    atr    = smc.get("atr", 0)
    rsi    = smc.get("rsi", 0)
    factores = conf.get("factores", [])

    if dir_ == "LONG":
        emoji_dir = "🟢 LONG"
    elif dir_ == "SHORT":
        emoji_dir = "🔴 SHORT"
    else:
        emoji_dir = "⚪ NEUTRAL"

    emoji = "🟢" if dir_ == "LONG" else "🔴" if dir_ == "SHORT" else "⚪"

    lineas = [
        f"{emoji} *{ticker}* — {tf}",
        "━━━━━━━━━━━━━",
        f"📌 Señal: *{tipo}*",
        f"💰 Precio: {precio:.5f}",
        f"📊 Dirección: {emoji_dir}",
        f"🎯 Confianza: {_conf_bar(pct)}",
        f"📉 RSI: {rsi:.1f}",
        f"📏 ATR: {atr:.5f}",
    ]
    if sl and tp_:
        lineas.append(f"🛑 SL: {sl:.5f}")
        lineas.append(f"✅ TP: {tp_:.5f}")
    if factores:
        lineas.append("⚡ Confluencias:")
        for f in factores:
            lineas.append(f"  • {f}")
    lineas.append(f"🕐 {datetime.now(TZ_MX).strftime('%H:%M')} CDMX")
    return "\n".join(lineas)


async def _reply(update, text):
    """Envía mensaje usando Markdown simple. Si falla, reintenta como texto plano."""
    try:
        if len(text) > 4000:
            text = text[:3990] + "\n_...truncado_"
        await update.message.reply_text(text, parse_mode=MD)
    except Exception as e:
        logger.error(f"Markdown error: {e}")
        try:
            # Reintentar sin formato
            plain = text.replace("*","").replace("_","").replace("`","")
            await update.message.reply_text(plain)
        except Exception as e2:
            logger.error(f"Plain text error: {e2}")


async def _send(bot, chat_id, text):
    """Envía mensaje desde job. Si falla con Markdown, reintenta sin formato."""
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


# ─── Comandos ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    msg = (
        "👋 *Bienvenido a ORAM Quant Systems*\n\n"
        "Comandos disponibles:\n"
        "📊 /mercado — Resumen del mercado ahora\n"
        "🔴 /senales — Señales SMC activas\n"
        "📰 /noticias — Eventos económicos hoy\n"
        "⚠️ /alertas — Historial de señales 24h\n"
        "📈 /resumen — Reporte diario completo\n"
        "❓ /ayuda — Lista de comandos\n\n"
        f"🔑 Tu Chat ID: `{chat_id}`\n"
        "_(Cópialo en la app → Bot Telegram → Chat ID)_"
    )
    await _reply(update, msg)


async def cmd_mercado(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Analizando mercado... espera un momento.")

    activos = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "BTC-USD", "GC=F"]
    lineas  = [
        "📊 *RESUMEN DE MERCADO*",
        f"_{datetime.now(TZ_MX).strftime('%d/%m/%Y %H:%M')} CDMX_",
        "━━━━━━━━━━━━━",
    ]

    for ticker in activos:
        try:
            smc, _ = _analizar_activo(ticker, "1h")
            if smc and "error" not in smc:
                est    = smc.get("estructura", {})
                dir_   = est.get("direccion", "neutral")
                conf   = smc.get("confluencia", {}).get("confianza", 0)
                precio = smc.get("precio", 0)
                tipo   = est.get("tipo", "?")
                emoji  = "🟢" if dir_=="LONG" else "🔴" if dir_=="SHORT" else "⚪"
                lineas.append(f"{emoji} *{ticker}* {precio:.5f} — {tipo} ({conf:.0f}%)")
            else:
                lineas.append(f"⚫ {ticker} — Sin datos")
        except Exception as e:
            lineas.append(f"⚫ {ticker} — Error")
            logger.error(f"cmd_mercado {ticker}: {e}")

    try:
        proximos = obtener_proximos_eventos(2)
        if proximos:
            lineas.append("")
            lineas.append("📰 *Próximos eventos:*")
            for ev in proximos:
                lineas.append(f"{impacto_emoji(ev['impacto'])} {ev['titulo']} — {ev['hora_mx']} CDMX")
    except Exception as e:
        logger.error(f"cmd_mercado eventos: {e}")

    await _reply(update, "\n".join(lineas))


async def cmd_senales(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Buscando señales SMC...")

    try:
        hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=30)
        if hay_ev and ev_info:
            await _reply(update,
                f"⚠️ *Precaución* — Evento de alto impacto en {ev_info['minutos_restantes']} min:\n"
                f"{ev_info['titulo']} ({ev_info['moneda']}) — {ev_info['hora_mx']} CDMX\n"
                "No es buen momento para entrar al mercado."
            )
            return
    except:
        pass

    activos     = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X"]
    encontradas = 0

    for ticker in activos:
        try:
            smc, _ = _analizar_activo(ticker, "15m")
            if not smc or "error" in smc:
                continue
            conf = smc.get("confluencia", {}).get("confianza", 0)
            dir_ = smc.get("estructura",  {}).get("direccion", "neutral")
            if conf >= 60 and dir_ != "neutral":
                await _reply(update, _formato_senal(smc, ticker, "15m"))
                encontradas += 1
        except Exception as e:
            logger.error(f"cmd_senales {ticker}: {e}")

    if encontradas == 0:
        await _reply(update,
            "⚪ *Sin señales de alta confianza ahora*\n"
            "Umbral: 60% de confluencia con estructura confirmada.\n\n"
            "💡 Mejores horarios:\n"
            "• London Open: 02:00-04:00 CDMX\n"
            "• NY Open: 07:30-09:30 CDMX\n"
            "• Overlap: 07:00-10:00 CDMX"
        )


async def cmd_noticias(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        eventos = obtener_eventos_hoy()
    except Exception as e:
        await update.message.reply_text(f"Error obteniendo eventos: {str(e)[:100]}")
        return

    if not eventos:
        await update.message.reply_text("📰 Sin eventos económicos importantes hoy.")
        return

    lineas = [
        "📰 *EVENTOS ECONÓMICOS HOY*",
        f"_{datetime.now(TZ_MX).strftime('%d/%m/%Y')}_",
        "━━━━━━━━━━━━━",
    ]
    for ev in eventos:
        estado = "✅" if ev["ya_paso"] else "⏳"
        lineas.append(f"{estado} {impacto_emoji(ev['impacto'])} *{ev['hora_mx']}* — {ev['titulo']} ({ev['moneda']})")

    lineas.append("")
    lineas.append("⚠️ _Evita operar ±30 min en eventos 🔴 High_")
    await _reply(update, "\n".join(lineas))


async def cmd_alertas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        senales = obtener_señales_recientes(horas=24)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)[:100]}")
        return

    if not senales:
        await update.message.reply_text("📭 Sin señales registradas en las últimas 24h.")
        return

    lineas = ["⚡ *SEÑALES ÚLTIMAS 24H*", "━━━━━━━━━━━━━"]
    for s in senales[:8]:
        emoji = "🟢" if s["direccion"]=="LONG" else "🔴"
        hora  = s["created_at"][-8:-3] if len(s["created_at"]) > 8 else "?"
        lineas.append(f"{emoji} *{s['ticker']}* {s.get('timeframe','?')} — {s['tipo']} ({s['confianza']:.0f}%) @ {hora}")

    await _reply(update, "\n".join(lineas))


async def cmd_resumen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Generando reporte...")
    try:
        txt = await _generar_resumen_diario()
        await _reply(update, txt)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)[:100]}")


async def cmd_ayuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _reply(update,
        "🤖 *ORAM Quant Systems — Comandos*\n\n"
        "/start — Bienvenida y tu Chat ID\n"
        "/mercado — Resumen del mercado ahora\n"
        "/senales — Señales SMC activas (60%+ confianza)\n"
        "/noticias — Eventos económicos del día en CDMX\n"
        "/alertas — Historial de señales últimas 24h\n"
        "/resumen — Reporte diario completo\n"
        "/ayuda — Este menú\n\n"
        "💡 _Configura el bot en la app → Bot Telegram_\n"
        "⚠️ _Las señales son orientativas. Siempre usa SL._"
    )


async def cmd_desconocido(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Comando no reconocido. Usa /ayuda para ver los comandos disponibles.")


# ─── Jobs automáticos ─────────────────────────────────────────────────────────

async def _generar_resumen_diario() -> str:
    activos = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "BTC-USD"]
    lineas  = [
        "🌅 *RESUMEN DIARIO SMC*",
        f"_{datetime.now(TZ_MX).strftime('%A %d/%m/%Y')}_",
        "━━━━━━━━━━━━━",
        "",
        "📊 *Estado del mercado (1H):*",
    ]

    for ticker in activos:
        try:
            smc, _ = _analizar_activo(ticker, "1h")
            if smc and "error" not in smc:
                est    = smc.get("estructura", {})
                conf   = smc.get("confluencia", {}).get("confianza", 0)
                precio = smc.get("precio", 0)
                tipo   = est.get("tipo", "?")
                emoji  = "🟢" if est.get("direccion")=="LONG" else "🔴" if est.get("direccion")=="SHORT" else "⚪"
                lineas.append(f"{emoji} *{ticker}* {precio:.5f} — {tipo} ({conf:.0f}%)")
        except:
            lineas.append(f"⚫ {ticker} — Sin datos")

    try:
        eventos = obtener_eventos_hoy()
        if eventos:
            lineas.append("")
            lineas.append("📰 *Eventos hoy:*")
            for ev in eventos:
                lineas.append(f"{impacto_emoji(ev['impacto'])} {ev['hora_mx']} {ev['titulo']}")
    except:
        pass

    lineas += [
        "",
        "💡 *Sesiones clave (CDMX):*",
        "🟡 London Open: 02:00-04:00",
        "🟠 NY Open: 07:30-09:30",
        "🔵 Overlap: 07:00-10:00",
        "",
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


async def job_monitoreo_senales(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        configs = obtener_todas_configs_bot()
        if not configs:
            return
        hay_ev, _ = hay_evento_alto_impacto_pronto(minutos=30)
        if hay_ev:
            return

        activos_default = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X"]

        for cfg in configs:
            chat_id  = cfg.get("telegram_chat_id", "")
            umbral   = float(cfg.get("umbral_confianza", 70))
            tf       = cfg.get("tf_monitor", "15m")
            try:
                activos = json.loads(cfg.get("activos_monitor", '[]')) or activos_default
            except:
                activos = activos_default

            for ticker in activos:
                try:
                    smc, _ = _analizar_activo(ticker, tf)
                    if not smc or "error" in smc:
                        continue
                    conf  = smc.get("confluencia", {}).get("confianza", 0)
                    dir_  = smc.get("estructura",  {}).get("direccion", "neutral")
                    tipo  = smc.get("estructura",  {}).get("tipo", "")
                    precio= smc.get("precio", 0)
                    sl    = smc.get("sl_sugerido", 0)
                    tp_   = smc.get("tp_sugerido", 0)

                    if conf >= umbral and dir_ != "neutral":
                        sig_id = registrar_señal(ticker, tf, tipo, dir_, conf, precio, sl, tp_)
                        txt = "🚨 *SEÑAL SMC DETECTADA*\n" + _formato_senal(smc, ticker, tf)
                        await _send(ctx.bot, chat_id, txt)
                        marcar_señal_enviada(sig_id)
                        logger.info(f"Señal enviada: {ticker} {dir_} {conf:.0f}%")
                except Exception as e:
                    logger.error(f"job_monitoreo {ticker}: {e}")
    except Exception as e:
        logger.error(f"job_monitoreo_senales: {e}")


async def job_verificar_alertas_precio(ctx: ContextTypes.DEFAULT_TYPE):
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
                except:
                    continue

            precio_actual = precios_cache.get(ticker)
            if precio_actual is None:
                continue

            disparar = (
                (alerta["tipo"]=="above" and precio_actual >= alerta["precio"]) or
                (alerta["tipo"]=="below" and precio_actual <= alerta["precio"])
            )

            if disparar:
                configs = obtener_todas_configs_bot()
                chat_id = next((c.get("telegram_chat_id") for c in configs
                                if c["user_id"]==alerta["user_id"]), None)
                if chat_id:
                    emoji = "📈" if alerta["tipo"]=="above" else "📉"
                    txt = (
                        f"🔔 *ALERTA DE PRECIO*\n"
                        f"{emoji} *{ticker}* alcanzo {precio_actual:.5f}\n"
                        f"Nivel: {alerta['precio']:.5f}\n"
                        f"{alerta['mensaje']}\n"
                        f"🕐 {datetime.now(TZ_MX).strftime('%H:%M')} CDMX"
                    )
                    await _send(ctx.bot, chat_id, txt)
                    disparar_alerta(alerta["id"])
    except Exception as e:
        logger.error(f"job_verificar_alertas: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_OK:
        print("ERROR: py -m pip install python-telegram-bot APScheduler")
        return
    if not TOKEN:
        print("ERROR: Define TELEGRAM_BOT_TOKEN en .env")
        return

    try:
        inicializar_db()
    except Exception as e:
        logger.warning(f"DB init: {e}")

    print("🤖 Iniciando ORAM Quant Bot...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("mercado",  cmd_mercado))
    app.add_handler(CommandHandler("senales",  cmd_senales))
    app.add_handler(CommandHandler("noticias", cmd_noticias))
    app.add_handler(CommandHandler("alertas",  cmd_alertas))
    app.add_handler(CommandHandler("resumen",  cmd_resumen))
    app.add_handler(CommandHandler("ayuda",    cmd_ayuda))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_desconocido))

    jq = app.job_queue
    if jq is not None:
        jq.run_daily(job_resumen_diario,
                     time=datetime.strptime("13:00", "%H:%M").time())
        jq.run_repeating(job_monitoreo_senales,        interval=900, first=60)
        jq.run_repeating(job_verificar_alertas_precio, interval=300, first=30)
        print("✅ Jobs: señales c/15min · alertas c/5min · resumen 8AM CDMX")
    else:
        print("⚠️ Sin jobs. Instala: py -m pip install APScheduler")

    print("✅ Bot activo. Ctrl+C para detener.")
    print("   Comandos: /start /mercado /senales /noticias /alertas /resumen /ayuda")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
