from __future__ import annotations

import unittest
from datetime import date

from engine.aggregator import aggregate_bars
from engine.providers.base import Bar


class AggregatorTests(unittest.TestCase):
    def test_duplicate_provider_sessions_do_not_double_count_volume(self) -> None:
        session = date(2026, 11, 24)
        raw_bars = {
            "yahoo": {"COMI": [Bar(session, 24.8, 25.4, 24.6, 25.2, 1_000)]},
            "borsa": {"COMI": [Bar(session, 24.8, 25.4, 24.6, 25.2, 1_000)]},
        }

        frames = aggregate_bars(raw_bars)

        self.assertEqual(int(frames["COMI"].iloc[0]["volume"]), 1_000)
        self.assertEqual(float(frames["COMI"].iloc[0]["close"]), 25.2)


if __name__ == "__main__":
    unittest.main()
