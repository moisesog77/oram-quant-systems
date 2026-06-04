"""
ui/styles.py — ORAM Quant Systems — Premium Design System FINAL
"""
import streamlit as st

APP_NAME    = "ORAM Quant Systems"
APP_ABBR    = "ORAM"
APP_TAGLINE = "Institutional-Grade Trading Intelligence"
APP_VERSION = ""

LOGO_GOLD = "#c9a227"
LOGO_BLUE = "#3d9be9"
LOGO_TEAL = "#00c4a7"

DARK = {
    "bg":          "#06090f",
    "bg_card":     "#0c1219",
    "bg_card2":    "#101822",
    "bg_sidebar":  "#080d14",
    "border":      "#1b2a40",
    "border2":     "#263d58",
    "text":        "#c8d8ea",
    "text_muted":  "#637a94",
    "text_strong": "#edf4ff",
    "accent":      "#c9a227",
    "accent2":     "#3d9be9",
    "accent3":     "#00c4a7",
    "green":       "#22c55e",
    "red":         "#ef4444",
    "purple":      "#8b5cf6",
    "orange":      "#f97316",
    "plot_bg":     "#080c12",
    "grid":        "#121e2e",
    "glow":        "rgba(201,162,39,0.10)",
    "btn_bg":      "transparent",
    "eye_bg":      "#060810",
    "input_bg":    "#0c1219",
    "sb_bg":       "linear-gradient(180deg,#080d14 0%,#060a10 100%)",
    "nav_hover":   "#121e2e",
    "shadow":      "0 4px 24px rgba(0,0,0,0.4)",
    # Sidebar pill buttons
    "sb_theme_bg":  "rgba(12,18,25,0.88)",
    "sb_theme_txt": "#c8d8ea",
    "sb_theme_bdr": "rgba(200,216,234,0.18)",
    "sb_logout_bg":  "rgba(239,68,68,0.10)",
    "sb_logout_txt": "#f87171",
    "sb_logout_bdr": "rgba(239,68,68,0.30)",
    # Sidebar logo — dark: vibrante con glow
    "logo_O": "#e8b830",
    "logo_R": "#4aadff",
    "logo_A": "#00dfc0",
    "logo_glow_O": "0 0 16px rgba(232,184,48,0.70),0 0 36px rgba(232,184,48,0.28)",
    "logo_glow_R": "0 0 16px rgba(74,173,255,0.70),0 0 36px rgba(74,173,255,0.28)",
    "logo_glow_A": "0 0 16px rgba(0,223,192,0.70),0 0 36px rgba(0,223,192,0.28)",
}

LIGHT = {
    "bg":          "#eef2f7",
    "bg_card":     "#ffffff",
    "bg_card2":    "#f7fafc",
    "bg_sidebar":  "#ffffff",
    "border":      "#d0dcea",
    "border2":     "#b5c8dc",
    "text":        "#1a2b3c",
    "text_muted":  "#526070",
    "text_strong": "#0b1824",
    "accent":      "#9a7510",
    "accent2":     "#1660a8",
    "accent3":     "#007a68",
    "green":       "#15803d",
    "red":         "#c81e1e",
    "purple":      "#6d28d9",
    "orange":      "#c2410c",
    "plot_bg":     "#f7fafc",
    "grid":        "#e0e9f2",
    "glow":        "rgba(154,117,16,0.08)",
    "btn_bg":      "#ffffff",
    "eye_bg":      "#d0d7e2",
    "input_bg":    "#ffffff",
    "sb_bg":       "#ffffff",
    "nav_hover":   "#edf3fa",
    "shadow":      "0 4px 16px rgba(0,0,0,0.08)",
    # Sidebar pill buttons
    "sb_theme_bg":  "rgba(255,255,255,0.94)",
    "sb_theme_txt": "#2a3f54",
    "sb_theme_bdr": "rgba(0,0,0,0.09)",
    "sb_logout_bg":  "rgba(239,68,68,0.07)",
    "sb_logout_txt": "#dc2626",
    "sb_logout_bdr": "rgba(220,38,38,0.25)",
    # Sidebar logo — light: saturado y denso, sin glow artificial
    "logo_O": "#a07a00",
    "logo_R": "#1565c0",
    "logo_A": "#007a6a",
    "logo_glow_O": "0 1px 0 rgba(160,122,0,0.18)",
    "logo_glow_R": "0 1px 0 rgba(21,101,192,0.18)",
    "logo_glow_A": "0 1px 0 rgba(0,122,106,0.18)",
}

def get_theme() -> str:
    return st.session_state.get("theme", "dark")

def get_colors() -> dict:
    return DARK if get_theme() == "dark" else LIGHT

def toggle_theme():
    st.session_state["theme"] = "light" if get_theme() == "dark" else "dark"


def inject_styles():
    t    = get_theme()
    c    = DARK if t == "dark" else LIGHT
    dark = t == "dark"
    st.session_state["plot_colors"] = c

    sb  = "rgba(34,197,94,0.07)"  if dark else "rgba(21,128,61,0.06)"
    sbr = "rgba(239,68,68,0.07)"  if dark else "rgba(200,30,30,0.06)"
    sbn = "rgba(201,162,39,0.07)" if dark else "rgba(154,117,16,0.06)"

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;700&family=Space+Grotesk:wght@400;500;600;700;800&display=swap');

/* ── COLOR-SCHEME FORZADO — independiente del SO ─────
   Esto evita que el navegador aplique colores del sistema
   a elementos nativos (scrollbars, inputs, popups).
   DEBE ir primero antes de cualquier otro estilo.        */
html {{
    color-scheme: {'dark' if dark else 'light'} !important;
}}
/* Los portals de Base Web (dropdowns) se renderizan
   directamente en body — necesitan el mismo override   */
body {{
    color-scheme: {'dark' if dark else 'light'} !important;
    background-color: {c['bg']} !important;
    color: {c['text']} !important;
}}
/* Portals de Base Web — contenedor raíz de popups/dropdowns
   Se montan fuera de la jerarquía del iframe de Streamlit */
