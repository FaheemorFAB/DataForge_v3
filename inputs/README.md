# DataForge v3: Benchmark & Demonstration Dataset Suite

This directory contains production-grade benchmark datasets designed to demonstrate the **maximum analytical, statistical, and ingestion capabilities** of DataForge v3 across diverse enterprise themes and file formats.

---

## 📊 Dataset Catalog & Capability Matrix

| Dataset | Format | Domain / Theme | Records | Key Measures (KPIs) | Features & Algorithms Demonstrated |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`saas_subscription_churn.csv`** | CSV | B2B SaaS Customer Success | 1,500 | `mrr_usd`, `churn_risk_flag` | Churn classification AutoML, MRR variance decomposition, Usage correlations (MAU, NPS, Tickets), **Protected attribute isolation** (`account_exec_gender`). |
| **`ecommerce_global_retail.xlsx`** | Excel (XLSX) | Omnichannel Retail & E-Commerce | 2,500 (3 sheets) | `gross_revenue_usd`, `net_profit_usd` | **Multi-sheet Excel workbook** (`Orders`, `Customers`, `Products`), Multi-table Joins (`POST /joins/suggest`), Pareto distributions, Holiday seasonal spikes. |
| **`fintech_credit_risk.parquet`** | Apache Parquet | FinTech & Consumer Lending | 2,000 | `default_risk_flag`, `loan_amount_usd` | **High-speed columnar Parquet ingestion**, Credit risk modeling, FICO non-linear correlations, Outlier detection. |
| **`fintech_credit_risk.csv`** | CSV | FinTech & Consumer Lending | 2,000 | `default_risk_flag`, `loan_amount_usd` | CSV counterpart for tabular comparison with Parquet ingestion. |
| **`healthcare_hospital_operations.json`** | JSON | Healthcare & Hospital Telemetry | 1,200 | `total_treatment_cost_usd`, `readmitted_30d_flag` | **Nested JSON parsing & auto-flattening** (`root_key="patients"`, nested `vitals`), Inpatient readmission risk, Length of Stay (LOS) regression. |
| **`healthcare_stream.jsonl`** | NDJSON / JSONL | Streaming Healthcare Telemetry | 1,200 | `total_treatment_cost_usd`, `readmitted_30d_flag` | Line-delimited JSON ingestion for event streaming pipelines. |
| **`supply_chain_iot_telemetry.csv`** | CSV | Industrial IoT & Predictive Maintenance | 2,500 | `oee_efficiency_pct`, `power_consumption_kwh` | **High-frequency time-series forecasting** (hourly intervals), Sensor anomaly detection (vibration & temp stress cycles), Predictive breakdown flagging. |
| **`workforce_talent_analytics.xlsx`** | Excel (XLSX) | Human Capital & Workforce Management | 900 | `annual_salary_usd`, `attrition_status` | **Demographic equity & protected attributes** (`gender`, `ethnicity`), Compensation variance decomposition, Employee attrition prediction. |
| **`sqlite_sample/dataforge_warehouse.db`** | SQLite DB | Relational Enterprise Data Warehouse | 3 tables | Normalized Star-Schema | **Direct external database ingestion** (`/upload/database/*`), SQL schema introspection, table selection (`dim_customers`, `dim_products`, `fact_orders`). |

---

## 🔍 Detailed Theme Breakdown

### 1. B2B SaaS Subscription & Churn Analytics (`saas_subscription_churn.csv`)
* **Use Case:** Subscription growth, account expansion, and churn prevention.
* **Columns:**
  - `account_id`: High-cardinality identifier (correctly bypassed by statistical driver scanners).
  - `signup_date`: Timestamp for cohort analysis and ARR trajectory forecasting.
  - `plan_tier`: Segment dimension (`Starter`, `Professional`, `Growth`, `Enterprise`).
  - `industry`, `region`: Demographic segment dimensions.
  - `monthly_active_users`, `feature_adoption_pct`, `nps_score`: Operational activity metrics.
  - `support_tickets_30d`: Heavy outlier distribution; strong correlation with churn.
  - `mrr_usd`: Continuous revenue KPI.
  - `account_exec_gender`: Protected attribute (strictly routed to demographic breakdowns; never labeled as a causal driver).
  - `churn_risk_flag`: Binary target for AutoML classification.

### 2. E-Commerce Omnichannel Retail (`ecommerce_global_retail.xlsx`)
* **Use Case:** Multi-table relational e-commerce analysis and multi-sheet spreadsheet ingestion.
* **Sheets in Workbook:**
  1. `Orders` (2,500 rows): Transactional records with `order_date`, `gross_revenue_usd`, `cost_of_goods_usd`, `shipping_fee_usd`, `net_profit_usd`, and `order_status`.
  2. `Customers` (549 rows): Customer demographic census with `customer_id`, `loyalty_tier`, `acquisition_channel`.
  3. `Products` (20 rows): Product catalog with `sku_id`, `category`, `unit_cost_usd`, `retail_price_usd`.
