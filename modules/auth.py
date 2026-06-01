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
    input_bg    = "#080d14"  if dark else "#f4f8fc"
    input_text  = "#c8d8ea"  if dark else "#1a2b3c"
    input_ph    = "#3a5068"  if dark else "#a0aeba"
    input_bdr   = "#263d58"  if dark else "#c8d8e8"
    label_col   = "#4a6a84"  if dark else "#6b7f94"
    tab_active  = "#c9a227"
    focus_clr   = "#22c55e"
    focus_glow  = "rgba(34,197,94,0.18)" if dark else "rgba(34,197,94,0.14)"
    shadow      = "0 8px 40px rgba(0,0,0,0.25)" if dark else "0 4px 24px rgba(0,0,0,0.09)"
    eye_col     = "#3a5068"  if dark else "#9baab8"

    # Colores botón tema
    tbtn_bg  = "rgba(12,18,25,0.85)"   if dark else "rgba(255,255,255,0.92)"
    tbtn_txt = "#c8d8ea"               if dark else "#2a3f54"
    tbtn_bdr = "rgba(255,255,255,0.1)" if dark else "rgba(0,0,0,0.08)"

    st.markdown(f"""
<style>
/* ── FONDO ── */
.main,.stApp,[data-testid="stAppViewContainer"],.block-container {{
    background:{bg}!important;
    padding:0!important;max-width:100%!important;
}}

/* ── BOTÓN TEMA: SOLO UNO, posición fija esquina derecha ──
   Selector específico para el key="auth_theme_toggle"       */
[data-testid="stVerticalBlock"] > [data-testid="element-container"]:first-child .stButton > button,
[data-testid="stVerticalBlock"] > div:first-child .stButton > button {{
    position: fixed !important;
    top: 1rem !important;
    right: 1rem !important;
    z-index: 9999 !important;
    background: {tbtn_bg} !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    color: {tbtn_txt} !important;
    -webkit-text-fill-color: {tbtn_txt} !important;
    border: 1px solid {tbtn_bdr} !important;
    border-radius: 999px !important;
    font-family: 'Inter',sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 1.1rem !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.18) !important;
    width: auto !important;
    white-space: nowrap !important;
    transition: all .18s ease !important;
}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {{
    background:transparent!important;
    border-bottom:1px solid {card_border}!important;
    gap:0!important;padding:0!important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family:'Inter',sans-serif!important;font-size:0.88rem!important;
    font-weight:500!important;color:{label_col}!important;
    background:transparent!important;border:none!important;
    padding:0.6rem 1.1rem!important;
}}
.stTabs [data-baseweb="tab"] p {{
    color:inherit!important;-webkit-text-fill-color:inherit!important;
}}
.stTabs [aria-selected="true"] {{
    color:{tab_active}!important;-webkit-text-fill-color:{tab_active}!important;
    border-bottom:2px solid {tab_active}!important;font-weight:600!important;
}}

/* ── FORM CARD ── */
[data-testid="stForm"] {{
    background:{card_bg}!important;
    border:1px solid {card_border}!important;
    border-radius:16px!important;
    padding:1.8rem 1.8rem 2rem!important;
    box-shadow:{shadow}!important;
    overflow:visible!important;
}}

/* ── LABELS ── */
.stTextInput label,.stNumberInput label {{
    color:{label_col}!important;
    font-family:'Inter',sans-serif!important;
    font-size:0.72rem!important;font-weight:600!important;
    letter-spacing:1px!important;text-transform:uppercase!important;
    margin-bottom:0.3rem!important;display:block!important;
}}

/* ══════════════════════════════════════════════════════
   TEXT INPUT — estructura Streamlit 1.58:
   .stTextInput
     > div  (wrapper sin estilo)
       > div  ← AQUÍ va el borde visible
         > [data-baseweb="input"]  (flex row)
           > input
           > button (ojo)
   ══════════════════════════════════════════════════════ */

/* Capa 0 — widget root: sin nada */
.stTextInput {{margin-bottom:0.1rem!important;}}

/* Capa 1 — primer div: invisible */
.stTextInput > div {{
    background:transparent!important;
    border:none!important;box-shadow:none!important;
    padding:0!important;margin:0!important;
}}

/* Capa 2 — CONTENEDOR CON BORDE — las 4 esquinas redondeadas */
.stTextInput > div > div {{
    background:{input_bg}!important;
    border:1.5px solid {input_bdr}!important;
    border-radius:10px!important;
    padding:0!important;margin:0!important;
    box-shadow:none!important;
    overflow:hidden!important;
    display:flex!important;
    align-items:stretch!important;
    min-height:44px!important;
    transition:border-color .15s,box-shadow .15s!important;
}}
.stTextInput > div > div:focus-within {{
    border-color:{focus_clr}!important;
    box-shadow:0 0 0 3px {focus_glow}!important;
}}

/* Capa 3 — Base Web input: transparente, solo flex */
.stTextInput [data-baseweb="input"],
.stTextInput [data-baseweb="base-input"],
[data-testid="stTextInputRootElement"] {{
    background:transparent!important;
    border:none!important;box-shadow:none!important;
    padding:0!important;margin:0!important;
    width:100%!important;
    display:flex!important;align-items:center!important;
    flex:1!important;
}}

/* Capa 4 — INPUT REAL */
.stTextInput input {{
    background:transparent!important;
    border:none!important;box-shadow:none!important;outline:none!important;
    color:{input_text}!important;-webkit-text-fill-color:{input_text}!important;
    font-family:'Inter',sans-serif!important;font-size:0.93rem!important;
    padding:0 0.85rem!important;
    flex:1!important;min-width:0!important;
    height:44px!important;
}}
.stTextInput input::placeholder {{
    color:{input_ph}!important;-webkit-text-fill-color:{input_ph}!important;
    opacity:1!important;
}}

/* BOTÓN OJO — cero fondo, cero borde */
.stTextInput button,
[data-testid="stTextInputRootElement"] button {{
    all:unset!important;
    display:flex!important;align-items:center!important;
    justify-content:center!important;
    width:42px!important;height:44px!important;
    flex-shrink:0!important;cursor:pointer!important;
    color:{eye_col}!important;
    transition:color .15s!important;
}}
.stTextInput button:hover {{ color:{input_text}!important; }}
.stTextInput button svg {{
    width:17px!important;height:17px!important;
    fill:{eye_col}!important;
}}
.stTextInput button:hover svg {{ fill:{input_text}!important; }}

/* ── NUMBER INPUT ── */
[data-testid="stNumberInput"] > div {{
    background:{input_bg}!important;
    border:1.5px solid {input_bdr}!important;
    border-radius:10px!important;
    overflow:hidden!important;box-shadow:none!important;
    display:flex!important;align-items:center!important;
    min-height:44px!important;
    transition:border-color .15s,box-shadow .15s!important;
}}
[data-testid="stNumberInput"] > div:focus-within {{
    border-color:{focus_clr}!important;
    box-shadow:0 0 0 3px {focus_glow}!important;
}}
[data-testid="stNumberInput"] input {{
    background:transparent!important;border:none!important;
    box-shadow:none!important;outline:none!important;
    color:{input_text}!important;-webkit-text-fill-color:{input_text}!important;
    font-family:'Inter',sans-serif!important;font-size:0.93rem!important;
    padding:0 0.75rem!important;flex:1!important;
}}

/* ── BOTÓN SUBMIT VERDE ── */
.stFormSubmitButton > button {{
    background:linear-gradient(135deg,#16a34a 0%,#14743d 100%)!important;
    border:none!important;border-radius:10px!important;
    color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;
    font-family:'Inter',sans-serif!important;font-size:0.95rem!important;
    font-weight:600!important;letter-spacing:0.3px!important;
    padding:0.72rem 1rem!important;width:100%!important;
    margin-top:0.6rem!important;
    box-shadow:0 4px 16px rgba(22,163,74,0.38)!important;
    transition:all .18s ease!important;cursor:pointer!important;
}}
.stFormSubmitButton > button * {{
    color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;
}}
.stFormSubmitButton > button:hover {{
    background:linear-gradient(135deg,#22c55e 0%,#16a34a 100%)!important;
    box-shadow:0 6px 24px rgba(34,197,94,0.48)!important;
    transform:translateY(-1px)!important;
}}
.stFormSubmitButton > button:active {{
    transform:scale(0.98)!important;
    box-shadow:0 2px 8px rgba(22,163,74,0.3)!important;
}}

/* ── QUITAR FOCUS AMARILLO ── */
*,*:focus,*:focus-visible {{ outline:none!important; }}
</style>
""", unsafe_allow_html=True)

    # ── Botón tema — ÚNICO, va primero para que el selector CSS lo encuentre ──
    theme_icon = "☀️ Claro" if dark else "🌙 Oscuro"
    if st.button(theme_icon, key="auth_theme_toggle"):
        toggle_theme()
        st.rerun()

    # ── Logo ──
    O = f'<span style="color:{LOGO_GOLD}">O</span>'
    R = f'<span style="color:{LOGO_BLUE}">R</span>'
    A = f'<span style="color:{LOGO_TEAL}">A</span>'
    M = f'<span style="color:{m}">M</span>'

    st.markdown(f"""
<div style="width:100%;max-width:520px;margin:2rem auto 1.4rem auto;
    padding:0 1rem;text-align:center;">
  <div style="margin-bottom:0.25rem">
    <span style="font-family:'Space Grotesk',sans-serif;font-size:3.8rem;
        font-weight:800;letter-spacing:-4px;line-height:1">{O}{R}{A}{M}</span>
  </div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:600;
      color:{m};letter-spacing:0.4px;margin-bottom:0.2rem">Quant Systems</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.57rem;
      color:{muted};letter-spacing:3px;text-transform:uppercase">{APP_TAGLINE}</div>
</div>
""", unsafe_allow_html=True)

    # ── Formulario ──
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
