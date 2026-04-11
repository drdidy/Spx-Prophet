"""
SPX PROPHET — Backtesting Engine
Walks through historical hourly candles applying the complete
strategy rule set. Produces trade-by-trade results and
aggregate statistics including win rate, R:R, drawdown,
P&L by VIX regime, and day-of-week performance.
"""

import datetime as dt
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

import pandas as pd
import numpy as np
import pytz

from config import (
    SLOPE, STOP_POINTS, BREAKEVEN_TRIGGER, DAILY_LOSS_LIMIT,
    POSITION_SIZE_ES, POINT_VALUE_ES, CONFLUENCE_THRESHOLD,
    REENTRY_LIMIT_EARLY, REENTRY_LIMIT_LATE, REENTRY_EARLY_END,
    BACKTEST_COMMISSION_PER_CONTRACT, BACKTEST_SLIPPAGE_POINTS,
    TIMEZONE, VIX_REGIME,
)
from pivot_detector import identify_upper_pivot, identify_lower_pivot
from line_calculator import (
    get_all_four_lines, detect_confluence_zones, calculate_line_value,
)
from signal_engine import detect_rejection, get_vix_regime
from macro_calendar import get_events_for_date, is_macro_blackout

CT = pytz.timezone(TIMEZONE)


# ═══════════════════════════════════════════════════════════════════════
#  DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class BacktestTrade:
    date: dt.date
    entry_time: pd.Timestamp
    direction: str               # "LONG" or "SHORT"
    entry_line: str
    entry_price: float
    target_price: float
    stop_price: float
    exit_price: float = 0.0
    exit_time: Optional[pd.Timestamp] = None
    exit_reason: str = ""        # "TARGET", "STOP", "BREAKEVEN_STOP", "EOD", "MACRO_HALT"
    result_pts: float = 0.0
    result_dollars: float = 0.0
    risk_pts: float = 0.0
    reward_pts: float = 0.0
    rr_ratio: float = 0.0
    vix_at_entry: float = 0.0
    vix_regime: str = ""
    confluence: bool = False
    signal_strength: str = "STANDARD"
    day_of_week: str = ""
    commission: float = 0.0
    slippage: float = 0.0
    is_winner: bool = False
    macro_event_active: bool = False


@dataclass
class BacktestResults:
    trades: List[BacktestTrade]
    start_date: dt.date
    end_date: dt.date
    trading_days: int = 0

    # Aggregate stats
    total_trades: int = 0
    winners: int = 0
    losers: int = 0
    breakeven: int = 0
    win_rate: float = 0.0

    # P&L
    gross_profit_pts: float = 0.0
    gross_loss_pts: float = 0.0
    net_pnl_pts: float = 0.0
    net_pnl_dollars: float = 0.0
    total_commissions: float = 0.0
    avg_win_pts: float = 0.0
    avg_loss_pts: float = 0.0
    avg_rr_ratio: float = 0.0
    profit_factor: float = 0.0

    # Drawdown
    max_drawdown_pts: float = 0.0
    max_drawdown_dollars: float = 0.0
    max_consecutive_losses: int = 0
    max_consecutive_wins: int = 0

    # Per-regime breakdown
    regime_stats: Dict = field(default_factory=dict)

    # Per-day-of-week breakdown
    dow_stats: Dict = field(default_factory=dict)

    # Per-line breakdown
    line_stats: Dict = field(default_factory=dict)

    # Per signal strength
    strength_stats: Dict = field(default_factory=dict)

    # Equity curve
    equity_curve: List[float] = field(default_factory=list)
    equity_dates: List = field(default_factory=list)

    # Macro impact
    macro_day_trades: int = 0
    macro_day_win_rate: float = 0.0
    clean_day_trades: int = 0
    clean_day_win_rate: float = 0.0


# ═══════════════════════════════════════════════════════════════════════
#  BACKTESTER CORE
# ═══════════════════════════════════════════════════════════════════════

def _get_trading_days(
    start_date: dt.date, end_date: dt.date
) -> List[dt.date]:
    """Generate list of weekday dates in range."""
    days = []
    d = start_date
    while d <= end_date:
        if d.weekday() < 5:
            days.append(d)
        d += dt.timedelta(days=1)
    return days


