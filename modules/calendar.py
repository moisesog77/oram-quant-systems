"""
modules/calendar.py — Calendario Económico semanal v3.
- Por defecto muestra solo HOY y días futuros de la semana
- Los días pasados se muestran en sección colapsada
- Noticias en español
"""
import streamlit as st
from utils.economic_calendar import (
    obtener_eventos_semana, obtener_proximos_eventos,
    hay_evento_alto_impacto_pronto,
    impacto_color, impacto_emoji,
)

_FOREX_FACTORY_URL = "https://www.forexfactory.com/calendar"

EVENTOS_ESPECIALES: list = [
    {"titulo": "Decisión de Tipos de la Fed",       "moneda": "USD", "impacto": "High",
     "descripcion": "🔴 MÁXIMO IMPACTO — Reunión del FOMC con decisión de tipos (8 veces/año). Evita operar 30 min antes y 30 min después."},
    {"titulo": "IPC de EE.UU. (Inflación)",         "moneda": "USD", "impacto": "High",
     "descripcion": "Índice de Precios al Consumidor. Mide la inflación mensual (~2do o 3er miércoles del mes)."},
    {"titulo": "IPP de EE.UU.",                     "moneda": "USD", "impacto": "Medium",
     "descripcion": "Índice de Precios al Productor. Mide la inflación en etapas previas al consumidor."},
    {"titulo": "PIB de EE.UU.",                     "moneda": "USD", "impacto": "High",
     "descripcion": "Producto Interno Bruto de EE.UU. — avance, estimado y final, publicados en trimestres escalonados."},
    {"titulo": "PCE Subyacente",                    "moneda": "USD", "impacto": "High",
     "descripcion": "🔴 El indicador de inflación preferido de la Fed — se publica ~último viernes de cada mes."},
    {"titulo": "Decisión de Tipos Banco de Japón",  "moneda": "JPY", "impacto": "High",
     "descripcion": "Política monetaria del BoJ. Causa alta volatilidad en USDJPY. Puede ocurrir cualquier día."},
    {"titulo": "Decisión de Tipos RBA",             "moneda": "AUD", "impacto": "High",
     "descripcion": "Banco de la Reserva de Australia. Impacta AUDUSD. Se publica generalmente los martes."},
    {"titulo": "Decisión de Tipos Banco de Canadá", "moneda": "CAD", "impacto": "High",
     "descripcion": "Política monetaria del BoC. Impacta USDCAD (~8 veces por año)."},
]
from ui.styles import get_colors, page_header, get_theme, inject_module_css



