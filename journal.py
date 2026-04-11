"""
SPX PROPHET — Persistent Trade Journal
Saves trade logs to CSV file so they survive across
Streamlit sessions and app restarts.
"""

import os
import datetime as dt
from typing import List, Optional

import pandas as pd
import pytz

from config import JOURNAL_CSV_PATH, TIMEZONE, POSITION_SIZE_ES, POINT_VALUE_ES

CT = pytz.timezone(TIMEZONE)

COLUMNS = [
    "date", "time", "direction", "entry_line", "entry_price",
    "target_price", "stop_price", "exit_price", "exit_reason",
    "result_pts", "result_dollars", "vix_at_entry", "vix_regime",
    "session_quality", "signal_strength", "confluence",
    "contracts", "instrument", "notes",
]


def _get_journal_path() -> str:
    """Return the journal file path, creating it if needed."""
    if not os.path.exists(JOURNAL_CSV_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(JOURNAL_CSV_PATH, index=False)
    return JOURNAL_CSV_PATH


def load_journal() -> pd.DataFrame:
    """Load the full journal from CSV."""
    path = _get_journal_path()
    try:
        df = pd.read_csv(path)
        # Ensure all columns exist
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=COLUMNS)


def save_trade(trade_data: dict) -> bool:
    """Append a single trade to the journal."""
    try:
        df = load_journal()

        # Fill defaults
        now = dt.datetime.now(CT)
        trade_data.setdefault("date", now.strftime("%Y-%m-%d"))
        trade_data.setdefault("time", now.strftime("%H:%M"))
        trade_data.setdefault("contracts", POSITION_SIZE_ES)
        trade_data.setdefault("instrument", "ES")

        # Calculate dollars if not provided
        if "result_dollars" not in trade_data and "result_pts" in trade_data:
            pts = float(trade_data["result_pts"])
            contracts = int(trade_data.get("contracts", POSITION_SIZE_ES))
            trade_data["result_dollars"] = pts * POINT_VALUE_ES * contracts

        new_row = pd.DataFrame([trade_data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(JOURNAL_CSV_PATH, index=False)
        return True
    except Exception as e:
        print(f"Journal save error: {e}")
        return False


def delete_trade(index: int) -> bool:
    """Delete a trade by row index."""
    try:
        df = load_journal()
        if 0 <= index < len(df):
            df = df.drop(index).reset_index(drop=True)
            df.to_csv(JOURNAL_CSV_PATH, index=False)
            return True
        return False
    except Exception:
        return False


def get_journal_stats() -> dict:
    """Compute summary stats from the journal."""
    df = load_journal()
    if df.empty:
        return {
            "total_trades": 0, "winners": 0, "losers": 0,
            "win_rate": 0, "net_pnl_pts": 0, "net_pnl_dollars": 0,
            "avg_win": 0, "avg_loss": 0, "profit_factor": 0,
            "best_trade": 0, "worst_trade": 0,
            "streak_current": 0, "streak_best_win": 0,
            "streak_worst_loss": 0,
            "days_traded": 0,
        }

    df["result_pts"] = pd.to_numeric(df["result_pts"], errors="coerce").fillna(0)
    df["result_dollars"] = pd.to_numeric(df["result_dollars"], errors="coerce").fillna(0)

    winners = df[df["result_pts"] > 0]
    losers = df[df["result_pts"] < 0]

    gross_profit = winners["result_pts"].sum()
    gross_loss = abs(losers["result_pts"].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Streaks
    current_streak = 0
    best_win_streak = 0
    worst_loss_streak = 0
    win_streak = 0
    loss_streak = 0

    for _, row in df.iterrows():
        if row["result_pts"] > 0:
            win_streak += 1
            loss_streak = 0
            best_win_streak = max(best_win_streak, win_streak)
        elif row["result_pts"] < 0:
            loss_streak += 1
            win_streak = 0
            worst_loss_streak = max(worst_loss_streak, loss_streak)
        else:
            win_streak = 0
            loss_streak = 0

    if win_streak > 0:
        current_streak = win_streak
    elif loss_streak > 0:
        current_streak = -loss_streak

    unique_days = df["date"].nunique()

    return {
        "total_trades": len(df),
        "winners": len(winners),
        "losers": len(losers),
        "win_rate": len(winners) / len(df) * 100 if len(df) > 0 else 0,
        "net_pnl_pts": round(df["result_pts"].sum(), 2),
        "net_pnl_dollars": round(df["result_dollars"].sum(), 2),
        "avg_win": round(winners["result_pts"].mean(), 2) if len(winners) > 0 else 0,
        "avg_loss": round(losers["result_pts"].mean(), 2) if len(losers) > 0 else 0,
        "profit_factor": round(pf, 2),
        "best_trade": round(df["result_pts"].max(), 2),
        "worst_trade": round(df["result_pts"].min(), 2),
        "streak_current": current_streak,
        "streak_best_win": best_win_streak,
        "streak_worst_loss": worst_loss_streak,
        "days_traded": unique_days,
    }


def get_daily_pnl() -> pd.DataFrame:
    """Group journal by date and return daily P&L."""
    df = load_journal()
    if df.empty:
        return pd.DataFrame(columns=["date", "pnl_pts", "pnl_dollars", "trades", "win_rate"])

    df["result_pts"] = pd.to_numeric(df["result_pts"], errors="coerce").fillna(0)
    df["result_dollars"] = pd.to_numeric(df["result_dollars"], errors="coerce").fillna(0)

    daily = df.groupby("date").agg(
        pnl_pts=("result_pts", "sum"),
        pnl_dollars=("result_dollars", "sum"),
        trades=("result_pts", "count"),
        winners=("result_pts", lambda x: (x > 0).sum()),
    ).reset_index()

    daily["win_rate"] = (daily["winners"] / daily["trades"] * 100).round(1)
    daily = daily.drop(columns=["winners"])

    return daily


def export_journal_csv() -> str:
    """Return the CSV content as a string for download."""
    df = load_journal()
    return df.to_csv(index=False)