[data-baseweb="layer"],
[data-baseweb="layer"] > * {{
    color-scheme: {'dark' if dark else 'light'} !important;
}}
/* Cobertura total del portal de dropdowns */
[data-baseweb="layer"] [data-baseweb="popover"],
[data-baseweb="layer"] [data-baseweb="popover"] > *,
[data-baseweb="layer"] [data-baseweb="menu"],
[data-baseweb="layer"] [data-baseweb="menu"] *,
[data-baseweb="layer"] [data-baseweb="calendar"],
[data-baseweb="layer"] [data-baseweb="calendar"] *,
[data-baseweb="layer"] [role="listbox"],
[data-baseweb="layer"] [role="listbox"] *,
[data-baseweb="layer"] ul,
[data-baseweb="layer"] li,
[data-baseweb="layer"] [role="option"] {{
    background-color: {c['bg_card']} !important;
    color: {c['text']} !important;
    border-color: {c['border']} !important;
}}
[data-baseweb="layer"] li:hover,
[data-baseweb="layer"] [role="option"]:hover,
[data-baseweb="layer"] [aria-selected="true"],
[data-baseweb="layer"] [data-highlighted="true"] {{
    background-color: {c['nav_hover']} !important;
    color: {c['text']} !important;
}}
/* Tooltip popups */
[data-baseweb="tooltip"] {{
    background-color: {c['bg_card2']} !important;
    color: {c['text']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 6px !important;
}}

/* ── RESET ─────────────────────────────────────────── */
*,*::before,*::after{{box-sizing:border-box}}
html,body{{
    font-family:'Inter',sans-serif!important;
    background-color:{c['bg']}!important;
    color:{c['text']}!important;
    -webkit-font-smoothing:antialiased;
    min-height:100vh!important;
}}
[class*="css"]{{
    font-family:'Inter',sans-serif!important;
    color:{c['text']}!important;
}}
/* stApp y contenedores internos: TRANSPARENTES para que el gradient de auth pase */
.stApp{{background:transparent!important;background-color:transparent!important;}}
.main,.block-container{{
    background:transparent!important;
    background-color:transparent!important;
    padding-top:1.2rem!important;
    color:{c['text']}!important;
}}
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"]>section,
[data-testid="stAppViewContainer"]>section>div,
[data-testid="stMain"],
[data-testid="stMainBlockContainer"]{{
    background:transparent!important;
    background-color:transparent!important;
}}
[data-testid="stBottom"],[data-testid="stBottom"]>div{{background:{c['bg']}!important}}

/* ── SIDEBAR TOGGLE BUTTON — visible en ambos temas ──────── */
/* Aplica a TODOS los botones de toggle del sidebar sin excepción */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] > *,
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapsedControl"] div {{
    background-color: {c['bg_card']} !important;
    background: {c['bg_card']} !important;
    border: 1px solid {c['border']} !important;
    color: {c['text']} !important;
}}
[data-testid="stSidebarCollapsedControl"] {{
    border-radius: 0 8px 8px 0 !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.12) !important;
    overflow: hidden !important;
}}
[data-testid="stSidebarCollapsedControl"] button {{
    border-radius: 0 !important;
    width: 100% !important;
    height: 100% !important;
    border: none !important;
}}
[data-testid="stSidebarCollapsedControl"] button:hover {{
    background-color: {c['nav_hover']} !important;
}}
/* ── Icono << — negro sólido en todo momento (expandido y colapsado) ── */
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] svg *,
[data-testid="stSidebarCollapsedControl"] svg path,
[data-testid="stSidebarCollapsedControl"] svg polyline,
[data-testid="stSidebarCollapsedControl"] svg line,
[data-testid="stBaseButton-headerNoPadding"] svg,
[data-testid="stBaseButton-headerNoPadding"] svg *,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapseButton"] svg * {{
    fill: {c['text_strong']} !important;
    stroke: {c['text_strong']} !important;
    color: {c['text_strong']} !important;
}}

/* ── HIDE DEPLOY ────────────────────────────────────── */
[data-testid="stDeployButton"],[data-testid="stToolbarActions"]{{display:none!important}}
header[data-testid="stHeader"]{{background:transparent!important;border-bottom:none!important;box-shadow:none!important}}
#MainMenu,footer{{visibility:hidden}}

/* ── SIDEBAR ────────────────────────────────────────── */
section[data-testid="stSidebar"]{{
    background:{c['sb_bg']}!important;
    border-right:1px solid {c['border']}!important;
}}
section[data-testid="stSidebar"] .block-container{{
    padding:0 1rem 1rem 1rem!important;
    background:transparent!important;
}}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div{{color:{c['text']}!important}}

/* ── LOGO CSS ───────────────────────────────────────── */
.oram-logo-wrap{{
    padding:1.4rem 0 1.1rem 0;
    border-bottom:1px solid {c['border']};
    margin-bottom:0.9rem;
}}
.oram-logo{{
    font-family:'Space Grotesk',sans-serif;
    font-size:1.9rem;font-weight:800;
    letter-spacing:-1.5px;line-height:1;
    -webkit-font-smoothing:antialiased;
    text-rendering:geometricPrecision;
}}
/* Logo colores — especificidad máxima para ganar al section div rule */
section[data-testid="stSidebar"] .oram-logo .lo{{
    color:{c['logo_O']}!important;
    text-shadow:{c['logo_glow_O']}!important;
    -webkit-text-stroke:0.4px {c['logo_O']}!important;
}}
section[data-testid="stSidebar"] .oram-logo .lr{{
    color:{c['logo_R']}!important;
    text-shadow:{c['logo_glow_R']}!important;
    -webkit-text-stroke:0.4px {c['logo_R']}!important;
}}
section[data-testid="stSidebar"] .oram-logo .la{{
    color:{c['logo_A']}!important;
    text-shadow:{c['logo_glow_A']}!important;
    -webkit-text-stroke:0.4px {c['logo_A']}!important;
}}
section[data-testid="stSidebar"] .oram-logo .lm{{
    color:{c['text_strong']}!important;
}}
.oram-tagline{{
    font-family:'JetBrains Mono',monospace;
    font-size:0.57rem;color:{c['text_muted']};
    letter-spacing:2px;text-transform:uppercase;margin-top:0.2rem;
}}
.oram-user{{
    font-family:'JetBrains Mono',monospace;
    font-size:0.69rem;color:{c['accent']};margin-top:0.3rem;
}}
.oram-user::before{{content:'▸ ';color:{c['accent3']}}}

/* ── NAV ────────────────────────────────────────────── */
div[role="radiogroup"] label{{
    font-family:'Inter',sans-serif!important;
    font-size:0.82rem!important;font-weight:500!important;
    padding:0.48rem 0.85rem!important;
    border-radius:8px!important;color:{c['text']}!important;
    transition:all .15s ease;border:1px solid transparent!important;
    margin:1px 0!important;
}}
div[role="radiogroup"] label:hover{{
    background:{c['nav_hover']}!important;
    border-color:{c['border']}!important;
}}
div[role="radiogroup"] label p{{color:{c['text']}!important}}

/* ── MÉTRICAS ───────────────────────────────────────── */
[data-testid="stMetricValue"]{{
    font-family:'Space Grotesk',sans-serif!important;
    font-size:1.6rem!important;font-weight:700!important;
    color:{c['text_strong']}!important;letter-spacing:-0.3px;
}}
[data-testid="stMetricLabel"]{{
    font-family:'JetBrains Mono',monospace!important;
    color:{c['text_muted']}!important;font-size:0.66rem!important;
    text-transform:uppercase!important;letter-spacing:1.5px!important;
}}
[data-testid="stMetricDelta"]{{
    font-family:'JetBrains Mono',monospace!important;font-size:0.73rem!important;
}}
[data-testid="metric-container"]{{
    background:{c['bg_card']}!important;
    border:1px solid {c['border']}!important;
    border-radius:12px!important;padding:1rem 1.2rem!important;
    box-shadow:{c['shadow']};transition:border-color .2s,box-shadow .2s;
}}
[data-testid="metric-container"]:hover{{
    border-color:{c['border2']}!important;
}}

