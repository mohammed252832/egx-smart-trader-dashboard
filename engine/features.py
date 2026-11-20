from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "ret_1",
    "ret_3",
    "ret_5",
    "ret_10",
    "sma_ratio_5",
    "sma_ratio_20",
    "sma_ratio_50",
    "ema_ratio_12",
    "ema_ratio_26",
    "macd_ratio",
    "macd_hist_ratio",
    "rsi_14",
    "atr",
    "atr_pct",
    "bb_position",
    "volume_ratio",
    "range_position",
    "volatility_10",
    "trend_slope_20",
]


def build_features(price_frame: pd.DataFrame) -> pd.DataFrame:
    """Technical features from one aggregated OHLCV frame."""
    frame = price_frame.copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"])
    frame = frame.sort_values("trade_date").reset_index(drop=True)

    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    volume = frame["volume"].astype(float)

    for period in (1, 3, 5, 10):
        frame[f"ret_{period}"] = close.pct_change(period)

    sma5 = close.rolling(5, min_periods=5).mean()
    sma20 = close.rolling(20, min_periods=20).mean()
    sma50 = close.rolling(50, min_periods=50).mean()
    frame["sma_ratio_5"] = close / sma5 - 1
    frame["sma_ratio_20"] = close / sma20 - 1
    frame["sma_ratio_50"] = close / sma50 - 1

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    frame["ema_ratio_12"] = ema12 / close - 1
    frame["ema_ratio_26"] = ema26 / close - 1
    frame["macd_ratio"] = macd / close
    frame["macd_hist_ratio"] = (macd - macd_signal) / close

    delta = close.diff()
    avg_gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    avg_loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rsi = 100 - 100 / (1 + avg_gain / avg_loss.replace(0, 1e-9))
    frame["rsi_14"] = rsi

    previous_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1
    ).max(axis=1)
    atr = true_range.rolling(14, min_periods=14).mean()
    frame["atr"] = atr
    frame["atr_pct"] = atr / close

    middle_band = close.rolling(20, min_periods=20).mean()
    band_width = 2 * close.rolling(20, min_periods=20).std()
    frame["bb_position"] = (close - (middle_band - band_width)) / band_width.replace(0, np.nan)

    volume_sma = volume.rolling(20, min_periods=20).mean()
    frame["volume_ratio"] = volume / volume_sma.replace(0, np.nan)

    low20 = low.rolling(20, min_periods=20).min()
    high20 = high.rolling(20, min_periods=20).max()
    frame["range_position"] = (close - low20) / (high20 - low20).replace(0, np.nan)

    daily_return = close.pct_change()
    frame["volatility_10"] = daily_return.rolling(10, min_periods=10).std()
    frame["trend_slope_20"] = (sma20 - sma20.shift(5)) / sma20.shift(5)

    frame[FEATURE_COLUMNS] = frame[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return frame
