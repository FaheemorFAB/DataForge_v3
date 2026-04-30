# DataForge v3

DataForge is a data analysis app with a Next.js frontend, a Flask/Socket.IO backend, Celery background jobs, Redis, and Supabase-backed persistence.

## Quick Start

You can run DataForge either with Docker or directly on your machine.

### Option 1: Run With Docker

From the project root:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:3000
```

Docker starts the full stack:

```text
App:    http://localhost:3000
Flower: http://localhost:5555
```

In Docker, `localhost:3000` maps to the Next frontend container. Flask is an internal backend service at `web:5000` and is not exposed directly.

Stop everything with:

```bash
docker compose down
```

### Option 2: Run Without Docker

Use two terminals.

Terminal 1, start Flask:

```bash
pip install -r backend/requirements.txt
$env:PORT="5001"
python backend/app.py
```

Terminal 2, start Next:

```bash
cd frontend
npm install
$env:NEXT_PUBLIC_BACKEND_URL="http://127.0.0.1:5001"
npm run dev
```

Then open:

```text
http://localhost:3000
```

For local non-Docker mode, `frontend/.env.local` should point Next to Flask:

```env
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:5001
```

For full background job support without Docker, also run Redis locally and start the Celery worker from `backend/`.

## Architecture

- `frontend/` contains the Next.js front door. In Docker it is the only exposed app port and proxies the working Flask UI/API internally.
- `backend/` contains the Python monolith: Flask routes, API endpoints, Socket.IO, Celery tasks, analytics engines, storage/database helpers, connectors, and schema.
- Redis is used for Celery broker/results, Socket.IO queue support, and cache support.

## Runtime Processes

Docker Compose starts these services:

1. `frontend`: the only browser entry point, on `http://localhost:3000`.
2. `web`: internal Flask UI/API service, reachable by other containers as `http://web:5000`.
3. `worker`: Celery worker for long-running jobs.
4. `beat`: Celery scheduler.
5. `redis`: Broker/result backend.
6. `flower`: Celery monitoring on `http://localhost:5555`.

The browser should only use `http://localhost:3000`. Next proxies UI routes, API routes, static assets, and Socket.IO to the internal Flask service. In Docker, `NEXT_PUBLIC_BACKEND_URL=http://web:5000`.

## Repository Layout

```text
DataForge_v3/
  backend/
    app.py                    # Flask/Socket.IO entry point
    Dockerfile                # Backend image
    requirements.txt          # Python dependencies
    database/schema.sql       # Supabase schema
    dataforge/                # Analytics, web routes, tasks, helpers
  frontend/
    Dockerfile                # Next.js image
    pages/                    # Next TSX routes
    public/legacy/            # Legacy static copies kept for reference/fallback
    templates/                # Original Flask/Jinja templates kept for reference
    static/                   # Original static assets
  docker-compose.yml
  DEPLOYMENT.md
```

Local runtime artifacts default to `backend/instance/projects`. Override with `DATAFORGE_PROJECTS_DIR` if needed.

## Running With Docker

Yes, after adding the Next frontend you should rebuild the Docker images.

1. Ensure Docker Desktop is running.
2. Create `.env` in the project root and set at least:

   ```env
   FLASK_SECRET_KEY=...
   REDIS_URL=redis://redis:6379/0
   SUPABASE_URL=...
   SUPABASE_SERVICE_KEY=...
   ```

3. Build and start everything:

   ```bash
   docker compose up --build
   ```

4. Open:

   ```text
   App:    http://localhost:3000
   Flower: http://localhost:5555
   ```

   The backend is not published as a host port in Docker. It is available internally as `http://web:5000`.

If you only change frontend files, rebuild just the frontend:

```bash
docker compose up --build frontend
```

If you only change backend Python code or requirements, rebuild backend-dependent services:

```bash
docker compose up --build web worker beat flower
```

## Running Locally Without Docker

Start the Flask backend:

```bash
pip install -r backend/requirements.txt
$env:PORT="5001"
python backend/app.py
```

Start the Next frontend in another terminal:

```bash
cd frontend
npm install
$env:NEXT_PUBLIC_BACKEND_URL="http://127.0.0.1:5001"
npm run dev
```

For local Next-to-Flask API rewrites, `frontend/.env.local` should contain:

```env
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:5001
```

Open `http://localhost:3000`. Keep Flask running on `5001`, but use it as the backend only.

For background jobs, run a worker from the backend folder:

```bash
cd backend
celery --app=dataforge.web.tasks:celery worker --pool=solo --loglevel=info
```

Optional scheduler and monitor:

```bash
cd backend
celery --app=dataforge.web.tasks:celery beat --loglevel=info
celery --app=dataforge.web.tasks:celery flower --port=5555
```

## Environment Variables

| Variable | Description | Requirement |
|---|---|---|
| `FLASK_SECRET_KEY` | Secret used for Flask sessions | Required |
| `REDIS_URL` | Redis connection string | Required |
| `SUPABASE_URL` | Supabase project URL/API base | Required |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Required |
| `NEXT_PUBLIC_BACKEND_URL` | URL used by Next rewrites to reach Flask | Required for frontend |
| `DATAFORGE_PROJECTS_DIR` | Local project artifact directory | Optional |
| `SUPABASE_BUCKET` | Supabase bucket for persisted artifacts | Optional |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Optional |
| `GEMINI_API_KEY` | Gemini key for LLM-assisted insights | Optional |
| `GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_SA_JSON_CONTENT` | Private Google Sheets credentials | Optional |

## Development Notes

- Use `frontend/pages/*.tsx` for Next routes.
- The preserved UI HTML lives in `frontend/public/legacy/`.
- Keep backend API and long-running work in `backend/dataforge/web`.
- Long-running actions should return a task id and be handled by Celery.


