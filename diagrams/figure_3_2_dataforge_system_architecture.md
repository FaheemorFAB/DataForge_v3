# Figure 3.2: DataForge System Architecture
**DataForge v3 System Architecture Series**  
**Document Standard:** Multi-Tiered System Architecture (IEEE 1471 / ISO 42010)  
**Page Budget:** 1 Page (A4 Portrait, Black & White / Grayscale Print-Ready)  

---

## 1. Architectural Narrative
Figure 3.2 depicts the five-tier structural engineering architecture of DataForge v3. The system is decoupled into discrete, scalable, and secure tiers with pure white figures and high-contrast monochrome textbook formatting:

1. **Tier 1: Presentation & Client Layer (Next.js 15 / React / Tailwind)**: Encapsulates the App Router, server/client component boundaries, and individual workspace view modules matching the end-to-end user journey: User Sign-In, Ingestion Explorer, Data Cleaner & Join Studio, Profiling & EDA Dashboard, Visualisation & AI Chatbot, AutoML Studio, and Executive Reports.
2. **Tier 2: API Gateway & Network Security (FastAPI / ASGI)**: Manages reverse proxy path rewrites (`/api/*`), CORS policies, OWASP defensive security headers, cookie session encryption, and `SlowAPI` token-bucket rate limiting.
3. **Tier 3: Application Services & Routing**: Routes HTTP/WebSocket traffic through modular controllers (`upload`, `workspace`, `procedures`, `joins`, `insights`, `automl`, `dashboard`). Employs an asynchronous `JobManager` backed by a `ThreadPoolExecutor` and Celery/Redis for non-blocking task processing.
4. **Tier 4: Core Analytical Engines & Processing Pipeline**: Houses the core pipeline stages: User Sign-In & Session, Dataset Upload & Ingestion, Data Cleaning & Transformation, Data Profiling and Analysis, Visualisation and AI-Assisted Exploration, Automated Machine Learning (where required), and Report Generation.
5. **Tier 5: Data Persistence & External Integrations**: Combines relational metadata storage (PostgreSQL on Supabase or local SQLite), object storage (`dataforge-datasets` bucket for Parquet caches and snapshots), Redis distributed message broker, and third-party APIs (Google Cloud OAuth 2.0, Google Generative AI, Resend Email).

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

---

## 3. Structural Layer Specifications

| Tier | Component Group | Technology Stack | Security / Protocol |
| :--- | :--- | :--- | :--- |
| **Tier 1: Client** | Workspace UI & State | Next.js 15, React 19, Tailwind CSS | HTTPS, WSS, HttpOnly Cookies |
| **Tier 2: Gateway** | Routing & Ingress Defense | FastAPI, Uvicorn, SlowAPI | JWT Bearer, CORS Origin Validation |
| **Tier 3: Services** | Controllers & Job Dispatch | FastAPI Routers, ThreadPoolExecutor | Celery Worker Isolation, Task Registry |
| **Tier 4: Pipeline Core** | Analytical Compute Pipeline | DuckDB, Pandas, NumPy, FLAML, Gemini | AST Sanitization, Restricted Sandbox |
| **Tier 5: Storage** | Data & Cloud Endpoints | PostgreSQL, Supabase Storage, Redis | Row Level Security (RLS), AES Encryption |
