# DataForge v3

A modern, stateless data analysis and automated machine learning platform.

## Architecture & Tech Stack

DataForge v3 is built around a Flask web app plus a small async processing stack.

* **Web/API:** Flask serves the HTTP app and templates.
* **Authentication:** Flask-Login manages sessions, and Authlib handles Google OAuth when configured.
* **Real-time UX:** Flask-SocketIO pushes progress/events to the browser.
* **Async jobs:** Celery runs long-running jobs such as insights, AutoML, EDA, alerts, and scheduled reports.
* **Broker / message backbone:** Redis is the Celery broker/result backend and the Socket.IO message queue in this repo.
* **Data layer:** pandas + NumPy power the in-memory analysis pipeline.
* **Storage:** Parquet files on disk, Supabase for database/object storage, and DuckDB for fast preview queries.
* **ML / profiling:** FLAML + scikit-learn for AutoML, ydata-profiling for rich EDA reports.

Celery note:
Celery is not the same thing as RabbitMQ. Celery is the task queue framework; RabbitMQ is one possible message broker for it. In this project, Celery is configured to use Redis, not RabbitMQ.

## Core Services

The platform is divided into interacting microservices, managed via Docker Compose:

1. **`web`**: The main Flask API and Frontend serving standard HTTP traffic.
2. **`worker`**: Celery workers executing heavy tasks (AutoML, EDA profiling, generating PDF/HTML reports).
3. **`beat`**: Celery Beat scheduler for periodic jobs.
4. **`redis`**: In-memory data store acting as the Celery broker, Socket.IO message queue, and application cache.
5. **`flower`**: Real-time monitor and web admin for Celery clusters (accessible on port `5555`).

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
| `Authlib` | Google OAuth client support | `services/web/app.py` | Used |
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
├── docker-compose.yml       # Primary orchestration
├── requirements.txt         # Common dependencies
├── app.py                   # Local dev shim pointing to web service
├── .env                     # Local environment file (create this yourself)
├── shared/                  # Domain driven core logic mapping to business entities
│   └── dataforge/           # Contains models, pipelines, connectors, report parsers
│       ├── anomaly_insight.py
│       ├── automl_trainer.py
│       ├── db.py            # Supabase API client and helper functions
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
2. Create a `.env` file in the project root and configure keys (at minimum, set `FLASK_SECRET_KEY`).
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
3. **Environment:** Create `.env` and set `REDIS_URL=redis://localhost:6379/0` plus your Supabase/Auth keys as needed.
4. **Database:** Apply `supabase/schema.sql` to your Supabase project. There is no working local migration script checked into `services/web/` right now.
5. **Run Web:** `python app.py` (or `flask --app services/web/app run`)
6. **Run Worker (in a new terminal):** 
   ```bash
   # Linux / macOS
   celery --app=services.web.tasks:celery worker --loglevel=info
   # Windows
   celery --app=services.web.tasks:celery worker --pool=solo --loglevel=info
   ```
7. **Optional: Run Beat and Flower in separate terminals:**
   ```bash
   celery --app=services.web.tasks:celery beat --loglevel=info
   celery --app=services.web.tasks:celery flower --port=5555
   ```
8. **Verify async infra health (optional but recommended):**
   ```bash
   curl http://127.0.0.1:5000/api/health/background
   ```
   Expect `{"ok": true, ...}` when task imports and broker connectivity are healthy.

## Essential Environment Variables

Create a `.env` file in the project root:

| Variable | Description | Requirement |
|---|---|---|
| `FLASK_SECRET_KEY` | UUID/Hash used for signing | **Required** |
| `REDIS_URL` | Redis connection string (e.g. `redis://redis:6379/0`) | **Required** |
| `SUPABASE_URL` | Supabase project URL / API base | **Required** |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | **Required** |
| `SUPABASE_BUCKET` | Supabase bucket name for persisted parquet/model artifacts | Optional |
| `GOOGLE_CLIENT_ID` | OAuth2 Client ID for Google Login | Optional |
| `GOOGLE_CLIENT_SECRET` | OAuth2 Client Secret for Google Login | Optional |
| `GEMINI_API_KEY` | Google Gemini key for LLM-assisted data insights | Optional |
| `GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_SA_JSON_CONTENT` | Optional private Google Sheets credentials | Optional |

## Development Patterns

- **Stateless Requests:** Do not use `flask.session` to store anything mutable (like DataFrames or project state). Routes should ingest an `upload_id` and rely on `_upath(...)` and `_load(...)`.
- **Backgrounding Heavy Tasks:** Any route that blocks for > 1 second (AutoML, complex insights) must be structured as an asynchronous Celery task in `tasks.py` and returned a `202 Accepted` to the frontend with a `{ "task_id": job.id }` for polling.
- **Supabase Jobs:** Background process tracking belongs in the `jobs` table in Supabase.
