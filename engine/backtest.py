from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .config import Config, RiskConfig
from .risk import derive_signal

BUY_SIGNALS = ("شراء قوي", "شراء")


def approximate_reward_risk(atr_pct_ratio: float, risk: RiskConfig) -> float:
    """Reward/risk from ATR only, used for out-of-sample signal summary."""
    atr_pct = max(0.0, float(atr_pct_ratio)) * 100
    target = min(risk.max_target_pct, max(risk.min_target_pct, risk.target_atr_multiplier * atr_pct))
    stop = min(risk.max_stop_pct, max(risk.min_stop_pct, risk.stop_atr_multiplier * atr_pct))
    return target / stop if stop > 0 else 0.0


def summarise_signals(validation: pd.DataFrame, probabilities: np.ndarray, config: Config) -> dict[str, Any]:
    """Summarise signal rules on the purged validation slice."""
    rules = config.signals.signals
    risk = config.signals.risk
    weights = config.signals.score
    total_weight = weights.probability + weights.reward_risk + weights.momentum + weights.volume

    rows: list[dict[str, Any]] = []
    for (_, row), probability in zip(validation.iterrows(), np.asarray(probabilities)):
        reward_risk = approximate_reward_risk(float(row.get("atr_pct", 0.0)), risk)
        momentum = max(
            -1.0,
            min(1.0, float(row.get("trend_slope_20", 0.0)) * 25 + float(row.get("ret_5", 0.0)) * 5),
        )
        volume = max(0.0, min(2.0, float(row.get("volume_ratio", 0.0))))
        score = (
            probability * weights.probability
            + (min(reward_risk, risk.max_reward_risk) / risk.max_reward_risk) * weights.reward_risk
            + ((momentum + 1) / 2) * weights.momentum
            + (volume / 2) * weights.volume
        )
        if total_weight:
            score = 100 * score / total_weight
        rows.append(
            {
                "signal": derive_signal(float(probability), score, reward_risk, rules),
                "label": int(row.get("label", 0)),
                "forward_return": float(row.get("forward_return", 0.0)),
                "reward_risk": reward_risk,
            }
        )

    if not rows:
        return {"buy_rows": 0, "buy_hit_rate": None, "buy_precision": None, "buy_recall": None}

    frame = pd.DataFrame(rows)
    counts = frame["signal"].value_counts().to_dict()
    buy = frame[frame["signal"].isin(BUY_SIGNALS)]
    total_hits = int(frame["label"].sum())
    buy_hits = int(buy["label"].sum()) if not buy.empty else 0

    return {
        "counts": {str(key): int(value) for key, value in counts.items()},
        "buy_rows": int(len(buy)),
        "buy_hit_rate": round(buy["label"].mean(), 4) if not buy.empty else None,
        "buy_precision": round(buy["label"].mean(), 4) if not buy.empty else None,
        "buy_recall": round(buy_hits / total_hits, 4) if total_hits else None,
        "average_forward_return_buy": round(float(buy["forward_return"].mean()), 4) if not buy.empty else None,
    }
