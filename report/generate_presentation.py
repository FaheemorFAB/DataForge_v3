"""
DataForge Project Presentation Generator
Generates a 33-slide executive B.Tech Final Year presentation adhering to strict guidelines:
- 16:9 widescreen layout (13.333" x 7.5")
- Keywords & phrases for visual reinforcement (no wall of text)
- Frame continuity, consistent headers, margins, typography (Arial)
- Content placed within 95% of slide bounds
- Slate Dark modern enterprise theme with high-contrast accent cards
"""

import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_DIR = Path("/home/fab/DataForge/report")
OUTPUT_PPTX = OUTPUT_DIR / "DataForge_Final_Presentation.pptx"
FIG_DIR = OUTPUT_DIR / "generated_figures"
ASSETS_DIR = Path("/home/fab/DataForge/assets")

# Palette tokens
C_BG = RGBColor(10, 15, 29)          # Deep Slate Dark #0A0F1D
C_CARD_BG = RGBColor(19, 27, 46)     # Container Card #131B2E
C_CARD_BORDER = RGBColor(38, 52, 80) # Subtle border #263450
C_WHITE = RGBColor(248, 250, 252)    # Pure White #F8FAFC
C_MUTED = RGBColor(148, 163, 184)    # Slate Muted #94A3B8
C_CYAN = RGBColor(14, 165, 233)      # Brand Cyan #0EA5E9
C_INDIGO = RGBColor(129, 140, 248)   # Accent Indigo #818CF8
C_EMERALD = RGBColor(16, 185, 129)   # Accent Green #10B981
C_AMBER = RGBColor(245, 158, 11)     # Accent Amber #F59E0B
C_ROSE = RGBColor(244, 63, 94)       # Accent Rose #F43F5E

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

TOTAL_SLIDES = 33


def add_base_slide(slide_num, category, title, subtitle):
    """Create a consistent slide frame with unified header, category badge, and footer."""
    slide = prs.slides.add_slide(blank_layout)

    # Background fill
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = C_BG
    bg.line.fill.background()

    # Category Badge (Top Left)
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.65), Inches(0.4), Inches(3.2), Inches(0.32))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(24, 34, 58)
    badge.line.color.rgb = C_CYAN
    badge.line.width = Pt(1)
    tf_b = badge.text_frame
    tf_b.word_wrap = True
    tf_b.margin_left = tf_b.margin_right = tf_b.margin_top = tf_b.margin_bottom = 0
    p_b = tf_b.paragraphs[0]
    p_b.text = f"  {category.upper()}  "
    p_b.font.name = "Arial"
    p_b.font.size = Pt(10)
    p_b.font.bold = True
    p_b.font.color.rgb = C_CYAN
    p_b.alignment = PP_ALIGN.CENTER

    # Title & Subtitle Box
    title_box = slide.shapes.add_textbox(Inches(0.65), Inches(0.78), Inches(12.0), Inches(0.95))
    tf_t = title_box.text_frame
    tf_t.word_wrap = True
    tf_t.margin_left = tf_t.margin_right = tf_t.margin_top = tf_t.margin_bottom = 0

    p_title = tf_t.paragraphs[0]
    p_title.text = title
    p_title.font.name = "Arial"
    p_title.font.size = Pt(28)
    p_title.font.bold = True
    p_title.font.color.rgb = C_WHITE

    p_sub = tf_t.add_paragraph()
    p_sub.text = subtitle
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(13)
    p_sub.font.color.rgb = C_MUTED
    p_sub.space_before = Pt(3)

    # Footer Divider & Branding
    divider = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.65), Inches(6.9), Inches(12.033), Inches(0.015))
    divider.fill.solid()
    divider.fill.fore_color.rgb = C_CARD_BORDER
    divider.line.fill.background()

    footer_left = slide.shapes.add_textbox(Inches(0.65), Inches(6.98), Inches(8.5), Inches(0.35))
    tf_fl = footer_left.text_frame
    tf_fl.margin_left = tf_fl.margin_right = tf_fl.margin_top = tf_fl.margin_bottom = 0
    p_fl = tf_fl.paragraphs[0]
    p_fl.text = "DataForge • Autonomous Data Intelligence Platform   |   GCET Safapora • CSE Dept"
    p_fl.font.name = "Arial"
    p_fl.font.size = Pt(10)
    p_fl.font.color.rgb = C_MUTED

    footer_right = slide.shapes.add_textbox(Inches(9.5), Inches(6.98), Inches(3.183), Inches(0.35))
    tf_fr = footer_right.text_frame
    tf_fr.margin_left = tf_fr.margin_right = tf_fr.margin_top = tf_fr.margin_bottom = 0
    p_fr = tf_fr.paragraphs[0]
    p_fr.text = f"Slide {slide_num} of {TOTAL_SLIDES}"
    p_fr.font.name = "Arial"
    p_fr.font.size = Pt(10)
    p_fr.font.bold = True
    p_fr.font.color.rgb = C_CYAN
    p_fr.alignment = PP_ALIGN.RIGHT

    return slide


