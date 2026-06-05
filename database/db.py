"""
database/db.py — ORAM Quant Systems — Capa de Persistencia Dual
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Motor de base de datos con detección automática de entorno:

  ┌─ Si existe DATABASE_URL (variable de entorno) ──────────────┐
  │   → PostgreSQL via psycopg2                                  │
  │   → Usado en Railway (bot) y Streamlit Cloud (app web)       │
  │   → Ambos servicios comparten la MISMA base de datos         │
  └─────────────────────────────────────────────────────────────┘
  ┌─ Si NO existe DATABASE_URL ─────────────────────────────────┐
  │   → SQLite local (smc_quant.db)                              │
  │   → Usado en desarrollo local                                │
  └─────────────────────────────────────────────────────────────┘

Compatibilidad SQL:
  · Marcador de parámetros: %s (PostgreSQL) vs ? (SQLite)
  · AUTOINCREMENT: SERIAL (PG) vs INTEGER PRIMARY KEY AUTOINCREMENT (SQLite)
  · datetime('now'): NOW() (PG) vs datetime('now') (SQLite)
  · La función _sql() adapta automáticamente la sintaxis

Tablas (7):
  users, trades, watchlist, price_alerts, bot_config, backtest_results, signal_log

Seguridad:
  · SHA-256 para contraseñas (nunca texto plano)
  · Superadmin Moises OG protegido (is_admin=1, nunca eliminable)
  · Hard delete en cascada para usuarios normales
"""

import os
import json
import hashlib
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# ── Detección de motor ────────────────────────────────────────────────────────
# DATABASE_URL se inyecta como variable de entorno en Railway y Streamlit Cloud
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES  = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    logger.info("DB: PostgreSQL (DATABASE_URL detectada)")
else:
    import sqlite3
    DB_PATH = "smc_quant.db"
    logger.info("DB: SQLite local (%s)", DB_PATH)


# ── Helpers de compatibilidad SQL ─────────────────────────────────────────────

def _ph(n: int = 1) -> str:
    """
    Retorna el placeholder correcto para N parámetros.
    PostgreSQL usa %s, SQLite usa ?

    Ejemplos:
      _ph(1)  → '?'   o  '%s'
      _ph(3)  → '?,?,?'  o  '%s,%s,%s'
    """
    mark = "%s" if USE_POSTGRES else "?"
    return ",".join([mark] * n)


def _now() -> str:
    """Función SQL para timestamp actual según motor."""
    return "NOW()" if USE_POSTGRES else "datetime('now')"


def _serial() -> str:
    """Tipo de columna ID autoincremental según motor."""
    return "SERIAL" if USE_POSTGRES else "INTEGER"


def _autoincrement() -> str:
    """Cláusula AUTOINCREMENT según motor (PG no la necesita con SERIAL)."""
    return "" if USE_POSTGRES else "AUTOINCREMENT"


# ── Context manager de conexión ───────────────────────────────────────────────

