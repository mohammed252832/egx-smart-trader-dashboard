from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

CAIRO_TZ = ZoneInfo("Africa/Cairo")


def is_quote_market_time(value: datetime) -> bool:
    cairo = value.astimezone(CAIRO_TZ)
    return cairo.weekday() in {6, 0, 1, 2, 3} and time(10, 0) <= cairo.time() <= time(15, 0)