/* ── CARDS ──────────────────────────────────────────── */
.oram-card,.smc-card{{
    background:{c['bg_card']};border:1px solid {c['border']};
    border-radius:12px;padding:1.2rem 1.4rem;
    margin-bottom:0.75rem;color:{c['text']};
    box-shadow:{c['shadow']};
}}
.oram-card-gold,.smc-card-accent{{border-left:3px solid {c['accent']}}}
.oram-card-blue,.smc-card-blue  {{border-left:3px solid {c['accent2']}}}
.oram-card-teal                  {{border-left:3px solid {c['accent3']}}}
.oram-card-green,.smc-card-green{{border-left:3px solid {c['green']}}}
.oram-card-red,.smc-card-red    {{border-left:3px solid {c['red']}}}
.oram-card-purple               {{border-left:3px solid {c['purple']}}}

.card-title{{
    font-family:'JetBrains Mono',monospace;
    font-size:0.62rem;text-transform:uppercase;
    letter-spacing:2.5px;color:{c['text_muted']}!important;margin-bottom:0.4rem;
}}
.card-value{{
    font-family:'Space Grotesk',sans-serif;
    font-size:1.4rem;font-weight:700;
    color:{c['text_strong']}!important;letter-spacing:-0.2px;
}}
.card-sub{{
    font-size:0.73rem;color:{c['text_muted']}!important;
    margin-top:0.25rem;line-height:1.55;
}}

/* ── SIGNAL BOXES ───────────────────────────────────── */
.signal-box{{border:1px solid {c['border']};border-radius:10px;padding:1rem 1.2rem;margin:.5rem 0;color:{c['text']}}}
.signal-bull   {{border-color:{c['green']};background:{sb}}}
.signal-bear   {{border-color:{c['red']};background:{sbr}}}
.signal-neutral{{border-color:{c['accent']};background:{sbn}}}
.signal-title  {{font-family:'Space Grotesk',sans-serif;font-size:1rem;font-weight:700}}
.signal-desc   {{font-size:.81rem;color:{c['text_muted']}!important;margin-top:.3rem;line-height:1.6}}

/* ── PAGE HEADER ────────────────────────────────────── */
.page-header{{
    font-family:'Space Grotesk',sans-serif;
    font-size:1.6rem;font-weight:800;
    color:{c['text_strong']}!important;letter-spacing:-.7px;
    margin-bottom:.1rem;line-height:1.1;
}}
.page-sub{{
    font-family:'JetBrains Mono',monospace;
    font-size:.71rem;color:{c['text_muted']}!important;
    margin-bottom:.35rem;letter-spacing:.3px;
}}
.page-accent-line{{
    height:2px;
    background:linear-gradient(90deg,{c['accent']},{c['accent2']},transparent);
    border-radius:2px;margin-bottom:1.3rem;
}}

/* ══════════════════════════════════════════════════════════════
   SISTEMA DE INPUTS PREMIUM — Unificado para toda la app
   Mismo estilo que Login/Crear cuenta en todos los módulos.
   
   Variables de diseño:
     input_bg  : {c['input_bg']}  (fondo del campo)
     border    : #2a4560 oscuro / #94a3b8 claro  (borde normal)  
     focus     : #22c55e  (borde al enfocar — verde)
     focus_glow: rgba(34,197,94,0.18/.14)
     label     : #4a6a84 / #6b7f94  (texto de etiqueta)
     text      : {c['text']}  (texto del valor)
     text_ph   : {c['text_muted']}  (placeholder)
     eye/step  : #64748b  (íconos de acción)
   ══════════════════════════════════════════════════════════════ */

/* ── Variables CSS de tema para uso en pseudo-elementos ── */
:root {{
    --oram-input-bg:      {'#080d14'   if dark else '#f0f4f8'};
    --oram-input-bdr:     {'#2a4560'   if dark else '#94a3b8'};
    --oram-input-text:    {'#c8d8ea'   if dark else '#1a2b3c'};
    --oram-input-ph:      {'#3a5068'   if dark else '#9baab8'};
    --oram-label-col:     {'#4a6a84'   if dark else '#6b7f94'};
    --oram-focus-clr:     #22c55e;
    --oram-focus-glow:    {'rgba(34,197,94,0.18)' if dark else 'rgba(34,197,94,0.14)'};
    --oram-icon-col:      #64748b;
    --oram-card-bg:       {c['bg_card']};
    --oram-border:        {c['border']};
    --oram-nav-hover:     {c['nav_hover']};
    --oram-text:          {c['text']};
    --oram-text-muted:    {c['text_muted']};
    --oram-border2:       {c['border2']};
    --oram-bg-card2:      {c['bg_card2']};
}}

/* ══════════════════════════════════════════════════════════════
   1. LABELS — Todos los inputs
   ══════════════════════════════════════════════════════════════ */
.stTextInput label, .stNumberInput label, .stTextArea label,
.stSelectbox label, .stMultiSelect label, .stDateInput label,
.stRadio label, .stToggle label, .stCheckbox label, .stSlider label {{
    color: var(--oram-label-col) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
    margin-bottom: 0.3rem !important;
    display: block !important;
}}
.stRadio>div>div>label, .stToggle>label {{
    color: var(--oram-text) !important;
    text-transform: none !important;
    font-size: 0.88rem !important;
    letter-spacing: 0 !important;
    font-weight: 500 !important;
}}
.stSlider p {{ color: var(--oram-text) !important; }}

/* ══════════════════════════════════════════════════════════════
   2. TEXT INPUT — Unificado premium
   ══════════════════════════════════════════════════════════════ */
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
    background: var(--oram-input-bg) !important;
    border: 2px solid var(--oram-input-bdr) !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    padding: 0 !important; margin: 0 !important;
    display: flex !important; align-items: center !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
}}
.stTextInput [data-baseweb="input"]:focus-within {{
    border-color: var(--oram-focus-clr) !important;
    box-shadow: 0 0 0 3px var(--oram-focus-glow) !important;
}}
.stTextInput [data-baseweb="base-input"] {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; padding: 0 !important;
    display: flex !important; align-items: center !important;
    flex: 1 !important; min-height: 46px !important; width: 100% !important;
}}
.stTextInput input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.9rem !important; flex: 1 !important;
    height: 46px !important; width: 100% !important;
}}
.stTextInput input::placeholder {{
    color: var(--oram-input-ph) !important;
    -webkit-text-fill-color: var(--oram-input-ph) !important;
    opacity: 1 !important;
}}
/* Botón del ojo — idéntico al del Login */
.stTextInput [data-baseweb="input"] button,
[data-testid="stTextInputRootElement"] button {{
    all: unset !important;
    display: flex !important; align-items: center !important;
    justify-content: center !important;
    width: 44px !important; min-width: 44px !important; height: 46px !important;
    flex-shrink: 0 !important; cursor: pointer !important;
    background: transparent !important; border: none !important;
    padding: 0 !important; margin: 0 !important;
    opacity: 0.55 !important; transition: opacity .15s !important;
}}
.stTextInput [data-baseweb="input"] button:hover,
[data-testid="stTextInputRootElement"] button:hover {{ opacity: 1 !important; }}
.stTextInput [data-baseweb="input"] button svg,
[data-testid="stTextInputRootElement"] button svg {{
    width: 17px !important; height: 17px !important;
    fill: none !important; stroke: var(--oram-icon-col) !important;
    stroke-width: 1.8 !important; pointer-events: none !important;
    display: block !important; flex-shrink: 0 !important;
}}
/* Div fantasma junto al ojo */
.stTextInput [data-baseweb="input"] > div:not(:has(input)):not(:has(button)) {{
    display: none !important;
}}
[data-testid="stTextInputRootElement"] > div > div:empty {{
    display: none !important; width: 0 !important; padding: 0 !important;
}}

