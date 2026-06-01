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
    card_bg     = "#0c1219"  if dark else "#ffffff"
    card_border = "#1b2a40"  if dark else "#dde5ef"
    input_bg    = "#080d14"  if dark else "#f0f4f8"
    input_text  = "#c8d8ea"  if dark else "#1a2b3c"
    input_ph    = "#3a5068"  if dark else "#9baab8"
    input_bdr   = "#2a4560"  if dark else "#94a3b8"
    label_col   = "#4a6a84"  if dark else "#6b7f94"
    tab_active  = "#c9a227"
    focus_clr   = "#22c55e"
    focus_glow  = "rgba(34,197,94,0.18)" if dark else "rgba(34,197,94,0.14)"
    shadow      = "0 8px 40px rgba(0,0,0,0.28)" if dark else "0 4px 24px rgba(0,0,0,0.09)"
    eye_col     = "#64748b"  if dark else "#64748b"
    tbtn_bg     = "rgba(12,18,25,0.88)"   if dark else "rgba(255,255,255,0.94)"
    tbtn_txt    = "#c8d8ea"               if dark else "#2a3f54"
    tbtn_bdr    = "rgba(255,255,255,0.12)" if dark else "rgba(0,0,0,0.09)"

    st.markdown(f"""
<style>
/* ══════════════════════════════════════
   FONDO — gradient en html/body, todo
   lo demás transparente
   ══════════════════════════════════════ */
html, body {{
    background: {bg} !important;
    background-attachment: fixed !important;
    min-height: 100vh !important;
}}
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section,
[data-testid="stAppViewContainer"] > section > div,
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.main,
.block-container {{
    background: transparent !important;
    background-color: transparent !important;
    padding: 0 !important;
    max-width: 100% !important;
}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent !important;
    border-bottom: 1px solid {card_border} !important;
    gap: 0 !important; padding: 0 !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Inter',sans-serif !important;
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
.stTextInput label,
.stNumberInput label {{
    color: {label_col} !important;
    font-family: 'Inter',sans-serif !important;
    font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
    margin-bottom: 0.3rem !important; display: block !important;
}}

/* ══════════════════════════════════════════════════════════
   TEXT INPUT — Estrategia definitiva para Streamlit 1.x
   
   La estructura DOM real es:
     .stTextInput
       [data-testid="stTextInputRootElement"]   ← BORDE AQUÍ
         [data-baseweb="input"]                 ← flex row interno
           input                                ← el campo real
           button                               ← ojo
   
   Usamos [data-baseweb="input"] como target principal
   porque es el elemento flex que contiene input + ojo,
   y es consistente entre versiones de Streamlit.
   ══════════════════════════════════════════════════════════ */

/* Reset completo de todos los wrappers previos */
.stTextInput,
.stTextInput > div,
.stTextInput > div > div,
.stTextInput > div > div > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}
.stTextInput {{ margin-bottom: 0.2rem !important; }}

/* ★ EL BORDE VA AQUÍ — [data-baseweb="input"] es el contenedor
     flex real que engloba input + botón ojo en todas las versiones */
.stTextInput [data-baseweb="input"] {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
    min-height: 46px !important;
    overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
}}
.stTextInput [data-baseweb="input"]:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}

/* Base-input interno — solo layout, sin borde */
.stTextInput [data-baseweb="base-input"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
    flex: 1 !important;
    min-height: 46px !important;
    width: 100% !important;
}}

/* Input real — texto */
.stTextInput input {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter',sans-serif !important;
    font-size: 0.93rem !important;
    padding: 0 0.9rem !important;
    flex: 1 !important;
    min-width: 0 !important;
    height: 46px !important;
    width: 100% !important;
}}
.stTextInput input::placeholder {{
    color: {input_ph} !important;
    -webkit-text-fill-color: {input_ph} !important;
    opacity: 1 !important;
}}

/* ── BOTÓN OJO — limpio, sin interferir con el borde ── */
.stTextInput [data-baseweb="input"] button {{
    all: unset !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 44px !important;
    min-width: 44px !important;
    height: 46px !important;
    flex-shrink: 0 !important;
    cursor: pointer !important;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    opacity: 0.55 !important;
    transition: opacity .15s !important;
}}
.stTextInput [data-baseweb="input"] button:hover {{
    opacity: 1 !important;
}}
.stTextInput [data-baseweb="input"] button svg {{
    width: 17px !important;
    height: 17px !important;
    fill: none !important;
    stroke: {eye_col} !important;
    stroke-width: 1.8 !important;
    pointer-events: none !important;
    display: block !important;
    flex-shrink: 0 !important;
}}

/* ── NUMBER INPUT ── */
[data-testid="stNumberInput"],
[data-testid="stNumberInput"] > div,
[data-testid="stNumberInput"] > div > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}
[data-testid="stNumberInput"] [data-baseweb="input"] {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    min-height: 46px !important;
    overflow: hidden !important;
    transition: border-color .18s, box-shadow .18s !important;
}}
[data-testid="stNumberInput"] [data-baseweb="input"]:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
[data-testid="stNumberInput"] input {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: {input_text} !important;
    -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter',sans-serif !important;
    font-size: 0.93rem !important;
    padding: 0 0.75rem !important;
    flex: 1 !important;
    height: 46px !important;
}}

/* ── BOTÓN SUBMIT VERDE ── */
.stFormSubmitButton > button {{
    background: linear-gradient(135deg,#16a34a 0%,#14743d 100%) !important;
    border: none !important; border-radius: 10px !important;
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    font-family: 'Inter',sans-serif !important; font-size: 0.95rem !important;
    font-weight: 600 !important; letter-spacing: 0.3px !important;
    padding: 0.75rem 1rem !important; width: 100% !important;
    margin-top: 0.6rem !important;
    box-shadow: 0 4px 16px rgba(22,163,74,0.38) !important;
    transition: all .18s ease !important; cursor: pointer !important;
}}
.stFormSubmitButton > button * {{
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
}}
.stFormSubmitButton > button:hover {{
    background: linear-gradient(135deg,#22c55e 0%,#16a34a 100%) !important;
    box-shadow: 0 6px 24px rgba(34,197,94,0.48) !important;
    transform: translateY(-1px) !important;
}}
.stFormSubmitButton > button:active {{
    transform: scale(0.98) !important;
    box-shadow: 0 2px 8px rgba(22,163,74,0.3) !important;
}}

/* ── Eliminar outline amarillo ── */
*, *:focus, *:focus-visible {{ outline: none !important; }}
[data-testid="InputInstructions"] {{ display: none !important; }}
</style>
""", unsafe_allow_html=True)

    # ── Cabecera: Logo + botón tema ──
    O = f'<span style="color:{LOGO_GOLD}">O</span>'
    R = f'<span style="color:{LOGO_BLUE}">R</span>'
    A = f'<span style="color:{LOGO_TEAL}">A</span>'
    M = f'<span style="color:{m}">M</span>'

    col_left, col_logo, col_right = st.columns([1, 2, 1])

    with col_logo:
        st.markdown(f"""
<div style="text-align:center;padding:2rem 0 0 0">
  <div style="margin-bottom:0.25rem">
    <span style="font-family:'Space Grotesk',sans-serif;font-size:3.8rem;
        font-weight:800;letter-spacing:-4px;line-height:1">{O}{R}{A}{M}</span>
  </div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:600;
      color:{m};letter-spacing:0.4px;margin-bottom:0.2rem">Quant Systems</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.57rem;
      color:{muted};letter-spacing:3px;text-transform:uppercase;
      margin-bottom:1.4rem">{APP_TAGLINE}</div>
</div>
""", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div style="padding-top:2.1rem;display:flex;justify-content:flex-end">', unsafe_allow_html=True)
        theme_icon = "☀️ Claro" if dark else "🌙 Oscuro"
        st.markdown(f"""
<style>
[data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] > div:last-child .stButton > button {{
    background: {tbtn_bg} !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    color: {tbtn_txt} !important;
    -webkit-text-fill-color: {tbtn_txt} !important;
    border: 1px solid {tbtn_bdr} !important;
    border-radius: 999px !important;
    font-family: 'Inter',sans-serif !important;
    font-size: 0.82rem !important; font-weight: 500 !important;
    padding: 0.4rem 1.1rem !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.18) !important;
    width: auto !important; white-space: nowrap !important;
    float: right !important;
    transition: all .18s ease !important;
}}
</style>
""", unsafe_allow_html=True)
        if st.button(theme_icon, key="auth_theme_toggle"):
            toggle_theme()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Formulario centrado ──
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
