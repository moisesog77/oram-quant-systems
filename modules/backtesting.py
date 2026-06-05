"""
modules/backtesting.py — ORAM Quant Systems — Backtesting SMC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Prueba la estrategia SMC sobre datos históricos reales de yfinance.

Motor (utils/backtesting.ejecutar_backtest):
  · Ventana deslizante de 80 velas para señales SMC
  · SL = ATR × 1.5 / TP = ATR × 3.0
  · Filtra señales por umbral de confianza configurable
  · Simula P&L con % de riesgo por trade sobre capital inicial

KPIs mostrados: Total trades, Win Rate, Profit Factor, P&L total,
Max Drawdown, Sharpe Ratio, gráfica de equity del backtest.

Tabs:
  ▶️ Nuevo Backtest → configurar ticker/TF/umbral/capital/riesgo + ejecutar
  📋 Historial      → últimos backtests guardados en DB por usuario
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.backtesting import ejecutar_backtest
from utils.market_data import ACTIVOS_DEFAULT
from database.db import guardar_backtest, obtener_backtests
from ui.styles import get_colors, page_header, oram_notify


def render_backtesting():
    user = st.session_state.user
    c    = get_colors()

    page_header("🧪", "Backtesting SMC", "Prueba la estrategia sobre datos históricos reales")

    st.markdown(f"""
    <div class="smc-card smc-card-accent">
        <div class="card-title">¿Cómo funciona?</div>
        <div class="card-sub">
        El motor analiza cada vela histórica disponible con una ventana SMC de 80 velas.
        Filtra por umbral de confianza y simula SL/TP basados en ATR (1.5x / 3x).
        Los resultados son orientativos — el mercado real incluye spread y slippage.
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_nuevo, tab_historial = st.tabs(["▶️ Nuevo Backtest", "📋 Historial"])

    with tab_nuevo:
        col1, col2, col3 = st.columns(3)
        with col1:
            cat    = st.selectbox("Categoría",    list(ACTIVOS_DEFAULT.keys()), key="bt_cat")
            ticker = st.selectbox("Activo",        ACTIVOS_DEFAULT[cat],         key="bt_tk")
        with col2:
            tf     = st.selectbox("Temporalidad", ["15m","30m","1h","4h","1d"],  key="bt_tf")
            umbral = st.slider("Umbral confianza (%)", 30, 85, 50, key="bt_umb",
                               help="Bájalo a 40-50% para ver más señales. Súbelo para señales de mayor calidad.")
        with col3:
            capital    = st.number_input("Capital (USD)", value=float(user.get("capital_inicial",10000)),
                                          min_value=100.0, step=500.0, key="bt_cap")
            riesgo_pct = st.slider("Riesgo por trade (%)", 0.5, 3.0, 1.0, step=0.25, key="bt_rsk")

        st.caption(
            "💡 **Consejo:** Usa 1h o 4h para backtests más robustos. "
            "El timeframe 15m tiene menos historia disponible en yfinance."
        )

        if st.button("▶️ Ejecutar Backtest", width='stretch', key="bt_run"):
            with st.spinner(f"Ejecutando backtest {ticker} {tf} (puede tardar 30-90 seg)..."):
                res = ejecutar_backtest(ticker, tf, riesgo_pct, umbral, capital)

            if "error" in res:
                oram_notify("error", f"❌ {res['error']}", toast=True, banner=True)
                oram_notify("info", "💡 Prueba: umbral más bajo (40-50%), timeframe con más datos (1h/4h/1d), o diferente activo.", toast=False, banner=True)
            else:
                oram_notify(
                    "success",
                    f"✅ Backtest completado: **{res['total_trades']}** operaciones "
                    f"de {res.get('señales_analizadas', 0)} señales analizadas",
                    toast=True, banner=True
                )

                # ── KPIs ──────────────────────────────────────────────────
                k1,k2,k3,k4,k5,k6 = st.columns(6)
                k1.metric("Trades",        res["total_trades"])
                k2.metric("Win Rate",      f"{res['win_rate']:.1f}%",
                           delta="✅ bueno" if res["win_rate"] > 50 else "⚠️ bajo")
                k3.metric("Profit Factor", f"{res['profit_factor']:.2f}",
                           delta="✅" if res["profit_factor"] > 1.5 else "⚠️")
                k4.metric("Total R",       f"{res['total_r']:+.1f}R")
                k5.metric("PnL USD",       f"${res['total_pnl']:+,.0f}")
                k6.metric("Max Drawdown",  f"${res['max_drawdown']:.0f}")

                st.divider()
                col_eq, col_info = st.columns([3, 1])

                with col_eq:
                    st.markdown("**Curva de Equity**")
                    eq = res["equity_curve"]
                    color_line = c["green"] if eq[-1] >= eq[0] else c["red"]
                    fill_color = "rgba(38,222,129,0.08)" if eq[-1] >= eq[0] else "rgba(252,92,101,0.08)"
                    fig = go.Figure(go.Scatter(
                        y=eq, mode="lines",
                        line=dict(color=color_line, width=2),
                        fill="tozeroy", fillcolor=fill_color,
                    ))
                    fig.update_layout(
                        height=260, margin=dict(l=0,r=0,t=10,b=0),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=c["plot_bg"],
                        xaxis=dict(showgrid=False, color=c["text_muted"], title="Trade #", tickfont=dict(color=c["text_muted"],size=9,family='JetBrains Mono'), tickcolor=c["text_muted"]),
                        yaxis=dict(gridcolor=c["grid"], color=c["text_muted"], title="Capital USD", tickfont=dict(color=c["grid"],size=9,family='JetBrains Mono'), tickcolor=c["grid"]),
                        showlegend=False,
                    )
                    st.plotly_chart(fig, width='stretch')

                with col_info:
                    st.markdown(f"""
                    <div class="smc-card smc-card-accent">
                        <div class="card-title">Resumen</div>
                        <div class="card-sub">Período:<br>{res['fecha_inicio'][:10]}<br>→ {res['fecha_fin'][:10]}</div>
                        <div class="card-sub" style="margin-top:0.5rem">Capital inicial: ${capital:,.0f}</div>
                        <div class="card-sub">Capital final: <b>${res['capital_final']:,.0f}</b></div>
                        <div class="card-sub">Sharpe: <b>{res['sharpe']:.2f}</b></div>
                        <div class="card-sub">Expectancy: <b>{res['expectancy_r']:.3f}R</b></div>
                    </div>
                    """, unsafe_allow_html=True)

                    por_tipo = res.get("por_tipo", {})
                    if por_tipo:
                        st.markdown("**Por tipo de señal:**")
                        for tipo, data in sorted(por_tipo.items(), key=lambda x: -x[1]["total"]):
                            wr = data["ganados"] / data["total"] * 100 if data["total"] else 0
                            st.markdown(
                                f'<div class="card-sub">{tipo or "Sin tipo"}: '
                                f'{data["total"]} ({wr:.0f}% WR)</div>',
                                unsafe_allow_html=True
                            )

                with st.expander("📋 Ver todos los trades simulados"):
                    df_t = pd.DataFrame(res["trades"])
                    if not df_t.empty:
                        def color_r(val):
                            if isinstance(val, (int,float)):
                                return "color:#26de81" if val > 0 else "color:#fc5c65" if val < 0 else ""
                            return ""
                        st.dataframe(
                            df_t.style.map(color_r, subset=["resultado_r"]),
                            width='stretch', height=300
                        )

                guardar_backtest(user["id"], {
                    "ticker":ticker, "timeframe":tf,
                    "fecha_inicio":res["fecha_inicio"], "fecha_fin":res["fecha_fin"],
                    "total_trades":res["total_trades"], "win_rate":res["win_rate"],
                    "profit_factor":res["profit_factor"], "total_pnl":res["total_pnl"],
                    "max_drawdown":res["max_drawdown"], "sharpe":res["sharpe"],
                    "parametros":res["parametros"],
                })

    with tab_historial:
        backtests = obtener_backtests(user["id"])
        if not backtests:
            st.info("No hay backtests guardados aún.")
            return
        df_bt = pd.DataFrame(backtests)
        cols_show = ["created_at","ticker","timeframe","total_trades",
                     "win_rate","profit_factor","total_pnl","max_drawdown","sharpe"]
        st.dataframe(df_bt[[col for col in cols_show if col in df_bt.columns]],
                     width='stretch')
