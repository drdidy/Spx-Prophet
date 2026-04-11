"""
SPX PROPHET — Line Calculator
Computes the 4 dynamic slope-adjusted trend lines
and detects confluence zones.
"""

import datetime as dt
from dataclasses import dataclass
from typing import Optional, List

import pandas as pd
import pytz

from config import SLOPE, CONFLUENCE_THRESHOLD, LINE_LABELS, TIMEZONE
from pivot_detector import Pivot

CT = pytz.timezone(TIMEZONE)


@dataclass
class LineValue:
    name: str
    label: str
    price: float
    direction: str    # "ascending" or "descending"
    pivot_price: float
    hours_elapsed: float


@dataclass
class ConfluenceZone:
    price_center: float
    lines: list
    strength: float  # 1.0 = two lines, 1.5 = three, 2.0 = four


def hours_between(t1: pd.Timestamp, t2: pd.Timestamp) -> float:
    """
    Calculate TRADING hours elapsed between two timestamps.
    
    ES futures trade Sun 5 PM – Fri 4 PM CT with a daily
    maintenance halt from 4:00 PM – 5:00 PM CT (Mon–Thu).
    
    This function EXCLUDES:
      1. The daily 4–5 PM CT maintenance window (1 hr/day, Mon–Thu)
      2. Weekend closure: Friday 4 PM CT → Sunday 5 PM CT
    
    Without this correction, lines drift ~1 pt/day from maintenance
    and ~50 pts over a weekend — enough to destroy every signal.
    """
    # Ensure both are in CT
    if t1.tzinfo is None:
        t1 = CT.localize(t1)
    if t2.tzinfo is None:
        t2 = CT.localize(t2)

    # Ensure t1 <= t2
    if t1 > t2:
        t1, t2 = t2, t1

    # Total clock hours
    total_clock_hours = (t2 - t1).total_seconds() / 3600.0

    # Count maintenance windows (4–5 PM CT) to subtract
    maintenance_hours = 0.0
    weekend_hours = 0.0

    # Walk day by day from t1's date to t2's date
    d = t1.date()
    end_date = t2.date()

    while d <= end_date:
        dow = d.weekday()  # 0=Mon ... 6=Sun

        # ── Weekend gap: all of Saturday + Sunday until 5 PM ──
        if dow == 5:  # Saturday — full day is closed
            # Count hours of Saturday that fall within [t1, t2]
            sat_start = CT.localize(dt.datetime.combine(d, dt.time(0, 0)))
            sat_end = CT.localize(dt.datetime.combine(d, dt.time(23, 59, 59)))
            overlap_start = max(t1, sat_start)
            overlap_end = min(t2, sat_end)
            if overlap_end > overlap_start:
                weekend_hours += (overlap_end - overlap_start).total_seconds() / 3600.0

        elif dow == 6:  # Sunday — closed until 5 PM CT
            sun_closed_start = CT.localize(dt.datetime.combine(d, dt.time(0, 0)))
            sun_closed_end = CT.localize(dt.datetime.combine(d, dt.time(17, 0)))
            overlap_start = max(t1, sun_closed_start)
            overlap_end = min(t2, sun_closed_end)
            if overlap_end > overlap_start:
                weekend_hours += (overlap_end - overlap_start).total_seconds() / 3600.0

        elif dow == 4:  # Friday — market closes at 4 PM, weekend starts
            fri_close = CT.localize(dt.datetime.combine(d, dt.time(16, 0)))
            fri_midnight = CT.localize(dt.datetime.combine(d, dt.time(23, 59, 59)))
            overlap_start = max(t1, fri_close)
            overlap_end = min(t2, fri_midnight)
            if overlap_end > overlap_start:
                weekend_hours += (overlap_end - overlap_start).total_seconds() / 3600.0

        else:
            # Mon–Thu: subtract the 4–5 PM maintenance window
            maint_start = CT.localize(dt.datetime.combine(d, dt.time(16, 0)))
            maint_end = CT.localize(dt.datetime.combine(d, dt.time(17, 0)))
            overlap_start = max(t1, maint_start)
            overlap_end = min(t2, maint_end)
            if overlap_end > overlap_start:
                maintenance_hours += (overlap_end - overlap_start).total_seconds() / 3600.0

        d += dt.timedelta(days=1)

    trading_hours = total_clock_hours - maintenance_hours - weekend_hours
    return max(0.0, trading_hours)


def calculate_line_value(
    pivot_price: float,
    pivot_time: pd.Timestamp,
    current_time: pd.Timestamp,
    ascending: bool,
) -> float:
    """
    line_value = pivot_price ± (slope × hours_elapsed)
    """
    h = hours_between(pivot_time, current_time)
    if ascending:
        return pivot_price + (SLOPE * h)
    else:
        return pivot_price - (SLOPE * h)


def get_all_four_lines(
    upper_pivot: Optional[Pivot],
    lower_pivot: Optional[Pivot],
    current_time: pd.Timestamp,
) -> List[LineValue]:
    """Return current values of all 4 pivot lines (backward compat)."""
    return get_all_six_lines(upper_pivot, lower_pivot, None, None, current_time)


