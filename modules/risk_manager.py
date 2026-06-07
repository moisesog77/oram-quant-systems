"""
modules/risk_manager.py — ORAM Quant Systems — Gestor de Riesgo Institucional
"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from ui.styles import get_colors, page_header, get_theme


def _inject_rm_css(dark: bool, c: dict):
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
.stSelectbox label, .stNumberInput label, .stSlider label {{
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

/* ══ NUMBER INPUT — igual a live_analysis, sin cuadro extra ══════════════ */
[data-testid="stNumberInput"] {{
    background: transparent !important; border: none !important;
}}
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
    height: 46px !important; -moz-appearance: textfield !important;
}}
[data-testid="stNumberInput"] input::-webkit-outer-spin-button,
[data-testid="stNumberInput"] input::-webkit-inner-spin-button {{
    -webkit-appearance: none !important; margin: 0 !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2) > div:last-child {{
    display: flex !important; align-items: center !important;
    align-self: stretch !important; height: 100% !important;
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
/* Eliminar cuadro extra al editar manualmente */
[data-testid="stNumberInput"] > input:last-child,
[data-testid="stNumberInput"] > div:last-child:not(:nth-child(2)),
[data-testid="stNumberInput"] > *:nth-child(n+3) {{
    display: none !important; visibility: hidden !important;
    height: 0 !important; margin: 0 !important; padding: 0 !important;
    border: none !important; opacity: 0 !important;
    position: absolute !important; pointer-events: none !important;
}}
[data-testid="InputInstructions"] {{
    display: none !important; visibility: hidden !important;
    height: 0 !important; margin: 0 !important;
}}

/* ══ BOTÓN SIMULAR ════════════════════════════════════════════════════════ */
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


def _resultado_overlay(prob_ruina: float, dark: bool):
    """Overlay premium con resultado de simulación Monte Carlo."""
    import time

    overlay_bg = "rgba(6,9,15,0.93)"  if dark else "rgba(238,242,247,0.95)"
    card_bg    = "#0c1219"            if dark else "#ffffff"
    text_muted = "#637a94"            if dark else "#7a8fa0"

    if prob_ruina > 20:
        icon    = "❌"
        color   = "#f87171"
        card_bdr = "#3d1a1a" if dark else "#f8d0d0"
        titulo  = "Riesgo de ruina alto"
        msg     = f"Probabilidad de ruina: <b>{prob_ruina:.1f}%</b>. Reduce el riesgo por trade o mejora tu edge."
    elif prob_ruina > 10:
        icon    = "⚠️"
        color   = "#fbbf24"
        card_bdr = "#3a3010" if dark else "#fef3c7"
        titulo  = "Riesgo moderado"
        msg     = f"Probabilidad de ruina: <b>{prob_ruina:.1f}%</b>. Considera reducir el tamaño de posición."
    else:
        icon    = "✅"
        color   = "#22c55e"
        card_bdr = "#1b3a24" if dark else "#d1fae5"
        titulo  = "Gestión de capital sólida"
        msg     = f"Probabilidad de ruina: <b>{prob_ruina:.1f}%</b>. Riesgo controlado."

    ph = st.empty()
    ph.markdown(f"""
<style>
@keyframes oram-rm-in {{
    from {{ opacity:0; transform:translateY(16px) scale(0.96); }}
    to   {{ opacity:1; transform:translateY(0) scale(1); }}
}}
#oram-rm-overlay {{
    position:fixed; inset:0; background:{overlay_bg};
    backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);
    z-index:99999; display:flex; align-items:center; justify-content:center;
}}
#oram-rm-card {{
    background:{card_bg}; border:1px solid {card_bdr};
    border-radius:20px; padding:2.8rem 3.2rem 2.6rem;
    text-align:center; max-width:420px; width:92%;
    animation:oram-rm-in 0.42s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow:0 24px 60px rgba(0,0,0,0.38);
}}
</style>
<div id="oram-rm-overlay"><div id="oram-rm-card">
  <div style="font-size:3.2rem;margin-bottom:1rem">{icon}</div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:0.62rem;
              letter-spacing:2px;color:#22c55e;font-weight:600;margin-bottom:0.4rem">
    ORAM · Risk Manager
  </div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:1.25rem;
              font-weight:700;color:{color};margin-bottom:0.7rem">
    {titulo}
  </div>
  <div style="font-family:Inter,sans-serif;font-size:0.9rem;
              color:{text_muted};line-height:1.6">
    {msg}
  </div>
  <div style="margin-top:1.4rem;font-family:Inter,sans-serif;
              font-size:0.78rem;color:{text_muted};opacity:0.7">
    Cerrando automáticamente…
  </div>
