"""
modules/journal.py — ORAM Quant Systems — Diario de Trades
"""
import streamlit as st
import pandas as pd
from datetime import date
from database.db import insertar_trade, obtener_trades, eliminar_trade, actualizar_trade
from utils.market_data import ACTIVOS_DEFAULT
from utils.smc_engine import calcular_riesgo
from ui.styles import get_colors, page_header, oram_bienvenida, get_theme, inject_module_css



def _overlay_error(mensaje: str, dark: bool = True) -> None:
    """Overlay premium de error."""
    import time
    dark = get_theme() == "dark"
    overlay_bg = "rgba(6,9,15,0.92)"  if dark else "rgba(238,242,247,0.94)"
    card_bg    = "#0c1219"            if dark else "#ffffff"
    card_bdr   = "#3d1a1a"            if dark else "#f8d0d0"
    text_muted = "#637a94"            if dark else "#7a8fa0"

    ph = st.empty()
    ph.markdown(f"""
<style>
@keyframes oram-err-in {{
    from {{ opacity:0; transform:translateY(14px) scale(0.97); }}
    to   {{ opacity:1; transform:translateY(0) scale(1); }}
}}
#oram-err-overlay {{
    position:fixed; inset:0; background:{overlay_bg};
    backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
    z-index:99999; display:flex; align-items:center; justify-content:center;
}}
#oram-err-card {{
    background:{card_bg}; border:1px solid {card_bdr};
    border-radius:20px; padding:2.8rem 3rem 2.4rem;
    text-align:center; max-width:400px; width:90%;
    animation:oram-err-in 0.45s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow:0 24px 60px rgba(0,0,0,0.35);
}}
</style>
<div id="oram-err-overlay"><div id="oram-err-card">
  <div style="font-size:3rem;margin-bottom:1rem">❌</div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:1.25rem;
              font-weight:700;color:#f87171;margin-bottom:0.6rem">
    Campo obligatorio
  </div>
  <div style="font-family:Inter,sans-serif;font-size:0.92rem;
              color:{text_muted};line-height:1.6">{mensaje}</div>
  <div style="margin-top:1.4rem;font-family:Inter,sans-serif;
              font-size:0.8rem;color:{text_muted};opacity:0.7">
    Cerrando automáticamente…</div>
</div></div>
""", unsafe_allow_html=True)
    time.sleep(2.2)
    ph.empty()
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
    dark = get_theme() == "dark"
    page_header("📋", "Diario de Trades", "Registro · Análisis · Psicología")
    inject_module_css(dark, textarea=True, date_input=True)

    tab_nuevo, tab_historial = st.tabs(["➕ Nuevo Trade", "📋 Historial"])

    # ── NUEVO TRADE ────────────────────────────────────────────────────────
    with tab_nuevo:
        with st.form("trade_form", clear_on_submit=True):

            # Fila 1: Fecha | Categoría | Activo
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1: fecha     = st.date_input("Fecha", date.today())
            with r1c2: categoria = st.selectbox("Categoría", list(ACTIVOS_DEFAULT.keys()))
            with r1c3: activo    = st.selectbox("Activo", ACTIVOS_DEFAULT[categoria])

            # Fila 2: Temporalidad | Setup SMC | Estado del trade
            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1: tf     = st.selectbox("Temporalidad", ["1m","5m","15m","30m","1h","4h","1d"])
            with r2c2: setup  = st.selectbox("Setup SMC", SETUPS_SMC)
            with r2c3: estado = st.selectbox("Estado del trade", ["Cerrado", "Abierto", "Breakeven"])

            # Fila 3: Dirección | Estado emocional
            r3c1, r3c2 = st.columns(2)
            with r3c1: direccion = st.radio("Dirección", ["LONG", "SHORT"], horizontal=True)
            with r3c2: emocion   = st.selectbox("Estado emocional", EMOCIONES)

            # Fila 4: Entrada | SL | TP | Riesgo
            c4, c5, c6, c7 = st.columns(4)
            with c4: entrada    = st.number_input("Entrada",      value=0.0, format="%.5f", step=0.00001)
            with c5: sl         = st.number_input("Stop Loss",    value=0.0, format="%.5f", step=0.00001)
            with c6: tp         = st.number_input("Take Profit",  value=0.0, format="%.5f", step=0.00001)
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
                    _overlay_error("Entrada, Stop Loss y Take Profit son campos obligatorios.", dark=dark)
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
                        delay=3.0,
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
        with fc1: filtro_activo = st.selectbox("Activo", ["Todos"] + sorted(df['activo'].unique().tolist()), key="f_act")
        with fc2: filtro_dir    = st.selectbox("Dirección", ["Todos", "LONG", "SHORT"], key="f_dir")
        with fc3: filtro_setup  = st.selectbox("Setup", ["Todos"] + sorted(df['setup'].unique().tolist()), key="f_stp")
        with fc4: filtro_estado = st.selectbox("Estado", ["Todos", "Cerrado", "Abierto", "Breakeven"], key="f_est")

        if filtro_activo != "Todos": df = df[df['activo'] == filtro_activo]
        if filtro_dir    != "Todos": df = df[df['direccion'] == filtro_dir]
        if filtro_setup  != "Todos": df = df[df['setup'] == filtro_setup]
        if filtro_estado != "Todos": df = df[df['estado'] == filtro_estado]

        pnl_total = df['resultado_usd'].sum()
        wr        = (df['resultado_usd'] > 0).mean() * 100 if len(df) > 0 else 0
        color_pnl = "#26de81" if pnl_total >= 0 else "#fc5c65"
        st.markdown(f"""
        <div style="display:flex;gap:1.5rem;margin-bottom:1rem;flex-wrap:wrap;
                    padding:0.75rem 1rem;background:#0c1219;border-radius:10px;
                    border:1px solid #1b2a40">
            <span class="card-sub" style="font-size:0.82rem">{len(df)} trades</span>
            <span class="card-sub" style="font-size:0.82rem">P&L: <b style="color:{color_pnl}">${pnl_total:,.2f}</b></span>
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

        if len(df) > 0:
            st.divider()
            with st.expander("✏️ Editar trade", expanded=False):
                edit_id = st.selectbox(
                    "Trade a editar",
                    df['id'].tolist(),
                    format_func=lambda i: f"#{i} — {df[df['id']==i]['activo'].values[0]} {df[df['id']==i]['direccion'].values[0]} {str(df[df['id']==i]['fecha'].values[0])[:10]}",
                    key="edit_trade_id"
                )
                row = df[df['id'] == edit_id].iloc[0]
                with st.form("edit_trade_form", clear_on_submit=False):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_resultado = st.number_input(
                            "Resultado (USD)", value=float(row.get('resultado_usd') or 0), step=1.0
                        )
                        _est = row.get('estado') or 'Cerrado'
                        _estados = ["Cerrado", "Abierto", "Breakeven"]
                        edit_estado = st.selectbox(
                            "Estado del trade", _estados,
                            index=_estados.index(_est) if _est in _estados else 0
                        )
                    with ec2:
                        _s = row.get('setup') or SETUPS_SMC[0]
                        edit_setup = st.selectbox(
                            "Setup SMC", SETUPS_SMC,
                            index=SETUPS_SMC.index(_s) if _s in SETUPS_SMC else 0
                        )
                        _e = row.get('emocion') or EMOCIONES[0]
                        edit_emocion = st.selectbox(
                            "Estado emocional", EMOCIONES,
                            index=EMOCIONES.index(_e) if _e in EMOCIONES else 0
                        )
                    edit_notas = st.text_area("Notas / Plan", value=row.get('notas') or '', height=80)
                    if st.form_submit_button("💾 Guardar cambios", use_container_width=True):
                        actualizar_trade(edit_id, user["id"], {
                            "resultado_usd": edit_resultado,
                            "estado":        edit_estado,
                            "setup":         edit_setup,
                            "emocion":       edit_emocion,
                            "notas":         edit_notas,
                        })
                        oram_bienvenida(
                            titulo        = "💾 Trade actualizado",
                            subtitulo     = f"Trade <b>#{edit_id}</b> guardado correctamente.",
                            spinner_label = "Actualizando diario…",
                            delay=2.5,
                        )

            st.divider()
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
                        delay=3.0,
                    )
