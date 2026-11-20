from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from .config import Config
from .repository import SupabaseRepository

LOG = logging.getLogger("egx.evaluate")


def _as_date(value: str) -> date:
    return date.fromisoformat(str(value)[:10])


def evaluate_outcomes(repo: SupabaseRepository, config: Config) -> int:
    """Score recommendations once their 2-3 day holding period has elapsed."""
    recommendations = repo.select(
        "recommendations",
        columns="id,symbol,as_of,horizon_days,entry_price,target_price,stop_loss,created_at",
        params={"order": "created_at.desc", "limit": 3000},
    )
    if not recommendations:
        return 0

    existing = {
        row["recommendation_id"]
        for row in repo.select("recommendation_outcomes", columns="recommendation_id", params={"limit": 10000})
    }
    pending = [row for row in recommendations if row["id"] not in existing]
    if not pending:
        return 0

    symbols = sorted({row["symbol"] for row in pending})
    symbol_filter = "in.(" + ",".join(symbols) + ")"
    bars = repo.select(
        "price_bars",
        columns="symbol,trade_date,high,low,close",
        params={"source": "eq.aggregated", "symbol": symbol_filter, "order": "trade_date.asc", "limit": 100000},
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for bar in bars:
        grouped[bar["symbol"]].append(bar)

    evaluated_at = datetime.now(timezone.utc).isoformat()
    outcomes: list[dict[str, Any]] = []

    for recommendation in pending:
        as_of = _as_date(recommendation["as_of"])
        future = [
            bar for bar in grouped[recommendation["symbol"]] if _as_date(bar["trade_date"]) > as_of
        ]
        future.sort(key=lambda bar: bar["trade_date"])

        horizon = int(recommendation.get("horizon_days") or config.horizon_days)
        if len(future) < horizon:
            continue

        window = future[:horizon]
        entry = float(recommendation["entry_price"])
        target = float(recommendation["target_price"])
        stop = float(recommendation["stop_loss"])

        target_dates = [bar["trade_date"] for bar in window if float(bar["high"]) >= target]
        stop_dates = [bar["trade_date"] for bar in window if float(bar["low"]) <= stop]

        if target_dates and stop_dates:
            result = "win" if target_dates[0] <= stop_dates[0] else "loss"
        elif target_dates:
            result = "win"
        elif stop_dates:
            result = "loss"
        else:
            change = (float(window[-1]["close"]) / entry - 1) * 100
            result = "win" if change > 0.5 else "loss" if change < -0.5 else "flat"

        final_bar = window[-1]
        outcomes.append(
            {
                "recommendation_id": recommendation["id"],
                "evaluated_at": evaluated_at,
                "exit_date": final_bar["trade_date"],
                "exit_price": round(float(final_bar["close"]), 4),
                "max_high": round(max(float(bar["high"]) for bar in window), 4),
                "min_low": round(min(float(bar["low"]) for bar in window), 4),
                "hit_target": bool(target_dates),
                "hit_stop": bool(stop_dates),
                "return_pct": round((float(final_bar["close"]) / entry - 1) * 100, 4),
                "outcome": result,
            }
        )

    if outcomes:
        repo.upsert("recommendation_outcomes", outcomes, "recommendation_id")
    LOG.info("Evaluated %d recommendation(s)", len(outcomes))
    return len(outcomes)
