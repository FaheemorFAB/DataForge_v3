# Figure 3.4: Detailed Diagram (level 1) DFD
**DataForge v3 System Architecture Series**  
**Document Standard:** Decomposed Data Flow Diagram (DFD Level 1)  
**Page Budget:** 1 Page (A4 Portrait, Black & White / Grayscale Print-Ready)  

---

## 1. Architectural Narrative
Figure 3.4 provides the Level 1 functional decomposition of process `0.0 DataForge System`. The system boundary is expanded into seven dedicated subprocesses and six internal data stores, mapping data flow paths, transformations, and state persistence:

- **Process 1.0 (Authenticate & Authorize Session)**: Interfaces with Google OAuth and data store `D1` to register users, enforce role-based access control (Admin, Data Engineer, Analyst, Viewer), and verify subscription quotas.
- **Process 2.0 (Ingest, Validate & Profile Datasets)**: Ingests raw data streams from users and external providers, stages the tables in `D2`, performs automated schema sniffing, and emits data health scorecards.
- **Process 3.0 (Transform, Cleanse & Execute Procedures)**: Drives the DuckDB Stored Procedure Execution engine (`DF-SPE`) and `DataCleaner`, executing AST-validated DAGs and multi-table joins, materializing immutable snapshots and lineage manifests into `D3`.
- **Process 4.0 (Compute Statistical & Deterministic Scans)**: Executes 14 heuristic scans across the cleaned snapshots in `D3`, writing ranked insight dictionaries and baseline metrics into `D4`.
- **Process 5.0 (Synthesize AI Narratives & NL Query Sandbox)**: Enriches statistical baselines from `D4` with Google Gemini 2.5 generative synthesis, and executes natural language queries by generating and executing sandboxed Pandas code.
- **Process 6.0 (Train, Tune & Register AutoML)**: Ingests training matrices from `D3`, runs FLAML model search and task detection, and registers trained pipelines (`.joblib`) and evaluation metrics in `D5`.
- **Process 7.0 (Generate Reports & Dispatch Baseline Alerts)**: Pulls insight metrics from `D4` and alert rules from `D6`, generating pure Python SVG executive presentation decks and sending threshold breach notifications via `E6`.

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
    'fontSize': '10px'
  }
}}%%

