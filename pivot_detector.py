"""
SPX PROPHET — Pivot Detector (Channel Structure)

Detects the LAST pivot high and LAST pivot low in the 12–4 PM CT
afternoon session using a 3-candle close-based pattern:

  Pivot HIGH: close[i] > close[i-1] AND close[i] > close[i+1]   (strict)
  Pivot LOW:  close[i] < close[i-1] AND close[i] < close[i+1]   (strict)

At each pivot, searches among candles {i-1, i, i+1} to find the actual
GREEN (bullish) and RED (bearish) candles and extract their prices:

  At pivot HIGH:
    GREEN candle HIGH → descending channel ceiling anchor
    RED candle HIGH   → ascending channel ceiling anchor

  At pivot LOW:
    RED candle LOW    → ascending channel floor anchor
    GREEN candle LOW  → descending channel floor anchor

Wick lines:
  HW ascending  = highest HIGH of any bearish candle in full RTH (8:30 AM–4 PM CT)
  LW descending = lowest LOW  of any bullish candle in full RTH (8:30 AM–4 PM CT)
"""

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import pytz

from data_fetcher import get_afternoon_candles, get_extended_candles, get_rth_candles
from config import TIMEZONE

CT = pytz.timezone(TIMEZONE)


@dataclass
class Pivot:
    """
    Represents a detected pivot with both green and red candle anchors.

    For pivot HIGH:
      green_candle_price = HIGH of green candle near the peak
      red_candle_price   = HIGH of red candle near the peak
    For pivot LOW:
      green_candle_price = LOW of green candle near the trough
      red_candle_price   = LOW of red candle near the trough
    For wick pivots (HW/LW):
      price = the wick extreme; green/red fields unused
    """
    price: float                   # primary price (backward compat / display)
    time: pd.Timestamp             # pivot candle timestamp
    candle_idx: int
    kind: str                      # "upper", "lower", "extreme_high", "extreme_low"
    confirmed: bool = False
    invalidated: bool = False
    confirmation_candle: Optional[pd.Timestamp] = None

    # Channel anchor data — TWO prices per pivot
    green_candle_price: float = 0.0
    green_candle_time: Optional[pd.Timestamp] = None
    red_candle_price: float = 0.0
    red_candle_time: Optional[pd.Timestamp] = None


def _is_bullish(row: pd.Series) -> bool:
    return row["Close"] > row["Open"]


def _is_bearish(row: pd.Series) -> bool:
    return row["Close"] < row["Open"]


def _find_green_red_at_high(candles: pd.DataFrame, i: int):
    """
    At a pivot HIGH (index i), search among {i-1, i, i+1} for the
    actual GREEN (bullish) and RED (bearish) candles.

    Returns (green_high, green_time, red_high, red_time).

    - GREEN candle HIGH → descending channel ceiling anchor
    - RED candle HIGH   → ascending channel ceiling anchor

    Search priority: prefer the candle closest to the pivot center (i),
    then i+1, then i-1. If no candle of that color exists in the window,
    fall back to the pivot candle itself.
    """
    candidates = []
    if i > 0:
        candidates.append((i - 1, candles.iloc[i - 1], candles.index[i - 1]))
    candidates.append((i, candles.iloc[i], candles.index[i]))
    if i < len(candles) - 1:
        candidates.append((i + 1, candles.iloc[i + 1], candles.index[i + 1]))

    # Find the GREEN (bullish) candle — take the one closest to i
    green_row, green_time = None, None
    for idx, row, ts in candidates:
        if _is_bullish(row):
            green_row, green_time = row, ts
            break  # first match (i-1, i, or i+1 in order)

    # Find the RED (bearish) candle — search separately
    red_row, red_time = None, None
    for idx, row, ts in candidates:
        if _is_bearish(row):
            red_row, red_time = row, ts
            break

    # Fallbacks: if we can't find one color, use the pivot candle
    peak_row = candles.iloc[i]
    peak_time = candles.index[i]
    if green_row is None:
        green_row, green_time = peak_row, peak_time
    if red_row is None:
        red_row, red_time = peak_row, peak_time

    return green_row["High"], green_time, red_row["High"], red_time


