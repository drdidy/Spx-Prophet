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
    gamma_approx: float       # approximate gamma at entry
    theta_approx: float       # approximate theta (per day) at entry
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


def bs_gamma(
    S: float, K: float, T: float, r: float, sigma: float
) -> float:
    """Black-Scholes gamma (same for calls and puts)."""
    if T <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return _norm_pdf(d1) / (S * sigma * math.sqrt(T))


def bs_theta(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str
) -> float:
    """Black-Scholes theta (per calendar day). Returns negative value for long options."""
    if T <= 0:
        return 0.0
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    # First term is the same for calls and puts
    term1 = -(S * _norm_pdf(d1) * sigma) / (2 * sqrt_T)

    if option_type == "CALL":
        theta = term1 - r * K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        theta = term1 + r * K * math.exp(-r * T) * _norm_cdf(-d2)

    # Convert from per-year to per-calendar-day
    return theta / 365.0


def vix_to_iv(vix: float, dte_hours: float) -> float:
    """
    Convert VIX to approximate implied volatility for 0DTE options.

    VIX is already annualized implied volatility for 30-day SPX options.
    0DTE IV tends to be modestly higher than VIX due to gamma/pinning
    premium, but the raw VIX is a reasonable starting point.

    We apply a small 0DTE premium that increases as expiry nears,
    reflecting the elevated short-dated IV observed in the market.
    """
    vix_decimal = vix / 100.0

    # Modest 0DTE IV premium — 0DTE IV typically runs 10-30% above VIX
    if dte_hours > 4:
        multiplier = 1.10
    elif dte_hours > 2:
        multiplier = 1.15
    elif dte_hours > 1:
        multiplier = 1.20
    else:
        multiplier = 1.25

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

    # Time to expiry in years (trading hours basis)
    trading_hours_per_year = 252 * 6.5  # ~1638 trading hours
    T = hours_to_expiry / trading_hours_per_year

    # Estimate time elapsed for target/stop scenarios.
    # Assume target hit takes ~30-60 min and stop hit ~15-30 min,
    # scaled by how far the move is relative to typical 0DTE range.
    # For 0DTE, even small time differences matter due to rapid theta.
    time_to_target_hrs = min(1.0, target_pts / 20.0) * 0.75  # ~45 min for 20pt move
    time_to_stop_hrs = min(0.5, stop_pts / 20.0) * 0.5       # ~15 min for 10pt move
    T_at_target = max(0.0001, T - time_to_target_hrs / trading_hours_per_year)
    T_at_stop = max(0.0001, T - time_to_stop_hrs / trading_hours_per_year)

    # IV from VIX
    iv = vix_to_iv(vix, hours_to_expiry)

    # Entry price via BSM
    premium_entry = black_scholes_price(spx_price, strike, T, RISK_FREE_RATE, iv, option_type)

    # Target/stop prices via full BSM reprice (captures gamma, theta implicitly)
    premium_target = black_scholes_price(spx_at_target, strike, T_at_target, RISK_FREE_RATE, iv, option_type)
    premium_stop = black_scholes_price(spx_at_stop, strike, T_at_stop, RISK_FREE_RATE, iv, option_type)

    # Greeks at entry
    delta = bs_delta(spx_price, strike, T, RISK_FREE_RATE, iv, option_type)
    gamma = bs_gamma(spx_price, strike, T, RISK_FREE_RATE, iv)
    theta_daily = bs_theta(spx_price, strike, T, RISK_FREE_RATE, iv, option_type)

    # P&L calculation
    commission = SPX_OPTIONS_COMMISSION * contracts * 2  # round trip (open + close)
    profit_per_contract = (premium_target - premium_entry) * SPX_OPTIONS_MULTIPLIER
    loss_per_contract = (premium_entry - premium_stop) * SPX_OPTIONS_MULTIPLIER

    max_profit = profit_per_contract * contracts
    max_loss = loss_per_contract * contracts

    # When buying options, max loss is capped at premium paid
    max_cost = premium_entry * SPX_OPTIONS_MULTIPLIER * contracts
    max_loss = min(max_loss, max_cost)
    max_loss = max(max_loss, 0)  # floor at 0

    net_profit = max_profit - commission
    net_loss = max_loss + commission

    rr = net_profit / net_loss if net_loss > 0 else float("inf")

    # Breakeven move: account for both commission drag and gamma
    # Use delta + 0.5*gamma*move for a better estimate than delta alone
    commission_per_contract = commission / contracts
    premium_to_recover = commission_per_contract / SPX_OPTIONS_MULTIPLIER
    if abs(delta) > 0.001:
        # Solve: delta*move + 0.5*gamma*move^2 = premium_to_recover
        # Quadratic: 0.5*gamma*x^2 + |delta|*x - premium_to_recover = 0
        a_coeff = 0.5 * gamma
        b_coeff = abs(delta)
        c_coeff = -premium_to_recover
        if a_coeff > 0.0001:
            discriminant = b_coeff ** 2 - 4 * a_coeff * c_coeff
            breakeven_move = (-b_coeff + math.sqrt(max(0, discriminant))) / (2 * a_coeff)
        else:
            breakeven_move = premium_to_recover / b_coeff
    else:
        breakeven_move = 0

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
        gamma_approx=round(gamma, 6),
        theta_approx=round(theta_daily, 2),
        time_to_expiry_hours=hours_to_expiry,
    )
