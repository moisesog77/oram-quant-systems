"""
modules/live_analysis.py — ORAM Quant Systems — Análisis SMC en Vivo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v6 — fix definitivo:
  · Inputs con CSS idéntico al de auth.py (nth-child, baseweb, etc.)
  · Dropdown: CSS inyectado en window.parent.document via JS
    (única forma de estilizar portals fuera del iframe de Streamlit)
  · Noticias al tope con variables CSS del tema
  · Botón primary con glow verde
"""
import streamlit as st
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


def _inject_module_css(dark: bool, c: dict):
    """
    Inyecta CSS del módulo en dos partes:
    1. CSS inline (iframe) para inputs, noticias, gráfica, botón
    2. JS que inyecta CSS del dropdown en window.parent.document
       (única forma de estilizar portals Base Web fuera del iframe)
    """
    input_bg   = "#080d14"  if dark else "#f0f4f8"
    input_text = "#c8d8ea"  if dark else "#1a2b3c"
    input_ph   = "#3a5068"  if dark else "#9baab8"
    input_bdr  = "#2a4560"  if dark else "#94a3b8"
    label_col  = "#4a6a84"  if dark else "#6b7f94"
    focus_clr  = "#22c55e"
    focus_glow = "rgba(34,197,94,0.18)" if dark else "rgba(34,197,94,0.14)"
    eye_col    = "#64748b"
    bg_card    = c["bg_card"]
    border     = c["border"]
    border2    = c["border2"]
    text       = c["text"]
    text_muted = c["text_muted"]
    accent2    = c["accent2"]
    nav_hover  = c["nav_hover"]
    shadow_dr  = "0 8px 32px rgba(0,0,0,0.45)" if dark else "0 8px 24px rgba(0,0,0,0.12)"

    # ── 1. CSS inyectado en el iframe (inputs, noticias, gráfica) ─────────
    st.markdown(f"""
<style>
/* ══════════════════════════════════════════════════════════
   INPUTS — Idéntico a auth.py para coherencia visual
   ══════════════════════════════════════════════════════════ */

/* Labels de inputs */
.stSelectbox label,
.stNumberInput label {{
    color: {label_col} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
    margin-bottom: 0.3rem !important; display: block !important;
}}

/* ── SELECTBOX — igual al login ── */
.stSelectbox,
.stSelectbox > div,
.stSelectbox > div > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}
.stSelectbox [data-baseweb="select"] > div {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important;
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
    font-family: 'Inter', sans-serif !important;
    font-size: 0.93rem !important;
}}
.stSelectbox [data-baseweb="select"] svg {{
    fill: {eye_col} !important;
    opacity: 0.7 !important;
    flex-shrink: 0 !important;
}}
.stSelectbox [data-baseweb="select"] input {{
    background: transparent !important;
    color: {input_text} !important;
    caret-color: transparent !important;
    user-select: none !important;
    pointer-events: none !important;
    border: none !important;
    box-shadow: none !important;
}}

/* ── NUMBER INPUT — idéntico a auth.py ── */
[data-testid="stNumberInput"] {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
}}
[data-testid="stNumberInput"] > div:nth-child(1) {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2) {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important; display: flex !important;
    align-items: center !important; min-height: 46px !important;
    overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    padding: 0 !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2):focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
[data-testid="stNumberInput"] input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important; -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; flex: 1 !important;
    height: 46px !important; -moz-appearance: textfield !important;
}}
[data-testid="stNumberInput"] input::-webkit-outer-spin-button,
[data-testid="stNumberInput"] input::-webkit-inner-spin-button {{
    -webkit-appearance: none !important; margin: 0 !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2) > div:last-child {{
    display: flex !important; flex-direction: row !important;
    align-items: center !important; align-self: stretch !important;
    height: 100% !important; gap: 0 !important;
    background: transparent !important; border: none !important;
}}
[data-testid="stNumberInput-StepDown"],
[data-testid="stNumberInput-StepUp"] {{
    all: unset !important; box-sizing: border-box !important;
    display: flex !important; align-items: center !important;
    justify-content: center !important; align-self: stretch !important;
    width: 44px !important; min-width: 44px !important;
    height: 100% !important; min-height: 46px !important;
    flex-shrink: 0 !important; cursor: pointer !important;
    border-left: 1px solid {input_bdr} !important;
    background: transparent !important;
    opacity: 0.55 !important; transition: opacity .15s !important;
}}
[data-testid="stNumberInput-StepDown"]:hover,
[data-testid="stNumberInput-StepUp"]:hover {{ opacity: 1 !important; }}
[data-testid="stNumberInput-StepDown"] svg,
[data-testid="stNumberInput-StepUp"] svg {{
    width: 17px !important; height: 17px !important;
    fill: none !important; stroke: {eye_col} !important;
    stroke-width: 1.8 !important; pointer-events: none !important;
    display: block !important; flex-shrink: 0 !important;
}}
/* fantasma */
[data-testid="stNumberInput"] > input:last-child,
[data-testid="stNumberInput"] > div:last-child:not(:nth-child(2)),
[data-testid="stNumberInput"] > *:nth-child(n+3) {{
    display: none !important; visibility: hidden !important;
    height: 0 !important; margin: 0 !important;
    padding: 0 !important; border: none !important;
    opacity: 0 !important; position: absolute !important;
    pointer-events: none !important;
}}
[data-testid="InputInstructions"] {{
    display: none !important; visibility: hidden !important;
    height: 0 !important; margin: 0 !important;
}}

/* ══════════════════════════════════════════════════════════
   BOTÓN PRINCIPAL — glow verde institucional
   ══════════════════════════════════════════════════════════ */
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important; border-radius: 10px !important;
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
    padding: 0.72rem 1rem !important; width: 100% !important;
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
@keyframes oram-btn-confirm {{
    0%   {{ box-shadow: 0 4px 14px 0 rgba(16,185,129,0.39); }}
    30%  {{ box-shadow: 0 0 0 6px rgba(34,197,94,0.45), 0 4px 22px 0 rgba(16,185,129,0.70); }}
    70%  {{ box-shadow: 0 0 0 12px rgba(34,197,94,0.10), 0 4px 18px 0 rgba(16,185,129,0.50); }}
    100% {{ box-shadow: 0 4px 14px 0 rgba(16,185,129,0.39); }}
}}
.oram-btn-confirming {{
    animation: oram-btn-confirm 0.7s cubic-bezier(0.22,1,0.36,1) both !important;
}}

/* ── micro-spinner status ── */
@keyframes oram-micro-spin {{ to {{ transform: rotate(360deg); }} }}
.oram-micro-spinner {{
    width: 12px; height: 12px;
    border: 1.5px solid rgba(34,197,94,0.3);
    border-top-color: #22c55e;
    border-radius: 50%;
    animation: oram-micro-spin 0.65s linear infinite;
    display: inline-block; vertical-align: middle;
}}
#oram-btn-status {{
    display: inline-flex; align-items: center; gap: 0.45rem;
    font-family: 'JetBrains Mono', monospace; font-size: 0.70rem;
    letter-spacing: 1.2px; text-transform: uppercase;
    color: #22c55e; opacity: 0; transition: opacity 0.3s ease;
    padding-top: 0.65rem;
}}
#oram-btn-status.oram-visible {{ opacity: 1; }}

/* ══════════════════════════════════════════════════════════
   NOTICIAS — contenedor consistente con inputs
   ══════════════════════════════════════════════════════════ */
.oram-news-wrapper {{
    background: {bg_card};
    border: 1px solid {border};
    border-left: 3px solid {accent2};
    border-radius: 12px;
    padding: 0.85rem 1.2rem 0.75rem 1.2rem;
    margin-bottom: 1.25rem;
}}
.oram-news-label {{
    font-family: 'JetBrains Mono', monospace; font-size: 0.58rem;
    text-transform: uppercase; letter-spacing: 2.5px;
    color: {text_muted}; margin-bottom: 0.55rem;
}}
.oram-news-cards {{ display: flex; gap: 0.55rem; flex-wrap: wrap; }}
.oram-news-card {{
    flex: 1; min-width: 148px; max-width: 230px;
    border-radius: 8px; padding: 0.5rem 0.75rem;
    border: 1px solid transparent;
}}
.oram-news-link {{
    display: inline-block; margin-top: 0.5rem;
    font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
    text-decoration: none; opacity: 0.75; color: {accent2};
    transition: opacity 0.2s;
}}
.oram-news-link:hover {{ opacity: 1; }}
.oram-alert-high {{
    display: flex; align-items: center; gap: 0.75rem;
    border-radius: 10px; padding: 0.65rem 1.1rem; margin-bottom: 0.65rem;
}}

/* ══════════════════════════════════════════════════════════
   GRÁFICA — tarjeta con contorno uniforme
   ══════════════════════════════════════════════════════════ */
.oram-chart-card {{
    background: {bg_card};
    border: 1px solid #1f2937;
    border-radius: 14px;
    padding: 0.75rem 0.25rem 0.5rem 0.25rem;
    margin-bottom: 1.25rem;
    box-shadow: {c["shadow"]};
    overflow: hidden;
}}
</style>
""", unsafe_allow_html=True)

    # ── 2. JS: inyectar CSS del dropdown en window.parent.document ────────
    # Los portals de Base Web se montan FUERA del iframe de Streamlit.
    # El único CSS que llega al documento padre es el que inyecta este JS.
    st.markdown(f"""
<script>
(function() {{
    var ORAM_STYLE_ID = 'oram-parent-dropdown-css';

    function injectParentCSS() {{
        var doc = window.parent.document;
        if (doc.getElementById(ORAM_STYLE_ID)) return;

        var style = doc.createElement('style');
        style.id = ORAM_STYLE_ID;
        style.textContent = `
            /* ORAM — Dropdown portal (Base Web, fuera del iframe) */
            [data-baseweb="layer"],
            [data-baseweb="layer"] > * {{
                background-color: {bg_card} !important;
                color-scheme: {'dark' if dark else 'light'} !important;
            }}
            [data-baseweb="layer"] *,
            [data-baseweb="layer"] [data-baseweb="popover"],
            [data-baseweb="layer"] [data-baseweb="popover"] > *,
            [data-baseweb="layer"] [data-baseweb="menu"],
            [data-baseweb="layer"] [data-baseweb="menu"] *,
            [data-baseweb="layer"] [role="listbox"],
            [data-baseweb="layer"] [role="listbox"] *,
            [data-baseweb="layer"] ul,
            [data-baseweb="layer"] li,
            [data-baseweb="layer"] [role="option"] {{
                background-color: {bg_card} !important;
                color: {text} !important;
                border-color: {border} !important;
            }}
            [data-baseweb="layer"] [data-baseweb="popover"] > div,
            [data-baseweb="layer"] [role="listbox"] > div {{
                border-radius: 10px !important;
                border: 1px solid {border2} !important;
                box-shadow: {shadow_dr} !important;
                overflow: hidden !important;
            }}
            [data-baseweb="layer"] li:hover,
            [data-baseweb="layer"] [role="option"]:hover,
            [data-baseweb="layer"] [aria-selected="true"],
            [data-baseweb="layer"] [data-highlighted="true"] {{
                background-color: {nav_hover} !important;
                color: {text} !important;
            }}
            [data-baseweb="menu"] {{
                background: {bg_card} !important;
                border: 1px solid {border} !important;
                border-radius: 8px !important;
            }}
            [data-baseweb="menu"] li,
            [data-baseweb="menu"] [role="option"] {{
                background: {bg_card} !important;
                color: {text} !important;
            }}
            [data-baseweb="menu"] li:hover,
            [data-baseweb="menu"] [role="option"]:hover {{
                background: {nav_hover} !important;
            }}
        `;
        doc.head.appendChild(style);
    }}

    // Intentar inmediatamente
    try {{ injectParentCSS(); }} catch(e) {{}}

    // Re-intentar en cada apertura de dropdown (MutationObserver en parent)
    try {{
        var observer = new MutationObserver(function(mutations) {{
            mutations.forEach(function(m) {{
                m.addedNodes.forEach(function(node) {{
                    if (node.nodeType === 1 &&
                        (node.getAttribute && node.getAttribute('data-baseweb') === 'layer' ||
                         node.querySelector && node.querySelector('[data-baseweb="layer"]'))) {{
                        injectParentCSS();
                    }}
                }});
            }});
        }});
        observer.observe(window.parent.document.body, {{
            childList: true, subtree: true
        }});
    }} catch(e) {{}}

    // También inyectar el CSS del botón primary en parent (por si acaso)
    function injectBtnCSS() {{
        var doc = window.parent.document;
        var btnStyleId = 'oram-parent-btn-css';
        if (doc.getElementById(btnStyleId)) return;
        var s = doc.createElement('style');
        s.id = btnStyleId;
        s.textContent = `
            [data-testid="stBaseButton-primary"] {{
                box-shadow: 0 4px 14px 0 rgba(16,185,129,0.39) !important;
            }}
        `;
        doc.head.appendChild(s);
    }}
    try {{ injectBtnCSS(); }} catch(e) {{}}

    // Animación confirmación al clicar
    setTimeout(function() {{
        var btn = window.parent.document.querySelector(
            '[data-testid="stBaseButton-primary"]'
        );
        if (!btn || btn.dataset.oramBound) return;
        btn.dataset.oramBound = '1';
        btn.addEventListener('click', function() {{
            btn.classList.add('oram-btn-confirming');
            var status = document.getElementById('oram-btn-status');
            if (status) {{
                status.classList.add('oram-visible');
                setTimeout(function() {{ status.classList.remove('oram-visible'); }}, 2400);
            }}
            btn.addEventListener('animationend', function h() {{
                btn.classList.remove('oram-btn-confirming');
                btn.removeEventListener('animationend', h);
            }});
        }});
    }}, 800);
}})();
</script>
""", unsafe_allow_html=True)


