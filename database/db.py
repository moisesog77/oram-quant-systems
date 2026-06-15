"""
database/db.py — ORAM Quant Systems — Capa de Persistencia Dual
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Motor de base de datos con detección automática de entorno:

  ┌─ Si existe DATABASE_URL (variable de entorno) ─────────────┐
  │  → PostgreSQL via psycopg2                                   │
  │  → Usado en Railway (bot) y Streamlit Cloud (app web)        │
  │  → Ambos servicios comparten la MISMA base de datos          │
  └─────────────────────────────────────────────────────────────┘
  ┌─ Si NO existe DATABASE_URL ────────────────────────────────┐
  │  → SQLite local (smc_quant.db)                               │
  │  → Usado en desarrollo local                                 │
  └─────────────────────────────────────────────────────────────┘

Marcador de parámetros:
  · SQLite     → ?
  · PostgreSQL → %s
  La función _ph() y _exec() adaptan automáticamente.

Tablas (7):
  users, trades, watchlist, price_alerts, bot_config,
  backtest_results, signal_log
"""

import os
import json
import hashlib
import logging
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta, date

logger = logging.getLogger(__name__)

# ── Detección de motor ────────────────────────────────────────────────────────
# DATABASE_URL puede venir de dos fuentes según el entorno:
#   · Railway (bot worker)    → variable de entorno del sistema (os.environ)
#   · Streamlit Cloud (app)   → st.secrets (NO es una variable de entorno)
# Esta función intenta ambas fuentes en orden, sin crashear si st no está disponible.

def _get_database_url() -> str:
    """
    Obtiene DATABASE_URL desde:
    1. Variable de entorno del sistema (Railway, Docker, local con .env)
    2. st.secrets de Streamlit Cloud (si está disponible)
    3. String vacío → usar SQLite local
    """
    # Fuente 1: variable de entorno del sistema (Railway worker, .env local)
    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url

    # Fuente 2: st.secrets de Streamlit Cloud
    # Importamos streamlit solo aquí para no romper el bot que no usa Streamlit
    try:
        import streamlit as st
        url = st.secrets.get("DATABASE_URL", "")
        if url:
            return url
    except Exception:
        pass  # streamlit no disponible o secrets no configurados

    return ""


DATABASE_URL = _get_database_url()
USE_POSTGRES  = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    logger.info("DB: PostgreSQL (DATABASE_URL detectada)")
else:
    import sqlite3
    DB_PATH = "smc_quant.db"
    logger.info("DB: SQLite local")


# ── Helpers de compatibilidad ─────────────────────────────────────────────────

def _ph(n: int = 1) -> str:
    """Placeholder para N parámetros: '?,?,?' (SQLite) o '%s,%s,%s' (PG)."""
    mark = "%s" if USE_POSTGRES else "?"
    return ",".join([mark] * n)


@contextmanager
def get_conn():
    """
    Context manager de conexión. Garantiza commit en éxito
    y rollback en excepción. Thread-safe para ambos motores.
    """
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _exec(conn, sql: str, params=()):
    """
    Ejecuta SQL en ambos motores.
    Convierte ? → %s automáticamente para PostgreSQL.
    Retorna el cursor.
    """
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def _fetchall(cur) -> list:
    """Convierte resultados a lista de dicts (compatible con ambos motores)."""
    rows = cur.fetchall()
    if not rows:
        return []
    return [dict(r) for r in rows]


def _fetchone(cur):
    """Convierte un resultado a dict, o None si no hay filas."""
    row = cur.fetchone()
    return dict(row) if row else None


def _lastrowid(cur, table: str, conn) -> int:
    """
    Obtiene el ID del último insert.
    PostgreSQL: usa LASTVAL() — devuelve el último valor de secuencia en la sesión actual.
    Es seguro en concurrencia porque LASTVAL() es session-local (no afectado por otros inserts).
    SQLite: usa cur.lastrowid directamente.
    """
    if USE_POSTGRES:
        row = _fetchone(_exec(conn, "SELECT LASTVAL() AS id"))
        return row["id"] if row else 0
    return cur.lastrowid


# ── Inicialización de esquema ─────────────────────────────────────────────────

