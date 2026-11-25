from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from .backtest import summarise_signals
from .config import Config
from .features import FEATURE_COLUMNS


class HeuristicModel:
    """Fallback used when there is not enough history to train XGBoost."""

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        data = pd.DataFrame(features, columns=FEATURE_COLUMNS).astype(float)
        signal = (
            data["trend_slope_20"] * 20
            + data["ret_5"] * 5
            + (data["rsi_14"] - 50) / 100
            + data["macd_hist_ratio"] * 10
        )
        probability = 1 / (1 + np.exp(-signal))
        return np.column_stack([1 - probability, probability])


@dataclass
class TrainedModel:
    estimator: Any
    version: str
    train_rows: int
    validation_accuracy: float | None
    metrics: dict[str, Any] | None = None


def build_training_frame(
    frames: dict[str, pd.DataFrame], horizon_days: int, target_pct: float
) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    for symbol, frame in frames.items():
        part = frame[["trade_date", *FEATURE_COLUMNS]].copy()
        future_close = frame["close"].shift(-horizon_days)
        part["forward_return"] = (future_close / frame["close"] - 1) * 100
        part = part.dropna(subset=["forward_return"])
        if part.empty:
            continue
        part["label"] = (part["forward_return"] >= target_pct).astype(int)
        part["symbol"] = symbol
        pieces.append(part)

    if not pieces:
        return pd.DataFrame(columns=["trade_date", *FEATURE_COLUMNS, "forward_return", "label", "symbol"])
    return pd.concat(pieces, ignore_index=True).sort_values("trade_date").reset_index(drop=True)


def _binary_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    true_positive = int(np.sum((actual == 1) & (predicted == 1)))
    false_positive = int(np.sum((actual == 0) & (predicted == 1)))
    false_negative = int(np.sum((actual == 1) & (predicted == 0)))
    true_negative = int(np.sum((actual == 0) & (predicted == 0)))
    total = len(actual)
    return {
        "accuracy": round((true_positive + true_negative) / total, 4) if total else 0.0,
        "precision": round(true_positive / (true_positive + false_positive), 4)
        if true_positive + false_positive else 0.0,
        "recall": round(true_positive / (true_positive + false_negative), 4)
        if true_positive + false_negative else 0.0,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
    }


def train_model(frames: dict[str, pd.DataFrame], config: Config) -> TrainedModel:
    model_cfg = config.signals.model
    data = build_training_frame(frames, config.horizon_days, config.target_pct)
    if len(data) < model_cfg.min_training_rows or data["label"].nunique() < 2:
        return TrainedModel(HeuristicModel(), f"heuristic+{config.model_version}", len(data), None)

    data = data.sort_values("trade_date").reset_index(drop=True)
    dates = data["trade_date"].drop_duplicates().sort_values().tolist()
    cut = int(len(dates) * model_cfg.train_fraction)
    # The purge must cover at least the label horizon so forward windows from
    # training rows never reach into the validation period.
    purge = max(model_cfg.purge_sessions, config.horizon_days)
    train_dates = set(dates[: max(0, cut - purge)])
    validation_dates = set(dates[min(len(dates), cut + purge) :])
    train = data[data["trade_date"].isin(train_dates)]
    validation = data[data["trade_date"].isin(validation_dates)]
    split_date = str(dates[cut - 1])[:10] if cut > 0 else ""

    if len(train) < model_cfg.min_training_rows or validation.empty:
        return TrainedModel(HeuristicModel(), f"heuristic+{config.model_version}", len(data), None)

    params: dict[str, Any] = {
        "n_estimators": 280,
        "max_depth": 4,
        "learning_rate": 0.05,
        "min_child_weight": 3,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "tree_method": "hist",
        "n_jobs": 2,
        "random_state": 42,
        "verbosity": 0,
    }
    params.update(model_cfg.xgboost)
    estimator = XGBClassifier(**params)
    estimator.fit(train[FEATURE_COLUMNS], train["label"])

    probabilities = estimator.predict_proba(validation[FEATURE_COLUMNS])[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    metrics = _binary_metrics(validation["label"].to_numpy(), predictions)
    metrics.update(
        {
            "train_rows": int(len(train)),
            "validation_rows": int(len(validation)),
            "split_date": split_date,
            "purge_sessions": purge,
            "signals": summarise_signals(validation, probabilities, config),
        }
    )
    accuracy = float(metrics["accuracy"])

    return TrainedModel(estimator, config.model_version, len(train), accuracy, metrics)


def predict_probability(estimator: Any, feature_values: dict[str, float]) -> float:
    row = pd.DataFrame([[float(feature_values.get(name, 0.0)) for name in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
    probability = float(estimator.predict_proba(row)[0][1])
    if not np.isfinite(probability):
        return 0.5
    return float(min(1.0, max(0.0, probability)))
