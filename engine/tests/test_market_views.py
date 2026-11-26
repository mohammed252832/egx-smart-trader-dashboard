from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20261126025651_expand_market_universe_coverage.sql"
SCHEMA = ROOT / "supabase/schema.sql"


def latest_market_view(sql: str) -> str:
    start = sql.index("create or replace view public.latest_market")
    end = sql.find("create or replace view public.monthly_price_bars", start)
    if end == -1:
        end = len(sql)
    return sql[start:end].strip()


class MarketViewTests(unittest.TestCase):
    def test_fresh_schema_matches_coverage_migration(self) -> None:
        self.assertEqual(latest_market_view(SCHEMA.read_text(encoding="utf-8")), latest_market_view(MIGRATION.read_text(encoding="utf-8")))

    def test_market_coverage_does_not_use_analysis_eligibility(self) -> None:
        view = latest_market_view(MIGRATION.read_text(encoding="utf-8"))
        self.assertNotIn("stocks.is_active", view)
        self.assertIn("max(recent.trade_date) >= market_session.trade_date - 30", view)

    def test_liquidity_ranking_tolerates_zero_volume_sessions(self) -> None:
        view = latest_market_view(MIGRATION.read_text(encoding="utf-8"))
        self.assertIn("count(recent.close) filter (where recent.close > 0) = 20", view)
        self.assertIn("count(recent.volume) filter (where recent.volume > 0) >= 1", view)
        self.assertNotIn("count(recent.close) filter (where recent.close > 0 and recent.volume > 0) = 20", view)

    def test_view_keeps_invoker_security(self) -> None:
        view = latest_market_view(MIGRATION.read_text(encoding="utf-8"))
        self.assertIn("with (security_invoker = true)", view)


if __name__ == "__main__":
    unittest.main()
