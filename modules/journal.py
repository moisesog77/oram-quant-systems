"""
modules/journal.py — ORAM Quant Systems — Diario de Trades
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Registro y análisis del historial de operaciones.

Tabs:
  ✏️ Nuevo Trade  → formulario: activo, TF, dirección, entrada/SL/TP,
                    RR calculado en tiempo real, setup SMC, emoción, estado
  📋 Historial    → tabla filtrable + métricas win rate, P&L, RR promedio
  📊 Analytics    → distribución por setup, emoción, activo, estado
  🗑️ Eliminar     → selección por ID con overlay de confirmación

RR planeado = |TP-entrada| / |SL-entrada| calculado en insertar_trade().
RR real = resultado_usd / riesgo_usd guardado en el mismo trade.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database.db import insertar_trade, obtener_trades, eliminar_trade
from utils.market_data import ACTIVOS_DEFAULT
from utils.smc_engine import calcular_riesgo
from ui.styles import get_colors, page_header, oram_notify, oram_bienvenida, get_theme


def _inject_journal_css():
    """CSS premium unificado — corrige todos los problemas visuales del formulario."""
    dark = get_theme() == "dark"

    input_bg   = "#080d14"  if dark else "#f0f4f8"
    input_text = "#c8d8ea"  if dark else "#1a2b3c"
    input_bdr  = "#2a4560"  if dark else "#94a3b8"
    label_col  = "#4a6a84"  if dark else "#6b7f94"
    focus_clr  = "#22c55e"
    focus_glow = "rgba(34,197,94,0.18)" if dark else "rgba(34,197,94,0.14)"
    eye_col    = "#64748b"
    tab_bg     = "#0c1219"  if dark else "#f8fafc"
    tab_bdr    = "#1b2a40"  if dark else "#dde5ef"
    tab_text   = "#637a94"  if dark else "#7a8fa0"

    st.markdown(f"""
<style>
/* ══ LABELS — uppercased premium ══════════════════════════════════════════ */
.stSelectbox label,
.stNumberInput label,
.stTextInput label,
.stTextArea label,
.stDateInput label,
[data-testid="stRadio"] > div > label:first-child,
[data-testid="stWidgetLabel"] p {{
    color: {label_col} !important;
    font-family: Inter, sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    margin-bottom: 0.3rem !important;
    display: block !important;
}}

/* ══ SELECTBOX ════════════════════════════════════════════════════════════ */
.stSelectbox > div,
.stSelectbox > div > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important; margin: 0 !important;
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
    font-family: Inter, sans-serif !important;
    font-size: 0.93rem !important;
    pointer-events: none !important;
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

/* ══ NUMBER INPUT — sin cuadro emergente al clickear ═══════════════════════ */
[data-testid="stNumberInput"] {{
    background: transparent !important; border: none !important;
}}
[data-testid="stNumberInput"] > div:nth-child(1) {{
    background: transparent !important; border: none !important;
    box-shadow: none !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2) {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    display: flex !important; align-items: center !important;
    min-height: 46px !important;
    overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    padding: 0 !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2):focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
[data-testid="stNumberInput"] input {{
    background: transparent !important;
    border: none !important; box-shadow: none !important; outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; flex: 1 !important;
    height: 46px !important;
    -moz-appearance: textfield !important;
}}
[data-testid="stNumberInput"] input::-webkit-outer-spin-button,
[data-testid="stNumberInput"] input::-webkit-inner-spin-button {{
    -webkit-appearance: none !important; margin: 0 !important;
}}
/* Eliminar tooltip/popover emergente */
[data-testid="stNumberInput"] input:focus {{
    outline: none !important;
    box-shadow: none !important;
}}
[data-testid="InputInstructions"],
[data-baseweb="popover"],
[data-baseweb="tooltip"] {{
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
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

/* ══ DATE INPUT ═══════════════════════════════════════════════════════════ */
[data-testid="stDateInput"] > div {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; overflow: hidden !important;
    min-height: 46px !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
}}
[data-testid="stDateInput"] > div > div {{
    background: transparent !important; border: none !important;
    box-shadow: none !important;
}}
[data-testid="stDateInput"] input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; height: 46px !important;
}}
[data-testid="stDateInput"]:focus-within > div {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}

