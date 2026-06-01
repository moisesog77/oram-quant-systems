"""
modules/dashboard.py — Resumen general del trader.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database.db import obtener_trades, actualizar_capital
from utils.ai_engine import calcular_drawdown, calcular_sharpe
from ui.styles import metric_card, get_colors, page_header


def render_dashboard():
    user = st.session_state.user
    page_header("📈", "Dashboard", f"Bienvenido, {user['username'].upper()}")

    c = get_colors()
    dark = st.session_state.get("theme", "dark") == "dark"

    # ── Variables de color para inputs premium (consistentes con auth.py) ──
    input_bg  = "#080d14" if dark else "#f0f4f8"
    input_bdr = "#2a4560" if dark else "#94a3b8"
    focus_clr = "#22c55e"
    focus_glow = "rgba(34,197,94,0.18)" if dark else "rgba(34,197,94,0.14)"
    eye_col   = "#64748b"
    input_text = "#c8d8ea" if dark else "#1a2b3c"
    input_ph   = "#3a5068" if dark else "#9baab8"
    label_col  = "#4a6a84" if dark else "#6b7f94"

    # ── CSS: botón verde idéntico a stFormSubmitButton + inputs premium ──
    st.markdown(f"""
<style>
/* ═══════════════════════════════════════════════════════════════
   BOTÓN "Actualizar capital" — idéntico al botón verde de
   'Guardar configuración' en Bot Telegram (stFormSubmitButton).
   Selector: data-testid del key específico para máxima especificidad
   y cero efecto secundario en otros botones de la app.
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stButton-btn_actualizar_capital"] > button {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    padding: 0.72rem 1rem !important;
    width: 100% !important;
    box-shadow: 0 4px 16px rgba(22, 163, 74, 0.38) !important;
    transition: all .18s ease !important;
    cursor: pointer !important;
    margin-top: 0.5rem !important;
}}
[data-testid="stButton-btn_actualizar_capital"] > button * {{
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}}
[data-testid="stButton-btn_actualizar_capital"] > button:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 24px rgba(34, 197, 94, 0.48) !important;
    transform: translateY(-1px) !important;
}}
[data-testid="stButton-btn_actualizar_capital"] > button:active {{
    transform: scale(0.98) !important;
    box-shadow: 0 2px 8px rgba(22, 163, 74, 0.3) !important;
}}

/* ═══════════════════════════════════════════════════════════════
   INPUTS PREMIUM dentro del expander "Configuración de cuenta"
   Selector scoped a [data-testid="stExpander"] para no afectar
   ningún otro input de la aplicación.
   ═══════════════════════════════════════════════════════════════ */

/* ── Labels ── */
[data-testid="stExpander"] .stTextInput label,
[data-testid="stExpander"] .stNumberInput label {{
    color: {label_col} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    margin-bottom: 0.3rem !important;
    display: block !important;
}}

/* ── Text input — reset wrappers ── */
[data-testid="stExpander"] .stTextInput,
[data-testid="stExpander"] .stTextInput > div,
[data-testid="stExpander"] .stTextInput > div > div,
[data-testid="stExpander"] .stTextInput > div > div > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}
/* ── Text input — borde premium en data-baseweb="input" ── */
[data-testid="stExpander"] .stTextInput [data-baseweb="input"] {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
    min-height: 46px !important;
    overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
}}
[data-testid="stExpander"] .stTextInput [data-baseweb="input"]:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
[data-testid="stExpander"] .stTextInput [data-baseweb="base-input"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    flex: 1 !important;
    min-height: 46px !important;
}}
[data-testid="stExpander"] .stTextInput input {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.93rem !important;
    padding: 0 0.9rem !important;
    flex: 1 !important;
    height: 46px !important;
}}
[data-testid="stExpander"] .stTextInput input::placeholder {{
    color: {input_ph} !important;
    -webkit-text-fill-color: {input_ph} !important;
    opacity: 1 !important;
}}
/* ── Ojo del password — mismo estilo que auth.py ── */
[data-testid="stExpander"] .stTextInput [data-baseweb="input"] button {{
    all: unset !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 44px !important;
    min-width: 44px !important;
    height: 46px !important;
    flex-shrink: 0 !important;
    cursor: pointer !important;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    opacity: 0.55 !important;
    transition: opacity .15s !important;
}}
[data-testid="stExpander"] .stTextInput [data-baseweb="input"] button:hover {{
    opacity: 1 !important;
}}
[data-testid="stExpander"] .stTextInput [data-baseweb="input"] button svg {{
    width: 17px !important;
    height: 17px !important;
    fill: none !important;
    stroke: {eye_col} !important;
    stroke-width: 1.8 !important;
    pointer-events: none !important;
    display: block !important;
}}

