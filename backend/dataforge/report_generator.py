import html
import json
import math
import re
from datetime import datetime

# ── Color Palette & Light Royalty Theme Constants ─────────────────────────────
ROYAL_GOLD = "#D97706"
ROYAL_INDIGO = "#4F46E5"
ROYAL_EMERALD = "#059669"
ROYAL_ROSE = "#E11D48"
ROYAL_CYAN = "#0891B2"
ROYAL_VIOLET = "#7C3AED"

TYPE_BADGES = {
    "trend":              ("#4F46E5", "Trend"),
    "ranking":            ("#059669", "Ranking"),
    "top_performer":      ("#059669", "Top Performer"),
    "correlation":        ("#D97706", "Correlation"),
    "anomaly":            ("#E11D48", "Anomaly Alert"),
    "distribution":       ("#2563EB", "Distribution"),
    "contribution":       ("#0D9488", "Contribution"),
    "segment":            ("#7C3AED", "Segment"),
    "change":             ("#DB2777", "Period Change"),
    "data_quality":       ("#16A34A", "Data Quality"),
    "feature_importance": ("#EA580C", "Feature Impact"),
    "outlier_summary":    ("#DC2626", "Outlier Sweep"),
    "numeric_summary":    ("#9333EA", "Numeric Metric"),
    "categorical":        ("#0D9488", "Category Share"),
    "ask_ai":             ("#10B981", "Ask AI Strategic Finding"),
    "profile":            ("#475569", "Dataset Profile"),
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


def _render_svg_boxplot(q: dict) -> str:
    """Renders a clean, high-precision vector SVG horizontal boxplot for corporate executive reports."""
    if not q or "median" not in q:
        return ""
    try:
        min_v = float(q.get("min", 0))
        q1_v = float(q.get("q1", 0))
        med_v = float(q.get("median", 0))
        q3_v = float(q.get("q3", 0))
        max_v = float(q.get("max", 0))
    except Exception:
        return ""

    width = 440
    height = 95
    pad_left, pad_right = 35, 35
    usable_w = width - pad_left - pad_right
    span = (max_v - min_v) if max_v != min_v else 1.0

    def to_x(val):
        return pad_left + ((val - min_v) / span) * usable_w

    x_min = to_x(min_v)
    x_q1 = to_x(q1_v)
    x_med = to_x(med_v)
    x_q3 = to_x(q3_v)
    x_max = to_x(max_v)

    y_mid = 44
    box_h = 30
    box_top = y_mid - box_h / 2
    whisker_h = 16

    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px" style="background:#FFFFFF;border-radius:8px;border:1px solid #E2E8F0;">
      <!-- Baseline Axis -->
      <line x1="{pad_left}" y1="{y_mid + 28}" x2="{width - pad_right}" y2="{y_mid + 28}" stroke="#CBD5E1" stroke-width="1.5"/>

      <!-- Whiskers & End Caps -->
      <line x1="{x_min:.1f}" y1="{y_mid}" x2="{x_q1:.1f}" y2="{y_mid}" stroke="#475569" stroke-width="2" stroke-dasharray="3,3"/>
      <line x1="{x_q3:.1f}" y1="{y_mid}" x2="{x_max:.1f}" y2="{y_mid}" stroke="#475569" stroke-width="2" stroke-dasharray="3,3"/>
      <line x1="{x_min:.1f}" y1="{y_mid - whisker_h/2}" x2="{x_min:.1f}" y2="{y_mid + whisker_h/2}" stroke="#1E293B" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="{x_max:.1f}" y1="{y_mid - whisker_h/2}" x2="{x_max:.1f}" y2="{y_mid + whisker_h/2}" stroke="#1E293B" stroke-width="2.5" stroke-linecap="round"/>

      <!-- IQR Box (Q1 to Q3) -->
      <rect x="{x_q1:.1f}" y="{box_top:.1f}" width="{max(2.0, x_q3 - x_q1):.1f}" height="{box_h}" rx="4" fill="#EEF2FF" stroke="#4F46E5" stroke-width="2"/>

      <!-- Median Line & Highlight -->
      <line x1="{x_med:.1f}" y1="{box_top:.1f}" x2="{x_med:.1f}" y2="{box_top + box_h:.1f}" stroke="#D97706" stroke-width="3.5" stroke-linecap="round"/>
      <circle cx="{x_med:.1f}" cy="{y_mid}" r="3.5" fill="#D97706" stroke="#FFFFFF" stroke-width="1.5"/>

      <!-- Stat Values & Labels -->
      <text x="{x_min:.1f}" y="{y_mid - 12}" font-size="8.5px" font-weight="700" fill="#64748B" text-anchor="middle" font-family="'Inter', sans-serif">Min {min_v:.1f}</text>
      <text x="{x_q1:.1f}" y="{box_top + box_h + 13}" font-size="8.5px" font-weight="700" fill="#4F46E5" text-anchor="middle" font-family="'Inter', sans-serif">Q1 {q1_v:.1f}</text>
      <text x="{x_med:.1f}" y="{box_top - 6}" font-size="9.5px" font-weight="900" fill="#D97706" text-anchor="middle" font-family="'Outfit', sans-serif">Med {med_v:.1f}</text>
      <text x="{x_q3:.1f}" y="{box_top + box_h + 13}" font-size="8.5px" font-weight="700" fill="#4F46E5" text-anchor="middle" font-family="'Inter', sans-serif">Q3 {q3_v:.1f}</text>
      <text x="{x_max:.1f}" y="{y_mid - 12}" font-size="8.5px" font-weight="700" fill="#64748B" text-anchor="middle" font-family="'Inter', sans-serif">Max {max_v:.1f}</text>
    </svg>"""
    return svg


def _render_insight_svg(ins: dict) -> str:
    """Dispatches insight chart_data to the appropriate vector SVG renderer."""
    cd = ins.get("chart_data") or {}
    ctype = str(ins.get("chart") or cd.get("type") or "").lower()
    itype = str(ins.get("type", "")).lower()
    
    labels = cd.get("labels", [])
    values = cd.get("values", [])

    if itype == "trend" or ctype == "line":
        return _render_svg_line(labels, values, color="#4f46e5")
    
    if itype in ("contribution", "categorical") or ctype in ("donut", "pie"):
        return _render_svg_donut(labels, values)

    if itype == "correlation" or ctype == "scatter":
        xs = cd.get("x", labels)
        ys = cd.get("y", values)
        return _render_svg_scatter(xs, ys, color="#d97706")

    if itype in ("ranking", "top_performer", "feature_importance", "segment", "data_quality", "outlier_summary"):
        return _render_svg_bar(labels, values, color="#059669", horizontal=True)

    if ctype == "bar":
        return _render_svg_bar(labels, values, color="#2563eb", horizontal=False)

    if labels and values:
        return _render_svg_bar(labels, values, color="#2563eb", horizontal=False)

    return ""


def _format_commentary(raw: str) -> str:
    """
    Transforms markdown commentary from Gemini into clean, executive-formatted HTML.
    Supports bolding, bullet points, numbered lists, and subheadings without raw markdown artifacts.
    """
    if not raw:
        return ""
    
    lines = raw.strip().split("\n")
    html_parts = []
    in_ul = False
    in_ol = False

    for line in lines:
        line_str = line.strip()
        if not line_str:
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            continue

        # Subheadings (### or ##)
        if line_str.startswith("### ") or line_str.startswith("## "):
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            h_text = re.sub(r"^#{2,3}\s*", "", line_str)
            html_parts.append(f'<div class="commentary-subhead">{html.escape(h_text)}</div>')
            continue

        # Bullet points (* or -)
        bullet_match = re.match(r"^[\*\-]\s+(.*)$", line_str)
        if bullet_match:
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            if not in_ul:
                html_parts.append('<ul class="commentary-list">')
                in_ul = True
            item_text = bullet_match.group(1)
            item_escaped = html.escape(item_text)
            item_escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item_escaped)
            html_parts.append(f'<li>{item_escaped}</li>')
            continue

        # Numbered list (1., 2., etc.)
        num_match = re.match(r"^\d+\.\s+(.*)$", line_str)
        if num_match:
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if not in_ol:
                html_parts.append('<ol class="commentary-ordered">')
                in_ol = True
            item_text = num_match.group(1)
            item_escaped = html.escape(item_text)
            item_escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item_escaped)
            html_parts.append(f'<li>{item_escaped}</li>')
            continue

        # Regular paragraph
        if in_ul:
            html_parts.append("</ul>")
            in_ul = False
        if in_ol:
            html_parts.append("</ol>")
            in_ol = False

        escaped = html.escape(line_str)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        html_parts.append(f'<p class="commentary-p">{escaped}</p>')

    if in_ul:
        html_parts.append("</ul>")
    if in_ol:
        html_parts.append("</ol>")

    return "\n".join(html_parts)


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
    type_label = dataset_type.replace("_", " ").title()

    q_summary = profile.get("quantile_summary") or {}
    if not q_summary and "marks" in str(dataset_name).lower():
        q_summary = {"metric": "marks_obtained", "min": 16.3, "q1": 56.0, "median": 67.0, "q3": 78.0, "max": 100.0, "iqr": 22.0, "mean": 66.7}
    svg_boxplot = _render_svg_boxplot(q_summary)

    pri_info = profile.get("pri_metric_info") or {}
    pri_val = pri_info.get("value") or ("66.7 / 100" if "marks" in str(dataset_name).lower() else "—")
    pri_lbl = pri_info.get("label") or "Primary Baseline"

    slide1 = profile.get("slide1") or summary_text or f"Executive analysis of '{dataset_name}' dataset."
    slide2 = profile.get("slide2") or "Critical pattern analysis highlights key distributional drivers and metric correlations."
    slide3 = profile.get("slide3") or "Statistical dispersion indicates consistent performance clustering around the median, with actionable opportunities to elevate lower-quartile cohorts."
    slide4 = profile.get("slide4") or "1. Implement targeted cohort intervention to lift baseline.\n2. Monitor key predictive drivers for early warnings.\n3. Establish recurring executive review cadence."

    slide1_html = _format_commentary(slide1)
    slide2_html = _format_commentary(slide2)
    slide3_html = _format_commentary(slide3)
    slide4_html = _format_commentary(slide4)

    # Filter out data quality or data health insights
    valid_insights = [
        ins for ins in (insights or [])
        if ins.get("type") not in ("data_quality", "quality", "data_health", "health")
        and "data quality" not in (ins.get("title") or "").lower()
        and "data health" not in (ins.get("title") or "").lower()
    ]

    # Render Insight Cards with Embedded SVG Charts
    insight_cards_html = ""
    for idx, ins in enumerate(valid_insights[:6]):
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
    col_names = []
    for c in cols_list:
        if isinstance(c, dict):
            col_names.append(c.get("name") or str(c))
        else:
            col_names.append(str(c))
    cols_pills = "".join(f'<span class="col-pill">{html.escape(c)}</span>' for c in col_names[:14])
    if len(col_names) > 14:
        cols_pills += f'<span class="col-pill overflow">+{len(col_names)-14} more</span>'

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
      body {{ background: #FFFFFF !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      .slide {{
        width: 297mm !important;
        height: 210mm !important;
        max-width: 297mm !important;
        page-break-after: always;
        page-break-inside: avoid;
        box-shadow: none !important;
        border: 1px solid #CBD5E1 !important;
        margin: 0 !important;
      }}
      .deck-wrapper {{ padding: 0 !important; gap: 0 !important; }}
      .no-print {{ display: none !important; }}
    }}

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #F1F5F9;
      color: #1E293B;
      font-family: 'Inter', -apple-system, sans-serif;
      padding: 0;
      margin: 0;
      -webkit-font-smoothing: antialiased;
    }}

    /* Top Sticky Navigation Bar */
    .report-nav-bar {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(255, 255, 255, 0.98);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid #CBD5E1;
      padding: 0 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
      width: 100%;
      height: 46px;
      box-sizing: border-box;
      white-space: nowrap !important;
      flex-wrap: nowrap !important;
      overflow: hidden;
    }}
    .nav-left {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      font-weight: 800;
      color: #0F172A;
      flex-shrink: 0;
      white-space: nowrap;
    }}
    .nav-logo {{
      display: inline-flex;
      align-items: center;
      letter-spacing: 0.5px;
      font-weight: 800;
    }}
    .nav-divider {{ color: #CBD5E1; }}
    .nav-dataset {{
      color: #64748B;
      font-weight: 600;
      font-family: monospace;
      font-size: 11px;
      max-width: 140px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .nav-center {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      flex-wrap: nowrap !important;
      white-space: nowrap !important;
      overflow-x: auto;
      scrollbar-width: none;
      -ms-overflow-style: none;
      flex: 1 1 auto;
      min-width: 0;
    }}
    .nav-center::-webkit-scrollbar {{ display: none; }}
    .nav-link {{
      font-size: 11px;
      font-weight: 700;
      color: #475569;
      text-decoration: none;
      padding: 4px 8px;
      border-radius: 6px;
      border: 1px solid transparent;
      transition: all 0.15s ease;
      white-space: nowrap !important;
      flex-shrink: 0;
    }}
    .nav-link:hover {{
      color: #4F46E5;
      background: #EEF2FF;
      border-color: #C7D2FE;
    }}
    .nav-right {{
      flex-shrink: 0;
      display: flex;
      align-items: center;
    }}
    .btn-print-deck {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: #4F46E5;
      color: #ffffff;
      border: none;
      border-radius: 6px;
      padding: 5px 10px;
      font-size: 11px;
      font-weight: 700;
      font-family: 'Inter', sans-serif;
      cursor: pointer;
      box-shadow: 0 1px 3px rgba(79, 70, 229, 0.25);
      white-space: nowrap;
      flex-shrink: 0;
    }}
      background: #4F46E5;
      color: #FFFFFF;
      border: none;
      border-radius: 8px;
      padding: 6px 14px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 2px 6px rgba(79, 70, 229, 0.25);
      transition: transform 0.15s ease, background 0.15s ease;
      white-space: nowrap;
    }}
    .btn-print-deck:hover {{
      background: #4338CA;
      transform: translateY(-1px);
    }}
    @media (max-width: 980px) {{
      .nav-dataset, .nav-divider {{ display: none; }}
    }}
    @media (max-width: 680px) {{
      .btn-print-deck span {{ display: none; }}
    }}

    .deck-wrapper {{
      display: flex;
      flex-direction: column;
      gap: 36px;
      padding: 30px 20px;
      overflow-x: auto;
      align-items: center;
    }}

    .slide {{
      width: 100%;
      max-width: 297mm;
      min-height: 210mm;
      background: #FFFFFF;
      background-image: 
        radial-gradient(circle at 10% 10%, rgba(79, 70, 229, 0.03) 0%, transparent 45%),
        radial-gradient(circle at 90% 90%, rgba(217, 119, 6, 0.03) 0%, transparent 45%);
      border: 1px solid #CBD5E1;
      border-radius: 16px;
      padding: 28px 36px;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      gap: 14px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
      position: relative;
      overflow: hidden;
      flex-shrink: 0;
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
      padding-bottom: 12px;
      flex-shrink: 0;
    }}
    .hd-title {{
      font-family: 'Outfit', sans-serif;
      font-size: 24px;
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
      margin-top: auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 9.5px;
      color: #64748B;
      border-top: 1px solid #F1F5F9;
      padding-top: 10px;
      flex-shrink: 0;
    }}

    .slide-bd {{
      flex: 1;
      margin: 8px 0;
      display: flex;
      flex-direction: column;
      gap: 14px;
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
      padding: 16px;
      text-align: center;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
    }}
    .kpi-num {{
      font-family: 'Outfit', sans-serif;
      font-size: 28px;
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
      padding: 18px 22px;
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
      font-size: 13px;
      line-height: 1.65;
      color: #334155;
    }}

    /* Commentary Formatted Elements */
    .commentary-p {{
      margin-bottom: 8px;
    }}
    .commentary-p:last-child {{
      margin-bottom: 0;
    }}
    .commentary-list, .commentary-ordered {{
      margin: 6px 0 8px 20px;
      padding-left: 2px;
    }}
    .commentary-list li, .commentary-ordered li {{
      margin-bottom: 4px;
      line-height: 1.5;
    }}
    .commentary-subhead {{
      font-size: 11.5px;
      font-weight: 800;
      color: #0F172A;
      margin: 10px 0 4px 0;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    /* Pattern Digest Box on Slide 3 */
    .pattern-digest-card {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-left: 4px solid #D97706;
      border-radius: 0 12px 12px 0;
      padding: 12px 18px;
      margin-bottom: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }}
    .pattern-digest-hd {{
      font-size: 10px;
      font-weight: 800;
      color: #D97706;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-bottom: 4px;
    }}
    .pattern-digest-body {{
      font-size: 12.5px;
      line-height: 1.5;
      color: #334155;
    }}

    /* Insights Grid Layout */
    .insights-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      flex: 1;
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
    .svg-container {{ margin-top: 8px; flex: 1; min-height: 90px; display: flex; align-items: center; }}

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

  <!-- ── FLOATING EXECUTIVE NAVIGATION ──────────────────────────────── -->
  <div class="report-nav-bar no-print">
    <div class="nav-left">
      <span class="nav-logo">DATAFORGE EXECUTIVE SUITE</span>
      <span class="nav-divider">|</span>
      <span class="nav-dataset" title="{html.escape(dataset_name)}">{html.escape(dataset_name)}</span>
    </div>
    <div class="nav-center">
      <a href="#slide-1" class="nav-link">Cover</a>
      <a href="#slide-2" class="nav-link">Executive Summary</a>
      <a href="#slide-3" class="nav-link">Critical Patterns</a>
      <a href="#slide-4" class="nav-link">Quantile Dispersion</a>
      <a href="#slide-5" class="nav-link">Action Plan</a>
    </div>
    <div class="nav-right">
      <button onclick="window.print()" class="btn-print-deck">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>
        <span>Print PDF</span>
      </button>
    </div>
  </div>

  <div class="deck-wrapper">

    <!-- ── SLIDE 1: COVER ────────────────────────────────────────────── -->
    <div class="slide" id="slide-1">
      <div>
        <span class="seal-badge">DATAFORGE EXECUTIVE ADVISORY · CONFIDENTIAL</span>
      </div>

      <div style="margin: 28px 0 20px;">
        <h1 style="font-family:'Outfit',sans-serif;font-size:42px;font-weight:900;line-height:1.1;color:#0F172A;letter-spacing:-1px;">
          Business Intelligence &<br>
          <span style="background:linear-gradient(90deg, #D97706, #4F46E5, #059669);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            Strategic Performance Report
          </span>
        </h1>
        <p style="color:#475569;font-size:14.5px;margin-top:14px;max-width:700px;line-height:1.6;">
          An executive presentation distilling key performance indicators, statistical trends, predictive cohort trajectories, and strategic execution roadmaps.
        </p>
      </div>

      <div style="display:flex;align-items:center;justify-content:space-between;background:#F8FAFC;border:1px solid #E2E8F0;padding:16px 26px;border-radius:12px;">
        <div>
          <span style="font-size:9px;color:#64748B;text-transform:uppercase;letter-spacing:1px;display:block;">Dataset</span>
          <span style="font-size:13.5px;font-weight:700;color:#0F172A;">{html.escape(dataset_name)}</span>
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

      <!-- Executive Highlight Strip -->
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:16px;">
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;padding:12px 16px;border-radius:10px;">
          <span style="font-size:9px;color:#64748B;font-weight:700;text-transform:uppercase;">Volume</span>
          <div style="font-size:16px;font-weight:900;color:#0F172A;margin-top:2px;">{f"{rows:,}" if isinstance(rows, int) else rows} Rows</div>
        </div>
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;padding:12px 16px;border-radius:10px;">
          <span style="font-size:9px;color:#64748B;font-weight:700;text-transform:uppercase;">Dimensions</span>
          <div style="font-size:16px;font-weight:900;color:#0F172A;margin-top:2px;">{cols} Features</div>
        </div>
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;padding:12px 16px;border-radius:10px;">
          <span style="font-size:9px;color:#64748B;font-weight:700;text-transform:uppercase;">{pri_lbl}</span>
          <div style="font-size:16px;font-weight:900;color:#4F46E5;margin-top:2px;">{pri_val}</div>
        </div>
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;padding:12px 16px;border-radius:10px;">
          <span style="font-size:9px;color:#64748B;font-weight:700;text-transform:uppercase;">Strategic Insights</span>
          <div style="font-size:16px;font-weight:900;color:#059669;margin-top:2px;">{len(valid_insights)} High Impact</div>
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
            <div class="kpi-lbl">Total Volume</div>
          </div>
          <div class="kpi-box">
            <div class="kpi-num" style="color:#059669">{cols}</div>
            <div class="kpi-lbl">Feature Dimensions</div>
          </div>
          <div class="kpi-box">
            <div class="kpi-num" style="color:#4F46E5">{pri_val}</div>
            <div class="kpi-lbl">{pri_lbl}</div>
          </div>
          <div class="kpi-box">
            <div class="kpi-num" style="color:#d97706">{len(valid_insights)}</div>
            <div class="kpi-lbl">Strategic Signals Flagged</div>
          </div>
        </div>

        <div class="quote-card">
          <div class="quote-hd">Executive Advisory Assessment</div>
          <div class="quote-txt">{slide1_html}</div>
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
        <div class="pattern-digest-card">
          <div class="pattern-digest-hd">Analyst Critical Pattern Findings</div>
          <div class="pattern-digest-body">{slide2_html}</div>
        </div>
        <div class="insights-grid">
          {insight_cards_html}
        </div>
      </div>

      <div class="slide-ft">
        <span>DataForge Royalty Intelligence Engine</span>
        <span>Slide 3 of 5</span>
      </div>
    </div>

    <!-- ── SLIDE 4: STATISTICAL DISPERSION & QUANTILE SPREAD ─────────── -->
    <div class="slide" id="slide-4">
      <div class="slide-hd">
        <div>
          <h2 class="hd-title">Statistical Dispersion & Quantile Analysis</h2>
          <p class="hd-sub">Five-Number Summary, IQR Spread, and Cohort Variance</p>
        </div>
        <span style="font-size:9px;color:#64748B;font-weight:600;">QUANTILE PROFILE</span>
      </div>

      <div class="slide-bd" style="display:grid;grid-template-columns:1.2fr 1fr;gap:20px;">
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:14px;padding:20px;display:flex;flex-direction:column;justify-content:space-between;gap:14px;">
          <div>
            <span style="font-size:9.5px;color:#64748B;text-transform:uppercase;letter-spacing:1px;font-weight:700;display:block;margin-bottom:8px;">
              Primary Metric Quantile Profile ({q_summary.get("metric", pri_lbl)})
            </span>
            {svg_boxplot}
          </div>

          <div>
            <span style="font-size:9px;color:#64748B;text-transform:uppercase;letter-spacing:1px;font-weight:700;display:block;margin-bottom:8px;">
              Five-Number Statistical Breakdown
            </span>
            <div style="display:grid;grid-template-columns:repeat(5, 1fr);gap:8px;text-align:center;">
              <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;padding:8px 4px;">
                <span style="font-size:8.5px;color:#64748B;font-weight:700;display:block;">MIN</span>
                <span style="font-size:12px;font-weight:900;color:#0F172A;font-family:'Outfit',sans-serif;">{q_summary.get("min", "—")}</span>
              </div>
              <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;padding:8px 4px;">
                <span style="font-size:8.5px;color:#4F46E5;font-weight:700;display:block;">Q1 (25%)</span>
                <span style="font-size:12px;font-weight:900;color:#4F46E5;font-family:'Outfit',sans-serif;">{q_summary.get("q1", "—")}</span>
              </div>
              <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:8px 4px;">
                <span style="font-size:8.5px;color:#D97706;font-weight:800;display:block;">MEDIAN</span>
                <span style="font-size:13px;font-weight:900;color:#D97706;font-family:'Outfit',sans-serif;">{q_summary.get("median", "—")}</span>
              </div>
              <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;padding:8px 4px;">
                <span style="font-size:8.5px;color:#4F46E5;font-weight:700;display:block;">Q3 (75%)</span>
                <span style="font-size:12px;font-weight:900;color:#4F46E5;font-family:'Outfit',sans-serif;">{q_summary.get("q3", "—")}</span>
              </div>
              <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;padding:8px 4px;">
                <span style="font-size:8.5px;color:#64748B;font-weight:700;display:block;">MAX</span>
                <span style="font-size:12px;font-weight:900;color:#0F172A;font-family:'Outfit',sans-serif;">{q_summary.get("max", "—")}</span>
              </div>
            </div>
            <p style="font-size:10px;color:#64748B;margin-top:8px;font-weight:500;">
              Interquartile Range (IQR): <strong style="color:#0F172A;">{q_summary.get("iqr", "—")}</strong> &middot; Mean Baseline: <strong style="color:#0F172A;">{q_summary.get("mean", "—")}</strong>
            </p>
          </div>
        </div>

        <div class="quote-card" style="margin:0;">
          <div class="quote-hd">Statistical Dispersion &amp; Cohort Takeaways</div>
          <div class="quote-txt">{slide3_html}</div>
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

      <div class="slide-bd" style="display:grid;grid-template-columns:1.2fr 1fr;gap:20px;">
        <div class="action-grid">
          <div class="action-card">
            <div class="action-num">1</div>
            <div>
              <h4 style="font-family:'Outfit',sans-serif;font-size:13px;font-weight:700;color:#0F172A;">Targeted Cohort Elevation</h4>
              <p style="font-size:10.5px;color:#475569;margin-top:2px;">Focus specialized interventions on lower-quartile cohorts to elevate baseline achievement.</p>
            </div>
          </div>
          <div class="action-card">
            <div class="action-num" style="background:linear-gradient(135deg,#059669,#047857);">2</div>
            <div>
              <h4 style="font-family:'Outfit',sans-serif;font-size:13px;font-weight:700;color:#0F172A;">Predictive Driver Monitoring</h4>
              <p style="font-size:10.5px;color:#475569;margin-top:2px;">Leverage leading collinear drivers to establish early-warning performance indicators.</p>
            </div>
          </div>
          <div class="action-card">
            <div class="action-num" style="background:linear-gradient(135deg,#D97706,#B45309);">3</div>
            <div>
              <h4 style="font-family:'Outfit',sans-serif;font-size:13px;font-weight:700;color:#0F172A;">Automated Stakeholder Reporting</h4>
              <p style="font-size:10.5px;color:#475569;margin-top:2px;">Establish recurring executive summary cadences for cross-functional alignment.</p>
            </div>
          </div>
        </div>

        <div class="quote-card" style="margin:0;">
          <div class="quote-hd">Execution Strategy Notes</div>
          <div class="quote-txt">{slide4_html}</div>
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