def _render_evento(ev, c, dark):
    """
    Renderiza un evento económico como tarjeta premium.
    Usa concatenación de strings (no f-string multilínea) para evitar
    que el parser de markdown de Streamlit interprete el HTML como código.
    """
    imp_color   = impacto_color(ev["impacto"], dark)
    dia_fecha   = ev["dia"] + " " + ev["fecha"]
    hora_mx     = ev["hora_mx"]
    hora_utc    = ev["hora_utc"]
    moneda      = ev["moneda"]
    impacto_txt = ev["impacto"]
    impacto_ico = impacto_emoji(ev["impacto"])
    titulo      = ev["titulo"]
    descripcion = ev.get("descripcion", "")
    border_col  = c["border"]
    text_muted  = c["text_muted"]
    text_strong = c["text_strong"]

    # Estilo de fondo para evento de hoy no pasado
    bg_extra = (
        "background:rgba(245,166,35,0.08);border-left:3px solid " + c["accent"] + ";"
        if ev["es_hoy"] and not ev["ya_paso"] else ""
    )

    # Badge de estado
    if ev["ya_paso"] and ev["es_hoy"]:
        badge = ('<span style="font-size:0.65rem;background:' + border_col +
                 ';color:' + text_muted +
                 ';border-radius:3px;padding:1px 6px;margin-left:6px">YA PASÓ</span>')
    elif ev["es_hoy"]:
        badge = ('<span style="font-size:0.65rem;background:' + imp_color +
                 '22;color:' + imp_color +
                 ';border-radius:3px;padding:1px 6px;margin-left:6px;font-weight:700">HOY</span>')
    else:
        badge = ""

    desc_html = (
        '<div class="card-sub" style="margin-top:0.2rem;line-height:1.5">' + descripcion + "</div>"
        if descripcion else ""
    )

    # HTML construido como cadena simple — SIN saltos de línea internos
    # para evitar que el parser markdown de Streamlit lo interprete como bloque de código
    html = (
        '<div class="smc-card" style="padding:0.85rem 1.2rem;margin-bottom:0.4rem;' + bg_extra + '">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">' +
        '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">' +
        '<span style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:' + text_muted + '">' +
        dia_fecha + '</span>' +
        '<span style="font-family:JetBrains Mono,monospace;font-size:0.75rem;background:' + border_col +
        ';border-radius:4px;padding:2px 8px;font-weight:700">' + hora_mx + ' CDMX</span>' +
        '<span style="font-family:JetBrains Mono,monospace;font-size:0.68rem;color:' + text_muted +
        '">UTC ' + hora_utc + '</span>' +
        badge +
        '</div>' +
        '<div style="display:flex;align-items:center;gap:8px">' +
        '<span style="font-family:JetBrains Mono,monospace;font-size:0.72rem;background:' + border_col +
        ';border-radius:4px;padding:2px 8px">' + moneda + '</span>' +
        '<span style="color:' + imp_color + ';font-weight:700;font-size:0.85rem">' +
        impacto_ico + " " + impacto_txt + '</span>' +
        '</div></div>' +
        '<div style="font-size:0.9rem;font-weight:700;margin-top:0.35rem;color:' + text_strong +
        '">' + titulo + '</div>' +
        desc_html +
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_calendar():
    c    = get_colors()
    dark = get_theme() == "dark"

    page_header("📰", "Calendario Económico", "Eventos semanales · Horas en CDMX · Alto impacto primero")
    inject_module_css(dark)

    # ── Alerta si hay evento pronto ────────────────────────────────────────
    hay_alerta, ev_alerta = hay_evento_alto_impacto_pronto(minutos=90)
    if hay_alerta and ev_alerta:
        st.error(
            f"⚠️ **EVENTO DE ALTO IMPACTO EN {ev_alerta['minutos_restantes']} MIN** — "
            f"{ev_alerta['titulo']} ({ev_alerta['moneda']}) · "
            f"{ev_alerta['hora_mx']} CDMX · No abras posiciones nuevas."
        )

    # ── Próximos eventos (máx 4) ───────────────────────────────────────────
    proximos = obtener_proximos_eventos(4)
    if proximos:
        st.markdown("#### ⏰ Próximos eventos")
        cols = st.columns(min(len(proximos), 4))
        for col, ev in zip(cols, proximos):
            imp_color = impacto_color(ev["impacto"], dark)
            card_color = "red" if ev["impacto"]=="High" else "accent" if ev["impacto"]=="Medium" else "blue"
            with col:
                st.markdown(f"""
                <div class="smc-card smc-card-{card_color}" style="padding:0.8rem 1rem">
                    <div class="card-title">{ev['dia']} · {ev['hora_mx']} CDMX</div>
                    <div style="font-size:0.82rem;font-weight:700;color:{imp_color}">
                        {impacto_emoji(ev['impacto'])} {ev['titulo']}
                    </div>
                    <div class="card-sub">{ev['moneda']} · UTC {ev['hora_utc']}</div>
                </div>
                """, unsafe_allow_html=True)
        st.divider()

    # ── Obtener todos los eventos y separarlos ─────────────────────────────
    todos = obtener_eventos_semana()

    # Separar: pendientes (hoy + futuro) vs pasados (días anteriores)
    pendientes   = [e for e in todos if not (e["ya_paso"] and not e["es_hoy"])]
    dias_pasados = [e for e in todos if e["ya_paso"] and not e["es_hoy"]]

    # ── Filtros (aplican solo a pendientes) ────────────────────────────────
    fc1, fc2 = st.columns(2)
    with fc1:
        filtro_moneda  = st.selectbox("Moneda",  ["Todas","USD","EUR","GBP","JPY","AUD","CAD"], key="cal_mon")
    with fc2:
        filtro_impacto = st.selectbox("Impacto", ["Todos","High","Medium","Low"],                key="cal_imp")

    def aplicar_filtros(lista):
        if filtro_moneda  != "Todas": lista = [e for e in lista if e["moneda"]  == filtro_moneda]
        if filtro_impacto != "Todos": lista = [e for e in lista if e["impacto"] == filtro_impacto]
        return lista

    pendientes_f   = aplicar_filtros(pendientes)
    dias_pasados_f = aplicar_filtros(dias_pasados)

    # ── Eventos pendientes (hoy + resto de semana) ─────────────────────────
    n_pend      = len(pendientes_f)
    label_pend  = f"📅 {n_pend} evento{'s' if n_pend != 1 else ''} pendiente{'s' if n_pend != 1 else ''}"
    with st.expander(label_pend, expanded=False):
        if pendientes_f:
            for ev in pendientes_f:
                _render_evento(ev, c, dark)
        else:
            st.caption("No hay más eventos pendientes esta semana.")

    st.divider()

    # ── Eventos pasados (esta semana, colapsados) ──────────────────────────
    if dias_pasados_f:
        with st.expander(f"📅 Eventos pasados esta semana ({len(dias_pasados_f)})", expanded=False):
            st.caption("Eventos que ya ocurrieron en días anteriores de esta semana.")
            for ev in dias_pasados_f:
                imp_color = impacto_color(ev["impacto"], dark)
                # Mostrar compacto con menor prominencia
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:0.5rem 0.8rem;
                            margin-bottom:0.3rem;border:1px solid {c['border']};
                            border-radius:8px;opacity:0.7">
                    <span style="color:{imp_color};font-size:0.85rem">{impacto_emoji(ev['impacto'])}</span>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                                 color:{c['text_muted']};min-width:100px">{ev['dia'][:3]} {ev['hora_mx']}</span>
                    <span style="font-size:0.85rem;font-weight:600;color:{c['text_strong']}">{ev['titulo']}</span>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;
                                 color:{c['text_muted']};margin-left:auto">{ev['moneda']}</span>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ── Eventos especiales de baja frecuencia ──────────────────────────────
    with st.expander("📋 Eventos de baja frecuencia (referencia)", expanded=False):
        for ev in EVENTOS_ESPECIALES:
            imp_color = impacto_color(ev["impacto"], dark)
            st.markdown(f"""
            <div class="smc-card" style="padding:0.7rem 1rem;margin-bottom:0.3rem">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="font-weight:700;font-size:0.9rem;color:{c['text_strong']}">{ev['titulo']}</span>
                    <span style="color:{imp_color};font-size:0.82rem;font-weight:700">
                        {impacto_emoji(ev['impacto'])} {ev['moneda']}
                    </span>
                </div>
                <div class="card-sub" style="margin-top:0.2rem">{ev['descripcion']}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Link Forex Factory ─────────────────────────────────────────────────
    st.divider()
    st.markdown(f"""
    <div class="smc-card smc-card-accent">
        <div class="card-title">📡 Verificación en tiempo real</div>
        <div style="font-size:0.88rem;line-height:1.8;color:{c['text']}">
        Para horarios exactos, resultados anteriores y pronósticos actualizados consulta Forex Factory:<br>
        <a href="{_FOREX_FACTORY_URL}" target="_blank"
           style="color:{c['accent']};font-family:'JetBrains Mono',monospace;font-weight:700;text-decoration:none">
            🔗 forexfactory.com/calendar →
        </a>
        </div>
        <div class="card-sub" style="margin-top:0.5rem">
        ⚠️ Regla de oro: no operes ±30 min alrededor de eventos 🔴 High Impact
        </div>
    </div>
    """, unsafe_allow_html=True)