/* ══════════════════════════════════════════════════════════════
   3. stTextInputRootElement (variante estructural de Streamlit 1.58+)
   ══════════════════════════════════════════════════════════════ */
[data-testid="stTextInputRootElement"] {{
    background: var(--oram-input-bg) !important;
    border: 2px solid var(--oram-input-bdr) !important;
    border-radius: 10px !important;
    padding: 0 !important;
    display: flex !important; align-items: center !important;
    min-height: 46px !important; overflow: hidden !important;
    transition: border-color .18s, box-shadow .18s !important;
    box-shadow: none !important;
}}
[data-testid="stTextInputRootElement"]:focus-within {{
    border-color: var(--oram-focus-clr) !important;
    box-shadow: 0 0 0 3px var(--oram-focus-glow) !important;
}}
[data-testid="stTextInputRootElement"] input {{
    background: transparent !important;
    border: none !important; box-shadow: none !important; outline: none !important;
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
    flex: 1 !important; padding: 0 0.9rem !important; height: 46px !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.93rem !important;
}}
[data-testid="stTextInputRootElement"] > div {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
    padding: 0 !important; width: 100% !important;
}}
[data-baseweb="input"] {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
    padding: 0 !important; gap: 0 !important;
}}

/* ══════════════════════════════════════════════════════════════
   4. NUMBER INPUT — Premium con ± como el ojo
   ══════════════════════════════════════════════════════════════ */
[data-testid="stNumberInput"] {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
}}
[data-testid="stNumberInput"] > div:nth-child(1) {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2) {{
    background: var(--oram-input-bg) !important;
    border: 2px solid var(--oram-input-bdr) !important;
    border-radius: 10px !important;
    box-shadow: none !important; display: flex !important;
    align-items: center !important; min-height: 46px !important;
    overflow: hidden !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    padding: 0 !important;
}}
[data-testid="stNumberInput"] > div:nth-child(2):focus-within {{
    border-color: var(--oram-focus-clr) !important;
    box-shadow: 0 0 0 3px var(--oram-focus-glow) !important;
}}
[data-testid="stNumberInput"] input,
[data-testid="stNumberInput"] input[type="number"] {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.93rem !important;
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
    align-items: center !important; align-self: stretch !important;
    height: 100% !important; gap: 0 !important;
    padding: 0 !important; margin: 0 !important;
    background: transparent !important; border: none !important;
}}
/* Botones ± — idénticos al ojo */
[data-testid="stNumberInput-StepDown"],
[data-testid="stNumberInput-StepUp"] {{
    all: unset !important;
    box-sizing: border-box !important;
    display: flex !important; align-items: center !important;
    justify-content: center !important; align-self: stretch !important;
    width: 44px !important; min-width: 44px !important;
    height: 100% !important; min-height: 46px !important;
    flex-shrink: 0 !important; cursor: pointer !important;
    border-left: 1px solid var(--oram-input-bdr) !important;
    background: transparent !important;
    padding: 0 !important; margin: 0 !important;
    opacity: 0.55 !important;
    transition: opacity .15s !important;
}}
[data-testid="stNumberInput-StepDown"]:hover,
[data-testid="stNumberInput-StepUp"]:hover {{
    opacity: 1 !important; background: transparent !important;
}}
[data-testid="stNumberInput-StepDown"] svg,
[data-testid="stNumberInput-StepUp"] svg {{
    width: 17px !important; height: 17px !important;
    fill: none !important; stroke: var(--oram-icon-col) !important;
    stroke-width: 1.8 !important; pointer-events: none !important;
    display: block !important; flex-shrink: 0 !important;
    filter: none !important;
}}
/* ── Fantasma / InputInstructions — COBERTURA GLOBAL ── */
[data-testid="InputInstructions"],
[data-testid="InputInstructions"] *,
div[class*="instructions"], p[class*="instructions"],
small[class*="instructions"] {{
    display: none !important; visibility: hidden !important;
    height: 0 !important; min-height: 0 !important;
    margin: 0 !important; padding: 0 !important; overflow: hidden !important;
}}
[data-testid="stNumberInput"] > input,
[data-testid="stNumberInput"] > input:last-child,
[data-testid="stNumberInput"] > div:last-child:not(:nth-child(2)),
[data-testid="stNumberInput"] > *:nth-child(n+3) {{
    display: none !important; visibility: hidden !important;
    height: 0 !important; min-height: 0 !important; max-height: 0 !important;
    margin: 0 !important; padding: 0 !important;
    border: none !important; outline: none !important;
    box-shadow: none !important; opacity: 0 !important;
    position: absolute !important; pointer-events: none !important;
    overflow: hidden !important;
}}
[data-testid="stForm"] [data-testid="stNumberInput"] > input,
[data-testid="stForm"] [data-testid="stNumberInput"] > *:nth-child(n+3) {{
    display: none !important; visibility: hidden !important;
    height: 0 !important; min-height: 0 !important;
    margin: 0 !important; padding: 0 !important;
    border: none !important; opacity: 0 !important;
    position: absolute !important; pointer-events: none !important;
    overflow: hidden !important;
}}
/* Number input — transparente general */
[data-testid="stNumberInput"] * {{ background-color: transparent !important; }}
[data-testid="stNumberInput"] > div {{ background-color: var(--oram-input-bg) !important; }}

/* ══════════════════════════════════════════════════════════════
   5. SELECTBOX — Premium con foco verde
   ══════════════════════════════════════════════════════════════ */
.stSelectbox > div,
.stSelectbox > div > div {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
}}
.stSelectbox [data-baseweb="select"] > div {{
    background: var(--oram-input-bg) !important;
    border: 2px solid var(--oram-input-bdr) !important;
    border-radius: 10px !important;
    min-height: 46px !important;
    transition: border-color .18s, box-shadow .18s !important;
    box-shadow: none !important;
    color: var(--oram-input-text) !important;
    padding: 0 0.75rem !important;
}}
.stSelectbox [data-baseweb="select"]:focus-within > div {{
    border-color: var(--oram-focus-clr) !important;
    box-shadow: 0 0 0 3px var(--oram-focus-glow) !important;
}}
.stSelectbox [data-baseweb="select"] > div > div {{
    color: var(--oram-input-text) !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.93rem !important;
}}
.stSelectbox [data-baseweb="select"] span {{
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
}}
/* Flecha del selectbox */
.stSelectbox [data-baseweb="select"] svg {{
    fill: var(--oram-icon-col) !important;
    opacity: 0.7 !important;
}}
/* Input interno del selectbox — ReadOnly: no escribir texto libre */
.stSelectbox [data-baseweb="select"] input {{
    background: transparent !important;
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
    caret-color: transparent !important;
    pointer-events: none !important;
    user-select: none !important;
}}

/* ══════════════════════════════════════════════════════════════
   6. MULTISELECT — Premium con foco verde
   ══════════════════════════════════════════════════════════════ */