def _simulate_trade(
    candles: pd.DataFrame,
    trade: BacktestTrade,
    lines: list,
) -> BacktestTrade:
    """
    Walk forward candle-by-candle from entry to determine exit.
    Applies: target hit, stop hit, breakeven management, EOD exit.
    """
    entry_idx = None
    for i, ts in enumerate(candles.index):
        if ts >= trade.entry_time:
            entry_idx = i
            break

    if entry_idx is None:
        trade.exit_reason = "NO_DATA"
        trade.exit_price = trade.entry_price
        return trade

    breakeven_active = False
    current_stop = trade.stop_price

    # Walk through subsequent candles
    for i in range(entry_idx, len(candles)):
        candle = candles.iloc[i]
        ts = candles.index[i]

        # EOD exit at 12:00 PM CT (end of primary trading window)
        if ts.hour >= 12 and ts.minute == 0:
            trade.exit_price = candle["Close"]
            trade.exit_time = ts
            trade.exit_reason = "EOD"
            break

        if trade.direction == "LONG":
            # Check stop first (worst case)
            if candle["Low"] <= current_stop:
                trade.exit_price = current_stop
                trade.exit_time = ts
                trade.exit_reason = "BREAKEVEN_STOP" if breakeven_active else "STOP"
                break

            # Check target
            if candle["High"] >= trade.target_price:
                trade.exit_price = trade.target_price
                trade.exit_time = ts
                trade.exit_reason = "TARGET"
                break

            # Breakeven management
            if not breakeven_active:
                max_favorable = candle["High"] - trade.entry_price
                if max_favorable >= BREAKEVEN_TRIGGER:
                    current_stop = trade.entry_price
                    breakeven_active = True

        else:  # SHORT
            # Check stop first
            if candle["High"] >= current_stop:
                trade.exit_price = current_stop
                trade.exit_time = ts
                trade.exit_reason = "BREAKEVEN_STOP" if breakeven_active else "STOP"
                break

            # Check target
            if candle["Low"] <= trade.target_price:
                trade.exit_price = trade.target_price
                trade.exit_time = ts
                trade.exit_reason = "TARGET"
                break

            # Breakeven management
            if not breakeven_active:
                max_favorable = trade.entry_price - candle["Low"]
                if max_favorable >= BREAKEVEN_TRIGGER:
                    current_stop = trade.entry_price
                    breakeven_active = True
    else:
        # If loop exhausts without exit, close at last candle
        trade.exit_price = candles.iloc[-1]["Close"]
        trade.exit_time = candles.index[-1]
        trade.exit_reason = "EOD"

    # Calculate result
    if trade.direction == "LONG":
        trade.result_pts = trade.exit_price - trade.entry_price
    else:
        trade.result_pts = trade.entry_price - trade.exit_price

    # Apply slippage (both sides)
    trade.slippage = BACKTEST_SLIPPAGE_POINTS * 2
    trade.result_pts -= trade.slippage

    # Commission
    trade.commission = BACKTEST_COMMISSION_PER_CONTRACT * POSITION_SIZE_ES * 2
    trade.result_dollars = (
        trade.result_pts * POINT_VALUE_ES * POSITION_SIZE_ES
        - trade.commission
    )

    trade.is_winner = trade.result_pts > 0

    return trade


