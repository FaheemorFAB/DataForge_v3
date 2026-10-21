"""
Generate high-fidelity sample datasets showcasing the full analytical and ingestion
capabilities of DataForge v3 across diverse industries and input formats.
"""

from __future__ import annotations

import json
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = Path("/home/fab/DataForge_v3/inputs")
SQLITE_DIR = OUTPUT_DIR / "sqlite_sample"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_DIR.mkdir(parents=True, exist_ok=True)


def generate_saas_churn(n_rows: int = 1500) -> pd.DataFrame:
    """B2B SaaS customer success and subscription analytics."""
    tiers = ["Starter", "Professional", "Growth", "Enterprise"]
    tier_weights = [0.40, 0.35, 0.15, 0.10]
    tier_mrr = {"Starter": 150, "Professional": 650, "Growth": 1800, "Enterprise": 6500}
    industries = ["FinTech", "Healthcare", "E-Commerce", "EdTech", "Logistics", "Cybersecurity"]
    regions = ["North America", "EMEA", "APAC", "LATAM"]
    genders = ["Female", "Male", "Non-Binary"]

    start_date = datetime(2024, 1, 1)
    records = []

    for i in range(1, n_rows + 1):
        tier = random.choices(tiers, weights=tier_weights)[0]
        industry = random.choice(industries)
        region = random.choice(regions)
        gender = random.choice(genders)

        # Date of subscription
        days_offset = random.randint(0, 950)
        sub_date = start_date + timedelta(days=days_offset)

        # Base usage metrics
        base_mrr = tier_mrr[tier] * np.random.uniform(0.85, 1.30)
        seats = {"Starter": random.randint(1, 5), "Professional": random.randint(6, 25),
                 "Growth": random.randint(26, 80), "Enterprise": random.randint(81, 500)}[tier]

        # Activity & satisfaction drivers
        mau = int(seats * np.random.uniform(0.40, 0.98))
        feature_adoption = np.clip(np.random.normal(68, 18), 10, 100)
        nps = int(np.clip(np.random.normal(35, 30), -100, 100))
        tickets = int(np.random.exponential(scale=2.2))

        # Churn probability is driven by low adoption, low NPS, high tickets, small seats
        churn_score = (
            -0.03 * (feature_adoption - 50)
            - 0.015 * nps
            + 0.15 * tickets
            + (0.4 if tier == "Starter" else -0.3 if tier == "Enterprise" else 0)
        )
        churn_prob = 1 / (1 + np.exp(-churn_score))
        churned = 1 if np.random.rand() < churn_prob else 0

        # Small percentage of missing values to showcase Data Cleaning & Imputation
        nps_val = nps if random.random() > 0.04 else None
        adoption_val = round(feature_adoption, 1) if random.random() > 0.03 else None

        records.append({
            "account_id": f"ACC-{10000 + i}",
            "signup_date": sub_date.strftime("%Y-%m-%d"),
            "plan_tier": tier,
            "industry": industry,
            "region": region,
            "seats_allocated": seats,
            "monthly_active_users": mau,
            "feature_adoption_pct": adoption_val,
            "support_tickets_30d": tickets,
            "nps_score": nps_val,
            "mrr_usd": round(base_mrr, 2),
            "contract_type": "Annual" if tier in ["Growth", "Enterprise"] and random.random() > 0.3 else "Monthly",
            "account_exec_gender": gender,  # Protected attribute (should be isolated from drivers)
            "churn_risk_flag": churned,      # Binary AutoML classification target
        })

    return pd.DataFrame(records)


