"""
modules/auth.py — ORAM Quant Systems
"""
import streamlit as st
from database.db import autenticar_usuario, crear_usuario
from ui.styles import toggle_theme, get_theme, APP_TAGLINE, LOGO_GOLD, LOGO_BLUE, LOGO_TEAL

def render_auth():
    dark  = get_theme() == "dark"
    m     = "#edf4ff" if dark else "#0b1824"
    muted = "#637a94" if dark else "#526070"

    # Fondo siempre definido por el tema del app, NO por el sistema
    bg = ("radial-gradient(ellipse at 25% 50%,#0a1525 0%,#06090f 100%)"
          if dark else "linear-gradient(135deg,#eef2f7 0%,#e6edf5 100%)")

    st.markdown(
        f'<style>'
        f'.main{{background:{bg}!important}}'
        f'.stApp{{background:{bg}!important}}'
        f'[data-testid="stAppViewContainer"]{{background:{bg}!important}}'
        f'</style>',
        unsafe_allow_html=True,
    )

    # Logo — colores hardcodeados, siempre visibles en ambos temas
    O = f'<span style="color:{LOGO_GOLD}">O</span>'
    R = f'<span style="color:{LOGO_BLUE}">R</span>'
    A = f'<span style="color:{LOGO_TEAL}">A</span>'
    M = f'<span style="color:{m}">M</span>'

    st.markdown(
        f'<div style="max-width:480px;margin:2.5rem auto 0 auto;text-align:center;padding:0 1rem">'
        f'<div style="margin-bottom:0.4rem">'
        f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:4rem;'
        f'font-weight:800;letter-spacing:-4px;line-height:1">{O}{R}{A}{M}</span>'
        f'</div>'
        f'<div style="font-family:\'Space Grotesk\',sans-serif;font-size:1.1rem;'
        f'font-weight:600;color:{m};letter-spacing:0.5px;margin-bottom:0.3rem">Quant Systems</div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.6rem;'
        f'color:{muted};letter-spacing:3px;text-transform:uppercase;margin-bottom:1.5rem">'
        f'{APP_TAGLINE}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Toggle de tema en la pantalla de login
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_r:
        theme_label = "☀️ Claro" if dark else "🌙 Oscuro"
        if st.button(theme_label, key="auth_theme_toggle", help="Cambiar tema"):
            toggle_theme()
            st.rerun()

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        tab_login, tab_reg = st.tabs(["Iniciar sesión", "Crear cuenta"])
        with tab_login:
            with st.form("login_form"):
                user = st.text_input("Usuario", placeholder="tu_usuario")
                pw   = st.text_input("Contraseña", type="password", placeholder="••••••••")
                sub  = st.form_submit_button("Acceder →", use_container_width=True)
                if sub:
                    if not user or not pw:
                        st.error("Completa todos los campos.")
                    else:
                        data = autenticar_usuario(user, pw)
                        if data:
                            st.session_state.user = data
                            from datetime import datetime, timezone
                            st.session_state["last_activity"] = datetime.now(timezone.utc).timestamp()
                            st.rerun()
                        else:
                            st.error("Credenciales incorrectas.")
        with tab_reg:
            with st.form("reg_form"):
                new_user = st.text_input("Usuario", placeholder="elige_un_nombre", key="ru")
                new_pw   = st.text_input("Contraseña", type="password", key="rp")
                new_pw2  = st.text_input("Confirmar contraseña", type="password", key="rp2")
                capital  = st.number_input("Capital inicial (USD)", value=1000.0,
                                            min_value=100.0, step=500.0)
                sub_reg  = st.form_submit_button("Crear cuenta →", use_container_width=True)
                if sub_reg:
                    if not new_user or not new_pw:
                        st.error("Completa todos los campos.")
                    elif len(new_pw) < 6:
                        st.error("Mínimo 6 caracteres en la contraseña.")
                    elif new_pw != new_pw2:
                        st.error("Las contraseñas no coinciden.")
                    elif len(new_user) < 3:
                        st.error("El usuario debe tener mínimo 3 caracteres.")
                    else:
                        ok = crear_usuario(new_user, new_pw, capital_inicial=capital)
                        if ok:
                            st.success("✅ Cuenta creada. Inicia sesión.")
                        else:
                            st.error("Ese nombre de usuario ya existe.")
