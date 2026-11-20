from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

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


def train_model(frames: dict[str, pd.DataFrame], config: Config) -> TrainedModel:
    data = build_training_frame(frames, config.horizon_days, config.target_pct)
    if len(data) < 150 or data["label"].nunique() < 2:
        return TrainedModel(HeuristicModel(), f"heuristic+{config.model_version}", len(data), None)

    split = int(len(data) * 0.8)
    train = data.iloc[:split]
    validation = data.iloc[split:]

    estimator = XGBClassifier(
        n_estimators=280,
        max_depth=4,
        learning_rate=0.05,
        min_child_weight=3,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="auc",
        tree_method="hist",
        n_jobs=2,
        random_state=42,
        verbosity=0,
    )
    estimator.fit(train[FEATURE_COLUMNS], train["label"])

    accuracy: float | None = None
    if not validation.empty:
        predictions = estimator.predict(validation[FEATURE_COLUMNS])
        accuracy = float(np.mean(predictions == validation["label"].to_numpy()))

    return TrainedModel(estimator, config.model_version, len(train), accuracy)


def predict_probability(estimator: Any, feature_values: dict[str, float]) -> float:
    row = pd.DataFrame([[float(feature_values.get(name, 0.0)) for name in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
    probability = float(estimator.predict_proba(row)[0][1])
    if not np.isfinite(probability):
        return 0.5
    return float(min(1.0, max(0.0, probability)))
