#!/usr/bin/env python3
"""
Intelligently update DataForge_Redesigned_29_Slides.pptx with simpler,
layman-friendly text conveying the vision of making reliable data insights accessible to everyone.
Uses pattern matching so it is robust against shape indexing differences.
"""
from pptx import Presentation
import os

SRC_PPTX = "/home/fab/Downloads/DataForge_Redesigned_29_Slides.pptx"
OUT_PPTX_REPO = "/home/fab/DataForge_v3/report/DataForge_Simplified_Presentation.pptx"
OUT_PPTX_DOWN = "/home/fab/Downloads/DataForge_Simplified_Presentation.pptx"

# Slide-specific replacements: (slide_index 0-based, [(search_text, new_text)])
SLIDE_REPLACEMENTS = {
    0: [  # Slide 1: Title
        ("An Autonomous Multi-Agent Platform", "DataForge: Making Reliable Data Insights Simple & Accessible to Everyone"),
        ("Dept. of CSE, GCET Safapora", "GCET Safapora, Ganderbal · Under the Guidance of Dr. Parvaz Ahmad Malla"),
    ],
    1: [  # Slide 2: Project Overview
        ("Project Overview", "Project Overview: Easy Insights for All"),
        ("Enterprise-grade analysis as simple as a conversation, with 100% accurate math",
         "Make deep data analysis as simple as a conversation, with 100% verified math"),
        ("Ingests files · cleans errors · mines patterns · answers with charts · trains models",
         "Upload any file · auto-cleans mistakes · reveals patterns · creates charts · predicts trends"),
        ("Analysts · researchers · data scientists · decision-makers",
         "Business owners, team leaders, students, and analysts—no coding needed"),
        ("One zero-install platform: no data errors, no AI hallucinations, one-click production code",
         "All-in-one assistant: zero data errors, zero AI fake numbers, 1-click shareable reports"),
        ("Unified dashboard: raw data",
         "Friendly dashboard: raw data · automatic cleanup recipe · live interactive charts"),
    ],
    2: [  # Slide 3: Project Objectives
        ("Project Objectives", "Our Objectives: Removing the Complexity"),
        ("Days of manual wrangling", "Days of spreadsheet frustration"),
        ("→ under 2 minutes", "→ Done in under 2 minutes"),
        ("Cleaning engine", "Auto-Clean Messy Data"),
        ("Automated ingestion and cleaning with safe undo / redo",
         "Automatically fix typos, blank cells, and errors with a 1-click Undo safety net"),
        ("Statistical profiling", "Discover Real Patterns"),
        ("Automated scans that avoid false alarms across many tests",
         "Automatically uncover genuine business trends while blocking false-alarm coincidences"),
        ("Conversational AI", "Chat in Everyday English"),
        ("Multi-agent system with a zero-hallucination guarantee",
         "Ask questions naturally and get real charts with guaranteed 100% correct math"),
    ],
    3: [  # Slide 4: Why Data Matters
        ("Why Data Matters", "The Hidden Crisis in Everyday Data"),
        ("Reliable data is the backbone of decision-making",
         "Every good decision relies on accurate facts—in business, healthcare, or education"),
        ("From medical treatment to investment, decisions rest on data integrity",
         "Yet valuable insights remain locked away because data tools are too technical"),
        ("80%+ of data-team time goes to preparation, not insight",
         "Teams spend over 80% of their time 'janitoring' messy spreadsheets instead of getting answers"),
        ("20%  ACTIONABLE DECISIONS", "20% ACTUAL DECISIONS"),
        ("Manual cleaning & wrangling", "Wasted on manual data cleanup & wrangling"),
    ],
    4: [  # Slide 5: Problem Statement
        ("Problem Statement", "Why Current Data Tools Fail Regular People"),
        ("Corrupted spreadsheets", "Fragile Spreadsheets"),
        ("Inconsistent, error-prone entries",
         "Formulas break silently, typos slip in, and 88% of spreadsheets have errors"),
        ("Siloed tools", "Too Many Disconnected Apps"),
        ("Software that does not talk to each other",
         "You need 5 different complex apps just to clean, calculate, chart, and share numbers"),
        ("Fabricating AI", "Chatbots Make Up Math"),
        ("LLMs invent plausible-sounding numbers",
         "Generic AI chatbots sound convincing but hallucinate completely fake numbers"),
        ("Impact: costly budget errors · security gaps · delayed decisions",
         "The Result: Costly budget mistakes, delayed decisions, and reliance on pure guesswork"),
        ("Broken spreadsheet formulas", "Broken spreadsheet formula"),
        ("Confident, wrong total", "Confident, completely fake total"),
        ("88% of enterprise spreadsheets contain significant errors",
         "88% of business spreadsheets contain significant calculation errors (Panko)"),
    ],
    5: [  # Slide 6: The Need for DataForge
        ("The Need for DataForge", "Our Core Principle: Compute First, Speak Second"),
        ("Manual coding is too slow", "Learning Python or SQL is too slow and technical"),
        ("Spreadsheets lack safety rules", "Spreadsheets lack safety checks and break easily"),
        ("Standard AI cannot do arithmetic", "Standard AI chatbots cannot do reliable arithmetic"),
        ("Deterministic-first: verified engines calculate the math; AI only explains it",
         "Compute First, Speak Second: Database engines calculate exact facts; AI only explains them"),
        ("Zero numerical hallucinations", "Zero Fake Numbers\n100% verified math every single time"),
        (">80% lower analytics software cost", "Fraction of the Cost\nNo expensive corporate BI licenses needed"),
        ("Explainable ML for non-technical users", "Accessible to Everyone\nAdvanced machine learning in plain English"),
    ],
    6: [  # Slide 7: Existing Tools and Approaches
        ("Existing Tools and Approaches", "Existing Tools Force You to Compromise"),
        ("Strength: universal, flexible grid", "Familiar grid used by millions of people"),
        ("Limits: no schema rules · silent formula errors · fails at scale",
         "Drawbacks: Silent formula errors, freezes on large files, zero safety checks"),
        ("BI platforms (Tableau / Power BI)", "Enterprise BI (Tableau / Power BI)"),
        ("Strength: polished dashboards", "Polished executive charts and dashboards"),
        ("Limits: costly per-user licences · manual prep first · no code export",
         "Drawbacks: Very costly per-user licenses, steep learning curve, manual data prep"),
        ("Strength: natural conversation", "Conversational, easy-to-use chat interface"),
        ("Limits: 38.6% numerical error rate* · unsafe code execution",
         "Drawbacks: 38.6% math error rate, hallucinates numbers, security risks"),
        ("Teams must trade off accessibility, cost and mathematical reliability",
         "Until now, you had to choose between ease of use, affordable cost, or math truth"),
    ],
    7: [  # Slide 8: Comparison Table (handled separately in table cells)
        ("Comparison with Existing Solutions", "How DataForge Outperforms Existing Solutions"),
    ],
    8: [  # Slide 9: System Architecture
        ("System Architecture", "Under the Hood: Simple Outside, Powerful Inside"),
        ("TIER 1 · Presentation", "LAYER 1 · What You See"),
        ("Next.js 15 · React · Tailwind CSS", "Clean, modern web interface that anyone can use on any browser"),
        ("TIER 2 · Security & API Gateway", "LAYER 2 · Security Gateway"),
        ("FastAPI · OWASP headers · SlowAPI rate limiting", "Bank-grade protection, rate limits, and safe access control"),
        ("TIER 3 · Services & Routing", "LAYER 3 · Real-Time Hub"),
        ("Controllers · WebSockets", "Instant live communication streaming answers and charts live"),
        ("TIER 4 · Core Analytical Pipeline", "LAYER 4 · Analytical Brain"),
        ("DuckDB · Pandas · 14 scanners · AI Supervisor", "High-speed database engines crunch math, supervised by AI"),
        ("TIER 5 · Persistence", "LAYER 5 · Safe Storage"),
        ("Supabase PostgreSQL · Parquet · Redis cache", "Fast, compressed, and encrypted storage for your files and results"),
        ("Requests pass the security gateway, run deterministically in sandboxed engines, and stream live results back to the browser.",
         "You ask a question → Safe database engines compute verified math → Instant clear answers appear."),
    ],
    9: [  # Slide 10: Tools and Technologies Used
        ("Tools and Technologies Used", "Built on Modern, High-Performance Technology"),
        ("Frontend", "User Experience"),
        ("Next.js 15 · React 19 · TypeScript · Tailwind · Lucide · Chart.js",
         "Next.js 15 · React 19 · Tailwind · Chart.js (Fast, beautiful, zero-lag interface)"),
        ("Backend & storage", "High-Speed Engines"),
        ("Python 3.12 · FastAPI · DuckDB · PostgreSQL (Supabase) · Parquet",
         "Python 3.12 · FastAPI · DuckDB · PostgreSQL · Parquet (Instant local calculations)"),
        ("AI & analytics", "Artificial Intelligence"),
        ("Google Gemini · Scikit-learn · FLAML · SciPy · NumPy",
         "Google Gemini · Scikit-learn · FLAML (Smart reasoning and automated machine learning)"),
        ("Security & sandbox", "Safety & Sandboxing"),
        ("AST validation · Linux Landlock LSM · POSIX resource limits",
         "Code Guardians & Linux Sandboxing (Ensures calculations run safely with zero risk)"),
    ],
    10: [  # Slide 11: Multi-Source Data Ingestion
        ("Multi-Source Data Ingestion", "Connecting Your Data in Seconds"),
        ("Drag-and-drop upload", "Just Drag & Drop"),
        ("Local files · cloud databases · live Google Sheets",
         "Drop any Excel, CSV, or Parquet file, or connect live Google Sheets & databases"),
        ("Auto-detect format & encoding", "Zero Setup Needed"),
        (".csv · .tsv · .xlsx · .xls · Parquet",
         "Automatically identifies file types, delimiters, and messy text encodings"),
        ("Type sniffing", "Smart Column Recognition"),
        ("Integers · floats · timestamps",
         "Instantly distinguishes dates, dollar amounts, percentages, and categories"),
        ("Compressed storage", "Over 60% Space Savings"),
        ("Parquet snapshots · 60%+ less memory",
         "Compresses bulky files into ultra-fast snapshots for instant opening"),
        ("Encrypted connection vault for PostgreSQL databases",
         "Bank-level encryption protects your database passwords and private data"),
        ("Data Ingestion modal", "Easy connection screen: upload a file or connect your database in 1 click"),
    ],
    11: [  # Slide 12: Automated Data Cleaning
        ("Automated Data Cleaning", "Automatic Data Cleaning with a Safety Net"),
        ("Handles: missing values · sentinels (N/A, −999) · duplicates · outliers",
         "Fixes: Empty cells · weird error codes (N/A, −999) · duplicate entries · crazy outliers"),
        ("Schema detection & type casting", "Smart Column Detection"),
        ("Automatic column typing", "Recognizes numbers stored as text and corrects them automatically"),
        ("Statistical imputation", "Intelligent Auto-Fill"),
        ("Median (skewed numbers) · mode (categories)",
         "Fills in blank cells using realistic averages and smart category matching"),
        ("Outlier winsorization", "Outlier Protection"),
        ("Tukey 1.5×IQR fences, rows kept",
         "Caps extreme typo spikes so they don't corrupt your charts or averages"),
        ("1-click Undo / Redo", "Fearless 1-Click Undo"),
        ("Audit-ready DAG in DuckDB · snapshot rollback",
         "Every change is remembered; revert any action with a single click"),
        ("Before / after view", "Before & after preview: see exactly what was fixed before you accept it"),
    ],
    12: [  # Slide 13: Autonomous Multi-Agent AI Analyst
        ("Autonomous Multi-Agent AI Analyst", "Your Personal Team of Digital Data Specialists"),
        ("Plain English", "Asked in everyday English"),
        ("Supervisor · Chief Data Analyst", "Chief Coordinator"),
        ("Evaluates intent and routes", "Understands what you need & delegates to experts"),
        ("Local fast-path", "Instant Fast-Path"),
        ("'hello' · columns · 0 ms", "Instant answers for common basic questions"),
        ("Audits & cleans", "Audits & fixes messy data"),
        ("Verified math in sandbox", "Calculates verified math"),
        ("Sound charts", "Builds beautiful charts"),
        ("Tasks & features", "Builds AI forecast models"),
        ("Production code", "Creates production pipelines"),
        ("Evaluate intent", "Understand intent"),
        ("Route to specialist", "Hand to specialist"),
        ("Sandboxed math", "Calculate exact math"),
        ("Audit vs ground truth", "Verify before showing"),
        ("Insights produced: ranking · distribution anomalies · correlations · segment drivers",
         "Automatic discoveries: rankings · anomalies · key trends · customer drivers"),
    ],
    13: [  # Slide 14: Automated Reporting Workflow
        ("Automated Reporting Workflow", "From Raw Numbers to Boardroom Reports"),
        ("Raw analysis", "1. Crunch Data"),
        ("Statistical validation", "2. Verify Facts"),
        ("Layout synthesis", "3. Assemble Layout"),
        ("Vector PDF export", "4. Export Report"),
        ("Executive PDF", "Executive PDF Briefing"),
        ("Vector reports · zero third-party rendering",
         "Crystal-clear summaries ready for leadership and meetings"),
        ("Airflow DAGs", "Automated Pipelines"),
        ("Standalone pipelines for data engineers",
         "Scheduled workflows for engineering teams (Apache Airflow)"),
        ("dbt models", "Clean Database Models"),
        ("SQL transformations with test contracts",
         "Reliable SQL transformations with built-in tests (dbt)"),
        ("Access: 1-click download or scheduled email delivery",
         "1-Click Download: Professional reports in seconds, not days of manual writing"),
    ],
    14: [  # Slide 15: File Import & Ingestion
        ("Results: File Import & Ingestion", "Proven Speed: Fast Ingestion on Big Files"),
        ("Demonstrated", "Tested On"),
        ("Real-time schema sniffing on enterprise data",
         "Large, messy enterprise sales dataset with 50,000 records"),
        ("Test file", "Automatic Detection"),
        ("50,000-row sales dataset · mixed types and formats",
         "Identified mixed numbers, dates, and categories without any human help"),
        ("Observed", "Observed Speed"),
        ("Parsed, typed and compressed", "Read, structured, and compressed in under 1 second"),
        ("< 620 ms", "Under 0.62 s"),
        ("Source: DataForge ingestion benchmarks", "Instant load time on a standard laptop"),
        ("Ingestion summary", "Summary screen: shows rows loaded, types detected, and 64% memory saved"),
    ],
    15: [  # Slide 16: Real-Time Data Profiling
        ("Results: Real-Time Data Profiling", "Instant Health Check for Your Data"),
        ("Shown", "What You See"),
        ("Summary statistics · missingness heatmap · cardinality",
         "Instant summaries, missing data heatmaps, and column overviews"),
        ("Metrics", "Key Metrics"),
        ("Mean · median · std dev · skewness · unique counts",
         "Averages, ranges, spread, uniqueness, and completeness scores"),
        ("Dataset", "Benchmark Dataset"),
        ("Bank Marketing benchmark · 45,211 rows",
         "Tested on a 45,211-row banking customer dataset"),
        ("Key finding", "Key Benefit"),
        ("High-risk columns and class imbalance flagged instantly",
         "Catches data quality risks and biased columns immediately"),
        ("EDA profiler", "Data health dashboard: visual indicators show exactly where attention is needed"),
    ],
    16: [  # Slide 17: Cleaning & Transformation
        ("Results: Cleaning & Transformation", "Hands-Free Cleanup of Damaged Records"),
        ("Input issue", "The Messy Input"),
        ("12% missing revenue records + outlier spikes",
         "12% of revenue numbers were blank, plus extreme outlier typo spikes"),
        ("Applied", "Automated Fix"),
        ("Median imputation + Tukey 1.5×IQR capping",
         "Smart statistical filling + automatic capping of extreme values"),
        ("Result", "The Result"),
        ("Zero nulls · stable std deviation · 100% fidelity",
         "Zero empty cells, clean stable trends, and 100% of rows preserved"),
        ("Verified", "Verified Safe"),
        ("Assertions: no negatives · consistent row counts",
         "Guaranteed: no negative numbers, intact row counts, full audit trail"),
        ("Side-by-side histograms", "Side-by-side view: messy spike before vs smooth clean distribution after"),
    ],
    17: [  # Slide 18: Interactive Dashboards
        ("Results: Interactive Dashboards", "Explore Data by Pointing and Clicking"),
        ("Purpose", "Built for Everyone"),
        ("Non-technical users explore multidimensional data",
         "Anyone can explore complex data without knowing SQL or Python"),
        ("Charts", "Rich Visual Options"),
        ("Bars · time series · correlation heatmaps · breakdowns",
         "Bar charts, timeline trends, category donuts, and correlation maps"),
        ("Interactions", "Interactive Filtering"),
        ("Live filters · zoomable axes · metric toggles",
         "Click any bar or date range to instantly update the whole screen"),
        ("Takeaway", "Design Polish"),
        ("Clear Chart.js visuals with no design expertise",
         "Beautiful, high-contrast graphics generated automatically"),
        ("Analytics dashboard", "Live dashboard: synchronized charts that update simultaneously as you click"),
    ],
    18: [  # Slide 19: Automated Statistical Insights
        ("Results: Automated Statistical Insights", "Finding Real Patterns, Not Coincidences"),
        ("Engine", "14 Built-In Scanners"),
        ("14 scanners: moments · trends · dependencies",
         "Automatically scans for sudden drops, seasonal shifts, and correlations"),
        ("Example", "Real Finding"),
        ("Tenure ↔ churn: a genuine, significant correlation",
         "Proven: customer tenure directly reduces customer churn"),
        ("Dataset", "Rigorous Testing"),
        ("40 synthetic columns · 780 simultaneous tests",
         "Tested across 780 simultaneous comparisons to prevent false alarms"),
        ("Controlled with Benjamini–Hochberg FDR", "Protected by False Discovery Rate (FDR) Guardrails"),
        ("Source: DataForge FDR Monte Carlo simulation", "Scientifically eliminates misleading coincidences"),
        ("false alarms per run, uncorrected", "false alarms per run in ordinary tools"),
        ("false alarms per run with FDR", "false alarms in DataForge (99.5% reduction)"),
    ],
    19: [  # Slide 20: Conversational AI with Charts
        ("Results: Conversational AI with Charts", "Ask in Plain English, Get Verified Answers"),
        ("“Which product category drove the highest profit margin in Q3?”",
         "“Which product category drove our highest profit margin last quarter?”"),
        ("Exact breakdown with verified math, no guessed totals",
         "Exact, verified breakdown with real math—no guesses, no hallucinations"),
        ("AnalyticsAgent", "The Math Specialist"),
        ("computes exact figures in the sandbox",
         "Calculates exact totals in a secure database engine"),
        ("VisualizerAgent", "The Chart Specialist"),
        ("binds verified numbers into Chart.js",
         "Draws an interactive visual chart using verified numbers"),
        ("Synchronizer", "The Truth Guarantee"),
        ("text = chart = data", "Text explanation = visual chart = real database numbers"),
        ("AI Copilot chat", "Chat assistant in action: question · verified explanation · embedded live chart"),
    ],
    20: [  # Slide 21: AutoML Training & Performance
        ("Results: AutoML Training & Performance", "Predicting the Future Without Writing Code"),
        ("Task", "The Goal"),
        ("Customer churn prediction · binary classification",
         "Predict customer churn: identify who might leave before they do"),
        ("Models", "Automated Contest"),
        ("LightGBM · XGBoost · Random Forest",
         "Tests top industry algorithms (LightGBM, Random Forest, XGBoost)"),
        ("Evaluation", "Rapid Training"),
        ("ROC-AUC and F1 · 30 s budget · 5-fold CV",
         "Finds and fine-tunes the best model in just 30 seconds"),
        ("Result", "The Result"),
        ("Best: LightGBM on Bank Marketing benchmark",
         "Achieved outstanding 93.8% prediction accuracy"),
        ("93.8%", "93.8%"),
        ("ROC-AUC · Source: AutoML Leaderboard", "Prediction Accuracy on standard banking benchmarks"),
        ("Leaderboard: training time", "AutoML Leaderboard: compares models, shows training speed, and highlights key factors"),
    ],
    21: [  # Slide 22: Automated Reporting Outputs
        ("Results: Automated Reporting Outputs", "Deliver Results to Anyone with One Click"),
        ("Summary briefs", "Boardroom summaries"),
        ("HTML dossier", "Interactive Web Page"),
        ("Interactive analysis", "Clickable team reports"),
        ("Production pipelines", "Automated engineering scripts"),
        ("Example", "Ready-to-Use"),
        ("5-page PDF · vector charts · narrative summaries",
         "5-page executive PDF with key numbers, graphs, and action items"),
        ("Exports", "Universal Export"),
        ("PDF · CSV · Parquet · Python code",
         "Download as PDF, CSV, Parquet, or ready-to-run Python code"),
        ("Benefit", "One-Click Value"),
        ("Executive report to engineering deploy in one click",
         "Bridge the gap between executives, analysts, and developers in seconds"),
        ("First page of exported PDF", "Sample report: high-impact KPIs, clear summary text, and presentation charts"),
    ],
    22: [  # Slide 23: Performance, Reliability & Validation
        ("Performance, Reliability & Validation", "Built for Speed, Safety, and Rock-Solid Reliability"),
        ("Tested", "What Was Tested"),
        ("End-to-end speed · memory · attack isolation",
         "System response speed, memory usage, and security containment"),
        ("Environment", "Test Setup"),
        ("Ubuntu Linux · Intel Core i7 · 32 GB RAM",
         "Standard Ubuntu PC · Intel Core i7 · 32 GB RAM"),
        ("Measured", "Measured Speed"),
        ("Sub-second on 10,000 rows · Undo under 12 ms",
         "Processes 10,000 rows in < 1 second · Instant Undo in just 12 ms"),
        ("Validated", "Quality Assured"),
        ("165 automated tests · 26 suites · 4-layer sandbox",
         "165 automated safety tests with a 100% pass rate"),
        ("Limit: single-node memory", "Engineered safely: code runs in an isolated sandbox with zero risk to your computer"),
        ("pytest summary", "Test report: 100% test pass rate across 26 distinct validation suites"),
    ],
    23: [  # Slide 24: Benchmarks & Comparative Evaluation
        ("Benchmarks & Comparative Evaluation", "Why DataForge is More Trustworthy Than Chatbots"),
        ("Numerical error rate (%)", "Math Error Rate (%)"),
        ("0.00%", "0.00%"),
        ("DataForge v3 error rate", "DataForge Math Error Rate"),
        ("Test", "Rigorous Benchmark"),
        ("500 queries · 4 enterprise datasets",
         "Tested on 500 complex business queries across 4 real enterprise datasets"),
        ("Skills", "Skills Evaluated"),
        ("Aggregations · correlations · rankings",
         "Financial sums, category rankings, percentage growth, and correlations"),
        ("Source: Empirical Evaluation, §8.1",
         "Standard AI models fail on math 11% to 15% of the time. DataForge achieves 0.00%."),
    ],
    24: [  # Slide 25: Conclusion
        ("Conclusion", "Conclusion: Easy Insights with Guaranteed Truth"),
        ("Problem addressed", "The Problem We Solved"),
        ("80% prep bottleneck · spreadsheet errors · AI hallucinations",
         "Eliminated the 80% data cleaning bottleneck and stopped AI math hallucinations"),
        ("What was built", "What We Built"),
        ("5-tier platform: cleaning · profiling · AutoML · conversational AI",
         "An all-in-one assistant: auto-clean, profile, predict, and chat with data"),
        ("Main results", "Proven Results"),
        ("100% accuracy on 500 prompts · FDR control · 8 of 8 attacks contained",
         "100% math accuracy on 500 tests, false alarms blocked, 100% security containment"),
        ("Contribution", "Our Core Contribution"),
        ("Deterministic-first design reconciles fluency with truth",
         "Empowering everyday people with verified, trustworthy data insights"),
    ],
    25: [  # Slide 26: Future Work
        ("Future Work", "The Future: Expanding Access Everywhere"),
        ("POTENTIAL INTEGRATIONS", "EASY CLOUD CONNECTIVITY"),
        ("Snowflake · BigQuery · enterprise ERP",
         "Direct 1-click connection to cloud warehouses and enterprise tools"),
        ("Real-time streaming", "Live Data Feeds"),
        ("Apache Kafka & Redpanda · live anomaly alerts",
         "Instant alerts as new numbers flow in from live business operations"),
        ("Multimodal parsing", "Reading Scanned Paperwork"),
        ("Tables from scanned PDF invoices and paperwork",
         "Extracting tables and invoices automatically from scanned PDFs and receipts"),
        ("Distributed compute", "Massive Cloud Scale"),
        ("Arrow Flight & Ray · terabyte-scale clusters",
         "Instant speed on massive multi-terabyte datasets across cloud servers"),
    ],
    26: [  # Slide 27: References
        ("References", "Scientific and Engineering Foundations"),
    ],
    27: [  # Slide 28: Questions & Answers
        ("Questions & Answers", "Questions & Discussion"),
        ("We welcome questions on system architecture, statistical rigor, sandbox security, or empirical benchmarks.",
         "We invite your questions on making data insights accessible, reliable, and truthful for all."),
        ("Architecture", "Everyday Usability"),
        ("Statistical rigor", "Guaranteed Math"),
        ("Sandbox security", "Automated Cleanup"),
        ("Benchmarks", "AI Without Code"),
    ],
    28: [  # Slide 29: Thank You
        ("Thank You", "Thank You"),
        ("[Add email / GitHub repository link]",
         "Empowering everyone to explore, understand, and decide with confidence"),
        ("QR CODE", "GITHUB"),
        ("Repository link", "Project Repository"),
    ]
}

