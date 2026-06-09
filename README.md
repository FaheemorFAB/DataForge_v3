# DataForge v3

A Flask-based data analysis, insight generation, and automated machine learning app.

> [!NOTE]
> **Monolithic Architecture**: This project is built as a single Python monolith. The frontend consists of Jinja HTML templates (`frontend/templates`) and static assets (`frontend/static`) served directly by the Flask server. There is **no separate frontend build step or npm server** (e.g. no `package.json` at the root). Running the Flask backend runs the entire application.

---

## Architecture

The repository is organized as follows:

- **`backend/`**: Contains the Python monolith (Flask routes, Celery tasks, analytics engines, database helpers, and Python dependencies).
- **`frontend/`**: Contains the server-rendered templates and static assets served by the Flask app.

Redis, Celery workers, Celery Beat, and Flower run the same backend codebase to handle background jobs and monitoring.

---

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
│       ├── web/               # Flask app, blueprints, Celery tasks, storage, cache
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
│   ├── templates/             # Jinja HTML templates (UI)
│   └── static/                # Static assets (CSS/JS) served by Flask
├── docker-compose.yml
├── DEPLOYMENT.md
└── README.md
```

Local runtime artifacts default to `backend/instance/projects`. Override with `DATAFORGE_PROJECTS_DIR` when needed.

---

## How to Start the App

### Option A: Running with Docker (Recommended)

Docker Compose automatically orchestrates all required processes (web app, Celery worker, Celery beat, Redis, Flower).

1. Ensure Docker Desktop is running.
2. Create a `.env` file in the project root containing your Supabase, Redis, and Flask credentials.
3. Build and start the containers:
   ```bash
   docker compose up --build
   ```
4. Access the applications:
   - **Main Web App (Frontend & Backend)**: http://localhost:5000
   - **Flower (Celery Monitor)**: http://localhost:5555

---

### Option B: Running Locally (Without Docker)

To run the application on your host machine, you will need to start the Flask web server (which serves the frontend page and APIs) and optionally the Celery worker for handling background tasks.

#### 1. Setup Environment & Dependencies
1. Install Python 3.10+ and start a Redis server locally.
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Create a `.env` file in the project root and configure the environment variables (see below).
4. Apply the database schema in your Supabase SQL editor using `backend/database/schema.sql`.

#### 2. Start the Web App (Frontend + Backend APIs)
Run the web application server. This serves the Jinja templates on port `5000`:
- **Windows (PowerShell)**:
  ```powershell
  $env:PYTHONPATH="backend"
  python backend/app.py
  ```
- **macOS / Linux**:
  ```bash
  PYTHONPATH=backend python backend/app.py
  ```
The app is now available at http://localhost:5000.

#### 3. Start the Celery Worker (For background tasks like AutoML & EDA)
In another terminal, navigate to the `backend` directory and run the worker:
- **Windows**:
  ```powershell
  cd backend
  celery --app=dataforge.web.tasks:celery worker --pool=solo --loglevel=info
  ```
- **macOS / Linux**:
  ```bash
  cd backend
  celery --app=dataforge.web.tasks:celery worker --loglevel=info
  ```

#### 4. Start the Beat Scheduler & Flower Monitor (Optional)
If you require scheduled automated reports or task monitoring:
- **Celery Beat**:
  ```bash
  cd backend
  celery --app=dataforge.web.tasks:celery beat --loglevel=info
  ```
- **Flower Monitor**:
  ```bash
  cd backend
  celery --app=dataforge.web.tasks:celery flower --port=5555
  ```

---

## Environment Variables

Configure these variables in your `.env` file at the root of the project:

| Variable | Description | Requirement |
|---|---|---|
| `FLASK_SECRET_KEY` | Secret key used for signing Flask sessions | Required |
| `REDIS_URL` | Redis connection string (e.g., `redis://localhost:6379/0`) | Required |
| `SUPABASE_URL` | Supabase project URL / API base | Required |
| `SUPABASE_SERVICE_KEY` | Supabase service role API key | Required |
| `DATAFORGE_PROJECTS_DIR` | Local project artifacts directory | Optional |
| `SUPABASE_BUCKET` | Supabase bucket for persisted artifacts | Optional |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Optional |
| `GEMINI_API_KEY` | Gemini API key for LLM-assisted insights | Optional |
| `GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_SA_JSON_CONTENT` | Google service account credentials for Google Sheets | Optional |

---

## Development Notes

- **Backend Logic**: Keep Python backend files in `backend/dataforge`.
- **Routes & Blueprints**: Keep Flask route handlers and blueprints in `backend/dataforge/web/routes`.
- **Frontend Templates**: Edit Jinja HTML/JS code inside `frontend/templates`.
- **Static Assets**: Add stylesheets or javascript assets in `frontend/static`.
- **Task Delegation**: Long-running requests (e.g. EDA, training) must be delegated to background Celery tasks. Use `_broker_available()` check and `SYNC_FALLBACK_ENABLED` pattern to implement synchronous fallback paths.