@contextmanager
def get_conn():
    """
    Context manager que provee una conexión de base de datos y
    garantiza commit en éxito o rollback en excepción.

    Uso:
        with get_conn() as conn:
            conn.execute("SELECT ...")

    PostgreSQL: usa psycopg2.connect(DATABASE_URL) con cursor tipo dict
    SQLite:     usa sqlite3.connect(DB_PATH) con row_factory=sqlite3.Row
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


def _exec(conn, sql: str, params=()) -> "cursor":
    """
    Ejecuta SQL unificado para ambos motores.
    · Convierte ? → %s automáticamente para PostgreSQL
    · Retorna el cursor con los resultados
    """
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def _fetchall(cur) -> list:
    """Convierte resultados a lista de dicts en ambos motores."""
    rows = cur.fetchall()
    if not rows:
        return []
    if USE_POSTGRES:
        return [dict(r) for r in rows]
    return [dict(r) for r in rows]


def _fetchone(cur):
    """Convierte un resultado a dict (o None) en ambos motores."""
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def _lastrowid(cur, table: str, conn) -> int:
    """
    Obtiene el ID del último registro insertado.
    PostgreSQL: usa RETURNING id (no tiene lastrowid)
    SQLite:     usa cur.lastrowid
    """
    if USE_POSTGRES:
        # Re-consulta el último ID de la tabla (funciona porque no hay concurrencia crítica aquí)
        row = _fetchone(_exec(conn, f"SELECT id FROM {table} ORDER BY id DESC LIMIT 1"))
        return row["id"] if row else 0
    return cur.lastrowid


# ── Inicialización de esquema ─────────────────────────────────────────────────

def inicializar_db():
    """
    Crea todas las tablas si no existen y garantiza la existencia
    del usuario demo y del superadmin Moises OG.

    Se ejecuta en cada arranque de la app y del bot — es idempotente:
    CREATE TABLE IF NOT EXISTS no modifica tablas ya existentes.

    Migración segura: ALTER TABLE ADD COLUMN ignora errores si la columna
    ya existe (compatible con bases de datos antiguas).
    """
    with get_conn() as conn:
        _serial_t  = _serial()
        _ai        = _autoincrement()
        _now_t     = _now()

        # Tabla de usuarios
        _exec(conn, f"""
        CREATE TABLE IF NOT EXISTS users (
            id {_serial_t} PRIMARY KEY {_ai},
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT ('{_now_t}'),
            capital_inicial REAL DEFAULT 1000.0,
            settings TEXT DEFAULT '{{}}',
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )""")

        # Tabla de trades (diario de operaciones)
        _exec(conn, f"""
        CREATE TABLE IF NOT EXISTS trades (
            id {_serial_t} PRIMARY KEY {_ai},
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
            created_at TEXT DEFAULT ('{_now_t}')
        )""")

        # Tabla de watchlist
        _exec(conn, f"""
        CREATE TABLE IF NOT EXISTS watchlist (
            id {_serial_t} PRIMARY KEY {_ai},
            user_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            alias TEXT DEFAULT '',
            UNIQUE(user_id, ticker)
        )""")

        # Tabla de alertas de precio
        _exec(conn, f"""
        CREATE TABLE IF NOT EXISTS price_alerts (
            id {_serial_t} PRIMARY KEY {_ai},
            user_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            tipo TEXT NOT NULL,
            precio REAL NOT NULL,
            mensaje TEXT DEFAULT '',
            activa INTEGER DEFAULT 1,
            disparada INTEGER DEFAULT 0,
            created_at TEXT DEFAULT ('{_now_t}'),
            fired_at TEXT DEFAULT NULL
        )""")

        # Tabla de configuración del bot de Telegram
        _exec(conn, f"""
        CREATE TABLE IF NOT EXISTS bot_config (
            id {_serial_t} PRIMARY KEY {_ai},
            user_id INTEGER UNIQUE NOT NULL,
            telegram_chat_id TEXT DEFAULT '',
            alertas_activas INTEGER DEFAULT 1,
            resumen_diario INTEGER DEFAULT 1,
            hora_resumen TEXT DEFAULT '08:00',
            activos_monitor TEXT DEFAULT '["EURUSD=X","GBPUSD=X","USDJPY=X"]',
            tf_monitor TEXT DEFAULT '15m',
            umbral_confianza REAL DEFAULT 70.0,
            ultima_alerta TEXT DEFAULT NULL
        )""")

        # Tabla de resultados de backtesting
        _exec(conn, f"""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id {_serial_t} PRIMARY KEY {_ai},
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
            parametros TEXT DEFAULT '{{}}',
            created_at TEXT DEFAULT ('{_now_t}')
        )""")

        # Tabla de log de señales SMC
        _exec(conn, f"""
        CREATE TABLE IF NOT EXISTS signal_log (
            id {_serial_t} PRIMARY KEY {_ai},
            ticker TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            tipo TEXT NOT NULL,
            direccion TEXT NOT NULL,
            confianza REAL DEFAULT 0,
            precio REAL DEFAULT 0,
            sl REAL DEFAULT 0,
            tp REAL DEFAULT 0,
            enviada_bot INTEGER DEFAULT 0,
            created_at TEXT DEFAULT ('{_now_t}')
        )""")

        # Migración segura para SQLite (PostgreSQL ya tiene las columnas desde CREATE)
        if not USE_POSTGRES:
            import sqlite3 as _sq
            for table, col, definition in [
                ("users", "is_admin",  "INTEGER DEFAULT 0"),
                ("users", "is_active", "INTEGER DEFAULT 1"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
                except _sq.OperationalError:
                    pass  # columna ya existe — normal en arranques subsecuentes

    # Crear usuarios iniciales (idempotente)
    crear_usuario("demo", "demo123", capital_inicial=10000.0)
    _crear_superadmin("moises og", "1977Emog", capital_inicial=10000.0)


# ── Utilidades internas ───────────────────────────────────────────────────────

def _hash(pw: str) -> str:
    """Hash SHA-256 de la contraseña. Nunca se almacena texto plano."""
    return hashlib.sha256(pw.encode()).hexdigest()


def _crear_superadmin(username: str, password: str, capital_inicial: float = 10000.0):
    """
    Garantiza la existencia del superadmin en cada arranque.
    Si ya existe → actualiza is_admin=1 y is_active=1.
    Si no existe → lo crea con los credenciales dados.
    Es idempotente y nunca falla si se llama múltiples veces.
    """
    uname = username.strip().lower()
    with get_conn() as conn:
        row = _fetchone(_exec(conn, "SELECT id FROM users WHERE username=?", (uname,)))
        if row:
            _exec(conn, "UPDATE users SET is_admin=1, is_active=1 WHERE username=?", (uname,))
        else:
            _exec(conn,
                "INSERT INTO users (username,password_hash,capital_inicial,is_admin,is_active) "
                f"VALUES ({_ph(5)})",
                (uname, _hash(password), capital_inicial, 1, 1)
            )


# ── CRUD: Usuarios ────────────────────────────────────────────────────────────

def crear_usuario(username: str, password: str, capital_inicial: float = 1000.0) -> bool:
    """
    Registra un nuevo usuario. Retorna True si fue creado, False si el
    username ya existe (IntegrityError por UNIQUE constraint).
    """
    try:
        with get_conn() as conn:
            _exec(conn,
                f"INSERT INTO users (username,password_hash,capital_inicial) VALUES ({_ph(3)})",
                (username.strip().lower(), _hash(password), capital_inicial)
            )
        return True
    except Exception:
        return False  # username duplicado


def autenticar_usuario(username: str, password: str):
    """
    Verifica credenciales. Retorna dict del usuario si es correcto y
    está activo (is_active=1), None en caso contrario.
    """
    with get_conn() as conn:
        row = _fetchone(_exec(conn,
            "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=1",
            (username.strip().lower(), _hash(password))
        ))
        return row


def actualizar_capital(user_id: int, capital: float):
    """Actualiza el capital inicial del usuario."""
    with get_conn() as conn:
        _exec(conn, "UPDATE users SET capital_inicial=? WHERE id=?", (capital, user_id))


def obtener_todos_usuarios() -> list:
    """Lista todos los usuarios ordenados por fecha de creación descendente."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT id,username,capital_inicial,created_at,is_admin,is_active "
            "FROM users ORDER BY created_at DESC"
        ))


