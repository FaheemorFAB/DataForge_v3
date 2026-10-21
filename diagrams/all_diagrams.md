# DataForge v3 — System Architecture & Engineering Diagrams
**Academic & Technical Documentation Series**  
**Document Standard:** ISO/IEC/IEEE 42010 Architecture Description & Structured Analysis (DFD)  
**Target Format:** A4 Portrait Print (Black & White / Monochrome Textbook Aesthetic, Pure White Figures & White Arrow Labels)  

---

## Table of Figures

| Figure | Title | Description | Page Ratio |
| :--- | :--- | :--- | :--- |
| **Figure 3.1** | [System Workflow](#figure-31-system-workflow) | Operational lifecycle across the 7 textbook stages from sign-in to report generation | A4 Portrait |
| **Figure 3.2** | [DataForge System Architecture](#figure-32-dataforge-system-architecture) | Five-tier structural architecture mapping client, gateway, services, pipeline engines, and persistence | A4 Portrait |
| **Figure 3.3** | [Context Diagram (Level 0) DFD](#figure-33-context-diagram-level-0-dfd) | High-level system boundary, external entities, and primary I/O data streams | A4 Portrait |
| **Figure 3.4** | [Detailed Diagram (Level 1) DFD](#figure-34-detailed-diagram-level-1-dfd) | Decomposition into 7 core subprocesses, 6 internal data stores, and entity flows | A4 Portrait |
| **Figure 3.5** | [Functional Module Interaction Diagram](#figure-35-functional-module-interaction-diagram) | Subsystem interface contracts, event streams, and procedural data exchanges | A4 Portrait |

---

<div style="page-break-after: always;"></div>

## Figure 3.1: System Workflow

### Description
Figure 3.1 delineates the complete execution lifecycle of the DataForge v3 ecosystem across the seven core stages: **User sign-in → Dataset upload → Data cleaning → Data profiling and analysis → Visualisation and AI-assisted exploration → Automated machine learning, where required → Report generation**. Rendered with pure white figures, crisp black borders, and white arrow label backgrounds for pristine textbook printing.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#ffffff',
    'primaryTextColor': '#000000',
    'primaryBorderColor': '#000000',
    'lineColor': '#000000',
    'secondaryColor': '#ffffff',
    'tertiaryColor': '#ffffff',
    'mainBkg': '#ffffff',
    'nodeBorder': '#000000',
    'clusterBkg': '#ffffff',
    'clusterBorder': '#000000',
    'defaultLinkColor': '#000000',
    'titleColor': '#000000',
    'edgeLabelBackground': '#ffffff',
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '11px'
  },
  'themeCSS': '.edgeLabel { background-color: #ffffff !important; color: #000000 !important; border: 1px solid #000000 !important; padding: 2px 4px !important; border-radius: 2px !important; font-size: 10px !important; } .edgeLabel rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 0.8px !important; } .cluster rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 1.5px !important; } .node rect, .node circle, .node ellipse, .node polygon, .node path { fill: #ffffff !important; stroke: #000000 !important; }'
}}%%

flowchart TD
    classDef process fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000;
    classDef decision fill:#ffffff,stroke:#000000,stroke-width:1.5px,stroke-dasharray: 4 2,color:#000000;
    classDef terminal fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;

    START(["● START: User Accesses DataForge"]):::terminal

    subgraph SG1 ["1. User sign-in"]
        A1["Google OAuth 2.0 / JWT Login"]:::process
        A2{"Valid Session & Active Tier?"}:::decision
        A3["Load Workspace & Quotas<br/>(Personal or Organization)"]:::process
        A4["Init Real-Time Socket<br/>(FastAPI /ws Connection)"]:::process
    end

    subgraph SG2 ["2. Dataset upload"]
        B1["Select Source: CSV / Excel /<br/>Google Sheets API / External DB"]:::process
        B2["Streaming Ingestion & Storage<br/>(Supabase Object Store / Local)"]:::process
        B3["Auto-Detect Schema & Delimiter<br/>(Pandas & DuckDB Sniffer)"]:::process
        B4["Generate Ingestion Health Card<br/>(Null %, Types, Memory Footprint)"]:::process
    end

    subgraph SG3 ["3. Data cleaning"]
        C1{"Cleaning Mode?"}:::decision
        C2["DataCleaner Pipeline:<br/>Imputation, Outliers, Coercion"]:::process
        C3["Join Canvas Studio:<br/>Inner/Left/Right/Outer (DuckDB)"]:::process
        C4["DF-SPE Stored Procedure:<br/>Compiled SQL DAG + Assertion Gates"]:::process
        C5["Materialize Snapshot & Lineage<br/>(Why-Provenance Manifest)"]:::process
    end

    subgraph SG4 ["4. Data profiling and analysis"]
        D1["Run 14 Heuristic Scanners<br/>(Trends, Outliers, Correlations, Segments)"]:::process
        D2["Statistical Rigor & Significance<br/>(Z-Score, IQR, Chi-Sq, Pearson)"]:::process
        D3["Baseline Metric Caching & Profile Summary"]:::process
    end

    subgraph SG5 ["5. Visualisation and AI-assisted exploration"]
        E1["Interactive Dashboard & Chart Plots"]:::process
        E2["Gemini 2.5 Flash Pipeline:<br/>Automated Executive Narrative"]:::process
        E3["Conversational Analyst Chatbot:<br/>NL Query → Pandas AST → Sandbox"]:::process
    end

    subgraph SG6 ["6. Automated machine learning, where required"]
        F1{"Train Model?"}:::decision
        F2["Auto Task Detection & Imbalance Check<br/>(Classification vs Regression)"]:::process
        F3["FLAML & Scikit-Learn Search<br/>(Isolated Worker Execution)"]:::process
        F4["Evaluate Metrics & Feature Importance<br/>(ROC-AUC, F1, RMSE, R²)"]:::process
        F5["Register Artifact (.joblib)<br/>in DataForge Model Registry"]:::process
    end

    subgraph SG7 ["7. Report generation"]
        G1["Generate Executive PDF Report<br/>(Pure Python Vector SVG Charts)"]:::process
        G2["Save Metric Baseline & Rules<br/>(Alert Engine Thresholds)"]:::process
        G3["Export Parquet / Team Share<br/>(RBAC Governance & Webhooks)"]:::process
    end

    END_NODE(["■ END: Insights Delivered & Deployed"]):::terminal

    START --> A1
    A1 --> A2
    A2 -- "No (Invalid)" --> A1
    A2 -- "Yes (Authorized)" --> A3
    A3 --> A4
    A4 ==>|"Authenticated"| B1

    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 ==>|"Raw Schema"| C1

    C1 -- "Cleaning Rules" --> C2
    C1 -- "Multi-Table Join" --> C3
    C1 -- "Stored Procedure" --> C4

    C2 --> C5
    C3 --> C5
    C4 --> C5

    C5 ==>|"Cleaned Snapshot"| D1
    D1 --> D2
    D2 --> D3

    D3 ==>|"Statistical Facts"| E1
    E1 --> E2
    E2 --> E3

    E3 ==>|"Prepared Data"| F1
    F1 -- "Yes (AutoML)" --> F2
    F2 --> F3
    F3 --> F4
    F4 --> F5
    F5 ==>|"Model Metrics"| G1
    F1 -- "Skip (Exploration Only)" --> G1

    G1 --> G2
    G2 --> G3
    G3 --> END_NODE
```

*Figure 3.1: DataForge End-to-End System Workflow.*

---

<div style="page-break-after: always;"></div>

## Figure 3.2: DataForge System Architecture

### Description
Figure 3.2 illustrates the five-tier structural engineering architecture of DataForge v3. All elements are formatted in pure white with high-contrast black strokes and white-background edge labels, highlighting the integrated core analytical processing pipeline (User Sign-In, Dataset Upload, Data Cleaning, Data Profiling, Visualisation & AI Exploration, AutoML, and Report Generation) supported by Client, Gateway, Routing, and Persistence tiers.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#ffffff',
    'primaryTextColor': '#000000',
    'primaryBorderColor': '#000000',
    'lineColor': '#000000',
    'secondaryColor': '#ffffff',
    'tertiaryColor': '#ffffff',
    'mainBkg': '#ffffff',
    'nodeBorder': '#000000',
    'clusterBkg': '#ffffff',
    'clusterBorder': '#000000',
    'defaultLinkColor': '#000000',
    'titleColor': '#000000',
    'edgeLabelBackground': '#ffffff',
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '11px'
  },
  'themeCSS': '.edgeLabel { background-color: #ffffff !important; color: #000000 !important; border: 1px solid #000000 !important; padding: 2px 4px !important; border-radius: 2px !important; font-size: 10px !important; } .edgeLabel rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 0.8px !important; } .cluster rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 1.5px !important; } .node rect, .node circle, .node ellipse, .node polygon, .node path { fill: #ffffff !important; stroke: #000000 !important; }'
}}%%

flowchart TD
    classDef comp fill:#ffffff,stroke:#000000,stroke-width:1.2px,color:#000000;
    classDef hub fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000;
    classDef ext fill:#ffffff,stroke:#000000,stroke-width:1.2px,stroke-dasharray: 3 3,color:#000000;

    subgraph TIER_CLIENT ["TIER 1: PRESENTATION & CLIENT LAYER (Next.js 15 / React / Tailwind)"]
        direction TB
        C_ROUTER["Next.js App Router & Layout System<br/>(Client & Server Components)"]:::comp
        subgraph C_VIEWS ["Interactive Workspace Modules"]
            V_AUTH["1. User Sign-In & Auth Modal"]:::comp
            V_EXP["2. Ingestion & Schema Explorer"]:::comp
            V_CLN["3. Data Cleaner & Join Studio"]:::comp
            V_EDA["4. Profiling & EDA Dashboard"]:::comp
            V_INS["5. Visualisation & AI Chatbot"]:::comp
            V_AUTO["6. AutoML Studio & Registry"]:::comp
            V_REP["7. Executive Report & Deck View"]:::comp
        end
        C_STATE["Client State & Supabase Auth SDK<br/>(WebSocket Client / SWR Hooks)"]:::comp
    end

    subgraph TIER_GATEWAY ["TIER 2: API GATEWAY & NETWORK SECURITY (FastAPI / ASGI)"]
        direction TB
        GW_PROXY["Reverse Proxy & Path Rewrites (/api/*)"]:::comp
        GW_SEC["Security Stack: CORS / OWASP Headers / Session / SlowAPI Rate Limiter"]:::comp
        GW_AUTH["Authentication Guard: Google OAuth 2.0 / JWT Bearer Validation"]:::comp
    end

    subgraph TIER_SERVICES ["TIER 3: APPLICATION SERVICES & ROUTING (FastAPI Routers)"]
        direction TB
        subgraph R_ROUTERS ["API Route Controllers"]
            R_AUTH["auth.py / teams.py"]:::comp
            R_UP["upload.py"]:::comp
            R_PROC["procedures.py / joins.py"]:::comp
            R_WORK["workspace.py / projects.py"]:::comp
            R_INS["insights.py / dashboard.py"]:::comp
            R_ML["automl.py / models.py"]:::comp
        end
        WS_MGR["WebSocket Manager<br/>(/ws Live Progress Stream)"]:::hub
        JOB_EXEC["Async Task & Job Manager<br/>(ThreadPoolExecutor / Celery)"]:::hub
    end

    subgraph TIER_CORE ["TIER 4: CORE ANALYTICAL ENGINES & PROCESSING PIPELINE"]
        direction TB
        E1_AUTH["1. User Sign-In & Session<br/>(OAuth 2.0 / JWT / RBAC / Quota Guard)"]:::comp
        E2_UPLOAD["2. Dataset Upload & Ingestion<br/>(CSV, Excel Online, Sheets API, DB Connectors)"]:::comp
        E3_CLEAN["3. Data Cleaning & Transformation<br/>(DataCleaner, JoinEngine, DuckDB DF-SPE DAG)"]:::comp
        E4_PROFILE["4. Data Profiling and Analysis<br/>(EDA Engine, 14-Scanner Insights, Statistical Rigor)"]:::comp
        E5_VIS_AI["5. Visualisation & AI-Assisted Exploration<br/>(Gemini 2.5 Flash Pipeline + Safe AST Code Sandbox)"]:::comp
        E6_AUTOML["6. Automated Machine Learning, where required<br/>(FLAML, Task Detection, Model Search, Registry)"]:::comp
        E7_REPORT["7. Report Generation<br/>(Pure Python Vector SVG Engine, Alert Baselines)"]:::comp

        %% Sequential pipeline flow
        E1_AUTH ==>|"User Session"| E2_UPLOAD
        E2_UPLOAD ==>|"Raw DataFrame"| E3_CLEAN
        E3_CLEAN ==>|"Clean Snapshot"| E4_PROFILE
        E4_PROFILE ==>|"Statistical Facts"| E5_VIS_AI
        E5_VIS_AI ==>|"Feature Matrix"| E6_AUTOML
        E6_AUTOML ==>|"Model Metrics"| E7_REPORT
        E5_VIS_AI -.->|"Direct Reporting"| E7_REPORT
    end

    subgraph TIER_DATA ["TIER 5: DATA PERSISTENCE & EXTERNAL INTEGRATIONS"]
        direction TB
        subgraph DB_PERSIST ["Internal & Cloud Persistence"]
            DB_SQL["Relational DB: PostgreSQL (Supabase) / SQLite<br/>(Users, Workspaces, Procedures, Metadata)"]:::comp
            DB_OBJ["Object Storage: Supabase Bucket<br/>(dataforge-datasets / Parquet Cache / Snapshots)"]:::comp
            DB_CACHE["Distributed Cache & Queue: Redis<br/>(Job Registry & Task Queues)"]:::comp
        end
        subgraph EXT_SVCS ["External Third-Party APIs"]
            EXT_OAUTH["Google Cloud Console<br/>(OAuth 2.0 Auth Server)"]:::ext
            EXT_GEMINI["Google Generative AI<br/>(Gemini API Endpoint)"]:::ext
            EXT_RESEND["Resend Email API<br/>(Alert Notifications & Reports)"]:::ext
        end
    end

    %% Cross-Tier Connections
    C_ROUTER --> C_VIEWS
    C_VIEWS --> C_STATE
    C_STATE ==>|"HTTPS REST / WSS"| GW_PROXY

    GW_PROXY --> GW_SEC
    GW_SEC --> GW_AUTH
    GW_AUTH ==>|"Authorized Request"| R_ROUTERS
    GW_AUTH -.->|"WebSocket Handshake"| WS_MGR

    R_ROUTERS --> JOB_EXEC
    R_ROUTERS --> E1_AUTH
    R_ROUTERS --> E2_UPLOAD
    R_ROUTERS --> E3_CLEAN
    R_ROUTERS --> E4_PROFILE
    R_ROUTERS --> E5_VIS_AI
    R_ROUTERS --> E6_AUTOML
    R_ROUTERS --> E7_REPORT

    JOB_EXEC <-->|"Task Broadcast"| WS_MGR

    E2_UPLOAD -->|"Raw File"| DB_OBJ
    E3_CLEAN -->|"Parquet Snapshot"| DB_OBJ
    E4_PROFILE -->|"Metric Cache"| DB_SQL
    E5_VIS_AI <-->|"Prompt / Code"| EXT_GEMINI
    E6_AUTOML -->|"Artifact .joblib"| DB_OBJ
    E7_REPORT -->|"Dispatched Email"| EXT_RESEND
    E1_AUTH <-->|"Token Exchange"| EXT_OAUTH

    JOB_EXEC <-->|"Queue Worker"| DB_CACHE
    R_ROUTERS <-->|"State Sync"| DB_SQL
```

*Figure 3.2: Multi-Tiered System Architecture of DataForge v3.*

---

<div style="page-break-after: always;"></div>

## Figure 3.3: Context Diagram (level 0) DFD

### Description
Figure 3.3 presents the formal Level 0 Data Flow Diagram (Context Diagram) under standard structured analysis notation, rendered with pure white entities and white arrow label backgrounds.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#ffffff',
    'primaryTextColor': '#000000',
    'primaryBorderColor': '#000000',
    'lineColor': '#000000',
    'secondaryColor': '#ffffff',
    'tertiaryColor': '#ffffff',
    'mainBkg': '#ffffff',
    'nodeBorder': '#000000',
    'clusterBkg': '#ffffff',
    'clusterBorder': '#000000',
    'defaultLinkColor': '#000000',
    'titleColor': '#000000',
    'edgeLabelBackground': '#ffffff',
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '11px'
  },
  'themeCSS': '.edgeLabel { background-color: #ffffff !important; color: #000000 !important; border: 1px solid #000000 !important; padding: 2px 4px !important; border-radius: 2px !important; font-size: 10px !important; } .edgeLabel rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 0.8px !important; } .cluster rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 1.5px !important; } .node rect, .node circle, .node ellipse, .node polygon, .node path { fill: #ffffff !important; stroke: #000000 !important; }'
}}%%

