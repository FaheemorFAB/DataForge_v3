"""
DataForge Publication Diagram Generator - Black and White Edition
Generates the 4 report diagrams in high-resolution B&W:
1. Figure 3.1: DataForge System Architecture
2. Figure 3.2: Context Diagram (Level 0 DFD)
3. Figure 3.3: DataForge Level 1 Data Flow Diagram
4. Figure 3.4: Overall Process Flow
"""

import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Polygon, Rectangle

OUT_DIR = Path("/home/fab/DataForge_v3/fin_pics")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Styling Constants: Pure Black and White
C_BG = "#ffffff"
C_WHITE = "#ffffff"
C_BLACK = "#000000"

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Liberation Sans", "Arial"]

def draw_card(ax, x, y, w, h, title, subtitle="", bg="#ffffff", border="#000000", radius=0.012, lw=1.5, title_size=9.5, sub_size=7.5, align="center"):
    """Draw a clean card with black border and white background."""
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
            ax.text(cx, y + h * 0.65, title, ha="center", va="center", fontsize=title_size, fontweight="bold", color=C_BLACK, zorder=3)
            ax.text(cx, y + h * 0.32, subtitle, ha="center", va="center", fontsize=sub_size, color=C_BLACK, zorder=3)
        else:
            ax.text(cx, y + h * 0.5, title, ha="center", va="center", fontsize=title_size, fontweight="bold", color=C_BLACK, zorder=3)
    elif align == "top-left":
        tx = x + 0.015
        ax.text(tx, y + h - 0.024, title, ha="left", va="center", fontsize=title_size, fontweight="bold", color=C_BLACK, zorder=3)
        if subtitle:
            ax.text(tx, y + h - 0.046, subtitle, ha="left", va="center", fontsize=sub_size, color=C_BLACK, zorder=3)
    else:
        tx = x + 0.015
        if subtitle:
            ax.text(tx, y + h * 0.68, title, ha="left", va="center", fontsize=title_size, fontweight="bold", color=C_BLACK, zorder=3)
            ax.text(tx, y + h * 0.32, subtitle, ha="left", va="center", fontsize=sub_size, color=C_BLACK, zorder=3)
        else:
            ax.text(tx, y + h * 0.5, title, ha="left", va="center", fontsize=title_size, fontweight="bold", color=C_BLACK, zorder=3)

def draw_arrow(ax, x1, y1, x2, y2, label="", color="#000000", lw=1.4, style="->", rad=0.0, label_pos=0.5, label_offset=(0, 0), label_size=7.2, dashed=False):
    """Draw a black directional arrow with optional label in a crisp white badge."""
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style,
        connectionstyle=f"arc3,rad={rad}",
        color=color,
        linewidth=lw,
        linestyle="--" if dashed else "-",
        mutation_scale=12,
        zorder=4
    )
    ax.add_patch(arrow)
    if label:
        mx = x1 + (x2 - x1) * label_pos + label_offset[0]
        my = y1 + (y2 - y1) * label_pos + label_offset[1]
        bbox_props = dict(boxstyle="square,pad=0.22", fc="#ffffff", ec="#000000", lw=0.8, alpha=1.0)
        ax.text(mx, my, label, ha="center", va="center", fontsize=label_size, color=C_BLACK, fontweight="bold", bbox=bbox_props, zorder=6)

def draw_entity(ax, x, y, w, h, title, subtitle="", lw=1.8):
    """Draw an external entity with classic double-line border."""
    box1 = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0", facecolor="#ffffff", edgecolor="#000000", linewidth=lw, zorder=2)
    ax.add_patch(box1)
    gap = 0.0055
    box2 = FancyBboxPatch((x + gap, y + gap), w - 2*gap, h - 2*gap, boxstyle="square,pad=0", facecolor="#ffffff", edgecolor="#000000", linewidth=0.8, zorder=2)
    ax.add_patch(box2)
    cx = x + w / 2
    if subtitle:
        ax.text(cx, y + h * 0.65, title, ha="center", va="center", fontsize=8.8, fontweight="bold", color=C_BLACK, zorder=3)
        ax.text(cx, y + h * 0.32, subtitle, ha="center", va="center", fontsize=7.0, color=C_BLACK, zorder=3)
    else:
        ax.text(cx, y + h * 0.5, title, ha="center", va="center", fontsize=9.2, fontweight="bold", color=C_BLACK, zorder=3)

def draw_datastore(ax, x, y, w, h, ds_id, name, sub="", lw=1.5):
    """Draw a classic DFD open-ended data store: parallel top & bottom lines with vertical label divider."""
    bg = Rectangle((x, y), w, h, facecolor="#ffffff", edgecolor="none", zorder=2)
    ax.add_patch(bg)
    ax.plot([x, x + w], [y + h, y + h], color="#000000", linewidth=lw, zorder=3)
    ax.plot([x, x + w], [y, y], color="#000000", linewidth=lw, zorder=3)
    ax.plot([x, x], [y, y + h], color="#000000", linewidth=lw, zorder=3)
    div_x = x + w * 0.20
    ax.plot([div_x, div_x], [y, y + h], color="#000000", linewidth=1.0, zorder=3)
    ax.text(x + (div_x - x) / 2, y + h / 2, ds_id, ha="center", va="center", fontsize=8.2, fontweight="bold", color=C_BLACK, zorder=4)
    if sub:
        ax.text(div_x + (w - (div_x - x)) / 2, y + h * 0.65, name, ha="center", va="center", fontsize=8.0, fontweight="bold", color=C_BLACK, zorder=4)
        ax.text(div_x + (w - (div_x - x)) / 2, y + h * 0.32, sub, ha="center", va="center", fontsize=6.6, color=C_BLACK, zorder=4)
    else:
        ax.text(div_x + (w - (div_x - x)) / 2, y + h / 2, name, ha="center", va="center", fontsize=8.0, fontweight="bold", color=C_BLACK, zorder=4)

