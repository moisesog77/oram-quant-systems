"""
modules/auth.py — ORAM Quant Systems
"""
import streamlit as st
from database.db import autenticar_usuario, crear_usuario
from ui.styles import toggle_theme, get_theme, APP_TAGLINE, LOGO_GOLD, LOGO_BLUE, LOGO_TEAL

def render_auth():
    dark  = get_theme() == "dark"
    m     = "#edf4ff" if dark else "#0b1824"
    muted = "#637a94" if dark else "#7a8fa0"

    bg          = "radial-gradient(ellipse at 25% 50%,#0a1525 0%,#06090f 100%)" if dark else "linear-gradient(135deg,#eef2f7 0%,#e6edf5 100%)"
    card_bg     = "#0c1219" if dark else "#ffffff"
    card_border = "#1b2a40" if dark else "#dde5ef"
    input_bg    = "#080d14" if dark else "#f4f8fc"
    input_text  = "#c8d8ea" if dark else "#1a2b3c"
    input_ph    = "#3a5068" if dark else "#a0aeba"
    input_bdr   = "#1e3048" if dark else "#d0dcea"
    label_col   = "#4a6a84" if dark else "#6b7f94"
    tab_active  = "#c9a227"
    focus_clr   = "#22c55e"
    focus_glow  = "rgba(34,197,94,0.18)" if dark else "rgba(34,197,94,0.14)"
    shadow      = "0 8px 40px rgba(0,0,0,0.25)" if dark else "0 4px 24px rgba(0,0,0,0.09)"

    # Botón tema: colores según tema activo
    tbtn_bg     = "rgba(255,255,255,0.12)" if dark else "rgba(255,255,255,0.85)"
    tbtn_txt    = "#c8d8ea" if dark else "#2a3f54"
    tbtn_bdr    = "rgba(200,216,234,0.2)" if dark else "rgba(0,0,0,0.12)"
    tbtn_hover_bg  = "rgba(255,255,255,0.20)" if dark else "rgba(255,255,255,1)"

    st.markdown(f"""
<style>
/* ── FONDO ── */
.main, .stApp, [data-testid="stAppViewContainer"],
.block-container {{
    background: {bg} !important;
    padding-top: 0 !important;
}}

/* ── OCULTAR TODO EL PADDING EXTRA DE STREAMLIT ── */
.block-container {{
    max-width: 100% !important;
    padding: 0 !important;
}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent !important;
    border-bottom: 1px solid {card_border} !important;
    gap: 0 !important; padding: 0 !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important; font-weight: 500 !important;
    color: {label_col} !important; background: transparent !important;
    border: none !important; padding: 0.6rem 1.1rem !important;
}}
.stTabs [data-baseweb="tab"] p {{
    color: inherit !important; -webkit-text-fill-color: inherit !important;
}}
.stTabs [aria-selected="true"] {{
    color: {tab_active} !important; -webkit-text-fill-color: {tab_active} !important;
    border-bottom: 2px solid {tab_active} !important; font-weight: 600 !important;
}}

/* ── FORM CARD ── */
[data-testid="stForm"] {{
    background: {card_bg} !important;
    border: 1px solid {card_border} !important;
    border-radius: 16px !important;
    padding: 1.8rem 1.8rem 2rem !important;
    box-shadow: {shadow} !important;
    overflow: visible !important;
}}

/* ── LABELS ── */
.stTextInput label, .stNumberInput label {{
    color: {label_col} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
    margin-bottom: 0.3rem !important;
}}

/* ── INPUTS: anular todos los wrappers de Streamlit ── */
.stTextInput > div,
.stTextInput > div > div > div {{
    background: transparent !important;
    border: none !important; box-shadow: none !important; padding: 0 !important;
}}

/* El contenedor real del input */
.stTextInput > div > div {{
    background: {input_bg} !important;
    border: 1.5px solid {input_bdr} !important;
    border-radius: 10px !important;
    padding: 0 !important; margin: 0 !important;
    box-shadow: none !important;
    transition: border-color .15s, box-shadow .15s !important;
    overflow: hidden !important;
    display: flex !important; align-items: center !important;
}}
.stTextInput > div > div:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}

/* El input en sí */
.stTextInput input {{
    background: transparent !important;
    border: none !important; box-shadow: none !important; outline: none !important;
    color: {input_text} !important; -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.93rem !important;
    padding: 0.6rem 0.85rem !important; flex: 1 !important; min-width: 0 !important;
}}
.stTextInput input::placeholder {{
    color: {input_ph} !important; -webkit-text-fill-color: {input_ph} !important;
    opacity: 1 !important;
}}

/* Base-web wrappers — totalmente transparentes */
[data-baseweb="input"],
[data-baseweb="base-input"] {{
    background: transparent !important;
    border: none !important; box-shadow: none !important; padding: 0 !important;
    width: 100% !important;
}}

/* Botón ojo — sin fondo ni borde */
.stTextInput button,
[data-testid="stTextInputRootElement"] button {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
    padding: 0 10px !important; cursor: pointer !important;
    color: {label_col} !important; flex-shrink: 0 !important;
    height: 100% !important;
}}
.stTextInput button svg {{
    fill: {label_col} !important; width: 17px !important; height: 17px !important;
}}

/* ── NUMBER INPUT ── */
[data-testid="stNumberInput"] > div {{
    background: {input_bg} !important;
    border: 1.5px solid {input_bdr} !important;
    border-radius: 10px !important; overflow: hidden !important;
    box-shadow: none !important;
    transition: border-color .15s, box-shadow .15s !important;
}}
[data-testid="stNumberInput"] > div:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
[data-testid="stNumberInput"] input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important; -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter', sans-serif !important;
}}

/* ── BOTÓN SUBMIT VERDE PREMIUM ── */
.stFormSubmitButton > button {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important; font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    padding: 0.7rem 1rem !important; width: 100% !important;
    margin-top: 0.6rem !important;
    box-shadow: 0 4px 16px rgba(22,163,74,0.38) !important;
    transition: all .18s ease !important; cursor: pointer !important;
}}
.stFormSubmitButton > button * {{
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
}}
.stFormSubmitButton > button:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 24px rgba(34,197,94,0.48) !important;
    transform: translateY(-1px) !important;
}}
.stFormSubmitButton > button:active {{
    transform: scale(0.98) !important;
    box-shadow: 0 2px 8px rgba(22,163,74,0.3) !important;
}}

/* ── BOTÓN TEMA — píldora flotante integrada ── */
.stButton > button {{
    background: {tbtn_bg} !important;
    color: {tbtn_txt} !important; -webkit-text-fill-color: {tbtn_txt} !important;
    border: 1px solid {tbtn_bdr} !important;
    border-radius: 999px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important; font-weight: 500 !important;
    padding: 0.35rem 1rem !important;
    backdrop-filter: blur(8px) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
    transition: all .18s ease !important;
}}
.stButton > button:hover {{
    background: {tbtn_hover_bg} !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.18) !important;
}}

/* ── QUITAR FOCUS AMARILLO NATIVO ── */
*, *:focus, *:focus-visible {{
    outline: none !important;
}}
</style>
""", unsafe_allow_html=True)

    # ── LOGO centrado ──
    O = f'<span style="color:{LOGO_GOLD}">O</span>'
    R = f'<span style="color:{LOGO_BLUE}">R</span>'
    A = f'<span style="color:{LOGO_TEAL}">A</span>'
    M = f'<span style="color:{m}">M</span>'

    # Layout: logo + botón tema en la misma fila visual
    st.markdown(f"""
<div style="
    width:100%;max-width:520px;margin:2.5rem auto 0 auto;
    padding:0 1rem;
    display:flex;flex-direction:column;align-items:center;
    position:relative;
">
    <!-- Botón tema como píldora en esquina superior derecha del bloque -->
    <div style="position:absolute;top:0;right:1rem;">
    </div>
    <div style="text-align:center;margin-bottom:0.3rem">
        <span style="font-family:'Space Grotesk',sans-serif;font-size:3.8rem;
            font-weight:800;letter-spacing:-4px;line-height:1">{O}{R}{A}{M}</span>
    </div>
    <div style="font-family:'Space Grotesk',sans-serif;font-size:1rem;
        font-weight:600;color:{m};letter-spacing:0.4px;margin-bottom:0.2rem;text-align:center">
        Quant Systems
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.57rem;
        color:{muted};letter-spacing:3px;text-transform:uppercase;
        margin-bottom:1.4rem;text-align:center">
        {APP_TAGLINE}
    </div>
</div>
""", unsafe_allow_html=True)

    # Botón tema centrado debajo del logo como parte natural del layout
    _, col_mid, _ = st.columns([2, 1, 2])
    with col_mid:
        theme_icon = "☀️ Claro" if dark else "🌙 Oscuro"
        if st.button(theme_icon, key="auth_theme_toggle"):
            toggle_theme()
            st.rerun()

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # Formulario centrado
    _, col_form, _ = st.columns([1, 2, 1])
    with col_form:
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
