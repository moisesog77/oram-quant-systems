"""
utils/smc_engine.py — Motor completo de Smart Money Concepts.
Detecta: BOS, CHoCH, Order Blocks, FVG, Liquidez, IPDA.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class NivelSMC:
    tipo: str        # OB_alcista, OB_bajista, FVG_alcista, FVG_bajista, liquidity_high, liquidity_low
    precio_top: float
    precio_bot: float
    fuerza: float    # 0-1
    idx: int         # índice en el DataFrame
    tocado: bool = False


def _detectar_swings(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """Detecta swing highs y swing lows."""
    highs = df['High'].values
    lows  = df['Low'].values
    n     = len(df)
    sh    = np.zeros(n, dtype=bool)
    sl    = np.zeros(n, dtype=bool)

    for i in range(lookback, n - lookback):
        if highs[i] == max(highs[i - lookback:i + lookback + 1]):
            sh[i] = True
        if lows[i]  == min(lows[i  - lookback:i + lookback + 1]):
            sl[i] = True

    df = df.copy()
    df['swing_high'] = sh
    df['swing_low']  = sl
    return df


def _detectar_bos_choch(df: pd.DataFrame) -> dict:
    """
    Detecta Break of Structure (BOS) y Change of Character (CHoCH).
    BOS  = ruptura en dirección de la tendencia (continuación).
    CHoCH = ruptura contra la tendencia anterior (reversión).
    """
    resultado = {
        "tipo": "Sin señal",
        "descripcion": "Mercado en rango",
        "direccion": "neutral",
        "fuerza": 0.0,
    }

    if len(df) < 20:
        return resultado

    df = _detectar_swings(df)
    sh_idx = df.index[df['swing_high']].tolist()
    sl_idx = df.index[df['swing_low']].tolist()

    if len(sh_idx) < 2 or len(sl_idx) < 2:
        return resultado

    # Últimos dos swing highs y lows
    last_sh   = df.loc[sh_idx[-1], 'High']
    prev_sh   = df.loc[sh_idx[-2], 'High']
    last_sl   = df.loc[sl_idx[-1], 'Low']
    prev_sl   = df.loc[sl_idx[-2], 'Low']
    close_now = df['Close'].iloc[-1]

    ema50 = df['EMA50'].iloc[-1] if 'EMA50' in df.columns else df['Close'].mean()

    # Estructura general
    is_bullish = close_now > ema50

    if is_bullish:
        if last_sh > prev_sh and last_sl > prev_sl:
            resultado = {
                "tipo": "BOS Alcista",
                "descripcion": "Estructura alcista confirmada: HH + HL. Busca longs en OB/FVG.",
                "direccion": "LONG",
                "fuerza": min(1.0, (last_sh - prev_sh) / (prev_sh * 0.001 + 1e-9)),
            }
        elif last_sh > prev_sh and last_sl < prev_sl:
            resultado = {
                "tipo": "CHoCH Bajista",
                "descripcion": "Cambio de carácter: nuevo HH pero LL. Posible reversión bajista.",
                "direccion": "SHORT",
                "fuerza": 0.6,
            }
    else:
        if last_sh < prev_sh and last_sl < prev_sl:
            resultado = {
                "tipo": "BOS Bajista",
                "descripcion": "Estructura bajista confirmada: LH + LL. Busca shorts en OB/FVG.",
                "direccion": "SHORT",
                "fuerza": min(1.0, (prev_sl - last_sl) / (prev_sl * 0.001 + 1e-9)),
            }
        elif last_sl < prev_sl and last_sh > prev_sh:
            resultado = {
                "tipo": "CHoCH Alcista",
                "descripcion": "Cambio de carácter: nuevo LL pero HH. Posible reversión alcista.",
                "direccion": "LONG",
                "fuerza": 0.6,
            }

    resultado['fuerza'] = round(min(resultado['fuerza'], 1.0), 2)
    return resultado


def _detectar_order_blocks(df: pd.DataFrame, n: int = 5) -> list[NivelSMC]:
    """
    Order Block: última vela bajista antes de impulso alcista (OB alcista)
    o última vela alcista antes de impulso bajista (OB bajista).
    """
    obs = []
    data = df.tail(80).reset_index(drop=True)

    for i in range(2, len(data) - 3):
        # OB Alcista: vela bajista seguida de impulso alcista fuerte
        if data['Close'].iloc[i] < data['Open'].iloc[i]:  # vela bajista
            impulso = data['Close'].iloc[i+1:i+4].max() - data['High'].iloc[i]
            if impulso > data['ATR'].iloc[i] * 1.5 if 'ATR' in data.columns else True:
                obs.append(NivelSMC(
                    tipo="OB_alcista",
                    precio_top=data['High'].iloc[i],
                    precio_bot=data['Low'].iloc[i],
                    fuerza=min(1.0, impulso / (data['ATR'].iloc[i] + 1e-9)) if 'ATR' in data.columns else 0.7,
                    idx=i
                ))

        # OB Bajista: vela alcista seguida de impulso bajista fuerte
        if data['Close'].iloc[i] > data['Open'].iloc[i]:  # vela alcista
            impulso = data['Low'].iloc[i] - data['Close'].iloc[i+1:i+4].min()
            if impulso > data['ATR'].iloc[i] * 1.5 if 'ATR' in data.columns else True:
                obs.append(NivelSMC(
                    tipo="OB_bajista",
                    precio_top=data['High'].iloc[i],
                    precio_bot=data['Low'].iloc[i],
                    fuerza=min(1.0, impulso / (data['ATR'].iloc[i] + 1e-9)) if 'ATR' in data.columns else 0.7,
                    idx=i
                ))

    # Tomar los N más recientes y fuertes
    obs = sorted(obs, key=lambda x: (x.idx, x.fuerza), reverse=True)[:n]
    return obs


def _detectar_fvg(df: pd.DataFrame) -> list[NivelSMC]:
    """
    Fair Value Gap (Imbalance): hueco entre vela i-2 y vela i.
    FVG alcista: Low[i] > High[i-2]
    FVG bajista: High[i] < Low[i-2]
    """
    fvgs = []
    data = df.tail(50).reset_index(drop=True)

    for i in range(2, len(data)):
        low_now   = data['Low'].iloc[i]
        high_prev = data['High'].iloc[i - 2]
        high_now  = data['High'].iloc[i]
        low_prev  = data['Low'].iloc[i - 2]
        atr = data['ATR'].iloc[i] if 'ATR' in data.columns else 0.0001

        if low_now > high_prev and (low_now - high_prev) > atr * 0.3:
            fvgs.append(NivelSMC(
                tipo="FVG_alcista",
                precio_top=low_now,
                precio_bot=high_prev,
                fuerza=min(1.0, (low_now - high_prev) / (atr + 1e-9)),
                idx=i
            ))
        elif high_now < low_prev and (low_prev - high_now) > atr * 0.3:
            fvgs.append(NivelSMC(
                tipo="FVG_bajista",
                precio_top=low_prev,
                precio_bot=high_now,
                fuerza=min(1.0, (low_prev - high_now) / (atr + 1e-9)),
                idx=i
            ))

    return sorted(fvgs, key=lambda x: x.idx, reverse=True)[:4]


def _detectar_liquidez(df: pd.DataFrame) -> dict:
    """
    Niveles de liquidez: swing highs y lows recientes donde
    probablemente hay órdenes stop acumuladas.
    """
    data = df.tail(50)
    sh = data['High'].nlargest(3).values
    sl = data['Low'].nsmallest(3).values
    atr = data['ATR'].iloc[-1] if 'ATR' in data.columns else 0

    return {
        "resistance_levels": [round(x, 5) for x in sh],
        "support_levels":    [round(x, 5) for x in sl],
        "equal_highs": abs(sh[0] - sh[1]) < atr * 0.5 if len(sh) > 1 else False,
        "equal_lows":  abs(sl[0] - sl[1]) < atr * 0.5 if len(sl) > 1 else False,
    }


def _calcular_confluencias(df: pd.DataFrame, direccion: str) -> dict:
    """
    Cuenta confluencias alcistas/bajistas para un score de confianza.
    """
    score = 0
    factores = []
    c = df['Close'].iloc[-1]

    if 'EMA50' in df.columns and 'EMA200' in df.columns:
        if direccion == "LONG":
            if c > df['EMA50'].iloc[-1]:  score += 1; factores.append("Precio > EMA50")
            if c > df['EMA200'].iloc[-1]: score += 1; factores.append("Precio > EMA200")
            if df['EMA50'].iloc[-1] > df['EMA200'].iloc[-1]: score += 1; factores.append("EMA50 > EMA200 (Golden Cross zone)")
        else:
            if c < df['EMA50'].iloc[-1]:  score += 1; factores.append("Precio < EMA50")
            if c < df['EMA200'].iloc[-1]: score += 1; factores.append("Precio < EMA200")
            if df['EMA50'].iloc[-1] < df['EMA200'].iloc[-1]: score += 1; factores.append("EMA50 < EMA200 (Death Cross zone)")

    if 'RSI' in df.columns:
        rsi = df['RSI'].iloc[-1]
        if direccion == "LONG"  and rsi < 50: score += 1; factores.append(f"RSI neutral-bajo ({rsi:.0f})")
        if direccion == "SHORT" and rsi > 50: score += 1; factores.append(f"RSI neutral-alto ({rsi:.0f})")
        if direccion == "LONG"  and rsi < 35: score += 1; factores.append(f"RSI sobrevendido ({rsi:.0f})")
        if direccion == "SHORT" and rsi > 65: score += 1; factores.append(f"RSI sobrecomprado ({rsi:.0f})")

    if 'MACD' in df.columns and 'MACD_signal' in df.columns:
        macd_cross = (df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]) and \
                     (df['MACD'].iloc[-2] <= df['MACD_signal'].iloc[-2]) if len(df) > 2 else False
        if direccion == "LONG"  and macd_cross: score += 2; factores.append("MACD cruce alcista reciente")
        if direccion == "SHORT" and not macd_cross and df['MACD'].iloc[-1] < df['MACD_signal'].iloc[-1]:
            score += 1; factores.append("MACD por debajo de señal")

    if 'Vol_ratio' in df.columns:
        vr = df['Vol_ratio'].iloc[-1]
        if pd.notna(vr) and vr > 1.5:
            score += 1; factores.append(f"Volumen elevado ({vr:.1f}x promedio)")

    max_score = 8
    confianza = round(min(score / max_score, 1.0) * 100, 1)
    return {"score": score, "max": max_score, "confianza": confianza, "factores": factores}


def calcular_riesgo(entrada: float, sl: float, tp: float, capital: float, riesgo_pct: float = 1.0) -> dict:
    """
    Calcula el tamaño de posición y métricas de riesgo.
    """
    if entrada == 0 or sl == 0:
        return {}

    riesgo_usd   = capital * (riesgo_pct / 100)
    distancia_sl = abs(entrada - sl)
    distancia_tp = abs(tp - entrada)

    if distancia_sl == 0:
        return {}

    rr = distancia_tp / distancia_sl
    # Pip value aproximado para forex (varía por par y broker)
    pip_value    = 10.0  # USD por pip en 1 lote estándar
    pips_sl      = distancia_sl * 10000  # para pares con 4 decimales
    lot_size     = riesgo_usd / (pips_sl * pip_value) if pips_sl > 0 else 0
    ganancia_pot = riesgo_usd * rr

    return {
        "riesgo_usd":   round(riesgo_usd, 2),
        "rr":           round(rr, 2),
        "lot_size":     round(lot_size, 3),
        "ganancia_pot": round(ganancia_pot, 2),
        "pips_sl":      round(pips_sl, 1),
        "pips_tp":      round(distancia_tp * 10000, 1),
    }


def analisis_completo(df: pd.DataFrame, ticker: str) -> dict:
    """
    Análisis SMC completo. Punto de entrada principal.
    """
    if df is None or len(df) < 20:
        return {"error": "Datos insuficientes"}

    estructura  = _detectar_bos_choch(df)
    obs         = _detectar_order_blocks(df)
    fvgs        = _detectar_fvg(df)
    liquidez    = _detectar_liquidez(df)
    confluencia = _calcular_confluencias(df, estructura.get("direccion", "neutral"))

    close = df['Close'].iloc[-1]
    atr   = df['ATR'].iloc[-1] if 'ATR' in df.columns else 0

    # SL y TP sugeridos basados en ATR
    sl_dist = atr * 1.5
    tp_dist = atr * 3.0
    if estructura.get("direccion") == "LONG":
        sl_sug = close - sl_dist
        tp_sug = close + tp_dist
    else:
        sl_sug = close + sl_dist
        tp_sug = close - tp_dist

    return {
        "ticker":       ticker,
        "precio":       round(close, 5),
        "atr":          round(atr, 5),
        "estructura":   estructura,
        "order_blocks": obs,
        "fvgs":         fvgs,
        "liquidez":     liquidez,
        "confluencia":  confluencia,
        "rsi":          round(df['RSI'].iloc[-1], 1)   if 'RSI'  in df.columns else None,
        "macd":         round(df['MACD'].iloc[-1], 6)  if 'MACD' in df.columns else None,
        "ema50":        round(df['EMA50'].iloc[-1], 5) if 'EMA50' in df.columns else None,
        "sl_sugerido":  round(sl_sug, 5),
        "tp_sugerido":  round(tp_sug, 5),
        "señal_resumen": _generar_resumen(estructura, confluencia),
    }


def _generar_resumen(estructura: dict, confluencia: dict) -> str:
    dir_   = estructura.get("direccion", "neutral")
    conf   = confluencia.get("confianza", 0)
    tipo   = estructura.get("tipo", "")

    if dir_ == "neutral":
        return "⚪ Sin señal clara. Esperar mejor estructura."
    emoji = "🟢" if dir_ == "LONG" else "🔴"
    fuerza = "ALTA" if conf > 70 else "MEDIA" if conf > 40 else "BAJA"
    return f"{emoji} {tipo} — Confianza {fuerza} ({conf}%)"
