"""
app.py — ORAM Quant Systems — Punto de entrada principal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sesión persistente de 60 minutos mediante cookie segura.

Flujo de sesión:
  1. Login exitoso → guarda user_id + session_start en cookie (TTL=1h)
  2. Cada render    → lee cookie, verifica TTL, carga usuario de DB
  3. Recarga / misma pestaña → cookie persiste, sesión continúa
  4. Expiración → cookie eliminada, redirige a login
  5. Salir → cookie eliminada explícitamente

La cookie se llama 'oram_session' y contiene:
  user_id       : int  — ID del usuario
  session_start : float — timestamp UTC de login
"""

import streamlit as st
from datetime import datetime, timezone
import json

st.set_page_config(
    page_title="ORAM Quant Systems",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Tema por defecto ──────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

SESSION_TIMEOUT_SECS = 60 * 60   # 60 minutos exactos
COOKIE_NAME          = "oram_session"

# ── Cookie Manager ────────────────────────────────────────────────────────────
try:
    import extra_streamlit_components as stx
    _cookie_manager = stx.CookieManager(key="oram_cookie_mgr")
    COOKIES_OK = True
except Exception:
    _cookie_manager = None
    COOKIES_OK = False


def _leer_cookie() -> dict | None:
    """
    Lee la cookie de sesión y retorna su contenido como dict.
    Retorna None si no existe o está malformada.
    """
    if not COOKIES_OK or _cookie_manager is None:
        return None
    try:
        raw = _cookie_manager.get(COOKIE_NAME)
        if not raw:
            return None
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return None


def _escribir_cookie(user_id: int, session_start: float) -> None:
    """
    Escribe la cookie de sesión con el user_id y timestamp de login.
    TTL = SESSION_TIMEOUT_SECS para que el browser la expire automáticamente.
    """
    if not COOKIES_OK or _cookie_manager is None:
        return
    try:
        payload = json.dumps({"user_id": user_id, "session_start": session_start})
        _cookie_manager.set(
            COOKIE_NAME,
            payload,
            max_age=SESSION_TIMEOUT_SECS,
            key="oram_set_cookie",
        )
    except Exception:
        pass


def _eliminar_cookie() -> None:
    """Elimina la cookie de sesión (logout o expiración)."""
    if not COOKIES_OK or _cookie_manager is None:
        return
    try:
        _cookie_manager.delete(COOKIE_NAME, key="oram_del_cookie")
    except Exception:
        pass


def _session_expiro(session_start: float) -> bool:
    """Verifica si han pasado más de 60 minutos desde el login."""
    elapsed = datetime.now(timezone.utc).timestamp() - session_start
    return elapsed >= SESSION_TIMEOUT_SECS


def _minutos_restantes(session_start: float) -> int:
    """Minutos restantes de sesión para mostrar en sidebar."""
    elapsed = datetime.now(timezone.utc).timestamp() - session_start
    return max(0, int((SESSION_TIMEOUT_SECS - elapsed) / 60))


# ── Imports ───────────────────────────────────────────────────────────────────
from ui.styles     import inject_styles, toggle_theme, get_theme, get_colors, APP_TAGLINE
from database.db   import inicializar_db, obtener_todos_usuarios

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

inicializar_db()

# ── Restaurar sesión desde cookie si session_state está vacío ────────────────
# Este bloque se ejecuta en CADA render (incluyendo recargas de página).
# Si el usuario recargó, session_state.user es None pero la cookie sigue viva.
# La recuperamos aquí para que la recarga NO cierre la sesión.

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None and COOKIES_OK:
    # Si el usuario acaba de hacer logout, NO restaurar desde cookie
    # (la cookie puede tardar un render en eliminarse)
    if st.session_state.get("logged_out"):
        st.session_state.pop("logged_out", None)
        _eliminar_cookie()  # intentar eliminar de nuevo
    else:
        cookie_data = _leer_cookie()
        if cookie_data:
            session_start = cookie_data.get("session_start", 0)
            user_id       = cookie_data.get("user_id")
            if user_id and not _session_expiro(session_start):
                # Cookie válida — restaurar usuario desde DB
                try:
                    usuarios = obtener_todos_usuarios()
                    user_db  = next((u for u in usuarios if u["id"] == int(user_id)), None)
                    if user_db:
                        st.session_state.user          = user_db
                        st.session_state["session_start"] = session_start
                except Exception:
                    _eliminar_cookie()
            else:
                # Cookie expirada — eliminar
                _eliminar_cookie()

# ── Verificar expiración en cada render ──────────────────────────────────────
if st.session_state.user is not None:
    start   = st.session_state.get("session_start", datetime.now(timezone.utc).timestamp())
    if _session_expiro(start):
        st.session_state.user = None
        st.session_state.pop("session_start", None)
        _eliminar_cookie()
        st.rerun()

# ── Enrutamiento ──────────────────────────────────────────────────────────────
if st.session_state.user is None:
    render_auth()

else:
    c        = get_colors()
    user     = st.session_state.user
    is_admin = bool(user.get("is_admin", 0))
    start    = st.session_state.get("session_start", datetime.now(timezone.utc).timestamp())

    with st.sidebar:
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

        # ── Título "MENÚ" diferenciado — no es un botón, es una cabecera ──────
        st.markdown(
            f'''<div style="
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.62rem;
                font-weight: 700;
                letter-spacing: 2.5px;
                text-transform: uppercase;
                color: {c['text_muted']};
                padding: 0.5rem 0.2rem 0.4rem 0.2rem;
                margin-bottom: 2px;
                border-bottom: 1px solid {c['border']};
                display: flex;
                align-items: center;
                gap: 6px;
            ">
                <span style="color:{c['accent3']};font-size:0.55rem">●</span>
                MÓDULOS
            </div>''',
            unsafe_allow_html=True
        )

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

        st.markdown("""
<script>
(function () {
    /* ── ORAM sidebar auto-close ─────────────────────────────────────────
       Mecanismo: sessionStorage como puente entre renders de Streamlit.
       
       RENDER N  (usuario hace click en label):
         · listener detecta el click → guarda timestamp en sessionStorage
       
       RENDER N+1 (Streamlit recarga por cambio de radio):
         · JS nuevo revisa sessionStorage
         · Si el timestamp es reciente (< 1.5s) → click en botón colapsar
         · Borra el flag para no colapsar en el siguiente render
       ──────────────────────────────────────────────────────────────────── */
    var FLAG = 'oram_nav_click_ts';

    /* Paso 1: ¿venimos de un click de nav? Colapsar el sidebar */
    var ts = sessionStorage.getItem(FLAG);
    if (ts && (Date.now() - parseInt(ts, 10)) < 1500) {
        sessionStorage.removeItem(FLAG);
        /* Intentar colapsar con múltiples selectores para máxima compatibilidad */
        function tryCollapse(attempts) {
            var selectors = [
                '[data-testid="stSidebarCollapseButton"] button',
                '[data-testid="stBaseButton-headerNoPadding"]',
                'button[aria-label="Close sidebar"]',
                'button[kind="header"]',
                '[data-testid="stSidebar"] button[aria-expanded="true"]',
            ];
            for (var i = 0; i < selectors.length; i++) {
                var btn = document.querySelector(selectors[i]);
                if (btn) { btn.click(); return; }
            }
            if (attempts > 0) setTimeout(function(){ tryCollapse(attempts - 1); }, 150);
        }
        setTimeout(function(){ tryCollapse(8); }, 80);
    }

    /* Paso 2: adjuntar listeners a los labels del sidebar */
    function attachListeners() {
        var sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return false;
        var labels = sidebar.querySelectorAll('div[role="radiogroup"] label');
        if (!labels.length) return false;
        labels.forEach(function (lbl) {
            if (lbl._oramBound) return;
            lbl._oramBound = true;
            lbl.addEventListener('mousedown', function () {
                sessionStorage.setItem(FLAG, Date.now().toString());
            });
        });
        return true;
    }

    var tries = 0;
    var t = setInterval(function () {
        if (attachListeners() || ++tries > 50) clearInterval(t);
    }, 150);
})();
</script>
""", unsafe_allow_html=True)

        st.divider()

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
                # Flag que previene que _leer_cookie() restaure la sesión en el siguiente render
                st.session_state["logged_out"] = True
                _eliminar_cookie()
                st.rerun()

        mins = _minutos_restantes(start)
        countdown_color = c["accent3"] if mins > 30 else (c["accent"] if mins > 10 else c["red"])

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

    # ── Guardar/renovar cookie en cada interacción exitosa ───────────────────
    # Esto mantiene la cookie viva mientras el usuario esté activo.
    # La cookie se escribe con el session_start ORIGINAL (no renueva el timer).
    if COOKIES_OK and st.session_state.user:
        _escribir_cookie(user["id"], start)

    # ── Detectar cambio de módulo para mostrar animación de transición ──────
    _prev_nav = st.session_state.get("_prev_nav")
    _nav_changed = (_prev_nav is not None and _prev_nav != nav)
    _just_logged_in = st.session_state.pop("_just_logged_in", False)
    st.session_state["_prev_nav"] = nav

    # Mostrar animación de carga al cambiar de módulo o al entrar desde login
    if _nav_changed or _just_logged_in:
        _ph = st.empty()
        _module_name = nav.split(" ", 1)[-1] if " " in nav else nav
        _ph.markdown(f"""
<style>
@keyframes oram-tr-in {{
    from {{ opacity:0; transform:translateY(18px); }}
    to   {{ opacity:1; transform:translateY(0); }}
}}
@keyframes oram-tr-bar {{
    from {{ width: 0%; }}
    to   {{ width: 100%; }}
}}
#oram-tr-wrap {{
    position:fixed;inset:0;
    background:{'rgba(6,9,15,0.96)' if get_theme()=='dark' else 'rgba(238,242,247,0.97)'};
    backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
    z-index:99999;display:flex;flex-direction:column;
    align-items:center;justify-content:center;gap:1.4rem;
}}
#oram-tr-logo {{
    font-family:'Space Grotesk',sans-serif;font-size:2.2rem;
    font-weight:800;letter-spacing:-1px;
    animation:oram-tr-in 0.4s cubic-bezier(.22,1,.36,1) both;
}}
#oram-tr-mod {{
    font-family:'Inter',sans-serif;font-size:0.95rem;font-weight:500;
    color:{'#c8d8ea' if get_theme()=='dark' else '#2a3f54'};
    animation:oram-tr-in 0.4s .08s cubic-bezier(.22,1,.36,1) both;
    letter-spacing:0.2px;
}}
#oram-tr-bar-wrap {{
    width:220px;height:2px;
    background:{'rgba(255,255,255,0.08)' if get_theme()=='dark' else 'rgba(0,0,0,0.08)'};
    border-radius:2px;overflow:hidden;
}}
#oram-tr-bar-fill {{
    height:100%;background:#22c55e;border-radius:2px;
    animation:oram-tr-bar 0.55s .1s cubic-bezier(.4,0,.2,1) both;
}}
</style>
<div id="oram-tr-wrap">
  <div id="oram-tr-logo">
    <span style="color:#c9a227">O</span><span style="color:#3d9bff">R</span><span style="color:#00bfa5">A</span><span style="color:{'#edf4ff' if get_theme()=='dark' else '#0b1824'}">M</span>
  </div>
  <div id="oram-tr-mod">{_module_name}</div>
  <div id="oram-tr-bar-wrap"><div id="oram-tr-bar-fill"></div></div>
</div>
""", unsafe_allow_html=True)
        import time as _time
        _time.sleep(0.55)
        _ph.empty()

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
