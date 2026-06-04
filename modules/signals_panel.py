"""
modules/signals_panel.py — ORAM Quant Systems
Panel de señales en tiempo real: escaneo de múltiples activos simultáneamente.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from utils.market_data import ACTIVOS_DEFAULT, obtener_datos
from utils.smc_engine import analisis_completo
from utils.economic_calendar import hay_evento_alto_impacto_pronto, obtener_proximos_eventos, impacto_emoji
from ui.styles import get_colors, page_header

TZ_MX = ZoneInfo("America/Mexico_City")


def _semaforo(confianza, dir_):
    if dir_ == "neutral":
        return "⚪", "NEUTRO", "#6b7f99"
    if confianza >= 70:
        color  = "#22c55e" if dir_=="LONG" else "#ef4444"
        emoji  = "🟢" if dir_=="LONG" else "🔴"
        label  = "FUERTE"
    elif confianza >= 50:
        color  = "#c9a227"
        emoji  = "🟡"
        label  = "MODERADO"
    else:
        color  = "#6b7f99"
        emoji  = "⚪"
        label  = "DÉBIL"
    return emoji, label, color


def render_signals_panel():
    user = st.session_state.user
    c    = get_colors()

    page_header("⚡", "Panel de Señales", "Escaneo multi-activo en tiempo real · SMC Score")

    # ── Alerta noticias ────────────────────────────────────────────────────
    hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=60)
    if hay_ev and ev_info:
        st.error(f"⚠️ **Evento de alto impacto en {ev_info['minutos_restantes']} min** — "
                 f"{ev_info['titulo']} · {ev_info['hora_mx']} CDMX")

    # ── Controles ──────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([2,1,1,1])
    with col1:
        cats = st.multiselect("Categorías", list(ACTIVOS_DEFAULT.keys()),
                               default=["Forex"], key="sp_cats")
    with col2:
        tf = st.selectbox("Timeframe", ["5m","15m","30m","1h","4h"], index=1, key="sp_tf")
    with col3:
        umbral = st.slider("Confianza mín. %", 0, 90, 50, key="sp_umb")
    with col4:
        st.markdown("&nbsp;")
        escanear = st.button("⚡ Escanear", width='stretch', key="sp_scan")

    # Construir lista de activos
    activos = []
    for cat in (cats or list(ACTIVOS_DEFAULT.keys())):
        activos.extend(ACTIVOS_DEFAULT.get(cat, []))

    if not escanear and "sp_results" not in st.session_state:
        st.info("Selecciona categorías y timeframe, luego haz clic en **⚡ Escanear** para analizar el mercado.")
        return

    if escanear:
        resultados = []
        prog = st.progress(0, text="Escaneando mercado...")
        for i, ticker in enumerate(activos):
            prog.progress((i+1)/len(activos), text=f"Analizando {ticker}...")
            try:
                df, _ = obtener_datos(ticker, tf)
                if df is None:
                    continue
                smc  = analisis_completo(df, ticker)
                if "error" in smc:
                    continue
                conf = smc.get("confluencia",{}).get("confianza",0)
                dir_ = smc.get("estructura",{}).get("direccion","neutral")
                tipo = smc.get("estructura",{}).get("tipo","?")
                rsi  = smc.get("rsi",0)
                atr  = smc.get("atr",0)
                precio = smc.get("precio",0)
                sl   = smc.get("sl_sugerido",0)
                tp_  = smc.get("tp_sugerido",0)
                rr   = abs(tp_-precio)/abs(precio-sl) if sl and abs(precio-sl)>0 else 0
                resultados.append({
                    "ticker":ticker, "precio":precio, "dir":dir_,
                    "tipo":tipo, "conf":conf, "rsi":rsi, "atr":atr,
                    "sl":sl, "tp":tp_, "rr":rr,
                    "hora": datetime.now(TZ_MX).strftime("%H:%M"),
                })
            except:
                continue
        prog.empty()
        st.session_state["sp_results"] = resultados
        st.session_state["sp_time"]    = datetime.now(TZ_MX).strftime("%H:%M:%S")

    resultados = st.session_state.get("sp_results", [])
    scan_time  = st.session_state.get("sp_time", "")

    # ── Resumen rápido ─────────────────────────────────────────────────────
    total    = len(resultados)
    longs    = [r for r in resultados if r["dir"]=="LONG"  and r["conf"]>=umbral]
    shorts   = [r for r in resultados if r["dir"]=="SHORT" and r["conf"]>=umbral]
    neutrals = [r for r in resultados if r["dir"]=="neutral"]

    st.markdown(f"""
    <div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap;align-items:center">
        <div class="oram-card oram-card-teal" style="padding:0.6rem 1rem;margin:0;flex:1;min-width:120px">
            <div class="card-title">Escaneados</div>
            <div class="card-value">{total}</div>
        </div>
        <div class="oram-card oram-card-green" style="padding:0.6rem 1rem;margin:0;flex:1;min-width:120px">
            <div class="card-title">🟢 LONG</div>
            <div class="card-value" style="color:{c['green']}">{len(longs)}</div>
        </div>
        <div class="oram-card oram-card-red" style="padding:0.6rem 1rem;margin:0;flex:1;min-width:120px">
            <div class="card-title">🔴 SHORT</div>
            <div class="card-value" style="color:{c['red']}">{len(shorts)}</div>
        </div>
        <div class="oram-card" style="padding:0.6rem 1rem;margin:0;flex:1;min-width:120px">
            <div class="card-title">⚪ Neutro</div>
            <div class="card-value" style="color:{c['text_muted']}">{len(neutrals)}</div>
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:{c['text_muted']}">
            Última actualización:<br><b style="color:{c['accent3']}">{scan_time}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Señales destacadas (alta confianza) ────────────────────────────────
    destacadas = [r for r in resultados if r["conf"] >= umbral and r["dir"] != "neutral"]
    destacadas.sort(key=lambda x: -x["conf"])

    if not destacadas:
        st.warning(f"Sin señales con confianza ≥ {umbral}% en este momento. Baja el umbral o prueba más tarde.")
    else:
        st.markdown(f"### ⚡ {len(destacadas)} señales activas (≥{umbral}%)")
        for r in destacadas:
            emoji, label, color = _semaforo(r["conf"], r["dir"])
            border = c["green"] if r["dir"]=="LONG" else c["red"]
            st.markdown(f"""
            <div class="oram-card" style="border-left:4px solid {border};padding:0.9rem 1.2rem;margin-bottom:0.5rem">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
                    <div style="display:flex;align-items:center;gap:12px">
                        <span style="font-family:'Space Grotesk',sans-serif;font-size:1.1rem;
                                     font-weight:700;color:{c['text_strong']}">{r['ticker']}</span>
                        <span style="font-family:'JetBrains Mono',monospace;font-size:0.9rem;
                                     font-weight:700;color:{border}">{emoji} {'COMPRA' if r['dir']=='LONG' else 'VENTA'}</span>
                        <span style="font-size:0.78rem;background:{color}22;color:{color};
                                     border:1px solid {color}44;border-radius:4px;padding:2px 8px;font-weight:600">
                            {label}
                        </span>
                    </div>
                    <div style="display:flex;gap:16px;font-family:'JetBrains Mono',monospace;font-size:0.78rem">
                        <div style="text-align:center">
                            <div style="color:{c['text_muted']};font-size:0.65rem">PRECIO</div>
                            <div style="color:{c['text_strong']};font-weight:600">{r['precio']:.5f}</div>
                        </div>
                        <div style="text-align:center">
                            <div style="color:{c['text_muted']};font-size:0.65rem">RSI</div>
                            <div style="color:{'#ef4444' if r['rsi']>70 else '#22c55e' if r['rsi']<30 else c['accent2']};font-weight:600">{r['rsi']:.0f}</div>
                        </div>
                        <div style="text-align:center">
                            <div style="color:{c['text_muted']};font-size:0.65rem">RR</div>
                            <div style="color:{c['accent']};font-weight:600">{r['rr']:.1f}:1</div>
                        </div>
                        <div style="text-align:center">
                            <div style="color:{c['text_muted']};font-size:0.65rem">CONF</div>
                            <div style="color:{color};font-weight:700">{r['conf']:.0f}%</div>
                        </div>
                    </div>
                </div>
                <div style="margin-top:0.5rem;font-size:0.78rem;color:{c['text_muted']}">
                    📌 {r['tipo']} &nbsp;|&nbsp;
                    🛑 SL: <b>{r['sl']:.5f}</b> &nbsp;|&nbsp;
                    ✅ TP: <b>{r['tp']:.5f}</b> &nbsp;|&nbsp;
                    📏 ATR: {r['atr']:.5f} &nbsp;|&nbsp;
                    🕐 {r['hora']} CDMX
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tabla completa ─────────────────────────────────────────────────────
    if resultados:
        with st.expander(f"📋 Todos los activos escaneados ({total})"):
            df_res = pd.DataFrame([{
                "Ticker":    r["ticker"],
                "Precio":    r["precio"],
                "Dirección": r["dir"],
                "Señal":     r["tipo"],
                "Conf %":    r["conf"],
                "RSI":       r["rsi"],
                "RR":        r["rr"],
                "SL":        r["sl"],
                "TP":        r["tp"],
            } for r in resultados]).sort_values("Conf %", ascending=False)

            def color_dir(val):
                if val == "LONG":  return "color:#22c55e;font-weight:600"
                if val == "SHORT": return "color:#ef4444;font-weight:600"
                return "color:#6b7f99"
            def color_conf(val):
                if isinstance(val, (int,float)):
                    if val >= 70: return "color:#22c55e;font-weight:700"
                    if val >= 50: return "color:#c9a227"
                return ""

            st.dataframe(
                df_res.style
                    .map(color_dir,  subset=["Dirección"])
                    .map(color_conf, subset=["Conf %"]),
                width='stretch', height=350
            )
