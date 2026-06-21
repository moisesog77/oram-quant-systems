"""
modules/multi_tf.py — ORAM Quant Systems — Análisis Multi-Timeframe
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analiza el mismo activo en dos timeframes para confirmar dirección.

Concepto:
  TF Alto → define la estructura/dirección maestra (ej: 1H → LONG)
  TF Bajo  → busca el punto de entrada preciso (ej: 15m → BOS Alcista)
  Solo operar cuando AMBOS apuntan en la misma dirección (alineación).

Confianza MTF combinada = conf_alto × 0.6 + conf_bajo × 0.4

Combos predefinidos (utils/multi_timeframe.MTF_COMBOS):
  Scalping (5m/1m), Intraday (1h/15m), Swing (4h/1h), Posicional (1d/4h)
"""
import streamlit as st
import plotly.graph_objects as go
from utils.multi_timeframe import analisis_mtf, MTF_COMBOS
from utils.market_data import ACTIVOS_DEFAULT, obtener_datos, mercado_cerrado
from ui.styles import get_colors, page_header, signal_box, get_theme, oram_bienvenida, inject_module_css


def _mini_chart(df, tf_label, ema_col, c):
    """Crea gráfica de velas limpia para MTF."""
    df = df.tail(80)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"],  close=df["Close"],
        name=tf_label,
        increasing_line_color=c["green"],
        decreasing_line_color=c["red"],
        increasing_fillcolor="rgba(38,222,129,0.6)",
        decreasing_fillcolor="rgba(252,92,101,0.6)",
        showlegend=False,
    ))
    if ema_col in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[ema_col],
            line=dict(color=c["accent"], width=1.5),
            name=ema_col, showlegend=False,
        ))
    fig.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=c["plot_bg"],
        xaxis=dict(
            gridcolor=c["grid"], color=c["text_muted"],
            showgrid=True, rangeslider_visible=False,
            tickfont=dict(size=9),
        ),
        yaxis=dict(
            gridcolor=c["grid"], color=c["text_muted"],
            side="right", showgrid=True,
            tickfont=dict(size=9),
        ),
        font=dict(family="JetBrains Mono", size=9, color=c["text_muted"]),
    )
    return fig


def _info_card(label, smc, c):
    """Panel de información SMC para un TF."""
    if not smc or "error" in smc:
        return
    est   = smc.get("estructura", {})
    cnf   = smc.get("confluencia", {})
    dir_  = est.get("direccion", "neutral")
    tipo  = est.get("tipo", "Sin señal")
    conf  = cnf.get("confianza", 0)
    color = c["green"] if dir_ == "LONG" else c["red"] if dir_ == "SHORT" else c["accent"]
    emoji = "🟢" if dir_ == "LONG" else "🔴" if dir_ == "SHORT" else "⚪"
    factores_html = "".join([f'<div class="card-sub">✓ {f}</div>' for f in cnf.get("factores", [])])

    st.markdown(f"""
    <div class="smc-card" style="border-left:3px solid {color};margin-bottom:0.5rem">
        <div class="card-title">{label}</div>
        <div style="font-size:1rem;font-weight:700;color:{color}">{emoji} {tipo}</div>
        <div class="card-sub" style="margin-top:0.3rem">
            Precio: <b>{smc.get('precio',0):.5f}</b> &nbsp;|&nbsp;
            RSI: <b>{smc.get('rsi',0):.1f}</b> &nbsp;|&nbsp;
            ATR: <b>{smc.get('atr',0):.5f}</b>
        </div>
        <div style="margin-top:0.4rem">
            <div class="card-sub">Confianza: <b style="color:{color}">{conf:.0f}%</b></div>
            <div style="background:{c['border']};border-radius:3px;height:5px;margin-top:3px">
                <div style="background:{color};width:{min(conf,100):.0f}%;height:100%;border-radius:3px"></div>
            </div>
        </div>
        {factores_html}
    </div>
    """, unsafe_allow_html=True)



