# 🚀 ORAM Quant Systems — Guía de Deploy

## PASO 1 — Configura tu token
Abre el archivo `.env` y reemplaza `TU_TOKEN_AQUI` con tu token real de Telegram:
```
TELEGRAM_BOT_TOKEN=tu_token_real_aqui
```

---

## PASO 2 — Subir a Railway (gratis)

1. Ve a https://railway.app y crea cuenta con GitHub
2. Haz clic en **"New Project"** → **"Deploy from GitHub repo"**
3. Sube esta carpeta a un repositorio de GitHub primero
4. En Railway → Settings → Variables → agrega:
   - `TELEGRAM_BOT_TOKEN` = tu token real
5. Railway detecta el `Procfile` automáticamente y arranca el bot

---

## PASO 3 — Subir a GitHub

```bash
git init
git add .
git commit -m "ORAM Quant Systems v5"
git remote add origin https://github.com/TU_USUARIO/oram-quant.git
git push -u origin main
```

⚠️ El archivo `.env` NO se sube a GitHub (está en .gitignore)
⚠️ La base de datos `smc_quant.db` tampoco se sube

---

## Comandos del bot en Telegram
- /start — Bienvenida y tu Chat ID
- /mercado — Resumen del mercado ahora
- /senales — Señales SMC activas
- /noticias — Eventos económicos del día
- /alertas — Historial de señales 24h
- /resumen — Reporte diario completo

---

## Jobs automáticos
- ✅ Señales SMC cada 15 minutos
- ✅ Alertas de precio cada 5 minutos  
- ✅ Resumen diario a las 8:00 AM CDMX

---

## Correr localmente (para pruebas)
```bash
pip install -r requirements.txt
python bot/telegram_bot.py
```
