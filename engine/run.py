from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

try:  # optional, useful for local runs
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from .aggregator import aggregate_bars, collect
from .config import Config
from .evaluate import evaluate_outcomes
from .features import FEATURE_COLUMNS, build_features
from .model import predict_probability, train_model
from .repository import SupabaseRepository
from .risk import TradePlan, build_plan

LOG = logging.getLogger("egx.run")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(config: Config, repo: SupabaseRepository) -> int:
    created = repo.insert(
        "analysis_runs",
        [
            {
                "started_at": _now(),
                "status": "running",
                "model_version": config.model_version,
                "notes": f"horizon={config.horizon_days}; top_n={config.top_n}",
            }
        ],
    )
    run_id = created[0]["id"]

    try:
        collected = collect(config)
        LOG.info("Collected %d symbol(s) from: %s", len(collected.universe), ", ".join(collected.source_rows))
        for source, error in collected.source_errors.items():
            LOG.warning("Source %s: %s", source, error)

        status_at = _now()
        repo.upsert(
            "data_source_status",
            [
                {
                    "source": source,
                    "last_success_at": status_at if row_count > 0 else None,
                    "last_error": collected.source_errors.get(source),
                    "rows_written": row_count,
                    "updated_at": status_at,
                }
                for source, row_count in collected.source_rows.items()
            ],
            "source",
        )

        repo.upsert(
            "stocks",
            [
                {
                    "symbol": entry.symbol,
                    "name": entry.name,
                    "sector": entry.sector,
                    "is_active": True,
                    "updated_at": _now(),
                }
                for entry in collected.universe.values()
            ],
            "symbol",
        )

        for source, by_symbol in collected.raw_bars.items():
            rows = [
                {
                    "symbol": symbol,
                    "trade_date": bar.trade_date.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "source": source,
                    "adjusted": False,
                    "updated_at": _now(),
                }
                for symbol, bars in by_symbol.items()
                for bar in bars
            ]
            repo.upsert("price_bars", rows, "symbol,trade_date,source")

        aggregated_frames = aggregate_bars(collected.raw_bars)
        if not aggregated_frames:
            raise RuntimeError("No price bars were collected")

        merged_rows = [
            {
                "symbol": symbol,
                "trade_date": row["trade_date"].date().isoformat(),
                "open": round(float(row["open"]), 4),
                "high": round(float(row["high"]), 4),
                "low": round(float(row["low"]), 4),
                "close": round(float(row["close"]), 4),
                "volume": int(row["volume"]),
                "source": "aggregated",
                "adjusted": False,
                "updated_at": _now(),
            }
            for symbol, frame in aggregated_frames.items()
            for _, row in frame.iterrows()
        ]
        repo.upsert("price_bars", merged_rows, "symbol,trade_date,source")

        feature_frames = {symbol: build_features(frame) for symbol, frame in aggregated_frames.items()}
        as_of = max(frame["trade_date"].max() for frame in feature_frames.values()).date().isoformat()

        model = train_model(feature_frames, config)
        LOG.info(
            "Model %s trained on %d rows (validation accuracy: %s)",
            model.version,
            model.train_rows,
            "n/a" if model.validation_accuracy is None else f"{model.validation_accuracy:.3f}",
        )

        ranked: list[tuple[TradePlan, str]] = []
        for symbol, frame in feature_frames.items():
            if frame.empty:
                continue
            latest = frame.iloc[-1]
            values = {name: float(latest[name]) for name in FEATURE_COLUMNS}
            probability = predict_probability(model.estimator, values)
            atr = float(latest["atr"])
            if not math.isfinite(atr) or atr <= 0:
                atr = float(latest["close"]) * 0.01
            plan = build_plan(probability, values, float(latest["close"]), atr, config)
            ranked.append((plan, symbol))

        ranked.sort(key=lambda item: item[0].score, reverse=True)
        top = ranked[: config.top_n]

        repo.insert(
            "recommendations",
            [
                {
                    "run_id": run_id,
                    "symbol": symbol,
                    "as_of": as_of,
                    "horizon_days": config.horizon_days,
                    "entry_price": plan.entry_price,
                    "target_price": plan.target_price,
                    "stop_loss": plan.stop_loss,
                    "upside_pct": plan.upside_pct,
                    "risk_pct": plan.risk_pct,
                    "reward_risk": plan.reward_risk,
                    "score": plan.score,
                    "confidence": plan.confidence,
                    "signal": plan.signal,
                    "sources": sorted(set(collected.sources_by_symbol.get(symbol, []) + ["aggregated"])),
                    "created_at": _now(),
                }
                for plan, symbol in top
            ],
        )

        evaluated = evaluate_outcomes(repo, config)
        repo.update(
            "analysis_runs",
            {
                "status": "success",
                "finished_at": _now(),
                "universe_size": len(feature_frames),
                "notes": f"model={model.version}; validation_accuracy={model.validation_accuracy}; outcomes={evaluated}",
            },
            {"id": f"eq.{run_id}"},
        )
        LOG.info("Run complete: as_of=%s, recommendations=%d", as_of, len(top))
        return 0

    except Exception as exc:
        LOG.exception("Analysis run failed")
        try:
            repo.update(
                "analysis_runs",
                {"status": "failed", "finished_at": _now(), "notes": str(exc)[:500]},
                {"id": f"eq.{run_id}"},
            )
        except Exception:
            LOG.exception("Could not mark the run as failed")
        return 1


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.from_env()
    if not config.supabase_url or not config.service_role_key:
        LOG.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        return 2
    repo = SupabaseRepository(config.supabase_url, config.service_role_key, config.request_timeout)
    return _run(config, repo)


if __name__ == "__main__":
    raise SystemExit(main())
