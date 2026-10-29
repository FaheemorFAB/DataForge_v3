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
from typing import Any, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from dataforge.automl_fallback import EstimatorArtifact, SklearnAutoMLResult

log = logging.getLogger(__name__)

_MAX_TRAIN_ROWS = 50_000


def _detect_task(y: pd.Series) -> str:
    if (
        y.dtype == object
        or str(y.dtype) == "category"
        or pd.api.types.is_string_dtype(y)
        or not pd.api.types.is_numeric_dtype(y)
    ):
        return "classification"
    n_unique = y.nunique()
    if n_unique <= 20 and n_unique / max(len(y), 1) < 0.20:
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


def _leak_free_preprocess(
    X_train: pd.DataFrame,
    X_test: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """
    Leak-free feature preprocessing.
    Imputers and encoders are fitted strictly on X_train and applied to X_test.
    Prevents data leakage into validation or test folds.
    """
    from sklearn.impute import SimpleImputer

    X_tr = X_train.copy()
    X_te = X_test.copy() if X_test is not None else None

    num_cols = X_tr.select_dtypes(include=["float64", "float32"]).columns.tolist()
    int_cols = X_tr.select_dtypes(include=["int64", "int32", "uint8"]).columns.tolist()

    if num_cols:
        imp_num = SimpleImputer(strategy="median")
        X_tr[num_cols] = imp_num.fit_transform(X_tr[num_cols])
        if X_te is not None:
            X_te[num_cols] = imp_num.transform(X_te[num_cols])

    if int_cols:
        imp_cat = SimpleImputer(strategy="most_frequent")
        X_tr[int_cols] = imp_cat.fit_transform(X_tr[int_cols])
        if X_te is not None:
            X_te[int_cols] = imp_cat.transform(X_te[int_cols])

    X_tr = X_tr.fillna(0)
    if X_te is not None:
        X_te = X_te.fillna(0)

    return X_tr, X_te


def _impute_features(df: pd.DataFrame) -> pd.DataFrame:
    X_tr, _ = _leak_free_preprocess(df)
    return X_tr


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


def analyze_features_for_target(df: pd.DataFrame, target_col: str) -> dict:
    """Enterprise pre-flight feature audit:
    Computes missingness, cardinality, data type, and correlation with target.
    Flags potential target leakage (corr >= 0.90) and IDs before training.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {"error": "Dataset is empty or invalid.", "features": []}
    if target_col not in df.columns:
        return {"error": f"Target column '{target_col}' not found in dataset.", "features": []}

    task = _detect_task(df[target_col])
    target_series = df[target_col]
    n_rows = len(df)

    if task == "classification":
        t_numeric = target_series.astype("category").cat.codes.astype(float)
        t_numeric[t_numeric == -1] = np.nan
    else:
        t_numeric = pd.to_numeric(target_series, errors="coerce")

    features = []
    high_risk_count = 0

    for col in df.columns:
        if col == target_col:
            continue
        col_s = df[col]
        dtype_str = str(col_s.dtype)
        n_unique = int(col_s.nunique(dropna=True))
        missing_count = int(col_s.isna().sum())
        missing_pct = round(float(missing_count / max(n_rows, 1) * 100), 2)

        # Check ID candidate
        is_id = False
        lower_name = col.lower()
        if n_unique > 0 and n_unique == (n_rows - missing_count) and n_rows > 30:
            is_id = True
        elif lower_name.endswith(("_id", "id", "guid", "uuid", "identifier", "pk")):
            is_id = True

        # Correlation computation
        corr_val = None
        leakage_risk = "low"
        try:
            if pd.api.types.is_numeric_dtype(col_s):
                c_num = col_s.astype(float)
            else:
                c_num = col_s.astype("category").cat.codes.astype(float)
                c_num[c_num == -1] = np.nan

            valid = c_num.notna() & t_numeric.notna()
            if valid.sum() >= 5:
                if c_num[valid].std() > 1e-9 and t_numeric[valid].std() > 1e-9:
                    raw_corr = float(c_num[valid].corr(t_numeric[valid]))
                    if math.isfinite(raw_corr):
                        corr_val = round(raw_corr, 4)
                        abs_c = abs(corr_val)
                        if abs_c >= 0.90:
                            leakage_risk = "high"
                            high_risk_count += 1
                        elif abs_c >= 0.70:
                            leakage_risk = "medium"
        except Exception:
            corr_val = None

        recommendation = "include"
        if leakage_risk == "high":
            recommendation = "drop_leakage"
        elif is_id:
            recommendation = "drop_id"
        elif missing_pct >= 60.0:
            recommendation = "drop_missing"

        features.append({
            "name": col,
            "dtype": dtype_str,
            "missing_count": missing_count,
            "missing_pct": missing_pct,
            "n_unique": n_unique,
            "is_id": is_id,
            "correlation": corr_val,
            "leakage_risk": leakage_risk,
            "recommendation": recommendation,
        })

    return {
        "error": None,
        "target_col": target_col,
        "task": task,
        "n_rows": n_rows,
        "features": features,
        "high_risk_count": high_risk_count,
    }


COMMON_ALGORITHMS = [
    {
        "id": "lgbm",
        "name": "LightGBM",
        "aliases": ["lgbm", "lightgbm"],
        "tag": "Ultra Fast",
        "desc": "Gradient boosted trees optimized for speed, low memory, and large datasets.",
    },
    {
        "id": "xgboost",
        "name": "XGBoost",
        "aliases": ["xgboost", "xgb"],
        "tag": "High Accuracy",
        "desc": "Extreme gradient boosting with exact greedy split search.",
    },
    {
        "id": "catboost",
        "name": "CatBoost",
        "aliases": ["catboost", "cat"],
        "tag": "Categorical",
        "desc": "Symmetric trees with ordered boosting; exceptional for categorical data.",
    },
    {
        "id": "rf",
        "name": "Random Forest",
        "aliases": ["rf", "random_forest", "randomforest"],
        "tag": "Bagging",
        "desc": "Averaged forest of decision trees; highly resistant to noise and variance.",
    },
    {
        "id": "extra_tree",
        "name": "Extra Trees",
        "aliases": ["extra_tree", "extratrees", "extra_trees"],
        "tag": "Randomized",
        "desc": "Extremely randomized trees with lower variance and high training throughput.",
    },
    {
        "id": "gradient_boosting",
        "name": "Hist Gradient Boosting",
        "aliases": ["gradient_boosting", "hist_gradient_boosting", "gradientboosting"],
        "tag": "Boosting",
        "desc": "Histogram-based gradient boosting trees with fast binning.",
    },
    {
        "id": "linear",
        "name": "Linear / Ridge",
        "aliases": ["linear", "logistic_regression", "ridge"],
        "tag": "Interpretable",
        "desc": "L1/L2 regularized linear model providing an interpretable baseline.",
    },
    {
        "id": "decision_tree",
        "name": "Decision Tree",
        "aliases": ["decision_tree", "decisiontree", "dt"],
        "tag": "Tree",
        "desc": "Single transparent decision tree; fast and easily visualizable.",
    },
    {
        "id": "knn",
        "name": "K-Nearest Neighbors",
        "aliases": ["knn", "kneighbors", "k_nearest_neighbors"],
        "tag": "Instance-based",
        "desc": "Non-parametric distance-weighted classification and regression.",
    },
    {
        "id": "svm",
        "name": "Support Vector Machine",
        "aliases": ["svm", "linear_svm", "svc", "svr"],
        "tag": "Margin-based",
        "desc": "Maximal-margin hyperplane classifier/regressor with regularized boundary.",
    },
]


def _resolve_algo_id(name: str) -> str:
    cleaned = str(name).lower().replace(" ", "_").replace("-", "")
    for algo in COMMON_ALGORITHMS:
        if cleaned in algo["aliases"] or cleaned == algo["id"]:
            return algo["id"]
    return "rf"


def _build_model_instance(algo_id: str, task: str, params: Optional[dict] = None):
    params = dict(params or {})
    resolved = _resolve_algo_id(algo_id)

    if resolved == "lgbm":
        from lightgbm import LGBMClassifier, LGBMRegressor
        n_est = int(params.get("n_estimators", 80))
        lr = float(params.get("learning_rate", 0.1))
        max_d = int(params["max_depth"]) if params.get("max_depth") not in (None, "", "null", -1) else -1
        subsample = float(params.get("subsample", 1.0))
        if task == "classification":
            return LGBMClassifier(n_estimators=n_est, learning_rate=lr, max_depth=max_d, subsample=subsample, random_state=42, verbose=-1)
        return LGBMRegressor(n_estimators=n_est, learning_rate=lr, max_depth=max_d, subsample=subsample, random_state=42, verbose=-1)

    if resolved == "xgboost":
        from xgboost import XGBClassifier, XGBRegressor
        n_est = int(params.get("n_estimators", 80))
        lr = float(params.get("learning_rate", 0.1))
        max_d = int(params["max_depth"]) if params.get("max_depth") not in (None, "", "null") else 6
        subsample = float(params.get("subsample", 1.0))
        if task == "classification":
            return XGBClassifier(n_estimators=n_est, learning_rate=lr, max_depth=max_d, subsample=subsample, random_state=42, verbosity=0)
        return XGBRegressor(n_estimators=n_est, learning_rate=lr, max_depth=max_d, subsample=subsample, random_state=42, verbosity=0)

    if resolved == "catboost":
        from catboost import CatBoostClassifier, CatBoostRegressor
        n_est = int(params.get("n_estimators") or params.get("iterations", 80))
        lr = float(params.get("learning_rate", 0.1))
        max_d = int(params["max_depth"]) if params.get("max_depth") not in (None, "", "null") else 6
        max_d = min(max_d, 10)
        if task == "classification":
            return CatBoostClassifier(iterations=n_est, learning_rate=lr, depth=max_d, random_state=42, verbose=0)
        return CatBoostRegressor(iterations=n_est, learning_rate=lr, depth=max_d, random_state=42, verbose=0)

    if resolved == "rf":
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        n_est = int(params.get("n_estimators", 80))
        max_d = int(params["max_depth"]) if params.get("max_depth") not in (None, "", "null") else None
        min_split = int(params.get("min_samples_split", 2))
        min_leaf = int(params.get("min_samples_leaf", 1))
        if task == "classification":
            return RandomForestClassifier(n_estimators=n_est, max_depth=max_d, min_samples_split=min_split, min_samples_leaf=min_leaf, random_state=42, n_jobs=-1)
        return RandomForestRegressor(n_estimators=n_est, max_depth=max_d, min_samples_split=min_split, min_samples_leaf=min_leaf, random_state=42, n_jobs=-1)

    if resolved == "extra_tree":
        from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
        n_est = int(params.get("n_estimators", 80))
        max_d = int(params["max_depth"]) if params.get("max_depth") not in (None, "", "null") else None
        min_split = int(params.get("min_samples_split", 2))
        min_leaf = int(params.get("min_samples_leaf", 1))
        if task == "classification":
            return ExtraTreesClassifier(n_estimators=n_est, max_depth=max_d, min_samples_split=min_split, min_samples_leaf=min_leaf, random_state=42, n_jobs=-1)
        return ExtraTreesRegressor(n_estimators=n_est, max_depth=max_d, min_samples_split=min_split, min_samples_leaf=min_leaf, random_state=42, n_jobs=-1)

    if resolved == "gradient_boosting":
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
        max_iter = int(params.get("n_estimators") or params.get("max_iter", 80))
        lr = float(params.get("learning_rate", 0.1))
        max_d = int(params["max_depth"]) if params.get("max_depth") not in (None, "", "null") else None
        min_leaf = int(params.get("min_samples_leaf", 20))
        if task == "classification":
            return HistGradientBoostingClassifier(max_iter=max_iter, learning_rate=lr, max_depth=max_d, min_samples_leaf=min_leaf, random_state=42)
        return HistGradientBoostingRegressor(max_iter=max_iter, learning_rate=lr, max_depth=max_d, min_samples_leaf=min_leaf, random_state=42)

    if resolved == "linear":
        from sklearn.linear_model import LogisticRegression, Ridge
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        if task == "classification":
            c_val = float(params.get("C", 1.0))
            return Pipeline([
                ("scale", StandardScaler()),
                ("model", LogisticRegression(C=c_val, max_iter=1000, random_state=42))
            ])
        alpha_val = float(params.get("alpha", 1.0))
        return Pipeline([
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=alpha_val, random_state=42))
        ])

    if resolved == "decision_tree":
        from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
        max_d = int(params["max_depth"]) if params.get("max_depth") not in (None, "", "null") else None
        min_split = int(params.get("min_samples_split", 2))
        min_leaf = int(params.get("min_samples_leaf", 1))
        crit = str(params.get("criterion", "gini" if task == "classification" else "squared_error"))
        if task == "classification":
            if crit not in ("gini", "entropy", "log_loss"):
                crit = "gini"
            return DecisionTreeClassifier(max_depth=max_d, min_samples_split=min_split, min_samples_leaf=min_leaf, criterion=crit, random_state=42)
        if crit not in ("squared_error", "friedman_mse", "absolute_error", "poisson"):
            crit = "squared_error"
        return DecisionTreeRegressor(max_depth=max_d, min_samples_split=min_split, min_samples_leaf=min_leaf, criterion=crit, random_state=42)

    if resolved == "knn":
        from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        n_neighbors = int(params.get("n_neighbors", 5))
        weights = str(params.get("weights", "uniform"))
        if weights not in ("uniform", "distance"):
            weights = "uniform"
        metric = str(params.get("metric", "minkowski"))
        if task == "classification":
            return Pipeline([
                ("scale", StandardScaler()),
                ("model", KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights, metric=metric))
            ])
        return Pipeline([
            ("scale", StandardScaler()),
            ("model", KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights, metric=metric))
        ])

    if resolved == "svm":
        from sklearn.svm import LinearSVC, LinearSVR
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        c_val = float(params.get("C", 1.0))
        max_iter = int(params.get("max_iter", 2000))
        if task == "classification":
            return Pipeline([
                ("scale", StandardScaler()),
                ("model", LinearSVC(C=c_val, max_iter=max_iter, dual="auto", random_state=42))
            ])
        return Pipeline([
            ("scale", StandardScaler()),
            ("model", LinearSVR(C=c_val, max_iter=max_iter, dual="auto", random_state=42))
        ])

    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    if task == "classification":
        return RandomForestClassifier(n_estimators=80, random_state=42)
    return RandomForestRegressor(n_estimators=80, random_state=42)


def _run_tournament(
    X_train, y_train, X_test, y_test,
    task: str,
    algorithm_whitelist: Optional[list[str]] = None,
    time_budget: int = 60,
    metric_name: str = "auto",
) -> SklearnAutoMLResult:
    candidate_keys = []
    if algorithm_whitelist:
        for a in algorithm_whitelist:
            if a == "all":
                candidate_keys = [algo["id"] for algo in COMMON_ALGORITHMS]
                break
            resolved = _resolve_algo_id(a)
            if resolved not in candidate_keys:
                candidate_keys.append(resolved)
    if not candidate_keys:
        candidate_keys = [algo["id"] for algo in COMMON_ALGORITHMS]

    evaluated = []
    losses = {}
    configs = {}
    best_model = None
    best_loss = float("inf")
    best_key = None
    best_config = {}

    for key in candidate_keys:
        algo_info = next((a for a in COMMON_ALGORITHMS if a["id"] == key), None)
        display_name = algo_info["name"] if algo_info else key
        try:
            model = _build_model_instance(key, task, {})
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            if task == "classification":
                from sklearn.metrics import accuracy_score
                acc = float(accuracy_score(y_test, y_pred))
                loss = 1.0 - acc
                metric_score = acc
            else:
                from sklearn.metrics import mean_squared_error, r2_score
                rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
                r2 = float(r2_score(y_test, y_pred))
                loss = rmse
                metric_score = r2

            losses[key] = loss
            cfg = getattr(model, "get_params", lambda: {})()
            compact_cfg = {k: v for k, v in cfg.items() if not k.startswith("_") and isinstance(v, (int, float, str, bool))}
            configs[key] = compact_cfg

            evaluated.append({
                "model": key,
                "display_name": display_name,
                "loss": loss,
                "metric": metric_score,
                "best_config": compact_cfg,
                "instance": model,
            })

            if loss < best_loss:
                best_loss = loss
                best_model = model
                best_key = key
                best_config = compact_cfg
        except Exception as exc:
            log.warning("[automl_tournament] Model %s failed: %s", key, exc)

    if not evaluated or best_model is None:
        raise RuntimeError("No models could be successfully trained in tournament mode.")

    evaluated.sort(key=lambda x: (x["loss"] is None, x["loss"]))

    leaderboard = []
    for rank_idx, item in enumerate(evaluated):
        is_best = (rank_idx == 0)
        leaderboard.append({
            "rank": rank_idx + 1,
            "model": item["model"],
            "display_name": item["display_name"],
            "metric": round(item["metric"], 4) if item["metric"] is not None else None,
            "loss": round(item["loss"], 4) if item["loss"] is not None else None,
            "best_config": str(item["best_config"]),
            "best": is_best,
            "status": "champion" if is_best else "evaluated",
        })

    return SklearnAutoMLResult(
        model=EstimatorArtifact(estimator=best_model),
        best_estimator=best_key,
        best_loss=best_loss,
        best_config=best_config,
        best_loss_per_estimator=losses,
        best_config_per_estimator=configs,
        custom_leaderboard=leaderboard,
        backend_name="tournament",
    )


def _run_manual_model(
    X_train, y_train, X_test, y_test,
    task: str,
    selected_model: str,
    hyperparameters: Optional[dict] = None,
) -> SklearnAutoMLResult:
    key = _resolve_algo_id(selected_model or "rf")
    algo_info = next((a for a in COMMON_ALGORITHMS if a["id"] == key), None)
    display_name = algo_info["name"] if algo_info else key
    params = dict(hyperparameters or {})

    model = _build_model_instance(key, task, params)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    if task == "classification":
        from sklearn.metrics import accuracy_score
        acc = float(accuracy_score(y_test, y_pred))
        loss = 1.0 - acc
        metric_score = acc
    else:
        from sklearn.metrics import mean_squared_error, r2_score
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        loss = rmse
        metric_score = r2

    leaderboard = [{
        "rank": 1,
        "model": key,
        "display_name": display_name,
        "metric": round(metric_score, 4),
        "loss": round(loss, 4),
        "best_config": str(params),
        "best": True,
        "status": "manual_trained",
    }]

    return SklearnAutoMLResult(
        model=EstimatorArtifact(estimator=model),
        best_estimator=key,
        best_loss=loss,
        best_config=params,
        best_loss_per_estimator={key: loss},
        best_config_per_estimator={key: params},
        custom_leaderboard=leaderboard,
        backend_name="manual",
    )


def run_automl(
    df: pd.DataFrame,
    target_col: str,
    task_choice: str = "auto-detect",
    time_budget: int = 120,
    test_size: float = 0.2,
    feature_whitelist: Optional[list[str]] = None,
    excluded_features: Optional[list[str]] = None,
    algorithm_whitelist: Optional[list[str]] = None,
    cv_strategy: str = "auto",
    cv_folds: int = 5,
    metric_override: str = "auto",
    mode: str = "tournament",
    selected_model: Optional[str] = None,
    hyperparameters: Optional[dict[str, Any]] = None,
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

    # Granular feature selection (whitelist & blacklist)
    all_features = [c for c in df.columns if c != target_col]
    if feature_whitelist is not None:
        selected_features = [c for c in all_features if c in feature_whitelist]
    else:
        selected_features = all_features

    if excluded_features:
        selected_features = [c for c in selected_features if c not in excluded_features]

    if not selected_features:
        return {"error": "No feature columns selected for AutoML training.", "model_pkl": None}

    # Pre-training Target Leakage check on selected features
    leakage_warnings = []
    try:
        t_series = df[target_col]
        if task == "classification":
            t_num = t_series.astype("category").cat.codes.astype(float)
            t_num[t_num == -1] = np.nan
        else:
            t_num = pd.to_numeric(t_series, errors="coerce")

        for c in selected_features:
            c_s = pd.to_numeric(df[c], errors="coerce") if pd.api.types.is_numeric_dtype(df[c]) else df[c].astype("category").cat.codes.astype(float)
            vld = c_s.notna() & t_num.notna()
            if vld.sum() >= 5 and c_s[vld].std() > 1e-9 and t_num[vld].std() > 1e-9:
                c_val = float(c_s[vld].corr(t_num[vld]))
                if math.isfinite(c_val) and abs(c_val) >= 0.90:
                    leakage_warnings.append({
                        "feature": c,
                        "correlation": round(c_val, 4),
                        "warning": f"Feature '{c}' has {round(c_val * 100, 1)}% correlation with target '{target_col}'. High risk of target leakage.",
                    })
    except Exception as exc:
        log.warning("[automl_trainer] Leakage pre-check failed: %s", exc)

    # Drop rows where target is null before any categorization/encoding
    valid_target_mask = df[target_col].notna()
    df_model = _encode_features(df.loc[valid_target_mask, selected_features])
    y = df.loc[valid_target_mask, target_col].copy()
    if task == "classification" and (not pd.api.types.is_numeric_dtype(y) or y.dtype == object or str(y.dtype) == "category"):
        cat = pd.Categorical(y)
        y = pd.Series(cat.codes, index=y.index, dtype=int)

    valid_mask = y.notna() & (y >= 0 if task == "classification" else True)
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

    # ── Target leakage check ──────────────────────────────────────────────────
    target_leakage_warnings: list[str] = []
    if pd.api.types.is_numeric_dtype(y):
        for col in df_model.select_dtypes(include="number").columns:
            try:
                corr = float(df_model[col].corr(y))
                if pd.notna(corr) and abs(corr) > 0.995:
                    target_leakage_warnings.append(
                        f"Feature '{col}' has extreme correlation ({corr:.4f}) with target, indicating potential target leakage."
                    )
            except Exception:
                pass

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

    # Strict fit-on-train only preprocessing (Zero Data Leakage)
    X_train, X_test = _leak_free_preprocess(X_train, X_test)
    X_train, dropped_cols = _remove_low_variance(X_train)
    if X_test is not None:
        kept_cols = [c for c in X_train.columns if c in X_test.columns]
        X_test = X_test[kept_cols]

    if X_train.shape[1] == 0:
        return {"error": "All features were removed during preprocessing.", "model_pkl": None}

    timing["preprocessing_s"] = round(time.time() - t0, 2)

    X_train, y_train, was_sampled = _smart_sample(X_train, y_train, task)
    effective_budget = _adaptive_time_budget(len(X_train), X_train.shape[1], time_budget)

    imbalance_report = {}
    flaml_metric = "auto"
    if task == "classification":
        n_classes = int(y_train.nunique())
        imbalance_report = _detect_imbalance(y_train)
        if imbalance_report["is_imbalanced"]:
            flaml_metric = imbalance_report["recommended_metric"]
            log.info(
                "[automl_trainer] Imbalanced dataset detected (minority=%.1f%%). Switching metric -> %s",
                imbalance_report["minority_ratio"] * 100,
                flaml_metric,
            )
        # Force a multiclass-safe metric when there are more than 2 classes
        if n_classes > 2 and flaml_metric in ("auto", "f1"):
            flaml_metric = "macro_f1" if n_classes <= 20 else "log_loss"
            log.info(
                "[automl_trainer] Multiclass target (%d classes). Using metric -> %s",
                n_classes, flaml_metric,
            )

    if cv_strategy == "holdout":
        use_cv = False
        n_splits = 1
    elif cv_strategy in ("cv", "stratified_kfold", "kfold"):
        use_cv = True
        n_splits = max(2, min(int(cv_folds), 10))
    else:  # "auto"
        use_cv = len(X_train) > 5_000
        n_splits = 5 if len(X_train) > 10_000 else 3

    t_train = time.time()

    if mode == "manual":
        backend_used = "manual"
        automl = _run_manual_model(
            X_train, y_train, X_test, y_test,
            task=task,
            selected_model=selected_model or "rf",
            hyperparameters=hyperparameters,
        )
    else:
        backend_used = "tournament"
        automl = _run_tournament(
            X_train, y_train, X_test, y_test,
            task=task,
            algorithm_whitelist=algorithm_whitelist,
            time_budget=effective_budget,
            metric_name=flaml_metric,
        )

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
            if len(importances) > len(feat_names):
                importances = np.mean(np.abs(model.coef_), axis=0)

        if importances is not None and len(importances) == len(feat_names):
            fi_df = (
                pd.DataFrame({"feature": feat_names, "importance": importances})
                .sort_values("importance", ascending=False)
                .head(15)
            )
            feature_importance = fi_df.to_dict("records")
            for row in feature_importance:
                row["importance"] = round(float(row["importance"]), 6)
        elif hasattr(automl, "predict") and len(feat_names) > 0 and len(X_test) > 0:
            from sklearn.inspection import permutation_importance
            r = permutation_importance(automl, X_test.head(100), y_test.head(100), n_repeats=3, random_state=42)
            fi_df = (
                pd.DataFrame({"feature": feat_names, "importance": np.maximum(0, r.importances_mean)})
                .sort_values("importance", ascending=False)
                .head(15)
            )
            feature_importance = fi_df.to_dict("records")
            for row in feature_importance:
                row["importance"] = round(float(row["importance"]), 6)
    except Exception as exc:
        log.debug("Feature importance calculation: %s", exc)

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
        "automl": automl,
    }, buf)
    model_pkl = buf.getvalue()
    timing["serialization_s"] = round(time.time() - t_serial, 2)
    timing["total_s"] = round(time.time() - t0, 2)

    return {
        "error": None,
        "task": task,
        "target_col": target_col,
        "target": target_col,
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
        "metrics": metrics,
        "leaderboard": leaderboard,
        "feature_importance": feature_importance,
        "shap_summary": shap_summary,
        "imbalance_report": imbalance_report,
        "leakage_warnings": leakage_warnings,
        "selected_features": selected_features,
        "feature_columns": list(df_model.columns),
        "algorithm_whitelist": algorithm_whitelist or ["all"],
        "cv_strategy": cv_strategy,
        "cv_folds": n_splits if use_cv else 1,
        "metric_override": metric_override,
        "mode": mode,
        "selected_model": selected_model,
        "hyperparameters": hyperparameters or {},
        "timing_breakdown": timing,
        "model_pkl": model_pkl,
    }


def get_json_result(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "model_pkl"}
