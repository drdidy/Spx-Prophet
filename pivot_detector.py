"""
SPX PROPHET — Pivot Detector
Identifies valid upper (high) and lower (low) pivots
from the prior day's afternoon session.
"""

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from data_fetcher import get_afternoon_candles, get_extended_candles, get_rth_candles


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
    1. Search 12–4 PM CT prior day for swing high
    2. Must be a BULLISH (green) candle that makes a swing high
    3. A BEARISH candle wick must also touch this level (confirmation)
    4. The pivot price and time come from the CONFIRMING bearish candle's
       HIGH WICK — that's the level tested from both sides.
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
        conf_idx = None
        for j in range(len(afternoon)):
            if j == i:
                continue
            other = afternoon.iloc[j]
            if _is_bearish(other) and other["High"] >= high_price * 0.9998:
                confirmed = True
                conf_idx = j
                break

        if not confirmed:
            continue

        # Check invalidation: any candle after the LATER of the two CLOSING above
        last_idx = max(i, conf_idx)
        invalidated = False
        for j in range(last_idx + 1, len(afternoon)):
            if afternoon.iloc[j]["Close"] > high_price:
                invalidated = True
                break

        if not invalidated:
            # Use the CONFIRMING bearish candle's high wick and timestamp
            conf_candle = afternoon.iloc[conf_idx]
            candidates.append(Pivot(
                price=conf_candle["High"],
                time=afternoon.index[conf_idx],
                candle_idx=conf_idx,
                kind="upper",
                confirmed=True,
                invalidated=False,
                confirmation_candle=afternoon.index[conf_idx],
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
    1. Search 12–4 PM CT prior day for swing low
    2. Must be a BEARISH (red) candle that makes a swing low
    3. A BULLISH candle wick must also touch this level (confirmation)
    4. The pivot price and time come from the CONFIRMING bullish candle's
       LOW WICK — that's the level tested from both sides.
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
        conf_idx = None
        for j in range(len(afternoon)):
            if j == i:
                continue
            other = afternoon.iloc[j]
            if _is_bullish(other) and other["Low"] <= low_price * 1.0002:
                confirmed = True
                conf_idx = j
                break

        if not confirmed:
            continue

        # Invalidation check: any candle after the LATER of the two CLOSING below
        last_idx = max(i, conf_idx)
        invalidated = False
        for j in range(last_idx + 1, len(afternoon)):
            if afternoon.iloc[j]["Close"] < low_price:
                invalidated = True
                break

        if not invalidated:
            # Use the CONFIRMING bullish candle's low wick and timestamp
            conf_candle = afternoon.iloc[conf_idx]
            candidates.append(Pivot(
                price=conf_candle["Low"],
                time=afternoon.index[conf_idx],
                candle_idx=conf_idx,
                kind="lower",
                confirmed=True,
                invalidated=False,
                confirmation_candle=afternoon.index[conf_idx],
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


def identify_rth_high(
    df: pd.DataFrame, trade_date: dt.date
) -> Optional[Pivot]:
    """
    Find the absolute HIGHEST wick of the entire prior day RTH session
    (8:30 AM to 3:00 PM CT). No confirmation needed — just the highest High.
    Used for Extreme Descending line (Line 6).
    """
    rth = get_rth_candles(df, trade_date)
    if rth.empty:
        return None

    idx = rth["High"].idxmax()
    row = rth.loc[idx]
    return Pivot(
        price=row["High"],
        time=idx,
        candle_idx=rth.index.get_loc(idx),
        kind="extreme_high",
        confirmed=True,
    )


def identify_rth_low(
    df: pd.DataFrame, trade_date: dt.date
) -> Optional[Pivot]:
    """
    Find the absolute LOWEST wick of the entire prior day RTH session
    (8:30 AM to 3:00 PM CT). No confirmation needed — just the lowest Low.
    Used for Extreme Ascending line (Line 5).
    """
    rth = get_rth_candles(df, trade_date)
    if rth.empty:
        return None

    idx = rth["Low"].idxmin()
    row = rth.loc[idx]
    return Pivot(
        price=row["Low"],
        time=idx,
        candle_idx=rth.index.get_loc(idx),
        kind="extreme_low",
        confirmed=True,
    )