def get_all_six_lines(
    upper_pivot: Optional[Pivot],
    lower_pivot: Optional[Pivot],
    rth_high: Optional[Pivot],
    rth_low: Optional[Pivot],
    current_time: pd.Timestamp,
) -> List[LineValue]:
    """
    Return current values of all 6 lines:
    Lines 1-4: from upper/lower pivots (12-3 PM CT)
    Lines 5-6: from RTH extremes (8:30 AM - 3:00 PM CT)
    """
    lines = []

    # Line 1 — Upper Ascending (Red)
    if upper_pivot:
        lines.append(LineValue(
            name="upper_ascending",
            label=LINE_LABELS["upper_ascending"],
            price=calculate_line_value(
                upper_pivot.price, upper_pivot.time, current_time, ascending=True
            ),
            direction="ascending",
            pivot_price=upper_pivot.price,
            hours_elapsed=hours_between(upper_pivot.time, current_time),
        ))

    # Line 2 — Lower Ascending (Red)
    if lower_pivot:
        lines.append(LineValue(
            name="lower_ascending",
            label=LINE_LABELS["lower_ascending"],
            price=calculate_line_value(
                lower_pivot.price, lower_pivot.time, current_time, ascending=True
            ),
            direction="ascending",
            pivot_price=lower_pivot.price,
            hours_elapsed=hours_between(lower_pivot.time, current_time),
        ))

    # Line 3 — Upper Descending (Green)
    if upper_pivot:
        lines.append(LineValue(
            name="upper_descending",
            label=LINE_LABELS["upper_descending"],
            price=calculate_line_value(
                upper_pivot.price, upper_pivot.time, current_time, ascending=False
            ),
            direction="descending",
            pivot_price=upper_pivot.price,
            hours_elapsed=hours_between(upper_pivot.time, current_time),
        ))

    # Line 4 — Lower Descending (Green)
    if lower_pivot:
        lines.append(LineValue(
            name="lower_descending",
            label=LINE_LABELS["lower_descending"],
            price=calculate_line_value(
                lower_pivot.price, lower_pivot.time, current_time, ascending=False
            ),
            direction="descending",
            pivot_price=lower_pivot.price,
            hours_elapsed=hours_between(lower_pivot.time, current_time),
        ))

    # Line 5 — Extreme Ascending (Black) from RTH High
    if rth_high:
        lines.append(LineValue(
            name="extreme_ascending",
            label=LINE_LABELS["extreme_ascending"],
            price=calculate_line_value(
                rth_high.price, rth_high.time, current_time, ascending=True
            ),
            direction="ascending",
            pivot_price=rth_high.price,
            hours_elapsed=hours_between(rth_high.time, current_time),
        ))

    # Line 6 — Extreme Descending (Black) from RTH Low
    if rth_low:
        lines.append(LineValue(
            name="extreme_descending",
            label=LINE_LABELS["extreme_descending"],
            price=calculate_line_value(
                rth_low.price, rth_low.time, current_time, ascending=False
            ),
            direction="descending",
            pivot_price=rth_low.price,
            hours_elapsed=hours_between(rth_low.time, current_time),
        ))

    return lines


def get_line_series(
    pivot: Pivot,
    ascending: bool,
    time_range: pd.DatetimeIndex,
) -> List[Optional[float]]:
    """
    Get a series of line values across a time range for charting.
    Returns None for timestamps before the pivot (lines only project forward).
    """
    return [
        calculate_line_value(pivot.price, pivot.time, t, ascending)
        if t >= pivot.time else None
        for t in time_range
    ]


def detect_confluence_zones(
    lines: List[LineValue], threshold: float = CONFLUENCE_THRESHOLD
) -> List[ConfluenceZone]:
    """
    Find zones where 2+ lines are within `threshold` points of each other.
    These are HIGH-PROBABILITY reversal zones.
    """
    if len(lines) < 2:
        return []

    zones = []
    checked = set()

    for i, l1 in enumerate(lines):
        cluster = [l1]
        for j, l2 in enumerate(lines):
            if i == j:
                continue
            if abs(l1.price - l2.price) <= threshold:
                cluster.append(l2)
                checked.add(j)

        if len(cluster) >= 2 and i not in checked:
            center = sum(l.price for l in cluster) / len(cluster)
            strength = 1.0 + (len(cluster) - 2) * 0.5
            zones.append(ConfluenceZone(
                price_center=center,
                lines=[l.name for l in cluster],
                strength=strength,
            ))
            checked.add(i)

    return zones


def find_nearest_target(
    lines: List[LineValue],
    entry_line_name: str,
    current_price: float,
    direction: str,  # "long" or "short"
) -> Optional[LineValue]:
    """
    Find the nearest line target in the trade direction.
    For LONG: nearest line ABOVE current price (excluding entry line)
    For SHORT: nearest line BELOW current price (excluding entry line)
    """
    candidates = [l for l in lines if l.name != entry_line_name]

    if direction == "long":
        above = [l for l in candidates if l.price > current_price]
        if above:
            return min(above, key=lambda l: l.price)
    else:
        below = [l for l in candidates if l.price < current_price]
        if below:
            return max(below, key=lambda l: l.price)

    return None