def _grafica_velas(df, ticker, smc):
    c    = get_colors()
    dark = get_theme() == "dark"
    grid_color = c["grid"]

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.60, 0.20, 0.20],
        vertical_spacing=0.06,
        subplot_titles=["", "RSI (14)", "MACD"],
    )
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name=ticker,
        increasing_line_color=c["green"], decreasing_line_color=c["red"],
        increasing_fillcolor="rgba(34,197,94,0.7)",
        decreasing_fillcolor="rgba(239,68,68,0.7)",
        whiskerwidth=0.3,
    ), row=1, col=1)
    for col_name, color, label in [
        ("EMA20", c["accent2"], "EMA20"), ("EMA50", c["accent"], "EMA50"),
        ("EMA200", c["purple"], "EMA200"),
    ]:
        if col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_name],
                line=dict(color=color, width=1.3), name=label, opacity=0.90,
            ), row=1, col=1)
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
    for ob in smc.get("order_blocks", [])[:3]:
        fc = "rgba(34,197,94,0.12)" if ob.tipo == "OB_alcista" else "rgba(239,68,68,0.12)"
        lc = c["green"] if ob.tipo == "OB_alcista" else c["red"]
        fig.add_hrect(
            y0=ob.precio_bot, y1=ob.precio_top, fillcolor=fc,
            line=dict(color=lc, width=1, dash="dot"),
            annotation_text="OB↑" if ob.tipo == "OB_alcista" else "OB↓",
            annotation_font_size=9, annotation_font_color=lc, row=1, col=1,
        )
    for fvg in smc.get("fvgs", [])[:2]:
        fc = "rgba(61,155,233,0.10)" if fvg.tipo == "FVG_alcista" else "rgba(201,162,39,0.10)"
        lc = c["accent2"] if fvg.tipo == "FVG_alcista" else c["accent"]
        fig.add_hrect(
            y0=fvg.precio_bot, y1=fvg.precio_top, fillcolor=fc,
            line=dict(color=lc, width=1, dash="dot"),
            annotation_text="FVG", annotation_font_size=8, annotation_font_color=lc, row=1, col=1,
        )
    liq = smc.get("liquidez", {})
    for lvl in liq.get("resistance_levels", [])[:2]:
        fig.add_hline(y=lvl, line=dict(color="rgba(239,68,68,0.4)", width=1, dash="dash"), row=1, col=1)
    for lvl in liq.get("support_levels", [])[:2]:
        fig.add_hline(y=lvl, line=dict(color="rgba(34,197,94,0.4)", width=1, dash="dash"), row=1, col=1)
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"],
            line=dict(color=c["accent2"], width=1.5), name="RSI", showlegend=False,
        ), row=2, col=1)
        for lvl, col_ in [(70, "rgba(239,68,68,0.5)"), (30, "rgba(34,197,94,0.5)"), (50, "rgba(107,127,153,0.3)")]:
            fig.add_hline(y=lvl, line=dict(color=col_, width=1, dash="dot"), row=2, col=1)
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

    tf_font = dict(color=c["text_muted"], size=10, family="JetBrains Mono")
    for ann in fig.layout.annotations:
        ann.update(font=tf_font)

    layout = get_plot_layout(height=740)
    layout.update(
        xaxis=dict(gridcolor=grid_color, color=c["text_muted"],
                   tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                   showline=False, zeroline=False, rangeslider=dict(visible=False)),
        yaxis=dict(gridcolor=grid_color, color=c["text_muted"], side="right",
                   tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                   showline=False, zeroline=False),
        xaxis2=dict(gridcolor=grid_color, color=c["text_muted"],
                    tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                    showline=False, zeroline=False),
        yaxis2=dict(gridcolor=grid_color, color=c["text_muted"], side="right",
                    tickfont=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
                    range=[0, 100], showline=False, zeroline=False),
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
        ),
        shapes=[
            dict(type="line", xref="paper", x0=0, x1=1, yref="paper", y0=0.405, y1=0.405,
                 line=dict(color=c["border2"], width=1, dash="dot")),
            dict(type="line", xref="paper", x0=0, x1=1, yref="paper", y0=0.205, y1=0.205,
                 line=dict(color=c["border2"], width=1, dash="dot")),
        ],
    )
    fig.update_layout(**layout)
    return fig


