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
    """Return a self-contained HTML report string."""

    now_str = datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")
    profile = profile or {}
    rows    = profile.get("rows", "—")
    cols    = profile.get("cols", "—")
    miss    = profile.get("missing_pct", "—")
    type_label = dataset_type.replace("_", " ").title()

    # ── Insight cards ────────────────────────────────────────────────────────
    cards_html = ""
    for i, ins in enumerate(insights):
        chart_block = _chart_canvas(i, ins)
        cards_html += f"""
    <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:12px;
                padding:20px;margin-bottom:16px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <h3 style="margin:0;font-size:16px;color:var(--text)">{html.escape(ins['title'])}</h3>
        {_badge(ins.get('type',''))}
      </div>
      <p style="color:var(--text-muted);font-size:14px;line-height:1.6;margin:0">
        {html.escape(ins['description'])}
      </p>
      {chart_block}
    </div>"""

    if not cards_html:
        cards_html = '<p style="color:var(--text-muted)">No significant insights found.</p>'

    # ── Stat pills ───────────────────────────────────────────────────────────
    def pill(label, value):
        return (
            f'<div style="background:var(--card-alt);border:1px solid var(--border);border-radius:8px;'
            f'padding:12px 20px;text-align:center">'
            f'<div style="color:var(--accent);font-size:22px;font-weight:700">{value}</div>'
            f'<div style="color:var(--text-muted);font-size:12px;margin-top:2px">{label}</div></div>'
        )

    pills_html = (
        pill("Rows", f"{rows:,}" if isinstance(rows, int) else rows) +
        pill("Columns", cols) +
        pill("Missing", f"{miss}%")
    )

    # ── Full HTML ─────────────────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>DataForge Report — {html.escape(dataset_name)}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&family=Inter:wght@300;400;500;700;900&family=Outfit:wght@300;400;500;700;900&family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Poppins:wght@300;400;500;700;900&family=Rajdhani:wght@500;700&display=swap');

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0 }}
    
    /* Default (Dark) CSS variables */
    :root, [data-theme="dark"] {{
      --bg: #0D0D1A;
      --card-bg: #1A1A2E;
      --card-alt: #0F172A;
      --summary-bg: #131328;
      --border: #2A2A4A;
      --text: #E2E8F0;
      --text-muted: #94A3B8;
      --accent: #6366F1;
      --accent-gradient: linear-gradient(90deg, #6366F1, #8B5CF6);
      --header-bg: linear-gradient(135deg, #1a1a3e, #0D0D1A);
    }}
    
    /* Light Theme */
    [data-theme="light"] {{
      --bg: #fafafa;
      --card-bg: #ffffff;
      --card-alt: #f1f3f5;
      --summary-bg: #f8f9fa;
      --border: #dee2e6;
      --text: #212529;
      --text-muted: #6c757d;
      --accent: #0d6efd;
      --accent-gradient: linear-gradient(90deg, #0d6efd, #6610f2);
      --header-bg: linear-gradient(135deg, #e9ecef, #f8f9fa);
    }}
    
    /* Dracula */
    [data-theme="dracula"] {{
      --bg: #282a36;
      --card-bg: #1e1f29;
      --card-alt: #282a36;
      --summary-bg: #1e1f29;
      --border: #44475a;
      --text: #f8f8f2;
      --text-muted: #6272a4;
      --accent: #bd93f9;
      --accent-gradient: linear-gradient(90deg, #bd93f9, #ff79c6);
      --header-bg: linear-gradient(135deg, #21222c, #282a36);
    }}
    
    /* Slate Blue */
    [data-theme="slate"] {{
      --bg: #1e222b;
      --card-bg: #252a34;
      --card-alt: #1e222b;
      --summary-bg: #252a34;
      --border: #303643;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --accent-gradient: linear-gradient(90deg, #38bdf8, #818cf8);
      --header-bg: linear-gradient(135deg, #252a34, #1e222b);
    }}
    
    /* Emerald Sage */
    [data-theme="emerald"] {{
      --bg: #141e1b;
      --card-bg: #1b2824;
      --card-alt: #141e1b;
      --summary-bg: #1b2824;
      --border: #273a34;
      --text: #e6f4f1;
      --text-muted: #8fa8a2;
      --accent: #10b981;
      --accent-gradient: linear-gradient(90deg, #10b981, #34d399);
      --header-bg: linear-gradient(135deg, #1b2824, #141e1b);
    }}
    
    /* Nord */
    [data-theme="nord"] {{
      --bg: #2e3440;
      --card-bg: #3b4252;
      --card-alt: #2e3440;
      --summary-bg: #3b4252;
      --border: #4c566a;
      --text: #eceff4;
      --text-muted: #d8dee9;
      --accent: #88c0d0;
      --accent-gradient: linear-gradient(90deg, #88c0d0, #81a1c1);
      --header-bg: linear-gradient(135deg, #3b4252, #2e3440);
    }}
    
    /* Luxury */
    [data-theme="luxury"] {{
      --bg: #09090b;
      --card-bg: #18181b;
      --card-alt: #09090b;
      --summary-bg: #18181b;
      --border: #27272a;
      --text: #f4f4f5;
      --text-muted: #a1a1aa;
      --accent: #d4af37;
      --accent-gradient: linear-gradient(90deg, #d4af37, #f4f4f5);
      --header-bg: linear-gradient(135deg, #18181b, #09090b);
    }}
    
    /* Cupcake */
    [data-theme="cupcake"] {{
      --bg: #faf7f5;
      --card-bg: #efeae6;
      --card-alt: #faf7f5;
      --summary-bg: #efeae6;
      --border: #d3c5ba;
      --text: #291334;
      --text-muted: #8d779b;
      --accent: #65c3c8;
      --accent-gradient: linear-gradient(90deg, #65c3c8, #fae0e4);
      --header-bg: linear-gradient(135deg, #efeae6, #faf7f5);
    }}
    
    /* Font Families */
    [data-font="inter"] {{
      --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    [data-font="outfit"] {{
      --font-family: 'Outfit', sans-serif;
    }}
    [data-font="poppins"] {{
      --font-family: 'Poppins', sans-serif;
    }}
    [data-font="roboto-mono"] {{
      --font-family: 'Roboto Mono', monospace;
    }}
    [data-font="playfair"] {{
      --font-family: 'Playfair Display', Georgia, serif;
    }}
    [data-font="rajdhani"] {{
      --font-family: 'Rajdhani', sans-serif;
    }}
    
    body, p, span, h1, h2, h3, h4, h5, h6, div, pre, td, th, table {{
      font-family: var(--font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif) !important;
    }}
    
    body {{
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
    }}
    a {{ color: var(--accent); text-decoration: none }}
  </style>
  <script id="df-theme-script">
    (function(){{
      function applyTheme(t, f){{
        if(t) {{
          document.documentElement.setAttribute('data-theme', t);
        }}
        if(f) {{
          document.documentElement.setAttribute('data-font', f);
        }}
      }}
      window.addEventListener('message', function(e){{
        if(e.data && (e.data.type === 'theme-change' || e.data.type === 'set-theme')) {{
          applyTheme(e.data.theme, e.data.font);
        }}
      }});
      try{{
        var p = window.parent;
        if(p && p !== window){{
          var t = p.document.documentElement.getAttribute('data-theme') || 'dark';
          var f = p.document.documentElement.getAttribute('data-font') || 'inter';
          applyTheme(t, f);
        }}
      }}catch(ex){{}}
    }})();
  </script>
</head>
<body>
  <!-- Header -->
  <div style="background:var(--header-bg);
              border-bottom:1px solid var(--border);padding:32px 40px">
    <div style="max-width:900px;margin:0 auto">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
        <span style="font-size:28px;font-weight:800;
                     background:var(--accent-gradient);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent">
          DataForge
        </span>
        <span style="background:rgba(99,102,241,0.12);color:var(--accent);font-size:12px;
                     padding:3px 10px;border-radius:20px;border:1px solid var(--border)">
          Automated Report
        </span>
      </div>
      <h1 style="font-size:22px;color:var(--text);font-weight:600">{html.escape(dataset_name)}</h1>
      <div style="color:var(--text-muted);font-size:13px;margin-top:4px">
        {type_label} dataset · Generated {now_str}
        {'· <span style="color:#10B981">Scheduled</span>' if scheduled else ''}
      </div>
    </div>
  </div>

  <div style="max-width:900px;margin:0 auto;padding:32px 40px">

    <!-- Stats row -->
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:32px">
      {pills_html}
    </div>

    <!-- Summary -->
    <div style="background:var(--summary-bg);border-left:4px solid var(--accent);
                border-radius:0 12px 12px 0;padding:20px 24px;margin-bottom:32px">
      <h2 style="font-size:14px;font-weight:600;color:var(--accent);
                 text-transform:uppercase;letter-spacing:1px;margin-bottom:10px">
        Executive Summary
      </h2>
      {_format_summary_html(summary_text)}
    </div>

    <!-- Insight cards -->
    <h2 style="font-size:16px;font-weight:600;color:var(--text-muted);
               text-transform:uppercase;letter-spacing:1px;margin-bottom:16px">
      Key Findings
    </h2>
    {cards_html}

    <!-- Footer -->
    <div style="border-top:1px solid var(--border);margin-top:40px;padding-top:20px;
                color:var(--text-muted);font-size:12px;text-align:center">
      Generated by DataForge Automated Reporting Engine · {now_str}
    </div>
  </div>
</body>
</html>"""
