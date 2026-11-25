from __future__ import annotations

import unittest
from datetime import date, timedelta

import pandas as pd

from engine.config import load_universe_config
from engine.providers import Bar
from engine.quality import apply_universe_filters, filter_bars


class QualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_universe_config()

    def test_filter_bars_drops_bad_and_impossible_rows(self) -> None:
        day = date(2026, 1, 5)
        bars = [
            Bar(day, 10, 10.5, 9.8, 10.2, 1000),
            Bar(day + timedelta(days=1), -1, 10, 9, 10, 1000),
            Bar(day + timedelta(days=2), 10, 9, 8, 10.2, 1000),
            Bar(day + timedelta(days=3), 10, 21.0, 9.8, 20.0, 1000),
            Bar(day + timedelta(days=4), 10, 30, 9.8, 10.2, 1000),
        ]
        cleaned, report = filter_bars({"yahoo": {"TEST": bars}}, self.config)

        self.assertEqual(report.raw_rows, 5)
        self.assertEqual(report.invalid_prices, 1)
        self.assertEqual(report.invalid_ohlc, 1)
        self.assertEqual(report.impossible_jumps, 1)
        self.assertEqual(report.extreme_ranges, 1)
        self.assertEqual(len(cleaned["yahoo"]["TEST"]), 1)

    def test_universe_filters_apply_history_liquidity_and_penny_rules(self) -> None:
        def frame(close: float, volume: int, rows: int) -> pd.DataFrame:
            dates = pd.date_range("2025-01-01", periods=rows, freq="B")
            return pd.DataFrame(
                {
                    "trade_date": dates,
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": volume,
                }
            )

        frames = {
            "GOOD": frame(10.0, 100_000, 130),
            "SHORT": frame(10.0, 100_000, 10),
            "PENNY": frame(0.5, 2_000_000, 130),
            "THIN": frame(10.0, 1, 130),
        }
        eligible, dropped, flags = apply_universe_filters(frames, self.config)

        self.assertEqual(list(eligible), ["GOOD", "PENNY"])
        self.assertIn("short_history", dropped["SHORT"])
        self.assertIn("low_liquidity", dropped["THIN"])
        self.assertEqual(flags.get("PENNY"), ["penny_stock"])


if __name__ == "__main__":
    unittest.main()
