"""
SPX PROPHET — Options P&L Calculator
Estimates 0DTE SPX option premiums using a simplified
Black-Scholes model. Converts ES-level signals into
approximate SPX options P&L.

This is an ESTIMATE. Actual premiums depend on real-time
implied volatility, bid-ask spread, and Greek exposure.
Use for planning, not execution pricing.
"""

import math
import datetime as dt
from dataclasses import dataclass
from typing import Optional

from config import (
    SPX_OPTIONS_COMMISSION, SPX_OPTIONS_MULTIPLIER,
    DEFAULT_OPTION_CONTRACTS, OTM_STRIKES, RISK_FREE_RATE,
)


@dataclass
class OptionEstimate:
    option_type: str          # "CALL" or "PUT"
    strike: float
    underlying: float         # SPX price at entry
    premium_entry: float      # estimated entry premium
    premium_target: float     # estimated premium at target
    premium_stop: float       # estimated premium at stop
    contracts: int
    max_profit: float         # dollars
    max_loss: float           # dollars
    commission_total: float   # round-trip
    net_profit: float         # max_profit - commission
    net_loss: float           # max_loss + commission
    rr_ratio: float
    breakeven_move: float     # SPX points needed to break even
    delta_approx: float       # approximate delta at entry
    time_to_expiry_hours: float


def _norm_cdf(x: float) -> float:
    """Standard normal CDF approximation (Abramowitz & Stegun)."""
    a1, a2, a3, a4, a5 = (
        0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    )
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2)
    return 0.5 * (1.0 + sign * y)


def _norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def black_scholes_price(
    S: float,        # underlying price
    K: float,        # strike
    T: float,        # time to expiry in years
    r: float,        # risk-free rate
    sigma: float,    # implied volatility (annualized)
    option_type: str  # "CALL" or "PUT"
) -> float:
    """Black-Scholes option price."""
    if T <= 0:
        # At expiry
        if option_type == "CALL":
            return max(0, S - K)
        else:
            return max(0, K - S)

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "CALL":
        price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)

    return max(price, 0.01)  # floor at $0.01


def bs_delta(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str
) -> float:
    """Black-Scholes delta."""
    if T <= 0:
        if option_type == "CALL":
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    if option_type == "CALL":
        return _norm_cdf(d1)
    else:
        return _norm_cdf(d1) - 1.0


def vix_to_iv(vix: float, dte_hours: float) -> float:
    """
    Convert VIX to approximate implied volatility for 0DTE options.
    0DTE IV is typically 1.2–1.8x the VIX level due to gamma premium.
    """
    vix_decimal = vix / 100.0

    # 0DTE premium multiplier (decreases as expiry approaches)
    if dte_hours > 6:
        multiplier = 1.3
    elif dte_hours > 3:
        multiplier = 1.5
    elif dte_hours > 1:
        multiplier = 1.8
    else:
        multiplier = 2.2

    return vix_decimal * multiplier


def estimate_option_trade(
    spx_price: float,
    direction: str,        # "LONG" or "SHORT" (the ES signal direction)
    target_pts: float,     # ES points to target
    stop_pts: float,       # ES points to stop
    vix: float,
    hours_to_expiry: float = 5.0,
    contracts: int = DEFAULT_OPTION_CONTRACTS,
) -> OptionEstimate:
    """
    Convert an ES signal into an SPX option trade estimate.

    If signal is LONG → buy CALLS (4 strikes OTM)
    If signal is SHORT → buy PUTS (4 strikes OTM)
    """
    # Round to nearest 5-point strike
    strike_interval = 5

    if direction == "LONG":
        option_type = "CALL"
        # 4 strikes OTM above current price
        raw_strike = spx_price + (OTM_STRIKES * strike_interval)
        strike = round(raw_strike / strike_interval) * strike_interval
        spx_at_target = spx_price + target_pts
        spx_at_stop = spx_price - stop_pts
    else:
        option_type = "PUT"
        # 4 strikes OTM below current price
        raw_strike = spx_price - (OTM_STRIKES * strike_interval)
        strike = round(raw_strike / strike_interval) * strike_interval
        spx_at_target = spx_price - target_pts
        spx_at_stop = spx_price + stop_pts

    # Time to expiry in years
    T = hours_to_expiry / (252 * 6.5)  # trading hours per year
    T_at_target = max(0.0001, T - 0.5 / (252 * 6.5))  # ~30 min later
    T_at_stop = max(0.0001, T - 0.25 / (252 * 6.5))    # ~15 min later

    # IV from VIX
    iv = vix_to_iv(vix, hours_to_expiry)

    # Prices
    premium_entry = black_scholes_price(spx_price, strike, T, RISK_FREE_RATE, iv, option_type)
    premium_target = black_scholes_price(spx_at_target, strike, T_at_target, RISK_FREE_RATE, iv, option_type)
    premium_stop = black_scholes_price(spx_at_stop, strike, T_at_stop, RISK_FREE_RATE, iv, option_type)

    # Delta
    delta = bs_delta(spx_price, strike, T, RISK_FREE_RATE, iv, option_type)

    # P&L
    commission = SPX_OPTIONS_COMMISSION * contracts * 2  # round trip
    max_profit = (premium_target - premium_entry) * SPX_OPTIONS_MULTIPLIER * contracts
    max_loss = (premium_stop - premium_entry) * SPX_OPTIONS_MULTIPLIER * contracts

    # max_loss is negative (premium drops), make it positive for display
    if max_loss > 0:
        max_loss = 0  # rare: stop price still ITM-ish
    max_loss = abs(max_loss)

    net_profit = max_profit - commission
    net_loss = max_loss + commission

    rr = net_profit / net_loss if net_loss > 0 else float("inf")

    # Breakeven: how many SPX points for premium to cover commission
    breakeven_move = (commission / contracts / SPX_OPTIONS_MULTIPLIER) / abs(delta) if delta != 0 else 0

    return OptionEstimate(
        option_type=option_type,
        strike=strike,
        underlying=round(spx_price, 2),
        premium_entry=round(premium_entry, 2),
        premium_target=round(premium_target, 2),
        premium_stop=round(premium_stop, 2),
        contracts=contracts,
        max_profit=round(max_profit, 2),
        max_loss=round(max_loss, 2),
        commission_total=round(commission, 2),
        net_profit=round(net_profit, 2),
        net_loss=round(net_loss, 2),
        rr_ratio=round(rr, 2),
        breakeven_move=round(breakeven_move, 2),
        delta_approx=round(delta, 4),
        time_to_expiry_hours=hours_to_expiry,
    )
