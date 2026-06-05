"""
utils/economic_calendar.py — Calendario económico en ESPAÑOL.
Eventos semanales de alto/medio impacto con horas en CDMX.
Sin dependencias externas.
"""
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from typing import Optional

TZ_UTC = ZoneInfo("UTC")
TZ_MX  = ZoneInfo("America/Mexico_City")

DIAS_ES = {
    "Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
    "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"
}

@dataclass
class EventoEconomico:
    titulo:     str
    moneda:     str
    impacto:    str   # High | Medium | Low
    dia_semana: int   # 0=Lun … 4=Vie
    hora_utc:   str   # "HH:MM"
    descripcion:str = ""

EVENTOS_RECURRENTES: list[EventoEconomico] = [
    # ── Lunes ──────────────────────────────────────────────────────────────
    EventoEconomico("PMI Manufacturero Flash (EE.UU.)", "USD", "Medium", 0, "13:45",
        "Índice preliminar de actividad manufacturera de EE.UU."),
    EventoEconomico("PMI Servicios Flash (EE.UU.)",     "USD", "Medium", 0, "13:45",
        "Índice preliminar de actividad en el sector servicios de EE.UU."),

    # ── Martes ─────────────────────────────────────────────────────────────
    EventoEconomico("Confianza del Consumidor (CB)",    "USD", "High",   1, "14:00",
        "Indicador de confianza del consumidor del Conference Board. Refleja expectativas económicas."),
    EventoEconomico("Ofertas de Empleo JOLTS",          "USD", "High",   1, "14:00",
        "Número de vacantes disponibles. Indicador clave de la salud del mercado laboral."),

    # ── Miércoles ──────────────────────────────────────────────────────────
    EventoEconomico("Empleo Privado ADP",               "USD", "High",   2, "12:15",
        "Empleo en el sector privado según ADP. Anticipo del NFP del viernes."),
    EventoEconomico("IPC de EE.UU. (Inflación)",        "USD", "High",   2, "12:30",
        "🔴 MÁXIMO IMPACTO — Índice de Precios al Consumidor. El dato de inflación más importante del mes."),
    EventoEconomico("PMI de Servicios ISM",             "USD", "High",   2, "14:00",
        "Actividad del sector servicios según el Institute for Supply Management."),
    EventoEconomico("Inventarios de Petróleo EIA",      "USD", "Medium", 2, "14:30",
        "Variación semanal de inventarios de crudo. Impacta directamente el precio del petróleo (CL=F)."),
    EventoEconomico("Decisión Fed / Actas FOMC",        "USD", "High",   2, "18:00",
        "🔴 MÁXIMO IMPACTO — Decisión de tipos de interés de la Reserva Federal o publicación de actas."),

    # ── Jueves ─────────────────────────────────────────────────────────────
    EventoEconomico("Solicitudes Iniciales Desempleo",  "USD", "High",   3, "12:30",
        "Nuevas solicitudes de subsidio por desempleo. Se publica cada jueves sin excepción."),
    EventoEconomico("Índice de Precios PCE Subyacente", "USD", "High",   3, "12:30",
        "🔴 Indicador favorito de inflación de la Reserva Federal. Se publica ~último jueves del mes."),
    EventoEconomico("Decisión de Tipos BCE",            "EUR", "High",   3, "12:15",
        "Decisión de política monetaria del Banco Central Europeo (cada 6 semanas aprox.)."),
    EventoEconomico("Conferencia de Prensa BCE",        "EUR", "High",   3, "12:45",
        "Rueda de prensa del presidente del BCE tras la decisión de tipos. Alta volatilidad en EUR."),
    EventoEconomico("Decisión de Tipos Banco de Inglaterra","GBP","High", 3, "12:00",
        "Decisión de política monetaria del BoE. Alta volatilidad en GBP (8 veces por año)."),

    # ── Viernes ────────────────────────────────────────────────────────────
    EventoEconomico("Nóminas No Agrícolas (NFP)",       "USD", "High",   4, "12:30",
        "🔴 MÁXIMO IMPACTO — Empleo no agrícola de EE.UU. El dato más importante del mes (1er viernes). Evita operar ±30 min."),
    EventoEconomico("Tasa de Desempleo EE.UU.",         "USD", "High",   4, "12:30",
        "Porcentaje de desempleo oficial. Se publica junto con el NFP el 1er viernes del mes."),
    EventoEconomico("Salarios por Hora Promedio",       "USD", "High",   4, "12:30",
        "Variación salarial mensual. Indica presión inflacionaria desde los salarios."),
    EventoEconomico("Sentimiento Consumidor Michigan",  "USD", "Medium", 4, "14:00",
        "Índice de confianza del consumidor de la Universidad de Michigan."),
    EventoEconomico("PIB de EE.UU.",                    "USD", "High",   4, "12:30",
        "Producto Interno Bruto de EE.UU. Publicado trimestralmente (avance, estimado y final)."),
]