def _render_news_banner(dark: bool, c: dict):
    """Noticias al tope — colores computados en Python (no var() CSS)."""
    hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=90)
    proximos = obtener_proximos_eventos(5)

    alert_html = ""
    if hay_ev and ev_info:
        ab  = "rgba(239,68,68,0.12)" if dark else "rgba(200,30,30,0.07)"
        abd = "rgba(239,68,68,0.55)" if dark else "rgba(200,30,30,0.40)"
        at  = "#f87171" if dark else "#c81e1e"
        alert_html = f"""
        <div class="oram-alert-high" style="background:{ab};border:1.5px solid {abd};">
            <span style="font-size:1.2rem">⚠️</span>
            <div>
                <span style="color:{at};font-weight:700;font-family:'Space Grotesk',sans-serif;font-size:0.88rem;">
                    Evento de alto impacto en {ev_info['minutos_restantes']} min
                </span>
                <span style="color:{c['text_muted']};font-size:0.80rem;margin-left:0.5rem;">
                    — {ev_info['titulo']} ({ev_info['moneda']}) · {ev_info['hora_mx']} CDMX
                </span>
            </div>
        </div>"""

    if not proximos:
        if alert_html:
            st.markdown(alert_html, unsafe_allow_html=True)
        return

    cards_html = ""
    for ev in proximos:
        imp_color = impacto_color(ev["impacto"], dark)
        imp_bg = (
            "rgba(239,68,68,0.10)"   if ev["impacto"] == "High"   else
            "rgba(201,162,39,0.08)"  if ev["impacto"] == "Medium" else
            "rgba(107,127,153,0.07)"
        ) if dark else (
            "rgba(200,30,30,0.07)"   if ev["impacto"] == "High"   else
            "rgba(154,117,16,0.06)"  if ev["impacto"] == "Medium" else
            "rgba(80,100,120,0.05)"
        )
        cards_html += f"""
        <div class="oram-news-card" style="background:{imp_bg};border-color:{imp_color}33;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.59rem;
                color:{c['text_muted']};margin-bottom:0.18rem;">
                {ev['dia']} · {ev['hora_mx']} CDMX
            </div>
            <div style="font-size:0.77rem;font-weight:700;color:{imp_color};
                font-family:'Inter',sans-serif;line-height:1.3;">
                {impacto_emoji(ev['impacto'])} {ev['titulo']}
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
                color:{c['text_muted']};margin-top:0.12rem;">{ev['moneda']}</div>
        </div>"""

    st.markdown(f"""
    {alert_html}
    <div class="oram-news-wrapper">
        <div class="oram-news-label">📰 &nbsp;Próximos eventos de mercado</div>
        <div class="oram-news-cards">{cards_html}</div>
        <a href="{FOREX_FACTORY_URL}" target="_blank" class="oram-news-link">
            🔗 Ver calendario completo en Forex Factory →
        </a>
    </div>
    """, unsafe_allow_html=True)


