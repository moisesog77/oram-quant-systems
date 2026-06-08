"""
utils/backtesting.py — ORAM Quant Systems — Motor de Backtesting SMC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ejecuta backtesting de la estrategia SMC sobre datos históricos reales.

Algoritmo (ventana deslizante):
  1. Descarga datos vía obtener_datos() (yfinance)
  2. Itera vela por vela con ventana de 80 velas para analisis_completo()
  3. Filtra señales por umbral de confianza y dirección no neutral
  4. Simula SL=1.5×ATR, TP=3×ATR sobre las próximas 25 velas
  5. Acumula equity y métricas (win rate, profit factor, Sharpe, drawdown)

Función pública:
  ejecutar_backtest(ticker, timeframe, riesgo_pct, umbral_confianza, capital)
  → dict con métricas, equity_curve, lista de trades y parámetros usados

Nota: los resultados son orientativos (sin spread ni slippage).
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from utils.market_data import obtener_datos
from utils.smc_engine  import analisis_completo
from utils.ai_engine   import calcular_drawdown, calcular_sharpe


@dataclass
class TradeBacktest:
    idx_entrada: int
    fecha:       str
    direccion:   str
    entrada:     float
    sl:          float
    tp:          float
    resultado:   float = 0.0
    gano:        bool  = False
    tipo:        str   = ""
    confianza:   float = 0.0


def _calcular_resultado(direccion, entrada, sl, tp, df_futuro):
    dist_sl = abs(entrada - sl)
    dist_tp = abs(tp - entrada)
    rr = dist_tp / dist_sl if dist_sl > 0 else 0
    for _, row in df_futuro.iterrows():
        if direccion == "LONG":
            if row["Low"]  <= sl: return -1.0, False
            if row["High"] >= tp: return  rr,  True
        else:
            if row["High"] >= sl: return -1.0, False
            if row["Low"]  <= tp: return  rr,  True
    return 0.0, False


def ejecutar_backtest(ticker: str, timeframe: str = "15m",
                      riesgo_pct: float = 1.0,
                      umbral_confianza: float = 50.0,
                      capital_inicial: float = 10000.0) -> dict:
    """
    Ejecuta backtest SMC sobre datos históricos de yfinance.
    Ventana deslizante de 80 velas para análisis SMC.
    """
    df_full, status = obtener_datos(ticker, timeframe)
    if df_full is None:
        return {"error": f"No se pudieron obtener datos: {status}"}
    if len(df_full) < 100:
        return {"error": f"Datos insuficientes para backtest: solo {len(df_full)} velas. Usa un timeframe con más historia (1h, 4h, 1d)."}

    trades: list[TradeBacktest] = []
    equity  = [capital_inicial]
    capital = capital_inicial
    ventana = 80   # velas para análisis SMC (ampliada de 60 a 80)

    señales_analizadas = 0
    señales_filtradas  = 0

    for i in range(ventana, len(df_full) - 15):
        df_ventana = df_full.iloc[i - ventana: i].copy()
        smc = analisis_completo(df_ventana, ticker)

        if "error" in smc:
            continue

        conf  = smc.get("confluencia", {}).get("confianza", 0)
        dir_  = smc.get("estructura",  {}).get("direccion", "neutral")
        tipo  = smc.get("estructura",  {}).get("tipo", "")
        precio = float(df_full["Close"].iloc[i])
        atr   = float(df_full["ATR"].iloc[i]) if "ATR" in df_full.columns else precio * 0.001

        señales_analizadas += 1

        if dir_ == "neutral":
            continue

        señales_filtradas += 1

        if conf < umbral_confianza:
            continue

        sl = precio - atr * 1.5 if dir_ == "LONG" else precio + atr * 1.5
        tp = precio + atr * 3.0 if dir_ == "LONG" else precio - atr * 3.0

        df_futuro = df_full.iloc[i + 1: i + 25]
        resultado_r, gano = _calcular_resultado(dir_, precio, sl, tp, df_futuro)

        riesgo_usd    = capital * (riesgo_pct / 100)
        resultado_usd = riesgo_usd * resultado_r

        capital += resultado_usd
        equity.append(round(capital, 2))

        trades.append(TradeBacktest(
            idx_entrada=i,
            fecha=str(df_full.index[i])[:16],
            direccion=dir_,
            entrada=round(precio, 5),
            sl=round(sl, 5),
            tp=round(tp, 5),
            resultado=round(resultado_r, 2),
            gano=gano,
            tipo=tipo,
            confianza=conf,
        ))

    # Diagnóstico cuando no hay trades
    if not trades:
        if señales_filtradas == 0:
            msg = (f"Sin señales direccionales en {len(df_full)} velas. "
                   f"El mercado estaba mayormente en rango. "
                   f"Prueba con otro activo o timeframe.")
        else:
            msg = (f"Se analizaron {señales_filtradas} señales direccionales pero ninguna "
                   f"superó el umbral de confianza del {umbral_confianza:.0f}%. "
                   f"Intenta bajar el umbral a 40-50%.")
        return {"error": msg}

    # ── Métricas ───────────────────────────────────────────────────────────
    total      = len(trades)
    ganadores  = [t for t in trades if t.gano]
    perdedores = [t for t in trades if not t.gano and t.resultado != 0]

    win_rate      = len(ganadores) / total * 100 if total > 0 else 0
    gross_profit  = sum(t.resultado for t in ganadores)
    gross_loss    = abs(sum(t.resultado for t in perdedores))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    total_r       = sum(t.resultado for t in trades)
    total_usd     = capital - capital_inicial

    pnl_series = pd.Series([t.resultado * capital_inicial * riesgo_pct / 100 for t in trades])
    dd_data    = calcular_drawdown(pnl_series)
    sharpe     = calcular_sharpe(pnl_series)

    avg_win    = np.mean([t.resultado for t in ganadores]) if ganadores else 0
    avg_loss   = abs(np.mean([t.resultado for t in perdedores])) if perdedores else 0
    expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)

    por_tipo = {}
    for t in trades:
        if t.tipo not in por_tipo:
            por_tipo[t.tipo] = {"total": 0, "ganados": 0}
        por_tipo[t.tipo]["total"] += 1
        if t.gano:
            por_tipo[t.tipo]["ganados"] += 1

    return {
        "ticker":        ticker,
        "timeframe":     timeframe,
        "fecha_inicio":  trades[0].fecha if trades else "",
        "fecha_fin":     trades[-1].fecha if trades else "",
        "total_trades":  total,
        "señales_analizadas": señales_analizadas,
        "win_rate":      round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "total_r":       round(total_r, 2),
        "total_pnl":     round(total_usd, 2),
        "max_drawdown":  round(dd_data["max_drawdown"], 2),
        "sharpe":        sharpe,
        "expectancy_r":  round(expectancy, 3),
        "capital_final": round(capital, 2),
        "equity_curve":  equity,
        "por_tipo":      por_tipo,
        "trades":        [
            {"fecha": t.fecha, "direccion": t.direccion,
             "entrada": t.entrada, "sl": t.sl, "tp": t.tp,
             "resultado_r": t.resultado, "gano": t.gano,
             "tipo": t.tipo, "confianza": t.confianza}
            for t in trades
        ],
        "parametros": {
            "umbral_confianza": umbral_confianza,
            "riesgo_pct":       riesgo_pct,
            "capital_inicial":  capital_inicial,
        },
    }
