# 🛠️ DataForge v3 — Enterprise AI Data & Analytics Platform

DataForge v3 is a premium, enterprise-grade automated data engineering, analytical profiling, dynamic data cleaning, and machine learning platform. Built with a high-performance **FastAPI** backend and a modern **Next.js** frontend, DataForge empowers organizations to ingest raw datasets, execute interactive dynamic data cleaning pipelines, run 13+ automated statistical insight algorithms, query data conversationally using AI, train predictive AutoML models, and export McKinsey-grade executive slide decks and vector PDF reports.

---

## 🎨 Architecture & Data Flow

```mermaid
graph TD
    classDef client fill:#E8F0FE,stroke:#4285F4,stroke-width:2px;
    classDef api fill:#F1F3F4,stroke:#3C4043,stroke-width:2px;
    classDef worker fill:#FCE8E6,stroke:#D93025,stroke-width:2px;
    classDef external fill:#FFE8D6,stroke:#DDBEA9,stroke-width:2px;
    classDef storage fill:#E6F4EA,stroke:#34A853,stroke-width:2px;

    User[Next.js 14 Frontend SPA]:::client
    FastAPI[FastAPI / Uvicorn ASGI Engine]:::api
    Gemini[Google Gemini 2.5 AI Engine]:::external
    Redis[Redis Response Cache & Rate Limiter]:::worker
    Supa[Supabase PostgreSQL & Object Storage]:::storage
    AutoML[FLAML / Scikit-Learn / XGBoost Engine]:::worker

    User -->|REST API / WebSockets| FastAPI
    FastAPI <-->|Metadata & User Storage| Supa
    FastAPI <-->|Cached Insights & State| Redis
    FastAPI <-->|Model Tuning & Training| AutoML
    FastAPI <-->|Narrative Summaries & AI Query| Gemini
    FastAPI -->|SVG & PDF Generation| User
```

---

## 🌟 Key Platform Capabilities

### 🧹 1. Dynamic Data Cleaning Studio
- **Automated 1-Click Clean**: Normalizes headers to `snake_case` using PyJanitor, prunes columns with >60% missing data, and imputes null values using distribution skewness heuristics.
- **Dynamic Interactive Studio**: Granular per-column cleaning rules:
  - **Imputation**: Mean, Median, Mode, Zero, Custom Constant, Forward Fill (`ffill`), Backward Fill (`bfill`), or Drop Missing Rows.
  - **Outlier Handling**: Winsorization (1st/99th percentile clipping), Replace with Median, or Remove Outlier Rows.
  - **Text Normalization**: Lowercase, Uppercase, Trim Whitespace, Header Normalization.
  - **Type Casting**: Explicit casting to Float, Integer, Datetime, or String.
- **Audit Action Logs**: Real-time before vs. after dataset stats, missing percentage diffs, and downloadable cleaned CSV/Excel files.

### 💡 2. Automated Insight Detection Engine
- **13 Specialized Plugins**:
  1. `TrendInsight` — Identifies metric growth and decline patterns over time.
  2. `TopPerformerInsight` — Ranks top and bottom dimensions.
  3. `CorrelationInsight` — Detects metric dependencies and correlations.
  4. `AnomalyInsight` — IQR + Z-score hybrid anomaly detection with red threshold bars.
  5. `DistributionInsight` — Skewness, Kurtosis, and histogram distribution profiling.
  6. `ContributionInsight` — Donut chart representation of dimension share.
  7. `SegmentInsight` — Grouped segment performance analysis.
  8. `ChangeInsight` — Period-over-period % change comparison.
  9. `FeatureImportanceInsight` — Key driver impact scores.
  10. `DataQualityInsight` — Column-level completeness and missingness meters.
  11. `OutlierSummaryInsight` — Column-by-column IQR outlier counts.
  12. `NumericSummaryInsight` — Coefficient of variation analysis.
  13. `CategoricalInsight` — Category concentration and dominant value share.
- **9 Dedicated Chart Renderers**: Custom Chart.js visualizations (Smooth Line, Ranked Horizontal Bar, Donut, Scatter Plot, Annotated Anomaly Bar, 2-Bar Period Change) with custom type themes.

### 📄 3. McKinsey-Grade Royalty Business Data Reports
- **5-Slide Executive Presentation Deck**:
  - **Slide 1**: Executive Cover with Royalty Seal Crest (`DATAFORGE EXECUTIVE ADVISORY`).
  - **Slide 2**: KPI Footprint & Executive Advisory Assessment.
  - **Slide 3**: Strategic Insights with Embedded Vector SVG Charts.
  - **Slide 4**: Data Health Diagnostics & Column Schema Footprint.
  - **Slide 5**: Actionable Execution Plan & Numbered Priority Cards.
