from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _parse_headers(raw: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for part in raw.split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        key, value = key.strip(), value.strip()
        if key and value:
            headers[key] = value
    return headers


DEFAULT_EGID_UNIVERSE_URL = "https://ticker.egidegypt.com/api/Feed/GetAllMarketWatchNames"
DEFAULT_EGID_BASE_URL = "https://ticker.egidegypt.com"
DEFAULT_EGID_PUBLIC_TICKER_URL = "https://feed.egitdns.net/api/DelayedFeed/getTickerInfo"
DEFAULT_TRADINGVIEW_SCANNER_URL = "https://scanner.tradingview.com/egypt/scan"
DEFAULT_YAHOO_HOSTS = "query1.finance.yahoo.com,query2.finance.yahoo.com"
DEFAULT_BORSA_BASE_URL = "https://demo.borsa.ashh.me"
DEFAULT_UNIVERSE_CONFIG = Path(__file__).parent / "config" / "universe.json"
DEFAULT_SIGNALS_CONFIG = Path(__file__).parent / "config" / "signals.json"


@dataclass(frozen=True)
class UniverseConfig:
    seed_symbols: tuple[str, ...]
    minimum_universe_size: int
    liquidity_lookback: int
    min_average_daily_value: float
    penny_max_price: float
    exclude_penny: bool
    min_history_bars: int
    max_daily_jump_pct: float
    max_intraday_range_pct: float
    max_stale_sessions: int
    index_sources: tuple[tuple[str, str], ...] = ()


def load_universe_config(path: Path = DEFAULT_UNIVERSE_CONFIG) -> UniverseConfig:
    """Load universe and data-quality thresholds from a config file, never from code."""
    with Path(path).open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = json.load(handle)

    liquidity = raw.get("liquidity") or {}
    penny = raw.get("penny_stock") or {}
    quality = raw.get("quality") or {}
    freshness = raw.get("freshness") or {}
    indexes = raw.get("index_sources") or []

    return UniverseConfig(
        seed_symbols=tuple(str(item).strip().upper() for item in raw.get("seed_symbols", []) if str(item).strip()),
        minimum_universe_size=max(1, int(liquidity.get("minimum_universe_size", raw.get("minimum_universe_size", 100)))),
        liquidity_lookback=max(1, int(liquidity.get("lookback_sessions", 20))),
        min_average_daily_value=max(0.0, float(liquidity.get("min_average_daily_value_egp", 500_000))),
        penny_max_price=max(0.0, float(penny.get("max_price_egp", 1.0))),
        exclude_penny=bool(penny.get("exclude", False)),
        min_history_bars=max(30, int(quality.get("min_history_bars", 120))),
        max_daily_jump_pct=max(1.0, float(quality.get("max_daily_jump_pct", 25.0))),
        max_intraday_range_pct=max(1.0, float(quality.get("max_intraday_range_pct", 60.0))),
        max_stale_sessions=max(0, int(freshness.get("max_stale_sessions", 1))),
        index_sources=tuple(
            (str(item.get("name", "")).strip(), str(item.get("url", "")).strip())
            for item in indexes
            if isinstance(item, dict) and item.get("url")
        ),
    )


@dataclass(frozen=True)
class TickTier:
    max_price: float | None
    tick_size: float


@dataclass(frozen=True)
class RiskConfig:
    target_atr_multiplier: float
    stop_atr_multiplier: float
    min_target_pct: float
    max_target_pct: float
    min_stop_pct: float
    max_stop_pct: float
    max_reward_risk: float
    max_upside_pct: float
    support_lookback: int
    level_buffer_pct: float
    price_limit_pct: float
    limit_buffer_pct: float
    tick_tiers: tuple[TickTier, ...]

    def tick_size(self, price: float) -> float:
        for tier in self.tick_tiers:
            if tier.max_price is None or price <= tier.max_price:
                return tier.tick_size
        return self.tick_tiers[-1].tick_size if self.tick_tiers else 0.01

    def round_price(self, price: float) -> float:
        tick = self.tick_size(max(0.0, float(price)))
        return round(round(float(price) / tick) * tick, 6)

    def round_down(self, price: float) -> float:
        tick = self.tick_size(max(0.0, float(price)))
        return round(math.floor(float(price) / tick) * tick, 6)

    def round_up(self, price: float) -> float:
        tick = self.tick_size(max(0.0, float(price)))
        return round(math.ceil(float(price) / tick) * tick, 6)


@dataclass(frozen=True)
class ModelConfig:
    label_target_pct: float
    train_fraction: float
    purge_sessions: int
    min_training_rows: int
    xgboost: dict[str, Any]


@dataclass(frozen=True)
class SignalRules:
    strong_buy_probability: float
    buy_probability: float
    avoid_probability: float
    strong_buy_score: float
    min_reward_risk: float


@dataclass(frozen=True)
class ScoreWeights:
    probability: float
    reward_risk: float
    momentum: float
    volume: float


@dataclass(frozen=True)
class SignalsConfig:
    model: ModelConfig
    risk: RiskConfig
    signals: SignalRules
    score: ScoreWeights


def load_signals_config(path: Path = DEFAULT_SIGNALS_CONFIG) -> SignalsConfig:
    """Load all signal, risk and scoring thresholds from a config file."""
    with Path(path).open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = json.load(handle)

    model = raw.get("model") or {}
    risk = raw.get("risk") or {}
    signals = raw.get("signals") or {}
    score = raw.get("score_weights") or {}

    tiers = tuple(
        TickTier(
            max_price=None if item.get("max_price_egp") is None else float(item["max_price_egp"]),
            tick_size=max(0.0001, float(item.get("tick_size_egp", 0.01))),
        )
        for item in (risk.get("tick_size_tiers") or [])
        if isinstance(item, dict)
    )

    return SignalsConfig(
        model=ModelConfig(
            label_target_pct=max(0.1, float(model.get("label_target_pct", 2.0))),
            train_fraction=min(0.95, max(0.5, float(model.get("train_fraction", 0.8)))),
            purge_sessions=max(0, int(model.get("purge_sessions", 3))),
            min_training_rows=max(50, int(model.get("min_training_rows", 150))),
            xgboost=dict(model.get("xgboost") or {}),
        ),
        risk=RiskConfig(
            target_atr_multiplier=max(0.1, float(risk.get("target_atr_multiplier", 1.8))),
            stop_atr_multiplier=max(0.1, float(risk.get("stop_atr_multiplier", 1.1))),
            min_target_pct=max(0.1, float(risk.get("min_target_pct", 1.5))),
            max_target_pct=max(1.0, float(risk.get("max_target_pct", 9.0))),
            min_stop_pct=max(0.1, float(risk.get("min_stop_pct", 0.8))),
            max_stop_pct=max(0.1, float(risk.get("max_stop_pct", 5.0))),
            max_reward_risk=max(1.0, float(risk.get("max_reward_risk", 3.0))),
            max_upside_pct=max(1.0, float(risk.get("max_upside_pct", 8.0))),
            support_lookback=max(5, int(risk.get("support_lookback", 20))),
            level_buffer_pct=max(0.0, float(risk.get("level_buffer_pct", 0.5))),
            price_limit_pct=max(1.0, float(risk.get("price_limit_pct", 10.0))),
            limit_buffer_pct=max(0.0, float(risk.get("limit_buffer_pct", 0.5))),
            tick_tiers=tiers,
        ),
        signals=SignalRules(
            strong_buy_probability=min(1.0, max(0.5, float(signals.get("strong_buy_probability", 0.68)))),
            buy_probability=min(1.0, max(0.4, float(signals.get("buy_probability", 0.56)))),
            avoid_probability=min(1.0, max(0.0, float(signals.get("avoid_probability", 0.4)))),
            strong_buy_score=float(signals.get("strong_buy_score", 75)),
            min_reward_risk=max(0.5, float(signals.get("min_reward_risk", 1.2))),
        ),
        score=ScoreWeights(
            probability=float(score.get("probability", 65)),
            reward_risk=float(score.get("reward_risk", 20)),
            momentum=float(score.get("momentum", 10)),
            volume=float(score.get("volume", 5)),
        ),
    )


@dataclass(frozen=True)
class ProviderConfig:
    prefix: str
    api_key: str = ""
    universe_url: str = ""
    history_url: str = ""
    auth_header: str = ""
    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return bool(self.universe_url or self.history_url)


@dataclass(frozen=True)
class Config:
    supabase_url: str
    supabase_secret_key: str
    history_days: int
    horizon_days: int
    top_n: int
    market_universe_size: int
    target_pct: float
    stop_atr: float
    target_atr: float
    max_stop_pct: float
    provider_prefixes: tuple[str, ...]
    request_timeout: int
    model_version: str
    universe: UniverseConfig
    yahoo_enabled: bool
    yahoo_universe_url: str
    yahoo_range: str
    yahoo_hosts: tuple[str, ...]
    borsa_enabled: bool
    borsa_base_url: str
    borsa_api_key: str
    egid_enabled: bool
    egid_base_url: str
    egid_username: str
    egid_password: str
    egid_delay_seconds: int
    egid_public_enabled: bool
    egid_public_ticker_url: str
    egid_public_delay_seconds: int
    tradingview_enabled: bool
    tradingview_scanner_url: str
    tradingview_delay_seconds: int
    tradingview_chunk_size: int
    yahoo_quote_enabled: bool
    yahoo_quote_delay_seconds: float
    signals: SignalsConfig

    @classmethod
    def from_env(cls) -> "Config":
        universe_path = os.getenv("EGX_UNIVERSE_CONFIG", "").strip()
        signals_path = os.getenv("EGX_SIGNALS_CONFIG", "").strip()
        signals = load_signals_config(Path(signals_path) if signals_path else DEFAULT_SIGNALS_CONFIG)
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", "").strip(),
            supabase_secret_key=os.getenv("SUPABASE_SECRET_KEY", "").strip(),
            history_days=max(120, _get_int("EGX_HISTORY_DAYS", 400)),
            horizon_days=max(1, _get_int("EGX_HORIZON_DAYS", 3)),
            top_n=max(1, _get_int("EGX_TOP_N", 10)),
            market_universe_size=max(1, min(500, _get_int("EGX_MARKET_UNIVERSE_SIZE", 250))),
            target_pct=signals.model.label_target_pct,
            stop_atr=signals.risk.stop_atr_multiplier,
            target_atr=signals.risk.target_atr_multiplier,
            max_stop_pct=signals.risk.max_stop_pct,
            provider_prefixes=tuple(
                part.strip().upper()
                for part in (
                    os.getenv("EGX_PROVIDERS", "").strip()
                    or "DATACEDAR,EGID,BORSA,EGX,OANOR,EGXNEWS"
                ).split(",")
                if part.strip()
            ),
            request_timeout=max(1, _get_int("EGX_REQUEST_TIMEOUT", 20)),
            model_version=os.getenv("EGX_MODEL_VERSION", "xgboost-v1").strip(),
            universe=load_universe_config(Path(universe_path) if universe_path else DEFAULT_UNIVERSE_CONFIG),
            yahoo_enabled=_get_bool("EGX_YAHOO_ENABLED", True),
            yahoo_universe_url=(
                os.getenv("EGX_YAHOO_UNIVERSE_URL", "").strip() or DEFAULT_EGID_UNIVERSE_URL
            ),
            yahoo_range=os.getenv("EGX_YAHOO_RANGE", "2y").strip() or "2y",
            yahoo_hosts=tuple(
                part.strip()
                for part in (os.getenv("EGX_YAHOO_HOSTS", "").strip() or DEFAULT_YAHOO_HOSTS).split(",")
                if part.strip()
            ),
            borsa_enabled=_get_bool("EGX_BORSA_ENABLED", True),
            borsa_base_url=(
                os.getenv("EGX_BORSA_BASE_URL", "").strip() or DEFAULT_BORSA_BASE_URL
            ),
            borsa_api_key=os.getenv("EGX_BORSA_API_KEY", "").strip(),
            egid_enabled=_get_bool("EGID_ENABLED", True),
            egid_base_url=os.getenv("EGID_BASE_URL", "").strip() or DEFAULT_EGID_BASE_URL,
            egid_username=os.getenv("EGID_USERNAME", "").strip(),
            egid_password=os.getenv("EGID_PASSWORD", ""),
            egid_delay_seconds=max(0, _get_int("EGID_DELAY_SECONDS", 900)),
            egid_public_enabled=_get_bool("EGID_PUBLIC_ENABLED", True),
            egid_public_ticker_url=(
                os.getenv("EGID_PUBLIC_TICKER_URL", "").strip()
                or DEFAULT_EGID_PUBLIC_TICKER_URL
            ),
            egid_public_delay_seconds=max(0, _get_int("EGID_PUBLIC_DELAY_SECONDS", 900)),
            tradingview_enabled=_get_bool("EGX_TRADINGVIEW_ENABLED", True),
            tradingview_scanner_url=(
                os.getenv("EGX_TRADINGVIEW_SCANNER_URL", "").strip()
                or DEFAULT_TRADINGVIEW_SCANNER_URL
            ),
            tradingview_delay_seconds=max(0, _get_int("EGX_TRADINGVIEW_DELAY_SECONDS", 900)),
            tradingview_chunk_size=max(1, min(200, _get_int("EGX_TRADINGVIEW_CHUNK_SIZE", 100))),
            yahoo_quote_enabled=_get_bool("EGX_YAHOO_QUOTE_ENABLED", True),
            yahoo_quote_delay_seconds=max(
                0.0,
                _get_float("EGX_YAHOO_QUOTE_DELAY_SECONDS", 1.0),
            ),
            signals=signals,
        )

    def provider(self, prefix: str) -> ProviderConfig:
        return ProviderConfig(
            prefix=prefix,
            api_key=os.getenv(f"{prefix}_API_KEY", "").strip(),
            universe_url=os.getenv(f"{prefix}_UNIVERSE_URL", "").strip(),
            history_url=os.getenv(f"{prefix}_HISTORY_URL", "").strip(),
            auth_header=os.getenv(f"{prefix}_AUTH_HEADER", "").strip(),
            extra_headers=_parse_headers(os.getenv(f"{prefix}_EXTRA_HEADERS", "")),
        )