def generate_ecommerce_retail(n_rows: int = 2200):
    """Multi-table e-commerce retail dataset with Orders, Customers, and Products."""
    # 1. Product Catalog
    categories = {
        "Electronics": ["Smartphone", "Wireless Earbuds", "Gaming Monitor", "Mechanical Keyboard", "USB-C Dock"],
        "Home & Kitchen": ["Air Fryer", "Espresso Machine", "Robot Vacuum", "Ergonomic Desk", "Chef Knife Set"],
        "Apparel": ["Merino Wool Sweater", "Waterproof Jacket", "Running Shoes", "Denim Jeans", "Yoga Leggings"],
        "Office Supplies": ["Standing Mat", "Noise Canceling Headset", "Desk Lamp", "Laser Printer", "Paper Shredder"]
    }

    products = []
    sku_idx = 100
    for cat, subcats in categories.items():
        for subcat in subcats:
            sku_idx += 1
            cost = round(random.uniform(15, 350), 2)
            margin = random.uniform(0.25, 0.65)
            price = round(cost / (1 - margin), 2)
            products.append({
                "sku_id": f"SKU-{sku_idx}",
                "product_name": subcat,
                "category": cat,
                "unit_cost_usd": cost,
                "retail_price_usd": price,
                "target_margin_pct": round(margin * 100, 1),
                "in_stock_units": random.randint(20, 1500)
            })
    df_products = pd.DataFrame(products)

    # 2. Customers
    genders = ["Female", "Male", "Non-Binary"]
    segments = ["Direct Consumer", "Small Business", "Corporate Enterprise"]
    customers = []
    for cid in range(1, 550):
        customers.append({
            "customer_id": f"CUST-{cid:04d}",
            "join_date": (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 700))).strftime("%Y-%m-%d"),
            "customer_segment": random.choices(segments, weights=[0.65, 0.25, 0.10])[0],
            "age_bracket": random.choice(["18-25", "26-35", "36-50", "51-65", "65+"]),
            "gender": random.choice(genders),
            "loyalty_tier": random.choices(["Bronze", "Silver", "Gold", "Platinum"], weights=[0.5, 0.3, 0.15, 0.05])[0],
            "acquisition_channel": random.choice(["Organic Search", "Paid Social", "Email Newsletter", "Referral", "Affiliate"])
        })
    df_customers = pd.DataFrame(customers)

    # 3. Orders
    channels = ["Web Storefront", "Mobile App", "Amazon Store", "B2B Portal"]
    regions = ["North America", "Western Europe", "Asia-Pacific", "Latin America"]
    order_records = []
    start_date = datetime(2024, 1, 1)

    for oid in range(1, n_rows + 1):
        # Time distribution with seasonal peak around holiday season (Nov/Dec)
        day_offset = random.randint(0, 950)
        order_date = start_date + timedelta(days=day_offset)
        # Seasonal multiplier for Q4
        is_q4 = order_date.month in [11, 12]

        cust = random.choice(customers)
        prod = random.choice(products)
        qty = random.randint(1, 4) if not is_q4 else random.randint(1, 8)
        discount = random.choices([0.0, 0.05, 0.10, 0.15, 0.25], weights=[0.50, 0.20, 0.15, 0.10, 0.05])[0]

        gross_rev = round(prod["retail_price_usd"] * qty * (1 - discount), 2)
        cogs = round(prod["unit_cost_usd"] * qty, 2)
        shipping = round(random.uniform(4.5, 18.0) + (qty * 1.2), 2)
        net_profit = round(gross_rev - cogs - shipping, 2)

        order_status = random.choices(["Delivered", "Returned", "Cancelled"], weights=[0.92, 0.06, 0.02])[0]

        order_records.append({
            "order_id": f"ORD-{oid:05d}",
            "order_date": order_date.strftime("%Y-%m-%d"),
            "customer_id": cust["customer_id"],
            "sku_id": prod["sku_id"],
            "category": prod["category"],
            "region": random.choice(regions),
            "sales_channel": random.choice(channels),
            "quantity_ordered": qty,
            "discount_applied": discount,
            "gross_revenue_usd": gross_rev,
            "cost_of_goods_usd": cogs,
            "shipping_fee_usd": shipping,
            "net_profit_usd": net_profit,
            "order_status": order_status,
            "delivery_days": random.randint(1, 7) if order_status != "Cancelled" else None,
        })
    df_orders = pd.DataFrame(order_records)

    return df_orders, df_customers, df_products


