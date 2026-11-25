from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .config import UniverseConfig
from .providers import Bar


@dataclass
class QualityReport:
    raw_rows: int = 0
    kept_rows: int = 0
    invalid_prices: int = 0
    invalid_ohlc: int = 0
    impossible_jumps: int = 0
    extreme_ranges: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "raw_rows": self.raw_rows,
            "kept_rows": self.kept_rows,
            "invalid_prices": self.invalid_prices,
            "invalid_ohlc": self.invalid_ohlc,
            "impossible_jumps": self.impossible_jumps,
            "extreme_ranges": self.extreme_ranges,
        }


def filter_bars(
    raw_bars: dict[str, dict[str, list[Bar]]], config: UniverseConfig
) -> tuple[dict[str, dict[str, list[Bar]]], QualityReport]:
    """Drop unusable bars before any persistence or feature calculation."""
    report = QualityReport()
    cleaned: dict[str, dict[str, list[Bar]]] = {}

    for source, by_symbol in raw_bars.items():
        cleaned[source] = {}
        for symbol, bars in by_symbol.items():
            previous: Bar | None = None
            kept: list[Bar] = []
            for bar in sorted(bars, key=lambda item: item.trade_date):
                report.raw_rows += 1
                values = (bar.open, bar.high, bar.low, bar.close)
                if any(not math.isfinite(float(value)) or float(value) <= 0 for value in values):
                    report.invalid_prices += 1
                    continue
                if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close) or bar.high < bar.low:
                    report.invalid_ohlc += 1
                    continue
                if previous is not None:
                    jump_pct = abs(bar.close / previous.close - 1.0) * 100.0
                    if jump_pct > config.max_daily_jump_pct:
                        report.impossible_jumps += 1
                        continue
                range_pct = (bar.high - bar.low) / bar.low * 100.0
                if range_pct > config.max_intraday_range_pct:
                    report.extreme_ranges += 1
                    continue
                kept.append(bar)
                previous = bar
            if kept:
                cleaned[source][symbol] = kept

    report.kept_rows = sum(len(bars) for by_symbol in cleaned.values() for bars in by_symbol.values())
    return cleaned, report


def apply_universe_filters(
    frames: dict[str, pd.DataFrame], config: UniverseConfig
) -> tuple[dict[str, pd.DataFrame], dict[str, list[str]], dict[str, list[str]]]:
    """Return eligible symbols, drop reasons and non-fatal flags."""
    eligible: dict[str, pd.DataFrame] = {}
    dropped: dict[str, list[str]] = {}
    flags: dict[str, list[str]] = {}

    for symbol, frame in frames.items():
        reasons: list[str] = []
        symbol_flags: list[str] = []
        sorted_frame = frame.sort_values("trade_date").reset_index(drop=True)
        if len(sorted_frame) < config.min_history_bars:
            reasons.append("short_history")
        if sorted_frame.empty:
            dropped[symbol] = reasons or ["no_bars"]
            continue

        last_close = float(sorted_frame.iloc[-1]["close"])
        if 0 < last_close < config.penny_max_price:
            if config.exclude_penny:
                reasons.append("penny_stock")
            else:
                symbol_flags.append("penny_stock")

        window = sorted_frame.tail(config.liquidity_lookback)
        values = (window["close"].astype(float) * window["volume"].astype(float)).median()
        if not math.isfinite(float(values)) or float(values) < config.min_average_daily_value:
            reasons.append("low_liquidity")

        if reasons:
            dropped[symbol] = reasons
            continue
        eligible[symbol] = sorted_frame
        if symbol_flags:
            flags[symbol] = symbol_flags

    return eligible, dropped, flags