.stMultiSelect > div,
.stMultiSelect > div > div {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
}}
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
    background: var(--oram-input-bg) !important;
    border: 2px solid var(--oram-input-bdr) !important;
    border-radius: 10px !important;
    min-height: 46px !important;
    transition: border-color .18s, box-shadow .18s !important;
    box-shadow: none !important;
    flex-wrap: wrap !important; height: auto !important;
    padding: 4px 8px !important;
}}
[data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within > div {{
    border-color: var(--oram-focus-clr) !important;
    box-shadow: 0 0 0 3px var(--oram-focus-glow) !important;
}}
[data-testid="stMultiSelect"] input {{
    color: var(--oram-input-text) !important;
    background: transparent !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stMultiSelect"] [data-baseweb="select"] svg {{
    fill: var(--oram-icon-col) !important; opacity: 0.7 !important;
}}

/* ══════════════════════════════════════════════════════════════
   7. TEXTAREA — Premium
   ══════════════════════════════════════════════════════════════ */
.stTextArea > div > div,
[data-baseweb="textarea"] {{
    background: var(--oram-input-bg) !important;
    border: 2px solid var(--oram-input-bdr) !important;
    border-radius: 10px !important;
    transition: border-color .18s, box-shadow .18s !important;
    box-shadow: none !important;
}}
.stTextArea > div > div:focus-within,
[data-baseweb="textarea"]:focus-within {{
    border-color: var(--oram-focus-clr) !important;
    box-shadow: 0 0 0 3px var(--oram-focus-glow) !important;
}}
.stTextArea textarea,
[data-baseweb="textarea"] textarea {{
    background: transparent !important; color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
    font-family: 'Inter', sans-serif !important;
    border: none !important; box-shadow: none !important; outline: none !important;
}}

/* ══════════════════════════════════════════════════════════════
   8. DATE INPUT — Premium
   ══════════════════════════════════════════════════════════════ */
[data-testid="stDateInput"] > div {{
    background: var(--oram-input-bg) !important;
    border: 2px solid var(--oram-input-bdr) !important;
    border-radius: 10px !important; overflow: hidden !important;
    transition: border-color .18s, box-shadow .18s !important;
}}
[data-testid="stDateInput"] > div > div {{
    background: transparent !important; border: none !important;
    box-shadow: none !important;
}}
[data-testid="stDateInput"] input {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; outline: none !important;
    color: var(--oram-input-text) !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.93rem !important;
    padding: 0 0.75rem !important; height: 46px !important;
}}
[data-testid="stDateInput"]:focus-within > div {{
    border-color: var(--oram-focus-clr) !important;
    box-shadow: 0 0 0 3px var(--oram-focus-glow) !important;
}}

/* ══════════════════════════════════════════════════════════════
   9. DROPDOWN POPOVER (lista desplegable) — Ambos modos
   ══════════════════════════════════════════════════════════════ */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="menu"] {{
    background: var(--oram-card-bg) !important;
    border: 1px solid var(--oram-border) !important;
    border-radius: 10px !important;
    box-shadow: {c['shadow']} !important;
    color-scheme: {'dark' if dark else 'light'} !important;
}}
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="listbox"] li,
[data-baseweb="popover"] [role="listbox"] ul,
[data-baseweb="menu"] ul,
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"] {{
    background: var(--oram-card-bg) !important;
    color: var(--oram-text) !important;
}}
[data-baseweb="popover"] li:hover,
[data-baseweb="menu"] li:hover,
[data-baseweb="menu"] [role="option"]:hover,
[data-baseweb="menu"] [aria-selected="true"],
[data-baseweb="menu"] [data-highlighted] {{
    background: var(--oram-nav-hover) !important;
    color: var(--oram-text) !important;
}}
[data-baseweb="option"] {{
    background: var(--oram-card-bg) !important;
    color: var(--oram-text) !important;
}}
[data-baseweb="option"]:hover {{ background: var(--oram-nav-hover) !important; }}
/* Scrollbar del dropdown */
[data-baseweb="menu"] ::-webkit-scrollbar {{ width: 4px !important; }}
[data-baseweb="menu"] ::-webkit-scrollbar-track {{
    background: var(--oram-card-bg) !important; border-radius: 2px !important;
}}
[data-baseweb="menu"] ::-webkit-scrollbar-thumb {{
    background: var(--oram-border2) !important; border-radius: 2px !important;
}}
[data-baseweb="menu"] ::-webkit-scrollbar-thumb:hover {{
    background: var(--oram-text-muted) !important;
}}

/* ══════════════════════════════════════════════════════════════
   10. SELECT / MULTISELECT BASE — Cobertura nuclear
   ══════════════════════════════════════════════════════════════ */
[data-baseweb="select"] > div {{
    background-color: var(--oram-input-bg) !important;
    border-color: var(--oram-input-bdr) !important;
    color: var(--oram-input-text) !important;
}}
[data-baseweb="select"] span {{
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
}}
[data-baseweb="select"] input {{
    background: transparent !important;
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
}}
/* Selectbox focus via base-web */
[data-baseweb="select"]:focus-within > div {{
    border-color: var(--oram-focus-clr) !important;
    box-shadow: 0 0 0 3px var(--oram-focus-glow) !important;
}}
/* Base inputs nuclear */
[data-baseweb="input"],
[data-baseweb="base-input"] {{
    background: transparent !important;
    border: none !important; box-shadow: none !important;
    padding: 0 !important; gap: 0 !important;
}}
[data-baseweb="input"] input,
[data-baseweb="base-input"] input,
[data-baseweb="base-input"] textarea {{
    background: transparent !important;
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
}}

/* ══════════════════════════════════════════════════════════════
   11. TAGS MULTISELECT — sin corte de texto
   ══════════════════════════════════════════════════════════════ */
[data-baseweb="tag"] {{
    max-width: none !important; white-space: nowrap !important;
    overflow: visible !important;
    background: var(--oram-bg-card2) !important;
    border: 1px solid var(--oram-border2) !important;
    color: var(--oram-text) !important;
    border-radius: 5px !important; padding: 2px 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
}}
[data-baseweb="tag"] span {{
    color: var(--oram-text) !important;
    -webkit-text-fill-color: var(--oram-text) !important;
    font-family: 'JetBrains Mono', monospace !important;
}}
[data-baseweb="tag"] [role="button"] {{ color: var(--oram-text-muted) !important; }}

/* ══════════════════════════════════════════════════════════════
   12. CALENDAR / DATE PICKER popup
   ══════════════════════════════════════════════════════════════ */
[data-baseweb="calendar"] {{
    background: var(--oram-card-bg) !important;
    border: 1px solid var(--oram-border) !important; border-radius: 10px !important;
}}
[data-baseweb="calendar"] * {{
    background: var(--oram-card-bg) !important; color: var(--oram-text) !important;
}}
[data-baseweb="calendar"] [aria-selected="true"] > div {{
    background: {c['accent']} !important; color: #ffffff !important;
}}

/* ══════════════════════════════════════════════════════════════
   13. RADIO BUTTONS — Diario de Trades LONG/SHORT dinámico
       Cambia el color del label activo según el tema
   ══════════════════════════════════════════════════════════════ */