# SQL para SQLite — usa sintaxis nativa de SQLite
_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    capital_inicial REAL DEFAULT 1000.0,
    settings TEXT DEFAULT '{}',
    is_admin INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    activo TEXT NOT NULL,
    timeframe TEXT DEFAULT '15m',
    direccion TEXT NOT NULL,
    entrada REAL NOT NULL,
    sl REAL NOT NULL,
    tp REAL NOT NULL,
    riesgo_usd REAL DEFAULT 0,
    resultado_usd REAL DEFAULT 0,
    rr_planeado REAL DEFAULT 0,
    rr_real REAL DEFAULT 0,
    setup TEXT DEFAULT '',
    emocion TEXT DEFAULT 'Neutral',
    notas TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    estado TEXT DEFAULT 'Cerrado',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    alias TEXT DEFAULT '',
    UNIQUE(user_id, ticker)
);
CREATE TABLE IF NOT EXISTS price_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    tipo TEXT NOT NULL,
    precio REAL NOT NULL,
    mensaje TEXT DEFAULT '',
    activa INTEGER DEFAULT 1,
    disparada INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    fired_at TEXT DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS bot_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    telegram_chat_id TEXT DEFAULT '',
    alertas_activas INTEGER DEFAULT 1,
    resumen_diario INTEGER DEFAULT 1,
    hora_resumen TEXT DEFAULT '08:00',
    activos_monitor TEXT DEFAULT '["EURUSD=X","GBPUSD=X","USDJPY=X"]',
    tf_monitor TEXT DEFAULT '15m',
    umbral_confianza REAL DEFAULT 70.0,
    ultima_alerta TEXT DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    total_trades INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,
    profit_factor REAL DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    sharpe REAL DEFAULT 0,
    parametros TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS signal_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    tipo TEXT NOT NULL,
    direccion TEXT NOT NULL,
    confianza REAL DEFAULT 0,
    precio REAL DEFAULT 0,
    sl REAL DEFAULT 0,
    tp REAL DEFAULT 0,
    enviada_bot INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

# SQL para PostgreSQL — usa SERIAL y NOW()
_PG_TABLES = [
    """CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT (NOW()::text),
        capital_inicial REAL DEFAULT 1000.0,
        settings TEXT DEFAULT '{}',
        is_admin INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS trades (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        activo TEXT NOT NULL,
        timeframe TEXT DEFAULT '15m',
        direccion TEXT NOT NULL,
        entrada REAL NOT NULL,
        sl REAL NOT NULL,
        tp REAL NOT NULL,
        riesgo_usd REAL DEFAULT 0,
        resultado_usd REAL DEFAULT 0,
        rr_planeado REAL DEFAULT 0,
        rr_real REAL DEFAULT 0,
        setup TEXT DEFAULT '',
        emocion TEXT DEFAULT 'Neutral',
        notas TEXT DEFAULT '',
        tags TEXT DEFAULT '[]',
        estado TEXT DEFAULT 'Cerrado',
        created_at TEXT DEFAULT (NOW()::text)
    )""",
    """CREATE TABLE IF NOT EXISTS watchlist (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        ticker TEXT NOT NULL,
        alias TEXT DEFAULT '',
        UNIQUE(user_id, ticker)
    )""",
    """CREATE TABLE IF NOT EXISTS price_alerts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        ticker TEXT NOT NULL,
        tipo TEXT NOT NULL,
        precio REAL NOT NULL,
        mensaje TEXT DEFAULT '',
        activa INTEGER DEFAULT 1,
        disparada INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (NOW()::text),
        fired_at TEXT DEFAULT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS bot_config (
        id SERIAL PRIMARY KEY,
        user_id INTEGER UNIQUE NOT NULL,
        telegram_chat_id TEXT DEFAULT '',
        alertas_activas INTEGER DEFAULT 1,
        resumen_diario INTEGER DEFAULT 1,
        hora_resumen TEXT DEFAULT '08:00',
        activos_monitor TEXT DEFAULT '["EURUSD=X","GBPUSD=X","USDJPY=X"]',
        tf_monitor TEXT DEFAULT '15m',
        umbral_confianza REAL DEFAULT 70.0,
        ultima_alerta TEXT DEFAULT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS backtest_results (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        ticker TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT NOT NULL,
        total_trades INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0,
        profit_factor REAL DEFAULT 0,
        total_pnl REAL DEFAULT 0,
        max_drawdown REAL DEFAULT 0,
        sharpe REAL DEFAULT 0,
        parametros TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (NOW()::text)
    )""",
    """CREATE TABLE IF NOT EXISTS signal_log (
        id SERIAL PRIMARY KEY,
        ticker TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        tipo TEXT NOT NULL,
        direccion TEXT NOT NULL,
        confianza REAL DEFAULT 0,
        precio REAL DEFAULT 0,
        sl REAL DEFAULT 0,
        tp REAL DEFAULT 0,
        enviada_bot INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (NOW()::text)
    )""",
]