flowchart TD
    classDef entity fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    classDef systemProcess fill:#ffffff,stroke:#000000,stroke-width:2.5px,color:#000000;

    %% Central Process
    P0(["0.0<br/>DATAFORGE SYSTEM<br/>(Automated Data Engineering, Profiling,<br/>AI Analytics & AutoML Platform)"]):::systemProcess

    %% Terminators
    E_USER["EXTERNAL ENTITY: E1<br/>Data Analyst / End User<br/>(Browser Client)"]:::entity
    E_SOURCES["EXTERNAL ENTITY: E2<br/>External Data Providers<br/>(Google Sheets / External DBs)"]:::entity
    E_AUTH["EXTERNAL ENTITY: E3<br/>Google OAuth 2.0<br/>(Identity Provider)"]:::entity
    E_AI["EXTERNAL ENTITY: E4<br/>Google Gemini AI<br/>(Generative Language Model)"]:::entity
    E_CLOUD["EXTERNAL ENTITY: E5<br/>Supabase Cloud Platform<br/>(PostgreSQL & Object Bucket)"]:::entity
    E_NOTIF["EXTERNAL ENTITY: E6<br/>Communication Services<br/>(Resend Email & Webhooks)"]:::entity

    %% Flows
    E_USER ==>|"1. Upload Files (CSV/Excel), Clean Rules,<br/>NL Queries, AutoML Targets"| P0
    P0 ==>|"2. Real-Time Ingestion Preview, Diff Cards,<br/>AI Narratives, Model Metrics & PDF Reports"| E_USER

    E_SOURCES -->|"3. Stream Remote Tabular Datasets & Sheet Cells"| P0
    P0 -.->|"4. API Credentials, Fetch Tokens & SQL Selects"| E_SOURCES

    E_AUTH -->|"5. User Identity Claims (sub, email, avatar)"| P0
    P0 -.->|"6. Authorization Code & Redirection Request"| E_AUTH

    P0 -->|"7. Prompt Context: Schema, Stats & NL Query"| E_AI
    E_AI -->|"8. Narrative Summaries & Pandas Analysis AST"| P0

    P0 -->|"9. Store Parquet Snapshots, DB Rows, Models & Logs"| E_CLOUD
    E_CLOUD -->|"10. Retrieve Workspaces, Lineage & Quotas"| P0

    P0 -->|"11. Metric Drift Alerts & Scheduled Reports"| E_NOTIF
    E_NOTIF -.->|"12. Delivery Acknowledgments"| P0
