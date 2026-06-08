"""
modules/auth.py — ORAM Quant Systems
"""
import time
import streamlit as st
from database.db import autenticar_usuario, crear_usuario
from ui.styles import toggle_theme, get_theme, APP_TAGLINE, LOGO_GOLD, LOGO_BLUE, LOGO_TEAL, inject_module_css


# ══════════════════════════════════════════════════════
#  HELPER — Pantalla de bienvenida Premium tras registro
# ══════════════════════════════════════════════════════
def _mostrar_bienvenida_premium(username: str, dark: bool) -> None:
    """
    Muestra un overlay de confirmación premium con fade-in,
    luego hace sleep(2.5) y llama st.rerun() para entrar a la app.
    Modular: llámalo desde cualquier flujo de registro con
        _mostrar_bienvenida_premium(username, dark)
    """
    overlay_bg  = "rgba(6,9,15,0.92)"  if dark else "rgba(238,242,247,0.94)"
    card_bg     = "#0c1219"            if dark else "#ffffff"
    card_border = "#1b2a40"            if dark else "#dde5ef"
    text_main   = "#edf4ff"            if dark else "#0b1824"
    text_muted  = "#637a94"            if dark else "#7a8fa0"

    # CSS del overlay + keyframe fade-in (inyectado UNA SOLA VEZ)
    st.markdown(f"""
<style>
@keyframes oram-fadein {{
    from {{ opacity: 0; transform: translateY(14px) scale(0.97); }}
    to   {{ opacity: 1; transform: translateY(0)   scale(1);    }}
}}
@keyframes oram-pulse {{
    0%,100% {{ box-shadow: 0 0 0 0   rgba(34,197,94,0.40); }}
    50%      {{ box-shadow: 0 0 0 18px rgba(34,197,94,0);   }}
}}
@keyframes oram-spin {{
    to {{ transform: rotate(360deg); }}
}}
#oram-welcome-overlay {{
    position: fixed;
    inset: 0;
    background: {overlay_bg};
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
}}
#oram-welcome-card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 20px;
    padding: 2.8rem 3rem 2.4rem;
    text-align: center;
    max-width: 400px;
    width: 90%;
    animation: oram-fadein 0.45s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow: 0 24px 60px rgba(0,0,0,0.35);
}}
.oram-check-ring {{
    width: 64px; height: 64px;
    border-radius: 50%;
    background: rgba(34,197,94,0.12);
    border: 2px solid #22c55e;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 1.4rem;
    animation: oram-pulse 1.6s ease-in-out infinite;
}}
.oram-check-ring svg {{
    width: 30px; height: 30px;
    stroke: #22c55e; fill: none;
    stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round;
}}
.oram-welcome-logo {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem; font-weight: 800;
    letter-spacing: -1px; margin-bottom: 0.15rem;
}}
.oram-welcome-title {{
    font-family: 'Inter', sans-serif;
    font-size: 1.15rem; font-weight: 700;
    color: {text_main}; margin-bottom: 0.5rem;
}}
.oram-welcome-sub {{
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem; color: {text_muted};
    margin-bottom: 1.6rem; line-height: 1.5;
}}
.oram-spinner-row {{
    display: flex; align-items: center;
    justify-content: center; gap: 0.55rem;
}}
.oram-spinner {{
    width: 16px; height: 16px;
    border: 2px solid rgba(34,197,94,0.25);
    border-top-color: #22c55e;
    border-radius: 50%;
    animation: oram-spin 0.75s linear infinite;
    flex-shrink: 0;
}}
.oram-spinner-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem; letter-spacing: 1.5px;
    text-transform: uppercase; color: {text_muted};
}}
</style>
<div id="oram-welcome-overlay">
  <div id="oram-welcome-card">
    <div class="oram-check-ring">
      <svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
    </div>
    <div class="oram-welcome-logo">
      <span style="color:{LOGO_GOLD}">O</span><span style="color:{LOGO_BLUE}">R</span><span style="color:{LOGO_TEAL}">A</span><span style="color:{text_main}">M</span>
      <span style="color:{text_muted};font-weight:500;font-size:0.85rem;letter-spacing:0px"> Quant Systems</span>
    </div>
    <div class="oram-welcome-title">¡Bienvenido, {username}!</div>
    <div class="oram-welcome-sub">
      Tu cuenta ha sido creada con éxito.<br>
      Acceso institucional activado.
    </div>
    <div class="oram-spinner-row">
      <div class="oram-spinner"></div>
      <span class="oram-spinner-label">Cargando plataforma&hellip;</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    time.sleep(2.5)
    st.rerun()


# ══════════════════════════════════════════════════════
#  RENDER PRINCIPAL
# ══════════════════════════════════════════════════════
def render_auth():
    dark  = get_theme() == "dark"
    inject_module_css(dark)  # CSS premium de inputs (SelectBox, NumberInput, TextInput)
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

/* ── TEXT INPUT ── */
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
.stTextInput [data-baseweb="input"] {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    padding: 0 !important; margin: 0 !important;
    display: flex !important; align-items: center !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
}}
.stTextInput [data-baseweb="input"]:focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
.stTextInput [data-baseweb="base-input"] {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; padding: 0 !important; margin: 0 !important;
    display: flex !important; align-items: center !important;
    flex: 1 !important; min-height: 46px !important; width: 100% !important;
}}
.stTextInput input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important; -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter',sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.9rem !important; flex: 1 !important;
    min-width: 0 !important; height: 46px !important; width: 100% !important;
}}
.stTextInput input::placeholder {{
    color: {input_ph} !important; -webkit-text-fill-color: {input_ph} !important;
    opacity: 1 !important;
}}
.stTextInput [data-baseweb="input"] button {{
    all: unset !important;
    display: flex !important; align-items: center !important;
    justify-content: center !important;
    width: 44px !important; min-width: 44px !important; height: 46px !important;
    flex-shrink: 0 !important; cursor: pointer !important;
    background: transparent !important; border: none !important;
    padding: 0 !important; margin: 0 !important;
    opacity: 0.55 !important; transition: opacity .15s !important;
}}
.stTextInput [data-baseweb="input"] button:hover {{ opacity: 1 !important; }}
.stTextInput [data-baseweb="input"] button svg {{
    width: 17px !important; height: 17px !important;
    fill: none !important; stroke: {eye_col} !important;
    stroke-width: 1.8 !important; pointer-events: none !important;
    display: block !important; flex-shrink: 0 !important;
}}

/* ── NUMBER INPUT ── */
[data-testid="stNumberInput"] {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
}}
[data-testid="stNumberInput"] > div:nth-child(1) {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2) {{
    background: {input_bg} !important;
    border: 2px solid {input_bdr} !important;
    border-radius: 10px !important;
    box-shadow: none !important; display: flex !important;
    align-items: center !important; min-height: 46px !important;
    overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    padding: 0 !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2):focus-within {{
    border-color: {focus_clr} !important;
    box-shadow: 0 0 0 3px {focus_glow} !important;
}}
[data-testid="stNumberInput"] input,
[data-testid="stNumberInput"] input[type="number"] {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: {input_text} !important; -webkit-text-fill-color: {input_text} !important;
    font-family: 'Inter',sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; flex: 1 !important;
    height: 46px !important; width: 100% !important;
    -moz-appearance: textfield !important;
}}
[data-testid="stNumberInput"] input::-webkit-outer-spin-button,
[data-testid="stNumberInput"] input::-webkit-inner-spin-button {{
    -webkit-appearance: none !important; margin: 0 !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2) > div:last-child {{
    display: flex !important; flex-direction: row !important;
    align-items: center !important; justify-content: center !important;
    align-self: stretch !important; height: 100% !important;
    gap: 0 !important; padding: 0 !important; margin: 0 !important;
    background: transparent !important; border: none !important;
    box-shadow: none !important;
}}
[data-testid="stNumberInput-StepDown"] {{
    all: unset !important;
    box-sizing: border-box !important;
    display: flex !important; align-items: center !important;
    justify-content: center !important; align-self: stretch !important;
    width: 44px !important; min-width: 44px !important;
    height: 100% !important; min-height: 46px !important;
    flex-shrink: 0 !important; cursor: pointer !important;
    border-left: 1px solid {input_bdr} !important;
    background: transparent !important;
    padding: 0 !important; margin: 0 !important;
    opacity: 0.55 !important;
    transition: opacity .15s !important;
}}
[data-testid="stNumberInput-StepDown"]:hover {{
    opacity: 1 !important;
}}
[data-testid="stNumberInput-StepDown"] svg {{
    width: 17px !important; height: 17px !important;
    fill: none !important; stroke: {eye_col} !important;
    stroke-width: 1.8 !important; pointer-events: none !important;
    display: block !important; flex-shrink: 0 !important;
}}
[data-testid="stNumberInput-StepUp"] {{
    all: unset !important;
    box-sizing: border-box !important;
    display: flex !important; align-items: center !important;
    justify-content: center !important; align-self: stretch !important;
    width: 44px !important; min-width: 44px !important;
    height: 100% !important; min-height: 46px !important;
    flex-shrink: 0 !important; cursor: pointer !important;
    border-left: 1px solid {input_bdr} !important;
    background: transparent !important;
    padding: 0 !important; margin: 0 !important;
    opacity: 0.55 !important;
    transition: opacity .15s !important;
}}
[data-testid="stNumberInput-StepUp"]:hover {{
    opacity: 1 !important;
}}
[data-testid="stNumberInput-StepUp"] svg {{
    width: 17px !important; height: 17px !important;
    fill: none !important; stroke: {eye_col} !important;
    stroke-width: 1.8 !important; pointer-events: none !important;
    display: block !important; flex-shrink: 0 !important;
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

/* ══════════════════════════════════════════════════════════════
   RECUADRO FANTASMA — solución definitiva
   
   Estructura DOM real del stNumberInput:
     [data-testid="stNumberInput"]
       div (1°) — label wrapper
       div (2°) — campo real con borde + botones ± ← MANTENER
       input/div (3°+) — el fantasma ← OCULTAR
   
   Usamos :last-child para apuntar solo al último elemento,
   excluyendo el campo real (2°) que necesitamos visible.
   Con :nth-child(n+3) cubrimos desde el tercero en adelante.
   ══════════════════════════════════════════════════════════════ */

/* Solo el último hijo — el fantasma siempre es el último */
[data-testid="stNumberInput"] > input:last-child,
[data-testid="stNumberInput"] > div:last-child:not(:nth-child(2)),
[data-testid="stNumberInput"] > *:nth-child(n+3) {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    outline: none !important;
    opacity: 0 !important;
    position: absolute !important;
    pointer-events: none !important;
    overflow: hidden !important;
}}

/* Refuerzo dentro de stForm */
[data-testid="stForm"] [data-testid="stNumberInput"] > input:last-child,
[data-testid="stForm"] [data-testid="stNumberInput"] > *:nth-child(n+3) {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    opacity: 0 !important;
    position: absolute !important;
    pointer-events: none !important;
    overflow: hidden !important;
}}

/* InputInstructions — hint "Press Enter to submit form" */
[data-testid="InputInstructions"],
[data-testid="InputInstructions"] *,
div[class*="instructions"],
p[class*="instructions"] {{
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}}
</style>
""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    #  CABECERA — Logo ORAM colorido + botón tema
    # ══════════════════════════════════════════════════
    # Colores más saturados y vibrantes por modo:
    # — Modo oscuro: versiones más brillantes de cada tono (fondo negro amplifica el glow)
    # — Modo claro:  versiones más oscuras y saturadas (necesitan más peso sobre gris)
    if dark:
        c_O   = "#e8b830"   # gold más brillante
        c_R   = "#4aadff"   # blue más eléctrico
        c_A   = "#00dfc0"   # teal más vibrante
        c_M   = "#edf4ff"   # blanco puro
        glow_O = "0 0 18px rgba(232,184,48,0.75),  0 0 40px rgba(232,184,48,0.30)"
        glow_R = "0 0 18px rgba(74,173,255,0.75),  0 0 40px rgba(74,173,255,0.30)"
        glow_A = "0 0 18px rgba(0,223,192,0.75),   0 0 40px rgba(0,223,192,0.30)"
        glow_M = "0 0 14px rgba(237,244,255,0.25)"
    else:
        c_O   = "#a07a00"   # gold oscuro-saturado, legible sobre gris claro
        c_R   = "#1565c0"   # blue profundo
        c_A   = "#007a6a"   # teal oscuro
        c_M   = "#0b1824"   # casi negro
        glow_O = "0 1px 0 rgba(160,122,0,0.18)"
        glow_R = "0 1px 0 rgba(21,101,192,0.18)"
        glow_A = "0 1px 0 rgba(0,122,106,0.18)"
        glow_M = "none"

    O = f'<span style="color:{c_O};text-shadow:{glow_O};-webkit-text-stroke:0.5px {c_O}">O</span>'
    R = f'<span style="color:{c_R};text-shadow:{glow_R};-webkit-text-stroke:0.5px {c_R}">R</span>'
    A = f'<span style="color:{c_A};text-shadow:{glow_A};-webkit-text-stroke:0.5px {c_A}">A</span>'
    M = f'<span style="color:{c_M};text-shadow:{glow_M}">M</span>'

    col_left, col_logo, col_right = st.columns([1, 2, 1])

    with col_logo:
        logo_filter = "drop-shadow(0 0 20px rgba(180,140,30,0.22)) drop-shadow(0 0 8px rgba(61,155,233,0.18))" if dark else "none"
        st.markdown(f"""
<div style="text-align:center;padding:2rem 0 0 0;filter:{logo_filter}">
  <div style="margin-bottom:0.25rem">
    <span style="font-family:'Space Grotesk',sans-serif;font-size:3.8rem;
        font-weight:800;letter-spacing:-4px;line-height:1;
        -webkit-font-smoothing:antialiased;text-rendering:geometricPrecision">{O}{R}{A}{M}</span>
  </div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:600;
      color:{m};letter-spacing:0.4px;margin-bottom:0.2rem;filter:none">{'' if dark else ''}<span style="opacity:0.85">Quant Systems</span></div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.57rem;
      color:{muted};letter-spacing:3px;text-transform:uppercase;
      margin-bottom:1.4rem;filter:none">{APP_TAGLINE}</div>
</div>
""", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div style="padding-top:2.1rem;display:flex;justify-content:flex-end">', unsafe_allow_html=True)
        theme_icon = "☀️ Claro" if dark else "🌙 Oscuro"
        st.markdown(f"""
<style>
[data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] > div:last-child .stButton > button {{
    background: {tbtn_bg} !important;
    backdrop-filter: blur(10px) !important; -webkit-backdrop-filter: blur(10px) !important;
    color: {tbtn_txt} !important; -webkit-text-fill-color: {tbtn_txt} !important;
    border: 1px solid {tbtn_bdr} !important; border-radius: 999px !important;
    font-family: 'Inter',sans-serif !important;
    font-size: 0.82rem !important; font-weight: 500 !important;
    padding: 0.4rem 1.1rem !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.18) !important;
    width: auto !important; white-space: nowrap !important;
    float: right !important; transition: all .18s ease !important;
}}
</style>
""", unsafe_allow_html=True)
        if st.button(theme_icon, key="auth_theme_toggle"):
            toggle_theme()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    #  FORMULARIOS
    # ══════════════════════════════════════════════════
    _, col_form, _ = st.columns([1, 2, 1])
    with col_form:
        tab_login, tab_reg = st.tabs(["Iniciar sesión", "Crear cuenta"])

        # ── Login ──
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
                            st.session_state["session_start"] = datetime.now(timezone.utc).timestamp()
                            st.rerun()
                        else:
                            st.error("Credenciales incorrectas.")

        # ── Registro ──
        with tab_reg:
            with st.form("reg_form"):
                new_user = st.text_input("Usuario", placeholder="elige_un_nombre", key="ru")
                new_pw   = st.text_input("Contraseña", type="password", key="rp")
                new_pw2  = st.text_input("Confirmar contraseña", type="password", key="rp2")
                capital  = st.number_input("Capital inicial (USD)", value=1000.0,
                                           min_value=100.0, step=500.0)
                sub_reg  = st.form_submit_button("Crear cuenta →", width="stretch")

                if sub_reg:
                    # ── Validaciones ──
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
                        if not ok:
                            st.error("Ese nombre de usuario ya existe.")
                        else:
                            # ── Tarea 1: flujo premium ──
                            # 1. Autenticar y guardar sesión en state
                            data = autenticar_usuario(new_user, new_pw)
                            if data:
                                st.session_state.user = data
                                from datetime import datetime, timezone
                                st.session_state["session_start"] = datetime.now(timezone.utc).timestamp()
                            # 2. Mostrar overlay premium + delay + rerun
                            #    (si autenticar falló igual mostramos
                            #     la pantalla y el rerun llevará al login)
                            _mostrar_bienvenida_premium(new_user, dark)
