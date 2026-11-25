from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from engine.config import Config
from engine.features import build_features
from engine.model import train_model


def test_config() -> Config:
    with patch.dict(os.environ, {}, clear=True):
        return Config.from_env()


class ModelTests(unittest.TestCase):
    def test_training_uses_purged_chronological_split(self) -> None:
        config = test_config()
        dates = pd.bdate_range("2024-01-01", periods=400)
        index = np.arange(len(dates))
        close = 10 + np.sin(index / 3.0) * 0.6 + index * 0.01
        frame = pd.DataFrame(
            {
                "trade_date": dates,
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 100_000,
            }
        )
        model = train_model({"TEST": build_features(frame)}, config)

        self.assertIsNotNone(model.metrics)
        assert model.metrics is not None
        self.assertGreater(model.metrics["train_rows"], 0)
        self.assertGreater(model.metrics["validation_rows"], 0)
        self.assertGreaterEqual(model.metrics["purge_sessions"], 1)
        self.assertIn("signals", model.metrics)
        self.assertLess(model.metrics["train_rows"], len(dates))


if __name__ == "__main__":
    unittest.main()
