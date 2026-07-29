import html
import json
import math
from datetime import datetime

# ── Color Palette & Light Royalty Theme Constants ─────────────────────────────
ROYAL_GOLD = "#D97706"
ROYAL_INDIGO = "#4F46E5"
ROYAL_EMERALD = "#059669"
ROYAL_ROSE = "#E11D48"
ROYAL_CYAN = "#0891B2"
ROYAL_VIOLET = "#7C3AED"

TYPE_BADGES = {
    "trend":              ("#4F46E5", "Trend 📈"),
    "ranking":            ("#059669", "Ranking 🏆"),
    "top_performer":      ("#059669", "Top Performer 🏆"),
    "correlation":        ("#D97706", "Correlation 🔗"),
    "anomaly":            ("#E11D48", "Anomaly Alert 🚨"),
    "distribution":       ("#2563EB", "Distribution 📊"),
    "contribution":       ("#0D9488", "Contribution 🍩"),
    "segment":            ("#7C3AED", "Segment 🎯"),
    "change":             ("#DB2777", "Period Change ⚡"),
    "data_quality":       ("#16A34A", "Data Quality 🛡️"),
    "feature_importance": ("#EA580C", "Feature Impact ⚡"),
    "outlier_summary":    ("#DC2626", "Outlier Sweep ⚠️"),
    "numeric_summary":    ("#9333EA", "Numeric Metric 📐"),
    "categorical":        ("#0D9488", "Category Share 🏷️"),
    "profile":            ("#475569", "Dataset Profile 📋"),
}

CHART_PALETTE = [
    "#4f46e5", "#059669", "#d97706", "#e11d48", "#7c3aed",
    "#0891b2", "#db2777", "#ea580c", "#65a30d", "#0d9488"
]

def _fmt_num(v: float) -> str:
    """Format large numbers cleanly with K/M suffixes."""
    try:
        val = float(v)
        if math.isnan(val):
            return "0"
        abs_v = abs(val)
        if abs_v >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        if abs_v >= 1_000:
            return f"{val / 1_000:.1f}K"
        return f"{val:.1f}" if val % 1 != 0 else str(int(val))
    except Exception:
        return str(v)


# =============================================================================
#  PURE PYTHON SVG VECTOR CHART ENGINE (LIGHT THEME VECTOR GRAPHICS)
# =============================================================================

