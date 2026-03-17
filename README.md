# DataForge_v3

Microservice-ready layout with a clear separation between services and shared code.

**Structure**
- `services/web`: Flask web app (routes, templates, static assets, instance data, migration script)
- `shared/dataforge`: Shared domain and analytics code used by services
- `app.py`: Entry point shim for local development
- `.env.example`: Template for environment variables

**Architecture (Clear Overview)**
- **Services** live under `services/`. Each service is its own deployable unit with its own entrypoint, templates/static (if web), and runtime data.
- `services/web` is the Flask UI/API server. It wires routes, auth, uploads, and rendering.
- **Shared code** lives under `shared/dataforge/`. This is the reusable domain + analytics layer (models, pipelines, connectors, reporting, alerts, ML, etc.) imported by services so logic is not duplicated.
- **Local entrypoints**: `app.py` and `migrate_db.py` are lightweight shims for local dev so you can still run from the repo root.

**Service Map (Today)**
```text
app.py (local shim)
  -> services/web/app.py
       -> shared/dataforge/*  (models, pipelines, connectors, reporting)
       -> services/web/templates + services/web/static
       -> services/web/instance (SQLite DB + project files)
```

This keeps the service boundary clear now and lets us extract additional services later without moving core logic again.

**Future Services (Ideas)**
- `services/api`: Public REST API for external clients (no UI).
- `services/worker`: Background jobs (AutoML training, report generation, scheduling).
- `services/ingest`: Data ingestion from files/APIs/streams with validation.
- `services/alerts`: Notifications engine (email, Slack, webhooks).
- `services/analytics`: Heavy analytics pipelines and batch insights.

**How To Add A Service (Update README + Compose)**
1. Create a new folder under `services/<name>` with its own entrypoint and Dockerfile.
2. Add the service to **Structure** and **Service Map (Today)** sections in this README.
3. Add a new service block in `docker-compose.yml` that points to `services/<name>/Dockerfile`.
4. Document any new environment variables in **Environment**.
5. If the service exposes a port, list it in **How To Run (Docker)**.

**How To Run (Local)**
1. Ensure Python 3.10+ is installed.
2. Create a `.env` file in the project root (start from `.env.example`) and set at least `FLASK_SECRET_KEY`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Start the app with `python app.py`.
5. If you are upgrading an existing SQLite database, run `python services/web/migrate_db.py`.

**How To Run (Docker)**
1. Create a `.env` file in the project root (start from `.env.example`).
2. Build and start: `docker compose up --build`.
3. Open `http://localhost:5000`.

**Environment**
- Create a `.env` file in the project root (you can start from `.env.example`).
- Common variables:
- `FLASK_SECRET_KEY`
- `DATABASE_URL` (optional: Postgres/Supabase)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (optional)
- `GEMINI_API_KEY` (optional)
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_BUCKET` (optional)
- `DATAFORGE_INSTANCE_DIR`, `DATAFORGE_PROJECTS_DIR` (optional overrides)

**Path overrides (optional)**
- `DATAFORGE_INSTANCE_DIR`: override where SQLite DB and project files are stored
- `DATAFORGE_PROJECTS_DIR`: override where per-upload project files are stored
