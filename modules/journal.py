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

SETUPS_SMC = [
    "OB Alcista + FVG", "OB Bajista + FVG",
    "BOS + OB Retest", "CHoCH Reversión",
    "Liquidity Sweep + Reversal", "EMA50 + OB Confluencia",
    "FVG Solo", "Order Block Solo",
    "Breaker Block", "Mitigation Block", "Otro"
]
EMOCIONES = ["Neutral", "Confiado", "Ansioso", "FOMO", "Revancha", "Paciente", "Dudoso"]


def _inject_journal_css(dark: bool, c: dict):
    """CSS premium idéntico al de Análisis en Vivo y Multi-Timeframe, extendido para
    todos los tipos de input presentes en el formulario Nuevo Trade."""
    input_bg   = "#080d14"  if dark else "#f0f4f8"
    input_text = "#c8d8ea"  if dark else "#1a2b3c"
    input_bdr  = "#2a4560"  if dark else "#94a3b8"
    label_col  = "#4a6a84"  if dark else "#6b7f94"
    focus_clr  = "#22c55e"
    focus_glow = "rgba(34,197,94,0.18)" if dark else "rgba(34,197,94,0.14)"
    eye_col    = "#64748b"
    radio_bg   = "#0f1e2e"  if dark else "#e8eef5"
    divider    = "#1b2e42"  if dark else "#cbd5e1"

    st.markdown(f"""
<style>
/* ══ LABELS — uppercase premium ══════════════════════════════════════════ */
.stSelectbox label, .stNumberInput label, .stTextInput label,
.stTextArea label, .stDateInput label, .stRadio label {{
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
    font-size: 0.93rem !important;
}}
.stSelectbox [data-baseweb="select"] svg {{
    fill: {eye_col} !important; opacity: 0.7 !important;
}}
.stSelectbox [data-baseweb="select"] input {{
    position: absolute !important; width: 1px !important;
    height: 1px !important; opacity: 0 !important;
    pointer-events: none !important; caret-color: transparent !important;
}}

/* ══ NUMBER INPUT ═════════════════════════════════════════════════════════ */
[data-testid="stNumberInput"] > div:nth-child(1) {{
    background: transparent !important; border: none !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2) {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    display: flex !important; align-items: center !important;
    min-height: 46px !important; overflow: hidden !important;
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
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; flex: 1 !important;
    height: 46px !important;
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
    stroke-width: 1.8 !important;
}}
[data-testid="InputInstructions"] {{ display: none !important; }}

/* ══ TEXT INPUT ═══════════════════════════════════════════════════════════ */
.stTextInput > div > div {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    min-height: 46px !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
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
    background: transparent !important; border: none !important; box-shadow: none !important;
}}
[data-testid="stDateInput"] input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; min-height: 44px !important;
}}
[data-testid="stDateInput"]:focus-within > div {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}

/* ══ TEXTAREA ═════════════════════════════════════════════════════════════ */
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
    resize: vertical !important;
}}

/* ══ RADIO ════════════════════════════════════════════════════════════════ */
.stRadio > div {{
    display: flex !important; gap: 0.6rem !important;
    background: {radio_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    padding: 0.4rem 0.6rem !important;
}}
.stRadio > div > label {{
    display: flex !important; align-items: center !important;
    gap: 0.4rem !important; cursor: pointer !important;
    color: {input_text} !important;
    font-family: Inter, sans-serif !important;
    font-size: 0.93rem !important; font-weight: 500 !important;
    text-transform: none !important; letter-spacing: 0 !important;
    padding: 0.25rem 0.5rem !important;
    border-radius: 6px !important;
    transition: background .15s !important;
}}
.stRadio > div > label:hover {{ background: rgba(34,197,94,0.08) !important; }}
[data-testid="stWidgetLabel"] p {{
    color: {label_col} !important;
    font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
}}

/* ══ FORM SUBMIT BUTTON ══════════════════════════════════════════════════ */
[data-testid="stFormSubmitButton"] button {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important; border-radius: 10px !important;
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    font-family: Inter, sans-serif !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
    padding: 0.72rem 1.4rem !important; width: 100% !important;
    box-shadow: 0 4px 14px 0 rgba(16,185,129,0.39) !important;
    transition: box-shadow .25s ease, transform .18s ease !important;
    cursor: pointer !important;
}}
[data-testid="stFormSubmitButton"] button:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 22px 0 rgba(16,185,129,0.58) !important;
    transform: translateY(-1px) !important;
}}
[data-testid="stFormSubmitButton"] button:active {{
    box-shadow: 0 2px 8px 0 rgba(16,185,129,0.30) !important;
    transform: scale(0.98) !important;
}}

/* ══ PRIMARY (Eliminar) ══════════════════════════════════════════════════ */
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important; border-radius: 10px !important;
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    font-family: Inter, sans-serif !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
    box-shadow: 0 4px 14px 0 rgba(16,185,129,0.39) !important;
    transition: box-shadow .25s ease, transform .18s ease !important;
    cursor: pointer !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 22px 0 rgba(16,185,129,0.58) !important;
    transform: translateY(-1px) !important;
}}

/* ══ DATAFRAME historial — normalización visual ═══════════════════════════ */
[data-testid="stDataFrame"] {{
    border: 2px solid {input_bdr} !important;
    border-radius: 12px !important; overflow: hidden !important;
}}
[data-testid="stDataFrame"] th {{
    background: {radio_bg} !important;
    color: {label_col} !important;
    font-family: Inter, sans-serif !important;
    font-size: 0.70rem !important; font-weight: 700 !important;
    letter-spacing: 0.8px !important; text-transform: uppercase !important;
    border-bottom: 1px solid {divider} !important;
}}
[data-testid="stDataFrame"] td {{
    color: {input_text} !important;
    font-family: Inter, sans-serif !important;
    font-size: 0.88rem !important;
    border-bottom: 1px solid {divider} !important;
}}
</style>
""", unsafe_allow_html=True)


