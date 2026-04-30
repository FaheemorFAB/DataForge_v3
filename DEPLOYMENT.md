# Deployment

This project now runs with one browser-facing process:

- Next.js frontend/proxy on host port `3000`
- Flask/Socket.IO backend UI/API internally on port `5000`

Celery worker, Celery Beat, Redis, and Flower run beside them.

## Local Docker Deployment

After the frontend conversion, rebuild the images:

```bash
docker compose up --build
```

Open the app at:

```text
http://localhost:3000
```

The Flask backend is not published to the host in Docker. It is available to containers as:

```text
http://web:5000
```

The frontend container uses:

```env
NEXT_PUBLIC_BACKEND_URL=http://web:5000
```

That value is correct inside Docker because Compose service names are DNS names.

For non-Docker local development, run Flask on another port, such as `5001`, and run Next on `3000`.

## Rebuild Rules

Rebuild everything after dependency or Dockerfile changes:

```bash
docker compose up --build
```

Rebuild only the frontend after changes in `frontend/`:

```bash
docker compose up --build frontend
```

Rebuild backend services after changes in `backend/requirements.txt`, `backend/Dockerfile`, or backend Python dependencies:

```bash
docker compose up --build web worker beat flower
```

Regular code changes may work with a restart, but rebuilding is the cleanest path while the app is still evolving.

## Production Shape

Recommended production services:

1. `frontend`: Next.js server or static-compatible Next deployment.
2. `web`: Flask/Socket.IO API server.
3. `worker`: Celery worker.
4. `beat`: Celery scheduler.
5. `redis`: broker and cache.

For a single VPS, Docker Compose is acceptable if you put a reverse proxy in front:

- `/` routes to Next on `frontend:3000`
- `/api/*` routes to Flask on `web:5000`
- Socket.IO routes should also reach Flask if you use live dashboard events

For managed platforms, deploy frontend and backend as separate services and set:

```env
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.example
```

## Backend Server Note

The current backend command is:

```bash
python backend/app.py
```

That uses Werkzeug through Flask-SocketIO and is fine for local Docker/testing. For production traffic, use a Socket.IO-compatible server such as Gunicorn with Eventlet or Gevent.

Example production command from the backend context:

```bash
gunicorn -k eventlet -w 1 dataforge.web.wsgi:app
```

Before switching to that command, add production dependencies such as `gunicorn` and `eventlet` to `backend/requirements.txt`, then rebuild the backend image.

## Health Checks

Backend health endpoint through the Next proxy:

```text
http://localhost:3000/api/health/background
```

Inside the Docker network, the same Flask endpoint is:

```text
http://web:5000/api/health/background
```

The `localhost:3000` URL should return `200` when the frontend and backend are connected.