/* ══ TEXT INPUT (Tags) — contorno completo ════════════════════════════════ */
.stTextInput > div {{
    border: none !important; background: transparent !important;
    box-shadow: none !important; padding: 0 !important; margin: 0 !important;
}}
.stTextInput > div > div,
[data-testid="textInputRootElement"] {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    display: flex !important; align-items: center !important;
}}
.stTextInput > div > div:focus-within,
[data-testid="textInputRootElement"]:focus-within {{
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

/* ══ TEXT AREA ════════════════════════════════════════════════════════════ */
.stTextArea > div > div {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    overflow: hidden !important;
}}
.stTextArea > div > div:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
.stTextArea textarea {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important;
    padding: 0.65rem 0.75rem !important;
}}

/* ══ RADIO BUTTONS — SOLO verde, sin dorado en hover ════════════════════ */
[data-testid="stRadio"] > div {{
    background: transparent !important;
    display: flex !important; gap: 0.5rem !important; flex-wrap: wrap !important;
}}
/* Neutralizar cualquier color heredado del tema */
[data-testid="stRadio"] label,
[data-testid="stRadio"] label * {{
    accent-color: {focus_clr} !important;
}}
[data-testid="stRadio"] label {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    padding: 0.45rem 1.1rem !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important;
    font-size: 0.88rem !important; font-weight: 500 !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    cursor: pointer !important;
    display: flex !important; align-items: center !important; gap: 0.5rem !important;
}}
/* HOVER: solo verde, nunca dorado */
[data-testid="stRadio"] label:hover {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 2px {focus_glow} !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
}}
/* Seleccionado */
[data-testid="stRadio"] [data-checked="true"] label,
[data-testid="stRadio"] label[data-checked="true"] {{
    border-color: {focus_clr} !important;
    color: {focus_clr} !important;
    -webkit-text-fill-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
/* Círculo radio — eliminar dorado nativo del tema */
[data-testid="stRadio"] div[role="radio"] {{
    border-color: {input_bdr} !important;
    background: {input_bg} !important;
    box-shadow: none !important;
    accent-color: {focus_clr} !important;
}}
[data-testid="stRadio"] div[role="radio"][aria-checked="true"] {{
    border-color: {focus_clr} !important;
    background: {focus_clr} !important;
}}
[data-testid="stRadio"] div[role="radio"] > div,
[data-testid="stRadio"] div[role="radio"] svg {{
    background: transparent !important;
    fill: {focus_clr} !important;
    color: {focus_clr} !important;
}}
/* Forzar que el acento del navegador sea verde, no dorado */
[data-testid="stRadio"] input[type="radio"] {{
    accent-color: {focus_clr} !important;
}}

/* ══ TABS premium ═════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {{
    background: {tab_bg} !important;
    border-bottom: 2px solid {tab_bdr} !important;
    padding: 0 0.5rem !important; gap: 4px !important;
    border-radius: 10px 10px 0 0 !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: Inter, sans-serif !important;
    font-size: 0.82rem !important; font-weight: 500 !important;
    color: {tab_text} !important;
    background: transparent !important; border: none !important;
    padding: 0.7rem 1.2rem !important;
    transition: color .18s ease !important;
    letter-spacing: 0.3px !important;
}}
.stTabs [data-baseweb="tab"]:hover {{ color: {input_text} !important; }}
.stTabs [aria-selected="true"] {{
    color: #22c55e !important;
    border-bottom: 2px solid #22c55e !important;
    font-weight: 700 !important;
}}
.stTabs [data-baseweb="tab"] p {{ color: inherit !important; }}

/* ══ BOTÓN GUARDAR TRADE — premium verde ══════════════════════════════════ */
[data-testid="stFormSubmitButton"] button,
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important; border-radius: 10px !important;
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    font-family: Inter, sans-serif !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
    padding: 0.72rem 1.4rem !important;
    box-shadow: 0 4px 14px 0 rgba(16,185,129,0.39) !important;
    transition: box-shadow .25s ease, transform .18s ease !important;
    cursor: pointer !important; width: 100% !important;
}}
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stBaseButton-primary"]:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 22px 0 rgba(16,185,129,0.58) !important;
    transform: translateY(-1px) !important;
}}
[data-testid="stFormSubmitButton"] button:active,
[data-testid="stBaseButton-primary"]:active {{
    box-shadow: 0 2px 8px 0 rgba(16,185,129,0.30) !important;
    transform: scale(0.98) !important;
}}