# ── CRUD: Admin ───────────────────────────────────────────────────────────────

def admin_crear_usuario(username: str, password: str, capital: float = 1000.0) -> bool:
    """Wrapper admin para crear usuario. Retorna True si fue creado."""
    return crear_usuario(username, password, capital)


def admin_eliminar_usuario(user_id: int) -> bool:
    """
    Elimina permanentemente un usuario y TODOS sus datos (hard delete).
    Orden de borrado respeta integridad referencial:
      trades → watchlist → price_alerts → bot_config → backtest_results → users

    Protección: no puede eliminar usuarios con is_admin=1.
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
    """Actualiza el hash de contraseña del usuario indicado."""
    with get_conn() as conn:
        _exec(conn, "UPDATE users SET password_hash=? WHERE id=?",
              (_hash(nueva_password), user_id))


def admin_actualizar_capital(user_id: int, capital: float):
    """Admin: actualiza capital de cualquier usuario."""
    actualizar_capital(user_id, capital)


def admin_stats_globales() -> dict:
    """
    Retorna KPIs globales de la plataforma para el panel de admin.
    Todas las consultas son COUNT simples — no afectan rendimiento.
    Usa date('now') que funciona en SQLite y en PostgreSQL vía adaptador.
    """
    # Fecha de hoy como string YYYY-MM-DD (compatible con ambos motores)
    from datetime import date
    hoy = date.today().isoformat()

    with get_conn() as conn:
        def cnt(sql, params=()):
            """Ejecuta una COUNT query y retorna el entero resultante."""
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
    """Retorna los últimas N señales SMC del log, descendente por fecha."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM signal_log ORDER BY created_at DESC LIMIT ?", (limite,)
        ))


