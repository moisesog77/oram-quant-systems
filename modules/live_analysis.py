"""
modules/live_analysis.py — ORAM Quant Systems — Análisis SMC en Vivo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<<<<<<< HEAD
Ejecuta el motor SMC completo sobre datos de yfinance en tiempo real.

Cambios v2:
  · Banner de noticias/eventos superior siempre visible (expandido por defecto)
  · Selectbox / dropdowns: solo selección, sin escritura; colores correctos en ambos temas
  · Capital y Riesgo: botones -/+ premium + edición manual
  · Gráficas con espaciado delimitado y aspecto premium
=======
v3 — fixes:
  · Plotly annotation: sin bgcolor (ValuerError corregido)
  · Capital / Riesgo: st.number_input nativo (mismo aspecto premium que login)
  · Sin HTML stepper duplicado
  · Banner de noticias siempre visible
  · Gráficas con paneles delimitados y espaciado
>>>>>>> 612939e (ORAM Quant Systems)
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
<<<<<<< HEAD
    c   = get_colors()
    dark = get_theme() == "dark"

    # Colores adaptativos al tema
    subplot_title_color = c["text_muted"]
    panel_bg   = c["plot_bg"]
=======
    c    = get_colors()
    dark = get_theme() == "dark"

>>>>>>> 612939e (ORAM Quant Systems)
    grid_color = c["grid"]

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
<<<<<<< HEAD
        vertical_spacing=0.06,          # más espacio entre paneles
=======
        vertical_spacing=0.06,
>>>>>>> 612939e (ORAM Quant Systems)
        subplot_titles=["", "RSI (14)", "MACD"],
    )

    # Velas
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name=ticker,
        increasing_line_color=c["green"], decreasing_line_color=c["red"],
        increasing_fillcolor="rgba(34,197,94,0.7)",
        decreasing_fillcolor="rgba(239,68,68,0.7)",
        whiskerwidth=0.3,
    ), row=1, col=1)

    # EMAs
    for col_name, color, label in [
        ("EMA20",  c["accent2"], "EMA20"),
        ("EMA50",  c["accent"],  "EMA50"),
        ("EMA200", c["purple"],  "EMA200"),
    ]:
        if col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_name],
                line=dict(color=color, width=1.3),
                name=label, opacity=0.90,
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
        fc = "rgba(34,197,94,0.12)" if ob.tipo == "OB_alcista" else "rgba(239,68,68,0.12)"
        lc = c["green"] if ob.tipo == "OB_alcista" else c["red"]
        fig.add_hrect(
            y0=ob.precio_bot, y1=ob.precio_top, fillcolor=fc,
            line=dict(color=lc, width=1, dash="dot"),
            annotation_text="OB↑" if ob.tipo == "OB_alcista" else "OB↓",
            annotation_font_size=9, annotation_font_color=lc,
            row=1, col=1,
        )

    # FVGs
    for fvg in smc.get("fvgs", [])[:2]:
        fc = "rgba(61,155,233,0.10)" if fvg.tipo == "FVG_alcista" else "rgba(201,162,39,0.10)"
        lc = c["accent2"] if fvg.tipo == "FVG_alcista" else c["accent"]
        fig.add_hrect(
            y0=fvg.precio_bot, y1=fvg.precio_top, fillcolor=fc,
            line=dict(color=lc, width=1, dash="dot"),
            annotation_text="FVG", annotation_font_size=8, annotation_font_color=lc,
            row=1, col=1,
        )

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
        for lvl, col_ in [(70, "rgba(239,68,68,0.5)"), (30, "rgba(34,197,94,0.5)"), (50, "rgba(107,127,153,0.3)")]:
            fig.add_hline(y=lvl, line=dict(color=col_, width=1, dash="dot"), row=2, col=1)

    # MACD
    if "MACD" in df.columns:
        hist = df["MACD_hist"]
        fig.add_trace(go.Bar(
            x=df.index, y=hist,
            marker_color=[c["green"] if v >= 0 else c["red"] for v in hist],
            name="Hist", showlegend=False, opacity=0.7,
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD"],
            line=dict(color=c["accent"], width=1.2), name="MACD", showlegend=False,
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_signal"],
            line=dict(color=c["purple"], width=1.2), name="Signal", showlegend=False,
        ), row=3, col=1)

<<<<<<< HEAD
    tf_font = dict(color=c["text_muted"], size=9, family="JetBrains Mono")
    layout  = get_plot_layout(height=720)

    # Subtítulos con color del tema
    for ann in fig.layout.annotations:
        ann.update(font=dict(color=c["text_muted"], size=10, family="JetBrains Mono"),
                   bgcolor="transparent")

    # Paneles con fondo y borde separado
    panel_border = dict(showline=True, linewidth=1, linecolor=c["border"], mirror=False)

    layout.update(
        # Panel 1 — Velas
        xaxis =dict(gridcolor=grid_color, color=c["text_muted"],
                    tickfont=tf_font, tickcolor=c["text_muted"],
                    showline=False, zeroline=False,
                    rangeslider=dict(visible=False)),
        yaxis =dict(gridcolor=grid_color, color=c["text_muted"], side="right",
                    tickfont=tf_font, tickcolor=c["text_muted"],
                    showline=False, zeroline=False,
                    domain=[0.44, 1.0]),

        # Panel 2 — RSI
        xaxis2=dict(gridcolor=grid_color, color=c["text_muted"],
                    tickfont=tf_font, tickcolor=c["text_muted"],
                    showline=False, zeroline=False),
        yaxis2=dict(gridcolor=grid_color, color=c["text_muted"], side="right",
                    tickfont=tf_font, tickcolor=c["text_muted"],
                    range=[0,100], showline=False, zeroline=False,
                    domain=[0.225, 0.41]),

        # Panel 3 — MACD
        xaxis3=dict(gridcolor=grid_color, color=c["text_muted"],
                    tickfont=tf_font, tickcolor=c["text_muted"],
                    showline=False, zeroline=False),
        yaxis3=dict(gridcolor=grid_color, color=c["text_muted"], side="right",
                    tickfont=tf_font, tickcolor=c["text_muted"],
                    showline=False, zeroline=False,
                    domain=[0.0, 0.205]),

        # Márgenes amplios para separar paneles visualmente
        margin=dict(l=12, r=72, t=28, b=36),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
            font=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
=======
    # ── Subtítulos de paneles (sin bgcolor — causa ValueError) ────────────
    tf_font = dict(color=c["text_muted"], size=10, family="JetBrains Mono")
    for ann in fig.layout.annotations:
        ann.update(font=tf_font)   # solo font, sin bgcolor ni bordercolor

    layout = get_plot_layout(height=740)
    layout.update(
        # Panel velas
        xaxis=dict(gridcolor=grid_color, color=c["text_muted"],
                   tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                   showline=False, zeroline=False,
                   rangeslider=dict(visible=False)),
        yaxis=dict(gridcolor=grid_color, color=c["text_muted"], side="right",
                   tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                   showline=False, zeroline=False),

        # Panel RSI
        xaxis2=dict(gridcolor=grid_color, color=c["text_muted"],
                    tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                    showline=False, zeroline=False),
        yaxis2=dict(gridcolor=grid_color, color=c["text_muted"], side="right",
                    tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                    range=[0, 100], showline=False, zeroline=False),

        # Panel MACD
        xaxis3=dict(gridcolor=grid_color, color=c["text_muted"],
                    tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                    showline=False, zeroline=False),
        yaxis3=dict(gridcolor=grid_color, color=c["text_muted"], side="right",
                    tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                    showline=False, zeroline=False),

        margin=dict(l=12, r=72, t=32, b=36),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
            font=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
>>>>>>> 612939e (ORAM Quant Systems)
        ),
        # Líneas divisoras entre paneles
        shapes=[
            dict(type="line", xref="paper", x0=0, x1=1,
<<<<<<< HEAD
                 yref="paper", y0=0.42, y1=0.42,
                 line=dict(color=c["border2"], width=1, dash="dot")),
            dict(type="line", xref="paper", x0=0, x1=1,
                 yref="paper", y0=0.215, y1=0.215,
=======
                 yref="paper", y0=0.405, y1=0.405,
                 line=dict(color=c["border2"], width=1, dash="dot")),
            dict(type="line", xref="paper", x0=0, x1=1,
                 yref="paper", y0=0.205, y1=0.205,
>>>>>>> 612939e (ORAM Quant Systems)
                 line=dict(color=c["border2"], width=1, dash="dot")),
        ],
    )
    fig.update_layout(**layout)
    return fig


def _render_news_banner(dark: bool):
<<<<<<< HEAD
    """Banner superior con noticias económicas — siempre visible, aspecto premium."""
=======
    """Banner superior con noticias económicas — siempre visible."""
>>>>>>> 612939e (ORAM Quant Systems)
    c = get_colors()

    hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=90)
    proximos = obtener_proximos_eventos(5)

    if hay_ev and ev_info:
        st.markdown(f"""
        <div style="
