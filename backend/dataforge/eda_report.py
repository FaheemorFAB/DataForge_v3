"""
EDA Report Generator  (Fixed 2026-03)
═══════════════════════════════════════
Generates a full HTML profiling report using ydata-profiling.
Falls back to a lightweight pandas-based report if ydata-profiling is
unavailable or crashes (which is the #1 cause of the EDA 500 error).

Fixes applied
─────────────
FIX A  Suppress imghdr / visions DeprecationWarning before import.
FIX B  Inject CSS custom-property theme block + postMessage theme-switcher.
FIX C  Rewrite Bootstrap navbar classes so dark mode works on the navbar.
FIX D  (NEW) Wrap entire ydata-profiling call in try/except; fall back to
       a self-contained pandas HTML report so EDA never returns a 500.
FIX E  (NEW) Guard ProfileReport import — handle both 'ydata_profiling'
       and legacy 'pandas_profiling' package names gracefully.
"""

import io
import logging
import re
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


# ── Dtype sanitiser ───────────────────────────────────────────────────────────

def _sanitize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert columns to types ydata-profiling can handle without crashing.
    Converts complex / interval / period dtypes to strings.
    """
    df = df.copy()
    for col in df.columns:
        dtype = str(df[col].dtype)
        if dtype.startswith("complex"):
            df[col] = df[col].astype(str)
        elif dtype.startswith("interval") or dtype.startswith("period"):
            df[col] = df[col].astype(str)
        elif dtype == "object":
            # Ensure pure string (some versions of pandas store mixed types)
            df[col] = df[col].where(df[col].isna(), df[col].astype(str))
    return df


# ── Theme injection helpers ───────────────────────────────────────────────────

_THEME_CSS = """
<style id="df-theme-block">
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&family=Inter:wght@300;400;500;700;900&family=Outfit:wght@300;400;500;700;900&family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Poppins:wght@300;400;500;700;900&family=Rajdhani:wght@500;700&display=swap');

/* Default Theme: Dark */
:root, [data-theme="dark"], [data-bs-theme="dark"] {
  --bg:          #050505;
  --card-bg:     #0A0A0B;
  --text:        #ffffff;
  --border:      #1A1A1C;
  --navbar-bg:   #0A0A0B;
}

/* Light Theme */
[data-theme="light"], [data-bs-theme="light"] {
  --bg:          #c8c8cd;
  --card-bg:     #dbd2d2;
  --text:        #0a0a0b;
  --border:      #e2e2e6;
  --navbar-bg:   #d1caca;
}

/* Dracula */
[data-theme="dracula"] {
  --bg:          #282a36;
  --card-bg:     #1e1f29;
  --text:        #f8f8f2;
  --border:      #44475a;
  --navbar-bg:   #282a36;
}

/* Slate Blue */
[data-theme="slate"] {
  --bg:          #1e222b;
  --card-bg:     #252a34;
  --text:        #f1f5f9;
  --border:      #303643;
  --navbar-bg:   #1e222b;
}

/* Emerald Sage */
[data-theme="emerald"] {
  --bg:          #141e1b;
  --card-bg:     #1b2824;
  --text:        #e6f4f1;
  --border:      #273a34;
  --navbar-bg:   #141e1b;
}

/* Nord */
[data-theme="nord"] {
  --bg:          #2e3440;
  --card-bg:     #3b4252;
  --text:        #eceff4;
  --border:      #4c566a;
  --navbar-bg:   #2e3440;
}

/* Luxury */
[data-theme="luxury"] {
  --bg:          #09090b;
  --card-bg:     #18181b;
  --text:        #f4f4f5;
  --border:      #27272a;
  --navbar-bg:   #09090b;
}

/* Cupcake */
[data-theme="cupcake"] {
  --bg:          #faf7f5;
  --card-bg:     #efeae6;
  --text:        #291334;
  --border:      #d3c5ba;
  --navbar-bg:   #faf7f5;
}

