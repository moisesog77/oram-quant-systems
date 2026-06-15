"""
modules/backtesting.py — ORAM Quant Systems — Backtesting SMC
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.backtesting import ejecutar_backtest
from utils.market_data import ACTIVOS_DEFAULT
from database.db import guardar_backtest, obtener_backtests
from ui.styles import get_colors, page_header, oram_notify, get_theme, inject_module_css



def _bt_overlay(ticker: str, tf: str, umbral: int, capital: float, dark: bool):
    """Muestra overlay premium de carga SIN rerun — se limpia al terminar."""
    overlay_bg = "rgba(6,9,15,0.93)"  if dark else "rgba(238,242,247,0.95)"
    card_bg    = "#0c1219"            if dark else "#ffffff"
    card_bdr   = "#1b3a24"           if dark else "#d1fae5"
    text_col   = "#edf4ff"           if dark else "#0b1824"
    text_muted = "#637a94"           if dark else "#7a8fa0"

    ph = st.empty()
    ph.markdown(f"""
<style>
@keyframes oram-bt-in {{
    from {{ opacity:0; transform:translateY(16px) scale(0.96); }}
    to   {{ opacity:1; transform:translateY(0) scale(1); }}
}}
@keyframes oram-spin {{
    to {{ transform: rotate(360deg); }}
}}
#oram-bt-overlay {{
    position:fixed; inset:0; background:{overlay_bg};
    backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);
    z-index:99999; display:flex; align-items:center; justify-content:center;
}}
#oram-bt-card {{
    background:{card_bg}; border:1px solid {card_bdr};
    border-radius:20px; padding:2.8rem 3.2rem 2.6rem;
    text-align:center; max-width:440px; width:92%;
    animation:oram-bt-in 0.42s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow:0 24px 60px rgba(0,0,0,0.38);
}}
.oram-bt-icon {{
    width:72px; height:72px; border-radius:50%;
    border:3px solid #22c55e;
    display:flex; align-items:center; justify-content:center;
    margin:0 auto 1.2rem;
    box-shadow:0 0 0 8px rgba(34,197,94,0.12);
}}
.oram-bt-spinner {{
    width:20px; height:20px;
    border:2.5px solid rgba(34,197,94,0.25);
    border-top-color:#22c55e;
    border-radius:50%;
    display:inline-block;
    animation:oram-spin 0.8s linear infinite;
    vertical-align:middle; margin-right:0.5rem;
}}
</style>
<div id="oram-bt-overlay"><div id="oram-bt-card">
  <div class="oram-bt-icon">
    <svg width="32" height="32" fill="none" stroke="#22c55e" stroke-width="2.5"
         stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
      <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>
  </div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:0.65rem;
              letter-spacing:2px;color:#22c55e;font-weight:600;margin-bottom:0.5rem">
    ORAM Quant Systems
  </div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:1.3rem;
              font-weight:700;color:{text_col};margin-bottom:0.5rem">
    🧪 Ejecutando Backtest
  </div>
  <div style="font-family:Inter,sans-serif;font-size:0.88rem;color:{text_muted};margin-bottom:1.4rem">
    <b style="color:{text_col}">{ticker}</b> · {tf} · Umbral {umbral}% · Capital ${capital:,.0f}
  </div>
  <div style="font-family:Inter,sans-serif;font-size:0.78rem;
              letter-spacing:1.5px;text-transform:uppercase;color:{text_muted}">
    <span class="oram-bt-spinner"></span>Analizando señales históricas…
  </div>
