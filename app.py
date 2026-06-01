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
        ], label_visibility="collapsed")

        st.divider()

        _dark = get_theme() == "dark"

        # Colores del botón tema — idénticos al login
        _tbtn_bg  = "rgba(12,18,25,0.88)"    if _dark else "rgba(255,255,255,0.94)"
        _tbtn_txt = "#c8d8ea"                 if _dark else "#2a3f54"
        _tbtn_bdr = "rgba(200,216,234,0.18)"  if _dark else "rgba(0,0,0,0.12)"
        # Colores del botón salir — píldora roja
        _logout_bg  = "rgba(239,68,68,0.10)"  if _dark else "rgba(239,68,68,0.07)"
        _logout_txt = "#f87171"               if _dark else "#dc2626"
        _logout_bdr = "rgba(239,68,68,0.30)"  if _dark else "rgba(220,38,38,0.25)"

        st.markdown(f'''
<style>
/* ═══════════════════════════════════════════════════════════════════
   SIDEBAR PILL BUTTONS
   Estrategia: JavaScript inyecta las clases .oram-btn-theme y
   .oram-btn-logout a los botones correctos buscándolos por texto.
   El CSS apunta a esas clases desde dentro del sidebar.
   Esta es la única estrategia 100% robusta ante cualquier versión
   de Streamlit, ya que no depende de data-testid internos.
   ═══════════════════════════════════════════════════════════════════ */

/* ── TEMA — glass pill ── */
section[data-testid="stSidebar"] .oram-btn-theme {{
    background: {_tbtn_bg} !important;
    color: {_tbtn_txt} !important;
    -webkit-text-fill-color: {_tbtn_txt} !important;
    border: 1px solid {_tbtn_bdr} !important;
    border-radius: 999px !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.07) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 1.1rem !important;
    width: 100% !important;
    min-height: 38px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all .18s ease !important;
    white-space: nowrap !important;
    letter-spacing: 0.2px !important;
}}
section[data-testid="stSidebar"] .oram-btn-theme:hover {{
    box-shadow: 0 6px 22px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.12) !important;
    transform: translateY(-1px) !important;
    opacity: 0.92 !important;
}}
section[data-testid="stSidebar"] .oram-btn-theme:active {{
    transform: scale(0.97) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18) !important;
    opacity: 1 !important;
}}
section[data-testid="stSidebar"] .oram-btn-theme *,
section[data-testid="stSidebar"] .oram-btn-theme p {{
    color: {_tbtn_txt} !important;
    -webkit-text-fill-color: {_tbtn_txt} !important;
}}

/* ── SALIR — red pill ── */
section[data-testid="stSidebar"] .oram-btn-logout {{
    background: {_logout_bg} !important;
    color: {_logout_txt} !important;
    -webkit-text-fill-color: {_logout_txt} !important;
    border: 1px solid {_logout_bdr} !important;
    border-radius: 999px !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    box-shadow: 0 2px 10px rgba(239,68,68,0.12), inset 0 1px 0 rgba(255,255,255,0.04) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 1.1rem !important;
    width: 100% !important;
    min-height: 38px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all .18s ease !important;
    white-space: nowrap !important;
    letter-spacing: 0.2px !important;
}}
section[data-testid="stSidebar"] .oram-btn-logout:hover {{
    background: rgba(239,68,68,0.22) !important;
    border-color: rgba(239,68,68,0.50) !important;
    box-shadow: 0 6px 22px rgba(239,68,68,0.32) !important;
    transform: translateY(-1px) !important;
}}
section[data-testid="stSidebar"] .oram-btn-logout:active {{
    transform: scale(0.97) !important;
    box-shadow: 0 2px 8px rgba(239,68,68,0.20) !important;
}}
section[data-testid="stSidebar"] .oram-btn-logout *,
section[data-testid="stSidebar"] .oram-btn-logout p {{
    color: {_logout_txt} !important;
    -webkit-text-fill-color: {_logout_txt} !important;
}}
</style>

<script>
(function applyOramSidebarButtons() {{
    // Textos posibles según tema activo
    const themeTexts = ['☀️ Claro', '🌙 Oscuro', 'Claro', 'Oscuro'];
    const logoutTexts = ['🚪 Salir', 'Salir'];

    function tagButtons() {{
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return;

        // Todos los botones dentro del sidebar
        const btns = sidebar.querySelectorAll('button');
        btns.forEach(btn => {{
            const txt = btn.innerText || btn.textContent || '';
            const trimmed = txt.trim();

            if (themeTexts.some(t => trimmed.includes(t.replace(/[☀️🌙]/g,'').trim()) || trimmed === t)) {{
                btn.classList.add('oram-btn-theme');
                btn.classList.remove('oram-btn-logout');
            }}
            if (logoutTexts.some(t => trimmed.includes(t.replace('🚪','').trim()) || trimmed === t)) {{
                btn.classList.add('oram-btn-logout');
                btn.classList.remove('oram-btn-theme');
            }}
        }});
    }}

    // Ejecutar inmediatamente y observar mutaciones del DOM
    // (Streamlit re-renderiza el sidebar en cada interacción)
    tagButtons();
    const observer = new MutationObserver(() => tagButtons());
    observer.observe(document.body, {{ childList: true, subtree: true }});
}})();
</script>
''', unsafe_allow_html=True)

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
    }
    page_map[nav]()
