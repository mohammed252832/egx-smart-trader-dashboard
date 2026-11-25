from __future__ import annotations

from dataclasses import dataclass

from .config import Config, SignalRules


@dataclass(frozen=True)
class TradePlan:
    entry_price: float
    target_price: float
    stop_loss: float
    upside_pct: float
    risk_pct: float
    reward_risk: float
    score: float
    probability: float
    confidence: float
    signal: str


def derive_signal(probability: float, score: float, reward_risk: float, rules: SignalRules) -> str:
    """Map model probability and risk quality into an Arabic trading signal."""
    if (
        probability >= rules.strong_buy_probability
        and score >= rules.strong_buy_score
        and reward_risk >= rules.min_reward_risk
    ):
        return "شراء قوي"
    if probability >= rules.buy_probability and reward_risk >= rules.min_reward_risk:
        return "شراء"
    if probability < rules.avoid_probability or reward_risk < rules.min_reward_risk:
        return "تجنّب"
    return "مراقبة"


def build_plan(
    probability: float,
    feature_values: dict[str, float],
    last_close: float,
    previous_close: float,
    atr: float,
    config: Config,
    support: float | None = None,
    resistance: float | None = None,
) -> TradePlan:
    """Build a per-stock plan from ATR, recent levels and EGX price rules."""
    risk_cfg = config.signals.risk
    entry = risk_cfg.round_price(last_close)
    if entry <= 0:
        raise ValueError("Entry price must be positive")

    atr_value = float(atr)
    if not (atr_value > 0) or atr_value != atr_value:
        atr_value = entry * 0.01
    atr_pct = atr_value / entry * 100

    target_move = min(
        risk_cfg.max_target_pct,
        max(risk_cfg.min_target_pct, risk_cfg.target_atr_multiplier * atr_pct),
    )
    stop_move = min(
        risk_cfg.max_stop_pct,
        max(risk_cfg.min_stop_pct, risk_cfg.stop_atr_multiplier * atr_pct),
    )

    if support is not None and 0 < support < entry:
        support_move = (entry - support) / entry * 100 - risk_cfg.level_buffer_pct
        if support_move > 0:
            stop_move = min(risk_cfg.max_stop_pct, max(stop_move, support_move))
    if resistance is not None and resistance > entry:
        resistance_move = (resistance - entry) / entry * 100 + risk_cfg.level_buffer_pct
        target_move = max(target_move, resistance_move)
    target_move = min(target_move, risk_cfg.max_target_pct, risk_cfg.max_upside_pct)

    limit = max(0.0, risk_cfg.price_limit_pct - risk_cfg.limit_buffer_pct)
    upper_limit_price: float | None = None
    lower_limit_price: float | None = None
    if previous_close > 0:
        upper_limit_price = previous_close * (1 + limit / 100)
        lower_limit_price = previous_close * (1 - limit / 100)
        max_upside_from_limit = (upper_limit_price / entry - 1) * 100
        max_stop_from_limit = (1 - lower_limit_price / entry) * 100
        target_move = min(target_move, max(0.0, max_upside_from_limit))
        stop_move = min(stop_move, max(0.0, max_stop_from_limit))

    target = risk_cfg.round_price(entry * (1 + target_move / 100))
    stop = risk_cfg.round_price(entry * (1 - stop_move / 100))
    # Rounding up to the next tick must not breach the daily price limit.
    if upper_limit_price is not None and target > upper_limit_price:
        target = risk_cfg.round_down(upper_limit_price)
    if lower_limit_price is not None and stop < lower_limit_price:
        stop = risk_cfg.round_up(lower_limit_price)
    if target > entry * (1 + risk_cfg.max_upside_pct / 100):
        target = risk_cfg.round_down(entry * (1 + risk_cfg.max_upside_pct / 100))
        if upper_limit_price is not None and target > upper_limit_price:
            target = risk_cfg.round_down(upper_limit_price)

    upside = (target / entry - 1) * 100
    risk = (entry - stop) / entry * 100

    reward_risk = upside / risk if risk > 0 else 0.0
    momentum = max(
        -1.0,
        min(1.0, float(feature_values.get("trend_slope_20", 0.0)) * 25 + float(feature_values.get("ret_5", 0.0)) * 5),
    )
    volume_ratio = max(0.0, min(2.0, float(feature_values.get("volume_ratio", 0.0))))

    weights = config.signals.score
    weighted_score = (
        probability * weights.probability
        + (min(reward_risk, risk_cfg.max_reward_risk) / risk_cfg.max_reward_risk) * weights.reward_risk
        + ((momentum + 1) / 2) * weights.momentum
        + (volume_ratio / 2) * weights.volume
    )
    total_weight = weights.probability + weights.reward_risk + weights.momentum + weights.volume
    score = round(100 * weighted_score / total_weight if total_weight else 0.0, 2)
    score = min(100.0, max(0.0, score))

    signal = derive_signal(probability, score, reward_risk, config.signals.signals)

    return TradePlan(
        entry_price=entry,
        target_price=target,
        stop_loss=stop,
        upside_pct=round(upside, 4),
        risk_pct=round(risk, 4),
        reward_risk=round(reward_risk, 4),
        score=score,
        probability=round(probability, 4),
        confidence=round(probability, 4),
        signal=signal,
    )
