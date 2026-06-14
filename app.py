"""
app.py — ORAM Quant Systems — Punto de entrada principal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Responsabilidades:
  · Configurar Streamlit (page_config, tema inicial)
  · Gestión de sesión con timeout estricto de 60 minutos
    desde el momento de login (no se renueva con recargas)
  · Enrutar al módulo correcto según navegación del sidebar
  · Mostrar sidebar con logo, navegación, tema y countdown

Patrón de sesión:
  - Al hacer login → se registra session_start = timestamp_UTC
  - En cada render  → se verifica (now - session_start) < 3600s
  - Si expira       → se limpia user y se redirige al login
  - Recargar página NO reinicia el contador (sesión por login, no por actividad)
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone

# ── Configuración de página — debe ser la primera llamada Streamlit ─────────
st.set_page_config(
    page_title="ORAM Quant Systems",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Tema por defecto: oscuro ──────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

# ── Constante de timeout de sesión ───────────────────────────────────────────
SESSION_TIMEOUT_SECS = 60 * 60   # 3600 segundos = 60 minutos exactos


def _session_expiro() -> bool:
    """
    Verifica si la sesión ha expirado comparando el tiempo
    transcurrido desde session_start (timestamp de login) con
    SESSION_TIMEOUT_SECS.

    IMPORTANTE: usa session_start (fijo al login), NO el patrón last-activity.
    Esto garantiza que recargar la página NO reinicia el contador.
    La sesión dura exactamente 60 min desde que el usuario inició sesión.

    Returns:
        True  → sesión expirada, cerrar sesión
        False → sesión vigente
    """
    start = st.session_state.get("session_start")
    if start is None:
        return False   # no hay sesión activa
    elapsed = datetime.now(timezone.utc).timestamp() - start
    return elapsed >= SESSION_TIMEOUT_SECS


def _minutos_restantes() -> int:
    """
    Calcula los minutos restantes de sesión para mostrar en el sidebar.
    Retorna 0 si ya expiró.
    """
    start = st.session_state.get("session_start", datetime.now(timezone.utc).timestamp())
    elapsed = datetime.now(timezone.utc).timestamp() - start
    return max(0, int((SESSION_TIMEOUT_SECS - elapsed) / 60))


# ── Imports de módulos internos ───────────────────────────────────────────────
from ui.styles import inject_styles, toggle_theme, get_theme, get_colors, APP_TAGLINE

# Inyectar CSS premium global (tema, inputs, botones, scrollbar, etc.)
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

# ── Inicializar base de datos (crea tablas + superadmin si no existen) ────────
inicializar_db()

# ── Estado inicial de sesión ─────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None

# ── Verificar expiración de sesión ────────────────────────────────────────────
# Se ejecuta en CADA render. Si la sesión expiró → forzar logout.
if st.session_state.user is not None and _session_expiro():
    st.session_state.user = None
    st.session_state.pop("session_start", None)
    st.rerun()

# ── Enrutamiento principal ────────────────────────────────────────────────────
if st.session_state.user is None:
    # Usuario no autenticado → pantalla de login/registro
    render_auth()

else:
    # Usuario autenticado → mostrar aplicación completa
    c        = get_colors()
    user     = st.session_state.user
    is_admin = bool(user.get("is_admin", 0))

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        # ── Logo ORAM ─────────────────────────────────────────────────────────
        # Variables calculadas fuera del f-string para evitar backslash dentro de {}
        admin_prefix = "🛡️ " if is_admin else ""
        admin_badge  = '&nbsp;<span style="font-size:0.6rem;color:#c9a227;font-weight:700">ADMIN</span>' if is_admin else ""

        st.markdown(
            f'<div class="oram-logo-wrap">'
            f'<div class="oram-logo">'
            f'<span class="lo">O</span><span class="lr">R</span>'
            f'<span class="la">A</span><span class="lm">M</span>'
            f'</div>'
            f'<div class="oram-tagline">{APP_TAGLINE}</div>'
            f'<div class="oram-user">'
            f'{admin_prefix}{user["username"]}{admin_badge}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Navegación ────────────────────────────────────────────────────────
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

        nav = st.radio("", nav_options, label_visibility="hidden")

        # ── Auto-colapsar sidebar al seleccionar módulo (efecto premium) ─────
        # JS via components.html - el unico metodo que ejecuta JS en Streamlit Cloud
        components.html("""
<script>
(function () {
    var P = window.parent, doc = P.document, ss = P.sessionStorage;
    var FLAG = "oram_sb_close";
    function doCollapse() {
        var sels = [
            '[data-testid="stSidebarCollapseButton"] button',
            '[data-testid="stSidebarCollapseButton"]',
            '[data-testid="stBaseButton-headerNoPadding"]',
            'button[aria-label="Close sidebar"]',
            'button[aria-label="Collapse sidebar"]',
            'section[data-testid="stSidebar"] button',
        ];
        for (var i = 0; i < sels.length; i++) {
            var el = doc.querySelector(sels[i]);
            if (el && el.offsetParent !== null) { el.click(); return true; }
        }
        return false;
    }
    var ts = ss.getItem(FLAG);
    if (ts && (Date.now() - parseInt(ts, 10)) < 4000) {
        ss.removeItem(FLAG);
        var tries = 0;
        var iv = setInterval(function () {
            if (doCollapse() || ++tries > 40) clearInterval(iv);
        }, 80);
    }
    function bindLabels() {
        var sb = doc.querySelector('[data-testid="stSidebar"]');
        if (!sb) return false;
        var labels = sb.querySelectorAll('div[role="radiogroup"] label');
        if (!labels.length) return false;
        labels.forEach(function (lb) {
            if (lb._oramBound) return;
            lb._oramBound = true;
            lb.addEventListener("mousedown", function () {
                ss.setItem(FLAG, String(Date.now()));
            });
        });
        return true;
    }
    var t = 0;
    var iv2 = setInterval(function () {
        if (bindLabels() || ++t > 80) clearInterval(iv2);
    }, 100);
})();
</script>
""", height=0, scrolling=False)

        st.divider()

        # ── Botones Tema / Salir ──────────────────────────────────────────────
        col_t, col_s = st.columns(2)
        with col_t:
            label_tema = "☀️ Claro" if get_theme() == "dark" else "🌙 Oscuro"
            if st.button(label_tema, key="sb_theme"):
                toggle_theme()
                st.rerun()
        with col_s:
            if st.button("🚪 Salir", key="sb_logout"):
                # Limpiar sesión completamente
                st.session_state.user = None
                st.session_state.pop("session_start", None)
                st.rerun()

        # ── Footer con countdown de sesión ────────────────────────────────────
        mins = _minutos_restantes()
        # Color del countdown: verde > 30 min, amarillo 10-30, rojo < 10
        if mins > 30:
            countdown_color = c["accent3"]   # teal/verde
        elif mins > 10:
            countdown_color = c["accent"]    # dorado/amarillo
        else:
            countdown_color = c["red"]       # rojo — urgente

        st.markdown(
            f'<div style="margin-top:.8rem;padding-top:.7rem;'
            f'border-top:1px solid {c["border"]};text-align:center">'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.6rem;'
            f'color:{c["text_muted"]}">ORAM Quant Systems<br>'
            f'<span style="color:{c["accent3"]}">'
            f'<span class="status-live"></span> LIVE</span><br>'
            f'<span style="color:{countdown_color}">Sesión: {mins} min restantes</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Mapa de páginas → funciones de render ────────────────────────────────
    _PAGE_MAP = {
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
    _PAGE_MAP[nav]()
