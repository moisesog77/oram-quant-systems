"""
utils/ai_engine.py — Motor de IA para análisis de performance y sesgo.
Usa RandomForest + validación cruzada, con advertencias de sobreajuste.
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, StratifiedKFold


def _preparar_features(df_trades: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Construye features a partir del historial de trades.
    """
    df = df_trades.copy()
    df['ganó'] = (df['resultado_usd'] > 0).astype(int)

    features = []
    feat_names = []

    # Dirección como binario
    if 'direccion' in df.columns:
        features.append((df['direccion'] == 'LONG').astype(float).values)
        feat_names.append('es_long')

    # RR planeado
    if 'rr_planeado' in df.columns:
        features.append(df['rr_planeado'].fillna(1.5).values)
        feat_names.append('rr_planeado')

    # Riesgo en USD
    if 'riesgo_usd' in df.columns:
        features.append(df['riesgo_usd'].fillna(30).values)
        feat_names.append('riesgo_usd')

    # Día de la semana
    if 'fecha' in df.columns:
        try:
            df['dow'] = pd.to_datetime(df['fecha']).dt.dayofweek
            features.append(df['dow'].values.astype(float))
            feat_names.append('dia_semana')
        except Exception:
            pass

    # Hora del día
    if 'fecha' in df.columns:
        try:
            df['hora'] = pd.to_datetime(df['fecha']).dt.hour
            features.append(df['hora'].values.astype(float))
            feat_names.append('hora')
        except Exception:
            pass

    if not features:
        return None, None, []

    X = np.column_stack(features)
    y = df['ganó'].values
    return X, y, feat_names


def analizar_performance_ia(df_trades: pd.DataFrame) -> dict:
    """
    Analiza el historial de trades con IA y retorna insights.
    Requiere mínimo 20 trades para ser estadísticamente relevante.
    """
    resultado_base = {
        "disponible": False,
        "mensaje": "",
        "recomendacion": "",
        "mejor_sesion": "",
        "peor_sesion": "",
        "mejor_setup": "",
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "expectancy": 0.0,
        "racha_max_win": 0,
        "racha_max_loss": 0,
        "importancia_features": {},
        "accuracy_cv": 0.0,
        "advertencia_ia": "",
    }

    if df_trades is None or len(df_trades) < 10:
        resultado_base["mensaje"] = f"Necesitas al menos 10 trades (tienes {len(df_trades) if df_trades is not None else 0})."
        return resultado_base

    df = df_trades.copy()

    # --- Métricas básicas ---
    ganadores = df[df['resultado_usd'] > 0]
    perdedores = df[df['resultado_usd'] < 0]

    win_rate = len(ganadores) / len(df) * 100 if len(df) > 0 else 0
    gross_profit = ganadores['resultado_usd'].sum() if not ganadores.empty else 0
    gross_loss   = abs(perdedores['resultado_usd'].sum()) if not perdedores.empty else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    avg_win  = ganadores['resultado_usd'].mean() if not ganadores.empty else 0
    avg_loss = abs(perdedores['resultado_usd'].mean()) if not perdedores.empty else 0
    expectancy = (win_rate/100 * avg_win) - ((1 - win_rate/100) * avg_loss)

    # Racha máxima
    resultados = (df['resultado_usd'] > 0).astype(int).values
    max_win_streak = max_loss_streak = curr_w = curr_l = 0
    for r in resultados:
        if r == 1: curr_w += 1; curr_l = 0
        else: curr_l += 1; curr_w = 0
        max_win_streak  = max(max_win_streak, curr_w)
        max_loss_streak = max(max_loss_streak, curr_l)

    resultado_base.update({
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "expectancy": round(expectancy, 2),
        "racha_max_win": max_win_streak,
        "racha_max_loss": max_loss_streak,
    })

    # --- Mejor sesión por día ---
    if 'fecha' in df.columns:
        try:
            df['dow'] = pd.to_datetime(df['fecha']).dt.day_name()
            por_dia = df.groupby('dow')['resultado_usd'].mean()
            if not por_dia.empty:
                resultado_base["mejor_sesion"] = por_dia.idxmax()
                resultado_base["peor_sesion"]  = por_dia.idxmin()
        except Exception: pass

    # --- Mejor setup ---
    if 'setup' in df.columns:
        setups = df[df['setup'] != ''].groupby('setup')['resultado_usd'].agg(['mean', 'count'])
        if not setups.empty and len(setups[setups['count'] >= 2]) > 0:
            best = setups[setups['count'] >= 2]['mean'].idxmax()
            resultado_base["mejor_setup"] = best

    # --- ML (solo si hay suficientes datos) ---
    if len(df) >= 20:
        X, y, feat_names = _preparar_features(df)
        if X is not None and len(np.unique(y)) == 2:
            try:
                scaler = StandardScaler()
                X_s = scaler.fit_transform(X)

                rf = RandomForestClassifier(
                    n_estimators=100, max_depth=4,
                    min_samples_leaf=3, random_state=42
                )
                cv = StratifiedKFold(n_splits=min(5, len(df)//4), shuffle=True, random_state=42)
                scores = cross_val_score(rf, X_s, y, cv=cv, scoring='accuracy')
                acc_cv = round(scores.mean() * 100, 1)

                rf.fit(X_s, y)
                importancia = dict(zip(feat_names, rf.feature_importances_.round(3)))

                # Predicción próximo trade
                X_next = X_s[-1:].copy()
                prob_win = rf.predict_proba(X_next)[0][1]

                if prob_win > 0.65:
                    rec = f"🟢 Condiciones similares a trades ganadores (prob. {prob_win:.0%})"
                elif prob_win < 0.40:
                    rec = f"🔴 Condiciones similares a trades perdedores (prob. {prob_win:.0%})"
                else:
                    rec = f"⚪ Señal IA neutral (prob. {prob_win:.0%}) — Confiar en análisis SMC"

                advertencia = ""
                if acc_cv < 55:
                    advertencia = "⚠️ Precisión del modelo baja — necesitas más datos de calidad"
                elif acc_cv > 85:
                    advertencia = "⚠️ Precisión muy alta — posible sobreajuste con pocos datos"

                resultado_base.update({
                    "disponible": True,
                    "recomendacion": rec,
                    "accuracy_cv": acc_cv,
                    "importancia_features": importancia,
                    "advertencia_ia": advertencia,
                })
            except Exception as e:
                resultado_base["mensaje"] = f"Error en modelo IA: {str(e)[:50]}"
    else:
        resultado_base["mensaje"] = f"Modelo IA requiere 20+ trades (tienes {len(df)})"

    return resultado_base


def calcular_drawdown(pnl_series: pd.Series) -> dict:
    """Calcula el drawdown máximo y actual."""
    cumsum = pnl_series.cumsum()
    peak   = cumsum.cummax()
    dd     = cumsum - peak
    max_dd = dd.min()
    cur_dd = dd.iloc[-1]

    return {
        "max_drawdown":     round(max_dd, 2),
        "current_drawdown": round(cur_dd, 2),
        "equity_curve":     cumsum.round(2).tolist(),
    }


def calcular_sharpe(pnl_series: pd.Series) -> float:
    """Sharpe ratio simplificado (sin tasa libre de riesgo)."""
    if len(pnl_series) < 5 or pnl_series.std() == 0:
        return 0.0
    return round(pnl_series.mean() / pnl_series.std() * np.sqrt(252), 2)