def inicializar_db():
    """
    Crea todas las tablas si no existen.
    · SQLite: usa executescript() con el bloque SQL completo (más eficiente)
    · PostgreSQL: ejecuta cada CREATE TABLE individualmente
    Es idempotente — se puede llamar múltiples veces sin efectos secundarios.
    Después garantiza la existencia del superadmin (único usuario inicial).
    """
    if not USE_POSTGRES:
        # SQLite — executescript es la forma correcta y más eficiente
        with get_conn() as conn:
            conn.executescript(_SQLITE_SCHEMA)
            # Migración segura: añadir columnas nuevas en DBs antiguas
            for table, col, definition in [
                ("users", "is_admin",  "INTEGER DEFAULT 0"),
                ("users", "is_active", "INTEGER DEFAULT 1"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
                except sqlite3.OperationalError:
                    pass  # columna ya existe — normal en rearranques
    else:
        # PostgreSQL — cada sentencia por separado (no soporta executescript)
        with get_conn() as conn:
            for sql in _PG_TABLES:
                _exec(conn, sql)

    # Crear superadmin inicial (idempotente — actualiza si ya existe)
    # Usa variables de entorno ADMIN_USERNAME / ADMIN_PASSWORD si están configuradas.
    _admin_user = os.environ.get("ADMIN_USERNAME", "moises og")
    _admin_pass = os.environ.get("ADMIN_PASSWORD", "1977Emog")
    _crear_superadmin(_admin_user, _admin_pass, capital_inicial=10000.0)


# ── Utilidades internas ───────────────────────────────────────────────────────

def _hash(pw: str) -> str:
    """SHA-256 de la contraseña. Nunca se almacena texto plano."""
    return hashlib.sha256(pw.encode()).hexdigest()


def _crear_superadmin(username: str, password: str, capital_inicial: float = 10000.0):
    """
    Garantiza la existencia del superadmin en CADA arranque.
    · Si ya existe → actualiza password_hash, is_admin=1, is_active=1
      (esto garantiza que las credenciales siempre sean correctas,
       incluso si la DB quedó en estado inconsistente por un deploy fallido)
    · Si no existe → lo crea con los credenciales dados
    Idempotente: nunca falla si se llama múltiples veces.
    """
    uname    = username.strip().lower()
    pw_hash  = _hash(password)
    with get_conn() as conn:
        row = _fetchone(_exec(conn, "SELECT id FROM users WHERE username=?", (uname,)))
        if row:
            # SIEMPRE actualiza hash + admin flags — garantiza credenciales correctas
            _exec(conn,
                "UPDATE users SET password_hash=?, is_admin=1, is_active=1 WHERE username=?",
                (pw_hash, uname)
            )
        else:
            _exec(conn,
                f"INSERT INTO users (username,password_hash,capital_inicial,is_admin,is_active) "
                f"VALUES ({_ph(5)})",
                (uname, pw_hash, capital_inicial, 1, 1)
            )


# ── CRUD: Usuarios ────────────────────────────────────────────────────────────

def crear_usuario(username: str, password: str, capital_inicial: float = 1000.0) -> bool:
    """Registra nuevo usuario. Retorna False si el username ya existe."""
    try:
        with get_conn() as conn:
            _exec(conn,
                f"INSERT INTO users (username,password_hash,capital_inicial) VALUES ({_ph(3)})",
                (username.strip().lower(), _hash(password), capital_inicial)
            )
        return True
    except Exception:
        return False


def autenticar_usuario(username: str, password: str):
    """Verifica credenciales. Retorna dict del usuario o None."""
    with get_conn() as conn:
        return _fetchone(_exec(conn,
            "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=1",
            (username.strip().lower(), _hash(password))
        ))


def actualizar_capital(user_id: int, capital: float):
    """Actualiza capital inicial del usuario."""
    with get_conn() as conn:
        _exec(conn, "UPDATE users SET capital_inicial=? WHERE id=?", (capital, user_id))


def obtener_todos_usuarios() -> list:
    """Lista todos los usuarios ordenados por fecha de creación DESC."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT id,username,capital_inicial,created_at,is_admin,is_active "
            "FROM users ORDER BY created_at DESC"
        ))


def obtener_usuario_por_id(user_id: int) -> dict | None:
    """Obtiene un usuario por ID. Más eficiente que cargar todos los usuarios."""
    with get_conn() as conn:
        return _fetchone(_exec(conn,
            "SELECT id,username,capital_inicial,created_at,is_admin,is_active "
            "FROM users WHERE id=?", (user_id,)
        ))


# ── CRUD: Admin ───────────────────────────────────────────────────────────────

def admin_crear_usuario(username: str, password: str, capital: float = 1000.0) -> bool:
    """Wrapper admin para crear usuario."""
    return crear_usuario(username, password, capital)


def admin_eliminar_usuario(user_id: int) -> bool:
    """
    Hard delete en cascada: borra todos los datos del usuario.
    Protegido: no puede eliminar admins (is_admin=1).
    Retorna True si se eliminó, False si era admin o no existía.
    """
    with get_conn() as conn:
        row = _fetchone(_exec(conn, "SELECT is_admin FROM users WHERE id=?", (user_id,)))
        if not row or row.get("is_admin"):
            return False
        for table in ["trades", "watchlist", "price_alerts", "bot_config", "backtest_results"]:
            _exec(conn, f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        _exec(conn, "DELETE FROM users WHERE id=? AND is_admin=0", (user_id,))
    return True


def admin_resetear_password(user_id: int, nueva_password: str):
    """Actualiza el hash de contraseña de cualquier usuario."""
    with get_conn() as conn:
        _exec(conn, "UPDATE users SET password_hash=? WHERE id=?",
              (_hash(nueva_password), user_id))


def admin_actualizar_capital(user_id: int, capital: float):
    """Admin: actualiza capital de cualquier usuario."""
    actualizar_capital(user_id, capital)


def admin_stats_globales() -> dict:
    """KPIs globales de la plataforma para el panel de admin."""
    hoy = date.today().isoformat()
    with get_conn() as conn:
        def cnt(sql, params=()):
            row = _fetchone(_exec(conn, sql, params))
            return list(row.values())[0] if row else 0
        return {
            "total_users":        cnt("SELECT COUNT(*) as c FROM users WHERE is_active=1"),
            "total_trades":       cnt("SELECT COUNT(*) as c FROM trades"),
            "total_senales":      cnt("SELECT COUNT(*) as c FROM signal_log"),
            "bots_activos":       cnt("SELECT COUNT(*) as c FROM bot_config WHERE alertas_activas=1 AND telegram_chat_id!=?", ("",)),
            "senales_hoy":        cnt("SELECT COUNT(*) as c FROM signal_log WHERE created_at >= ?", (hoy,)),
            "alertas_pendientes": cnt("SELECT COUNT(*) as c FROM price_alerts WHERE activa=1 AND disparada=0"),
            "trades_hoy":         cnt("SELECT COUNT(*) as c FROM trades WHERE fecha >= ?", (hoy,)),
        }



def admin_logs_senales(limite: int = 100) -> list:
    """Últimas N señales SMC del log, descendente."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM signal_log ORDER BY created_at DESC LIMIT ?", (limite,)
        ))


