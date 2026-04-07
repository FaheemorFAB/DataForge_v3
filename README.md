# DataForge v3

A modern, stateless data analysis and automated machine learning platform.

## Architecture & Tech Stack

DataForge v3 is built around a Flask web app plus a small async processing stack.

- **Web/API:** Flask serves the HTTP app and templates.
- **Authentication:** A dedicated `auth` Flask service manages Google OAuth and issues the shared session consumed by `web`.
- **Real-time UX:** Flask-SocketIO pushes progress/events to the browser.
- **Async jobs:** Celery runs long-running jobs such as insights, AutoML, EDA, alerts, and scheduled reports.
- **Broker / message backbone:** Redis is the Celery broker/result backend and the Socket.IO message queue in this repo.
- **Data layer:** pandas + NumPy power the in-memory analysis pipeline.
- **Storage:** Parquet files on disk, Supabase for database/object storage, and DuckDB for fast preview queries.
- **ML / profiling:** FLAML + scikit-learn for AutoML, ydata-profiling for rich EDA reports.

Celery note:
Celery is not the same thing as RabbitMQ. Celery is the task queue framework; RabbitMQ is one possible message broker for it. In this project, Celery is configured to use Redis, not RabbitMQ.

## Core Services

The platform is divided into interacting microservices, managed via Docker Compose:

1. **`web`**: The main Flask API and frontend serving standard HTTP traffic and Socket.IO.
2. **`auth`**: Dedicated login service for Google OAuth and shared session management.
3. **`worker`**: Celery workers executing heavy tasks such as AutoML, EDA profiling, alerts, and report generation.
4. **`beat`**: Celery Beat scheduler for periodic jobs.
5. **`redis`**: In-memory data store acting as the Celery broker, Socket.IO message queue, and application cache.
6. **`flower`**: Real-time monitor and web admin for Celery clusters on port `5555`.

## Dependency Audit

The current `requirements.txt` is mostly valid, but not every package is used in the same way. Some are core runtime dependencies, some are optional paths, and one appears to be redundant.

| Requirement | What it does here | Where it is used | Status |
|---|---|---|---|
| `Flask` | Main web framework and route handling | `services/web/app.py` | Used |
| `Flask-SocketIO` | WebSocket/event pushes from web and worker processes | `services/web/app.py`, `services/web/tasks.py` | Used |
| `Flask-Login` | Login/session protection for routes | `services/web/app.py` | Used |
| `pandas` | Main dataframe engine | Used across `services/web/*` and `shared/dataforge/*` | Used |
| `numpy` | Numeric operations and statistics | Used across `services/web/*` and `shared/dataforge/*` | Used |
| `python-dotenv` | Loads `.env` values into the app/worker process | `services/web/app.py`, `services/web/tasks.py`, `shared/dataforge/gemini_pipeline.py`, `shared/dataforge/supabase_storage.py` | Used |
| `Authlib` | Google OAuth client support | `services/auth/app.py` | Used |
| `requests` | HTTP access for API connectors and Google Sheets public import | `shared/dataforge/api_connector.py`, `shared/dataforge/sheets_connector.py` | Used |
| `duckdb` | Fast SQL previews over Parquet files | `services/web/app.py` | Used |
| `pyarrow` | Parquet engine behind `pandas.read_parquet()` / `to_parquet()` | Indirect via pandas parquet reads/writes in `services/web/app.py` and `services/web/tasks.py` | Used indirectly |
| `filelock` | Prevents concurrent file corruption for cached/parquet/joblib/json artifacts | `services/web/app.py`, `services/web/tasks.py` | Used |
| `celery` | Background task queue framework | `services/web/celery_app.py`, `services/web/tasks.py`, `services/web/app.py` | Used |
| `redis` | Python client for cache access and Socket.IO/Celery connectivity checks | `services/web/cache.py`, `services/web/app.py`, `shared/dataforge/cache_manager.py` | Used |
| `orjson` | Fast JSON serialization for Redis cache payloads | `services/web/cache.py` | Used |
| `flower` | Celery monitoring UI/CLI service | `docker-compose.yml` (`flower` service command) | Used via service/CLI |
| `joblib` | Not directly imported by project code; files are stored with a `.joblib` extension, but model serialization currently uses `pickle` bytes | No direct import found | Probably redundant |
| `supabase` | Database and storage client | `shared/dataforge/db.py`, `shared/dataforge/supabase_storage.py` | Used |
| `pydantic` | Typed models for database entities | `shared/dataforge/db.py` | Used |
| `scikit-learn` | Train/test split and evaluation metrics for AutoML | `shared/dataforge/automl_trainer.py` | Used |
| `flaml[default]` | AutoML engine | `shared/dataforge/automl_trainer.py` | Used |
| `ydata-profiling` | Full HTML profiling report generation with fallback to lightweight pandas report | `shared/dataforge/eda_report.py` | Used optionally |
| `gspread` | Private Google Sheets access via service account | `shared/dataforge/sheets_connector.py` | Optional / partially wired |
| `spacy` | Better natural-language column matching in the deterministic query engine | `shared/dataforge/deterministic_engine.py` | Optional at runtime |
| `watchdog` | File-system watching for CSV drop-folder ingestion helper | `shared/dataforge/csv_connector.py` | Optional / helper-only |

