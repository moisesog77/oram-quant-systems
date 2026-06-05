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

if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

# ── Sesión con timeout de 60 minutos ─────────────────────────────────────────
SESSION_TIMEOUT = 60 * 60   # 60 min exactos en segundos

def _check_session():
    """Renueva el timestamp de actividad en cada interacción."""
    st.session_state["last_activity"] = datetime.now(timezone.utc).timestamp()

def _is_session_valid() -> bool:
    now  = datetime.now(timezone.utc).timestamp()
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
from modules.admin         import render_admin
from database.db           import inicializar_db

inicializar_db()

if "user" not in st.session_state:
    st.session_state.user = None

# Verificar timeout — cerrar sesión si pasaron 60 min sin actividad
if st.session_state.user is not None:
    if not _is_session_valid():
        st.session_state.user = None
        st.session_state.pop("last_activity", None)
        st.rerun()
    else:
        _check_session()  # renovar timestamp

if st.session_state.user is None:
    render_auth()
else:
    c    = get_colors()
    dark = get_theme() == "dark"
    user = st.session_state.user
    is_admin = bool(user.get("is_admin", 0))

    with st.sidebar:
        # Logo
        st.markdown(
            f'<div class="oram-logo-wrap">'
            f'<div class="oram-logo">'
            f'<span class="lo">O</span><span class="lr">R</span>'
            f'<span class="la">A</span><span class="lm">M</span>'
            f'</div>'
            f'<div class="oram-tagline">{APP_TAGLINE}</div>'
            f'<div class="oram-user">'
            f'{"🛡️ " if is_admin else ""}{user["username"]}'
            f'{"  <span style=\'font-size:0.6rem;color:#c9a227\'>ADMIN</span>" if is_admin else ""}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Navegación — el admin ve el panel de administración
        nav_options = [
            "📈 Dashboard",
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
        ]

        if is_admin:
            nav_options.append("🔐 Admin Panel")

        nav = st.radio("Navegación", nav_options, label_visibility="collapsed")

        st.divider()

        _dark = get_theme() == "dark"

        col_t, col_s = st.columns(2)
        with col_t:
            label = "☀️ Claro" if _dark else "🌙 Oscuro"
            if st.button(label, key="sb_theme"):
                toggle_theme()
                st.rerun()
        with col_s:
            if st.button("🚪 Salir", key="sb_logout"):
                st.session_state.user = None
                st.session_state.pop("last_activity", None)
                st.rerun()

        # Tiempo de sesión restante
        now  = datetime.now(timezone.utc).timestamp()
        last = st.session_state.get("last_activity", now)
        mins_restantes = max(0, int((SESSION_TIMEOUT - (now - last)) / 60))
        st.markdown(
            f'<div style="margin-top:.8rem;padding-top:.7rem;'
            f'border-top:1px solid {c["border"]};text-align:center">'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.6rem;'
            f'color:{c["text_muted"]}">ORAM Quant Systems<br>'
            f'<span style="color:{c["accent3"]}">'
            f'<span class="status-live"></span> LIVE</span><br>'
            f'<span style="color:{c["text_muted"]}">Sesión: {mins_restantes} min</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    page_map = {
        "📈 Dashboard":            render_dashboard,
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
        "🔐 Admin Panel":          render_admin,
    }
    page_map[nav]()
