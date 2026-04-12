"""
SPX PROPHET — Monte Carlo Simulator
Takes historical trade results (or parameterized win rate / R:R)
and runs forward simulations to estimate:
  - Probability of ruin
  - Expected P&L distribution
  - Confidence intervals for account growth
  - Optimal position sizing (Kelly criterion)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from config import (
    MONTE_CARLO_SIMULATIONS, MONTE_CARLO_TRADE_HORIZON,
    RUIN_THRESHOLD, POSITION_SIZE_ES, POINT_VALUE_ES,
)


@dataclass
class MonteCarloResults:
    simulations: int
    trade_horizon: int
    starting_capital: float

    # Core outcomes
    probability_of_ruin: float       # % of sims hitting ruin threshold
    probability_of_profit: float     # % of sims ending positive
    median_final_pnl: float
    mean_final_pnl: float

    # Percentile distribution
    pct_5: float                     # worst 5%
    pct_25: float
    pct_50: float                    # median
    pct_75: float
    pct_95: float                    # best 5%

    # Drawdown analysis
    avg_max_drawdown: float
    worst_max_drawdown: float
    median_max_drawdown: float

    # Kelly criterion
    kelly_fraction: float            # optimal fraction of capital to risk
    half_kelly_fraction: float       # conservative Kelly (recommended)

    # Equity curve bands (for plotting)
    curve_median: List[float] = field(default_factory=list)
    curve_upper: List[float] = field(default_factory=list)  # 75th pct
    curve_lower: List[float] = field(default_factory=list)  # 25th pct
    curve_worst: List[float] = field(default_factory=list)  # 5th pct
    curve_best: List[float] = field(default_factory=list)   # 95th pct

    # Profit target probabilities  {target_dollar: probability %}
    profit_target_probs: Dict = field(default_factory=dict)

    # Drawdown percentiles
    drawdown_pct_50: float = 0.0
    drawdown_pct_75: float = 0.0
    drawdown_pct_95: float = 0.0


def run_monte_carlo(
    win_rate: float,            # 0–1 (e.g., 0.55 for 55%)
    avg_win_pts: float,         # average winning trade in points
    avg_loss_pts: float,        # average losing trade in points (positive number)
    starting_capital: float = 10000.0,
    num_simulations: int = MONTE_CARLO_SIMULATIONS,
    trade_horizon: int = MONTE_CARLO_TRADE_HORIZON,
    ruin_threshold: float = RUIN_THRESHOLD,
    position_size: int = POSITION_SIZE_ES,
    point_value: float = POINT_VALUE_ES,
) -> MonteCarloResults:
    """
    Run Monte Carlo simulation of forward trading.

    Each simulation:
      - Runs `trade_horizon` trades
      - Each trade randomly wins (prob=win_rate) or loses
      - Win = +avg_win_pts, Loss = -avg_loss_pts
      - Tracks equity curve and max drawdown
    """
    np.random.seed(None)  # truly random each run

    dollar_per_pt = point_value * position_size

    all_final_pnl = np.zeros(num_simulations)
    all_max_drawdown = np.zeros(num_simulations)
    ruin_count = 0

    # For equity curve bands
    all_curves = np.zeros((num_simulations, trade_horizon + 1))

    for sim in range(num_simulations):
        equity = 0.0
        peak = 0.0
        max_dd = 0.0

        all_curves[sim, 0] = 0.0

        for t in range(trade_horizon):
            # Random win/loss
            if np.random.random() < win_rate:
                # Add some variance to wins (±30%)
                win_var = avg_win_pts * (0.7 + np.random.random() * 0.6)
                equity += win_var * dollar_per_pt
            else:
                # Add some variance to losses (±30%)
                loss_var = avg_loss_pts * (0.7 + np.random.random() * 0.6)
                equity -= loss_var * dollar_per_pt

            all_curves[sim, t + 1] = equity

            peak = max(peak, equity)
            dd = peak - equity
            max_dd = max(max_dd, dd)

            # Check ruin
            if equity <= ruin_threshold:
                ruin_count += 1
                # Fill remaining with ruin level
                all_curves[sim, t + 1:] = equity
                break

        all_final_pnl[sim] = equity
        all_max_drawdown[sim] = max_dd

    # Kelly criterion
    # f* = (p * b - q) / b where p=win_rate, q=1-p, b=avg_win/avg_loss
    b = avg_win_pts / avg_loss_pts if avg_loss_pts > 0 else 1
    q = 1 - win_rate
    kelly = (win_rate * b - q) / b if b > 0 else 0
    kelly = max(0, kelly)  # can't be negative

    # Percentile curves
    curve_median = np.median(all_curves, axis=0).tolist()
    curve_upper = np.percentile(all_curves, 75, axis=0).tolist()
    curve_lower = np.percentile(all_curves, 25, axis=0).tolist()
    curve_worst = np.percentile(all_curves, 5, axis=0).tolist()
    curve_best = np.percentile(all_curves, 95, axis=0).tolist()

    # Profit target probabilities
    targets = [1000, 2000, 5000, 10000, 20000, 50000]
    profit_target_probs = {}
    for tgt in targets:
        prob = float(np.sum(all_final_pnl >= tgt) / num_simulations * 100)
        profit_target_probs[tgt] = round(prob, 1)

    # Drawdown percentiles
    dd_pct_50 = float(np.percentile(all_max_drawdown, 50))
    dd_pct_75 = float(np.percentile(all_max_drawdown, 75))
    dd_pct_95 = float(np.percentile(all_max_drawdown, 95))

    return MonteCarloResults(
        simulations=num_simulations,
        trade_horizon=trade_horizon,
        starting_capital=starting_capital,
        probability_of_ruin=round(ruin_count / num_simulations * 100, 2),
        probability_of_profit=round(
            np.sum(all_final_pnl > 0) / num_simulations * 100, 2
        ),
        median_final_pnl=round(float(np.median(all_final_pnl)), 2),
        mean_final_pnl=round(float(np.mean(all_final_pnl)), 2),
        pct_5=round(float(np.percentile(all_final_pnl, 5)), 2),
        pct_25=round(float(np.percentile(all_final_pnl, 25)), 2),
        pct_50=round(float(np.percentile(all_final_pnl, 50)), 2),
        pct_75=round(float(np.percentile(all_final_pnl, 75)), 2),
        pct_95=round(float(np.percentile(all_final_pnl, 95)), 2),
        avg_max_drawdown=round(float(np.mean(all_max_drawdown)), 2),
        worst_max_drawdown=round(float(np.max(all_max_drawdown)), 2),
        median_max_drawdown=round(float(np.median(all_max_drawdown)), 2),
        kelly_fraction=round(kelly, 4),
        half_kelly_fraction=round(kelly / 2, 4),
        curve_median=curve_median,
        curve_upper=curve_upper,
        curve_lower=curve_lower,
        curve_worst=curve_worst,
        curve_best=curve_best,
        profit_target_probs=profit_target_probs,
        drawdown_pct_50=round(dd_pct_50, 2),
        drawdown_pct_75=round(dd_pct_75, 2),
        drawdown_pct_95=round(dd_pct_95, 2),
    )
