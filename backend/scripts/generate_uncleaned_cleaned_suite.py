"""
Generate comprehensive Uncleaned vs Cleaned benchmark datasets for DataForge v3.
Outputs to:
  - inputs/uncleaned/
  - inputs/cleaned/
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

BASE_INPUTS = Path("/home/fab/DataForge_v3/inputs")
UNCLEANED_DIR = BASE_INPUTS / "uncleaned"
CLEANED_DIR = BASE_INPUTS / "cleaned"

UNCLEANED_DIR.mkdir(parents=True, exist_ok=True)
CLEANED_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 1. SaaS Subscription Churn Dataset (B2B SaaS)
# ==============================================================================

def generate_saas_churn_pair(n_rows: int = 1500):
    tiers = ["Starter", "Professional", "Growth", "Enterprise"]
    tier_weights = [0.40, 0.35, 0.15, 0.10]
    tier_mrr = {"Starter": 150, "Professional": 650, "Growth": 1800, "Enterprise": 6500}
    industries = ["FinTech", "Healthcare", "E-Commerce", "EdTech", "Logistics", "Cybersecurity"]
    regions = ["North America", "EMEA", "APAC", "LATAM"]
    genders = ["Female", "Male", "Non-Binary"]
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Robin", "Casey", "Riley"]
    domains = ["acmeworks.com", "apexdata.io", "cloudscale.net", "hypertech.org", "novacorp.com"]

    start_date = datetime(2024, 1, 1)
    clean_records = []
    unclean_records = []

    for i in range(1, n_rows + 1):
        tier = random.choices(tiers, weights=tier_weights)[0]
        industry = random.choice(industries)
        region = random.choice(regions)
        gender = random.choice(genders)

        days_offset = random.randint(0, 950)
        sub_date = start_date + timedelta(days=days_offset)

        base_mrr = round(tier_mrr[tier] * np.random.uniform(0.85, 1.30), 2)
        seats = {"Starter": random.randint(1, 5), "Professional": random.randint(6, 25),
                 "Growth": random.randint(26, 80), "Enterprise": random.randint(81, 500)}[tier]

        mau = int(seats * np.random.uniform(0.40, 0.98))
        adoption = round(float(np.clip(np.random.normal(68, 18), 10, 100)), 1)
        nps = int(np.clip(np.random.normal(35, 30), -100, 100))
        tickets = int(np.random.exponential(scale=2.2))

        churn_score = (
            -0.03 * (adoption - 50)
            - 0.015 * nps
            + 0.15 * tickets
            + (0.4 if tier == "Starter" else -0.3 if tier == "Enterprise" else 0)
        )
        churn_prob = 1 / (1 + np.exp(-churn_score))
        churned = 1 if np.random.rand() < churn_prob else 0

        # Clean record
        clean_records.append({
            "account_id": f"ACC-{10000 + i}",
            "signup_date": sub_date.strftime("%Y-%m-%d"),
            "plan_tier": tier,
            "industry": industry,
            "region": region,
            "seats_allocated": seats,
            "monthly_active_users": mau,
            "feature_adoption_pct": adoption,
            "support_tickets_30d": tickets,
            "nps_score": nps,
            "mrr_usd": base_mrr,
            "contract_type": "Annual" if tier in ["Growth", "Enterprise"] and random.random() > 0.3 else "Monthly",
            "account_exec_gender": gender,
            "churn_risk_flag": churned,
        })

        # Inject realistic flaws into uncleaned record
        u_tier = tier
        if random.random() < 0.25:
            # Dirty casing and trailing spaces
            choice = random.choice(["upper", "lower", "spaces", "short"])
            if choice == "upper":
                u_tier = tier.upper()
            elif choice == "lower":
                u_tier = tier.lower()
            elif choice == "spaces":
                u_tier = f"  {tier}  "
            elif choice == "short" and tier == "Professional":
                u_tier = "Pro "

        # Nulls
        u_mau = mau if random.random() > 0.12 else None
        u_adoption = adoption if random.random() > 0.10 else None
        u_nps = nps if random.random() > 0.15 else None
        u_tickets = tickets if random.random() > 0.08 else None

        # Outliers
        u_mrr = base_mrr
        if random.random() < 0.02:
            u_mrr = random.choice([-50.00, 999999.00, 0.00])
        if random.random() < 0.015:
            u_tickets = random.choice([85, 120, 250])

        # Dirty date formats
        if random.random() < 0.30:
            u_date = sub_date.strftime("%m/%d/%Y")
        elif random.random() < 0.10:
            u_date = sub_date.strftime("%d-%b-%Y")
        else:
            u_date = sub_date.strftime("%Y-%m-%d")

        # PII fields for anonymization testing
        fname = random.choice(first_names).lower()
        domain = random.choice(domains)
        email = f"{fname}.{i}@{domain}"
        phone = f"+1 ({random.randint(200, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"

        unclean_records.append({
            "account_id": f"ACC-{10000 + i}",
            "customer_email": email,
            "contact_phone": phone,
            "signup_date": u_date,
            "plan_tier": u_tier,
            "industry": industry.lower() if random.random() < 0.15 else industry,
            "region": f" {region} " if random.random() < 0.10 else region,
            "seats_allocated": seats,
            "monthly_active_users": u_mau,
            "feature_adoption_pct": u_adoption,
            "support_tickets_30d": u_tickets,
            "nps_score": u_nps,
            "mrr_usd": u_mrr,
            "contract_type": "Annual" if tier in ["Growth", "Enterprise"] and random.random() > 0.3 else "Monthly",
            "account_exec_gender": gender,
            "churn_risk_flag": churned,
        })

    # Add duplicate rows to uncleaned dataset
    duplicates = random.sample(unclean_records, 40)
    unclean_records.extend(duplicates)

    return pd.DataFrame(clean_records), pd.DataFrame(unclean_records)


# ==============================================================================
# 2. E-Commerce Orders & Multi-Table Relational Suite
# ==============================================================================

def generate_ecommerce_suite(n_orders: int = 2500):
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

    customers = []
    genders = ["Female", "Male", "Non-Binary"]
    segments = ["Direct Consumer", "Small Business", "Corporate Enterprise"]
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

    channels = ["Web Storefront", "Mobile App", "Amazon Store", "B2B Portal"]
    regions = ["North America", "Western Europe", "Asia-Pacific", "Latin America"]
    clean_orders = []
    unclean_orders = []
    start_date = datetime(2024, 1, 1)

    for oid in range(1, n_orders + 1):
        day_offset = random.randint(0, 950)
        order_date = start_date + timedelta(days=day_offset)
        is_q4 = order_date.month in [11, 12]

        cust = random.choice(customers)
        prod = random.choice(products)
        qty = random.randint(1, 4) if not is_q4 else random.randint(1, 8)
        discount = random.choices([0.0, 0.05, 0.10, 0.15, 0.25], weights=[0.50, 0.20, 0.15, 0.10, 0.05])[0]

        gross_rev = round(prod["retail_price_usd"] * qty * (1 - discount), 2)
        cogs = round(prod["unit_cost_usd"] * qty, 2)
        shipping = round(random.uniform(4.5, 18.0) + (qty * 1.2), 2)
        net_profit = round(gross_rev - cogs - shipping, 2)
        status = random.choices(["Delivered", "Returned", "Cancelled"], weights=[0.92, 0.06, 0.02])[0]
        region = random.choice(regions)
        channel = random.choice(channels)

        clean_orders.append({
            "order_id": f"ORD-{oid:05d}",
            "order_date": order_date.strftime("%Y-%m-%d"),
            "customer_id": cust["customer_id"],
            "sku_id": prod["sku_id"],
            "category": prod["category"],
            "region": region,
            "sales_channel": channel,
            "quantity_ordered": qty,
            "discount_applied": discount,
            "gross_revenue_usd": gross_rev,
            "cost_of_goods_usd": cogs,
            "shipping_fee_usd": shipping,
            "net_profit_usd": net_profit,
            "order_status": status,
            "delivery_days": random.randint(1, 7) if status != "Cancelled" else None,
        })

        # Uncleaned order flaws
        u_status = status
        if random.random() < 0.25:
            u_status = random.choice([status.lower(), status.upper(), f" {status} ", f"{status}."])

        # Currency formatting strings vs raw floats
        u_rev = gross_rev
        if random.random() < 0.20:
            u_rev = f"${gross_rev:,.2f}"
        elif random.random() < 0.05:
            u_rev = f"USD {gross_rev}"

        u_shipping = shipping if random.random() > 0.12 else None
        u_discount = discount if random.random() > 0.10 else None
        u_cogs = cogs if random.random() > 0.05 else None

        # Date flaws
        if random.random() < 0.25:
            u_date = order_date.strftime("%m/%d/%Y")
        elif random.random() < 0.10:
            u_date = order_date.strftime("%d-%m-%Y")
        else:
            u_date = order_date.strftime("%Y-%m-%d")

        unclean_orders.append({
            "order_id": f"ORD-{oid:05d}",
            "order_date": u_date,
            "customer_id": cust["customer_id"] if random.random() > 0.04 else None,
            "sku_id": prod["sku_id"],
            "category": f" {prod['category']} " if random.random() < 0.15 else prod["category"],
            "region": region,
            "sales_channel": channel,
            "quantity_ordered": qty if random.random() > 0.02 else -1,
            "discount_applied": u_discount,
            "gross_revenue_usd": u_rev,
            "cost_of_goods_usd": u_cogs,
            "shipping_fee_usd": u_shipping,
            "net_profit_usd": net_profit,
            "order_status": u_status,
        })

    # Duplicates in uncleaned
    unclean_orders.extend(random.sample(unclean_orders, 50))

    return (
        pd.DataFrame(clean_orders),
        pd.DataFrame(unclean_orders),
        df_customers,
        df_products
    )


# ==============================================================================
# 3. FinTech Consumer Credit Risk
# ==============================================================================

def generate_credit_risk_pair(n_rows: int = 2000):
    purposes = ["debt_consolidation", "credit_card_refinancing", "home_improvement", "small_business", "major_purchase"]
    ownership = ["RENT", "MORTGAGE", "OWN"]
    start_date = datetime(2024, 1, 1)
    clean_records = []
    unclean_records = []

    for i in range(1, n_rows + 1):
        app_date = start_date + timedelta(days=random.randint(0, 950))
        age = random.randint(21, 68)
        years_emp = round(min(max(0.0, np.random.exponential(scale=5.0)), age - 18), 1)
        income = round(float(np.random.lognormal(mean=10.9, sigma=0.55)), 2)
        loan_amt = round(random.uniform(2000, 45000), 2)
        dti = round(random.uniform(5.0, 45.0), 2)
        fico = int(np.clip(np.random.normal(690, 65), 540, 850))

        int_rate = round(float(np.clip(28.0 - (fico - 550) * 0.065 + (dti * 0.12), 4.5, 29.9)), 2)
        delinquent_24m = random.choices([0, 1, 2, 3], weights=[0.82, 0.11, 0.05, 0.02])[0]

        risk_score = (
            -0.025 * (fico - 650)
            + 0.05 * (dti - 20)
            + 1.5 * (loan_amt / max(income, 10000))
            + 0.8 * delinquent_24m
        )
        prob_default = 1 / (1 + np.exp(-risk_score))
        default_flag = 1 if np.random.rand() < prob_default else 0

        clean_records.append({
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
            "default_risk_flag": default_flag,
        })

        # Flaws
        u_fico = fico if random.random() > 0.14 else None
        u_income = income
        if random.random() < 0.02:
            u_income = random.choice([-2500.0, 99999999.0, 0.0])

        u_dti = dti
        if random.random() < 0.20:
            u_dti = f"{dti}%"
        elif random.random() < 0.10:
            u_dti = round(dti / 100, 3)

        u_purpose = random.choice(purposes)
        if random.random() < 0.20:
            u_purpose = u_purpose.upper() if random.random() > 0.5 else f" {u_purpose} "

        ssn_last4 = f"***-**-{random.randint(1000, 9999)}"

        unclean_records.append({
            "loan_application_id": f"LN-{i:06d}",
            "applicant_ssn_last4": ssn_last4,
            "application_date": app_date.strftime("%Y-%m-%d"),
            "applicant_age": age if random.random() > 0.02 else -5,
            "years_employed": years_emp if random.random() > 0.10 else None,
            "annual_income_usd": u_income,
            "home_ownership": random.choices(ownership, weights=[0.48, 0.42, 0.10])[0],
            "loan_purpose": u_purpose,
            "loan_amount_usd": loan_amt,
            "interest_rate_pct": int_rate,
            "debt_to_income_ratio": u_dti,
            "credit_score_fico": u_fico,
            "delinquencies_past_24m": delinquent_24m,
            "default_risk_flag": default_flag,
        })

    unclean_records.extend(random.sample(unclean_records, 40))

    return pd.DataFrame(clean_records), pd.DataFrame(unclean_records)


# ==============================================================================
# 4. Healthcare Operations (JSON)
# ==============================================================================

def generate_healthcare_pair(n_rows: int = 1200):
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
    clean_patients = []
    unclean_patients = []

    for i in range(1, n_rows + 1):
        diag = random.choice(diagnoses)
        adm_date = start_date + timedelta(days=random.randint(0, 950))
        age = random.randint(18, 92)
        gender = random.choice(genders)
        adm_type = random.choices(admission_types, weights=[0.60, 0.25, 0.15])[0]
        ins = random.choices(insurances, weights=[0.45 if age >= 65 else 0.10, 0.18, 0.35, 0.25, 0.07])[0]

        los = max(1, int(np.random.normal(diag["base_los"] + (age * 0.02), 1.8)))
        disch_date = adm_date + timedelta(days=los)
        total_cost = round(diag["base_cost"] * (los / diag["base_los"]) * np.random.uniform(0.85, 1.25), 2)
        systolic_bp = int(np.random.normal(132, 18))
        heart_rate = int(np.random.normal(78, 12))
        bmi = round(float(np.random.normal(28.4, 5.2)), 1)

        readmit_score = -2.5 + (0.02 * (age - 50)) + (0.12 * los) + (0.4 if diag["name"] == "Heart Failure" else 0)
        readmit_prob = 1 / (1 + np.exp(-readmit_score))
        readmitted = 1 if np.random.rand() < readmit_prob else 0

        clean_patients.append({
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

        # Flawed patient
        u_vitals = {
            "systolic_bp_mmhg": systolic_bp if random.random() > 0.12 else None,
            "heart_rate_bpm": heart_rate if random.random() > 0.10 else None,
            "body_mass_index": bmi if random.random() > 0.08 else None,
        }

        unclean_patients.append({
            "patient_id": f"PT-{i:05d}",
            "mrn_hash": f"MRN-{random.randint(100000, 999999)}",
            "admission_date": adm_date.strftime("%m/%d/%Y") if random.random() < 0.25 else adm_date.strftime("%Y-%m-%d"),
            "primary_diagnosis_code": diag["code"],
            "diagnosis_name": f" {diag['name']} " if random.random() < 0.15 else diag["name"],
            "admission_type": adm_type.upper() if random.random() < 0.15 else adm_type,
            "patient_age": age,
            "gender": gender,
            "insurance_provider": ins,
            "length_of_stay_days": los,
            "total_treatment_cost_usd": total_cost if random.random() > 0.08 else None,
            "vitals": u_vitals,
            "readmitted_30d_flag": readmitted,
        })

    return clean_patients, unclean_patients


# ==============================================================================
# 5. Workforce Talent Analytics (XLSX)
# ==============================================================================

def generate_workforce_pair(n_rows: int = 900):
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
    clean_records = []
    unclean_records = []

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

        dept_mult = 1.25 if dept == "Engineering" else 1.15 if dept == "Product" else 1.0
        salary = round(base_salaries[level] * dept_mult * (1 + 0.035 * years_exp) * np.random.uniform(0.92, 1.08), 2)

        attr_score = (
            -0.25 * (salary / 100000)
            + 0.035 * overtime_hrs
            - 0.15 * performance
            - 0.20 * years_exp
            + (0.4 if level == "Junior" else -0.3 if level == "Director" else 0)
        )
        prob_attr = 1 / (1 + np.exp(-attr_score))
        attrition = "Left" if np.random.rand() < prob_attr else "Current Employee"

        clean_records.append({
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
            "gender": gender,
            "ethnicity": ethnicity,
            "attrition_status": attrition,
        })

        # Flawed workforce records
        u_dept = dept
        if random.random() < 0.25:
            if dept == "Engineering":
                u_dept = random.choice(["eng", "ENGINEERING", " Engineering "])
            elif dept == "People Operations":
                u_dept = random.choice(["HR", "people ops", "PEOPLE OPERATIONS"])
            else:
                u_dept = dept.lower()

        u_salary = salary if random.random() > 0.12 else None
        u_perf = performance if random.random() > 0.08 else None

        unclean_records.append({
            "employee_id": f"EMP-{i:04d}",
            "work_email": f"emp{i}@enterprise.corp",
            "hire_date": hire_date.strftime("%m/%d/%Y") if random.random() < 0.3 else hire_date.strftime("%Y-%m-%d"),
            "department": u_dept,
            "job_role": role,
            "job_level": level,
            "years_at_company": years_exp,
            "annual_salary_usd": u_salary,
            "monthly_overtime_hours": overtime_hrs,
            "last_performance_rating": u_perf,
            "gender": gender,
            "ethnicity": ethnicity,
            "attrition_status": attrition,
        })

    unclean_records.extend(random.sample(unclean_records, 25))

    return pd.DataFrame(clean_records), pd.DataFrame(unclean_records)


# ==============================================================================
# Execution & File Serialization
# ==============================================================================

def main():
    print("🚀 Recreating Benchmark Input Suites: inputs/uncleaned/ & inputs/cleaned/ ...\n")

    # 1. SaaS Churn
    print("[1/5] Generating SaaS Subscription & Churn (CSV)...")
    clean_saas, unclean_saas = generate_saas_churn_pair(1500)
    clean_saas.to_csv(CLEANED_DIR / "saas_churn_cleaned.csv", index=False)
    unclean_saas.to_csv(UNCLEANED_DIR / "saas_churn_uncleaned.csv", index=False)
    # Also update baseline in root inputs/
    clean_saas.to_csv(BASE_INPUTS / "saas_subscription_churn.csv", index=False)
    print(f"  ✓ Cleaned: {len(clean_saas)} rows -> {CLEANED_DIR / 'saas_churn_cleaned.csv'}")
    print(f"  ✓ Uncleaned: {len(unclean_saas)} rows -> {UNCLEANED_DIR / 'saas_churn_uncleaned.csv'}")

    # 2. E-Commerce Retail
    print("[2/5] Generating E-Commerce Orders & Relational Tables (CSV + XLSX)...")
    clean_orders, unclean_orders, df_custs, df_prods = generate_ecommerce_suite(2500)
    clean_orders.to_csv(CLEANED_DIR / "ecommerce_orders_cleaned.csv", index=False)
    unclean_orders.to_csv(UNCLEANED_DIR / "ecommerce_orders_uncleaned.csv", index=False)
    df_custs.to_csv(CLEANED_DIR / "ecommerce_customers_cleaned.csv", index=False)
    df_prods.to_csv(CLEANED_DIR / "ecommerce_products_cleaned.csv", index=False)

    # Multi-sheet Excel workbook in root
    with pd.ExcelWriter(BASE_INPUTS / "ecommerce_global_retail.xlsx", engine="openpyxl") as writer:
        clean_orders.to_excel(writer, sheet_name="Orders", index=False)
        df_custs.to_excel(writer, sheet_name="Customers", index=False)
        df_prods.to_excel(writer, sheet_name="Products", index=False)
    print(f"  ✓ Cleaned: {len(clean_orders)} rows -> {CLEANED_DIR / 'ecommerce_orders_cleaned.csv'}")
    print(f"  ✓ Relational Customers: {len(df_custs)} rows -> {CLEANED_DIR / 'ecommerce_customers_cleaned.csv'}")
    print(f"  ✓ Relational Products: {len(df_prods)} rows -> {CLEANED_DIR / 'ecommerce_products_cleaned.csv'}")
    print(f"  ✓ Uncleaned: {len(unclean_orders)} rows -> {UNCLEANED_DIR / 'ecommerce_orders_uncleaned.csv'}")

    # 3. FinTech Credit Risk
    print("[3/5] Generating FinTech Consumer Credit Risk (CSV + Parquet)...")
    clean_credit, unclean_credit = generate_credit_risk_pair(2000)
    clean_credit.to_csv(CLEANED_DIR / "credit_risk_cleaned.csv", index=False)
    clean_credit.to_parquet(CLEANED_DIR / "credit_risk_cleaned.parquet", index=False, engine="pyarrow")
    unclean_credit.to_csv(UNCLEANED_DIR / "credit_risk_uncleaned.csv", index=False)
    # Root baselines
    clean_credit.to_csv(BASE_INPUTS / "fintech_credit_risk.csv", index=False)
    clean_credit.to_parquet(BASE_INPUTS / "fintech_credit_risk.parquet", index=False, engine="pyarrow")
    print(f"  ✓ Cleaned: {len(clean_credit)} rows -> {CLEANED_DIR / 'credit_risk_cleaned.csv'} (.parquet)")
    print(f"  ✓ Uncleaned: {len(unclean_credit)} rows -> {UNCLEANED_DIR / 'credit_risk_uncleaned.csv'}")

    # 4. Healthcare Operations
    print("[4/5] Generating Healthcare Inpatient Admissions (JSON)...")
    clean_hc, unclean_hc = generate_healthcare_pair(1200)
    with open(CLEANED_DIR / "healthcare_operations_cleaned.json", "w", encoding="utf-8") as f:
        json.dump({"status": "success", "count": len(clean_hc), "patients": clean_hc}, f, indent=2)
    with open(UNCLEANED_DIR / "healthcare_operations_uncleaned.json", "w", encoding="utf-8") as f:
        json.dump({"status": "raw", "count": len(unclean_hc), "patients": unclean_hc}, f, indent=2)
    print(f"  ✓ Cleaned: {len(clean_hc)} records -> {CLEANED_DIR / 'healthcare_operations_cleaned.json'}")
    print(f"  ✓ Uncleaned: {len(unclean_hc)} records -> {UNCLEANED_DIR / 'healthcare_operations_uncleaned.json'}")

    # 5. Workforce Talent Analytics
    print("[5/5] Generating Workforce Talent Analytics (XLSX)...")
    clean_workforce, unclean_workforce = generate_workforce_pair(900)
    with pd.ExcelWriter(CLEANED_DIR / "workforce_talent_cleaned.xlsx", engine="openpyxl") as writer:
        clean_workforce.to_excel(writer, sheet_name="Census", index=False)
    with pd.ExcelWriter(UNCLEANED_DIR / "workforce_talent_uncleaned.xlsx", engine="openpyxl") as writer:
        unclean_workforce.to_excel(writer, sheet_name="Census_Raw", index=False)
    print(f"  ✓ Cleaned: {len(clean_workforce)} rows -> {CLEANED_DIR / 'workforce_talent_cleaned.xlsx'}")
    print(f"  ✓ Uncleaned: {len(unclean_workforce)} rows -> {UNCLEANED_DIR / 'workforce_talent_uncleaned.xlsx'}")

    print("\n✅ Successfully recreated all benchmark inputs across inputs/uncleaned/ and inputs/cleaned/!")


if __name__ == "__main__":
    main()
