# DataForge v3

A Flask-based data analysis, insight generation, and automated machine learning app.

## Architecture

The repo is organized into two top-level folders:

- **`backend/`** contains the Python monolith: Flask routes, Celery tasks, analytics engines, storage/database helpers, connectors, schema, Dockerfile, and Python dependencies.
- **`frontend/`** contains the server-rendered UI assets: Jinja templates and static files used by the Flask backend.

Redis, Celery workers, Celery Beat, and Flower are still used at runtime, but they run the same backend codebase rather than separate application services.

## Runtime Processes

Docker Compose starts these cooperating processes:

1. **`web`**: Runs the Flask app from `backend/app.py`.
2. **`worker`**: Runs Celery tasks from `dataforge.web.tasks`.
3. **`beat`**: Runs scheduled Celery jobs.
4. **`redis`**: Provides broker, result backend, Socket.IO queue, and cache support.
5. **`flower`**: Provides Celery monitoring on port `5555`.

## Repository Layout

```text
DataForge_v3/
├── backend/
│   ├── app.py                 # Flask/SocketIO entry point
│   ├── Dockerfile             # Container build
│   ├── requirements.txt       # Python dependencies
│   ├── migrate_db.py          # Prints schema path to apply
│   ├── database/
│   │   └── schema.sql         # Supabase database schema
│   └── dataforge/
│       ├── web/               # Flask app, blueprints, Celery, storage, cache
│       │   ├── app.py
│       │   ├── celery_app.py
│       │   ├── tasks.py
│       │   ├── routes/
│       │   └── storage.py
│       ├── settings.py
│       ├── db.py
│       ├── *_insight.py
│       ├── automl_trainer.py
│       ├── eda_report.py
│       └── *_connector.py
├── frontend/
│   ├── templates/             # Jinja HTML templates
│   └── static/                # Static assets served by Flask
├── docker-compose.yml
├── DEPLOYMENT.md
└── README.md
```

Local runtime artifacts default to `backend/instance/projects`. Override with `DATAFORGE_PROJECTS_DIR` when needed.

## Running With Docker

1. Ensure Docker Desktop is running.
2. Create `.env` in the project root and set at least `FLASK_SECRET_KEY`, `REDIS_URL`, `SUPABASE_URL`, and `SUPABASE_SERVICE_KEY`.
3. Build and start:

   ```bash
   docker compose up --build
   ```

4. Open the app at http://localhost:5000.
5. Open Flower at http://localhost:5555.

## Running Locally

1. Install Python 3.10+ and start Redis locally.
2. Install dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

3. Create `.env` in the project root and set `REDIS_URL=redis://localhost:6379/0` plus your Supabase/Auth keys.
4. Apply `backend/database/schema.sql` in your Supabase SQL editor.
5. Run the web app:

   ```bash
   python backend/app.py
   ```

6. In another terminal, run the Celery worker from the backend folder:

   ```bash
   cd backend
   celery --app=dataforge.web.tasks:celery worker --loglevel=info
   ```

   On Windows, use:

   ```bash
   cd backend
   celery --app=dataforge.web.tasks:celery worker --pool=solo --loglevel=info
   ```

7. Optional scheduler and monitor:

   ```bash
   cd backend
   celery --app=dataforge.web.tasks:celery beat --loglevel=info
   celery --app=dataforge.web.tasks:celery flower --port=5555
   ```

## Environment Variables

| Variable | Description | Requirement |
|---|---|---|
| `FLASK_SECRET_KEY` | Secret used for signing Flask sessions | Required |
| `REDIS_URL` | Redis connection string | Required |
| `SUPABASE_URL` | Supabase project URL/API base | Required |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Required |
| `DATAFORGE_PROJECTS_DIR` | Local project artifact directory | Optional |
| `SUPABASE_BUCKET` | Supabase bucket for persisted artifacts | Optional |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Optional |
| `GEMINI_API_KEY` | Gemini key for LLM-assisted insights | Optional |
| `GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_SA_JSON_CONTENT` | Private Google Sheets credentials | Optional |

## Development Notes

- Keep Python application code in `backend/dataforge`.
- Keep Flask routes, Celery tasks, and backend web glue in `backend/dataforge/web`.
- Keep Jinja templates in `frontend/templates`.
- Keep static files in `frontend/static`.
- Long-running work should remain in Celery tasks and return a task id for polling.
