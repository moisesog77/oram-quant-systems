"""
database/db.py — ORAM Quant Systems — Capa de Persistencia (SQLite)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Responsabilidades:
  · Definir el esquema de 7 tablas SQLite (ver inicializar_db)
  · Proveer la conexión thread-safe vía context manager get_conn()
  · Implementar todas las operaciones CRUD de la aplicación
  · Gestión de superadmin: creación/actualización garantizada en cada arranque
  · Migración segura: columnas nuevas se añaden con ALTER TABLE sin romper DBs existentes

Tablas:
  users             → Usuarios registrados (id, username, password_hash, capital, is_admin)
  trades            → Diario de operaciones por usuario
  watchlist         → Lista de activos monitoreados por usuario
  price_alerts      → Alertas de precio personalizadas
  bot_config        → Configuración del bot de Telegram por usuario
  backtest_results  → Resultados de backtests guardados
  signal_log        → Log de señales SMC generadas por el motor

Seguridad:
  · Contraseñas hasheadas con SHA-256 (nunca en texto plano)
  · is_admin=1 solo para Moises OG (Superadmin protegido)
  · admin_eliminar_usuario() verifica is_admin=0 antes de borrar
  · Hard delete en cascada: eliminar usuario borra TODOS sus datos

Uso típico:
  from database.db import obtener_trades, insertar_trade
  trades = obtener_trades(user_id=1)
"""
import sqlite3, json, hashlib
from contextlib import contextmanager

DB_PATH = "smc_quant.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def inicializar_db():
    with get_conn() as conn:
        conn.executescript("""
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
            user_id INTEGER NOT NULL REFERENCES users(id),
            fecha TEXT NOT NULL, activo TEXT NOT NULL,
            timeframe TEXT DEFAULT '15m', direccion TEXT NOT NULL,
            entrada REAL NOT NULL, sl REAL NOT NULL, tp REAL NOT NULL,
            riesgo_usd REAL DEFAULT 0, resultado_usd REAL DEFAULT 0,
            rr_planeado REAL DEFAULT 0, rr_real REAL DEFAULT 0,
            setup TEXT DEFAULT '', emocion TEXT DEFAULT 'Neutral',
            notas TEXT DEFAULT '', tags TEXT DEFAULT '[]',
            estado TEXT DEFAULT 'Cerrado',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            ticker TEXT NOT NULL, alias TEXT DEFAULT '',
            UNIQUE(user_id, ticker)
        );
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            ticker TEXT NOT NULL, tipo TEXT NOT NULL,
            precio REAL NOT NULL, mensaje TEXT DEFAULT '',
            activa INTEGER DEFAULT 1, disparada INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            fired_at TEXT DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS bot_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
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
            user_id INTEGER NOT NULL REFERENCES users(id),
            ticker TEXT NOT NULL, timeframe TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL, fecha_fin TEXT NOT NULL,
            total_trades INTEGER DEFAULT 0, win_rate REAL DEFAULT 0,
            profit_factor REAL DEFAULT 0, total_pnl REAL DEFAULT 0,
            max_drawdown REAL DEFAULT 0, sharpe REAL DEFAULT 0,
            parametros TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS signal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL, timeframe TEXT NOT NULL,
            tipo TEXT NOT NULL, direccion TEXT NOT NULL,
            confianza REAL DEFAULT 0, precio REAL DEFAULT 0,
            sl REAL DEFAULT 0, tp REAL DEFAULT 0,
            enviada_bot INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        # Migración segura — añadir columnas nuevas si no existen en DBs antiguas
        for table, col, definition in [
            ("users", "is_admin",  "INTEGER DEFAULT 0"),
            ("users", "is_active", "INTEGER DEFAULT 1"),
        ]:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            except sqlite3.OperationalError:
                pass  # ya existe

    crear_usuario("demo", "demo123", capital_inicial=10000.0)
    _crear_superadmin("moises og", "1977Emog", capital_inicial=10000.0)


def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()


def _crear_superadmin(username: str, password: str, capital_inicial: float = 10000.0):
    """Crea o actualiza el superadmin — garantizado en cada arranque."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username=?", (username.strip().lower(),)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET is_admin=1, is_active=1 WHERE username=?",
                (username.strip().lower(),)
            )
        else:
            conn.execute(
                "INSERT INTO users (username,password_hash,capital_inicial,is_admin,is_active) "
                "VALUES (?,?,?,1,1)",
                (username.strip().lower(), _hash(password), capital_inicial)
            )


