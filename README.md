# DataForge v3

A modern, stateless data analysis and automated machine learning platform.

## Architecture & Tech Stack

DataForge v3 is built for production, featuring a fully stateless API and a robust background task processing engine.

* **Web Framework:** Flask (stateless, session-free architecture)
* **Real-time UX:** Flask-SocketIO (Redis message queue)
* **Background Tasks:** Celery + Redis
* **Data Storage Engines:**
  * **Primary Format:** Parquet (Snappy compression)
  * **Fast Querying (Previews):** DuckDB
  * **Object Storage:** Supabase Storage (or local disk fallback)
  * **Relational DB:** PostgreSQL (Supabase) or SQLite (local config)
* **Metadata/Models:** JSON (`orjson` accelerated) and Joblib

## Core Services

The platform is divided into interacting microservices, managed via Docker Compose:

1. **`web`**: The main Flask API and Frontend serving standard HTTP traffic.
2. **`worker`**: Celery workers executing heavy tasks (AutoML, EDA profiling, generating PDF/HTML reports).
3. **`beat`**: Celery Beat scheduler executing CRON jobs (e.g., repeating daily email reports, threshold alerts).
4. **`redis`**: In-memory data store acting as the Celery broker, SocketIO message queue, and application Read-Through Cache.
5. **`flower`**: Real-time monitor and web admin for Celery clusters (accessible on port `5555`).

## Repository Layout

```text
DataForge_v3/
├── docker-compose.yml       # Primary orchestration
├── requirements.txt         # Common dependencies
├── app.py                   # Local dev shim pointing to web service
├── .env.example             # Template for required environment variables
├── shared/                  # Domain driven core logic mapping to business entities
│   └── dataforge/           # Contains models, pipelines, connectors, report parsers
│       ├── anomaly_insight.py
│       ├── automl_trainer.py
│       ├── models.py        # SQLAlchemy schema (User, Job, Alert, Upload, etc.)
│       └── supabase_storage.py
└── services/
    └── web/                 # The actual web microservice implementation
        ├── app.py           # The Flask application factory & routes
        ├── celery_app.py    # Celery ContextTask factory
        ├── tasks.py         # Declarative background Celery tasks
        ├── cache.py         # Redis caching layer
        ├── Dockerfile       # Container build instructions
        ├── templates/       # HTML
        └── static/          # CSS/JS
```

## Running the Application

### Method 1: Docker (Recommended)

Docker Compose configures the entire stack (Web, Redis, Worker, Beat, Flower) instantly.

1. Ensure Docker Desktop is running.
2. Copy `.env.example` to `.env` and configure keys (at minimum, set `FLASK_SECRET_KEY`).
3. Build and launch:
   ```bash
   docker compose up --build
   ```
4. Access the App: http://localhost:5000
5. Access Celery Flower Admin: http://localhost:5555

### Method 2: Local Python Execution

If you prefer to run services natively (mostly for development/debugging):

1. **Prerequisites:** Python 3.10+ and a globally running Redis Server (`redis-server`).
2. **Install deps:** `pip install -r requirements.txt`
3. **Environment:** Copy `.env.example` to `.env` and set `REDIS_URL=redis://localhost:6379/0`.
4. **Initialize DB:** `python services/web/migrate_db.py`
5. **Run Web:** `python app.py` (or `flask --app services/web/app run`)
6. **Run Worker (in a new terminal):** 
   ```bash
   # Linux / macOS
   celery -A services.web.tasks worker --loglevel=info
   # Windows
   celery -A services.web.tasks worker --pool=solo --loglevel=info
   ```

## Essential Environment Variables

Create a `.env` file in the project root:

| Variable | Description | Requirement |
|---|---|---|
| `FLASK_SECRET_KEY` | UUID/Hash used for signing | **Required** |
| `REDIS_URL` | Redis connection string (e.g. `redis://redis:6379/0`) | **Required** |
| `DATABASE_URL` | Postgres/Supabase DB connection string | Optional (falls back to local SQLite) |
| `SUPABASE_URL` | Supabase project URL | Optional (falls back to local filesystem object storage) |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Required if `SUPABASE_URL` is set |
| `SUPABASE_BUCKET` | Supabase bucket name for parquets | Required if `SUPABASE_URL` is set |
| `GOOGLE_CLIENT_ID` | OAuth2 Client ID for Google Login | Optional |
| `GEMINI_API_KEY` | Google Gemini key for LLM-assisted data insights | Optional |

## Development Patterns

- **Stateless Requests:** Do not use `flask.session` to store anything mutable (like DataFrames or project state). Routes should ingest an `upload_id` and rely on `_upath(...)` and `_load(...)`.
- **Backgrounding Heavy Tasks:** Any route that blocks for > 1 second (AutoML, complex insights) must be structured as an asynchronous Celery task in `tasks.py` and returned a `202 Accepted` to the frontend with a `{ "task_id": job.id }` for polling.
- **SQLAlchemy Jobs:** Background process tracking belongs in the `Job` SQLAlchemy model.