def _render_svg_line(labels: list, values: list, color: str = "#4f46e5", height: int = 150) -> str:
    """Renders a vector SVG line chart with light gradient area fill."""
    if not values or len(values) < 2:
        return ""
    
    width = 380
    pad_top, pad_bot, pad_left, pad_right = 20, 25, 35, 15
    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bot

    try:
        num_vals = [float(v) for v in values if v is not None and not math.isnan(float(v))]
        if not num_vals:
            return ""
        min_v, max_v = min(num_vals), max(num_vals)
    except Exception:
        return ""

    val_range = (max_v - min_v) if max_v != min_v else 1.0
    n = len(values)

    points = []
    for i, v in enumerate(num_vals):
        x = pad_left + (i / (n - 1 if n > 1 else 1)) * chart_w
        y = pad_top + chart_h - ((v - min_v) / val_range) * chart_h
        points.append((x, y))

    path_d = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
    for i in range(1, len(points)):
        p0 = points[i-1]
        p1 = points[i]
        cx1 = p0[0] + (p1[0] - p0[0]) * 0.4
        cx2 = p1[0] - (p1[0] - p0[0]) * 0.4
        path_d += f" C {cx1:.1f} {p0[1]:.1f}, {cx2:.1f} {p1[1]:.1f}, {p1[0]:.1f} {p1[1]:.1f}"

    area_d = path_d + f" L {points[-1][0]:.1f} {height - pad_bot} L {points[0][0]:.1f} {height - pad_bot} Z"
    grad_id = f"line_grad_light_{abs(hash(color)) % 10000}"
    
    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px">
      <defs>
        <linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="{color}" stop-opacity="0.20"/>
          <stop offset="100%" stop-color="{color}" stop-opacity="0.01"/>
        </linearGradient>
      </defs>
      <!-- Grid lines -->
      <line x1="{pad_left}" y1="{pad_top}" x2="{width - pad_right}" y2="{pad_top}" stroke="#E2E8F0" stroke-dasharray="3 3"/>
      <line x1="{pad_left}" y1="{height - pad_bot}" x2="{width - pad_right}" y2="{height - pad_bot}" stroke="#CBD5E1"/>
      
      <!-- Area & Line -->
      <path d="{area_d}" fill="url(#{grad_id})"/>
      <path d="{path_d}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>
      
      <!-- Dots -->
      {"".join([f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#ffffff" stroke="{color}" stroke-width="2"/>' for x, y in points[::max(1, len(points)//8)]])}
      
      <!-- Labels -->
      <text x="{pad_left - 5}" y="{pad_top + 4}" fill="#64748B" font-size="9px" text-anchor="end" font-family="sans-serif">{_fmt_num(max_v)}</text>
      <text x="{pad_left - 5}" y="{height - pad_bot}" fill="#64748B" font-size="9px" text-anchor="end" font-family="sans-serif">{_fmt_num(min_v)}</text>
    </svg>"""
    return svg


def _render_svg_bar(labels: list, values: list, color: str = "#059669", height: int = 150, horizontal: bool = True) -> str:
    """Renders ranked vector SVG bar chart in light theme."""
    if not values:
        return ""
    
    width = 380
    pad_left = 90 if horizontal else 35
    pad_right = 45 if horizontal else 15
    pad_top = 15
    pad_bot = 25
    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bot

    num_vals = [float(v) for v in values[:6]]
    str_lbls = [str(l)[:12] for l in labels[:6]]
    max_v = max(num_vals) if num_vals and max(num_vals) > 0 else 1.0

    svg_parts = []
    
    if horizontal:
        bar_h = min(18, (chart_h / len(num_vals)) - 6)
        for i, (lbl, val) in enumerate(zip(str_lbls, num_vals)):
            y = pad_top + i * (bar_h + 6)
            bw = max(4, (val / max_v) * chart_w)
            c = CHART_PALETTE[i % len(CHART_PALETTE)]
            svg_parts.append(f"""
              <text x="{pad_left - 8}" y="{y + bar_h*0.75:.1f}" fill="#475569" font-size="9.5px" font-weight="600" text-anchor="end" font-family="sans-serif">{html.escape(lbl)}</text>
              <rect x="{pad_left}" y="{y:.1f}" width="{bw:.1f}" height="{bar_h:.1f}" rx="3" fill="{c}" opacity="0.9"/>
              <text x="{pad_left + bw + 6:.1f}" y="{y + bar_h*0.75:.1f}" fill="#1E293B" font-size="9px" font-weight="bold" font-family="sans-serif">{_fmt_num(val)}</text>
            """)
    else:
        bar_w = min(24, (chart_w / len(num_vals)) - 6)
        for i, (lbl, val) in enumerate(zip(str_lbls, num_vals)):
            bh = max(4, (val / max_v) * chart_h)
            x = pad_left + i * (bar_w + 6)
            y = pad_top + chart_h - bh
            c = CHART_PALETTE[i % len(CHART_PALETTE)]
            svg_parts.append(f"""
              <rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="3" fill="{c}" opacity="0.9"/>
              <text x="{x + bar_w/2:.1f}" y="{height - 8}" fill="#64748B" font-size="8.5px" text-anchor="middle" font-family="sans-serif">{html.escape(lbl)}</text>
              <text x="{x + bar_w/2:.1f}" y="{y - 4:.1f}" fill="#1E293B" font-size="8.5px" font-weight="bold" text-anchor="middle" font-family="sans-serif">{_fmt_num(val)}</text>
            """)

    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px">
      {"".join(svg_parts)}
    </svg>"""
    return svg


def _render_svg_donut(labels: list, values: list, height: int = 150) -> str:
    """Renders vector SVG Donut chart in light theme."""
    if not values:
        return ""
    
    width = 380
    cx, cy, r_outer, r_inner = 80, height // 2, 45, 26
    total = sum(abs(float(v)) for v in values if v is not None)
    if total == 0:
        return ""

    slices = []
    current_angle = -90.0

    for i, (lbl, val) in enumerate(zip(labels[:5], values[:5])):
        v = abs(float(val))
        pct = (v / total)
        angle = pct * 360.0
        
        a0 = math.radians(current_angle)
        a1 = math.radians(current_angle + angle)
        current_angle += angle

        x0_o = cx + r_outer * math.cos(a0)
        y0_o = cy + r_outer * math.sin(a0)
        x1_o = cx + r_outer * math.cos(a1)
        y1_o = cy + r_outer * math.sin(a1)

        x0_i = cx + r_inner * math.cos(a1)
        y0_i = cy + r_inner * math.sin(a1)
        x1_i = cx + r_inner * math.cos(a0)
        y1_i = cy + r_inner * math.sin(a0)

        large_arc = 1 if angle > 180 else 0
        color = CHART_PALETTE[i % len(CHART_PALETTE)]

        path_d = (
            f"M {x0_o:.1f} {y0_o:.1f} "
            f"A {r_outer} {r_outer} 0 {large_arc} 1 {x1_o:.1f} {y1_o:.1f} "
            f"L {x0_i:.1f} {y0_i:.1f} "
            f"A {r_inner} {r_inner} 0 {large_arc} 0 {x1_i:.1f} {y1_i:.1f} Z"
        )
        
        slices.append(f'<path d="{path_d}" fill="{color}" opacity="0.95"/>')

    legend_items = []
    for i, (lbl, val) in enumerate(zip(labels[:5], values[:5])):
        v = abs(float(val))
        pct_str = f"{(v / total * 100):.1f}%"
        c = CHART_PALETTE[i % len(CHART_PALETTE)]
        ly = 25 + i * 22
        legend_items.append(f"""
          <rect x="160" y="{ly}" width="10" height="10" rx="2" fill="{c}"/>
          <text x="178" y="{ly + 9}" fill="#334155" font-size="9.5px" font-weight="600" font-family="sans-serif">{html.escape(str(lbl)[:15])}</text>
          <text x="360" y="{ly + 9}" fill="#64748B" font-size="9px" font-weight="bold" text-anchor="end" font-family="sans-serif">{pct_str}</text>
        """)

    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px">
      <g>{"".join(slices)}</g>
      <circle cx="{cx}" cy="{cy}" r="{r_inner-2}" fill="#FFFFFF"/>
      <g>{"".join(legend_items)}</g>
    </svg>"""
    return svg


def _render_svg_scatter(xs: list, ys: list, color: str = "#d97706", height: int = 150) -> str:
    """Renders vector SVG scatter plot in light theme."""
    if not xs or not ys:
        return ""
    
    width = 380
    pad_left, pad_right, pad_top, pad_bot = 35, 15, 20, 25
    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bot

    try:
        pts = [(float(x), float(y)) for x, y in zip(xs, ys) if x is not None and y is not None]
        if not pts:
            return ""
        min_x, max_x = min(p[0] for p in pts), max(p[0] for p in pts)
        min_y, max_y = min(p[1] for p in pts), max(p[1] for p in pts)
    except Exception:
        return ""

    range_x = (max_x - min_x) if max_x != min_x else 1.0
    range_y = (max_y - min_y) if max_y != min_y else 1.0

    circle_elements = []
    for x_val, y_val in pts[:40]:
        cx = pad_left + ((x_val - min_x) / range_x) * chart_w
        cy = pad_top + chart_h - ((y_val - min_y) / range_y) * chart_h
        circle_elements.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{color}" fill-opacity="0.7" stroke="{color}" stroke-width="1"/>')

    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px">
      <line x1="{pad_left}" y1="{height - pad_bot}" x2="{width - pad_right}" y2="{height - pad_bot}" stroke="#CBD5E1"/>
      <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{height - pad_bot}" stroke="#CBD5E1"/>
      {"".join(circle_elements)}
    </svg>"""
    return svg


def _render_insight_svg(ins: dict) -> str:
    """Dispatches insight chart_data to the appropriate vector SVG renderer."""
    cd = ins.get("chart_data") or {}
    ctype = ins.get("chart")
    itype = ins.get("type")
    
    labels = cd.get("labels", [])
    values = cd.get("values", [])

    if itype == "trend" or ctype == "line":
        return _render_svg_line(labels, values, color="#4f46e5")
    
    if itype in ("contribution", "categorical") or ctype == "donut":
        return _render_svg_donut(labels, values)

    if itype == "correlation" or ctype == "scatter":
        xs = cd.get("x", labels)
        ys = cd.get("y", values)
        return _render_svg_scatter(xs, ys, color="#d97706")

    if itype in ("ranking", "top_performer", "feature_importance", "segment", "data_quality", "outlier_summary"):
        return _render_svg_bar(labels, values, color="#059669", horizontal=True)

    if labels and values:
        return _render_svg_bar(labels, values, color="#2563eb", horizontal=False)

    return ""


# =============================================================================
#  CORPORATE LIGHT ROYALTY EXECUTIVE SLIDE DECK GENERATOR
# =============================================================================

def generate_html_report(
    insights: list[dict],
    summary_text: str,
    dataset_name: str = "Dataset",
    dataset_type: str = "general",
    profile: dict | None = None,
    scheduled: bool = False,
) -> str:
    """
    Generates a McKinsey-grade Executive Presentation Deck & PDF report
    with a clean, crisp WHITE background theme, corporate typography, and vector SVG charts.
    """
    now_str = datetime.utcnow().strftime("%B %d, %Y")
    profile = profile or {}
    rows = profile.get("rows", "—")
    cols = profile.get("cols", "—")
    miss = profile.get("missing_pct", "0.0")
    type_label = dataset_type.replace("_", " ").title()

    slide1 = profile.get("slide1") or summary_text or f"Executive analysis of '{dataset_name}' dataset."
    slide2 = profile.get("slide2") or "Critical pattern analysis highlights key distributional drivers and metric correlations."
    slide3 = profile.get("slide3") or f"Data profiling confirms dataset structure with {miss}% missing cell footprint."
    slide4 = profile.get("slide4") or "1. Implement automated anomaly alerts.\n2. Optimize key driver metrics.\n3. Schedule recurring executive updates."

    # Render Insight Cards with Embedded SVG Charts
    insight_cards_html = ""
    for idx, ins in enumerate(insights[:6]):
        badge_color, badge_label = TYPE_BADGES.get(ins.get("type", ""), ("#4f46e5", ins.get("type", "Insight").title()))
        svg_chart = _render_insight_svg(ins)
        imp = int(ins.get("importance", 0.5) * 100)

        insight_cards_html += f"""
        <div class="insight-royalty-card">
          <div class="card-top flex-between">
            <span class="badge-royalty" style="background:{badge_color}14;color:{badge_color};border:1px solid {badge_color}30;">
              {html.escape(badge_label)}
            </span>
            <span class="imp-pill">Impact {imp}%</span>
          </div>
          <h4 class="card-title">{html.escape(ins.get("title", ""))}</h4>
          <p class="card-desc">{html.escape(ins.get("description", ""))}</p>
          {f'<div class="svg-container">{svg_chart}</div>' if svg_chart else ''}
        </div>"""

    if not insight_cards_html:
        insight_cards_html = '<p class="empty-state">No algorithmic insights flagged for this dataset.</p>'

    # Columns metadata grid
    cols_list = profile.get("columns", [])
    cols_pills = "".join(f'<span class="col-pill">{html.escape(str(c))}</span>' for c in cols_list[:14])
    if len(cols_list) > 14:
        cols_pills += f'<span class="col-pill overflow">+{len(cols_list)-14} more</span>'

    # FULL EXECUTIVE CORPORATE WHITE THEME HTML & CSS
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DataForge Executive Report — {html.escape(dataset_name)}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700&display=swap');

    @page {{
      size: A4 landscape;
      margin: 0;
    }}

    @media print {{
      body {{ background: #F1F5F9 !important; -webkit-print-color-adjust: exact; }}
      .slide {{ page-break-after: always; page-break-inside: avoid; box-shadow: none !important; border: 1px solid #CBD5E1 !important; }}
      .deck-wrapper {{ padding: 0 !important; gap: 0 !important; }}
    }}

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #E2E8F0;
      color: #1E293B;
      font-family: 'Inter', -apple-system, sans-serif;
      padding: 0;
      margin: 0;
      -webkit-font-smoothing: antialiased;
    }}

    .deck-wrapper {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 40px;
      padding: 40px 20px;
    }}

    .slide {{
      width: 297mm;
      height: 210mm;
      background: #FFFFFF;
      background-image: 
        radial-gradient(circle at 10% 10%, rgba(79, 70, 229, 0.03) 0%, transparent 45%),
        radial-gradient(circle at 90% 90%, rgba(217, 119, 6, 0.03) 0%, transparent 45%);
      border: 1px solid #CBD5E1;
      border-radius: 16px;
      padding: 40px 50px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 10px 35px rgba(15, 23, 42, 0.08);
      position: relative;
      overflow: hidden;
    }}

    /* Accent Bar Top */
    .slide::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 5px;
      background: linear-gradient(90deg, #D97706, #4F46E5, #059669);
    }}

    /* Header & Footer */
    .slide-hd {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      border-bottom: 2px solid #F1F5F9;
      padding-bottom: 14px;
      flex-shrink: 0;
    }}
    .hd-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 26px;
      font-weight: 800;
      color: #0F172A;
      letter-spacing: -0.5px;
      line-height: 1.1;
    }}
    .hd-sub {{
      font-size: 10px;
      color: #D97706;
      text-transform: uppercase;
      letter-spacing: 2px;
      font-weight: 700;
      margin-top: 3px;
    }}

    .slide-ft {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 9.5px;
      color: #64748B;
      border-top: 1px solid #F1F5F9;
      padding-top: 12px;
      flex-shrink: 0;
    }}

    .slide-bd {{
      flex: 1;
      margin: 20px 0;
      display: flex;
      flex-direction: column;
      min-height: 0;
    }}

    /* Royalty Crest Seal */
    .seal-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #FFFBEB;
      border: 1px solid #FDE68A;
      color: #D97706;
      font-size: 9.5px;
      font-weight: 800;
      letter-spacing: 1.5px;
      padding: 5px 14px;
      border-radius: 20px;
      text-transform: uppercase;
    }}

    /* KPI Cards Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 20px;
    }}
    .kpi-box {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 14px;
      padding: 18px;
      text-align: center;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
    }}
    .kpi-num {{
      font-family: 'Outfit', sans-serif;
      font-size: 30px;
      font-weight: 900;
      color: #4F46E5;
      line-height: 1;
    }}
    .kpi-lbl {{
      font-size: 9px;
      color: #64748B;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-top: 6px;
      font-weight: 700;
    }}

    /* Narrative Quote Card */
    .quote-card {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-left: 4px solid #4F46E5;
      border-radius: 0 14px 14px 0;
      padding: 20px 24px;
      flex: 1;
      overflow-y: auto;
    }}
    .quote-hd {{
      font-size: 10px;
      font-weight: 800;
      color: #4F46E5;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-bottom: 8px;
    }}
    .quote-txt {{
      font-size: 13.5px;
      line-height: 1.7;
      color: #334155;
    }}

    /* Insights Grid Layout */
    .insights-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      grid-template-rows: repeat(2, 1fr);
      gap: 16px;
      height: 100%;
    }}
    .insight-royalty-card {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 14px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }}
    .flex-between {{ display: flex; justify-content: space-between; align-items: center; }}
    .badge-royalty {{
      font-size: 9px;
      font-weight: 800;
      padding: 3px 9px;
      border-radius: 10px;
      text-transform: uppercase;
    }}
    .imp-pill {{ font-size: 9px; font-weight: 700; color: #64748B; }}
    .card-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 13px;
      font-weight: 700;
      color: #0F172A;
      margin: 6px 0 3px 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .card-desc {{
      font-size: 10px;
      color: #475569;
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .svg-container {{ margin-top: 8px; flex: 1; min-height: 100px; display: flex; align-items: center; }}

    /* Column Pills */
    .col-pill {{
      background: #F1F5F9;
      border: 1px solid #CBD5E1;
      color: #0284C7;
      font-family: monospace;
      font-size: 10px;
      padding: 3px 8px;
      border-radius: 6px;
      display: inline-block;
      margin: 2px;
      font-weight: 600;
    }}

    /* Action Roadmap Cards */
    .action-grid {{ display: flex; flex-direction: column; gap: 12px; height: 100%; }}
    .action-card {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 12px;
      padding: 16px;
      display: flex;
      gap: 16px;
      align-items: center;
    }}
    .action-num {{
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: linear-gradient(135deg, #4F46E5, #4338CA);
      color: #ffffff;
      font-family: 'Outfit', sans-serif;
      font-size: 14px;
      font-weight: 900;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}
  </style>
</head>
<body>

  <div class="deck-wrapper">

    <!-- ── SLIDE 1: COVER ────────────────────────────────────────────── -->
    <div class="slide" id="slide-1">
      <div>
        <span class="seal-badge">👑 DATAFORGE EXECUTIVE ADVISORY · CONFIDENTIAL</span>
      </div>

      <div style="margin: 35px 0;">
        <h1 style="font-family:'Outfit',sans-serif;font-size:44px;font-weight:900;line-height:1.1;color:#0F172A;letter-spacing:-1px;">
          Business Intelligence &<br>
          <span style="background:linear-gradient(90deg, #D97706, #4F46E5, #059669);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            Strategic Performance Report
          </span>
        </h1>
        <p style="color:#475569;font-size:15px;margin-top:16px;max-width:680px;line-height:1.6;">
          An executive slide deck distilling key dataset metrics, statistical trends, operational data health alerts, and strategic execution roadmaps.
        </p>
      </div>

      <div style="display:flex;align-items:center;justify-content:space-between;background:#F8FAFC;border:1px solid #E2E8F0;padding:18px 28px;border-radius:14px;">
        <div>
          <span style="font-size:9px;color:#64748B;text-transform:uppercase;letter-spacing:1px;display:block;">Dataset</span>
          <span style="font-size:14px;font-weight:700;color:#0F172A;">{html.escape(dataset_name)}</span>
        </div>
        <div>
          <span style="font-size:9px;color:#64748B;text-transform:uppercase;letter-spacing:1px;display:block;">Domain Type</span>
          <span style="font-size:11px;font-weight:800;color:#059669;background:#ECFDF5;padding:3px 10px;border-radius:8px;border:1px solid #A7F3D0;">{type_label}</span>
        </div>
        <div>
          <span style="font-size:9px;color:#64748B;text-transform:uppercase;letter-spacing:1px;display:block;">Date</span>
          <span style="font-size:12px;font-weight:700;color:#334155;">{now_str}</span>
        </div>
      </div>

      <div class="slide-ft">
        <span>DataForge Royalty Intelligence Engine</span>
        <span>Slide 1 of 5</span>
      </div>
    </div>

    <!-- ── SLIDE 2: KPI & EXECUTIVE SUMMARY ──────────────────────────── -->
    <div class="slide" id="slide-2">
      <div class="slide-hd">
        <div>
          <h2 class="hd-title">Executive Summary</h2>
          <p class="hd-sub">Business Overview & Metric Footprint</p>
        </div>
        <span style="font-size:9px;color:#64748B;font-weight:600;">DATASET: {html.escape(dataset_name)}</span>
      </div>

      <div class="slide-bd">
        <div class="kpi-grid">
          <div class="kpi-box">
            <div class="kpi-num">{f"{rows:,}" if isinstance(rows, int) else rows}</div>
            <div class="kpi-lbl">Total Records</div>
          </div>
          <div class="kpi-box">
            <div class="kpi-num" style="color:#059669">{cols}</div>
            <div class="kpi-lbl">Attributes</div>
          </div>
          <div class="kpi-box">
            <div class="kpi-num" style="color:{'#e11d48' if float(miss) > 10 else '#059669'}">{miss}%</div>
            <div class="kpi-lbl">Missing Footprint</div>
          </div>
          <div class="kpi-box">
            <div class="kpi-num" style="color:#d97706">{len(insights)}</div>
            <div class="kpi-lbl">Insights Flagged</div>
          </div>
        </div>

        <div class="quote-card">
          <div class="quote-hd">Executive Advisory Assessment</div>
          <div class="quote-txt">{html.escape(slide1)}</div>
        </div>
      </div>

      <div class="slide-ft">
        <span>DataForge Royalty Intelligence Engine</span>
        <span>Slide 2 of 5</span>
      </div>
    </div>

    <!-- ── SLIDE 3: STRATEGIC INSIGHTS & VISUALS ─────────────────────── -->
    <div class="slide" id="slide-3">
      <div class="slide-hd">
        <div>
          <h2 class="hd-title">Strategic Insights & Visual Analytics</h2>
          <p class="hd-sub">Algorithmic Patterns & Vector Charts</p>
        </div>
        <span style="font-size:9px;color:#64748B;font-weight:600;">QUANTIFIED PATTERNS</span>
      </div>

      <div class="slide-bd">
        <div class="insights-grid">
          {insight_cards_html}
        </div>
      </div>

      <div class="slide-ft">
        <span>DataForge Royalty Intelligence Engine</span>
        <span>Slide 3 of 5</span>
      </div>
    </div>

    <!-- ── SLIDE 4: DATA HEALTH & PROFILING ──────────────────────────── -->
    <div class="slide" id="slide-4">
      <div class="slide-hd">
        <div>
          <h2 class="hd-title">Data Quality & Schema Profiling</h2>
          <p class="hd-sub">Structural Verification & Health Status</p>
        </div>
        <span style="font-size:9px;color:#64748B;font-weight:600;">HEALTH DIAGNOSTICS</span>
      </div>

      <div class="slide-bd" style="display:grid;grid-template-columns:1fr 1.1fr;gap:24px;">
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:14px;padding:20px;display:flex;flex-direction:column;justify-content:space-between;">
          <div>
            <span style="font-size:9px;color:#64748B;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:8px;">Health Status Verification</span>
            <div style="display:flex;align-items:center;gap:10px;">
              <div style="width:12px;height:12px;border-radius:50%;background:{'#e11d48' if float(miss) > 10 else '#059669'};"></div>
              <span style="font-size:14px;font-weight:700;color:#0F172A;">
                {'Data Quality Alert: High Missing Footprint' if float(miss) > 10 else 'Optimal Database Health & Structure'}
              </span>
            </div>
          </div>

          <div>
            <span style="font-size:9px;color:#64748B;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:8px;">Column Schema Attributes</span>
            <div style="max-height:140px;overflow-y:auto;">
              {cols_pills}
            </div>
          </div>
        </div>

        <div class="quote-card" style="margin:0;">
          <div class="quote-hd">Data Quality Commentary</div>
          <div class="quote-txt">{html.escape(slide3)}</div>
        </div>
      </div>

      <div class="slide-ft">
        <span>DataForge Royalty Intelligence Engine</span>
        <span>Slide 4 of 5</span>
      </div>
    </div>

    <!-- ── SLIDE 5: ACTIONABLE ROADMAP ───────────────────────────────── -->
    <div class="slide" id="slide-5">
      <div class="slide-hd">
        <div>
          <h2 class="hd-title">Strategic Action Plan</h2>
          <p class="hd-sub">Execution Roadmap & Recommendations</p>
        </div>
        <span style="font-size:9px;color:#64748B;font-weight:600;">RECOMMENDED STEPS</span>
      </div>

      <div class="slide-bd" style="display:grid;grid-template-columns:1.2fr 1fr;gap:24px;">
        <div class="action-grid">
          <div class="action-card">
            <div class="action-num">1</div>
            <div>
              <h4 style="font-family:'Outfit',sans-serif;font-size:13px;font-weight:700;color:#0F172A;">Continuous Alert Monitoring</h4>
              <p style="font-size:10.5px;color:#475569;margin-top:2px;">Set up automated triggers on key metric spikes and anomalies.</p>
            </div>
          </div>
          <div class="action-card">
            <div class="action-num" style="background:linear-gradient(135deg,#059669,#047857);">2</div>
            <div>
              <h4 style="font-family:'Outfit',sans-serif;font-size:13px;font-weight:700;color:#0F172A;">Attribute Optimization</h4>
              <p style="font-size:10.5px;color:#475569;margin-top:2px;">Prioritize high-impact predictor columns for AutoML modeling.</p>
            </div>
          </div>
          <div class="action-card">
            <div class="action-num" style="background:linear-gradient(135deg,#D97706,#B45309);">3</div>
            <div>
              <h4 style="font-family:'Outfit',sans-serif;font-size:13px;font-weight:700;color:#0F172A;">Automate Weekly Cadence</h4>
              <p style="font-size:10.5px;color:#475569;margin-top:2px;">Schedule automated PDF report generation for executive stakeholders.</p>
            </div>
          </div>
        </div>

        <div class="quote-card" style="margin:0;">
          <div class="quote-hd">Execution Strategy Notes</div>
          <div class="quote-txt">{html.escape(slide4)}</div>
        </div>
      </div>

      <div class="slide-ft">
        <span>DataForge Royalty Intelligence Engine</span>
        <span>Slide 5 of 5</span>
      </div>
    </div>

  </div>

</body>
</html>"""

    return html_doc
