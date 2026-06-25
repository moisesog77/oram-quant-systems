#!/usr/bin/env python3
"""
reset_db.py — Limpieza de datos para producción.

Borra todos los datos de trading conservando:
  - Usuario superadmin (is_admin=1) y su contraseña
  - bot_config del superadmin (Chat ID Telegram, umbral, activos, etc.)

Tablas limpiadas:
  trades, signal_log, watchlist, price_alerts,
  backtest_results, confirmed_trades

USO:
    python reset_db.py            → modo interactivo (pide confirmación)
    python reset_db.py --force    → sin confirmación (Railway terminal)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import get_conn, _exec, USE_POSTGRES


def limpiar_datos(force: bool = False):
    motor = "PostgreSQL" if USE_POSTGRES else "SQLite local"
    print(f"\n⚠️  LIMPIEZA DE BASE DE DATOS — {motor}")
    print("   Borra : trades, señales, watchlist, alertas, backtests, confirmed_trades")
    print("   Conserva: superadmin + bot_config (configuración del bot)\n")

    if not force:
        confirm = input("Escribe 'CONFIRMAR' para continuar: ")
        if confirm.strip() != "CONFIRMAR":
            print("Cancelado.")
            return

    with get_conn() as conn:
        # 1. Borrar usuarios NO admin (registros de prueba / invitados)
        _exec(conn, "DELETE FROM users WHERE is_admin = 0 OR is_admin IS NULL")
        print("  ✓ users — solo queda superadmin")

        # 2. Limpiar bot_config huérfanas (usuarios que ya no existen)
        _exec(conn,
            "DELETE FROM bot_config WHERE user_id NOT IN "
            "(SELECT id FROM users WHERE is_admin = 1)"
        )
        print("  ✓ bot_config — configuración del superadmin conservada")

        # 3. Limpiar tablas de datos
        tablas = [
            "trades",
            "signal_log",
            "watchlist",
            "price_alerts",
            "backtest_results",
            "confirmed_trades",
        ]
        for tabla in tablas:
            try:
                _exec(conn, f"DELETE FROM {tabla}")
                print(f"  ✓ {tabla}")
            except Exception as e:
                print(f"  ⚠ {tabla}: {e}")

    print("\n✅ Limpieza completada.")
    print("   Superadmin conservado con contraseña original.")
    print("   Configuración del bot (Chat ID, umbral, activos) conservada.")
    print("   Todos los datos de trading eliminados.\n")


if __name__ == "__main__":
    force = "--force" in sys.argv
    limpiar_datos(force=force)