<<<<<<< HEAD
            background: {'rgba(239,68,68,0.12)' if dark else 'rgba(200,30,30,0.07)'};
            border: 1.5px solid {'rgba(239,68,68,0.55)' if dark else 'rgba(200,30,30,0.40)'};
            border-radius: 10px; padding: 0.65rem 1.1rem; margin-bottom: 0.6rem;
            display: flex; align-items: center; gap: 0.75rem;
=======
            background:{'rgba(239,68,68,0.12)' if dark else 'rgba(200,30,30,0.07)'};
            border:1.5px solid {'rgba(239,68,68,0.55)' if dark else 'rgba(200,30,30,0.40)'};
            border-radius:10px;padding:0.65rem 1.1rem;margin-bottom:0.6rem;
            display:flex;align-items:center;gap:0.75rem;
>>>>>>> 612939e (ORAM Quant Systems)
        ">
            <span style="font-size:1.25rem">⚠️</span>
            <div>
                <span style="color:{'#f87171' if dark else '#c81e1e'};font-weight:700;
                    font-family:'Space Grotesk',sans-serif;font-size:0.9rem;">
                    Evento de alto impacto en {ev_info['minutos_restantes']} min
                </span>
                <span style="color:{c['text_muted']};font-size:0.82rem;margin-left:0.5rem;">
                    — {ev_info['titulo']} ({ev_info['moneda']}) · {ev_info['hora_mx']} CDMX
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if not proximos:
        return

