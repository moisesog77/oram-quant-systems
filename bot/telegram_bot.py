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

def _analizar_activo(ticker: str, tf: str = "15m"):
    try:
        df, status = obtener_datos(ticker, tf)
        if df is None:
            return None, status
        smc = analisis_completo(df, ticker)
        # Inyectar aviso de fuente de datos si se está usando yfinance (15min delay)
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

    lineas = [
        f"{'🚨' if pct >= 75 else '📡'} *SEÑAL SMC — {prio}*",
        f"{emoji} *{ticker}* · {tf}",
        "━━━━━━━━━━━━━━━━",
        f"📌 *Señal:* {tipo}",
        f"💰 *Precio actual:* `{precio:.5f}`",
        f"📊 *Dirección:* {emoji} {dir_}",
        entrada_txt,
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
    return "\n".join(l for l in lineas if l is not None)

def _formato_mtf(mtf: dict, ticker: str) -> str:
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
    lineas += ["", f"📝 _{desc}_", "", f"🕐 {_hora_mx()} CDMX"]
    return "\n".join(l for l in lineas if l is not None)


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
    await update.message.reply_text("🔍 Analizando mercado... espera.")
    categorias = {
        "Forex":   ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","AUDUSD=X","USDCAD=X"],
        "Cripto":  ["BTC-USD","ETH-USD"],
        "Materias":["GC=F","CL=F"],
    }
    lineas = [
        "📊 *RESUMEN DE MERCADO*",
        f"_{datetime.now(TZ_MX).strftime('%d/%m/%Y %H:%M')} CDMX_",
        "━━━━━━━━━━━━━━━━",
    ]
    for cat, tickers in categorias.items():
        icons = {"Forex":"🔵","Cripto":"🟡","Materias":"🟠"}
        lineas.append(f"\n{icons[cat]} *{cat}:*")
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
    if not activos:
        activos = ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","AUDUSD=X","USDCAD=X","XAUUSD=X"]

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
    ticker = args[0].upper()
    if not ticker.endswith("=X") and ticker not in ["BTC-USD","ETH-USD","GC=F","CL=F"]:
        ticker = ticker + "=X"
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
    """Multi-Timeframe. Uso: /mtf EURUSD [combo]
    Combos: scalping, intraday, swing, posicional"""
    args   = ctx.args
    ticker = args[0].upper() if args else "EURUSD=X"
    if not ticker.endswith("=X") and ticker not in ["BTC-USD","ETH-USD","GC=F","CL=F"]:
        ticker = ticker + "=X"

    combo_key = (args[1].lower() if len(args) > 1 else "intraday")
    combo_map = {
        "scalping": "Scalping (5m/1m)",
        "intraday": "Intraday (1h/15m)",
        "swing":    "Swing (4h/1h)",
        "posicional": "Posicional (1d/4h)",
    }
    combo    = combo_map.get(combo_key, "Intraday (1h/15m)")
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
    ticker = args[0].upper()
    if not ticker.endswith("=X") and ticker not in ["BTC-USD","ETH-USD","GC=F","CL=F"]:
        ticker = ticker + "=X"
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

        "🤖 *AUTOMÁTICO (sin comandos):*\n"
        "• 🚨 Alertas compra/venta cuando confianza ≥umbral\n"
        "• 🔭 MTF alineado → notificación automática\n"
        "• 🔔 Alertas de precio en tus niveles\n"
        "• ⚠️ Aviso 30 min antes de noticias alto impacto\n"
        "• 🌅 Reporte diario a las 7AM CDMX\n\n"

        "⚠️ _Las señales son orientativas. Siempre usa SL._"
    )


async def cmd_desconocido(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Comando no reconocido.\nUsa /ayuda para ver todos los comandos.")


# ─── JOBS AUTOMÁTICOS ─────────────────────────────────────────────────────────

async def _generar_resumen_diario() -> str:
    activos = ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","BTC-USD","GC=F"]
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


async def job_alerta_noticias(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=35)
        if not hay_ev or not ev_info:
            return
        mins = ev_info.get("minutos_restantes", 99)
        if not (25 <= mins <= 35):
            return
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
        activos_default = ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","AUDUSD=X"]

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
                    msg = "🚨 *SEÑAL ALTA PRIORIDAD*\n" + _formato_senal_completo(smc, ticker, tf, capital, riesgo_pct)
                    await _send(ctx.bot, chat_id, msg)
                    marcar_señal_enviada(sig_id)
                except Exception as e:
                    logger.error(f"send alta {ticker}: {e}")

            if medias:
                lineas = [f"⚡ *SEÑALES MEDIAS — {tf} · {_hora_mx()} CDMX*", ""]
                for ticker, smc, conf, sig_id in sorted(medias, key=lambda x: -x[2]):
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
                try:
                    await _send(ctx.bot, chat_id, "\n".join(lineas))
                except Exception as e:
                    logger.error(f"send medias: {e}")

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
        activos_default = ["EURUSD=X","GBPUSD=X","USDJPY=X"]
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
                    if mtf.get("confianza_mtf", 0) < UMBRAL_MTF_ALINEADO: continue
                    # Verificar que AMBOS timeframes tienen señal válida SMC
                    smc_alto = mtf.get("smc_alto", {})
                    smc_bajo = mtf.get("smc_bajo", {})
                    if not smc_alto.get("señal_valida") or not smc_bajo.get("señal_valida"): continue
                    dir_mtf = mtf.get("direccion", "neutral")
                    if (ticker, dir_mtf) in mtf_recientes: continue
                    await _send(ctx.bot, chat_id, "🔭 *MTF ALINEADO — SEÑAL CONFIRMADA*\n" + _formato_mtf(mtf, ticker))
                except Exception as e:
                    logger.error(f"job_mtf {ticker}: {e}")
    except Exception as e:
        logger.error(f"job_monitoreo_mtf: {e}")


async def job_verificar_alertas_precio(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        alertas = obtener_todas_alertas_activas()
        if not alertas: return
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
    ]:
        app.add_handler(CommandHandler(cmd, handler))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_desconocido))

    jq = app.job_queue
    if jq is not None:
        jq.run_daily(job_resumen_diario, time=dtime(hour=13, minute=0))  # 7AM CDMX
        jq.run_repeating(job_monitoreo_senales,    interval=300,  first=60)
        jq.run_repeating(job_monitoreo_mtf,        interval=900,  first=120)
        jq.run_repeating(job_verificar_alertas_precio, interval=300, first=30)
        jq.run_repeating(job_alerta_noticias,      interval=300,  first=60)
        print("✅ Jobs activos: Reporte diario · Señales c/5m · MTF c/15m · Alertas precio c/5m · Noticias c/5m")
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
