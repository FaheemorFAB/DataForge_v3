"""
DataForge AutoML trainer.

Primary backend: FLAML
Fallback backend: fast sklearn model search
"""

from __future__ import annotations

import concurrent.futures
import io
import logging
import math
import time
from typing import Tuple

import joblib
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_MAX_TRAIN_ROWS = 50_000


def _detect_task(y: pd.Series) -> str:
    if y.dtype == object or str(y.dtype) == "category":
        return "classification"
    n_unique = y.nunique()
    if n_unique <= 20 and n_unique / max(len(y), 1) < 0.05:
        return "classification"
    return "regression"


def _detect_imbalance(y: pd.Series) -> dict:
    counts = y.value_counts()
    if counts.empty:
        return {
            "is_imbalanced": False,
            "minority_ratio": 0.0,
            "recommended_metric": "auto",
            "class_counts": {},
        }

    minority_ratio = float(counts.min() / len(y))
    is_imbalanced = minority_ratio < 0.15
    recommended_metric = "auto"
    if is_imbalanced:
        recommended_metric = "roc_auc" if counts.shape[0] == 2 else "f1"

    return {
        "is_imbalanced": is_imbalanced,
        "minority_ratio": round(minority_ratio, 4),
        "recommended_metric": recommended_metric,
        "class_counts": {str(k): int(v) for k, v in counts.items()},
    }


def _downcast_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = df[col].astype(np.float32)
    for col in df.select_dtypes(include=["int64"]).columns:
        if df[col].between(-2_147_483_648, 2_147_483_647).all():
            df[col] = df[col].astype(np.int32)
    return df


def _remove_low_variance(df: pd.DataFrame, threshold: float = 0.0) -> Tuple[pd.DataFrame, list]:
    from sklearn.feature_selection import VarianceThreshold

    if df.shape[1] == 0:
        return df, []
    try:
        selector = VarianceThreshold(threshold=threshold)
        selector.fit(df)
        kept = df.columns[selector.get_support()].tolist()
        dropped = [c for c in df.columns if c not in kept]
        if dropped:
            log.info("[automl_trainer] Low-variance drop: %s", dropped)
        return df[kept], dropped
    except Exception as exc:
        log.warning("[automl_trainer] VarianceThreshold failed (%s); skipping.", exc)
        return df, []


def _smart_sample(
    X: pd.DataFrame,
    y: pd.Series,
    task: str,
    max_rows: int = _MAX_TRAIN_ROWS,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.Series, bool]:
    if len(X) <= max_rows:
        return X, y, False

    fraction = max_rows / len(X)
    try:
        stratify = y if task == "classification" and y.nunique() < 50 else None
        from sklearn.model_selection import train_test_split

        X_s, _, y_s, _ = train_test_split(
            X,
            y,
            train_size=fraction,
            random_state=seed,
            stratify=stratify,
        )
        log.info(
            "[automl_trainer] Large dataset sampled: %d -> %d rows (%.1f%%).",
            len(X), len(X_s), fraction * 100,
        )
        return X_s, y_s, True
    except Exception as exc:
        log.warning("[automl_trainer] Sampling failed (%s); using full dataset.", exc)
        return X, y, False


def _adaptive_time_budget(n_rows: int, n_cols: int, user_budget: int) -> int:
    if n_rows < 1_000:
        minimum = 20
    elif n_rows < 5_000:
        minimum = 20
    elif n_rows < 20_000:
        minimum = 30
    else:
        minimum = 60

    budget = max(int(user_budget), minimum)
    if budget != user_budget:
        log.info(
            "[automl_trainer] Time budget adapted: %ds -> %ds (dataset: %d rows x %d cols).",
            user_budget, budget, n_rows, n_cols,
        )
    return budget


def _encode_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in df.select_dtypes(include=["datetime64", "datetimetz"]).columns:
        df.drop(columns=[col], inplace=True)

    for col in df.select_dtypes(include=["object", "category", "string"]).columns:
        codes = df[col].astype("category").cat.codes.astype(float)
        codes[codes == -1] = np.nan
        df[col] = codes

    return df


