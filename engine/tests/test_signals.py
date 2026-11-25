from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from engine.backtest import summarise_signals
from engine.config import Config
from engine.model import TrainedModel, HeuristicModel
from engine.model_report import build_report
from engine.risk import build_plan, derive_signal


def test_config() -> Config:
    with patch.dict(os.environ, {}, clear=True):
        return Config.from_env()


class SignalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = test_config()

    def test_tick_size_tiers(self) -> None:
        risk = self.config.signals.risk
        self.assertEqual(risk.tick_size(0.5), 0.005)
        self.assertEqual(risk.tick_size(3.0), 0.01)
        self.assertEqual(risk.tick_size(50.0), 0.1)
        self.assertEqual(risk.tick_size(500.0), 0.5)

    def test_plan_respects_upside_and_daily_price_caps(self) -> None:
        plan = build_plan(
            probability=0.85,
            feature_values={"trend_slope_20": 0.02, "ret_5": 0.03, "volume_ratio": 1.5},
            last_close=10.0,
            previous_close=9.8,
            atr=2.0,
            config=self.config,
            support=5.0,
            resistance=15.0,
        )
        risk = self.config.signals.risk
        self.assertLessEqual(plan.upside_pct, risk.max_upside_pct)
        self.assertLessEqual(plan.target_price, 9.8 * (1 + (risk.price_limit_pct - risk.limit_buffer_pct) / 100) + 1e-6)
        self.assertGreaterEqual(plan.stop_loss, 9.8 * (1 - (risk.price_limit_pct - risk.limit_buffer_pct) / 100) - 1e-6)
        self.assertGreater(plan.reward_risk, 0)
        self.assertEqual(plan.probability, plan.confidence)
        self.assertIn(plan.signal, {"شراء قوي", "شراء", "مراقبة", "تجنّب"})

    def test_signal_states(self) -> None:
        rules = self.config.signals.signals
        self.assertEqual(derive_signal(0.8, 85, 2.0, rules), "شراء قوي")
        self.assertEqual(derive_signal(0.6, 50, 2.0, rules), "شراء")
        self.assertEqual(derive_signal(0.3, 20, 2.0, rules), "تجنّب")
        self.assertEqual(derive_signal(0.5, 50, 2.0, rules), "مراقبة")

    def test_backtest_summary_returns_signal_counts(self) -> None:
        validation = pd.DataFrame(
            {
                "label": [1, 0, 1],
                "forward_return": [3.0, -1.0, 2.5],
                "atr_pct": [0.02, 0.01, 0.03],
                "trend_slope_20": [0.01, -0.01, 0.02],
                "ret_5": [0.02, 0.0, 0.03],
                "volume_ratio": [1.2, 0.8, 1.5],
            }
        )
        summary = summarise_signals(validation, np.array([0.8, 0.3, 0.6]), self.config)
        self.assertEqual(sum(summary["counts"].values()), 3)
        self.assertGreaterEqual(summary["buy_rows"], 1)

    def test_report_documents_score_and_thresholds(self) -> None:
        model = TrainedModel(HeuristicModel(), "test", 0, None)
        report = build_report(model, self.config)
        self.assertIn("Strength score", report)
        self.assertIn("Signal thresholds", report)
        self.assertNotIn("sb_secret", report)


if __name__ == "__main__":
    unittest.main()