def render_journal():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"
    page_header("📋", "Diario de Trades", "Registro · Análisis · Psicología")
    _inject_journal_css(dark, c)

    tab_nuevo, tab_historial = st.tabs(["➕ Nuevo Trade", "📋 Historial"])

    # ── NUEVO TRADE ────────────────────────────────────────────────────────
    with tab_nuevo:
        with st.form("trade_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                fecha     = st.date_input("Fecha", date.today())
                categoria = st.selectbox("Categoría", list(ACTIVOS_DEFAULT.keys()))
                activo    = st.selectbox("Activo", ACTIVOS_DEFAULT[categoria])
            with col2:
                direccion = st.radio("Dirección", ["LONG", "SHORT"], horizontal=True)
                tf        = st.selectbox("Temporalidad", ["1m","5m","15m","30m","1h","4h","1d"])
                setup     = st.selectbox("Setup SMC", SETUPS_SMC)
            with col3:
                emocion = st.selectbox("Estado emocional", EMOCIONES)
                estado  = st.selectbox("Estado del trade", ["Cerrado", "Abierto", "Breakeven"])

            st.divider()
            c4, c5, c6, c7 = st.columns(4)
            with c4: entrada    = st.number_input("Entrada",       value=0.0, format="%.5f")
            with c5: sl         = st.number_input("Stop Loss",      value=0.0, format="%.5f")
            with c6: tp         = st.number_input("Take Profit",    value=0.0, format="%.5f")
            with c7: riesgo_usd = st.number_input("Riesgo (USD)",   value=30.0, min_value=0.0)

            resultado_usd = st.number_input("Resultado (USD)", value=0.0,
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

            notas = st.text_area("Notas / Plan", placeholder="Describe el setup, confluencias, razonamiento...", height=80)
            tags  = st.text_input("Tags (coma)", placeholder="impulso, NY session, OTE, CHoCH...")

            if st.form_submit_button("💾 Guardar Trade", width='stretch'):
                if entrada == 0 or sl == 0 or tp == 0:
                    oram_notify("error", "❌ Entrada, SL y TP son obligatorios.", toast=True, banner=True)
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
                        subtitulo     = f"<b>{activo}</b> {direccion} — {setup}<br>RR estimado: {riesgo_usd:.1f} USD en riesgo.",
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
        <div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap">
            <span class="card-sub">{len(df)} trades</span>
            <span class="card-sub">PnL: <b style="color:{c['green'] if pnl_total>=0 else c['red']}">${pnl_total:,.2f}</b></span>
            <span class="card-sub">Win Rate: <b>{wr:.1f}%</b></span>
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
        st.dataframe(styled, width='stretch', height=400)

        st.divider()
        if len(df) > 0:
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                trade_ids = df['id'].tolist()
                del_id = st.selectbox("Trade a eliminar", trade_ids,
                                       format_func=lambda i: f"#{i} – {df[df['id']==i]['activo'].values[0]} {str(df[df['id']==i]['fecha'].values[0])[:10]}",
                                       key="del_id")
            with col_del2:
                st.markdown("")
                if st.button("🗑️ Eliminar", width='stretch'):
                    eliminar_trade(del_id, user["id"])
                    oram_bienvenida(
                        titulo        = "🗑️ Trade eliminado",
                        subtitulo     = f"El trade <b>#{del_id}</b> ha sido eliminado permanentemente de tu historial.",
                        spinner_label = "Actualizando diario…",
                        delay         = 1.8,
                    )
