"""
Alert Engine
════════════
Compares current dataset metrics against stored baselines and fires alerts
when configurable thresholds are breached.

Usage::

    from dataforge.alert_engine import AlertEngine

    engine = AlertEngine()

    # After first analysis — save baseline
    engine.save_baseline(upload_id=42, df=df, schema=schema)

    # On data refresh — check for alerts
    alerts = engine.check(upload_id=42, df=new_df, schema=schema)
    # alerts → list of alert dicts
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ── Alert severity levels ─────────────────────────────────────────────────────
SEVERITY_INFO     = "info"
SEVERITY_WARNING  = "warning"
SEVERITY_CRITICAL = "critical"

# ── Default threshold rules ───────────────────────────────────────────────────
DEFAULT_RULES = [
    {
        "name":      "metric_drop",
        "label":     "Metric Drop",
        "threshold": -0.20,    # −20 %
        "severity":  SEVERITY_WARNING,
        "message_tpl": "{metric} dropped {pct}% compared to baseline.",
    },
    {
        "name":      "metric_spike",
        "label":     "Metric Spike",
        "threshold":  0.50,    # +50 %
        "severity":  SEVERITY_INFO,
        "message_tpl": "{metric} spiked {pct}% above baseline.",
    },
    {
        "name":      "critical_drop",
        "label":     "Critical Drop",
        "threshold": -0.40,    # −40 %
        "severity":  SEVERITY_CRITICAL,
        "message_tpl": "CRITICAL: {metric} dropped {pct}% — immediate attention required.",
    },
    {
        "name":      "missing_values",
        "label":     "Data Quality",
        "threshold":  0.05,    # > 5 % missing
        "severity":  SEVERITY_WARNING,
        "message_tpl": "Data quality issue: {pct}% missing values detected in {metric}.",
    },
    {
        "name":      "row_count_drop",
        "label":     "Row Count Drop",
        "threshold": -0.30,    # −30 % rows
        "severity":  SEVERITY_WARNING,
        "message_tpl": "Dataset shrank {pct}% in row count vs baseline.",
    },
]


class AlertEngine:

    def __init__(self, store_dir: str | Path | None = None):
        self._store = Path(store_dir) if store_dir else Path("/tmp/dataforge_alerts")
        self._store.mkdir(parents=True, exist_ok=True)

    # ── Baseline management ───────────────────────────────────────────────────
    def _baseline_path(self, upload_id: int) -> Path:
        return self._store / f"baseline_{upload_id}.json"

    def save_baseline(self, upload_id: int, df: pd.DataFrame, schema: dict) -> dict:
        """Compute and persist baseline metrics for an upload."""
        baseline = self._compute_metrics(df, schema)
        baseline["saved_at"]  = datetime.utcnow().isoformat()
        baseline["upload_id"] = upload_id

        with open(self._baseline_path(upload_id), "w") as f:
            json.dump(baseline, f, indent=2)

        return baseline

    def load_baseline(self, upload_id: int) -> dict | None:
        p = self._baseline_path(upload_id)
        if not p.exists():
            return None
        with open(p) as f:
            return json.load(f)

    # ── Metric computation ────────────────────────────────────────────────────
    def _compute_metrics(self, df: pd.DataFrame, schema: dict) -> dict:
        """
        Compute per-column summary metrics for the given DataFrame.

        FIX: Added `if col not in df_cols: continue` guard so stale schema
        columns (from a previously uploaded dataset) never cause a KeyError.
        FIX: Restored correct indentation — s = df[col].dropna() must be
        inside the for loop, not at module scope.
        """
        metrics: dict = {}
        metrics["row_count"] = len(df)

        df_cols = set(df.columns)  # build once for O(1) membership checks

        for col in schema.get("metrics", []):
            if col not in df_cols:        # ← GUARD: skip columns from old datasets
                continue

            s = df[col].dropna()          # ← FIXED: inside the loop (was de-dented)

            if s.empty:
                continue

            metrics[f"{col}__mean"]    = float(s.mean())
            metrics[f"{col}__std"]     = float(s.std()) if len(s) > 1 else 0.0
            metrics[f"{col}__missing"] = float(df[col].isna().mean())

        return metrics

    # ── Alert check ───────────────────────────────────────────────────────────
    def check(
        self,
        upload_id: int,
        df: pd.DataFrame,
        schema: dict,
        custom_rules: list[dict] | None = None,
    ) -> list[dict]:
        """
        Compare `df` against the saved baseline for `upload_id`.
        Returns a list of fired alert dicts.

        FIX: Added schema-drift detection — if the baseline was built against
        a different dataset (different columns), it is silently discarded and
        a fresh baseline is written instead of crashing.
        """
        baseline = self.load_baseline(upload_id)

        # ── Schema-drift guard ────────────────────────────────────────────────
        # If the baseline references columns that no longer exist in the
        # current df (e.g. a new file was uploaded), treat it as a fresh
        # dataset so _compute_metrics never hits a KeyError.
        if baseline is not None:
            baseline_metric_cols = {
                k.split("__")[0]
                for k in baseline
                if k not in ("row_count", "saved_at", "upload_id")
            }
            current_cols = set(df.columns)
            if baseline_metric_cols and not baseline_metric_cols.issubset(current_cols):
                log.info(
                    "upload %s: baseline columns %s not in current df — resetting baseline.",
                    upload_id, baseline_metric_cols - current_cols,
                )
                baseline = None  # will rebuild below

        if not baseline:
            log.info("No baseline for upload %s — saving now.", upload_id)
            self.save_baseline(upload_id, df, schema)
            return []

        current = self._compute_metrics(df, schema)
        rules   = custom_rules or DEFAULT_RULES
        alerts: list[dict] = []

        for rule in rules:
            try:
                fired = self._evaluate_rule(rule, baseline, current, schema)
                if fired:
                    alerts.append(fired)
            except Exception as exc:
                log.warning("Alert rule %s failed: %s", rule["name"], exc)

        # Sort critical first
        sev_order = {SEVERITY_CRITICAL: 0, SEVERITY_WARNING: 1, SEVERITY_INFO: 2}
        alerts.sort(key=lambda a: sev_order.get(a["severity"], 9))
        return alerts

    def _evaluate_rule(
        self,
        rule: dict,
        baseline: dict,
        current: dict,
        schema: dict,
    ) -> dict | None:
        name = rule["name"]

        if name == "row_count_drop":
            base_rows = baseline.get("row_count", 0)
            curr_rows = current.get("row_count", 0)
            if base_rows == 0:
                return None
            change = (curr_rows - base_rows) / base_rows
            if change < rule["threshold"]:
                return self._make_alert(rule, abs(change) * 100, "row count")
            return None

        if name == "missing_values":
            for col in schema.get("metrics", []):
                miss = current.get(f"{col}__missing", 0.0)
                if miss > rule["threshold"]:
                    return self._make_alert(rule, round(miss * 100, 1), col)
            return None

        if name in ("metric_drop", "metric_spike", "critical_drop"):
            worst_col   = None
            worst_delta = 0.0
            for col in schema.get("metrics", []):
                b_mean = baseline.get(f"{col}__mean")
                c_mean = current.get(f"{col}__mean")
                if b_mean is None or c_mean is None or b_mean == 0:
                    continue
                delta = (c_mean - b_mean) / abs(b_mean)
                if name == "metric_spike" and delta > rule["threshold"]:
                    if delta > worst_delta:
                        worst_delta, worst_col = delta, col
                elif name in ("metric_drop", "critical_drop") and delta < rule["threshold"]:
                    if delta < worst_delta:
                        worst_delta, worst_col = delta, col

            if worst_col:
                return self._make_alert(rule, round(abs(worst_delta) * 100, 1), worst_col)

        return None

    @staticmethod
    def _make_alert(rule: dict, pct: float, metric: str) -> dict:
        msg = rule["message_tpl"].format(pct=round(pct, 1), metric=metric)
        return {
            "rule":         rule["name"],
            "label":        rule["label"],
            "message":      msg,
            "severity":     rule["severity"],
            "metric":       metric,
            "pct_change":   pct,
            "triggered_at": datetime.utcnow().isoformat(),
        }

    # ── Notification helpers ──────────────────────────────────────────────────
    @staticmethod
    def format_slack_payload(alerts: list[dict], dataset_name: str) -> dict:
        """Return a Slack webhook payload dict."""
        if not alerts:
            return {}

        severity_emoji = {
            SEVERITY_CRITICAL: ":red_circle:",
            SEVERITY_WARNING:  ":warning:",
            SEVERITY_INFO:     ":information_source:",
        }
        lines = [f"*DataForge Alert — {dataset_name}*\n"]
        for a in alerts:
            emoji = severity_emoji.get(a["severity"], ":white_circle:")
            lines.append(f"{emoji} {a['message']}")

        return {"text": "\n".join(lines)}

    @staticmethod
    def format_email_body(alerts: list[dict], dataset_name: str) -> str:
        """Return a plain-text email body."""
        lines = [
            f"DataForge Alert Report — {dataset_name}",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "-" * 60,
            "",
        ]
        for a in alerts:
            lines.append(f"[{a['severity'].upper()}] {a['message']}")
        lines += ["", "—", "DataForge Automated Monitoring"]
        return "\n".join(lines)