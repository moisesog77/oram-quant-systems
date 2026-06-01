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
    "input_bg":    "#0c1219",
    "sb_bg":       "linear-gradient(180deg,#080d14 0%,#060a10 100%)",
    "nav_hover":   "#121e2e",
    "shadow":      "0 4px 24px rgba(0,0,0,0.4)",
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
    "input_bg":    "#ffffff",
    "sb_bg":       "#ffffff",
    "nav_hover":   "#edf3fa",
    "shadow":      "0 4px 16px rgba(0,0,0,0.08)",
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
html,body,[class*="css"]{{
    font-family:'Inter',sans-serif!important;
    background-color:{c['bg']}!important;
    color:{c['text']}!important;
    -webkit-font-smoothing:antialiased;
}}
.main,.block-container{{
    background-color:{c['bg']}!important;
    padding-top:1.2rem!important;
    color:{c['text']}!important;
}}
.stApp,[data-testid="stAppViewContainer"]{{background-color:{c['bg']}!important}}
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
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] svg path,
[data-testid="stSidebarCollapsedControl"] svg polyline,
[data-testid="stSidebarCollapsedControl"] svg line {{
    fill: {c['text']} !important;
    stroke: {c['text']} !important;
    color: {c['text']} !important;
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
/* Sidebar buttons — base, los estilos específicos van en app.py */
section[data-testid="stSidebar"] .stButton>button{{
    border-radius:999px!important;
    font-family:'Inter',sans-serif!important;
    font-size:0.82rem!important;font-weight:500!important;
    transition:all .18s ease!important;
    white-space:nowrap!important;
}}

/* ── LOGO CSS ───────────────────────────────────────── */
.oram-logo-wrap{{
    padding:1.4rem 0 1.1rem 0;
    border-bottom:1px solid {c['border']};
    margin-bottom:0.9rem;
}}
.oram-logo{{
    font-family:'Space Grotesk',sans-serif;
    font-size:1.9rem;font-weight:800;
    letter-spacing:-1px;line-height:1;
}}
.oram-logo .lo{{color:{LOGO_GOLD}}}
.oram-logo .lr{{color:{LOGO_BLUE}}}
.oram-logo .la{{color:{LOGO_TEAL}}}
.oram-logo .lm{{color:{c['text_strong']}}}
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
    border:1.5px solid {c['border']}!important;
    border-radius:10px!important;overflow:hidden!important;
    gap:3px!important;padding:2px 4px!important;
    transition:border-color .15s;box-shadow:none!important;
}}
[data-testid="stNumberInput"]>div:focus-within{{
    border-color:{c['green']}!important;
    box-shadow:0 0 0 3px rgba(34,197,94,0.15)!important;
}}
[data-testid="stNumberInput"] input{{
    background:transparent!important;border:none!important;
    box-shadow:none!important;outline:none!important;
    color:{c['text']}!important;
    font-family:'JetBrains Mono',monospace!important;
    padding:.35rem .5rem!important;flex:1!important;
}}
/* +/- buttons verde/rojo */
[data-testid="stNumberInput"] button{{
    border:none!important;border-radius:6px!important;
    width:26px!important;min-width:26px!important;height:26px!important;
    display:flex!important;align-items:center!important;
    justify-content:center!important;cursor:pointer!important;
    transition:all .15s ease!important;flex-shrink:0!important;
    box-shadow:0 1px 3px rgba(0,0,0,0.25)!important;
    padding:0!important;
}}
[data-testid="stNumberInput"] button:first-child{{
    background:linear-gradient(135deg,{c['red']},#b91c1c)!important;
}}
[data-testid="stNumberInput"] button:first-child:hover{{
    background:linear-gradient(135deg,#b91c1c,#991b1b)!important;
    box-shadow:0 2px 8px rgba(239,68,68,.45)!important;
    transform:scale(1.08)!important;
}}
[data-testid="stNumberInput"] button:last-child{{
    background:linear-gradient(135deg,{c['green']},#16a34a)!important;
}}
[data-testid="stNumberInput"] button:last-child:hover{{
    background:linear-gradient(135deg,#16a34a,#15803d)!important;
    box-shadow:0 2px 8px rgba(34,197,94,.45)!important;
    transform:scale(1.08)!important;
}}
[data-testid="stNumberInput"] button svg{{
    fill:#ffffff!important;stroke:#ffffff!important;
    width:13px!important;height:13px!important;
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
/* Selectbox */
.stSelectbox>div>div{{
    background:{c['input_bg']}!important;
    border:1px solid {c['border']}!important;
    border-radius:8px!important;color:{c['text']}!important;
    transition:border-color .15s;
}}
.stSelectbox>div>div>div{{color:{c['text']}!important}}
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="listbox"] li,
[data-baseweb="popover"] [role="listbox"] ul {{
    background:{c['bg_card']}!important;
    border:1px solid {c['border']}!important;border-radius:8px!important;
    color:{c['text']}!important;
    color-scheme: {'dark' if dark else 'light'} !important;
}}
[data-baseweb="popover"] li{{color:{c['text']}!important;background:{c['bg_card']}!important}}
[data-baseweb="popover"] li:hover{{background:{c['nav_hover']}!important}}
/* Multiselect */
[data-testid="stMultiSelect"]>div{{
    background:{c['input_bg']}!important;
    border:1px solid {c['border']}!important;border-radius:8px!important;
}}
[data-testid="stMultiSelect"] [data-baseweb="tag"]{{
    background:{c['bg_card2']}!important;
    border:1px solid {c['border2']}!important;
    color:{c['text']}!important;border-radius:5px!important;
}}
[data-testid="stMultiSelect"] input{{color:{c['text']}!important;background:transparent!important}}
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
.stButton>button:hover{{
    border-color:{c['accent']}!important;
    color:{c['accent']}!important;
    -webkit-text-fill-color:{c['accent']}!important;
    background:{c['glow']}!important;
}}
.stButton>button:active{{transform:scale(.98)!important}}
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
/* Number input */
[data-testid="stNumberInput"] * {{ background-color: transparent !important; }}
[data-testid="stNumberInput"] > div {{ background-color: {c['input_bg']} !important; }}
/* Select / Multiselect — DROPDOWN FONDO CLARO */
[data-baseweb="select"] > div {{
    background-color: {c['input_bg']} !important;
    border-color: {c['border']} !important;
    color: {c['text']} !important;
}}
[data-baseweb="select"] span {{ color: {c['text']} !important; }}
[data-baseweb="select"] input {{
    background: transparent !important;
    color: {c['text']} !important;
    -webkit-text-fill-color: {c['text']} !important;
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
/* Radio circle dot — override dark color */
[data-testid="stRadio"] div[role="radio"] {{
    border-color: {c['border']} !important;
    background: transparent !important;
}}
[data-testid="stRadio"] div[role="radio"][aria-checked="true"] {{
    border-color: {c['accent']} !important;
    background: {c['accent']} !important;
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
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
    flex-wrap: wrap !important;
    min-height: 40px !important;
    height: auto !important;
    padding: 4px 8px !important;
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
