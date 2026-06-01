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
    page_header("⬛", "Dashboard", f"Bienvenido, {user['username'].upper()}")

    c = get_colors()
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
        if st.button("Actualizar capital"):
            actualizar_capital(user["id"], new_cap)
            st.session_state.user["capital_inicial"] = new_cap
            st.success("Capital actualizado.")
            st.rerun()