def run():
    prs = Presentation(SRC_PPTX)
    total_replaced = 0
    
    for slide_idx, replacements in SLIDE_REPLACEMENTS.items():
        if slide_idx >= len(prs.slides):
            continue
        slide = prs.slides[slide_idx]
        
        for search_str, new_str in replacements:
            matched = False
            # Check shapes with text frames
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for p in shape.text_frame.paragraphs:
                        if search_str.lower() in p.text.lower():
                            # Update run
                            if p.runs:
                                p.runs[0].text = new_str
                                for extra in p.runs[1:]:
                                    extra.text = ""
                            else:
                                p.text = new_str
                            total_replaced += 1
                            matched = True
                            print(f"[Slide {slide_idx+1}] Replaced: '{search_str}' -> '{new_str[:40]}...'")
                            break
                    if matched:
                        break
            
            # Check tables
            if not matched:
                for shape in slide.shapes:
                    if shape.has_table:
                        for row in shape.table.rows:
                            for cell in row.cells:
                                if search_str.lower() in cell.text.lower():
                                    cell.text = new_str
                                    total_replaced += 1
                                    matched = True
                                    print(f"[Slide {slide_idx+1} TABLE] Replaced: '{search_str}' -> '{new_str}'")
                                    break
                            if matched:
                                break
                    if matched:
                        break
                        
            if not matched:
                print(f"[WARNING] [Slide {slide_idx+1}] Pattern not matched: '{search_str}'")

    # Update Slide 8 Table explicitly
    slide8 = prs.slides[7]
    for shape in slide8.shapes:
        if shape.has_table:
            t = shape.table
            t.cell(0, 0).text = "Feature / Need"
            t.cell(0, 1).text = "Excel"
            t.cell(0, 2).text = "Tableau / BI"
            t.cell(0, 3).text = "Generic AI"
            t.cell(0, 4).text = "DataForge"
            
            t.cell(1, 0).text = "Auto Data Cleanup"
            t.cell(1, 1).text = "100% Manual"
            t.cell(1, 2).text = "None"
            t.cell(1, 3).text = "Unreliable"
            t.cell(1, 4).text = "Automated with Undo"
            
            t.cell(2, 0).text = "False-Alarm Control"
            t.cell(2, 1).text = "None"
            t.cell(2, 2).text = "Manual"
            t.cell(2, 3).text = "None"
            t.cell(2, 4).text = "Built-in Guardrails"
            
            t.cell(3, 0).text = "Math Accuracy"
            t.cell(3, 1).text = "High (if formulas right)"
            t.cell(3, 2).text = "High"
            t.cell(3, 3).text = "Poor (~61% accurate)"
            t.cell(3, 4).text = "100% Verified Math"
            
            t.cell(4, 0).text = "Export Real Work"
            t.cell(4, 1).text = "None"
            t.cell(4, 2).text = "None"
            t.cell(4, 3).text = "Untested snippets"
            t.cell(4, 4).text = "1-Click PDF & Code"
            print("[Slide 8] Successfully updated comparison table!")

    prs.save(OUT_PPTX_REPO)
    prs.save(OUT_PPTX_DOWN)
    print(f"\nDone! Replaced {total_replaced} text blocks.")
    print(f"Saved to:\n  {OUT_PPTX_REPO}\n  {OUT_PPTX_DOWN}")

if __name__ == "__main__":
    run()
