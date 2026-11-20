from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .config import Config
from .providers import Bar, CsvProvider, HttpProvider, Provider, SampleProvider, UniverseEntry


@dataclass
class Collected:
    universe: dict[str, UniverseEntry] = field(default_factory=dict)
    raw_bars: dict[str, dict[str, list[Bar]]] = field(default_factory=dict)
    source_rows: dict[str, int] = field(default_factory=dict)
    source_errors: dict[str, str] = field(default_factory=dict)
    sources_by_symbol: dict[str, list[str]] = field(default_factory=dict)


def _providers(config: Config) -> list[Provider]:
    providers: list[Provider] = []
    for prefix in config.provider_prefixes:
        provider_config = config.provider(prefix)
        if provider_config.enabled:
            providers.append(HttpProvider(provider_config, config.request_timeout))

    csv_provider = CsvProvider.from_env()
    if csv_provider.enabled:
        providers.append(csv_provider)

    # Sample data is the safety net: it also fills symbols discovered by other sources.
    if config.use_sample:
        providers.append(SampleProvider(config.history_days))
    if not providers:
        raise RuntimeError("No data provider configured: set EGX_USE_SAMPLE=true or provider URL templates")
    return providers


def collect(config: Config) -> Collected:
    """Fetch universe + history from every configured provider."""
    providers = _providers(config)
    collected = Collected()

    provider_universes: dict[str, list[UniverseEntry]] = {}
    for provider in providers:
        try:
            entries = provider.fetch_universe()
        except Exception as exc:
            entries = []
            provider.last_error = f"universe: {exc}"
        provider_universes[provider.name] = entries
        for entry in entries:
            collected.universe.setdefault(entry.symbol, entry)

    symbols = sorted(collected.universe)
    if not symbols:
        raise RuntimeError("No symbols returned by any data provider")

    for provider in providers:
        by_symbol: dict[str, list[Bar]] = {}
        for symbol in symbols:
            try:
                bars = provider.fetch_history(symbol, config.history_days)
            except Exception as exc:
                provider.last_error = f"history[{symbol}]: {exc}"
                bars = []
            if bars:
                by_symbol[symbol] = bars
                collected.sources_by_symbol.setdefault(symbol, []).append(provider.name)

        collected.raw_bars[provider.name] = by_symbol
        collected.source_rows[provider.name] = sum(len(bars) for bars in by_symbol.values())
        if provider.last_error:
            collected.source_errors[provider.name] = provider.last_error
        elif collected.source_rows[provider.name] == 0:
            collected.source_errors[provider.name] = "no rows returned"

    for prefix in config.provider_prefixes:
        name = prefix.lower()
        if name not in collected.source_rows:
            collected.source_rows[name] = 0
            collected.source_errors[name] = "not configured"

    return collected


def aggregate_bars(raw_bars: dict[str, dict[str, list[Bar]]]) -> dict[str, pd.DataFrame]:
    """Median close, max high, min low across sources for each trading day."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for source, by_symbol in raw_bars.items():
        for symbol, bars in by_symbol.items():
            bucket = grouped.setdefault(symbol, [])
            for bar in bars:
                bucket.append(
                    {
                        "trade_date": bar.trade_date,
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "volume": float(bar.volume),
                        "source": source,
                    }
                )

    frames: dict[str, pd.DataFrame] = {}
    for symbol, rows in grouped.items():
        frame = pd.DataFrame(rows)
        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        aggregated = (
            frame.groupby("trade_date", as_index=False)
            .agg(
                open=("open", "first"),
                high=("high", "max"),
                low=("low", "min"),
                close=("close", "median"),
                volume=("volume", "sum"),
            )
            .sort_values("trade_date")
            .reset_index(drop=True)
        )
        aggregated["symbol"] = symbol
        frames[symbol] = aggregated
    return frames