def render_live_analysis():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"

    # CSS + JS del módulo (inputs, dropdown portal, botón, noticias, gráfica)
    _inject_module_css(dark, c)

    # [1] Header
    page_header("📡", "Análisis en Vivo", "Smart Money Concepts · Order Blocks · FVG · Liquidez")

    # [2] Noticias AL TOPE
    _render_news_banner(dark, c)

    # [3] Controles
    col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1.5])
    with col1:
        categoria = st.selectbox("Categoría", list(ACTIVOS_DEFAULT.keys()), key="cat_live")
    with col2:
        ticker = st.selectbox("Activo", ACTIVOS_DEFAULT[categoria], key="ticker_live")
    with col3:
        tf = st.selectbox(
            "Temporalidad", list(TIMEFRAME_LABELS.keys()),
            format_func=lambda x: TIMEFRAME_LABELS[x], index=2, key="tf_live",
        )
    with col4:
        capital = st.number_input(
            "Capital USD", value=float(user.get("capital_inicial", 1000)),
            min_value=100.0, step=500.0, key="cap_live",
        )
    with col5:
        riesgo_pct = st.number_input(
            "Riesgo %", value=1.0, min_value=0.1, max_value=5.0, step=0.1, key="rsk_live",
        )

    # [4] Botón + status
    btn_col, status_col = st.columns([3, 7])
    with btn_col:
        actualizar = st.button(
            "🔄 Actualizar análisis", key="btn_actualizar_live",
            type="primary", use_container_width=True,
        )
    with status_col:
        st.markdown(
            '<span id="oram-btn-status">'
            '<span class="oram-micro-spinner"></span>&nbsp;Actualizando…'
            '</span>',
            unsafe_allow_html=True,
        )

    # [5] Datos
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

    # [6] Gráfica con tarjeta institucional
    st.markdown('<div class="oram-chart-card">', unsafe_allow_html=True)
    st.plotly_chart(_grafica_velas(df, ticker, smc), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # [7] Panel de análisis
    precio    = smc.get("precio", 0)
    atr       = smc.get("atr", 0)
    rsi       = smc.get("rsi")
    est       = smc.get("estructura", {})
    conf      = smc.get("confluencia", {})
    tipo      = est.get("tipo", "Sin señal")
    confianza = conf.get("confianza", 0)
    factores  = conf.get("factores", [])

    st.divider()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Precio",    f"{precio:.5f}")
    m2.metric("ATR",       f"{atr:.5f}")
    m3.metric("RSI",       f"{rsi:.1f}" if rsi else "—",
               delta="Sobrecomprado" if rsi and rsi > 70 else "Sobrevendido" if rsi and rsi < 30 else "Neutral")
    m4.metric("Señal",     tipo if tipo != "Sin señal" else "Rango")
    m5.metric("Confianza", f"{confianza:.0f}%")

    st.markdown("")
    col_senal, col_niveles, col_riesgo = st.columns([2, 2, 1])

    with col_senal:
        st.markdown(signal_box(tipo, est.get("descripcion", ""), confianza), unsafe_allow_html=True)
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
            </div>""", unsafe_allow_html=True)

    with col_niveles:
        obs  = smc.get("order_blocks", [])
        fvgs = smc.get("fvgs", [])
        liq  = smc.get("liquidez", {})
        st.markdown("**🧱 Order Blocks**")
        if obs:
            for ob in obs[:4]:
                badge = "badge-ob-bull" if ob.tipo == "OB_alcista" else "badge-ob-bear"
                label = "OB↑" if ob.tipo == "OB_alcista" else "OB↓"
                st.markdown(f'<span class="level-badge {badge}">{label} {ob.precio_bot:.5f}–{ob.precio_top:.5f}</span>', unsafe_allow_html=True)
        else:
            st.caption("Sin OBs detectados.")
        st.markdown("**⚡ Fair Value Gaps**")
        if fvgs:
            for fvg in fvgs[:4]:
                badge = "badge-fvg-bull" if fvg.tipo == "FVG_alcista" else "badge-fvg-bear"
                label = "FVG↑" if fvg.tipo == "FVG_alcista" else "FVG↓"
                st.markdown(f'<span class="level-badge {badge}">{label} {fvg.precio_bot:.5f}–{fvg.precio_top:.5f}</span>', unsafe_allow_html=True)
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
            </div>""", unsafe_allow_html=True)
            risk = calcular_riesgo(precio, sl_s, tp_s, capital, riesgo_pct)
            if risk:
                st.markdown(f"""
                <div class="oram-card oram-card-gold">
                    <div class="card-title">Gestión de Riesgo</div>
                    <div class="card-sub">Riesgo: <b>${risk['riesgo_usd']}</b></div>
                    <div class="card-sub">RR: <b>{risk['rr']}:1</b></div>
                    <div class="card-sub">Ganancia pot: <b>${risk['ganancia_pot']}</b></div>
                    <div class="card-sub">Lote: <b>{risk['lot_size']}</b></div>
                </div>""", unsafe_allow_html=True)