def run_backtest(
    candles: pd.DataFrame,
    vix_data: pd.Series | None,
    start_date: dt.date,
    end_date: dt.date,
    filter_by_session_quality: bool = False,
    min_rr: float = 0.0,
    exclude_macro_extreme: bool = True,
) -> BacktestResults:
    """
    Full backtest over a date range.
    
    For each trading day:
      1. Identify pivots from prior day's 12–3 PM (or extended)
      2. Calculate the 4 lines
      3. Scan 9 AM – 12 PM candles for rejection signals
      4. Simulate each trade to completion
      5. Enforce daily loss limit and re-entry caps
    """
    all_trades: List[BacktestTrade] = []
    trading_days = _get_trading_days(start_date, end_date)

    for day in trading_days:
        # ── Macro check ──
        macro_events = get_events_for_date(day)
        has_extreme_macro = any(e.severity == "extreme" for e in macro_events)

        if exclude_macro_extreme and has_extreme_macro:
            continue  # Skip this day entirely

        # ── Pivot detection ──
        upper_pivot = identify_upper_pivot(candles, day)
        lower_pivot = identify_lower_pivot(candles, day)

        if upper_pivot is None and lower_pivot is None:
            continue  # Can't trade without any pivots

        # ── Calculate lines at 9 AM CT ──
        ref_time = CT.localize(dt.datetime.combine(day, dt.time(9, 0)))
        lines = get_all_four_lines(upper_pivot, lower_pivot, ref_time)

        if not lines:
            continue

        confluence_zones = detect_confluence_zones(lines, CONFLUENCE_THRESHOLD)

        # ── Get today's trading candles (9 AM – 12 PM CT) ──
        day_start = CT.localize(dt.datetime.combine(day, dt.time(9, 0)))
        day_end = CT.localize(dt.datetime.combine(day, dt.time(12, 0)))
        day_candles = candles[
            (candles.index >= day_start) & (candles.index <= day_end)
        ]

        if len(day_candles) < 2:
            continue

        # ── VIX for this day ──
        day_vix = 16.5  # default
        if vix_data is not None and not vix_data.empty:
            # Find closest VIX reading
            vix_on_day = vix_data[vix_data.index.date == day]
            if not vix_on_day.empty:
                day_vix = float(vix_on_day.iloc[-1])

        vix_regime_name, _ = get_vix_regime(day_vix)

        # ── Scan for rejection signals ──
        daily_loss = 0.0
        daily_entries = 0
        early_entries = 0  # 9–11 AM
        late_entries = 0   # 11 AM–12 PM
        used_lines = set()

        for i in range(1, len(day_candles)):
            # Check daily loss limit
            if daily_loss <= -DAILY_LOSS_LIMIT:
                break

            candle = day_candles.iloc[i - 1]  # Rejection candle
            entry_time = day_candles.index[i]  # Entry on next candle

            # Re-entry limits
            entry_hour = entry_time.hour
            if entry_hour < REENTRY_EARLY_END:
                if early_entries >= REENTRY_LIMIT_EARLY:
                    continue
            else:
                if late_entries >= REENTRY_LIMIT_LATE:
                    continue

            # Recalculate lines at this specific time
            current_lines = get_all_four_lines(
                upper_pivot, lower_pivot, entry_time
            )

            for line in current_lines:
                if line.name in used_lines:
                    continue  # Re-entry must be on different line

                rejection = detect_rejection(candle, line.price)
                if rejection is None:
                    continue

                entry_price = day_candles.iloc[i]["Open"]

                # Stop
                if rejection == "short":
                    stop = candle["High"] + STOP_POINTS
                else:
                    stop = candle["Low"] - STOP_POINTS

                # Target: nearest line in trade direction
                from line_calculator import find_nearest_target
                target_line = find_nearest_target(
                    current_lines, line.name, entry_price, rejection
                )

                if target_line is None:
                    continue

                risk = abs(entry_price - stop)
                reward = abs(target_line.price - entry_price)
                rr = reward / risk if risk > 0 else 0

                # R:R filter
                if rr < min_rr:
                    continue

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

                # Build trade
                trade = BacktestTrade(
                    date=day,
                    entry_time=entry_time,
                    direction=rejection.upper(),
                    entry_line=line.label,
                    entry_price=round(entry_price, 2),
                    target_price=round(target_line.price, 2),
                    stop_price=round(stop, 2),
                    risk_pts=round(risk, 2),
                    reward_pts=round(reward, 2),
                    rr_ratio=round(rr, 2),
                    vix_at_entry=day_vix,
                    vix_regime=vix_regime_name,
                    confluence=in_confluence,
                    signal_strength=strength,
                    day_of_week=day.strftime("%A"),
                    macro_event_active=bool(macro_events),
                )

                # Simulate to exit
                remaining_candles = day_candles[day_candles.index >= entry_time]
                trade = _simulate_trade(remaining_candles, trade, current_lines)

                all_trades.append(trade)
                daily_loss += trade.result_dollars
                daily_entries += 1
                used_lines.add(line.name)

                if entry_hour < REENTRY_EARLY_END:
                    early_entries += 1
                else:
                    late_entries += 1

                # Only take one signal per candle
                break

    # ── Compute aggregate results ──
    return _compute_results(all_trades, start_date, end_date, len(trading_days))


# ═══════════════════════════════════════════════════════════════════════
#  RESULTS COMPUTATION
# ═══════════════════════════════════════════════════════════════════════