def generate_fintech_credit_risk(n_rows: int = 1800) -> pd.DataFrame:
    """FinTech consumer lending and loan default risk."""
    purposes = ["debt_consolidation", "credit_card_refinancing", "home_improvement", "small_business", "major_purchase"]
    ownership = ["RENT", "MORTGAGE", "OWN"]
    start_date = datetime(2024, 1, 1)
    records = []

    for i in range(1, n_rows + 1):
        app_date = start_date + timedelta(days=random.randint(0, 950))
        age = random.randint(21, 68)
        years_emp = round(min(max(0.0, np.random.exponential(scale=5.0)), age - 18), 1)
        income = round(np.random.lognormal(mean=10.9, sigma=0.55), 2)  # ~$55,000 median
        loan_amt = round(random.uniform(2000, 45000), 2)
        dti = round(random.uniform(5.0, 45.0), 2)

        # FICO credit score
        fico = int(np.clip(np.random.normal(690, 65), 540, 850))

        # Interest rate correlates inversely with FICO and positively with DTI
        int_rate = round(np.clip(28.0 - (fico - 550) * 0.065 + (dti * 0.12), 4.5, 29.9), 2)
        delinquent_24m = random.choices([0, 1, 2, 3], weights=[0.82, 0.11, 0.05, 0.02])[0]

        # Default probability driven by low FICO, high DTI, high loan to income ratio, delinquencies
        risk_score = (
            -0.025 * (fico - 650)
            + 0.05 * (dti - 20)
            + 1.5 * (loan_amt / max(income, 10000))
            + 0.8 * delinquent_24m
        )
        prob_default = 1 / (1 + np.exp(-risk_score))
        default_flag = 1 if np.random.rand() < prob_default else 0

        records.append({
            "loan_application_id": f"LN-{i:06d}",
            "application_date": app_date.strftime("%Y-%m-%d"),
            "applicant_age": age,
            "years_employed": years_emp,
            "annual_income_usd": income,
            "home_ownership": random.choices(ownership, weights=[0.48, 0.42, 0.10])[0],
            "loan_purpose": random.choice(purposes),
            "loan_amount_usd": loan_amt,
            "interest_rate_pct": int_rate,
            "debt_to_income_ratio": dti,
            "credit_score_fico": fico,
            "delinquencies_past_24m": delinquent_24m,
            "monthly_debt_obligations": round((income / 12) * (dti / 100), 2),
            "default_risk_flag": default_flag,  # Classification target
        })

    return pd.DataFrame(records)


def generate_healthcare_operations(n_rows: int = 1200) -> list[dict]:
    """Healthcare hospital inpatient admissions and readmission telemetry."""
    diagnoses = [
        {"code": "I50.9", "name": "Heart Failure", "base_los": 5.2, "base_cost": 14500},
        {"code": "J18.9", "name": "Pneumonia", "base_los": 4.1, "base_cost": 9800},
        {"code": "E11.9", "name": "Type 2 Diabetes", "base_los": 3.4, "base_cost": 7200},
        {"code": "S72.0", "name": "Femur Fracture", "base_los": 6.8, "base_cost": 22000},
        {"code": "K52.9", "name": "Gastroenteritis", "base_los": 2.5, "base_cost": 4900},
        {"code": "N39.0", "name": "Urinary Tract Infection", "base_los": 2.9, "base_cost": 5400},
    ]
    insurances = ["Medicare", "Medicaid", "Commercial PPO", "HMO Managed", "Self-Pay"]
    admission_types = ["Emergency", "Urgent", "Elective Referral"]
    genders = ["Female", "Male"]

    start_date = datetime(2024, 1, 1)
    patients = []

    for i in range(1, n_rows + 1):
        diag = random.choice(diagnoses)
        adm_date = start_date + timedelta(days=random.randint(0, 950))
        age = random.randint(18, 92)
        gender = random.choice(genders)
        adm_type = random.choices(admission_types, weights=[0.60, 0.25, 0.15])[0]
        ins = random.choices(insurances, weights=[0.45 if age >= 65 else 0.10, 0.18, 0.35, 0.25, 0.07])[0]

        # Length of stay in days
        los = max(1, int(np.random.normal(diag["base_los"] + (age * 0.02), 1.8)))
        disch_date = adm_date + timedelta(days=los)

        # Total billed cost
        total_cost = round(diag["base_cost"] * (los / diag["base_los"]) * np.random.uniform(0.85, 1.25), 2)
        systolic_bp = int(np.random.normal(132, 18))
        heart_rate = int(np.random.normal(78, 12))
        bmi = round(np.random.normal(28.4, 5.2), 1)

        # 30-day readmission risk
        readmit_score = -2.5 + (0.02 * (age - 50)) + (0.12 * los) + (0.4 if diag["name"] == "Heart Failure" else 0)
        readmit_prob = 1 / (1 + np.exp(-readmit_score))
        readmitted = 1 if np.random.rand() < readmit_prob else 0

        patients.append({
            "patient_id": f"PT-{i:05d}",
            "admission_date": adm_date.strftime("%Y-%m-%d"),
            "discharge_date": disch_date.strftime("%Y-%m-%d"),
            "primary_diagnosis_code": diag["code"],
            "diagnosis_name": diag["name"],
            "admission_type": adm_type,
            "patient_age": age,
            "gender": gender,
            "insurance_provider": ins,
            "length_of_stay_days": los,
            "total_treatment_cost_usd": total_cost,
            "vitals": {
                "systolic_bp_mmhg": systolic_bp,
                "heart_rate_bpm": heart_rate,
                "body_mass_index": bmi
            },
            "readmitted_30d_flag": readmitted,
        })

    return patients


