"""
DataForge Forecast Engine
═════════════════════════
Advanced time-series forecasting with:
  - Triple Exponential Smoothing (Holt-Winters)
  - ARIMA / SARIMA (via statsmodels)
  - Ridge-Lag ML model with temporal features
  - Ensemble blending (MAPE-weighted)
  - 80% + 95% prediction intervals
  - Additive time-series decomposition (trend / seasonal / residual)
  - Automatic frequency inference & resampling
  - Future value estimation (total, growth %, target date)

All heavy dependencies (statsmodels, sklearn) are imported lazily so the
module loads fast and degrades gracefully when packages are missing.
"""

from __future__ import annotations

import logging
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
_MIN_POINTS = 8          # minimum observations needed for any model
_HOLDOUT_FRAC = 0.2      # fraction of series used for model backtesting
_CONFIDENCE = {80: 1.282, 95: 1.645}   # z-scores for PI widths

# Frequency → default forecast horizon (periods)
_HORIZON_MAP = {
    "D": 30,
    "W": 12,
    "M": 6,
    "Q": 4,
    "Y": 2,
    "H": 48,
    "T": 60,
    "min": 60,
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _safe(v):
    """Convert numpy scalar or NaN to plain Python float, 0.0 on failure."""
    try:
        f = float(v)
        return 0.0 if (f != f or np.isinf(f)) else f
    except Exception:
        return 0.0


def _mape(actual: np.ndarray, pred: np.ndarray) -> float:
    """Mean absolute percentage error (0–100 scale); handles zeros."""
    mask = actual != 0
    if not mask.any():
        return 100.0
    return float(np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])) * 100)


def _rmse(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - pred) ** 2)))


def _infer_freq(index: pd.DatetimeIndex) -> str:
    """Best-effort frequency string from a DatetimeIndex."""
    try:
        freq = pd.infer_freq(index)
        if freq:
            return freq[0]          # 'D', 'W', 'M', 'Q', 'Y' …
    except Exception:
        pass
    # Fallback: compute median gap
    if len(index) < 2:
        return "D"
    gaps = pd.Series(index).diff().dropna().dt.total_seconds()
    median_sec = gaps.median()
    if median_sec < 3600:
        return "T"
    if median_sec < 86_400:
        return "H"
    if median_sec < 86_400 * 8:
        return "D"
    if median_sec < 86_400 * 35:
        return "W"
    if median_sec < 86_400 * 100:
        return "M"
    return "Q"


def _resample_series(series: pd.Series, freq_char: str) -> pd.Series:
    """Aggregate series to the target frequency, filling gaps via interpolation."""
    freq_map = {"T": "T", "H": "H", "D": "D", "W": "W", "M": "MS", "Q": "QS", "Y": "YS"}
    resample_freq = freq_map.get(freq_char, "D")
    try:
        resampled = series.resample(resample_freq).sum()
        resampled = resampled.interpolate(method="linear")
        return resampled
    except Exception:
        return series


# ── Individual models ─────────────────────────────────────────────────────────
def _holt_winters(train: np.ndarray, horizon: int, freq_char: str) -> Tuple[np.ndarray, float]:
    """Triple Exponential Smoothing (Holt-Winters additive)."""
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        # Determine seasonal period
        seasonal_periods_map = {"D": 7, "W": 4, "M": 12, "Q": 4, "H": 24, "T": 60}
        seasonal_periods = seasonal_periods_map.get(freq_char, 7)

        has_seasonality = len(train) >= 2 * seasonal_periods

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if has_seasonality:
                model = ExponentialSmoothing(
                    train,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=seasonal_periods,
                    initialization_method="estimated",
                )
            else:
                model = ExponentialSmoothing(
                    train,
                    trend="add",
                    seasonal=None,
                    initialization_method="estimated",
                )
            fitted = model.fit(optimized=True, remove_bias=True)
            forecast = fitted.forecast(horizon)

        # Backtest on last 20% of train
        n_test = max(2, int(len(train) * _HOLDOUT_FRAC))
        train_bt = train[:-n_test]
        actual_bt = train[-n_test:]
        if has_seasonality and len(train_bt) >= 2 * seasonal_periods:
            m_bt = ExponentialSmoothing(
                train_bt,
                trend="add",
                seasonal="add",
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            ).fit(optimized=True, remove_bias=True)
        else:
            m_bt = ExponentialSmoothing(
                train_bt,
                trend="add",
                seasonal=None,
                initialization_method="estimated",
            ).fit(optimized=True, remove_bias=True)
        pred_bt = m_bt.forecast(n_test)
        mape = _mape(actual_bt, pred_bt)
        return np.array(forecast), mape

    except ImportError:
        log.debug("statsmodels not available; skipping Holt-Winters")
        return _simple_exponential_smoothing(train, horizon)
    except Exception as exc:
        log.debug("Holt-Winters failed: %s", exc)
        return _simple_exponential_smoothing(train, horizon)


