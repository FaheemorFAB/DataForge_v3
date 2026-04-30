# Deployment

This document explains **what is running**, **why it works locally**, and **what will change for production** so everyone understands the deployment path.

**Current State (Local Docker)**
- The app runs with `python backend/app.py`, which calls `socketio.run(...)`.
- This uses the Werkzeug **development** server — it is fine for local testing but not designed for production load.
- Docker setup is only for local use right now.

**How To Run Locally (Docker)**
1. Create `.env` from `.env.example`.
2. Build and start: `docker compose up --build`
3. Open `http://localhost:5000`

**Why We Need Gunicorn In Production**
- Flask’s built-in server is single‑process and intended only for development.
- It is not designed for real traffic, stability, or long‑running WebSocket connections.
- Your project uses `flask_socketio`, which requires an async worker to keep WebSockets alive.

**Recommended Production Server**
- `gunicorn` = the main Python HTTP server
- `eventlet` (or `gevent`) = async worker required by SocketIO

**What Production Run Command Looks Like**
```bash
gunicorn -k eventlet -w 1 dataforge.web.wsgi:app
```
Run this from the `backend/` folder, or set `PYTHONPATH` to the absolute backend path. This uses `backend/dataforge/web/wsgi.py`, which is the backend WSGI entry point.

**What Changes When We Go Production**
- Add production dependencies: `gunicorn` + `eventlet`
- Change the Dockerfile or hosting command to use gunicorn instead of `python backend/app.py`
- Add health checks and proper logging
- Add platform‑specific steps (Render/Railway/Fly/VPS/etc.)

**When You’re Ready To Deploy**
Tell us the target platform and we’ll:
- Add production dependencies
- Update Docker/Docker Compose
- Provide exact deployment steps for that platform
