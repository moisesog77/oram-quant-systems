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
from ui.styles import get_colors, page_header, oram_notify, oram_bienvenida, get_theme


def _inject_wl_css(dark: bool, c: dict):
    input_bg   = "#080d14"  if dark else "#f0f4f8"
    input_text = "#c8d8ea"  if dark else "#1a2b3c"
    input_bdr  = "#2a4560"  if dark else "#94a3b8"
    label_col  = "#4a6a84"  if dark else "#6b7f94"
    focus_clr  = "#22c55e"
    focus_glow = "rgba(34,197,94,0.18)" if dark else "rgba(34,197,94,0.14)"
    eye_col    = "#64748b"

    st.markdown(f"""
<style>
/* ══ LABELS ══════════════════════════════════════════════════════════════ */
.stSelectbox label, .stTextInput label {{
    color: {label_col} !important;
    font-family: Inter, sans-serif !important;
    font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
    margin-bottom: 0.3rem !important; display: block !important;
}}

/* ══ SELECTBOX ════════════════════════════════════════════════════════════ */
.stSelectbox, .stSelectbox > div, .stSelectbox > div > div {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
}}
.stSelectbox [data-baseweb="select"] {{ cursor: pointer !important; }}
.stSelectbox [data-baseweb="select"] > div {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    min-height: 46px !important;
    display: flex !important; align-items: center !important;
    cursor: pointer !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    padding: 0 0.75rem !important;
}}
.stSelectbox [data-baseweb="select"] > div:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
.stSelectbox [data-baseweb="select"] span {{
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important;
    font-size: 0.93rem !important; pointer-events: none !important;
}}
.stSelectbox [data-baseweb="select"] svg {{
    fill: {eye_col} !important; opacity: 0.7 !important;
    flex-shrink: 0 !important; pointer-events: none !important;
}}
.stSelectbox [data-baseweb="select"] input {{
    position: absolute !important; width: 1px !important;
    height: 1px !important; opacity: 0 !important;
    pointer-events: none !important; caret-color: transparent !important;
    user-select: none !important; border: none !important;
}}

/* ══ TEXT INPUT (Alias) ═══════════════════════════════════════════════════ */
.stTextInput > div {{
    border: none !important; background: transparent !important;
    box-shadow: none !important; padding: 0 !important; margin: 0 !important;
}}
.stTextInput > div > div {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    display: flex !important; align-items: center !important;
    padding: 0 !important;
}}
.stTextInput > div > div:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
.stTextInput input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; height: 46px !important; width: 100% !important;
}}
[data-testid="stTextInputRootElement"] {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    display: flex !important; align-items: center !important;
}}
[data-testid="stTextInputRootElement"]:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}

/* ══ BOTÓN AGREGAR ════════════════════════════════════════════════════════ */
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important; border-radius: 10px !important;
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    font-family: Inter, sans-serif !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
    padding: 0.72rem 1.4rem !important;
    box-shadow: 0 4px 14px 0 rgba(16,185,129,0.39) !important;
    transition: box-shadow .25s ease, transform .18s ease !important;
    cursor: pointer !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 22px 0 rgba(16,185,129,0.58) !important;
    transform: translateY(-1px) !important;
}}
[data-testid="stBaseButton-primary"]:active {{
    box-shadow: 0 2px 8px 0 rgba(16,185,129,0.30) !important;
    transform: scale(0.98) !important;
}}
</style>
""", unsafe_allow_html=True)


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
    _inject_wl_css(dark, c)

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

                # Sparkline
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
