"""
modules/admin.py — ORAM Quant Systems — Panel de Superadministración
"""
import streamlit as st
import pandas as pd
import json
import time
from database.db import (
    obtener_todos_usuarios, admin_stats_globales,
    admin_crear_usuario, admin_eliminar_usuario,
    admin_resetear_password, admin_actualizar_capital,
    admin_logs_senales, admin_trades_todos, admin_configs_bot_todas,
    actualizar_bot_config,
)
from ui.styles import get_colors, page_header, oram_bienvenida, oram_overlay_error, get_theme, inject_module_css




def render_admin():
    user = st.session_state.user
    c    = get_colors()
    dark = get_theme() == "dark"

    if not user.get("is_admin"):
        st.error("🚫 Acceso denegado. Solo el administrador puede acceder a este panel.")
        return

    page_header("🛡️", "Panel de Administración", f"Superadmin: {user['username'].upper()}")
    inject_module_css(dark, metrics=True)

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
                        oram_overlay_error("Usuario y contraseña son campos obligatorios.")
                    elif nu_pw1 != nu_pw2:
                        oram_overlay_error("Las contraseñas no coinciden. Verifícalas e intenta de nuevo.", "Contraseñas diferentes")
                    elif len(nu_pw1) < 6:
                        oram_overlay_error("La contraseña debe tener mínimo 6 caracteres.")
                    else:
                        ok = admin_crear_usuario(nu_user, nu_pw1, nu_cap)
                        if ok:
                            oram_bienvenida(
                                titulo="✅ Usuario creado",
                                subtitulo=f"<b>{nu_user}</b> registrado con capital ${nu_cap:,.0f}.",
                                spinner_label="Actualizando base de datos…",
                                delay=2.0,
                            )
                        else:
                            oram_overlay_error(f"El usuario <b>{nu_user}</b> ya existe en el sistema.")

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
                            spinner_label="Guardando cambios…", delay=2.0,
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
                                spinner_label="Guardando cambios…", delay=2.0,
                            )

                    with col_b:
                        nueva_pw = st.text_input("Nueva contraseña", type="password", key=f"pw_{uid}")
                        if st.button("🔑 Resetear contraseña", key=f"upw_{uid}", use_container_width=True):
                            if nueva_pw and len(nueva_pw) >= 6:
                                admin_resetear_password(uid, nueva_pw)
                                oram_bienvenida(
                                    titulo="🔑 Contraseña actualizada",
                                    subtitulo=f"Contraseña de <b>{uname}</b> reseteada exitosamente.",
                                    spinner_label="Aplicando cambios…", delay=2.0,
                                )
                            else:
                                oram_overlay_error("La contraseña debe tener mínimo 6 caracteres.")

                    with col_c:
                        st.markdown('<div style="margin-top:1.65rem"></div>', unsafe_allow_html=True)
                        confirming = st.session_state["admin_confirm_delete"].get(uid, False)
                        if not confirming:
                            if st.button("🗑️ Eliminar", key=f"del1_{uid}", use_container_width=True):
                                st.session_state["admin_confirm_delete"][uid] = True
                                st.rerun()

                # Overlay premium con botones integrados via sendPrompt JS
                confirming = st.session_state["admin_confirm_delete"].get(uid, False)
                if confirming:
                    # ── Confirmación inline — diseño idéntico al overlay del Dashboard ──
                    # Renderiza la card en el flujo del documento (no fixed/overlay)
                    # para que los botones estén SIEMPRE dentro del área visible.
                    bg         = "#0c1219" if dark else "#ffffff"
                    bdr        = "#7c2626" if dark else "#fecaca"
                    muted      = "#637a94" if dark else "#7a8fa0"
                    text_col   = "#edf4ff" if dark else "#0b1824"
                    card_style = (
                        "background:" + bg + ";border:1.5px solid " + bdr + ";"
                        "border-radius:20px;padding:2.4rem 2.8rem 2rem;"
                        "text-align:center;max-width:480px;margin:1.5rem auto;"
                        "box-shadow:0 16px 48px rgba(0,0,0,0.35);"
                    )
                    st.markdown(
                        "<div style=\"" + card_style + "\">"
                        "<div style=\"font-size:3rem;margin-bottom:0.8rem\">⚠️</div>"
                        "<div style=\"font-family:Space Grotesk,sans-serif;font-size:0.6rem;"
                        "letter-spacing:2px;color:#f87171;font-weight:700;margin-bottom:0.4rem\">ACCIÓN IRREVERSIBLE</div>"
                        "<div style=\"font-family:Space Grotesk,sans-serif;font-size:1.15rem;"
                        "font-weight:700;color:#fbbf24;margin-bottom:0.6rem\">¿Eliminar a <b>" + uname + "</b>?</div>"
                        "<div style=\"font-family:Inter,sans-serif;font-size:0.88rem;color:" + muted + ";line-height:1.7\">"
                        "Se borrarán permanentemente:<br>"
                        "trades · alertas · watchlist · configuración del bot.</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )

                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ Sí, eliminar", key=f"del_yes_{uid}",
                                     use_container_width=True, type="primary"):
                            ok = admin_eliminar_usuario(uid)
                            st.session_state["admin_confirm_delete"].pop(uid, None)
                            if ok:
                                oram_bienvenida(
                                    titulo        = "🗑️ Usuario eliminado",
                                    subtitulo     = f"<b>{uname}</b> y todos sus datos han sido eliminados permanentemente.",
                                    spinner_label = "Actualizando base de datos…",
                                    delay         = 2.0,
                                )
                            else:
                                oram_overlay_error(
                                    f"No se pudo eliminar a <b>{uname}</b>. Puede tener permisos de administrador."
                                )
                    with col_no:
                        if st.button("❌ Cancelar", key=f"del_no_{uid}",
                                     use_container_width=True, type="secondary"):
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
                                spinner_label="Aplicando cambios…", delay=2.0,
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
