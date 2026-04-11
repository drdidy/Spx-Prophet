"""
SPX PROPHET — Pivot Detector
Identifies valid upper (high) and lower (low) pivots
from the prior day's afternoon session.
"""

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from data_fetcher import get_afternoon_candles, get_extended_candles


@dataclass
class Pivot:
    price: float
    time: pd.Timestamp
    candle_idx: int
    kind: str  # "upper" or "lower"
    confirmed: bool = False
    invalidated: bool = False
    confirmation_candle: Optional[pd.Timestamp] = None


def _is_bullish(row: pd.Series) -> bool:
    return row["Close"] >= row["Open"]


def _is_bearish(row: pd.Series) -> bool:
    return row["Close"] < row["Open"]


def identify_upper_pivot(
    df: pd.DataFrame, trade_date: dt.date
) -> Optional[Pivot]:
    """
    Find valid HIGH pivot:
    1. Search 12–3 PM CT prior day for swing high
    2. Must be a BULLISH (green) candle
    3. A BEARISH candle wick must also touch this level (confirmation)
    4. Use UPPER WICK price
    5. Wick-through = valid; close-above = invalidated
    """
    afternoon = get_afternoon_candles(df, trade_date)
    if afternoon.empty:
        afternoon = get_extended_candles(df, trade_date)
    if afternoon.empty:
        return None

    # Find swing highs — iterate from most recent
    candidates = []
    for i in range(len(afternoon) - 1, -1, -1):
        row = afternoon.iloc[i]
        if not _is_bullish(row):
            continue

        high_price = row["High"]

        # Check confirmation: a bearish candle wick touching this level
        confirmed = False
        conf_time = None
        for j in range(len(afternoon)):
            if j == i:
                continue
            other = afternoon.iloc[j]
            if _is_bearish(other) and other["High"] >= high_price * 0.9998:
                confirmed = True
                conf_time = afternoon.index[j]
                break

        if not confirmed:
            continue

        # Check invalidation: any subsequent candle CLOSING above
        invalidated = False
        for j in range(i + 1, len(afternoon)):
            if afternoon.iloc[j]["Close"] > high_price:
                invalidated = True
                break

        if not invalidated:
            candidates.append(Pivot(
                price=high_price,
                time=afternoon.index[i],
                candle_idx=i,
                kind="upper",
                confirmed=True,
                invalidated=False,
                confirmation_candle=conf_time,
            ))

    # Return most recent valid
    if candidates:
        return candidates[0]

    # Extended search fallback — relaxed confirmation
    extended = get_extended_candles(df, trade_date)
    if extended.empty:
        return None

    for i in range(len(extended) - 1, -1, -1):
        row = extended.iloc[i]
        if _is_bullish(row):
            return Pivot(
                price=row["High"],
                time=extended.index[i],
                candle_idx=i,
                kind="upper",
                confirmed=False,
                invalidated=False,
            )
    return None


def identify_lower_pivot(
    df: pd.DataFrame, trade_date: dt.date
) -> Optional[Pivot]:
    """
    Find valid LOW pivot:
    1. Search 12–3 PM CT prior day for swing low
    2. Must be a BEARISH (red) candle
    3. A BULLISH candle wick must also touch this level (confirmation)
    4. Use LOWER WICK price
    5. Wick-through = valid; close-below = invalidated
    """
    afternoon = get_afternoon_candles(df, trade_date)
    if afternoon.empty:
        afternoon = get_extended_candles(df, trade_date)
    if afternoon.empty:
        return None

    candidates = []
    for i in range(len(afternoon) - 1, -1, -1):
        row = afternoon.iloc[i]
        if not _is_bearish(row):
            continue

        low_price = row["Low"]

        # Confirmation: bullish candle wick touching this level
        confirmed = False
        conf_time = None
        for j in range(len(afternoon)):
            if j == i:
                continue
            other = afternoon.iloc[j]
            if _is_bullish(other) and other["Low"] <= low_price * 1.0002:
                confirmed = True
                conf_time = afternoon.index[j]
                break

        if not confirmed:
            continue

        # Invalidation check
        invalidated = False
        for j in range(i + 1, len(afternoon)):
            if afternoon.iloc[j]["Close"] < low_price:
                invalidated = True
                break

        if not invalidated:
            candidates.append(Pivot(
                price=low_price,
                time=afternoon.index[i],
                candle_idx=i,
                kind="lower",
                confirmed=True,
                invalidated=False,
                confirmation_candle=conf_time,
            ))

    if candidates:
        return candidates[0]

    # Extended search fallback
    extended = get_extended_candles(df, trade_date)
    if extended.empty:
        return None

    for i in range(len(extended) - 1, -1, -1):
        row = extended.iloc[i]
        if _is_bearish(row):
            return Pivot(
                price=row["Low"],
                time=extended.index[i],
                candle_idx=i,
                kind="lower",
                confirmed=False,
                invalidated=False,
            )
    return None
