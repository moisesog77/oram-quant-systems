"""
modules/bot_config.py — ORAM Quant Systems — Configuración Bot Telegram
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Permite configurar el bot de Telegram por usuario:
  · Chat ID (se obtiene con /start en ToroMaster)
  · Umbral de confianza para alertas automáticas
  · Timeframe de monitoreo y activos a vigilar
  · Activar/desactivar alertas y resumen diario (8AM CDMX)

Tabs:
  🔧 Configuración → formulario guardado en bot_config DB
  🔔 Alertas       → crear alertas de precio (above/below) por nivel
  📋 Historial     → señales enviadas por el bot en últimas 72h
"""
import streamlit as st
import json
from database.db import obtener_bot_config, actualizar_bot_config, obtener_alertas, crear_alerta, eliminar_alerta, obtener_señales_recientes
from utils.market_data import ACTIVOS_DEFAULT
from ui.styles import get_colors, page_header, oram_bienvenida, get_theme, inject_module_css



def render_bot_config():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"

    page_header("🤖", "Bot de Telegram", "Configuración · Alertas de precio · Historial de señales")
    inject_module_css(dark)

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
            # Marcador para CSS :has() — identifica este form
            st.markdown('<div id="bot-cfg-form-marker" style="display:none"></div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="card-title" style="margin-bottom:0.75rem">🔗 Conexión Bot</div>
            """, unsafe_allow_html=True)
            chat_id = st.text_input("Telegram Chat ID", value=cfg.get("telegram_chat_id",""),
                                     placeholder="123456789", help="Ejecuta /start en tu bot para obtenerlo")
            st.caption("El TOKEN del bot va en el archivo .env como TELEGRAM_BOT_TOKEN=tu_token")

            col1, col2 = st.columns(2)
            with col1:
                alertas_act = st.toggle("Alertas automáticas activas", value=bool(cfg.get("alertas_activas",1)))
                resumen_d   = st.toggle("Resumen diario (8:00 AM CDMX)", value=bool(cfg.get("resumen_diario",1)))
                riesgo_pct  = st.number_input(
                    "Riesgo por trade (%)", min_value=0.25, max_value=5.0,
                    value=float(cfg.get("riesgo_pct") or 1.0), step=0.25,
                    help="% de capital por operación — aparece en todas las señales automáticas",
                    key="riesgo_bot",
                )
            with col2:
                umbral      = st.slider("Umbral confianza para alertas (%)", 65, 90,
                                         max(int(cfg.get("umbral_confianza", 70)), 65), key="umbral_bot")
                _tf_opts    = ["15m","30m","1h","4h"]
                _tf_actual  = cfg.get("tf_monitor", "15m")
                _tf_actual  = _tf_actual if _tf_actual in _tf_opts else "15m"
                tf_mon      = st.selectbox("Timeframe a monitorear", _tf_opts,
                                            index=_tf_opts.index(_tf_actual),
                                            key="tf_mon_bot")

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
                    riesgo_pct=float(riesgo_pct),
                )
                oram_bienvenida(
                    titulo        = "✅ Configuración guardada",
                    subtitulo     = f"Bot Telegram configurado.<br>Umbral: <b>{umbral:.0f}%</b> · Riesgo: <b>{riesgo_pct:.2f}%</b> · TF: <b>{tf_mon}</b>",
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
                <div class="card-sub">Umbral: {cfg.get('umbral_confianza') or 70:.0f}% · Riesgo: {cfg.get('riesgo_pct') or 1.0:.2f}% · TF: {cfg.get('tf_monitor','15m')}</div>
                <div class="card-sub">Alertas: {'✅ Activas' if cfg.get('alertas_activas') else '❌ Desactivadas'}</div>
                <div class="card-sub">Resumen diario: {'✅' if cfg.get('resumen_diario') else '❌'}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Chat ID no configurado. El bot no puede enviarte mensajes.")

        st.markdown(f"""
        <div class="smc-card">
            <div class="card-title">Comandos disponibles en Telegram</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin-bottom:0.2rem">🤖 INICIO</div>
            <div class="card-sub"><code>/start</code> — Bienvenida y obtén tu Chat ID</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">🔍 ANÁLISIS</div>
            <div class="card-sub"><code>/mercado</code> — Resumen de todos los pares (1H)</div>
            <div class="card-sub"><code>/senales</code> — Señales SMC activas con tu config</div>
            <div class="card-sub"><code>/mtf EURUSD [swing]</code> — Multi-Timeframe</div>
            <div class="card-sub"><code>/analizar GBPUSD 1h</code> — Análisis completo de un par</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">💼 GESTIÓN DE RIESGO</div>
            <div class="card-sub"><code>/riesgo EURUSD 1.08 1.075 1.09</code> — Calcula lote y RR</div>
            <div class="card-sub"><code>/kelly 55 2.0 [10000]</code> — Kelly Criterion</div>
            <div class="card-sub"><code>/capital</code> — Dashboard completo de tu cuenta</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">📋 DIARIO & PERFORMANCE</div>
            <div class="card-sub"><code>/trades [N]</code> — Últimos N trades registrados</div>
            <div class="card-sub"><code>/performance</code> — Análisis estadístico + IA</div>
            <div class="card-sub"><code>/backtest EURUSD [1h] [50]</code> — Backtest SMC histórico</div>
            <div class="card-sub"><code>/watchlist</code> — Precios y señales de tus activos</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">📰 INFORMACIÓN</div>
            <div class="card-sub"><code>/noticias</code> — Eventos económicos del día</div>
            <div class="card-sub"><code>/proximos</code> — Próximos eventos (2 horas)</div>
            <div class="card-sub"><code>/sesiones</code> — Horarios de sesiones en CDMX</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">📊 HISTORIAL</div>
            <div class="card-sub"><code>/alertas [N]</code> — Señales de las últimas Nh</div>
            <div class="card-sub"><code>/resumen</code> — Reporte diario completo</div>
            <div class="card-sub"><code>/ayuda</code> — Lista completa de comandos</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">🤖 AUTOMÁTICO (sin comandos)</div>
            <div class="card-sub">🚨 Alertas compra/venta cuando confianza ≥umbral</div>
            <div class="card-sub">🔭 MTF alineado → notificación automática</div>
            <div class="card-sub">🔔 Alertas de precio en tus niveles</div>
            <div class="card-sub">📰 Aviso 30 min antes de noticias de alto impacto</div>
            <div class="card-sub">🌅 Reporte diario automático a las 7AM CDMX</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ALERTAS DE PRECIO ──────────────────────────────────────────────────
    with tab_alertas:
        # CSS para envolver el form con borde izquierdo verde
        with st.form("alerta_form", clear_on_submit=True):
            # Marcador para CSS :has() — identifica este form
            st.markdown('<div id="bot-alerta-form-marker" style="display:none"></div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="card-title" style="margin-bottom:0.75rem">🔔 Nueva Alerta de Precio</div>
            """, unsafe_allow_html=True)
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
                    import time
                    overlay_bg = "rgba(6,9,15,0.92)" if dark else "rgba(238,242,247,0.94)"
                    card_bg    = "#0c1219"           if dark else "#ffffff"
                    text_muted = "#637a94"           if dark else "#7a8fa0"
                    ph = st.empty()
                    ph.markdown(f"""
<style>
@keyframes oram-al-err {{
    from {{ opacity:0; transform:translateY(14px) scale(0.97); }}
    to   {{ opacity:1; transform:translateY(0) scale(1); }}
}}
#oram-al-overlay {{
    position:fixed; inset:0; background:{overlay_bg};
    backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
    z-index:99999; display:flex; align-items:center; justify-content:center;
}}
#oram-al-card {{
    background:{card_bg}; border:1px solid #3d1a1a;
    border-radius:20px; padding:2.8rem 3rem 2.4rem;
    text-align:center; max-width:400px; width:90%;
    animation:oram-al-err 0.45s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow:0 24px 60px rgba(0,0,0,0.35);
}}
</style>
<div id="oram-al-overlay"><div id="oram-al-card">
  <div style="font-size:3rem;margin-bottom:1rem">❌</div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:1.2rem;
              font-weight:700;color:#f87171;margin-bottom:0.6rem">
    Campo obligatorio
  </div>
  <div style="font-family:Inter,sans-serif;font-size:0.9rem;
              color:{text_muted};line-height:1.6">
    El precio objetivo no puede ser <b>0</b>.<br>Ingresa el nivel de precio para la alerta.
  </div>
  <div style="margin-top:1.2rem;font-family:Inter,sans-serif;
              font-size:0.78rem;color:{text_muted};opacity:0.7">
    Cerrando automáticamente…
  </div>