/* ══ DATAFRAME historial ══════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {{
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; overflow: hidden !important;
}}
[data-testid="stDataFrame"] thead tr th {{
    background: {input_bg} !important;
    color: {label_col} !important;
    font-family: Inter, sans-serif !important;
    font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
    border-bottom: 2px solid {input_bdr} !important;
}}
[data-testid="stDataFrame"] tbody tr td {{
    color: {input_text} !important;
    font-family: Inter, sans-serif !important;
    font-size: 0.85rem !important;
    border-bottom: 1px solid {tab_bdr} !important;
}}
[data-testid="stDataFrame"] tbody tr:hover td {{
    background: {tab_bg} !important;
}}
</style>
""", unsafe_allow_html=True)


def _error_overlay(mensaje: str) -> None:
    """Overlay premium de error — mismo estilo que oram_bienvenida."""
    dark = get_theme() == "dark"
    overlay_bg  = "rgba(6,9,15,0.92)"  if dark else "rgba(238,242,247,0.94)"
    card_bg     = "#0c1219"            if dark else "#ffffff"
    card_border = "#3d1a1a"            if dark else "#f8d0d0"
    text_main   = "#edf4ff"            if dark else "#0b1824"
    text_muted  = "#637a94"            if dark else "#7a8fa0"

    import time
    placeholder = st.empty()
    placeholder.markdown(f"""
<style>
@keyframes oram-fadein {{
    from {{ opacity: 0; transform: translateY(14px) scale(0.97); }}
    to   {{ opacity: 1; transform: translateY(0)    scale(1);    }}
}}
#oram-error-overlay {{
    position: fixed; inset: 0;
    background: {overlay_bg};
    backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
    z-index: 99999;
    display: flex; align-items: center; justify-content: center;
}}
#oram-error-card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 20px;
    padding: 2.8rem 3rem 2.4rem;
    text-align: center; max-width: 400px; width: 90%;
    animation: oram-fadein 0.45s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow: 0 24px 60px rgba(0,0,0,0.35);
}}
</style>
<div id="oram-error-overlay">
  <div id="oram-error-card">
    <div style="font-size:3rem;margin-bottom:1rem">❌</div>
    <div style="font-family:'Space Grotesk',sans-serif;font-size:1.25rem;
                font-weight:700;color:#f87171;margin-bottom:0.6rem">
      Campo obligatorio
    </div>
    <div style="font-family:Inter,sans-serif;font-size:0.92rem;
                color:{text_muted};line-height:1.6">
      {mensaje}
    </div>
    <div style="margin-top:1.4rem;font-family:Inter,sans-serif;
                font-size:0.8rem;color:{text_muted};opacity:0.7">
      Cerrando automáticamente…
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    time.sleep(2.2)
    placeholder.empty()
    st.rerun()


SETUPS_SMC = [
    "OB Alcista + FVG", "OB Bajista + FVG",
    "BOS + OB Retest", "CHoCH Reversión",
    "Liquidity Sweep + Reversal", "EMA50 + OB Confluencia",
    "FVG Solo", "Order Block Solo",
    "Breaker Block", "Mitigation Block", "Otro"
]
EMOCIONES = ["Neutral", "Confiado", "Ansioso", "FOMO", "Revancha", "Paciente", "Dudoso"]


def render_journal():
    user = st.session_state.user
    c    = get_colors()
    page_header("📋", "Diario de Trades", "Registro · Análisis · Psicología")
    _inject_journal_css()

    tab_nuevo, tab_historial = st.tabs(["➕ Nuevo Trade", "📋 Historial"])

    # ── NUEVO TRADE ────────────────────────────────────────────────────────
    with tab_nuevo:
        with st.form("trade_form", clear_on_submit=True):
            # Fila 1: Fecha | Dirección | Estado emocional
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                fecha = st.date_input("Fecha", date.today())
            with col2:
                direccion = st.radio("Dirección", ["LONG", "SHORT"], horizontal=True)
            with col3:
                emocion = st.selectbox("Estado emocional", EMOCIONES)

            # Fila 2: Categoría | Temporalidad | Estado del trade
            col4, col5, col6 = st.columns([1, 1, 1])
            with col4:
                categoria = st.selectbox("Categoría", list(ACTIVOS_DEFAULT.keys()))
            with col5:
                tf = st.selectbox("Temporalidad", ["1m","5m","15m","30m","1h","4h","1d"])
            with col6:
                estado = st.selectbox("Estado del trade", ["Cerrado", "Abierto", "Breakeven"])

            # Fila 3: Activo | Setup SMC
            col7, col8 = st.columns([1, 1])
            with col7:
                activo = st.selectbox("Activo", ACTIVOS_DEFAULT[categoria])
            with col8:
                setup = st.selectbox("Setup SMC", SETUPS_SMC)

            st.markdown('<div style="margin-top:0.5rem"></div>', unsafe_allow_html=True)

            # Fila 4: números
            c4, c5, c6, c7 = st.columns(4)
            with c4: entrada    = st.number_input("Entrada",     value=0.0, format="%.5f", step=0.00001)
            with c5: sl         = st.number_input("Stop Loss",   value=0.0, format="%.5f", step=0.00001)
            with c6: tp         = st.number_input("Take Profit", value=0.0, format="%.5f", step=0.00001)
            with c7: riesgo_usd = st.number_input("Riesgo (USD)", value=30.0, min_value=0.0, step=1.0)

            resultado_usd = st.number_input("Resultado (USD)", value=0.0, step=1.0,
                                            help="Positivo = ganancia · Negativo = pérdida")

            if entrada > 0 and sl > 0 and tp > 0:
                risk = calcular_riesgo(entrada, sl, tp, user.get('capital_inicial', 1000), 1.0)
                if risk:
                    st.markdown(f"""
                    <div class="smc-card" style="padding:0.7rem 1rem">
                        <span class="card-sub">
                        📐 RR: <b>{risk['rr']}:1</b> &nbsp;|&nbsp;
                        Pips SL: <b>{risk['pips_sl']}</b> &nbsp;|&nbsp;
                        Pips TP: <b>{risk['pips_tp']}</b> &nbsp;|&nbsp;
                        Ganancia pot.: <b>${risk['ganancia_pot']}</b>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

            notas = st.text_area("Notas / Plan",
                                 placeholder="Describe el setup, confluencias, razonamiento...",
                                 height=80)
            tags  = st.text_input("Tags (coma)", placeholder="impulso, NY session, OTE, CHoCH...")

            if st.form_submit_button("💾 Guardar Trade", use_container_width=True):
                if entrada == 0 or sl == 0 or tp == 0:
                    _error_overlay("Entrada, Stop Loss y Take Profit son obligatorios antes de guardar el trade.")
                else:
                    insertar_trade(user["id"], {
                        "fecha": str(fecha), "activo": activo, "timeframe": tf,
                        "direccion": direccion, "entrada": entrada, "sl": sl, "tp": tp,
                        "riesgo_usd": riesgo_usd, "resultado_usd": resultado_usd,
                        "setup": setup, "emocion": emocion, "notas": notas,
                        "tags": [t.strip() for t in tags.split(",") if t.strip()],
                        "estado": estado,
                    })
                    oram_bienvenida(
                        titulo        = "💾 Trade registrado",
                        subtitulo     = f"<b>{activo}</b> {direccion} — {setup}<br>Riesgo: ${riesgo_usd:.2f} USD",
                        spinner_label = "Actualizando diario…",
                        delay         = 2.0,
                    )

    # ── HISTORIAL ──────────────────────────────────────────────────────────
    with tab_historial:
        trades = obtener_trades(user["id"])
        if not trades:
            st.info("No tienes trades registrados aún.")
            return

        df = pd.DataFrame(trades)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])

        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            filtro_activo = st.selectbox("Activo", ["Todos"] + sorted(df['activo'].unique().tolist()), key="f_act")
        with fc2:
            filtro_dir = st.selectbox("Dirección", ["Todos", "LONG", "SHORT"], key="f_dir")
        with fc3:
            filtro_setup = st.selectbox("Setup", ["Todos"] + sorted(df['setup'].unique().tolist()), key="f_stp")
        with fc4:
            filtro_estado = st.selectbox("Estado", ["Todos", "Cerrado", "Abierto", "Breakeven"], key="f_est")

        if filtro_activo != "Todos": df = df[df['activo'] == filtro_activo]
        if filtro_dir    != "Todos": df = df[df['direccion'] == filtro_dir]
        if filtro_setup  != "Todos": df = df[df['setup'] == filtro_setup]
        if filtro_estado != "Todos": df = df[df['estado'] == filtro_estado]

        pnl_total = df['resultado_usd'].sum()
        wr        = (df['resultado_usd'] > 0).mean() * 100 if len(df) > 0 else 0
        st.markdown(f"""
        <div style="display:flex;gap:1.5rem;margin-bottom:1rem;flex-wrap:wrap;
                    padding:0.75rem 1rem;background:#0c1219;border-radius:10px;
                    border:1px solid #1b2a40">
            <span class="card-sub" style="font-size:0.82rem">{len(df)} trades</span>
            <span class="card-sub" style="font-size:0.82rem">P&L: <b style="color:{'#26de81' if pnl_total>=0 else '#fc5c65'}">${pnl_total:,.2f}</b></span>
            <span class="card-sub" style="font-size:0.82rem">Win Rate: <b>{wr:.1f}%</b></span>
        </div>
        """, unsafe_allow_html=True)

        display_cols = ['fecha','activo','timeframe','direccion','entrada','sl','tp',
                        'riesgo_usd','resultado_usd','rr_planeado','setup','emocion','estado']
        df_show = df[[col for col in display_cols if col in df.columns]].copy()

        def color_result(val):
            if isinstance(val, (int, float)):
                if val > 0:   return 'color: #26de81'
                elif val < 0: return 'color: #fc5c65'
            return ''

        styled = df_show.style.map(color_result, subset=['resultado_usd'])
        st.dataframe(styled, use_container_width=True, height=400)

        st.divider()
        if len(df) > 0:
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                trade_ids = df['id'].tolist()
                del_id = st.selectbox(
                    "Trade a eliminar", trade_ids,
                    format_func=lambda i: f"#{i} – {df[df['id']==i]['activo'].values[0]} {str(df[df['id']==i]['fecha'].values[0])[:10]}",
                    key="del_id"
                )
            with col_del2:
                st.markdown('<div style="margin-top:1.65rem"></div>', unsafe_allow_html=True)
                if st.button("🗑️ Eliminar", use_container_width=True):
                    eliminar_trade(del_id, user["id"])
                    oram_bienvenida(
                        titulo        = "🗑️ Trade eliminado",
                        subtitulo     = f"El trade <b>#{del_id}</b> ha sido eliminado de tu historial.",
                        spinner_label = "Actualizando diario…",
                        delay         = 1.8,
                    )