[data-testid="stRadio"] > div {{ background: transparent !important; }}
[data-testid="stRadio"] label {{
    background: transparent !important;
    border: 1px solid var(--oram-border) !important;
    border-radius: 8px !important; padding: 0.3rem 0.8rem !important;
    color: var(--oram-text) !important; transition: all .15s ease !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stRadio"] label:hover {{
    border-color: {c['accent']} !important; background: {c['glow']} !important;
}}
/* LONG — verde dinámico por tema */
[data-testid="stRadio"] [data-checked="true"] label[data-testid*="LONG"],
[data-testid="stRadio"] label[data-checked="true"]:has(span:first-child) {{
    border-color: {c['green']} !important; color: {c['green']} !important;
}}
/* SHORT — rojo dinámico por tema */
[data-testid="stRadio"] [data-checked="true"] label[data-testid*="SHORT"] {{
    border-color: {c['red']} !important; color: {c['red']} !important;
}}
/* Estado seleccionado genérico (accent del tema) */
[data-testid="stRadio"] [data-checked="true"] label,
[data-testid="stRadio"] label[data-checked="true"] {{
    border-color: {c['accent']} !important; color: {c['accent']} !important;
}}
[data-testid="stRadio"] div[role="radio"] {{
    border-color: var(--oram-border) !important; background: transparent !important;
}}
[data-testid="stRadio"] div[role="radio"][aria-checked="true"] {{
    border-color: {c['accent']} !important; background: {c['accent']} !important;
}}

/* ══════════════════════════════════════════════════════════════
   14. SCROLLBAR GLOBAL — Elegante en ambos modos
   ══════════════════════════════════════════════════════════════ */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{
    background: {'rgba(8,13,20,0.4)' if dark else 'rgba(220,230,240,0.5)'} !important;
    border-radius: 3px !important;
}}
::-webkit-scrollbar-thumb {{
    background: {'rgba(42,69,96,0.8)' if dark else 'rgba(148,163,184,0.7)'} !important;
    border-radius: 3px !important;
}}
::-webkit-scrollbar-thumb:hover {{
    background: {'rgba(74,108,138,0.9)' if dark else 'rgba(100,116,139,0.9)'} !important;
}}
::-webkit-scrollbar-corner {{ background: transparent !important; }}
.stRadio>div>div>label{{color:{c['text']}!important}}
.stToggle>label{{color:{c['text']}!important}}
.stSlider p{{color:{c['text']}!important}}

/* ── BOTONES ────────────────────────────────────────── */
.stButton>button{{
    background:{c['btn_bg']}!important;
    border:1px solid {c['border']}!important;
    color:{c['text']}!important;
    -webkit-text-fill-color:{c['text']}!important;
    font-family:'Inter',sans-serif!important;font-weight:500!important;
    border-radius:8px!important;padding:.48rem 1rem!important;
    transition:all .18s ease;letter-spacing:.15px;
}}
.stButton>button *{{
    color:{c['text']}!important;
    -webkit-text-fill-color:{c['text']}!important;
}}
/* Hover amarillo eliminado — sustituido por hover verde premium global abajo */
/* ══════════════════════════════════════════════════════════
   SIDEBAR PILL BUTTONS — Tema y Salir
   
   Streamlit genera st.button() como:
     <div data-testid="stHorizontalBlock">
       <div>  ← col_t (primer hijo)
         <button data-testid="stBaseButton-secondary">☀️ Claro</button>
       </div>
       <div>  ← col_s (segundo hijo)
         <button data-testid="stBaseButton-secondary">🚪 Salir</button>
       </div>
     </div>
   
   Selector estructural: primer/último hijo del stHorizontalBlock
   que está dentro del sidebar — no depende de ningún data-testid
   ni key inventado. Es la posición real en el DOM.
   ══════════════════════════════════════════════════════════ */

/* BASE — forma pill compartida para ambos botones del sidebar */
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div [data-testid="stBaseButton-secondary"] {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
    min-height: 38px !important;
    box-sizing: border-box !important;
    border-radius: 999px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.2px !important;
    line-height: 1 !important;
    padding: 0.4rem 1.1rem !important;
    cursor: pointer !important;
    transition: all .18s ease !important;
    white-space: nowrap !important;
}}

/* TEMA — primer botón (col izquierda) — glass pill */
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child [data-testid="stBaseButton-secondary"] {{
    background: {c['sb_theme_bg']} !important;
    color: {c['sb_theme_txt']} !important;
    -webkit-text-fill-color: {c['sb_theme_txt']} !important;
    border: 1px solid {c['sb_theme_bdr']} !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.07) !important;
}}
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child [data-testid="stBaseButton-secondary"]:hover {{
    box-shadow: 0 6px 22px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.12) !important;
    transform: translateY(-1px) !important;
    opacity: 0.92 !important;
    border-color: {c['sb_theme_bdr']} !important;
    color: {c['sb_theme_txt']} !important;
    -webkit-text-fill-color: {c['sb_theme_txt']} !important;
    background: {c['sb_theme_bg']} !important;
}}
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child [data-testid="stBaseButton-secondary"]:active {{
    transform: scale(0.97) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18) !important;
    opacity: 1 !important;
}}
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child [data-testid="stBaseButton-secondary"] *,
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child [data-testid="stBaseButton-secondary"] p {{
    color: {c['sb_theme_txt']} !important;
    -webkit-text-fill-color: {c['sb_theme_txt']} !important;
}}

/* SALIR — segundo botón (col derecha) — red pill */
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child [data-testid="stBaseButton-secondary"] {{
    background: {c['sb_logout_bg']} !important;
    color: {c['sb_logout_txt']} !important;
    -webkit-text-fill-color: {c['sb_logout_txt']} !important;
    border: 1px solid {c['sb_logout_bdr']} !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    box-shadow: 0 2px 10px rgba(239,68,68,0.12), inset 0 1px 0 rgba(255,255,255,0.04) !important;
}}
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child [data-testid="stBaseButton-secondary"]:hover {{
    background: rgba(239,68,68,0.22) !important;
    border-color: rgba(239,68,68,0.50) !important;
    box-shadow: 0 6px 22px rgba(239,68,68,0.32) !important;
    transform: translateY(-1px) !important;
    color: {c['sb_logout_txt']} !important;
    -webkit-text-fill-color: {c['sb_logout_txt']} !important;
}}
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child [data-testid="stBaseButton-secondary"]:active {{
    transform: scale(0.97) !important;
    box-shadow: 0 2px 8px rgba(239,68,68,0.20) !important;
}}
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child [data-testid="stBaseButton-secondary"] *,
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child [data-testid="stBaseButton-secondary"] p {{
    color: {c['sb_logout_txt']} !important;
    -webkit-text-fill-color: {c['sb_logout_txt']} !important;
}}
.stButton>button:active{{transform:scale(.98)!important}}