flowchart TD
    classDef entity fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    classDef process fill:#f8f8f8,stroke:#000000,stroke-width:1.5px,color:#000000;
    classDef store fill:#ffffff,stroke:#000000,stroke-width:1.5px,stroke-dasharray: 6 2,color:#000000;

    %% External Entities
    E1["EXTERNAL ENTITY: E1<br/>Data Analyst / User"]:::entity
    E2["EXTERNAL ENTITY: E2<br/>External Sources (Sheets/DB)"]:::entity
    E3["EXTERNAL ENTITY: E3<br/>Google OAuth 2.0"]:::entity
    E4["EXTERNAL ENTITY: E4<br/>Google Gemini 2.5 API"]:::entity
    E5["EXTERNAL ENTITY: E5<br/>Supabase Bucket / PostgreSQL"]:::entity
    E6["EXTERNAL ENTITY: E6<br/>Resend Email & Webhooks"]:::entity

    %% Internal Data Stores
    D1[("D1 | Users, Workspaces & Tier Quotas")]:::store
    D2[("D2 | Raw Uploads & Ingested Tables")]:::store
    D3[("D3 | Cleaned Parquet Snapshots & Lineage")]:::store
    D4[("D4 | Analytical Baselines & Insight Cache")]:::store
    D5[("D5 | Model Registry & Weights (.joblib)")]:::store
    D6[("D6 | Audit Logs & Alert Schedules")]:::store

    %% Subprocesses
    P1(["1.0<br/>Authenticate &<br/>Authorize Session"]):::process
    P2(["2.0<br/>Ingest, Validate &<br/>Profile Datasets"]):::process
    P3(["3.0<br/>Transform, Cleanse<br/>& Execute Procedures"]):::process
    P4(["4.0<br/>Compute Statistical<br/>& Deterministic Scans"]):::process
    P5(["5.0<br/>Synthesize AI Narratives<br/>& NL Query Sandbox"]):::process
    P6(["6.0<br/>Train, Tune &<br/>Register AutoML"]):::process
    P7(["7.0<br/>Generate Reports &<br/>Dispatch Baseline Alerts"]):::process

    %% Flows: 1.0 Auth
    E1 -->|"OAuth Login Request"| P1
    E3 -->|"OAuth Claims / Token"| P1
    P1 -->|"Write / Update User Record"| D1
    D1 -->|"Read Roles & Quotas"| P1
    P1 -->|"JWT Session Cookie & UI Context"| E1

    %% Flows: 2.0 Ingest
    E1 -->|"Upload Local CSV / Excel"| P2
    E2 -->|"Stream Sheet Cells / SQL Rows"| P2
    P2 -->|"Stage Raw Data Parquet"| D2
    D2 -->|"Read Raw Table"| P2
    P2 -->|"Real-Time Profiling & Schema Health Card"| E1
    P2 -->|"Sync Cloud Mirror"| E5

    %% Flows: 3.0 Transform
    E1 -->|"Cleaning Specs / Join Keys / Procedure DAG"| P3
    D2 -->|"Stream Raw Data"| P3
    P3 -->|"Persist Cleaned Snapshot & Lineage Manifest"| D3
    P3 -->|"Interactive Transformation Diff Preview"| E1
    P3 -->|"Persist Snapshot Artifacts"| E5

    %% Flows: 4.0 Insights
    D3 -->|"Read Cleaned Snapshot"| P4
    P4 -->|"Store Ranked Insight Objects & Baselines"| D4
    P4 -->|"Statistical Visualizations & Heuristic Cards"| E1

    %% Flows: 5.0 AI & Query
    E1 -->|"Natural Language Business Query"| P5
    D3 -->|"Schema & Sample Tuples"| P5
    D4 -->|"Synthesized Statistical Facts"| P5
    P5 -->|"Prompt Envelopes (Schema + Context)"| E4
    E4 -->|"Narrative Explanations & Pandas Code AST"| P5
    P5 -->|"Dynamic Answers & Sandboxed Plotly Charts"| E1

    %% Flows: 6.0 AutoML
    E1 -->|"Target Column & Metric Goal"| P6
    D3 -->|"Train/Test Encoded Matrices"| P6
    P6 -->|"Save Serialized Pipeline & Performance Metrics"| D5
    P6 -->|"Save Model Artifacts"| E5
    P6 -->|"Leaderboard, Confusion Matrix & Predictions"| E1

    %% Flows: 7.0 Reports & Alerts
    D4 -->|"Insight Summaries & Baseline Values"| P7
    D6 -->|"Schedule Rules & Webhook URLs"| P7
    P7 -->|"Downloadable PDF / SVG Presentation Deck"| E1
    P7 -->|"Send Breach Notifications & Summary Decks"| E6
    P1 -.->|"Log User Activity"| D6
    P3 -.->|"Log Audit Event"| D6
```

---

## 3. Data Store Schema & Role Mapping

| Store ID | Logical Name | Physical Storage | Principal Schema / Contents |
| :---: | :--- | :--- | :--- |
| **D1** | Users & Quotas | PostgreSQL / SQLite | `users`, `organizations`, `memberships`, `subscriptions` |
| **D2** | Raw Uploads | Local Parquet / Supabase | `uploads`, raw CSV/Excel chunks, schema discovery JSON |
| **D3** | Clean Snapshots | Parquet / Supabase Bucket | Immutable snapshots, `procedures`, `lineage_manifest_json` |
| **D4** | Insight Cache | Relational DB / Memory | Statistical baselines, metric definitions, correlation matrices |
| **D5** | Model Registry | File Storage / Supabase | Trained `.joblib` estimators, feature importance, test metrics |
| **D6** | Audit & Alerts | PostgreSQL / SQLite | `audit_events`, `report_schedules`, webhook targets |
