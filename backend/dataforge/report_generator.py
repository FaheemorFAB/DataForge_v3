import html
import json
from datetime import datetime


def _format_summary_html(text: str) -> str:
    """
    Convert a summary string to formatted HTML for the report body.

    Handles two formats:
      - Numbered-list fallback:  "1. Title — Description\n2. ..."
      - Gemini prose paragraph:  free-form text (may contain newlines)
    """
    import re
    if not text or not text.strip():
        return '<p style="color:#64748B">No summary available.</p>'

    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    is_numbered = bool(lines and re.match(r"^\d+[.)\s]", lines[0]))

    if is_numbered:
        parts = []
        for line in lines:
            m = re.match(r"^(\d+)[.)\s]+(.+)$", line)
            if not m:
                continue
            num  = m.group(1)
            body = m.group(2).strip()
            dash = body.find(" \u2014 ")
            if dash != -1:
                title = body[:dash].strip()
                desc  = body[dash + 3:].strip()
            else:
                dot = body.find(". ")
                if dot != -1 and dot < 120:
                    title = body[:dot].strip()
                    desc  = body[dot + 2:].strip()
                else:
                    title, desc = body, ""

            num_badge = (
                '<span style="flex-shrink:0;width:22px;height:22px;border-radius:50%;'
                'background:#6366F1;color:#fff;font-size:10px;font-weight:800;'
                'display:flex;align-items:center;justify-content:center;margin-top:1px">'
                + num + '</span>'
            )
            title_html = '<span style="font-weight:700;font-size:13px;color:#E2E8F0">' + html.escape(title) + '.</span>'
            desc_html  = (' <span style="font-size:13px;color:#94A3B8">' + html.escape(desc) + '</span>') if desc else ''
            row = (
                '<div style="display:flex;gap:12px;align-items:flex-start;'
                'padding:10px 0;border-bottom:1px solid #1E293B;">'
                + num_badge
                + '<div>' + title_html + desc_html + '</div></div>'
            )
            parts.append(row)
        return '<div style="display:flex;flex-direction:column">' + ''.join(parts) + '</div>'

    # Plain prose — convert newlines to paragraphs
    paras = re.split(r"\n{2,}", text.strip())
    result = ""
    for p in paras:
        if p.strip():
            result += '<p style="color:#CBD5E1;font-size:15px;line-height:1.75;margin-bottom:10px">' + html.escape(p.replace("\n", " ").strip()) + '</p>'
    return result


# ── Chart colour palette ──────────────────────────────────────────────────────
CHART_COLOURS = [
    "#6366F1", "#10B981", "#F59E0B", "#EF4444",
    "#3B82F6", "#EC4899", "#14B8A6", "#8B5CF6",
]

TYPE_BADGES = {
    "trend":        ("#6366F1", "Trend"),
    "ranking":      ("#10B981", "Ranking"),
    "correlation":  ("#F59E0B", "Correlation"),
    "anomaly":      ("#EF4444", "Anomaly"),
    "distribution": ("#3B82F6", "Distribution"),
    "contribution": ("#14B8A6", "Contribution"),
    "segment":      ("#8B5CF6", "Segment"),
    "change":       ("#EC4899", "Change"),
    "profile":      ("#475569", "Profile"),
}


def _badge(insight_type: str) -> str:
    colour, label = TYPE_BADGES.get(insight_type, ("#6366F1", insight_type.title()))
    return (
        f'<span style="background:{colour};color:#fff;font-size:11px;font-weight:600;'
        f'padding:2px 8px;border-radius:12px;letter-spacing:0.5px">{html.escape(label)}</span>'
    )