<<<<<<< HEAD
    st.markdown(f"""
    <div style="
        background: {c['bg_card']};
        border: 1px solid {c['border']};
        border-left: 3px solid {c['accent2']};
        border-radius: 10px; padding: 0.75rem 1.1rem 0.65rem 1.1rem;
        margin-bottom: 1rem;
    ">
        <div style="
            font-family:'JetBrains Mono',monospace;
            font-size:0.60rem;text-transform:uppercase;letter-spacing:2.5px;
            color:{c['text_muted']};margin-bottom:0.55rem;
        ">📰 &nbsp;Próximos eventos de mercado</div>
        <div style="display:flex;gap:0.6rem;flex-wrap:wrap;align-items:stretch;">
    """, unsafe_allow_html=True)

    for ev in proximos:
        imp_color = impacto_color(ev["impacto"], dark)
        imp_bg = (
            "rgba(239,68,68,0.10)"   if ev["impacto"]=="High"   else
            "rgba(201,162,39,0.08)"  if ev["impacto"]=="Medium" else
            "rgba(107,127,153,0.07)"
        )
        imp_bg_light = (
            "rgba(200,30,30,0.07)"   if ev["impacto"]=="High"   else
            "rgba(154,117,16,0.06)"  if ev["impacto"]=="Medium" else
            "rgba(80,100,120,0.05)"
        )
        st.markdown(f"""
        <div style="
            flex:1;min-width:150px;max-width:240px;
            background:{imp_bg if dark else imp_bg_light};
            border:1px solid {imp_color}33;
            border-radius:8px;padding:0.5rem 0.75rem;
        ">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
                color:{c['text_muted']};margin-bottom:0.2rem;">
=======
    cards_html = ""
    for ev in proximos:
        imp_color = impacto_color(ev["impacto"], dark)
        imp_bg = (
            "rgba(239,68,68,0.10)"  if ev["impacto"] == "High"   else
            "rgba(201,162,39,0.08)" if ev["impacto"] == "Medium" else
            "rgba(107,127,153,0.07)"
        )
        imp_bg_l = (
            "rgba(200,30,30,0.07)"  if ev["impacto"] == "High"   else
            "rgba(154,117,16,0.06)" if ev["impacto"] == "Medium" else
            "rgba(80,100,120,0.05)"
        )
        cards_html += f"""
        <div style="flex:1;min-width:148px;max-width:230px;
            background:{imp_bg if dark else imp_bg_l};
            border:1px solid {imp_color}33;border-radius:8px;padding:0.5rem 0.75rem;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.60rem;
                color:{c['text_muted']};margin-bottom:0.18rem;">
>>>>>>> 612939e (ORAM Quant Systems)
                {ev['dia']} · {ev['hora_mx']} CDMX
            </div>
            <div style="font-size:0.78rem;font-weight:700;color:{imp_color};
                font-family:'Inter',sans-serif;line-height:1.3;">
                {impacto_emoji(ev['impacto'])} {ev['titulo']}
            </div>
<<<<<<< HEAD
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;
                color:{c['text_muted']};margin-top:0.15rem;">
                {ev['moneda']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
=======
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.63rem;
                color:{c['text_muted']};margin-top:0.12rem;">{ev['moneda']}</div>
        </div>"""

    st.markdown(f"""
    <div style="background:{c['bg_card']};border:1px solid {c['border']};
        border-left:3px solid {c['accent2']};border-radius:10px;
        padding:0.75rem 1.1rem 0.65rem 1.1rem;margin-bottom:1rem;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.60rem;
            text-transform:uppercase;letter-spacing:2.5px;
            color:{c['text_muted']};margin-bottom:0.5rem;">
            📰 &nbsp;Próximos eventos de mercado
        </div>
        <div style="display:flex;gap:0.55rem;flex-wrap:wrap;">
            {cards_html}
>>>>>>> 612939e (ORAM Quant Systems)
        </div>
        <div style="margin-top:0.5rem;">
            <a href="{FOREX_FACTORY_URL}" target="_blank"
               style="color:{c['accent2']};font-family:'JetBrains Mono',monospace;
<<<<<<< HEAD
               font-size:0.68rem;text-decoration:none;opacity:0.8;">
=======
               font-size:0.67rem;text-decoration:none;opacity:0.8;">
>>>>>>> 612939e (ORAM Quant Systems)
               🔗 Ver calendario completo en Forex Factory →
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)


<<<<<<< HEAD
def _stepper_css(c: dict, dark: bool) -> str:
    """CSS inline para los controles +/- premium de Capital y Riesgo."""
    btn_bg  = "rgba(255,255,255,0.06)" if dark else "rgba(0,0,0,0.05)"
    btn_hov = "rgba(34,197,94,0.18)"   if dark else "rgba(22,163,74,0.12)"
    return f"""
    <style>
    .oram-stepper-wrap {{
        display:flex;flex-direction:column;gap:2px;
    }}
    .oram-stepper-label {{
        font-family:'Inter',sans-serif;font-size:0.81rem;font-weight:500;
        color:{c['text']};margin-bottom:0.15rem;
    }}
    .oram-stepper {{
        display:flex;align-items:center;
        background:{c['input_bg']};
        border:2px solid {c['border2']};
        border-radius:10px;
        overflow:hidden;min-height:46px;
        transition:border-color .15s;
    }}
    .oram-stepper:focus-within {{
        border-color:{c['green']};
        box-shadow:0 0 0 3px rgba(34,197,94,0.15);
    }}
    .oram-stepper input {{
        flex:1;background:transparent;border:none;outline:none;
        font-family:'Inter',sans-serif;font-size:0.93rem;
        color:{c['text']};padding:0 0.6rem;text-align:center;
        min-width:60px;height:46px;
        -moz-appearance:textfield;
    }}
    .oram-stepper input::-webkit-outer-spin-button,
    .oram-stepper input::-webkit-inner-spin-button {{ -webkit-appearance:none;margin:0; }}
    .oram-stepper button {{
        all:unset;cursor:pointer;
        width:40px;min-width:40px;height:46px;
        display:flex;align-items:center;justify-content:center;
        background:{btn_bg};
        font-size:1.15rem;font-weight:600;
        color:{c['text_muted']};
        border:none;transition:background .15s,color .15s;
        flex-shrink:0;
        user-select:none;
    }}
    .oram-stepper button:hover {{
        background:{btn_hov};
        color:{c['green']};
    }}
    .oram-stepper .sep {{
        width:1px;height:30px;background:{c['border']};flex-shrink:0;
    }}
    </style>
    """


=======
>>>>>>> 612939e (ORAM Quant Systems)
def render_live_analysis():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"

    page_header("📡", "Análisis en Vivo", "Smart Money Concepts · Order Blocks · FVG · Liquidez")

<<<<<<< HEAD
    # ── Banner de noticias económicas (siempre visible, no collapsible) ───
    _render_news_banner(dark)

    # ── Controles — selectboxes solo lectura + steppers premium ───────────
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1.5])

    with col1:
        categoria = st.selectbox(
            "Categoría", list(ACTIVOS_DEFAULT.keys()),
            key="cat_live", label_visibility="visible"
        )
    with col2:
        ticker = st.selectbox(
            "Activo", ACTIVOS_DEFAULT[categoria], key="ticker_live"
        )
    with col3:
        tf = st.selectbox(
            "Temporalidad", list(TIMEFRAME_LABELS.keys()),
            format_func=lambda x: TIMEFRAME_LABELS[x], index=2, key="tf_live"
        )

    # Capital — stepper premium
    with col4:
        # Inicializar estado
        if "cap_live_val" not in st.session_state:
            st.session_state["cap_live_val"] = float(user.get("capital_inicial", 1000))

        st.markdown(_stepper_css(c, dark), unsafe_allow_html=True)
        st.markdown('<div class="oram-stepper-label">Capital USD</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="oram-stepper" id="cap-stepper">
            <button onclick="(function(){{
                var inp=document.getElementById('cap_inp');
                var v=parseFloat(inp.value)||0;
                inp.value=Math.max(100,v-500).toFixed(2);
                inp.dispatchEvent(new Event('input',{{bubbles:true}}));
                inp.dispatchEvent(new Event('change',{{bubbles:true}}));
            }})()">−</button>
            <div class="sep"></div>
            <input id="cap_inp" type="number" min="100" step="500"
                value="{st.session_state['cap_live_val']:.2f}"
                oninput="window.__cap_val=this.value"
                style="color:{c['text']}">
            <div class="sep"></div>
            <button onclick="(function(){{
                var inp=document.getElementById('cap_inp');
                var v=parseFloat(inp.value)||0;
                inp.value=(v+500).toFixed(2);
                inp.dispatchEvent(new Event('input',{{bubbles:true}}));
                inp.dispatchEvent(new Event('change',{{bubbles:true}}));
            }})()">+</button>
        </div>
        """, unsafe_allow_html=True)
        capital = st.number_input(
            "Capital USD", value=float(user.get("capital_inicial", 1000)),
            min_value=100.0, step=500.0, key="cap_live",
            label_visibility="collapsed"
        )

    # Riesgo — stepper premium
    with col5:
        if "rsk_live_val" not in st.session_state:
            st.session_state["rsk_live_val"] = 1.0

        st.markdown('<div class="oram-stepper-label">Riesgo %</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="oram-stepper" id="rsk-stepper">
            <button onclick="(function(){{
                var inp=document.getElementById('rsk_inp');
                var v=parseFloat(inp.value)||0;
                inp.value=Math.max(0.1,(v-0.1)).toFixed(1);
                inp.dispatchEvent(new Event('input',{{bubbles:true}}));
                inp.dispatchEvent(new Event('change',{{bubbles:true}}));
            }})()">−</button>
            <div class="sep"></div>
            <input id="rsk_inp" type="number" min="0.1" max="5.0" step="0.1"
                value="{st.session_state['rsk_live_val']:.1f}"
                style="color:{c['text']}">
            <div class="sep"></div>
            <button onclick="(function(){{
                var inp=document.getElementById('rsk_inp');
                var v=parseFloat(inp.value)||0;
                inp.value=Math.min(5.0,(v+0.1)).toFixed(1);
                inp.dispatchEvent(new Event('input',{{bubbles:true}}));
                inp.dispatchEvent(new Event('change',{{bubbles:true}}));
            }})()">+</button>
        </div>
        """, unsafe_allow_html=True)
        riesgo_pct = st.number_input(
            "Riesgo %", value=1.0, min_value=0.1, max_value=5.0,
            step=0.1, key="rsk_live", label_visibility="collapsed"
=======
    # ── Banner de noticias (siempre visible) ──────────────────────────────
    _render_news_banner(dark)

    # ── Controles ─────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1.5])

    with col1:
        categoria = st.selectbox(
            "Categoría", list(ACTIVOS_DEFAULT.keys()), key="cat_live"
        )
    with col2:
        ticker = st.selectbox(
            "Activo", ACTIVOS_DEFAULT[categoria], key="ticker_live"
        )
    with col3:
        tf = st.selectbox(
            "Temporalidad", list(TIMEFRAME_LABELS.keys()),
            format_func=lambda x: TIMEFRAME_LABELS[x], index=2, key="tf_live"
        )
    with col4:
        # st.number_input nativo — hereda el CSS premium de styles.py
        capital = st.number_input(
            "Capital USD",
            value=float(user.get("capital_inicial", 1000)),
            min_value=100.0,
            step=500.0,
            key="cap_live",
        )
    with col5:
        riesgo_pct = st.number_input(
            "Riesgo %",
            value=1.0,
            min_value=0.1,
            max_value=5.0,
            step=0.1,
            key="rsk_live",
>>>>>>> 612939e (ORAM Quant Systems)
        )

    actualizar = st.button("🔄 Actualizar análisis", key="btn_actualizar_live")

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

<<<<<<< HEAD
    # ── Gráfica premium con paneles delimitados ───────────────────────────
=======
    # ── Gráfica envuelta en tarjeta premium ───────────────────────────────
>>>>>>> 612939e (ORAM Quant Systems)
    st.markdown(f"""
    <div style="
        background:{c['bg_card']};
        border:1px solid {c['border']};
        border-radius:14px;
<<<<<<< HEAD
        padding:1rem 0.5rem 0.75rem 0.5rem;
=======
        padding:1rem 0.4rem 0.6rem 0.4rem;
>>>>>>> 612939e (ORAM Quant Systems)
        margin-bottom:1.25rem;
        box-shadow:{c['shadow']};
    ">
    """, unsafe_allow_html=True)
    st.plotly_chart(_grafica_velas(df, ticker, smc), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

<<<<<<< HEAD
    # ── Panel de análisis ────────────────────────────────────────────────
    precio  = smc.get("precio", 0)
    atr     = smc.get("atr", 0)
    rsi     = smc.get("rsi")
    est     = smc.get("estructura", {})
    conf    = smc.get("confluencia", {})
    dir_    = est.get("direccion", "neutral")
    tipo    = est.get("tipo", "Sin señal")
=======
    # ── Panel de análisis ─────────────────────────────────────────────────
    precio    = smc.get("precio", 0)
    atr       = smc.get("atr", 0)
    rsi       = smc.get("rsi")
    est       = smc.get("estructura", {})
    conf      = smc.get("confluencia", {})
    tipo      = est.get("tipo", "Sin señal")
>>>>>>> 612939e (ORAM Quant Systems)
    confianza = conf.get("confianza", 0)
    factores  = conf.get("factores", [])

    st.divider()

<<<<<<< HEAD
    # Métricas rápidas
=======
>>>>>>> 612939e (ORAM Quant Systems)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Precio",    f"{precio:.5f}")
    m2.metric("ATR",       f"{atr:.5f}")
    m3.metric("RSI",       f"{rsi:.1f}" if rsi else "—",
<<<<<<< HEAD
               delta="Sobrecomprado" if rsi and rsi>70 else "Sobrevendido" if rsi and rsi<30 else "Neutral")
=======
               delta="Sobrecomprado" if rsi and rsi > 70 else "Sobrevendido" if rsi and rsi < 30 else "Neutral")
>>>>>>> 612939e (ORAM Quant Systems)
    m4.metric("Señal",     tipo if tipo != "Sin señal" else "Rango")
    m5.metric("Confianza", f"{confianza:.0f}%")

    st.markdown("")

    col_senal, col_niveles, col_riesgo = st.columns([2, 2, 1])

    with col_senal:
<<<<<<< HEAD
        st.markdown(signal_box(tipo, est.get("descripcion",""), confianza), unsafe_allow_html=True)

=======
        st.markdown(signal_box(tipo, est.get("descripcion", ""), confianza), unsafe_allow_html=True)
>>>>>>> 612939e (ORAM Quant Systems)
        if "Alcista" in tipo or "LONG" in tipo:
            st.success("✅ **SEÑAL: COMPRA (LONG)**\nBusca entrada en OB o FVG alcista.")
        elif "Bajista" in tipo or "SHORT" in tipo:
            st.error("❌ **SEÑAL: VENTA (SHORT)**\nBusca entrada en OB o FVG bajista.")
        else:
            st.warning("⚠️ **ESPERA / RANGO**\nSin tendencia clara definida.")

        if factores:
            st.markdown(f"""
            <div class="oram-card oram-card-blue" style="margin-top:0.5rem">
                <div class="card-title">Confluencias ({conf.get('score',0)}/{conf.get('max',8)})</div>
                {"".join([f'<div class="card-sub">✓ {f}</div>' for f in factores])}
            </div>
            """, unsafe_allow_html=True)

    with col_niveles:
        obs  = smc.get("order_blocks", [])
        fvgs = smc.get("fvgs", [])
        liq  = smc.get("liquidez", {})

        st.markdown("**🧱 Order Blocks**")
        if obs:
            for ob in obs[:4]:
                badge = "badge-ob-bull" if ob.tipo == "OB_alcista" else "badge-ob-bear"
                label = "OB↑" if ob.tipo == "OB_alcista" else "OB↓"
                st.markdown(
                    f'<span class="level-badge {badge}">{label} {ob.precio_bot:.5f}–{ob.precio_top:.5f}</span>',
                    unsafe_allow_html=True)
        else:
            st.caption("Sin OBs detectados.")

        st.markdown("**⚡ Fair Value Gaps**")
        if fvgs:
            for fvg in fvgs[:4]:
                badge = "badge-fvg-bull" if fvg.tipo == "FVG_alcista" else "badge-fvg-bear"
                label = "FVG↑" if fvg.tipo == "FVG_alcista" else "FVG↓"
                st.markdown(
                    f'<span class="level-badge {badge}">{label} {fvg.precio_bot:.5f}–{fvg.precio_top:.5f}</span>',
                    unsafe_allow_html=True)
        else:
            st.caption("Sin FVGs activos.")

        st.markdown("**💧 Zonas de Liquidez**")
        for lvl in liq.get("resistance_levels", [])[:2]:
            st.markdown(f'<span class="level-badge badge-ob-bear">Res {lvl:.5f}</span>', unsafe_allow_html=True)
        for lvl in liq.get("support_levels", [])[:2]:
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