/* ── Number input — reset wrappers ── */
[data-testid="stExpander"] [data-testid="stNumberInput"],
[data-testid="stExpander"] [data-testid="stNumberInput"] > div,
[data-testid="stExpander"] [data-testid="stNumberInput"] > div > div,
[data-testid="stExpander"] [data-testid="stNumberInput"] > div > div > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}
/* ── Number input — borde premium ── */
[data-testid="stExpander"] [data-testid="stNumberInput"] > div:last-child {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    min-height: 46px !important;
    overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    padding: 0 !important;
}}
[data-testid="stExpander"] [data-testid="stNumberInput"] > div:last-child:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
[data-testid="stExpander"] [data-testid="stNumberInput"] input,
[data-testid="stExpander"] [data-testid="stNumberInput"] input[type="number"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.93rem !important;
    padding: 0 0.75rem !important;
    flex: 1 !important;
    height: 46px !important;
    -moz-appearance: textfield !important;
}}
[data-testid="stExpander"] [data-testid="stNumberInput"] input::-webkit-outer-spin-button,
[data-testid="stExpander"] [data-testid="stNumberInput"] input::-webkit-inner-spin-button {{
    -webkit-appearance: none !important;
    margin: 0 !important;
}}
/* ── Wrapper de botones +/- ── */
[data-testid="stExpander"] [data-testid="stNumberInput"] > div:last-child > div:last-child {{
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: center !important;
    align-self: stretch !important;
    height: 100% !important;
    gap: 0 !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
}}
/* ── Botones +/- individuales ── */
[data-testid="stExpander"] [data-testid="stNumberInput-StepDown"],
[data-testid="stExpander"] [data-testid="stNumberInput-StepUp"] {{
    all: unset !important;
    box-sizing: border-box !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    align-self: stretch !important;
    width: 36px !important;
    min-width: 36px !important;
    height: 100% !important;
    min-height: 42px !important;
    flex-shrink: 0 !important;
    cursor: pointer !important;
    background: transparent !important;
    border: none !important;
    border-left: 1px solid {input_bdr} !important;
    opacity: 0.6 !important;
    transition: opacity .15s, background .15s !important;
}}
[data-testid="stExpander"] [data-testid="stNumberInput-StepDown"]:hover,
[data-testid="stExpander"] [data-testid="stNumberInput-StepUp"]:hover {{
    opacity: 1 !important;
    background: rgba(34, 197, 94, 0.08) !important;
}}
[data-testid="stExpander"] [data-testid="stNumberInput-StepDown"] svg,
[data-testid="stExpander"] [data-testid="stNumberInput-StepUp"] svg {{
    width: 14px !important;
    height: 14px !important;
    fill: none !important;
    stroke: {eye_col} !important;
    stroke-width: 2 !important;
    pointer-events: none !important;
    display: block !important;
}}
</style>
""", unsafe_allow_html=True)

    trades = obtener_trades(user["id"])
    df     = pd.DataFrame(trades) if trades else pd.DataFrame()

    # Capital actual
    capital_ini = user.get("capital_inicial", 1000.0)
    pnl_total   = df['resultado_usd'].sum() if not df.empty else 0
    capital_act = capital_ini + pnl_total

    # ── Métricas superiores ──────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Capital actual", f"${capital_act:,.2f}", delta=f"${pnl_total:,.2f}")
    with c2:
        st.metric("Total trades", len(df))
    with c3:
        if not df.empty:
            wr = (df['resultado_usd'] > 0).mean() * 100
            st.metric("Win Rate", f"{wr:.1f}%")
        else:
            st.metric("Win Rate", "—")
    with c4:
        if not df.empty:
            gp = df[df['resultado_usd'] > 0]['resultado_usd'].sum()
            gl = abs(df[df['resultado_usd'] < 0]['resultado_usd'].sum())
            pf = gp / gl if gl > 0 else 0
            st.metric("Profit Factor", f"{pf:.2f}")
        else:
            st.metric("Profit Factor", "—")
    with c5:
        if not df.empty and len(df) > 2:
            sharpe = calcular_sharpe(df['resultado_usd'])
            st.metric("Sharpe", f"{sharpe:.2f}")
        else:
            st.metric("Sharpe", "—")

    st.divider()

    col_left, col_right = st.columns([3, 2])

    with col_left:
        # ── Equity Curve ────────────────────────────────────────────────────
        st.markdown("**Curva de Equity**")
        if not df.empty and len(df) >= 2:
            dd_data = calcular_drawdown(df['resultado_usd'])
            equity  = dd_data['equity_curve']
            eq_ser  = [capital_ini + e for e in equity]

            fig = go.Figure()
            colors = [c['green'] if v >= capital_ini else c['red'] for v in eq_ser]
            fig.add_trace(go.Scatter(
                y=eq_ser, mode='lines+markers',
                line=dict(color=c['accent'], width=2),
                fill='tozeroy',
                fillcolor='rgba(245,166,35,0.06)',
                marker=dict(size=4, color=colors),
                name='Equity'
            ))
            fig.update_layout(
                height=280, margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor=c['plot_bg'],
                xaxis=dict(showgrid=False, color=c['text_muted'], tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
                yaxis=dict(gridcolor=c['grid'], color=c['text_muted'], tickfont=dict(color=c['grid'],size=9,family='JetBrains Mono'), tickcolor=c['grid']),
                showlegend=False
            )
            st.plotly_chart(fig, width='stretch')

            # Drawdown
            max_dd = dd_data['max_drawdown']
            if max_dd < 0:
                st.markdown(f'<div class="card-sub">Max Drawdown: <span style="color:#fc5c65">${max_dd:.2f}</span></div>', unsafe_allow_html=True)
        else:
            st.info("Registra al menos 2 trades para ver la curva de equity.")

    with col_right:
        # ── Estadísticas por activo ─────────────────────────────────────────
        st.markdown("**Rendimiento por Activo**")
        if not df.empty:
            por_activo = df.groupby('activo').agg(
                trades=('resultado_usd', 'count'),
                pnl=('resultado_usd', 'sum'),
                wr=('resultado_usd', lambda x: (x > 0).mean() * 100)
            ).reset_index().sort_values('pnl', ascending=False)

            fig2 = go.Figure(go.Bar(
                x=por_activo['activo'],
                y=por_activo['pnl'],
                marker_color=[c['green'] if p >= 0 else c['red'] for p in por_activo['pnl']],
                text=[f"${p:.0f}" for p in por_activo['pnl']],
                textposition='outside',
            ))
            fig2.update_layout(
                height=220, margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor=c['plot_bg'],
                xaxis=dict(color=c['text_muted'], showgrid=False, tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
                yaxis=dict(color=c['text_muted'], gridcolor=c['grid'], tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
                showlegend=False
            )
            st.plotly_chart(fig2, width='stretch')
        else:
            st.info("Sin trades registrados.")

    st.divider()

    # ── Ajustar capital inicial ──────────────────────────────────────────────
    with st.expander("⚙️ Configuración de cuenta"):
        new_cap = st.number_input("Capital inicial (USD)", value=float(capital_ini),
                                   min_value=100.0, step=100.0)
        if st.button("💾 Actualizar capital", key="btn_actualizar_capital"):
            actualizar_capital(user["id"], new_cap)
            st.session_state.user["capital_inicial"] = new_cap
            st.success("✅ Capital actualizado.")
            st.rerun()
