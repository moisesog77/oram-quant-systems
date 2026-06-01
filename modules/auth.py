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

    bg = ("radial-gradient(ellipse at 25% 50%,#0a1525 0%,#06090f 100%)"
          if dark else "linear-gradient(135deg,#eef2f7 0%,#e6edf5 100%)")

    # Colores del tema para todos los elementos del auth
    card_bg     = "#0c1219"  if dark else "#ffffff"
    card_border = "#1b2a40"  if dark else "#d0dcea"
    input_bg    = "#080d14"  if dark else "#f7fafc"
    input_text  = "#c8d8ea"  if dark else "#1a2b3c"
    input_border= "#1b2a40"  if dark else "#d0dcea"
    label_color = "#637a94"  if dark else "#526070"
    focus_color = "#22c55e"
    focus_glow  = "rgba(34,197,94,0.18)" if dark else "rgba(34,197,94,0.12)"
    tab_active  = "#c9a227"  if dark else "#9a7510"
    btn_bg      = "#ffffff"  if not dark else "#0c1219"
    btn_color   = "#1a2b3c"  if not dark else "#c8d8ea"
    btn_border  = "#d0dcea"  if not dark else "#1b2a40"
    shadow      = "0 8px 32px rgba(0,0,0,0.18)" if dark else "0 4px 16px rgba(0,0,0,0.08)"

    st.markdown(f"""
<style>
/* ── FONDO AUTH ── */
.main, .stApp, [data-testid="stAppViewContainer"] {{
    background: {bg} !important;
}}

/* ── BOTÓN TEMA AUTH — colores explícitos independientes del OS ── */
.stButton > button {{
    background: {btn_bg} !important;
    color: {btn_color} !important;
    -webkit-text-fill-color: {btn_color} !important;
    border: 1px solid {btn_border} !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    padding: 0.4rem 1rem !important;
    transition: all .18s ease !important;
    box-shadow: none !important;
}}
.stButton > button:hover {{
    border-color: {focus_color} !important;
    color: {focus_color} !important;
    -webkit-text-fill-color: {focus_color} !important;
    background: {focus_glow} !important;
}}

/* ── FORM CARD ── */
[data-testid="stForm"] {{
    background: {card_bg} !important;
    border: 1px solid {card_border} !important;
    border-radius: 14px !important;
    padding: 1.6rem 1.8rem 1.8rem !important;
    box-shadow: {shadow} !important;
}}

/* ── LABELS ── */
.stTextInput label, .stNumberInput label {{
    color: {label_color} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.3px !important;
    margin-bottom: 0.25rem !important;
    text-transform: uppercase !important;
}}

/* ── TEXT INPUT — caja limpia sin doble borde ── */
.stTextInput > div {{
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
}}
.stTextInput > div > div {{
    background: {input_bg} !important;
    border: 1.5px solid {input_border} !important;
    border-radius: 10px !important;
    padding: 0 !important;
    box-shadow: none !important;
    transition: border-color .15s, box-shadow .15s !important;
    overflow: hidden !important;
}}
.stTextInput > div > div:focus-within {{
    border-color: {focus_color} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
/* Input text — quitar borde/fondo propio */
.stTextInput input {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 0.75rem !important;
}}
/* Base-web input wrapper — transparente */
[data-baseweb="input"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}}
/* Botón del ojo — limpio */
[data-testid="stTextInputRootElement"] button,
.stTextInput button {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 12px !important;
    cursor: pointer !important;
    color: {label_color} !important;
}}
[data-testid="stTextInputRootElement"] button:hover {{
    color: {input_text} !important;
}}
[data-testid="stTextInputRootElement"] button svg,
.stTextInput button svg {{
    fill: {label_color} !important;
    width: 16px !important;
    height: 16px !important;
}}

/* ── NUMBER INPUT ── */
[data-testid="stNumberInput"] > div {{
    background: {input_bg} !important;
    border: 1.5px solid {input_border} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    box-shadow: none !important;
}}
[data-testid="stNumberInput"] > div:focus-within {{
    border-color: {focus_color} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
[data-testid="stNumberInput"] input {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter', sans-serif !important;
}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent !important;
    border-bottom: 1px solid {card_border} !important;
    gap: 0 !important;
    padding: 0 !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: {label_color} !important;
    background: transparent !important;
    border: none !important;
    padding: 0.65rem 1.2rem !important;
    border-radius: 0 !important;
}}
.stTabs [aria-selected="true"] {{
    color: {tab_active} !important;
    border-bottom: 2px solid {tab_active} !important;
    font-weight: 600 !important;
}}
.stTabs [data-baseweb="tab"] p {{
    color: inherit !important;
    -webkit-text-fill-color: inherit !important;
}}

/* ── BOTÓN SUBMIT — verde premium ── */
.stFormSubmitButton > button {{
    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
    border: 1.5px solid #16a34a !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.4px !important;
    padding: 0.65rem 1rem !important;
    width: 100% !important;
    margin-top: 0.5rem !important;
    box-shadow: 0 3px 14px rgba(22,163,74,0.35) !important;
    transition: all .18s ease !important;
    cursor: pointer !important;
}}
.stFormSubmitButton > button:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    border-color: #22c55e !important;
    box-shadow: 0 5px 22px rgba(34,197,94,0.45) !important;
    transform: translateY(-1px) !important;
}}
.stFormSubmitButton > button:active {{
    transform: scale(0.98) !important;
    box-shadow: 0 2px 8px rgba(22,163,74,0.3) !important;
}}
.stFormSubmitButton > button * {{
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}}

/* ── QUITAR HIGHLIGHT AMARILLO del focus — forzar verde ── */
*:focus, *:focus-visible {{
    outline: none !important;
    box-shadow: none !important;
}}
[data-baseweb="base-input"]:focus-within,
[data-baseweb="input"]:focus-within {{
    border-color: {focus_color} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
</style>
""", unsafe_allow_html=True)

    # Logo
    O = f'<span style="color:{LOGO_GOLD}">O</span>'
    R = f'<span style="color:{LOGO_BLUE}">R</span>'
    A = f'<span style="color:{LOGO_TEAL}">A</span>'
    M = f'<span style="color:{m}">M</span>'

    st.markdown(
        f'<div style="max-width:480px;margin:2rem auto 0 auto;text-align:center;padding:0 1rem">'
        f'<div style="margin-bottom:0.3rem">'
        f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:3.8rem;'
        f'font-weight:800;letter-spacing:-4px;line-height:1">{O}{R}{A}{M}</span>'
        f'</div>'
        f'<div style="font-family:\'Space Grotesk\',sans-serif;font-size:1.05rem;'
        f'font-weight:600;color:{m};letter-spacing:0.5px;margin-bottom:0.25rem">Quant Systems</div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.58rem;'
        f'color:{muted};letter-spacing:3px;text-transform:uppercase;margin-bottom:1.2rem">'
        f'{APP_TAGLINE}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Botón de tema — arriba a la derecha
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_r:
        theme_label = "☀️ Claro" if dark else "🌙 Oscuro"
        if st.button(theme_label, key="auth_theme_toggle", help="Cambiar tema"):
            toggle_theme()
            st.rerun()

    # Formularios centrados
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        tab_login, tab_reg = st.tabs(["Iniciar sesión", "Crear cuenta"])

        with tab_login:
            with st.form("login_form"):
                user = st.text_input("Usuario", placeholder="tu_usuario")
                pw   = st.text_input("Contraseña", type="password", placeholder="••••••••")
                sub  = st.form_submit_button("Acceder →", width="stretch")
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
                sub_reg  = st.form_submit_button("Crear cuenta →", width="stretch")
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
                            data = autenticar_usuario(new_user, new_pw)
                            if data:
                                st.session_state.user = data
                                from datetime import datetime, timezone
                                st.session_state["last_activity"] = datetime.now(timezone.utc).timestamp()
                                st.rerun()
                            else:
                                st.success("✅ Cuenta creada. Inicia sesión.")
                        else:
                            st.error("Ese nombre de usuario ya existe.")