</div></div>
""", unsafe_allow_html=True)
                    time.sleep(2.2)
                    ph.empty()
                else:
                    crear_alerta(user["id"], ticker_a, tipo_a, precio_a, msg_a)
                    dir_label = "sube sobre" if tipo_a == "above" else "baja bajo"
                    oram_bienvenida(
                        titulo        = "🔔 Alerta creada",
                        subtitulo     = f"<b>{ticker_a}</b> notificará cuando el precio {dir_label} <b>{precio_a:.5f}</b>.",
                        spinner_label = "Registrando alerta…",
                        delay         = 2.0,
                    )

        st.divider()
        alertas = obtener_alertas(user["id"], solo_activas=False)
        if not alertas:
            st.info("Sin alertas configuradas.")
        else:
            activas   = [a for a in alertas if not a['disparada']]
            disparadas = [a for a in alertas if a['disparada']]
            st.markdown(f"""
<div class="smc-card" style="padding:0.8rem 1rem;margin-bottom:0.75rem">
    <div class="card-title">📋 Mis Alertas</div>
    <div class="card-sub">
        <b style="color:{c['green']}">{len(activas)}</b> activas &nbsp;·&nbsp;
        <b style="color:{c['text_muted']}">{len(disparadas)}</b> disparadas
    </div>