def render_multi_tf():
    c    = get_colors()
    dark = get_theme() == "dark"

    page_header("🔭", "Multi-Timeframe", "Confluencia entre TF alto (estructura) y TF bajo (entrada)")
    inject_module_css(dark)
    if mercado_cerrado():
        st.warning("🔒 **Mercado cerrado — Fin de semana.** Los datos mostrados corresponden al último cierre del viernes. Reapertura: Domingo 16:00 CDMX.")

    # ── Controles ──────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        cat    = st.selectbox("Categoría", list(ACTIVOS_DEFAULT.keys()), key="mtf_cat")
        ticker = st.selectbox("Activo",    ACTIVOS_DEFAULT[cat],          key="mtf_tk")
    with col2:
        combo  = st.selectbox("Combinación MTF", list(MTF_COMBOS.keys()), key="mtf_combo")
        tf_alto, tf_bajo = MTF_COMBOS[combo]
    with col3:
        st.markdown('<div style="margin-top:1.65rem"></div>', unsafe_allow_html=True)
        analizar = st.button("🔭 Analizar", width='stretch', key="mtf_btn")

    st.markdown(f"""
    <div class="smc-card smc-card-blue" style="padding:0.7rem 1rem;margin-bottom:1rem">
        <div class="card-sub">
        <b>TF Alto ({tf_alto})</b> → define la dirección y estructura (BOS / CHoCH) &nbsp;|&nbsp;
        <b>TF Bajo ({tf_bajo})</b> → busca la entrada en OB o FVG alineado &nbsp;|&nbsp;
        Solo operar cuando <b>ambos apuntan igual</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Análisis ───────────────────────────────────────────────────────────
    if analizar:
        st.session_state["_mtf_analizar"] = True
        oram_bienvenida(
            titulo="🔭 Analizando confluencia MTF",
            subtitulo=f"{ticker} · {tf_alto} (estructura) → {tf_bajo} (entrada)",
            spinner_label="Calculando alineación de timeframes…",
            delay=3.0,
        )

    forzar    = st.session_state.pop("_mtf_analizar", False)
    cache_key = f"mtf_{ticker}_{tf_alto}_{tf_bajo}"
    if forzar or cache_key in st.session_state:
        if forzar or cache_key not in st.session_state:
            with st.spinner(f"Analizando {ticker} en {tf_alto} y {tf_bajo}..."):
                res = analisis_mtf(ticker, tf_alto, tf_bajo)
                st.session_state[cache_key] = res
        else:
            res = st.session_state[cache_key]

        señal = res.get("señal_mtf", "")
        desc  = res.get("descripcion", "")
        conf  = res.get("confianza_mtf", 0)
        alin  = res.get("alineacion", False)

        # ── Señal MTF ──────────────────────────────────────────────────────
        st.markdown(signal_box(señal, desc, conf), unsafe_allow_html=True)

        # ── Layout: info arriba, gráficas abajo ────────────────────────────
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"**📐 {tf_alto} — Estructura**")
            _info_card(f"Timeframe Alto · {tf_alto}", res.get("smc_alto", {}), c)

        with col_b:
            st.markdown(f"**🎯 {tf_bajo} — Entrada**")
            _info_card(f"Timeframe Bajo · {tf_bajo}", res.get("smc_bajo", {}), c)
            # Niveles sugeridos si hay alineación
            if alin:
                sl = res.get("sl_sugerido")
                tp = res.get("tp_sugerido")
                en = res.get("entrada_sugerida")
                if sl and tp and en:
                    rr = abs(tp - en) / abs(en - sl) if abs(en - sl) > 0 else 0
                    color_dir = c["green"] if "LONG" in señal else c["red"]
                    st.markdown(f"""
                    <div class="smc-card smc-card-green">
                        <div class="card-title">Niveles MTF sugeridos</div>
                        <div class="card-sub">📍 Entrada: <b>{en:.5f}</b></div>
                        <div class="card-sub">🛑 SL: <b>{sl:.5f}</b></div>
                        <div class="card-sub">✅ TP: <b>{tp:.5f}</b></div>
                        <div class="card-sub">📐 RR: <b style="color:{color_dir}">{rr:.1f}:1</b></div>
                    </div>
                    """, unsafe_allow_html=True)

        st.divider()

        # ── Gráficas separadas debajo ───────────────────────────────────────
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown(f"**📊 Gráfica {tf_alto}**")
            df_a, status_a = obtener_datos(ticker, tf_alto)
            if df_a is not None:
                fig_a = _mini_chart(df_a, tf_alto, "EMA50", c)
                st.plotly_chart(fig_a, width='stretch', key=f"chart_alto_{ticker}")
            else:
                st.caption(f"Sin datos: {status_a}")

        with col_g2:
            st.markdown(f"**📊 Gráfica {tf_bajo}**")
            df_b, status_b = obtener_datos(ticker, tf_bajo)
            if df_b is not None:
                fig_b = _mini_chart(df_b, tf_bajo, "EMA20", c)
                st.plotly_chart(fig_b, width='stretch', key=f"chart_bajo_{ticker}")
            else:
                st.caption(f"Sin datos: {status_b}")

    else:
        st.info("Selecciona un activo y combinación MTF, luego haz clic en **Analizar**.")