# ── Users ──────────────────────────────────────────────────────────────────────

def crear_usuario(username, password, capital_inicial=1000.0):
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username,password_hash,capital_inicial) VALUES (?,?,?)",
                (username.strip().lower(), _hash(password), capital_inicial)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def autenticar_usuario(username, password):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=1",
            (username.strip().lower(), _hash(password))
        ).fetchone()
        return dict(row) if row else None


def actualizar_capital(user_id, capital):
    with get_conn() as conn:
        conn.execute("UPDATE users SET capital_inicial=? WHERE id=?", (capital, user_id))


def obtener_todos_usuarios():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id,username,capital_inicial,created_at,is_admin,is_active "
            "FROM users ORDER BY created_at DESC"
        ).fetchall()]


# ── Admin ──────────────────────────────────────────────────────────────────────

def admin_crear_usuario(username: str, password: str, capital: float = 1000.0) -> bool:
    return crear_usuario(username, password, capital)


def admin_eliminar_usuario(user_id: int) -> bool:
    """
    Elimina permanentemente un usuario y TODOS sus datos.
    Protegido: no puede eliminar admins.
    """
    with get_conn() as conn:
        # Verificar que no sea admin
        row = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
        if not row or row["is_admin"]:
            return False
        # Borrar en cascada todos los datos del usuario
        conn.execute("DELETE FROM trades        WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM watchlist     WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM price_alerts  WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM bot_config    WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM backtest_results WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM users         WHERE id=? AND is_admin=0", (user_id,))
    return True


def admin_resetear_password(user_id: int, nueva_password: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (_hash(nueva_password), user_id)
        )


def admin_actualizar_capital(user_id: int, capital: float):
    actualizar_capital(user_id, capital)


def admin_stats_globales() -> dict:
    with get_conn() as conn:
        return {
            "total_users":        conn.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0],
            "total_trades":       conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0],
            "total_senales":      conn.execute("SELECT COUNT(*) FROM signal_log").fetchone()[0],
            "bots_activos":       conn.execute(
                "SELECT COUNT(*) FROM bot_config WHERE alertas_activas=1 AND telegram_chat_id!=''"
            ).fetchone()[0],
            "senales_hoy":        conn.execute(
                "SELECT COUNT(*) FROM signal_log WHERE created_at >= date('now')"
            ).fetchone()[0],
            "alertas_pendientes": conn.execute(
                "SELECT COUNT(*) FROM price_alerts WHERE activa=1 AND disparada=0"
            ).fetchone()[0],
            "trades_hoy":         conn.execute(
                "SELECT COUNT(*) FROM trades WHERE fecha >= date('now')"
            ).fetchone()[0],
        }


def admin_logs_senales(limite: int = 100) -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM signal_log ORDER BY created_at DESC LIMIT ?", (limite,)
        ).fetchall()]


def admin_trades_todos(limite: int = 100) -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT t.*, u.username FROM trades t
            JOIN users u ON t.user_id=u.id
            ORDER BY t.created_at DESC LIMIT ?
        """, (limite,)).fetchall()]


def admin_configs_bot_todas() -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT bc.*, u.username FROM bot_config bc
            JOIN users u ON bc.user_id=u.id ORDER BY u.username
        """).fetchall()]


# ── Trades ─────────────────────────────────────────────────────────────────────