def admin_trades_todos(limite: int = 100) -> list:
    """Últimos N trades de todos los usuarios con su username."""
    with get_conn() as conn:
        return _fetchall(_exec(conn, """
            SELECT t.*, u.username FROM trades t
            JOIN users u ON t.user_id=u.id
            ORDER BY t.created_at DESC LIMIT ?
        """, (limite,)))


def admin_configs_bot_todas() -> list:
    """Configuración de bot de todos los usuarios."""
    with get_conn() as conn:
        return _fetchall(_exec(conn, """
            SELECT bc.*, u.username FROM bot_config bc
            JOIN users u ON bc.user_id=u.id ORDER BY u.username
        """))


# ── CRUD: Trades ──────────────────────────────────────────────────────────────

def insertar_trade(user_id: int, data: dict) -> int:
    """
    Inserta trade en el diario. Calcula automáticamente:
    · rr_planeado = |TP-entrada| / |SL-entrada|
    · rr_real     = resultado_usd / riesgo_usd
    Retorna el ID del trade creado.
    """
    riesgo    = abs(data['entrada'] - data['sl'])
    beneficio = abs(data['tp'] - data['entrada'])
    rr        = round(beneficio / riesgo, 2) if riesgo > 0 else 0
    rr_real   = round(data['resultado_usd'] / abs(data['riesgo_usd']), 2) \
                if data.get('resultado_usd') and data.get('riesgo_usd') else 0.0
    with get_conn() as conn:
        cur = _exec(conn, f"""INSERT INTO trades
            (user_id,fecha,activo,timeframe,direccion,entrada,sl,tp,
             riesgo_usd,resultado_usd,rr_planeado,rr_real,setup,emocion,notas,tags,estado)
            VALUES ({_ph(17)})""",
            (user_id, data['fecha'], data['activo'], data.get('timeframe','15m'),
             data['direccion'], data['entrada'], data['sl'], data['tp'],
             data.get('riesgo_usd',0), data.get('resultado_usd',0), rr, rr_real,
             data.get('setup',''), data.get('emocion','Neutral'),
             data.get('notas',''), json.dumps(data.get('tags',[])),
             data.get('estado','Cerrado'))
        )
        return _lastrowid(cur, "trades", conn)


