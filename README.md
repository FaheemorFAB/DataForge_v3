# 🛠️ DataForge v3

DataForge is a premium, enterprise-grade automated data engineering, analytical profiling, and machine learning platform. It empowers organizations to seamlessly ingest raw datasets, execute rule-based data cleaning pipelines, run advanced statistical scans, generate AI-driven narrative business insights, query datasets using conversational natural language, train predictive models automatically, and distribute publication-quality reports.

---

## 🎨 System Architecture Overview

This diagram displays the flow of data and asynchronous requests through the DataForge backend services and third-party integration layers:

```mermaid
graph TD
    %% Styling
    classDef client fill:#E8F0FE,stroke:#4285F4,stroke-width:2px;
    classDef api fill:#F1F3F4,stroke:#3C4043,stroke-width:2px;
    classDef worker fill:#FCE8E6,stroke:#D93025,stroke-width:2px;
    classDef external fill:#FFE8D6,stroke:#DDBEA9,stroke-width:2px;
    classDef storage fill:#E6F4EA,stroke:#34A853,stroke-width:2px;

    %% Nodes
    User[Client Browser / SPA]:::client
    GAuth[Google OAuth 2.0]:::external
    Gemini[Google Gemini 2.5 Flash]:::external
    Flask[Flask Web API Server]:::api
    Redis[Redis Message Broker & Cache]:::worker
    Celery[Celery Async Task Workers]:::worker
    Supa[Supabase PostgreSQL & S3 Storage]:::storage

    %% Flows
    User -->|HTTPS Requests / WebSockets| Flask
    Flask <-->|OAuth Code Exchange| GAuth
    Flask <-->|Metadata & File Store| Supa
    Flask -->|Enqueue Async Jobs| Redis
    Redis -->|Dispatch Tasks| Celery
    Celery <-->|Dataset Reads & Writes| Supa
    Celery <-->|Context & Prompts / Narrative Slides| Gemini
    Flask <-->|Session Cache & Live Alerts| Redis
    Celery -->|WebSocket Broadcasts| User
```

---

## 📸 Platform Showcase

Explore the end-to-end user journey within the DataForge ecosystem, showcasing the workflow from secure entry to machine learning deployment.

### 🔐 1. Secure Authentication Portal
A secure, role-based gateway featuring native local credentials verification alongside Google OAuth 2.0 single sign-on (SSO).
![Secure Authentication Portal](assets/auth.jpg)

### 📥 2. Intelligent Data Ingestion
Drag-and-drop CSV/Excel file uploads or live streaming via public Google Sheets connections, with automatic initial dimension profiling.
![Intelligent Data Ingestion](assets/uplid.jpg)

### 🔍 3. Interactive Data Preview & Profiling
High-fidelity tabular preview of ingested data highlighting missing cell percentages, data type detection, completeness metrics, and summary stats.
![Interactive Data Preview](assets/previwe.jpg)

### 🧹 4. Workspace & Data Cleaning Pipeline
Apply rule-based transformations—such as filters, group-bys, column derivations, and missing value interpolations—with visual pipeline state validation and parquet-optimized storage.
![Data Cleaning Pipeline](assets/cleaning.jpg)

### 📊 5. Executive Dashboard
An interactive central cockpit showing dataset metrics, key statistics, column distributions, and live Celery/WebSocket event activity logs.
![Executive Dashboard](assets/dash_brd.jpg)

### 💡 6. AI-Powered Insight Engine
Automated scans for statistical anomalies, category distributions, trends, and correlations, paired with executive summaries compiled by Google Gemini API.
![AI-Powered Insight Engine](assets/insght.jpg)

### 💬 7. Conversational AI Analyst Chatbot
Interact with datasets in plain English. The sandboxed AI Analyst generates, validates, and runs Python code to create charts and tables on the fly.
![Conversational AI Analyst Chatbot](assets/aiQry.jpg)

