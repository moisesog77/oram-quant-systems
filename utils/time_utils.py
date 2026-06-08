"""
utils/time_utils.py — ORAM Quant Systems — Zonas Horarias
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Constantes de zona horaria sin dependencia de pytz.
Usa stdlib zoneinfo (Python 3.9+).

Exporta:
  TZ_MEXICO → ZoneInfo("America/Mexico_City") — CDMX (UTC-6 / UTC-5 DST)
  TZ_UTC    → ZoneInfo("UTC")
"""
from zoneinfo import ZoneInfo

TZ_MEXICO = ZoneInfo("America/Mexico_City")
TZ_UTC    = ZoneInfo("UTC")
