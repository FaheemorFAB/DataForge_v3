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
    <div style="background:#1A1A2E;border:1px solid #2A2A4A;border-radius:12px;
                padding:20px;margin-bottom:16px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <h3 style="margin:0;font-size:16px;color:#E2E8F0">{html.escape(ins['title'])}</h3>
        {_badge(ins.get('type',''))}
      </div>
      <p style="color:#94A3B8;font-size:14px;line-height:1.6;margin:0">
        {html.escape(ins['description'])}
      </p>
      {chart_block}
    </div>"""

    if not cards_html:
        cards_html = '<p style="color:#64748B">No significant insights found.</p>'

    # ── Stat pills ───────────────────────────────────────────────────────────
    def pill(label, value):
        return (
            f'<div style="background:#0F172A;border:1px solid #1E293B;border-radius:8px;'
            f'padding:12px 20px;text-align:center">'
            f'<div style="color:#6366F1;font-size:22px;font-weight:700">{value}</div>'
            f'<div style="color:#64748B;font-size:12px;margin-top:2px">{label}</div></div>'
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
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0 }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0D0D1A; color: #CBD5E1; line-height: 1.6;
    }}
    a {{ color: #6366F1; text-decoration: none }}
  </style>
</head>
<body>
  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a1a3e,#0D0D1A);
              border-bottom:1px solid #1E293B;padding:32px 40px">
    <div style="max-width:900px;margin:0 auto">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
        <span style="font-size:28px;font-weight:800;
                     background:linear-gradient(90deg,#6366F1,#8B5CF6);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent">
          DataForge
        </span>
        <span style="background:#6366F120;color:#6366F1;font-size:12px;
                     padding:3px 10px;border-radius:20px;border:1px solid #6366F140">
          Automated Report
        </span>
      </div>
      <h1 style="font-size:22px;color:#E2E8F0;font-weight:600">{html.escape(dataset_name)}</h1>
      <div style="color:#64748B;font-size:13px;margin-top:4px">
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
    <div style="background:#131328;border-left:4px solid #6366F1;
                border-radius:0 12px 12px 0;padding:20px 24px;margin-bottom:32px">
      <h2 style="font-size:14px;font-weight:600;color:#6366F1;
                 text-transform:uppercase;letter-spacing:1px;margin-bottom:10px">
        Executive Summary
      </h2>
      {_format_summary_html(summary_text)}
    </div>

    <!-- Insight cards -->
    <h2 style="font-size:16px;font-weight:600;color:#94A3B8;
               text-transform:uppercase;letter-spacing:1px;margin-bottom:16px">
      Key Findings
    </h2>
    {cards_html}

    <!-- Footer -->
    <div style="border-top:1px solid #1E293B;margin-top:40px;padding-top:20px;
                color:#334155;font-size:12px;text-align:center">
      Generated by DataForge Automated Reporting Engine · {now_str}
    </div>
  </div>
</body>
</html>"""
