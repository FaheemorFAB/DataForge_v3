# DataForge v3 — Feature Data Flow Diagrams

This document contains the minimal, portrait-optimized Data Flow Diagrams (DFDs) for each primary feature of the DataForge application, organized individually to fit cleanly in portrait PDF reports.

---

## 🔍 Level 0: Context Level Diagram
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

---

## ⚙️ Level 1: Feature-Specific DFDs

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

---

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

---

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

---

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

---

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

---

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
