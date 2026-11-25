from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from engine.config import Config, ProviderConfig, load_signals_config, load_universe_config
from engine.providers import HttpProvider


class ConfigTests(unittest.TestCase):
    def test_universe_config_loads_thresholds_from_file(self) -> None:
        config = load_universe_config()
        self.assertGreaterEqual(len(config.seed_symbols), 300)
        self.assertEqual(len(config.seed_symbols), len(set(config.seed_symbols)))
        self.assertEqual(config.seed_symbols, tuple(sorted(config.seed_symbols)))
        self.assertTrue({"COMI", "FWRY", "ABUK", "TMGH"}.issubset(config.seed_symbols))
        self.assertGreaterEqual(config.minimum_universe_size, 100)
        self.assertGreater(config.min_history_bars, 0)
        self.assertGreater(config.min_average_daily_value, 0)
        self.assertGreater(config.max_daily_jump_pct, 0)

    def test_signals_config_loads_all_thresholds_from_file(self) -> None:
        config = load_signals_config()
        self.assertGreater(config.model.label_target_pct, 0)
        self.assertGreater(config.model.purge_sessions, 0)
        self.assertGreater(config.risk.price_limit_pct, 0)
        self.assertEqual(len(config.risk.tick_tiers), 5)
        self.assertGreater(config.signals.buy_probability, config.signals.avoid_probability)

    def test_secret_key_uses_new_name_only(self) -> None:
        clean = {
            key: value
            for key, value in os.environ.items()
            if key not in {"SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"}
        }
        with patch.dict(os.environ, clean, clear=True):
            with patch.dict(os.environ, {"SUPABASE_SECRET_KEY": "test-secret"}):
                config = Config.from_env()
        self.assertEqual(config.supabase_secret_key, "test-secret")
        self.assertFalse(hasattr(config, "service_role_key"))
        self.assertFalse(hasattr(config, "use_sample"))

    def test_free_quote_sources_are_enabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_env()

        self.assertTrue(config.tradingview_enabled)
        self.assertTrue(config.yahoo_quote_enabled)
        self.assertEqual(config.tradingview_delay_seconds, 900)
        self.assertEqual(config.yahoo_quote_delay_seconds, 1.0)
        self.assertEqual(config.egid_username, "")
        self.assertEqual(config.egid_password, "")

    def test_generic_http_provider_cannot_shadow_borsa_provider(self) -> None:
        provider = HttpProvider(ProviderConfig(prefix="BORSA"))
        self.assertEqual(provider.name, "http_borsa")


if __name__ == "__main__":
    unittest.main()
