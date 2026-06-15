"""
utils/economic_calendar.py — Calendario económico en ESPAÑOL.
Eventos semanales de alto/medio impacto con horas en CDMX.
Sin dependencias externas.
"""
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from typing import Optional

# Eventos que solo ocurren en una semana específica del mes
_SOLO_PRIMER_VIERNES = {
    "Nóminas No Agrícolas (NFP)",
    "Tasa de Desempleo EE.UU.",
    "Salarios por Hora Promedio",
}
_SOLO_ULTIMO_JUEVES = {
    "Índice de Precios PCE Subyacente",
}


def _es_primer_viernes_del_mes(fecha: date) -> bool:
    """True si la fecha es el primer viernes del mes (días 1-7 inclusive)."""
    return fecha.weekday() == 4 and fecha.day <= 7


def _es_ultimo_jueves_del_mes(fecha: date) -> bool:
    """True si la fecha es el último jueves del mes."""
    if fecha.weekday() != 3:
        return False
    return (fecha + timedelta(days=7)).month != fecha.month


def _es_semana_del_primer_viernes(fecha: date) -> bool:
    """True si el viernes de la misma semana es el primer viernes del mes.
    Usado para ADP, que siempre sale en la semana del NFP (2 días antes)."""
    lunes = fecha - timedelta(days=fecha.weekday())
    viernes = lunes + timedelta(days=4)
    return _es_primer_viernes_del_mes(viernes)


# ── Eventos que solo ocurren en semanas específicas del mes ───────────────────
_SOLO_SEMANA_NFP = {
    "Empleo Privado ADP",   # Miércoles de la semana del NFP (2 días antes)
}
_SOLO_SEMANA_2_3 = {
    "IPC de EE.UU. (Inflación)",   # 2do o 3er miércoles del mes (días 8-21)
}

# ── Fechas exactas por año para bancos centrales ──────────────────────────────
# Actualizadas para 2026-2027. Fuente: calendarios oficiales de cada banco.
# FOMC: miércoles al final de cada reunión (8 veces/año, 18:00 UTC)
_FECHAS_FOMC = {
    date(2026,  1, 28), date(2026,  3, 18), date(2026,  4, 29),
    date(2026,  6, 17), date(2026,  7, 29), date(2026,  9, 16),
    date(2026, 10, 28), date(2026, 12,  9),
    date(2027,  1, 27), date(2027,  3, 17), date(2027,  4, 28),
    date(2027,  6, 16), date(2027,  7, 28), date(2027,  9, 15),
    date(2027, 10, 27), date(2027, 12,  8),
}
# BCE: jueves de decisión (~cada 6-7 semanas, 12:15 UTC)
_FECHAS_BCE = {
    date(2026,  1, 30), date(2026,  3,  6), date(2026,  4, 17),
    date(2026,  6,  5), date(2026,  7, 24), date(2026,  9, 11),
    date(2026, 10, 23), date(2026, 12, 11),
    date(2027,  1, 29), date(2027,  3,  5), date(2027,  4, 16),
    date(2027,  6,  4), date(2027,  7, 23), date(2027,  9, 10),
    date(2027, 10, 22), date(2027, 12, 10),
}
# BoE: jueves de decisión (8 veces/año, 12:00 UTC)
_FECHAS_BOE = {
    date(2026,  2,  5), date(2026,  3, 19), date(2026,  5,  7),
    date(2026,  6, 18), date(2026,  8,  6), date(2026,  9, 17),
    date(2026, 11,  5), date(2026, 12, 10),
    date(2027,  2,  4), date(2027,  3, 18), date(2027,  5,  6),
    date(2027,  6, 17), date(2027,  8,  5), date(2027,  9, 16),
    date(2027, 11,  4), date(2027, 12,  9),
}

_SOLO_FECHA_ESPECIFICA: dict = {
    "Decisión Fed / Actas FOMC":              _FECHAS_FOMC,
    "Decisión de Tipos BCE":                  _FECHAS_BCE,
    "Conferencia de Prensa BCE":              _FECHAS_BCE,
    "Decisión de Tipos Banco de Inglaterra":  _FECHAS_BOE,
}


def _evento_aplica_esta_semana(titulo: str, fecha_ev: date) -> bool:
    """Filtra eventos que solo ocurren en fechas/semanas específicas del mes."""
    if titulo in _SOLO_PRIMER_VIERNES:
        return _es_primer_viernes_del_mes(fecha_ev)
    if titulo in _SOLO_ULTIMO_JUEVES:
        return _es_ultimo_jueves_del_mes(fecha_ev)
    if titulo in _SOLO_SEMANA_NFP:
        return _es_semana_del_primer_viernes(fecha_ev)
    if titulo in _SOLO_SEMANA_2_3:
        return 8 <= fecha_ev.day <= 21
    if titulo in _SOLO_FECHA_ESPECIFICA:
        return fecha_ev in _SOLO_FECHA_ESPECIFICA[titulo]
    return True

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
        if not _evento_aplica_esta_semana(ev.titulo, fecha_ev):
            continue
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


def _agregar_minutos_restantes(eventos: list) -> list:
    """
    Añade campo 'minutos_restantes' a cada evento.
    Calcula cuántos minutos faltan hasta la hora UTC del evento.
    Usado por cmd_proximos del bot y hay_evento_alto_impacto_pronto.
    """
    from zoneinfo import ZoneInfo
    ahora_utc = datetime.now(ZoneInfo("UTC"))
    result = []
    for ev in eventos:
        try:
            hh, mm  = map(int, ev["hora_utc"].split(":"))
            # Determinar la fecha del evento (puede ser hoy o fecha futura)
            from datetime import date as date_type
            ev_date = datetime.strptime(ev["fecha"], "%Y-%m-%d").date() if "fecha" in ev else ahora_utc.date()
            ev_dt   = datetime(ev_date.year, ev_date.month, ev_date.day, hh, mm,
                               tzinfo=ZoneInfo("UTC"))
            mins    = int((ev_dt - ahora_utc).total_seconds() / 60)
            ev_copy = dict(ev)
            ev_copy["minutos_restantes"] = max(0, mins)
            result.append(ev_copy)
        except Exception:
            ev_copy = dict(ev)
            ev_copy["minutos_restantes"] = 0
            result.append(ev_copy)
    return result


def obtener_proximos_eventos(n: int = 3) -> list[dict]:
    """
    Retorna hasta n eventos proximos (no pasados) con campo 'minutos_restantes'.
    Si la semana actual ya termino (fin de semana), muestra los
    eventos de la siguiente semana para que el banner siempre tenga contenido.
    """
    esta_semana = [e for e in obtener_eventos_semana() if not e["ya_paso"]]
    if esta_semana:
        return _agregar_minutos_restantes(esta_semana[:n])
    # Fin de semana o semana completamente pasada: calcular proxima semana
    hoy   = date.today()
    lunes = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=1)
    out = []
    for ev in EVENTOS_RECURRENTES:
        fecha_ev = lunes + timedelta(days=ev.dia_semana)
        if not _evento_aplica_esta_semana(ev.titulo, fecha_ev):
            continue
        hora_mx  = _utc_a_mx(ev.hora_utc, fecha_ev)
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
            "es_hoy":      False,
            "ya_paso":     False,
        })
    return sorted(out, key=lambda x: (x["fecha"], x["hora_utc"]))[:n]


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
        if not _evento_aplica_esta_semana(ev.titulo, fecha_ev):
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