def _compute_results(
    trades: List[BacktestTrade],
    start_date: dt.date,
    end_date: dt.date,
    trading_days: int,
) -> BacktestResults:
    """Calculate all aggregate statistics from trade list."""
    r = BacktestResults(
        trades=trades,
        start_date=start_date,
        end_date=end_date,
        trading_days=trading_days,
    )

    if not trades:
        return r

    r.total_trades = len(trades)
    r.winners = sum(1 for t in trades if t.result_pts > 0)
    r.losers = sum(1 for t in trades if t.result_pts < 0)
    r.breakeven = sum(1 for t in trades if t.result_pts == 0)
    r.win_rate = r.winners / r.total_trades * 100 if r.total_trades > 0 else 0

    # P&L
    winning_pts = [t.result_pts for t in trades if t.result_pts > 0]
    losing_pts = [t.result_pts for t in trades if t.result_pts < 0]

    r.gross_profit_pts = sum(winning_pts)
    r.gross_loss_pts = sum(losing_pts)
    r.net_pnl_pts = sum(t.result_pts for t in trades)
    r.total_commissions = sum(t.commission for t in trades)
    r.net_pnl_dollars = sum(t.result_dollars for t in trades)

    r.avg_win_pts = np.mean(winning_pts) if winning_pts else 0
    r.avg_loss_pts = np.mean(losing_pts) if losing_pts else 0
    r.avg_rr_ratio = np.mean([t.rr_ratio for t in trades])
    r.profit_factor = (
        abs(r.gross_profit_pts / r.gross_loss_pts)
        if r.gross_loss_pts != 0 else float("inf")
    )

    # Drawdown
    equity = 0
    peak = 0
    max_dd = 0
    r.equity_curve = [0]
    r.equity_dates = [start_date]
    consecutive_losses = 0
    consecutive_wins = 0
    max_consec_l = 0
    max_consec_w = 0

    for t in trades:
        equity += t.result_dollars
        r.equity_curve.append(equity)
        r.equity_dates.append(t.date)
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

        if t.result_pts > 0:
            consecutive_wins += 1
            consecutive_losses = 0
            max_consec_w = max(max_consec_w, consecutive_wins)
        elif t.result_pts < 0:
            consecutive_losses += 1
            consecutive_wins = 0
            max_consec_l = max(max_consec_l, consecutive_losses)

    r.max_drawdown_dollars = max_dd
    r.max_drawdown_pts = max_dd / (POINT_VALUE_ES * POSITION_SIZE_ES) if max_dd else 0
    r.max_consecutive_losses = max_consec_l
    r.max_consecutive_wins = max_consec_w

    # ── Per-regime breakdown ──
    for regime in ["LOW VOL", "NORMAL", "ELEVATED", "EXTREME"]:
        regime_trades = [t for t in trades if t.vix_regime == regime]
        if regime_trades:
            wins = sum(1 for t in regime_trades if t.result_pts > 0)
            r.regime_stats[regime] = {
                "trades": len(regime_trades),
                "win_rate": wins / len(regime_trades) * 100,
                "net_pts": sum(t.result_pts for t in regime_trades),
                "net_dollars": sum(t.result_dollars for t in regime_trades),
                "avg_rr": np.mean([t.rr_ratio for t in regime_trades]),
            }

    # ── Per-day-of-week breakdown ──
    for dow in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        dow_trades = [t for t in trades if t.day_of_week == dow]
        if dow_trades:
            wins = sum(1 for t in dow_trades if t.result_pts > 0)
            r.dow_stats[dow] = {
                "trades": len(dow_trades),
                "win_rate": wins / len(dow_trades) * 100,
                "net_pts": sum(t.result_pts for t in dow_trades),
                "net_dollars": sum(t.result_dollars for t in dow_trades),
            }

    # ── Per-line breakdown ──
    for line_label in set(t.entry_line for t in trades):
        line_trades = [t for t in trades if t.entry_line == line_label]
        wins = sum(1 for t in line_trades if t.result_pts > 0)
        r.line_stats[line_label] = {
            "trades": len(line_trades),
            "win_rate": wins / len(line_trades) * 100,
            "net_pts": sum(t.result_pts for t in line_trades),
        }

    # ── Per signal strength ──
    for strength in ["STANDARD", "HIGH", "PREMIUM"]:
        s_trades = [t for t in trades if t.signal_strength == strength]
        if s_trades:
            wins = sum(1 for t in s_trades if t.result_pts > 0)
            r.strength_stats[strength] = {
                "trades": len(s_trades),
                "win_rate": wins / len(s_trades) * 100,
                "net_pts": sum(t.result_pts for t in s_trades),
                "net_dollars": sum(t.result_dollars for t in s_trades),
                "avg_rr": np.mean([t.rr_ratio for t in s_trades]),
            }

    # ── Macro vs clean days ──
    macro_trades = [t for t in trades if t.macro_event_active]
    clean_trades = [t for t in trades if not t.macro_event_active]

    r.macro_day_trades = len(macro_trades)
    r.macro_day_win_rate = (
        sum(1 for t in macro_trades if t.result_pts > 0) / len(macro_trades) * 100
        if macro_trades else 0
    )
    r.clean_day_trades = len(clean_trades)
    r.clean_day_win_rate = (
        sum(1 for t in clean_trades if t.result_pts > 0) / len(clean_trades) * 100
        if clean_trades else 0
    )

    return r
