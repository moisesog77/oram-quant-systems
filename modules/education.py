"""
modules/education.py — ORAM Quant Systems — Guía SMC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Manual de referencia rápida de Smart Money Concepts.

Tabs (solo contenido estático, sin DB ni API):
  · 🏗️ Estructura  → BOS, CHoCH, IPDA
  · 🧱 Order Blocks → OB alcista y bajista con filtros de calidad
  · ⚡ FVG          → Fair Value Gap y regla del 50% (OTE)
  · 💧 Liquidez     → buy/sell stops, sesiones de mayor liquidez
  · 🎯 Checklist    → checklist de entrada + reglas de hierro

Módulo stateless: no requiere DB, yfinance ni ninguna API externa.
Solo usa ui.styles para page_header y get_colors.
"""
import streamlit as st
from ui.styles import get_colors, page_header


def render_education():
    page_header("📚", "Guía SMC", "Smart Money Concepts · Manual de referencia rápida")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏗️ Estructura", "🧱 Order Blocks", "⚡ FVG",
        "💧 Liquidez", "🎯 Checklist"
    ])

    with tab1:
        st.markdown("""
        <div class="smc-card smc-card-accent">
            <div class="card-title">BOS — Break of Structure</div>
            <div style="font-size:0.9rem;line-height:1.8">
            El mercado se mueve en ondas. Un <b>BOS alcista</b> ocurre cuando el precio supera
            el último swing high anterior, confirmando continuación alcista (HH + HL).<br>
            Un <b>BOS bajista</b> es lo opuesto: nuevo LL con LH.<br><br>
            <b>Regla:</b> Solo opera en la dirección del BOS. Si el BOS es alcista, busca LONGS.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="smc-card smc-card-blue">
            <div class="card-title">CHoCH — Change of Character</div>
            <div style="font-size:0.9rem;line-height:1.8">
            El CHoCH indica <b>posible reversión</b>. Ocurre cuando en tendencia alcista el precio
            rompe el último swing low (LL), o en bajista rompe el último swing high (HH).<br><br>
            <b>Regla:</b> El CHoCH es una alerta, no una entrada. Espera confirmación con OB o FVG
            en la nueva dirección.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="smc-card smc-card-blue">
            <div class="card-title">IPDA — Interbank Price Delivery Algorithm</div>
            <div style="font-size:0.9rem;line-height:1.8">
            El precio se entrega en ciclos de 20, 40 y 60 días de trading. El mercado
            alterna entre fases de <b>acumulación</b> (rango), <b>distribución</b> (impulso) y
            <b>re-distribución</b>. Identifica en qué fase estás para filtrar señales.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown("""
        <div class="smc-card smc-card-green">
            <div class="card-title">Order Block Alcista</div>
            <div style="font-size:0.9rem;line-height:1.8">
            Es la <b>última vela bajista</b> antes de un impulso alcista fuerte. Representa
            donde los market makers acumularon posiciones largas.<br><br>
            <b>Cómo usarlo:</b><br>
            1. Identifica el impulso alcista (BOS)<br>
            2. Busca la última vela bajista antes del impulso<br>
            3. Espera que el precio regrese a ese rango (mitigación)<br>
            4. Entra LONG con SL por debajo del OB<br>
            5. TP en el siguiente nivel de liquidez (swing high previo)
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="smc-card smc-card-red">
            <div class="card-title">Order Block Bajista</div>
            <div style="font-size:0.9rem;line-height:1.8">
            Es la <b>última vela alcista</b> antes de un impulso bajista fuerte.<br><br>
            <b>Filtros de calidad:</b><br>
            ✓ OB coincide con FVG (mayor probabilidad)<br>
            ✓ OB está en zona premium (por encima del 50% del rango)<br>
            ✓ El retroceso es suave (sin impulso contrario fuerte)<br>
            ✓ Hay liquidez visible arriba del OB (equal highs, stops)
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tab3:
        st.markdown("""
        <div class="smc-card smc-card-blue">
            <div class="card-title">FVG — Fair Value Gap (Imbalance)</div>
            <div style="font-size:0.9rem;line-height:1.8">
            Un FVG existe cuando hay un <b>hueco de precio</b> entre la mecha superior de
            la vela i-2 y la mecha inferior de la vela i (alcista), o viceversa (bajista).<br><br>
            <b>Por qué funciona:</b> El mercado tiende a "rellenar" estos huecos porque
            representan zonas donde no hubo negociación bilateral. Los algoritmos
            institucionales vuelven a estos niveles para ejecutar órdenes pendientes.<br><br>
            <b>Regla del 50% (OTE):</b> La zona de mayor probabilidad de reacción es el
            50% del FVG. Muchos traders usan el 0.5 del gap como entrada.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tab4:
        st.markdown("""
        <div class="smc-card smc-card-accent">
            <div class="card-title">Zonas de Liquidez — Buy Stops y Sell Stops</div>
            <div style="font-size:0.9rem;line-height:1.8">
            La liquidez son las <b>órdenes stop acumuladas</b> encima de swing highs
            (buy stops) o debajo de swing lows (sell stops).<br><br>
            <b>Concepto clave:</b> El Smart Money necesita liquidez para llenar sus posiciones.
            Por eso el precio "caza" los stops antes de moverse en la dirección real.<br><br>
            <b>Equal Highs / Equal Lows:</b> Dos o más swings al mismo nivel = trampa.
            El precio los barre antes de invertir. NO operes el breakout, espera la reversión.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="smc-card smc-card-teal">
            <div class="card-title">Sesiones de Mayor Liquidez</div>
            <div style="font-size:0.9rem;line-height:1.8">
            🟡 <b>London Open</b> (08:00–10:00 UTC): Mayor volumen, mejores setups<br>
            🟠 <b>NY Open</b> (13:30–15:30 UTC): Segundo pico, muy volátil<br>
            🔵 <b>London-NY Overlap</b> (13:00–16:00 UTC): Mejor zona del día<br>
            🔴 <b>Evitar:</b> Sesión asiática, horas antes de noticias (NFP, CPI, FOMC)
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tab5:
        c = get_colors()
        st.markdown(f"""
        <div class="smc-card smc-card-green">
            <div class="card-title">✅ Checklist antes de entrar a un trade</div>
            <div style="font-size:0.88rem;line-height:2;color:{c['text']}">
            <b style="color:{c['text_strong']}">Estructura (obligatorio):</b><br>
            ☐ ¿El BOS confirma la dirección? (alcista = busco LONG, bajista = SHORT)<br>
            ☐ ¿Estamos en tendencia o en rango? (solo opero tendencias claras)<br><br>
            <b style="color:{c['text_strong']}">Entry (necesito al menos 2 de 3):</b><br>
            ☐ ¿Hay un Order Block en la zona de entrada?<br>
            ☐ ¿Hay un FVG coincidente con el OB?<br>
            ☐ ¿Hay liquidez visible que el precio podría cazar?<br><br>
            <b style="color:{c['text_strong']}">Gestión de riesgo (obligatorio todo):</b><br>
            ☐ Riesgo ≤ 1% del capital por trade<br>
            ☐ RR mínimo 1:2 (preferible 1:3)<br>
            ☐ SL por debajo/encima del OB o FVG (no en la mitad)<br>
            ☐ No hay noticias de alto impacto en las próximas 2 horas<br><br>
            <b style="color:{c['text_strong']}">Psicología:</b><br>
            ☐ ¿Estoy operando por setup o por FOMO/revancha?<br>
            ☐ ¿Ya perdí 2 trades hoy? → Parar el día<br>
            ☐ ¿El drawdown del día supera el 3%? → Parar el día
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="smc-card smc-card-red">
            <div class="card-title">🚫 Reglas de hierro</div>
            <div style="font-size:0.88rem;line-height:2">
            ✗ Nunca muevas el SL en contra de tu posición<br>
            ✗ Nunca promedies pérdidas (martingala = cuenta quemada)<br>
            ✗ Nunca operes los lunes antes de las 9:00 UTC (gap riesgo)<br>
            ✗ Nunca operes durante NFP, FOMC o CPI sin experiencia<br>
            ✗ Nunca arriesgues más del 5% del capital total en un solo día<br>
            ✗ Nunca entres sin SL definido
            </div>
        </div>
        """, unsafe_allow_html=True)
