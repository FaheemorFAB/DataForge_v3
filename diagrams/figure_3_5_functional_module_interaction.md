# Figure 3.5: Functional Module Interaction Diagram
**DataForge v3 System Architecture Series**  
**Document Standard:** Software Subsystem Interoperability & Component Collaboration  
**Page Budget:** 1 Page (A4 Portrait, Black & White / Grayscale Print-Ready)  

---

## 1. Architectural Narrative
Figure 3.5 models the functional dependencies, method contracts, and event streams interconnecting DataForge v3's core Python modules. Grouped into seven logical domains, these modules exhibit high cohesion and loose coupling:

1. **Security & Identity Governance (`M_AUTH`)**: Authenticates sessions via OAuth 2.0 / JWT and validates tenant usage limits before allowing ingestion.
2. **Ingress & Ingestion Suite (`M_INGEST`)**: Multi-source ingestion drivers (CSV, Excel Online, Google Sheets API, database connectors) parse files and hand raw DataFrames to the EDA profiler and storage.
3. **Data Transformation & Pipeline (`M_PIPELINE`)**: Composed of `M_CLEAN` (outlier clipping, median/mode imputation, type coercion), `M_JOIN` (DuckDB multi-table joins), and `M_DFSPE` (the SQL procedure compiler with AST expression validation and assertion gates).
4. **Analytical Profiling & Insights (`M_ANALYTICS`)**: `M_EDA` generates data quality health cards, while `M_INSIGHT` executes 14 statistical heuristics (trends, anomalies, correlations, segments) with mathematical rigor checks.
5. **Augmented AI & Machine Learning (`M_AI_ML`)**: `M_AI` connects to Google Gemini 2.5 Flash for narrative synthesis and safe sandboxed code execution; `M_AUTOML` trains predictive models via FLAML, logging metrics and artifacts to the registry.
6. **Presentation, Alerting & Distribution (`M_OUTPUT`)**: Pure Python vector SVG engine (`M_REPORT`) renders executive decks, while `M_ALERT` compares metrics against baselines to trigger alerts.
7. **Infrastructure & Orchestration (`M_INFRA`)**: `M_STORE` manages immutable snapshots and database transactions, while `M_JOBS` orchestrates the `ThreadPoolExecutor`, task queues, and `/ws` WebSocket streaming.

---

## 2. Mermaid Diagram

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#ffffff',
    'primaryTextColor': '#000000',
    'primaryBorderColor': '#000000',
    'lineColor': '#000000',
    'secondaryColor': '#f5f5f5',
    'tertiaryColor': '#ffffff',
    'edgeLabelBackground': '#ffffff',
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '11px'
  }
}}%%