def admin_trades_todos(limite: int = 100) -> list:
    """Retorna los últimos N trades de TODOS los usuarios con su username."""
    with get_conn() as conn:
        return _fetchall(_exec(conn, """
            SELECT t.*, u.username FROM trades t
            JOIN users u ON t.user_id=u.id
            ORDER BY t.created_at DESC LIMIT ?
        """, (limite,)))


def admin_configs_bot_todas() -> list:
    """Retorna la configuración de bot de todos los usuarios."""
    with get_conn() as conn:
        return _fetchall(_exec(conn, """
            SELECT bc.*, u.username FROM bot_config bc
            JOIN users u ON bc.user_id=u.id ORDER BY u.username
        """))


# ── CRUD: Trades ──────────────────────────────────────────────────────────────

def insertar_trade(user_id: int, data: dict) -> int:
    """
    Inserta un nuevo trade en el diario.
    Calcula automáticamente:
      · rr_planeado = |TP - entrada| / |SL - entrada|
      · rr_real     = resultado_usd / riesgo_usd (si ambos existen)
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
    """Retorna todos los trades del usuario, ordenados por fecha descendente."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM trades WHERE user_id=? ORDER BY fecha DESC, id DESC", (user_id,)
        ))


def eliminar_trade(trade_id: int, user_id: int):
    """Elimina un trade verificando que pertenezca al usuario."""
    with get_conn() as conn:
        _exec(conn, "DELETE FROM trades WHERE id=? AND user_id=?", (trade_id, user_id))


# ── CRUD: Watchlist ───────────────────────────────────────────────────────────

