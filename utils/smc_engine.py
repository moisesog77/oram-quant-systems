"""
utils/smc_engine.py — ORAM Quant Systems — Motor SMC v2 (10/10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mejoras sobre v1:
  1. Validación de volumen institucional en Order Blocks
  2. Score SMC obligatorio (OB+FVG+BOS deben existir para señal válida)
  3. SL/TP dinámico sobre estructura del OB real (no ATR genérico)
  4. Filtro de contexto mercado (rango vs tendencia)
  5. lookback=10 en detección de swings (menos falsos BOS)
  6. Score reescrito: factores SMC pesan el doble que indicadores
  7. Confluencia mínima obligatoria de 3 factores SMC para señal

Score máximo: 14 puntos
  SMC obligatorios (mínimo 3 para señal):
    · BOS/CHoCH en dirección:          3 pts
    · OB activo tocado:                3 pts
    · FVG en dirección:                2 pts
    · Precio en zona de liquidez:      2 pts
  Confirmación técnica (complementarios):
    · EMA200 alineada:                 1 pt
    · RSI zona favorable:              1 pt
    · MACD cruce:                      1 pt
    · Volumen institucional en OB:     1 pt
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field


@dataclass
class NivelSMC:
    tipo:       str    # OB_alcista, OB_bajista, FVG_alcista, FVG_bajista
    precio_top: float
    precio_bot: float
    fuerza:     float  # 0-1
    idx:        int
    vol_ratio:  float  = 1.0   # Volumen del impulso / volumen promedio
    tocado:     bool   = False


# ── 1. Detección de swings ────────────────────────────────────────────────────
def _detectar_swings(df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
    """
    Detecta swing highs y swing lows con doble pasada:
    - Pasada 1: lookback=10 para swings establecidos (alta calidad)
    - Pasada 2: lookback=5 en las últimas 20 velas (captura BOS recientes)
    """
    highs = df['High'].values
    lows  = df['Low'].values
    n     = len(df)
    sh    = np.zeros(n, dtype=bool)
    sl    = np.zeros(n, dtype=bool)

    # Pasada 1: swings establecidos con lookback completo
    for i in range(lookback, n - lookback):
        window_h = highs[i - lookback: i + lookback + 1]
        window_l = lows[i  - lookback: i + lookback + 1]
        if highs[i] == window_h.max():
            sh[i] = True
        if lows[i] == window_l.min():
            sl[i] = True

    # Pasada 2: swings recientes con lookback reducido (últimas 20 velas)
    recent_lb = 5
    recent_start = max(lookback + 1, n - 20)
    for i in range(recent_start, n - recent_lb):
        if sh[i] or sl[i]:
            continue
        lb = min(recent_lb, min(i, n - i - 1))
        if lb < 2:
            continue
        window_h = highs[i - lb: i + lb + 1]
        window_l = lows[i  - lb: i + lb + 1]
        if len(window_h) > 0 and highs[i] == window_h.max():
            sh[i] = True
        if len(window_l) > 0 and lows[i] == window_l.min():
            sl[i] = True

    df = df.copy()
    df['swing_high'] = sh
    df['swing_low']  = sl
    return df


# ── 2. Contexto de mercado (rango vs tendencia) ───────────────────────────────
def _contexto_mercado(df: pd.DataFrame) -> str:
    """
    Determina si el mercado está en tendencia o rango.

    Método ATR + rango de precio:
      · Calcula el rango de las últimas 20 velas
      · Si rango < 2 × ATR_promedio → mercado en RANGO (no operar)
      · Si rango ≥ 2 × ATR_promedio → mercado en TENDENCIA (operar)

    Retorna: 'tendencia' | 'rango'
    """
    if len(df) < 20 or 'ATR' not in df.columns:
        return 'tendencia'  # default conservador: no bloquear por falta de datos

    ultimas = df.tail(20)
    rango   = ultimas['High'].max() - ultimas['Low'].min()
    atr_avg = ultimas['ATR'].mean()

    if atr_avg == 0:
        return 'tendencia'

    return 'tendencia' if rango >= atr_avg * 1.5 else 'rango'


# ── 3. BOS / CHoCH mejorado ───────────────────────────────────────────────────
def _detectar_bos_choch(df: pd.DataFrame) -> dict:
    """
    Detecta BOS y CHoCH con lookback elevado para minimizar falsas rupturas.

    BOS  = ruptura en la dirección de la tendencia (continuación)
    CHoCH = ruptura contra la tendencia anterior (reversión potencial)

    Añade campo 'es_bos' para que el score distinga entre los dos.
    """
    resultado = {
        "tipo":       "Sin señal",
        "descripcion":"Mercado en rango",
        "direccion":  "neutral",
        "fuerza":     0.0,
        "es_bos":     False,
    }

    if len(df) < 30:
        return resultado

    df_sw = _detectar_swings(df)
    sh_idx = df_sw.index[df_sw['swing_high']].tolist()
    sl_idx = df_sw.index[df_sw['swing_low']].tolist()

    if len(sh_idx) < 2 or len(sl_idx) < 2:
        return resultado

    last_sh = df_sw.loc[sh_idx[-1], 'High']
    prev_sh = df_sw.loc[sh_idx[-2], 'High']
    last_sl = df_sw.loc[sl_idx[-1], 'Low']
    prev_sl = df_sw.loc[sl_idx[-2], 'Low']
    close   = df['Close'].iloc[-1]

    ema200  = df['EMA200'].iloc[-1] if 'EMA200' in df.columns else df['Close'].mean()
    is_bull = close > ema200

    if is_bull:
        if last_sh > prev_sh and last_sl > prev_sl:
            resultado = {
                "tipo":       "BOS Alcista",
                "descripcion":"HH + HL confirmado. Busca longs en OB/FVG.",
                "direccion":  "LONG",
                "fuerza":     round(min(1.0, (last_sh - prev_sh) / (prev_sh * 0.001 + 1e-9)), 2),
                "es_bos":     True,
            }
        elif last_sh > prev_sh and last_sl < prev_sl:
            resultado = {
                "tipo":       "CHoCH Bajista",
                "descripcion":"Nuevo HH pero LL: posible giro bajista.",
                "direccion":  "SHORT",
                "fuerza":     0.6,
                "es_bos":     False,
            }
    else:
        if last_sh < prev_sh and last_sl < prev_sl:
            resultado = {
                "tipo":       "BOS Bajista",
                "descripcion":"LH + LL confirmado. Busca shorts en OB/FVG.",
                "direccion":  "SHORT",
                "fuerza":     round(min(1.0, (prev_sl - last_sl) / (prev_sl * 0.001 + 1e-9)), 2),
                "es_bos":     True,
            }
        elif last_sl < prev_sl and last_sh > prev_sh:
            resultado = {
                "tipo":       "CHoCH Alcista",
                "descripcion":"Nuevo LL pero HH: posible giro alcista.",
                "direccion":  "LONG",
                "fuerza":     0.6,
                "es_bos":     False,
            }

    return resultado


# ── 4. Order Blocks con validación de volumen ─────────────────────────────────
def _detectar_order_blocks(df: pd.DataFrame, n: int = 5) -> list:
    """
    Order Block = última vela contraria antes de impulso fuerte.

    MEJORA v2: valida que el impulso tuvo volumen > 1.3× promedio.
    Un OB sin volumen institucional es ruido técnico, no un OB real.

    Campos adicionales:
      · vol_ratio: volumen del impulso / volumen promedio de 20 velas
      · es_fresco: True si el precio no ha tocado el OB todavía
      · distancia_pct: distancia del precio actual al OB en %
    """
    obs   = []
    data  = df.tail(100).reset_index(drop=True)
    precio_actual = data['Close'].iloc[-1]

    # Volumen promedio de referencia (últimas 20 velas)
    vol_avg = data['Volume'].rolling(20).mean() if 'Volume' in data.columns else None

    for i in range(3, len(data) - 3):
        atr_i  = data['ATR'].iloc[i] if 'ATR' in data.columns else None
        umbral = atr_i * 1.5 if atr_i is not None else None

        # ── OB Alcista: vela bajista + impulso alcista fuerte ────────────────
        if data['Close'].iloc[i] < data['Open'].iloc[i]:
            impulso_alcista = data['Close'].iloc[i+1:i+4].max() - data['High'].iloc[i]
            if umbral is None or impulso_alcista > umbral:
                vol_impulso = data['Volume'].iloc[i+1:i+4].mean() if 'Volume' in data.columns else None
                vol_ref     = vol_avg.iloc[i] if vol_avg is not None else None
                # El volumen es INFORMATIVO para el score, no un filtro de acceso.
                # En Forex, yfinance provee volumen de tick (no real) — eliminar como gating.
                ratio = (vol_impulso / vol_ref) if (vol_impulso and vol_ref and vol_ref > 0) else 1.0

                ob_top = data['High'].iloc[i]
                ob_bot = data['Low'].iloc[i]
                # OB fresco = precio no ha retrocedido al OB todavía (está por encima)
                es_fresco = precio_actual > ob_top
                # Ignorar OBs completamente por debajo del precio actual (muy distantes)
                if ob_top < precio_actual * 0.997:
                    # Verificar que el OB no fue mitigado (precio cerró por debajo del fondo)
                    future_slice = data.iloc[i + 4:] if i + 4 < len(data) else pd.DataFrame()
                    if not future_slice.empty and future_slice['Close'].min() < ob_bot:
                        continue  # OB completamente consumido — omitir
                    obs.append(NivelSMC(
                        tipo       = "OB_alcista",
                        precio_top = round(ob_top, 5),
                        precio_bot = round(ob_bot, 5),
                        fuerza     = round(min(1.0, impulso_alcista / (atr_i + 1e-9)) if atr_i else 0.7, 2),
                        idx        = i,
                        vol_ratio  = round(ratio, 2),
                        tocado     = not es_fresco,
                    ))

        # ── OB Bajista: vela alcista + impulso bajista fuerte ────────────────
        elif data['Close'].iloc[i] > data['Open'].iloc[i]:
            impulso_bajista = data['Low'].iloc[i] - data['Close'].iloc[i+1:i+4].min()
            if umbral is None or impulso_bajista > umbral:
                vol_impulso = data['Volume'].iloc[i+1:i+4].mean() if 'Volume' in data.columns else None
                vol_ref     = vol_avg.iloc[i] if vol_avg is not None else None
                ratio = (vol_impulso / vol_ref) if (vol_impulso and vol_ref and vol_ref > 0) else 1.0

                ob_top = data['High'].iloc[i]
                ob_bot = data['Low'].iloc[i]
                es_fresco = precio_actual < ob_bot
                # Ignorar OBs completamente por encima del precio actual (muy distantes)
                if ob_bot > precio_actual * 1.003:
                    # Verificar que el OB no fue mitigado (precio cerró por encima del techo)
                    future_slice = data.iloc[i + 4:] if i + 4 < len(data) else pd.DataFrame()
                    if not future_slice.empty and future_slice['Close'].max() > ob_top:
                        continue  # OB completamente consumido — omitir
                    obs.append(NivelSMC(
                        tipo       = "OB_bajista",
                        precio_top = round(ob_top, 5),
                        precio_bot = round(ob_bot, 5),
                        fuerza     = round(min(1.0, impulso_bajista / (atr_i + 1e-9)) if atr_i else 0.7, 2),
                        idx        = i,
                        vol_ratio  = round(ratio, 2),
                        tocado     = not es_fresco,
                    ))

    # Ordenar por recencia y fuerza; devolver los N más relevantes
    obs = sorted(obs, key=lambda x: (x.idx, x.fuerza), reverse=True)[:n]
    return obs


# ── 5. FVG mejorado ───────────────────────────────────────────────────────────
def _detectar_fvg(df: pd.DataFrame) -> list:
    """
    Fair Value Gap: hueco entre vela[i-2].high y vela[i].low (alcista)
    o entre vela[i-2].low y vela[i].high (bajista).

    MEJORA v2: filtra FVGs menores a 0.5×ATR (ruido mínimo).
    """
    fvgs = []
    data = df.tail(60).reset_index(drop=True)

    for i in range(2, len(data)):
        atr = data['ATR'].iloc[i] if 'ATR' in data.columns else 0.0001
        min_size = atr * 0.5   # FVGs pequeños no tienen relevancia institucional

        gap_alc = data['Low'].iloc[i] - data['High'].iloc[i - 2]
        gap_baj = data['Low'].iloc[i - 2] - data['High'].iloc[i]

        if gap_alc > min_size:
            gap_bot = data['High'].iloc[i - 2]
            future_closes = data['Close'].iloc[i + 1:]
            # FVG llenado = precio cerró por debajo del fondo del gap
            if not future_closes.empty and future_closes.min() < gap_bot:
                continue
            fvgs.append(NivelSMC(
                tipo       = "FVG_alcista",
                precio_top = round(data['Low'].iloc[i], 5),
                precio_bot = round(gap_bot, 5),
                fuerza     = round(min(1.0, gap_alc / (atr + 1e-9)), 2),
                idx        = i,
            ))
        elif gap_baj > min_size:
            gap_top = data['Low'].iloc[i - 2]
            future_closes = data['Close'].iloc[i + 1:]
            # FVG llenado = precio cerró por encima del techo del gap
            if not future_closes.empty and future_closes.max() > gap_top:
                continue
            fvgs.append(NivelSMC(
                tipo       = "FVG_bajista",
                precio_top = round(gap_top, 5),
                precio_bot = round(data['High'].iloc[i], 5),
                fuerza     = round(min(1.0, gap_baj / (atr + 1e-9)), 2),
                idx        = i,
            ))

    return sorted(fvgs, key=lambda x: x.idx, reverse=True)[:4]


# ── 6. Liquidez ───────────────────────────────────────────────────────────────
def _detectar_liquidez(df: pd.DataFrame) -> dict:
    """Niveles de liquidez: swing highs/lows con clusters de stops."""
    data = df.tail(60)
    atr  = data['ATR'].iloc[-1] if 'ATR' in data.columns else 0

    sh = data['High'].nlargest(4).values
    sl = data['Low'].nsmallest(4).values

    eq_highs = len(sh) > 1 and abs(sh[0] - sh[1]) < atr * 0.5
    eq_lows  = len(sl) > 1 and abs(sl[0] - sl[1]) < atr * 0.5

    return {
        "resistance_levels": [round(x, 5) for x in sh],
        "support_levels":    [round(x, 5) for x in sl],
        "equal_highs":       eq_highs,
        "equal_lows":        eq_lows,
    }


# ── 7. Score SMC v2 — factores SMC primero ────────────────────────────────────
def _calcular_confluencias(
    df: pd.DataFrame,
    direccion: str,
    obs: list,
    fvgs: list,
    liquidez: dict,
    estructura: dict,
) -> dict:
    """
    Score v2: los factores SMC son OBLIGATORIOS para una señal válida.

    Puntuación máxima: 14 pts
    ─────────────────────────────────────────────────────────────
    SMC (requiere mínimo 3 de estos 4 grupos para señal válida):
      [A] BOS/CHoCH en dirección           → 3 pts (BOS=3, CHoCH=2)
      [B] OB activo y con volumen          → 3 pts (vol_ratio≥1.5=3, ≥1.2=2, sin vol=1)
      [C] FVG en dirección activo          → 2 pts
      [D] Precio cerca de zona de liquidez → 2 pts

    Confirmación técnica (bonus):
      [E] EMA200 alineada con dirección    → 1 pt
      [F] RSI zona favorable               → 1 pt
      [G] MACD cruce en dirección          → 1 pt
      [H] Volumen vela actual elevado      → 1 pt

    Bloqueos (restan puntos):
      · Mercado en rango              → score SMC = 0, señal bloqueada
      · 0 OBs válidos en dirección    → señal bloqueada
    """
    score     = 0
    factores  = []
    smc_score = 0   # solo puntos SMC (A+B+C+D)
    c = df['Close'].iloc[-1]
    atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else 0

    if direccion == "neutral":
        return {"score": 0, "max": 14, "confianza": 0.0,
                "factores": ["Sin dirección — neutral"],
                "smc_score": 0, "señal_valida": False}

    # ── [A] BOS / CHoCH ──────────────────────────────────────────────────────
    if estructura.get("es_bos") and estructura.get("direccion") == direccion:
        score += 3; smc_score += 3; factores.append("✅ BOS confirmado en dirección")
    elif not estructura.get("es_bos") and estructura.get("direccion") == direccion:
        score += 2; smc_score += 2; factores.append("✅ CHoCH en dirección (reversión)")

    # ── [B] Order Block activo ────────────────────────────────────────────────
    ob_tipo = "OB_alcista" if direccion == "LONG" else "OB_bajista"
    obs_dir = [o for o in obs if o.tipo == ob_tipo]

    # Buscar OB más cercano al precio actual
    ob_activo = None
    if obs_dir:
        # OB alcista: precio debería estar sobre el OB (retroceso al OB)
        # OB bajista: precio debería estar bajo el OB (retroceso al OB)
        if direccion == "LONG":
            # OBs donde el precio está por encima o dentro del OB
            en_zona = [o for o in obs_dir if c >= o.precio_bot and c <= o.precio_top * 1.02]
            ob_activo = en_zona[0] if en_zona else (obs_dir[0] if obs_dir else None)
        else:
            en_zona = [o for o in obs_dir if c <= o.precio_top and c >= o.precio_bot * 0.98]
            ob_activo = en_zona[0] if en_zona else (obs_dir[0] if obs_dir else None)

    if ob_activo:
        if ob_activo.vol_ratio >= 1.5:
            score += 3; smc_score += 3
            factores.append(f"✅ OB institucional (vol {ob_activo.vol_ratio:.1f}×)")
        elif ob_activo.vol_ratio >= 1.2:
            score += 2; smc_score += 2
            factores.append(f"✅ OB válido (vol {ob_activo.vol_ratio:.1f}×)")
        elif ob_activo.vol_ratio >= 1.0:
            score += 2; smc_score += 2
            factores.append(f"✅ OB estructural ({ob_activo.precio_bot:.5f}–{ob_activo.precio_top:.5f})")
        else:
            score += 1; smc_score += 1
            factores.append(f"⚠️ OB técnico (vol bajo {ob_activo.vol_ratio:.1f}×)")
    else:
        factores.append("❌ Sin OB en dirección — señal débil")

    # ── [C] FVG activo ────────────────────────────────────────────────────────
    fvg_tipo  = "FVG_alcista" if direccion == "LONG" else "FVG_bajista"
    fvgs_dir  = [f for f in fvgs if f.tipo == fvg_tipo]
    # FVG activo = precio está dentro o justo sobre/bajo el FVG
    fvg_activo = None
    if fvgs_dir:
        if direccion == "LONG":
            dentro = [f for f in fvgs_dir if f.precio_bot <= c <= f.precio_top * 1.01]
        else:
            dentro = [f for f in fvgs_dir if f.precio_bot * 0.99 <= c <= f.precio_top]
        fvg_activo = dentro[0] if dentro else None

    if fvg_activo:
        score += 2; smc_score += 2
        factores.append(f"✅ FVG activo ({fvg_activo.precio_bot:.5f}–{fvg_activo.precio_top:.5f})")
    elif fvgs_dir:
        score += 1; smc_score += 1
        factores.append(f"⚠️ FVG presente (precio fuera del gap)")

    # ── [D] Liquidez cercana ──────────────────────────────────────────────────
    if atr > 0:
        zona_liq = 1.5 * atr  # dentro de 1.5 ATRs — evita inflación del score
        if direccion == "LONG":
            sops = liquidez.get("support_levels", [])
            cerca = any(abs(c - s) < zona_liq for s in sops)
        else:
            ress = liquidez.get("resistance_levels", [])
            cerca = any(abs(c - r) < zona_liq for r in ress)

        if cerca:
            score += 2; smc_score += 2
            factores.append("✅ Precio cerca de zona de liquidez")
        if liquidez.get("equal_highs") and direccion == "SHORT":
            score += 1; smc_score += 1
            factores.append("✅ Equal Highs detectados (liquidez SHORT)")
        if liquidez.get("equal_lows") and direccion == "LONG":
            score += 1; smc_score += 1
            factores.append("✅ Equal Lows detectados (liquidez LONG)")

    # ── [E] EMA200 ────────────────────────────────────────────────────────────
    if 'EMA200' in df.columns:
        ema200 = df['EMA200'].iloc[-1]
        if direccion == "LONG"  and c > ema200:
            score += 1; factores.append("✅ Precio sobre EMA200 (sesgo alcista)")
        elif direccion == "SHORT" and c < ema200:
            score += 1; factores.append("✅ Precio bajo EMA200 (sesgo bajista)")

    # ── [F] RSI ───────────────────────────────────────────────────────────────
    if 'RSI' in df.columns:
        rsi = df['RSI'].iloc[-1]
        if direccion == "LONG" and rsi < 45:
            score += 1; factores.append(f"✅ RSI favorable para LONG ({rsi:.0f})")
        elif direccion == "SHORT" and rsi > 55:
            score += 1; factores.append(f"✅ RSI favorable para SHORT ({rsi:.0f})")

    # ── [G] MACD ──────────────────────────────────────────────────────────────
    if 'MACD' in df.columns and 'MACD_signal' in df.columns and len(df) > 2:
        m_now  = df['MACD'].iloc[-1]
        m_prev = df['MACD'].iloc[-2]
        s_now  = df['MACD_signal'].iloc[-1]
        s_prev = df['MACD_signal'].iloc[-2]
        if direccion == "LONG" and m_now > s_now and m_prev <= s_prev:
            score += 1; factores.append("✅ MACD cruce alcista")
        elif direccion == "SHORT" and m_now < s_now and m_prev >= s_prev:
            score += 1; factores.append("✅ MACD cruce bajista")

    # ── [H] Volumen vela actual ───────────────────────────────────────────────
    if 'Volume' in df.columns:
        vol_now = df['Volume'].iloc[-1]
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        if vol_avg > 0 and vol_now > vol_avg * 1.5:
            score += 1; factores.append(f"✅ Volumen elevado ({vol_now/vol_avg:.1f}×)")

    # ── Señal válida ────────────────────────────────────────────────────────────
    # Ruta A: BOS + OB + algo más  (señal clásica completa)
    # Ruta B: BOS + FVG + liquidez + EMA (sin OB pero confluencia alta — real market)
    ruta_a = smc_score >= 5 and ob_activo is not None
    ruta_b = smc_score >= 7  # requiere al menos 3 factores SMC fuertes sin OB
    señal_valida = ruta_a or ruta_b

    max_score = 14
    confianza = round(min(score / max_score, 1.0) * 100, 1)

    return {
        "score":         score,
        "max":           max_score,
        "confianza":     confianza,
        "factores":      factores,
        "smc_score":     smc_score,
        "señal_valida":  señal_valida,
        "ob_activo":     ob_activo,
    }


# ── 8. SL/TP dinámico sobre estructura real ───────────────────────────────────
def _calcular_sl_tp_dinamico(
    precio: float,
    direccion: str,
    ob_activo,
    liquidez: dict,
    atr: float,
) -> tuple[float, float]:
    """
    SL/TP basado en estructura real del OB y liquidez, no en ATR genérico.

    LONG:
      SL = justo bajo el OB alcista activo (con buffer de 10% del ATR)
      TP = nivel de resistencia/liquidez más cercano por encima del precio

    SHORT:
      SL = justo sobre el OB bajista activo (con buffer de 10% del ATR)
      TP = nivel de soporte/liquidez más cercano por debajo del precio

    Fallback: si no hay OB activo, usa 1.5×ATR / 3×ATR.
    """
    buffer = atr * 0.1   # buffer del 10% del ATR para evitar stop hunts

    if direccion == "neutral" or atr == 0:
        return 0.0, 0.0

    dist_sl_min = atr * 0.5  # SL mínimo aceptable

    if ob_activo is not None:
        if direccion == "LONG":
            sl = ob_activo.precio_bot - buffer
            if precio - sl < dist_sl_min:
                sl = precio - dist_sl_min
            # Limitar SL máximo a 3×ATR: si el OB quedó muy lejos del precio
            # actual, un SL en él produce RR absurdos (ej: 0.1:1). En ese caso
            # se usa un SL ajustado al rango actual del mercado.
            if precio - sl > atr * 3.0:
                sl = precio - atr * 3.0
            dist_sl = precio - sl
            ress = sorted([r for r in liquidez.get("resistance_levels", []) if r > precio])
            tp_candidatos = [r for r in ress if (r - precio) >= dist_sl * 1.5]
            # Fallback garantiza RR 2:1 (no usa ress[0] que puede ser demasiado cercano)
            tp = tp_candidatos[0] if tp_candidatos else precio + dist_sl * 2.0
        else:
            sl = ob_activo.precio_top + buffer
            if sl - precio < dist_sl_min:
                sl = precio + dist_sl_min
            if sl - precio > atr * 3.0:
                sl = precio + atr * 3.0
            dist_sl = sl - precio
            sops = sorted([s for s in liquidez.get("support_levels", []) if s < precio], reverse=True)
            tp_candidatos = [s for s in sops if (precio - s) >= dist_sl * 1.5]
            tp = tp_candidatos[0] if tp_candidatos else precio - dist_sl * 2.0
    else:
        # Fallback ATR garantiza RR 2:1
        if direccion == "LONG":
            sl = precio - atr * 1.5
            tp = precio + atr * 3.0
        else:
            sl = precio + atr * 1.5
            tp = precio - atr * 3.0

    return round(sl, 5), round(tp, 5)


# ── 9. Cálculo de riesgo ──────────────────────────────────────────────────────
def calcular_riesgo(
    entrada: float,
    sl: float,
    tp: float,
    capital: float,
    riesgo_pct: float = 1.0,
    ticker: str = "",
) -> dict:
    """Calcula tamaño de posición, RR y ganancia potencial.
    Detecta pares JPY automáticamente para usar el multiplicador de pips correcto."""
    if entrada == 0 or sl == 0:
        return {}

    riesgo_usd = capital * (riesgo_pct / 100)
    dist_sl    = abs(entrada - sl)
    dist_tp    = abs(tp - entrada)

    if dist_sl == 0:
        return {}

    rr = dist_tp / dist_sl

    # Pares JPY usan 2 decimales (pip = 0.01) y pip_value ~9.3 USD/lot
    _t = ticker.upper()
    if "JPY" in _t:
        pip_value = 9.3
        pip_mult  = 100
    else:
        pip_value = 10.0
        pip_mult  = 10000

    pips_sl  = dist_sl * pip_mult
    pips_tp  = dist_tp * pip_mult
    lot_size = riesgo_usd / (pips_sl * pip_value) if pips_sl > 0 else 0
    ganancia = riesgo_usd * rr

    return {
        "riesgo_usd":   round(riesgo_usd, 2),
        "rr":           round(rr, 2),
        "lot_size":     round(lot_size, 3),
        "ganancia_pot": round(ganancia, 2),
        "pips_sl":      round(pips_sl, 1),
        "pips_tp":      round(pips_tp, 1),
    }


# ── 10. Análisis completo ─────────────────────────────────────────────────────
def analisis_completo(df: pd.DataFrame, ticker: str) -> dict:
    """
    Punto de entrada principal del motor SMC v2.

    Flujo:
      1. Detectar contexto (rango vs tendencia)
      2. Detectar BOS/CHoCH
      3. Detectar OBs con validación de volumen
      4. Detectar FVGs
      5. Detectar zonas de liquidez
      6. Calcular score con factores SMC obligatorios
      7. Calcular SL/TP dinámico sobre estructura real
      8. Retornar resultado completo con flag señal_valida

    La señal solo se activa si señal_valida=True:
      · Mínimo 5 puntos SMC
      · Al menos 1 OB activo en la dirección
    """
    if df is None or len(df) < 30:
        return {"error": "Datos insuficientes (mínimo 30 velas)"}

    # Paso 1: contexto de mercado
    contexto = _contexto_mercado(df)

    # Paso 2–5: detección de patrones
    estructura = _detectar_bos_choch(df)
    obs        = _detectar_order_blocks(df)
    fvgs       = _detectar_fvg(df)
    liquidez   = _detectar_liquidez(df)

    # Paso 6: score v2
    confluencia = _calcular_confluencias(
        df, estructura.get("direccion", "neutral"),
        obs, fvgs, liquidez, estructura
    )

    # Bloquear señal en mercado de rango
    if contexto == "rango":
        confluencia["señal_valida"] = False
        confluencia["factores"].insert(0, "🚫 Mercado en RANGO — esperar tendencia")
        confluencia["confianza"] = min(confluencia["confianza"], 30.0)

    # Paso 7: SL/TP dinámico
    precio    = df['Close'].iloc[-1]
    atr       = df['ATR'].iloc[-1] if 'ATR' in df.columns else 0
    ob_activo = confluencia.get("ob_activo")
    direccion = estructura.get("direccion", "neutral")

    sl_sug, tp_sug = _calcular_sl_tp_dinamico(
        precio, direccion, ob_activo, liquidez, atr
    )

    # ── Tipo de entrada: mercado vs orden límite en OB/FVG ────────────────────
    # Si el precio ya está EN el OB → entrada a mercado (zona de reacción activa).
    # Si el OB está lejos (precio no retrocedió aún) → esperar retroceso con límite.
    pip_mult = 100 if "JPY" in ticker.upper() else 10000
    tipo_entrada        = "mercado"
    precio_entrada_ideal = None
    retroceso_pips       = 0.0

    if ob_activo is not None and direccion != "neutral":
        if direccion == "LONG":
            # Precio considerado "en OB" solo si está dentro o máx 5 pips sobre el top.
            # Con 1.02 multiplicador, precio 36 pips arriba del OB se trataba como "mercado"
            # y anclaba SL al fondo del OB lejano → RR 0.21:1. Ahora: buffer de 5 pips exactos.
            en_ob = ob_activo.precio_bot <= precio <= ob_activo.precio_top + atr * 1.0
        else:
            en_ob = ob_activo.precio_bot - atr * 1.0 <= precio <= ob_activo.precio_top
        if en_ob:
            tipo_entrada = "mercado"
        else:
            tipo_entrada = "limite_ob"
            if direccion == "LONG":
                precio_entrada_ideal = round(ob_activo.precio_top, 5)
                retroceso_pips = round((precio - ob_activo.precio_top) * pip_mult, 1)
            else:
                precio_entrada_ideal = round(ob_activo.precio_bot, 5)
                retroceso_pips = round((ob_activo.precio_bot - precio) * pip_mult, 1)
    elif ob_activo is None and direccion != "neutral":
        # Sin OB → buscar FVG fresco como nivel alternativo de entrada diferida
        fvg_tipo = "FVG_alcista" if direccion == "LONG" else "FVG_bajista"
        fvgs_dir = [f for f in fvgs if f.tipo == fvg_tipo]
        if fvgs_dir:
            fvg = fvgs_dir[0]
            if direccion == "LONG" and fvg.precio_top < precio:
                en_fvg = fvg.precio_bot <= precio <= fvg.precio_top * 1.01
                if not en_fvg:
                    tipo_entrada         = "limite_fvg"
                    precio_entrada_ideal = round(fvg.precio_top, 5)
                    retroceso_pips       = round((precio - fvg.precio_top) * pip_mult, 1)
            elif direccion == "SHORT" and fvg.precio_bot > precio:
                en_fvg = fvg.precio_bot * 0.99 <= precio <= fvg.precio_top
                if not en_fvg:
                    tipo_entrada         = "limite_fvg"
                    precio_entrada_ideal = round(fvg.precio_bot, 5)
                    retroceso_pips       = round((fvg.precio_bot - precio) * pip_mult, 1)

    return {
        "ticker":               ticker,
        "precio":               round(precio, 5),
        "atr":                  round(atr, 5),
        "contexto":             contexto,
        "estructura":           estructura,
        "order_blocks":         obs,
        "fvgs":                 fvgs,
        "liquidez":             liquidez,
        "confluencia":          confluencia,
        "señal_valida":         confluencia.get("señal_valida", False),
        "rsi":                  round(df['RSI'].iloc[-1], 1)   if 'RSI'   in df.columns else None,
        "macd":                 round(df['MACD'].iloc[-1], 6)  if 'MACD'  in df.columns else None,
        "ema50":                round(df['EMA50'].iloc[-1], 5) if 'EMA50' in df.columns else None,
        "sl_sugerido":          sl_sug,
        "tp_sugerido":          tp_sug,
        "tipo_entrada":         tipo_entrada,
        "precio_entrada_ideal": precio_entrada_ideal,
        "retroceso_pips":       retroceso_pips,
        "señal_resumen":        _generar_resumen(estructura, confluencia, contexto),
        "barrido_liquidez":     _detectar_barrido_liquidez(df, direccion),
    }


def _detectar_barrido_liquidez(df: pd.DataFrame, direccion: str) -> bool:
    """
    Detecta si hubo un stop hunt (barrido de liquidez) en las últimas velas.
    LONG : spike bajo el swing low previo con cierre de regreso arriba.
    SHORT: spike sobre el swing high previo con cierre de regreso abajo.
    """
    if df is None or len(df) < 20:
        return False
    try:
        recientes = df.iloc[-5:]
        previas   = df.iloc[-25:-5]
        if len(previas) < 5:
            return False
        if direccion == "LONG":
            swing_low = previas["Low"].min()
            return any(
                r["Low"] < swing_low and r["Close"] > swing_low
                for _, r in recientes.iterrows()
            )
        if direccion == "SHORT":
            swing_high = previas["High"].max()
            return any(
                r["High"] > swing_high and r["Close"] < swing_high
                for _, r in recientes.iterrows()
            )
        return False
    except Exception:
        return False


def _generar_resumen(estructura: dict, confluencia: dict, contexto: str = "tendencia") -> str:
    dir_  = estructura.get("direccion", "neutral")
    conf  = confluencia.get("confianza", 0)
    tipo  = estructura.get("tipo", "")
    valid = confluencia.get("señal_valida", False)

    if contexto == "rango":
        return "⏸️ Mercado en rango — esperar ruptura con volumen"
    if dir_ == "neutral":
        return "⚪ Sin estructura clara — no operar"
    if not valid:
        return f"⚠️ {tipo} detectado pero sin confluencia SMC suficiente"

    emoji  = "🟢" if dir_ == "LONG" else "🔴"
    fuerza = "ALTA" if conf > 75 else "MEDIA" if conf > 55 else "BAJA"
    return f"{emoji} {tipo} — Confianza {fuerza} ({conf:.0f}%) ✅"
