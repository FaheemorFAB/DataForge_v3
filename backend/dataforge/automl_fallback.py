"""
Fast sklearn fallback backend for DataForge AutoML.

This keeps AutoML functional when FLAML is unavailable or unsuitable for the
current environment. The fallback intentionally favors reliability and bounded
runtime over exhaustive search.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import numpy as np


@dataclass
class EstimatorArtifact:
    estimator: Any


@dataclass
class SklearnAutoMLResult:
    model: EstimatorArtifact
    best_estimator: str
    best_loss: float
    best_config: dict
    best_loss_per_estimator: dict[str, float]
    best_config_per_estimator: dict[str, dict]
    custom_leaderboard: list[dict]
    backend_name: str = "sklearn"

    def predict(self, X):
        return self.model.estimator.predict(X)

    def predict_proba(self, X):
        estimator = self.model.estimator
        if hasattr(estimator, "predict_proba"):
            return estimator.predict_proba(X)
        return None


def _candidate_configs(task: str, budget_s: int) -> list[tuple[str, Any, list[dict]]]:
    from sklearn.ensemble import (
        ExtraTreesClassifier,
        ExtraTreesRegressor,
        GradientBoostingClassifier,
        GradientBoostingRegressor,
        RandomForestClassifier,
        RandomForestRegressor,
    )
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    expanded = budget_s >= 60

    if task == "classification":
        return [
            (
                "logistic_regression",
                lambda cfg: Pipeline([
                    ("scale", StandardScaler()),
                    ("model", LogisticRegression(
                        max_iter=500,
                        C=cfg["C"],
                        solver="lbfgs",
                    )),
                ]),
                [{"C": 1.0}] + ([{"C": 3.0}] if expanded else []),
            ),
            (
                "random_forest",
                lambda cfg: RandomForestClassifier(
                    n_estimators=cfg["n_estimators"],
                    max_depth=cfg["max_depth"],
                    min_samples_leaf=cfg["min_samples_leaf"],
                    random_state=42,
                    n_jobs=1,
                    class_weight="balanced",
                ),
                [{"n_estimators": 120, "max_depth": None, "min_samples_leaf": 1}]
                + ([{"n_estimators": 180, "max_depth": 12, "min_samples_leaf": 2}] if expanded else []),
            ),
            (
                "extra_trees",
                lambda cfg: ExtraTreesClassifier(
                    n_estimators=cfg["n_estimators"],
                    max_depth=cfg["max_depth"],
                    min_samples_leaf=cfg["min_samples_leaf"],
                    random_state=42,
                    n_jobs=1,
                    class_weight="balanced",
                ),
                [{"n_estimators": 160, "max_depth": None, "min_samples_leaf": 1}]
                + ([{"n_estimators": 220, "max_depth": 14, "min_samples_leaf": 2}] if expanded else []),
            ),
            (
                "gradient_boosting",
                lambda cfg: GradientBoostingClassifier(
                    learning_rate=cfg["learning_rate"],
                    max_depth=cfg["max_depth"],
                    random_state=42,
                    n_estimators=cfg["n_estimators"],
                ),
                [{"learning_rate": 0.08, "max_depth": 3, "n_estimators": 120}]
                + ([{"learning_rate": 0.05, "max_depth": 4, "n_estimators": 180}] if expanded else []),
            ),
        ]

    return [
        (
            "ridge",
            lambda cfg: Pipeline([
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=cfg["alpha"])),
            ]),
            [{"alpha": 1.0}] + ([{"alpha": 0.3}] if expanded else []),
        ),
        (
            "random_forest",
            lambda cfg: RandomForestRegressor(
                n_estimators=cfg["n_estimators"],
                max_depth=cfg["max_depth"],
                min_samples_leaf=cfg["min_samples_leaf"],
                random_state=42,
                n_jobs=1,
            ),
            [{"n_estimators": 120, "max_depth": None, "min_samples_leaf": 1}]
            + ([{"n_estimators": 180, "max_depth": 12, "min_samples_leaf": 2}] if expanded else []),
        ),
        (
            "extra_trees",
            lambda cfg: ExtraTreesRegressor(
                n_estimators=cfg["n_estimators"],
                max_depth=cfg["max_depth"],
                min_samples_leaf=cfg["min_samples_leaf"],
                random_state=42,
                n_jobs=1,
            ),
            [{"n_estimators": 160, "max_depth": None, "min_samples_leaf": 1}]
            + ([{"n_estimators": 220, "max_depth": 14, "min_samples_leaf": 2}] if expanded else []),
        ),
        (
            "gradient_boosting",
            lambda cfg: GradientBoostingRegressor(
                learning_rate=cfg["learning_rate"],
                max_depth=cfg["max_depth"],
                random_state=42,
                n_estimators=cfg["n_estimators"],
            ),
            [{"learning_rate": 0.08, "max_depth": 3, "n_estimators": 120}]
            + ([{"learning_rate": 0.05, "max_depth": 4, "n_estimators": 180}] if expanded else []),
        ),
    ]


def _classification_loss(model, X_val, y_val, metric_name: str) -> float:
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

    y_pred = model.predict(X_val)
    if metric_name == "roc_auc" and hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_val)
        if proba is not None and proba.shape[1] >= 2:
            return float(1.0 - roc_auc_score(y_val, proba[:, 1]))
    if metric_name == "f1":
        return float(1.0 - f1_score(y_val, y_pred, average="weighted", zero_division=0))
    return float(1.0 - accuracy_score(y_val, y_pred))


def _regression_loss(model, X_val, y_val) -> float:
    from sklearn.metrics import mean_squared_error

    pred = model.predict(X_val)
    return float(np.sqrt(mean_squared_error(y_val, pred)))


def run_sklearn_automl(
    X_train,
    y_train,
    task: str,
    time_budget: int,
    metric_name: str = "auto",
    seed: int = 42,
):
    from sklearn.model_selection import train_test_split

    if len(X_train) < 10:
        raise RuntimeError("Not enough rows for AutoML training after preprocessing.")

    stratify = None
    if task == "classification":
        counts = y_train.value_counts()
        if counts.min() >= 2 and y_train.nunique() < 50:
            stratify = y_train

    X_fit, X_val, y_fit, y_val = train_test_split(
        X_train,
        y_train,
        test_size=0.2,
        random_state=seed,
        stratify=stratify,
    )

    deadline = time.time() + max(int(time_budget), 8)
    losses: dict[str, float] = {}
    configs: dict[str, dict] = {}
    leaderboard: list[dict] = []
    best_model = None
    best_name = None
    best_loss = float("inf")
    best_config: dict = {}

    for estimator_name, builder, estimator_configs in _candidate_configs(task, time_budget):
        estimator_best_loss = float("inf")
        estimator_best_cfg: dict | None = None

        for cfg in estimator_configs:
            if time.time() >= deadline and best_model is not None:
                break

            model = builder(cfg)
            model.fit(X_fit, y_fit)

            if task == "classification":
                loss = _classification_loss(model, X_val, y_val, metric_name)
            else:
                loss = _regression_loss(model, X_val, y_val)

            if not np.isfinite(loss):
                continue

            if loss < estimator_best_loss:
                estimator_best_loss = float(loss)
                estimator_best_cfg = dict(cfg)

            if loss < best_loss:
                best_loss = float(loss)
                best_model = model
                best_name = estimator_name
                best_config = dict(cfg)

        if estimator_best_cfg is not None:
            losses[estimator_name] = estimator_best_loss
            configs[estimator_name] = estimator_best_cfg
            leaderboard.append({
                "model": estimator_name,
                "metric": round(estimator_best_loss, 6),
                "best_config": str(estimator_best_cfg),
                "best": False,
            })

        if time.time() >= deadline and best_model is not None:
            break

    if best_model is None or best_name is None:
        raise RuntimeError("Fallback AutoML could not fit a valid sklearn model.")

    for row in leaderboard:
        row["best"] = row["model"] == best_name

    leaderboard.sort(key=lambda row: (row["metric"] is None, row["metric"] or 0))

    return SklearnAutoMLResult(
        model=EstimatorArtifact(estimator=best_model),
        best_estimator=best_name,
        best_loss=best_loss,
        best_config=best_config,
        best_loss_per_estimator=losses,
        best_config_per_estimator=configs,
        custom_leaderboard=leaderboard,
    )