/* ══════════════════════════════════════════════════════════════════
   BOTONES DE ACCIÓN PREMIUM — Verde consistente en toda la app
   
   Afecta solo los st.button() de acción principal, identificados
   por sus key exactas via el atributo aria/data generado por Streamlit.
   Streamlit genera: [data-testid="stBaseButton-secondary"][aria-label]
   pero el selector más robusto es el key del widget que se convierte
   en el ID del botón padre: [key="btn_key"] → div.stButton padre.
   
   Método seguro: los botones de acción con width='stretch' generan
   un contenedor .stButton de ancho completo. Los combinamos con el
   contexto de módulo (fuera de sidebar, fuera de stHorizontalBlock
   de sidebar) para no tocar "Tema" ni "Salir".
   
   Identificación exacta: cada botón tiene un data-testid en el
   contenedor padre stButton. Streamlit también expone el key como
   parte del elemento hijo button — no hay un atributo key directo
   en el DOM, pero sí podemos usar el patrón de que todos los botones
   de acción viven fuera del sidebar y tienen width stretch = 100%.
   Usamos una clase auxiliar .oram-btn-premium inyectada vía JS
   y el selector de texto via :has() o, más seguro, una lista
   explícita de los [data-testid] de los contenedores por posición.
   
   SOLUCIÓN DEFINITIVA: Los st.button con width='stretch' fuera del
   sidebar heredan la clase .stButton con display:block completo.
   Aplicamos el verde a TODOS los .stButton>button fuera del sidebar,
   excepto los 🗑️ (botones de icono pequeño, identificados porque
   su ancho no es stretch y tienen texto de 1-2 chars).
   
   Los botones 🗑️ de watchlist usan key="rm_{{tk}}" y no tienen
   width='stretch' explícito, lo que en el DOM los hace más angostos
   — pero para ser 100% seguros, los excluimos por posición dentro
   de .stHorizontalBlock > div (los delete están siempre en grid).
   ══════════════════════════════════════════════════════════════════ */

/* ── BASE PREMIUM: todos los st.button fuera del sidebar ── */
:not(section[data-testid="stSidebar"]) .stButton>button{{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.3px !important;
    padding: 0.72rem 1rem !important;
    width: 100% !important;
    box-shadow: 0 4px 16px rgba(22, 163, 74, 0.38) !important;
    transition: all .18s ease !important;
    cursor: pointer !important;
}}
:not(section[data-testid="stSidebar"]) .stButton>button *,
:not(section[data-testid="stSidebar"]) .stButton>button p {{
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}}
:not(section[data-testid="stSidebar"]) .stButton>button:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 24px rgba(34, 197, 94, 0.48) !important;
    transform: translateY(-1px) !important;
    border: none !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}}
:not(section[data-testid="stSidebar"]) .stButton>button:active {{
    transform: scale(0.98) !important;
    box-shadow: 0 2px 8px rgba(22, 163, 74, 0.3) !important;
}}

/* ── EXCEPCIÓN 🗑️: botones pequeños de eliminar (Quitar/Delete) ──
   Están dentro de un .stHorizontalBlock anidado en la watchlist.
   Los identificamos porque conviven con texto de activo (cols iguales).
   Los revertimos a estilo neutro compacto. ── */
[data-testid="stHorizontalBlock"] .stButton>button{{
    background: rgba(239,68,68,0.12) !important;
    border: 1px solid rgba(239,68,68,0.30) !important;
    color: #fc5c65 !important;
    -webkit-text-fill-color: #fc5c65 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.35rem 0.7rem !important;
    border-radius: 6px !important;
    box-shadow: none !important;
    width: 100% !important;
}}
[data-testid="stHorizontalBlock"] .stButton>button:hover{{
    background: rgba(239,68,68,0.22) !important;
    border-color: rgba(239,68,68,0.55) !important;
    transform: none !important;
    box-shadow: none !important;
    color: #fc5c65 !important;
    -webkit-text-fill-color: #fc5c65 !important;
}}

