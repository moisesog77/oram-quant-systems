"""
modules/risk_manager.py — Calculadora avanzada de riesgo y Kelly Criterion.
"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from ui.styles import get_colors, page_header, oram_notify

def render_risk_manager():
    c = get_colors()
    page_header("🛡️", "Risk Manager", "Calculadora de posición · Kelly Criterion · Simulación de ruina")

    tab_calc, tab_kelly, tab_ruina = st.tabs(["📐 Calculadora", "📊 Kelly Criterion", "💀 Riesgo de Ruina"])

    # ── CALCULADORA ────────────────────────────────────────────────────────
    with tab_calc:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Datos de la operación**")
            capital   = st.number_input("Capital total (USD)", value=10000.0, min_value=100.0, step=500.0, key="rm_cap")
            riesgo_pct = st.slider("% de riesgo por trade", 0.25, 5.0, 1.0, step=0.25, key="rm_rsk")
            entrada   = st.number_input("Precio de entrada",  value=1.08500, format="%.5f", key="rm_en")
            sl        = st.number_input("Stop Loss",          value=1.08200, format="%.5f", key="rm_sl")
            tp        = st.number_input("Take Profit",        value=1.09100, format="%.5f", key="rm_tp")
            par       = st.selectbox("Par (para pip value)", ["Forex 4 dec (EURUSD,GBPUSD…)","Forex JPY (USDJPY…)","Cripto / Índices"])

        if entrada > 0 and sl > 0 and tp > 0:
            dist_sl   = abs(entrada - sl)
            dist_tp   = abs(tp - entrada)
            rr        = dist_tp / dist_sl if dist_sl > 0 else 0
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

            lotes = riesgo_usd / (pips_sl * pip_value) if pips_sl > 0 else 0
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

                # Semáforo
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
            rr_k  = st.slider("RR promedio",             1.0, 5.0, 2.0, step=0.1, key="k_rr")
            cap_k = st.number_input("Capital (USD)", value=10000.0, step=500.0, key="k_cap")

        kelly_full = wr_k - (1 - wr_k) / rr_k
        kelly_half = kelly_full / 2  # Half Kelly — más conservador
        kelly_qrt  = kelly_full / 4  # Quarter Kelly

        kelly_full = max(0, kelly_full)
        kelly_half = max(0, kelly_half)
        kelly_qrt  = max(0, kelly_qrt)

        with col2:
            st.markdown(f"""
            <div class="smc-card smc-card-accent">
                <div class="card-title">Kelly Criterion</div>
                <div class="card-value">{kelly_full*100:.1f}%</div>
                <div class="card-sub">Full Kelly (agresivo) = ${cap_k*kelly_full:.0f}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div class="smc-card smc-card-green">
                <div class="card-title">Half Kelly (recomendado)</div>
                <div class="card-value">{kelly_half*100:.1f}%</div>
                <div class="card-sub">= ${cap_k*kelly_half:.0f} por trade</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div class="smc-card smc-card-blue">
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
            wr_r   = st.slider("Win Rate (%)", 30, 75, 50, key="r_wr") / 100
            rr_r   = st.slider("RR promedio", 1.0, 4.0, 2.0, step=0.1, key="r_rr")
            rsk_r  = st.slider("Riesgo por trade (%)", 0.5, 5.0, 1.0, step=0.25, key="r_rsk")
            n_op   = st.slider("Número de operaciones", 50, 500, 200, key="r_nop")
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

            # Graficar muestra de trayectorias
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
                height=320, margin=dict(l=0,r=0,t=10,b=0),
                title=dict(text=f"Monte Carlo — {n_sim} simulaciones · {n_op} trades cada una",
                           font=dict(size=11, color=c["text_muted"])),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=c["plot_bg"],
                xaxis=dict(title="Trade #", color=c["text_muted"], gridcolor=c["grid"], tickfont=dict(color=c["text_muted"],size=9,family='JetBrains Mono'), tickcolor=c["text_muted"]),
                yaxis=dict(title="Capital (%)", color=c["text_muted"], gridcolor=c["grid"]),
            )
            st.plotly_chart(fig, width='stretch')

            if prob_ruina > 20:
                oram_notify("error",   f"⚠️ Probabilidad de ruina alta ({prob_ruina:.1f}%). Reduce el riesgo por trade o mejora tu edge.", toast=True, banner=True)
            elif prob_ruina > 10:
                oram_notify("warning", f"⚠️ Riesgo moderado ({prob_ruina:.1f}%). Considera reducir tamaño de posición.", toast=True, banner=True)
            else:
                oram_notify("success", f"✅ Riesgo de ruina controlado ({prob_ruina:.1f}%). Buena gestión de capital.", toast=True, banner=True)