def obtener_watchlist(user_id: int) -> list:
    """Retorna la lista de activos monitoreados del usuario."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM watchlist WHERE user_id=?", (user_id,)
        ))


def agregar_watchlist(user_id: int, ticker: str, alias: str = "") -> bool:
    """
    Agrega un activo a la watchlist del usuario.
    Retorna False si el ticker ya existe (UNIQUE constraint).
    """
    try:
        with get_conn() as conn:
            _exec(conn, f"INSERT INTO watchlist (user_id,ticker,alias) VALUES ({_ph(3)})",
                  (user_id, ticker.upper(), alias))
        return True
    except Exception:
        return False


def eliminar_watchlist(user_id: int, ticker: str):
    """Elimina un activo de la watchlist del usuario."""
    with get_conn() as conn:
        _exec(conn, "DELETE FROM watchlist WHERE user_id=? AND ticker=?", (user_id, ticker))


# ── CRUD: Price Alerts ────────────────────────────────────────────────────────

def crear_alerta(user_id: int, ticker: str, tipo: str, precio: float, mensaje: str = "") -> int:
    """
    Crea una alerta de precio.
    tipo: 'above' (notificar cuando precio >= nivel) o 'below' (precio <= nivel)
    Retorna el ID de la alerta creada.
    """
    with get_conn() as conn:
        cur = _exec(conn,
            f"INSERT INTO price_alerts (user_id,ticker,tipo,precio,mensaje) VALUES ({_ph(5)})",
            (user_id, ticker, tipo, precio, mensaje)
        )
        return _lastrowid(cur, "price_alerts", conn)


def obtener_alertas(user_id: int, solo_activas: bool = True) -> list:
    """Retorna alertas del usuario. Con solo_activas=True filtra disparadas."""
    with get_conn() as conn:
        q = "SELECT * FROM price_alerts WHERE user_id=?"
        if solo_activas:
            q += " AND activa=1 AND disparada=0"
        return _fetchall(_exec(conn, q + " ORDER BY created_at DESC", (user_id,)))


def obtener_todas_alertas_activas() -> list:
    """
    Retorna TODAS las alertas activas de TODOS los usuarios.
    Usada por el bot para verificar niveles de precio cada 5 min.
    """
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT pa.*, u.username FROM price_alerts pa "
            "JOIN users u ON pa.user_id=u.id WHERE pa.activa=1 AND pa.disparada=0"
        ))


def disparar_alerta(alert_id: int):
    """Marca una alerta como disparada con timestamp actual (compatible PG/SQLite)."""
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        _exec(conn,
            "UPDATE price_alerts SET disparada=1, fired_at=? WHERE id=?",
            (now_str, alert_id)
        )


def eliminar_alerta(alert_id: int, user_id: int):
    """Elimina una alerta verificando que pertenezca al usuario."""
    with get_conn() as conn:
        _exec(conn, "DELETE FROM price_alerts WHERE id=? AND user_id=?", (alert_id, user_id))


# ── CRUD: Bot Config ──────────────────────────────────────────────────────────

def obtener_bot_config(user_id: int) -> dict:
    """
    Retorna la configuración del bot del usuario.
    Si no existe, la crea con valores por defecto y la retorna.
    """
    with get_conn() as conn:
        row = _fetchone(_exec(conn, "SELECT * FROM bot_config WHERE user_id=?", (user_id,)))
        if row:
            return row
        _exec(conn, f"INSERT INTO bot_config (user_id) VALUES ({_ph(1)})", (user_id,))
        return _fetchone(_exec(conn, "SELECT * FROM bot_config WHERE user_id=?", (user_id,)))


def actualizar_bot_config(user_id: int, **kwargs):
    """
    Actualiza campos arbitrarios de bot_config via kwargs.
    Ejemplo: actualizar_bot_config(1, telegram_chat_id='123', umbral_confianza=75.0)
    """
    if not kwargs:
        return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    with get_conn() as conn:
        _exec(conn, f"UPDATE bot_config SET {sets} WHERE user_id=?",
              tuple(kwargs.values()) + (user_id,))


def obtener_todas_configs_bot() -> list:
    """
    Retorna configs de todos los usuarios que tienen bot activo y Chat ID configurado.
    Usada por los jobs del bot (monitoreo, resumen diario, alertas).
    """
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT bc.*, u.username FROM bot_config bc "
            "JOIN users u ON bc.user_id=u.id "
            "WHERE bc.alertas_activas=1 AND bc.telegram_chat_id!=''"
        ))


# ── CRUD: Signal Log ──────────────────────────────────────────────────────────

def registrar_señal(ticker: str, timeframe: str, tipo: str, direccion: str,
                    confianza: float, precio: float, sl: float, tp: float) -> int:
    """
    Registra una señal SMC detectada en el log.
    Retorna el ID de la señal para marcarla como enviada después.
    """
    with get_conn() as conn:
        cur = _exec(conn,
            f"INSERT INTO signal_log (ticker,timeframe,tipo,direccion,confianza,precio,sl,tp) "
            f"VALUES ({_ph(8)})",
            (ticker, timeframe, tipo, direccion, confianza, precio, sl, tp)
        )
        return _lastrowid(cur, "signal_log", conn)


def marcar_señal_enviada(signal_id: int):
    """Marca una señal del log como enviada via Telegram."""
    with get_conn() as conn:
        _exec(conn, "UPDATE signal_log SET enviada_bot=1 WHERE id=?", (signal_id,))


def obtener_señales_recientes(horas: int = 24) -> list:
    """
    Retorna señales generadas en las últimas N horas, descendente.
    Usa datetime aritmético compatible con SQLite y PostgreSQL:
      · SQLite:     datetime('now', '-N hours')
      · PostgreSQL: NOW() - INTERVAL 'N hours'  (via Python datetime)
    """
    from datetime import datetime, timezone, timedelta
    # Calculamos el corte en Python — compatible con ambos motores
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM signal_log WHERE created_at >= ? ORDER BY created_at DESC",
            (cutoff,)
        ))


# ── CRUD: Backtest ────────────────────────────────────────────────────────────

def guardar_backtest(user_id: int, data: dict) -> int:
    """
    Guarda los resultados de un backtest en la base de datos.
    Retorna el ID del backtest creado.
    """
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
    """Retorna todos los backtests del usuario, más recientes primero."""
    with get_conn() as conn:
        return _fetchall(_exec(conn,
            "SELECT * FROM backtest_results WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ))
