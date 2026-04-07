# Deployment

DataForge now deploys as separate runtime services:

- `web` on port `5000`: UI, API, Socket.IO, and Celery job orchestration
- `auth` on port `5001`: Google OAuth login/logout and shared session issuance
- `worker`: Celery workers for long-running tasks
- `beat`: Celery scheduler
- `redis`: broker, result backend, Socket.IO queue, and cache
- `flower` on port `5555`: Celery monitoring

## Production Runtime

Both HTTP services now use Gunicorn instead of Flask's dev server:

```bash
# web
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 services.web.wsgi:app

# auth
gunicorn --worker-class gthread --threads 4 --workers 1 --bind 0.0.0.0:5001 services.auth.wsgi:app
```

`eventlet` is used only for `web`, because Socket.IO needs an async worker.

## Required Environment

Set these in `.env` for local Docker and for your deployment platform:

```env
FLASK_SECRET_KEY=replace-me
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
REDIS_URL=redis://redis:6379/0

AUTH_BASE_URL=http://localhost:5001
WEB_BASE_URL=http://localhost:5000

GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

Optional but recommended for HTTPS deployments:

```env
SESSION_COOKIE_SECURE=1
SESSION_COOKIE_SAMESITE=Lax
# SESSION_COOKIE_DOMAIN=.your-domain.com
```

## Google OAuth Callback

Because auth is now its own service, Google OAuth must point to:

```text
http://localhost:5001/auth/google/callback
```

In production, replace `localhost:5001` with your public auth service URL.

## Docker Compose

Run the full stack with:

```bash
docker compose up --build
```

Available endpoints:

- App UI: `http://localhost:5000`
- Auth service: `http://localhost:5001/login`
- Flower: `http://localhost:5555`

## Persistence

The compose setup now mounts the paths the app actually uses:

- `/data/instance`
- `/data/store`

That keeps uploads, generated artifacts, and cached task outputs available across container restarts.

## Deploy Checklist

1. Set `AUTH_BASE_URL` and `WEB_BASE_URL` to the public URLs users will open.
2. Update the Google OAuth callback URL to the auth service.
3. Set `SESSION_COOKIE_SECURE=1` when serving over HTTPS.
4. Make sure `web`, `auth`, and `worker` all share the same `.env` values, especially `FLASK_SECRET_KEY`.
5. Keep Redis reachable by both `web` and `worker`.
