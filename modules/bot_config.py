"""
modules/bot_config.py — Configuración del bot de Telegram desde la app.
"""
import streamlit as st
import json
from database.db import obtener_bot_config, actualizar_bot_config, obtener_alertas, crear_alerta, eliminar_alerta, obtener_señales_recientes
from utils.market_data import ACTIVOS_DEFAULT
from ui.styles import get_colors, page_header, oram_notify, oram_bienvenida

def render_bot_config():
    user = st.session_state.user
    c    = get_colors()

    page_header("🤖", "Bot de Telegram", "Configuración · Alertas de precio · Historial de señales")

    cfg = obtener_bot_config(user["id"])

    tab_setup, tab_alertas, tab_historial = st.tabs(["⚙️ Configuración", "🔔 Alertas de Precio", "📋 Señales enviadas"])

    # ── SETUP ──────────────────────────────────────────────────────────────
    with tab_setup:
        st.markdown(f"""
        <div class="smc-card smc-card-accent">
            <div class="card-title">🚀 Cómo conectar el bot en 3 pasos</div>
            <div style="font-size:0.88rem;line-height:2">
            <b>1.</b> Abre Telegram y busca <b>@BotFather</b><br>
            <b>2.</b> Envía <code>/newbot</code> → elige nombre → copia el <b>TOKEN</b><br>
            <b>3.</b> Habla con tu bot → envía <code>/start</code> → copia tu <b>Chat ID</b><br>
            <b>4.</b> Pega ambos aquí y haz clic en Guardar<br>
            <b>5.</b> Ejecuta: <code>python bot/telegram_bot.py</code> en tu servidor/PC
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("bot_cfg_form"):
            chat_id = st.text_input("Telegram Chat ID", value=cfg.get("telegram_chat_id",""),
                                     placeholder="123456789", help="Ejecuta /start en tu bot para obtenerlo")
            st.caption("El TOKEN del bot va en el archivo .env como TELEGRAM_BOT_TOKEN=tu_token")

            col1, col2 = st.columns(2)
            with col1:
                alertas_act = st.toggle("Alertas automáticas activas", value=bool(cfg.get("alertas_activas",1)))
                resumen_d   = st.toggle("Resumen diario (8:00 AM CDMX)", value=bool(cfg.get("resumen_diario",1)))
            with col2:
                umbral      = st.slider("Umbral confianza para alertas (%)", 50, 90,
                                         int(cfg.get("umbral_confianza",70)), key="umbral_bot")
                tf_mon      = st.selectbox("Timeframe a monitorear",
                                            ["1m","5m","15m","30m","1h","4h"],
                                            index=["1m","5m","15m","30m","1h","4h"].index(
                                                cfg.get("tf_monitor","15m")))

            st.markdown("**Activos a monitorear:**")
            todos_activos = [a for lista in ACTIVOS_DEFAULT.values() for a in lista]
            actuales = json.loads(cfg.get("activos_monitor",'["EURUSD=X","GBPUSD=X","USDJPY=X"]'))
            sel_activos = st.multiselect("Selecciona activos", todos_activos, default=actuales, key="sel_act_bot")

            if st.form_submit_button("💾 Guardar configuración", width='stretch'):
                actualizar_bot_config(
                    user["id"],
                    telegram_chat_id=chat_id.strip(),
                    alertas_activas=int(alertas_act),
                    resumen_diario=int(resumen_d),
                    umbral_confianza=float(umbral),
                    tf_monitor=tf_mon,
                    activos_monitor=json.dumps(sel_activos),
                )
                oram_bienvenida(
                    titulo        = "✅ Configuración guardada",
                    subtitulo     = f"Bot Telegram configurado correctamente.<br>Umbral: <b>{umbral:.0f}%</b> · Timeframe: <b>{tf_mon}</b>",
                    spinner_label = "Aplicando configuración…",
                    delay         = 2.0,
                )

        # Estado actual
        st.divider()
        chat_actual = cfg.get("telegram_chat_id","")
        if chat_actual:
            st.markdown(f"""
            <div class="smc-card smc-card-green">
                <div class="card-title">Estado del bot</div>
                <div class="card-sub">✅ Chat ID configurado: <code>{chat_actual}</code></div>
                <div class="card-sub">Umbral: {cfg.get('umbral_confianza',70):.0f}% · TF: {cfg.get('tf_monitor','15m')}</div>
                <div class="card-sub">Alertas: {'✅ Activas' if cfg.get('alertas_activas') else '❌ Desactivadas'}</div>
                <div class="card-sub">Resumen diario: {'✅' if cfg.get('resumen_diario') else '❌'}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Chat ID no configurado. El bot no puede enviarte mensajes.")

        st.markdown(f"""
        <div class="smc-card">
            <div class="card-title">Comandos disponibles en Telegram</div>
            <div class="card-sub"><code>/start</code> — Bienvenida y tu Chat ID</div>
            <div class="card-sub"><code>/mercado</code> — Resumen del mercado ahora</div>
            <div class="card-sub"><code>/señales</code> — Señales SMC activas</div>
            <div class="card-sub"><code>/noticias</code> — Eventos económicos del día</div>
            <div class="card-sub"><code>/alertas</code> — Señales de las últimas 24h</div>
            <div class="card-sub"><code>/resumen</code> — Reporte diario completo</div>
            <div class="card-sub"><code>/ayuda</code> — Lista de comandos</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ALERTAS DE PRECIO ──────────────────────────────────────────────────
    with tab_alertas:
        st.markdown("**Crear alerta de precio**")
        with st.form("alerta_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                cat_a   = st.selectbox("Categoría", list(ACTIVOS_DEFAULT.keys()), key="al_cat")
                ticker_a = st.selectbox("Activo", ACTIVOS_DEFAULT[cat_a], key="al_tk")
            with col2:
                tipo_a  = st.selectbox("Tipo de alerta", ["above","below"],
                                        format_func=lambda x: "📈 Precio sube sobre" if x=="above" else "📉 Precio baja bajo")
                precio_a = st.number_input("Precio objetivo", value=0.0, format="%.5f", key="al_pr")
            with col3:
                msg_a = st.text_input("Mensaje personalizado", placeholder="ej: OB alcista en 1.0850", key="al_msg")

            if st.form_submit_button("🔔 Crear Alerta", width='stretch'):
                if precio_a == 0:
                    oram_notify("error", "❌ El precio objetivo no puede ser 0.", toast=True, banner=True)
                else:
                    crear_alerta(user["id"], ticker_a, tipo_a, precio_a, msg_a)
                    dir_label = "sube sobre" if tipo_a == "above" else "baja bajo"
                    oram_bienvenida(
                        titulo        = "🔔 Alerta creada",
                        subtitulo     = f"<b>{ticker_a}</b> notificará cuando el precio {dir_label} <b>{precio_a:.5f}</b>.",
                        spinner_label = "Registrando alerta…",
                        delay         = 1.8,
                    )

        st.divider()
        alertas = obtener_alertas(user["id"], solo_activas=False)
        if not alertas:
            st.info("Sin alertas configuradas.")
        else:
            st.markdown(f"**{len([a for a in alertas if not a['disparada']])} alertas activas · {len([a for a in alertas if a['disparada']])} disparadas**")
            for al in alertas:
                estado   = "✅ Disparada" if al["disparada"] else "⏳ Activa"
                emoji    = "📈" if al["tipo"]=="above" else "📉"
                bg_color = "rgba(38,222,129,0.08)" if al["disparada"] else ""
                col1, col2 = st.columns([4,1])
                with col1:
                    st.markdown(f"""
                    <div class="smc-card" style="padding:0.6rem 1rem;margin-bottom:0.3rem;background:{bg_color}">
                        <span style="font-family:'JetBrains Mono',monospace;font-size:0.8rem">
                        {estado} · {emoji} <b>{al['ticker']}</b> {al['tipo']} <b>{al['precio']:.5f}</b>
                        {' · ' + al['mensaje'] if al['mensaje'] else ''}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if not al["disparada"]:
                        if st.button("🗑️", key=f"del_al_{al['id']}"):
                            eliminar_alerta(al["id"], user["id"])
                            oram_bienvenida(
                                titulo        = "🗑️ Alerta eliminada",
                                subtitulo     = f"La alerta de <b>{al['ticker']}</b> ha sido cancelada.",
                                spinner_label = "Actualizando alertas…",
                                delay         = 1.5,
                            )

    # ── HISTORIAL DE SEÑALES ──────────────────────────────────────────────
    with tab_historial:
        señales = obtener_señales_recientes(horas=72)
        if not señales:
            st.info("Sin señales registradas en las últimas 72 horas.")
            return
        st.markdown(f"**{len(señales)} señales registradas (últimas 72h)**")
        import pandas as pd
        df_s = pd.DataFrame(señales)
        cols = ["created_at","ticker","timeframe","tipo","direccion","confianza","precio","sl","tp","enviada_bot"]
        df_show = df_s[[col for col in cols if col in df_s.columns]]

        def color_dir(v):
            if v == "LONG":  return "color:#26de81"
            if v == "SHORT": return "color:#fc5c65"
            return ""

        st.dataframe(df_show.style.map(color_dir, subset=["direccion"] if "direccion" in df_show.columns else []),
                     width='stretch', height=400)
