"""
ui/styles.py — ORAM Quant Systems — Sistema de Diseño Premium
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Responsabilidades:
  · Definir la paleta de colores para modo oscuro (DARK) y claro (LIGHT)
  · Inyectar el CSS global premium vía inject_styles()
  · Proveer funciones utilitarias: get_theme(), get_colors(), toggle_theme()
  · Proveer componentes HTML reutilizables: signal_box(), page_header()
  · Proveer el sistema de notificaciones: oram_notify(), oram_bienvenida()

Principios de diseño:
  · Un solo punto de verdad para todos los estilos (Single Source of Truth)
  · Selectores de alta especificidad con !important para sobrescribir Streamlit
  · Tema dinámico: todos los colores se leen de DARK o LIGHT en tiempo de render
  · Inputs premium unificados: mismo estilo en login, dashboard y todos los módulos
  · Selectbox/multiselect: readonly por CSS (sin escritura libre, solo selección)
  · Barra de scroll: elegante y adaptada al tema (no el negro del sistema)
  · Notificaciones: toast flotante (st.toast) + overlay premium tipo "Bienvenida"

Variables CSS globales (:root):
  --oram-input-bg, --oram-input-bdr, --oram-input-text, --oram-input-ph
  --oram-label-col, --oram-focus-clr, --oram-focus-glow, --oram-icon-col
  Estas variables permiten que módulos externos las referencien sin
  necesitar importar Python — útil para CSS inyectado en módulos.
"""
import time
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
/* Portals [data-baseweb="layer"] — controlados via JS en bloque <script> al final de inject_styles() */
/* Tooltip popups */
[data-baseweb="tooltip"] {{
    background-color: {c['bg_card2']} !important;
    color: {c['text']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 6px !important;
}}

/* ── VARIABLES CSS GLOBALES — usadas por módulos externos ── */
:root {{
    --oram-input-bg:   {c['input_bg']};
    --oram-input-bdr:  {c['border']};
    --oram-input-bdr2: {c['border2']};
    --oram-label-col:  {c['text_muted']};
    --oram-text:       {c['text']};
    --oram-text-muted: {c['text_muted']};
    --oram-bg-card:    {c['bg_card']};
    --oram-accent:     {c['accent']};
    --oram-accent2:    {c['accent2']};
    --oram-green:      {c['green']};
    --oram-focus-clr:  {c['green']};
    --oram-focus-glow: rgba(34,197,94,0.15);
    --oram-icon-col:   {c['text_muted']};
    --oram-shadow:     {c['shadow']};
    --oram-border:     {c['border']};
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
    background-color: {'#080d14' if dark else c['bg_card']} !important;
    background: {'#080d14' if dark else c['bg_card']} !important;
    border: 1px solid {c['border']} !important;
    color: {c['text_strong']} !important;
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

/* ── INPUTS — COMPLETO SIN DOBLE BORDE ─────────────── */
/* Text input (incluye password) */
.stTextInput>div{{
    border:none!important;background:transparent!important;
    box-shadow:none!important;padding:0!important;
    margin:0!important;
}}
.stTextInput>div>div{{
    background:{c['input_bg']}!important;
    border:1.5px solid {c['border']}!important;
    border-radius:10px!important;
    transition:border-color .15s,box-shadow .15s;
    box-shadow:none!important;
    padding:0!important;
    overflow:hidden!important;
    display:flex!important;align-items:center!important;
}}
.stTextInput>div>div:focus-within{{
    border-color:{c['green']}!important;
    box-shadow:0 0 0 3px rgba(34,197,94,0.15)!important;
}}
.stTextInput input{{
    background:transparent!important;color:{c['text']}!important;
    font-family:'JetBrains Mono',monospace!important;
    border:none!important;box-shadow:none!important;outline:none!important;
}}
/* Password — eliminar el div extra que aparece junto al ojo */
.stTextInput [data-baseweb="input"]{{
    background:transparent!important;
    border:none!important;box-shadow:none!important;padding:0!important;
    gap:0!important;
}}
.stTextInput [data-baseweb="input"] > div:not(:has(input)):not(:has(button)){{
    display:none!important;
}}
/* Botón del ojo en password */
.stTextInput [data-testid="textInputRootElement"] button,
.stTextInput button[aria-label*="password"],
.stTextInput button[kind="icon"]{{
    background:transparent!important;
    border:none!important;box-shadow:none!important;
    color:{c['text_muted']}!important;
    padding:0 8px!important;
}}
.stTextInput [data-testid="textInputRootElement"] button svg,
.stTextInput button svg{{
    fill:{c['text_muted']}!important;
    stroke:{c['text_muted']}!important;
}}
/* Textarea */
.stTextArea>div>div{{
    background:{c['input_bg']}!important;
    border:1px solid {c['border']}!important;
    border-radius:8px!important;
}}
.stTextArea>div>div:focus-within{{
    border-color:{c['green']}!important;
    box-shadow:0 0 0 3px rgba(34,197,94,0.15)!important;
}}
.stTextArea textarea{{
    background:transparent!important;color:{c['text']}!important;
    font-family:'Inter',sans-serif!important;
    border:none!important;box-shadow:none!important;
}}
/* Number input — sin doble borde */
[data-testid="stNumberInput"]>div{{
    display:flex!important;align-items:center!important;
    background:{c['input_bg']}!important;
    border:2px solid {c['border2']}!important;
    border-radius:10px!important;overflow:hidden!important;
    gap:0!important;padding:0!important;
    transition:border-color .15s;box-shadow:none!important;
    min-height:46px!important;
}}
[data-testid="stNumberInput"]>div:focus-within{{
    border-color:{c['green']}!important;
    box-shadow:0 0 0 3px rgba(34,197,94,0.15)!important;
}}
[data-testid="stNumberInput"] input{{
    background:transparent!important;border:none!important;
    box-shadow:none!important;outline:none!important;
    color:{c['text']}!important;
    font-family:'Inter',sans-serif!important;
    font-size:0.93rem!important;
    padding:0 0.75rem!important;flex:1!important;
    height:46px!important;
    -moz-appearance:textfield!important;
}}
[data-testid="stNumberInput"] input::-webkit-outer-spin-button,
[data-testid="stNumberInput"] input::-webkit-inner-spin-button{{
    -webkit-appearance:none!important;margin:0!important;
}}
/* Wrapper de los botones +/- — sin fondo propio */
[data-testid="stNumberInput"]>div>div:last-child{{
    display:flex!important;flex-direction:row!important;
    align-items:center!important;align-self:stretch!important;
    height:100%!important;gap:0!important;padding:0!important;
    background:transparent!important;
    border:none!important;
}}
/* Botones +/- — idénticos al botón ojo */
[data-testid="stNumberInput-StepDown"],
[data-testid="stNumberInput-StepUp"]{{
    all:unset!important;
    box-sizing:border-box!important;
    display:flex!important;align-items:center!important;
    justify-content:center!important;align-self:stretch!important;
    width:44px!important;min-width:44px!important;
    height:100%!important;min-height:46px!important;
    flex-shrink:0!important;cursor:pointer!important;
    border-left:1px solid {c['border']}!important;
    background:transparent!important;
    padding:0!important;margin:0!important;
    opacity:0.55!important;
    transition:opacity .15s!important;
}}
[data-testid="stNumberInput-StepDown"]:hover,
[data-testid="stNumberInput-StepUp"]:hover{{
    opacity:1!important;
    background:transparent!important;
}}
[data-testid="stNumberInput-StepDown"] svg,
[data-testid="stNumberInput-StepUp"] svg{{
    width:17px!important;height:17px!important;
    fill:none!important;
    stroke:#64748b!important;
    stroke-width:1.8!important;
    pointer-events:none!important;display:block!important;
    flex-shrink:0!important;
    filter:none!important;
}}
/* ══════════════════════════════════════════════════════
   RECUADRO FANTASMA — el elemento real es un <input>
   que Streamlit inyecta como hermano del contenedor
   del number_input cuando el campo tiene foco.
   
   Estructura DOM real cuando está activo:
     [data-testid="stNumberInput"]
       div (el contenedor con borde — primer hijo)
       input  ← EL FANTASMA (hermano del div, no hijo)
   
   También puede ser [data-testid="InputInstructions"].
   ══════════════════════════════════════════════════════ */
[data-testid="InputInstructions"]{{
    display:none!important;
    visibility:hidden!important;
    height:0!important;
    margin:0!important;
    padding:0!important;
    overflow:hidden!important;
}}
/* El input fantasma — hermano directo del stNumberInput,
   distinto del input real que vive DENTRO del div con borde */
[data-testid="stNumberInput"] > input{{
    display:none!important;
    visibility:hidden!important;
    position:absolute!important;
    height:0!important;
    width:0!important;
    opacity:0!important;
    pointer-events:none!important;
    margin:0!important;
    padding:0!important;
    border:none!important;
}}
/* Por si viene dentro de un form — misma lógica */
[data-testid="stForm"] [data-testid="stNumberInput"] > input{{
    display:none!important;
    visibility:hidden!important;
    position:absolute!important;
    height:0!important;
    width:0!important;
    opacity:0!important;
    pointer-events:none!important;
    margin:0!important;
    border:none!important;
}}
/* Date input — sin doble borde */
[data-testid="stDateInput"]>div{{
    background:{c['input_bg']}!important;
    border:1px solid {c['border']}!important;
    border-radius:8px!important;overflow:hidden!important;
}}
[data-testid="stDateInput"]>div>div{{
    background:transparent!important;border:none!important;box-shadow:none!important;
}}
[data-testid="stDateInput"] input{{
    background:transparent!important;border:none!important;
    box-shadow:none!important;outline:none!important;
    color:{c['text']}!important;
    font-family:'JetBrains Mono',monospace!important;
}}
[data-testid="stDateInput"]:focus-within>div{{
    border-color:{c['green']}!important;
    box-shadow:0 0 0 3px rgba(34,197,94,0.15)!important;
}}
/* ══════════════════════════════════════════════════════════════
   SELECTBOX — Premium unificado con foco verde
   ─────────────────────────────────────────────────────────────
   Estructura DOM de st.selectbox:
     .stSelectbox
       div           → wrapper externo (limpiar bordes)
       div > div     → contenedor principal con borde premium
         [data-baseweb="select"] > div  → el control visual
           span      → texto seleccionado
           div       → flecha chevron
         input       → campo oculto interno (NO debe escribirse)

   Comportamiento:
   · Solo dropdown — el usuario elige, no escribe
   · caret-color: transparent  → oculta el cursor de texto
   · user-select: none         → no se puede seleccionar/copiar
   · pointer-events: none      → en el input interno (no en el div)
   · El div externo conserva pointer-events para abrir el dropdown
   ══════════════════════════════════════════════════════════════ */
.stSelectbox > div {{
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important; margin: 0 !important;
}}
.stSelectbox > div > div {{
    background: {c['input_bg']} !important;
    border: 2px solid {c['border2']} !important;
    border-radius: 10px !important;
    min-height: 46px !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
    box-shadow: none !important;
    display: flex !important; align-items: center !important;
    cursor: pointer !important;
}}
.stSelectbox > div > div:focus-within {{
    border-color: {c['green']} !important;
    box-shadow: 0 0 0 3px rgba(34,197,94,0.15) !important;
}}
.stSelectbox [data-baseweb="select"] > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: {c['text']} !important;
    padding: 0 0.75rem !important;
    min-height: 44px !important;
    cursor: pointer !important;
}}
.stSelectbox [data-baseweb="select"] span {{
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.93rem !important;
}}
/* Flecha/chevron del selectbox */
.stSelectbox [data-baseweb="select"] svg {{
    fill: #64748b !important;
    opacity: 0.7 !important;
    flex-shrink: 0 !important;
}}
/* ── READONLY: el input interno NO debe permitir escritura libre ──
   El input interno de Base Web es un campo de búsqueda oculto.
   Lo deshabilitamos visualmente para que funcione SOLO como selector. */
.stSelectbox [data-baseweb="select"] input,
.stSelectbox input {{
    background: transparent !important;
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
    caret-color: transparent !important;    /* oculta cursor de texto      */
    user-select: none !important;           /* no seleccionable con mouse   */
    -webkit-user-select: none !important;
    pointer-events: none !important;        /* no recibe clics directos     */
    cursor: pointer !important;
}}

/* ══════════════════════════════════════════════════════════════
   MULTISELECT — Premium con foco verde y tags elegantes
   ─────────────────────────────────────────────────────────────
   Diferencia con selectbox: permite múltiples selecciones.
   El input interno SÍ debe recibir texto para filtrar opciones,
   pero no queremos que parezca un campo de texto libre —
   se oculta el cursor y se mantiene el estilo coherente.
   ══════════════════════════════════════════════════════════════ */
[data-testid="stMultiSelect"] > div {{
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important; margin: 0 !important;
}}
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
    background: {c['input_bg']} !important;
    border: 2px solid {c['border2']} !important;
    border-radius: 10px !important;
    min-height: 46px !important;
    transition: border-color .18s, box-shadow .18s !important;
    box-shadow: none !important;
    flex-wrap: wrap !important;
    height: auto !important;
    padding: 4px 8px !important;
    cursor: pointer !important;
}}
[data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within > div {{
    border-color: {c['green']} !important;
    box-shadow: 0 0 0 3px rgba(34,197,94,0.15) !important;
}}
[data-testid="stMultiSelect"] [data-baseweb="select"] svg {{
    fill: #64748b !important;
    opacity: 0.7 !important;
}}
/* Input de búsqueda dentro del multiselect — permite escribir para filtrar */
[data-testid="stMultiSelect"] input {{
    background: transparent !important;
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
    caret-color: {c['green']} !important;   /* cursor visible pero verde    */
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    min-width: 60px !important;
}}
/* Labels */
.stTextInput label,.stNumberInput label,.stTextArea label,
.stSelectbox label,.stSlider label,.stDateInput label,
.stRadio label,.stToggle label,.stMultiSelect label,.stCheckbox label{{
    color:{c['text']}!important;font-family:'Inter',sans-serif!important;
    font-size:.81rem!important;font-weight:500!important;margin-bottom:.15rem!important;
}}
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

/* ── EXCEPCIÓN: botones de ACCIÓN PRINCIPAL (type=primary) dentro de stHorizontalBlock ──
   El btn "Actualizar análisis" vive en st.columns → stHorizontalBlock pero
   debe mantener el estilo verde premium, no el rojo de watchlist.
   El selector [data-testid="stBaseButton-primary"] identifica type="primary". ── */
[data-testid="stHorizontalBlock"] .stButton>[data-testid="stBaseButton-primary"],
[data-testid="stHorizontalBlock"] [data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, #16a34a 0%, #14743d 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.72rem 1rem !important;
    box-shadow: 0 4px 14px 0 rgba(16, 185, 129, 0.39) !important;
    transition: box-shadow 0.25s ease, transform 0.18s ease !important;
    width: 100% !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stBaseButton-primary"]:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 22px 0 rgba(16, 185, 129, 0.58) !important;
    transform: translateY(-1px) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stBaseButton-primary"]:active {{
    box-shadow: 0 2px 8px 0 rgba(16, 185, 129, 0.30) !important;
    transform: translateY(0) !important;
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

/* ── BOTÓN PRIMARY (type="primary") — glow institucional ORAM ──────────
   Aplica a st.button(..., type="primary") en cualquier contexto.
   Especificidad mayor que el selector genérico de arriba.           ── */
[data-testid="stBaseButton-primary"] {{
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
    box-shadow: 0 4px 14px 0 rgba(16, 185, 129, 0.39) !important;
    transition: box-shadow 0.25s ease, transform 0.18s ease, background 0.18s ease !important;
    cursor: pointer !important;
    width: 100% !important;
}}
[data-testid="stBaseButton-primary"] * {{
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    box-shadow: 0 6px 22px 0 rgba(16, 185, 129, 0.58) !important;
    transform: translateY(-1px) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}}
[data-testid="stBaseButton-primary"]:active {{
    box-shadow: 0 2px 8px 0 rgba(16, 185, 129, 0.30) !important;
    transform: scale(0.98) !important;
}}
@keyframes oram-btn-confirm {{
    0%   {{ box-shadow: 0 4px 14px 0 rgba(16, 185, 129, 0.39); }}
    30%  {{ box-shadow: 0 0 0 6px rgba(34,197,94,0.45), 0 4px 22px 0 rgba(16,185,129,0.70); }}
    70%  {{ box-shadow: 0 0 0 12px rgba(34,197,94,0.10), 0 4px 18px 0 rgba(16,185,129,0.50); }}
    100% {{ box-shadow: 0 4px 14px 0 rgba(16, 185, 129, 0.39); }}
}}
.oram-btn-confirming {{
    animation: oram-btn-confirm 0.7s cubic-bezier(0.22,1,0.36,1) both !important;
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
/* ── Chart card: estilo premium directamente sobre el contenedor de Plotly ── */
/* Elimina la necesidad del div wrapper HTML que genera el elemento en blanco */
.element-container:has([data-testid="stPlotlyChart"]) {{
    background: {c['bg_card']} !important;
    border: 1.5px solid {c['border2']} !important;
    border-radius: 14px !important;
    padding: 0.75rem 0.25rem 0.5rem 0.25rem !important;
    box-shadow: {c['shadow']} !important;
    overflow: hidden !important;
    margin-top: 0 !important;
}}
[data-testid="stPlotlyChart"]>div{{
    background:transparent!important;border-radius:0;overflow:hidden;
}}
.js-plotly-plot,.plotly{{background:transparent!important}}

/* ── Eliminar espacio entre st.success/warning/error y lo que sigue ── */
/* El elemento en blanco entre alert y gráfica */
.element-container:has([data-testid="stAlert"]) + .element-container {{
    margin-top: 0 !important;
}}
.element-container:empty,
div[data-testid="stVerticalBlockBorderWrapper"]:empty {{
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}}

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


/* ═══ NUCLEAR FIX — cobertura total de widgets ═══════════════ */
/* Base inputs */
[data-baseweb="input"],
[data-baseweb="base-input"] {{
    background: {c['input_bg']} !important;
    border-color: {c['border']} !important;
}}
[data-baseweb="input"] input,
[data-baseweb="base-input"] input,
[data-baseweb="base-input"] textarea {{
    background: transparent !important;
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
}}
/* Textarea — sin borde negro, solo el del contenedor */
[data-baseweb="textarea"] {{
    background: {c['input_bg']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 8px !important;
}}
[data-baseweb="textarea"] textarea {{
    background: transparent !important;
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}}
/* Number input — transparente general incluyendo botones ± */
[data-testid="stNumberInput"] * {{ background-color: transparent !important; }}
[data-testid="stNumberInput"] > div {{ background-color: {c['input_bg']} !important; }}
/* ── Cobertura global de selectbox Base Web (portals y inline) ──
   Aplica el color correcto sin sobreescribir el readonly del bloque superior */
[data-baseweb="select"] > div {{
    background-color: {c['input_bg']} !important;
    border-color: {c['border2']} !important;
    color: {c['text']} !important;
}}
[data-baseweb="select"] span {{
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
}}
/* Input interno de cualquier select — READONLY global */
[data-baseweb="select"] input {{
    background: transparent !important;
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
    caret-color: transparent !important;
    user-select: none !important;
    -webkit-user-select: none !important;
}}
/* Dropdown menu popup — CRÍTICO para fondo de la lista.
   Se aplica tanto dentro de la app como en portals de body */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] [data-baseweb="menu"] {{
    background: {c['bg_card']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 8px !important;
    box-shadow: {c['shadow']} !important;
    color-scheme: {'dark' if dark else 'light'} !important;
}}
[data-baseweb="menu"] {{
    background: {c['bg_card']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 8px !important;
    box-shadow: {c['shadow']} !important;
    color-scheme: {'dark' if dark else 'light'} !important;
}}
[data-baseweb="menu"] ul,
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"] {{
    background: {c['bg_card']} !important;
    color: {c['text']} !important;
}}
[data-baseweb="menu"] li:hover,
[data-baseweb="menu"] [role="option"]:hover,
[data-baseweb="menu"] [aria-selected="true"],
[data-baseweb="menu"] [data-highlighted] {{
    background: {c['nav_hover']} !important;
    color: {c['text']} !important;
}}
[data-baseweb="option"] {{
    background: {c['bg_card']} !important;
    color: {c['text']} !important;
}}
[data-baseweb="option"]:hover {{
    background: {c['nav_hover']} !important;
}}
/* Date picker popup */
[data-baseweb="calendar"] {{
    background: {c['bg_card']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 10px !important;
}}
[data-baseweb="calendar"] * {{
    background: {c['bg_card']} !important;
    color: {c['text']} !important;
}}
[data-baseweb="calendar"] [aria-selected="true"] > div {{
    background: {c['accent']} !important;
    color: #ffffff !important;
}}
/* Tags multiselect — sin amarillo */
[data-baseweb="tag"] {{
    background: {c['bg_card2']} !important;
    border: 1px solid {c['border2']} !important;
    color: {c['text']} !important;
    border-radius: 5px !important;
}}
[data-baseweb="tag"] span {{
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
}}
/* Todos los inputs — cobertura total */
input:not([type="range"]):not([type="checkbox"]):not([type="radio"]) {{
    background-color: {c['input_bg']} !important;
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
}}
textarea {{
    background-color: {c['input_bg']} !important;
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
}}

/* ═══ RADIO BUTTONS — sin fondo oscuro ══════════════════════ */
[data-testid="stRadio"] > div {{
    background: transparent !important;
}}
[data-testid="stRadio"] label {{
    background: transparent !important;
    border: 1px solid {c['border']} !important;
    border-radius: 8px !important;
    padding: 0.3rem 0.8rem !important;
    color: {c['text']} !important;
    transition: all .15s ease;
}}
[data-testid="stRadio"] label:hover {{
    border-color: {c['accent']} !important;
    background: {c['glow']} !important;
}}
[data-testid="stRadio"] [data-checked="true"] label,
[data-testid="stRadio"] label[data-checked="true"] {{
    border-color: {c['accent']} !important;
    color: {c['accent']} !important;
}}
/* Radio circle dot — override dark color — tema adaptable */
[data-testid="stRadio"] div[role="radio"],
[data-testid="stRadio"] span[data-testid="stWidgetLabel"] ~ div div[role="radio"],
div[role="radiogroup"] div[role="radio"] {{
    border-color: {c['border2']} !important;
    background: {c['bg_card']} !important;
    box-shadow: none !important;
}}
[data-testid="stRadio"] div[role="radio"][aria-checked="true"],
div[role="radiogroup"] div[role="radio"][aria-checked="true"] {{
    border-color: {c['accent']} !important;
    background: {c['accent']} !important;
}}
/* SVG/círculo nativo dentro del radio */
[data-testid="stRadio"] div[role="radio"] > div,
[data-testid="stRadio"] div[role="radio"] svg,
div[role="radiogroup"] div[role="radio"] > div,
div[role="radiogroup"] div[role="radio"] svg {{
    background: transparent !important;
    fill: {c['accent']} !important;
    color: {c['accent']} !important;
}}
/* Asegurar que el círculo exterior no sea negro en modo claro */
[data-testid="stRadio"] label input[type="radio"] + div,
section[data-testid="stSidebar"] div[role="radio"] {{
    border-color: {c['border2']} !important;
    background-color: {c['bg_card']} !important;
}}

/* ═══ MULTISELECT TAGS — texto completo, sin corte ══════════ */
[data-baseweb="tag"] {{
    max-width: none !important;
    white-space: nowrap !important;
    overflow: visible !important;
    background: {c['bg_card2']} !important;
    border: 1px solid {c['border2']} !important;
    color: {c['text']} !important;
    border-radius: 5px !important;
    padding: 2px 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
}}
[data-baseweb="tag"] span {{
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
    font-family: 'JetBrains Mono', monospace !important;
}}
[data-baseweb="tag"] [role="button"] {{
    color: {c['text_muted']} !important;
}}
/* ── PASSWORD INPUT — eliminar espacio extra junto al ojo ── */
/* En Streamlit 1.58 el password wrapper tiene estructura:
   stTextInput > div > div[data-baseweb="input"] > div.input > input
                                                 > div.trailing > button(ojo)
   El div extra que genera el espacio es un segundo div vacío */
[data-testid="stTextInputRootElement"]{{
    background:{c['input_bg']}!important;
    border:1px solid {c['border']}!important;
    border-radius:8px!important;
    padding:0!important;
    display:flex!important;align-items:center!important;
    transition:border-color .15s,box-shadow .15s;
    box-shadow:none!important;
}}
[data-testid="stTextInputRootElement"]:focus-within{{
    border-color:{c['accent']}!important;
    box-shadow:0 0 0 3px {c['glow']}!important;
}}
[data-testid="stTextInputRootElement"] input{{
    background:transparent!important;
    border:none!important;box-shadow:none!important;outline:none!important;
    color:{c['text']}!important;
    -webkit-text-fill-color:{c['text']}!important;
    flex:1!important;padding:.45rem .6rem!important;
    font-family:'JetBrains Mono',monospace!important;
}}
[data-testid="stTextInputRootElement"] > div{{
    background:transparent!important;
    border:none!important;box-shadow:none!important;
    padding:0!important;width:100%!important;
}}
/* Botón ojo — sin fondo extra */
[data-testid="stTextInputRootElement"] button{{
    background:transparent!important;
    border:none!important;box-shadow:none!important;
    padding:0 10px!important;cursor:pointer!important;
    color:{c['text_muted']}!important;flex-shrink:0!important;
}}
[data-testid="stTextInputRootElement"] button:hover{{
    color:{c['text']}!important;
}}
[data-testid="stTextInputRootElement"] button svg{{
    fill:{c['text_muted']}!important;width:16px!important;height:16px!important;
}}
/* Anular el div fantasma que crea el espacio extra */
[data-testid="stTextInputRootElement"] > div > div:empty{{
    display:none!important;width:0!important;padding:0!important;
}}
[data-baseweb="input"]{{
    background:transparent!important;
    border:none!important;box-shadow:none!important;
    padding:0!important;gap:0!important;
}}

/* ── FOCUS GLOBAL — quitar amarillo, todo verde ─────── */
*:focus{{outline:none!important}}
*:focus-visible{{
    outline:2px solid {c['green']}!important;
    outline-offset:2px!important;
    box-shadow:none!important;
}}
/* Inputs Base Web — foco verde */
[data-baseweb="input"]:focus-within,
[data-baseweb="base-input"]:focus-within,
[data-baseweb="textarea"]:focus-within {{
    border-color:{c['green']}!important;
    box-shadow:0 0 0 3px rgba(34,197,94,0.15)!important;
}}
/* Selectbox focus */
[data-baseweb="select"]:focus-within > div {{
    border-color:{c['green']}!important;
    box-shadow:0 0 0 3px rgba(34,197,94,0.15)!important;
}}

/* ── SCROLLBAR ──────────────────────────────────────── */
::-webkit-scrollbar{{width:4px;height:4px}}
::-webkit-scrollbar-track{{background:{c['bg']}}}
::-webkit-scrollbar-thumb{{background:{c['border2']};border-radius:2px}}
::-webkit-scrollbar-thumb:hover{{background:{c['accent']}}}
/* ═══ FORZADO FINAL — wrapper +/- transparente, igual que zona del ojo ═══ */
[data-testid="stNumberInput"]>div>div:last-child {{ background: transparent !important; }}
[data-testid="stNumberInput-StepDown"] {{ background: transparent !important; opacity: 0.55 !important; }}
[data-testid="stNumberInput-StepUp"] {{ background: transparent !important; opacity: 0.55 !important; }}
[data-testid="stNumberInput-StepDown"]:hover {{ background: transparent !important; opacity: 1 !important; }}
[data-testid="stNumberInput-StepUp"]:hover {{ background: transparent !important; opacity: 1 !important; }}
[data-testid="stNumberInput-StepDown"] svg {{ stroke: #64748b !important; filter: none !important; width: 17px !important; height: 17px !important; stroke-width: 1.8 !important; }}
[data-testid="stNumberInput-StepUp"] svg {{ stroke: #64748b !important; filter: none !important; width: 17px !important; height: 17px !important; stroke-width: 1.8 !important; }}

/* ══════════════════════════════════════════════════════════════
   SISTEMA DE NOTIFICACIONES PREMIUM — Toast + Banners
   ══════════════════════════════════════════════════════════════ */

/* ── st.toast — burbuja flotante esquina inferior derecha ── */
[data-testid="stToast"] {{
    border-radius: 12px !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-left: 4px solid transparent !important;
    padding: 0.85rem 1.1rem !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35), 0 2px 8px rgba(0,0,0,0.18) !important;
    min-width: 280px !important;
    max-width: 360px !important;
    animation: oram-toast-in 0.28s cubic-bezier(0.34,1.56,0.64,1) !important;
}}
@keyframes oram-toast-in {{
    from {{ opacity: 0; transform: translateY(14px) scale(0.95); }}
    to   {{ opacity: 1; transform: translateY(0)    scale(1);    }}
}}
/* Toast icono */
[data-testid="stToast"] [data-testid="stMarkdownContainer"] p {{
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    margin: 0 !important; line-height: 1.45 !important;
    color: {c['text_strong']} !important;
}}
/* Toast botón X de cierre */
[data-testid="stToast"] button {{
    opacity: 0.5 !important; transition: opacity .15s !important;
    background: transparent !important; border: none !important;
}}
[data-testid="stToast"] button:hover {{ opacity: 1 !important; }}

/* ── Banners inline — st.success / error / warning / info ── */
/* SUCCESS */
[data-testid="stAlert"][kind="success"],
div[data-testid="stAlert"].st-success,
.element-container:has([data-testid="stAlert"][kind="success"]) {{
    background: {'rgba(22,163,74,0.12)' if dark else 'rgba(22,163,74,0.08)'} !important;
    border: 1px solid {'rgba(34,197,94,0.35)' if dark else 'rgba(22,163,74,0.3)'} !important;
    border-left: 4px solid #22c55e !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 12px rgba(34,197,94,0.12) !important;
    animation: oram-banner-in 0.22s ease !important;
}}
[data-testid="stAlert"][kind="success"] p,
[data-testid="stAlert"][kind="success"] [data-testid="stMarkdownContainer"] p {{
    color: {'#4ade80' if dark else '#15803d'} !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}}
[data-testid="stAlert"][kind="success"] svg {{
    color: #22c55e !important; fill: #22c55e !important;
}}
/* ERROR */
[data-testid="stAlert"][kind="error"],
div[data-testid="stAlert"].st-error {{
    background: {'rgba(239,68,68,0.12)' if dark else 'rgba(200,30,30,0.07)'} !important;
    border: 1px solid {'rgba(239,68,68,0.35)' if dark else 'rgba(200,30,30,0.28)'} !important;
    border-left: 4px solid #ef4444 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 12px rgba(239,68,68,0.10) !important;
    animation: oram-banner-in 0.22s ease !important;
}}
[data-testid="stAlert"][kind="error"] p,
[data-testid="stAlert"][kind="error"] [data-testid="stMarkdownContainer"] p {{
    color: {'#f87171' if dark else '#c81e1e'} !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important; font-size: 0.88rem !important;
}}
[data-testid="stAlert"][kind="error"] svg {{
    color: #ef4444 !important; fill: #ef4444 !important;
}}
/* WARNING */
[data-testid="stAlert"][kind="warning"],
div[data-testid="stAlert"].st-warning {{
    background: {'rgba(201,162,39,0.12)' if dark else 'rgba(154,117,16,0.08)'} !important;
    border: 1px solid {'rgba(201,162,39,0.35)' if dark else 'rgba(154,117,16,0.28)'} !important;
    border-left: 4px solid #c9a227 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 12px rgba(201,162,39,0.10) !important;
    animation: oram-banner-in 0.22s ease !important;
}}
[data-testid="stAlert"][kind="warning"] p,
[data-testid="stAlert"][kind="warning"] [data-testid="stMarkdownContainer"] p {{
    color: {'#f1c232' if dark else '#9a7510'} !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important; font-size: 0.88rem !important;
}}
[data-testid="stAlert"][kind="warning"] svg {{
    color: #c9a227 !important; fill: #c9a227 !important;
}}
/* INFO */
[data-testid="stAlert"][kind="info"],
div[data-testid="stAlert"].st-info {{
    background: {'rgba(61,155,233,0.10)' if dark else 'rgba(22,96,168,0.07)'} !important;
    border: 1px solid {'rgba(61,155,233,0.28)' if dark else 'rgba(22,96,168,0.22)'} !important;
    border-left: 4px solid #3d9be9 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 12px rgba(61,155,233,0.08) !important;
    animation: oram-banner-in 0.22s ease !important;
}}
[data-testid="stAlert"][kind="info"] p,
[data-testid="stAlert"][kind="info"] [data-testid="stMarkdownContainer"] p {{
    color: {'#7dd3fc' if dark else '#1660a8'} !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important; font-size: 0.88rem !important;
}}
[data-testid="stAlert"][kind="info"] svg {{
    color: #3d9be9 !important; fill: #3d9be9 !important;
}}
@keyframes oram-banner-in {{
    from {{ opacity: 0; transform: translateY(-6px); }}
    to   {{ opacity: 1; transform: translateY(0);    }}
}}

/* ══ FIX ESPACIO EN BLANCO: quitar margin despues de st.success/error ══ */
.element-container:empty {{
    display: none !important; height: 0 !important; margin: 0 !important;
}}
[data-testid="stAlert"] + .element-container {{
    margin-top: 0 !important; padding-top: 0 !important;
}}

/* :root [data-baseweb] — movido a JS (ver bloque <script> en inject_styles) */
</style>
""", unsafe_allow_html=True)

    # ── Dropdown portal: CSS + JS triple garantía ────────────────────────────────
    # CAUSA RAÍZ: config.toml con base="dark" forzaba --secondary-background-color
    # oscuro en los portals [data-baseweb="layer"] sin importar el tema activo.
    # SOLUCIÓN: config.toml → base="light" + CSS variables + JS deepPaint recursivo.
    _bg      = c["bg_card"]
    _text    = c["text"]
    _hover   = c["nav_hover"]
    _bdr2    = c["border2"]
    _scheme  = "dark" if dark else "light"
    _sid     = "oram-dd-d" if dark else "oram-dd-l"
    _opp_sid = "oram-dd-l" if dark else "oram-dd-d"

    # ── CSS: variables Streamlit + portal con especificidad máxima ────────────
    st.markdown(f"""
<style>
:root {{
    --secondary-background-color: {_bg} !important;
    --background-color: {c['bg']} !important;
    color-scheme: {_scheme} !important;
}}
html, body {{ color-scheme: {_scheme} !important; }}
html body [data-baseweb="layer"],
html body [data-baseweb="layer"] *,
html body [data-baseweb="layer"] > div,
html body [data-baseweb="layer"] > div > div,
html body [data-baseweb="layer"] [data-baseweb="popover"],
html body [data-baseweb="layer"] [data-baseweb="menu"],
html body [data-baseweb="layer"] ul,
html body [data-baseweb="layer"] li,
html body [data-baseweb="layer"] [role="option"],
html body [data-baseweb="layer"] [role="listbox"],
html body [data-baseweb="layer"] span {{
    background-color: {_bg} !important;
    color: {_text} !important;
    color-scheme: {_scheme} !important;
    -webkit-text-fill-color: {_text} !important;
}}
html body [data-baseweb="layer"] li:hover,
html body [data-baseweb="layer"] [role="option"]:hover,
html body [data-baseweb="layer"] [data-highlighted],
html body [data-baseweb="layer"] [aria-selected="true"] {{
    background-color: {_hover} !important;
    color: {_text} !important;
}}
html body [data-baseweb="layer"] > div > div:first-child {{
    border-radius: 10px !important;
    border: 1.5px solid {_bdr2} !important;
    overflow: hidden !important;
    box-shadow: 0 8px 32px rgba(0,0,0,{'0.40' if dark else '0.12'}) !important;
}}
html body [data-baseweb="layer"] [style*="background"] {{
    background-color: {_bg} !important;
    background: {_bg} !important;
}}
</style>
""", unsafe_allow_html=True)

    # ── JS: observer recursivo con setProperty 'important' ───────────────────
    # setProperty con 'important' es el único mecanismo que supera inline styles
    # que Base Web inyecta directamente en cada elemento del portal.
    st.markdown(f"""
<script>
(function() {{
    var BG   = '{_bg}';
    var TEXT = '{_text}';
    var HOV  = '{_hover}';
    var SID  = '{_sid}';
    var OPP  = '{_opp_sid}';
    var SCH  = '{_scheme}';

    // 1. Eliminar <style> del tema opuesto
    var opp = document.getElementById(OPP);
    if (opp) opp.parentNode.removeChild(opp);

    // 2. Inyectar <style> con variables CSS Streamlit corregidas
    var old = document.getElementById(SID);
    if (old) old.parentNode.removeChild(old);
    var s = document.createElement('style');
    s.id = SID;
    s.textContent = [
        ':root {{--secondary-background-color:' + BG + ' !important;--background-color:{c['bg']} !important;color-scheme:' + SCH + ' !important;}}',
        'html body [data-baseweb="layer"] * {{background-color:' + BG + ' !important;color:' + TEXT + ' !important;-webkit-text-fill-color:' + TEXT + ' !important;}}',
        'html body [data-baseweb="layer"] li:hover,html body [data-baseweb="layer"] [role="option"]:hover,html body [data-baseweb="layer"] [aria-selected="true"] {{background-color:' + HOV + ' !important;}}'
    ].join('');
    document.head.appendChild(s);

    // 3. deepPaint: setProperty 'important' en todos los descendientes
    var SKIP = {{'SCRIPT':1,'STYLE':1,'INPUT':1}};
    function deepPaint(root) {{
        if (!root || !root.style) return;
        try {{
            root.style.setProperty('background-color', BG, 'important');
            root.style.setProperty('color', TEXT, 'important');
            root.style.setProperty('-webkit-text-fill-color', TEXT, 'important');
            root.style.setProperty('color-scheme', SCH, 'important');
        }} catch(e) {{}}
        var ch = root.querySelectorAll ? root.querySelectorAll('*') : [];
        for (var i=0; i<ch.length; i++) {{
            if (SKIP[ch[i].tagName]) continue;
            try {{
                ch[i].style.setProperty('background-color', BG, 'important');
                ch[i].style.setProperty('color', TEXT, 'important');
                ch[i].style.setProperty('-webkit-text-fill-color', TEXT, 'important');
            }} catch(e) {{}}
        }}
    }}

    // 4. Manejar portals al montarse + observer interno para lazy render
    function handleLayer(node) {{
        if (!node || !node.getAttribute) return;
        if (node.getAttribute('data-baseweb') === 'layer') {{
            deepPaint(node);
            new MutationObserver(function(ms2) {{
                ms2.forEach(function(m2) {{
                    m2.addedNodes.forEach(function(n2) {{
                        if (n2.nodeType === 1) deepPaint(n2);
                    }});
                }});
            }}).observe(node, {{childList:true, subtree:true}});
        }}
    }}

    // 5. Observer principal sobre body (subtree:false = solo hijos directos, más eficiente)
    new MutationObserver(function(ms) {{
        ms.forEach(function(m) {{
            m.addedNodes.forEach(function(n) {{
                if (n.nodeType !== 1) return;
                handleLayer(n);
                if (n.querySelectorAll) n.querySelectorAll('[data-baseweb="layer"]').forEach(handleLayer);
            }});
        }});
    }}).observe(document.body, {{childList:true, subtree:false}});

    // 6. Portals ya existentes al cargar
    document.querySelectorAll('[data-baseweb="layer"]').forEach(deepPaint);
}})();
</script>
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


def oram_notify(kind: str, message: str, toast: bool = True, banner: bool = False) -> None:
    """
    Sistema de notificaciones premium ORAM.
    
    kind    : 'success' | 'error' | 'warning' | 'info'
    message : Texto del mensaje (soporta markdown)
    toast   : Muestra burbuja flotante (esquina inf-derecha) — default True
    banner  : Muestra banner inline además del toast — default False
    """
    icons = {'success': '✅', 'error': '❌', 'warning': '⚠️', 'info': '💡'}
    icon = icons.get(kind, '🔔')
    if toast:
        st.toast(message, icon=icon)
    if banner:
        fn = {'success': st.success, 'error': st.error,
              'warning': st.warning, 'info': st.info}.get(kind, st.info)
        fn(message)


def oram_bienvenida(
    titulo: str,
    subtitulo: str,
    spinner_label: str = "Aplicando cambios\u2026",
    delay: float = 2.2,
) -> None:
    """
    Overlay de confirmación premium — idéntico al que aparece al crear cuenta.

    Muestra una tarjeta centrada con:
      • Anillo animado con checkmark verde (pulse infinito)
      • Logo ORAM coloreado
      • Título y subtítulo personalizables
      • Spinner animado mientras espera

    Llama st.rerun() automáticamente tras delay segundos.

    Uso:
        oram_bienvenida(
            titulo    = "💾 Capital actualizado",
            subtitulo = "Tu capital inicial ha sido guardado correctamente.",
        )
        oram_bienvenida(
            titulo        = "✅ Trade guardado",
            subtitulo     = "EURUSD LONG registrado en tu diario.",
            spinner_label = "Actualizando historial…",
            delay         = 2.0,
        )
    """
    t    = get_theme()
    dark = t == "dark"

    overlay_bg  = "rgba(6,9,15,0.92)"   if dark else "rgba(238,242,247,0.94)"
    card_bg     = "#0c1219"             if dark else "#ffffff"
    card_border = "#1b2a40"             if dark else "#dde5ef"
    text_main   = "#edf4ff"             if dark else "#0b1824"
    text_muted  = "#637a94"             if dark else "#7a8fa0"

    st.markdown(f"""
<style>
@keyframes oram-fadein {{
    from {{ opacity: 0; transform: translateY(14px) scale(0.97); }}
    to   {{ opacity: 1; transform: translateY(0)   scale(1);    }}
}}
@keyframes oram-pulse {{
    0%,100% {{ box-shadow: 0 0 0 0    rgba(34,197,94,0.40); }}
    50%      {{ box-shadow: 0 0 0 18px rgba(34,197,94,0);   }}
}}
@keyframes oram-spin {{
    to {{ transform: rotate(360deg); }}
}}
#oram-welcome-overlay {{
    position: fixed; inset: 0;
    background: {overlay_bg};
    backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
    z-index: 99999;
    display: flex; align-items: center; justify-content: center;
}}
#oram-welcome-card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 20px;
    padding: 2.8rem 3rem 2.4rem;
    text-align: center; max-width: 400px; width: 90%;
    animation: oram-fadein 0.45s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow: 0 24px 60px rgba(0,0,0,0.35);
}}
.oram-check-ring {{
    width: 64px; height: 64px; border-radius: 50%;
    background: rgba(34,197,94,0.12); border: 2px solid #22c55e;
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
    border-top-color: #22c55e; border-radius: 50%;
    animation: oram-spin 0.75s linear infinite; flex-shrink: 0;
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
    <div class="oram-welcome-title">{titulo}</div>
    <div class="oram-welcome-sub">{subtitulo}</div>
    <div class="oram-spinner-row">
      <div class="oram-spinner"></div>
      <span class="oram-spinner-label">{spinner_label}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    time.sleep(delay)
    st.rerun()
