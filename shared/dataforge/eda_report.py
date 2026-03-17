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
:root,[data-bs-theme="light"]{
  --bg:          #ffffff;
  --card-bg:     #f8f9fa;
  --text:        #212529;
  --border:      #dee2e6;
  --navbar-bg:   #f8f9fa;
}
[data-theme="dark"],[data-bs-theme="dark"]{
  --bg:          #0D0D1A;
  --card-bg:     #161625;
  --text:        #e2e8f0;
  --border:      #2d3748;
  --navbar-bg:   #161625;
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
  function applyTheme(t){
    document.documentElement.setAttribute('data-theme', t);
    document.documentElement.setAttribute('data-bs-theme', t);
  }
  // Apply theme sent from parent frame
  window.addEventListener('message', function(e){
    if(e.data && e.data.type === 'set-theme') applyTheme(e.data.theme);
  });
  // Inherit parent theme on load
  try{
    var p = window.parent;
    if(p && p !== window){
      var t = p.document.documentElement.getAttribute('data-theme') || 'light';
      applyTheme(t);
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

def _pandas_fallback_report(df: pd.DataFrame) -> dict:
    """
    FIX D — lightweight self-contained HTML report built from pandas only.
    Used when ydata-profiling is not installed or crashes.
    """
    rows = len(df)
    cols = len(df.columns)
    missing_total = int(df.isnull().sum().sum())
    generated_at  = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Per-column stats table
    col_rows_html = []
    for col in df.columns:
        s         = df[col]
        dtype     = str(s.dtype)
        non_null  = int(s.notna().sum())
        miss_pct  = round(s.isnull().mean() * 100, 1)
        n_unique  = int(s.nunique())

        if pd.api.types.is_numeric_dtype(s):
            clean = s.dropna()
            mn  = f"{clean.min():.4g}"  if len(clean) else "—"
            mx  = f"{clean.max():.4g}"  if len(clean) else "—"
            avg = f"{clean.mean():.4g}" if len(clean) else "—"
            extra = f"min {mn} / mean {avg} / max {mx}"
        else:
            top_val = s.value_counts().index[0] if s.notna().any() else "—"
            extra   = f"top: {str(top_val)[:40]}"

        badge_colour = ("#dc3545" if miss_pct > 20
                        else "#fd7e14" if miss_pct > 5
                        else "#198754")

        col_rows_html.append(f"""
        <tr>
          <td><code>{col}</code></td>
          <td><span class="badge" style="background:{badge_colour}">{dtype}</span></td>
          <td>{non_null:,}</td>
          <td style="color:{badge_colour}">{miss_pct}%</td>
          <td>{n_unique:,}</td>
          <td style="font-size:.85em;color:#888">{extra}</td>
        </tr>""")

    col_table = "\n".join(col_rows_html)

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <title>DataForge EDA — {generated_at}</title>
  <link rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/css/bootstrap.min.css">
  {_THEME_CSS}
  {_THEME_JS}
</head>
<body style="background:var(--bg);color:var(--text);padding:2rem">

<div class="container-fluid">

  <h2 class="mb-1">📊 DataForge EDA Report</h2>
  <p class="text-muted mb-4" style="font-size:.85em">
    Generated {generated_at} &nbsp;·&nbsp;
    Lightweight report — install <code>ydata-profiling</code> for full profiling
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
        <div style="font-size:2rem;font-weight:700">
          {round(missing_total / max(rows * cols, 1) * 100, 1)}%
        </div>
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

  <!-- Numeric describe -->
  <div class="card p-3 mt-3">
    <h5 class="mb-3">Numeric Summary (pandas describe)</h5>
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