### 🤖 8. Automated Machine Learning (AutoML)
Automatically detect classification/regression tasks, search for optimal models (XGBoost, LightGBM, Random Forest) via hyperparameter optimization, and export trained model assets.
![AutoML Model Training](assets/AutoML.jpg)

---

## 🚀 Core Features

* **Quality & Completeness Scans**: Live quality bars, column-level completeness, and missingness metrics.
* **Rule-Based Data Transformation**: In-place filtering, column renaming, drop/imputation of null values, and custom expressions saved to Parquet.
* **Statistical Insights Engine**: Automatic trend detection, segment analysis, outlier detection, and correlation matrices.
* **AI Summary Generator**: McKinsey-style executive commentary and narrative bullet points powered by `gemini-2.5-flash`.
* **Visual Sandbox Chatbot**: Secure AST validation of generated Python scripts before execution to prevent system calls or arbitrary file edits.
* **AutoML Leaderboard**: Hyperparameter tuning, F1/ROC-AUC scoring, and downloadable pickled model objects.
* **WebSocket Alert Broadcasting**: Instantaneous warnings and live job updates sent to connected browser clients.

---

## 🛠️ Architecture & Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend Framework** | Flask (Python 3.10+) | Monolithic web server and API routes handler |
| **Async Task Queue** | Celery + Redis | Handles async AutoML training, slides compiling, and alert evaluation |
| **AI Orchestration** | Gemini API (`gemini-2.5-flash`) | Narrative report synthesis and conversational NLP code generation |
| **Database & Storage** | Supabase (PostgreSQL + S3 Bucket) | User credentials storage, workspace state tables, and Parquet data store |
| **Machine Learning** | FLAML (AutoML) + scikit-learn | Fast hyperparameter optimization and model search |
| **Frontend** | Vanilla JS (Alpine.js), CSS (Themes), HTML5 | Clean, responsive UI supporting custom themes (dark & light) |

---

## ⚙️ How to Run Locally