</div></div>
""", unsafe_allow_html=True)
    return ph


def render_backtesting():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"

    page_header("🧪", "Backtesting SMC", "Prueba la estrategia sobre datos históricos reales")
    inject_module_css(dark)

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
            capital    = st.number_input("Capital (USD)", value=float(user.get("capital_inicial", 10000)),
                                          min_value=100.0, step=500.0, key="bt_cap")
        with col3:
            umbral = st.slider("Umbral confianza (%)", 30, 85, 50, key="bt_umb",
                               help="Bájalo a 40-50% para ver más señales.")
            riesgo_pct = st.slider("Riesgo por trade (%)", 0.5, 3.0, 1.0, step=0.25, key="bt_rsk")

        with st.expander("⚙️ Parámetros de realismo (spread/slippage)"):
            c1s, c2s = st.columns(2)
            with c1s:
                spread_pips = st.number_input(
                    "Spread (pips)", min_value=0.0, max_value=10.0,
                    value=1.5, step=0.5, key="bt_spread",
                    help="Spread típico: EURUSD/GBPUSD ~1-2 pips, XAUUSD ~20-30 pips")
            with c2s:
                slippage_pips = st.number_input(
                    "Slippage (pips)", min_value=0.0, max_value=5.0,
                    value=0.5, step=0.25, key="bt_slip",
                    help="Slippage estimado en ejecución de órdenes")
            st.caption(f"💡 Costo total por trade: **{spread_pips + slippage_pips:.1f} pips** — "
                       "simula condiciones reales de broker")

        st.caption(
            "💡 **Consejo:** Usa 1h o 4h para backtests más robustos. "
            "El timeframe 15m tiene menos historia disponible en yfinance."
        )

        if st.button("▶️ Ejecutar Backtest", width='stretch', key="bt_run"):
            # 1. Mostrar overlay premium mientras trabaja
            overlay_ph = _bt_overlay(ticker, tf, umbral, capital, dark)

            # 2. Ejecutar el backtest (con overlay visible)
            res = ejecutar_backtest(ticker, tf, riesgo_pct, umbral, capital,
                                    spread_pips=spread_pips, slippage_pips=slippage_pips)

            # 3. Limpiar overlay al terminar
            overlay_ph.empty()

            if "error" in res:
                oram_notify("error", f"❌ {res['error']}", toast=True, banner=False)
                oram_notify("info", "💡 Prueba: umbral más bajo (40-50%), timeframe con más datos (1h/4h/1d), o diferente activo.", toast=True, banner=False)
            else:

                # ── KPIs ──────────────────────────────────────────────────
                params = res.get("parametros", {})
                sp = params.get("spread_pips", 0) + params.get("slippage_pips", 0)
                st.caption(f"📊 Resultado con spread+slippage de **{sp:.1f} pips** por trade")
                k1, k2, k3, k4, k5, k6 = st.columns(6)
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
                        height=260, margin=dict(l=0, r=0, t=10, b=0),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=c["plot_bg"],
                        xaxis=dict(showgrid=False, color=c["text_muted"], title="Trade #",
                                   tickfont=dict(color=c["text_muted"], size=9, family='JetBrains Mono'),
                                   tickcolor=c["text_muted"]),
                        yaxis=dict(gridcolor=c["grid"], color=c["text_muted"], title="Capital USD",
                                   tickfont=dict(color=c["grid"], size=9, family='JetBrains Mono'),
                                   tickcolor=c["grid"]),
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
                            if isinstance(val, (int, float)):
                                return "color:#26de81" if val > 0 else "color:#fc5c65" if val < 0 else ""
                            return ""
                        st.dataframe(
                            df_t.style.map(color_r, subset=["resultado_r"]),
                            width='stretch', height=300
                        )

                try:
                    guardar_backtest(user["id"], {
                        "ticker": ticker, "timeframe": tf,
                        "fecha_inicio": res["fecha_inicio"], "fecha_fin": res["fecha_fin"],
                        "total_trades": res["total_trades"], "win_rate": res["win_rate"],
                        "profit_factor": res["profit_factor"], "total_pnl": res["total_pnl"],
                        "max_drawdown": res["max_drawdown"], "sharpe": res["sharpe"],
                        "parametros": res["parametros"],
                    })
                except Exception:
                    pass  # La tabla puede no existir en ciertos entornos; no crashear la UI

    with tab_historial:
        backtests = obtener_backtests(user["id"])
        if not backtests:
            st.info("No hay backtests guardados aún.")
            return
        df_bt = pd.DataFrame(backtests)
        cols_show = ["created_at", "ticker", "timeframe", "total_trades",
                     "win_rate", "profit_factor", "total_pnl", "max_drawdown", "sharpe"]
        st.dataframe(df_bt[[col for col in cols_show if col in df_bt.columns]],
                     width='stretch')