- **Pure Python SVG Vector Chart Engine**: Generates pure SVG line, bar, donut, and scatter graphics that render instantly in browser iframes and export to PDF with vector crispness.
- **Corporate Light Theme**: Crisp `#FFFFFF` slides, deep slate titles (`#0F172A`), gold/emerald metallic accents, and seamless 1-click vector PDF saving.

### 📊 4. Interactive Analytics Dashboard
- Auto-cased titles (`Title Case`), explicit Y-axis aggregation hints (e.g. `Revenue (sum)`), formatted tick labels, rotated X-axis categories, and responsive chart legends.

### 🤖 5. Automated Machine Learning (AutoML) Studio
- Automatic task detection (Classification vs Regression), hyperparameter tuning via **FLAML**, leaderboard model evaluation (F1 / ROC-AUC / RMSE), **SHAP** feature importance graphs, and downloadable `.pkl` model assets.

### 💬 6. Conversational AI Analyst Chatbot
- Ask natural language questions about your dataset. Features an AST-validated Python code sandbox that safely generates, executes, and renders dynamic pandas dataframes and charts.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS | High-performance SPA with modern dark/light aesthetics |
| **Visualization** | Chart.js, React-Chartjs-2, Custom SVG Engine | Interactive dashboard charts & vector PDF report graphics |
| **Backend Framework** | FastAPI (Python 3.11+), Uvicorn | High-concurrency async REST API and WebSockets |
| **Data Engine** | Pandas 2.3+, NumPy 2.3+, PyArrow, OpenPyXL, PyJanitor | Fast Parquet storage, DataFrame manipulation & cleaning |
| **Machine Learning** | FLAML, Scikit-Learn, LightGBM, XGBoost, SHAP | Automated model selection, tuning, and explainability |
| **AI Orchestration** | Google Gemini API (`gemini-2.5-flash`) | Executive narrative generation and natural language data querying |
| **Database & Cache** | Supabase (PostgreSQL), Redis | Account data, workspace metadata, and response caching |
| **Report PDF Engine**| Pure Python SVG Engine + WeasyPrint / Print API | Pixel-perfect A4 landscape slide PDF generation |

---

## ⚙️ Quick Start & Local Setup Guide

### Prerequisites
- **Node.js 18+** & `npm` — [nodejs.org](https://nodejs.org/)
- **Python 3.11+** — [python.org](https://www.python.org/)
- **Redis** *(Optional for caching)* — [redis.io](https://redis.io/)

---

### Step 1 — Clone Repository & Environment Setup

```bash
# Clone repository
git clone https://github.com/your-org/DataForge_v3.git
cd DataForge_v3-main

# Set up environment variables
cp .env.example .env
```

---

### Step 2 — Backend Setup (FastAPI)

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate Virtualenv
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat
# macOS / Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run FastAPI backend server
python main.py
```
> The backend server will start on **`http://localhost:8000`** (API Docs available at `http://localhost:8000/docs`).

---

### Step 3 — Frontend Setup (Next.js)

In a **second terminal window**:

```bash
# Navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```
> The frontend application will start on **`http://localhost:3000`**.

---

## 📖 User Guide & Step-by-Step Workflow

1. **Upload Dataset**: Navigate to Workspace and drag-and-drop a CSV or Excel file (or connect via Google Sheets link).
2. **Data Cleaning Studio**:
   - Click **1-Click Auto Clean** for instant automated cleaning.
   - Or toggle **Dynamic Studio** to build custom per-column rules (imputation, outlier clipping, text casing, type casting). Click **Apply Dynamic Pipeline**.
3. **Run Insight Engine**: Switch to the **Insight Engine** tab and click **Run Insights**. View 13+ auto-detected trends, anomalies, and correlations rendered with custom visual charts.
4. **Explore Dashboard**: Switch to **Dashboard** for auto-generated analytical charts, aggregated metrics, and distribution visuals.
5. **Train AutoML Model**: Select your target column in **AutoML**, set your time budget, and train optimal models with SHAP feature importance.
6. **Generate Executive Business Report**:
   - In the **Report** section, click **Generate Analysis**.
   - Preview the 5-slide McKinsey presentation deck with vector SVG charts.
   - Click **Download PDF** for instant 1-click vector PDF saving!

---

## 📄 License & Credits

Built with ❤️ by the DataForge Team. Powered by FastAPI, Next.js, Chart.js, PyJanitor, FLAML, and Google Gemini 2.5.