def insertar_trade(user_id, data):
    riesgo    = abs(data['entrada'] - data['sl'])
    beneficio = abs(data['tp'] - data['entrada'])
    rr        = round(beneficio / riesgo, 2) if riesgo > 0 else 0
    rr_real   = round(data['resultado_usd'] / abs(data['riesgo_usd']), 2) \
                if data.get('resultado_usd') and data.get('riesgo_usd') else 0.0
    with get_conn() as conn:
        cur = conn.execute("""INSERT INTO trades
            (user_id,fecha,activo,timeframe,direccion,entrada,sl,tp,
             riesgo_usd,resultado_usd,rr_planeado,rr_real,setup,emocion,notas,tags,estado)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, data['fecha'], data['activo'], data.get('timeframe','15m'),
             data['direccion'], data['entrada'], data['sl'], data['tp'],
             data.get('riesgo_usd',0), data.get('resultado_usd',0), rr, rr_real,
             data.get('setup',''), data.get('emocion','Neutral'),
             data.get('notas',''), json.dumps(data.get('tags',[])),
             data.get('estado','Cerrado')))
        return cur.lastrowid


def obtener_trades(user_id):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM trades WHERE user_id=? ORDER BY fecha DESC, id DESC", (user_id,)
        ).fetchall()]


def eliminar_trade(trade_id, user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM trades WHERE id=? AND user_id=?", (trade_id, user_id))


# ── Watchlist ──────────────────────────────────────────────────────────────────

def obtener_watchlist(user_id):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM watchlist WHERE user_id=?", (user_id,)
        ).fetchall()]


def agregar_watchlist(user_id, ticker, alias=""):
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO watchlist (user_id,ticker,alias) VALUES (?,?,?)",
                         (user_id, ticker.upper(), alias))
        return True
    except sqlite3.IntegrityError:
        return False


def eliminar_watchlist(user_id, ticker):
    with get_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE user_id=? AND ticker=?", (user_id, ticker))


# ── Price Alerts ───────────────────────────────────────────────────────────────

def crear_alerta(user_id, ticker, tipo, precio, mensaje=""):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO price_alerts (user_id,ticker,tipo,precio,mensaje) VALUES (?,?,?,?,?)",
            (user_id, ticker, tipo, precio, mensaje))
        return cur.lastrowid


def obtener_alertas(user_id, solo_activas=True):
    with get_conn() as conn:
        q = "SELECT * FROM price_alerts WHERE user_id=?"
        if solo_activas: q += " AND activa=1 AND disparada=0"
        return [dict(r) for r in conn.execute(q + " ORDER BY created_at DESC", (user_id,)).fetchall()]


def obtener_todas_alertas_activas():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT pa.*, u.username FROM price_alerts pa "
            "JOIN users u ON pa.user_id=u.id WHERE pa.activa=1 AND pa.disparada=0"
        ).fetchall()]


def disparar_alerta(alert_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE price_alerts SET disparada=1, fired_at=datetime('now') WHERE id=?", (alert_id,))


def eliminar_alerta(alert_id, user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM price_alerts WHERE id=? AND user_id=?", (alert_id, user_id))


# ── Bot Config ─────────────────────────────────────────────────────────────────

def obtener_bot_config(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM bot_config WHERE user_id=?", (user_id,)).fetchone()
        if row: return dict(row)
        conn.execute("INSERT INTO bot_config (user_id) VALUES (?)", (user_id,))
        return dict(conn.execute("SELECT * FROM bot_config WHERE user_id=?", (user_id,)).fetchone())


def actualizar_bot_config(user_id, **kwargs):
    if not kwargs: return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    with get_conn() as conn:
        conn.execute(f"UPDATE bot_config SET {sets} WHERE user_id=?",
                     list(kwargs.values()) + [user_id])


def obtener_todas_configs_bot():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT bc.*, u.username FROM bot_config bc JOIN users u ON bc.user_id=u.id "
            "WHERE bc.alertas_activas=1 AND bc.telegram_chat_id!=''"
        ).fetchall()]


# ── Signal Log ─────────────────────────────────────────────────────────────────

def registrar_señal(ticker, timeframe, tipo, direccion, confianza, precio, sl, tp):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO signal_log (ticker,timeframe,tipo,direccion,confianza,precio,sl,tp) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ticker, timeframe, tipo, direccion, confianza, precio, sl, tp))
        return cur.lastrowid


def marcar_señal_enviada(signal_id):
    with get_conn() as conn:
        conn.execute("UPDATE signal_log SET enviada_bot=1 WHERE id=?", (signal_id,))


def obtener_señales_recientes(horas=24):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM signal_log WHERE created_at >= datetime('now',?) ORDER BY created_at DESC",
            (f"-{horas} hours",)).fetchall()]


# ── Backtest ───────────────────────────────────────────────────────────────────

def guardar_backtest(user_id, data):
    with get_conn() as conn:
        cur = conn.execute("""INSERT INTO backtest_results
            (user_id,ticker,timeframe,fecha_inicio,fecha_fin,
             total_trades,win_rate,profit_factor,total_pnl,max_drawdown,sharpe,parametros)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, data['ticker'], data['timeframe'], data['fecha_inicio'], data['fecha_fin'],
             data['total_trades'], data['win_rate'], data['profit_factor'],
             data['total_pnl'], data['max_drawdown'], data['sharpe'],
             json.dumps(data.get('parametros',{}))))
        return cur.lastrowid


def obtener_backtests(user_id):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM backtest_results WHERE user_id=? ORDER BY created_at DESC", (user_id,)
        ).fetchall()]
