"""
High-Resolution Publication-Quality Diagram Generator for DataForge Final Year Project Report.
Generates 5 crisp, professional, beautifully styled architectural and data flow diagrams:
1. Figure 3.1: System Workflow
2. Figure 3.2: DataForge System Architecture
3. Figure 3.3: Context Diagram (Level 0 DFD)
4. Figure 3.4: Detailed Diagram (Level 1 DFD)
5. Figure 3.5: Functional Module Interaction Diagram
"""

import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

OUT_DIR = Path("/home/fab/DataForge/report/generated_figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Common styling palette
C_BG = "#ffffff"
C_TEXT = "#0f172a"
C_TEXT_MUTED = "#475569"
C_LINE = "#334155"

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]


def draw_card(ax, x, y, w, h, title, subtitle="", bg="#ffffff", border=C_LINE, radius=0.03, lw=1.5, title_color=C_TEXT, title_size=11, sub_size=8.5, sub_color=C_TEXT_MUTED, align="center"):
    """Draw a rounded container card with centered, left, or top-left aligned text."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=bg,
        edgecolor=border,
        linewidth=lw,
        zorder=2
    )
    ax.add_patch(box)
    
    cx = x + w / 2
    if align == "center":
        if subtitle:
            ax.text(cx, y + h * 0.63, title, ha="center", va="center", fontsize=title_size, fontweight="bold", color=title_color, zorder=3)
            ax.text(cx, y + h * 0.32, subtitle, ha="center", va="center", fontsize=sub_size, color=sub_color, zorder=3)
        else:
            ax.text(cx, y + h * 0.5, title, ha="center", va="center", fontsize=title_size, fontweight="bold", color=title_color, zorder=3)
    elif align == "top-left":
        tx = x + 0.02
        ax.text(tx, y + h - 0.025, title, ha="left", va="center", fontsize=title_size, fontweight="bold", color=title_color, zorder=3)
        if subtitle:
            ax.text(tx, y + h - 0.048, subtitle, ha="left", va="center", fontsize=sub_size, color=sub_color, zorder=3)
    else:
        tx = x + 0.02
        if subtitle:
            ax.text(tx, y + h * 0.68, title, ha="left", va="center", fontsize=title_size, fontweight="bold", color=title_color, zorder=3)
            ax.text(tx, y + h * 0.32, subtitle, ha="left", va="center", fontsize=sub_size, color=sub_color, zorder=3)
        else:
            ax.text(tx, y + h * 0.5, title, ha="left", va="center", fontsize=title_size, fontweight="bold", color=title_color, zorder=3)


def draw_arrow(ax, x1, y1, x2, y2, label="", color="#475569", lw=1.8, style="->", rad=0.0, label_pos=0.5, label_offset=(0, 0.015), label_size=8, label_color="#1e293b", label_bg=None):
    """Draw a clean directional connection arrow with optional text label."""
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style,
        connectionstyle=f"arc3,rad={rad}",
        color=color,
        linewidth=lw,
        mutation_scale=14,
        zorder=4
    )
    ax.add_patch(arrow)
    if label:
        mx = x1 + (x2 - x1) * label_pos + label_offset[0]
        my = y1 + (y2 - y1) * label_pos + label_offset[1]
        bbox_props = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9) if label_bg != False else None
        ax.text(mx, my, label, ha="center", va="center", fontsize=label_size, color=label_color, fontweight="semibold", bbox=bbox_props, zorder=5)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Figure 3.1: System Workflow
# ══════════════════════════════════════════════════════════════════════════════
def generate_figure_3_1():
    fig, ax = plt.subplots(figsize=(10, 14), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.965, "DataForge End-to-End System Workflow", ha="center", va="center", fontsize=15, fontweight="black", color="#0f172a")
    ax.text(0.5, 0.942, "Comprehensive Sequential Pipeline from Raw Data Ingestion to Multimodal Export", ha="center", va="center", fontsize=9.5, color="#64748b")

    w, h = 0.58, 0.065
    cx = 0.5 - w / 2

    steps = [
        ("1. Data Ingestion & Validation", "Multi-Source Uploads: CSV, Excel (.xlsx/.xls), Google Sheets, Cloud Storage\nFormat verification, MIME checking, and automated schema inference", "#eff6ff", "#3b82f6", 0.85),
        ("2. Automated Data Cleaning Pipeline", "Heuristic Null Imputation (Mean/Median/Mode), >60% Missing Column Pruning,\nDuplicate Row Removal, snake_case Normalization, Whitespace Stripping", "#f0fdf4", "#10b981", 0.74),
        ("3. Exploratory Data Analysis (EDA)", "Summary Statistics, Column Cardinality, Distribution Skewness,\nMissingness Heatmaps & Univariate/Bivariate Statistical Profiling", "#faf5ff", "#8b5cf6", 0.63),
        ("4. Deterministic Insight Engine", "Hypothesis-Free Statistical Pattern Mining: OLS Trend Regressions,\nZ-Score (Z > 3.5) Anomaly Identification & Pearson (|r| >= 0.65) Correlations", "#fffbeb", "#f59e0b", 0.52),
    ]

    for title, sub, bg, border, y in steps:
        draw_card(ax, cx, y, w, h, title, sub, bg=bg, border=border, lw=2, title_size=10.5, sub_size=7.5, title_color=border)

    draw_arrow(ax, 0.5, 0.85, 0.5, 0.74 + h, color="#3b82f6", lw=2)
    draw_arrow(ax, 0.5, 0.74, 0.5, 0.63 + h, color="#10b981", lw=2)
    draw_arrow(ax, 0.5, 0.63, 0.5, 0.52 + h, color="#8b5cf6", lw=2)

    y_split = 0.38
    w_half = 0.38
    x_left = 0.10
    x_right = 0.52

    draw_card(ax, x_left, y_split, w_half, 0.08, "5A. AI Query Module", "Google Gemini 2.5 Flash NLQ Engine\nNatural Language to Python AST Sandbox Execution\nGenerates Dynamic Visualizations & Contextual Insights", bg="#ecfeff", border="#06b6d4", lw=2, title_size=10, sub_size=7.5, title_color="#0891b2")
    draw_card(ax, x_right, y_split, w_half, 0.08, "5B. AutoML Predictive Engine", "FLAML Automated Machine Learning\nTask Detection (Classification / Regression)\nLightGBM, XGBoost, Random Forest, SHAP Values", bg="#fdf2f8", border="#ec4899", lw=2, title_size=10, sub_size=7.5, title_color="#db2777")

    draw_arrow(ax, 0.44, 0.52, x_left + w_half/2, y_split + 0.08, label="Natural Language", color="#0891b2", rad=-0.15, label_size=7.5)
    draw_arrow(ax, 0.56, 0.52, x_right + w_half/2, y_split + 0.08, label="Predictive Modeling", color="#db2777", rad=0.15, label_size=7.5)

    y_rep = 0.23
    draw_card(ax, cx, y_rep, w, 0.07, "6. Multi-Source Report Generation", "Executive 5-Section Synthesis: Overview, Data Quality Audit, Key Statistical Insights,\nPredictive Model Performance Leaderboards & Actionable Business Recommendations", bg="#fef2f2", border="#ef4444", lw=2, title_size=10.5, sub_size=7.5, title_color="#dc2626")

    draw_arrow(ax, x_left + w_half/2, y_split, 0.44, y_rep + 0.07, color="#0891b2", rad=-0.1)
    draw_arrow(ax, x_right + w_half/2, y_split, 0.56, y_rep + 0.07, color="#db2777", rad=0.1)

    y_exp = 0.11
    draw_card(ax, cx, y_exp, w, 0.065, "7. Delivery, Dashboard & Export", "Interactive Web Dashboard, Cleaned Dataset CSV/Excel Download,\nTrained Model Binary (.pkl), and Comprehensive Formatted PDF Report", bg="#f8fafc", border="#475569", lw=2, title_size=10.5, sub_size=7.5, title_color="#334155")

    draw_arrow(ax, 0.5, y_rep, 0.5, y_exp + 0.065, color="#ef4444", lw=2)
    ax.text(0.5, 0.035, "Figure 3.1: DataForge System Workflow Pipeline", ha="center", va="center", fontsize=11, fontweight="bold", color="#0f172a")

    out_file = OUT_DIR / "figure_3_1_system_workflow.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {out_file}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Figure 3.2: DataForge System Architecture
# ══════════════════════════════════════════════════════════════════════════════
def generate_figure_3_2():
    fig, ax = plt.subplots(figsize=(13, 11), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.965, "DataForge Multi-Tier System Architecture", ha="center", va="center", fontsize=16, fontweight="black", color="#0f172a")
    ax.text(0.5, 0.940, "Decoupled 4-Tier Layered Architecture with Asynchronous Analytical Processing", ha="center", va="center", fontsize=10, color="#64748b")

    tier_h = 0.155
    child_h = 0.082

    # Tier 1
    y_t1 = 0.765
    draw_card(ax, 0.04, y_t1, 0.92, tier_h, "1. Presentation Layer (Next.js 15 Client Tier)", bg="#f8fafc", border="#3b82f6", lw=2, title_size=11, title_color="#1d4ed8", align="top-left")
    t1_mods = [
        ("Next.js 15 App Router", "Server & Client Components\nTypeScript, React 19", 0.06, 0.19),
        ("Theme & UI System", "TailwindCSS, CSS Variables\nLucide Icons, 12 Human Avatars", 0.28, 0.21),
        ("Interactive Visualization", "Chart.js 4.x Canvas Charts\nDynamic Responsive EDA", 0.52, 0.20),
        ("Real-Time Notification", "WebSocket Client, Live Job\nProgress & Status Toast Alerts", 0.75, 0.19),
    ]
    for m_title, m_sub, mx, mw in t1_mods:
        draw_card(ax, mx, y_t1 + 0.016, mw, child_h, m_title, m_sub, bg="#ffffff", border="#93c5fd", lw=1.2, title_size=8.5, sub_size=7)

    # Tier 2
    y_t2 = 0.545
    draw_card(ax, 0.04, y_t2, 0.92, tier_h, "2. Application & API Gateway Layer (FastAPI Asynchronous Backend)", bg="#f0fdf4", border="#10b981", lw=2, title_size=11, title_color="#047857", align="top-left")
    t2_mods = [
        ("REST API Gateway", "Asynchronous Endpoints\nUvicorn ASGI Server, CORS", 0.06, 0.19),
        ("Auth & Access Control", "JWT Verification, Google OAuth\nRBAC & Organization Governance", 0.28, 0.21),
        ("Job & Pipeline Manager", "Async Job Orchestrator, ETag\nOptimistic Concurrency Control", 0.52, 0.20),
        ("WebSocket Hub", "ConnectionManager Channels\nLive Ingestion & Train Updates", 0.75, 0.19),
    ]
    for m_title, m_sub, mx, mw in t2_mods:
        draw_card(ax, mx, y_t2 + 0.016, mw, child_h, m_title, m_sub, bg="#ffffff", border="#6ee7b7", lw=1.2, title_size=8.5, sub_size=7)

    # Tier 3
    y_t3 = 0.325
    draw_card(ax, 0.04, y_t3, 0.92, tier_h, "3. Processing & Analytical Intelligence Layer", bg="#faf5ff", border="#8b5cf6", lw=2, title_size=11, title_color="#6d28d9", align="top-left")
    t3_mods = [
        ("Automated Data Cleaner", "Missing Imputation, De-duplication\nType Normalization & Sanitization", 0.06, 0.20),
        ("Deterministic Insights", "Z-Score (Z>3.5) Outlier Detection\nPearson Correlations, OLS Trends", 0.29, 0.21),
        ("FLAML AutoML Engine", "Task Detection, Model Leaderboard\nLightGBM, XGBoost, SHAP Explain", 0.53, 0.21),
        ("Gemini AI Query Engine", "Natural Language Querying, Python\nAST-Sandbox Execution & Plotting", 0.77, 0.17),
    ]
    for m_title, m_sub, mx, mw in t3_mods:
        draw_card(ax, mx, y_t3 + 0.016, mw, child_h, m_title, m_sub, bg="#ffffff", border="#c4b5fd", lw=1.2, title_size=8.5, sub_size=7)

    # Tier 4
    y_t4 = 0.105
    draw_card(ax, 0.04, y_t4, 0.92, tier_h, "4. Data, Storage & External Services Layer", bg="#fffbeb", border="#f59e0b", lw=2, title_size=11, title_color="#b45309", align="top-left")
    t4_mods = [
        ("Supabase PostgreSQL", "User Accounts, Projects, Teams,\nMetadata, Subscriptions & Quotas", 0.06, 0.20),
        ("Storage Subsystem", "Supabase Object Storage, Local\nRaw/Clean CSV & Parquet Artifacts", 0.29, 0.21),
        ("Model Registry", "Joblib/Pickle Model Binaries,\nEvaluation Metrics & SHAP Values", 0.53, 0.21),
        ("External Cloud APIs", "Google OAuth 2.0 Identity,\nGoogle Gemini 2.5 Flash API", 0.77, 0.17),
    ]
    for m_title, m_sub, mx, mw in t4_mods:
        draw_card(ax, mx, y_t4 + 0.016, mw, child_h, m_title, m_sub, bg="#ffffff", border="#fcd34d", lw=1.2, title_size=8.5, sub_size=7)

    # Inter-tier communication arrows
    draw_arrow(ax, 0.25, y_t1, 0.25, y_t2 + tier_h, label="HTTP / REST Requests", color="#2563eb", style="<->", label_size=7.5)
    draw_arrow(ax, 0.75, y_t2 + tier_h, 0.75, y_t1, label="WebSocket Events (WSS)", color="#2563eb", style="->", label_size=7.5)

    draw_arrow(ax, 0.25, y_t2, 0.25, y_t3 + tier_h, label="Async Tasks & Execution", color="#059669", style="<->", label_size=7.5)
    draw_arrow(ax, 0.75, y_t3 + tier_h, 0.75, y_t2, label="Analytical Results & Metrics", color="#059669", style="->", label_size=7.5)

    draw_arrow(ax, 0.25, y_t3, 0.25, y_t4 + tier_h, label="Read/Write Datasets & Artifacts", color="#7c3aed", style="<->", label_size=7.5)
    draw_arrow(ax, 0.75, y_t4 + tier_h, 0.75, y_t3, label="AI Inference & Metadata Sync", color="#7c3aed", style="<->", label_size=7.5)

    ax.text(0.5, 0.035, "Figure 3.2: DataForge Enterprise Multi-Tier System Architecture", ha="center", va="center", fontsize=11, fontweight="bold", color="#0f172a")

    out_file = OUT_DIR / "figure_3_2_system_architecture.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {out_file}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Figure 3.3: Context Diagram (Level 0 DFD)
# ══════════════════════════════════════════════════════════════════════════════
def generate_figure_3_3():
    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.95, "DataForge Context Diagram (Level 0 DFD)", ha="center", va="center", fontsize=15, fontweight="black", color="#0f172a")
    ax.text(0.5, 0.92, "High-Level External Entity Boundary and Environmental Data Flows", ha="center", va="center", fontsize=9.5, color="#64748b")

    cx, cy, cr = 0.5, 0.50, 0.12
    circle = Circle((cx, cy), cr, facecolor="#eff6ff", edgecolor="#2563eb", linewidth=2.5, zorder=3)
    ax.add_patch(circle)
    ax.text(cx, cy + 0.035, "0.0", ha="center", va="center", fontsize=12, fontweight="black", color="#1d4ed8", zorder=4)
    ax.text(cx, cy, "DataForge\nAnalytics Platform", ha="center", va="center", fontsize=11, fontweight="bold", color="#0f172a", zorder=4)

    ux, uy, uw, uh = 0.06, 0.68, 0.24, 0.12
    draw_card(ax, ux, uy, uw, uh, "User / Client Browser", "Web User interacting via\nNext.js responsive interface", bg="#ffffff", border="#334155", lw=2, title_color="#0f172a")

    gx, gy, gw, gh = 0.06, 0.18, 0.24, 0.12
    draw_card(ax, gx, gy, gw, gh, "Google OAuth 2.0", "Third-party authentication\nand identity token verification", bg="#ffffff", border="#ea4335", lw=2, title_color="#b91c1c")

    dx, dy, dw, dh = 0.70, 0.68, 0.24, 0.12
    draw_card(ax, dx, dy, dw, dh, "Data Sources & APIs", "Google Sheets, OneDrive, S3,\nPostgreSQL & Local File Uploads", bg="#ffffff", border="#059669", lw=2, title_color="#047857")

    ai_x, ai_y, ai_w, ai_h = 0.70, 0.18, 0.24, 0.12
    draw_card(ax, ai_x, ai_y, ai_w, ai_h, "Google Gemini AI API", "Gemini 2.5 Flash\nLLM Analytical Inference", bg="#ffffff", border="#7c3aed", lw=2, title_color="#6d28d9")

    db_x, db_y, db_w, db_h = 0.38, 0.08, 0.24, 0.11
    draw_card(ax, db_x, db_y, db_w, db_h, "Supabase Database & S3", "PostgreSQL tables and object\nstorage for datasets & models", bg="#ffffff", border="#d97706", lw=2, title_color="#b45309")

    draw_arrow(ax, ux + uw, uy + uh * 0.7, cx - cr * 0.7, cy + cr * 0.7, label="Dataset uploads, queries, actions", color="#2563eb", rad=-0.08, label_size=7)
    draw_arrow(ax, cx - cr * 0.7, cy + cr * 0.3, ux + uw, uy + uh * 0.2, label="Interactive charts, reports, insights", color="#2563eb", rad=0.08, label_size=7)

    draw_arrow(ax, cx - cr * 0.8, cy - cr * 0.5, gx + gw, gy + gh * 0.65, label="OAuth exchange request", color="#ea4335", rad=-0.08, label_size=7)
    draw_arrow(ax, gx + gw, gy + gh * 0.25, cx - cr * 0.5, cy - cr * 0.8, label="JWT user profile token", color="#ea4335", rad=0.08, label_size=7)

    draw_arrow(ax, dx, dy + dh * 0.5, cx + cr * 0.8, cy + cr * 0.6, label="Raw CSV / Excel / Sheet Stream", color="#059669", rad=-0.08, label_size=7)

    draw_arrow(ax, cx + cr * 0.8, cy - cr * 0.4, ai_x, ai_y + ai_h * 0.7, label="Schema prompt & context", color="#7c3aed", rad=-0.08, label_size=7)
    draw_arrow(ax, ai_x, ai_y + ai_h * 0.3, cx + cr * 0.6, cy - cr * 0.8, label="Analysis code & summary", color="#7c3aed", rad=0.08, label_size=7)

    draw_arrow(ax, cx - 0.04, cy - cr, db_x + db_w * 0.3, db_y + db_h, label="Save meta / artifacts", color="#d97706", rad=-0.05, label_size=6.8)
    draw_arrow(ax, db_x + db_w * 0.7, db_y + db_h, cx + 0.04, cy - cr, label="Retrieve sessions & models", color="#d97706", rad=0.05, label_size=6.8)

    ax.text(0.5, 0.025, "Figure 3.3: DataForge Context Diagram (Level 0 DFD)", ha="center", va="center", fontsize=11, fontweight="bold", color="#0f172a")

    out_file = OUT_DIR / "figure_3_3_context_dfd_level_0.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {out_file}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. Figure 3.4: Detailed Diagram (Level 1 DFD)
# ══════════════════════════════════════════════════════════════════════════════
def generate_figure_3_4():
    fig, ax = plt.subplots(figsize=(12, 14), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.97, "DataForge Detailed Level 1 Data Flow Diagram (DFD)", ha="center", va="center", fontsize=15, fontweight="black", color="#0f172a")
    ax.text(0.5, 0.948, "Internal Functional Processes, Information Flows, and Persistent Data Stores", ha="center", va="center", fontsize=9.5, color="#64748b")

    def draw_process(ax, cx, cy, pid, name, sub="", color="#2563eb", bg="#eff6ff"):
        r = 0.055
        circle = Circle((cx, cy), r, facecolor=bg, edgecolor=color, linewidth=2, zorder=3)
        ax.add_patch(circle)
        ax.text(cx, cy + 0.022, pid, ha="center", va="center", fontsize=9, fontweight="black", color=color, zorder=4)
        ax.text(cx, cy - 0.005, name, ha="center", va="center", fontsize=8, fontweight="bold", color="#0f172a", zorder=4)
        if sub:
            ax.text(cx, cy - 0.025, sub, ha="center", va="center", fontsize=6.5, color="#475569", zorder=4)

    def draw_datastore(ax, x, y, w, h, ds_id, name):
        box = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0", facecolor="#fffbeb", edgecolor="#d97706", linewidth=1.5, zorder=2)
        ax.add_patch(box)
        ax.plot([x + w * 0.28, x + w * 0.28], [y, y + h], color="#d97706", linewidth=1.2, zorder=3)
        ax.text(x + w * 0.14, y + h / 2, ds_id, ha="center", va="center", fontsize=8, fontweight="bold", color="#b45309", zorder=4)
        ax.text(x + w * 0.64, y + h / 2, name, ha="center", va="center", fontsize=8, fontweight="semibold", color="#0f172a", zorder=4)

    draw_card(ax, 0.08, 0.86, 0.24, 0.06, "User / Client Browser", "Data Analyst, Researcher, SME", bg="#ffffff", border="#334155", lw=1.8)
    draw_card(ax, 0.68, 0.86, 0.24, 0.06, "Google APIs & Sheets", "Sheets API, Gemini 2.5 Flash", bg="#ffffff", border="#7c3aed", lw=1.8)

    draw_process(ax, 0.50, 0.87, "P1.0", "Data Ingestion", "Validation & Parse", color="#0284c7", bg="#f0f9ff")
    draw_process(ax, 0.50, 0.72, "P2.0", "Data Cleaning", "Impute & Normalize", color="#059669", bg="#f0fdf4")
    draw_process(ax, 0.25, 0.56, "P3.0", "EDA & Profiling", "Distributions & Stats", color="#8b5cf6", bg="#faf5ff")
    draw_process(ax, 0.50, 0.56, "P4.0", "Insight Engine", "Z-Scores & Regressions", color="#d97706", bg="#fffbeb")
    draw_process(ax, 0.75, 0.56, "P5.0", "AI Querying", "NLQ to Python Sandbox", color="#0891b2", bg="#ecfeff")
    draw_process(ax, 0.35, 0.38, "P6.0", "AutoML Engine", "Model Search & SHAP", color="#ec4899", bg="#fdf2f8")
    draw_process(ax, 0.65, 0.38, "P7.0", "Report Generator", "Executive Synthesizer", color="#dc2626", bg="#fef2f2")

    draw_datastore(ax, 0.05, 0.71, 0.25, 0.045, "D1", "Raw & Clean Datasets")
    draw_datastore(ax, 0.70, 0.71, 0.25, 0.045, "D2", "Metadata & Schemas")
    draw_datastore(ax, 0.38, 0.23, 0.24, 0.045, "D3", "Trained Models & SHAP")
    draw_datastore(ax, 0.68, 0.23, 0.26, 0.045, "D4", "Generated Reports & PDFs")

    draw_arrow(ax, 0.32, 0.89, 0.44, 0.88, label="Uploads (.csv, .xlsx)", color="#0284c7", label_size=7)
    draw_arrow(ax, 0.68, 0.89, 0.56, 0.88, label="Sheet URI", color="#0284c7", label_size=7)

    draw_arrow(ax, 0.50, 0.81, 0.50, 0.78, label="Raw DataFrame", color="#059669", label_size=7)
    draw_arrow(ax, 0.45, 0.84, 0.18, 0.76, label="Store Raw Data", color="#0284c7", rad=-0.1, label_size=6.5)

    draw_arrow(ax, 0.44, 0.72, 0.30, 0.73, label="Store Cleaned Data", color="#059669", label_size=6.5)
    draw_arrow(ax, 0.56, 0.72, 0.70, 0.73, label="Store Clean Schema", color="#059669", label_size=6.5)

    draw_arrow(ax, 0.45, 0.68, 0.27, 0.62, label="Cleaned Data", color="#8b5cf6", rad=-0.1, label_size=6.5)
    draw_arrow(ax, 0.50, 0.66, 0.50, 0.62, label="Cleaned Data", color="#d97706", label_size=6.5)
    draw_arrow(ax, 0.55, 0.68, 0.73, 0.62, label="Cleaned Data", color="#0891b2", rad=0.1, label_size=6.5)

    draw_arrow(ax, 0.80, 0.86, 0.77, 0.62, label="Schema & Prompts", color="#7c3aed", rad=-0.1, label_size=6.5)
    draw_arrow(ax, 0.74, 0.62, 0.77, 0.86, label="Python Code & Response", color="#7c3aed", rad=-0.1, label_size=6.5)

    draw_arrow(ax, 0.25, 0.50, 0.32, 0.44, label="Correlations & Dtypes", color="#8b5cf6", rad=-0.1, label_size=6.5)
    draw_arrow(ax, 0.50, 0.50, 0.62, 0.44, label="Ranked Insights", color="#d97706", rad=0.1, label_size=6.5)
    draw_arrow(ax, 0.73, 0.50, 0.67, 0.44, label="AI Query Summaries", color="#0891b2", rad=-0.1, label_size=6.5)

    draw_arrow(ax, 0.38, 0.32, 0.45, 0.28, label="Model .pkl & Metrics", color="#ec4899", label_size=6.5)
    draw_arrow(ax, 0.41, 0.38, 0.59, 0.38, label="Evaluation Leaderboard", color="#ec4899", label_size=6.5)

    draw_arrow(ax, 0.68, 0.32, 0.75, 0.28, label="Save PDF & Slides", color="#dc2626", label_size=6.5)

    draw_arrow(ax, 0.20, 0.54, 0.12, 0.86, label="Interactive EDA Visuals", color="#8b5cf6", rad=-0.25, label_size=6.5)
    draw_arrow(ax, 0.65, 0.32, 0.15, 0.86, label="Download PDF Reports & Models", color="#dc2626", rad=0.35, label_size=6.5)

    ax.text(0.5, 0.04, "Figure 3.4: DataForge Detailed Level 1 Data Flow Diagram (DFD)", ha="center", va="center", fontsize=11, fontweight="bold", color="#0f172a")

    out_file = OUT_DIR / "figure_3_4_detailed_dfd_level_1.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {out_file}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. Figure 3.5: Functional Module Interaction Diagram
# ══════════════════════════════════════════════════════════════════════════════
def generate_figure_3_5():
    fig, ax = plt.subplots(figsize=(12, 10), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.965, "DataForge Functional Module Interaction Architecture", ha="center", va="center", fontsize=16, fontweight="black", color="#0f172a")
    ax.text(0.5, 0.940, "Interconnected Workable Subsystems Orchestrated Across the Analytics Lifecycle", ha="center", va="center", fontsize=10, color="#64748b")

    hx, hy, hw, hh = 0.38, 0.44, 0.24, 0.12
    draw_card(ax, hx, hy, hw, hh, "Central Workspace Hub", "State Orchestrator, ETag Lock,\nSession & Dataset Memory Cache", bg="#eff6ff", border="#2563eb", lw=2.5, title_color="#1d4ed8")

    modules = [
        ("3.3.1 User Authentication", "Google OAuth 2.0, JWT Tokens,\nRBAC & Org Membership", 0.06, 0.77, 0.26, 0.09, "#f8fafc", "#475569", "#1e293b"),
        ("3.3.2 Data Ingestion Hub", "Multi-Source Uploads: CSV, XLS,\nGoogle Sheets & DB Connectors", 0.37, 0.77, 0.26, 0.09, "#f0f9ff", "#0284c7", "#0369a1"),
        ("3.3.3 Data Cleaning Engine", "Imputation, 60% Missing Drop,\nsnake_case & Deduplication", 0.68, 0.77, 0.26, 0.09, "#f0fdf4", "#10b981", "#047857"),
        ("3.3.4 Exploratory Analysis (EDA)", "Summary Statistics, Cardinality,\nDistribution & Missing Heatmaps", 0.69, 0.46, 0.26, 0.09, "#faf5ff", "#8b5cf6", "#6d28d9"),
        ("3.3.5 AI Query Engine (Gemini)", "Natural Language Interaction,\nAST Code Sandbox Execution", 0.68, 0.15, 0.26, 0.09, "#ecfeff", "#0891b2", "#0e7490"),
        ("3.3.6 AutoML Predictive Engine", "Task Detection, Iterative Search,\nLightGBM/XGBoost, SHAP Values", 0.37, 0.15, 0.26, 0.09, "#fdf2f8", "#ec4899", "#be185d"),
        ("3.3.7 Deterministic Insight Engine", "Hypothesis-Free Statistical Mining,\nZ-Score Anomalies, Pearson Regr.", 0.06, 0.15, 0.26, 0.09, "#fffbeb", "#f59e0b", "#b45309"),
        ("3.3.8 Report Generation Module", "Executive 5-Slide Report Synthesis,\nPDF/HTML Export & Storytelling", 0.05, 0.46, 0.26, 0.09, "#fef2f2", "#ef4444", "#b91c1c"),
    ]

    for title, sub, x, y, w, h, bg, border, tc in modules:
        draw_card(ax, x, y, w, h, title, sub, bg=bg, border=border, lw=2, title_size=9.5, sub_size=7.5, title_color=tc)

    draw_arrow(ax, 0.25, 0.77, 0.40, 0.56, label="User Identity & Claims", color="#475569", style="->", label_size=7)
    draw_arrow(ax, 0.50, 0.77, 0.50, 0.56, label="Raw Dataset Upload ID", color="#0284c7", style="->", label_size=7)
    draw_arrow(ax, 0.58, 0.56, 0.72, 0.77, label="Cleaned Frame", color="#10b981", style="<->", label_size=7)
    draw_arrow(ax, 0.62, 0.50, 0.69, 0.50, label="Statistical Profiles", color="#8b5cf6", style="<->", label_size=7)
    draw_arrow(ax, 0.58, 0.44, 0.73, 0.24, label="NLQ Responses & Charts", color="#0891b2", style="<->", label_size=7)
    draw_arrow(ax, 0.50, 0.44, 0.50, 0.24, label="Model Artifacts & Metrics", color="#ec4899", style="<->", label_size=7)
    draw_arrow(ax, 0.42, 0.44, 0.25, 0.24, label="Ranked Findings", color="#f59e0b", style="<->", label_size=7)
    draw_arrow(ax, 0.38, 0.50, 0.31, 0.50, label="Compile All Artifacts", color="#ef4444", style="<->", label_size=7)

    draw_arrow(ax, 0.63, 0.81, 0.68, 0.81, color="#10b981", style="->")
    draw_arrow(ax, 0.18, 0.24, 0.18, 0.46, label="Insights Stream", color="#f59e0b", style="->", label_size=6.5)
    draw_arrow(ax, 0.37, 0.20, 0.26, 0.46, label="Leaderboard Data", color="#ec4899", style="->", label_size=6.5, rad=-0.1)

    ax.text(0.5, 0.035, "Figure 3.5: DataForge Functional Module Interaction Diagram", ha="center", va="center", fontsize=11, fontweight="bold", color="#0f172a")

    out_file = OUT_DIR / "figure_3_5_module_interaction.png"
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Generated {out_file}")


if __name__ == "__main__":
    generate_figure_3_1()
    generate_figure_3_2()
    generate_figure_3_3()
    generate_figure_3_4()
    generate_figure_3_5()
    print("All 5 diagrams successfully generated at publication-ready 300 DPI.")