</div>
""", unsafe_allow_html=True)
            for al in alertas:
                disparada  = bool(al["disparada"])
                estado_txt = "✅ Disparada" if disparada else "⏳ Activa"
                emoji_dir  = "📈" if al["tipo"] == "above" else "📉"
                dir_txt    = "sube sobre" if al["tipo"] == "above" else "baja bajo"
                msg_txt    = f" · <i>{al['mensaje']}</i>" if al.get('mensaje') else ""
                card_class = "smc-card" if disparada else "smc-card smc-card-green"
                estado_color = c['text_muted'] if disparada else c['green']

                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"""
<div class="{card_class}" style="padding:0.8rem 1rem;margin-bottom:0.4rem">
    <div class="card-title" style="color:{estado_color}">{estado_txt}</div>
    <div class="card-sub" style="font-family:'JetBrains Mono',monospace;font-size:0.88rem;margin-top:0.2rem">
        {emoji_dir} <b style="color:{c['text_strong']}">{al['ticker']}</b>
        &nbsp;<span style="color:{c['text_muted']}">{dir_txt}</span>&nbsp;
        <b style="color:{estado_color}">{al['precio']:.5f}</b>{msg_txt}
    </div>
</div>
""", unsafe_allow_html=True)
                with col2:
                    st.markdown('<div style="margin-top:0.5rem"></div>', unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_al_{al['id']}", use_container_width=True):
                        eliminar_alerta(al["id"], user["id"])
                        oram_bienvenida(
                            titulo        = "🗑️ Alerta eliminada",
                            subtitulo     = f"La alerta de <b>{al['ticker']}</b> ha sido eliminada del historial.",
                            spinner_label = "Actualizando alertas…",
                            delay         = 2.0,
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
