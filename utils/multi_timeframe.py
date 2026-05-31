"""
utils/multi_timeframe.py — Análisis Multi-Timeframe (MTF).
Confluencia entre timeframe alto (estructura) y bajo (entrada).
"""
import pandas as pd
from utils.market_data import obtener_datos
from utils.smc_engine  import analisis_completo

MTF_COMBOS = {
    "Scalping (5m/1m)":       ("5m",  "1m"),
    "Intraday (1h/15m)":      ("1h",  "15m"),
    "Swing (4h/1h)":          ("4h",  "1h"),
    "Posicional (1d/4h)":     ("1d",  "4h"),
}


def analisis_mtf(ticker: str, tf_alto: str, tf_bajo: str) -> dict:
    """
    Analiza el mismo activo en dos timeframes.
    El TF alto define la estructura/dirección.
    El TF bajo busca la entrada precisa.
    """
    df_alto, status_alto = obtener_datos(ticker, tf_alto)
    df_bajo, status_bajo = obtener_datos(ticker, tf_bajo)

    resultado = {
        "ticker":        ticker,
        "tf_alto":       tf_alto,
        "tf_bajo":       tf_bajo,
        "status_alto":   status_alto,
        "status_bajo":   status_bajo,
        "smc_alto":      None,
        "smc_bajo":      None,
        "alineacion":    False,
        "señal_mtf":     "Sin señal",
        "descripcion":   "",
        "confianza_mtf": 0.0,
        "entrada_sugerida": None,
        "sl_sugerido":   None,
        "tp_sugerido":   None,
    }

    if df_alto is None or df_bajo is None:
        resultado["señal_mtf"] = "Error de datos"
        return resultado

    smc_alto = analisis_completo(df_alto, ticker)
    smc_bajo = analisis_completo(df_bajo, ticker)

    resultado["smc_alto"] = smc_alto
    resultado["smc_bajo"] = smc_bajo

    dir_alto = smc_alto.get("estructura", {}).get("direccion", "neutral")
    dir_bajo = smc_bajo.get("estructura", {}).get("direccion", "neutral")
    conf_alto = smc_alto.get("confluencia", {}).get("confianza", 0)
    conf_bajo = smc_bajo.get("confluencia", {}).get("confianza", 0)

    # Alineación: ambos TF apuntan en la misma dirección
    alineados = (dir_alto != "neutral" and dir_bajo != "neutral" and dir_alto == dir_bajo)
    resultado["alineacion"] = alineados

    precio = smc_bajo.get("precio", smc_alto.get("precio", 0))
    atr_bajo = smc_bajo.get("atr", 0)

    if alineados:
        confianza_mtf = round((conf_alto * 0.6 + conf_bajo * 0.4), 1)
        resultado["confianza_mtf"] = confianza_mtf

        tipo_alto = smc_alto.get("estructura", {}).get("tipo", "")
        tipo_bajo = smc_bajo.get("estructura", {}).get("tipo", "")
        emoji = "🟢" if dir_alto == "LONG" else "🔴"

        resultado["señal_mtf"] = f"{emoji} {dir_alto} — MTF Alineado"
        resultado["descripcion"] = (
            f"{tf_alto}: {tipo_alto} ({conf_alto:.0f}%)\n"
            f"{tf_bajo}: {tipo_bajo} ({conf_bajo:.0f}%)\n"
            f"Confianza MTF combinada: {confianza_mtf:.0f}%"
        )

        if dir_alto == "LONG":
            resultado["sl_sugerido"]      = round(precio - atr_bajo * 1.5, 5)
            resultado["tp_sugerido"]      = round(precio + atr_bajo * 4.0, 5)
            resultado["entrada_sugerida"] = round(precio, 5)
        else:
            resultado["sl_sugerido"]      = round(precio + atr_bajo * 1.5, 5)
            resultado["tp_sugerido"]      = round(precio - atr_bajo * 4.0, 5)
            resultado["entrada_sugerida"] = round(precio, 5)

    elif dir_alto != "neutral" and dir_bajo == "neutral":
        resultado["señal_mtf"] = f"⏳ Esperar entrada en {tf_bajo}"
        resultado["descripcion"] = (
            f"{tf_alto} tiene estructura {dir_alto} ({conf_alto:.0f}%), "
            f"pero {tf_bajo} aún no confirma. Espera BOS/CHoCH en {tf_bajo}."
        )
        resultado["confianza_mtf"] = conf_alto * 0.4

    elif dir_alto != dir_bajo and dir_alto != "neutral" and dir_bajo != "neutral":
        resultado["señal_mtf"] = "⚠️ Divergencia MTF"
        resultado["descripcion"] = (
            f"Conflicto: {tf_alto} indica {dir_alto} pero {tf_bajo} indica {dir_bajo}. "
            f"No operar hasta alineación."
        )
        resultado["confianza_mtf"] = 0

    else:
        resultado["señal_mtf"] = "⚪ Sin señal clara"
        resultado["descripcion"] = "Ambos timeframes en rango o sin estructura definida."

    return resultado
