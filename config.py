"""
SPX PROPHET — LEGENDARY EDITION
Configuration & Constants
"""

# ─── Strategy Parameters ─────────────────────────────────────────────
SLOPE = 1.04  # points per hour
NUM_LINES = 6
POSITION_SIZE_ES = 2
POINT_VALUE_ES = 50  # $ per point per contract
STOP_POINTS = 5
BREAKEVEN_TRIGGER = 5  # points in favor
DAILY_LOSS_LIMIT = 400  # dollars
OTM_STRIKES = 4  # for SPX options

# ─── Time Windows (CT) ───────────────────────────────────────────────
PIVOT_WINDOW_START = 12  # 12:00 PM CT
PIVOT_WINDOW_END = 15    # 3:00 PM CT
EXTENDED_PIVOT_END = 20  # 8:00 PM CT
LINES_LOCK_HOUR = 8      # 8:30 AM CT
LINES_LOCK_MINUTE = 30
TRADING_START = 9         # 9:00 AM CT
TRADING_END = 12          # 12:00 PM CT
OVERNIGHT_START = 17      # 5:00 PM CT
OVERNIGHT_END_HOUR = 8
OVERNIGHT_END_MIN = 30

# ─── Re-entry limits ─────────────────────────────────────────────────
REENTRY_LIMIT_EARLY = 2   # 9:00–11:00 AM
REENTRY_LIMIT_LATE = 1    # 11:00 AM–12:00 PM
REENTRY_EARLY_END = 11    # boundary hour

# ─── Data ─────────────────────────────────────────────────────────────
ES_SYMBOL = "ES=F"
SPX_SYMBOL = "^GSPC"
VIX_SYMBOL = "^VIX"
DATA_LOOKBACK_DAYS = 7
TIMEZONE = "US/Central"

# ─── UI Colors ────────────────────────────────────────────────────────
COLORS = {
    "bg_primary": "#020209",
    "bg_card": "#0c0c1f",
    "bg_card_alt": "#0a0a1a",
    "accent_cyan": "#00d4ff",
    "accent_purple": "#7B2CBF",
    "accent_gold": "#f0c040",
    "bullish": "#00ff88",
    "bearish": "#ff0055",
    "warning": "#ff9500",
    "text_primary": "#e8e8f0",
    "text_muted": "#a0a0c0",
    "text_dim": "#555577",
    "border": "#1a1a35",
    "glow_cyan": "rgba(0, 212, 255, 0.2)",
    "glow_green": "rgba(0, 255, 136, 0.2)",
    "glow_red": "rgba(255, 0, 85, 0.2)",
}

LINE_COLORS_DISPLAY = {
    "upper_ascending": "#FF4444",
    "lower_ascending": "#FF4444",
    "upper_descending": "#00FF88",
    "lower_descending": "#00FF88",
    "extreme_ascending": "#a0a0c0",
    "extreme_descending": "#a0a0c0",
}

LINE_COLORS = {
    "upper_ascending": "#FF4444",    # Red — ascending from upper pivot
    "lower_ascending": "#FF4444",    # Red — ascending from lower pivot
    "upper_descending": "#00FF88",   # Green — descending from upper pivot
    "lower_descending": "#00FF88",   # Green — descending from lower pivot
    "extreme_ascending": "#a0a0c0",  # Silver — ascending from RTH low
    "extreme_descending": "#a0a0c0", # Silver — descending from RTH high
}

LINE_LABELS = {
    "upper_ascending": "UA ↗",
    "upper_descending": "UD ↘",
    "lower_ascending": "LA ↗",
    "lower_descending": "LD ↘",
    "extreme_ascending": "EA ↗",
    "extreme_descending": "ED ↘",
}

# ─── VIX Regime Thresholds (NEW — PROFITABILITY ENHANCEMENT) ─────────
VIX_REGIME = {
    "low": 14,        # Below: tight ranges, fade aggressively
    "normal": 20,     # 14–20: standard rules
    "elevated": 28,   # 20–28: widen stops, reduce size
    "extreme": 28,    # Above: halt or paper-trade only
}

# ─── Session Quality Score Weights (NEW) ─────────────────────────────
SESSION_QUALITY_WEIGHTS = {
    "vix_regime": 0.25,
    "range_percentile": 0.20,
    "gap_size": 0.15,
    "time_of_week": 0.10,
    "pivot_clarity": 0.15,
    "line_convergence": 0.15,
}

# ─── Confluence Zone Settings (NEW) ──────────────────────────────────
CONFLUENCE_THRESHOLD = 3.0   # points — if two lines within this, it's a confluence zone
CONFLUENCE_BONUS_WEIGHT = 1.5  # signal strength multiplier at confluence

# ─── Trade Journal Fields (NEW) ──────────────────────────────────────
JOURNAL_FIELDS = [
    "date", "time", "direction", "entry_line", "entry_price",
    "target_line", "target_price", "stop_price", "result_pts",
    "result_dollars", "vix_at_entry", "session_quality", "notes",
]