Notes:
`joblib` is the only dependency that currently looks unnecessary from a direct code-usage standpoint.
`pyarrow` is still needed even without an explicit import because pandas Parquet support depends on it.
`flower` is expected to be absent from Python imports because it is launched as a service/CLI, not imported as a library.
`gspread`, `spacy`, and `watchdog` are valid dependencies, but they support optional code paths rather than the main happy-path UI flow.
Private Google Sheets access also references `gspread-dataframe` and `google-auth`, and spaCy support expects the `en_core_web_sm` model. Those extras are not currently listed in `requirements.txt`.

## Repository Layout

```text
DataForge_v3/
├── docker-compose.yml       # Multi-service local orchestration
├── requirements.txt         # Shared Python dependencies
├── app.py                   # Legacy local entry shim
├── .env.example             # Example environment variables
├── shared/
│   └── dataforge/           # Shared domain logic, DB/storage helpers, ML/reporting modules
├── services/
│   ├── auth/                # Dedicated auth service
│   │   ├── app.py
│   │   ├── shared.py
│   │   ├── wsgi.py
│   │   └── templates/
│   └── web/                 # Main web/API service
│       ├── app.py
│       ├── celery_app.py
│       ├── tasks.py
│       ├── cache.py
│       ├── Dockerfile
│       ├── wsgi.py
│       ├── templates/
│       └── static/
└── supabase/
    └── schema.sql
```

## Running the Application

### With Docker (Recommended)

This is the easiest way to run the full stack because it starts `web`, `auth`, `redis`, `worker`, `beat`, and `flower` together.

1. Copy the example env file and fill in your real values:
   ```bash
   cp .env.example .env
   ```
   PowerShell:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Set at least these variables in `.env`:
   - `FLASK_SECRET_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `REDIS_URL=redis://redis:6379/0`
   - `AUTH_BASE_URL=http://localhost:5001`
   - `WEB_BASE_URL=http://localhost:5000`
3. If you want Google login locally, also set:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
4. Build and start everything:
   ```bash
   docker compose up --build
   ```
5. Open:
   - App UI: `http://localhost:5000`
   - Auth login: `http://localhost:5001/login`
   - Flower: `http://localhost:5555`
6. If Google OAuth is enabled, use this callback URL in Google Cloud:
   ```text
   http://localhost:5001/auth/google/callback
   ```

Helpful Docker commands:

```bash
docker compose down
docker compose logs -f web
docker compose logs -f auth
docker compose logs -f worker
```

### Without Docker

Run this way if you want to debug each process directly on your machine.

1. Install prerequisites:
   - Python 3.10+
   - Redis running locally
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` from `.env.example` and fill in your real keys.
   PowerShell:
   ```powershell
   Copy-Item .env.example .env
   ```
4. Apply `supabase/schema.sql` to your Supabase project.
5. Start the auth service in one terminal:
   ```bash
   gunicorn --worker-class gthread --threads 4 --workers 1 --bind 0.0.0.0:5001 services.auth.wsgi:app
   ```
6. Start the web service in a second terminal:
   ```bash
   gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 services.web.wsgi:app
   ```
7. Start the Celery worker in a third terminal:
   ```bash
   # Linux / macOS
   celery --app=services.web.tasks:celery worker --loglevel=info

   # Windows
   celery --app=services.web.tasks:celery worker --pool=solo --loglevel=info
   ```
8. Optional: start beat and Flower in extra terminals:
   ```bash
   celery --app=services.web.tasks:celery beat --loglevel=info
   celery --app=services.web.tasks:celery flower --port=5555
   ```
9. Verify health:
   ```bash
   curl http://127.0.0.1:5001/healthz
   curl http://127.0.0.1:5000/healthz
   curl http://127.0.0.1:5000/api/health/background
   ```

If local imports fail because of package/version issues, Docker is the safer path because it installs from `requirements.txt` into a clean environment.

## Essential Environment Variables

Create a `.env` file in the project root:

| Variable | Description | Requirement |
|---|---|---|
| `FLASK_SECRET_KEY` | UUID/Hash used for signing | **Required** |
| `REDIS_URL` | Redis connection string (e.g. `redis://redis:6379/0`) | **Required** |
| `SUPABASE_URL` | Supabase project URL / API base | **Required** |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | **Required** |
| `AUTH_BASE_URL` | Public URL for the auth service (e.g. `http://localhost:5001`) | **Required for OAuth redirects** |
| `WEB_BASE_URL` | Public URL for the web service (e.g. `http://localhost:5000`) | **Required for auth return redirects** |
| `SUPABASE_BUCKET` | Supabase bucket name for persisted parquet/model artifacts | Optional |
| `GOOGLE_CLIENT_ID` | OAuth2 Client ID for Google Login | Optional |
| `GOOGLE_CLIENT_SECRET` | OAuth2 Client Secret for Google Login | Optional |
| `SESSION_COOKIE_SECURE` | Set to `1` behind HTTPS so session cookies are marked secure | Recommended in production |
| `GEMINI_API_KEY` | Google Gemini key for LLM-assisted data insights | Optional |
| `GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_SA_JSON_CONTENT` | Optional private Google Sheets credentials | Optional |

## Development Patterns

- **Stateless Requests:** Do not use `flask.session` to store anything mutable like DataFrames or project state. Routes should ingest an `upload_id` and rely on `_upath(...)` and `_load(...)`.
- **Backgrounding Heavy Tasks:** Any route that blocks for more than one second should be structured as an asynchronous Celery task in `tasks.py` and return a `202 Accepted` plus a `{ "task_id": job.id }` for polling.
- **Supabase Jobs:** Background process tracking belongs in the `jobs` table in Supabase.
