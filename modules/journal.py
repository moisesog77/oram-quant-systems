"""
modules/journal.py — Diario de trades.
Incorpora: setup SMC, emoción, timeframe, tags, preview RR, filtros avanzados.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database.db import insertar_trade, obtener_trades, eliminar_trade
from utils.market_data import ACTIVOS_DEFAULT
from utils.smc_engine import calcular_riesgo
from ui.styles import get_colors, page_header

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

            if st.form_submit_button("💾 Guardar Trade", use_container_width=True):
                if entrada == 0 or sl == 0 or tp == 0:
                    st.error("Entrada, SL y TP son obligatorios.")
                else:
                    insertar_trade(user["id"], {
                        "fecha": str(fecha), "activo": activo, "timeframe": tf,
                        "direccion": direccion, "entrada": entrada, "sl": sl, "tp": tp,
                        "riesgo_usd": riesgo_usd, "resultado_usd": resultado_usd,
                        "setup": setup, "emocion": emocion, "notas": notas,
                        "tags": [t.strip() for t in tags.split(",") if t.strip()],
                        "estado": estado,
                    })
                    st.success("✅ Trade guardado.")
                    st.rerun()

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
        st.dataframe(styled, use_container_width=True, height=400)

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
                if st.button("🗑️ Eliminar", use_container_width=True):
                    eliminar_trade(del_id, user["id"])
                    st.success("Trade eliminado.")
                    st.rerun()
