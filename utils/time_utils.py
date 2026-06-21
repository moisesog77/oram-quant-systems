"""
utils/time_utils.py — DEPRECADO.
Las constantes TZ_MEXICO y TZ_UTC no se usan en el proyecto.
Cada módulo define su propia instancia ZoneInfo inline.
Este archivo se conserva únicamente para no romper imports externos.
"""
from zoneinfo import ZoneInfo

TZ_MEXICO = ZoneInfo("America/Mexico_City")
TZ_UTC    = ZoneInfo("UTC")
