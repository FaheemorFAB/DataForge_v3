# 🛠️ DataForge v3

DataForge is a premium, enterprise-grade automated data engineering, analytical profiling, and machine learning platform. It empowers organizations to seamlessly ingest raw datasets, execute rule-based data cleaning pipelines, run advanced statistical scans, generate AI-driven narrative business insights, query datasets using conversational natural language, train predictive models automatically, and distribute publication-quality reports.

---

## 📸 Platform Showcase

Explore the end-to-end user journey within the DataForge ecosystem, showcasing the workflow from secure entry to machine learning deployment.

### 🔐 1. Secure Authentication Portal
A secure gateway featuring fast, one-click authentication exclusively powered by Google OAuth 2.0.

<div align="center">
  <img src="assets/auth.png" alt="Secure Authentication Portal" width="900" />
  <br/>
  <em>Fig 1: The secure login modal with seamless Google OAuth integration.</em>
</div>

### 📥 2. Data Ingestion
Upload local datasets (CSV, Excel, Parquet, JSON), connect directly to cloud workbooks (Google Sheets & Microsoft 365 OneDrive / SharePoint Excel Online) with automatic tab detection and live "Sync Sheet" delta tracking, or stream tables from cloud and local relational databases (MySQL, PostgreSQL, Supabase, ClickHouse Cloud, SQLite, DuckDB) via the encrypted Connection Vault.

<div align="center">
  <img src="assets/upload.png" alt="Intelligent Data Ingestion" width="900" />
  <br/>
  <em>Fig 2: The intuitive ingestion interface supporting local drag-and-drop, cloud spreadsheets with live sync deltas, and encrypted database connections.</em>
</div>

### 🔍 3. Data Preview
Tabular grid preview of ingested data highlighting missing cell percentages, basic data types, and summary statistics.

<div align="center">
  <img src="assets/preview.png" alt="Interactive Data Preview" width="900" />
  <br/>
  <em>Fig 3: Real-time, high-fidelity data preview with inline column statistics.</em>
</div>

### 🧹 4. Data Cleaning Pipeline
Apply rule-based transformations such as outlier clipping, missing value imputation, and type casting, saving the results in a parquet-optimized storage format.

<div align="center">
  <img src="assets/cleaning_1.png" alt="Data Cleaning Pipeline Step 1" width="900" />
  <br/><br/>
  <img src="assets/Cleaning_2.png" alt="Data Cleaning Pipeline Step 2" width="900" />
  <br/>
  <em>Fig 4: Step-by-step visual data cleaning pipeline with instant transformation feedback.</em>
</div>

### 📊 5. Interactive Dashboard
A central workspace showing key dataset metrics, interactive charts, and live activity feeds.

<div align="center">
  <img src="assets/Dashboard.png" alt="Executive Dashboard" width="900" />
  <br/>
  <em>Fig 5: The central command dashboard featuring real-time metrics and live activity feeds.</em>
</div>

### 💡 6. AI Insights
Run automated statistical scans and correlation detection, paired with insightful executive summaries compiled by Google Gemini.

<div align="center">
  <img src="assets/Insights.png" alt="AI-Powered Insight Engine" width="900" />
  <br/>
  <em>Fig 6: The AI Insight Engine revealing hidden correlations, anomalies, and executive narratives.</em>
</div>

### 💬 7. AI Multi-Agent Analyst & Orchestrator
Interact with your data conversationally through an autonomous multi-agent ecosystem. Coordinated by a **Supervisor Agent** ("Chief Data Analyst"), specialized sub-agents collaborate to clean data, train models, export pipelines, and execute sandboxed code with real-time Chart.js visual synthesis.

<div align="center">
  <img src="assets/AiQuery.png" alt="Conversational AI Analyst Chatbot" width="900" />
  <br/>
  <em>Fig 7: The multi-agent AI system orchestrating domain tools and executing sandboxed analytical Python code in real-time.</em>
</div>

### 🤖 8. AutoML Training
Automatically train classification or regression models on your dataset.

<div align="center">
  <img src="assets/AutoML.png" alt="AutoML Model Training" width="900" />
  <br/>
  <em>Fig 8: Zero-code AutoML model training interface with automatic task detection and tuning.</em>
</div>

### 📑 9. Automated Reporting
Generate and export strategic insights into printable presentation decks powered by AI.

<div align="center">
  <img src="assets/Report.png" alt="Automated Reporting" width="900" />
  <br/>
  <em>Fig 9: Generate and download publication-ready reports with one click.</em>
</div>

### 👥 10. The Team
Meet the talented engineers who built the DataForge ecosystem.

<div align="center">
  <img src="assets/TeamSection.png" alt="Team Section" width="900" />
  <br/>
  <em>Fig 10: The DataForge team section.</em>
</div>

---

## 🧠 Autonomous Multi-Agent Architecture

DataForge incorporates a hierarchical, deterministic-first multi-agent system designed to handle complex data operations without hallucination:

```
                      ┌─────────────────────────────────────────┐
                      │    Supervisor Agent ("Chief Analyst")   │
                      │  • Evaluates Intent & Schema Metadata   │
                      │  • Fast-Path Zero-Latency Intercepts   │
                      │  • Ground-Truth Math Synchronization    │
                      └────────────────────┬────────────────────┘
                                           │
         ┌───────────────────┬─────────────┴───────┬───────────────────┐
         ▼                   ▼                     ▼                   ▼
┌──────────────────┐ ┌───────────────┐ ┌──────────────────────┐ ┌───────────────┐
│   CleanerAgent   │ │  AutoMLAgent  │ │    PipelineAgent     │ │AnalyticsAgent │
│ • Missing Values │ │ • Task Type   │ │ • Apache Airflow DAG │ │ • AST Sandbox │
│ • Outlier Clip   │ │ • Feature Sig │ │ • dbt SQL Models     │ │ • Pandas Code │
│ • State Sync     │ │ • Top Models  │ │ • Python ETL Scripts │ │ • Real Values │
│ • Snapshot Undo  │ │ • Class Ratio │ │ • Retry & SLA Logic  │ │ • Local Fallbk│
└──────────────────┘ └───────────────┘ └──────────────────────┘ └───────┬───────┘
                                                                       │
                                                                       ▼
                                                              ┌─────────────────┐
                                                              │ VisualizerAgent │
                                                              │ • Chart.js Spec │
                                                              │ • Dynamic Types │
                                                              │ • Anti-Mislead  │
                                                              └─────────────────┘
```

### Specialized Domain Agents in Detail

1. **Supervisor Agent ("Chief Data Analyst")**:
   - Central coordinator orchestrating query flow, conversational onboarding, and intent arbitration.
   - **Zero-Latency Intercepts**: Greetings ('hello', 'help') and metadata requests ('describe dataset') are intercepted instantly via regex matchers with 0ms external API latency.
   - **Structured Routing**: Dispatches direct tasks immediately; routes ambiguous queries via Google Gemini (`gemini-2.5-flash`) structured JSON schemas (`AgentSelectionDecision`).
   - **Ground-Truth Synchronization**: Programmatically verifies all LLM textual narrative against raw computational array output to eliminate hallucinations (100% mathematical fidelity).

2. **CleanerAgent (Data Sanitization & Hygiene)**:
   - Evaluates missing value distributions and outlier skew across columns.
   - **Automated Imputation**: Imputes numeric columns with the median (avoiding outlier skew) and categorical columns with the mode.
   - **IQR Outlier Capping**: Caps extreme values using 1.5x Interquartile Range boundaries without discarding valid rows.
   - **Quality Score Telemetry**: Calculates live data completeness improvements (e.g. 81.5% &rarr; 100.0%) and syncs the active workspace DataFrame.
   - **1-Click Snapshot Rollbacks**: Records pre-transformation state snapshots; typing `undo` or `revert` immediately restores the previous dataset.

3. **AutoMLAgent (Predictive Formulation & Advisor)**:
   - **Task Detection**: Analyzes target column cardinalities and distributions to determine Binary Classification, Multiclass Classification, or Continuous Regression.
   - **High-Signal Feature Selection**: Computes mutual information and correlation scores to highlight the most predictive features while flagging data leakage risks.
   - **Class Imbalance Auditing**: Evaluates majority vs. minority class ratios and recommends optimal evaluation metrics (PR-AUC, F1-Score).
   - **Algorithm Recommendations**: Benchmarks LightGBM, XGBoost, Random Forest, and Ridge Regression, seeding parameters directly into the AutoML Studio.

4. **PipelineAgent (Production ETL & Orchestration Compiler)**:
   - Translates exploratory workspace transformations into production data engineering code.
   - **Apache Airflow DAGs**: Compiles production Python DAGs with `@dag`, `PythonOperator`, retry counts, SLAs, and error logging.
   - **dbt Models**: Generates dimensional SQL staging models complete with `schema.yml` contracts, `not_null`, and `unique` data tests.
   - **Standalone Python Scripts**: Generates executable CLI scripts utilizing Pandas and DuckDB with structured logging.

5. **AnalyticsAgent (Sandboxed Mathematical & Statistical Engine)**:
   - **AST-Isolated Python Sandbox**: Validates Python expressions through an Abstract Syntax Tree scanner, blocking dangerous calls (`os`, `sys`, `socket`, `eval`, `open`).
   - **Vectorized Computations**: Computes Pearson and Spearman correlation matrices, quantiles (Q1, Q2, Q3), variance, skewness, kurtosis, and multi-column groupings.
   - **High-Availability Deterministic Fallback**: Continues executing exact mathematical aggregations and correlations locally even if Gemini API credits are depleted (HTTP 402) or offline.

6. **VisualizerAgent (Interactive Graphical Synthesis & Chart.js Engine)**:
   - **Typed Chart Synthesis**: Translates numerical arrays into interactive Chart.js specifications (Bar, Line, Scatter, Pie/Doughnut, Histogram).
   - **Aesthetic Validation**: Enforces statistical charting rules (e.g. prohibits line charts for unordered categorical dimensions).
   - **Design System Token Harmony**: Applies responsive sizing, theme-aware contrast tokens, and currency/percentage hover tooltips.

### High-Availability Local Analytics Engine
If external LLM APIs are unreachable or have depleted prepayment credits (HTTP 402), DataForge automatically falls back to its **Local Pandas Engine**. Queries regarding specific columns (e.g., *"What is the average customer_age?"*) are computed locally in real time and visualized with live charts, guaranteeing 100% platform uptime.

---

## ⚙️ Environment Configuration & Setup

Configuration is managed via `.env` in the project root:

```env
# Server URLs
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:5000

# Google Gemini API (Hot-Reloading Enabled)
GEMINI_API_KEY=your_gemini_api_key_here

# Supabase Storage & Persistence
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
SUPABASE_BUCKET=dataforge-datasets
```

> **Hot-Reloading:** When updating `GEMINI_API_KEY`, DataForge automatically re-reads `.env` on your next request without requiring a server reboot. Ensure your Google AI Studio project has an active credit balance or free-tier quota at [https://aistudio.google.com](https://aistudio.google.com).