# ─── Macro Event Calendar ────────────────────────────────────────────
# Events that blow through lines — need special handling
MACRO_EVENT_TYPES = {
    "FOMC": {
        "severity": "extreme",
        "recommendation": "SIT OUT",
        "buffer_minutes_before": 30,
        "buffer_minutes_after": 60,
        "description": "Federal Reserve interest rate decision & statement",
    },
    "FOMC_MINUTES": {
        "severity": "high",
        "recommendation": "HALF SIZE",
        "buffer_minutes_before": 15,
        "buffer_minutes_after": 45,
        "description": "FOMC meeting minutes release",
    },
    "CPI": {
        "severity": "extreme",
        "recommendation": "SIT OUT first 30 min",
        "buffer_minutes_before": 5,
        "buffer_minutes_after": 30,
        "description": "Consumer Price Index release (8:30 AM ET)",
    },
    "PPI": {
        "severity": "high",
        "recommendation": "HALF SIZE first 30 min",
        "buffer_minutes_before": 5,
        "buffer_minutes_after": 30,
        "description": "Producer Price Index release (8:30 AM ET)",
    },
    "NFP": {
        "severity": "extreme",
        "recommendation": "SIT OUT first 30 min",
        "buffer_minutes_before": 5,
        "buffer_minutes_after": 30,
        "description": "Non-Farm Payrolls (8:30 AM ET / 7:30 AM CT)",
    },
    "JOBLESS_CLAIMS": {
        "severity": "moderate",
        "recommendation": "NORMAL — watch for spike",
        "buffer_minutes_before": 0,
        "buffer_minutes_after": 15,
        "description": "Weekly Initial Jobless Claims (8:30 AM ET)",
    },
    "GDP": {
        "severity": "high",
        "recommendation": "HALF SIZE first 30 min",
        "buffer_minutes_before": 5,
        "buffer_minutes_after": 30,
        "description": "GDP report (8:30 AM ET)",
    },
    "PCE": {
        "severity": "high",
        "recommendation": "HALF SIZE first 30 min",
        "buffer_minutes_before": 5,
        "buffer_minutes_after": 30,
        "description": "Personal Consumption Expenditures (8:30 AM ET)",
    },
    "ISM_MFG": {
        "severity": "moderate",
        "recommendation": "NORMAL — watch for spike",
        "buffer_minutes_before": 0,
        "buffer_minutes_after": 15,
        "description": "ISM Manufacturing Index (10:00 AM ET)",
    },
    "ISM_SVC": {
        "severity": "moderate",
        "recommendation": "NORMAL — watch for spike",
        "buffer_minutes_before": 0,
        "buffer_minutes_after": 15,
        "description": "ISM Services Index (10:00 AM ET)",
    },
    "RETAIL_SALES": {
        "severity": "high",
        "recommendation": "HALF SIZE first 30 min",
        "buffer_minutes_before": 5,
        "buffer_minutes_after": 30,
        "description": "Retail Sales (8:30 AM ET)",
    },
    "OPEX": {
        "severity": "high",
        "recommendation": "HALF SIZE — pin risk",
        "buffer_minutes_before": 0,
        "buffer_minutes_after": 0,
        "description": "Monthly/Quarterly Options Expiration (3rd Friday)",
    },
    "QUAD_WITCH": {
        "severity": "extreme",
        "recommendation": "HALF SIZE — extreme pin risk",
        "buffer_minutes_before": 0,
        "buffer_minutes_after": 0,
        "description": "Quarterly quadruple witching (Mar/Jun/Sep/Dec 3rd Fri)",
    },
}

# Severity colors for UI
MACRO_SEVERITY_COLORS = {
    "extreme": "#ff0055",
    "high": "#ff9500",
    "moderate": "#00d4ff",
    "low": "#00ff88",
}

# ─── Backtesting Parameters ─────────────────────────────────────────
BACKTEST_DEFAULT_DAYS = 30
BACKTEST_MAX_DAYS = 90
BACKTEST_COMMISSION_PER_CONTRACT = 2.25  # round-trip ES commission
BACKTEST_SLIPPAGE_POINTS = 0.25  # per side

# ─── Options P&L Calculator ──────────────────────────────────────────
SPX_OPTIONS_COMMISSION = 0.65  # per contract per side (Tastytrade)
SPX_OPTIONS_MULTIPLIER = 100   # $100 per point per contract
DEFAULT_OPTION_CONTRACTS = 5
RISK_FREE_RATE = 0.045         # approximate for BSM

# ─── Monte Carlo Simulation ──────────────────────────────────────────
MONTE_CARLO_SIMULATIONS = 1000
MONTE_CARLO_TRADE_HORIZON = 200  # simulate 200 trades forward
RUIN_THRESHOLD = -5000            # account considered "ruined" at this drawdown

# ─── Persistent Journal ──────────────────────────────────────────────
JOURNAL_CSV_PATH = "prophet_journal.csv"

# ─── TradingView Webhook ─────────────────────────────────────────────
TV_WEBHOOK_PORT = 8501  # separate from Streamlit's port
TV_WEBHOOK_SECRET = "prophet_legendary"  # simple auth token

# ─── Sound Notifications ─────────────────────────────────────────────
SOUND_ENABLED_DEFAULT = True


