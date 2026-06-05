"""
modules/admin.py — ORAM Quant Systems
Panel de control del Superadministrador.
Solo accesible para usuarios con is_admin=1 (Moises OG).
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from database.db import (
    obtener_todos_usuarios, admin_stats_globales,
    admin_crear_usuario, admin_eliminar_usuario,
    admin_resetear_password, admin_actualizar_capital,
    admin_logs_senales, admin_trades_todos, admin_configs_bot_todas,
    actualizar_bot_config,
)
from ui.styles import get_colors, page_header, oram_bienvenida, oram_notify


def render_admin():
    user = st.session_state.user
    c    = get_colors()

    # Doble verificación de seguridad
    if not user.get("is_admin"):
        st.error("🚫 Acceso denegado. Solo el administrador puede acceder a este panel.")
        return

    page_header("🛡️", "Panel de Administración", f"Superadmin: {user['username'].upper()}")

    # ── Tabs del panel ───────────────────────────────────────────────────────
    tab_stats, tab_users, tab_bot, tab_senales, tab_trades = st.tabs([
        "📊 Estadísticas",
        "👥 Usuarios",
        "🤖 Configuración Bot",
        "⚡ Log de Señales",
        "📋 Trades Globales",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — ESTADÍSTICAS GLOBALES
    # ════════════════════════════════════════════════════════════════════════
    with tab_stats:
        st.markdown("### 📊 Estado Global de la Plataforma")

        try:
            stats = admin_stats_globales()
        except Exception as e:
            st.error(f"Error obteniendo estadísticas: {e}")
            return

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 Usuarios activos",  stats["total_users"])
        col2.metric("🤖 Bots activos",      stats["bots_activos"])
        col3.metric("⚡ Señales hoy",        stats["senales_hoy"])
        col4.metric("📋 Trades hoy",         stats["trades_hoy"])

        col5, col6, col7 = st.columns(3)
        col5.metric("⚡ Total señales",       stats["total_senales"])
        col6.metric("📋 Total trades",        stats["total_trades"])
        col7.metric("🔔 Alertas pendientes",  stats["alertas_pendientes"])

        st.divider()

        # Log de señales recientes
        st.markdown("#### ⚡ Últimas señales enviadas")
        try:
            senales = admin_logs_senales(20)
            if senales:
                df = pd.DataFrame(senales)
                cols_show = [c for c in ["created_at","ticker","timeframe","tipo",
                                          "direccion","confianza","precio","enviada_bot"]
                             if c in df.columns]
                df = df[cols_show].copy()
                if "confianza" in df.columns:
                    df["confianza"] = df["confianza"].apply(lambda x: f"{x:.0f}%")
                if "enviada_bot" in df.columns:
                    df["enviada_bot"] = df["enviada_bot"].apply(lambda x: "✅" if x else "⏳")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Sin señales registradas aún.")
        except Exception as e:
            st.error(f"Error: {e}")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — GESTIÓN DE USUARIOS
    # ════════════════════════════════════════════════════════════════════════
    with tab_users:
        st.markdown("### 👥 Gestión de Usuarios")

        # Crear nuevo usuario
        with st.expander("➕ Crear nuevo usuario", expanded=False):
            with st.form("admin_crear_user"):
                col1, col2 = st.columns(2)
                with col1:
                    nu_user = st.text_input("Usuario", placeholder="nombre_usuario")
                    nu_cap  = st.number_input("Capital inicial (USD)", value=1000.0,
                                               min_value=100.0, step=100.0)
                with col2:
                    nu_pw1 = st.text_input("Contraseña", type="password")
                    nu_pw2 = st.text_input("Confirmar contraseña", type="password")

                if st.form_submit_button("✅ Crear usuario", use_container_width=True):
                    if not nu_user or not nu_pw1:
                        oram_notify("error", "❌ Usuario y contraseña son obligatorios.", toast=True, banner=True)
                    elif nu_pw1 != nu_pw2:
                        oram_notify("error", "❌ Las contraseñas no coinciden.", toast=True, banner=True)
                    elif len(nu_pw1) < 6:
                        oram_notify("error", "❌ Mínimo 6 caracteres en la contraseña.", toast=True, banner=True)
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
                            oram_notify("error", f"❌ El usuario '{nu_user}' ya existe.", toast=True, banner=True)

        st.divider()

        # Lista de usuarios
        st.markdown("#### Lista de usuarios registrados")
        try:
            usuarios = obtener_todos_usuarios()
        except Exception as e:
            st.error(f"Error: {e}")
            return

        # Inicializar estado de confirmación de eliminación
        if "admin_confirm_delete" not in st.session_state:
            st.session_state["admin_confirm_delete"] = {}

        for u in usuarios:
            uid      = u["id"]
            uname    = u["username"]
            capital  = u.get("capital_inicial", 0)
            is_admin_u = u.get("is_admin", 0)
            creado   = str(u.get("created_at", ""))[:10]

            badge_admin = "🛡️ ADMIN" if is_admin_u else ""
            badge_est   = "🟢 Activo" if u.get("is_active", 1) else "🔴"

            with st.expander(f"{badge_est} {badge_admin} **{uname}** — ${capital:,.0f} — {creado}"):

                if is_admin_u:
                    # Admin: solo mostrar info, sin controles de eliminación
                    st.info("🛡️ Superadministrador — cuenta protegida, no puede eliminarse.")
                    col_a, _ = st.columns([1, 2])
                    with col_a:
                        nuevo_cap = st.number_input(
                            "Capital (USD)", value=float(capital),
                            min_value=0.0, step=100.0, key=f"cap_{uid}"
                        )
                        if st.button("💾 Actualizar capital", key=f"ucap_{uid}", use_container_width=True):
                            admin_actualizar_capital(uid, nuevo_cap)
                            oram_notify("success", f"✅ Capital actualizado a ${nuevo_cap:,.0f}", toast=True)
                            st.rerun()
                else:
                    # Usuario normal: capital + resetear pw + ELIMINAR
                    col_a, col_b, col_c = st.columns(3)

                    with col_a:
                        nuevo_cap = st.number_input(
                            "Capital (USD)", value=float(capital),
                            min_value=0.0, step=100.0, key=f"cap_{uid}"
                        )
                        if st.button("💾 Actualizar capital", key=f"ucap_{uid}", use_container_width=True):
                            admin_actualizar_capital(uid, nuevo_cap)
                            oram_notify("success", f"✅ Capital de {uname} actualizado a ${nuevo_cap:,.0f}", toast=True)
                            st.rerun()

                    with col_b:
                        nueva_pw = st.text_input("Nueva contraseña", type="password", key=f"pw_{uid}")
                        if st.button("🔑 Resetear contraseña", key=f"upw_{uid}", use_container_width=True):
                            if nueva_pw and len(nueva_pw) >= 6:
                                admin_resetear_password(uid, nueva_pw)
                                oram_notify("success", f"✅ Contraseña de {uname} actualizada.", toast=True)
                            else:
                                oram_notify("error", "❌ Mínimo 6 caracteres.", toast=True, banner=True)

                    with col_c:
                        confirm_key = f"confirm_del_{uid}"
                        confirming  = st.session_state["admin_confirm_delete"].get(uid, False)

                        if not confirming:
                            # Primer clic — pedir confirmación
                            if st.button(
                                "🗑️ Eliminar usuario",
                                key=f"del1_{uid}",
                                use_container_width=True,
                                type="primary",
                            ):
                                st.session_state["admin_confirm_delete"][uid] = True
                                st.rerun()
                        else:
                            # Segundo paso — confirmación real
                            st.warning(f"⚠️ **¿Eliminar permanentemente a {uname}?**\nSe borrarán todos sus trades, watchlist, alertas y configuración. Esta acción es irreversible.")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button(
                                    "✅ Sí, eliminar",
                                    key=f"del_yes_{uid}",
                                    use_container_width=True,
                                ):
                                    ok = admin_eliminar_usuario(uid)
                                    st.session_state["admin_confirm_delete"].pop(uid, None)
                                    if ok:
                                        oram_bienvenida(
                                            titulo="🗑️ Usuario eliminado",
                                            subtitulo=f"<b>{uname}</b> y todos sus datos han sido eliminados permanentemente.",
                                            spinner_label="Actualizando base de datos…",
                                            delay=1.8,
                                        )
                                    else:
                                        oram_notify("error", "❌ No se pudo eliminar. ¿Es admin?", toast=True, banner=True)
                                        st.rerun()
                            with col_no:
                                if st.button(
                                    "❌ Cancelar",
                                    key=f"del_no_{uid}",
                                    use_container_width=True,
                                ):
                                    st.session_state["admin_confirm_delete"].pop(uid, None)
                                    st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — CONFIGURACIÓN BOT POR USUARIO
    # ════════════════════════════════════════════════════════════════════════
    with tab_bot:
        st.markdown("### 🤖 Configuración de Bot por Usuario")
        st.caption("Desde aquí puedes ver y modificar la configuración del bot de cualquier usuario, igual que ellos lo harían desde la app.")

        try:
            configs = admin_configs_bot_todas()
        except Exception as e:
            st.error(f"Error: {e}")
            return

        if not configs:
            st.info("Ningún usuario tiene bot configurado aún.")
        else:
            for cfg in configs:
                uname    = cfg.get("username", "?")
                chat_id  = cfg.get("telegram_chat_id", "")
                umbral   = cfg.get("umbral_confianza", 70)
                tf       = cfg.get("tf_monitor", "15m")
                activas  = bool(cfg.get("alertas_activas", 1))
                resumen  = bool(cfg.get("resumen_diario", 1))
                user_id  = cfg.get("user_id")

                try:
                    activos = json.loads(cfg.get("activos_monitor", "[]"))
                except Exception:
                    activos = []

                estado = "🟢 Activo" if activas and chat_id else "🔴 Sin configurar"

                with st.expander(f"{estado} — **{uname}** · Chat ID: `{chat_id or 'Sin configurar'}` · TF: {tf} · Umbral: {umbral:.0f}%"):
                    with st.form(f"admin_bot_{user_id}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_chat = st.text_input("Chat ID Telegram", value=chat_id, key=f"cid_{user_id}")
                            new_umbral = st.slider("Umbral confianza (%)", 40, 90,
                                                    int(umbral), key=f"umb_{user_id}")
                        with col2:
                            new_tf = st.selectbox("Timeframe", ["1m","5m","15m","30m","1h","4h"],
                                                   index=["1m","5m","15m","30m","1h","4h"].index(tf)
                                                   if tf in ["1m","5m","15m","30m","1h","4h"] else 2,
                                                   key=f"tf_{user_id}")
                            new_activas = st.toggle("Alertas activas", value=activas, key=f"al_{user_id}")
                            new_resumen = st.toggle("Resumen diario", value=resumen, key=f"re_{user_id}")

                        st.caption(f"Activos monitoreados: {', '.join(activos) or 'Por defecto'}")

                        if st.form_submit_button("💾 Guardar cambios", use_container_width=True):
                            actualizar_bot_config(
                                user_id,
                                telegram_chat_id=new_chat.strip(),
                                umbral_confianza=float(new_umbral),
                                tf_monitor=new_tf,
                                alertas_activas=int(new_activas),
                                resumen_diario=int(new_resumen),
                            )
                            oram_notify("success", f"✅ Bot de {uname} actualizado.", toast=True)
                            st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — LOG DE SEÑALES
    # ════════════════════════════════════════════════════════════════════════
    with tab_senales:
        st.markdown("### ⚡ Log completo de señales SMC")

        limite = st.slider("Mostrar últimas N señales", 20, 200, 50, step=10, key="admin_sl_lim")

        try:
            senales = admin_logs_senales(limite)
        except Exception as e:
            st.error(f"Error: {e}")
            return

        if not senales:
            st.info("Sin señales registradas.")
            return

        df = pd.DataFrame(senales)
        # Limpiar y formatear
        if "confianza" in df.columns:
            df["confianza"] = df["confianza"].apply(lambda x: f"{x:.0f}%")
        if "enviada_bot" in df.columns:
            df["enviada_bot"] = df["enviada_bot"].apply(lambda x: "✅ Enviada" if x else "⏳ Pendiente")
        if "direccion" in df.columns:
            df["direccion"] = df["direccion"].apply(
                lambda x: "🟢 LONG" if x=="LONG" else "🔴 SHORT" if x=="SHORT" else "⚪"
            )

        cols_show = [c for c in ["created_at","ticker","timeframe","tipo",
                                   "direccion","confianza","precio","sl","tp","enviada_bot"]
                     if c in df.columns]
        st.dataframe(df[cols_show], use_container_width=True, hide_index=True)

        # Métricas rápidas
        col1, col2, col3 = st.columns(3)
        raw = admin_logs_senales(limite)
        n_long  = sum(1 for s in raw if s.get("direccion") == "LONG")
        n_short = sum(1 for s in raw if s.get("direccion") == "SHORT")
        n_env   = sum(1 for s in raw if s.get("enviada_bot"))
        col1.metric("🟢 LONG",    n_long)
        col2.metric("🔴 SHORT",   n_short)
        col3.metric("✅ Enviadas", n_env)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 5 — TRADES GLOBALES
    # ════════════════════════════════════════════════════════════════════════
    with tab_trades:
        st.markdown("### 📋 Trades de todos los usuarios")

        limite_t = st.slider("Mostrar últimos N trades", 20, 200, 50, step=10, key="admin_tr_lim")

        try:
            trades = admin_trades_todos(limite_t)
        except Exception as e:
            st.error(f"Error: {e}")
            return

        if not trades:
            st.info("Sin trades registrados.")
            return

        df = pd.DataFrame(trades)
        cols_show = [c for c in ["fecha","username","activo","timeframe","direccion",
                                   "entrada","sl","tp","rr_planeado","resultado_usd","estado"]
                     if c in df.columns]
        st.dataframe(df[cols_show], use_container_width=True, hide_index=True)

        # Estadísticas globales
        if "resultado_usd" in df.columns:
            total_pnl = df["resultado_usd"].sum()
            n_pos = (df["resultado_usd"] > 0).sum()
            n_neg = (df["resultado_usd"] < 0).sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 P&L global", f"${total_pnl:+,.2f}")
            col2.metric("🟢 Ganadores",  n_pos)
            col3.metric("🔴 Perdedores", n_neg)
