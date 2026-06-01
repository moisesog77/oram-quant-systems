"""
ORAM Quant Systems — Institutional-Grade Trading Intelligence
"""
import streamlit as st
from datetime import datetime, timezone

st.set_page_config(
    page_title="ORAM Quant Systems",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Tema independiente del sistema ────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"   # siempre oscuro por defecto

# ── Sesión con timeout de 40 minutos ─────────────────────────────────────────
SESSION_TIMEOUT = 40 * 60   # 40 min en segundos

def _check_session():
    """Verifica si la sesión sigue activa. Cierra si pasaron 40 min sin actividad."""
    now = datetime.now(timezone.utc).timestamp()
    if "last_activity" not in st.session_state:
        st.session_state["last_activity"] = now
    # Renovar actividad en cada interacción
    st.session_state["last_activity"] = now

def _is_session_valid():
    now = datetime.now(timezone.utc).timestamp()
    last = st.session_state.get("last_activity", now)
    return (now - last) < SESSION_TIMEOUT

from ui.styles import inject_styles, toggle_theme, get_theme, get_colors, APP_TAGLINE
inject_styles()

from modules.auth          import render_auth
from modules.dashboard     import render_dashboard
from modules.live_analysis import render_live_analysis
from modules.journal       import render_journal
from modules.performance   import render_performance
from modules.education     import render_education
from modules.calendar      import render_calendar
from modules.backtesting   import render_backtesting
from modules.multi_tf      import render_multi_tf
from modules.risk_manager  import render_risk_manager
from modules.bot_config    import render_bot_config
from modules.watchlist     import render_watchlist
from modules.signals_panel import render_signals_panel
from database.db           import inicializar_db

inicializar_db()

if "user" not in st.session_state:
    st.session_state.user = None

# Verificar timeout
if st.session_state.user is not None:
    if not _is_session_valid():
        st.session_state.user = None
        st.session_state.pop("last_activity", None)
        st.rerun()
    else:
        _check_session()

if st.session_state.user is None:
    render_auth()
else:
    c    = get_colors()
    dark = get_theme() == "dark"
    user = st.session_state.user

    with st.sidebar:
        st.markdown(
            f'<div class="oram-logo-wrap">'
            f'<div class="oram-logo">'
            f'<span class="lo">O</span><span class="lr">R</span>'
            f'<span class="la">A</span><span class="lm">M</span>'
            f'</div>'
            f'<div class="oram-tagline">{APP_TAGLINE}</div>'
            f'<div class="oram-user">{user["username"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        nav = st.radio("Navegación", [
            "⬛ Dashboard",
            "📡 Análisis en Vivo",
            "🔭 Multi-Timeframe",
            "📋 Diario de Trades",
            "📊 Performance & IA",
            "🧪 Backtesting",
            "🛡️ Risk Manager",
            "👁️ Watchlist",
            "⚡ Panel de Señales",
            "📰 Calendario Económico",
            "🤖 Bot Telegram",
            "📚 Guía SMC",
        ], label_visibility="collapsed")

        st.divider()

        # Colores píldora según tema — mismo estilo que el login
        _dark = get_theme() == "dark"
        _tbtn_bg  = "rgba(12,18,25,0.88)"    if _dark else "rgba(255,255,255,0.94)"
        _tbtn_txt = "#c8d8ea"                 if _dark else "#2a3f54"
        _tbtn_bdr = "rgba(255,255,255,0.12)"  if _dark else "rgba(0,0,0,0.09)"
        _logout_bg  = "rgba(239,68,68,0.12)"  if _dark else "rgba(239,68,68,0.08)"
        _logout_txt = "#ef4444"
        _logout_bdr = "rgba(239,68,68,0.25)"  if _dark else "rgba(239,68,68,0.20)"

        st.markdown(f'''
<style>
/* ── Botones del sidebar — misma píldora que el login ── */
section[data-testid="stSidebar"] .stButton > button {{
    border-radius: 999px !important;
    font-family: "Inter", sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 0.9rem !important;
    width: 100% !important;
    transition: all .18s ease !important;
    border: 1px solid !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.15) !important;
    white-space: nowrap !important;
}}
/* Botón tema */
section[data-testid="stSidebar"] .stButton:first-of-type > button {{
    background: {_tbtn_bg} !important;
    color: {_tbtn_txt} !important;
    -webkit-text-fill-color: {_tbtn_txt} !important;
    border-color: {_tbtn_bdr} !important;
}}
section[data-testid="stSidebar"] .stButton:first-of-type > button:hover {{
    box-shadow: 0 4px 16px rgba(0,0,0,0.22) !important;
    opacity: 0.9 !important;
}}
/* Botón cerrar sesión — píldora roja */
section[data-testid="stSidebar"] .stButton:last-of-type > button {{
    background: {_logout_bg} !important;
    color: {_logout_txt} !important;
    -webkit-text-fill-color: {_logout_txt} !important;
    border-color: {_logout_bdr} !important;
}}
section[data-testid="stSidebar"] .stButton:last-of-type > button:hover {{
    background: rgba(239,68,68,0.20) !important;
    box-shadow: 0 4px 16px rgba(239,68,68,0.25) !important;
}}
</style>
''', unsafe_allow_html=True)

        col_t, col_s = st.columns(2)
        with col_t:
            label = "☀️ Claro" if get_theme() == "dark" else "🌙 Oscuro"
            if st.button(label, key="sb_theme", help="Cambiar tema"):
                toggle_theme()
                st.rerun()
        with col_s:
            if st.button("🚪 Salir", key="sb_logout", help="Cerrar sesión"):
                st.session_state.user = None
                st.session_state.pop("last_activity", None)
                st.rerun()

        st.markdown(
            f'<div style="margin-top:.8rem;padding-top:.7rem;'
            f'border-top:1px solid {c["border"]};text-align:center">'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.6rem;'
            f'color:{c["text_muted"]}">ORAM Quant Systems<br>'
            f'<span style="color:{c["accent3"]}">'
            f'<span class="status-live"></span> LIVE</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    page_map = {
        "⬛ Dashboard":            render_dashboard,
        "📡 Análisis en Vivo":     render_live_analysis,
        "🔭 Multi-Timeframe":      render_multi_tf,
        "📋 Diario de Trades":     render_journal,
        "📊 Performance & IA":     render_performance,
        "🧪 Backtesting":          render_backtesting,
        "🛡️ Risk Manager":         render_risk_manager,
        "👁️ Watchlist":            render_watchlist,
        "⚡ Panel de Señales":     render_signals_panel,
        "📰 Calendario Económico": render_calendar,
        "🤖 Bot Telegram":         render_bot_config,
        "📚 Guía SMC":             render_education,
    }
    page_map[nav]()
