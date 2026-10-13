# ADR 0001: Feature Triage (Keep, Freeze, and Cut Decisions)
**Status:** Accepted  
**Date:** October 13, 2026  
**Context:** Multi-perspective audit and execution of DataForge A+ Implementation Plan.

---

## 1. Static Pipeline Code Exporter (`pipeline.py:export`)
* **Decision:** **REPLACE (P3-11)**
* **Rationale:** The current implementation emits hardcoded string templates for dbt, Airflow, and pytest that cannot be validated, debugged, or executed inside the platform. It will be replaced by the compilation of Stored Procedure definitions into verified, runnable DuckDB / dbt SQL with full test coverage.

## 2. One-Click "Clean All" Magic Button (`data_cleaner.py`)
* **Decision:** **DEPRECATE & REPLACE WITH PREVIEW (P1-5)**
* **Rationale:** Indiscriminate median and mode imputation silently corrupts distribution variance and introduces artificial bias in production data. "Clean All" as an unprompted mutation is removed; instead, DataForge provides suggested cleaning transformations that require explicit per-column review and interactive diff previews before application.

## 3. In-App AutoML Training (`automl_trainer.py`)
* **Decision:** **FREEZE & QUARANTINE TO DISTRIBUTED WORKERS (P4-2)**
* **Rationale:** Synchronous or unmetered in-process training threatens FastAPI event-loop health. If retained, AutoML must be moved to Celery/Redis isolated workers with strict scikit-learn `Pipeline` + `ColumnTransformer` encapsulation to prevent cross-validation target leakage.

## 4. Heavy Three.js Landing Canvas (`ThreeBackground.tsx`)
* **Decision:** **CUT / RETIRE**
* **Rationale:** The 3D canvas consumes 15–25% client GPU/CPU, degrades Core Web Vitals (LCP/INP), and projects a consumer demo aesthetic rather than a high-performance enterprise data tool. Replaced with lightweight CSS/SVG design tokens.

## 5. Cron Email Report Scheduling (`ReportSchedule`)
* **Decision:** **SUPERSEDE BY SCHEDULE ENGINE (P5-7)**
* **Rationale:** Scheduled HTML emails on static CSVs are obsolete. Replaced by webhook and Slack alerts triggered on procedure completion or data quality assertion failures.
