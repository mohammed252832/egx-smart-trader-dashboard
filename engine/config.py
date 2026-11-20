from __future__ import annotations

import os
from dataclasses import dataclass


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ProviderConfig:
    prefix: str
    api_key: str = ""
    universe_url: str = ""
    history_url: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.universe_url and self.history_url)


@dataclass(frozen=True)
class Config:
    supabase_url: str
    service_role_key: str
    history_days: int
    horizon_days: int
    top_n: int
    target_pct: float
    stop_atr: float
    target_atr: float
    max_stop_pct: float
    use_sample: bool
    provider_prefixes: tuple[str, ...]
    request_timeout: int
    model_version: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            supabase_url=os.getenv("SUPABASE_URL", "").strip(),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
            history_days=max(120, _get_int("EGX_HISTORY_DAYS", 400)),
            horizon_days=max(1, _get_int("EGX_HORIZON_DAYS", 3)),
            top_n=max(1, _get_int("EGX_TOP_N", 10)),
            target_pct=_get_float("EGX_TARGET_PCT", 2.0),
            stop_atr=_get_float("EGX_STOP_ATR", 1.4),
            target_atr=_get_float("EGX_TARGET_ATR", 2.4),
            max_stop_pct=_get_float("EGX_MAX_STOP_PCT", 8.0),
            use_sample=_get_bool("EGX_USE_SAMPLE", True),
            provider_prefixes=tuple(
                part.strip()
                for part in os.getenv("EGX_PROVIDERS", "DATACEDAR,EGID,BORSA,EGX").split(",")
                if part.strip()
            ),
            request_timeout=_get_int("EGX_REQUEST_TIMEOUT", 20),
            model_version=os.getenv("EGX_MODEL_VERSION", "xgboost-v1").strip(),
        )

    def provider(self, prefix: str) -> ProviderConfig:
        return ProviderConfig(
            prefix=prefix,
            api_key=os.getenv(f"{prefix}_API_KEY", "").strip(),
            universe_url=os.getenv(f"{prefix}_UNIVERSE_URL", "").strip(),
            history_url=os.getenv(f"{prefix}_HISTORY_URL", "").strip(),
        )
