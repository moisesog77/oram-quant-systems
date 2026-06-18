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
import streamlit.components.v1 as _stc
from datetime import datetime, timezone
import json

st.set_page_config(
    page_title="ORAM Quant Systems",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
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
    if not COOKIES_OK or _cookie_manager is None:
        return
    try:
        _cookie_manager.delete(COOKIE_NAME, key="oram_del_cookie")
    except Exception:
        pass


def _session_expiro(session_start: float) -> bool:
    elapsed = datetime.now(timezone.utc).timestamp() - session_start
    return elapsed >= SESSION_TIMEOUT_SECS


def _minutos_restantes(session_start: float) -> int:
    elapsed = datetime.now(timezone.utc).timestamp() - session_start
    return max(0, int((SESSION_TIMEOUT_SECS - elapsed) / 60))


# ── Imports ───────────────────────────────────────────────────────────────────
from ui.styles     import inject_styles, toggle_theme, get_theme, get_colors, APP_TAGLINE
from database.db   import inicializar_db, obtener_todos_usuarios, obtener_usuario_por_id

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

@st.cache_resource
def _init_db_once():
    inicializar_db()

_init_db_once()

# ── Restaurar sesión desde cookie ────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None and COOKIES_OK:
    if st.session_state.get("logged_out"):
        st.session_state.pop("logged_out", None)
        _eliminar_cookie()
    else:
        cookie_data = _leer_cookie()
        if cookie_data:
            session_start = cookie_data.get("session_start", 0)
            user_id       = cookie_data.get("user_id")
            if user_id and not _session_expiro(session_start):
                try:
                    user_db = obtener_usuario_por_id(int(user_id))
                    if user_db:
                        st.session_state.user          = user_db
                        st.session_state["session_start"] = session_start
                except Exception:
                    _eliminar_cookie()
            else:
                _eliminar_cookie()

# ── Verificar expiración ──────────────────────────────────────────────────────
if st.session_state.user is not None:
    start = st.session_state.get("session_start", datetime.now(timezone.utc).timestamp())
    if _session_expiro(start):
        st.session_state.user = None
        st.session_state.pop("session_start", None)
        _eliminar_cookie()
        st.rerun()

# ── Enrutamiento ──────────────────────────────────────────────────────────────
if st.session_state.user is None:
    render_auth()

else:
    import time as _time
    from ui.styles import LOGO_GOLD, LOGO_BLUE, LOGO_TEAL

    c        = get_colors()
    user     = st.session_state.user
    is_admin = bool(user.get("is_admin", 0))
    start    = st.session_state.get("session_start", datetime.now(timezone.utc).timestamp())

    # ── Estado de navegación ─────────────────────────────────────────────────
    # _current_nav  : módulo que se está mostrando AHORA
    # _transitioning: True → render de overlay (sidebar NO se renderiza)
    # _show_reveal  : True → overlay de reveal UNA vez tras navegación
    # _tr_tick      : contador para forzar recreación del iframe de JS cada navegación
    if "_current_nav" not in st.session_state:
        st.session_state["_current_nav"] = "📈 Dashboard"

    _transitioning = st.session_state.pop("_transitioning", False)

    # ── FASE DE TRANSICIÓN: solo overlay, sin sidebar ────────────────────────
    if _transitioning:
        _nav_target  = st.session_state["_current_nav"]
        _dark  = get_theme() == "dark"
        _olay  = "rgba(6,9,15,0.97)"  if _dark else "rgba(238,242,247,0.97)"
        _cbg   = "#0c1219"            if _dark else "#ffffff"
        _cbdr  = "#1b2a40"            if _dark else "#dde5ef"
        _tmain = "#edf4ff"            if _dark else "#0b1824"
        _tmut  = "#637a94"            if _dark else "#7a8fa0"
        _module_name = _nav_target.split(" ", 1)[-1] if " " in _nav_target else _nav_target

        # CSS + overlay combinados: sidebar oculto + fondo opaco cubre todo.
        # El fondo NO anima — permanece sólido hasta que st.rerun() reemplaza el DOM.
        # Solo el card hace su exit premium (fade + move up) para el aspecto premium.
        st.markdown(f"""
<style>
section[data-testid="stSidebar"]{{display:none!important;}}
[data-testid="stSidebarCollapsedControl"]{{display:none!important;}}
@keyframes oram-fadein{{
    from{{opacity:0;transform:translateY(16px) scale(0.96);}}
    to  {{opacity:1;transform:translateY(0) scale(1);}}
}}
@keyframes oram-card-exit{{
    0%,72%{{opacity:1;transform:translateY(0) scale(1);}}
    100%  {{opacity:0;transform:translateY(-10px) scale(0.96);}}
}}
@keyframes oram-pulse{{
    0%,100%{{box-shadow:0 0 0 0    rgba(34,197,94,0.45);}}
    50%    {{box-shadow:0 0 0 20px rgba(34,197,94,0);}}
}}
@keyframes oram-spin{{to{{transform:rotate(360deg);}}}}
#oram-tr-overlay{{
    position:fixed;inset:0;background:{_olay};
    backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
    z-index:99999;display:flex;align-items:center;justify-content:center;
}}
#oram-tr-card{{
    background:{_cbg};border:1px solid {_cbdr};border-radius:20px;
    padding:2.8rem 3rem 2.4rem;text-align:center;max-width:400px;width:90%;
    animation:oram-fadein 0.4s cubic-bezier(0.22,1,0.36,1) both,
              oram-card-exit 2.0s ease-in-out forwards;
    box-shadow:0 28px 64px rgba(0,0,0,0.4);
}}
.oram-tr-ring{{
    width:68px;height:68px;border-radius:50%;
    background:rgba(34,197,94,0.12);border:2px solid #22c55e;
    display:flex;align-items:center;justify-content:center;margin:0 auto 1.4rem;
    animation:oram-pulse 1.6s ease-in-out infinite;
}}
.oram-tr-ring svg{{width:30px;height:30px;stroke:#22c55e;fill:none;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round;}}
.oram-tr-logo{{font-family:'Space Grotesk',sans-serif;font-size:1.1rem;font-weight:800;letter-spacing:-1px;margin-bottom:0.2rem;}}
.oram-tr-title{{font-family:'Inter',sans-serif;font-size:1.15rem;font-weight:700;color:{_tmain};margin-bottom:0.55rem;}}
.oram-tr-spin-row{{display:flex;align-items:center;justify-content:center;gap:0.55rem;}}
.oram-tr-spinner{{width:15px;height:15px;border:2px solid rgba(34,197,94,0.25);border-top-color:#22c55e;border-radius:50%;animation:oram-spin 0.7s linear infinite;flex-shrink:0;}}
.oram-tr-label{{font-family:'JetBrains Mono',monospace;font-size:0.72rem;letter-spacing:1.5px;text-transform:uppercase;color:{_tmut};}}
</style>
<div id="oram-tr-overlay">
  <div id="oram-tr-card">
    <div class="oram-tr-ring">
      <svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
    </div>
    <div class="oram-tr-logo">
      <span style="color:{LOGO_GOLD}">O</span><span style="color:{LOGO_BLUE}">R</span><span style="color:{LOGO_TEAL}">A</span><span style="color:{_tmain}">M</span>
      <span style="color:{_tmut};font-weight:500;font-size:0.85rem;letter-spacing:0"> Quant Systems</span>
    </div>
    <div class="oram-tr-title">{_module_name}</div>
    <div class="oram-tr-spin-row">
      <div class="oram-tr-spinner"></div>
      <span class="oram-tr-label">Cargando módulo…</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        # Durante los 1.5s de sleep el overlay cubre todo.
        # JS aprovecha ese tiempo para clickear el botón de colapso del sidebar
        # (stSidebarCollapseButton) y dejar el estado de React en "cerrado".
        # Reintentos cada 50ms durante ~1.5s → muy alta probabilidad de éxito.
        # _tr_tick fuerza un iframe nuevo en cada navegación → JS siempre corre.
        _tr_tick = st.session_state.get("_tr_tick", 0) + 1
        st.session_state["_tr_tick"] = _tr_tick
        _stc.html(f"""<script>
/* oram-close tick:{_tr_tick} */
(function(){{
    var p;try{{p=window.parent;}}catch(e){{return;}}
    var doc=p.document;
    function tryClose(n){{
        var btn=doc.querySelector('[data-testid="stSidebarCollapseButton"] button');
        if(btn){{btn.click();return;}}
        if(n<29){{setTimeout(function(){{tryClose(n+1);}},50);}}
    }}
    setTimeout(function(){{tryClose(0);}},80);
}})();
</script>""", height=1)
        _time.sleep(2.0)
        st.session_state["_show_reveal"] = True
        st.rerun()

    # ── FASE NORMAL: sidebar + módulo ────────────────────────────────────────
    else:
        _show_reveal = st.session_state.pop("_show_reveal", False)

        # Reveal overlay: cubre el flash del swap de módulo (1 render tras nav).
        if _show_reveal:
            _dark_rv = get_theme() == "dark"
            _olay_rv = "rgba(6,9,15,0.98)" if _dark_rv else "rgba(238,242,247,0.98)"
            st.markdown(f"""<style>
@keyframes oram-rv{{0%,62%{{opacity:1;}}100%{{opacity:0;pointer-events:none;}}}}
#oram-rv{{position:fixed;inset:0;background:{_olay_rv};z-index:99998;pointer-events:none;animation:oram-rv 0.8s ease-out forwards;}}
</style><div id="oram-rv"></div>""", unsafe_allow_html=True)

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

            # El índice por defecto refleja el módulo actual
            _cur = st.session_state["_current_nav"]
            _default_idx = nav_options.index(_cur) if _cur in nav_options else 0

            nav = st.radio(
                "", nav_options,
                index=_default_idx,
                label_visibility="hidden",
            )

            st.divider()

            col_t, col_s = st.columns(2)
            with col_t:
                label_tema = "☀️ Claro" if get_theme() == "dark" else "🌙 Oscuro"
                if st.button(label_tema, key="sb_theme"):
                    toggle_theme()
                    st.rerun()
            with col_s:
                if st.button("🚪 Salir", key="sb_logout"):
                    _dark_lo  = get_theme() == "dark"
                    _olay_lo  = "rgba(6,9,15,0.92)"  if _dark_lo else "rgba(238,242,247,0.94)"
                    _cbg_lo   = "#0c1219"             if _dark_lo else "#ffffff"
                    _cbdr_lo  = "#1b2a40"             if _dark_lo else "#dde5ef"
                    _tmain_lo = "#edf4ff"             if _dark_lo else "#0b1824"
                    _tmut_lo  = "#637a94"             if _dark_lo else "#7a8fa0"
                    _user_lo  = user.get("username", "").upper()
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
                    _time.sleep(2.0)
                    _ph_lo.empty()
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

        # ── Guardar cookie ───────────────────────────────────────────────────
        if COOKIES_OK and st.session_state.user:
            _escribir_cookie(user["id"], start)

        # ── Detectar cambio de módulo ────────────────────────────────────────
        if nav != st.session_state["_current_nav"]:
            st.session_state["_current_nav"] = nav
            st.session_state["_transitioning"] = True
            st.rerun()

        # ── Renderizar módulo actual ─────────────────────────────────────────
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
        _PAGE_MAP[st.session_state["_current_nav"]]()