def obtener_trades(user_id: int) -> list:
    """Trades del usuario, ordenados por fecha DESC."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM trades WHERE user_id=? ORDER BY fecha DESC, id DESC", (user_id,)
        ))


def eliminar_trade(trade_id: int, user_id: int):
    """Elimina trade verificando que pertenezca al usuario."""
    with get_conn() as conn:
        _exec(conn, "DELETE FROM trades WHERE id=? AND user_id=?", (trade_id, user_id))


# ── CRUD: Watchlist ───────────────────────────────────────────────────────────

def obtener_watchlist(user_id: int) -> list:
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM watchlist WHERE user_id=?", (user_id,)
        ))


def agregar_watchlist(user_id: int, ticker: str, alias: str = "") -> bool:
    """Agrega activo a la watchlist. Retorna False si ya existe."""
    try:
        with get_conn() as conn:
            _exec(conn, f"INSERT INTO watchlist (user_id,ticker,alias) VALUES ({_ph(3)})",
                  (user_id, ticker.upper(), alias))
        return True
    except Exception:
        return False


def eliminar_watchlist(user_id: int, ticker: str):
    with get_conn() as conn:
        _exec(conn, "DELETE FROM watchlist WHERE user_id=? AND ticker=?", (user_id, ticker))


# ── CRUD: Price Alerts ────────────────────────────────────────────────────────

def crear_alerta(user_id: int, ticker: str, tipo: str, precio: float, mensaje: str = "") -> int:
    """
    Crea alerta de precio. tipo: 'above' o 'below'.
    Retorna el ID creado.
    """
    with get_conn() as conn:
        cur = _exec(conn,
            f"INSERT INTO price_alerts (user_id,ticker,tipo,precio,mensaje) VALUES ({_ph(5)})",
            (user_id, ticker, tipo, precio, mensaje)
        )
        return _lastrowid(cur, "price_alerts", conn)


def obtener_alertas(user_id: int, solo_activas: bool = True) -> list:
    with get_conn() as conn:
        q = "SELECT * FROM price_alerts WHERE user_id=?"
        if solo_activas:
            q += " AND activa=1 AND disparada=0"
        return _fetchall(_exec(conn, q + " ORDER BY created_at DESC", (user_id,)))


def obtener_todas_alertas_activas() -> list:
    """Todas las alertas activas de todos los usuarios (para el bot)."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT pa.*, u.username FROM price_alerts pa "
            "JOIN users u ON pa.user_id=u.id WHERE pa.activa=1 AND pa.disparada=0"
        ))