def _impute_features(df: pd.DataFrame) -> pd.DataFrame:
    from sklearn.impute import SimpleImputer

    df = df.copy()
    num_cols = df.select_dtypes(include=["float64", "float32"]).columns.tolist()
    int_cols = df.select_dtypes(include=["int64", "int32", "uint8"]).columns.tolist()
    cat_cols = int_cols

    if num_cols:
        imp = SimpleImputer(strategy="median")
        df[num_cols] = imp.fit_transform(df[num_cols])

    if cat_cols:
        imp = SimpleImputer(strategy="most_frequent")
        df[cat_cols] = imp.fit_transform(df[cat_cols])

    if df.isnull().any().any():
        df = df.fillna(0)

    return df


def _build_leaderboard(automl) -> list:
    rows = []
    try:
        if getattr(automl, "custom_leaderboard", None):
            return automl.custom_leaderboard

        loss_map = automl.best_loss_per_estimator
        config_map = automl.best_config_per_estimator or {}
        best_name = automl.best_estimator

        for estimator, loss in loss_map.items():
            try:
                metric_val = round(float(loss), 6)
                if not math.isfinite(metric_val):
                    metric_val = None
            except (TypeError, ValueError):
                metric_val = None

            rows.append({
                "model": estimator,
                "metric": metric_val,
                "best_config": str(config_map.get(estimator, "")),
                "best": estimator == best_name,
            })

        rows.sort(key=lambda r: (r["metric"] is None, r["metric"] or 0))
    except Exception:
        try:
            rows = [{
                "model": automl.best_estimator,
                "metric": round(float(automl.best_loss), 6),
                "best_config": str(automl.best_config),
                "best": True,
            }]
        except Exception:
            pass
    return rows


def _metric_safe(fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
        val = float(result)
        return round(val, 4) if math.isfinite(val) else None
    except Exception as exc:
        log.debug("[automl_trainer] metric %s failed: %s", getattr(fn, "__name__", fn), exc)
        return None


def _compute_metrics(automl, X_test, y_test, task: str) -> dict:
    try:
        y_pred = automl.predict(X_test)
    except Exception as exc:
        log.warning("[automl_trainer] automl.predict() failed: %s", exc)
        return {}

    if y_pred is None:
        log.warning("[automl_trainer] automl.predict() returned None; skipping metrics.")
        return {}

    import numpy as _np

    y_pred = _np.asarray(y_pred)
    metrics: dict = {}

    if task == "classification":
        from sklearn.metrics import (
            accuracy_score,
            brier_score_loss,
            f1_score,
            log_loss,
            precision_score,
            recall_score,
        )

        safe = lambda fn, *a, **kw: _metric_safe(fn, *a, **kw)
        metrics["Accuracy"] = safe(accuracy_score, y_test, y_pred)
        metrics["F1 (weighted)"] = safe(f1_score, y_test, y_pred, average="weighted", zero_division=0)
        metrics["Precision"] = safe(precision_score, y_test, y_pred, average="weighted", zero_division=0)
        metrics["Recall"] = safe(recall_score, y_test, y_pred, average="weighted", zero_division=0)
        try:
            from sklearn.metrics import roc_auc_score

            proba = automl.predict_proba(X_test)
            if proba is not None:
                if len(_np.unique(y_test)) == 2 and proba.shape[1] >= 2:
                    metrics["ROC-AUC"] = safe(roc_auc_score, y_test, proba[:, 1])
                    metrics["Log Loss"] = safe(log_loss, y_test, proba)
                    metrics["Brier Score"] = safe(brier_score_loss, y_test, proba[:, 1])
                else:
                    metrics["Log Loss"] = safe(log_loss, y_test, proba)
        except Exception:
            pass
    else:
        from sklearn.metrics import (
            explained_variance_score,
            max_error,
            mean_absolute_error,
            mean_absolute_percentage_error,
            mean_squared_error,
            r2_score,
        )

        safe = lambda fn, *a, **kw: _metric_safe(fn, *a, **kw)
        metrics["MAE"] = safe(mean_absolute_error, y_test, y_pred)
        metrics["RMSE"] = safe(lambda yt, yp: float(_np.sqrt(mean_squared_error(yt, yp))), y_test, y_pred)
        metrics["R²"] = safe(r2_score, y_test, y_pred)
        metrics["MAPE"] = safe(mean_absolute_percentage_error, y_test, y_pred)
        metrics["Expl. Variance"] = safe(explained_variance_score, y_test, y_pred)
        metrics["Max Error"] = safe(max_error, y_test, y_pred)

    return {k: v for k, v in metrics.items() if v is not None}


def _unwrap_estimator(estimator):
    if hasattr(estimator, "named_steps") and "model" in estimator.named_steps:
        return estimator.named_steps["model"]
    return estimator


def _compute_shap(automl, X_test: pd.DataFrame, max_rows: int = 100, timeout_s: int = 30) -> list:
    def _shap_worker():
        import shap

        model = _unwrap_estimator(automl.model.estimator)
        X_sample = X_test.head(max_rows)
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)
        if isinstance(shap_values, list):
            arr = np.mean([np.abs(sv) for sv in shap_values], axis=0)
        else:
            arr = np.abs(shap_values)
        mean_shap = arr.mean(axis=0)
        feat_names = X_sample.columns.tolist()
        shap_df = (
            pd.DataFrame({"feature": feat_names, "shap_importance": mean_shap})
            .sort_values("shap_importance", ascending=False)
            .head(15)
        )
        return [
            {"feature": r["feature"], "shap_importance": round(float(r["shap_importance"]), 6)}
            for _, r in shap_df.iterrows()
        ]

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_shap_worker)
            return future.result(timeout=timeout_s)
    except concurrent.futures.TimeoutError:
        log.warning("[automl_trainer] SHAP timed out after %ds; skipping.", timeout_s)
        return []
    except Exception as exc:
        log.warning("[automl_trainer] SHAP computation skipped: %s", exc)
        return []