def _chart_canvas(idx: int, insight: dict) -> str:
    """Returns a Chart.js canvas block for an insight that has chart data."""
    cd    = insight.get("chart_data") or {}
    ctype = insight.get("chart")

    if ctype == "scatter":
        xs     = cd.get("x", [])
        ys     = cd.get("y", [])
        points = json.dumps([{"x": x, "y": y} for x, y in zip(xs, ys)])
        data_js = (
            f"{{datasets:[{{label:'',data:{points},"
            f"backgroundColor:'{CHART_COLOURS[idx % len(CHART_COLOURS)]}40',"
            f"borderColor:'{CHART_COLOURS[idx % len(CHART_COLOURS)]}',"
            f"pointRadius:3}}]}}"
        )
        opts_js = "{scales:{x:{title:{display:true,text:" + json.dumps(cd.get("x_label", "x")) + "}},y:{title:{display:true,text:" + json.dumps(cd.get("y_label", "y")) + "}}}}"
        chart_type = "scatter"

    elif ctype in ("bar", "histogram"):
        labels  = cd.get("labels", [])
        values  = cd.get("values", [])
        colour  = CHART_COLOURS[idx % len(CHART_COLOURS)]
        lbl_js  = json.dumps(labels)
        val_js  = json.dumps(values)
        data_js = (
            f"{{labels:{lbl_js},"
            f"datasets:[{{label:{json.dumps(str(insight.get('metric', '')))},data:{val_js},"
            f"backgroundColor:'{colour}80',borderColor:'{colour}',borderWidth:1}}]}}"
        )
        opts_js = "{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}"
        chart_type = "bar"

    elif ctype == "line":
        labels  = cd.get("labels", [])
        values  = cd.get("values", [])
        colour  = CHART_COLOURS[idx % len(CHART_COLOURS)]
        # Truncate labels for readability
        short   = [l[-10:] if len(l) > 10 else l for l in labels]
        lbl_js  = json.dumps(short)
        val_js  = json.dumps(values)
        data_js = (
            f"{{labels:{lbl_js},"
            f"datasets:[{{label:{json.dumps(str(insight.get('metric', '')))},data:{val_js},"
            f"borderColor:'{colour}',backgroundColor:'{colour}20',"
            f"tension:0.3,fill:true,pointRadius:2}}]}}"
        )
        opts_js = "{plugins:{legend:{display:false}},scales:{y:{beginAtZero:false}}}"
        chart_type = "line"

    else:
        return ""

    return f"""
      <div style="margin-top:16px;height:220px">
        <canvas id="chart_{idx}"></canvas>
      </div>
      <script>
        (function(){{
          var ctx = document.getElementById('chart_{idx}').getContext('2d');
          new Chart(ctx, {{type:'{chart_type}',data:{data_js},options:{opts_js}}});
        }})();
      </script>"""