```

*Figure 3.3: Level 0 Context Data Flow Diagram.*

---

<div style="page-break-after: always;"></div>

## Figure 3.4: Detailed Diagram (level 1) DFD

### Description
Figure 3.4 decomposes process `0.0` into seven discrete Level 1 subprocesses and six internal data stores, formatted with pure white figures and white arrow label backgrounds.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#ffffff',
    'primaryTextColor': '#000000',
    'primaryBorderColor': '#000000',
    'lineColor': '#000000',
    'secondaryColor': '#ffffff',
    'tertiaryColor': '#ffffff',
    'mainBkg': '#ffffff',
    'nodeBorder': '#000000',
    'clusterBkg': '#ffffff',
    'clusterBorder': '#000000',
    'defaultLinkColor': '#000000',
    'titleColor': '#000000',
    'edgeLabelBackground': '#ffffff',
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '10px'
  },
  'themeCSS': '.edgeLabel { background-color: #ffffff !important; color: #000000 !important; border: 1px solid #000000 !important; padding: 2px 4px !important; border-radius: 2px !important; font-size: 10px !important; } .edgeLabel rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 0.8px !important; } .cluster rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 1.5px !important; } .node rect, .node circle, .node ellipse, .node polygon, .node path { fill: #ffffff !important; stroke: #000000 !important; }'
}}%%

flowchart TD
    classDef entity fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    classDef process fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000;
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

    %% Subprocesses (Level 1)
    P1(["1.0<br/>User Sign-In &<br/>Session Auth"]):::process
    P2(["2.0<br/>Dataset Upload,<br/>Ingest & Validate"]):::process
    P3(["3.0<br/>Data Cleaning,<br/>Joins & Procedures"]):::process
    P4(["4.0<br/>Data Profiling &<br/>Analysis Engine"]):::process
    P5(["5.0<br/>Visualisation &<br/>AI Exploration"]):::process
    P6(["6.0<br/>Automated ML<br/>(where required)"]):::process
    P7(["7.0<br/>Report Generation<br/>& Baseline Alerts"]):::process

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

*Figure 3.4: Level 1 Detailed Data Flow Diagram.*

---

<div style="page-break-after: always;"></div>

## Figure 3.5: Functional Module Interaction Diagram

### Description
Figure 3.5 formalizes the inter-module contracts, asynchronous event dependencies, and data coupling across the core Python packages, rendered in pure white figures with white arrow label backgrounds.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#ffffff',
    'primaryTextColor': '#000000',
    'primaryBorderColor': '#000000',
    'lineColor': '#000000',
    'secondaryColor': '#ffffff',
    'tertiaryColor': '#ffffff',
    'mainBkg': '#ffffff',
    'nodeBorder': '#000000',
    'clusterBkg': '#ffffff',
    'clusterBorder': '#000000',
    'defaultLinkColor': '#000000',
    'titleColor': '#000000',
    'edgeLabelBackground': '#ffffff',
    'fontFamily': 'Helvetica, Arial, sans-serif',
    'fontSize': '11px'
  },
  'themeCSS': '.edgeLabel { background-color: #ffffff !important; color: #000000 !important; border: 1px solid #000000 !important; padding: 2px 4px !important; border-radius: 2px !important; font-size: 10px !important; } .edgeLabel rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 0.8px !important; } .cluster rect { fill: #ffffff !important; stroke: #000000 !important; stroke-width: 1.5px !important; } .node rect, .node circle, .node ellipse, .node polygon, .node path { fill: #ffffff !important; stroke: #000000 !important; }'
}}%%

flowchart TD
    classDef module fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000;
    classDef engine fill:#ffffff,stroke:#000000,stroke-width:1.8px,color:#000000;
    classDef infra fill:#ffffff,stroke:#000000,stroke-width:1.5px,stroke-dasharray: 4 2,color:#000000;

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

*Figure 3.5: Functional Module Interaction and Contract Flow Diagram.*