.stFormSubmitButton>button{{
    background:linear-gradient(135deg,#16a34a 0%,#14743d 100%)!important;
    border:none!important;
    color:#ffffff!important;
    -webkit-text-fill-color:#ffffff!important;
    font-family:'Inter',sans-serif!important;
    font-weight:600!important;
    font-size:0.95rem!important;
    letter-spacing:0.3px!important;
    border-radius:10px!important;
    padding:0.7rem 1rem!important;
    box-shadow:0 4px 16px rgba(22,163,74,0.38)!important;
    transition:all .18s ease!important;
    margin-top:0.5rem!important;
    width:100%!important;
}}
.stFormSubmitButton>button *{{
    color:#ffffff!important;
    -webkit-text-fill-color:#ffffff!important;
}}
.stFormSubmitButton>button:hover{{
    background:linear-gradient(135deg,#22c55e 0%,#16a34a 100%)!important;
    box-shadow:0 6px 24px rgba(34,197,94,0.48)!important;
    transform:translateY(-1px)!important;
}}
.stFormSubmitButton>button:active{{
    transform:scale(.98)!important;
    box-shadow:0 2px 8px rgba(22,163,74,0.3)!important;
}}

/* ── FORM ───────────────────────────────────────────── */
[data-testid="stForm"]{{
    background:{c['bg_card']}!important;
    border:1px solid {c['border']}!important;
    border-radius:16px!important;padding:1.5rem 1.6rem 1.8rem!important;
    box-shadow:{c['shadow']};
    overflow:visible!important;
}}

/* ── TABS ───────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"]{{
    background:{c['bg_card']};border-bottom:1px solid {c['border']};
    padding:0 .5rem;gap:2px;
}}
.stTabs [data-baseweb="tab"]{{
    font-family:'Inter',sans-serif;font-size:.81rem;font-weight:500;
    color:{c['text_muted']};background:transparent;border:none;
    padding:.62rem 1.1rem;transition:color .15s;
}}
.stTabs [data-baseweb="tab"]:hover{{color:{c['text']}}}
.stTabs [aria-selected="true"]{{
    color:{c['accent']}!important;
    border-bottom:2px solid {c['accent']}!important;font-weight:600!important;
}}
.stTabs [data-baseweb="tab"] p{{color:inherit!important}}

/* ── ALERTS ─────────────────────────────────────────── */
hr{{border-color:{c['border']}!important;margin:1rem 0!important}}
.stAlert,[data-testid="stNotification"]{{
    background:{c['bg_card']}!important;
    border:1px solid {c['border']}!important;
    border-radius:10px!important;color:{c['text']}!important;
}}
.stAlert p,.stAlert div,[data-testid="stNotification"] p,
[data-testid="stNotification"] div{{color:{c['text']}!important}}

/* ── EXPANDER ───────────────────────────────────────── */
[data-testid="stExpander"]{{
    background:{c['bg_card']}!important;
    border:1px solid {c['border']}!important;
    border-radius:10px!important;overflow:hidden;
}}
[data-testid="stExpander"] summary{{
    background:{c['bg_card']}!important;color:{c['text']}!important;
    padding:.7rem 1rem!important;
}}
[data-testid="stExpander"] summary *,
.streamlit-expanderHeader,
.streamlit-expanderHeader p,
.streamlit-expanderHeader span{{color:{c['text']}!important;opacity:1!important}}
[data-testid="stExpander"]>div:last-child{{
    background:{c['bg_card']}!important;color:{c['text']}!important;
    padding:.7rem 1rem 1rem!important;
}}
.streamlit-expanderContent{{background:{c['bg_card']}!important;color:{c['text']}!important}}

/* ── CODE ───────────────────────────────────────────── */
code{{
    background:{c['bg_card2']}!important;color:{c['accent2']}!important;
    border:1px solid {c['border']}!important;border-radius:4px!important;
    padding:2px 7px!important;font-family:'JetBrains Mono',monospace!important;
    font-size:.82em!important;
}}
pre,[data-testid="stCode"]>div{{
    background:{c['bg_card2']}!important;border:1px solid {c['border']}!important;
    border-radius:8px!important;color:{c['text']}!important;
}}
[data-testid="stCode"] code{{background:transparent!important;border:none!important}}

/* ── DATAFRAME ──────────────────────────────────────── */
[data-testid="stDataFrame"]{{
    border:1px solid {c['border']}!important;
    border-radius:10px!important;overflow:hidden;
}}
.stDataFrame thead th{{
    background:{c['bg_card2']}!important;color:{c['text_muted']}!important;
    font-family:'JetBrains Mono',monospace!important;font-size:.67rem!important;
    text-transform:uppercase!important;letter-spacing:1px!important;
    border-color:{c['border']}!important;
}}
.stDataFrame td{{
    color:{c['text']}!important;background:{c['bg_card']}!important;
    font-family:'JetBrains Mono',monospace!important;font-size:.77rem!important;
    border-color:{c['border']}!important;
}}

/* ── MARKDOWN ───────────────────────────────────────── */
.stMarkdown p,.stMarkdown li,.stMarkdown span,
.element-container p{{color:{c['text']}!important}}
.stCaption,.stCaption p,small{{color:{c['text_muted']}!important}}

/* ── PLOTLY ─────────────────────────────────────────── */
[data-testid="stPlotlyChart"]>div{{
    background:transparent!important;border-radius:12px;overflow:hidden;
}}
.js-plotly-plot,.plotly{{background:transparent!important}}

/* ── CONF BAR ───────────────────────────────────────── */
.conf-bar-container{{
    background:{c['border']};border-radius:3px;
    height:5px;width:100%;margin-top:.4rem;overflow:hidden;
}}
.conf-bar-fill{{height:100%;border-radius:3px;transition:width .6s ease}}

/* ── BADGES ─────────────────────────────────────────── */
.level-badge{{
    display:inline-flex;align-items:center;
    font-family:'JetBrains Mono',monospace;font-size:.66rem;
    padding:3px 8px;border-radius:4px;margin:2px;font-weight:600;
}}
.badge-ob-bull {{background:rgba(34,197,94,.12);  color:{c['green']};  border:1px solid rgba(34,197,94,.3)}}
.badge-ob-bear {{background:rgba(239,68,68,.12);  color:{c['red']};    border:1px solid rgba(239,68,68,.3)}}
.badge-fvg-bull{{background:rgba(61,155,233,.12); color:{c['accent2']};border:1px solid rgba(61,155,233,.3)}}
.badge-fvg-bear{{background:rgba(201,162,39,.12); color:{c['accent']}; border:1px solid rgba(201,162,39,.3)}}

/* ── STATUS ─────────────────────────────────────────── */
.status-live{{
    display:inline-block;width:7px;height:7px;
    border-radius:50%;background:{c['green']};
    animation:oram-pulse 2s infinite;
}}
@keyframes oram-pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}



/* ══════════════════════════════════════════════════════════════
   FOCUS GLOBAL — quitar outline amarillo, todo verde
   ══════════════════════════════════════════════════════════════ */
*:focus {{ outline: none !important; }}
*:focus-visible {{
    outline: 2px solid var(--oram-focus-clr) !important;
    outline-offset: 2px !important; box-shadow: none !important;
}}
[data-baseweb="input"]:focus-within,
[data-baseweb="base-input"]:focus-within,
[data-baseweb="textarea"]:focus-within {{
    border-color: var(--oram-focus-clr) !important;
    box-shadow: 0 0 0 3px var(--oram-focus-glow) !important;
}}

/* ══════════════════════════════════════════════════════════════
   COBERTURA NUCLEAR FINAL — evita que Streamlit revierta colores
   ══════════════════════════════════════════════════════════════ */
[data-testid="stNumberInput"]>div>div:last-child {{ background: transparent !important; }}
[data-testid="stNumberInput-StepDown"] {{ background: transparent !important; opacity: 0.55 !important; }}
[data-testid="stNumberInput-StepUp"] {{ background: transparent !important; opacity: 0.55 !important; }}
[data-testid="stNumberInput-StepDown"]:hover {{ background: transparent !important; opacity: 1 !important; }}
[data-testid="stNumberInput-StepUp"]:hover {{ background: transparent !important; opacity: 1 !important; }}
[data-testid="stNumberInput-StepDown"] svg {{ stroke: var(--oram-icon-col) !important; filter: none !important; width: 17px !important; height: 17px !important; stroke-width: 1.8 !important; }}
[data-testid="stNumberInput-StepUp"] svg {{ stroke: var(--oram-icon-col) !important; filter: none !important; width: 17px !important; height: 17px !important; stroke-width: 1.8 !important; }}
input:not([type="range"]):not([type="checkbox"]):not([type="radio"]) {{
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
}}
textarea {{
    color: var(--oram-input-text) !important;
    -webkit-text-fill-color: var(--oram-input-text) !important;
}}
</style>
""", unsafe_allow_html=True)


def page_header(icon: str, title: str, subtitle: str = ""):
    display = f"{icon} {title}" if icon else title
    st.markdown(f'<div class="page-header">{display}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-accent-line"></div>', unsafe_allow_html=True)


def get_plot_layout(height: int = 700) -> dict:
    c  = get_colors()
    tf = dict(color=c["text_muted"], size=9, family="JetBrains Mono")
    return dict(
        height=height,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=c["plot_bg"],
        xaxis_rangeslider_visible=False,
        font=dict(family="JetBrains Mono", size=10, color=c["text_muted"]),
        xaxis=dict(
            gridcolor=c["grid"], color=c["text_muted"],
            tickfont=tf, tickcolor=c["text_muted"],
            linecolor=c["border"], showline=False,
        ),
        yaxis=dict(
            gridcolor=c["grid"], color=c["text_muted"],
            tickfont=tf, tickcolor=c["text_muted"],
            linecolor=c["border"], showline=False, side="right",
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01,
            xanchor="left", x=0,
            font=dict(size=10, color=c["text_muted"]),
            bgcolor="rgba(0,0,0,0)",
        ),
    )


def metric_card(title: str, value: str, sub: str = "", color: str = "gold") -> str:
    return (f'<div class="oram-card oram-card-{color}">'
            f'<div class="card-title">{title}</div>'
            f'<div class="card-value">{value}</div>'
            + (f'<div class="card-sub">{sub}</div>' if sub else "")
            + '</div>')


def signal_box(tipo: str, descripcion: str, confianza: float = 0) -> str:
    c = get_colors()
    if "LONG" in tipo or "Alcista" in tipo:
        cls, color = "signal-bull",    c["green"]
    elif "SHORT" in tipo or "Bajista" in tipo:
        cls, color = "signal-bear",    c["red"]
    else:
        cls, color = "signal-neutral", c["accent"]
    bar = int(min(confianza, 100))
    return (
        f'<div class="signal-box {cls}">'
        f'<div class="signal-title" style="color:{color}">{tipo}</div>'
        f'<div class="signal-desc">{descripcion}</div>'
        f'<div class="conf-bar-container">'
        f'<div class="conf-bar-fill" style="width:{bar}%;background:{color}"></div></div>'
        f'<div class="card-sub" style="margin-top:5px;font-family:\'JetBrains Mono\',monospace">'
        f'Confianza: <span style="color:{color};font-weight:700">{confianza:.0f}%</span>'
        f'</div></div>'
    )