def generate_html_report(
    insights: list[dict],
    summary_text: str,
    dataset_name: str = "Dataset",
    dataset_type: str = "general",
    profile: dict | None = None,
    scheduled: bool = False,
) -> str:
    """Return a landscape slide-deck presentation HTML report."""

    now_str = datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")
    profile = profile or {}
    rows    = profile.get("rows", "—")
    cols    = profile.get("cols", "—")
    miss    = profile.get("missing_pct", "—")
    type_label = dataset_type.replace("_", " ").title()

    # Retrieve slide commentary from profile
    slide1 = profile.get("slide1", "")
    slide2 = profile.get("slide2", "")
    slide3 = profile.get("slide3", "")
    slide4 = profile.get("slide4", "")

    # Fallback splitting if slides are empty
    if not slide1 and summary_text:
        slide1 = summary_text
    if not slide2:
        slide2 = "Critical patterns reveal stable correlations and distributions across numerical metrics. Outliers should be investigated for operational deviation."
    if not slide3:
        slide3 = f"Data health review points to a well-structured dataset. Missing cell footprint is low ({miss}%), indicating high database logging reliability."
    if not slide4:
        slide4 = "1. Maintain continuous anomaly checks on key metrics.\n2. Leverage top performing dimensions for product optimization.\n3. Automate weekly dashboard updates to track changes in real-time."

    # Format insights into a 3-column deck cards
    insights_html = ""
    for idx, ins in enumerate(insights[:6]): # Show top 6 insights on Slide 3
        colour, label = TYPE_BADGES.get(ins.get('type', ''), ("#6366F1", ins.get('type', '').title()))
        insights_html += f"""
        <div style="background:rgba(30, 41, 59, 0.4);border:1px solid #1e293b;border-radius:8px;padding:12px 15px;display:flex;flex-direction:column;justify-content:space-between">
          <div>
            <div style="display:flex;justify-content:between;align-items:center;margin-bottom:6px">
              <span style="font-size:10px;font-weight:800;color:#fff;background:{colour};padding:1px 6px;border-radius:8px">{html.escape(label)}</span>
              <span style="font-size:10px;color:#64748b;margin-left:auto">Imp: {int(ins.get('importance', 0)*100)}%</span>
            </div>
            <h4 style="font-size:12px;font-weight:700;color:#f8fafc;margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{html.escape(ins.get('title', ''))}</h4>
            <p style="font-size:10px;color:#94a3b8;line-height:1.4;margin:0">{html.escape(ins.get('description', ''))}</p>
          </div>
        </div>"""
    
    if not insights_html:
        insights_html = '<p style="color:#64748b;font-size:11px">No algorithmic findings detected.</p>'

    # Format column list for Slide 4
    cols_html = ""
    cols_list = profile.get("columns", [])
    if not cols_list and isinstance(profile.get("metrics"), list):
        cols_list = profile.get("metrics") + profile.get("dimensions", [])
    
    if cols_list:
        cols_html = "".join(f'<span style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);padding:4px 8px;border-radius:4px;font-size:10px;font-family:monospace;color:#38bdf8">{html.escape(str(c))}</span>' for c in cols_list[:12])
        if len(cols_list) > 12:
            cols_html += f'<span style="color:#64748b;font-size:10px;padding-top:4px">+{len(cols_list)-12} more</span>'
    else:
        cols_html = '<span style="color:#64748b;font-size:10px">No columns metadata available.</span>'

    # Build PDF / Presentation HTML
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DataForge Business Analysis Presentation — {html.escape(dataset_name)}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;700;900&family=Outfit:wght@300;400;500;700;900&display=swap');
    
    @page {{
      size: A4 landscape;
      margin: 0;
    }}
    
    @media print {{
      body {{
        background: #090d16 !important;
      }}
      .slide {{
        page-break-after: always;
        page-break-inside: avoid;
        box-shadow: none !important;
        border: none !important;
        border-radius: 0 !important;
      }}
      .slide-deck {{
        padding: 0 !important;
        gap: 0 !important;
      }}
    }}
    
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    
    body {{
      background: #05070f;
      color: #e2e8f0;
      font-family: 'Outfit', 'Inter', -apple-system, sans-serif;
      padding: 0;
      margin: 0;
    }}
    
    .slide-deck {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 35px;
      padding: 40px;
    }}
    
    .slide {{
      width: 297mm;
      height: 210mm;
      background: #090d16;
      background-image: radial-gradient(circle at 5% 10%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
                        radial-gradient(circle at 95% 90%, rgba(20, 184, 166, 0.06) 0%, transparent 40%);
      border: 1px solid #1e293b;
      border-radius: 20px;
      padding: 45px 55px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 20px 50px rgba(0,0,0,0.6);
      overflow: hidden;
      box-sizing: border-box;
    }}
    
    .slide-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      border-bottom: 2px solid #1e293b;
      padding-bottom: 12px;
      flex-shrink: 0;
    }}
    
    .slide-title {{
      font-size: 24px;
      font-weight: 800;
      color: #f8fafc;
      letter-spacing: -0.5px;
    }}
    
    .slide-subtitle {{
      font-size: 10px;
      color: #38bdf8;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      font-weight: 700;
    }}
    
    .slide-body {{
      flex: 1;
      margin-top: 25px;
      margin-bottom: 25px;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      min-height: 0;
    }}
    
    .slide-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 9px;
      color: #64748b;
      border-top: 1px solid #1e293b;
      padding-top: 10px;
      flex-shrink: 0;
    }}
    
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 15px;
      margin-bottom: 20px;
    }}
    
    .kpi-card {{
      background: rgba(30, 41, 59, 0.4);
      border: 1px solid #1e293b;
      border-radius: 12px;
      padding: 16px;
      text-align: center;
    }}
    
    .kpi-val {{
      font-size: 26px;
      font-weight: 900;
      color: #38bdf8;
    }}
    
    .kpi-lbl {{
      font-size: 9px;
      color: #94a3b8;
      text-transform: uppercase;
      margin-top: 4px;
      letter-spacing: 0.5px;
    }}
    
    .commentary-box {{
      background: rgba(99, 102, 241, 0.04);
      border-left: 4px solid #6366f1;
      border-radius: 0 12px 12px 0;
      padding: 16px 20px;
      margin-top: 5px;
      flex: 1;
      min-height: 0;
      overflow-y: auto;
    }}
    
    .commentary-title {{
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #818cf8;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    
    .commentary-text {{
      font-size: 12.5px;
      line-height: 1.6;
      color: #cbd5e1;
    }}
    
    .grid-2col {{
      display: grid;
      grid-template-columns: 1fr 1.1fr;
      gap: 25px;
      flex: 1;
      min-height: 0;
    }}
    
    .rec-item {{
      background: rgba(30, 41, 59, 0.3);
      border: 1px solid #1e293b;
      border-radius: 10px;
      padding: 12px 15px;
      display: flex;
      gap: 15px;
      align-items: flex-start;
    }}
    
    .rec-num {{
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: #10b981;
      color: #fff;
      font-size: 11px;
      font-weight: 900;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}
  </style>
</head>
<body>

  <div class="slide-deck">

    <!-- ── SLIDE 1: COVER SLIDE ──────────────────────────────────────── -->
    <div class="slide" id="slide-1">
      <div style="text-align:left">
        <span style="background:rgba(99,102,241,0.12);color:#818cf8;font-size:10px;padding:3px 10px;border-radius:20px;border:1px solid #1e293b;font-weight:700;letter-spacing:1px">
          CORPORATE ADVISORY DECK
        </span>
      </div>
      
      <div style="margin:40px 0">
        <h1 style="font-size:42px;font-weight:900;line-height:1.15;color:#f8fafc;letter-spacing:-1px">
          DataForge Business Analysis <br>
          <span style="background:linear-gradient(90deg, #38bdf8, #818cf8, #2dd4bf);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
            Strategic Performance Report
          </span>
        </h1>
        <p style="color:#94a3b8;font-size:15px;margin-top:15px;max-width:650px;line-height:1.6">
          A high-fidelity slide deck analyzing the dataset metrics, key algorithmic findings, operational data quality alerts, and recommendations for strategic execution.
        </p>
      </div>
      
      <div style="display:flex;align-items:center;justify-content:space-between;background:rgba(30, 41, 59, 0.4);border:1px solid #1e293b;padding:15px 25px;border-radius:12px">
        <div>
          <span style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px;display:block">Target Dataset</span>
          <span style="font-size:13px;font-weight:700;color:#f8fafc">{html.escape(dataset_name)}</span>
        </div>
        <div>
          <span style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px;display:block">Dataset Category</span>
          <span style="font-size:11px;font-weight:700;color:#2dd4bf;background:rgba(45,212,191,0.1);padding:2px 8px;border-radius:8px">{type_label}</span>
        </div>
        <div>
          <span style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px;display:block">Analysis Date</span>
          <span style="font-size:12px;font-weight:700;color:#e2e8f0">{now_str.split()[0]}</span>
        </div>
      </div>
      
      <div class="slide-footer">
        <span>DataForge Automated Reporting</span>
        <span>Slide 1 of 5</span>
      </div>
    </div>

    <!-- ── SLIDE 2: KPI & EXECUTIVE SUMMARY ──────────────────────────── -->
    <div class="slide" id="slide-2">
      <div class="slide-header">
        <div>
          <h2 class="slide-title">Executive Summary</h2>
          <span class="slide-subtitle">Business Performance Metrics & Key indicators</span>
        </div>
        <span style="font-size:9px;color:#64748b">PROJECT: {html.escape(dataset_name)}</span>
      </div>
      
      <div class="slide-body">
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-val">{f"{rows:,}" if isinstance(rows, int) else rows}</div>
            <div class="kpi-lbl">Total Records</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val">{cols}</div>
            <div class="kpi-lbl">Total Dimensions</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val" style="color:{'#ef4444' if isinstance(miss,(int,float)) and miss > 10 else '#10b981'}">{miss}%</div>
            <div class="kpi-lbl">Missing Cells</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val" style="color:#2dd4bf">{len(insights)}</div>
            <div class="kpi-lbl">Detected Insights</div>
          </div>
        </div>
        
        <div class="commentary-box">
          <div class="commentary-title">AI Business Summary & Potential</div>
          <div class="commentary-text">{html.escape(slide1)}</div>
        </div>
      </div>
      
      <div class="slide-footer">
        <span>DataForge Automated Reporting</span>
        <span>Slide 2 of 5</span>
      </div>
    </div>

    <!-- ── SLIDE 3: STRATEGIC PATTERNS & INSIGHTS ─────────────────────── -->
    <div class="slide" id="slide-3">
      <div class="slide-header">
        <div>
          <h2 class="slide-title">Strategic Insights</h2>
          <span class="slide-subtitle">Algorithmic findings from the insight engine</span>
        </div>
        <span style="font-size:9px;color:#64748b">QUANTIFIED PATTERNS</span>
      </div>
      
      <div class="slide-body">
        <div class="grid-2col">
          <div style="display:grid;grid-template-rows:repeat(3, 1fr);gap:10px">
            {insights_html}
          </div>
          <div class="commentary-box" style="margin-top:0">
            <div class="commentary-title">Strategic Patterns Commentary</div>
            <div class="commentary-text" style="font-size:12px">{html.escape(slide2)}</div>
          </div>
        </div>
      </div>
      
      <div class="slide-footer">
        <span>DataForge Automated Reporting</span>
        <span>Slide 3 of 5</span>
      </div>
    </div>

    <!-- ── SLIDE 4: DATA HEALTH & QUALITY ALERTS ──────────────────────── -->
    <div class="slide" id="slide-4">
      <div class="slide-header">
        <div>
          <h2 class="slide-title">Data Quality & Profiling</h2>
          <span class="slide-subtitle">YData structural validation & health status</span>
        </div>
        <span style="font-size:9px;color:#64748b">HEALTH DIAGNOSTICS</span>
      </div>
      
      <div class="slide-body">
        <div class="grid-2col">
          <div style="background:rgba(30, 41, 59, 0.2);border:1px solid #1e293b;border-radius:12px;padding:20px;display:flex;flex-direction:column;gap:15px">
            <div>
              <span style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:5px">Quality Verification</span>
              <div style="display:flex;align-items:center;gap:10px">
                <div style="width:12px;height:12px;border-radius:50%;background:{'#ef4444' if isinstance(miss,(int,float)) and miss > 10 else '#10b981'}"></div>
                <span style="font-size:13px;font-weight:700;color:#fff">
                  { 'Critical Quality Warnings' if isinstance(miss,(int,float)) and miss > 10 else 'Optimal Database Health Status' }
                </span>
              </div>
            </div>
            
            <div>
              <span style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:8px">Dataset Schema Columns</span>
              <div style="display:flex;flex-wrap:wrap;gap:5px;max-height:100px;overflow-y:auto">
                {cols_html}
              </div>
            </div>
          </div>
          
          <div class="commentary-box" style="margin-top:0">
            <div class="commentary-title">Data Health & Profiling Commentary</div>
            <div class="commentary-text">{html.escape(slide3)}</div>
          </div>
        </div>
      </div>
      
      <div class="slide-footer">
        <span>DataForge Automated Reporting</span>
        <span>Slide 4 of 5</span>
      </div>
    </div>

    <!-- ── SLIDE 5: STRATEGIC RECOMMENDATIONS ─────────────────────────── -->
    <div class="slide" id="slide-5">
      <div class="slide-header">
        <div>
          <h2 class="slide-title">Actionable Recommendations</h2>
          <span class="slide-subtitle">Strategic next steps for business leaders</span>
        </div>
        <span style="font-size:9px;color:#64748b">EXECUTION ROADMAP</span>
      </div>
      
      <div class="slide-body">
        <div class="grid-2col">
          <div style="display:flex;flex-direction:column;gap:10px">
            <div class="rec-item">
              <div class="rec-num" style="background:#6366f1">1</div>
              <div>
                <h4 style="font-size:12px;font-weight:700;color:#f8fafc;margin-bottom:2px">Implement Real-time Monitoring</h4>
                <p style="font-size:10.5px;color:#94a3b8;line-height:1.4">Configure alerts on crucial spikes or drops in business dimensions.</p>
              </div>
            </div>
            <div class="rec-item">
              <div class="rec-num" style="background:#2dd4bf">2</div>
              <div>
                <h4 style="font-size:12px;font-weight:700;color:#f8fafc;margin-bottom:2px">Optimize Data Capture Quality</h4>
                <p style="font-size:10.5px;color:#94a3b8;line-height:1.4">Address dimensions with high missingness percentage to stabilize predictive runs.</p>
              </div>
            </div>
            <div class="rec-item">
              <div class="rec-num" style="background:#10b981">3</div>
              <div>
                <h4 style="font-size:12px;font-weight:700;color:#f8fafc;margin-bottom:2px">Run Periodic AutoML Audits</h4>
                <p style="font-size:10.5px;color:#94a3b8;line-height:1.4">Evaluate model feature importance updates as new dataset batches arrive.</p>
              </div>
            </div>
          </div>
          
          <div class="commentary-box" style="margin-top:0">
            <div class="commentary-title">Recommendations Commentary</div>
            <div class="commentary-text">{html.escape(slide4)}</div>
          </div>
        </div>
      </div>
      
      <div class="slide-footer">
        <span>DataForge Automated Reporting</span>
        <span>Slide 5 of 5</span>
      </div>
    </div>

  </div>

</body>
</html>"""
