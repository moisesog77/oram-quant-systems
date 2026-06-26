"""
utils/webhook_server.py — Receptor de alertas de TradingView
Servidor HTTP ligero (stdlib pura) que corre en hilo daemon junto al bot.
Sin dependencias adicionales: usa http.server + requests (ya en requirements).

Endpoint: POST /webhook/tradingview?token=SECRET
Health:   GET  /health
"""
import json
import logging
import os
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import requests as _req

TZ_MX   = ZoneInfo("America/Mexico_City")
logger  = logging.getLogger(__name__)

_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
_SECRET  = os.getenv("WEBHOOK_SECRET", "")
_TAPI    = f"https://api.telegram.org/bot{_TOKEN}"

# Lista de chat_ids que recibirán las alertas — se llena desde main()
_CHAT_IDS: list = []
_SERVER_REF = None


def set_chat_ids(ids: list):
    global _CHAT_IDS
    _CHAT_IDS = list(ids)


def _hora_mx() -> str:
    return datetime.now(TZ_MX).strftime("%H:%M")


def _enviar_telegram(msg: str):
    """Envía mensaje a todos los chats configurados vía HTTP directo (sin asyncio)."""
    if not _TOKEN or not _CHAT_IDS:
        logger.warning("Webhook: sin TOKEN o sin chats configurados — mensaje no enviado")
        return
    for chat_id in _CHAT_IDS:
        try:
            resp = _req.post(
                f"{_TAPI}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                timeout=10,
            )
            if not resp.ok:
                logger.error(f"Telegram API {chat_id}: {resp.status_code} {resp.text[:80]}")
        except Exception as e:
            logger.error(f"webhook→telegram {chat_id}: {e}")


def _construir_mensaje(data) -> str:
    """Convierte el payload de TradingView en mensaje formateado para Telegram."""
    # Texto plano (alerta básica sin JSON)
    if isinstance(data, str):
        return (
            "📺 *ALERTA TRADINGVIEW*\n"
            "━━━━━━━━━━━━━━━━\n"
            f"📝 _{data.strip()}_\n"
            f"🕐 {_hora_mx()} CDMX\n"
            "⚠️ _Confirma en el chart antes de operar._"
        )

    ticker    = str(data.get("ticker", "")).strip()
    precio    = data.get("precio") or data.get("price") or data.get("close", "")
    tipo      = str(data.get("tipo", "Alerta de precio")).strip()
    mensaje   = str(data.get("mensaje", "")).strip()
    direccion = str(data.get("direccion", "")).upper().strip()
    sl        = data.get("sl", "")
    tp        = data.get("tp", "")

    es_senal = bool(direccion in ("LONG", "SHORT") and sl and tp)
    titulo   = "📺 *SEÑAL TRADINGVIEW*" if es_senal else "📺 *ALERTA TRADINGVIEW*"
    emoji    = "🟢" if direccion == "LONG" else "🔴" if direccion == "SHORT" else "🔵"

    lineas = [titulo, "━━━━━━━━━━━━━━━━"]

    if ticker:
        if es_senal:
            accion = "🟢 *COMPRAR*" if direccion == "LONG" else "🔴 *VENDER*"
            lineas.append(f"{accion} *{ticker}*")
        else:
            lineas.append(f"{emoji} *{ticker}*")

    if precio != "":
        lineas.append(f"💰 Precio: `{precio}`")
    if tipo:
        lineas.append(f"📍 {tipo}")
    if sl:
        lineas.append(f"🛑 SL: `{sl}`")
    if tp:
        lineas.append(f"✅ TP: `{tp}`")
    if mensaje:
        lineas.append(f"📝 _{mensaje}_")

    lineas.append(f"🕐 {_hora_mx()} CDMX")
    lineas.append("⚠️ _Señal de TradingView. Confirma en el chart._")
    return "\n".join(lineas)


class _WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.debug("webhook: " + fmt % args)

    def _token_valido(self) -> bool:
        if not _SECRET:
            return True  # sin secreto → acepta todo (solo desarrollo local)
        qs = parse_qs(urlparse(self.path).query)
        return qs.get("token", [""])[0] == _SECRET

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/health"):
            body = b"ORAM Quant Systems - Webhook OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/webhook/tradingview":
            self.send_response(404)
            self.end_headers()
            return

        if not self._token_valido():
            logger.warning(f"Webhook: token inválido desde {self.client_address[0]}")
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length).decode("utf-8", errors="replace").strip()

        if not raw:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Empty body")
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw  # texto plano — alerta simple

        try:
            msg = _construir_mensaje(data)
            _enviar_telegram(msg)
            logger.info(f"Webhook TV procesado: {raw[:100]}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            logger.error(f"Webhook procesamiento error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")


def iniciar_servidor(port: int = 8080):
    """Lanza el servidor HTTP en un hilo daemon. No bloquea el proceso principal."""
    global _SERVER_REF
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), _WebhookHandler)
        hilo   = threading.Thread(
            target=server.serve_forever,
            daemon=True,
            name="webhook-tradingview",
        )
        hilo.start()
        _SERVER_REF = server
        logger.info(f"Webhook TradingView activo → :{port}/webhook/tradingview")
        return server
    except OSError as e:
        logger.error(f"No se pudo iniciar webhook en :{port} — {e}")
        return None
