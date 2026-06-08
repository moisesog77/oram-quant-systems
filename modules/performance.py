"""
modules/performance.py — ORAM Quant Systems — Performance & Análisis IA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Análisis profundo del historial de trades con métricas institucionales.

Secciones:
  · KPIs principales: P&L total, win rate, trades, Sharpe, drawdown
  · Curva de equity acumulada (Plotly interactivo)
  · P&L desglosado por: activo, setup SMC, temporalidad, emoción
  · Análisis IA (RandomForest): qué variables predicen trades ganadores
    Features: activo, TF, dirección, setup, emoción, riesgo, RR planeado
    Target: trade ganador/perdedor (resultado_usd > 0)

Requiere mínimo 5 trades para el análisis IA.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database.db import obtener_trades
from utils.ai_engine import analizar_performance_ia, calcular_sharpe
from ui.styles import get_colors, page_header


def render_performance():
    user = st.session_state.user
    page_header("📊", "Performance & IA", "Análisis estadístico · Machine Learning · Psicología")

    c = get_colors()
    trades = obtener_trades(user["id"])
    if not trades:
        st.info("Registra al menos 5 trades para ver el análisis de performance.")
        return

    df = pd.DataFrame(trades)
    ia = analizar_performance_ia(df)

    # ── KPIs ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Win Rate", f"{ia['win_rate']}%",
                        delta="bueno" if ia['win_rate'] > 50 else "revisar")
    with c2: st.metric("Profit Factor", f"{ia['profit_factor']}",
                        delta="bueno" if ia['profit_factor'] > 1.5 else "revisar")
    with c3: st.metric("Expectancy", f"${ia['expectancy']:.2f}")
    with c4: st.metric("Racha win", f"{ia['racha_max_win']} 🔥")
    with c5: st.metric("Racha loss", f"{ia['racha_max_loss']} 🥶")
    with c6:
        if len(df) > 2:
            sharpe = calcular_sharpe(df['resultado_usd'])
            st.metric("Sharpe", f"{sharpe:.2f}")

    st.divider()

    # ── Recomendación IA ──────────────────────────────────────────────────
    if ia['disponible']:
        col_ia, col_stats = st.columns([1, 1])
        with col_ia:
            st.markdown("**🧠 Análisis IA**")
            acc = ia['accuracy_cv']
            acc_color = c["green"] if acc > 60 else c["red"] if acc < 50 else c["accent"]
            st.markdown(f"""
            <div class="smc-card smc-card-accent">
                <div class="card-title">Recomendación del modelo</div>
                <div style="font-size:0.95rem;margin:0.5rem 0">{ia['recomendacion']}</div>
                <div class="card-sub">Precisión CV: <span style="color:{acc_color};font-weight:700">{acc}%</span></div>
                {"<div class='card-sub' style='color:#f5a623'>⚠️ " + ia['advertencia_ia'] + "</div>" if ia['advertencia_ia'] else ""}
            </div>
            """, unsafe_allow_html=True)

            # Feature importance
            if ia['importancia_features']:
                st.markdown("**Factores más predictivos:**")
                for feat, imp in sorted(ia['importancia_features'].items(), key=lambda x: -x[1]):
                    bar_w = int(imp * 100)
                    st.markdown(f"""
                    <div style="margin:4px 0">
                        <span class="card-sub">{feat}</span>
                        <div class="conf-bar-container">
                            <div class="conf-bar-fill" style="width:{bar_w}%;background:#f5a623"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        with col_stats:
            st.markdown("**📅 Mejor sesión de trading**")
            if ia['mejor_sesion']:
                st.markdown(f"""
                <div class="smc-card smc-card-green">
                    <div class="card-title">Mejor día</div>
                    <div class="card-value">{ia['mejor_sesion']}</div>
                    <div class="card-sub">Peor día: {ia['peor_sesion']}</div>
                </div>
                """, unsafe_allow_html=True)

            if ia['mejor_setup']:
                st.markdown(f"""
                <div class="smc-card smc-card-blue">
                    <div class="card-title">Setup más rentable</div>
                    <div class="card-value" style="font-size:1rem">{ia['mejor_setup']}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info(f"🧠 {ia['mensaje']}")

    st.divider()

    # ── Gráficas ──────────────────────────────────────────────────────────
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        # Distribución de resultados
        st.markdown("**Distribución de P&L**")
        fig_hist = go.Figure(go.Histogram(
            x=df['resultado_usd'],
            nbinsx=20,
            marker_color=[c['green'] if x >= 0 else c['red'] for x in df['resultado_usd']],
        ))
        fig_hist.update_layout(
            height=250, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor=c['plot_bg'],
            xaxis=dict(color=c['text_muted'], gridcolor=c['grid'], tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
            yaxis=dict(color=c['text_muted'], gridcolor=c['grid'], tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
        )
        st.plotly_chart(fig_hist, width='stretch')

    with col_g2:
        # PnL por setup
        if 'setup' in df.columns and df['setup'].notna().any():
            st.markdown("**P&L por Setup**")
            por_setup = df[df['setup'] != ''].groupby('setup')['resultado_usd'].sum().reset_index()
            por_setup = por_setup.sort_values('resultado_usd', ascending=True)
            fig_setup = go.Figure(go.Bar(
                x=por_setup['resultado_usd'], y=por_setup['setup'],
                orientation='h',
                marker_color=[c['green'] if v >= 0 else c['red'] for v in por_setup['resultado_usd']],
            ))
            fig_setup.update_layout(
                height=250, margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor=c['plot_bg'],
                xaxis=dict(color=c['text_muted'], gridcolor=c['grid'], tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
                yaxis=dict(color=c['text_muted'], tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
            )
            st.plotly_chart(fig_setup, width='stretch')

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        # PnL por emoción
        if 'emocion' in df.columns:
            st.markdown("**P&L por Estado Emocional**")
            por_emo = df.groupby('emocion').agg(
                pnl=('resultado_usd', 'sum'),
                trades=('resultado_usd', 'count')
            ).reset_index()
            fig_emo = go.Figure(go.Bar(
                x=por_emo['emocion'], y=por_emo['pnl'],
                marker_color=[c['green'] if v >= 0 else c['red'] for v in por_emo['pnl']],
                text=[f"${v:.0f}" for v in por_emo['pnl']], textposition='outside'
            ))
            fig_emo.update_layout(
                height=230, margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor=c['plot_bg'],
                xaxis=dict(color=c['text_muted'], showgrid=False, tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
                yaxis=dict(color=c['text_muted'], gridcolor=c['grid'], tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
            )
            st.plotly_chart(fig_emo, width='stretch')
            st.caption("💡 Si ves que operar con FOMO o Revancha da pérdidas, evítalo.")

    with col_g4:
        # RR planeado vs real
        if 'rr_planeado' in df.columns and 'rr_real' in df.columns:
            st.markdown("**RR Planeado vs Real**")
            df_rr = df[(df['rr_planeado'] > 0) & (df['rr_real'] != 0)].copy()
            if not df_rr.empty:
                fig_rr = go.Figure()
                fig_rr.add_trace(go.Scatter(
                    x=df_rr.index, y=df_rr['rr_planeado'],
                    mode='lines+markers', name='RR Planeado',
                    line=dict(color='#4fc3f7', width=2)
                ))
                fig_rr.add_trace(go.Scatter(
                    x=df_rr.index, y=df_rr['rr_real'],
                    mode='lines+markers', name='RR Real',
                    line=dict(color=c['accent'], width=2)
                ))
                fig_rr.update_layout(
                    height=230, margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor=c['plot_bg'],
                    xaxis=dict(color=c['text_muted'], showgrid=False, tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
                    yaxis=dict(color=c['text_muted'], gridcolor=c['grid'], tickfont=dict(color=c['text_muted'],size=9,family='JetBrains Mono'), tickcolor=c['text_muted']),
                    legend=dict(font=dict(color=c['text_muted']), bgcolor='rgba(0,0,0,0)')
                )
                st.plotly_chart(fig_rr, width='stretch')

    # ── Advertencia final ──────────────────────────────────────────────────
    st.divider()
    st.markdown("""
    <div class="smc-card smc-card-red">
        <div class="card-title">⚠️ Recordatorio de gestión de riesgo</div>
        <div class="card-sub">
        • Nunca arriesgues más del 1-2% por trade · El Profit Factor debe ser > 1.5 para ser consistente<br>
        • El drawdown máximo recomendado es 10-15% del capital · Si estás en racha de 3+ pérdidas seguidas, para el día<br>
        • La IA de esta herramienta es orientativa, no es una señal de entrada automática
        </div>
    </div>
    """, unsafe_allow_html=True)
