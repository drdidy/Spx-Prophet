"""
SPX PROPHET — Data Fetcher
Pulls ES, SPX, and VIX data from Yahoo Finance.
Handles timezone conversion and caching.
"""

import datetime as dt
import pytz
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

from config import (
    ES_SYMBOL, SPX_SYMBOL, VIX_SYMBOL,
    DATA_LOOKBACK_DAYS, TIMEZONE,
)

CT = pytz.timezone(TIMEZONE)


def _ensure_ct(df: pd.DataFrame) -> pd.DataFrame:
    """Convert index to Central Time."""
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(CT)
    return df


@st.cache_data(ttl=120)
def fetch_hourly_candles(symbol: str, days: int = DATA_LOOKBACK_DAYS) -> pd.DataFrame:
    """Fetch hourly OHLCV candles."""
    if not YF_AVAILABLE:
        return _generate_demo_data(symbol, days)
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d", interval="1h")
        if df.empty:
            return _generate_demo_data(symbol, days)
        df = _ensure_ct(df)
        return df
    except Exception:
        return _generate_demo_data(symbol, days)


@st.cache_data(ttl=60)
def fetch_current_price(symbol: str) -> float | None:
    """Get last traded price."""
    if not YF_AVAILABLE:
        return None
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        return float(info.get("lastPrice", info.get("regularMarketPrice", 0)))
    except Exception:
        return None


@st.cache_data(ttl=60)
def fetch_vix() -> float:
    """Current VIX level."""
    p = fetch_current_price(VIX_SYMBOL)
    return p if p else 16.5  # fallback


def fetch_es_spx_offset() -> float:
    """Dynamic ES – SPX offset."""
    es = fetch_current_price(ES_SYMBOL)
    spx = fetch_current_price(SPX_SYMBOL)
    if es and spx:
        return es - spx
    return 40.0  # typical fallback


def get_prior_trading_day(ref_date: dt.date) -> dt.date:
    """Return the most recent trading day before ref_date."""
    d = ref_date - dt.timedelta(days=1)
    while d.weekday() >= 5:  # skip weekends
        d -= dt.timedelta(days=1)
    return d


def get_next_trading_day(ref_date: dt.date) -> dt.date:
    """Return the next trading day on or after ref_date.
    If ref_date is a weekday, returns ref_date itself.
    If ref_date is Saturday or Sunday, returns Monday."""
    d = ref_date
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def get_afternoon_candles(df: pd.DataFrame, trade_date: dt.date) -> pd.DataFrame:
    """Extract 11 AM – 4 PM CT candles for a given date.
    Starts at 11 AM to include the candle BEFORE 12 PM as context —
    the 12 PM candle needs an i-1 neighbor for 3-candle pivot detection.
    The pivot search zone is still 12–4 PM (enforced in pivot_detector).
    The 3 PM candle starts at 3 PM and closes at 4 PM, so we go to 4 PM."""
    prior = get_prior_trading_day(trade_date)
    start = CT.localize(dt.datetime.combine(prior, dt.time(11, 0)))
    end = CT.localize(dt.datetime.combine(prior, dt.time(16, 0)))
    mask = (df.index >= start) & (df.index < end)
    return df.loc[mask].copy()


def get_rth_candles(df: pd.DataFrame, trade_date: dt.date) -> pd.DataFrame:
    """Extract full NY RTH session: 8:30 AM – 4:00 PM CT for a given date."""
    prior = get_prior_trading_day(trade_date)
    start = CT.localize(dt.datetime.combine(prior, dt.time(8, 30)))
    end = CT.localize(dt.datetime.combine(prior, dt.time(16, 0)))
    mask = (df.index >= start) & (df.index < end)
    return df.loc[mask].copy()


def get_extended_candles(df: pd.DataFrame, trade_date: dt.date) -> pd.DataFrame:
    """
    Extended pivot search: 8:30 AM through 8 PM CT on the prior trading day.
    
    The spec says extend to 8 PM if no valid pivot in 12–3 PM.
    Real-world experience shows that pivots can form as early as
    10 AM RTH (e.g., Mar 27 2026 — no 12–3 PM pivot, but a clean
    10 AM high wick projected perfectly into Monday's session).
    So we search the full RTH day backward.
    """
    prior = get_prior_trading_day(trade_date)
    start = CT.localize(dt.datetime.combine(prior, dt.time(8, 30)))
    end = CT.localize(dt.datetime.combine(prior, dt.time(20, 0)))
    mask = (df.index >= start) & (df.index < end)
    return df.loc[mask].copy()


# ─── Demo / Fallback Data ────────────────────────────────────────────

def _generate_demo_data(symbol: str, days: int) -> pd.DataFrame:
    """Generate realistic demo data when yfinance is unavailable."""
    import numpy as np

    now = dt.datetime.now(CT)
    base = 5950 if "ES" in symbol or "GSPC" in symbol else 16.5

    periods = days * 7  # ~7 hourly candles per RTH day
    idx = pd.date_range(
        end=now, periods=periods, freq="1h", tz=CT
    )

    np.random.seed(42)
    returns = np.random.normal(0, 0.0008, periods)
    prices = base * np.exp(np.cumsum(returns))

    noise = np.random.uniform(0.5, 3.0, periods)
    df = pd.DataFrame({
        "Open": prices,
        "High": prices + noise,
        "Low": prices - noise,
        "Close": prices + np.random.uniform(-1, 1, periods),
        "Volume": np.random.randint(50000, 300000, periods),
    }, index=idx)

    df["High"] = df[["Open", "Close", "High"]].max(axis=1)
    df["Low"] = df[["Open", "Close", "Low"]].min(axis=1)

    return df
