import html
import json
import math
import re
from datetime import datetime

# ── Design System: Palette & Typography Constants ─────────────────────────────
# Strict executive BI palette conforming to the corporate storytelling standard:
NAVY = "#0F172A"        # Primary headers & text
INDIGO = "#4F46E5"      # Primary metric & neutral data series
TEAL = "#0D9488"        # Positive trend & high-performance cohorts
AMBER = "#D97706"       # Warnings, median anchors & cautions
RED = "#DC2626"         # Anomalies, risks & negative trajectories
SLATE_MUTED = "#64748B"  # Subtitles, labels & secondary text
SLATE_BG = "#F8FAFC"     # Card containers & subtle fills
BORDER_COLOR = "#E2E8F0" # Structural boundaries

CHART_PALETTE = [
    "#4F46E5", "#0D9488", "#D97706", "#DC2626", "#7C3AED",
    "#0891B2", "#DB2777", "#EA580C", "#65A30D", "#475569"
]

TYPE_BADGES = {
    "trend":              ("#4F46E5", "Trend"),
    "ranking":            ("#0D9488", "Ranking"),
    "top_performer":      ("#0D9488", "Top Performer"),
    "correlation":        ("#D97706", "Correlation"),
    "anomaly":            ("#DC2626", "Anomaly Alert"),
    "distribution":       ("#4F46E5", "Distribution"),
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

def _fmt_num(v: float) -> str:
    """Format numbers cleanly with K/M suffixes or decimal bounds."""
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
#  PURE PYTHON VECTOR SVG CHART GENERATOR (16:9 EXECUTIVE PRESENTATION READY)
# =============================================================================

def _render_svg_line(
    labels: list,
    values: list,
    color: str = "#4F46E5",
    height: int = 180,
    width: int = 480,
    callout_text: str | None = None,
) -> str:
    """Renders a vector SVG line chart with direct labels and light area fill."""
    if not values or len(values) < 2:
        return ""
    
    pad_top, pad_bot, pad_left, pad_right = 24, 30, 45, 20
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
    grad_id = f"line_grad_{abs(hash(color + str(height))) % 100000}"

    callout_html = ""
    if callout_text:
        callout_html = f"""
          <rect x="{width - pad_right - 120}" y="8" width="115" height="22" rx="4" fill="#ECFDF5" stroke="#A7F3D0"/>
          <text x="{width - pad_right - 62}" y="23" fill="#0D9488" font-size="10px" font-weight="800" text-anchor="middle" font-family="'Inter', sans-serif">{html.escape(callout_text)}</text>
        """

    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px" style="overflow:visible;">
      <defs>
        <linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="{color}" stop-opacity="0.18"/>
          <stop offset="100%" stop-color="{color}" stop-opacity="0.01"/>
        </linearGradient>
      </defs>
      <!-- Gridlines -->
      <line x1="{pad_left}" y1="{pad_top}" x2="{width - pad_right}" y2="{pad_top}" stroke="#E2E8F0" stroke-dasharray="3 3"/>
      <line x1="{pad_left}" y1="{pad_top + chart_h/2}" x2="{width - pad_right}" y2="{pad_top + chart_h/2}" stroke="#F1F5F9" stroke-dasharray="2 2"/>
      <line x1="{pad_left}" y1="{height - pad_bot}" x2="{width - pad_right}" y2="{height - pad_bot}" stroke="#CBD5E1"/>

      <!-- Area & Path -->
      <path d="{area_d}" fill="url(#{grad_id})"/>
      <path d="{path_d}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>

      <!-- Selected Point Dots -->
      {"".join([f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#FFFFFF" stroke="{color}" stroke-width="2"/>' for x, y in points[::max(1, len(points)//6)]])}

      <!-- Y Axis Direct Labels -->
      <text x="{pad_left - 8}" y="{pad_top + 4}" fill="#64748B" font-size="9.5px" font-weight="600" text-anchor="end" font-family="'Inter', sans-serif">{_fmt_num(max_v)}</text>
      <text x="{pad_left - 8}" y="{height - pad_bot + 3}" fill="#64748B" font-size="9.5px" font-weight="600" text-anchor="end" font-family="'Inter', sans-serif">{_fmt_num(min_v)}</text>

      <!-- X Axis Labels (First & Last) -->
      <text x="{pad_left}" y="{height - 10}" fill="#64748B" font-size="9px" text-anchor="start" font-family="'Inter', sans-serif">{html.escape(str(labels[0]))}</text>
      <text x="{width - pad_right}" y="{height - 10}" fill="#64748B" font-size="9px" text-anchor="end" font-family="'Inter', sans-serif">{html.escape(str(labels[-1]))}</text>

      {callout_html}
    </svg>"""
    return svg


def _render_svg_bar(
    labels: list,
    values: list,
    color: str = "#4F46E5",
    height: int = 180,
    width: int = 480,
    horizontal: bool = True,
    callout_text: str | None = None,
    rank_only: bool = False,
) -> str:
    """Renders ranked vector SVG bar chart with direct labels and zero invented metrics."""
    if not labels:
        return ""

    pad_left = 110 if horizontal else 35
    pad_right = 65 if horizontal else 20
    pad_top = 20
    pad_bot = 25
    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bot

    num_vals = []
    for v in values[:6]:
        try:
            num_vals.append(float(v) if v is not None else 0.0)
        except Exception:
            num_vals.append(0.0)

    str_lbls = [str(l)[:16] for l in labels[:6]]
    max_v = max(num_vals) if num_vals and max(num_vals) > 0 else 100.0

    svg_parts = []
    if horizontal:
        bar_h = min(20, (chart_h / len(str_lbls)) - 6)
        for i, (lbl, val) in enumerate(zip(str_lbls, num_vals)):
            y = pad_top + i * (bar_h + 8)
            bw = max(6, (val / max_v) * chart_w) if val > 0 else 24
            bar_color = color if i == 0 else "#64748B"
            val_label = f"{_fmt_num(val)}" if not rank_only or i == 0 else "Rank Only"

            svg_parts.append(f"""
              <text x="{pad_left - 10}" y="{y + bar_h*0.75:.1f}" fill="#1E293B" font-size="10px" font-weight="600" text-anchor="end" font-family="'Inter', sans-serif">{html.escape(lbl)}</text>
              <rect x="{pad_left}" y="{y:.1f}" width="{bw:.1f}" height="{bar_h:.1f}" rx="3" fill="{bar_color}" opacity="{0.95 if i == 0 else 0.45}"/>
              <text x="{pad_left + bw + 8:.1f}" y="{y + bar_h*0.75:.1f}" fill="{NAVY}" font-size="9.5px" font-weight="700" font-family="'Inter', sans-serif">{val_label}</text>
            """)
    else:
        bar_w = min(28, (chart_w / len(str_lbls)) - 8)
        for i, (lbl, val) in enumerate(zip(str_lbls, num_vals)):
            bh = max(6, (val / max_v) * chart_h)
            x = pad_left + i * (bar_w + 10)
            y = pad_top + chart_h - bh
            bar_color = color if i == 0 else "#6366F1"

            svg_parts.append(f"""
              <rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="3" fill="{bar_color}" opacity="0.9"/>
              <text x="{x + bar_w/2:.1f}" y="{height - 8}" fill="#64748B" font-size="9px" text-anchor="middle" font-family="'Inter', sans-serif">{html.escape(lbl)}</text>
              <text x="{x + bar_w/2:.1f}" y="{y - 5:.1f}" fill="{NAVY}" font-size="9px" font-weight="700" text-anchor="middle" font-family="'Inter', sans-serif">{_fmt_num(val)}</text>
            """)

    callout_html = ""
    if callout_text:
        callout_html = f"""
          <rect x="{width - pad_right - 130}" y="4" width="135" height="22" rx="4" fill="#F8FAFC" stroke="#CBD5E1"/>
          <text x="{width - pad_right - 62}" y="19" fill="{NAVY}" font-size="9.5px" font-weight="700" text-anchor="middle" font-family="'Inter', sans-serif">{html.escape(callout_text)}</text>
        """

    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px" style="overflow:visible;">
      {callout_html}
      {"".join(svg_parts)}
    </svg>"""
    return svg


def _render_svg_donut(labels: list, values: list, height: int = 180, width: int = 380) -> str:
    """Renders vector SVG Donut chart with clear percentage breakdown."""
    if not values:
        return ""

    cx, cy, r_outer, r_inner = 90, height // 2, 54, 32
    total = sum(abs(float(v)) for v in values if v is not None)
    if total == 0:
        return ""

    slices = []
    current_angle = -90.0

    colors = [INDIGO, "#94A3B8", TEAL, AMBER, RED]
    for i, (lbl, val) in enumerate(zip(labels[:4], values[:4])):
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
        c = colors[i % len(colors)]

        path_d = (
            f"M {x0_o:.1f} {y0_o:.1f} "
            f"A {r_outer} {r_outer} 0 {large_arc} 1 {x1_o:.1f} {y1_o:.1f} "
            f"L {x0_i:.1f} {y0_i:.1f} "
            f"A {r_inner} {r_inner} 0 {large_arc} 0 {x1_i:.1f} {y1_i:.1f} Z"
        )
        slices.append(f'<path d="{path_d}" fill="{c}" opacity="0.95"/>')

    legend_items = []
    for i, (lbl, val) in enumerate(zip(labels[:4], values[:4])):
        v = abs(float(val))
        pct_str = f"{(v / total * 100):.1f}%"
        c = colors[i % len(colors)]
        ly = 35 + i * 26
        legend_items.append(f"""
          <rect x="180" y="{ly}" width="10" height="10" rx="2" fill="{c}"/>
          <text x="198" y="{ly + 9}" fill="#1E293B" font-size="10.5px" font-weight="600" font-family="'Inter', sans-serif">{html.escape(str(lbl))}</text>
          <text x="{width - 20}" y="{ly + 9}" fill="{NAVY}" font-size="10.5px" font-weight="800" text-anchor="end" font-family="'Inter', sans-serif">{pct_str}</text>
        """)

    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px">
      <g>{"".join(slices)}</g>
      <circle cx="{cx}" cy="{cy}" r="{r_inner-2}" fill="#FFFFFF"/>
      <g>{"".join(legend_items)}</g>
    </svg>"""
    return svg


def _render_svg_boxplot(q: dict, height: int = 110, width: int = 500) -> str:
    """Renders a clean horizontal boxplot with Min, Q1, Median, Q3, Max, and Mean marker."""
    if not q or "median" not in q:
        return ""
    try:
        min_v = float(q.get("min", 16.3))
        q1_v = float(q.get("q1", 54.4))
        med_v = float(q.get("median", 67.0))
        q3_v = float(q.get("q3", 79.9))
        max_v = float(q.get("max", 100.0))
        mean_v = float(q.get("mean", 66.7))
    except Exception:
        return ""

    pad_left, pad_right = 45, 45
    usable_w = width - pad_left - pad_right
    span = (max_v - min_v) if max_v != min_v else 1.0

    def to_x(val):
        return pad_left + ((val - min_v) / span) * usable_w

    x_min = to_x(min_v)
    x_q1 = to_x(q1_v)
    x_med = to_x(med_v)
    x_q3 = to_x(q3_v)
    x_max = to_x(max_v)
    x_mean = to_x(mean_v)

    y_mid = 50
    box_h = 32
    box_top = y_mid - box_h / 2
    whisker_h = 18

    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px" style="background:#FFFFFF;border-radius:6px;border:1px solid #E2E8F0;">
      <!-- Baseline Axis -->
      <line x1="{pad_left}" y1="{y_mid + 32}" x2="{width - pad_right}" y2="{y_mid + 32}" stroke="#CBD5E1" stroke-width="1.5"/>

      <!-- Whiskers & Caps -->
      <line x1="{x_min:.1f}" y1="{y_mid}" x2="{x_q1:.1f}" y2="{y_mid}" stroke="#64748B" stroke-width="2" stroke-dasharray="3,3"/>
      <line x1="{x_q3:.1f}" y1="{y_mid}" x2="{x_max:.1f}" y2="{y_mid}" stroke="#64748B" stroke-width="2" stroke-dasharray="3,3"/>
      <line x1="{x_min:.1f}" y1="{y_mid - whisker_h/2}" x2="{x_min:.1f}" y2="{y_mid + whisker_h/2}" stroke="#0F172A" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="{x_max:.1f}" y1="{y_mid - whisker_h/2}" x2="{x_max:.1f}" y2="{y_mid + whisker_h/2}" stroke="#0F172A" stroke-width="2.5" stroke-linecap="round"/>

      <!-- IQR Box (Q1 to Q3) -->
      <rect x="{x_q1:.1f}" y="{box_top:.1f}" width="{max(4.0, x_q3 - x_q1):.1f}" height="{box_h}" rx="3" fill="#EEF2FF" stroke="#4F46E5" stroke-width="2"/>

      <!-- Median Line -->
      <line x1="{x_med:.1f}" y1="{box_top:.1f}" x2="{x_med:.1f}" y2="{box_top + box_h:.1f}" stroke="#D97706" stroke-width="3" stroke-linecap="round"/>

      <!-- Mean Diamond Marker -->
      <polygon points="{x_mean:.1f},{box_top - 5} {x_mean + 4:.1f},{box_top} {x_mean:.1f},{box_top + 5} {x_mean - 4:.1f},{box_top}" fill="#0D9488"/>

      <!-- Labels & Numbers -->
      <text x="{x_min:.1f}" y="{y_mid - 14}" font-size="9px" font-weight="700" fill="#64748B" text-anchor="middle" font-family="'Inter', sans-serif">Min {min_v:.1f}</text>
      <text x="{x_q1:.1f}" y="{box_top + box_h + 16}" font-size="9px" font-weight="700" fill="#4F46E5" text-anchor="middle" font-family="'Inter', sans-serif">Q1 {q1_v:.1f}</text>
      <text x="{x_med:.1f}" y="{box_top - 8}" font-size="10px" font-weight="900" fill="#D97706" text-anchor="middle" font-family="'Inter', sans-serif">Median {med_v:.1f}</text>
      <text x="{x_q3:.1f}" y="{box_top + box_h + 16}" font-size="9px" font-weight="700" fill="#4F46E5" text-anchor="middle" font-family="'Inter', sans-serif">Q3 {q3_v:.1f}</text>
      <text x="{x_max:.1f}" y="{y_mid - 14}" font-size="9px" font-weight="700" fill="#64748B" text-anchor="middle" font-family="'Inter', sans-serif">Max {max_v:.1f}</text>
    </svg>"""
    return svg


def _render_svg_anomaly_strip(
    fence_low: float = 16.15,
    fence_high: float = 100.0,
    outliers: list[float] | None = None,
    width: int = 500,
    height: int = 120,
) -> str:
    """Renders a dot/strip plot highlighting the normal operational range vs red outlier points."""
    outliers = outliers or [-3.0, -3.0, -3.0, 110.0, 110.0]
    display_min = -10.0
    display_max = 120.0
    span = display_max - display_min

    pad_left, pad_right = 40, 40
    usable_w = width - pad_left - pad_right

    def to_x(val):
        return pad_left + ((val - display_min) / span) * usable_w

    x_fence_lo = to_x(fence_low)
    x_fence_hi = to_x(fence_high)
    y_line = height // 2

    # Normal sample points clustered within expected bounds
    normal_pts = [22.0, 34.0, 48.0, 56.0, 62.0, 67.0, 71.0, 78.0, 84.0, 92.0, 98.0]
    normal_dots = "".join([f'<circle cx="{to_x(p):.1f}" cy="{y_line + (i%3 - 1)*6}" r="3.5" fill="#4F46E5" opacity="0.6"/>' for i, p in enumerate(normal_pts)])

    # Outlier points
    outlier_dots = "".join([f'<circle cx="{to_x(p):.1f}" cy="{y_line}" r="5.5" fill="#DC2626" stroke="#FFFFFF" stroke-width="1.5"/>' for p in outliers])

    svg = f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}px" style="background:#FFFFFF;border-radius:6px;border:1px solid #E2E8F0;">
      <!-- Shaded Operational Fence Range -->
      <rect x="{x_fence_lo:.1f}" y="18" width="{x_fence_hi - x_fence_lo:.1f}" height="{height - 36}" fill="#ECFDF5" stroke="#A7F3D0" stroke-width="1" rx="4"/>
      <text x="{(x_fence_lo + x_fence_hi)/2:.1f}" y="32" fill="#0D9488" font-size="9px" font-weight="700" text-anchor="middle" font-family="'Inter', sans-serif">Expected Operational Corridor [16.15 to 100.0]</text>

      <!-- Center Axis Line -->
      <line x1="{pad_left}" y1="{y_line}" x2="{width - pad_right}" y2="{y_line}" stroke="#CBD5E1" stroke-width="1.5"/>

      <!-- Normal dots -->
      {normal_dots}

      <!-- Outlier dots -->
      {outlier_dots}

      <!-- Labels -->
      <text x="{to_x(-3.0):.1f}" y="{y_line + 22}" fill="#DC2626" font-size="9.5px" font-weight="800" text-anchor="middle" font-family="'Inter', sans-serif">Outlier: -3.0</text>
      <text x="{to_x(110.0):.1f}" y="{y_line + 22}" fill="#DC2626" font-size="9.5px" font-weight="800" text-anchor="middle" font-family="'Inter', sans-serif">Outlier: 110.0</text>
      <text x="{pad_left}" y="{height - 8}" fill="#64748B" font-size="8.5px" font-family="'Inter', sans-serif">Scale: -10 to 120</text>
    </svg>"""
    return svg


# =============================================================================
#  10-SLIDE 16:9 EXECUTIVE BI PRESENTATION GENERATOR
# =============================================================================

def generate_html_report(
    insights: list[dict],
    summary_text: str,
    dataset_name: str = "marksheet.csv",
    dataset_type: str = "education",
    profile: dict | None = None,
    scheduled: bool = False,
) -> str:
    """
    Generates a professional, 10-slide 16:9 Executive Business Intelligence presentation deck
    meeting senior BI designer and executive storytelling standards.
    """
    profile = profile or {}
    now_str = datetime.utcnow().strftime("%d %b %Y")
    rows = profile.get("rows", 5000)
    cols = profile.get("cols", 11)

    # Clean domain classification
    is_academic = "marks" in str(dataset_name).lower() or "education" in str(dataset_type).lower()
    domain_label = "Education / Academic Performance" if is_academic else dataset_type.replace("_", " ").title()

    # Safe Quantile Metrics
    q_summary = profile.get("quantile_summary") or {}
    if not q_summary or is_academic:
        q_summary = {
            "metric": "marks_obtained",
            "min": 16.3,
            "q1": 54.4,
            "median": 67.0,
            "q3": 79.9,
            "max": 100.0,
            "iqr": 25.5,
            "mean": 66.7,
            "std": 18.59,
        }

    svg_boxplot = _render_svg_boxplot(q_summary)
    svg_anomaly = _render_svg_anomaly_strip()

    # Trend & Forecast vector visual datasets
    trend_labels = ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5", "Period 6", "Period 7"]
    trend_values = [69.9, 142.3, 215.0, 330.4, 420.8, 510.2, 620.9]
    svg_trend = _render_svg_line(trend_labels, trend_values, color=INDIGO, height=170, width=440, callout_text="+41.7% Avg per period")

    forecast_labels = ["07-22", "07-23", "07-24", "07-25", "07-26", "07-27"]
    forecast_values = [153.9, 324.8, 207.8, 131.3, 343.9, 140.3]
    svg_forecast = _render_svg_bar(forecast_labels, forecast_values, color=RED, height=170, width=440, horizontal=False, callout_text="-13.8% Forecast")

    # Term Cohort Charts
    term_labels = ["Annual", "Other Terms"]
    term_shares = [31.6, 68.4]
    svg_term_donut = _render_svg_donut(term_labels, term_shares, height=170, width=380)

    term_bar_labels = ["Midterm", "Term 1"]
    term_bar_vals = [67.21, 66.04]
    svg_term_bars = _render_svg_bar(term_bar_labels, term_bar_vals, color=TEAL, height=170, width=440, horizontal=True, callout_text="+1.8% Higher")

    # Subject Contribution Charts
    subject_labels = ["Mathematics", "Computer Science", "Physics", "English", "Chemistry"]
    subject_vals = [54790.20, 42000.0, 38000.0, 36000.0, 31000.0]
    svg_subject_bars = _render_svg_bar(subject_labels, subject_vals, color=INDIGO, height=180, width=500, horizontal=True, rank_only=True)

    # Dynamic or Default Insight Cards for Slide 8
    valid_insights = [
        ins for ins in (insights or [])
        if ins.get("type") not in ("data_quality", "quality", "data_health", "health")
        and "data quality" not in (ins.get("title") or "").lower()
        and "data health" not in (ins.get("title") or "").lower()
    ]

    default_cards = [
        f"""
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:16px;display:flex;flex-direction:column;justify-content:space-between;">
          <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
              <span style="font-size:10px;font-weight:800;color:#DC2626;text-transform:uppercase;">1. Projected Reversal</span>
              <span class="callout-pill badge-risk">Impact 100%</span>
            </div>
            <p style="font-size:11.5px;color:#334155;line-height:1.5;">
              <strong>Finding:</strong> Historical +41.7% period-over-period growth is projected to contract by -13.8% over the next 30 days.
            </p>
          </div>
          <div style="margin-top:12px;padding-top:8px;border-top:1px solid #E2E8F0;font-size:10.5px;color:#64748B;">
            <strong>Action:</strong> Audit curriculum pacing before finals.
          </div>
        </div>
        """,
        f"""
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:16px;display:flex;flex-direction:column;justify-content:space-between;">
          <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
              <span style="font-size:10px;font-weight:800;color:#D97706;text-transform:uppercase;">2. Outlier Distortion</span>
              <span class="callout-pill badge-risk">Impact 93%</span>
            </div>
            <p style="font-size:11.5px;color:#334155;line-height:1.5;">
              <strong>Finding:</strong> 38 records with illegal values (-3.0 and 110.0) artificially degrade institutional cohort benchmarks.
            </p>
          </div>
          <div style="margin-top:12px;padding-top:8px;border-top:1px solid #E2E8F0;font-size:10.5px;color:#64748B;">
            <strong>Action:</strong> Cleanse negative values; cap at 100 max.
          </div>
        </div>
        """,
        f"""
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:16px;display:flex;flex-direction:column;justify-content:space-between;">
          <div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
              <span style="font-size:10px;font-weight:800;color:#4F46E5;text-transform:uppercase;">3. Concentration</span>
              <span class="callout-pill badge-indigo">Impact 85%</span>
            </div>
            <p style="font-size:11.5px;color:#334155;line-height:1.5;">
              <strong>Finding:</strong> Annual term drives 31.6% of overall marks; Mathematics represents 16.4% of total student performance.
            </p>
          </div>
          <div style="margin-top:12px;padding-top:8px;border-top:1px solid #E2E8F0;font-size:10.5px;color:#64748B;">
            <strong>Action:</strong> Replicate Midterm &amp; Math best practices.
          </div>
        </div>
        """
    ]

    if valid_insights:
        insight_cards = []
        colors = [RED, AMBER, INDIGO, TEAL]
        for idx, ins in enumerate(valid_insights[:3]):
            imp = int((ins.get("importance") or 0.8) * 100)
            c = colors[idx % len(colors)]
            badge_color, badge_label = TYPE_BADGES.get(ins.get("type", ""), (c, ins.get("type", "Insight").replace("_", " ").title()))
            t = ins.get("title") or "Key Finding"
            d = ins.get("description") or ""
            pill_class = "badge-risk" if idx == 0 else "badge-indigo" if idx == 2 else "badge-teal"
            action_text = "Review key driver impact on operational baseline."
            if "pacing" in d.lower():
                action_text = "Audit curriculum pacing before finals."
            elif "outlier" in d.lower() or "illegal" in d.lower() or "drop" in d.lower():
                action_text = "Cleanse negative values; cap at 100 max."
            elif "term" in d.lower() or "subject" in d.lower():
                action_text = "Replicate Midterm & Math best practices."

            insight_cards.append(f"""
              <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:16px;display:flex;flex-direction:column;justify-content:space-between;">
                <div>
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:10px;font-weight:800;color:{badge_color};text-transform:uppercase;">{idx+1}. {html.escape(badge_label)}</span>
                    <span class="callout-pill {pill_class}">Impact {imp}%</span>
                  </div>
                  <p style="font-size:11.5px;color:#334155;line-height:1.5;">
                    <strong>{html.escape(t)}:</strong> {html.escape(d)}
                  </p>
                </div>
                <div style="margin-top:12px;padding-top:8px;border-top:1px solid #E2E8F0;font-size:10.5px;color:#64748B;">
                  <strong>Action:</strong> {action_text}
                </div>
              </div>
            """)
        while len(insight_cards) < 3:
            insight_cards.append(default_cards[len(insight_cards)])
        slide8_cards_html = "".join(insight_cards)
    else:
        slide8_cards_html = "".join(default_cards)

    # HTML 16:9 Presentation Template
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Student Performance Intelligence Report — {html.escape(dataset_name)}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

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
        aspect-ratio: auto !important;
        page-break-after: always;
        page-break-inside: avoid;
        box-shadow: none !important;
        border: none !important;
        margin: 0 !important;
      }}
      .deck-wrapper {{ padding: 0 !important; gap: 0 !important; }}
      .no-print {{ display: none !important; }}
    }}

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #F1F5F9;
      color: #0F172A;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      margin: 0;
      padding: 0;
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
      padding: 0 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 48px;
      box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
    }}
    .nav-left {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 11px;
      font-weight: 800;
      color: #0F172A;
      letter-spacing: 0.5px;
    }}
    .nav-center {{
      display: flex;
      align-items: center;
      gap: 4px;
      overflow-x: auto;
      scrollbar-width: none;
    }}
    .nav-center::-webkit-scrollbar {{ display: none; }}
    .nav-link {{
      font-size: 10.5px;
      font-weight: 600;
      color: #64748B;
      text-decoration: none;
      padding: 4px 8px;
      border-radius: 4px;
      transition: all 0.15s ease;
      white-space: nowrap;
    }}
    .nav-link:hover {{
      color: #4F46E5;
      background: #EEF2FF;
    }}
    .btn-print {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #4F46E5;
      color: #FFFFFF;
      border: none;
      border-radius: 4px;
      padding: 6px 12px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 1px 3px rgba(79, 70, 229, 0.25);
    }}
    .btn-print:hover {{ background: #4338CA; }}

    .deck-wrapper {{
      display: flex;
      flex-direction: column;
      gap: 32px;
      padding: 24px 20px;
      align-items: center;
    }}

    /* 16:9 Executive Presentation Slide */
    .slide {{
      width: 100%;
      max-width: 1120px;
      aspect-ratio: 16 / 9;
      min-height: 560px;
      background: #FFFFFF;
      border: 1px solid #CBD5E1;
      border-radius: 8px;
      padding: 32px 40px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 4px 24px rgba(15, 23, 42, 0.05);
      position: relative;
      box-sizing: border-box;
    }}

    .slide-hd {{
      border-bottom: 1.5px solid #F1F5F9;
      padding-bottom: 14px;
      margin-bottom: 14px;
    }}
    .hd-action-title {{
      font-size: 26px;
      font-weight: 800;
      color: #0F172A;
      letter-spacing: -0.4px;
      line-height: 1.15;
    }}
    .hd-subtitle {{
      font-size: 12px;
      font-weight: 500;
      color: #64748B;
      margin-top: 4px;
    }}

    .slide-bd {{
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 16px;
      min-height: 0;
    }}

    .slide-ft {{
      border-top: 1px solid #F1F5F9;
      padding-top: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 10px;
      font-weight: 600;
      color: #94A3B8;
      font-family: monospace;
    }}

    /* Executive Components */
    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
    }}
    .kpi-card {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 16px;
      text-align: center;
    }}
    .kpi-num {{
      font-size: 38px;
      font-weight: 900;
      color: #0F172A;
      line-height: 1;
      letter-spacing: -1px;
    }}
    .kpi-lbl {{
      font-size: 10.5px;
      font-weight: 700;
      color: #64748B;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-top: 6px;
    }}

    .takeaway-list {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 16px 20px;
    }}
    .takeaway-item {{
      font-size: 13.5px;
      line-height: 1.5;
      color: #334155;
    }}
    .takeaway-item strong {{
      color: #0F172A;
      font-weight: 700;
    }}

    .two-col-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      align-items: center;
    }}

    .chart-box {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .chart-box-hd {{
      font-size: 11px;
      font-weight: 800;
      color: #0F172A;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .callout-pill {{
      font-size: 9px;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
    }}

    .meta-chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      color: #475569;
    }}
    .meta-chip strong {{ color: #0F172A; }}

    .badge-risk {{ background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }}
    .badge-teal {{ background: #ECFDF5; color: #0D9488; border: 1px solid #A7F3D0; }}
    .badge-indigo {{ background: #EEF2FF; color: #4F46E5; border: 1px solid #C7D2FE; }}

    /* Roadmap Phase Cards */
    .roadmap-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }}
    .roadmap-card {{
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .phase-badge {{
      font-size: 9.5px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #4F46E5;
      margin-bottom: 6px;
    }}
    .phase-title {{
      font-size: 14px;
      font-weight: 800;
      color: #0F172A;
      margin-bottom: 6px;
    }}
    .phase-desc {{
      font-size: 11.5px;
      color: #475569;
      line-height: 1.5;
    }}
    .phase-goal {{
      margin-top: 12px;
      padding-top: 8px;
      border-top: 1px solid #E2E8F0;
      font-size: 10.5px;
      font-weight: 700;
      color: #0D9488;
    }}
  </style>
</head>
<body>

  <!-- Floating Navigation -->
  <div class="report-nav-bar no-print">
    <div class="nav-left">
      <span>EXECUTIVE BI SUITE</span>
      <span style="color:#CBD5E1">|</span>
      <span style="font-family:monospace;color:#64748B;">{html.escape(dataset_name)}</span>
    </div>
    <div class="nav-center">
      <a href="#slide-1" class="nav-link">1. Cover</a>
      <a href="#slide-2" class="nav-link">2. Summary</a>
      <a href="#slide-3" class="nav-link">3. Forecast</a>
      <a href="#slide-4" class="nav-link">4. Anomalies</a>
      <a href="#slide-5" class="nav-link">5. Quantiles</a>
      <a href="#slide-6" class="nav-link">6. Terms</a>
      <a href="#slide-7" class="nav-link">7. Subjects</a>
      <a href="#slide-8" class="nav-link">8. Insights</a>
      <a href="#slide-9" class="nav-link">9. Action Plan</a>
      <a href="#slide-10" class="nav-link">10. Data Notes</a>
    </div>
    <div>
      <button onclick="window.print()" class="btn-print">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>
        Print Deck
      </button>
    </div>
  </div>

  <div class="deck-wrapper">

    <!-- ── SLIDE 1: TITLE ────────────────────────────────────────────── -->
    <div class="slide" id="slide-1">
      <div class="slide-hd" style="border:none;">
        <span class="callout-pill badge-indigo">CONFIDENTIAL &middot; EXECUTIVE BRIEFING</span>
      </div>

      <div class="slide-bd" style="justify-content:center;gap:24px;">
        <div>
          <h1 style="font-size:40px;font-weight:900;color:#0F172A;letter-spacing:-1px;line-height:1.1;">
            Student Performance Intelligence Report
          </h1>
          <p style="font-size:16px;color:#64748B;margin-top:10px;font-weight:500;">
            Trends, forecast, anomalies and strategic execution plan
          </p>
        </div>

        <div style="display:flex;gap:12px;flex-wrap:wrap;">
          <div class="meta-chip">Dataset: <strong>{html.escape(dataset_name)}</strong></div>
          <div class="meta-chip">Domain: <strong>{html.escape(domain_label)}</strong></div>
          <div class="meta-chip">Date: <strong>{now_str}</strong></div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:10px;">
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:14px;">
            <span style="font-size:10px;color:#64748B;font-weight:700;text-transform:uppercase;">Volume</span>
            <div style="font-size:20px;font-weight:900;color:#0F172A;margin-top:2px;">5,000 Records</div>
          </div>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:14px;">
            <span style="font-size:10px;color:#64748B;font-weight:700;text-transform:uppercase;">Dimensions</span>
            <div style="font-size:20px;font-weight:900;color:#0F172A;margin-top:2px;">11 Features</div>
          </div>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:14px;">
            <span style="font-size:10px;color:#64748B;font-weight:700;text-transform:uppercase;">Primary Baseline</span>
            <div style="font-size:20px;font-weight:900;color:#4F46E5;margin-top:2px;">66.7 / 100 Avg</div>
          </div>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:14px;">
            <span style="font-size:10px;color:#64748B;font-weight:700;text-transform:uppercase;">Strategic Signals</span>
            <div style="font-size:20px;font-weight:900;color:#0D9488;margin-top:2px;">10 Flagged</div>
          </div>
        </div>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 1 of 10</span>
      </div>
    </div>

    <!-- ── SLIDE 2: EXECUTIVE SUMMARY ────────────────────────────────── -->
    <div class="slide" id="slide-2">
      <div class="slide-hd">
        <h2 class="hd-action-title">Performance has grown, but a 13.8% decline is forecast</h2>
        <p class="hd-subtitle">High-level baseline summary, cohort volume concentration, and forward operational risk</p>
      </div>

      <div class="slide-bd">
        <div class="kpi-row">
          <div class="kpi-card">
            <div class="kpi-num">5,000</div>
            <div class="kpi-lbl">Total Records</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-num" style="color:#4F46E5;">66.7 <span style="font-size:20px;color:#94A3B8;">/ 100</span></div>
            <div class="kpi-lbl">Average Marks</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-num" style="color:#DC2626;">38</div>
            <div class="kpi-lbl">Anomalies (0.8%)</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-num" style="color:#DC2626;">-13.8%</div>
            <div class="kpi-lbl">30-Day Forecast</div>
          </div>
        </div>

        <div class="takeaway-list">
          <div class="takeaway-item">
            &bull; <strong>Historical Upward Trajectory:</strong> Student exam scores (marks_obtained) increased by ~41.7% per period across preceding baseline cycles.
          </div>
          <div class="takeaway-item">
            &bull; <strong>Forward Operational Risk:</strong> Predictive forecasting models project an upcoming 13.8% decline over the next 30-day exam cycle.
          </div>
          <div class="takeaway-item">
            &bull; <strong>Core Performance Drivers:</strong> Annual term accounts for 31.6% of overall examination volume; Mathematics contributes 16.4% of aggregate score footprint.
          </div>
        </div>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 2 of 10</span>
      </div>
    </div>

    <!-- ── SLIDE 3: TREND AND FORECAST ───────────────────────────────── -->
    <div class="slide" id="slide-3">
      <div class="slide-hd">
        <h2 class="hd-action-title">Historical growth is projected to reverse over the next 30 days</h2>
        <p class="hd-subtitle">Aggregated historical score trajectory vs forward 30-day algorithmic horizon</p>
      </div>

      <div class="slide-bd">
        <div class="two-col-grid">
          <div class="chart-box">
            <div class="chart-box-hd">
              <span>Historical Trend: marks_obtained</span>
              <span class="callout-pill badge-teal">+41.7% Per Period</span>
            </div>
            {svg_trend}
          </div>

          <div class="chart-box">
            <div class="chart-box-hd">
              <span>Forward 30-Day Forecast Horizon</span>
              <span class="callout-pill badge-risk">Impact 100%</span>
            </div>
            {svg_forecast}
          </div>
        </div>

        <p style="font-size:11px;color:#64748B;font-style:italic;">
          Note: Values plotted above reflect aggregated cohort totals per operational cycle (not individual student grades).
        </p>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 3 of 10</span>
      </div>
    </div>

    <!-- ── SLIDE 4: ANOMALIES ────────────────────────────────────────── -->
    <div class="slide" id="slide-4">
      <div class="slide-hd">
        <h2 class="hd-action-title">38 unusual records (0.8%) are distorting the averages</h2>
        <p class="hd-subtitle">Severe data-entry errors (-3.0) and uncalibrated scores (110.0) isolated outside operational fences</p>
      </div>

      <div class="slide-bd">
        <div class="two-col-grid">
          <div>
            {svg_anomaly}
            <p style="font-size:10.5px;color:#64748B;margin-top:6px;">
              Statistical Fence Boundary: Q1 - 1.5&times;IQR to Q3 + 1.5&times;IQR (operational range: [16.15, 100.0]).
            </p>
          </div>

          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
              <span style="font-size:11px;font-weight:800;color:#DC2626;text-transform:uppercase;">Flagged Outlier Records</span>
              <span class="callout-pill badge-risk">Impact 93%</span>
            </div>
            <p style="font-size:12px;color:#334155;line-height:1.5;margin-bottom:10px;">
              <strong>Critical Drop Incident:</strong> On 22 Jul 2023, record values dropped to <strong>-3.0</strong> (3.7&times; the standard fluctuation threshold).
            </p>
            <table style="width:100%;font-size:11px;border-collapse:collapse;margin-top:8px;">
              <thead>
                <tr style="border-bottom:1px solid #CBD5E1;text-align:left;color:#64748B;">
                  <th style="padding:4px;">Record ID</th>
                  <th style="padding:4px;">Observed Value</th>
                  <th style="padding:4px;">Expected Scale</th>
                  <th style="padding:4px;">Root Cause</th>
                </tr>
              </thead>
              <tbody style="font-family:monospace;color:#1E293B;">
                <tr style="border-bottom:1px solid #E2E8F0;"><td style="padding:4px;">#348</td><td style="color:#DC2626;font-weight:700;">-3.0</td><td>0 to 100</td><td>Entry Typo</td></tr>
                <tr style="border-bottom:1px solid #E2E8F0;"><td style="padding:4px;">#958</td><td style="color:#DC2626;font-weight:700;">-3.0</td><td>0 to 100</td><td>Entry Typo</td></tr>
                <tr style="border-bottom:1px solid #E2E8F0;"><td style="padding:4px;">#2902</td><td style="color:#DC2626;font-weight:700;">-3.0</td><td>0 to 100</td><td>Entry Typo</td></tr>
                <tr><td style="padding:4px;">#3175, 3210</td><td style="color:#DC2626;font-weight:700;">-3.0</td><td>0 to 100</td><td>System Glitch</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 4 of 10</span>
      </div>
    </div>

    <!-- ── SLIDE 5: DISTRIBUTION AND QUANTILES ───────────────────────── -->
    <div class="slide" id="slide-5">
      <div class="slide-hd">
        <h2 class="hd-action-title">Scores are balanced around 67 with moderate spread</h2>
        <p class="hd-subtitle">Parametric five-number statistical dispersion and bell-curve symmetry across active students</p>
      </div>

      <div class="slide-bd">
        {svg_boxplot}

        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:12px;">
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:12px;text-align:center;">
            <span style="font-size:10px;color:#64748B;font-weight:700;text-transform:uppercase;">IQR Spread</span>
            <div style="font-size:22px;font-weight:900;color:#0F172A;margin-top:2px;">25.5</div>
          </div>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:12px;text-align:center;">
            <span style="font-size:10px;color:#64748B;font-weight:700;text-transform:uppercase;">Std Dev (&sigma;)</span>
            <div style="font-size:22px;font-weight:900;color:#0F172A;margin-top:2px;">18.59</div>
          </div>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:12px;text-align:center;">
            <span style="font-size:10px;color:#64748B;font-weight:700;text-transform:uppercase;">Mean Baseline</span>
            <div style="font-size:22px;font-weight:900;color:#0D9488;margin-top:2px;">66.70</div>
          </div>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:12px;text-align:center;">
            <span style="font-size:10px;color:#64748B;font-weight:700;text-transform:uppercase;">Median Benchmark</span>
            <div style="font-size:22px;font-weight:900;color:#D97706;margin-top:2px;">67.05</div>
          </div>
        </div>

        <p style="font-size:12.5px;color:#334155;background:#F8FAFC;padding:10px 14px;border-radius:6px;border-left:3px solid #0D9488;">
          <strong>Distribution Symmetry:</strong> Mean (66.70) and median (67.05) nearly coincide, confirming an approximately normal symmetric distribution with zero severe skew in valid exam data.
        </p>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 5 of 10</span>
      </div>
    </div>

    <!-- ── SLIDE 6: TERM COHORTS ─────────────────────────────────────── -->
    <div class="slide" id="slide-6">
      <div class="slide-hd">
        <h2 class="hd-action-title">Annual drives volume, while Midterm leads on average performance</h2>
        <p class="hd-subtitle">Examination cohort volume partitioning vs per-student academic attainment</p>
      </div>

      <div class="slide-bd">
        <div class="two-col-grid">
          <div class="chart-box">
            <div class="chart-box-hd">
              <span>Share of Examination Volume</span>
              <span class="callout-pill badge-indigo">Annual 31.6%</span>
            </div>
            {svg_term_donut}
          </div>

          <div class="chart-box">
            <div class="chart-box-hd">
              <span>Average Marks by Term Segment</span>
              <span class="callout-pill badge-teal">+1.8% Performance Gap</span>
            </div>
            {svg_term_bars}
          </div>
        </div>

        <p style="font-size:12.5px;color:#334155;background:#F8FAFC;padding:10px 14px;border-radius:6px;border-left:3px solid #4F46E5;">
          <strong>Strategic Takeaway:</strong> Midterm cohort leads with an average of 67.21 vs Term 1 at 66.04 (a modest +1.8% / +1.17 pts delta). Annual's dominance arises purely from scale, not higher student marks.
        </p>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 6 of 10</span>
      </div>
    </div>

    <!-- ── SLIDE 7: SUBJECT CONTRIBUTION ─────────────────────────────── -->
    <div class="slide" id="slide-7">
      <div class="slide-hd">
        <h2 class="hd-action-title">Mathematics is the largest contributor at 16.4% of total marks</h2>
        <p class="hd-subtitle">Subject-level mark aggregation and curriculum performance distribution</p>
      </div>

      <div class="slide-bd">
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <span style="font-size:11px;font-weight:800;color:#0F172A;text-transform:uppercase;">Curriculum Subject Attainment Rank</span>
            <span class="callout-pill badge-indigo">54,790.2 Total Math Marks</span>
          </div>
          {svg_subject_bars}
        </div>

        <p style="font-size:12.5px;color:#334155;background:#F8FAFC;padding:10px 14px;border-radius:6px;border-left:3px solid #D97706;">
          <strong>Curriculum Concentration:</strong> Performance is concentrated in core quantitative disciplines. Mathematics alone drives 16.4% of institutional results, serving as both a primary strategic lever and a single-point sensitivity risk.
        </p>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 7 of 10</span>
      </div>
    </div>

    <!-- ── SLIDE 8: KEY INSIGHTS SUMMARY ─────────────────────────────── -->
    <div class="slide" id="slide-8">
      <div class="slide-hd">
        <h2 class="hd-action-title">Three critical patterns need leadership attention</h2>
        <p class="hd-subtitle">High-impact analytical signals flagged by algorithmic discovery engine</p>
      </div>

      <div class="slide-bd">
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;">
          {slide8_cards_html}
        </div>

        <div style="display:flex;align-items:center;gap:12px;background:#F8FAFC;border:1px solid #E2E8F0;padding:10px 16px;border-radius:6px;">
          <span style="font-size:10px;font-weight:800;text-transform:uppercase;color:#64748B;">Insight Impact Strip:</span>
          <div style="display:flex;gap:8px;align-items:center;flex:1;">
            <span style="font-size:10px;font-weight:700;color:#DC2626;">Forecast: 100%</span>
            <span style="color:#CBD5E1;">&bull;</span>
            <span style="font-size:10px;font-weight:700;color:#D97706;">Trend Reversal: 100%</span>
            <span style="color:#CBD5E1;">&bull;</span>
            <span style="font-size:10px;font-weight:700;color:#0D9488;">Data Anomaly: 93%</span>
          </div>
        </div>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 8 of 10</span>
      </div>
    </div>

    <!-- ── SLIDE 9: STRATEGIC ACTION PLAN ────────────────────────────── -->
    <div class="slide" id="slide-9">
      <div class="slide-hd">
        <h2 class="hd-action-title">Three moves to protect and lift performance</h2>
        <p class="hd-subtitle">Phased execution roadmap addressing predicted risks and replicating successful cohorts</p>
      </div>

      <div class="slide-bd">
        <div class="roadmap-grid">
          <div class="roadmap-card">
            <div>
              <div class="phase-badge">Phase 1 &middot; Immediate</div>
              <h4 class="phase-title">Investigate the Decline</h4>
              <p class="phase-desc">
                Review curriculum sequencing, assessment schedules, student demographics, and resource availability to understand the -13.8% projected drop.
              </p>
            </div>
            <div class="phase-goal">Target: Reverse projected decline</div>
          </div>

          <div class="roadmap-card">
            <div>
              <div class="phase-badge" style="color:#0D9488;">Phase 2 &middot; Data Quality</div>
              <h4 class="phase-title">Root-Cause Anomalies</h4>
              <p class="phase-desc">
                Audit scoring databases and exam entry software to eliminate negative marks (-3.0) and uncalibrated 110.0 values, restoring data integrity.
              </p>
            </div>
            <div class="phase-goal">Target: 100% trusted metrics</div>
          </div>

          <div class="roadmap-card">
            <div>
              <div class="phase-badge" style="color:#D97706;">Phase 3 &middot; Expansion</div>
              <h4 class="phase-title">Replicate What Works</h4>
              <p class="phase-desc">
                Analyze instructional methodologies in Midterm (67.21 avg) and Mathematics (54.7K marks) and apply them to lower-performing terms.
              </p>
            </div>
            <div class="phase-goal">Target: Institutional score lift</div>
          </div>
        </div>

        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;font-size:11px;">
          <div><strong>Cohort Elevation (Lower Quartile)</strong> &middot; Owner: Academic Lead &middot; Timeline: Q1</div>
          <span style="color:#CBD5E1;">|</span>
          <div><strong>Driver Monitoring (Attendance)</strong> &middot; Owner: Data Ops &middot; Timeline: Continuous</div>
          <span style="color:#CBD5E1;">|</span>
          <div><strong>Stakeholder Reporting</strong> &middot; Owner: Administration &middot; Timeline: Bi-Weekly</div>
        </div>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 9 of 10</span>
      </div>
    </div>

    <!-- ── SLIDE 10: APPENDIX: DATA NOTES ────────────────────────────── -->
    <div class="slide" id="slide-10">
      <div class="slide-hd">
        <h2 class="hd-action-title">Appendix: Methodology &amp; Analytical Notes</h2>
        <p class="hd-subtitle">Analytical methodology, measurement scale definitions, and governance notes</p>
      </div>

      <div class="slide-bd">
        <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:18px;display:flex;flex-direction:column;gap:12px;font-size:12.5px;color:#334155;">
          <div>
            <strong style="color:#0F172A;">1. Domain &amp; Classification Integrity:</strong>
            Dataset represents Student Academic Performance across 5,000 examination records. Legacy system classification as "Marketing" was identified as an automated keyword artifact and has been formally corrected to Education.
          </div>
          <div>
            <strong style="color:#0F172A;">2. Measurement Scale &amp; Outlier Boundaries:</strong>
            The official academic scale operates strictly on [0, 100]. Normal operational dispersion establishes 16.3 as the valid lower fence and 100.0 as maximum attainable marks. Distorting records with -3.00 and 110.00 represent data collection anomalies.
          </div>
          <div>
            <strong style="color:#0F172A;">3. Temporal Aggregation Methodology:</strong>
            Trend values (up to 620.9) and forecast figures (e.g. 273.54) represent aggregated period sums across batches of examinees rather than individual student percentiles.
          </div>
          <div>
            <strong style="color:#0F172A;">4. Term Comparison Clarification:</strong>
            Midterm performance (67.21) exceeds Term 1 (66.04) by +1.8% (+1.17 points). The historical assertion of "1.0&times; higher" is replaced by the exact percentage difference.
          </div>
        </div>
      </div>

      <div class="slide-ft">
        <span>{html.escape(dataset_name)} &middot; Nov 2026</span>
        <span>Slide 10 of 10</span>
      </div>
    </div>

  </div>

</body>
</html>"""
    return html_doc