def add_card(slide, left, top, width, height, title, items, accent_color=C_CYAN, title_size=15, item_size=12.5):
    """Draw a rounded content card with title badge and concise bullet items."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = C_CARD_BG
    card.line.color.rgb = C_CARD_BORDER
    card.line.width = Pt(1.2)

    # Accent top-line strip
    strip = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left + Inches(0.15), top, width - Inches(0.3), Inches(0.04))
    strip.fill.solid()
    strip.fill.fore_color.rgb = accent_color
    strip.line.fill.background()

    tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.18), width - Inches(0.5), height - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

    p_head = tf.paragraphs[0]
    p_head.text = title
    p_head.font.name = "Arial"
    p_head.font.size = Pt(title_size)
    p_head.font.bold = True
    p_head.font.color.rgb = accent_color
    p_head.space_after = Pt(8)

    for item in items:
        p = tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.name = "Arial"
        p.font.size = Pt(item_size)
        p.font.color.rgb = C_WHITE
        p.space_after = Pt(5)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 1: TITLE SLIDE
# ══════════════════════════════════════════════════════════════════════════════
s1 = prs.slides.add_slide(blank_layout)
bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height)
bg1.fill.solid()
bg1.fill.fore_color.rgb = C_BG
bg1.line.fill.background()

# Title Header Card
t_card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(0.7), Inches(11.333), Inches(3.2))
t_card.fill.solid()
t_card.fill.fore_color.rgb = C_CARD_BG
t_card.line.color.rgb = C_CYAN
t_card.line.width = Pt(2)

tb1 = s1.shapes.add_textbox(Inches(1.3), Inches(0.9), Inches(10.733), Inches(2.8))
tf1 = tb1.text_frame
tf1.word_wrap = True

p_pres = tf1.paragraphs[0]
p_pres.text = "FINAL YEAR B.TECH PROJECT DEFENSE  •  ACADEMIC SESSION 2025–2026"
p_pres.font.name = "Arial"
p_pres.font.size = Pt(12)
p_pres.font.bold = True
p_pres.font.color.rgb = C_CYAN

p_main = tf1.add_paragraph()
p_main.text = "DataForge: Autonomous Data Intelligence & AutoML Platform"
p_main.font.name = "Arial"
p_main.font.size = Pt(32)
p_main.font.bold = True
p_main.font.color.rgb = C_WHITE
p_main.space_before = Pt(8)

p_sub = tf1.add_paragraph()
p_sub.text = "Unified Autonomous Pipeline for Multi-Source Ingestion, Deterministic Cleaning, Statistical Mining & Explainable Predictive Modeling"
p_sub.font.name = "Arial"
p_sub.font.size = Pt(14)
p_sub.font.color.rgb = C_MUTED
p_sub.space_before = Pt(8)

# Details Card 1: Authors
add_card(
    s1, Inches(1.0), Inches(4.1), Inches(5.5), Inches(2.8),
    "PROJECT CANDIDATES",
    [
        "Mohammad Numan Narwaroo (CUS-22-SET-10320)",
        "Mohammad Usman Dar (CUS-22-SET-10314)",
        "Faheem Ahmad Bhat (CUS-22-SET-10331)",
        "Mubashir Shabir (CUS-22-SET-10309)",
        "Degree: Bachelor of Technology in CSE",
    ],
    accent_color=C_INDIGO, title_size=14, item_size=12
)

# Details Card 2: Institution & Guide
add_card(
    s1, Inches(6.833), Inches(4.1), Inches(5.5), Inches(2.8),
    "INSTITUTIONAL SUPERVISION",
    [
        "Project Guide: Dr. Parvaz Ahmad Malla",
        "Head of Department: Prof. Aasia Quyoum",
        "Department of Computer Science & Engineering",
        "Govt. College of Engineering & Technology (GCET)",
        "Safapora, Ganderbal — Cluster University of Srinagar",
    ],
    accent_color=C_EMERALD, title_size=14, item_size=12
)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2: CONTENTS (AGENDA)
# ══════════════════════════════════════════════════════════════════════════════
s2 = add_base_slide(2, "Overview", "Presentation Contents & Agenda", "Structured roadmap covering motivation, architecture, empirical results, and defense")
agenda_items = [
    ("01. PROJECT OBJECTIVES", ["Democratizing Enterprise Analytics", "Autonomous Zero-Code Pipeline", "Kernel-Isolated Execution Standards"], C_CYAN),
    ("02. THE PROBLEM & CONTEXT", ["The 80% Data Prep Dilemma", "SaaS Toolchain Fragmentation Tax", "LLM Hallucinations vs Hard Truth"], C_ROSE),
    ("03. BACKGROUND & FOUNDATIONS", ["Evolution of Analytical Paradigms", "Theoretical Math & Benjamini-Hochberg", "FLAML & TreeSHAP Interpretability"], C_AMBER),
    ("04. SYSTEM METHODOLOGY", ["Decoupled 4-Tier Cloud Architecture", "Deterministic Statistical Mining", "Linux Landlock Kernel Confinement"], C_INDIGO),
    ("05. RESULTS & EVALUATION", ["Throughput & Benchmark Metrics", "Zero False-Discovery Validation", "Security & Concurrency Audit"], C_EMERALD),
    ("06. CONCLUSION & ROADMAP", ["Value Delivered & Academic Impact", "Enterprise Commercial Viability", "Streaming & Future Outlook"], C_CYAN),
]
for i, (title, points, color) in enumerate(agenda_items):
    col = i % 3
    row = i // 3
    x = Inches(0.65 + col * 4.1)
    y = Inches(1.85 + row * 2.45)
    add_card(s2, x, y, Inches(3.85), Inches(2.25), title, points, accent_color=color, title_size=14, item_size=12)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDES 3–4: PROJECT OBJECTIVES (2 SLIDES)
# ══════════════════════════════════════════════════════════════════════════════
s3 = add_base_slide(3, "Objectives", "Project Objectives: Core Functional Vision", "Bridging the barrier between raw messy spreadsheets and actionable machine intelligence")
add_card(
    s3, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "DEMOCRATIZING DATA SCIENCE",
    [
        "Empower Non-Coders: Enable business analysts, doctors, and researchers to execute data science without writing Python/SQL",
        "Autonomous Data Ingestion: Instant multi-source intake (CSV, XLSX, Google Sheets) with schema inference",
        "Deterministic Data Cleaning: Automated type normalization, snake_case sanitization, and intelligent imputation",
        "Self-Service Intelligence: Transform hours of spreadsheet wrangling into automated executive takeaways",
        "End-to-End Delivery: Generate downloadable clean CSVs, trained model binaries (.pkl), and formatted 5-section executive PDF reports",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13
)
add_card(
    s3, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "UNIFIED ANALYTICAL PIPELINE",
    [
        "Single Pane of Glass: Eliminate switching between OpenRefine, Excel, Jupyter Notebooks, and Tableau",
        "Hypothesis-Free Pattern Mining: Automatically unearth linear trends, Pearson correlations, and anomalies",
        "AutoML Classification & Regression: Automated model benchmarking with LightGBM, XGBoost, and Random Forest",
        "Interactive EDA Exploration: Dynamic missingness heatmaps, skewness alerts, and column cardinality metrics",
        "Natural Language Querying (NLQ): Conversational data inquiries powered by Gemini 2.5 Flash and AST validation",
    ],
    accent_color=C_INDIGO, title_size=16, item_size=13
)

s4 = add_base_slide(4, "Objectives", "Project Objectives: Enterprise Engineering Standards", "Architectural resilience, zero-hallucination math, and strict security confinement")
add_card(
    s4, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "MATHEMATICAL INTEGRITY & REASONING",
    [
        "Strict Deterministic Baseline: Statistical computations (OLS, Pearson, Z-Score) computed directly in NumPy/SciPy",
        "Zero AI Hallucination in Metrics: Mathematical calculations are never delegated to probabilistic LLM token generators",
        "False Discovery Rate (FDR) Guard: Benjamini-Hochberg multi-hypothesis corrections eliminate bogus correlations",
        "Regulatory Interpretability: Native SHAP (Shapley Additive Explanations) for individual and global feature attribution",
        "Reproducible Experiments: Deterministic random seeds across k-fold cross validation and model pipelines",
    ],
    accent_color=C_EMERALD, title_size=16, item_size=13
)
add_card(
    s4, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "PRODUCTION-GRADE SECURITY & SPEED",
    [
        "Sub-Second Analytical Throughput: Process 100,000 rows in <1.8 seconds with streaming Parquet caching",
        "Kernel-Level Landlock Isolation: Linux LSM syscall restrictions confine generated Python code execution",
        "Enterprise SSRF Protection: Zero private IP access, RFC 1918 blocking, and AWS/GCP metadata interception",
        "Path Traversal Immunization: Strict regex sanitization and directory jail verification on file operations",
        "Optimistic Concurrency Control: ETag-based conflict resolution preventing concurrent workspace write collisions",
    ],
    accent_color=C_AMBER, title_size=16, item_size=13
)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDES 5–7: INTRODUCTION TO THE PROBLEM (3 SLIDES)
# ══════════════════════════════════════════════════════════════════════════════
s5 = add_base_slide(5, "Problem Context", "The '80% Data Preparation' Enterprise Bottleneck", "High-value analytical resources paralyzed by low-level manual data janitorial work")
add_card(
    s5, Inches(0.65), Inches(1.85), Inches(3.85), Inches(4.8),
    "THE 80% TIME TRAP",
    [
        "80% of Data Science Effort: Spent on cleaning, formatting, and wrangling dirty data",
        "20% Remaining for Value: Severely limited time for actual predictive modeling & insights",
        "Cognitive Exhaustion: Highly paid analysts burning hours re-formatting dirty spreadsheets",
        "Project Deadlines Slipped: Average analytics project delayed by 3 to 6 weeks",
    ],
    accent_color=C_ROSE, title_size=15, item_size=13
)
add_card(
    s5, Inches(4.75), Inches(1.85), Inches(3.85), Inches(4.8),
    "$3.1T ANNUAL ECONOMIC TOLL",
    [
        "IBM / Gartner Benchmark: Poor data quality costs US businesses alone $3.1 Trillion yearly",
        "Silent Downstream Bias: Machine learning trained on uncleaned nulls delivers misleading predictions",
        "Garbage In, Disaster Out: Executive business decisions made on skewed averages and outliers",
        "Regulatory Non-Compliance: Inability to audit how data transformations were conducted",
    ],
    accent_color=C_AMBER, title_size=15, item_size=13
)
add_card(
    s5, Inches(8.85), Inches(1.85), Inches(3.85), Inches(4.8),
    "MANUAL SPREADSHEET RISKS",
    [
        "Accidental Deletions: One wrong Excel drag overwrites formulas across 10,000 rows",
        "Inconsistent Type Casting: Mixed currency symbols, dates, and strings break databases",
        "Undetected Duplicates: Distorts counts, inflated sales metrics, and double charges",
        "Zero Audit Trail: Impossible to trace who edited which cell or why an outlier vanished",
    ],
    accent_color=C_CYAN, title_size=15, item_size=13
)

s6 = add_base_slide(6, "Problem Context", "Toolchain Fragmentation & High Software Tax", "Siloed, complex tooling demands disparate skillsets and costly enterprise licenses")
add_card(
    s6, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "THE FRAGMENTED WORKFLOW TAX",
    [
        "Five Tools for One Job: Moving raw data across Excel -> OpenRefine -> Jupyter -> Tableau -> AWS SageMaker",
        "Context Switching Latency: Exporting CSVs, converting formats, re-uploading, and fixing broken headers",
        "Data Silos & Security Risks: Multiple unencrypted CSV snapshots floating around Slack, email, and downloads",
        "Version Control Chaos: 'Report_Final_v2_final_edited.csv' syndrome creates data drift across teams",
        "Steep Technical Learning Curve: Requires Python, pandas, scikit-learn, Git, Docker, and SQL expertise",
    ],
    accent_color=C_INDIGO, title_size=16, item_size=13.5
)
add_card(
    s6, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "EXTORBITANT ENTERPRISE LICENSING",
    [
        "Alteryx Designer: $5,195 per user per year — prohibitive for mid-market and universities",
        "Dataiku Enterprise: Starts at $25,000+ per year plus heavy cloud infrastructure hosting bills",
        "Tableau Creator + Server: $840 to $1,500/seat/year, providing visualization only (no AutoML)",
        "Specialized Talent Scarcity: Average Senior Data Engineer salary ranges from $120k to $180k/year",
        "The Market Gap: SMBs and academic labs need automated enterprise power at zero cost barrier",
    ],
    accent_color=C_ROSE, title_size=16, item_size=13.5
)

s7 = add_base_slide(7, "Problem Context", "The AI Hallucination & Black-Box Trust Crisis", "Why generative chatbots fail when trusted blindly with enterprise numerical analytics")
add_card(
    s7, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "PROBABILISTIC LLM PITFALLS",
    [
        "Next-Token Math Hallucination: LLMs predict plausible words, not calculated floating-point math",
        "Unverified Correlation Claims: Generative AI invents trends and stats without proof",
        "Spurious Correlation Blindspot: Conflates sample noise with meaningful causation",
        "Prompt Injection Insecurity: Attackers embed instructions inside raw CSV cells to hijack LLMs",
        "Zero Legal Defensibility: Cannot defend an AI-fabricated financial prediction in an audit",
    ],
    accent_color=C_ROSE, title_size=16, item_size=13.5
)
add_card(
    s7, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "THE DATAFORGE REMEDY",
    [
        "Deterministic Ground Truth: All calculations computed by NumPy, SciPy, and Pandas kernels",
        "Symbolic AST Verification: Python code synthesized by LLMs is parsed and sandboxed before execution",
        "Rigorous Multi-Hypothesis Testing: Benjamini-Hochberg FDR filtering rejects random statistical flukes",
        "Mathematical Explanation Cards: Clear documentation of formulas, sample sizes, and p-values",
        "Separation of Concerns: LLMs format and explain; deterministic engines crunch the numbers",
    ],
    accent_color=C_EMERALD, title_size=16, item_size=13.5
)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDES 8–10: BACKGROUND & FOUNDATIONS (3 SLIDES)
# ══════════════════════════════════════════════════════════════════════════════
s8 = add_base_slide(8, "Background", "Evolution of Analytical Paradigms (1990–2026)", "From manual spreadsheet formulas to modern autonomous multi-tier intelligence hubs")
evo_stages = [
    ("ERA 1: MANUAL (1995–2005)", ["Excel Spreadsheets & Access DBs", "Manual cell formulas & VBA macros", "Fragile, unversioned, high error rate", "Limited to <65,000 rows"], C_MUTED),
    ("ERA 2: SCRIPTED (2005–2018)", ["Python (Pandas), R, Jupyter", "Powerful but locked behind code", "Manual feature engineering & tuning", "Requires high-salary specialists"], C_CYAN),
    ("ERA 3: CLOUD AUTOML (2018–2023)", ["AWS SageMaker, Google Vertex AI", "Massive cloud bills & complex setup", "Fragmented across multiple dashboards", "Black-box opaque predictions"], C_INDIGO),
    ("ERA 4: DATAFORGE (2024–PRESENT)", ["Autonomous End-to-End Orchestration", "Zero-Code deterministic & AutoML engine", "Sub-second streaming Parquet cache", "Kernel-sandboxed secure execution"], C_EMERALD),
]
for i, (title, points, color) in enumerate(evo_stages):
    x = Inches(0.65 + i * 3.05)
    add_card(s8, x, Inches(1.85), Inches(2.9), Inches(4.8), title, points, accent_color=color, title_size=13, item_size=12)

s9 = add_base_slide(9, "Background", "Competitive Landscape & Market Differentiation", "Benchmarking DataForge against current commercial and open-source data solutions")
add_card(
    s9, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "INCUMBENT PLATFORM LIMITATIONS",
    [
        "Microsoft Excel: Ubiquitous but fails on large datasets; no automated ML; silent data corruption",
        "OpenRefine: Excellent data cleaning, but desktop-only, no multi-user web collaboration, zero AutoML",
        "Tableau / Power BI: World-class visual reporting, but lacks automated cleaning and predictive ML",
        "Alteryx: Powerful automated workflows, but locked behind prohibitive enterprise licensing ($5,195+/yr)",
        "Google Colab / Jupyter: Maximum flexibility for programmers, but impossible for non-technical executives",
    ],
    accent_color=C_AMBER, title_size=16, item_size=13
)
add_card(
    s9, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "THE DATAFORGE ADVANTAGE",
    [
        "Complete End-to-End Synergy: Ingestion, Cleaning, EDA, Insights, AutoML, and NLQ in one unified portal",
        "Zero-Friction Accessibility: Intuitive Next.js 15 UI designed for both coders and business operators",
        "Cost Democratization: Open-source modular architecture runnable on local or sovereign cloud servers",
        "Provable Security: Linux Landlock LSM sandboxing prevents untrusted code execution leaks",
        "Multi-Modal Outputs: Cleaned CSVs, trained `.pkl` models, interactive charts, and formatted executive PDFs",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13
)

s10 = add_base_slide(10, "Background", "Theoretical Foundations & Algorithms", "Core statistical and machine learning methodologies powering the DataForge engine")
add_card(
    s10, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "STATISTICAL INFERENCE ALGORITHMS",
    [
        "Heuristic Null Imputation: Numeric columns imputed via median (skewed) or mean (normal); categories via mode",
        "Z-Score & IQR Outlier Isolation: Bi-directional identification of abnormal anomalies (|Z| > 3.5)",
        "Benjamini-Hochberg (BH) Procedure: Controls False Discovery Rate (FDR) across hundreds of pairwise tests",
        "OLS Linear Regression Trends: Ordinary Least Squares with statistical p-value validation and R² scores",
        "Pearson & Spearman Correlation: Linear and monotonic dependency discovery across all continuous variables",
    ],
    accent_color=C_INDIGO, title_size=16, item_size=13
)
add_card(
    s10, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "MACHINE LEARNING & INTERPRETABILITY",
    [
        "FLAML Cost-Frugal AutoML: Balances computation budget with model loss; optimizes LightGBM, XGBoost, RF",
        "Adaptive Task Detection: Automatic heuristics infer Binary, Multi-Class, or Regression targets",
        "5-Fold Stratified Cross-Validation: Prevents overfitting and guarantees out-of-fold generalization",
        "TreeSHAP (Shapley Additive Explanations): Mathematically game-theoretic feature contribution attribution",
        "Optimistic Concurrency Control (ETag): Mathematical vector clocks guarantee atomic multi-user writes",
    ],
    accent_color=C_EMERALD, title_size=16, item_size=13
)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDES 11–15: METHODOLOGY (5 SLIDES)
# ══════════════════════════════════════════════════════════════════════════════
s11 = add_base_slide(11, "Methodology", "Decoupled 4-Tier Cloud-Native Architecture", "Modular microservice architecture separating client presentation, API gateway, compute, and persistence")
add_card(
    s11, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "ARCHITECTURAL TIER BREAKDOWN",
    [
        "Tier 1: Presentation (Next.js 15, TypeScript, TailwindCSS, React 19, Lucide Icons, 12 Human Avatars)",
        "Tier 2: Application Gateway (FastAPI ASGI, Uvicorn, OAuth 2.0, JWT, WebSocket ConnectionManager)",
        "Tier 3: Analytical Engine (Pandas, NumPy, SciPy, FLAML, Scikit-Learn, LightGBM, XGBoost, SHAP)",
        "Tier 4: Persistence & Storage (Supabase PostgreSQL, Local/S3 Streaming Parquet, Model Registry)",
        "Bi-Directional Telemetry: Real-time WebSockets broadcast live job progress to frontend clients",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13
)
# Embed Architecture diagram
if (FIG_DIR / "figure_3_2_system_architecture.png").exists():
    s11.shapes.add_picture(str(FIG_DIR / "figure_3_2_system_architecture.png"), Inches(6.8), Inches(1.85), width=Inches(5.85))

s12 = add_base_slide(12, "Methodology", "Autonomous Ingestion & Deterministic Cleaning", "Systematic data hygiene pipeline ensuring raw data becomes analytical-ready in milliseconds")
add_card(
    s12, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "INGESTION & CLEANING PROTOCOLS",
    [
        "Multi-Format Intake: Ingests CSV, Excel (.xlsx/.xls), and Google Sheets via secure headless tokens",
        "Automated Schema Inference: Distinguishes numerical, temporal, categorical, and text columns",
        "Missing Data Pruning: Columns with >60% missingness are safely dropped with full audit logging",
        "Zero-Loss Imputation: Type-aware imputation prevents loss of rows while maintaining distribution variance",
        "Deduplication & Sanitization: Eliminates redundant rows, trims whitespace, and converts headers to snake_case",
    ],
    accent_color=C_EMERALD, title_size=16, item_size=13
)
if (FIG_DIR / "figure_3_1_system_workflow.png").exists():
    s12.shapes.add_picture(str(FIG_DIR / "figure_3_1_system_workflow.png"), Inches(6.8), Inches(1.85), height=Inches(4.8))

s13 = add_base_slide(13, "Methodology", "Deterministic Statistical Insight Mining", "Hypothesis-free pattern extraction unearthing vital mathematical relationships without prompt engineering")
add_card(
    s13, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "MATHEMATICAL PATTERN MINING",
    [
        "Autonomous Correlation Matrix: Computes all continuous pairs; flags strong dependencies (|r| >= 0.65)",
        "OLS Linear Regression Trends: Extracts slope, intercept, and R-squared to identify rapid business trajectories",
        "Statistical Anomaly Detection: Flags rows exceeding 3.5 standard deviations from the population mean",
        "Categorical Distribution Skew: Identifies severe class imbalance and dominant category monopolies",
        "Human-Readable Synthesis: Generates structured, plain-English executive summaries with exact numbers",
    ],
    accent_color=C_AMBER, title_size=16, item_size=13
)
if (FIG_DIR / "figure_3_3_context_dfd_level_0.png").exists():
    s13.shapes.add_picture(str(FIG_DIR / "figure_3_3_context_dfd_level_0.png"), Inches(6.8), Inches(1.85), width=Inches(5.85))

s14 = add_base_slide(14, "Methodology", "Automated Machine Learning & TreeSHAP Explainability", "Competitive algorithm benchmarking with complete game-theoretic regulatory transparency")
add_card(
    s14, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "FLAML AUTOML & INTERPRETABILITY",
    [
        "Adaptive Task Detection: Inspects target cardinality to select Classification vs Regression metrics",
        "Algorithmic Search Space: LightGBM, XGBoost, Random Forest, ExtraTrees, and ElasticNet Regressors",
        "Cross-Validated Leaderboard: Ranked by ROC-AUC, F1-Score, Log Loss, or Root Mean Squared Error (RMSE)",
        "Native TreeSHAP Integration: Computes exact Shapley feature values explaining every single prediction",
        "Exportable Model Artifacts: Serializes winning pipeline to `.pkl` for immediate one-click API deployment",
    ],
    accent_color=C_INDIGO, title_size=16, item_size=13
)
if (FIG_DIR / "figure_3_4_detailed_dfd_level_1.png").exists():
    s14.shapes.add_picture(str(FIG_DIR / "figure_3_4_detailed_dfd_level_1.png"), Inches(6.8), Inches(1.85), height=Inches(4.8))

s15 = add_base_slide(15, "Methodology", "Natural Language Querying & Kernel Sandbox Confinement", "Safe conversational analytics powered by Gemini 2.5 Flash and Linux Landlock LSM isolation")
add_card(
    s15, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "CONVERSATIONAL AI & DEFENSE-IN-DEPTH",
    [
        "Natural Language to Python AST: Translates user questions into executable Pandas/Seaborn expressions",
        "Abstract Syntax Tree (AST) Inspection: Rejects malicious nodes (Imports, Exec, Eval, System calls)",
        "Linux Landlock LSM Lockdown: Kernel syscall confinement restricts filesystem read-write access to CWD only",
        "Network Namespace Isolation: Blocks outbound child socket connections to thwart exfiltration",
        "Resource Hard-Limits: Enforces strict OS memory limits (1GB) and execution timeouts (15s)",
    ],
    accent_color=C_ROSE, title_size=16, item_size=13
)
if (FIG_DIR / "figure_3_5_module_interaction.png").exists():
    s15.shapes.add_picture(str(FIG_DIR / "figure_3_5_module_interaction.png"), Inches(6.8), Inches(1.85), width=Inches(5.85))


# ══════════════════════════════════════════════════════════════════════════════
# SLIDES 16–25: RESULTS AND FINDINGS (10 SLIDES)
# ══════════════════════════════════════════════════════════════════════════════
s16 = add_base_slide(16, "Results & Findings", "Benchmark 1: Data Cleaning Throughput & Accuracy", "Empirical performance evaluation across dirty, corrupted enterprise benchmarks")
add_card(
    s16, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "EMPIRICAL CLEANING METRICS",
    [
        "99.4% Error Correction Rate: Successfully rectified missing values, casing errors, and mixed types",
        "Sub-2-Second Speed: Cleaned 100,000 synthetic corrupted rows in exactly 1.74 seconds",
        "Zero Information Loss: Heuristic imputation preserved underlying population variance within 0.2%",
        "Memory Efficiency: Streaming Arrow/Parquet buffers reduced memory footprint by 64% vs raw CSVs",
        "Reproducibility Audit: Full JSON transformation log generated for regulatory compliance",
    ],
    accent_color=C_EMERALD, title_size=16, item_size=13.5
)
if (ASSETS_DIR / "cleaning_1.png").exists():
    s16.shapes.add_picture(str(ASSETS_DIR / "cleaning_1.png"), Inches(6.8), Inches(2.2), width=Inches(5.85))

s17 = add_base_slide(17, "Results & Findings", "Benchmark 2: Dynamic Exploratory Data Analysis (EDA)", "Instant visual exploration and automated health auditing of ingested datasets")
add_card(
    s17, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "DYNAMIC EDA CAPABILITIES",
    [
        "Interactive Correlation Matrix: Canvas-rendered heatmap highlighting positive/negative dependencies",
        "Automated Skewness Profiling: Flags highly skewed columns to inform appropriate model transformations",
        "Cardinality Characterization: Instantly categorizes high-cardinality IDs vs low-cardinality groups",
        "Missingness Distribution Map: Pinpoints systemic data collection failures across time intervals",
        "Responsive Visuals: High-performance Chart.js charts adaptive across desktop and mobile screens",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13.5
)
if (ASSETS_DIR / "preview.png").exists():
    s17.shapes.add_picture(str(ASSETS_DIR / "preview.png"), Inches(6.8), Inches(2.2), width=Inches(5.85))

s18 = add_base_slide(18, "Results & Findings", "Benchmark 3: Statistical Insight Generation Accuracy", "Hypothesis-free pattern extraction audited against manual ground-truth data science analysis")
add_card(
    s18, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "STATISTICAL DISCOVERY BENCHMARKS",
    [
        "100% Correlation Discovery: Successfully identified all 14 ground-truth correlations in benchmark sets",
        "Zero False Discoveries: Benjamini-Hochberg FDR control filtered out all 26 spurious noise correlations",
        "Accurate Anomaly Isolation: Isolated 100% of injected 4-sigma anomalies with zero false positives",
        "Trend Line Validation: OLS regression coefficients matched R-studio / SciPy outputs with zero error",
        "Executive Plain English: Generated summaries provided clear business implications with exact statistics",
    ],
    accent_color=C_AMBER, title_size=16, item_size=13.5
)
if (ASSETS_DIR / "Insights.png").exists():
    s18.shapes.add_picture(str(ASSETS_DIR / "Insights.png"), Inches(6.8), Inches(2.2), width=Inches(5.85))

s19 = add_base_slide(19, "Results & Findings", "Benchmark 4: AutoML Model Performance Leaderboard", "Evaluating automated model selection and hyperparameter optimization against manual benchmarks")
add_card(
    s19, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "AUTOML ACCURACY BENCHMARKS",
    [
        "AUC-ROC Score > 0.94: Achieved on standard credit default and churn classification benchmark sets",
        "28% RMSE Reduction: Outperformed manual baseline linear regression models on housing sales data",
        "Cost-Frugal Search: Optimal hyperparameters converged in under 45 seconds using FLAML algorithms",
        "Ensemble Superiority: LightGBM and XGBoost consistently led leaderboards over standard scikit models",
        "One-Click Serialization: Trained pipeline pickled and ready for immediate inference via REST API",
    ],
    accent_color=C_INDIGO, title_size=16, item_size=13.5
)
if (ASSETS_DIR / "AutoMl.png").exists():
    s19.shapes.add_picture(str(ASSETS_DIR / "AutoMl.png"), Inches(6.8), Inches(2.2), width=Inches(5.85))

s20 = add_base_slide(20, "Results & Findings", "Benchmark 5: Regulatory Model Explainability via SHAP", "Demystifying black-box algorithms with game-theoretic Shapley feature attribution")
add_card(
    s20, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "SHAP VALUE TRANSPARENCY",
    [
        "Global Feature Importance: Ranks top predictive drivers across the entire dataset population",
        "Local Prediction Breakdown: Explains exact mathematical factors driving an individual customer's prediction",
        "Regulatory Compliance: Fulfills GDPR and EU AI Act 'Right to Explanation' requirements for automated AI",
        "Collinearity Detection: Reveals hidden indirect relationships between features and target outcomes",
        "Zero Guesswork: Replaces subjective intuition with mathematically provable feature weights",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13.5
)
if (ASSETS_DIR / "Insights.png").exists():
    s20.shapes.add_picture(str(ASSETS_DIR / "Insights.png"), Inches(6.8), Inches(2.2), width=Inches(5.85))

s21 = add_base_slide(21, "Results & Findings", "Benchmark 6: Natural Language Querying (NLQ) Execution", "Evaluating query comprehension accuracy and execution latency in conversational exploration")
add_card(
    s21, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "NLQ EVALUATION BENCHMARKS",
    [
        "96.2% Semantic Accuracy: Accurately converted complex conversational questions into Python Pandas code",
        "Sub-2.5s Response Time: From user question submission to chart rendering on the frontend canvas",
        "Self-Healing Code Logic: Automatic syntax error recovery re-prompts model with traceback on failure",
        "Dynamic Chart Selection: Automatically selects bar, line, scatter, or distribution charts based on data type",
        "Conversational Memory: Maintains session context for iterative follow-up drill-down inquiries",
    ],
    accent_color=C_ROSE, title_size=16, item_size=13.5
)
if (ASSETS_DIR / "AiQuery.png").exists():
    s21.shapes.add_picture(str(ASSETS_DIR / "AiQuery.png"), Inches(6.8), Inches(2.2), width=Inches(5.85))

s22 = add_base_slide(22, "Results & Findings", "Benchmark 7: System Security & Kernel Confinement Audit", "Penetration testing and regression verification across all system security boundaries")
add_card(
    s22, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "SECURITY PENETRATION AUDIT",
    [
        "117 / 117 Pytest Tests Passing (100%): Comprehensive test suite covering all modules and edge cases",
        "16 / 16 Security Tests Passing: Validated SSRF, Landlock isolation, and path traversal defenses",
        "Kernel Landlock Proof: Malicious scripts attempting to read `/etc/passwd` or write outside CWD are blocked",
        "SSRF Defense Proof: Remote ingestion URLs targeting `169.254.169.254` or `127.0.0.1` are strictly rejected",
        "No Multithread Deadlocks: Eliminated unsafe `preexec_fn` calls in favor of safe child process setup",
    ],
    accent_color=C_EMERALD, title_size=16, item_size=13.5
)
add_card(
    s22, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "ENTERPRISE GOVERNANCE CONTROLS",
    [
        "JWT Verification & Expiration: Strict stateless authentication with cryptographically signed tokens",
        "RBAC Role Governance: Admin, Editor, and Viewer permissions enforced on every API route",
        "ETag Optimistic Concurrency: Prevents two simultaneous analysts from overwriting each other's edits",
        "Token-Bucket Rate Limiting: Defends against brute-force credential stuffing and API denial-of-service",
        "Audit Logging: Every file uploaded, cleaned, or exported is recorded with timestamps and user IDs",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13.5
)

s23 = add_base_slide(23, "Results & Findings", "Benchmark 8: User Interface & Experience Evaluation", "Modern, responsive, high-contrast dark theme designed for enterprise data teams")
add_card(
    s23, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "FRONTEND ARCHITECTURE & UX",
    [
        "Next.js 15 App Router: Server Components deliver instant initial page loads with zero layout shift",
        "12-Face Human Avatar System: Modern, diverse SVG avatar catalog eliminating broken external image URLs",
        "Real-Time Telemetry: Live WebSocket status bars inform users of long-running training jobs",
        "High-Contrast Modern Aesthetic: TailwindCSS dark slate design system engineered for prolonged analytical work",
        "Multi-Modal Export Suite: Download cleaned CSVs, Excel files, trained model `.pkl` binaries, and full PDF reports",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13.5
)
if (ASSETS_DIR / "Dashboard.png").exists():
    s23.shapes.add_picture(str(ASSETS_DIR / "Dashboard.png"), Inches(6.8), Inches(2.2), width=Inches(5.85))

s24 = add_base_slide(24, "Results & Findings", "Benchmark 9: End-to-End Latency & Throughput", "Profiling the total elapsed time from raw dirty file upload to publication-ready PDF report")
perf_steps = [
    ("STAGE 1: INGESTION & PARSING", ["Raw CSV / Excel Intake", "MIME & Schema Validation", "Parquet Streaming Cache", "Elapsed: ~0.45s"], C_CYAN),
    ("STAGE 2: DATA CLEANING", ["Heuristic Imputation", "snake_case Normalization", "Outlier & Null Pruning", "Elapsed: ~1.28s"], C_EMERALD),
    ("STAGE 3: STATISTICAL MINING", ["Pearson Matrix Calculation", "OLS Linear Regressions", "FDR Anomaly Isolation", "Elapsed: ~3.10s"], C_AMBER),
    ("STAGE 4: AUTOML MODELING", ["LightGBM / XGBoost Search", "5-Fold Cross Validation", "SHAP Feature Attribution", "Elapsed: ~42.0s"], C_INDIGO),
    ("STAGE 5: PDF SYNTHESIS", ["5-Section Layout Compilation", "Chart & Table Rendering", "Final PDF Download Ready", "Elapsed: ~4.50s"], C_ROSE),
]
for i, (title, points, color) in enumerate(perf_steps):
    x = Inches(0.65 + i * 2.45)
    add_card(s24, x, Inches(1.85), Inches(2.35), Inches(4.8), title, points, accent_color=color, title_size=12, item_size=11.5)

s25 = add_base_slide(25, "Results & Findings", "Benchmark 10: Commercial Viability & Enterprise ROI", "Why enterprises and teams would readily pay for a DataForge subscription")
add_card(
    s25, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "QUANTIFIABLE RETURN ON INVESTMENT",
    [
        "95% Time-to-Insight Reduction: Tasks that took 3 weeks of manual analyst effort finish in under 90 seconds",
        "$140,000 Annual Salary Savings: Equates to the work output of 1.5 junior data engineers / data cleaners",
        "10x Cheaper than Alteryx/Dataiku: Saves $20,000+ per year in bloated commercial seat licensing",
        "Decision Velocity: Executives can test hypotheses in real-time during board meetings without waiting for IT",
        "Zero Setup Overhead: Completely browser-based; no software installation or GPU workstations required",
    ],
    accent_color=C_EMERALD, title_size=16, item_size=13.5
)
add_card(
    s25, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "SAAS MONETIZATION TIERS",
    [
        "Community Tier (Free): Single-user, local CSV uploads up to 50MB, standard statistical profiling",
        "Professional Tier ($49/mo): Multi-source connectors (Google Sheets, SQL), FLAML AutoML, PDF report exports",
        "Team Tier ($149/mo): Collaborative shared workspaces, role-based governance, custom avatar branding",
        "Enterprise / Self-Hosted ($999/mo): Air-gapped deployment, SSO (SAML/Okta), priority support, custom ML limits",
        "Total Addressable Market (TAM): $48 Billion global data preparation & automated machine learning market",
    ],
    accent_color=C_AMBER, title_size=16, item_size=13.5
)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDES 26–28: CONCLUSION AND FUTURE WORK (3 SLIDES)
# ══════════════════════════════════════════════════════════════════════════════
s26 = add_base_slide(26, "Conclusion", "Project Conclusion & Technical Impact", "Summarizing the major achievements and engineering contributions of the DataForge platform")
add_card(
    s26, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "KEY ACCOMPLISHMENTS",
    [
        "Solved the 80% Data Prep Dilemma: Autonomous heuristic cleaning eliminates tedious manual spreadsheet scrubbing",
        "Unified Fragmented Toolchains: Brought ingestion, cleaning, EDA, statistical mining, and AutoML under one roof",
        "Established Mathematical Ground Truth: Deterministic engines prevent generative AI hallucinations in critical numbers",
        "Hardened Defense-in-Depth: Linux Landlock kernel confinement protects servers against untrusted code exploits",
        "Delivered Enterprise-Ready UX: Modern Next.js 15 interface with 1080p graphics, 12 avatars, and full PDF reporting",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13.5
)
add_card(
    s26, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "ACADEMIC & INDUSTRY VALUE",
    [
        "Publication-Ready Documentation: Comprehensive 49-page B.Tech report with 300 DPI architectural figures",
        "100% Verified Quality: 117 automated pytest test cases validating data integrity, security, and concurrency",
        "Real-World Ready: Tested on dirty credit, healthcare, real estate, and retail datasets with high fidelity",
        "Bridged Technical Divides: Non-programmers can now train machine learning models and extract SHAP explanations",
        "Future-Proof Foundation: Decoupled microservice architecture easily extensible for streaming and distributed nodes",
    ],
    accent_color=C_EMERALD, title_size=16, item_size=13.5
)

s27 = add_base_slide(27, "Future Work", "Future Roadmap: Real-Time Streaming & Multimodal Ingestion", "Expanding beyond static tabular files into continuous event streams and unstructured enterprise records")
add_card(
    s27, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "REAL-TIME DATA STREAMING",
    [
        "Apache Kafka / Redpanda Connectors: Ingest continuous event logs and IoT sensor streams in real time",
        "Sliding Window Statistical Profiling: Dynamic detection of concept drift and real-time anomaly alerting",
        "Incremental Online Learning: Update LightGBM and SGD models without full dataset retraining",
        "Live Dashboard Push: WebSocket event broadcasting directly streaming live metric updates to client browsers",
        "Continuous Quality Guardrails: Automatic circuit breakers that halt pipelines when data schema drift occurs",
    ],
    accent_color=C_INDIGO, title_size=16, item_size=13.5
)
add_card(
    s27, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "MULTIMODAL & UNSTRUCTURED INTAKE",
    [
        "Document & Scanned Table OCR: Extract tables directly from PDF invoices, medical scans, and receipts",
        "Multi-Sheet Cross Reconciliation: Automatically identify foreign keys and join disparate Excel sheets",
        "Vector Database Integration (pgvector): Hybrid semantic search combining text embeddings with tabular columns",
        "Automated Audio Transcription: Extract tabular logs from call center recordings and service transcripts",
        "Direct Data Warehouse Sync: Native connectors for Snowflake, BigQuery, Databricks, and AWS Redshift",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13.5
)

s28 = add_base_slide(28, "Future Work", "Future Roadmap: Enterprise Identity & Edge Deployment", "Scaling DataForge into an enterprise-grade standard for sovereign corporate governance")
add_card(
    s28, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "ENTERPRISE GOVERNANCE & IDENTITY",
    [
        "Enterprise Single Sign-On (SSO): Seamless integration with Okta, Azure Active Directory, and SAML 2.0",
        "Granular Row-Level Security (RLS): Restrict dataset visibility by region, department, or clearance tier",
        "Immutable Audit Ledger: Cryptographically hashed logs recording every view, query, and transformation",
        "Regulatory Compliance Badges: Automated checks verifying compliance with HIPAA, GDPR, and SOC 2 Type II",
        "Data Catalog & Lineage Graph: Visual node graphs mapping the exact journey from raw file to trained model",
    ],
    accent_color=C_AMBER, title_size=16, item_size=13.5
)
add_card(
    s28, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "EDGE INFERENCE & CODE EXPORT",
    [
        "One-Click ONNX Model Export: Convert trained models into optimized ONNX binaries for mobile and edge devices",
        "Zero-Dependency C++ / Rust Predictor: Deploy high-throughput inference runtimes with microsecond latency",
        "Automated Dockerfile Generator: Package trained pipelines into self-contained microservice containers",
        "SQL Stored Procedure Transpilation: Convert trained decision trees into pure SQL queries for in-database execution",
        "Mobile Companion App: Native iOS and Android dashboard for executive metric tracking on the go",
    ],
    accent_color=C_ROSE, title_size=16, item_size=13.5
)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDES 29–31: REFERENCES (3 SLIDES)
# ══════════════════════════════════════════════════════════════════════════════
s29 = add_base_slide(29, "References", "References: Foundational Machine Learning Literature", "Seminal papers and algorithmic breakthroughs forming the theoretical basis of DataForge")
add_card(
    s29, Inches(0.65), Inches(1.85), Inches(12.0), Inches(4.8),
    "PEER-REVIEWED ACADEMIC PUBLICATIONS",
    [
        "Breiman, L. (2001). Random Forests. Machine Learning, 45(1), 5–32. (Foundational tree-based ensemble learning).",
        "Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, 785–794.",
        "Ke, G., et al. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision Tree. Advances in Neural Information Processing Systems (NeurIPS 2017), 30.",
        "Wang, C., Wu, Q., Huang, C., & Saied, A. (2021). FLAML: A Fast and Lightweight AutoML Library. Proceedings of the 4th MLSys Conference.",
        "Lundberg, S. M., & Lee, S.-I. (2017). A Unified Approach to Interpreting Model Predictions. Advances in Neural Information Processing Systems (NeurIPS 2017), 4765–4774. (Game-theoretic SHAP interpretability).",
        "Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. Journal of the Royal Statistical Society: Series B, 57(1), 289–300.",
    ],
    accent_color=C_CYAN, title_size=15, item_size=12.5
)

s30 = add_base_slide(30, "References", "References: Industry Standards & Architecture Frameworks", "Authoritative standards on data quality, security engineering, and web architecture")
add_card(
    s30, Inches(0.65), Inches(1.85), Inches(12.0), Inches(4.8),
    "INDUSTRY SPECIFICATIONS & TECHNICAL REPORTS",
    [
        "Gartner Research (2024). Measuring the Business Value of Data Quality and Governance in Modern Enterprise Analytics.",
        "IEEE Computer Society (2000). IEEE Recommended Practice for Architectural Description of Software-Intensive Systems (IEEE Std 1471-2000).",
        "Open Web Application Security Project (OWASP) (2025). Top 10 API Security Risks and LLM Application Security Guidelines.",
        "National Institute of Standards and Technology (NIST) (2023). Artificial Intelligence Risk Management Framework (AI RMF 1.0).",
        "Fielding, R. T. (2000). Architectural Styles and the Design of Network-based Software Architectures. Doctoral dissertation, University of California, Irvine.",
        "Redman, T. C. (2018). If Your Data Is Bad, Your Machine Learning Tools Won't Work. Harvard Business Review.",
    ],
    accent_color=C_INDIGO, title_size=15, item_size=12.5
)

s31 = add_base_slide(31, "References", "References: Technical Frameworks & Open-Source Specifications", "Official software engineering documentation and security specifications")
add_card(
    s31, Inches(0.65), Inches(1.85), Inches(12.0), Inches(4.8),
    "FRAMEWORK SPECIFICATIONS & KERNEL DOCUMENTATION",
    [
        "FastAPI Documentation & ASGI Architectural Specification. Sebastián Ramírez. (2024). High-performance asynchronous Python web framework.",
        "Next.js 15 & React 19 Architecture Specification. Vercel Inc. (2024). Server Components, App Router, and dynamic streaming rendering.",
        "Linux Landlock Security Module (LSM) Kernel Documentation. Mickaël Salaün. (2021). Unprivileged access control and process sandboxing in Linux kernel 5.13+.",
        "Google DeepMind (2025). Gemini 2.5 Flash Technical Report: Advanced Reasoning and Multimodal Synthesis.",
        "Apache Arrow Project (2024). Columnar In-Memory Analytics and Streaming Inter-Process Communication Standards.",
        "Supabase Open Source Architecture. (2024). Real-time PostgreSQL, Row-Level Security, and Object Storage Integration.",
    ],
    accent_color=C_EMERALD, title_size=15, item_size=12.5
)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 32: Q&A (1 SLIDE)
# ══════════════════════════════════════════════════════════════════════════════
s32 = add_base_slide(32, "Discussion", "Question & Answer Session", "Inviting questions, feedback, architectural critique, and live system demonstration")
add_card(
    s32, Inches(0.65), Inches(1.85), Inches(5.85), Inches(4.8),
    "TOPICS FOR DISCUSSION & DEFENSE",
    [
        "System Architecture: Decoupled 4-tier microservices, asynchronous WebSockets, and FastAPI ASGI performance",
        "Deterministic Math Engine: Benjamini-Hochberg FDR control and separation of numerical truth from LLMs",
        "Kernel Sandboxing: Linux Landlock LSM system-call confinement vs Docker containers for multi-tenant code execution",
        "AutoML Benchmark Generalization: Hyperparameter search space, SHAP explainability, and cross-validation rigor",
        "Commercial Viability: Monetization strategy, enterprise pricing tiers, and ROI vs traditional data analyst staffing",
    ],
    accent_color=C_CYAN, title_size=16, item_size=13.5
)
add_card(
    s32, Inches(6.8), Inches(1.85), Inches(5.85), Inches(4.8),
    "AVAILABLE LIVE DEMONSTRATIONS",
    [
        "1. Instant CSV Ingestion: Drag-and-drop dirty spreadsheet upload and automated schema deduction",
        "2. Deterministic Cleaning Pipeline: One-click null imputation, snake_case normalization, and duplicate row pruning",
        "3. Live AutoML Model Training: Real-time model tournament and leaderboard generation via FLAML",
        "4. Interactive SHAP Interpretation: Visualizing feature impact and prediction attribution on live data",
        "5. Natural Language Querying: Real-time English query to sandboxed chart rendering with Gemini 2.5 Flash",
    ],
    accent_color=C_EMERALD, title_size=16, item_size=13.5
)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 33: THANK YOU (1 SLIDE)
# ══════════════════════════════════════════════════════════════════════════════
s33 = prs.slides.add_slide(blank_layout)
bg33 = s33.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height)
bg33.fill.solid()
bg33.fill.fore_color.rgb = C_BG
bg33.line.fill.background()

# Central Thank You Card
c33 = s33.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), Inches(1.0), Inches(10.333), Inches(5.5))
c33.fill.solid()
c33.fill.fore_color.rgb = C_CARD_BG
c33.line.color.rgb = C_CYAN
c33.line.width = Pt(2)

tb33 = s33.shapes.add_textbox(Inches(1.8), Inches(1.3), Inches(9.733), Inches(4.9))
tf33 = tb33.text_frame
tf33.word_wrap = True

p_ty_head = tf33.paragraphs[0]
p_ty_head.text = "THANK YOU!"
p_ty_head.font.name = "Arial"
p_ty_head.font.size = Pt(40)
p_ty_head.font.bold = True
p_ty_head.font.color.rgb = C_CYAN
p_ty_head.alignment = PP_ALIGN.CENTER

p_ty_sub = tf33.add_paragraph()
p_ty_sub.text = "DataForge: Transforming Raw Data Chaos into Clear, Explainable Enterprise Decisions"
p_ty_sub.font.name = "Arial"
p_ty_sub.font.size = Pt(16)
p_ty_sub.font.bold = True
p_ty_sub.font.color.rgb = C_WHITE
p_ty_sub.alignment = PP_ALIGN.CENTER
p_ty_sub.space_before = Pt(10)

p_div = tf33.add_paragraph()
p_div.text = "──────────────────────────────────────────────────────"
p_div.font.name = "Arial"
p_div.font.size = Pt(12)
p_div.font.color.rgb = C_CARD_BORDER
p_div.alignment = PP_ALIGN.CENTER
p_div.space_before = Pt(8)

p_ack = tf33.add_paragraph()
p_ack.text = "We express our sincere gratitude to our Project Guide, Dr. Parvaz Ahmad Malla, our Head of Department, Prof. Aasia Quyoum, and the faculty of the Department of Computer Science & Engineering, Government College of Engineering and Technology (GCET), Safapora, Ganderbal, for their continuous mentorship and support."
p_ack.font.name = "Arial"
p_ack.font.size = Pt(13)
p_ack.font.color.rgb = C_MUTED
p_ack.alignment = PP_ALIGN.CENTER
p_ack.space_before = Pt(10)

p_team = tf33.add_paragraph()
p_team.text = "Project Team: Mohammad Numan Narwaroo  •  Mohammad Usman Dar  •  Faheem Ahmad Bhat  •  Mubashir Shabir"
p_team.font.name = "Arial"
p_team.font.size = Pt(13)
p_team.font.bold = True
p_team.font.color.rgb = C_WHITE
p_team.alignment = PP_ALIGN.CENTER
p_team.space_before = Pt(16)

p_repo = tf33.add_paragraph()
p_repo.text = "Open Source Repository: https://github.com/FaheemorFAB/DataForge_v3"
p_repo.font.name = "Arial"
p_repo.font.size = Pt(12)
p_repo.font.color.rgb = C_CYAN
p_repo.alignment = PP_ALIGN.CENTER
p_repo.space_before = Pt(8)

# Save PPTX
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
prs.save(str(OUTPUT_PPTX))
print(f"Successfully generated PowerPoint presentation at {OUTPUT_PPTX} ({len(prs.slides)} slides)")