* **Testing Multi-Table Joins:**
  Upload `Orders`, then use DataForge's **Join Engine** (`POST /joins/suggest`) to join with `Customers` on `customer_id` and `Products` on `sku_id`!

### 3. FinTech Consumer Credit Risk (`fintech_credit_risk.parquet` / `.csv`)
* **Use Case:** Credit scoring, loan default risk assessment, and high-performance columnar ingestion.
* **Columns:** `loan_application_id`, `applicant_age`, `annual_income_usd`, `debt_to_income_ratio`, `credit_score_fico`, `delinquencies_past_24m`, `interest_rate_pct`, `default_risk_flag`.
* **Analytical Highlights:**
  - Non-linear relationship between FICO score and interest rates.
  - Strong classification signal for default risk.
  - Automatic Parquet schema decoding via `pyarrow`.

### 4. Healthcare Hospital Inpatient Operations (`healthcare_hospital_operations.json` / `.jsonl`)
* **Use Case:** Clinical resource allocation, patient stay duration, and nested JSON ingestion.
* **Nested Structure:**
  ```json
  {
    "status": "success",
    "count": 1200,
    "patients": [
      {
        "patient_id": "PT-00001",
        "admission_date": "2024-05-12",
        "length_of_stay_days": 4,
        "total_treatment_cost_usd": 12450.00,
        "vitals": {
          "systolic_bp_mmhg": 134,
          "heart_rate_bpm": 82,
          "body_mass_index": 27.8
        },
        "readmitted_30d_flag": 0
      }
    ]
  }
  ```
* **Testing JSON Ingestion:**
  - Standard JSON upload: specify `root_key="patients"`.
  - Nested vital signs are automatically unpacked into `vitals_systolic_bp_mmhg`, etc.

### 5. Industrial Supply Chain & IoT Telemetry (`supply_chain_iot_telemetry.csv`)
* **Use Case:** Predictive maintenance, equipment vibration analysis, and automated time-series forecasting.
* **Columns:** `telemetry_id`, `timestamp` (hourly frequency), `production_line`, `machine_asset`, `operating_temperature_c`, `vibration_amplitude_mm_s`, `hydraulic_pressure_bar`, `power_consumption_kwh`, `oee_efficiency_pct`, `anomaly_defect_detected`.
* **Analytical Highlights:**
  - Regular hourly interval enables ARIMA / Holt-Winters time-series forecast models.
  - Cyclic machine stress patterns create detectable anomaly spikes.

### 6. Workforce Talent & Equity Analytics (`workforce_talent_analytics.xlsx`)
* **Use Case:** Compensation analysis, promotion velocity, and protected attribute equity.
* **Columns:** `employee_id`, `hire_date`, `department`, `job_role`, `job_level`, `annual_salary_usd`, `monthly_overtime_hours`, `last_performance_rating`, `gender`, `ethnicity`, `attrition_status`.
* **Analytical Highlights:**
  - Verifies that `gender` and `ethnicity` are respected as protected attributes.
  - Tests salary variance decomposition across experience and job level.

### 7. Relational SQLite Enterprise Warehouse (`sqlite_sample/dataforge_warehouse.db`)
* **Use Case:** Testing the DataForge External Database Connector without requiring external cloud databases.
* **Included Tables:**
  - `fact_orders`
  - `dim_customers`
  - `dim_products`
* **Connection String:**
  ```text
  sqlite:////home/fab/DataForge_v3/inputs/sqlite_sample/dataforge_warehouse.db
  ```

---

## 🚀 How to Ingest & Test Each Input Method

### Method A: Web UI File Upload
1. Navigate to `http://localhost:3000/workspace`.
2. Drag and drop any `.csv`, `.xlsx`, `.parquet`, or `.json` file from the `inputs/` folder.
3. For multi-sheet Excel files (`ecommerce_global_retail.xlsx`), DataForge will prompt you to select your target sheet (`Orders`, `Customers`, or `Products`).

### Method B: Ingest via External Database Connector (SQLite)
Test live database connectivity and table ingestion via cURL:
```bash
# 1. Test database connection
curl -X POST http://localhost:5000/api/upload/database/test \
  -H "Content-Type: application/json" \
  -d '{"connection_string": "sqlite:////home/fab/DataForge_v3/inputs/sqlite_sample/dataforge_warehouse.db"}'

# 2. List tables in the database
curl -X POST http://localhost:5000/api/upload/database/tables \
  -H "Content-Type: application/json" \
  -d '{"connection_string": "sqlite:////home/fab/DataForge_v3/inputs/sqlite_sample/dataforge_warehouse.db"}'

# 3. Ingest the 'fact_orders' table
curl -X POST http://localhost:5000/api/upload/database/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "connection_string": "sqlite:////home/fab/DataForge_v3/inputs/sqlite_sample/dataforge_warehouse.db",
    "table_name": "fact_orders"
  }'
```

### Method C: Ingest via REST API / JSON URL
```bash
curl -X POST http://localhost:5000/api/upload/json-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://dummyjson.com/products",
    "root_key": "products",
    "dataset_name": "ecommerce_catalog_feed"
  }'
```