### Prerequisites
- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **Redis** — used for Celery task queuing and WebSocket pub/sub  
  - **Windows**: install via [Chocolatey](https://chocolatey.org/) → `choco install redis-64` or use the [Windows port](https://github.com/microsoftarchive/redis/releases). Alternatively use WSL2 → `sudo apt install redis-server && sudo service redis start`
  - **macOS**: `brew install redis && brew services start redis`
  - **Linux**: `sudo apt install redis-server && sudo service redis start`
  > Redis is **optional** — the app automatically falls back to synchronous task execution if Redis/Celery are not running.

---

### Step 1 — Clone and Configure Environment

```bash
# 1. Copy the example env file and fill in your values
cp .env.example .env
# Then open .env and populate all required variables (see comments inside)
```

---

### Step 2 — Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv

# Activate (Windows PowerShell)
venv\Scripts\Activate.ps1

# Activate (Windows CMD)
venv\Scripts\activate.bat

# Activate (macOS / Linux)
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

---

### Step 3 — Run the Flask Server

```bash
# From the project root (with venv active and PYTHONPATH set to backend/)
cd backend
python app.py
```

Open your browser at **http://localhost:5000**

---

### Step 4 — Run the Celery Worker (Optional but Recommended)

In a **second terminal** (with the same venv active):

```bash
cd backend

# Windows (uses --pool=solo for compatibility)
celery --app=dataforge.web.tasks:celery worker --loglevel=info --pool=solo

# macOS / Linux (uses prefork for full parallelism)
celery --app=dataforge.web.tasks:celery worker --loglevel=info --pool=prefork
```

> **Without a Celery worker**, heavy tasks (AutoML, EDA reports, Insights) run synchronously in the web request. The app will be slower but fully functional.

---

### Step 5 — Run Celery Beat (Optional — for scheduled reports)

In a **third terminal**:

```bash
cd backend
celery --app=dataforge.web.tasks:celery beat --loglevel=info
```

---

### Step 6 — Monitor Tasks with Flower (Optional)

```bash
cd backend
celery --app=dataforge.web.tasks:celery flower --port=5555
```

Open **http://localhost:5555** to see the Celery task dashboard.

---



## 📐 Data Flow Diagrams (DFDs)

For full architectural transparency, here are the System Data Flow Diagrams:

<details>
<summary>🔍 Level 0: Context Level Diagram</summary>

Shows system boundaries and data exchange between external entities and the core system.

```mermaid
graph TD
    %% Styling
    classDef entity fill:#FFE8D6,stroke:#DDBEA9,stroke-width:2px;
    classDef process fill:#E8F0FE,stroke:#4285F4,stroke-width:2px;
    classDef store fill:#E6F4EA,stroke:#34A853,stroke-width:2px;

    %% Nodes
    User[User / Client Browser]:::entity
    GAuth[Google OAuth]:::entity
    GSheets[Google Sheets API]:::entity
    Gemini[Gemini AI API]:::entity
    Supa[Supabase DB & Storage]:::store
    DF((DataForge System)):::process

    %% Flows
    User -->|Credentials / Uploads / Rules| DF
    DF -->|Data Previews / Reports / Alerts| User
    DF <-->|Validate User Auth| GAuth
    GSheets -->|Stream Sheet Data| DF
    DF <-->|Metadata & Files| Supa
    DF <-->|Context & Prompts / Business Slides| Gemini
```
</details>

<details>
<summary>⚙️ Level 1: Feature-Specific DFDs</summary>

### 1. Authentication & Session Management
Manages user logins, credentials validation, and Google OAuth flow.

```mermaid
flowchart TD
    classDef entity fill:#FFE8D6,stroke:#DDBEA9,stroke-width:2px;
    classDef process fill:#E8F0FE,stroke:#4285F4,stroke-width:2px;
    classDef store fill:#E6F4EA,stroke:#34A853,stroke-width:2px;

    User[User / Client Browser]:::entity
    GAuth[Google OAuth Provider]:::entity
    P1((1.0 Auth & Session Management)):::process
    DB[(Users Table)]:::store

    User -->|Credentials / OAuth Request| P1
    P1 <-->|Verify Code / Token| GAuth
    P1 <-->|Read / Write User Session| DB
    P1 -->|Session Cookie & Login Status| User
```

### 2. Data Ingestion & Import
Handles file uploads (CSV/Excel) and public Google Sheet connections.

```mermaid
flowchart TD
    classDef entity fill:#FFE8D6,stroke:#DDBEA9,stroke-width:2px;
    classDef process fill:#E8F0FE,stroke:#4285F4,stroke-width:2px;
    classDef store fill:#E6F4EA,stroke:#34A853,stroke-width:2px;

    User[User / Client Browser]:::entity
    GSheets[Google Sheets API]:::entity
    P2((2.0 Data Ingestion & Profiling)):::process
    DB[(Uploads Table)]:::store
    Store[(df_raw Parquet)]:::store

    User -->|Upload CSV-Excel / Google Sheets Link| P2
    P2 -->|Fetch Sheet Data| GSheets
    GSheets -->|Raw CSV Data| P2
    P2 -->|Save Dataset File| Store
    P2 -->|Log Upload Metadata| DB
    P2 -->|Dataset Stats Profile| User
```

### 3. Workspace & Transformation Pipeline
Executes dynamic, rule-based data cleaning, filtering, groupings, and derived column calculations.

```mermaid
flowchart TD
    classDef entity fill:#FFE8D6,stroke:#DDBEA9,stroke-width:2px;
    classDef process fill:#E8F0FE,stroke:#4285F4,stroke-width:2px;
    classDef store fill:#E6F4EA,stroke:#34A853,stroke-width:2px;

    User[User / Client Browser]:::entity
    P3((3.0 Cleaning & Transform Engine)):::process
    DB[(Uploads Table)]:::store
    RawStore[(df_raw Parquet)]:::store
    CleanStore[(df_clean Parquet)]:::store

    User -->|Define Rules: Clean / Filter / Groupby / Derive| P3
    P3 -->|Load Raw Dataset| RawStore
    P3 -->|Save Cleaned Dataset| CleanStore
    P3 -->|Update Clean Metadata JSON| DB
    P3 -->|Interactive Data Preview| User
```

### 4. Insights Engine
Runs plugin scanning rules (Trends, Outliers, Correlations, segment analysis) and calls Gemini to build executive summaries.

```mermaid
flowchart TD
    classDef entity fill:#FFE8D6,stroke:#DDBEA9,stroke-width:2px;
    classDef process fill:#E8F0FE,stroke:#4285F4,stroke-width:2px;
    classDef store fill:#E6F4EA,stroke:#34A853,stroke-width:2px;

    User[User / Client Browser]:::entity
    Gemini[Gemini AI API]:::entity
    P4((4.0 Insights Generation)):::process
    DB_Jobs[(Jobs Table)]:::store
    DB_Insights[(Insight Records Table)]:::store
    CleanStore[(df_clean Parquet)]:::store
    Cache[(last_insights Parquet/JSON)]:::store

    User -->|Trigger Insights Request| P4
    P4 -->|Create Background Job| DB_Jobs
    P4 -->|Load Cleaned Dataset| CleanStore
    P4 -->|Run Statistical Scan & Send Context| Gemini
    Gemini -->|Generate Summary Narrative| P4
    P4 -->|Save Structured Insights| DB_Insights
    P4 -->|Cache Result Details| Cache
    P4 -->|Rendered Statistical Charts| User
```

### 5. AutoML Training
Fits machine learning classifiers or regressors based on target selection, saving and evaluating the results.

```mermaid
flowchart TD
    classDef entity fill:#FFE8D6,stroke:#DDBEA9,stroke-width:2px;
    classDef process fill:#E8F0FE,stroke:#4285F4,stroke-width:2px;
    classDef store fill:#E6F4EA,stroke:#34A853,stroke-width:2px;

    User[User / Client Browser]:::entity
    P5((5.0 AutoML Training)):::process
    DB_Jobs[(Jobs Table)]:::store
    DB_Uploads[(Uploads Table)]:::store
    CleanStore[(df_clean Parquet)]:::store
    ModelStore[(model_pkl Joblib)]:::store

    User -->|Select Target Column & Time Budget| P5
    P5 -->|Create Training Background Job| DB_Jobs
    P5 -->|Load Cleaned Dataset| CleanStore
    P5 -->|Fit & Save Trained Model| ModelStore
    P5 -->|Update Upload automl_meta_json| DB_Uploads
    P5 -->|Model Evaluation Metrics & Importance| User
```

### 6. Strategic Reporting & Alerting
Generates presentation-ready HTML/PDF reports using McKinsey-formatted slide commentary, evaluates alert conditions, and broadcasts messages via WebSockets.

```mermaid
flowchart TD
    classDef entity fill:#FFE8D6,stroke:#DDBEA9,stroke-width:2px;
    classDef process fill:#E8F0FE,stroke:#4285F4,stroke-width:2px;
    classDef store fill:#E6F4EA,stroke:#34A853,stroke-width:2px;

    User[User Browser / WebSocket]:::entity
    Gemini[Gemini AI API]:::entity
    P6((6.0 Reporting & Alerts)):::process
    DB_Alerts[(Alerts Table)]:::store
    DB_Reports[(Reports Table)]:::store
    DB_Jobs[(Jobs Table)]:::store
    CleanStore[(df_clean Parquet)]:::store
    ReportStore[(report_html File)]:::store

    User -->|Request Slide Deck Report / Rules Check| P6
    P6 -->|Check Celery Job status| DB_Jobs
    P6 -->|Load Cleaned Dataset| CleanStore
    P6 -->|Evaluate Alert Rules| P6
    P6 -->|Log Fired Alerts| DB_Alerts
    P6 -->|Prompts for McKinsey Slide Commentary| Gemini
    Gemini -->|Executive Slides Text| P6
    P6 -->|Generate & Save HTML Report| ReportStore
    P6 -->|Save Report Reference| DB_Reports
    P6 -->|WebSocket Push & HTML Download| User
```
</details>