</div></div>
""", unsafe_allow_html=True)
    time.sleep(2.4)
    ph.empty()


def render_risk_manager():
    c    = get_colors()
    dark = get_theme() == "dark"
    page_header("🛡️", "Risk Manager", "Calculadora de posición · Kelly Criterion · Simulación de ruina")
    _inject_rm_css(dark, c)

    tab_calc, tab_kelly, tab_ruina = st.tabs(["📐 Calculadora", "📊 Kelly Criterion", "💀 Riesgo de Ruina"])

    # ── CALCULADORA ────────────────────────────────────────────────────────
    with tab_calc:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Datos de la operación**")
            capital    = st.number_input("Capital total (USD)", value=10000.0, min_value=100.0, step=500.0, key="rm_cap")
            riesgo_pct = st.slider("% de riesgo por trade", 0.25, 5.0, 1.0, step=0.25, key="rm_rsk")
            entrada    = st.number_input("Precio de entrada", value=1.08500, format="%.5f", key="rm_en")
            sl         = st.number_input("Stop Loss",         value=1.08200, format="%.5f", key="rm_sl")
            tp         = st.number_input("Take Profit",       value=1.09100, format="%.5f", key="rm_tp")
            par        = st.selectbox("Par (para pip value)", [
                "Forex 4 dec (EURUSD,GBPUSD…)",
                "Forex JPY (USDJPY…)",
                "Cripto / Índices"
            ])

        if entrada > 0 and sl > 0 and tp > 0:
            dist_sl    = abs(entrada - sl)
            dist_tp    = abs(tp - entrada)
            rr         = dist_tp / dist_sl if dist_sl > 0 else 0
            riesgo_usd = capital * riesgo_pct / 100

            if par == "Forex 4 dec (EURUSD,GBPUSD…)":
                pips_sl   = dist_sl * 10000
                pip_value = 10.0
            elif par == "Forex JPY (USDJPY…)":
                pips_sl   = dist_sl * 100
                pip_value = 9.0
            else:
                pips_sl   = dist_sl
                pip_value = 1.0

            lotes        = riesgo_usd / (pips_sl * pip_value) if pips_sl > 0 else 0
            ganancia_pot = riesgo_usd * rr

            with col2:
                st.markdown("**Resultados**")
                st.markdown(f"""
                <div class="smc-card smc-card-accent">
                    <div class="card-title">Tamaño de posición</div>
                    <div class="card-value">{lotes:.3f} lotes</div>
                    <div class="card-sub">= {lotes*100:.1f} mini-lotes = {lotes*1000:.0f} micro-lotes</div>
                </div>
                """, unsafe_allow_html=True)

                cols_r = st.columns(2)
                cols_r[0].metric("Riesgo USD",    f"${riesgo_usd:.2f}")
                cols_r[1].metric("RR",            f"{rr:.2f}:1")
                cols_r[0].metric("Pips SL",       f"{pips_sl:.1f}")
                cols_r[1].metric("Ganancia pot.", f"${ganancia_pot:.2f}")

                if rr >= 2:
                    st.success(f"✅ RR {rr:.1f}:1 — Buena relación riesgo/beneficio")
                elif rr >= 1.5:
                    st.warning(f"⚠️ RR {rr:.1f}:1 — Aceptable, prefiere ≥2:1")
                else:
                    st.error(f"❌ RR {rr:.1f}:1 — Demasiado bajo, evita esta operación")

                if riesgo_pct > 2:
                    st.error(f"⚠️ Riesgo {riesgo_pct}% — Excede el máximo recomendado (1-2%)")

    # ── KELLY CRITERION ───────────────────────────────────────────────────
    with tab_kelly:
        st.markdown(f"""
        <div class="smc-card smc-card-blue">
            <div class="card-title">¿Qué es Kelly Criterion?</div>
            <div class="card-sub">
            Fórmula matemática que calcula el % óptimo de capital a arriesgar por trade
            para maximizar el crecimiento a largo plazo, basándose en tu win rate y RR históricos.
            <br><b>Kelly% = W - (1-W)/R</b> donde W=win rate, R=RR promedio
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            wr_k  = st.slider("Win Rate histórico (%)", 30, 80, 50, key="k_wr") / 100
            rr_k  = st.slider("RR promedio", 1.0, 5.0, 2.0, step=0.1, key="k_rr")
            cap_k = st.number_input("Capital (USD)", value=10000.0, step=500.0, key="k_cap")

        kelly_full = max(0, wr_k - (1 - wr_k) / rr_k)
        kelly_half = kelly_full / 2
        kelly_qrt  = kelly_full / 4

        with col2:
            st.markdown(f"""
            <div class="smc-card smc-card-accent">
                <div class="card-title">Kelly Criterion</div>
                <div class="card-value">{kelly_full*100:.1f}%</div>
                <div class="card-sub">Full Kelly (agresivo) = ${cap_k*kelly_full:.0f}</div>
            </div>
            <div class="smc-card smc-card-green" style="margin-top:0.75rem">
                <div class="card-title">Half Kelly (recomendado)</div>
                <div class="card-value">{kelly_half*100:.1f}%</div>
                <div class="card-sub">= ${cap_k*kelly_half:.0f} por trade</div>
            </div>
            <div class="smc-card smc-card-blue" style="margin-top:0.75rem">
                <div class="card-title">Quarter Kelly (conservador)</div>
                <div class="card-value">{kelly_qrt*100:.1f}%</div>
                <div class="card-sub">= ${cap_k*kelly_qrt:.0f} por trade</div>
            </div>
            """, unsafe_allow_html=True)
            if kelly_full <= 0:
                st.error("❌ Estrategia con pérdida esperada. Mejora tu win rate o RR.")

    # ── SIMULACIÓN DE RUINA ───────────────────────────────────────────────
    with tab_ruina:
        st.markdown("**Simulación Monte Carlo — Riesgo de Ruina**")
        col1, col2 = st.columns(2)
        with col1:
            wr_r  = st.slider("Win Rate (%)", 30, 75, 50, key="r_wr") / 100
            rr_r  = st.slider("RR promedio", 1.0, 4.0, 2.0, step=0.1, key="r_rr")
            rsk_r = st.slider("Riesgo por trade (%)", 0.5, 5.0, 1.0, step=0.25, key="r_rsk")
            n_op  = st.slider("Número de operaciones", 50, 500, 200, key="r_nop")
        with col2:
            ruina_pct = st.slider("Ruina = pérdida de (%)", 20, 80, 50, key="r_ruin")
            n_sim     = st.select_slider("Simulaciones Monte Carlo", [100,500,1000,2000], value=500, key="r_sim")

        if st.button("🎲 Simular", width='stretch', key="sim_btn"):
            np.random.seed(42)
            ruinas = 0
            trayectorias = []

            for _ in range(n_sim):
                capital_sim = 100.0
                tray = [capital_sim]
                arruinado = False
                for _ in range(n_op):
                    if np.random.random() < wr_r:
                        capital_sim *= (1 + rsk_r/100 * rr_r)
                    else:
                        capital_sim *= (1 - rsk_r/100)
                    tray.append(round(capital_sim, 2))
                    if capital_sim <= (100 * (1 - ruina_pct/100)):
                        arruinado = True
                        break
                if arruinado:
                    ruinas += 1
                trayectorias.append(tray)

            prob_ruina = ruinas / n_sim * 100
            tray_med   = np.median([t[-1] for t in trayectorias])
            tray_p10   = np.percentile([t[-1] for t in trayectorias], 10)
            tray_p90   = np.percentile([t[-1] for t in trayectorias], 90)

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            col_r1.metric("Probabilidad de Ruina", f"{prob_ruina:.1f}%",
                           delta="✅ Seguro" if prob_ruina < 10 else "⚠️ Alto riesgo")
            col_r2.metric("Capital mediano final", f"{tray_med:.0f}%")
            col_r3.metric("Peor 10%",              f"{tray_p10:.0f}%")
            col_r4.metric("Mejor 90%",             f"{tray_p90:.0f}%")

            fig = go.Figure()
            sample = np.random.choice(len(trayectorias), min(50, len(trayectorias)), replace=False)
            for i in sample:
                tray = trayectorias[i]
                final_color = "rgba(38,222,129,0.33)" if tray[-1] >= 100 else "rgba(252,92,101,0.33)"
                fig.add_trace(go.Scatter(y=tray, mode="lines",
                    line=dict(color=final_color, width=0.8), showlegend=False))
            fig.add_hline(y=100*(1-ruina_pct/100),
                          line=dict(color=c["red"], width=2, dash="dash"),
                          annotation_text=f"Nivel de ruina ({ruina_pct}% pérdida)")
            fig.update_layout(
                height=320, margin=dict(l=0, r=0, t=10, b=0),
                title=dict(text=f"Monte Carlo — {n_sim} simulaciones · {n_op} trades cada una",
                           font=dict(size=11, color=c["text_muted"])),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=c["plot_bg"],
                xaxis=dict(title="Trade #", color=c["text_muted"], gridcolor=c["grid"],
                           tickfont=dict(color=c["text_muted"], size=9, family='JetBrains Mono'),
                           tickcolor=c["text_muted"]),
                yaxis=dict(title="Capital (%)", color=c["text_muted"], gridcolor=c["grid"]),
            )
            st.plotly_chart(fig, width='stretch')

            # Overlay premium en lugar de oram_notify con banner
            _resultado_overlay(prob_ruina, dark)