def generate_supply_chain_iot(n_rows: int = 2500) -> pd.DataFrame:
    """Industrial IoT sensor telemetry and machine predictive maintenance."""
    lines = ["Line-A Alpha", "Line-B Beta", "Line-C Gamma"]
    machines = ["CNC Milling Unit", "Hydraulic Stamping Press", "Automated Injection Molder", "Robotic Welding Cell"]

    start_time = datetime(2025, 1, 1, 0, 0, 0)
    records = []

    for i in range(1, n_rows + 1):
        timestamp = start_time + timedelta(hours=i)
        line = random.choice(lines)
        machine = random.choice(machines)

        # Operating physics parameters
        base_temp = 65.0
        vibe_base = 1.2
        rpm_base = 3200

        # Degradation event every ~400 readings simulating machine wear
        is_stressed = (i % 380) > 340
        temp = round(np.random.normal(base_temp + (25.0 if is_stressed else 0.0), 4.2), 1)
        vibration = round(np.clip(np.random.normal(vibe_base + (2.8 if is_stressed else 0.0), 0.4), 0.2, 10.0), 3)
        pressure = round(np.random.normal(120.0 - (18.0 if is_stressed else 0.0), 6.5), 1)
        rpm = int(np.random.normal(rpm_base, 80))
        power_kwh = round(temp * 0.42 + vibration * 3.5 + np.random.uniform(5, 12), 2)

        # Defect flag
        defect = 1 if (temp > 85.0 or vibration > 3.2 or random.random() < 0.02) else 0
        oee_efficiency = round(np.clip(100.0 - (vibration * 6.5) - (defect * 22.0) - np.random.uniform(0, 5), 45.0, 99.5), 1)

        records.append({
            "telemetry_id": f"IOT-{i:06d}",
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "production_line": line,
            "machine_asset": machine,
            "operating_temperature_c": temp,
            "vibration_amplitude_mm_s": vibration,
            "hydraulic_pressure_bar": pressure,
            "motor_speed_rpm": rpm,
            "power_consumption_kwh": power_kwh,
            "oee_efficiency_pct": oee_efficiency,
            "anomaly_defect_detected": defect,
        })

    return pd.DataFrame(records)


def generate_workforce_talent(n_rows: int = 850) -> pd.DataFrame:
    """HR talent analytics, compensation equity, and employee retention."""
    departments = ["Engineering", "Product", "Sales", "Marketing", "Finance", "People Operations"]
    roles = {
        "Engineering": ["Software Engineer", "Senior Architect", "QA Automation Engineer", "DevOps Engineer"],
        "Product": ["Product Manager", "UX Designer", "Technical Writer"],
        "Sales": ["Account Executive", "Sales Engineer", "BDR Associate", "Territory Lead"],
        "Marketing": ["Content Strategist", "Growth Marketer", "Brand Designer"],
        "Finance": ["Financial Analyst", "Accountant", "Payroll Specialist"],
        "People Operations": ["HR Business Partner", "Talent Recruiter", "L&D Specialist"]
    }
    levels = ["Junior", "Mid-Level", "Senior", "Lead", "Director"]
    genders = ["Female", "Male", "Non-Binary"]
    ethnicities = ["Asian", "Black", "Hispanic / Latino", "White", "Two or More Races"]

    base_salaries = {
        "Junior": 62000, "Mid-Level": 92000, "Senior": 138000, "Lead": 165000, "Director": 210000
    }

    start_date = datetime(2018, 1, 1)
    records = []

    for i in range(1, n_rows + 1):
        dept = random.choice(departments)
        role = random.choice(roles[dept])
        level = random.choices(levels, weights=[0.25, 0.35, 0.25, 0.10, 0.05])[0]
        hire_date = start_date + timedelta(days=random.randint(0, 2400))
        gender = random.choice(genders)
        ethnicity = random.choice(ethnicities)

        years_exp = round((datetime(2026, 10, 1) - hire_date).days / 365.25, 1)
        performance = random.choices([1, 2, 3, 4, 5], weights=[0.05, 0.15, 0.50, 0.22, 0.08])[0]
        overtime_hrs = int(np.clip(np.random.exponential(scale=12), 0, 80))

        # Salary calculation
        dept_mult = 1.25 if dept == "Engineering" else 1.15 if dept == "Product" else 1.0
        salary = round(base_salaries[level] * dept_mult * (1 + 0.035 * years_exp) * np.random.uniform(0.92, 1.08), 2)

        # Attrition probability
        attr_score = (
            -0.25 * (salary / 100000)
            + 0.035 * overtime_hrs
            - 0.15 * performance
            - 0.20 * years_exp
            + (0.4 if level == "Junior" else -0.3 if level == "Director" else 0)
        )
        prob_attr = 1 / (1 + np.exp(-attr_score))
        attrition = "Left" if np.random.rand() < prob_attr else "Current Employee"

        records.append({
            "employee_id": f"EMP-{i:04d}",
            "hire_date": hire_date.strftime("%Y-%m-%d"),
            "department": dept,
            "job_role": role,
            "job_level": level,
            "years_at_company": years_exp,
            "annual_salary_usd": salary,
            "monthly_overtime_hours": overtime_hrs,
            "last_performance_rating": performance,
            "training_hours_ytd": random.randint(4, 90),
            "promotion_in_last_3y": 1 if years_exp > 2.0 and random.random() > 0.55 else 0,
            "gender": gender,          # Protected attribute
            "ethnicity": ethnicity,    # Protected attribute
            "attrition_status": attrition,
        })

    return pd.DataFrame(records)