/* Font Families */
[data-font="inter"] {
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
[data-font="outfit"] {
  --font-family: 'Outfit', sans-serif;
}
[data-font="poppins"] {
  --font-family: 'Poppins', sans-serif;
}
[data-font="roboto-mono"] {
  --font-family: 'Roboto Mono', monospace;
}
[data-font="playfair"] {
  --font-family: 'Playfair Display', Georgia, serif;
}
[data-font="rajdhani"] {
  --font-family: 'Rajdhani', sans-serif;
}

body, p, span, h1, h2, h3, h4, h5, h6, table, td, th, code, pre {
  font-family: var(--font-family, 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif) !important;
}

body{background:var(--bg)!important;color:var(--text)!important}
.card{background:var(--card-bg)!important;border-color:var(--border)!important;color:var(--text)!important}
.navbar,.navbar-default{background:var(--navbar-bg)!important;border-color:var(--border)!important}
.navbar .navbar-brand,.navbar .nav-link,.navbar-nav .nav-link{color:var(--text)!important}
.table{color:var(--text)!important}
.table>:not(caption)>*>*{background-color:var(--card-bg)!important;color:var(--text)!important}
</style>
"""

_THEME_JS = """
<script id="df-theme-script">
(function(){
  function applyTheme(t, f){
    if(t) {
      document.documentElement.setAttribute('data-theme', t);
      document.documentElement.setAttribute('data-bs-theme', t === 'light' || t === 'cupcake' || t === 'retro' ? 'light' : 'dark');
    }
    if(f) {
      document.documentElement.setAttribute('data-font', f);
    }
  }
  // Apply theme sent from parent frame
  window.addEventListener('message', function(e){
    if(e.data && (e.data.type === 'theme-change' || e.data.type === 'set-theme')) {
      applyTheme(e.data.theme, e.data.font);
    }
  });
  // Inherit parent theme on load
  try{
    var p = window.parent;
    if(p && p !== window){
      var t = p.document.documentElement.getAttribute('data-theme') || 'dark';
      var f = p.document.documentElement.getAttribute('data-font') || 'inter';
      applyTheme(t, f);
    }
  }catch(ex){}
})();
</script>
"""


def _inject_theme(html: str) -> str:
    """FIX B — inject theme CSS + JS before </head>."""
    return html.replace("</head>", _THEME_CSS + _THEME_JS + "\n</head>", 1)


def _fix_navbar(html: str) -> str:
    """FIX C — neutralise Bootstrap light-mode navbar classes."""
    html = re.sub(r'\bnavbar-light\b', '', html)
    html = re.sub(r'\bbg-light\b',    '', html)
    html = re.sub(r'\bbg-white\b',    '', html)
    # Strip inline background / color styles from the navbar element
    html = re.sub(
        r'(<nav\b[^>]*?)(\s+style="[^"]*?")',
        r'\1',
        html,
        flags=re.IGNORECASE,
    )
    return html


# ── Pandas fallback report ────────────────────────────────────────────────────

def _svg_bar(value: float, max_val: float, color: str = "#4f46e5", height: int = 14) -> str:
    """
    Render a horizontal SVG bar for use inside a table cell.
    value / max_val determines the fill fraction.
    """
    width = 120
    fill  = max(2, int(width * min(value / max_val, 1.0))) if max_val > 0 else 0
    return (
        f'<svg width="{width}" height="{height}" style="vertical-align:middle">'
        f'<rect width="{width}" height="{height}" rx="3" fill="#2d3748"/>'
        f'<rect width="{fill}" height="{height}" rx="3" fill="{color}"/>'
        f'</svg>'
    )


def _correlation_heatmap_html(df: pd.DataFrame) -> str:
    """
    Build a color-coded HTML correlation table for numeric columns.
    Green = strong positive, Red = strong negative, Grey = weak.
    """
    num_df = df.select_dtypes(include="number")
    if num_df.shape[1] < 2:
        return ""
    # Cap at 12 columns to keep the table readable
    cols = num_df.columns[:12].tolist()
    try:
        corr = num_df[cols].corr().round(2)
    except Exception:
        return ""

    def _cell_style(r):
        if pd.isna(r) or r == 1.0:
            return 'background:#1a2035;color:#4a5568'
        abs_r = abs(r)
        if abs_r < 0.3:
            return 'background:#1e2535;color:#718096'
        intensity = int(abs_r * 180)
        if r > 0:
            return f'background:rgba(72,187,120,{abs_r:.2f});color:#fff;font-weight:600'
        else:
            return f'background:rgba(245,101,101,{abs_r:.2f});color:#fff;font-weight:600'

    header_cells = "".join(f'<th style="font-size:.75em;padding:4px 6px">{c}</th>' for c in cols)
    rows_html = ""
    for row_col in cols:
        cells = "".join(
            f'<td style="text-align:center;font-size:.78em;padding:4px 6px;{_cell_style(corr.loc[row_col, c])}">'
            f'{"" if pd.isna(corr.loc[row_col, c]) or corr.loc[row_col, c] == 1.0 else corr.loc[row_col, c]}</td>'
            for c in cols
        )
        rows_html += f'<tr><td style="font-size:.78em;padding:4px 8px"><code>{row_col}</code></td>{cells}</tr>'

    return f"""
<div class="card p-3 mt-3">
  <h5 class="mb-2">&#x1F9EE; Correlation Heatmap</h5>
  <p style="font-size:.8em;color:#718096" class="mb-2">
    Pearson r &mdash; <span style="color:#48bb78">&#9632; positive</span>
    &nbsp;<span style="color:#f56565">&#9632; negative</span>
    &nbsp;<span style="color:#718096">&#9632; weak (&lt;0.3)</span>
  </p>
  <div class="table-responsive" style="max-height:320px;overflow:auto">
    <table class="table table-sm" style="font-size:.85em;border-collapse:collapse">
      <thead><tr><th></th>{header_cells}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>"""


def _category_dist_html(df: pd.DataFrame, max_cats: int = 15) -> str:
    """
    For each low-cardinality categorical column, render an inline SVG frequency bar.
    """
    cat_cols = df.select_dtypes(include=["object", "category"]).columns
    sections = []
    for col in cat_cols[:6]:   # cap at 6 columns
        vc = df[col].value_counts().head(max_cats)
        if vc.empty or len(vc) > max_cats:
            continue
        max_count = int(vc.max())
        bar_rows = ""
        for label, count in vc.items():
            pct   = round(count / len(df) * 100, 1)
            color = "#4f46e5"
            bar_rows += (
                f'<tr>'
                f'<td style="font-size:.78em;white-space:nowrap;max-width:150px;'
                f'overflow:hidden;text-overflow:ellipsis;padding:2px 6px">{str(label)[:30]}</td>'
                f'<td style="padding:2px 6px">{_svg_bar(count, max_count, color, 12)}</td>'
                f'<td style="font-size:.75em;color:#a0aec0;padding:2px 4px">{count:,} ({pct}%)</td>'
                f'</tr>'
            )
        sections.append(f"""
        <div class="col-md-6 mb-3">
          <div class="card p-3">
            <h6 style="font-size:.85em" class="mb-2"><code>{col}</code></h6>
            <table style="width:100%">{bar_rows}</table>
          </div>
        </div>""")

    if not sections:
        return ""
    return (
        '<div class="card p-3 mt-3">'
        '<h5 class="mb-3">&#x1F4CA; Categorical Distributions</h5>'
        '<div class="row g-2">' + "".join(sections) + "</div></div>"
    )


def _pandas_fallback_report(df: pd.DataFrame) -> dict:
    """
    Enhanced self-contained HTML report built from pandas only.
    Used when ydata-profiling is not installed or crashes.
    Includes: overview cards, column table with SVG missing bars,
    correlation heatmap, categorical distributions, and numeric describe.
    """
    rows           = len(df)
    cols           = len(df.columns)
    missing_total  = int(df.isnull().sum().sum())
    generated_at   = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    missing_pct_total = round(missing_total / max(rows * cols, 1) * 100, 1)

    # Per-column stats table with SVG missing bars
    max_missing_pct = max(
        (df[c].isnull().mean() * 100 for c in df.columns), default=1.0
    ) or 1.0

    col_rows_html = []
    for col in df.columns:
        s         = df[col]
        dtype     = str(s.dtype)
        non_null  = int(s.notna().sum())
        miss_pct  = round(s.isnull().mean() * 100, 1)
        n_unique  = int(s.nunique())

        if pd.api.types.is_numeric_dtype(s):
            clean = s.dropna()
            mn  = f"{clean.min():.4g}"  if len(clean) else "&#8212;"
            mx  = f"{clean.max():.4g}"  if len(clean) else "&#8212;"
            avg = f"{clean.mean():.4g}" if len(clean) else "&#8212;"
            extra = f"min {mn} &nbsp;/&nbsp; mean {avg} &nbsp;/&nbsp; max {mx}"
        else:
            top_val = s.value_counts().index[0] if s.notna().any() else "&#8212;"
            extra   = f"top: {str(top_val)[:40]}"

        badge_colour = (
            "#dc3545" if miss_pct > 20
            else "#fd7e14" if miss_pct > 5
            else "#198754"
        )
        miss_bar = _svg_bar(miss_pct, max_missing_pct, badge_colour) if miss_pct > 0 else ""

        col_rows_html.append(f"""
        <tr>
          <td><code>{col}</code></td>
          <td><span class="badge" style="background:{badge_colour}">{dtype}</span></td>
          <td>{non_null:,}</td>
          <td style="color:{badge_colour}">{miss_pct}% {miss_bar}</td>
          <td>{n_unique:,}</td>
          <td style="font-size:.85em;color:#a0aec0">{extra}</td>
        </tr>""")

    col_table        = "\n".join(col_rows_html)
    corr_section     = _correlation_heatmap_html(df)
    cat_dist_section = _category_dist_html(df)

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <title>DataForge EDA &mdash; {generated_at}</title>
  <link rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/css/bootstrap.min.css">
  {_THEME_CSS}
  {_THEME_JS}
</head>
<body style="background:var(--bg);color:var(--text);padding:2rem">

<div class="container-fluid">

  <h2 class="mb-1">&#x1F4CA; DataForge EDA Report</h2>
  <p class="text-muted mb-4" style="font-size:.85em">
    Generated {generated_at} &nbsp;&middot;&nbsp;
    Lightweight report &mdash; install <code>ydata-profiling</code> for full profiling
  </p>

  <!-- Overview cards -->
  <div class="row g-3 mb-4">
    <div class="col-md-3">
      <div class="card text-center p-3">
        <div style="font-size:2rem;font-weight:700">{rows:,}</div>
        <div class="text-muted">Rows</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="card text-center p-3">
        <div style="font-size:2rem;font-weight:700">{cols}</div>
        <div class="text-muted">Columns</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="card text-center p-3">
        <div style="font-size:2rem;font-weight:700">{missing_total:,}</div>
        <div class="text-muted">Missing Values</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="card text-center p-3">
        <div style="font-size:2rem;font-weight:700">{missing_pct_total}%</div>
        <div class="text-muted">Missing %</div>
      </div>
    </div>
  </div>

  <!-- Column details -->
  <div class="card p-3">
    <h5 class="mb-3">Column Overview</h5>
    <div class="table-responsive">
      <table class="table table-sm table-hover align-middle" style="font-size:.9em">
        <thead>
          <tr>
            <th>Column</th><th>Type</th><th>Non-null</th>
            <th>Missing %</th><th>Unique</th><th>Stats</th>
          </tr>
        </thead>
        <tbody>
          {col_table}
        </tbody>
      </table>
    </div>
  </div>

  {corr_section}

  {cat_dist_section}

  <!-- Numeric describe -->
  <div class="card p-3 mt-3">
    <h5 class="mb-3">Numeric Summary</h5>
    <div class="table-responsive">
      <pre style="font-size:.8em;color:var(--text)">{df.describe(include='all').to_string()}</pre>
    </div>
  </div>

</div>
</body>
</html>"""

    return {"html": html, "error": None, "rows_profiled": rows}


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_eda_report(
    df: pd.DataFrame,
    minimal: bool = True,
    sample_n: int = 5000,
) -> dict:
    """
    Generate an HTML EDA report.

    Returns
    -------
    {"html": str | None, "error": str | None, "rows_profiled": int}

    Never raises — always returns a dict so Flask routes stay clean.
    On any failure, falls back to the lightweight pandas report (FIX D).
    """
    # ── FIX A: suppress deprecation warnings from imghdr / visions ──────────
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", message=".*imghdr.*")
        warnings.filterwarnings("ignore", message=".*visions.*")

        # ── FIX E: try both package names ────────────────────────────────────
        ProfileReport = None
        for pkg in ("ydata_profiling", "pandas_profiling"):
            try:
                mod = __import__(pkg, fromlist=["ProfileReport"])
                ProfileReport = mod.ProfileReport
                break
            except ImportError:
                continue

    if ProfileReport is None:
        log.warning("ydata-profiling not installed — using pandas fallback EDA.")
        return _pandas_fallback_report(df)

    # Sample large datasets
    rows_profiled = len(df)
    df_sample = df
    if len(df) > sample_n:
        df_sample = df.sample(n=sample_n, random_state=42).reset_index(drop=True)
        rows_profiled = sample_n

    df_sample = _sanitize_dtypes(df_sample)

    try:
        profile = ProfileReport(
            df_sample,
            minimal=minimal,
            title="DataForge EDA",
            progress_bar=False,
            # Disable correlation on very wide datasets (slow + can OOM)
            correlations=None if df_sample.shape[1] > 50 else {"pearson": {"calculate": True}},
        )
        html = profile.to_html()

        # FIX B + C
        html = _inject_theme(html)
        html = _fix_navbar(html)

        return {"html": html, "error": None, "rows_profiled": rows_profiled}

    except Exception as exc:
        log.error("ydata-profiling crashed (%s) — falling back to pandas report.", exc)
        # FIX D: always return something usable
        result = _pandas_fallback_report(df)
        result["error"] = f"Full profiling unavailable ({exc}); showing lightweight report."
        return result