"""
utils/time_utils.py — Zona horaria CDMX sin pytz (usa stdlib zoneinfo).
Compatible con Python 3.9+. No requiere instalación de pytz.
"""
from zoneinfo import ZoneInfo

TZ_MEXICO = ZoneInfo("America/Mexico_City")
TZ_UTC    = ZoneInfo("UTC")
