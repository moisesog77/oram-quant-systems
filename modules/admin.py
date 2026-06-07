"""
modules/admin.py — ORAM Quant Systems — Panel de Superadministración
"""
import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
from database.db import (
    obtener_todos_usuarios, admin_stats_globales,
    admin_crear_usuario, admin_eliminar_usuario,
    admin_resetear_password, admin_actualizar_capital,
    admin_logs_senales, admin_trades_todos, admin_configs_bot_todas,
    actualizar_bot_config,
)
from ui.styles import get_colors, page_header, oram_bienvenida, get_theme


def _inject_admin_css(dark: bool, c: dict):
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
    background: transparent !important; border: none !important; box-shadow: none !important;
}}
.stSelectbox [data-baseweb="select"] {{ cursor: pointer !important; }}
.stSelectbox [data-baseweb="select"] > div {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    min-height: 46px !important; display: flex !important; align-items: center !important;
    cursor: pointer !important; transition: border-color .18s ease, box-shadow .18s ease !important;
    padding: 0 0.75rem !important;
}}
.stSelectbox [data-baseweb="select"] > div:focus-within {{
    border-color: {focus_clr} !important; box-shadow: 0 0 0 3px {focus_glow} !important;
}}
.stSelectbox [data-baseweb="select"] span {{
    color: {input_text} !important; -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important; pointer-events: none !important;
}}
.stSelectbox [data-baseweb="select"] svg {{
    fill: {eye_col} !important; opacity: 0.7 !important; flex-shrink: 0 !important; pointer-events: none !important;
}}
.stSelectbox [data-baseweb="select"] input {{
    position: absolute !important; width: 1px !important; height: 1px !important; opacity: 0 !important;
    pointer-events: none !important; caret-color: transparent !important; user-select: none !important; border: none !important;
}}
/* ══ NUMBER INPUT ═════════════════════════════════════════════════════════ */
[data-testid="stNumberInput"] {{ background: transparent !important; border: none !important; }}
[data-testid="stNumberInput"] > div:nth-child(1) {{ background: transparent !important; border: none !important; }}
[data-testid="stNumberInput"] > div:nth-child(2) {{
    background: {input_bg} !important; border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    display: flex !important; align-items: center !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important; padding: 0 !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2):focus-within {{
    border-color: {focus_clr} !important; box-shadow: 0 0 0 3px {focus_glow} !important;
}}
[data-testid="stNumberInput"] input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important; -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; flex: 1 !important; height: 46px !important; -moz-appearance: textfield !important;
}}
[data-testid="stNumberInput"] input::-webkit-outer-spin-button,
[data-testid="stNumberInput"] input::-webkit-inner-spin-button {{ -webkit-appearance: none !important; margin: 0 !important; }}
[data-testid="stNumberInput"] > div:nth-child(2) > div:last-child {{
    display: flex !important; align-items: center !important; align-self: stretch !important;
    height: 100% !important; background: transparent !important; border: none !important;
}}
[data-testid="stNumberInput-StepDown"], [data-testid="stNumberInput-StepUp"] {{
    all: unset !important; box-sizing: border-box !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    align-self: stretch !important; width: 44px !important; min-width: 44px !important;
    height: 100% !important; min-height: 46px !important; flex-shrink: 0 !important;
    cursor: pointer !important; border-left: 1px solid {input_bdr} !important;
    background: transparent !important; opacity: 0.55 !important; transition: opacity .15s !important;
}}
[data-testid="stNumberInput-StepDown"]:hover, [data-testid="stNumberInput-StepUp"]:hover {{ opacity: 1 !important; }}
[data-testid="stNumberInput-StepDown"] svg, [data-testid="stNumberInput-StepUp"] svg {{
    width: 17px !important; height: 17px !important; fill: none !important;
    stroke: {eye_col} !important; stroke-width: 1.8 !important;
    pointer-events: none !important; display: block !important; flex-shrink: 0 !important;
}}
[data-testid="stNumberInput"] > input:last-child,
[data-testid="stNumberInput"] > div:last-child:not(:nth-child(2)),
[data-testid="stNumberInput"] > *:nth-child(n+3) {{
    display: none !important; visibility: hidden !important; height: 0 !important;
    margin: 0 !important; padding: 0 !important; border: none !important;
    opacity: 0 !important; position: absolute !important; pointer-events: none !important;
}}
[data-testid="InputInstructions"] {{
    display: none !important; visibility: hidden !important; height: 0 !important; margin: 0 !important;
}}
/* ══ TEXT INPUT ═══════════════════════════════════════════════════════════ */
.stTextInput > div {{
    border: none !important; background: transparent !important;
    box-shadow: none !important; padding: 0 !important; margin: 0 !important;
}}
.stTextInput > div > div {{
    background: {input_bg} !important; border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    display: flex !important; align-items: center !important; padding: 0 !important;
}}
.stTextInput > div > div:focus-within {{
    border-color: {focus_clr} !important; box-shadow: 0 0 0 3px {focus_glow} !important;
}}
.stTextInput input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important; -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; height: 46px !important; width: 100% !important;
}}
[data-testid="stTextInputRootElement"] {{
    background: {input_bg} !important; border: 2px solid {input_bdr} !important;
    border-radius: 10px !important; box-shadow: none !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    display: flex !important; align-items: center !important;
}}
[data-testid="stTextInputRootElement"]:focus-within {{
    border-color: {focus_clr} !important; box-shadow: 0 0 0 3px {focus_glow} !important;
}}
/* ══ BOTONES PREMIUM ══════════════════════════════════════════════════════ */
[data-testid="stFormSubmitButton"] button,
[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important; border-radius: 10px !important;
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    font-family: Inter, sans-serif !important; font-weight: 600 !important;
    font-size: 0.95rem !important; padding: 0.72rem 1.4rem !important;
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
[data-testid="stBaseButton-secondary"] {{
    border: 2px solid {input_bdr} !important; border-radius: 10px !important;
    background: transparent !important; color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: Inter, sans-serif !important; font-weight: 500 !important;
    font-size: 0.9rem !important; width: 100% !important;
    transition: border-color .18s ease !important;
}}
[data-testid="stBaseButton-secondary"]:hover {{
    border-color: {focus_clr} !important; color: {focus_clr} !important;
    -webkit-text-fill-color: {focus_clr} !important;
}}
/* ══ MÉTRICAS — alineación perfecta ══════════════════════════════════════ */
[data-testid="stMetric"] {{
    background: {input_bg} !important;
    border: 1px solid {input_bdr} !important;
    border-radius: 10px !important;
    padding: 0.9rem 1rem !important;
}}
[data-testid="stMetricLabel"] {{
    font-family: Inter, sans-serif !important;
    font-size: 0.68rem !important; font-weight: 600 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
    color: {label_col} !important;
}}
[data-testid="stMetricValue"] {{
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 2rem !important; font-weight: 700 !important;
    color: {input_text} !important; line-height: 1.1 !important;
}}
</style>
""", unsafe_allow_html=True)


def _overlay_error(msg: str, titulo: str = "Campo obligatorio", dark: bool = True):
    overlay_bg = "rgba(6,9,15,0.92)" if dark else "rgba(238,242,247,0.94)"
    card_bg    = "#0c1219"           if dark else "#ffffff"
    text_muted = "#637a94"           if dark else "#7a8fa0"
    ph = st.empty()
    ph.markdown(f"""
<style>
@keyframes oad-err {{from{{opacity:0;transform:translateY(14px) scale(0.97)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
#oad-overlay{{position:fixed;inset:0;background:{overlay_bg};backdrop-filter:blur(6px);
z-index:99999;display:flex;align-items:center;justify-content:center}}
#oad-card{{background:{card_bg};border:1px solid #3d1a1a;border-radius:20px;
padding:2.6rem 3rem 2.2rem;text-align:center;max-width:400px;width:90%;
animation:oad-err 0.4s cubic-bezier(0.22,1,0.36,1) both;
box-shadow:0 24px 60px rgba(0,0,0,0.35)}}
</style>
<div id="oad-overlay"><div id="oad-card">
<div style="font-size:2.8rem;margin-bottom:0.8rem">❌</div>
<div style="font-family:'Space Grotesk',sans-serif;font-size:1.15rem;font-weight:700;color:#f87171;margin-bottom:0.5rem">{titulo}</div>
<div style="font-family:Inter,sans-serif;font-size:0.9rem;color:{text_muted};line-height:1.6">{msg}</div>
<div style="margin-top:1.2rem;font-family:Inter,sans-serif;font-size:0.75rem;color:{text_muted};opacity:0.7">Cerrando automáticamente…</div>
</div></div>""", unsafe_allow_html=True)
    time.sleep(2.2)
    ph.empty()


def _overlay_confirm_delete(uname: str, dark: bool = True):
    """Overlay de advertencia — se muestra brevemente y luego aparecen botones inline."""
    overlay_bg = "rgba(6,9,15,0.93)" if dark else "rgba(238,242,247,0.95)"
    card_bg    = "#0c1219"           if dark else "#ffffff"
    text_muted = "#637a94"           if dark else "#7a8fa0"
    ph = st.empty()
    ph.markdown(f"""
<style>
@keyframes oad-warn {{from{{opacity:0;transform:translateY(14px) scale(0.97)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
#oad-warn-overlay{{position:fixed;inset:0;background:{overlay_bg};backdrop-filter:blur(8px);
z-index:99999;display:flex;align-items:center;justify-content:center}}
#oad-warn-card{{background:{card_bg};border:1px solid #7c2626;border-radius:20px;
padding:2.6rem 3rem 2.2rem;text-align:center;max-width:440px;width:92%;
animation:oad-warn 0.4s cubic-bezier(0.22,1,0.36,1) both;
box-shadow:0 24px 60px rgba(0,0,0,0.4)}}
</style>
<div id="oad-warn-overlay"><div id="oad-warn-card">
<div style="font-size:2.8rem;margin-bottom:0.8rem">⚠️</div>
<div style="font-family:'Space Grotesk',sans-serif;font-size:1.15rem;font-weight:700;color:#fbbf24;margin-bottom:0.5rem">¿Eliminar permanentemente?</div>
<div style="font-family:Inter,sans-serif;font-size:0.9rem;color:{text_muted};line-height:1.6">
Se eliminarán todos los datos de <b style="color:#edf4ff">{uname}</b>.<br>
Trades, alertas, watchlist y configuración.<br><br>
<b style="color:#edf4ff">Confirma o cancela en el panel de abajo.</b>
</div>
</div></div>""", unsafe_allow_html=True)
    time.sleep(2.5)
    ph.empty()


def render_admin():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"

    if not user.get("is_admin"):
        st.error("🚫 Acceso denegado. Solo el administrador puede acceder a este panel.")
        return

    page_header("🛡️", "Panel de Administración", f"Superadmin: {user['username'].upper()}")
    _inject_admin_css(dark, c)

    tab_stats, tab_users, tab_bot, tab_senales, tab_trades = st.tabs([
        "📊 Estadísticas", "👥 Usuarios", "🤖 Configuración Bot",
        "⚡ Log de Señales", "📋 Trades Globales",
    ])

    # ── ESTADÍSTICAS ──────────────────────────────────────────────────────
    with tab_stats:
        st.markdown(f"""
<div class="smc-card smc-card-blue" style="padding:0.8rem 1rem;margin-bottom:1.2rem">
    <div class="card-title">📊 Estado Global de la Plataforma</div>
</div>
""", unsafe_allow_html=True)
        try:
            stats = admin_stats_globales()
        except Exception as e:
            st.error(f"Error obteniendo estadísticas: {e}")
            return

        # Fila 1: 4 métricas iguales
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 Usuarios activos",  stats["total_users"])
        col2.metric("🤖 Bots activos",      stats["bots_activos"])
        col3.metric("⚡ Señales hoy",        stats["senales_hoy"])
        col4.metric("📋 Trades hoy",         stats["trades_hoy"])

        st.markdown('<div style="margin-top:0.75rem"></div>', unsafe_allow_html=True)

        # Fila 2: 3 métricas iguales
        col5, col6, col7 = st.columns(3)
        col5.metric("⚡ Total señales",       stats["total_senales"])
        col6.metric("📋 Total trades",        stats["total_trades"])
        col7.metric("🔔 Alertas pendientes",  stats["alertas_pendientes"])

        st.divider()
        st.markdown(f"""
<div class="smc-card" style="padding:0.8rem 1rem;margin-bottom:0.75rem">
    <div class="card-title">⚡ Últimas señales enviadas</div>
</div>
""", unsafe_allow_html=True)
        try:
            senales = admin_logs_senales(20)
            if senales:
                df = pd.DataFrame(senales)
                cols_show = [x for x in ["created_at","ticker","timeframe","tipo","direccion","confianza","precio","enviada_bot"] if x in df.columns]
                df = df[cols_show].copy()
                if "confianza" in df.columns: df["confianza"] = df["confianza"].apply(lambda x: f"{x:.0f}%")
                if "enviada_bot" in df.columns: df["enviada_bot"] = df["enviada_bot"].apply(lambda x: "✅" if x else "⏳")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Sin señales registradas aún.")
        except Exception as e:
            st.error(f"Error: {e}")

    # ── USUARIOS ──────────────────────────────────────────────────────────
    with tab_users:
        st.markdown(f"""
<div class="smc-card smc-card-green" style="padding:0.8rem 1rem;margin-bottom:1rem">
    <div class="card-title">👥 Gestión de Usuarios</div>
</div>
""", unsafe_allow_html=True)

        # Crear nuevo usuario
        with st.expander("➕ Crear nuevo usuario", expanded=False):
            with st.form("admin_crear_user"):
                col1, col2 = st.columns(2)
                with col1:
                    nu_user = st.text_input("Usuario", placeholder="nombre_usuario")
                    nu_cap  = st.number_input("Capital inicial (USD)", value=1000.0, min_value=100.0, step=100.0)
                with col2:
                    nu_pw1 = st.text_input("Contraseña", type="password")
                    nu_pw2 = st.text_input("Confirmar contraseña", type="password")

                if st.form_submit_button("✅ Crear usuario", use_container_width=True):
                    if not nu_user or not nu_pw1:
                        _overlay_error("Usuario y contraseña son campos obligatorios.", dark=dark)
                    elif nu_pw1 != nu_pw2:
                        _overlay_error("Las contraseñas no coinciden. Verifícalas e intenta de nuevo.", "Contraseñas diferentes", dark=dark)
                    elif len(nu_pw1) < 6:
                        _overlay_error("La contraseña debe tener mínimo 6 caracteres.", dark=dark)
                    else:
                        ok = admin_crear_usuario(nu_user, nu_pw1, nu_cap)
                        if ok:
                            oram_bienvenida(
                                titulo="✅ Usuario creado",
                                subtitulo=f"<b>{nu_user}</b> registrado con capital ${nu_cap:,.0f}.",
                                spinner_label="Actualizando base de datos…",
                                delay=1.5,
                            )
                        else:
                            _overlay_error(f"El usuario <b>{nu_user}</b> ya existe en el sistema.", dark=dark)

        st.divider()
        st.markdown("#### Lista de usuarios registrados")

        try:
            usuarios = obtener_todos_usuarios()
        except Exception as e:
            st.error(f"Error: {e}")
            return

        if "admin_confirm_delete" not in st.session_state:
            st.session_state["admin_confirm_delete"] = {}

        for u in usuarios:
            uid        = u["id"]
            uname      = u["username"]
            capital    = u.get("capital_inicial", 0)
            is_admin_u = u.get("is_admin", 0)
            creado     = str(u.get("created_at", ""))[:10]
            badge_admin = "🛡️ ADMIN " if is_admin_u else ""
            badge_est   = "🟢 Activo" if u.get("is_active", 1) else "🔴 Inactivo"

            with st.expander(f"{badge_est} {badge_admin}**{uname}** — ${capital:,.0f} — {creado}"):
                if is_admin_u:
                    st.markdown(f"""
<div class="smc-card smc-card-blue" style="padding:0.7rem 1rem;margin-bottom:0.75rem">
    <div class="card-sub">🛡️ Superadministrador — cuenta protegida, no puede eliminarse.</div>
</div>
""", unsafe_allow_html=True)
                    nuevo_cap = st.number_input("Capital (USD)", value=float(capital),
                                                min_value=0.0, step=100.0, key=f"cap_{uid}")
                    if st.button("💾 Actualizar capital", key=f"ucap_{uid}", use_container_width=True):
                        admin_actualizar_capital(uid, nuevo_cap)
                        oram_bienvenida(
                            titulo="💾 Capital actualizado",
                            subtitulo=f"Capital de <b>{uname}</b> actualizado a <b>${nuevo_cap:,.0f}</b>.",
                            spinner_label="Guardando cambios…", delay=1.5,
                        )
                else:
                    # 3 columnas alineadas: capital | contraseña | eliminar
                    col_a, col_b, col_c = st.columns([2, 2, 1])

                    with col_a:
                        nuevo_cap = st.number_input("Capital (USD)", value=float(capital),
                                                    min_value=0.0, step=100.0, key=f"cap_{uid}")
                        if st.button("💾 Actualizar capital", key=f"ucap_{uid}", use_container_width=True):
                            admin_actualizar_capital(uid, nuevo_cap)
                            oram_bienvenida(
                                titulo="💾 Capital actualizado",
                                subtitulo=f"Capital de <b>{uname}</b> actualizado a <b>${nuevo_cap:,.0f}</b>.",
                                spinner_label="Guardando cambios…", delay=1.5,
                            )

                    with col_b:
                        nueva_pw = st.text_input("Nueva contraseña", type="password", key=f"pw_{uid}")
                        if st.button("🔑 Resetear contraseña", key=f"upw_{uid}", use_container_width=True):
                            if nueva_pw and len(nueva_pw) >= 6:
                                admin_resetear_password(uid, nueva_pw)
                                oram_bienvenida(
                                    titulo="🔑 Contraseña actualizada",
                                    subtitulo=f"Contraseña de <b>{uname}</b> reseteada exitosamente.",
                                    spinner_label="Aplicando cambios…", delay=1.5,
                                )
                            else:
                                _overlay_error("La contraseña debe tener mínimo 6 caracteres.", dark=dark)

                    with col_c:
                        st.markdown('<div style="margin-top:1.65rem"></div>', unsafe_allow_html=True)
                        confirming = st.session_state["admin_confirm_delete"].get(uid, False)
                        if not confirming:
                            if st.button("🗑️ Eliminar", key=f"del1_{uid}", use_container_width=True):
                                st.session_state["admin_confirm_delete"][uid] = True
                                st.rerun()

                # Confirmación premium — aparece debajo como card de pantalla completa
                confirming = st.session_state["admin_confirm_delete"].get(uid, False)
                if confirming:
                    bg   = "#0c1219" if dark else "#ffffff"
                    bdr  = "#7c2626" if dark else "#fecaca"
                    muted = "#637a94" if dark else "#7a8fa0"
                    st.markdown(f"""
<div style="
    background:{bg};
    border:1.5px solid {bdr};
    border-left:4px solid #f87171;
    border-radius:16px;
    padding:1.8rem 2rem;
    margin-top:0.75rem;
    text-align:center;
">
  <div style="font-size:2.4rem;margin-bottom:0.6rem">⚠️</div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:0.6rem;
              letter-spacing:2px;color:#f87171;font-weight:700;margin-bottom:0.3rem">
    ACCIÓN IRREVERSIBLE
  </div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:1.1rem;
              font-weight:700;color:#fbbf24;margin-bottom:0.5rem">
    ¿Eliminar a <b>{uname}</b>?
  </div>
  <div style="font-family:Inter,sans-serif;font-size:0.85rem;color:{muted};line-height:1.7">
    Se borrarán permanentemente: trades, alertas,<br>watchlist y configuración del bot.
  </div>
</div>
""", unsafe_allow_html=True)
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ Sí, eliminar", key=f"del_yes_{uid}", use_container_width=True):
                            ok = admin_eliminar_usuario(uid)
                            st.session_state["admin_confirm_delete"].pop(uid, None)
                            if ok:
                                oram_bienvenida(
                                    titulo="🗑️ Usuario eliminado",
                                    subtitulo=f"<b>{uname}</b> y todos sus datos han sido eliminados permanentemente.",
                                    spinner_label="Actualizando base de datos…", delay=1.8,
                                )
                            else:
                                _overlay_error(f"No se pudo eliminar a <b>{uname}</b>. Puede tener permisos de administrador.", dark=dark)
                    with col_no:
                        if st.button("❌ Cancelar", key=f"del_no_{uid}", use_container_width=True, type="secondary"):
                            st.session_state["admin_confirm_delete"].pop(uid, None)
                            st.rerun()

    # ── CONFIG BOT ────────────────────────────────────────────────────────
    with tab_bot:
        st.markdown(f"""
<div class="smc-card smc-card-accent" style="padding:0.8rem 1rem;margin-bottom:1rem">
    <div class="card-title">🤖 Configuración de Bot por Usuario</div>
</div>
""", unsafe_allow_html=True)
        try:
            configs = admin_configs_bot_todas()
        except Exception as e:
            st.error(f"Error: {e}")
            return

        if not configs:
            st.info("Ningún usuario tiene bot configurado aún.")
        else:
            for cfg in configs:
                uname   = cfg.get("username", "?")
                chat_id = cfg.get("telegram_chat_id", "")
                umbral  = cfg.get("umbral_confianza", 70)
                tf      = cfg.get("tf_monitor", "15m")
                activas = bool(cfg.get("alertas_activas", 1))
                resumen = bool(cfg.get("resumen_diario", 1))
                user_id = cfg.get("user_id")
                try:
                    activos = json.loads(cfg.get("activos_monitor", "[]"))
                except Exception:
                    activos = []
                estado = "🟢 Activo" if activas and chat_id else "🔴 Sin configurar"

                with st.expander(f"{estado} — **{uname}** · Chat: `{chat_id or 'N/A'}` · TF: {tf} · Umbral: {umbral:.0f}%"):
                    with st.form(f"admin_bot_{user_id}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_chat   = st.text_input("Chat ID Telegram", value=chat_id, key=f"cid_{user_id}")
                            new_umbral = st.slider("Umbral confianza (%)", 40, 90, int(umbral), key=f"umb_{user_id}")
                        with col2:
                            new_tf      = st.selectbox("Timeframe", ["1m","5m","15m","30m","1h","4h"],
                                                        index=["1m","5m","15m","30m","1h","4h"].index(tf) if tf in ["1m","5m","15m","30m","1h","4h"] else 2,
                                                        key=f"tf_{user_id}")
                            new_activas = st.toggle("Alertas activas", value=activas, key=f"al_{user_id}")
                            new_resumen = st.toggle("Resumen diario",  value=resumen, key=f"re_{user_id}")
                        st.caption(f"Activos monitoreados: {', '.join(activos) or 'Por defecto'}")
                        if st.form_submit_button("💾 Guardar cambios", use_container_width=True):
                            actualizar_bot_config(
                                user_id, telegram_chat_id=new_chat.strip(),
                                umbral_confianza=float(new_umbral), tf_monitor=new_tf,
                                alertas_activas=int(new_activas), resumen_diario=int(new_resumen),
                            )
                            oram_bienvenida(
                                titulo="💾 Bot actualizado",
                                subtitulo=f"Configuración del bot de <b>{uname}</b> guardada.",
                                spinner_label="Aplicando cambios…", delay=1.5,
                            )

    # ── LOG SEÑALES ───────────────────────────────────────────────────────
    with tab_senales:
        st.markdown(f"""
<div class="smc-card" style="padding:0.8rem 1rem;margin-bottom:1rem">
    <div class="card-title">⚡ Log completo de señales SMC</div>
</div>
""", unsafe_allow_html=True)
        limite = st.slider("Mostrar últimas N señales", 20, 200, 50, step=10, key="admin_sl_lim")
        try:
            senales = admin_logs_senales(limite)
        except Exception as e:
            st.error(f"Error: {e}"); return
        if not senales:
            st.info("Sin señales registradas."); return
        df = pd.DataFrame(senales)
        if "confianza"  in df.columns: df["confianza"]  = df["confianza"].apply(lambda x: f"{x:.0f}%")
        if "enviada_bot" in df.columns: df["enviada_bot"] = df["enviada_bot"].apply(lambda x: "✅ Enviada" if x else "⏳ Pendiente")
        if "direccion"  in df.columns: df["direccion"]  = df["direccion"].apply(lambda x: "🟢 LONG" if x=="LONG" else "🔴 SHORT" if x=="SHORT" else "⚪")
        cols_show = [x for x in ["created_at","ticker","timeframe","tipo","direccion","confianza","precio","sl","tp","enviada_bot"] if x in df.columns]
        st.dataframe(df[cols_show], use_container_width=True, hide_index=True)
        raw = admin_logs_senales(limite)
        c1, c2, c3 = st.columns(3)
        c1.metric("🟢 LONG",    sum(1 for s in raw if s.get("direccion") == "LONG"))
        c2.metric("🔴 SHORT",   sum(1 for s in raw if s.get("direccion") == "SHORT"))
        c3.metric("✅ Enviadas", sum(1 for s in raw if s.get("enviada_bot")))

    # ── TRADES GLOBALES ───────────────────────────────────────────────────
    with tab_trades:
        st.markdown(f"""
<div class="smc-card" style="padding:0.8rem 1rem;margin-bottom:1rem">
    <div class="card-title">📋 Trades de todos los usuarios</div>
</div>
""", unsafe_allow_html=True)
        limite_t = st.slider("Mostrar últimos N trades", 20, 200, 50, step=10, key="admin_tr_lim")
        try:
            trades = admin_trades_todos(limite_t)
        except Exception as e:
            st.error(f"Error: {e}"); return
        if not trades:
            st.info("Sin trades registrados."); return
        df = pd.DataFrame(trades)
        cols_show = [x for x in ["fecha","username","activo","timeframe","direccion","entrada","sl","tp","rr_planeado","resultado_usd","estado"] if x in df.columns]
        st.dataframe(df[cols_show], use_container_width=True, hide_index=True)
        if "resultado_usd" in df.columns:
            total_pnl = df["resultado_usd"].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 P&L global", f"${total_pnl:+,.2f}")
            c2.metric("🟢 Ganadores",  int((df["resultado_usd"] > 0).sum()))
            c3.metric("🔴 Perdedores", int((df["resultado_usd"] < 0).sum()))