def draw_process_node(ax, cx, cy, r, pid, name, sub=""):
    """Draw a circular process node for DFD."""
    circle = Circle((cx, cy), r, facecolor="#ffffff", edgecolor="#000000", linewidth=1.8, zorder=3)
    ax.add_patch(circle)
    ch_y = cy + r * 0.35
    half_w = (r**2 - (ch_y - cy)**2)**0.5
    ax.plot([cx - half_w, cx + half_w], [ch_y, ch_y], color="#000000", linewidth=1.0, zorder=4)
    ax.text(cx, cy + r * 0.62, pid, ha="center", va="center", fontsize=8.2, fontweight="bold", color=C_BLACK, zorder=5)
    if sub:
        ax.text(cx, cy - r * 0.08, name, ha="center", va="center", fontsize=7.2, fontweight="bold", color=C_BLACK, zorder=5)
        ax.text(cx, cy - r * 0.46, sub, ha="center", va="center", fontsize=6.2, color=C_BLACK, zorder=5)
    else:
        ax.text(cx, cy - r * 0.22, name, ha="center", va="center", fontsize=7.6, fontweight="bold", color=C_BLACK, zorder=5)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Figure 3.1: DataForge System Architecture
# ══════════════════════════════════════════════════════════════════════════════
def generate_figure_3_1_architecture():
    fig, ax = plt.subplots(figsize=(14, 12.5), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.972, "Figure 3.1: DataForge System Architecture", ha="center", va="center", fontsize=15, fontweight="bold", color=C_BLACK)
    ax.text(0.5, 0.950, "Layered Web Architecture Separating Presentation, API Gateway, Analytical Processing, and Storage", ha="center", va="center", fontsize=9.5, style="italic", color=C_BLACK)

    tier_w = 0.92
    tier_x = 0.04
    tier_h = 0.165
    child_h = 0.095

    # TIER 1
    y_t1 = 0.760
    draw_card(ax, tier_x, y_t1, tier_w, tier_h, "TIER 1: PRESENTATION & CLIENT LAYER (Next.js 15 / React / TypeScript)", bg="#ffffff", border="#000000", lw=2, title_size=10.5, align="top-left")
    t1_cards = [
        ("App Router & State", "Next.js App Router (Client/Server)\nSWR Data Fetching & Hooks\nTailwind CSS Design System", 0.055, 0.165),
        ("User Auth & Workspace", "Google OAuth 2.0 PKCE Modal\nJWT Session Cookie State\nRBAC: Owner / Admin / Viewer", 0.235, 0.165),
        ("Dataset Management", "Multi-Source File Uploader\nCSV, Excel, Sheets & DB Preview\nSchema Health Card & Data Types", 0.415, 0.165),
        ("Cleaning & Joins Studio", "Missing Imputation & Tukey Capping\nInteractive Rule Preview DAG\nDuckDB Multi-Table Join Canvas", 0.595, 0.170),
        ("Analytics & AutoML View", "Plotly & Chart.js Visualizations\nAI Chatbot Query Interface\nFLAML Model Leaderboard & PDF", 0.780, 0.165),
    ]
    for title, sub, mx, mw in t1_cards:
        draw_card(ax, mx, y_t1 + 0.016, mw, child_h, title, sub, bg="#ffffff", border="#000000", lw=1.2, title_size=8.5, sub_size=6.8)

    # TIER 2
    y_t2 = 0.535
    draw_card(ax, tier_x, y_t2, tier_w, tier_h, "TIER 2: BACKEND SERVICES & API GATEWAY LAYER (Python / FastAPI / Uvicorn ASGI)", bg="#ffffff", border="#000000", lw=2, title_size=10.5, align="top-left")
    t2_cards = [
        ("Reverse Proxy & Security", "FastAPI Path Routing (/api/*)\nCORS Middleware & OWASP Headers\nSlowAPI Sliding-Window Rate Limiter", 0.055, 0.205),
        ("Authentication & Access Guard", "JWT Bearer Token Decoding\nGoogle OAuth 2.0 Token Exchange\nWorkspace Permission & Quota Guard", 0.280, 0.205),
        ("API Route Controllers", "auth.py / upload.py / procedures.py\ninsights.py / automl.py / reports.py\nETag Optimistic Concurrency Control", 0.505, 0.215),
        ("WebSocket & Worker Hub", "WebSocket ConnectionManager (/ws)\nLive Streaming Ingestion / Training\nThreadPoolExecutor Background Queue", 0.740, 0.205),
    ]
    for title, sub, mx, mw in t2_cards:
        draw_card(ax, mx, y_t2 + 0.016, mw, child_h, title, sub, bg="#ffffff", border="#000000", lw=1.2, title_size=8.5, sub_size=6.8)

    # TIER 3
    y_t3 = 0.310
    draw_card(ax, tier_x, y_t3, tier_w, tier_h, "TIER 3: CORE ANALYTICAL & PROCESSING ENGINE LAYER (Pandas / NumPy / Scikit-Learn / FLAML / Gemini)", bg="#ffffff", border="#000000", lw=2, title_size=10.5, align="top-left")
    t3_cards = [
        ("Ingestion & Validation", "Format & MIME Sniffer (Pandas/DuckDB)\nAutomatic Schema & Delimiter Detect\nNull % & Ingestion Health Summary", 0.055, 0.165),
        ("Cleaning & Preprocessing", "PyJanitor Column Sanitization\nMedian/Mode Imputation, Tukey IQR\nSHA-256 Snapshot Lineage Manifest", 0.235, 0.165),
        ("EDA & Statistical Engine", "14 Heuristic Insight Scanners\nBenjamini-Hochberg FDR Control\nPearson Correlation & OLS Trends", 0.415, 0.165),
        ("AI Analytics & Multi-Agent", "Supervisor Agent Intent Routing\nPython AST Code Execution Sandbox\nNumerical Grounding Validation", 0.595, 0.170),
        ("AutoML & Report Synthesizer", "FLAML Model Search (LightGBM/XGB)\nSHAP Feature Attribution Analysis\nARIMA / WeasyPrint HTML-to-PDF", 0.780, 0.165),
    ]
    for title, sub, mx, mw in t3_cards:
        draw_card(ax, mx, y_t3 + 0.016, mw, child_h, title, sub, bg="#ffffff", border="#000000", lw=1.2, title_size=8.5, sub_size=6.8)

    # TIER 4
    y_t4 = 0.085
    draw_card(ax, tier_x, y_t4, tier_w, tier_h, "TIER 4: DATA PERSISTENCE & EXTERNAL INTEGRATIONS LAYER", bg="#ffffff", border="#000000", lw=2, title_size=10.5, align="top-left")
    t4_cards = [
        ("Relational Database", "PostgreSQL (via Supabase)\nUsers, Workspaces, Teams, Quotas\nStored Procedures & Execution Logs", 0.055, 0.205),
        ("Cloud Object Storage", "Supabase Storage Bucket & Local Cache\nRaw CSV/XLSX & Clean Parquet Files\nModel Weights & Serialized Artifacts", 0.280, 0.205),
        ("External AI & Auth APIs", "Google OAuth 2.0 Identity Server\nGoogle Gemini AI API (GenAI SDK)\nAutomated Code & Narrative Gen", 0.505, 0.215),
        ("External Data Connectors", "Google Sheets API & MS 365 OneDrive\nDuckDB, MySQL, SQLite, PostgreSQL\nResend Email & Webhook Delivery", 0.740, 0.205),
    ]
    for title, sub, mx, mw in t4_cards:
        draw_card(ax, mx, y_t4 + 0.016, mw, child_h, title, sub, bg="#ffffff", border="#000000", lw=1.2, title_size=8.5, sub_size=6.8)

    # Inter-tier arrows
    draw_arrow(ax, 0.22, y_t1, 0.22, y_t2 + tier_h, label="HTTPS / REST API Requests", lw=1.6, style="<->", label_size=7.2)
    draw_arrow(ax, 0.78, y_t2 + tier_h, 0.78, y_t1, label="WebSocket Real-Time Stream (WSS)", lw=1.6, style="->", label_size=7.2)

    draw_arrow(ax, 0.22, y_t2, 0.22, y_t3 + tier_h, label="Service Dispatch & Job Payload", lw=1.6, style="->", label_size=7.2)
    draw_arrow(ax, 0.78, y_t3 + tier_h, 0.78, y_t2, label="Computed Findings, Models & PDF Reports", lw=1.6, style="->", label_size=7.2)

    draw_arrow(ax, 0.22, y_t3, 0.22, y_t4 + tier_h, label="Read / Write Parquet & SQL Records", lw=1.6, style="<->", label_size=7.2)
    draw_arrow(ax, 0.78, y_t3, 0.78, y_t4 + tier_h, label="Gemini AI Prompts & Data Ingestion Streams", lw=1.6, style="<->", label_size=7.2)

    ax.text(0.5, 0.028, "DataForge Academic Report - Figure 3.1", ha="center", va="center", fontsize=9, fontweight="bold", color=C_BLACK)

    out_png = OUT_DIR / "figure_3_1_dataforge_system_architecture.png"
    out_svg = OUT_DIR / "figure_3_1_dataforge_system_architecture.svg"
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.savefig(out_svg, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated {out_png}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Figure 3.2: Context Diagram (Level 0 DFD)
# ══════════════════════════════════════════════════════════════════════════════
def generate_figure_3_2_context_dfd():
    fig, ax = plt.subplots(figsize=(13.5, 10.5), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.970, "Figure 3.2: Context Diagram (Level 0 DFD)", ha="center", va="center", fontsize=15, fontweight="bold", color=C_BLACK)
    ax.text(0.5, 0.946, "DataForge System Boundary, External Entities, and High-Level Environmental Data Flows", ha="center", va="center", fontsize=9.5, style="italic", color=C_BLACK)

    # Central Process 0.0
    cx, cy, cw, ch = 0.36, 0.44, 0.28, 0.16
    c_box = FancyBboxPatch((cx, cy), cw, ch, boxstyle="round,pad=0,rounding_size=0.03", facecolor="#ffffff", edgecolor="#000000", linewidth=2.5, zorder=3)
    ax.add_patch(c_box)
    c_box_inner = FancyBboxPatch((cx + 0.006, cy + 0.006), cw - 0.012, ch - 0.012, boxstyle="round,pad=0,rounding_size=0.024", facecolor="#ffffff", edgecolor="#000000", linewidth=0.8, zorder=3)
    ax.add_patch(c_box_inner)

    mid_x = cx + cw / 2
    ax.text(mid_x, cy + ch * 0.72, "0.0", ha="center", va="center", fontsize=12, fontweight="bold", color=C_BLACK, zorder=4)
    ax.text(mid_x, cy + ch * 0.50, "DATAFORGE SYSTEM", ha="center", va="center", fontsize=11, fontweight="bold", color=C_BLACK, zorder=4)
    ax.text(mid_x, cy + ch * 0.26, "(Automated Data Engineering, Profiling,\nAI Analytics, AutoML & Reporting Platform)", ha="center", va="center", fontsize=7.2, color=C_BLACK, zorder=4)

    # 6 External Entities
    ew, eh = 0.24, 0.11

    # E1: Top-Left
    e1_x, e1_y = 0.05, 0.76
    draw_entity(ax, e1_x, e1_y, ew, eh, "EXTERNAL ENTITY: E1\nEnd User / Data Analyst", "Browser Client (Next.js 15)\nInteracts with DataForge Workspace")

    # E2: Top-Right
    e2_x, e2_y = 0.71, 0.76
    draw_entity(ax, e2_x, e2_y, ew, eh, "EXTERNAL ENTITY: E2\nExternal Data Providers", "Google Sheets, Microsoft 365,\nRemote SQL Databases (Postgres, DuckDB)")

    # E3: Bottom-Left
    e3_x, e3_y = 0.05, 0.08
    draw_entity(ax, e3_x, e3_y, ew, eh, "EXTERNAL ENTITY: E3\nGoogle OAuth 2.0", "Third-Party Identity Provider\nToken Verification & User Profile Claims")

    # E4: Bottom-Right
    e4_x, e4_y = 0.71, 0.08
    draw_entity(ax, e4_x, e4_y, ew, eh, "EXTERNAL ENTITY: E4\nGoogle Gemini AI SDK", "Generative AI Language & Code Engine\nPrompt Evaluation & AST Code Gen")

    # E5: Bottom-Center
    e5_x, e5_y = 0.38, 0.08
    draw_entity(ax, e5_x, e5_y, ew, eh, "EXTERNAL ENTITY: E5\nSupabase Cloud Platform", "PostgreSQL Database & Object Storage\nWorkspaces, Parquet Snapshots & Models")

    # E6: Middle-Right
    e6_x, e6_y = 0.71, 0.46
    draw_entity(ax, e6_x, e6_y, ew, eh, "EXTERNAL ENTITY: E6\nCommunication Services", "Resend Email & Webhook Dispatchers\nWorkspace Invites & Drift Alert Delivery")

    # ──────────────────────────────────────────────────────────────────────────
    # Flows - Positioned cleanly without overlaps
    # ──────────────────────────────────────────────────────────────────────────
    # E1 <-> 0.0
    draw_arrow(ax, e1_x + ew, e1_y + eh * 0.70, cx, cy + ch * 0.85, 
               label="1. Upload Files (CSV/XLSX), Cleaning Rules,\nNL Queries, AutoML Target Selections", 
               rad=-0.08, label_size=6.7, label_pos=0.45)
    draw_arrow(ax, cx, cy + ch * 0.45, e1_x + ew, e1_y + eh * 0.20, 
               label="2. Ingestion Health Previews, Interactive Charts,\nAI Narratives, Model Metrics & PDF Reports", 
               rad=0.08, label_size=6.7, label_pos=0.55)

    # 0.0 <-> E2
    draw_arrow(ax, cx + cw, cy + ch * 0.85, e2_x, e2_y + eh * 0.25, 
               label="3. API Credentials, Sheet Tokens & SQL Queries", 
               rad=-0.06, label_size=6.7, label_pos=0.5)
    draw_arrow(ax, e2_x, e2_y + eh * 0.70, cx + cw * 0.85, cy + ch, 
               label="4. Stream Remote Datasets & Sheet Cell Values", 
               rad=-0.06, label_size=6.7, label_pos=0.5)

    # E3 <-> 0.0
    draw_arrow(ax, cx * 0.95, cy + ch * 0.25, e3_x + ew * 0.75, e3_y + eh, 
               label="5. Auth Code & Token Exchange", 
               rad=-0.05, label_size=6.7, label_pos=0.45, label_offset=(-0.02, 0.02))
    draw_arrow(ax, e3_x + ew, e3_y + eh * 0.70, cx, cy + ch * 0.10, 
               label="6. User Identity Claims (sub, email, name)", 
               rad=0.08, label_size=6.7, label_pos=0.55, label_offset=(-0.02, -0.02))

    # 0.0 <-> E4
    draw_arrow(ax, cx + cw, cy + ch * 0.18, e4_x, e4_y + eh * 0.85, 
               label="7. Prompt Context: Schema, Stats & Query", 
               rad=-0.05, label_size=6.7, label_pos=0.45, label_offset=(0.02, 0.03))
    draw_arrow(ax, e4_x, e4_y + eh * 0.40, cx + cw * 0.90, cy, 
               label="8. Narrative Summaries & Python Code", 
               rad=0.06, label_size=6.7, label_pos=0.55, label_offset=(0.02, -0.02))

    # 0.0 <-> E5
    draw_arrow(ax, mid_x - 0.04, cy, mid_x - 0.04, e5_y + eh, 
               label="9. Store Snapshots, Models & Logs", 
               rad=0.0, label_size=6.7, label_pos=0.5, label_offset=(-0.11, 0))
    draw_arrow(ax, mid_x + 0.04, e5_y + eh, mid_x + 0.04, cy, 
               label="10. Retrieve Workspaces & Quotas", 
               rad=0.0, label_size=6.7, label_pos=0.5, label_offset=(0.11, 0))

    # 0.0 <-> E6
    draw_arrow(ax, cx + cw, cy + ch * 0.58, e6_x, e6_y + eh * 0.65, 
               label="11. Drift Alerts & Scheduled Reports", 
               rad=-0.04, label_size=6.7, label_pos=0.5)
    draw_arrow(ax, e6_x, e6_y + eh * 0.30, cx + cw, cy + ch * 0.38, 
               label="12. Delivery Acknowledgments", 
               rad=0.04, label_size=6.7, label_pos=0.5)

    ax.text(0.5, 0.026, "DataForge Academic Report - Figure 3.2", ha="center", va="center", fontsize=9, fontweight="bold", color=C_BLACK)

    out_png = OUT_DIR / "figure_3_2_context_diagram_level_0_dfd.png"
    out_svg = OUT_DIR / "figure_3_2_context_diagram_level_0_dfd.svg"
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.savefig(out_svg, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated {out_png}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Figure 3.3: DataForge Level 1 Data Flow Diagram (DFD)
# ══════════════════════════════════════════════════════════════════════════════
def generate_figure_3_3_level_1_dfd():
    fig, ax = plt.subplots(figsize=(16, 15), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.980, "Figure 3.3: DataForge Level 1 Data Flow Diagram (DFD)", ha="center", va="center", fontsize=15, fontweight="bold", color=C_BLACK)
    ax.text(0.5, 0.960, "Internal Subprocesses, Data Stores, and Comprehensive Inter-Module Information Flows", ha="center", va="center", fontsize=9.5, style="italic", color=C_BLACK)

    pr = 0.042  # process circle radius

    # ── External Entities ──────────────────────────────────────────────────────
    ew, eh = 0.20, 0.065
    draw_entity(ax, 0.03, 0.88, ew, eh, "E1: User / Data Analyst", "Browser Client (Next.js 15)")
    draw_entity(ax, 0.77, 0.88, ew, eh, "E2: External Data Providers", "Google Sheets, OneDrive, DBs")
    draw_entity(ax, 0.03, 0.72, ew, eh, "E3: Google OAuth 2.0", "Identity & Claims Authority")
    draw_entity(ax, 0.77, 0.52, ew, eh, "E4: Google Gemini AI SDK", "Generative Analytical Engine")
    draw_entity(ax, 0.40, 0.05, 0.20, 0.058, "E5: Supabase Cloud Platform", "PostgreSQL & S3 Storage Bucket")
    draw_entity(ax, 0.77, 0.22, ew, eh, "E6: Communication Services", "Resend Email & Webhooks")

    # ── Subprocesses P1.0 to P7.0 ──────────────────────────────────────────────
    # Row 1 (top): P1.0 and P2.0
    p1_x, p1_y = 0.36, 0.89
    p2_x, p2_y = 0.60, 0.89
    draw_process_node(ax, p1_x, p1_y, pr, "P1.0", "User Sign-In &", "Session Auth")
    draw_process_node(ax, p2_x, p2_y, pr, "P2.0", "Data Ingestion &", "Profiling Check")

    # Row 2 (cleaning): P3.0
    p3_x, p3_y = 0.50, 0.73
    draw_process_node(ax, p3_x, p3_y, pr, "P3.0", "Data Cleaning &", "Transformation")

    # Row 3 (analysis & AI): P4.0 and P5.0
    p4_x, p4_y = 0.26, 0.54
    p5_x, p5_y = 0.52, 0.54
    draw_process_node(ax, p4_x, p4_y, pr, "P4.0", "Statistical Profiling", "& Visualisation")
    draw_process_node(ax, p5_x, p5_y, pr, "P5.0", "AI Analytics &", "Query Module")

    # Row 4 (ML & Reports): P6.0 and P7.0
    p6_x, p6_y = 0.26, 0.34
    p7_x, p7_y = 0.52, 0.34
    draw_process_node(ax, p6_x, p6_y, pr, "P6.0", "Automated ML &", "Forecasting")
    draw_process_node(ax, p7_x, p7_y, pr, "P7.0", "Report Generation", "& Delivery")

    # ── Internal Data Stores D1 to D6 ─────────────────────────────────────────
    dw, dh = 0.21, 0.040
    # D1: Users & Quotas
    d1_x, d1_y = 0.03, 0.80
    draw_datastore(ax, d1_x, d1_y, dw, dh, "D1", "Users & Quota Store", "Roles & Permission Rules")

    # D2: Raw Tables
    d2_x, d2_y = 0.76, 0.79
    draw_datastore(ax, d2_x, d2_y, dw, dh, "D2", "Raw Datasets & Tables", "Staged Raw Files & Schemas")

    # D3: Cleaned Snapshots
    d3_x, d3_y = 0.76, 0.65
    draw_datastore(ax, d3_x, d3_y, dw, dh, "D3", "Cleaned Parquet Snapshots", "Lineage Manifest & Clean DF")

    # D4: Analytical Baselines
    d4_x, d4_y = 0.03, 0.44
    draw_datastore(ax, d4_x, d4_y, dw, dh, "D4", "Analytical Baselines", "14 Scanners, Outliers & Cache")

    # D5: Model Registry
    d5_x, d5_y = 0.03, 0.24
    draw_datastore(ax, d5_x, d5_y, dw, dh, "D5", "Model Registry (.joblib)", "Trained Weights & SHAP Scores")

    # D6: Audit Logs & Schedules
    d6_x, d6_y = 0.395, 0.18
    draw_datastore(ax, d6_x, d6_y, dw, dh, "D6", "Audit Logs & Schedules", "Activity Logs & Threshold Rules")

    # ──────────────────────────────────────────────────────────────────────────
    # Flows for P1.0 (Auth)
    # ──────────────────────────────────────────────────────────────────────────
    draw_arrow(ax, 0.23, 0.90, p1_x - pr, 0.90, label="1. Login Request", lw=1.3, label_size=6.3)
    draw_arrow(ax, 0.23, 0.75, p1_x - pr * 0.7, 0.86, label="2. OAuth Claims", lw=1.3, label_size=6.3)
    draw_arrow(ax, p1_x - pr * 0.7, 0.85, d1_x + dw, d1_y + dh * 0.7, label="3. Sync User Record", lw=1.2, label_size=6.0)
    draw_arrow(ax, d1_x + dw, d1_y + dh * 0.3, p1_x - 0.02, 0.85, label="4. Read Quotas", lw=1.2, label_size=6.0, dashed=True)
    draw_arrow(ax, p1_x - 0.01, 0.93, 0.23, 0.93, label="5. JWT Session Cookie", lw=1.3, label_size=6.3, rad=-0.04)

    # ──────────────────────────────────────────────────────────────────────────
    # Flows for P2.0 (Ingestion)
    # ──────────────────────────────────────────────────────────────────────────
    draw_arrow(ax, 0.23, 0.88, p2_x - pr, 0.88, label="6. Upload File (CSV/Excel)", lw=1.3, label_size=6.3, rad=0.05, label_pos=0.4)
    draw_arrow(ax, 0.77, 0.90, p2_x + pr, 0.90, label="7. Stream Remote Cells", lw=1.3, label_size=6.3)
    draw_arrow(ax, p2_x + pr * 0.7, 0.86, d2_x, d2_y + dh * 0.6, label="8. Stage Raw Data Table", lw=1.3, label_size=6.2)
    draw_arrow(ax, p2_x, 0.94, 0.16, 0.945, label="9. Ingestion Health Card Preview", lw=1.3, label_size=6.3, rad=-0.06)

    # ──────────────────────────────────────────────────────────────────────────
    # Flows for P3.0 (Cleaning)
    # ──────────────────────────────────────────────────────────────────────────
    draw_arrow(ax, 0.20, 0.88, p3_x - 0.04, p3_y + pr, label="10. Cleaning Rules & Join Keys", lw=1.3, label_size=6.2, rad=0.06)
    draw_arrow(ax, d2_x, d2_y + dh * 0.2, p3_x + pr, p3_y + 0.02, label="11. Read Raw Staged Data", lw=1.3, label_size=6.2)
    draw_arrow(ax, p3_x + pr, p3_y - 0.01, d3_x, d3_y + dh * 0.7, label="12. Persist Clean Snapshot & Lineage", lw=1.3, label_size=6.2)
    draw_arrow(ax, p3_x - pr, p3_y + 0.01, 0.14, 0.88, label="13. Transformation Diff Card", lw=1.3, label_size=6.2, rad=-0.08)

    # ──────────────────────────────────────────────────────────────────────────
    # Flows for P4.0 (Statistical Profiling)
    # ──────────────────────────────────────────────────────────────────────────
    draw_arrow(ax, d3_x, d3_y + dh * 0.3, p4_x + pr * 0.8, p4_y + pr * 0.8, label="14. Stream Clean DF", lw=1.3, label_size=6.2, rad=0.08)
    draw_arrow(ax, p4_x - pr, p4_y - 0.01, d4_x + dw, d4_y + dh * 0.7, label="15. Cache Baseline Stats", lw=1.3, label_size=6.0)
    draw_arrow(ax, p4_x - pr * 0.7, p4_y + pr * 0.7, 0.08, 0.88, label="16. Statistical Summaries & Charts", lw=1.3, label_size=6.2, rad=-0.12)

    # ──────────────────────────────────────────────────────────────────────────
    # Flows for P5.0 (AI Analytics)
    # ──────────────────────────────────────────────────────────────────────────
    draw_arrow(ax, 0.22, 0.88, p5_x - 0.02, p5_y + pr, label="17. Natural Language Query", lw=1.3, label_size=6.2, rad=0.08)
    draw_arrow(ax, d3_x, d3_y, p5_x + pr * 0.7, p5_y + pr * 0.7, label="18. Schema & Column Stats", lw=1.2, label_size=6.0)
    draw_arrow(ax, p5_x + pr, p5_y, 0.77, 0.54, label="19. Prompt Envelope & Context", lw=1.3, label_size=6.2)
    draw_arrow(ax, 0.77, 0.51, p5_x + pr, p5_y - 0.02, label="20. AI Narrative & AST Code", lw=1.3, label_size=6.2)
    draw_arrow(ax, p5_x - pr, p5_y + 0.02, 0.12, 0.88, label="21. Grounded Answers & Visuals", lw=1.3, label_size=6.2, rad=-0.10)

    # ──────────────────────────────────────────────────────────────────────────
    # Flows for P6.0 (AutoML)
    # ──────────────────────────────────────────────────────────────────────────
    draw_arrow(ax, 0.22, 0.88, p6_x, p6_y + pr, label="22. Target Variable & Metric", lw=1.3, label_size=6.2, rad=0.12, label_pos=0.6)
    draw_arrow(ax, d3_x, d3_y - 0.01, p6_x + pr, p6_y + 0.02, label="23. Features Matrix", lw=1.3, label_size=6.0, rad=0.14)
    draw_arrow(ax, p6_x - pr, p6_y - 0.01, d5_x + dw, d5_y + dh * 0.7, label="24. Save Model & SHAP", lw=1.3, label_size=6.0)
    draw_arrow(ax, p6_x - pr * 0.8, p6_y + pr * 0.6, 0.05, 0.88, label="25. Leaderboard & Predictions", lw=1.3, label_size=6.2, rad=-0.15)

    # ──────────────────────────────────────────────────────────────────────────
    # Flows for P7.0 (Reports & Alerts)
    # ──────────────────────────────────────────────────────────────────────────
    draw_arrow(ax, d4_x + dw, d4_y + dh * 0.2, p7_x - pr * 0.7, p7_y + pr * 0.7, label="26. Read Insight Baselines", lw=1.3, label_size=6.0)
    draw_arrow(ax, p6_x + pr, p6_y, p7_x - pr, p7_y, label="27. Evaluation Metrics", lw=1.3, label_size=6.2)
    draw_arrow(ax, d6_x + dw * 0.5, d6_y + dh, p7_x, p7_y - pr, label="28. Alert Threshold Rules", lw=1.2, label_size=6.0)
    draw_arrow(ax, p7_x - pr * 0.8, p7_y + pr * 0.8, 0.18, 0.88, label="29. Download Executive PDF", lw=1.3, label_size=6.2, rad=-0.14)
    draw_arrow(ax, p7_x + pr, p7_y - 0.01, 0.77, 0.24, label="30. Send Drift Alerts", lw=1.3, label_size=6.2)

    # ── Cloud Backup & Audit Logging ───────────────────────────────────────────
    draw_arrow(ax, d3_x + dw * 0.5, d3_y, 0.60, 0.08, label="31. Cloud Parquet Mirror", lw=1.2, label_size=6.0, rad=0.08)
    draw_arrow(ax, d5_x + dw * 0.8, d5_y, 0.40, 0.08, label="32. Register Model Binaries", lw=1.2, label_size=6.0, rad=-0.08)

    draw_arrow(ax, p1_x, p1_y - pr, d6_x + 0.02, d6_y + dh, label="33. Auth Audit Event", lw=1.1, label_size=5.8, dashed=True)
    draw_arrow(ax, p3_x, p3_y - pr, d6_x + dw * 0.4, d6_y + dh, label="34. Cleaning Log", lw=1.1, label_size=5.8, dashed=True)

    ax.text(0.5, 0.022, "DataForge Academic Report - Figure 3.3", ha="center", va="center", fontsize=9, fontweight="bold", color=C_BLACK)

    out_png = OUT_DIR / "figure_3_3_dataforge_level_1_data_flow_diagram.png"
    out_svg = OUT_DIR / "figure_3_3_dataforge_level_1_data_flow_diagram.svg"
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.savefig(out_svg, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated {out_png}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. Figure 3.4: Overall Process Flow
# ══════════════════════════════════════════════════════════════════════════════
def generate_figure_3_4_overall_process_flow():
    fig, ax = plt.subplots(figsize=(11, 16), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.980, "Overall Process Flow of DataForge", ha="center", va="center", fontsize=15, fontweight="bold", color=C_BLACK)
    ax.text(0.5, 0.962, "Complete Operational Sequence Corresponding to Section 3.4 (Steps 1 through 8)", ha="center", va="center", fontsize=9.5, style="italic", color=C_BLACK)

    w = 0.64
    cx = 0.5 - w / 2

    def draw_terminal(ax, x, y, tw, th, text):
        box = FancyBboxPatch((x, y), tw, th, boxstyle=f"round,pad=0,rounding_size={th/2}", facecolor="#ffffff", edgecolor="#000000", linewidth=2.0, zorder=3)
        ax.add_patch(box)
        box_in = FancyBboxPatch((x + 0.005, y + 0.005), tw - 0.010, th - 0.010, boxstyle=f"round,pad=0,rounding_size={(th-0.01)/2}", facecolor="#ffffff", edgecolor="#000000", linewidth=0.8, zorder=3)
        ax.add_patch(box_in)
        ax.text(x + tw/2, y + th/2, text, ha="center", va="center", fontsize=10, fontweight="bold", color=C_BLACK, zorder=4)

    # START Terminal
    term_w, term_h = 0.40, 0.032
    draw_terminal(ax, 0.5 - term_w/2, 0.915, term_w, term_h, "● START: User Accesses DataForge")

    card_h = 0.060
    
    # Step 1
    y1 = 0.825
    draw_card(ax, cx, y1, w, card_h, "Step 1: User Access and Dataset Selection", 
              "• Google OAuth 2.0 PKCE authentication with JWT session management\n• Load user workspace and evaluate role permissions (Owner, Admin, Analyst, Viewer)\n• Upload local dataset (CSV, Excel, Parquet, JSON) or connect Google Sheets / DB", 
              bg="#ffffff", border="#000000", lw=1.8, title_size=9.5, sub_size=7.2, align="top-left")
    draw_arrow(ax, 0.5, 0.915, 0.5, y1 + card_h, lw=1.6)

    # Step 2
    y2 = 0.735
    draw_card(ax, cx, y2, w, card_h, "Step 2: Data Ingestion and Validation", 
              "• FastAPI backend route validates input payload, MIME type, and structure\n• Automatic delimiter detection and schema inference (Pandas & DuckDB sniffer)\n• Generate Ingestion Health Card (Null percentage, column types, memory footprint)", 
              bg="#ffffff", border="#000000", lw=1.8, title_size=9.5, sub_size=7.2, align="top-left")
    draw_arrow(ax, 0.5, y1, 0.5, y2 + card_h, label="Raw Input File", lw=1.6, label_size=7.0)

    # Step 3
    y3 = 0.645
    draw_card(ax, cx, y3, w, card_h, "Step 3: Data Cleaning and Preprocessing", 
              "• Standardise column names (snake_case conversion, whitespace stripping)\n• Handle missing values: median-based imputation (numerical) & mode-based (categorical)\n• Apply Tukey IQR outlier capping boundaries; preview changes; create SHA-256 snapshot", 
              bg="#ffffff", border="#000000", lw=1.8, title_size=9.5, sub_size=7.2, align="top-left")
    draw_arrow(ax, 0.5, y2, 0.5, y3 + card_h, label="Validated Schema", lw=1.6, label_size=7.0)

    # Step 4
    y4 = 0.555
    draw_card(ax, cx, y4, w, card_h, "Step 4: Statistical Profiling and Exploratory Analysis", 
              "• Execute analytical insight engine with 14 scanner categories (trends, correlations, anomalies)\n• Benjamini-Hochberg FDR control for multiple-hypothesis statistical testing rigor\n• Cache baseline metrics, summary statistics, and generate interactive Chart.js/Plotly plots", 
              bg="#ffffff", border="#000000", lw=1.8, title_size=9.5, sub_size=7.2, align="top-left")
    draw_arrow(ax, 0.5, y3, 0.5, y4 + card_h, label="Cleaned Snapshot", lw=1.6, label_size=7.0)

    # Step 5
    y5 = 0.465
    draw_card(ax, cx, y5, w, card_h, "Step 5: AI-Assisted Analytical Interaction", 
              "• Supervisor agent evaluates natural language intent and dataset metadata\n• Google Gemini AI SDK processes user query; generates Python AST analytical code\n• Code execution in safe sandbox; grounding validation against computed statistical facts", 
              bg="#ffffff", border="#000000", lw=1.8, title_size=9.5, sub_size=7.2, align="top-left")
    draw_arrow(ax, 0.5, y4, 0.5, y5 + card_h, label="Statistical Facts", lw=1.6, label_size=7.0)

    # Decision Diamond
    dia_cx, dia_cy = 0.5, 0.380
    dia_w, dia_h = 0.46, 0.055
    diamond = Polygon([
        [dia_cx, dia_cy + dia_h / 2],
        [dia_cx + dia_w / 2, dia_cy],
        [dia_cx, dia_cy - dia_h / 2],
        [dia_cx - dia_w / 2, dia_cy]
    ], facecolor="#ffffff", edgecolor="#000000", linewidth=2.0, zorder=3)
    ax.add_patch(diamond)
    ax.text(dia_cx, dia_cy + 0.008, "Predictive Modelling or", ha="center", va="center", fontsize=8.8, fontweight="bold", color=C_BLACK, zorder=4)
    ax.text(dia_cx, dia_cy - 0.010, "Forecasting Required?", ha="center", va="center", fontsize=8.8, fontweight="bold", color=C_BLACK, zorder=4)

    draw_arrow(ax, 0.5, y5, 0.5, dia_cy + dia_h / 2, label="Prepared Dataset", lw=1.6, label_size=7.0)

    # Step 6 (Branch: YES)
    y6 = 0.265
    draw_card(ax, cx, y6, w, card_h, "Step 6: Predictive Modelling and Forecasting (AutoML)", 
              "• Task identification: automatic classification vs regression detection with imbalance check\n• FLAML model search across LightGBM, XGBoost, Random Forest; evaluate ROC-AUC/RMSE\n• SHAP feature attribution explainability; time-series forecasting via ARIMA & Holt-Winters", 
              bg="#ffffff", border="#000000", lw=1.8, title_size=9.5, sub_size=7.2, align="top-left")
    
    draw_arrow(ax, 0.5, dia_cy - dia_h / 2, 0.5, y6 + card_h, label="Yes (Train / Forecast)", lw=1.6, label_size=7.0)

    # No / Skip Arrow around Step 6 directly to Step 7
    ax.plot([dia_cx + dia_w / 2, 0.86, 0.86, 0.80], [dia_cy, dia_cy, 0.175 + card_h / 2, 0.175 + card_h / 2], color="#000000", linewidth=1.5, linestyle="--", zorder=4)
    arrow_skip = FancyArrowPatch((0.82, 0.175 + card_h / 2), (cx + w, 0.175 + card_h / 2), arrowstyle="->", color="#000000", linewidth=1.5, linestyle="--", mutation_scale=12, zorder=4)
    ax.add_patch(arrow_skip)
    bbox_props = dict(boxstyle="square,pad=0.25", fc="#ffffff", ec="#000000", lw=0.8, alpha=1.0)
    ax.text(0.86, dia_cy - 0.05, "No (Exploration Only)", ha="center", va="center", fontsize=7.0, fontweight="bold", bbox=bbox_props, zorder=5)

    # Step 7
    y7 = 0.175
    draw_card(ax, cx, y7, w, card_h, "Step 7: Visualisation and Report Generation", 
              "• Dashboard presents statistical summaries, distributions, comparisons, and predictive charts\n• Synthesize dataset findings, visual plots, and grounded AI narratives into executive report\n• Convert prepared report to publication-grade PDF via WeasyPrint; export SVG/Parquet", 
              bg="#ffffff", border="#000000", lw=1.8, title_size=9.5, sub_size=7.2, align="top-left")
    draw_arrow(ax, 0.5, y6, 0.5, y7 + card_h, label="Model Metrics & Artifacts", lw=1.6, label_size=7.0)

    # Step 8
    y8 = 0.085
    draw_card(ax, cx, y8, w, card_h, "Step 8: Dataset History and Result Management", 
              "• Maintain content-addressed snapshots using SHA-256 hashes for restoration & audit\n• Optimistic concurrency control using HTTP ETags to prevent silent concurrent overwrites\n• Store models in Model Registry; dispatch alert notifications via email/webhooks", 
              bg="#ffffff", border="#000000", lw=1.8, title_size=9.5, sub_size=7.2, align="top-left")
    draw_arrow(ax, 0.5, y7, 0.5, y8 + card_h, label="Report Document", lw=1.6, label_size=7.0)

    # END Terminal
    draw_terminal(ax, 0.5 - term_w/2, 0.025, term_w, term_h, "■ END: Insights Delivered & Deployed")
    draw_arrow(ax, 0.5, y8, 0.5, 0.025 + term_h, lw=1.6)

    ax.text(0.5, 0.010, "DataForge Academic Report - Section 3.4 Operational Flow", ha="center", va="center", fontsize=9, fontweight="bold", color=C_BLACK)

    out_png = OUT_DIR / "figure_3_4_overall_process_flow.png"
    out_svg = OUT_DIR / "figure_3_4_overall_process_flow.svg"
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.savefig(out_svg, bbox_inches="tight")
    plt.close()
    print(f"[OK] Generated {out_png}")


if __name__ == "__main__":
    generate_figure_3_1_architecture()
    generate_figure_3_2_context_dfd()
    generate_figure_3_3_level_1_dfd()
    generate_figure_3_4_overall_process_flow()
    print("\nAll 4 Black-and-White publication diagrams successfully generated in /home/fab/DataForge_v3/fin_pics/")
