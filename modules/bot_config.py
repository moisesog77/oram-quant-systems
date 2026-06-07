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
from ui.styles import get_colors, page_header, oram_notify, oram_bienvenida, get_theme


def _inject_bot_css(dark: bool, c: dict):
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
.stSelectbox label, .stNumberInput label, .stTextInput label, .stSlider label {{
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

/* ══ NUMBER INPUT — sin cuadro extra ═════════════════════════════════════ */
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

/* ══ TEXT INPUT (Chat ID, Mensaje) ════════════════════════════════════════ */
.stTextInput > div {{
    border: none !important; background: transparent !important;
    box-shadow: none !important; padding: 0 !important; margin: 0 !important;
}}
.stTextInput > div > div {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    display: flex !important; align-items: center !important;
    padding: 0 !important;
}}
.stTextInput > div > div:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
.stTextInput input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; height: 46px !important; width: 100% !important;
}}
[data-testid="stTextInputRootElement"] {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    display: flex !important; align-items: center !important;
}}
[data-testid="stTextInputRootElement"]:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}

/* ══ BOTONES FORMULARIO ══════════════════════════════════════════════════ */
[data-testid="stFormSubmitButton"] button,
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important; border-radius: 10px !important;
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    font-family: Inter, sans-serif !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
    padding: 0.72rem 1.4rem !important;
    box-shadow: 0 4px 14px 0 rgba(16,185,129,0.39) !important;
    transition: box-shadow .25s ease, transform .18s ease !important;
    cursor: pointer !important; width: 100% !important;
}}
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stBaseButton-primary"]:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 22px 0 rgba(16,185,129,0.58) !important;
    transform: translateY(-1px) !important;
}}

/* ══ CARDS con borde izquierdo de color — todos los bloques ══════════════ */
.smc-card {{ border-left: 3px solid {c['border']} !important; }}
.smc-card-green  {{ border-left: 3px solid {c['green']} !important; }}
.smc-card-accent {{ border-left: 3px solid {c['accent']} !important; }}
.smc-card-blue   {{ border-left: 3px solid {c['accent3']} !important; }}
.smc-card-red    {{ border-left: 3px solid {c['red']} !important; }}
.oram-card       {{ border-left: 3px solid {c['border']} !important; }}
</style>
""", unsafe_allow_html=True)


def render_bot_config():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"

    page_header("🤖", "Bot de Telegram", "Configuración · Alertas de precio · Historial de señales")
    _inject_bot_css(dark, c)

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
            st.markdown("""
            <div class="smc-card smc-card-blue" style="margin-bottom:1rem;padding:0.8rem 1rem">
                <div class="card-title">🔗 Conexión Bot</div>
            </div>
            """, unsafe_allow_html=True)
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
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin-bottom:0.5rem">🔍 ANÁLISIS</div>
            <div class="card-sub"><code>/mercado</code> — Resumen de todos los pares (1H)</div>
            <div class="card-sub"><code>/senales</code> — Señales SMC activas ≥60% confianza</div>
            <div class="card-sub"><code>/mtf EURUSD</code> — Análisis Multi-Timeframe</div>
            <div class="card-sub"><code>/analizar GBPUSD 1h</code> — Análisis completo de un par</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">💼 GESTIÓN DE RIESGO</div>
            <div class="card-sub"><code>/riesgo EURUSD 1.08 1.075 1.09</code> — Calcula lote y RR</div>
            <div class="card-sub"><code>/capital</code> — Tu cuenta y métricas de trading</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">📰 INFORMACIÓN</div>
            <div class="card-sub"><code>/noticias</code> — Eventos económicos del día</div>
            <div class="card-sub"><code>/proximos</code> — Próximos eventos (2 horas)</div>
            <div class="card-sub"><code>/sesiones</code> — Horarios de sesiones en CDMX</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">📊 HISTORIAL</div>
            <div class="card-sub"><code>/alertas</code> — Señales de las últimas 24h</div>
            <div class="card-sub"><code>/resumen</code> — Reporte diario completo</div>
            <div class="card-sub" style="font-size:0.75rem;color:{c['text_muted']};margin:0.5rem 0 0.2rem">🤖 AUTOMÁTICO (sin comandos)</div>
            <div class="card-sub">🚨 Alertas compra/venta cuando confianza ≥75%</div>
            <div class="card-sub">🔭 MTF alineado → notificación automática</div>
            <div class="card-sub">🔔 Alertas de precio en tus niveles</div>
            <div class="card-sub">📰 Aviso 30 min antes de noticias de alto impacto</div>
            <div class="card-sub">🌅 Reporte diario automático a las 7AM CDMX</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ALERTAS DE PRECIO ──────────────────────────────────────────────────
    with tab_alertas:
        # CSS para envolver el form con borde izquierdo verde
        st.markdown("""
<div class="smc-card smc-card-green" style="margin-bottom:1rem;padding:0.8rem 1rem">
    <div class="card-title">🔔 Nueva Alerta de Precio</div>
</div>
        """, unsafe_allow_html=True)
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
                        delay         = 1.8,
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
                bdr_color  = c['text_muted'] if disparada else c['green']
                bg_extra   = f"background:rgba(34,197,94,0.06);" if not disparada else ""
                msg_txt    = f" &nbsp;·&nbsp; <i>{al['mensaje']}</i>" if al.get('mensaje') else ""
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"""
<div style="border-left:3px solid {bdr_color};padding:0.65rem 1rem;
            border-radius:0 10px 10px 0;margin-bottom:0.4rem;
            background:{c['bg_card']};{bg_extra}">
    <div style="font-family:Inter,sans-serif;font-size:0.78rem;
                color:{c['text_muted']};margin-bottom:0.15rem;
                letter-spacing:0.5px;text-transform:uppercase;font-weight:600">
        {estado_txt}
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.88rem;color:{c['text']}">
        {emoji_dir} <b style="color:{c['text_strong']}">{al['ticker']}</b>
        &nbsp;<span style="color:{c['text_muted']}">{dir_txt}</span>&nbsp;
        <b style="color:{bdr_color}">{al['precio']:.5f}</b>{msg_txt}
    </div>
</div>
""", unsafe_allow_html=True)
                with col2:
                    if not disparada:
                        if st.button("🗑️", key=f"del_al_{al['id']}", use_container_width=True):
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