def _find_green_red_at_low(candles: pd.DataFrame, i: int):
    """
    At a pivot LOW (index i), search among {i-1, i, i+1} for the
    actual GREEN (bullish) and RED (bearish) candles.

    Returns (red_low, red_time, green_low, green_time).

    - RED candle LOW    → ascending channel floor anchor
    - GREEN candle LOW  → descending channel floor anchor
    """
    candidates = []
    if i > 0:
        candidates.append((i - 1, candles.iloc[i - 1], candles.index[i - 1]))
    candidates.append((i, candles.iloc[i], candles.index[i]))
    if i < len(candles) - 1:
        candidates.append((i + 1, candles.iloc[i + 1], candles.index[i + 1]))

    # Find the RED (bearish) candle
    red_row, red_time = None, None
    for idx, row, ts in candidates:
        if _is_bearish(row):
            red_row, red_time = row, ts
            break

    # Find the GREEN (bullish) candle
    green_row, green_time = None, None
    for idx, row, ts in candidates:
        if _is_bullish(row):
            green_row, green_time = row, ts
            break

    # Fallbacks
    trough_row = candles.iloc[i]
    trough_time = candles.index[i]
    if red_row is None:
        red_row, red_time = trough_row, trough_time
    if green_row is None:
        green_row, green_time = trough_row, trough_time

    return red_row["Low"], red_time, green_row["Low"], green_time


def identify_upper_pivot(
    df: pd.DataFrame, trade_date: dt.date
) -> Optional[Pivot]:
    """
    Find the LAST pivot HIGH in the 12–4 PM CT afternoon session.

    Pattern (STRICT): close[i] > close[i-1] AND close[i] > close[i+1]

    The candle data includes 11 AM as context (for i-1 at 12 PM).
    Only pivots at 12 PM CT or later are accepted.

    At the pivot, searches {i-1, i, i+1} for:
      - green candle HIGH → descending channel ceiling anchor
      - red candle HIGH   → ascending channel ceiling anchor
    """
    afternoon = get_afternoon_candles(df, trade_date)
    if len(afternoon) < 3:
        afternoon = get_extended_candles(df, trade_date)
    if len(afternoon) < 3:
        return None

    # 12 PM CT cutoff — only accept pivots at or after this time
    pivot_window_start = CT.localize(
        dt.datetime.combine(
            afternoon.index[0].date(), dt.time(12, 0)
        )
    )

    # Scan backward for the LAST pivot HIGH (strict >)
    for i in range(len(afternoon) - 2, 0, -1):
        # Only accept pivots in the 12-4 PM window
        if afternoon.index[i] < pivot_window_start:
            continue

        close_prev = afternoon.iloc[i - 1]["Close"]
        close_curr = afternoon.iloc[i]["Close"]
        close_next = afternoon.iloc[i + 1]["Close"]

        if close_curr > close_prev and close_curr > close_next:
            green_high, green_time, red_high, red_time = \
                _find_green_red_at_high(afternoon, i)

            return Pivot(
                price=afternoon.iloc[i]["High"],
                time=afternoon.index[i],
                candle_idx=i,
                kind="upper",
                confirmed=True,
                green_candle_price=green_high,
                green_candle_time=green_time,
                red_candle_price=red_high,
                red_candle_time=red_time,
            )

    # Fallback — no strict pivot found in window
    # Use the candle with highest close in the 12-4 PM zone
    in_window = afternoon[afternoon.index >= pivot_window_start]
    if in_window.empty:
        return None

    idx = in_window["Close"].idxmax()
    i = afternoon.index.get_loc(idx)
    green_high, green_time, red_high, red_time = \
        _find_green_red_at_high(afternoon, i)

    return Pivot(
        price=afternoon.iloc[i]["High"],
        time=afternoon.index[i],
        candle_idx=i,
        kind="upper",
        confirmed=False,
        green_candle_price=green_high,
        green_candle_time=green_time,
        red_candle_price=red_high,
        red_candle_time=red_time,
    )


