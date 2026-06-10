#!/usr/bin/env python3
"""
reset_db.py — Script de inicialización de BD para producción.
Elimina todos los datos y crea SOLO el superadmin "Moises OG".
Ejecutar UNA VEZ antes del deploy inicial a producción.

USO:
    python3 reset_db.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import get_conn, _exec, _hash, USE_POSTGRES

def reset_para_produccion():
    print("⚠️  RESET DE BASE DE DATOS PARA PRODUCCIÓN")
    print("   Esto eliminará TODOS los datos existentes.")
    confirm = input("Escribe 'CONFIRMAR' para continuar: ")
    if confirm != "CONFIRMAR":
        print("Cancelado.")
        return

    with get_conn() as conn:
        # Eliminar todos los usuarios excepto el que crearemos
        _exec(conn, "DELETE FROM users")
        # Eliminar todos los datos dependientes
        for table in ["trades", "watchlist", "price_alerts", "bot_config", 
                      "backtest_results", "signal_log"]:
            try:
                _exec(conn, f"DELETE FROM {table}")
            except Exception:
                pass  # tabla puede no existir aún

        # Crear SOLO el superadmin
        pw_hash = _hash("1977Emog")
        ph = "%s" if USE_POSTGRES else "?"
        conn.execute(
            f"INSERT INTO users (username, password_hash, capital_inicial, is_admin, is_active) "
            f"VALUES ({ph},{ph},{ph},{ph},{ph})",
            ("moises og", pw_hash, 10000.0, 1, 1)
        )
        print("✅ BD reseteada. Solo existe el superadmin 'moises og'.")
        print("   Credenciales: usuario=moises og | contraseña=1977Emog")

if __name__ == "__main__":
    reset_para_produccion()