flowchart TD
    classDef module fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000;
    classDef engine fill:#f7f7f7,stroke:#000000,stroke-width:2px,color:#000000;
    classDef infra fill:#f0f0f0,stroke:#000000,stroke-width:1.5px,stroke-dasharray: 4 2,color:#000000;

    subgraph MOD_AUTH ["1. Security, Identity & Workspace Governance"]
        M_AUTH["Auth & Governance Module<br/>(OAuth 2.0 / JWT / RBAC / Quota Enforcer)"]:::module
    end

    subgraph MOD_INGEST ["2. Data Ingestion & Ingress Connectors"]
        M_INGEST["Ingestion Connector Suite<br/>(CSV / Excel Online / Sheets API / Remote SQL)"]:::module
    end

    subgraph MOD_PIPELINE ["3. Data Transformation & Pipeline Engines"]
        direction TB
        M_CLEAN["Data Cleaner Module<br/>(Outlier Clipper / Imputation / Type Coercion)"]:::engine
        M_JOIN["Join Canvas Engine<br/>(Multi-Table DuckDB Hash Joins)"]:::engine
        M_DFSPE["DF-SPE Procedure Engine<br/>(DuckDB SQL Compiler, AST Validator, Assertion Gates)"]:::engine
    end

    subgraph MOD_ANALYTICS ["4. Analytical Profiling & Statistical Insight Core"]
        direction TB
        M_EDA["EDA & Data Quality Module<br/>(Missingness Matrix, Skew, Cardinality)"]:::engine
        M_INSIGHT["Deterministic Insight Engine<br/>(14 Statistical Scanners: Trends, Outliers, Segments)"]:::engine
    end

    subgraph MOD_AI_ML ["5. Augmented Intelligence & AutoML Systems"]
        direction TB
        M_AI["Augmented AI Engine<br/>(Gemini 2.5 Flash Pipeline + Safe AST Code Sandbox)"]:::engine
        M_AUTOML["AutoML & Model Registry<br/>(FLAML, Hyperparameter Tuner, Metric Evaluator)"]:::engine
    end

    subgraph MOD_OUTPUT ["6. Presentation, Alerting & Distribution"]
        direction TB
        M_REPORT["Executive Report Generator<br/>(Pure Python Vector SVG & Deck Engine)"]:::module
        M_ALERT["Alert & Baseline Engine<br/>(Statistical Drift & Threshold Breach Monitor)"]:::module
    end

    subgraph MOD_INFRA ["7. Shared Infrastructure & Data Orchestration"]
        direction TB
        M_STORE["Storage & Snapshot Manager<br/>(Supabase DB, Parquet Bucket, Snapshot Materializer)"]:::infra
        M_JOBS["Async Job Manager & WebSocket Streamer<br/>(ThreadPoolExecutor / Redis Queue / /ws PubSub)"]:::infra
    end

    %% Interactions & Data Contracts
    M_AUTH ==>|"1. Authorize User & Check Quota"| M_INGEST
    M_AUTH -.->|"2. Audit Events & Access Policies"| M_STORE

    M_INGEST -->|"3. Raw Ingested DataFrame & Schema"| M_STORE
    M_INGEST -->|"4. Dispatch Ingestion Task"| M_JOBS
    M_INGEST -->|"5. Hand off Raw Dataset"| M_EDA

    M_EDA -->|"6. Quality Score & Health Card"| M_CLEAN
    M_EDA -->|"7. Multi-Dataset Metadata"| M_JOIN

    M_CLEAN -->|"8. Transformation Spec"| M_DFSPE
    M_JOIN -->|"9. Joined Staged Table"| M_DFSPE

    M_DFSPE -->|"10. Compiled DuckDB Execution Graph"| M_STORE
    M_DFSPE -->|"11. Immutable Parquet Snapshot & Lineage"| M_INSIGHT
    M_DFSPE -->|"12. Snapshot Reference"| M_AUTOML

    M_INSIGHT -->|"13. Ranked Statistical Insight Dictionaries"| M_AI
    M_INSIGHT -->|"14. Ingestion Baseline Metrics"| M_ALERT

    M_AI -->|"15. Contextual Prompts & Synthesis"| M_REPORT
    M_AI <-->|"16. Safe Query Execution in Sandbox"| M_STORE

    M_AUTOML -->|"17. Async Training Job Status"| M_JOBS
    M_AUTOML -->|"18. Serialized Model (.joblib) & Test Metrics"| M_STORE
    M_AUTOML -->|"19. Model Card & Feature Importance"| M_REPORT

    M_ALERT -->|"20. Drift Alarms & Threshold Status"| M_REPORT

    M_JOBS ==>|"21. Real-Time Push Events (/ws)"| M_AUTH
    M_STORE <-->|"22. Query State & Retrieve Artifacts"| M_REPORT
```

---

## 3. Inter-Module Contract Specifications

| Contract # | Caller Module | Callee Module | Protocol / Payload Description |
| :---: | :--- | :--- | :--- |
| **1** | `M_AUTH` | `M_INGEST` | `verify_quota(user_id, file_size)` → returns boolean admission |
| **3, 10** | `M_INGEST`, `M_DFSPE` | `M_STORE` | `save_parquet(upload_id, df)` → returns storage URI & hash |
| **4, 17** | `M_INGEST`, `M_AUTOML` | `M_JOBS` | `dispatch_job(func, *args)` → returns job UUID for polling / socket |
| **6, 7** | `M_EDA` | `M_CLEAN`, `M_JOIN` | Ingestion health dictionary with null counts, column types & unique counts |
| **8, 9** | `M_CLEAN`, `M_JOIN` | `M_DFSPE` | Procedural step nodes & join condition DAG for SQL compilation |
| **11, 12** | `M_DFSPE` | `M_INSIGHT`, `M_AUTOML` | Immutable Parquet snapshot path with verified tuple-level Why-Provenance |
| **13** | `M_INSIGHT` | `M_AI` | Ranked insight objects (type, score, p-value, metrics, narrative stub) |
| **14, 20** | `M_INSIGHT`, `M_ALERT` | `M_ALERT`, `M_REPORT` | Baseline metric snapshot; threshold check (`metric_drop`, `null_spike`) |
| **16** | `M_AI` | `M_STORE` | Safe Python execution in restricted AST sandbox against local snapshot |
| **18** | `M_AUTOML` | `M_STORE` | Model weights serialized via `joblib.dump()` + test evaluation metrics |
| **21** | `M_JOBS` | `M_AUTH` | Real-time WebSocket event broadcast: `{"event": "job_progress", ...}` |
