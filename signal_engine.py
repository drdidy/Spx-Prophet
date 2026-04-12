"""
SPX PROPHET — Signal Engine
Detects rejection entries at dynamically-computed line levels.
Lines have SLOPE so their value changes every hour — we recalculate
per candle, not once for the whole session.

Trading window: overnight session through 12:00 PM CT (no entries after noon).
"""

import datetime as dt
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

import pandas as pd
import pytz
import numpy as np

from config import (
    SLOPE, CHANNEL_SLOPE, STOP_POINTS, BREAKEVEN_TRIGGER, DAILY_LOSS_LIMIT,
    POSITION_SIZE_ES, POINT_VALUE_ES,
    REENTRY_LIMIT_EARLY, REENTRY_LIMIT_LATE, REENTRY_EARLY_END,
    TRADING_END,
    VIX_REGIME, SESSION_QUALITY_WEIGHTS, CONFLUENCE_BONUS_WEIGHT,
    TIMEZONE,
)
from line_calculator import (
    LineValue, ConfluenceZone, find_nearest_target,
    calculate_line_value, hours_between, get_all_six_lines,
    detect_confluence_zones,
)
from pivot_detector import Pivot

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
    line_direction: str,
    tolerance: float = 1.5,
) -> bool:
    """
    Check if an hourly candle touched/interacted with a line level.

    The candle's range (low to high) must reach the line within tolerance.
    Direction is NOT determined here — it's determined by where the
    next candle opens relative to the line.

    A candle that wicks down to DC and closes above it is still a
    valid touch (the entry direction will be LONG since it opens above).
    """
    high = candle["High"]
    low = candle["Low"]
    candle_range = high - low

    # Minimum candle range to avoid doji noise
    if candle_range < 0.5:
        return False

    # Did the candle's range reach the line level?
    if low <= line_value + tolerance and high >= line_value - tolerance:
        return True

    return False


# ─── Line value computation at a specific time ───────────────────────

def _compute_lines_at_time(
    upper_pivot: Optional[Pivot],
    lower_pivot: Optional[Pivot],
    rth_high: Optional[Pivot],
    rth_low: Optional[Pivot],
    at_time: pd.Timestamp,
) -> List[LineValue]:
    """
    Compute all 6 line values at a specific timestamp.
    This is the same as get_all_six_lines but called per-candle
    so each signal checks against the correct line price at that hour.
    """
    return get_all_six_lines(upper_pivot, lower_pivot, rth_high, rth_low, at_time)


# ─── Main Signal Scanner ─────────────────────────────────────────────

def scan_for_signals(
    candles: pd.DataFrame,
    upper_pivot: Optional[Pivot],
    lower_pivot: Optional[Pivot],
    rth_high: Optional[Pivot],
    rth_low: Optional[Pivot],
    trade_date: dt.date,
) -> List[Tuple[pd.Timestamp, Signal]]:
    """
    Scan hourly candles for rejection signals at the 6 lines.
    Returns list of (time, Signal) tuples.

    KEY: Line values are RECALCULATED at each candle's timestamp
    because lines have slope — their price changes every hour.

    Entries are only generated before 12:00 PM CT (TRADING_END).
    Direction is determined by line type: ascending→LONG, descending→SHORT.
    Deduplicates overlapping lines (e.g., AC and HW at same price).
    """
    signals = []

    # Absolute time bounds: prior day 5 PM CT → trade date 12 PM CT (noon)
    from data_fetcher import get_prior_trading_day
    prior_day = get_prior_trading_day(trade_date)
    entries_start = CT.localize(dt.datetime.combine(prior_day, dt.time(17, 0)))
    entries_end = CT.localize(dt.datetime.combine(trade_date, dt.time(TRADING_END, 0)))

    for i in range(1, len(candles)):
        candle = candles.iloc[i - 1]  # The rejection candle
        candle_time = candles.index[i - 1]
        entry_time = candles.index[i]  # Entry on NEXT candle open

        # ── Time filter: only allow entries within [prior 5 PM, trade date noon) ──
        entry_ct = entry_time
        if entry_ct.tzinfo is None:
            entry_ct = CT.localize(entry_ct)
        if entry_ct < entries_start or entry_ct >= entries_end:
            continue

        # ── Compute line values at THIS candle's time ──
        lines_at_candle = _compute_lines_at_time(
            upper_pivot, lower_pivot, rth_high, rth_low, candle_time
        )
        # Also compute at entry time for targets
        lines_at_entry = _compute_lines_at_time(
            upper_pivot, lower_pivot, rth_high, rth_low, entry_time
        )

        if not lines_at_candle:
            continue

        # Deduplicate: one signal per direction per candle
        # (multiple lines at similar prices produce only one signal)
        seen_signals = set()  # (direction, rounded_price)

        for line in lines_at_candle:
            rejected = detect_rejection(candle, line.price, line.direction)
            if not rejected:
                continue

            entry_price = candles.iloc[i]["Open"]

            # Direction: determined by where entry opens relative to the line
            #   Entry above line → LONG (price bounced up off the level)
            #   Entry below line → SHORT (price rejected down off the level)
            if entry_price >= line.price:
                direction = "long"
            else:
                direction = "short"

            # Dedup: skip if we already have this direction at a similar price
            sig_key = (direction, round(entry_price))
            if sig_key in seen_signals:
                continue
            seen_signals.add(sig_key)

            # Stop loss
            if direction == "short":
                stop = candle["High"] + STOP_POINTS
            else:
                stop = candle["Low"] - STOP_POINTS

            # Target: nearest line in trade direction (at entry time)
            target = find_nearest_target(
                lines_at_entry, line.name, entry_price, direction
            )

            risk = abs(entry_price - stop)
            reward = abs(target.price - entry_price) if target else 0
            rr = reward / risk if risk > 0 else 0

            # Skip signals with negligible R:R
            if rr < 0.3:
                continue

            # Confluence check
            confluence_zones = detect_confluence_zones(lines_at_candle)
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
                direction=direction.upper(),
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


# ─── Session Quality Score ──────────────────────────────────────────

def compute_session_quality(
    vix: float,
    candles: pd.DataFrame,
    pivots_confirmed: int,  # 0, 1, or 2
    num_confluence_zones: int,
    trade_date: dt.date,
) -> SessionQuality:
    """
    Composite score (0–100) rating how tradeable today's session looks.
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

    # 2. Range component
    if len(candles) >= 7:
        daily_ranges = candles["High"] - candles["Low"]
        avg_range = daily_ranges.mean()
        range_score = min(100, avg_range * 8)
    else:
        range_score = 50

    # 3. Gap component
    if len(candles) >= 2:
        gap = abs(candles.iloc[-1]["Open"] - candles.iloc[-2]["Close"])
        gap_score = max(0, 100 - gap * 5)
    else:
        gap_score = 50

    # 4. Day-of-week
    dow = trade_date.weekday()
    dow_scores = {0: 70, 1: 90, 2: 100, 3: 90, 4: 50}
    time_score = dow_scores.get(dow, 50)

    # 5. Pivot clarity
    pivot_score = pivots_confirmed * 50

    # 6. Confluence zones
    conf_score = min(100, num_confluence_zones * 40)

    total = (
        vix_score * w["vix_regime"]
        + range_score * w["range_percentile"]
        + gap_score * w["gap_size"]
        + time_score * w["time_of_week"]
        + pivot_score * w["pivot_clarity"]
        + conf_score * w["line_convergence"]
    )

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