def disparar_alerta(alert_id: int):
    """Marca alerta como disparada con timestamp UTC actual."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        _exec(conn,
            "UPDATE price_alerts SET disparada=1, fired_at=? WHERE id=?",
            (now_str, alert_id)
        )


def eliminar_alerta(alert_id: int, user_id: int):
    with get_conn() as conn:
        _exec(conn, "DELETE FROM price_alerts WHERE id=? AND user_id=?", (alert_id, user_id))


# ── CRUD: Bot Config ──────────────────────────────────────────────────────────

def obtener_bot_config(user_id: int) -> dict:
    """Retorna config del bot. Si no existe, la crea con defaults."""
    with get_conn() as conn:
        row = _fetchone(_exec(conn, "SELECT * FROM bot_config WHERE user_id=?", (user_id,)))
        if row:
            return row
        _exec(conn, f"INSERT INTO bot_config (user_id) VALUES ({_ph(1)})", (user_id,))
        return _fetchone(_exec(conn, "SELECT * FROM bot_config WHERE user_id=?", (user_id,)))


def actualizar_bot_config(user_id: int, **kwargs):
    """Actualiza campos arbitrarios de bot_config via kwargs."""
    if not kwargs:
        return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    with get_conn() as conn:
        _exec(conn, f"UPDATE bot_config SET {sets} WHERE user_id=?",
              tuple(kwargs.values()) + (user_id,))


def obtener_todas_configs_bot() -> list:
    """Configs de todos los usuarios con bot activo y Chat ID configurado."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT bc.*, u.username FROM bot_config bc "
            "JOIN users u ON bc.user_id=u.id "
            "WHERE bc.alertas_activas=1 AND bc.telegram_chat_id!=''"
        ))


# ── CRUD: Signal Log ──────────────────────────────────────────────────────────

def registrar_señal(ticker: str, timeframe: str, tipo: str, direccion: str,
                    confianza: float, precio: float, sl: float, tp: float) -> int:
    """Registra señal SMC en el log. Retorna ID para marcarla enviada."""
    with get_conn() as conn:
        cur = _exec(conn,
            f"INSERT INTO signal_log (ticker,timeframe,tipo,direccion,confianza,precio,sl,tp) "
            f"VALUES ({_ph(8)})",
            (ticker, timeframe, tipo, direccion, confianza, precio, sl, tp)
        )
        return _lastrowid(cur, "signal_log", conn)


def marcar_señal_enviada(signal_id: int):
    """Marca señal como enviada via Telegram."""
    with get_conn() as conn:
        _exec(conn, "UPDATE signal_log SET enviada_bot=1 WHERE id=?", (signal_id,))


def obtener_señales_recientes(horas: int = 24) -> list:
    """Señales generadas en las últimas N horas."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM signal_log WHERE created_at >= ? ORDER BY created_at DESC",
            (cutoff,)
        ))


# ── CRUD: Backtest ────────────────────────────────────────────────────────────

def guardar_backtest(user_id: int, data: dict) -> int:
    """Guarda resultados de backtest. Retorna ID creado."""
    with get_conn() as conn:
        cur = _exec(conn, f"""INSERT INTO backtest_results
            (user_id,ticker,timeframe,fecha_inicio,fecha_fin,
             total_trades,win_rate,profit_factor,total_pnl,max_drawdown,sharpe,parametros)
            VALUES ({_ph(12)})""",
            (user_id, data['ticker'], data['timeframe'], data['fecha_inicio'], data['fecha_fin'],
             data['total_trades'], data['win_rate'], data['profit_factor'],
             data['total_pnl'], data['max_drawdown'], data['sharpe'],
             json.dumps(data.get('parametros',{})))
        )
        return _lastrowid(cur, "backtest_results", conn)


def obtener_backtests(user_id: int) -> list:
    """Backtests del usuario, más recientes primero."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM backtest_results WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ))
