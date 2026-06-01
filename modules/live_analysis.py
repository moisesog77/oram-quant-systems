"""
modules/live_analysis.py — ORAM Quant Systems — Análisis SMC en vivo.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.market_data import obtener_datos, ACTIVOS_DEFAULT
from utils.smc_engine import analisis_completo, calcular_riesgo
from utils.economic_calendar import (hay_evento_alto_impacto_pronto,
                                      obtener_proximos_eventos,
                                      impacto_emoji, impacto_color,
                                      FOREX_FACTORY_URL)
from ui.styles import signal_box, get_colors, get_plot_layout, page_header, get_theme

TIMEFRAME_LABELS = {
    "1m":"1 Min","5m":"5 Min","15m":"15 Min","30m":"30 Min",
    "1h":"1 Hora","4h":"4 Horas","1d":"Diario","1wk":"Semanal",
}


def _grafica_velas(df, ticker, smc):
    c   = get_colors()
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.62, 0.19, 0.19],
        vertical_spacing=0.03,
        subplot_titles=["", "RSI (14)", "MACD"],
    )

    # Velas
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"],  close=df["Close"], name=ticker,
        increasing_line_color=c["green"], decreasing_line_color=c["red"],
        increasing_fillcolor="rgba(34,197,94,0.7)",
        decreasing_fillcolor="rgba(239,68,68,0.7)",
    ), row=1, col=1)

    # EMAs
    for col_name, color, label in [
        ("EMA20", c["accent2"], "EMA20"),
        ("EMA50", c["accent"],  "EMA50"),
        ("EMA200",c["purple"],  "EMA200"),
    ]:
        if col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_name],
                line=dict(color=color, width=1.2),
                name=label, opacity=0.85,
            ), row=1, col=1)

    # Bollinger Bands
    if "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"],
            line=dict(color="rgba(139,92,246,0.35)", width=1, dash="dot"),
            name="BB", showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"],
            line=dict(color="rgba(139,92,246,0.35)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(139,92,246,0.04)",
            showlegend=False, name="BB Lower",
        ), row=1, col=1)

    # Order Blocks
    for ob in smc.get("order_blocks", [])[:3]:
        fc = "rgba(34,197,94,0.12)" if ob.tipo=="OB_alcista" else "rgba(239,68,68,0.12)"
        lc =  c["green"] if ob.tipo=="OB_alcista" else c["red"]
        fig.add_hrect(y0=ob.precio_bot, y1=ob.precio_top, fillcolor=fc,
            line=dict(color=lc, width=1, dash="dot"),
            annotation_text="OB↑" if ob.tipo=="OB_alcista" else "OB↓",
            annotation_font_size=9, annotation_font_color=lc, row=1, col=1)

    # FVGs
    for fvg in smc.get("fvgs", [])[:2]:
        fc = "rgba(61,155,233,0.10)" if fvg.tipo=="FVG_alcista" else "rgba(201,162,39,0.10)"
        lc = c["accent2"] if fvg.tipo=="FVG_alcista" else c["accent"]
        fig.add_hrect(y0=fvg.precio_bot, y1=fvg.precio_top, fillcolor=fc,
            line=dict(color=lc, width=1, dash="dot"),
            annotation_text="FVG", annotation_font_size=8,
            annotation_font_color=lc, row=1, col=1)

    # Liquidez
    liq = smc.get("liquidez", {})
    for lvl in liq.get("resistance_levels", [])[:2]:
        fig.add_hline(y=lvl, line=dict(color="rgba(239,68,68,0.4)", width=1, dash="dash"), row=1, col=1)
    for lvl in liq.get("support_levels", [])[:2]:
        fig.add_hline(y=lvl, line=dict(color="rgba(34,197,94,0.4)", width=1, dash="dash"), row=1, col=1)

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"],
            line=dict(color=c["accent2"], width=1.5),
            name="RSI", showlegend=False,
        ), row=2, col=1)
        for lvl, col_ in [(70,"rgba(239,68,68,0.5)"),(30,"rgba(34,197,94,0.5)"),(50,"rgba(107,127,153,0.3)")]:
            fig.add_hline(y=lvl, line=dict(color=col_, width=1, dash="dot"), row=2, col=1)

    # MACD
    if "MACD" in df.columns:
        hist = df["MACD_hist"]
        fig.add_trace(go.Bar(
            x=df.index, y=hist,
            marker_color=[c["green"] if v>=0 else c["red"] for v in hist],
            name="Hist", showlegend=False, opacity=0.7,
        ), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"],
            line=dict(color=c["accent"], width=1.2), name="MACD", showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"],
            line=dict(color=c["purple"], width=1.2), name="Signal", showlegend=False), row=3, col=1)

    tf = dict(color=c["text_muted"], size=9, family="JetBrains Mono")
    layout = get_plot_layout(height=660)
    layout.update(
        xaxis =dict(gridcolor=c["grid"], color=c["text_muted"],
                    tickfont=tf, tickcolor=c["text_muted"], showline=False),
        xaxis2=dict(gridcolor=c["grid"], color=c["text_muted"],
                    tickfont=tf, tickcolor=c["text_muted"], showline=False),
        xaxis3=dict(gridcolor=c["grid"], color=c["text_muted"],
                    tickfont=tf, tickcolor=c["text_muted"], showline=False),
        yaxis =dict(gridcolor=c["grid"], color=c["text_muted"], side="right",
                    tickfont=tf, tickcolor=c["text_muted"], showline=False),
        yaxis2=dict(gridcolor=c["grid"], color=c["text_muted"], side="right",
                    tickfont=tf, tickcolor=c["text_muted"], range=[0,100], showline=False),
        yaxis3=dict(gridcolor=c["grid"], color=c["text_muted"], side="right",
                    tickfont=tf, tickcolor=c["text_muted"], showline=False),
    )
    fig.update_layout(**layout)
    return fig


def render_live_analysis():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"

    page_header("📡", "Análisis en Vivo", "Smart Money Concepts · Order Blocks · FVG · Liquidez")

    # ── Alerta económica ──────────────────────────────────────────────────
    hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=90)
    if hay_ev and ev_info:
        st.error(f"⚠️ **Evento de alto impacto en {ev_info['minutos_restantes']} min** — "
                 f"{ev_info['titulo']} ({ev_info['moneda']}) · {ev_info['hora_mx']} CDMX")

    # Próximos eventos
    proximos = obtener_proximos_eventos(3)
    if proximos:
        with st.expander("📰 Próximos eventos económicos", expanded=False):
            cols = st.columns(min(len(proximos), 3))
            for col, ev in zip(cols, proximos):
                imp_color = impacto_color(ev["impacto"], dark)
                col.markdown(f"""
                <div class="oram-card" style="padding:0.6rem 0.9rem;margin:0">
                    <div class="card-title">{ev['dia']} · {ev['hora_mx']} CDMX</div>
                    <div style="font-size:0.8rem;font-weight:700;color:{imp_color}">
                        {impacto_emoji(ev['impacto'])} {ev['titulo']}
                    </div>
                    <div class="card-sub">{ev['moneda']}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(
                f'<a href="{FOREX_FACTORY_URL}" target="_blank" '
                f'style="color:{c["accent"]};font-size:0.78rem">'
                f'🔗 Forex Factory →</a>',
                unsafe_allow_html=True)

    # ── Controles ─────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
    with col1:
        categoria = st.selectbox("Categoría", list(ACTIVOS_DEFAULT.keys()), key="cat_live", label_visibility="visible")
    with col2:
        ticker = st.selectbox("Activo", ACTIVOS_DEFAULT[categoria], key="ticker_live")
    with col3:
        tf = st.selectbox("Temporalidad", list(TIMEFRAME_LABELS.keys()),
                          format_func=lambda x: TIMEFRAME_LABELS[x], index=2, key="tf_live")
    with col4:
        capital = st.number_input("Capital USD", value=float(user.get("capital_inicial", 1000)),
                                   min_value=100.0, step=500.0, key="cap_live")
    with col5:
        riesgo_pct = st.number_input("Riesgo %", value=1.0, min_value=0.1, max_value=5.0,
                                      step=0.1, key="rsk_live")

    actualizar = st.button("🔄 Actualizar análisis", width='stretch')

    # ── Datos ─────────────────────────────────────────────────────────────
    theme_key = get_theme()
    cache_key  = f"df_{ticker}_{tf}_{theme_key}"
    if cache_key not in st.session_state or actualizar:
        with st.spinner(f"Descargando {ticker} ({TIMEFRAME_LABELS[tf]})..."):
            df, status_msg = obtener_datos(ticker, tf)
            st.session_state[cache_key] = (df, status_msg)
    else:
        df, status_msg = st.session_state[cache_key]

    if   "✅" in status_msg: st.success(status_msg)
    elif "⚠️" in status_msg: st.warning(status_msg)
    else:                     st.error(status_msg)

    if df is None:
        st.info("No se pudieron obtener datos. Verifica el ticker o intenta más tarde.")
        return

    smc = analisis_completo(df, ticker)

    # ── LAYOUT PRINCIPAL: gráfica arriba completa, panel abajo ────────────
    # Gráfica a ancho completo
    st.plotly_chart(_grafica_velas(df, ticker, smc), width='stretch')

    # Panel de análisis debajo en 4 columnas
    precio  = smc.get("precio", 0)
    atr     = smc.get("atr", 0)
    rsi     = smc.get("rsi")
    est     = smc.get("estructura", {})
    conf    = smc.get("confluencia", {})
    dir_    = est.get("direccion", "neutral")
    tipo    = est.get("tipo", "Sin señal")
    confianza = conf.get("confianza", 0)
    factores  = conf.get("factores", [])

    st.divider()

    # Fila de métricas rápidas
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Precio", f"{precio:.5f}")
    m2.metric("ATR", f"{atr:.5f}")
    m3.metric("RSI", f"{rsi:.1f}" if rsi else "—",
               delta="Sobrecomprado" if rsi and rsi>70 else "Sobrevendido" if rsi and rsi<30 else "Neutral")
    m4.metric("Señal", tipo if tipo != "Sin señal" else "Rango")
    m5.metric("Confianza", f"{confianza:.0f}%")

    st.markdown("")

    # Panel analítico en 3 columnas
    col_senal, col_niveles, col_riesgo = st.columns([2, 2, 1])

    with col_senal:
        st.markdown(signal_box(tipo, est.get("descripcion",""), confianza), unsafe_allow_html=True)

        # Recomendación directa
        if "Alcista" in tipo or "LONG" in tipo:
            st.success("✅ **SEÑAL: COMPRA (LONG)**\nBusca entrada en OB o FVG alcista.")
        elif "Bajista" in tipo or "SHORT" in tipo:
            st.error("❌ **SEÑAL: VENTA (SHORT)**\nBusca entrada en OB o FVG bajista.")
        else:
            st.warning("⚠️ **ESPERA / RANGO**\nSin tendencia clara definida.")

        # Confluencias
        if factores:
            st.markdown(f"""
            <div class="oram-card oram-card-blue" style="margin-top:0.5rem">
                <div class="card-title">Confluencias ({conf.get('score',0)}/{conf.get('max',8)})</div>
                {"".join([f'<div class="card-sub">✓ {f}</div>' for f in factores])}
            </div>
            """, unsafe_allow_html=True)

    with col_niveles:
        # Order Blocks
        obs = smc.get("order_blocks", [])
        fvgs = smc.get("fvgs", [])
        liq  = smc.get("liquidez", {})

        st.markdown("**🧱 Order Blocks**")
        if obs:
            for ob in obs[:4]:
                badge = "badge-ob-bull" if ob.tipo=="OB_alcista" else "badge-ob-bear"
                label = "OB↑" if ob.tipo=="OB_alcista" else "OB↓"
                st.markdown(
                    f'<span class="level-badge {badge}">{label} {ob.precio_bot:.5f}–{ob.precio_top:.5f}</span>',
                    unsafe_allow_html=True)
        else:
            st.caption("Sin OBs detectados.")

        st.markdown("**⚡ Fair Value Gaps**")
        if fvgs:
            for fvg in fvgs[:4]:
                badge = "badge-fvg-bull" if fvg.tipo=="FVG_alcista" else "badge-fvg-bear"
                label = "FVG↑" if fvg.tipo=="FVG_alcista" else "FVG↓"
                st.markdown(
                    f'<span class="level-badge {badge}">{label} {fvg.precio_bot:.5f}–{fvg.precio_top:.5f}</span>',
                    unsafe_allow_html=True)
        else:
            st.caption("Sin FVGs activos.")

        st.markdown("**💧 Zonas de Liquidez**")
        for lvl in liq.get("resistance_levels",[])[:2]:
            st.markdown(f'<span class="level-badge badge-ob-bear">Res {lvl:.5f}</span>', unsafe_allow_html=True)
        for lvl in liq.get("support_levels",[])[:2]:
            st.markdown(f'<span class="level-badge badge-ob-bull">Sop {lvl:.5f}</span>', unsafe_allow_html=True)
        if liq.get("equal_highs"):
            st.markdown('<span class="level-badge badge-fvg-bear">⚠️ Equal Highs</span>', unsafe_allow_html=True)
        if liq.get("equal_lows"):
            st.markdown('<span class="level-badge badge-fvg-bull">⚠️ Equal Lows</span>', unsafe_allow_html=True)

    with col_riesgo:
        sl_s = smc.get("sl_sugerido", 0)
        tp_s = smc.get("tp_sugerido", 0)
        if sl_s and tp_s:
            st.markdown(f"""
            <div class="oram-card oram-card-blue">
                <div class="card-title">SL / TP sugeridos</div>
                <div class="card-sub">🟢 TP: <b>{tp_s:.5f}</b></div>
                <div class="card-sub">🔴 SL: <b>{sl_s:.5f}</b></div>
            </div>
            """, unsafe_allow_html=True)

            risk = calcular_riesgo(precio, sl_s, tp_s, capital, riesgo_pct)
            if risk:
                st.markdown(f"""
                <div class="oram-card oram-card-gold">
                    <div class="card-title">Gestión de Riesgo</div>
                    <div class="card-sub">Riesgo: <b>${risk['riesgo_usd']}</b></div>
                    <div class="card-sub">RR: <b>{risk['rr']}:1</b></div>
                    <div class="card-sub">Ganancia pot: <b>${risk['ganancia_pot']}</b></div>
                    <div class="card-sub">Lote: <b>{risk['lot_size']}</b></div>
                </div>
                """, unsafe_allow_html=True)