def run_automl(
    df: pd.DataFrame,
    target_col: str,
    task_choice: str = "auto-detect",
    time_budget: int = 120,
    test_size: float = 0.2,
) -> dict:
    from sklearn.model_selection import train_test_split

    timing: dict = {}

    if not isinstance(df, pd.DataFrame) or df.empty:
        return {"error": "Dataset is empty or invalid.", "model_pkl": None}
    if target_col not in df.columns:
        return {"error": f"Target column '{target_col}' not found in dataset.", "model_pkl": None}
    if df[target_col].dropna().empty:
        return {"error": f"Target column '{target_col}' has no non-null values.", "model_pkl": None}

    t0 = time.time()
    auto_task = _detect_task(df[target_col])
    task = auto_task if task_choice == "auto-detect" else task_choice
    log.info("[automl_trainer] Task detected: %s (rows=%d, cols=%d)", task, len(df), df.shape[1])

    df_model = _encode_features(df.drop(columns=[target_col]))
    y = df[target_col].copy()

    if task == "classification" and (y.dtype == object or str(y.dtype) == "category"):
        y = y.astype("category").cat.codes

    valid_mask = y.notna()
    df_model = df_model[valid_mask]
    y = y[valid_mask]
    df_model = df_model.dropna(axis=1, how="all")

    if len(y) < 10:
        return {
            "error": "Not enough usable rows remain after filtering null targets for AutoML training.",
            "model_pkl": None,
        }
    if task == "classification" and y.nunique() < 2:
        return {"error": "Classification target must contain at least 2 distinct classes.", "model_pkl": None}
    if df_model.shape[1] == 0:
        return {"error": "No usable feature columns remain after preprocessing.", "model_pkl": None}

    df_model = _downcast_dtypes(df_model)
    df_model = _impute_features(df_model)
    df_model, dropped_cols = _remove_low_variance(df_model)
    if df_model.shape[1] == 0:
        return {"error": "All features were removed during preprocessing.", "model_pkl": None}

    timing["preprocessing_s"] = round(time.time() - t0, 2)

    stratify = None
    if task == "classification" and y.nunique() < 50:
        counts = y.value_counts()
        if not counts.empty and counts.min() >= 2:
            stratify = y

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            df_model,
            y,
            test_size=test_size,
            random_state=42,
            shuffle=True,
            stratify=stratify,
        )
    except Exception as exc:
        return {"error": f"Train/test split failed: {exc}", "model_pkl": None}

    X_train, y_train, was_sampled = _smart_sample(X_train, y_train, task)
    effective_budget = _adaptive_time_budget(len(X_train), X_train.shape[1], time_budget)

    imbalance_report = {}
    flaml_metric = "auto"
    if task == "classification":
        imbalance_report = _detect_imbalance(y_train)
        if imbalance_report["is_imbalanced"]:
            flaml_metric = imbalance_report["recommended_metric"]
            log.info(
                "[automl_trainer] Imbalanced dataset detected (minority=%.1f%%). Switching metric -> %s",
                imbalance_report["minority_ratio"] * 100,
                flaml_metric,
            )

    backend_used = "flaml"
    use_cv = len(X_train) > 5_000
    n_splits = 5 if len(X_train) > 10_000 else 3
    t_train = time.time()

    try:
        from flaml import AutoML

        automl = AutoML()
        fit_kwargs = dict(
            time_budget=effective_budget,
            task=task,
            log_type="all",
            verbose=0,
            seed=42,
            eval_method="cv" if use_cv else "holdout",
            n_jobs=-1,
        )
        if use_cv:
            fit_kwargs["n_splits"] = n_splits
        if flaml_metric != "auto":
            fit_kwargs["metric"] = flaml_metric

        try:
            automl.fit(X_train, y_train, **fit_kwargs)
        except Exception as exc:
            log.warning("[automl_trainer] FLAML fit failed (%s); retrying with holdout.", exc)
            fit_kwargs.pop("eval_method", None)
            fit_kwargs.pop("n_splits", None)
            automl.fit(X_train, y_train, **fit_kwargs)
    except ImportError:
        from dataforge.automl_fallback import run_sklearn_automl

        backend_used = "sklearn"
        use_cv = False
        n_splits = 1
        automl = run_sklearn_automl(
            X_train,
            y_train,
            task=task,
            time_budget=effective_budget,
            metric_name=flaml_metric,
        )
    except Exception as exc:
        from dataforge.automl_fallback import run_sklearn_automl

        log.warning("[automl_trainer] FLAML runtime failure (%s); using sklearn fallback.", exc)
        backend_used = "sklearn"
        use_cv = False
        n_splits = 1
        try:
            automl = run_sklearn_automl(
                X_train,
                y_train,
                task=task,
                time_budget=effective_budget,
                metric_name=flaml_metric,
            )
        except Exception as fallback_exc:
            return {"error": f"AutoML training failed: {fallback_exc}", "model_pkl": None}

    elapsed = round(time.time() - t_train, 1)
    timing["flaml_training_s"] = elapsed

    try:
        probe = automl.predict(X_test.iloc[:1])
        if probe is None:
            return {
                "error": (
                    "AutoML completed but could not fit any usable model. "
                    "Ensure the target column has enough signal and at least 2 classes for classification."
                ),
                "model_pkl": None,
            }
    except Exception as exc:
        return {"error": f"Model validation failed after training: {exc}", "model_pkl": None}

    t_eval = time.time()
    metrics = _compute_metrics(automl, X_test, y_test, task)
    leaderboard = _build_leaderboard(automl)
    timing["evaluation_s"] = round(time.time() - t_eval, 2)

    feature_importance = []
    try:
        model = _unwrap_estimator(automl.model.estimator)
        feat_names = list(df_model.columns)
        importances = None
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            importances = np.abs(model.coef_).flatten()

        if importances is not None and len(importances) == len(feat_names):
            fi_df = (
                pd.DataFrame({"feature": feat_names, "importance": importances})
                .sort_values("importance", ascending=False)
                .head(15)
            )
            feature_importance = fi_df.to_dict("records")
            for row in feature_importance:
                row["importance"] = round(float(row["importance"]), 6)
    except Exception:
        pass

    t_shap = time.time()
    shap_summary = _compute_shap(automl, X_test)
    timing["shap_s"] = round(time.time() - t_shap, 2)

    t_serial = time.time()
    buf = io.BytesIO()
    joblib.dump({
        "backend": backend_used,
        "task": task,
        "target_col": target_col,
        "feature_columns": list(df_model.columns),
        "dropped_cols": dropped_cols,
        "model": automl.model,
    }, buf)
    model_pkl = buf.getvalue()
    timing["serialization_s"] = round(time.time() - t_serial, 2)
    timing["total_s"] = round(time.time() - t0, 2)

    return {
        "error": None,
        "task": task,
        "best_estimator": automl.best_estimator,
        "best_loss": (lambda v: None if not math.isfinite(v) else v)(round(float(automl.best_loss), 6)),
        "best_config": str(automl.best_config),
        "backend_used": backend_used,
        "elapsed_s": elapsed,
        "effective_budget_s": effective_budget,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "was_sampled": was_sampled,
        "dropped_cols": dropped_cols,
        "n_cv_splits": n_splits if use_cv else 1,
        "eval_method": "cv" if use_cv else "holdout",
        "metrics": metrics,
        "leaderboard": leaderboard,
        "feature_importance": feature_importance,
        "shap_summary": shap_summary,
        "imbalance_report": imbalance_report,
        "timing_breakdown": timing,
        "model_pkl": model_pkl,
    }


def get_json_result(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "model_pkl"}