def _simple_exponential_smoothing(train: np.ndarray, horizon: int) -> Tuple[np.ndarray, float]:
    """Pure-numpy fallback: simple exponential smoothing with linear extrapolation."""
    alpha = 0.3
    level = float(train[0])
    for v in train[1:]:
        level = alpha * v + (1 - alpha) * level

    # Trend from last 20% of data
    n = max(2, len(train) // 5)
    slope = np.polyfit(np.arange(n), train[-n:], 1)[0]
    forecast = np.array([level + slope * (i + 1) for i in range(horizon)])

    # Backtest
    n_test = max(2, int(len(train) * _HOLDOUT_FRAC))
    pred_bt = np.full(n_test, level)
    mape = _mape(train[-n_test:], pred_bt)
    return forecast, mape


def _ridge_lag_model(
    train: np.ndarray,
    horizon: int,
    freq_char: str,
) -> Tuple[np.ndarray, float]:
    """Ridge regression with lag, rolling, and calendar features."""
    try:
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler

        n = len(train)
        lag_sizes = [1, 2, 3, 7, 14, 30]
        lag_sizes = [l for l in lag_sizes if l < n - 5]

        def _make_features(series: np.ndarray, start_idx: int = 0) -> np.ndarray:
            feats = []
            for lag in lag_sizes:
                if start_idx - lag >= 0:
                    feats.append(series[start_idx - lag])
                else:
                    feats.append(0.0)
            # Rolling stats (window=3)
            window = series[max(0, start_idx - 3): start_idx]
            feats += [
                float(np.mean(window)) if len(window) else 0.0,
                float(np.std(window)) if len(window) > 1 else 0.0,
            ]
            # Time index (normalized)
            feats.append(start_idx / max(n, 1))
            return np.array(feats)

        if not lag_sizes:
            raise ValueError("Not enough data for lag model")

        X, y = [], []
        for i in range(max(lag_sizes), n):
            X.append(_make_features(train, i))
            y.append(train[i])

        X, y = np.array(X), np.array(y)
        if len(X) < 5:
            raise ValueError("Too few training samples")

        scaler = StandardScaler()
        X_sc = scaler.fit_transform(X)
        model = Ridge(alpha=1.0)
        model.fit(X_sc, y)

        # Backtest
        n_test = max(2, int(len(X) * _HOLDOUT_FRAC))
        X_train, X_test = X[:-n_test], X[-n_test:]
        y_train, y_test = y[:-n_test], y[-n_test:]
        model_bt = Ridge(alpha=1.0).fit(scaler.transform(X_train), y_train)
        pred_bt = model_bt.predict(scaler.transform(X_test))
        mape = _mape(y_test, pred_bt)

        # Forward predict
        history = list(train)
        preds = []
        for _ in range(horizon):
            feats = _make_features(np.array(history), len(history))
            pred = model.predict(scaler.transform([feats]))[0]
            preds.append(pred)
            history.append(pred)

        return np.array(preds), mape

    except ImportError:
        log.debug("scikit-learn not available; skipping Ridge-Lag model")
        return _simple_exponential_smoothing(train, horizon)
    except Exception as exc:
        log.debug("Ridge-Lag model failed: %s", exc)
        return _simple_exponential_smoothing(train, horizon)


def _arima_model(train: np.ndarray, horizon: int) -> Tuple[np.ndarray, float]:
    """SARIMAX auto-order model (statsmodels)."""
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = SARIMAX(train, order=(1, 1, 1), trend="c")
            fitted = model.fit(disp=False, maxiter=50)
            forecast = fitted.forecast(horizon)

        n_test = max(2, int(len(train) * _HOLDOUT_FRAC))
        m_bt = SARIMAX(train[:-n_test], order=(1, 1, 1), trend="c").fit(disp=False, maxiter=50)
        pred_bt = m_bt.forecast(n_test)
        mape = _mape(train[-n_test:], pred_bt)
        return np.array(forecast), mape

    except Exception as exc:
        log.debug("ARIMA model failed: %s", exc)
        return _simple_exponential_smoothing(train, horizon)


# ── Ensemble & confidence intervals ──────────────────────────────────────────
def _ensemble(
    models: List[Tuple[np.ndarray, float]],
    train_residuals: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    MAPE-weighted ensemble of model predictions.
    Returns (point_forecast, upper_95, lower_95, upper_80, lower_80).
    """
    MAPE-weighted ensemble of model predictions.
    Returns (point_forecast, upper_95, lower_95).
    """
    # Weights = inverse MAPE (lower MAPE = higher weight)
    mapes = np.array([m[1] for m in models])
    mapes = np.clip(mapes, 1e-3, 1e6)
    weights = (1.0 / mapes)
    weights /= weights.sum()

    forecasts = np.stack([m[0] for m in models], axis=0)
    point = np.average(forecasts, axis=0, weights=weights)

    # Residual std for prediction intervals
    std = float(np.std(train_residuals)) if len(train_residuals) > 1 else float(np.mean(np.abs(point)) * 0.15)
    std = max(std, abs(np.mean(point)) * 0.02)

    # Expanding uncertainty over horizon
    horizon = len(point)
    factor = np.sqrt(np.arange(1, horizon + 1))
    upper_95 = point + _CONFIDENCE[95] * std * factor
    lower_95 = point - _CONFIDENCE[95] * std * factor
    upper_80 = point + _CONFIDENCE[80] * std * factor
    lower_80 = point - _CONFIDENCE[80] * std * factor

    return (
        point,
        upper_95,
        lower_95,
        upper_80,
        lower_80,
    )


# ── Decomposition ─────────────────────────────────────────────────────────────
def _decompose(series: pd.Series, freq_char: str) -> Dict:
    """Additive seasonal decomposition (statsmodels). Falls back to simple trend."""
    seasonal_map = {"D": 7, "W": 4, "M": 12, "Q": 4, "H": 24}
    period = seasonal_map.get(freq_char, 7)

    try:
        from statsmodels.tsa.seasonal import seasonal_decompose

        if len(series) < 2 * period:
            raise ValueError("Series too short for decomposition")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = seasonal_decompose(series, model="additive", period=period, extrapolate_trend="freq")

        return {
            "labels":    [str(d)[:10] for d in result.trend.index],
            "trend":     [_safe(v) for v in result.trend.values],
            "seasonal":  [_safe(v) for v in result.seasonal.values],
            "residual":  [_safe(v) for v in result.resid.values],
        }

    except Exception as exc:
        log.debug("Decomposition failed: %s", exc)
        # Fallback: simple rolling-mean trend
        window = max(3, min(period, len(series) // 3))
        trend = series.rolling(window, center=True, min_periods=1).mean()
        residual = series - trend
        return {
            "labels":   [str(d)[:10] for d in series.index],
            "trend":    [_safe(v) for v in trend.values],
            "seasonal": [0.0] * len(series),
            "residual": [_safe(v) for v in residual.values],
        }


# ── Public API ────────────────────────────────────────────────────────────────
def run_forecast(
    df: pd.DataFrame,
    date_col: str,
    metric_col: str,
    horizon: Optional[int] = None,
    freq_override: Optional[str] = None,
    include_decomposition: bool = True,
) -> Dict:
    """
    Run full forecasting pipeline on a single metric time series.

    Parameters
    ----------
    df : input DataFrame
    date_col : name of the date / datetime column
    metric_col : name of the numeric metric to forecast
    horizon : number of future steps (auto-inferred if None)
    freq_override : override frequency detection ('D','W','M','Q', …)
    include_decomposition : whether to run seasonal decomposition

    Returns
    -------
    dict with keys:
        metric, freq, horizon,
        historical_labels, historical_values,
        forecast_labels, forecast_values,
        upper_95, lower_95, upper_80, lower_80,
        model_mapes,                 # dict of model → MAPE %
        best_model,
        decomposition,               # {labels, trend, seasonal, residual}
        summary_stats,               # {start_val, end_val, growth_pct, proj_total, …}
        error (str, only on failure)
    """
    result: Dict = {
        "metric": metric_col,
        "date_col": date_col,
    }

    try:
        # ── 1. Prepare series ─────────────────────────────────────────────
        ts = df[[date_col, metric_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col], errors="coerce")
        ts = ts.dropna(subset=[date_col])
        ts = ts.groupby(date_col)[metric_col].sum().sort_index()

        if len(ts) < _MIN_POINTS:
            result["error"] = f"Need at least {_MIN_POINTS} data points; got {len(ts)}"
            return result

        # ── 2. Frequency & resampling ─────────────────────────────────────
        freq_char = freq_override or _infer_freq(ts.index)
        ts = _resample_series(ts, freq_char)

        if len(ts) < _MIN_POINTS:
            result["error"] = "After resampling, too few data points remain"
            return result

        result["freq"] = freq_char

        # ── 3. Horizon ────────────────────────────────────────────────────
        if horizon is None:
            horizon = _HORIZON_MAP.get(freq_char, 30)
        result["horizon"] = horizon

        train = ts.values.astype(float)

        # ── 4. Run models ─────────────────────────────────────────────────
        hw_forecast,    hw_mape    = _holt_winters(train, horizon, freq_char)
        ridge_forecast, ridge_mape = _ridge_lag_model(train, horizon, freq_char)
        arima_forecast, arima_mape = _arima_model(train, horizon)

        models = [
            (hw_forecast,    hw_mape),
            (ridge_forecast, ridge_mape),
            (arima_forecast, arima_mape),
        ]
        model_names = ["Holt-Winters", "Ridge-Lag ML", "ARIMA"]

        result["model_mapes"] = {
            name: round(mape, 2) for name, (_, mape) in zip(model_names, models)
        }
        best_model = model_names[int(np.argmin([m[1] for m in models]))]
        result["best_model"] = best_model

        # ── 5. Ensemble ───────────────────────────────────────────────────
        # Residuals for uncertainty quantification
        hw_insample, _ = _holt_winters(train[:-max(1, horizon)], min(horizon, len(train) // 4), freq_char)
        residuals = train[-len(hw_insample):] - hw_insample if len(hw_insample) > 0 else train * 0.1

        point, upper_95, lower_95, upper_80, lower_80 = _ensemble(models, residuals)

        # ── 6. Future date labels ─────────────────────────────────────────
        last_date = ts.index[-1]
        freq_offset_map = {
            "D": "D", "W": "W", "M": "MS", "Q": "QS", "Y": "YS",
            "H": "H", "T": "T", "min": "T",
        }
        offset = freq_offset_map.get(freq_char, "D")
        try:
            future_index = pd.date_range(start=last_date, periods=horizon + 1, freq=offset)[1:]
        except Exception:
            future_index = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)

        fmt_map = {
            "D": "%Y-%m-%d", "W": "%Y-%m-%d", "M": "%b %Y",
            "Q": "%b %Y", "Y": "%Y", "H": "%Y-%m-%d %H:00", "T": "%H:%M",
        }
        date_fmt = fmt_map.get(freq_char, "%Y-%m-%d")
        hist_labels = [d.strftime(date_fmt) for d in ts.index]
        future_labels = [d.strftime(date_fmt) for d in future_index]

        # ── 7. Populate result ────────────────────────────────────────────
        result["historical_labels"] = hist_labels[-60:]   # cap for chart perf
        result["historical_values"] = [_safe(v) for v in train[-60:]]
        result["forecast_labels"]   = future_labels
        result["forecast_values"]   = [_safe(v) for v in point]
        result["upper_95"]          = [_safe(v) for v in upper_95]
        result["lower_95"]          = [_safe(v) for v in lower_95]
        result["upper_80"]          = [_safe(v) for v in upper_80]
        result["lower_80"]          = [_safe(v) for v in lower_80]

        # ── 8. Summary stats ──────────────────────────────────────────────
        start_val    = _safe(train[0])
        end_val      = _safe(train[-1])
        proj_end_val = _safe(point[-1])
        growth_hist  = ((end_val - start_val) / abs(start_val) * 100) if start_val != 0 else 0.0
        growth_proj  = ((proj_end_val - end_val) / abs(end_val) * 100) if end_val != 0 else 0.0
        proj_total   = float(np.sum(point))
        avg_mape     = float(np.mean([m[1] for m in models]))

        # Trend direction classification
        slope = np.polyfit(np.arange(len(train)), train, 1)[0]
        if slope > abs(np.mean(train)) * 0.005:
            direction = "upward"
        elif slope < -abs(np.mean(train)) * 0.005:
            direction = "downward"
        else:
            direction = "stable"

        result["summary_stats"] = {
            "start_val":        round(start_val, 2),
            "end_val":          round(end_val, 2),
            "proj_end_val":     round(proj_end_val, 2),
            "historical_growth_pct": round(growth_hist, 1),
            "projected_growth_pct":  round(growth_proj, 1),
            "proj_total":       round(proj_total, 2),
            "avg_mape":         round(avg_mape, 1),
            "direction":        direction,
            "n_points":         len(train),
        }

        # ── 9. Decomposition ──────────────────────────────────────────────
        if include_decomposition:
            result["decomposition"] = _decompose(ts, freq_char)

        log.info(
            "[forecast_engine] %s | freq=%s horizon=%d best=%s mape=%.1f%%",
            metric_col, freq_char, horizon, best_model, avg_mape,
        )

    except Exception as exc:
        log.exception("[forecast_engine] Unexpected error: %s", exc)
        result["error"] = f"Forecast failed: {exc}"

    return result
