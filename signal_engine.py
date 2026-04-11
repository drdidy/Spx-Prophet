"""
SPX PROPHET — Signal Engine
Detects rejection entries, breakout continuations,
and computes the Session Quality Score.
"""

import datetime as dt
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

import pandas as pd
import pytz
import numpy as np

from config import (
    SLOPE, STOP_POINTS, BREAKEVEN_TRIGGER, DAILY_LOSS_LIMIT,
    POSITION_SIZE_ES, POINT_VALUE_ES,
    REENTRY_LIMIT_EARLY, REENTRY_LIMIT_LATE, REENTRY_EARLY_END,
    VIX_REGIME, SESSION_QUALITY_WEIGHTS, CONFLUENCE_BONUS_WEIGHT,
    TIMEZONE,
)
from line_calculator import LineValue, ConfluenceZone, find_nearest_target

CT = pytz.timezone(TIMEZONE)


# ─── Data Classes ─────────────────────────────────────────────────────

@dataclass
class Signal:
    direction: str           # "LONG", "SHORT", "NEUTRAL"
    entry_line: str          # which line triggered
    entry_price: float       # entry price
    target_line: Optional[str] = None
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    risk_pts: float = 0.0
    reward_pts: float = 0.0
    rr_ratio: float = 0.0
    potential_dollars: float = 0.0
    confluence_boost: bool = False
    session_quality: float = 0.0
    signal_strength: str = "STANDARD"  # "STANDARD", "HIGH", "PREMIUM"


@dataclass
class SessionQuality:
    score: float             # 0–100
    grade: str               # A, B, C, D, F
    vix_component: float
    range_component: float
    gap_component: float
    time_component: float
    pivot_component: float
    confluence_component: float
    recommendation: str      # "FULL SIZE", "HALF SIZE", "PAPER ONLY", "SIT OUT"


# ─── Rejection Detection ─────────────────────────────────────────────

def detect_rejection(
    candle: pd.Series,
    line_value: float,
    tolerance: float = 2.0,
) -> Optional[str]:
    """
    Check if an hourly candle rejected at a line level.
    Returns "long" or "short" if rejection detected, None otherwise.

    Rejection = price wicked through the line but closed back.
    """
    high = candle["High"]
    low = candle["Low"]
    close = candle["Close"]
    open_p = candle["Open"]

    # Price hit line from below, rejected down → SHORT signal
    if high >= line_value - tolerance and close < line_value:
        wick_above = high - max(open_p, close)
        body = abs(close - open_p)
        if body > 0 and wick_above / body > 0.5:
            return "short"

    # Price hit line from above, rejected up → LONG signal
    if low <= line_value + tolerance and close > line_value:
        wick_below = min(open_p, close) - low
        body = abs(close - open_p)
        if body > 0 and wick_below / body > 0.5:
            return "long"

    return None


def scan_for_signals(
    candles: pd.DataFrame,
    lines: List[LineValue],
    confluence_zones: List[ConfluenceZone],
) -> List[Tuple[pd.Timestamp, Signal]]:
    """
    Scan hourly candles for rejection signals at any of the 6 lines.
    Returns list of (time, Signal) tuples.
    """
    signals = []

    for i in range(1, len(candles)):
        candle = candles.iloc[i - 1]  # The rejection candle
        entry_time = candles.index[i]  # Entry on NEXT candle open

        for line in lines:
            rejection = detect_rejection(candle, line.price)
            if rejection is None:
                continue

            entry_price = candles.iloc[i]["Open"]

            # Stop loss
            if rejection == "short":
                stop = candle["High"] + STOP_POINTS
            else:
                stop = candle["Low"] - STOP_POINTS

            # Target
            target = find_nearest_target(
                lines, line.name, entry_price, rejection
            )

            risk = abs(entry_price - stop)
            reward = abs(target.price - entry_price) if target else 0
            rr = reward / risk if risk > 0 else 0

            # Confluence check
            in_confluence = any(
                abs(line.price - cz.price_center) < 3.0
                for cz in confluence_zones
            )

            strength = "STANDARD"
            if in_confluence and rr >= 2.0:
                strength = "PREMIUM"
            elif in_confluence or rr >= 1.5:
                strength = "HIGH"

            sig = Signal(
                direction=rejection.upper(),
                entry_line=line.label,
                entry_price=round(entry_price, 2),
                target_line=target.label if target else None,
                target_price=round(target.price, 2) if target else None,
                stop_price=round(stop, 2),
                risk_pts=round(risk, 2),
                reward_pts=round(reward, 2),
                rr_ratio=round(rr, 2),
                potential_dollars=round(
                    reward * POINT_VALUE_ES * POSITION_SIZE_ES, 2
                ),
                confluence_boost=in_confluence,
                signal_strength=strength,
            )
            signals.append((entry_time, sig))

    return signals


