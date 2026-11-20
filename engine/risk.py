from __future__ import annotations

from dataclasses import dataclass

from .config import Config


@dataclass(frozen=True)
class TradePlan:
    entry_price: float
    target_price: float
    stop_loss: float
    upside_pct: float
    risk_pct: float
    reward_risk: float
    score: float
    confidence: float
    signal: str


def build_plan(
    probability: float,
    feature_values: dict[str, float],
    last_close: float,
    atr: float,
    config: Config,
) -> TradePlan:
    """Translate a model probability into an actionable, ATR-based trade plan."""
    entry = round(float(last_close), 4)
    if entry <= 0:
        raise ValueError("Entry price must be positive")

    atr_value = float(atr)
    if not (atr_value > 0) or atr_value != atr_value:
        atr_value = entry * 0.01
    atr_pct = atr_value / entry * 100

    target_move = max(config.target_pct, config.target_atr * atr_pct)
    stop_move = min(config.max_stop_pct, max(0.8, config.stop_atr * atr_pct))

    target = round(entry * (1 + target_move / 100), 4)
    stop = round(entry * (1 - stop_move / 100), 4)

    upside = (target / entry - 1) * 100
    risk = (entry - stop) / entry * 100
    reward_risk = upside / risk if risk > 0 else 0.0

    momentum = max(
        -1.0,
        min(1.0, float(feature_values.get("trend_slope_20", 0.0)) * 25 + float(feature_values.get("ret_5", 0.0)) * 5),
    )
    score = probability * 70 + (min(reward_risk, 3.0) / 3.0) * 20 + ((momentum + 1) / 2) * 10
    score = round(min(100.0, max(0.0, score)), 2)

    if probability >= 0.70 and score >= 78:
        signal = "شراء قوي"
    elif probability >= 0.58:
        signal = "شراء"
    else:
        signal = "مراقبة"

    return TradePlan(
        entry_price=entry,
        target_price=target,
        stop_loss=stop,
        upside_pct=round(upside, 4),
        risk_pct=round(risk, 4),
        reward_risk=round(reward_risk, 4),
        score=score,
        confidence=round(probability, 4),
        signal=signal,
    )
