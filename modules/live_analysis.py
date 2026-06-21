"""
modules/live_analysis.py — ORAM Quant Systems — Análisis SMC en Vivo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v10 — fixes definitivos:
  · Noticias: font-family con comillas dobles (soluciona HTML crudo)
  · Dropdown: 100% gestionado por styles.py + config.toml sin base=dark
  · Espacio blanco: CSS en styles.py elimina margin post-alert
  · Gráficas: separación visual premium con badges de título
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.market_data import obtener_datos, ACTIVOS_DEFAULT, mercado_cerrado
from utils.smc_engine import analisis_completo, calcular_riesgo
from database.db import obtener_bot_config, actualizar_bot_config
from utils.economic_calendar import (hay_evento_alto_impacto_pronto,
                                      obtener_proximos_eventos,
                                      impacto_emoji, impacto_color)
from ui.styles import (signal_box, get_colors, get_plot_layout,
                       page_header, get_theme, oram_bienvenida, inject_module_css)

TIMEFRAME_LABELS = {
    "1m":"1 Min","5m":"5 Min","15m":"15 Min","30m":"30 Min",
    "1h":"1 Hora","4h":"4 Horas","1d":"Diario","1wk":"Semanal",
}



def _render_news_banner(dark: bool, c: dict):
    """
    Noticias al tope con INLINE STYLES.
    CRÍTICO: usar comillas dobles (") en font-family dentro de style="..."
    Las comillas simples (') causan que Streamlit muestre HTML crudo.
    """
    hay_ev, ev_info = hay_evento_alto_impacto_pronto(minutos=90)
    proximos = obtener_proximos_eventos(5)

    if not proximos and not hay_ev:
        return

    bg_card    = c["bg_card"]
    border     = c["border"]
    accent2    = c["accent2"]
    text_muted = c["text_muted"]

    alert_html = ""
    if hay_ev and ev_info:
        ab  = "rgba(239,68,68,0.12)" if dark else "rgba(200,30,30,0.07)"
        abd = "rgba(239,68,68,0.55)" if dark else "rgba(200,30,30,0.40)"
        at  = "#f87171" if dark else "#c81e1e"
        alert_html = (
            f'<div style="display:flex;align-items:center;gap:0.75rem;'
            f'border-radius:10px;padding:0.65rem 1.1rem;margin-bottom:0.65rem;'
            f'background:{ab};border:1.5px solid {abd};">'
            f'<span style="font-size:1.2rem">&#9888;&#65039;</span>'
            f'<div>'
            f'<span style="color:{at};font-weight:700;'
            f'font-family:Space Grotesk,sans-serif;font-size:0.88rem;">'
            f'Evento de alto impacto en {ev_info["minutos_restantes"]} min'
            f'</span>'
            f'<span style="color:{text_muted};font-size:0.80rem;margin-left:0.5rem;">'
            f'&mdash; {ev_info["titulo"]} ({ev_info["moneda"]}) &middot; {ev_info["hora_mx"]} CDMX'
            f'</span>'
            f'</div></div>'
        )

    # Construir cards con string concatenation (sin f-string anidado)
    # Usar comillas dobles en font-family para evitar que Streamlit escape el HTML
    cards_html = ""
    for ev in proximos:
        imp_color = impacto_color(ev["impacto"], dark)
        imp_bg = (
            "rgba(239,68,68,0.10)"   if ev["impacto"] == "High"   else
            "rgba(201,162,39,0.08)"  if ev["impacto"] == "Medium" else
            "rgba(107,127,153,0.07)"
        ) if dark else (
            "rgba(200,30,30,0.07)"   if ev["impacto"] == "High"   else
            "rgba(154,117,16,0.06)"  if ev["impacto"] == "Medium" else
            "rgba(80,100,120,0.05)"
        )
        emoji = impacto_emoji(ev["impacto"])
        cards_html += (
            f'<div style="flex:1;min-width:140px;max-width:220px;border-radius:8px;'
            f'padding:0.5rem 0.75rem;background:{imp_bg};'
            f'border:1px solid {imp_color}33;">'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.59rem;'
            f'color:{text_muted};margin-bottom:0.18rem;">'
            f'{ev["dia"]} &middot; {ev["hora_mx"]} CDMX'
            f'</div>'
            f'<div style="font-size:0.77rem;font-weight:700;color:{imp_color};'
            f'font-family:Inter,sans-serif;line-height:1.3;">'
            f'{emoji} {ev["titulo"]}'
            f'</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.62rem;'
            f'color:{text_muted};margin-top:0.12rem;">{ev["moneda"]}</div>'
            f'</div>'
        )

    html = (
        alert_html +
        f'<div style="background:{bg_card};border:1px solid {border};'
        f'border-left:3px solid {accent2};border-radius:12px;'
        f'padding:0.85rem 1.2rem 0.75rem 1.2rem;margin-bottom:1.25rem;">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.58rem;'
        f'text-transform:uppercase;letter-spacing:2.5px;'
        f'color:{text_muted};margin-bottom:0.55rem;">'
        f'&#128240;&nbsp;&nbsp;PR&Oacute;XIMOS EVENTOS DE MERCADO'
        f'</div>'
        f'<div style="display:flex;gap:0.55rem;flex-wrap:wrap;">'
        f'{cards_html}'
        f'</div>'
        f'<a href="https://www.forexfactory.com/calendar" target="_blank"'
        f' style="display:inline-block;margin-top:0.5rem;'
        f'font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        f'text-decoration:none;opacity:0.75;color:{accent2};">'
        f'&#128279; Ver calendario completo en Forex Factory &rarr;'
        f'</a>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _grafica_velas(df, ticker, smc):
    """Gráfica con 3 paneles separados visualmente — estilo premium ORAM."""
    c    = get_colors()
    dark = get_theme() == "dark"
    gc   = c["grid"]

    # Fondos de paneles — muy sutil para no competir con las líneas
    bg_rsi  = "rgba(61,155,233,0.05)"  if dark else "rgba(22,96,168,0.04)"
    bg_macd = "rgba(201,162,39,0.05)"  if dark else "rgba(154,117,16,0.04)"
    # Color de la línea separadora entre paneles
    sep_col = c["border2"]

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.56, 0.22, 0.22],
        # vertical_spacing=0 para controlar separación manualmente con shapes
        vertical_spacing=0.0,
        subplot_titles=["", "", ""],
    )

    # ── Panel 1: Velas ───────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name=ticker,
        increasing_line_color=c["green"], decreasing_line_color=c["red"],
        increasing_fillcolor="rgba(34,197,94,0.75)",
        decreasing_fillcolor="rgba(239,68,68,0.75)",
        whiskerwidth=0.3,
    ), row=1, col=1)
    for col_name, color, label in [
        ("EMA20", c["accent2"], "EMA20"), ("EMA50", c["accent"], "EMA50"),
        ("EMA200", c["purple"], "EMA200"),
    ]:
        if col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_name],
                line=dict(color=color, width=1.3), name=label, opacity=0.90,
            ), row=1, col=1)
    if "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"],
            line=dict(color="rgba(139,92,246,0.35)", width=1, dash="dot"),
            name="BB", showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"],
            line=dict(color="rgba(139,92,246,0.35)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(139,92,246,0.04)",
            showlegend=False, name="BB Lower",
        ), row=1, col=1)
    for ob in smc.get("order_blocks", [])[:3]:
        fc = "rgba(34,197,94,0.12)" if ob.tipo == "OB_alcista" else "rgba(239,68,68,0.12)"
        lc = c["green"] if ob.tipo == "OB_alcista" else c["red"]
        fig.add_hrect(y0=ob.precio_bot, y1=ob.precio_top, fillcolor=fc,
                      line=dict(color=lc, width=1, dash="dot"),
                      annotation_text="OB↑" if ob.tipo == "OB_alcista" else "OB↓",
                      annotation_font_size=9, annotation_font_color=lc, row=1, col=1)
    for fvg in smc.get("fvgs", [])[:2]:
        fc = "rgba(61,155,233,0.10)" if fvg.tipo == "FVG_alcista" else "rgba(201,162,39,0.10)"
        lc = c["accent2"] if fvg.tipo == "FVG_alcista" else c["accent"]
        fig.add_hrect(y0=fvg.precio_bot, y1=fvg.precio_top, fillcolor=fc,
                      line=dict(color=lc, width=1, dash="dot"),
                      annotation_text="FVG", annotation_font_size=8,
                      annotation_font_color=lc, row=1, col=1)
    liq = smc.get("liquidez", {})
    for lvl in liq.get("resistance_levels", [])[:2]:
        fig.add_hline(y=lvl, line=dict(color="rgba(239,68,68,0.4)", width=1, dash="dash"), row=1, col=1)
    for lvl in liq.get("support_levels", [])[:2]:
        fig.add_hline(y=lvl, line=dict(color="rgba(34,197,94,0.4)", width=1, dash="dash"), row=1, col=1)

    # ── Panel 2: RSI ─────────────────────────────────────────────────────────
    if "RSI" in df.columns:
        # Línea RSI con gradiente suavizado
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"],
            line=dict(color="#3d9be9", width=2.0, shape="spline", smoothing=0.6),
            name="RSI", showlegend=False,
            fill="tozeroy",
            fillcolor="rgba(61,155,233,0.06)",
        ), row=2, col=1)
        # Zona sobrecompra (70-100)
        fig.add_hrect(y0=70, y1=100,
                      fillcolor="rgba(239,68,68,0.08)", line_width=0, row=2, col=1)
        # Zona sobreventa (0-30)
        fig.add_hrect(y0=0, y1=30,
                      fillcolor="rgba(34,197,94,0.08)", line_width=0, row=2, col=1)
        # Líneas de referencia RSI — sin dash, solo color sutil
        fig.add_hline(y=70,
                      line=dict(color="rgba(239,68,68,0.55)", width=1, dash="dash"),
                      row=2, col=1)
        fig.add_hline(y=30,
                      line=dict(color="rgba(34,197,94,0.55)", width=1, dash="dash"),
                      row=2, col=1)
        fig.add_hline(y=50,
                      line=dict(color="rgba(107,127,153,0.30)", width=1),
                      row=2, col=1)

    # ── Panel 3: MACD ────────────────────────────────────────────────────────
    if "MACD" in df.columns:
        hist = df["MACD_hist"]
        # Histograma con colores sólidos bien diferenciados
        fig.add_trace(go.Bar(
            x=df.index, y=hist,
            marker_color=["rgba(34,197,94,0.70)" if v >= 0 else "rgba(239,68,68,0.70)"
                          for v in hist],
            marker_line_width=0,
            name="Hist", showlegend=False,
        ), row=3, col=1)
        # Línea MACD — dorado ORAM, más gruesa y visible
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD"],
            line=dict(color="#e8b830", width=2.0, shape="spline", smoothing=0.5),
            name="MACD", showlegend=False,
        ), row=3, col=1)
        # Línea Signal — violeta claro, bien diferenciada del dorado
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_signal"],
            line=dict(color="#c084fc", width=1.8, shape="spline", smoothing=0.5),
            name="Signal", showlegend=False,
        ), row=3, col=1)
        # Línea cero — referencia sutil
        fig.add_hline(y=0,
                      line=dict(color="rgba(107,127,153,0.35)", width=1),
                      row=3, col=1)

    # ── Layout premium ───────────────────────────────────────────────────────
    layout = get_plot_layout(height=800)

    # Posiciones de los separadores (en coordenadas paper 0-1)
    # row_heights=[0.56, 0.22, 0.22] con spacing=0
    # panel RSI: y de 0.44 a 0.22 → separador superior en 0.44
    # panel MACD: y de 0.22 a 0.0  → separador superior en 0.22
    y_sep1 = 0.44   # separador entre Velas y RSI
    y_sep2 = 0.22   # separador entre RSI y MACD

    # Ticket de colores para los labels de paneles
    rsi_label_col  = "#3d9be9"
    macd_label_col = "#e8b830"
    rsi_label_bg   = "rgba(61,155,233,0.16)"  if dark else "rgba(61,155,233,0.12)"
    macd_label_bg  = "rgba(232,184,48,0.16)"  if dark else "rgba(232,184,48,0.12)"

    tick_font = dict(color=c["text_muted"], size=9, family="JetBrains Mono")

    layout.update(
        # ── Panel 1: Velas ────────────────────────────────────────────────
        xaxis=dict(
            gridcolor=gc, color=c["text_muted"], tickfont=tick_font,
            showline=False, zeroline=False, rangeslider=dict(visible=False),
            showgrid=True, griddash="solid",
        ),
        yaxis=dict(
            gridcolor=gc, color=c["text_muted"], side="right", tickfont=tick_font,
            showline=False, zeroline=False, showgrid=True, griddash="solid",
        ),
        # ── Panel 2: RSI ─────────────────────────────────────────────────
        xaxis2=dict(
            gridcolor=gc, color=c["text_muted"], tickfont=tick_font,
            showline=False, zeroline=False, showgrid=True, griddash="solid",
        ),
        yaxis2=dict(
            gridcolor=gc, color=c["text_muted"], side="right",
            tickfont=tick_font, range=[0, 100],
            showline=False, zeroline=False,
            showgrid=True, griddash="solid",
            # dtick=20 → líneas en 0,20,40,60,80,100 — mismo espaciado visual que velas
            dtick=20, tick0=0,
            tickvals=[20, 40, 60, 80],
            ticktext=["20", "40", "60", "80"],
        ),
        # ── Panel 3: MACD ────────────────────────────────────────────────
        xaxis3=dict(
            gridcolor=gc, color=c["text_muted"], tickfont=tick_font,
            showline=False, zeroline=False, showgrid=True, griddash="solid",
        ),
        yaxis3=dict(
            gridcolor=gc, color=c["text_muted"], side="right",
            tickfont=tick_font, showline=False,
            showgrid=True, griddash="solid",
            # autoticksuffix — Plotly calcula el dtick según el rango MACD
            # nticks fuerza un número similar al de los otros paneles
            nticks=5,
            zerolinecolor=c["border2"], zerolinewidth=1, zeroline=True,
        ),
        margin=dict(l=8, r=68, t=28, b=32),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.005, xanchor="left", x=0,
            font=dict(color=c["text_muted"], size=9, family="JetBrains Mono"),
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
        ),
        bargap=0.15,
        # ── Labels de paneles ──────────────────────────────────────────────
        annotations=[
            dict(
                text="<b>RSI</b> (14)",
                xref="paper", yref="paper",
                x=0.01, y=y_sep1 - 0.008,
                xanchor="left", yanchor="top",
                font=dict(color=rsi_label_col, size=10, family="JetBrains Mono"),
                showarrow=False,
                bgcolor=rsi_label_bg,
                bordercolor=rsi_label_col,
                borderwidth=1,
                borderpad=4,
                opacity=0.92,
            ),
            dict(
                text="<b>MACD</b>",
                xref="paper", yref="paper",
                x=0.01, y=y_sep2 - 0.008,
                xanchor="left", yanchor="top",
                font=dict(color=macd_label_col, size=10, family="JetBrains Mono"),
                showarrow=False,
                bgcolor=macd_label_bg,
                bordercolor=macd_label_col,
                borderwidth=1,
                borderpad=4,
                opacity=0.92,
            ),
        ],
        # ── Separadores y fondos de paneles ───────────────────────────────
        shapes=[
            # Línea separadora superior (Velas / RSI) — sólida y visible
            dict(
                type="line", xref="paper", x0=0, x1=1,
                yref="paper", y0=y_sep1, y1=y_sep1,
                line=dict(color=sep_col, width=1.5),
            ),
            # Línea separadora inferior (RSI / MACD)
            dict(
                type="line", xref="paper", x0=0, x1=1,
                yref="paper", y0=y_sep2, y1=y_sep2,
                line=dict(color=sep_col, width=1.5),
            ),
            # Fondo del panel RSI
            dict(
                type="rect", xref="paper", x0=0, x1=1,
                yref="paper", y0=y_sep2, y1=y_sep1,
                fillcolor=bg_rsi, line_width=0, layer="below",
            ),
            # Fondo del panel MACD
            dict(
                type="rect", xref="paper", x0=0, x1=1,
                yref="paper", y0=0, y1=y_sep2,
                fillcolor=bg_macd, line_width=0, layer="below",
            ),
        ],
    )
    fig.update_layout(**layout)
    return fig


def render_live_analysis():
    user    = st.session_state.user
    user_id = user.get("id") or user.get("user_id")
    c    = get_colors()
    dark = get_theme() == "dark"

    page_header("📡", "Análisis en Vivo",
                "Smart Money Concepts · Order Blocks · FVG · Liquidez")
    if mercado_cerrado():
        st.warning("🔒 **Mercado cerrado — Fin de semana.** Los datos mostrados corresponden al último cierre del viernes. Reapertura: Domingo 16:00 CDMX.")
    _render_news_banner(dark, c)
    inject_module_css(dark)

    # Capital se administra en Configuración de cuenta (dashboard)
    capital = int(user.get("capital_inicial", 1000))

    # Riesgo % se carga desde bot_config al iniciar sesión y se guarda al cambiar
    if "rsk_live" not in st.session_state:
        cfg_db = obtener_bot_config(user_id) if user_id else {}
        st.session_state["rsk_live"] = float(cfg_db.get("riesgo_pct") or 1.0)

    def _guardar_riesgo():
        if user_id:
            actualizar_bot_config(user_id, riesgo_pct=st.session_state["rsk_live"])

    col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1.5])
    with col1:
        categoria = st.selectbox("Categoría", list(ACTIVOS_DEFAULT.keys()), key="cat_live")
    with col2:
        ticker = st.selectbox("Activo", ACTIVOS_DEFAULT[categoria], key="ticker_live")
    with col3:
        tf = st.selectbox("Temporalidad", list(TIMEFRAME_LABELS.keys()),
                          format_func=lambda x: TIMEFRAME_LABELS[x], index=2, key="tf_live")
    with col4:
        st.number_input("Capital USD", value=capital, min_value=100, step=500,
                        format="%d", disabled=True)
    with col5:
        riesgo_pct = st.number_input("Riesgo %", min_value=0.1, max_value=5.0,
                                     step=0.1, key="rsk_live", on_change=_guardar_riesgo)

    actualizar = st.button("🔄 Actualizar análisis", key="btn_actualizar_live",
                           type="primary", use_container_width=False)

    if actualizar:
        st.session_state["_live_actualizar"] = True
        oram_bienvenida(
            titulo="🔄 Analizando mercado",
            subtitulo=f"Descargando datos de {ticker} · {TIMEFRAME_LABELS.get(tf, tf)}",
            spinner_label="Actualizando análisis…", delay=2.0)

    forzar    = st.session_state.pop("_live_actualizar", False)
    theme_key = get_theme()
    cache_key = f"df_{ticker}_{tf}_{theme_key}"
    if cache_key not in st.session_state or forzar:
        with st.spinner(f"Descargando {ticker} ({TIMEFRAME_LABELS[tf]})..."):
            df, status_msg = obtener_datos(ticker, tf)
            st.session_state[cache_key] = (df, status_msg)
    else:
        df, status_msg = st.session_state[cache_key]

    if   "✅" in status_msg: st.success(status_msg)
    elif "⚠️" in status_msg: st.warning(status_msg)
    else:                     st.error(status_msg)

    if df is None:
        st.info("No se pudieron obtener datos. Verifica el ticker.")
        return

    smc = analisis_completo(df, ticker)

    # Gráfica — el estilo premium (borde, bg, shadow) lo aplica el CSS en styles.py
    # directamente sobre .element-container:has([data-testid="stPlotlyChart"])
    # Sin div wrapper HTML para evitar el elemento en blanco entre alert y gráfica
    st.plotly_chart(_grafica_velas(df, ticker, smc), use_container_width=True)

    precio    = smc.get("precio", 0)
    atr       = smc.get("atr", 0)
    rsi       = smc.get("rsi")
    est       = smc.get("estructura", {})
    conf      = smc.get("confluencia", {})
    tipo      = est.get("tipo", "Sin señal")
    confianza = conf.get("confianza", 0)
    factores  = conf.get("factores", [])

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Precio", f"{precio:.5f}")
    m2.metric("ATR", f"{atr:.5f}")
    m3.metric("RSI", f"{rsi:.1f}" if rsi else "—",
              delta=("Sobrecomprado" if rsi and rsi > 70
                     else "Sobrevendido" if rsi and rsi < 30 else "Neutral"))
    m4.metric("Señal", tipo if tipo != "Sin señal" else "Rango")
    m5.metric("Confianza", f"{confianza:.0f}%")

    st.markdown("")
    # ── Layout: Señal | Niveles (3 cards apiladas) | Riesgo ─────────────────────
    # col_niveles contiene Order Blocks, Fair Value Gaps y Zonas de Liquidez
    # apiladas verticalmente como cards premium, en orden:
    #   1. Order Blocks  2. Fair Value Gaps  3. Zonas de Liquidez  4. SL/TP
    col_senal, col_niveles, col_riesgo = st.columns([2, 2, 1])

    with col_senal:
        # ── Card 1: Estructura BOS/CHoCH ──────────────────────────────────────
        if "Alcista" in tipo or "LONG" in tipo:
            struct_border = "oram-card-green"
            struct_icon   = "🟢"
        elif "Bajista" in tipo or "SHORT" in tipo:
            struct_border = "oram-card-red"
            struct_icon   = "🔴"
        else:
            struct_border = "oram-card-gold"
            struct_icon   = "⚪"

        conf_bar_w  = int(min(confianza, 100))
        conf_color  = c["green"] if confianza >= 65 else (c["accent"] if confianza >= 40 else c["red"])
        struct_desc = est.get("descripcion", "")

        st.markdown(
            f'<div class="oram-card {struct_border}">'
            f'<div class="card-title">{struct_icon} {tipo}</div>'
            f'<div class="card-sub" style="margin-bottom:0.5rem">{struct_desc}</div>'
            f'<div style="height:4px;background:{c["border"]};border-radius:2px;overflow:hidden;margin-bottom:0.3rem">'
            f'<div style="width:{conf_bar_w}%;height:100%;background:{conf_color};border-radius:2px"></div>'
            f'</div>'
            f'<div class="card-sub">Confianza: <b style="color:{conf_color}">{confianza:.0f}%</b></div>'
            f'</div>',
            unsafe_allow_html=True)

        # ── Card 2: Señal de trading ───────────────────────────────────────────
        tipo_entrada    = smc.get("tipo_entrada", "mercado")
        entrada_ideal   = smc.get("precio_entrada_ideal")
        retroceso_pips  = smc.get("retroceso_pips", 0)

        if "Alcista" in tipo or "LONG" in tipo:
            senal_border = "oram-card-green"
            senal_txt    = "✅ SEÑAL: COMPRA (LONG)"
            if tipo_entrada == "limite_ob" and entrada_ideal:
                senal_sub = f"🎯 Orden límite en OB: <b>{entrada_ideal:.5f}</b> (~{retroceso_pips:.0f} pips de retroceso)"
            elif tipo_entrada == "limite_fvg" and entrada_ideal:
                senal_sub = f"🎯 Orden límite en FVG: <b>{entrada_ideal:.5f}</b> (~{retroceso_pips:.0f} pips de retroceso)"
            else:
                senal_sub = "✅ Precio en zona — entrada a mercado válida."
        elif "Bajista" in tipo or "SHORT" in tipo:
            senal_border = "oram-card-red"
            senal_txt    = "❌ SEÑAL: VENTA (SHORT)"
            if tipo_entrada == "limite_ob" and entrada_ideal:
                senal_sub = f"🎯 Orden límite en OB: <b>{entrada_ideal:.5f}</b> (~{retroceso_pips:.0f} pips de retroceso)"
            elif tipo_entrada == "limite_fvg" and entrada_ideal:
                senal_sub = f"🎯 Orden límite en FVG: <b>{entrada_ideal:.5f}</b> (~{retroceso_pips:.0f} pips de retroceso)"
            else:
                senal_sub = "✅ Precio en zona — entrada a mercado válida."
        else:
            senal_border = "oram-card-gold"
            senal_txt    = "⚠️ ESPERA / RANGO"
            senal_sub    = "Sin tendencia clara definida."

        st.markdown(
            f'<div class="oram-card {senal_border}">'
            f'<div class="card-title">{senal_txt}</div>'
            f'<div class="card-sub">{senal_sub}</div>'
            f'</div>',
            unsafe_allow_html=True)

        # ── Card 3: Confluencias ───────────────────────────────────────────────
        if factores:
            factores_html = "".join(
                f'<div class="card-sub">&#10003; {f}</div>'
                for f in factores
            )
            st.markdown(
                f'<div class="oram-card oram-card-blue">'
                f'<div class="card-title">Confluencias ({conf.get("score",0)}/{conf.get("max",8)})</div>'
                f'{factores_html}'
                f'</div>',
                unsafe_allow_html=True)
    with col_niveles:
        obs  = smc.get("order_blocks", [])
        fvgs = smc.get("fvgs", [])
        liq  = smc.get("liquidez", {})

        # ── Card 1: Order Blocks ──────────────────────────────────────────────
        obs_items = "".join(
            f'<div style="margin-bottom:0.28rem">'
            f'<span class="level-badge {"badge-ob-bull" if ob.tipo == "OB_alcista" else "badge-ob-bear"}">'
            f'{"OB↑" if ob.tipo == "OB_alcista" else "OB↓"} {ob.precio_bot:.5f}–{ob.precio_top:.5f}'
            f'</span></div>'
            for ob in obs[:5]
        ) if obs else '<div class="card-sub">Sin OBs detectados.</div>'
        st.markdown(
            f'<div class="oram-card oram-card-red">'
            f'<div class="card-title">&#129523; Order Blocks</div>'
            f'{obs_items}</div>',
            unsafe_allow_html=True)

        # ── Card 2: Fair Value Gaps ───────────────────────────────────────────
        fvg_items = "".join(
            f'<div style="margin-bottom:0.28rem">'
            f'<span class="level-badge {"badge-fvg-bull" if fvg.tipo == "FVG_alcista" else "badge-fvg-bear"}">'
            f'{"FVG↑" if fvg.tipo == "FVG_alcista" else "FVG↓"} {fvg.precio_bot:.5f}–{fvg.precio_top:.5f}'
            f'</span></div>'
            for fvg in fvgs[:5]
        ) if fvgs else '<div class="card-sub">Sin FVGs activos.</div>'
        st.markdown(
            f'<div class="oram-card oram-card-blue">'
            f'<div class="card-title">&#9889; Fair Value Gaps</div>'
            f'{fvg_items}</div>',
            unsafe_allow_html=True)

        # ── Card 3: Zonas de Liquidez ─────────────────────────────────────────
        liq_items = ""
        for lvl in liq.get("resistance_levels", [])[:3]:
            liq_items += f'<div style="margin-bottom:0.28rem"><span class="level-badge badge-ob-bear">Res {lvl:.5f}</span></div>'
        for lvl in liq.get("support_levels", [])[:3]:
            liq_items += f'<div style="margin-bottom:0.28rem"><span class="level-badge badge-ob-bull">Sop {lvl:.5f}</span></div>'
        if liq.get("equal_highs"):
            liq_items += '<div style="margin-bottom:0.28rem"><span class="level-badge badge-fvg-bear">&#9888;&#65039; Equal Highs</span></div>'
        if liq.get("equal_lows"):
            liq_items += '<div style="margin-bottom:0.28rem"><span class="level-badge badge-fvg-bull">&#9888;&#65039; Equal Lows</span></div>'
        if not liq_items:
            liq_items = '<div class="card-sub">Sin zonas detectadas.</div>'
        st.markdown(
            f'<div class="oram-card oram-card-teal">'
            f'<div class="card-title">&#128167; Zonas de Liquidez</div>'
            f'{liq_items}</div>',
            unsafe_allow_html=True)

    with col_riesgo:
        sl_s = smc.get("sl_sugerido", 0)
        tp_s = smc.get("tp_sugerido", 0)
        if sl_s and tp_s:
            st.markdown(
                f'<div class="oram-card oram-card-blue">'
                f'<div class="card-title">SL / TP sugeridos</div>'
                f'<div class="card-sub">&#129001; TP: <b>{tp_s:.5f}</b></div>'
                f'<div class="card-sub">&#128308; SL: <b>{sl_s:.5f}</b></div>'
                f'</div>', unsafe_allow_html=True)
            risk = calcular_riesgo(precio, sl_s, tp_s, capital, riesgo_pct)
            if risk:
                st.markdown(
                    f'<div class="oram-card oram-card-gold">'
                    f'<div class="card-title">Gesti&oacute;n de Riesgo</div>'
                    f'<div class="card-sub">Riesgo: <b>${risk["riesgo_usd"]}</b></div>'
                    f'<div class="card-sub">RR: <b>{risk["rr"]}:1</b></div>'
                    f'<div class="card-sub">Ganancia pot: <b>${risk["ganancia_pot"]}</b></div>'
                    f'<div class="card-sub">Lote: <b>{risk["lot_size"]}</b></div>'
                    f'</div>', unsafe_allow_html=True)