# ─── Session Quality Score (NEW — PROFITABILITY FEATURE) ──────────────

def compute_session_quality(
    vix: float,
    candles: pd.DataFrame,
    pivots_confirmed: int,  # 0, 1, or 2
    num_confluence_zones: int,
    trade_date: dt.date,
) -> SessionQuality:
    """
    Composite score (0–100) rating how tradeable today's session looks.
    Factors: VIX regime, prior-day range, overnight gap, day-of-week,
    pivot clarity, and line confluence.
    """
    w = SESSION_QUALITY_WEIGHTS

    # 1. VIX component (best in 14–20 range)
    if VIX_REGIME["low"] <= vix <= VIX_REGIME["normal"]:
        vix_score = 100
    elif vix < VIX_REGIME["low"]:
        vix_score = max(40, 100 - (VIX_REGIME["low"] - vix) * 5)
    elif vix <= VIX_REGIME["elevated"]:
        vix_score = max(20, 100 - (vix - VIX_REGIME["normal"]) * 8)
    else:
        vix_score = 10

    # 2. Range component (prior day's range percentile)
    if len(candles) >= 7:
        daily_ranges = candles["High"] - candles["Low"]
        avg_range = daily_ranges.mean()
        range_score = min(100, avg_range * 8)  # scale to ~100
    else:
        range_score = 50

    # 3. Gap component (smaller gaps = more predictable)
    if len(candles) >= 2:
        gap = abs(candles.iloc[-1]["Open"] - candles.iloc[-2]["Close"])
        gap_score = max(0, 100 - gap * 5)
    else:
        gap_score = 50

    # 4. Day-of-week (Tue-Thu best, Mon decent, Fri worst)
    dow = trade_date.weekday()
    dow_scores = {0: 70, 1: 90, 2: 100, 3: 90, 4: 50}
    time_score = dow_scores.get(dow, 50)

    # 5. Pivot clarity (both confirmed = best)
    pivot_score = pivots_confirmed * 50

    # 6. Confluence zones
    conf_score = min(100, num_confluence_zones * 40)

    # Weighted composite
    total = (
        vix_score * w["vix_regime"]
        + range_score * w["range_percentile"]
        + gap_score * w["gap_size"]
        + time_score * w["time_of_week"]
        + pivot_score * w["pivot_clarity"]
        + conf_score * w["line_convergence"]
    )

    # Grade
    if total >= 80:
        grade, rec = "A", "FULL SIZE"
    elif total >= 65:
        grade, rec = "B", "FULL SIZE"
    elif total >= 50:
        grade, rec = "C", "HALF SIZE"
    elif total >= 35:
        grade, rec = "D", "PAPER ONLY"
    else:
        grade, rec = "F", "SIT OUT"

    return SessionQuality(
        score=round(total, 1),
        grade=grade,
        vix_component=round(vix_score, 1),
        range_component=round(range_score, 1),
        gap_component=round(gap_score, 1),
        time_component=round(time_score, 1),
        pivot_component=round(pivot_score, 1),
        confluence_component=round(conf_score, 1),
        recommendation=rec,
    )


# ─── VIX Regime Labeler ──────────────────────────────────────────────

def get_vix_regime(vix: float) -> Tuple[str, str]:
    """Returns (regime_name, color_hex)."""
    if vix < VIX_REGIME["low"]:
        return "LOW VOL", "#00ff88"
    elif vix <= VIX_REGIME["normal"]:
        return "NORMAL", "#00d4ff"
    elif vix <= VIX_REGIME["elevated"]:
        return "ELEVATED", "#ff9500"
    else:
        return "EXTREME", "#ff0055"