def identify_lower_pivot(
    df: pd.DataFrame, trade_date: dt.date
) -> Optional[Pivot]:
    """
    Find the LAST pivot LOW in the 12–4 PM CT afternoon session.

    Pattern (STRICT): close[i] < close[i-1] AND close[i] < close[i+1]

    At the pivot, searches {i-1, i, i+1} for:
      - red candle LOW   → ascending channel floor anchor
      - green candle LOW → descending channel floor anchor
    """
    afternoon = get_afternoon_candles(df, trade_date)
    if len(afternoon) < 3:
        afternoon = get_extended_candles(df, trade_date)
    if len(afternoon) < 3:
        return None

    pivot_window_start = CT.localize(
        dt.datetime.combine(
            afternoon.index[0].date(), dt.time(12, 0)
        )
    )

    # Scan backward for the LAST pivot LOW (strict <)
    for i in range(len(afternoon) - 2, 0, -1):
        if afternoon.index[i] < pivot_window_start:
            continue

        close_prev = afternoon.iloc[i - 1]["Close"]
        close_curr = afternoon.iloc[i]["Close"]
        close_next = afternoon.iloc[i + 1]["Close"]

        if close_curr < close_prev and close_curr < close_next:
            red_low, red_time, green_low, green_time = \
                _find_green_red_at_low(afternoon, i)

            return Pivot(
                price=afternoon.iloc[i]["Low"],
                time=afternoon.index[i],
                candle_idx=i,
                kind="lower",
                confirmed=True,
                green_candle_price=green_low,
                green_candle_time=green_time,
                red_candle_price=red_low,
                red_candle_time=red_time,
            )

    # Fallback — use lowest close candle in window
    in_window = afternoon[afternoon.index >= pivot_window_start]
    if in_window.empty:
        return None

    idx = in_window["Close"].idxmin()
    i = afternoon.index.get_loc(idx)
    red_low, red_time, green_low, green_time = \
        _find_green_red_at_low(afternoon, i)

    return Pivot(
        price=afternoon.iloc[i]["Low"],
        time=afternoon.index[i],
        candle_idx=i,
        kind="lower",
        confirmed=False,
        green_candle_price=green_low,
        green_candle_time=green_time,
        red_candle_price=red_low,
        red_candle_time=red_time,
    )


def identify_rth_high(
    df: pd.DataFrame, trade_date: dt.date
) -> Optional[Pivot]:
    """
    HW ascending wick line:
    Find the highest HIGH of any BEARISH candle in the full RTH session
    (8:30 AM – 4:00 PM CT). Only bearish candles qualify.
    """
    rth = get_rth_candles(df, trade_date)
    if rth.empty:
        return None

    bearish = rth[rth["Close"] < rth["Open"]]
    if bearish.empty:
        idx = rth["High"].idxmax()
        row = rth.loc[idx]
        return Pivot(
            price=row["High"],
            time=idx,
            candle_idx=rth.index.get_loc(idx),
            kind="extreme_high",
            confirmed=True,
        )

    idx = bearish["High"].idxmax()
    row = bearish.loc[idx]
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
    LW descending wick line:
    Find the lowest LOW of any BULLISH candle in the full RTH session
    (8:30 AM – 4:00 PM CT). Only bullish candles qualify.
    """
    rth = get_rth_candles(df, trade_date)
    if rth.empty:
        return None

    bullish = rth[rth["Close"] > rth["Open"]]
    if bullish.empty:
        idx = rth["Low"].idxmin()
        row = rth.loc[idx]
        return Pivot(
            price=row["Low"],
            time=idx,
            candle_idx=rth.index.get_loc(idx),
            kind="extreme_low",
            confirmed=True,
        )

    idx = bullish["Low"].idxmin()
    row = bullish.loc[idx]
    return Pivot(
        price=row["Low"],
        time=idx,
        candle_idx=rth.index.get_loc(idx),
        kind="extreme_low",
        confirmed=True,
    )
