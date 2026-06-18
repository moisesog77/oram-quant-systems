"""
modules/watchlist.py — ORAM Quant Systems — Watchlist Personalizada
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lista de activos favoritos del usuario con análisis SMC rápido.

Funcionalidades:
  · Agregar activos por categoría (Forex, Cripto, Índices, Commodities)
  · Mini-gráfica sparkline (últimas 50 velas, Plotly)
  · Señal SMC actual, confianza, precio, RSI, ATR, SL/TP sugeridos
  · Botón "Quitar" con overlay de confirmación premium

Los datos se obtienen de yfinance (obtener_datos) en cada render;
el spinner indica la carga por activo.
"""
import streamlit as st
import plotly.graph_objects as go
from database.db import obtener_watchlist, agregar_watchlist, eliminar_watchlist
from utils.market_data import ACTIVOS_DEFAULT, obtener_datos
from utils.smc_engine import analisis_completo
from ui.styles import get_colors, page_header, oram_notify, oram_bienvenida, get_theme, inject_module_css



def _sparkline(df, c):
    """Mini gráfica de precio para watchlist."""
    df_tail = df.tail(50)
    close   = df_tail["Close"]
    color   = c["green"] if close.iloc[-1] >= close.iloc[0] else c["red"]
    fill    = "rgba(34,197,94,0.08)" if color == c["green"] else "rgba(239,68,68,0.08)"
    fig = go.Figure(go.Scatter(
        y=close, mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy", fillcolor=fill,
    ))
    fig.update_layout(
        height=60, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=c["plot_bg"],
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def render_watchlist():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"

    page_header("👁️", "Watchlist", "Monitoreo de activos · Precios en tiempo real · Señal rápida")
    inject_module_css(dark)

    # ── Agregar activo ─────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([2,2,2,1])
    with col1:
        cat    = st.selectbox("Categoría", list(ACTIVOS_DEFAULT.keys()), key="wl_cat")
    with col2:
        ticker = st.selectbox("Activo",    ACTIVOS_DEFAULT[cat],          key="wl_tk")
    with col3:
        alias  = st.text_input("Alias (opcional)", placeholder="ej: Cable, DXY...", key="wl_alias")
    with col4:
        st.markdown('<div style="margin-top:1.6rem"></div>', unsafe_allow_html=True)
        if st.button("➕ Agregar", width='stretch'):
            ok = agregar_watchlist(user["id"], ticker, alias)
            if ok:
                oram_bienvenida(
                    titulo        = "✅ Activo agregado",
                    subtitulo     = f"<b>{ticker}</b>{' — ' + alias if alias else ''} ha sido añadido a tu watchlist.",
                    spinner_label = "Actualizando watchlist…",
                    delay         = 1.8,
                )
            else:
                oram_notify("warning", f"⚠️ **{ticker}** ya está en tu watchlist", toast=True)

    st.divider()

    # ── Watchlist actual ───────────────────────────────────────────────────
    wl = obtener_watchlist(user["id"])
    if not wl:
        st.markdown(f"""
        <div class="oram-card" style="text-align:center;padding:2.5rem">
            <div style="font-size:2rem;margin-bottom:0.5rem">👁️</div>
            <div class="card-value" style="font-size:1rem">Tu watchlist está vacía</div>
            <div class="card-sub">Agrega activos arriba para monitorearlos aquí</div>
        </div>
        """, unsafe_allow_html=True)
        return

    tf_watch = st.selectbox("Temporalidad", ["15m","1h","4h"], index=1, key="wl_tf",
                             help="Timeframe para el análisis SMC rápido")

    st.markdown(f"**{len(wl)} activos monitoreados**")

    # Renderizar en grid de 2 columnas
    for i in range(0, len(wl), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(wl):
                break
            item = wl[i + j]
            tk   = item["ticker"]
            al   = item["alias"] or tk

            with col:
                with st.spinner(f"Cargando {tk}..."):
                    df, status = obtener_datos(tk, tf_watch)

                if df is None:
                    st.markdown(f"""
                    <div class="oram-card oram-card-red" style="padding:0.8rem 1rem">
                        <div class="card-title">{al}</div>
                        <div class="card-sub" style="color:{c['red']}">Sin datos — {status[:50]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    continue

                smc    = analisis_completo(df, tk)
                precio = smc.get("precio", 0)
                rsi    = smc.get("rsi", 0)
                dir_   = smc.get("estructura",{}).get("direccion","neutral")
                conf   = smc.get("confluencia",{}).get("confianza",0)
                tipo   = smc.get("estructura",{}).get("tipo","?")
                atr    = smc.get("atr",0)

                # Variación
                close_series = df["Close"]
                var_pct = (close_series.iloc[-1] / close_series.iloc[-2] - 1) * 100 if len(close_series) > 1 else 0
                var_color = c["green"] if var_pct >= 0 else c["red"]
                var_sign  = "▲" if var_pct >= 0 else "▼"

                # Detectar mercado cerrado: sin variación + última vela > 24h
                import pandas as _pd
                mercado_cerrado = False
                try:
                    ultima_vela = df.index[-1]
                    if hasattr(ultima_vela, 'tzinfo') and ultima_vela.tzinfo is not None:
                        ahora = _pd.Timestamp.utcnow().tz_localize(None)
                        ultima_naive = ultima_vela.tz_convert("UTC").tz_localize(None)
                    else:
                        ahora = _pd.Timestamp.utcnow().tz_localize(None)
                        ultima_naive = ultima_vela
                    horas_sin_datos = (ahora - ultima_naive).total_seconds() / 3600
                    mercado_cerrado = horas_sin_datos > 6
                except Exception:
                    pass

                dir_emoji = "🟢" if dir_=="LONG" else "🔴" if dir_=="SHORT" else "⚪"
                border_color = c["green"] if dir_=="LONG" else c["red"] if dir_=="SHORT" else c["border"]

                st.markdown(f"""
                <div class="oram-card" style="border-left:3px solid {border_color};padding:0.9rem 1.1rem">
                    <div style="display:flex;justify-content:space-between;align-items:start">
                        <div>
                            <div class="card-title">{al}</div>
                            <div style="font-family:'Space Grotesk',sans-serif;font-size:1.3rem;
                                        font-weight:700;color:{c['text_strong']};letter-spacing:-0.3px">
                                {precio:.5f}
                            </div>
                            <div style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                                        color:{var_color};margin-top:2px">
                                {var_sign} {abs(var_pct):.3f}%
                            </div>
                        </div>
                        <div style="text-align:right">
                            <div style="font-size:0.72rem;color:{c['text_muted']}">RSI</div>
                            <div style="font-family:'JetBrains Mono',monospace;font-size:1rem;
                                        font-weight:700;color:{'#ef4444' if rsi>70 else '#22c55e' if rsi<30 else c['accent2']}">
                                {rsi:.0f}
                            </div>
                        </div>
                    </div>
                    <div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid {c['border']};
                                display:flex;justify-content:space-between;align-items:center">
                        <div style="font-size:0.78rem;color:{c['text_muted']}">
                            {dir_emoji} <b style="color:{c['text']}">{tipo}</b>
                        </div>
                        <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:{c['text_muted']}">
                            Conf: <span style="color:{c['accent']};font-weight:700">{conf:.0f}%</span>
                            &nbsp;|&nbsp; ATR: {atr:.5f}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Sparkline o badge de mercado cerrado
                if mercado_cerrado:
                    bg_closed  = "#0c1219" if dark else "#f1f5f9"
                    bdr_closed = "#1b2a40" if dark else "#dde5ef"
                    txt_muted  = c["text_muted"]
                    st.markdown(f"""
                    <div style="background:{bg_closed};border:1px solid {bdr_closed};
                                border-radius:10px;padding:0.55rem 1rem;
                                display:flex;align-items:center;gap:0.6rem;
                                margin-bottom:0.25rem">
                        <span style="font-size:1rem">🔒</span>
                        <span style="font-family:Inter,sans-serif;font-size:0.78rem;
                                     color:{txt_muted};font-weight:500">
                            Mercado cerrado · Último precio hace
                            <b style="color:{c['text']}">{horas_sin_datos:.0f}h</b>
                            · Reabre el lunes
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    fig = _sparkline(df, c)
                    st.plotly_chart(fig, width='stretch', key=f"spark_{tk}_{i}{j}")

                # Botón eliminar
                if st.button(f"🗑️ Quitar {al}", key=f"rm_{tk}", width='stretch'):
                    eliminar_watchlist(user["id"], tk)
                    oram_bienvenida(
                        titulo        = "🗑️ Activo eliminado",
                        subtitulo     = f"<b>{al or tk}</b> ha sido eliminado de tu watchlist.",
                        spinner_label = "Actualizando watchlist…",
                        delay         = 1.5,
                    )