def main():
    print("[1/7] Generating SaaS Subscription & Churn dataset (CSV)...")
    df_saas = generate_saas_churn(1500)
    saas_path = OUTPUT_DIR / "saas_subscription_churn.csv"
    df_saas.to_csv(saas_path, index=False)
    print(f"  ✓ Saved {len(df_saas)} rows to {saas_path}")

    print("[2/7] Generating E-Commerce Global Retail multi-sheet workbook (XLSX)...")
    df_orders, df_custs, df_prods = generate_ecommerce_retail(2500)
    excel_path = OUTPUT_DIR / "ecommerce_global_retail.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_orders.to_excel(writer, sheet_name="Orders", index=False)
        df_custs.to_excel(writer, sheet_name="Customers", index=False)
        df_prods.to_excel(writer, sheet_name="Products", index=False)
    print(f"  ✓ Saved 3 sheets (Orders={len(df_orders)}, Customers={len(df_custs)}, Products={len(df_prods)}) to {excel_path}")

    print("[3/7] Generating FinTech Credit Risk datasets (Parquet + CSV)...")
    df_fintech = generate_fintech_credit_risk(2000)
    parquet_path = OUTPUT_DIR / "fintech_credit_risk.parquet"
    df_fintech.to_parquet(parquet_path, index=False, engine="pyarrow")
    csv_fintech_path = OUTPUT_DIR / "fintech_credit_risk.csv"
    df_fintech.to_csv(csv_fintech_path, index=False)
    print(f"  ✓ Saved {len(df_fintech)} rows to {parquet_path} and {csv_fintech_path}")

    print("[4/7] Generating Healthcare Hospital Operations (JSON + JSONL)...")
    healthcare_data = generate_healthcare_operations(1200)
    json_path = OUTPUT_DIR / "healthcare_hospital_operations.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"status": "success", "count": len(healthcare_data), "patients": healthcare_data}, f, indent=2)

    jsonl_path = OUTPUT_DIR / "healthcare_stream.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for p in healthcare_data:
            f.write(json.dumps(p) + "\n")
    print(f"  ✓ Saved {len(healthcare_data)} records to {json_path} (root_key='patients') and {jsonl_path}")

    print("[5/7] Generating Supply Chain IoT Sensor Telemetry (CSV)...")
    df_iot = generate_supply_chain_iot(2500)
    iot_path = OUTPUT_DIR / "supply_chain_iot_telemetry.csv"
    df_iot.to_csv(iot_path, index=False)
    print(f"  ✓ Saved {len(df_iot)} rows to {iot_path}")

    print("[6/7] Generating Workforce Talent Analytics workbook (XLSX)...")
    df_talent = generate_workforce_talent(900)
    workforce_path = OUTPUT_DIR / "workforce_talent_analytics.xlsx"
    with pd.ExcelWriter(workforce_path, engine="openpyxl") as writer:
        df_talent.to_excel(writer, sheet_name="Workforce_Census", index=False)
    print(f"  ✓ Saved {len(df_talent)} rows to {workforce_path}")

    print("[7/7] Generating Relational SQLite Database for external DB connector...")
    sqlite_db_path = SQLITE_DIR / "dataforge_warehouse.db"
    if sqlite_db_path.exists():
        sqlite_db_path.unlink()
    conn = sqlite3.connect(sqlite_db_path)

    # Populate 3 normalized relational tables
    df_custs.to_sql("dim_customers", conn, if_exists="replace", index=False)
    df_prods.to_sql("dim_products", conn, if_exists="replace", index=False)
    df_orders.to_sql("fact_orders", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
    print(f"  ✓ Created SQLite Database with 3 tables (dim_customers, dim_products, fact_orders) at {sqlite_db_path}")

    print("\nAll datasets generated successfully in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
