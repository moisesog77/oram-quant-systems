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
    initial_sidebar_state="auto",
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

    # ── Mantener sidebar colapsado si el usuario acaba de navegar ──────────────
    # Streamlit no expone set_sidebar_state() en caliente, pero sí respeta
    # el estado interno si lo forzamos via JS en el área principal ANTES
    # de que el sidebar se renderice. Usamos session_state como flag.
    if st.session_state.get("_sidebar_collapsed"):
        st.markdown("""
<style>
/* Mantiene el sidebar colapsado hasta que el usuario lo abra manualmente */
[data-testid="stSidebar"][aria-expanded="true"] {
    margin-left: calc(-1 * var(--sidebar-width, 21rem)) !important;
    visibility: hidden !important;
}
</style>
<script>
(function () {
    /* Colapsar sidebar y limpiar flag via postMessage a Streamlit */
    function collapseNow(attempts) {
        var selectors = [
            '[data-testid="stSidebarCollapseButton"] button',
            '[data-testid="stBaseButton-headerNoPadding"]',
            'button[aria-label="Close sidebar"]',
            '[data-testid="stSidebar"] button[aria-expanded="true"]',
        ];
        for (var i = 0; i < selectors.length; i++) {
            var btn = document.querySelector(selectors[i]);
            if (btn) { btn.click(); return; }
        }
        if (attempts > 0) setTimeout(function () { collapseNow(attempts - 1); }, 80);
    }
    collapseNow(15);
})();
</script>
""", unsafe_allow_html=True)
        # Limpiar el flag inmediatamente para no volver a colapsar en el siguiente render
        del st.session_state["_sidebar_collapsed"]

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

        st.markdown("""
<script>
(function () {
    /* ── ORAM sidebar nav listeners ──────────────────────────────────────
       RENDER N (usuario hace click en label):
         · listener mousedown → guarda timestamp + nombre en sessionStorage
       El collapse real ocurre en el área principal (render N+1), ANTES
       que el overlay de carga, usando CSS hide + JS click.
       ──────────────────────────────────────────────────────────────────── */
    var FLAG = 'oram_nav_click_ts';

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
                # ── Overlay premium de despedida ──────────────────────────────
                _dark_lo  = get_theme() == "dark"
                _olay_lo  = "rgba(6,9,15,0.92)"  if _dark_lo else "rgba(238,242,247,0.94)"
                _cbg_lo   = "#0c1219"             if _dark_lo else "#ffffff"
                _cbdr_lo  = "#1b2a40"             if _dark_lo else "#dde5ef"
                _tmain_lo = "#edf4ff"             if _dark_lo else "#0b1824"
                _tmut_lo  = "#637a94"             if _dark_lo else "#7a8fa0"
                _user_lo  = user.get("username", "").upper()
                from ui.styles import LOGO_GOLD, LOGO_BLUE, LOGO_TEAL
                import time as _tlo
                _ph_lo = st.empty()
                _ph_lo.markdown(f"""
<style>
@keyframes oram-lo-in {{
    from {{ opacity:0; transform:translateY(14px) scale(0.97); }}
    to   {{ opacity:1; transform:translateY(0) scale(1); }}
}}
@keyframes oram-lo-pulse {{
    0%,100% {{ box-shadow:0 0 0 0    rgba(201,162,39,0.40); }}
    50%      {{ box-shadow:0 0 0 18px rgba(201,162,39,0); }}
}}
@keyframes oram-lo-spin {{ to {{ transform:rotate(360deg); }} }}
#oram-lo-overlay {{
    position:fixed;inset:0;background:{_olay_lo};
    backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);
    z-index:99999;display:flex;align-items:center;justify-content:center;
}}
#oram-lo-card {{
    background:{_cbg_lo};border:1px solid {_cbdr_lo};border-radius:20px;
    padding:2.8rem 3rem 2.4rem;text-align:center;
    max-width:400px;width:90%;
    animation:oram-lo-in 0.45s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow:0 24px 60px rgba(0,0,0,0.35);
}}
.oram-lo-ring {{
    width:64px;height:64px;border-radius:50%;
    background:rgba(201,162,39,0.12);border:2px solid {LOGO_GOLD};
    display:flex;align-items:center;justify-content:center;
    margin:0 auto 1.4rem;
    animation:oram-lo-pulse 1.6s ease-in-out infinite;
}}
.oram-lo-ring svg {{
    width:28px;height:28px;stroke:{LOGO_GOLD};fill:none;
    stroke-width:2;stroke-linecap:round;stroke-linejoin:round;
}}
.oram-lo-logo {{
    font-family:'Space Grotesk',sans-serif;
    font-size:1.1rem;font-weight:800;letter-spacing:-1px;margin-bottom:0.15rem;
}}
.oram-lo-title {{
    font-family:'Inter',sans-serif;font-size:1.1rem;font-weight:700;
    color:{_tmain_lo};margin-bottom:0.3rem;
}}
.oram-lo-sub {{
    font-family:'Inter',sans-serif;font-size:0.82rem;
    color:{_tmut_lo};margin-bottom:1.6rem;line-height:1.5;
}}
.oram-lo-spin-row {{
    display:flex;align-items:center;justify-content:center;gap:0.55rem;
}}
.oram-lo-spinner {{
    width:16px;height:16px;
    border:2px solid rgba(201,162,39,0.25);
    border-top-color:{LOGO_GOLD};border-radius:50%;
    animation:oram-lo-spin 0.75s linear infinite;flex-shrink:0;
}}
.oram-lo-label {{
    font-family:'JetBrains Mono',monospace;font-size:0.72rem;
    letter-spacing:1.5px;text-transform:uppercase;color:{_tmut_lo};
}}
</style>
<div id="oram-lo-overlay">
  <div id="oram-lo-card">
    <div class="oram-lo-ring">
      <svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
    </div>
    <div class="oram-lo-logo">
      <span style="color:{LOGO_GOLD}">O</span><span style="color:{LOGO_BLUE}">R</span><span style="color:{LOGO_TEAL}">A</span><span style="color:{_tmain_lo}">M</span>
      <span style="color:{_tmut_lo};font-weight:500;font-size:0.85rem;letter-spacing:0"> Quant Systems</span>
    </div>
    <div class="oram-lo-title">Hasta pronto, {_user_lo}</div>
    <div class="oram-lo-sub">Tu sesión ha sido cerrada de forma segura.</div>
    <div class="oram-lo-spin-row">
      <div class="oram-lo-spinner"></div>
      <span class="oram-lo-label">Cerrando sesión…</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
                _tlo.sleep(2.0)
                _ph_lo.empty()
                # Limpiar sesión y cookie
                st.session_state.user = None
                st.session_state.pop("session_start", None)
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
        import time as _time
        from ui.styles import LOGO_GOLD, LOGO_BLUE, LOGO_TEAL
        _dark  = get_theme() == "dark"
        _olay  = "rgba(6,9,15,0.92)"    if _dark else "rgba(238,242,247,0.94)"
        _cbg   = "#0c1219"              if _dark else "#ffffff"
        _cbdr  = "#1b2a40"              if _dark else "#dde5ef"
        _tmain = "#edf4ff"              if _dark else "#0b1824"
        _tmut  = "#637a94"              if _dark else "#7a8fa0"
        _module_name = nav.split(" ", 1)[-1] if " " in nav else nav

        _ph = st.empty()
        _ph.markdown(f"""
<style>
/* ── Colapsar sidebar INSTANTÁNEAMENTE durante la transición ─────────────
   El overlay cubre todo (z-index 99999), pero también ocultamos el sidebar
   directamente para que no haya ningún flash visible del menú abierto.    */
[data-testid="stSidebar"] {{
    transform: translateX(-110%) !important;
    transition: transform 0.18s cubic-bezier(0.4,0,0.2,1) !important;
}}

@keyframes oram-fadein {{
    from {{ opacity:0; transform:translateY(14px) scale(0.97); }}
    to   {{ opacity:1; transform:translateY(0) scale(1); }}
}}
@keyframes oram-pulse {{
    0%,100% {{ box-shadow:0 0 0 0    rgba(34,197,94,0.40); }}
    50%      {{ box-shadow:0 0 0 18px rgba(34,197,94,0); }}
}}
@keyframes oram-spin {{
    to {{ transform:rotate(360deg); }}
}}
#oram-tr-overlay {{
    position:fixed;inset:0;background:{_olay};
    backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);
    z-index:99999;display:flex;align-items:center;justify-content:center;
}}
#oram-tr-card {{
    background:{_cbg};border:1px solid {_cbdr};border-radius:20px;
    padding:2.8rem 3rem 2.4rem;text-align:center;
    max-width:400px;width:90%;
    animation:oram-fadein 0.45s cubic-bezier(0.22,1,0.36,1) both;
    box-shadow:0 24px 60px rgba(0,0,0,0.35);
}}
.oram-tr-ring {{
    width:64px;height:64px;border-radius:50%;
    background:rgba(34,197,94,0.12);border:2px solid #22c55e;
    display:flex;align-items:center;justify-content:center;
    margin:0 auto 1.4rem;
    animation:oram-pulse 1.6s ease-in-out infinite;
}}
.oram-tr-ring svg {{
    width:30px;height:30px;stroke:#22c55e;fill:none;
    stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round;
}}
.oram-tr-logo {{
    font-family:'Space Grotesk',sans-serif;
    font-size:1.1rem;font-weight:800;letter-spacing:-1px;margin-bottom:0.15rem;
}}
.oram-tr-title {{
    font-family:'Inter',sans-serif;font-size:1.15rem;font-weight:700;
    color:{_tmain};margin-bottom:0.5rem;
}}
.oram-tr-spin-row {{
    display:flex;align-items:center;justify-content:center;gap:0.55rem;
}}
.oram-tr-spinner {{
    width:16px;height:16px;
    border:2px solid rgba(34,197,94,0.25);
    border-top-color:#22c55e;border-radius:50%;
    animation:oram-spin 0.75s linear infinite;flex-shrink:0;
}}
.oram-tr-label {{
    font-family:'JetBrains Mono',monospace;font-size:0.72rem;
    letter-spacing:1.5px;text-transform:uppercase;color:{_tmut};
}}
</style>
<script>
/* ── Collapse sidebar via botón Y limpiar flag de sessionStorage ────────
   Se ejecuta en este mismo render (N+1), justo cuando el overlay aparece.
   El CSS ya ocultó visualmente el sidebar; ahora hacemos el click para que
   Streamlit actualice su estado interno y el sidebar siga colapsado
   después de que el overlay desaparezca.                                 */
(function () {{
    var FLAG = 'oram_nav_click_ts';
    sessionStorage.removeItem(FLAG);   // limpiar flag

    function tryCollapse(attempts) {{
        var selectors = [
            '[data-testid="stSidebarCollapseButton"] button',
            '[data-testid="stBaseButton-headerNoPadding"]',
            'button[aria-label="Close sidebar"]',
            'button[kind="header"]',
            '[data-testid="stSidebar"] button[aria-expanded="true"]',
        ];
        for (var i = 0; i < selectors.length; i++) {{
            var btn = document.querySelector(selectors[i]);
            if (btn) {{ btn.click(); return; }}
        }}
        if (attempts > 0) setTimeout(function () {{ tryCollapse(attempts - 1); }}, 100);
    }}
    tryCollapse(12);   /* intentos: 12 × 100ms = hasta 1.2s de margen */
}})();
</script>
<div id="oram-tr-overlay">
  <div id="oram-tr-card">
    <div class="oram-tr-ring">
      <svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
    </div>
    <div class="oram-tr-logo">
      <span style="color:{LOGO_GOLD}">O</span><span style="color:{LOGO_BLUE}">R</span><span style="color:{LOGO_TEAL}">A</span><span style="color:{_tmain}">M</span>
      <span style="color:{_tmut};font-weight:500;font-size:0.85rem;letter-spacing:0px"> Quant Systems</span>
    </div>
    <div class="oram-tr-title">{_module_name}</div>
    <div class="oram-tr-spin-row">
      <div class="oram-tr-spinner"></div>
      <span class="oram-tr-label">Cargando módulo…</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        _time.sleep(1.8)
        _ph.empty()
        # Flag para que el PRÓXIMO render mantenga el sidebar colapsado
        st.session_state["_sidebar_collapsed"] = True

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
