# Deployment Guide

This document covers running DataForge in **local development** mode and promoting it to **production**.

---

## Local Development

The simplest way to run DataForge is directly on your machine.

### What's running locally

| Process | Command | Port |
|---------|---------|------|
| Flask web server | `python app.py` | 5000 |
| Celery worker | `celery ... worker` | — |
| Celery Beat | `celery ... beat` | — |
| Flower monitor | `celery ... flower` | 5555 |
| Redis | System service | 6379 |

> **Redis and Celery are optional.** If no worker is active, the app executes tasks synchronously inline (controlled by `DATAFORGE_SYNC_FALLBACK=1`).

### Running

See the full setup guide in [README.md](README.md) — specifically Steps 1–6.

```bash
# Quick-start (after venv + pip install):
cd backend && python app.py
```

---

## Production Deployment

### Why Gunicorn?

Flask's built-in development server (`python app.py`) is **single-process** and not designed for production traffic or long-running WebSocket connections. For production, use **Gunicorn** with the **eventlet** async worker, which is required by Flask-SocketIO.

### Install Production Dependencies

```bash
pip install gunicorn eventlet
```

### Production Start Command

Run from the `backend/` directory with the `venv` active:

```bash
gunicorn \
  --worker-class eventlet \
  --workers 1 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --keep-alive 5 \
  dataforge.web.wsgi:app
```

> Use `--workers 1` with eventlet. Multiple workers + SocketIO requires a Redis message queue (already configured via `REDIS_URL`).

### Production Celery Worker

```bash
# Linux / macOS (production)
celery --app=dataforge.web.tasks:celery worker \
  --loglevel=warning \
  --pool=prefork \
  --concurrency=2 \
  --queues=celery
```

### Environment Variables for Production

Ensure these are set in your production environment (or a secrets manager — do **not** commit `.env` to source control):

| Variable | Required | Notes |
|----------|----------|-------|
| `FLASK_SECRET_KEY` | **YES** | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GEMINI_API_KEY` | Recommended | AI features disabled without it |
| `SUPABASE_URL` | **YES** | Your Supabase project URL |
| `SUPABASE_KEY` | **YES** | Service role key |
| `SUPABASE_BUCKET` | Recommended | Remote file storage |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth |
| `REDIS_URL` | Recommended | Celery + WebSocket pub/sub |

### Platform-Specific Notes

**Render / Railway / Fly.io**
- Set all env vars in the dashboard secrets panel.
- Start command: `gunicorn -k eventlet -w 1 --timeout 120 dataforge.web.wsgi:app`
- Run from `backend/` directory or set `PYTHONPATH=backend`.

**VPS / Self-hosted**
- Use `systemd` or `supervisor` to manage the Flask, Celery worker, and Celery beat processes.
- Place Nginx in front of Gunicorn to handle TLS and static files.

---

## Troubleshooting

**App fails with `KeyError: 'FLASK_SECRET_KEY'`**
→ Your `.env` file is missing or not being loaded. Run from the project root or `backend/` so `python-dotenv` finds the `.env`.

**Celery tasks stay PENDING forever**
→ No Celery worker is running, and `DATAFORGE_SYNC_FALLBACK=0`. Either start a worker or set `DATAFORGE_SYNC_FALLBACK=1`.

**`SUPABASE_URL and SUPABASE_SERVICE_KEY must be set` error**
→ Add both variables to your `.env`. See `.env.example` for the correct names.

**WebSockets not working in production**
→ Ensure you're using `gunicorn -k eventlet` (not prefork) and your proxy (Nginx/Render) supports WebSocket upgrades.