EVENTOS_ESPECIALES: list[dict] = [
    {"titulo": "Decisión de Tipos de la Fed",      "moneda":"USD","impacto":"High",
     "descripcion":"🔴 MÁXIMO IMPACTO — Reunión del FOMC con decisión de tipos (8 veces/año). Evita operar 30 min antes y 30 min después."},
    {"titulo": "IPC de EE.UU. (Inflación)",        "moneda":"USD","impacto":"High",
     "descripcion":"Índice de Precios al Consumidor. Mide la inflación mensual (~2do o 3er miércoles del mes)."},
    {"titulo": "IPP de EE.UU.",                    "moneda":"USD","impacto":"Medium",
     "descripcion":"Índice de Precios al Productor. Mide la inflación en etapas previas al consumidor."},
    {"titulo": "PIB de EE.UU.",                    "moneda":"USD","impacto":"High",
     "descripcion":"Producto Interno Bruto de EE.UU. — avance, estimado y final, publicados en trimestres escalonados."},
    {"titulo": "PCE Subyacente",                   "moneda":"USD","impacto":"High",
     "descripcion":"🔴 El indicador de inflación preferido de la Fed — se publica ~último viernes de cada mes."},
    {"titulo": "Decisión de Tipos Banco de Japón", "moneda":"JPY","impacto":"High",
     "descripcion":"Política monetaria del BoJ. Causa alta volatilidad en USDJPY. Puede ocurrir cualquier día."},
    {"titulo": "Decisión de Tipos RBA",            "moneda":"AUD","impacto":"High",
     "descripcion":"Banco de la Reserva de Australia. Impacta AUDUSD. Se publica generalmente los martes."},
    {"titulo": "Decisión de Tipos Banco de Canadá","moneda":"CAD","impacto":"High",
     "descripcion":"Política monetaria del BoC. Impacta USDCAD (~8 veces por año)."},
]

FOREX_FACTORY_URL = "https://www.forexfactory.com/calendar"


def _utc_a_mx(hora_utc_str: str, fecha: date) -> str:
    try:
        h, m = map(int, hora_utc_str.split(":"))
        dt = datetime(fecha.year, fecha.month, fecha.day, h, m, tzinfo=TZ_UTC)
        return dt.astimezone(TZ_MX).strftime("%H:%M")
    except Exception:
        return hora_utc_str


def _hora_ya_paso(hora_utc_str: str) -> bool:
    try:
        h, m  = map(int, hora_utc_str.split(":"))
        ahora = datetime.now(TZ_UTC)
        ev    = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
        return ahora > ev
    except Exception:
        return False


def obtener_eventos_semana() -> list[dict]:
    hoy   = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    out   = []
    for ev in EVENTOS_RECURRENTES:
        fecha_ev = lunes + timedelta(days=ev.dia_semana)
        hora_mx  = _utc_a_mx(ev.hora_utc, fecha_ev)
        ya_paso  = fecha_ev < hoy or (fecha_ev == hoy and _hora_ya_paso(ev.hora_utc))
        dia_en   = fecha_ev.strftime("%A")
        out.append({
            "fecha":       fecha_ev.strftime("%Y-%m-%d"),
            "dia":         DIAS_ES.get(dia_en, dia_en),
            "hora_utc":    ev.hora_utc,
            "hora_mx":     hora_mx,
            "titulo":      ev.titulo,
            "moneda":      ev.moneda,
            "impacto":     ev.impacto,
            "descripcion": ev.descripcion,
            "es_hoy":      fecha_ev == hoy,
            "ya_paso":     ya_paso,
        })
    return sorted(out, key=lambda x: (x["fecha"], x["hora_utc"]))


def obtener_eventos_hoy() -> list[dict]:
    return [e for e in obtener_eventos_semana() if e["es_hoy"]]


def obtener_proximos_eventos(n: int = 3) -> list[dict]:
    return [e for e in obtener_eventos_semana() if not e["ya_paso"]][:n]


def hay_evento_alto_impacto_pronto(minutos: int = 60) -> tuple[bool, Optional[dict]]:
    ahora = datetime.now(TZ_UTC)
    hoy   = ahora.date()
    lunes = hoy - timedelta(days=hoy.weekday())
    for ev in EVENTOS_RECURRENTES:
        if ev.impacto != "High":
            continue
        fecha_ev = lunes + timedelta(days=ev.dia_semana)
        if fecha_ev != hoy:
            continue
        try:
            h, m  = map(int, ev.hora_utc.split(":"))
            dt_ev = datetime(hoy.year, hoy.month, hoy.day, h, m, tzinfo=TZ_UTC)
            diff  = (dt_ev - ahora).total_seconds() / 60
            if 0 <= diff <= minutos:
                return True, {
                    "titulo":            ev.titulo,
                    "moneda":            ev.moneda,
                    "hora_mx":           _utc_a_mx(ev.hora_utc, hoy),
                    "hora_utc":          ev.hora_utc,
                    "minutos_restantes": round(diff),
                }
        except Exception:
            continue
    return False, None


def impacto_color(impacto: str, dark: bool = True) -> str:
    if dark:
        return {"High":"#fc5c65","Medium":"#f5a623","Low":"#8899aa"}.get(impacto,"#8899aa")
    return {"High":"#c0392b","Medium":"#d68910","Low":"#7f8c8d"}.get(impacto,"#7f8c8d")


def impacto_emoji(impacto: str) -> str:
    return {"High":"🔴","Medium":"🟡","Low":"⚪"}.get(impacto,"⚪")
