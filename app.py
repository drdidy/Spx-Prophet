"""
╔══════════════════════════════════════════════════════════════╗
║              SPX PROPHET — LEGENDARY EDITION                ║
║         Rule-Based Trading System for ES / SPX              ║
║                    Version 2.0 · April 2026                 ║
╚══════════════════════════════════════════════════════════════╝
"""

import datetime as dt
import streamlit as st
import pytz
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ─── Page Config (MUST be first Streamlit call) ───────────────────────
st.set_page_config(
    page_title="SPX Prophet · Legendary Edition",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Local Imports ────────────────────────────────────────────────────
from config import (
    SLOPE, TIMEZONE, DAILY_LOSS_LIMIT, POSITION_SIZE_ES, POINT_VALUE_ES,
    STOP_POINTS, CONFLUENCE_THRESHOLD, LINE_COLORS,
    BACKTEST_DEFAULT_DAYS, BACKTEST_MAX_DAYS,
    BACKTEST_COMMISSION_PER_CONTRACT, BACKTEST_SLIPPAGE_POINTS,
    MACRO_SEVERITY_COLORS, COLORS,
    SPX_OPTIONS_COMMISSION, SPX_OPTIONS_MULTIPLIER, DEFAULT_OPTION_CONTRACTS,
    MONTE_CARLO_SIMULATIONS, MONTE_CARLO_TRADE_HORIZON, RUIN_THRESHOLD,
    SOUND_ENABLED_DEFAULT, TV_WEBHOOK_PORT, DATA_LOOKBACK_DAYS,
)
from styles import MAIN_CSS
from data_fetcher import (
    fetch_hourly_candles, fetch_current_price, fetch_vix,
    fetch_es_spx_offset, get_prior_trading_day, get_next_trading_day,
    ES_SYMBOL, SPX_SYMBOL,
)
from pivot_detector import identify_upper_pivot, identify_lower_pivot, identify_rth_high, identify_rth_low
from line_calculator import (
    get_all_four_lines, get_all_six_lines, detect_confluence_zones,
)
from signal_engine import (
    scan_for_signals, compute_session_quality, get_vix_regime,
)
try:
    from ui_components import (
        render_hero, render_lines_panel, render_pivot_panel,
        render_signal_panel, render_session_quality,
        render_confluence_zones, render_chart, render_trade_journal,
        render_9am_levels, render_live_levels,
        render_daily_pnl_card, render_nearest_levels,
        render_event_countdown, render_trade_readiness,
        render_scenario_card, render_trade_card, render_ladder,
    )
except Exception as _ui_err:
    import traceback as _tb
    st.error(f"**ui_components import failed:** {_ui_err}")
    st.code(_tb.format_exc())
    st.stop()
from macro_calendar import (
    get_events_for_date, get_upcoming_events,
    get_event_summary_for_week, get_worst_severity_today,
    is_macro_blackout, fetch_market_news, time_ago,
    get_next_event_countdown, get_week_day_severities,
    EVENT_HISTORICAL_IMPACT,
)
from backtester import run_backtest
from options_calculator import estimate_option_trade
from monte_carlo import run_monte_carlo
from journal import (
    load_journal, save_trade, delete_trade, get_journal_stats,
    get_daily_pnl, export_journal_csv,
)
from tv_webhook import (
    get_alerts, clear_alerts, start_webhook_server,
    get_notification_html,
)

CT = pytz.timezone(TIMEZONE)

# ─── Inject Styles ───────────────────────────────────────────────────
st.markdown(MAIN_CSS, unsafe_allow_html=True)
st.markdown('<div class="grid-bg"></div>', unsafe_allow_html=True)

# ─── Fix Streamlit expander icon glyphs (React re-render safe) ───────
st.markdown("""
<script>
(function() {
    function fixExpanders() {
        document.querySelectorAll('[data-testid="stExpander"] summary').forEach(function(summary) {
            summary.querySelectorAll('span, div').forEach(function(el) {
                var t = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3
                    ? el.childNodes[0].textContent.trim() : '';
                if (t === 'arrow_right' || t === '_arrow_right' ||
                    t === 'expand_more' || t === 'chevron_right' ||
                    t === 'double_arrow_right' || t === 'keyboard_arrow_right') {
                    el.style.setProperty('font-family', "'Material Symbols Rounded'", 'important');
                    el.style.setProperty('font-variation-settings',
                        "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24", 'important');
                }
            });
        });
    }
    var obs = new MutationObserver(fixExpanders);
    obs.observe(document.documentElement, { childList: true, subtree: true });
    fixExpanders();
    setTimeout(fixExpanders, 200);
    setTimeout(fixExpanders, 800);
})();
</script>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR — Manual Overrides & Controls
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙ COMMAND CENTER")
    st.markdown("---")

    # ── Date & Time ──
    st.markdown("##### 📅 DATE & TIME")
    today = dt.date.today()
    # Auto-advance to next trading day if today is a weekend
    default_trade_date = get_next_trading_day(today)
    trade_date = st.date_input("Trading Date", value=default_trade_date, key="trade_date")
    # Always ensure trade_date is a trading day
    trade_date = get_next_trading_day(trade_date)

    time_options = []
    for h in range(0, 24):
        for m in [0, 30]:
            time_options.append(f"{h:02d}:{m:02d}")

    now_ct = dt.datetime.now(CT)
    is_today = (trade_date == now_ct.date())
    if is_today:
        default_time_str = f"{now_ct.hour:02d}:{now_ct.minute // 30 * 30:02d}"
    else:
        # Historical date: default to 9:00 AM CT (trading session open)
        default_time_str = "09:00"
    default_idx = time_options.index(default_time_str) if default_time_str in time_options else 18

    ref_time_str = st.selectbox(
        "Reference Time (CT)",
        time_options,
        index=default_idx,
        key="ref_time",
    )

    ref_hour, ref_min = map(int, ref_time_str.split(":"))

    st.markdown("---")

    # ── Manual Pivot Overrides ──
    st.markdown("##### 🎯 PIVOT OVERRIDES")
    use_manual_pivots = st.checkbox("Enable Manual Pivots", value=False, key="manual_piv")

    manual_upper_price = None
    manual_upper_time = None
    manual_lower_price = None
    manual_lower_time = None

    if use_manual_pivots:
        manual_upper_price = st.number_input(
            "Upper Pivot Price", value=0.0, step=0.25,
            format="%.2f", key="m_up_price",
        )
        manual_upper_time_str = st.selectbox(
            "Upper Pivot Time", time_options, index=24, key="m_up_time"
        )
        manual_lower_price = st.number_input(
            "Lower Pivot Price", value=0.0, step=0.25,
            format="%.2f", key="m_lo_price",
        )
        manual_lower_time_str = st.selectbox(
            "Lower Pivot Time", time_options, index=24, key="m_lo_time"
        )

        if manual_upper_price > 0:
            uh, um = map(int, manual_upper_time_str.split(":"))
            prior = get_prior_trading_day(trade_date)
            manual_upper_time = CT.localize(
                dt.datetime.combine(prior, dt.time(uh, um))
            )
        if manual_lower_price > 0:
            lh, lm = map(int, manual_lower_time_str.split(":"))
            prior = get_prior_trading_day(trade_date)
            manual_lower_time = CT.localize(
                dt.datetime.combine(prior, dt.time(lh, lm))
            )

    st.markdown("---")

    # ── Price Overrides ──
    st.markdown("##### 💰 PRICE OVERRIDES")
    use_price_override = st.checkbox("Override Live Prices", value=False, key="price_ovr")

    override_es = None
    override_vix = None
    if use_price_override:
        override_es = st.number_input(
            "ES Price", value=5950.0, step=0.25, format="%.2f", key="ovr_es"
        )
        override_vix = st.number_input(
            "VIX", value=16.5, step=0.1, format="%.1f", key="ovr_vix"
        )

    st.markdown("---")

    # ── Quick Reference ──
    with st.expander("📋 QUICK REFERENCE"):
        st.markdown(
            '<div style="font-size:0.75rem;line-height:1.6;">'
            '<span class="dim">'
            '<b>Timeframe:</b> HOURLY ONLY<br>'
            '<b>Slope:</b> ' + str(SLOPE) + ' pts/hr<br>'
            '<b>Lines:</b> 4 (UA, UD, LA, LD)<br>'
            '<b>Pivot Window:</b> 12&ndash;3 PM CT prior day<br>'
            '<b>Lines Lock:</b> Before 8:30 AM CT<br>'
            '<b>Entry:</b> Rejection + hourly CLOSE<br>'
            '<b>Stop:</b> ' + str(STOP_POINTS) + ' pts beyond rejection<br>'
            '<b>Target:</b> Nearest remaining line<br>'
            '<b>Breakeven:</b> At +' + str(STOP_POINTS) + ' pts<br>'
            '<b>Max Loss:</b> $' + str(DAILY_LOSS_LIMIT) + '/day<br>'
            '<b>Size:</b> ' + str(POSITION_SIZE_ES) + ' ES / 4-strike OTM 0DTE<br>'
            '<b>Re-entry 9&ndash;11:</b> Up to 2<br>'
            '<b>Re-entry 11&ndash;12:</b> 1 only'
            '</span></div>',
            unsafe_allow_html=True,
        )

    # ── Auto-refresh ──
    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh (2 min)", value=False, key="auto_ref")
    if auto_refresh:
        st.markdown(
            '<meta http-equiv="refresh" content="120">',
            unsafe_allow_html=True,
        )

    # ── Sound Notifications ──
    sound_enabled = st.checkbox("Sound Notifications", value=SOUND_ENABLED_DEFAULT, key="sound_on")

    # ── TradingView Webhook ──
    st.markdown("---")
    st.markdown("##### 📡 TRADINGVIEW LINK")
    tv_enabled = st.checkbox("Enable TV Webhook", value=False, key="tv_on")
    if tv_enabled:
        webhook_started = start_webhook_server(TV_WEBHOOK_PORT)
        if webhook_started:
            st.success(f"Webhook active on port {TV_WEBHOOK_PORT}")
        st.markdown(
            '<span class="dim" style="font-size:0.65rem;">'
            '<b>Option A — ngrok (recommended):</b><br>'
            'Run: <code>ngrok http ' + str(TV_WEBHOOK_PORT) + '</code><br>'
            'Copy the https:// URL → paste in TV as:<br>'
            '<code>https://xxxx.ngrok.io/webhook</code><br><br>'
            '<b>Option B — direct (port 80):</b><br>'
            'Run Streamlit as admin, then use:<br>'
            '<code>http://YOUR_IP/webhook</code>'
            '</span>',
            unsafe_allow_html=True,
        )

    if st.button("🔄 Refresh Now", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════

# ── Fetch Data ────────────────────────────────────────────────────────
# Fetch enough history to cover the selected trade date
_days_back = max(DATA_LOOKBACK_DAYS, (dt.datetime.now(CT).date() - trade_date).days + 7)
candles = fetch_hourly_candles(ES_SYMBOL, days=_days_back)

es_price = override_es if override_es else (fetch_current_price(ES_SYMBOL) or candles.iloc[-1]["Close"])
vix = override_vix if override_vix else fetch_vix()
offset = fetch_es_spx_offset()
spx_price = es_price - offset

# Reference time for line calculations
ref_datetime = CT.localize(
    dt.datetime.combine(trade_date, dt.time(ref_hour, ref_min))
)

# Determine session status
hour_now = ref_hour
if 9 <= hour_now < 15:
    if hour_now < 12:
        session_status = "RTH"
    else:
        session_status = "RTH · PIVOT WINDOW"
elif 17 <= hour_now or hour_now < 9:
    session_status = "OVERNIGHT"
else:
    session_status = "CLOSED"

# ── Pivot Detection ───────────────────────────────────────────────────
if use_manual_pivots and manual_upper_price and manual_upper_price > 0:
    from pivot_detector import Pivot
    upper_pivot = Pivot(
        price=manual_upper_price,
        time=manual_upper_time,
        candle_idx=0,
        kind="upper",
        confirmed=True,
        green_candle_price=manual_upper_price,
        green_candle_time=manual_upper_time,
        red_candle_price=manual_upper_price,
        red_candle_time=manual_upper_time,
    )
else:
    upper_pivot = identify_upper_pivot(candles, trade_date)

if use_manual_pivots and manual_lower_price and manual_lower_price > 0:
    from pivot_detector import Pivot
    lower_pivot = Pivot(
        price=manual_lower_price,
        time=manual_lower_time,
        candle_idx=0,
        kind="lower",
        confirmed=True,
        green_candle_price=manual_lower_price,
        green_candle_time=manual_lower_time,
        red_candle_price=manual_lower_price,
        red_candle_time=manual_lower_time,
    )
else:
    lower_pivot = identify_lower_pivot(candles, trade_date)

# ── RTH Wick Pivots (Lines 5 & 6) ────────────────────────────────────
# HW ascending = highest bearish HIGH in RTH, LW descending = lowest bullish LOW
rth_high = identify_rth_high(candles, trade_date)
rth_low = identify_rth_low(candles, trade_date)

# ── Line Calculations (all 6 lines) ─────────────────────────────────
lines = get_all_six_lines(upper_pivot, lower_pivot, rth_high, rth_low, ref_datetime)
confluence_zones = detect_confluence_zones(lines, CONFLUENCE_THRESHOLD)

# ── Signal Scan ───────────────────────────────────────────────────────
# Get candles from overnight session start (prior day 5 PM) through trade date
prior_day = get_prior_trading_day(trade_date)
overnight_start = CT.localize(dt.datetime.combine(prior_day, dt.time(17, 0)))
today_candles = candles[candles.index >= overnight_start]

signals = scan_for_signals(
    today_candles, upper_pivot, lower_pivot, rth_high, rth_low, trade_date
)
latest_signal = signals[-1][1] if signals else None

# ── Session Quality Score ─────────────────────────────────────────────
pivots_confirmed = sum([
    1 for p in [upper_pivot, lower_pivot]
    if p is not None and p.confirmed
])

session_quality = compute_session_quality(
    vix=vix,
    candles=candles.tail(14),  # last ~2 trading days
    pivots_confirmed=pivots_confirmed,
    num_confluence_zones=len(confluence_zones),
    trade_date=trade_date,
)


# ═══════════════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════════════

# ── Hero ──
render_hero(es_price, spx_price, vix, offset, ref_datetime, session_status)

# ── Macro events for today ──
today_events = get_events_for_date(trade_date)
today_severity, today_macro_rec = get_worst_severity_today(trade_date)
macro_blackout = is_macro_blackout(ref_datetime)

# ── Sound notification for new signals ──
if latest_signal and latest_signal.direction != "NEUTRAL" and sound_enabled:
    sound_type = "long" if latest_signal.direction == "LONG" else "short"
    st.markdown(get_notification_html(sound_type), unsafe_allow_html=True)

# ── Main Content Tabs ──
tab_dashboard, tab_chart, tab_options, tab_macro, tab_backtest, tab_montecarlo, tab_journal, tab_tv, tab_analysis = st.tabs([
    "⚡ DASHBOARD", "📊 CHART", "🧮 OPTIONS", "⚠️ MACRO", "🔬 BACKTEST", "🎰 MONTE CARLO", "💰 JOURNAL", "📡 TV ALERTS", "🛡️ EDGE"
])

# ════════════════════════════════════════════════════════════════
#  TAB 1: DASHBOARD
# ════════════════════════════════════════════════════════════════
with tab_dashboard:
    # ── Load journal data (needed by P&L expander) ──
    journal_df = load_journal()
    today_str = trade_date.strftime("%Y-%m-%d")
    today_journal = journal_df[journal_df["date"] == today_str] if not journal_df.empty else pd.DataFrame()
    today_realized_pnl = float(
        pd.to_numeric(today_journal["result_dollars"], errors="coerce").fillna(0).sum()
    ) if not today_journal.empty else 0.0

    # ── Critical blackout banner (only when active) ──
    if macro_blackout:
        worst_color = MACRO_SEVERITY_COLORS.get(today_severity, "#888")
        event_names = ", ".join(e.title for e in today_events)
        st.markdown(
            f'<div class="macro-warn" style="border-color:{worst_color};">'
            f'<span class="lbl" style="color:{worst_color}">⛔ MACRO BLACKOUT ACTIVE</span><br>'
            f'<span class="sm" style="color:{worst_color}">{event_names}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Find alternate signal (opposite direction from primary) ──
    alt_signal = None
    if latest_signal and latest_signal.direction != "NEUTRAL":
        opposite_dir = "SHORT" if latest_signal.direction == "LONG" else "LONG"
        for _, sig in reversed(signals):
            if sig.direction == opposite_dir:
                alt_signal = sig
                break

    # ── Core 3-panel row: Scenario · Primary Trade · Alternate Trade ──
    sc_col, primary_col, alt_col = st.columns([1, 1.2, 1.2])

    with sc_col:
        render_scenario_card(
            session_quality, latest_signal, vix,
            pivots_confirmed, macro_blackout, today_severity,
        )

    with primary_col:
        render_trade_card(latest_signal, offset, "PRIMARY")

    with alt_col:
        render_trade_card(alt_signal, offset, "ALTERNATE")

    # ── Price Ladder (full width) ──
    render_ladder(lines, es_price, offset)

    # ── Expanders: everything else ──
    with st.expander("📊 Daily P&L · Budget · Readiness"):
        pnl_col, countdown_col, readiness_col = st.columns(3)
        with pnl_col:
            render_daily_pnl_card(journal_df, trade_date, DAILY_LOSS_LIMIT)
        with countdown_col:
            week_events = get_upcoming_events(trade_date, days_ahead=7)
            render_event_countdown(week_events, ref_datetime)
        with readiness_col:
            render_trade_readiness(
                vix=vix,
                pivots_confirmed=pivots_confirmed,
                session_quality_grade=session_quality.grade,
                daily_pnl=today_realized_pnl,
                daily_loss_limit=DAILY_LOSS_LIMIT,
                macro_blackout=macro_blackout,
            )

    with st.expander("📐 Lines · Pivots · Confluence"):
        render_lines_panel(lines, es_price, offset)
        piv_col2, conf_col2 = st.columns([3, 2])
        with piv_col2:
            render_pivot_panel(upper_pivot, lower_pivot)
        with conf_col2:
            render_confluence_zones(confluence_zones, offset)

    if today_events:
        sev_label = today_severity.upper() if today_severity else "EVENT"
        with st.expander(f"⚠️ Macro Events Today · {sev_label}"):
            worst_color = MACRO_SEVERITY_COLORS.get(today_severity, "#888")
            event_names = ", ".join(e.title for e in today_events)
            st.markdown(
                f'<div style="padding:0.8rem 1rem;border-left:4px solid {worst_color};'
                f'background:rgba(255,255,255,0.02);border-radius:0 8px 8px 0;">'
                f'<div class="sm" style="color:{worst_color};font-weight:600;">{event_names}</div>'
                f'<div class="dim" style="margin-top:6px;">{today_macro_rec}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    if signals:
        with st.expander(f"📈 Signal History · {len(signals)} today"):
            for sig_time, sig in signals:
                color = COLORS["bullish"] if sig.direction == "LONG" else COLORS["bearish"]
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:1rem;padding:0.5rem 0;'
                    f'border-bottom:1px solid #1a1a35;">'
                    f'<span class="sm" style="color:{COLORS["text_muted"]};min-width:80px;">'
                    f'{sig_time.strftime("%I:%M %p")}</span>'
                    f'<span class="sm" style="color:{color};font-weight:600;min-width:60px;">'
                    f'{sig.direction}</span>'
                    f'<span class="dim">at {sig.entry_line} · {sig.entry_price:,.2f}</span>'
                    f'<span class="sm" style="color:{COLORS["accent_gold"]};">'
                    f'R:R {sig.rr_ratio:.1f}</span>'
                    f'<span class="strength-{sig.signal_strength.lower()}">'
                    f'{sig.signal_strength}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ════════════════════════════════════════════════════════════════
#  TAB 2: CHART
# ════════════════════════════════════════════════════════════════
with tab_chart:
    # ── Timeframe selector (radio buttons) ──
    _tf_options = ["Today", "24h", "2 Days", "3 Days", "1 Week"]
    _tf_map = {"Today": None, "24h": 24, "2 Days": 48, "3 Days": 72, "1 Week": 168}
    chart_tf = st.radio("Timeframe", _tf_options, index=1, horizontal=True, key="chart_tf")
    _tf_hours = _tf_map[chart_tf]
    if _tf_hours is None:
        _today_9am = CT.localize(dt.datetime.combine(trade_date, dt.time(9, 0)))
        chart_candles = candles[candles.index >= _today_9am]
        if len(chart_candles) < 2:
            chart_candles = candles.tail(12)
    else:
        chart_candles = candles.tail(_tf_hours)

    # ── Prior day RTH high / low ──
    _prior_date = get_prior_trading_day(trade_date)
    _prior_rth_start = CT.localize(dt.datetime.combine(_prior_date, dt.time(8, 30)))
    _prior_rth_end = CT.localize(dt.datetime.combine(_prior_date, dt.time(15, 0)))
    _prior_rth = candles[(candles.index >= _prior_rth_start) & (candles.index <= _prior_rth_end)]
    _prior_day_high = float(_prior_rth["High"].max()) if len(_prior_rth) > 0 else None
    _prior_day_low = float(_prior_rth["Low"].min()) if len(_prior_rth) > 0 else None

    chart_col, panel_col = st.columns([7, 3])

    with chart_col:
        render_chart(
            chart_candles,
            upper_pivot, lower_pivot,
            lines, es_price,
            signals=signals,
            confluence_zones=confluence_zones,
            rth_high=rth_high,
            rth_low=rth_low,
            trade_date=trade_date,
            prior_day_high=_prior_day_high,
            prior_day_low=_prior_day_low,
        )

    with panel_col:
        # Panel 1 — 9 AM Levels (static, with distance column)
        st.markdown('<div class="pc pc-gold">', unsafe_allow_html=True)
        render_9am_levels(upper_pivot, lower_pivot, rth_high, rth_low, trade_date, offset, es_price=es_price)
        st.markdown('</div>', unsafe_allow_html=True)

        # Panel 2 — Live Levels (next hour, with distance column)
        st.markdown('<div class="pc" style="border-left:4px solid #00d4ff;">', unsafe_allow_html=True)
        render_live_levels(upper_pivot, lower_pivot, rth_high, rth_low, trade_date, offset, es_price, ref_hour)
        st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 3: OPTIONS P&L CALCULATOR
# ════════════════════════════════════════════════════════════════
with tab_options:
    st.markdown(
        '<div class="pc pc-gold">'
        '<span class="lbl"><span style="font-size:2rem;">&#129518;</span> 0DTE SPX OPTIONS CALCULATOR</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Quick Preset Buttons ──────────────────────────────────────
    st.markdown(
        '<div class="pc">'
        '<span class="lbl"><span style="font-size:2rem;">&#9889;</span> QUICK PRESETS</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    preset_c1, preset_c2, preset_c3 = st.columns(3)
    with preset_c1:
        if st.button("Conservative (2 OTM)", key="preset_conservative", use_container_width=True):
            st.session_state["opt_preset_otm"] = 2
            st.session_state["opt_preset_target"] = 5.0
            st.session_state["opt_preset_stop"] = 3.0
    with preset_c2:
        if st.button("Standard (4 OTM)", key="preset_standard", use_container_width=True):
            st.session_state["opt_preset_otm"] = 4
            st.session_state["opt_preset_target"] = 8.0
            st.session_state["opt_preset_stop"] = 5.0
    with preset_c3:
        if st.button("Aggressive (ATM)", key="preset_aggressive", use_container_width=True):
            st.session_state["opt_preset_otm"] = 0
            st.session_state["opt_preset_target"] = 12.0
            st.session_state["opt_preset_stop"] = 6.0

    _preset_target = st.session_state.get(
        "opt_preset_target",
        float(latest_signal.reward_pts) if latest_signal else 8.0,
    )
    _preset_stop = st.session_state.get(
        "opt_preset_stop",
        float(latest_signal.risk_pts) if latest_signal else 5.0,
    )

    oc1, oc2 = st.columns(2)
    with oc1:
        opt_direction = (
            latest_signal.direction
            if (latest_signal and latest_signal.direction != "NEUTRAL")
            else "LONG"
        )
        opt_dir = st.selectbox(
            "Direction", ["LONG", "SHORT"],
            index=0 if opt_direction == "LONG" else 1, key="opt_dir",
        )
        opt_target_pts = st.number_input(
            "Target (ES pts)", value=_preset_target, step=0.5, key="opt_tgt",
        )
        opt_stop_pts = st.number_input(
            "Stop (ES pts)", value=_preset_stop, step=0.5, key="opt_stp",
        )
    with oc2:
        opt_contracts = st.number_input(
            "Contracts", value=DEFAULT_OPTION_CONTRACTS,
            min_value=1, max_value=50, key="opt_ct",
        )
        opt_hours = st.slider(
            "Hours to Expiry", 0.5, 6.5, 5.0, step=0.5, key="opt_tte",
        )
        opt_vix_input = st.number_input("VIX", value=vix, step=0.5, key="opt_vix")

    if st.button("Calculate Options P&L", type="primary", use_container_width=True, key="calc_opt"):
        import config as _cfg
        _otm_override = st.session_state.get("opt_preset_otm", None)
        _orig_otm = _cfg.OTM_STRIKES
        if _otm_override is not None:
            _cfg.OTM_STRIKES = _otm_override
        opt_result = estimate_option_trade(
            spx_price=spx_price,
            direction=opt_dir,
            target_pts=opt_target_pts,
            stop_pts=opt_stop_pts,
            vix=opt_vix_input,
            hours_to_expiry=opt_hours,
            contracts=opt_contracts,
        )
        _cfg.OTM_STRIKES = _orig_otm
        st.session_state["opt_result"] = opt_result

    if "opt_result" in st.session_state:
        opt = st.session_state["opt_result"]

        # ── Strike / Premium / P&L cards ──
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">' + opt.option_type + '</span><br>'
                '<span class="big">' + f"{opt.strike:.0f}" + '</span><br>'
                '<span class="dim">Strike</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with r2:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">ENTRY PREMIUM</span><br>'
                '<span class="big">$' + f"{opt.premium_entry:.2f}" + '</span><br>'
                '<span class="dim">per contract</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with r3:
            st.markdown(
                '<div class="pc pc-green" style="text-align:center;">'
                '<span class="lbl">MAX PROFIT</span><br>'
                '<span class="big" style="color:'
                + COLORS["bullish"] + ';">$' + f"{opt.net_profit:+,.0f}" + '</span><br>'
                '<span class="dim">Premium &rarr; $'
                + f"{opt.premium_target:.2f}" + '</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with r4:
            st.markdown(
                '<div class="pc pc-red" style="text-align:center;">'
                '<span class="lbl">MAX LOSS</span><br>'
                '<span class="big" style="color:'
                + COLORS["bearish"] + ';">-$' + f"{opt.net_loss:,.0f}" + '</span><br>'
                '<span class="dim">Premium &rarr; $'
                + f"{opt.premium_stop:.2f}" + '</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        # ── Greeks Display ────────────────────────────────────────
        st.markdown(
            '<div class="pc">'
            '<span class="lbl">'
            '<span class="icon" style="font-size:2rem;">&#916;</span>'
            'GREEKS AT ENTRY</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        _delta_color = COLORS["accent_cyan"]
        _gamma_color = COLORS["accent_purple"]
        _theta_color = COLORS["bearish"]
        g1, g2, g3 = st.columns(3)
        with g1:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">DELTA</span><br>'
                '<span class="big" style="color:' + _delta_color + ';">'
                + f"{opt.delta_approx:.4f}" + '</span><br>'
                '<span class="dim">$ per 1pt SPX move</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with g2:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">GAMMA</span><br>'
                '<span class="big" style="color:' + _gamma_color + ';">'
                + f"{opt.gamma_approx:.6f}" + '</span><br>'
                '<span class="dim">Delta change per 1pt</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with g3:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">THETA</span><br>'
                '<span class="big" style="color:' + _theta_color + ';">'
                + f"{opt.theta_approx:.2f}" + '</span><br>'
                '<span class="dim">$/day time decay</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        # ── Break-Even Visualization ──────────────────────────────
        _be_dir = "UP" if opt.option_type == "CALL" else "DOWN"
        _be_arrow = "&#9650;" if opt.option_type == "CALL" else "&#9660;"
        _be_color = COLORS["bullish"] if opt.option_type == "CALL" else COLORS["bearish"]
        st.markdown(
            '<div class="pc" style="text-align:center;padding:1.2rem;">'
            '<span class="lbl">'
            '<span class="icon" style="font-size:2rem;">&#127919;</span>'
            'BREAK-EVEN TARGET</span><br><br>'
            '<span style="font-size:2.2rem;font-weight:800;color:' + _be_color + ';">'
            + _be_arrow + ' ' + f"{opt.breakeven_move:.1f}" + ' pts ' + _be_dir
            + '</span><br>'
            '<span class="dim" style="font-size:1rem;">'
            'SPX needs to move <b>' + f"{opt.breakeven_move:.1f}"
            + '</b> points ' + _be_dir
            + ' to break even (including commissions)</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Risk Warning for deep OTM + <1hr expiry ──────────────
        _is_deep_otm = abs(opt.strike - opt.underlying) > 20
        _is_low_tte = opt.time_to_expiry_hours < 1.0
        if _is_deep_otm and _is_low_tte:
            st.markdown(
                '<div class="pc" style="text-align:center;padding:1rem;'
                'border:2px solid ' + COLORS["bearish"] + ';'
                'background:rgba(255,0,85,0.12);">'
                '<span style="font-size:2rem;">&#9888;&#65039;</span><br>'
                '<span class="lbl" style="color:'
                + COLORS["bearish"] + ';">'
                'EXTREME THETA DECAY WARNING</span><br><br>'
                '<span class="sm" style="color:'
                + COLORS["bearish"] + ';">'
                'This option is <b>deep OTM</b> ('
                + f"{abs(opt.strike - opt.underlying):.0f}"
                + ' pts from spot) with <b>less than 1 hour</b> to expiry.<br>'
                'Theta is decaying at an accelerating rate. '
                'Premium can lose 50-80% of value in the final hour.<br>'
                '<b>Extremely high probability of expiring worthless.</b>'
                '</span></div>',
                unsafe_allow_html=True,
            )

        # ── Trade Summary ─────────────────────────────────────────
        st.markdown(
            '<div class="pc">'
            '<span class="lbl">TRADE SUMMARY</span><br><br>'
            '<span class="sm">'
            + str(opt.contracts) + 'x SPX ' + f"{opt.strike:.0f}" + ' '
            + opt.option_type + ' @ $' + f"{opt.premium_entry:.2f}" + '<br>'
            'Cost basis: $'
            + f"{opt.premium_entry * opt.contracts * SPX_OPTIONS_MULTIPLIER:,.0f}" + '<br>'
            'Commission (RT): $' + f"{opt.commission_total:.2f}" + '<br>'
            'Breakeven move: ' + f"{opt.breakeven_move:.1f}" + ' SPX pts<br>'
            'Options R:R: <b style="color:' + COLORS["accent_gold"] + ';">'
            + f"{opt.rr_ratio:.2f}" + '</b><br>'
            'Time to expiry: ' + f"{opt.time_to_expiry_hours:.1f}" + ' hrs'
            '</span></div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════════
#  TAB 4: MACRO CALENDAR
# ════════════════════════════════════════════════════════════════
with tab_macro:
    st.markdown(
        '<div class="pc pc-gold">'
        '<span class="lbl"><span style="font-size:2rem;">&#9888;&#65039;</span> MACRO EVENT CALENDAR</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Countdown to Next Event ───────────────────────────────────
    _next_evt = get_next_event_countdown(trade_date)
    if _next_evt is not None:
        _ne = _next_evt["event"]
        _ne_color = MACRO_SEVERITY_COLORS.get(_ne.severity, "#888")
        _countdown_str = ""
        if _next_evt["days"] > 0:
            _countdown_str += str(_next_evt["days"]) + "d "
        _countdown_str += str(_next_evt["hours"]) + "h " + str(_next_evt["minutes"]) + "m"
        st.markdown(
            '<div class="pc" style="text-align:center;padding:1rem;">'
            '<span class="lbl">'
            '<span class="icon" style="font-size:2rem;">&#9200;</span>'
            'NEXT EVENT COUNTDOWN</span><br><br>'
            '<span style="font-size:1.8rem;font-weight:800;color:'
            + _ne_color + ';">' + _ne.title + '</span><br>'
            '<span style="font-size:2.4rem;font-weight:900;color:'
            + COLORS["accent_cyan"] + ';font-family:Orbitron,sans-serif;">'
            + _countdown_str + '</span><br>'
            '<span class="dim">'
            + _ne.date.strftime("%a %b %d")
            + (' at ' + _ne.time_ct.strftime("%I:%M %p CT") if _ne.time_ct else ' (All Day)')
            + '</span></div>',
            unsafe_allow_html=True,
        )

    # ── This Week's Overview Cards ──
    week_summary = get_event_summary_for_week(trade_date)

    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        st.markdown(
            '<div class="pc" style="text-align:center;">'
            '<span class="lbl">THIS WEEK</span><br>'
            '<span class="big">'
            + str(week_summary["total_events"]) + '</span><br>'
            '<span class="dim">events</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with wc2:
        extreme_count = len(week_summary["extreme_days"])
        e_color = COLORS["bearish"] if extreme_count > 0 else COLORS["bullish"]
        st.markdown(
            '<div class="pc" style="text-align:center;">'
            '<span class="lbl">EXTREME DAYS</span><br>'
            '<span class="big" style="color:' + e_color + ';">'
            + str(extreme_count) + '</span><br>'
            '<span class="dim">sit-out days</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with wc3:
        clear_count = len(week_summary["clear_days"])
        st.markdown(
            '<div class="pc" style="text-align:center;">'
            '<span class="lbl">CLEAR DAYS</span><br>'
            '<span class="big" style="color:' + COLORS["bullish"] + ';">'
            + str(clear_count) + '</span><br>'
            '<span class="dim">full-size trading</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Weekly Heatmap ────────────────────────────────────────────
    _heatmap_colors = {
        "clear": COLORS["bullish"],
        "low": "#66bb6a",
        "moderate": COLORS["accent_gold"],
        "high": COLORS["warning"],
        "extreme": COLORS["bearish"],
    }
    _week_days = get_week_day_severities(trade_date)
    _heatmap_cells = ""
    for _wd in _week_days:
        _cell_bg = _heatmap_colors.get(_wd["severity"], "#333")
        _cell_label = _wd["severity"].upper()
        _is_sel = " border:2px solid " + COLORS["accent_cyan"] + ";" if _wd["date"] == trade_date else ""
        _evt_names = ", ".join(e.title for e in _wd["events"]) if _wd["events"] else "Clear"
        _heatmap_cells += (
            '<div style="text-align:center;padding:0.6rem 0.3rem;'
            'border-radius:8px;background:rgba(255,255,255,0.03);' + _is_sel + '">'
            '<span style="font-size:0.75rem;font-weight:700;color:'
            + COLORS["text_muted"] + ';font-family:Orbitron,sans-serif;">'
            + _wd["day_name"].upper() + '</span><br>'
            '<span style="font-size:0.7rem;color:' + COLORS["text_dim"] + ';">'
            + _wd["date"].strftime("%b %d") + '</span><br>'
            '<div style="margin:0.3rem auto;width:2.5rem;height:2.5rem;'
            'border-radius:50%;background:' + _cell_bg + ';opacity:0.85;'
            'display:flex;align-items:center;justify-content:center;">'
            '<span style="font-size:0.5rem;font-weight:800;color:#000;">'
            + _cell_label[:3] + '</span></div>'
            '<span style="font-size:0.6rem;color:' + COLORS["text_dim"] + ';">'
            + _evt_names + '</span>'
            '</div>'
        )
    st.markdown(
        '<div class="pc">'
        '<span class="lbl">'
        '<span class="icon" style="font-size:2rem;">&#128197;</span>'
        'WEEKLY HEATMAP</span><br><br>'
        '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.5rem;">'
        + _heatmap_cells + '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Upcoming Events List ──
    look_ahead = st.slider("Look ahead (days)", 7, 30, 14, key="macro_ahead")
    upcoming = get_upcoming_events(trade_date, look_ahead)

    if upcoming:
        for event in upcoming:
            sev_color = MACRO_SEVERITY_COLORS.get(event.severity, "#888")
            time_str = event.time_ct.strftime("%I:%M %p CT") if event.time_ct else "All Day"
            is_today = event.date == trade_date

            today_badge = ""
            if is_today:
                today_badge = (
                    '<span style="background:' + sev_color
                    + ';color:#fff;padding:3px 10px;border-radius:20px;'
                    'font-size:0.55rem;font-weight:700;margin-left:8px;'
                    'font-family:Orbitron,sans-serif;letter-spacing:1px;">'
                    'TODAY</span>'
                )

            _impact_note = EVENT_HISTORICAL_IMPACT.get(event.event_type, "")
            _impact_html = ""
            if _impact_note:
                _impact_html = (
                    '<br><span style="font-size:0.7rem;color:'
                    + COLORS["accent_gold"] + ';font-style:italic;">'
                    + _impact_note + '</span>'
                )

            _today_bg = "background:rgba(255,0,85,0.05);border-radius:8px;" if is_today else ""
            st.markdown(
                '<div style="display:flex;align-items:center;gap:1rem;'
                'padding:0.6rem 0.5rem;border-bottom:1px solid #1a1a35;'
                + _today_bg + '">'
                '<span class="sm" style="color:'
                + COLORS["text_muted"] + ';min-width:90px;font-size:0.85rem;">'
                + event.date.strftime("%a %b %d") + '</span>'
                '<span class="sm" style="color:'
                + COLORS["text_muted"] + ';min-width:80px;font-size:0.85rem;">'
                + time_str + '</span>'
                '<span class="line-dot" style="background:' + sev_color + ';"></span>'
                '<span class="sm" style="font-size:0.9rem;">'
                + event.title + today_badge + _impact_html + '</span>'
                '<span class="vix-badge" style="color:#fff;background:'
                + sev_color + ';border:none;margin-left:auto;">'
                + event.severity.upper() + '</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        # ── Severity Legend ──
        st.markdown(
            '<div class="pc">'
            '<span class="lbl">SEVERITY GUIDE</span><br><br>'
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;text-align:center;">'
            '<div>'
            '<span class="line-dot" style="background:'
            + MACRO_SEVERITY_COLORS["extreme"] + ';"></span>'
            '<span class="sm" style="color:'
            + MACRO_SEVERITY_COLORS["extreme"] + ';font-size:0.8rem;">EXTREME</span><br>'
            '<span class="dim" style="font-size:0.7rem;">'
            'SIT OUT entirely<br>FOMC, CPI, NFP, Quad Witch</span></div>'
            '<div>'
            '<span class="line-dot" style="background:'
            + MACRO_SEVERITY_COLORS["high"] + ';"></span>'
            '<span class="sm" style="color:'
            + MACRO_SEVERITY_COLORS["high"] + ';font-size:0.8rem;">HIGH</span><br>'
            '<span class="dim" style="font-size:0.7rem;">'
            'HALF SIZE<br>PPI, PCE, GDP, OPEX</span></div>'
            '<div>'
            '<span class="line-dot" style="background:'
            + MACRO_SEVERITY_COLORS["moderate"] + ';"></span>'
            '<span class="sm" style="color:'
            + MACRO_SEVERITY_COLORS["moderate"] + ';font-size:0.8rem;">MODERATE</span><br>'
            '<span class="dim" style="font-size:0.7rem;">'
            'NORMAL with caution<br>ISM, Jobless Claims</span></div>'
            '<div>'
            '<span class="line-dot" style="background:'
            + MACRO_SEVERITY_COLORS["low"] + ';"></span>'
            '<span class="sm" style="color:'
            + MACRO_SEVERITY_COLORS["low"] + ';font-size:0.8rem;">LOW</span><br>'
            '<span class="dim" style="font-size:0.7rem;">'
            'FULL SIZE<br>Minor releases</span></div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="pc" style="text-align:center;padding:2rem;">'
            '<span class="sm" style="color:'
            + COLORS["bullish"] + ';">ALL CLEAR</span><br>'
            '<span class="dim">No macro events in the next '
            + str(look_ahead) + ' days</span></div>',
            unsafe_allow_html=True,
        )

    # ── Live Market News Feed ──
    st.markdown(
        '<div class="pc pc-gold">'
        '<span class="lbl">'
        '<span class="icon">\U0001F4F0</span>MARKET NEWS'
        '</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button("Refresh News", key="refresh_news"):
        fetch_market_news.clear()

    try:
        news_items = fetch_market_news(max_items=15)
    except Exception:
        news_items = []

    if news_items:
        news_rows_html = ""
        for item in news_items:
            ago_str = time_ago(item.get("published"))
            src = item.get("source", "")
            title = item.get("title", "")
            link = item.get("link", "")

            # Pick badge color per source
            if "MarketWatch" in src:
                badge_bg = COLORS["accent_gold"]
                badge_fg = "#000"
            elif "CNBC" in src:
                badge_bg = COLORS["accent_cyan"]
                badge_fg = "#000"
            else:
                badge_bg = COLORS["accent_purple"]
                badge_fg = "#fff"

            # Build the title - link or plain text
            if link:
                title_html = (
                    '<a href="' + link + '" target="_blank" rel="noopener" '
                    'style="color:' + COLORS["text_primary"] + ';text-decoration:none;">'
                    + title + '</a>'
                )
            else:
                title_html = (
                    '<span style="color:' + COLORS["text_primary"] + ';">'
                    + title + '</span>'
                )

            news_rows_html += (
                '<div style="display:flex;align-items:center;gap:0.75rem;'
                'padding:0.5rem 0.6rem;border-bottom:1px solid '
                + COLORS["border"] + ';">'
                '<span style="min-width:55px;font-size:0.75rem;color:'
                + COLORS["text_dim"] + ';font-family:Orbitron,sans-serif;'
                'letter-spacing:0.5px;">' + ago_str + '</span>'
                '<span style="font-size:0.65rem;font-weight:700;padding:2px 8px;'
                'border-radius:4px;font-family:Orbitron,sans-serif;'
                'letter-spacing:0.5px;background:' + badge_bg + ';color:'
                + badge_fg + ';min-width:85px;text-align:center;">'
                + src + '</span>'
                '<span style="font-size:0.85rem;">' + title_html + '</span>'
                '</div>'
            )

        st.markdown(
            '<div class="pc">' + news_rows_html + '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="pc" style="text-align:center;padding:1.5rem;">'
            '<span class="dim">'
            'News feed unavailable — check your connection and try Refresh'
            '</span></div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════════
#  TAB 4: BACKTESTER
# ════════════════════════════════════════════════════════════════
with tab_backtest:

    st.markdown(
        '<div class="pc pc-gold">'
        '<span class="lbl"><span style="font-size:2rem;">&#128300;</span> STRATEGY BACKTESTER</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Controls ──
    bt_c1, bt_c2, bt_c3 = st.columns(3)
    with bt_c1:
        bt_days = st.slider(
            "Lookback (days)", 7, BACKTEST_MAX_DAYS, BACKTEST_DEFAULT_DAYS,
            key="bt_days",
            help="How many trading days to test"
        )
    with bt_c2:
        bt_min_rr = st.slider(
            "Min R:R Filter", 0.0, 3.0, 1.0, step=0.25, key="bt_rr",
            help="Only take trades with this R:R or higher"
        )
    with bt_c3:
        bt_skip_macro = st.checkbox(
            "Skip extreme macro days", value=True, key="bt_macro",
            help="Exclude FOMC/CPI/NFP days from backtest"
        )

    if st.button("RUN BACKTEST", type="primary", use_container_width=True, key="run_bt"):
        end = trade_date
        start = end - dt.timedelta(days=bt_days)

        bt_candles = fetch_hourly_candles(ES_SYMBOL, days=bt_days + 7)

        with st.spinner("Running backtest..."):
            results = run_backtest(
                candles=bt_candles,
                vix_data=None,
                start_date=start,
                end_date=end,
                min_rr=bt_min_rr,
                exclude_macro_extreme=bt_skip_macro,
            )

        st.session_state["bt_results"] = results

    # ── Display Results ──
    if "bt_results" in st.session_state:
        r = st.session_state["bt_results"]

        # Top-line stats
        s1, s2, s3, s4, s5 = st.columns(5)

        with s1:
            pnl_color = COLORS["bullish"] if r.net_pnl_dollars >= 0 else COLORS["bearish"]
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">NET P&L</span><br>'
                '<span class="big" style="color:' + pnl_color + ';">'
                + f"${r.net_pnl_dollars:+,.0f}" + '</span><br>'
                '<span class="dim">' + f"{r.net_pnl_pts:+.1f}" + ' pts</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with s2:
            wr_color = COLORS["bullish"] if r.win_rate >= 50 else COLORS["bearish"]
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">WIN RATE</span><br>'
                '<span class="big" style="color:' + wr_color + ';">'
                + f"{r.win_rate:.1f}" + '%</span><br>'
                '<span class="dim">' + str(r.winners) + 'W / ' + str(r.losers) + 'L</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with s3:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">PROFIT FACTOR</span><br>'
                '<span class="big">' + f"{r.profit_factor:.2f}" + '</span><br>'
                '<span class="dim">Avg R:R ' + f"{r.avg_rr_ratio:.2f}" + '</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with s4:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">MAX DRAWDOWN</span><br>'
                '<span class="big" style="color:' + COLORS["bearish"] + ';">'
                + f"${r.max_drawdown_dollars:,.0f}" + '</span><br>'
                '<span class="dim">' + str(r.max_consecutive_losses) + ' consec losses</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with s5:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">TOTAL TRADES</span><br>'
                '<span class="big">' + str(r.total_trades) + '</span><br>'
                '<span class="dim">' + str(r.trading_days) + ' days</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        # ── Expectancy ──
        if r.total_trades > 0:
            win_pct = r.win_rate / 100.0
            loss_pct = 1.0 - win_pct
            avg_win_d = (r.avg_win_pts * POINT_VALUE_ES * POSITION_SIZE_ES) if r.avg_win_pts else 0
            avg_loss_d = abs(r.avg_loss_pts * POINT_VALUE_ES * POSITION_SIZE_ES) if r.avg_loss_pts else 0
            expectancy = (win_pct * avg_win_d) - (loss_pct * avg_loss_d)
            exp_color = COLORS["bullish"] if expectancy >= 0 else COLORS["bearish"]
            exp_html = '<div class="pc" style="text-align:center;border:1px solid ' + exp_color + ';">'
            exp_html += '<span class="lbl">EXPECTANCY PER TRADE</span><br>'
            exp_html += '<span class="big" style="color:' + exp_color + ';">$' + f"{expectancy:+,.2f}" + '</span><br>'
            exp_html += '<span class="dim" style="font-size:0.75rem;">'
            exp_html += '(' + f"{win_pct:.0%}" + ' x $' + f"{avg_win_d:,.0f}" + ') - (' + f"{loss_pct:.0%}" + ' x $' + f"{avg_loss_d:,.0f}" + ')'
            exp_html += '</span></div>'
            st.markdown(exp_html, unsafe_allow_html=True)

        # ── Sharpe Ratio + Best/Worst Trade ──
        bt_sharpe = 0.0
        if r.total_trades > 1:
            trade_returns = [t.result_dollars for t in r.trades]
            mean_ret = np.mean(trade_returns)
            std_ret = np.std(trade_returns, ddof=1)
            bt_sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0.0

        if r.trades:
            best_trade = max(r.trades, key=lambda t: t.result_dollars)
            worst_trade = min(r.trades, key=lambda t: t.result_dollars)
            bw_col1, bw_col2 = st.columns(2)
            with bw_col1:
                bt_html = '<div class="pc" style="border-left:3px solid ' + COLORS["bullish"] + ';">'
                bt_html += '<span class="lbl">BEST TRADE</span><br>'
                bt_html += '<span class="sm" style="color:' + COLORS["bullish"] + ';font-size:1.1rem;">$' + f"{best_trade.result_dollars:+,.0f}" + '</span><br>'
                bt_html += '<span class="dim" style="font-size:0.75rem;">'
                bt_html += best_trade.date.strftime("%m/%d") + ' | ' + best_trade.direction + ' | Entry: ' + f"{best_trade.entry_price:.2f}" + ' | ' + best_trade.exit_reason
                bt_html += '</span></div>'
                st.markdown(bt_html, unsafe_allow_html=True)
            with bw_col2:
                wt_html = '<div class="pc" style="border-left:3px solid ' + COLORS["bearish"] + ';">'
                wt_html += '<span class="lbl">WORST TRADE</span><br>'
                wt_html += '<span class="sm" style="color:' + COLORS["bearish"] + ';font-size:1.1rem;">$' + f"{worst_trade.result_dollars:+,.0f}" + '</span><br>'
                wt_html += '<span class="dim" style="font-size:0.75rem;">'
                wt_html += worst_trade.date.strftime("%m/%d") + ' | ' + worst_trade.direction + ' | Entry: ' + f"{worst_trade.entry_price:.2f}" + ' | ' + worst_trade.exit_reason
                wt_html += '</span></div>'
                st.markdown(wt_html, unsafe_allow_html=True)

        if r.total_trades > 1:
            sharpe_color = COLORS["bullish"] if bt_sharpe >= 1.0 else (COLORS["warning"] if bt_sharpe >= 0.5 else COLORS["bearish"])
            sh_col1, sh_col2 = st.columns(2)
            with sh_col1:
                sh_html = '<div class="pc" style="text-align:center;">'
                sh_html += '<span class="lbl">SHARPE RATIO (ANNUALIZED)</span><br>'
                sh_html += '<span class="big" style="color:' + sharpe_color + ';">' + f"{bt_sharpe:.2f}" + '</span><br>'
                sh_html += '<span class="dim" style="font-size:0.7rem;">Above 1.0 = good | Above 2.0 = excellent</span>'
                sh_html += '</div>'
                st.markdown(sh_html, unsafe_allow_html=True)
            with sh_col2:
                avg_per_day = r.net_pnl_dollars / r.trading_days if r.trading_days > 0 else 0
                apd_color = COLORS["bullish"] if avg_per_day >= 0 else COLORS["bearish"]
                ad_html = '<div class="pc" style="text-align:center;">'
                ad_html += '<span class="lbl">AVG P&L PER TRADING DAY</span><br>'
                ad_html += '<span class="big" style="color:' + apd_color + ';">$' + f"{avg_per_day:+,.0f}" + '</span><br>'
                ad_html += '<span class="dim" style="font-size:0.7rem;">' + str(r.trading_days) + ' trading days</span>'
                ad_html += '</div>'
                st.markdown(ad_html, unsafe_allow_html=True)

        # ── Equity Curve ──
        if len(r.equity_curve) > 1:
            eq_fig = go.Figure()
            eq_fig.add_trace(go.Scatter(
                y=r.equity_curve,
                mode="lines",
                fill="tozeroy",
                line=dict(color="#00d4ff", width=2),
                fillcolor="rgba(0,212,255,0.06)",
                name="Equity",
            ))
            eq_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#060612",
                plot_bgcolor="#060612",
                font=dict(family="JetBrains Mono", color="#a0a0c0"),
                height=300,
                margin=dict(l=60, r=30, t=30, b=30),
                yaxis=dict(
                    title="P&L ($)",
                    gridcolor="#1a1a35",
                    zeroline=True,
                    zerolinecolor="#555577",
                ),
                xaxis=dict(title="Trade #", gridcolor="#1a1a35"),
                showlegend=False,
            )
            st.plotly_chart(eq_fig, use_container_width=True, config={"displayModeBar": False})

        # ── Win/Loss Streak Chart ──
        if r.trades:
            streaks = []
            current_streak = 0
            for t in r.trades:
                if t.result_pts > 0:
                    if current_streak > 0:
                        current_streak += 1
                    else:
                        if current_streak != 0:
                            streaks.append(current_streak)
                        current_streak = 1
                elif t.result_pts < 0:
                    if current_streak < 0:
                        current_streak -= 1
                    else:
                        if current_streak != 0:
                            streaks.append(current_streak)
                        current_streak = -1
                else:
                    if current_streak != 0:
                        streaks.append(current_streak)
                    current_streak = 0
            if current_streak != 0:
                streaks.append(current_streak)

            if streaks:
                streak_colors = [COLORS["bullish"] if s > 0 else COLORS["bearish"] for s in streaks]
                streak_labels = [("+" + str(s) + "W") if s > 0 else (str(s) + "L") for s in streaks]
                streak_fig = go.Figure()
                streak_fig.add_trace(go.Bar(
                    y=list(range(len(streaks))),
                    x=streaks,
                    orientation="h",
                    marker=dict(color=streak_colors),
                    text=streak_labels,
                    textposition="outside",
                    textfont=dict(color="#a0a0c0", size=10),
                ))
                streak_fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#060612",
                    plot_bgcolor="#060612",
                    font=dict(family="JetBrains Mono", color="#a0a0c0"),
                    height=max(150, len(streaks) * 22),
                    margin=dict(l=40, r=60, t=30, b=20),
                    yaxis=dict(
                        title="Streak #",
                        gridcolor="#1a1a35",
                        autorange="reversed",
                    ),
                    xaxis=dict(
                        title="Consecutive Trades",
                        gridcolor="#1a1a35",
                        zeroline=True,
                        zerolinecolor="#555577",
                    ),
                    showlegend=False,
                    title=dict(text="WIN / LOSS STREAKS", font=dict(size=12, color="#a0a0c0")),
                )
                st.plotly_chart(streak_fig, use_container_width=True, config={"displayModeBar": False})

        # ── Monthly Breakdown ──
        if r.trades:
            from collections import defaultdict
            monthly = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0})
            for t in r.trades:
                key = t.date.strftime("%Y-%m")
                monthly[key]["pnl"] += t.result_dollars
                if t.result_pts > 0:
                    monthly[key]["wins"] += 1
                elif t.result_pts < 0:
                    monthly[key]["losses"] += 1

            if len(monthly) > 1:
                mo_html = '<div class="pc">'
                mo_html += '<span class="lbl">MONTHLY P&L BREAKDOWN</span><br><br>'
                mo_html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:0.3rem 1rem;font-size:0.8rem;">'
                mo_html += '<span class="sm" style="color:#a0a0c0;font-weight:600;">MONTH</span>'
                mo_html += '<span class="sm" style="color:#a0a0c0;font-weight:600;text-align:center;">W/L</span>'
                mo_html += '<span class="sm" style="color:#a0a0c0;font-weight:600;text-align:center;">WIN%</span>'
                mo_html += '<span class="sm" style="color:#a0a0c0;font-weight:600;text-align:right;">NET P&L</span>'
                for mo_key in sorted(monthly.keys()):
                    stats = monthly[mo_key]
                    total = stats["wins"] + stats["losses"]
                    wr = (stats["wins"] / total * 100) if total > 0 else 0
                    pcolor = COLORS["bullish"] if stats["pnl"] >= 0 else COLORS["bearish"]
                    mo_html += '<span class="dim">' + mo_key + '</span>'
                    mo_html += '<span class="dim" style="text-align:center;">' + str(stats["wins"]) + 'W / ' + str(stats["losses"]) + 'L</span>'
                    mo_html += '<span class="dim" style="text-align:center;">' + f"{wr:.0f}" + '%</span>'
                    mo_html += '<span class="sm" style="color:' + pcolor + ';text-align:right;font-size:0.8rem;">$' + f"{stats['pnl']:+,.0f}" + '</span>'
                mo_html += '</div></div>'
                st.markdown(mo_html, unsafe_allow_html=True)

        # ── Detailed Breakdowns ──
        bd1, bd2 = st.columns(2)

        with bd1:
            # By VIX Regime
            if r.regime_stats:
                st.markdown(
                    '<div class="pc">'
                    '<span class="lbl">P&L BY VIX REGIME</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                for regime, stats in r.regime_stats.items():
                    pcolor = COLORS["bullish"] if stats["net_dollars"] >= 0 else COLORS["bearish"]
                    st.markdown(
                        '<div style="display:flex;justify-content:space-between;padding:0.4rem 0;'
                        'border-bottom:1px solid #1a1a35;">'
                        '<span class="sm" style="font-size:0.8rem;">' + regime + '</span>'
                        '<span class="dim">' + str(stats["trades"]) + ' trades</span>'
                        '<span class="dim">' + f"{stats['win_rate']:.0f}" + '% win</span>'
                        '<span class="sm" style="color:' + pcolor + ';font-size:0.8rem;">'
                        + f"${stats['net_dollars']:+,.0f}" + '</span>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

            # By Signal Strength
            if r.strength_stats:
                st.markdown(
                    '<div class="pc">'
                    '<span class="lbl">P&L BY SIGNAL STRENGTH</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                for strength, stats in r.strength_stats.items():
                    pcolor = COLORS["bullish"] if stats["net_dollars"] >= 0 else COLORS["bearish"]
                    badge_class = "strength-" + strength.lower()
                    st.markdown(
                        '<div style="display:flex;justify-content:space-between;align-items:center;'
                        'padding:0.4rem 0;border-bottom:1px solid #1a1a35;">'
                        '<span class="' + badge_class + '">' + strength + '</span>'
                        '<span class="dim">' + str(stats["trades"]) + ' trades</span>'
                        '<span class="dim">' + f"{stats['win_rate']:.0f}" + '% win</span>'
                        '<span class="sm" style="color:' + pcolor + ';font-size:0.8rem;">'
                        + f"${stats['net_dollars']:+,.0f}" + '</span>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

        with bd2:
            # By Day of Week
            if r.dow_stats:
                st.markdown(
                    '<div class="pc">'
                    '<span class="lbl">P&L BY DAY OF WEEK</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                for dow in dow_order:
                    if dow in r.dow_stats:
                        stats = r.dow_stats[dow]
                        pcolor = COLORS["bullish"] if stats["net_dollars"] >= 0 else COLORS["bearish"]
                        st.markdown(
                            '<div style="display:flex;justify-content:space-between;padding:0.4rem 0;'
                            'border-bottom:1px solid #1a1a35;">'
                            '<span class="sm" style="font-size:0.8rem;">' + dow[:3] + '</span>'
                            '<span class="dim">' + str(stats["trades"]) + ' trades</span>'
                            '<span class="dim">' + f"{stats['win_rate']:.0f}" + '% win</span>'
                            '<span class="sm" style="color:' + pcolor + ';font-size:0.8rem;">'
                            + f"${stats['net_dollars']:+,.0f}" + '</span>'
                            '</div>',
                            unsafe_allow_html=True,
                        )

            # By Entry Line
            if r.line_stats:
                st.markdown(
                    '<div class="pc">'
                    '<span class="lbl">P&L BY ENTRY LINE</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                for line_label, stats in r.line_stats.items():
                    pcolor = COLORS["bullish"] if stats["net_pts"] >= 0 else COLORS["bearish"]
                    st.markdown(
                        '<div style="display:flex;justify-content:space-between;padding:0.4rem 0;'
                        'border-bottom:1px solid #1a1a35;">'
                        '<span class="sm" style="font-size:0.8rem;">' + line_label + '</span>'
                        '<span class="dim">' + str(stats["trades"]) + ' trades</span>'
                        '<span class="dim">' + f"{stats['win_rate']:.0f}" + '% win</span>'
                        '<span class="sm" style="color:' + pcolor + ';font-size:0.8rem;">'
                        + f"{stats['net_pts']:+.1f}" + ' pts</span>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

        # ── Macro Impact ──
        if r.macro_day_trades > 0 or r.clean_day_trades > 0:
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown(
                    '<div class="pc" style="text-align:center;">'
                    '<span class="lbl">CLEAN DAYS</span><br>'
                    '<span class="sm" style="color:' + COLORS["bullish"] + ';">'
                    + str(r.clean_day_trades) + ' trades &middot; '
                    + f"{r.clean_day_win_rate:.0f}" + '% win rate</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            with mc2:
                st.markdown(
                    '<div class="pc" style="text-align:center;">'
                    '<span class="lbl">MACRO DAYS</span><br>'
                    '<span class="sm" style="color:' + COLORS["warning"] + ';">'
                    + str(r.macro_day_trades) + ' trades &middot; '
                    + f"{r.macro_day_win_rate:.0f}" + '% win rate</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )

        # ── Trade Log ──
        if r.trades:
            with st.expander("Full Trade Log"):
                trade_data = []
                for t in r.trades:
                    trade_data.append({
                        "Date": t.date.strftime("%m/%d"),
                        "Time": t.entry_time.strftime("%I:%M %p") if t.entry_time else "",
                        "Dir": t.direction,
                        "Line": t.entry_line,
                        "Entry": t.entry_price,
                        "Target": t.target_price,
                        "Stop": t.stop_price,
                        "Exit": t.exit_price,
                        "Reason": t.exit_reason,
                        "Pts": f"{t.result_pts:+.2f}",
                        "P&L": f"${t.result_dollars:+,.0f}",
                        "R:R": t.rr_ratio,
                        "VIX": t.vix_at_entry,
                        "Strength": t.signal_strength,
                    })
                st.dataframe(
                    pd.DataFrame(trade_data),
                    use_container_width=True,
                    hide_index=True,
                )

        # ── Key Stats Summary ──
        st.markdown(
            '<div class="pc">'
            '<span class="lbl">EXECUTION COSTS</span><br>'
            '<span class="dim" style="font-size:0.8rem;">'
            'Commission: $' + str(BACKTEST_COMMISSION_PER_CONTRACT) + '/contract/side ('
            + str(POSITION_SIZE_ES) + ' contracts) &middot; '
            'Slippage: ' + str(BACKTEST_SLIPPAGE_POINTS) + ' pts/side &middot; '
            'Total costs this backtest: $' + f"{r.total_commissions:,.2f}"
            + '</span></div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════════
#  TAB 6: MONTE CARLO SIMULATION
# ════════════════════════════════════════════════════════════════
with tab_montecarlo:

    st.markdown(
        '<div class="pc pc-gold">'
        '<span class="lbl"><span style="font-size:2rem;">&#127920;</span> MONTE CARLO SIMULATOR</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        mc_win_rate = st.slider("Win Rate (%)", 30, 80, 55, key="mc_wr")
        mc_avg_win = st.number_input("Avg Win (pts)", value=6.0, step=0.5, key="mc_aw")
    with mc2:
        mc_avg_loss = st.number_input("Avg Loss (pts)", value=4.5, step=0.5, key="mc_al")
        mc_trades = st.slider("Trade Horizon", 50, 500, MONTE_CARLO_TRADE_HORIZON, step=50, key="mc_th")
    with mc3:
        mc_sims = st.slider("Simulations", 500, 5000, MONTE_CARLO_SIMULATIONS, step=500, key="mc_ns")
        mc_capital = st.number_input("Starting Capital ($)", value=10000, step=1000, key="mc_cap")

    if st.button("RUN SIMULATION", type="primary", use_container_width=True, key="run_mc"):
        with st.spinner("Running Monte Carlo..."):
            mc_results = run_monte_carlo(
                win_rate=mc_win_rate / 100,
                avg_win_pts=mc_avg_win,
                avg_loss_pts=mc_avg_loss,
                starting_capital=float(mc_capital),
                num_simulations=mc_sims,
                trade_horizon=mc_trades,
                ruin_threshold=RUIN_THRESHOLD,
            )
        st.session_state["mc_results"] = mc_results

    if "mc_results" in st.session_state:
        mc = st.session_state["mc_results"]

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            ruin_color = COLORS["bullish"] if mc.probability_of_ruin < 5 else (
                COLORS["warning"] if mc.probability_of_ruin < 15 else COLORS["bearish"]
            )
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">PROB OF RUIN</span><br>'
                '<span class="big" style="color:' + ruin_color + ';">'
                + f"{mc.probability_of_ruin:.1f}" + '%</span><br>'
                '<span class="dim">Threshold: $' + f"{RUIN_THRESHOLD:,}" + '</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">PROB OF PROFIT</span><br>'
                '<span class="big" style="color:' + COLORS["bullish"] + ';">'
                + f"{mc.probability_of_profit:.1f}" + '%</span><br>'
                '<span class="dim">' + str(mc.simulations) + ' sims</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">MEDIAN P&L</span><br>'
                '<span class="big">$' + f"{mc.median_final_pnl:+,.0f}" + '</span><br>'
                '<span class="dim">' + str(mc.trade_horizon) + ' trades</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">KELLY FRACTION</span><br>'
                '<span class="big" style="color:' + COLORS["accent_gold"] + ';">'
                + f"{mc.half_kelly_fraction:.1%}" + '</span><br>'
                '<span class="dim">Half Kelly (safe)</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        # Equity curve bands (improved visuals)
        if mc.curve_median:
            mc_fig = go.Figure()
            x_trades = list(range(len(mc.curve_median)))

            # 5th-95th band (outermost)
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_best, mode="lines",
                line=dict(width=0), showlegend=False, hoverinfo="skip",
            ))
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_worst, mode="lines",
                fill="tonexty", fillcolor="rgba(123,44,191,0.08)",
                line=dict(width=0.5, color="rgba(123,44,191,0.3)", dash="dot"),
                name="5th-95th percentile",
            ))
            # 25th-75th band (inner)
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_upper, mode="lines",
                line=dict(width=0), showlegend=False, hoverinfo="skip",
            ))
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_lower, mode="lines",
                fill="tonexty", fillcolor="rgba(0,212,255,0.12)",
                line=dict(width=0.5, color="rgba(0,212,255,0.4)", dash="dash"),
                name="25th-75th percentile",
            ))
            # Median line
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_median, mode="lines",
                line=dict(color="#00d4ff", width=2.5),
                name="Median equity",
            ))
            # Best/worst edge lines
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_best, mode="lines",
                line=dict(color="rgba(0,255,136,0.35)", width=1, dash="dot"),
                name="Best 5%",
            ))
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_worst, mode="lines",
                line=dict(color="rgba(255,0,85,0.35)", width=1, dash="dot"),
                name="Worst 5%",
            ))
            mc_fig.add_hline(y=0, line_dash="dash", line_color="#555577", line_width=1)
            mc_fig.add_hline(y=RUIN_THRESHOLD, line_dash="dot",
                             line_color="#ff0055", line_width=1,
                             annotation_text="Ruin Line",
                             annotation_font_color="#ff0055")

            mc_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#020209",
                plot_bgcolor="#060612",
                font=dict(family="JetBrains Mono", color="#a0a0c0"),
                height=380, margin=dict(l=60, r=30, t=20, b=40),
                yaxis=dict(title="P&L ($)", gridcolor="#1a1a35"),
                xaxis=dict(title="Trade #", gridcolor="#1a1a35"),
                legend=dict(
                    orientation="h", yanchor="top", y=-0.15, x=0.5, xanchor="center",
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10),
                ),
            )
            st.plotly_chart(mc_fig, use_container_width=True, config={"displayModeBar": False})

        # Percentile table
        st.markdown(
            '<div class="pc">'
            '<span class="lbl">OUTCOME DISTRIBUTION</span><br><br>'
            '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.5rem;text-align:center;">'
            '<div>'
            '<span class="sm" style="color:' + COLORS["bearish"] + ';">WORST 5%</span><br>'
            '<span class="dim">$' + f"{mc.pct_5:+,.0f}" + '</span>'
            '</div>'
            '<div>'
            '<span class="sm">25TH</span><br>'
            '<span class="dim">$' + f"{mc.pct_25:+,.0f}" + '</span>'
            '</div>'
            '<div>'
            '<span class="sm" style="color:' + COLORS["accent_cyan"] + ';">MEDIAN</span><br>'
            '<span class="dim">$' + f"{mc.pct_50:+,.0f}" + '</span>'
            '</div>'
            '<div>'
            '<span class="sm">75TH</span><br>'
            '<span class="dim">$' + f"{mc.pct_75:+,.0f}" + '</span>'
            '</div>'
            '<div>'
            '<span class="sm" style="color:' + COLORS["bullish"] + ';">BEST 5%</span><br>'
            '<span class="dim">$' + f"{mc.pct_95:+,.0f}" + '</span>'
            '</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        # ── Profit Target Probability Table ──
        if mc.profit_target_probs:
            pt_html = '<div class="pc">'
            pt_html += '<span class="lbl">PROBABILITY OF REACHING PROFIT TARGETS</span><br><br>'
            pt_html += '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:0.5rem;text-align:center;">'
            for target, prob in mc.profit_target_probs.items():
                if prob > 50:
                    tcolor = COLORS["bullish"]
                elif prob > 20:
                    tcolor = COLORS["accent_cyan"]
                elif prob > 5:
                    tcolor = COLORS["warning"]
                else:
                    tcolor = COLORS["bearish"]
                pt_html += '<div>'
                pt_html += '<span class="dim" style="font-size:0.7rem;">P(+$' + f"{target:,}" + ')</span><br>'
                pt_html += '<span class="sm" style="color:' + tcolor + ';font-size:1.0rem;">' + f"{prob:.1f}" + '%</span>'
                pt_html += '</div>'
            pt_html += '</div></div>'
            st.markdown(pt_html, unsafe_allow_html=True)

        # ── Optimal Position Sizing + Drawdown Analysis ──
        mc_ps1, mc_ps2 = st.columns(2)
        with mc_ps1:
            kelly_risk_per_trade = mc.half_kelly_fraction * mc.starting_capital
            dollar_per_pt = POINT_VALUE_ES
            risk_pts = mc_avg_loss if mc_avg_loss > 0 else 4.5
            kelly_contracts = kelly_risk_per_trade / (risk_pts * dollar_per_pt) if (risk_pts * dollar_per_pt) > 0 else 0
            kelly_contracts = max(0, kelly_contracts)
            kp_html = '<div class="pc" style="border:1px solid ' + COLORS["accent_gold"] + ';">'
            kp_html += '<span class="lbl">OPTIMAL POSITION SIZE (HALF KELLY)</span><br><br>'
            kp_html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;text-align:center;">'
            kp_html += '<div>'
            kp_html += '<span class="dim" style="font-size:0.7rem;">RISK PER TRADE</span><br>'
            kp_html += '<span class="sm" style="color:' + COLORS["accent_gold"] + ';font-size:1.0rem;">$' + f"{kelly_risk_per_trade:,.0f}" + '</span>'
            kp_html += '</div>'
            kp_html += '<div>'
            kp_html += '<span class="dim" style="font-size:0.7rem;">ES CONTRACTS</span><br>'
            kp_html += '<span class="sm" style="color:' + COLORS["accent_gold"] + ';font-size:1.0rem;">' + f"{kelly_contracts:.1f}" + '</span>'
            kp_html += '</div>'
            kp_html += '<div>'
            kp_html += '<span class="dim" style="font-size:0.7rem;">MES CONTRACTS</span><br>'
            kp_html += '<span class="sm" style="color:' + COLORS["accent_gold"] + ';font-size:1.0rem;">' + f"{kelly_contracts * 10:.0f}" + '</span>'
            kp_html += '</div>'
            kp_html += '</div>'
            kp_html += '<br><span class="dim" style="font-size:0.65rem;">'
            kp_html += 'Kelly: ' + f"{mc.kelly_fraction:.1%}" + ' | Half Kelly: ' + f"{mc.half_kelly_fraction:.1%}" + ' | Capital: $' + f"{mc.starting_capital:,.0f}"
            kp_html += '</span></div>'
            st.markdown(kp_html, unsafe_allow_html=True)

        with mc_ps2:
            dd_html = '<div class="pc">'
            dd_html += '<span class="lbl">EXPECTED MAX DRAWDOWN</span><br><br>'
            dd_html += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;text-align:center;">'
            dd_pcts = [
                ("50th pct", mc.drawdown_pct_50, COLORS["accent_cyan"]),
                ("75th pct", mc.drawdown_pct_75, COLORS["warning"]),
                ("95th pct", mc.drawdown_pct_95, COLORS["bearish"]),
            ]
            for label, val, color in dd_pcts:
                pct_of_cap = (val / mc.starting_capital * 100) if mc.starting_capital > 0 else 0
                dd_html += '<div>'
                dd_html += '<span class="dim" style="font-size:0.7rem;">' + label.upper() + '</span><br>'
                dd_html += '<span class="sm" style="color:' + color + ';font-size:1.0rem;">$' + f"{val:,.0f}" + '</span><br>'
                dd_html += '<span class="dim" style="font-size:0.65rem;">' + f"{pct_of_cap:.0f}" + '% of capital</span>'
                dd_html += '</div>'
            dd_html += '</div>'
            dd_html += '<br><span class="dim" style="font-size:0.65rem;">'
            dd_html += 'Avg: $' + f"{mc.avg_max_drawdown:,.0f}" + ' | Worst: $' + f"{mc.worst_max_drawdown:,.0f}"
            dd_html += '</span></div>'
            st.markdown(dd_html, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 7: PERSISTENT JOURNAL
# ════════════════════════════════════════════════════════════════
with tab_journal:
    st.markdown(
        '<div class="pc pc-gold">'
        '<span class="lbl"><span style="font-size:2rem;">💰</span> TRADE JOURNAL</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    jstats = get_journal_stats()
    journal_df = load_journal()

    if jstats["total_trades"] > 0:
        js1, js2, js3, js4, js5 = st.columns(5)
        with js1:
            _pcolor = COLORS["bullish"] if jstats["net_pnl_dollars"] >= 0 else COLORS["bearish"]
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">NET P&L</span><br>'
                '<span class="med" style="color:' + _pcolor + '">'
                '${:+,.0f}'.format(jstats["net_pnl_dollars"]) + '</span></div>',
                unsafe_allow_html=True,
            )
        with js2:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">WIN RATE</span><br>'
                '<span class="med">{:.0f}%</span></div>'.format(jstats["win_rate"]),
                unsafe_allow_html=True,
            )
        with js3:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">PROFIT FACTOR</span><br>'
                '<span class="med">{:.2f}</span></div>'.format(jstats["profit_factor"]),
                unsafe_allow_html=True,
            )
        with js4:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">TRADES</span><br>'
                '<span class="med">' + str(jstats["total_trades"]) + '</span></div>',
                unsafe_allow_html=True,
            )
        with js5:
            _streak = jstats["streak_current"]
            _sc = COLORS["bullish"] if _streak > 0 else (COLORS["bearish"] if _streak < 0 else COLORS["text_muted"])
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">STREAK</span><br>'
                '<span class="med" style="color:' + _sc + '">'
                '{:+d}'.format(_streak) + '</span></div>',
                unsafe_allow_html=True,
            )

        # ── Weekly P&L Summary ──
        _now_ct = dt.datetime.now(CT)
        _week_start = (_now_ct - dt.timedelta(days=_now_ct.weekday())).strftime("%Y-%m-%d")
        _jdf_week = journal_df.copy()
        _jdf_week["result_pts"] = pd.to_numeric(_jdf_week["result_pts"], errors="coerce").fillna(0)
        _jdf_week["result_dollars"] = pd.to_numeric(_jdf_week["result_dollars"], errors="coerce").fillna(0)
        _jdf_week = _jdf_week[_jdf_week["date"] >= _week_start]
        _wk_pnl = _jdf_week["result_dollars"].sum()
        _wk_trades = len(_jdf_week)
        _wk_wins = len(_jdf_week[_jdf_week["result_pts"] > 0])
        _wk_wr = (_wk_wins / _wk_trades * 100) if _wk_trades > 0 else 0
        _wk_color = COLORS["bullish"] if _wk_pnl >= 0 else COLORS["bearish"]
        st.markdown(
            '<div class="pc" style="display:flex;justify-content:space-around;align-items:center;padding:0.75rem 1.5rem;">'
            '<div style="text-align:center;">'
            '<span class="lbl">THIS WEEK P&L</span><br>'
            '<span class="med" style="color:' + _wk_color + '">${:+,.0f}</span>'.format(_wk_pnl)
            + '</div>'
            '<div style="text-align:center;">'
            '<span class="lbl">WEEK WIN RATE</span><br>'
            '<span class="med">{:.0f}%</span>'.format(_wk_wr)
            + '</div>'
            '<div style="text-align:center;">'
            '<span class="lbl">WEEK TRADES</span><br>'
            '<span class="med">' + str(_wk_trades) + '</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        # ── Performance Metrics ──
        _jdf_perf = journal_df.copy()
        _jdf_perf["result_dollars"] = pd.to_numeric(_jdf_perf["result_dollars"], errors="coerce").fillna(0)
        _jdf_perf["result_pts"] = pd.to_numeric(_jdf_perf["result_pts"], errors="coerce").fillna(0)
        _daily_grp = _jdf_perf.groupby("date")["result_dollars"].sum()
        _best_day_val = _daily_grp.max() if len(_daily_grp) > 0 else 0
        _best_day_dt = _daily_grp.idxmax() if len(_daily_grp) > 0 else "N/A"
        _worst_day_val = _daily_grp.min() if len(_daily_grp) > 0 else 0
        _worst_day_dt = _daily_grp.idxmin() if len(_daily_grp) > 0 else "N/A"
        _equity = _jdf_perf["result_dollars"].cumsum()
        _peak = _equity.cummax()
        _dd = (_equity - _peak)
        _cur_dd = _dd.iloc[-1] if len(_dd) > 0 else 0
        _max_dd = _dd.min() if len(_dd) > 0 else 0
        _avg_trades_day = jstats["total_trades"] / max(jstats["days_traded"], 1)

        _pm1, _pm2, _pm3, _pm4 = st.columns(4)
        with _pm1:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">BEST DAY</span><br>'
                '<span class="sm" style="color:' + COLORS["bullish"] + '">'
                '${:+,.0f}'.format(_best_day_val) + '</span><br>'
                '<span class="dim">' + str(_best_day_dt) + '</span></div>',
                unsafe_allow_html=True,
            )
        with _pm2:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">WORST DAY</span><br>'
                '<span class="sm" style="color:' + COLORS["bearish"] + '">'
                '${:+,.0f}'.format(_worst_day_val) + '</span><br>'
                '<span class="dim">' + str(_worst_day_dt) + '</span></div>',
                unsafe_allow_html=True,
            )
        with _pm3:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">CURRENT DRAWDOWN</span><br>'
                '<span class="sm" style="color:' + COLORS["bearish"] + '">'
                '${:,.0f}'.format(_cur_dd) + '</span><br>'
                '<span class="dim">Peak DD: ${:,.0f}</span>'.format(_max_dd)
                + '</div>',
                unsafe_allow_html=True,
            )
        with _pm4:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">AVG TRADES / DAY</span><br>'
                '<span class="sm">{:.1f}</span>'.format(_avg_trades_day)
                + '<br><span class="dim">' + str(jstats["days_traded"]) + ' days traded</span></div>',
                unsafe_allow_html=True,
            )

    # ── Log New Trade (notes field prominent) ──
    with st.expander("LOG A TRADE", expanded=False):
        st.markdown(
            '<div class="pc" style="padding:0.6rem 1rem;margin-bottom:0.5rem;">'
            '<span style="font-size:2rem;">📝</span> '
            '<span class="lbl" style="color:' + COLORS["accent_gold"] + '">TRADE NOTES -- capture your reasoning</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        j_notes = st.text_area(
            "Notes / Reasoning",
            placeholder="Why did you take this trade? What was the setup? What did you learn?",
            height=80, key="pj_notes",
        )

        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            j_dir = st.selectbox("Direction", ["LONG", "SHORT"], key="pj_dir")
            j_entry = st.number_input("Entry Price", value=0.0, step=0.25, key="pj_entry")
            j_line = st.text_input("Entry Line", placeholder="e.g. UA", key="pj_line")
        with lc2:
            j_exit = st.number_input("Exit Price", value=0.0, step=0.25, key="pj_exit")
            j_reason = st.selectbox("Exit Reason", ["TARGET", "STOP", "BREAKEVEN", "EOD", "MANUAL"], key="pj_reason")
            j_instrument = st.selectbox("Instrument", ["ES", "SPX 0DTE CALL", "SPX 0DTE PUT"], key="pj_inst")
        with lc3:
            j_result = st.number_input("Result (pts)", value=0.0, step=0.25, key="pj_result")
            j_strength = st.selectbox("Signal Strength", ["STANDARD", "HIGH", "PREMIUM"], key="pj_str")
            j_contracts = st.number_input("Contracts", value=POSITION_SIZE_ES, min_value=1, step=1, key="pj_contracts")

        if st.button("Save Trade", type="primary", key="pj_save"):
            success = save_trade({
                "direction": j_dir,
                "entry_price": j_entry,
                "exit_price": j_exit,
                "entry_line": j_line,
                "exit_reason": j_reason,
                "result_pts": j_result,
                "signal_strength": j_strength,
                "instrument": j_instrument,
                "vix_at_entry": vix,
                "notes": j_notes,
                "contracts": j_contracts,
            })
            if success:
                st.success("Trade saved to journal!")
                st.rerun()

    # ── Visual Trade Cards (most recent 5) ──
    if not journal_df.empty:
        st.markdown(
            '<div style="margin:0.5rem 0;">'
            '<span class="lbl"><span style="font-size:2rem;">🃏</span> RECENT TRADES</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        _recent = journal_df.tail(5).iloc[::-1]
        for _, _tr in _recent.iterrows():
            _tr_pts = float(_tr["result_pts"]) if pd.notna(_tr["result_pts"]) else 0
            _tr_dollars = float(_tr["result_dollars"]) if pd.notna(_tr["result_dollars"]) else 0
            _tr_dir = str(_tr.get("direction", "")).upper()
            _dir_icon = "📈" if _tr_dir == "LONG" else "📉"
            _tr_color = COLORS["bullish"] if _tr_pts >= 0 else COLORS["bearish"]
            _border_color = COLORS["bullish"] if _tr_pts >= 0 else COLORS["bearish"]
            _entry_p = _tr.get("entry_price", "")
            _exit_p = _tr.get("exit_price", "")
            _line = str(_tr.get("entry_line", "")) if pd.notna(_tr.get("entry_line", "")) else ""
            _reason = str(_tr.get("exit_reason", "")) if pd.notna(_tr.get("exit_reason", "")) else ""
            _notes_val = str(_tr.get("notes", "")) if pd.notna(_tr.get("notes", "")) else ""
            _tdate = str(_tr.get("date", ""))
            _ttime = str(_tr.get("time", ""))

            _card_html = (
                '<div style="background:linear-gradient(135deg,#0c0c1f 0%,#0a0a1a 100%);'
                'border:1px solid ' + _border_color + '33;border-left:3px solid ' + _border_color + ';'
                'border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;">'
                '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">'
                '<div style="display:flex;align-items:center;gap:0.75rem;">'
                '<span style="font-size:1.5rem;">' + _dir_icon + '</span>'
                '<div>'
                '<span class="lbl" style="font-size:0.7rem;">' + _tr_dir + ' ' + _line + '</span><br>'
                '<span class="sm" style="font-family:JetBrains Mono,monospace;">'
                + str(_entry_p) + ' &rarr; ' + str(_exit_p) + '</span>'
                '</div></div>'
                '<div style="text-align:center;">'
                '<span class="dim" style="font-size:0.65rem;">' + _tdate + ' ' + _ttime + '</span><br>'
                '<span class="dim" style="font-size:0.6rem;">' + _reason + '</span>'
                '</div>'
                '<div style="text-align:right;">'
                '<span style="font-family:JetBrains Mono,monospace;font-size:1.1rem;font-weight:700;color:' + _tr_color + ';">'
                '{:+.2f} pts'.format(_tr_pts) + '</span><br>'
                '<span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;color:' + _tr_color + ';">'
                '${:+,.0f}'.format(_tr_dollars) + '</span>'
                '</div></div>'
            )
            if _notes_val:
                _card_html += (
                    '<div style="margin-top:0.4rem;padding-top:0.4rem;border-top:1px solid #1a1a35;">'
                    '<span class="dim" style="font-size:0.7rem;">📝 ' + _notes_val + '</span>'
                    '</div>'
                )
            _card_html += '</div>'
            st.markdown(_card_html, unsafe_allow_html=True)

        # Full journal table in expander
        with st.expander("FULL JOURNAL TABLE", expanded=False):
            st.dataframe(journal_df, use_container_width=True, hide_index=True)

        # Daily P&L chart
        daily = get_daily_pnl()
        if len(daily) > 1:
            daily_fig = go.Figure()
            colors = [COLORS["bullish"] if x >= 0 else COLORS["bearish"] for x in daily["pnl_dollars"]]
            daily_fig.add_trace(go.Bar(
                x=daily["date"], y=daily["pnl_dollars"],
                marker_color=colors, name="Daily P&L",
            ))
            daily_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#060612",
                plot_bgcolor="#060612",
                font=dict(family="JetBrains Mono", color="#a0a0c0"),
                height=250, margin=dict(l=60, r=30, t=20, b=40),
                yaxis=dict(title="P&L ($)", gridcolor="#1a1a35"),
            )
            st.plotly_chart(daily_fig, use_container_width=True, config={"displayModeBar": False})

        # Export
        csv_data = export_journal_csv()
        st.download_button("Download Journal CSV", csv_data, "prophet_journal.csv", "text/csv", key="dl_journal")
    else:
        st.info("No trades logged yet. Use the form above to log your first trade.")


# ════════════════════════════════════════════════════════════════
#  TAB 8: TRADINGVIEW ALERTS
# ════════════════════════════════════════════════════════════════
with tab_tv:
    st.markdown(
        '<div class="pc pc-gold">'
        '<span class="lbl"><span style="font-size:2rem;">📡</span> TRADINGVIEW WEBHOOK ALERTS</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Connection Status ──
    _tv_on = st.session_state.get("tv_on", False)
    _tv_status_color = COLORS["bullish"] if _tv_on else COLORS["bearish"]
    _tv_status_text = "RUNNING" if _tv_on else "OFFLINE"
    _tv_direct_url = "http://YOUR_IP/webhook"
    _tv_ngrok_url = "https://YOUR_NGROK_URL/webhook"
    st.markdown(
        '<div class="pc" style="padding:0.75rem 1.5rem;">'
        '<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.6rem;">'
        '<span style="font-size:2rem;">🔌</span>'
        '<div>'
        '<span class="lbl">WEBHOOK SERVER</span><br>'
        '<span class="sm" style="color:' + _tv_status_color + ';font-weight:700;">'
        + _tv_status_text + '</span>'
        '<span class="dim"> on port ' + str(TV_WEBHOOK_PORT) + '</span>'
        '</div></div>'
        '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;">'
        '<div style="flex:1;background:#020209;border:1px solid ' + COLORS["bullish"] + '44;border-radius:6px;padding:0.4rem 0.8rem;">'
        '<span class="dim" style="font-size:0.55rem;">RECOMMENDED — USE NGROK</span><br>'
        '<span style="font-family:JetBrains Mono,monospace;font-size:0.75rem;color:' + COLORS["bullish"] + ';">'
        + _tv_ngrok_url + '</span><br>'
        '<span class="dim" style="font-size:0.55rem;">Run: ngrok http ' + str(TV_WEBHOOK_PORT) + '</span>'
        '</div>'
        '<div style="flex:1;background:#020209;border:1px solid ' + COLORS["accent_cyan"] + '22;border-radius:6px;padding:0.4rem 0.8rem;">'
        '<span class="dim" style="font-size:0.55rem;">DIRECT (PORT 80 — NEEDS ADMIN)</span><br>'
        '<span style="font-family:JetBrains Mono,monospace;font-size:0.75rem;color:' + COLORS["text_muted"] + ';">'
        + _tv_direct_url + '</span>'
        '</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    alerts = get_alerts(20)

    # ── Alert Statistics ──
    if alerts:
        _today_str = dt.datetime.now(CT).strftime("%Y-%m-%d")
        _today_alerts = [a for a in alerts if a.timestamp.strftime("%Y-%m-%d") == _today_str]
        _today_count = len(_today_alerts)
        _latest_time = alerts[0].timestamp.strftime("%I:%M:%S %p") if alerts else "N/A"
        _buy_count = sum(1 for a in alerts if a.action == "BUY")
        _sell_count = sum(1 for a in alerts if a.action == "SELL")
        _most_common = "BUY" if _buy_count >= _sell_count else "SELL"
        _mc_color = COLORS["bullish"] if _most_common == "BUY" else COLORS["bearish"]

        _as1, _as2, _as3 = st.columns(3)
        with _as1:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">ALERTS TODAY</span><br>'
                '<span class="med">' + str(_today_count) + '</span></div>',
                unsafe_allow_html=True,
            )
        with _as2:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">LATEST ALERT</span><br>'
                '<span class="med" style="font-size:0.95rem;">' + _latest_time + '</span></div>',
                unsafe_allow_html=True,
            )
        with _as3:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">MOST COMMON</span><br>'
                '<span class="med" style="color:' + _mc_color + ';">' + _most_common
                + '</span><span class="dim"> (' + str(_buy_count) + 'B / ' + str(_sell_count) + 'S)</span></div>',
                unsafe_allow_html=True,
            )

        # ── Visual Timeline ──
        _tl_dots = ""
        for _a in reversed(alerts[:20]):
            _dot_c = COLORS["bullish"] if _a.action == "BUY" else (COLORS["bearish"] if _a.action == "SELL" else COLORS["accent_cyan"])
            _dot_label = _a.timestamp.strftime("%I:%M")
            _tl_dots += (
                '<div style="display:flex;flex-direction:column;align-items:center;gap:2px;">'
                '<div style="width:14px;height:14px;border-radius:50%;background:' + _dot_c + ';'
                'box-shadow:0 0 6px ' + _dot_c + '66;"></div>'
                '<span style="font-family:JetBrains Mono,monospace;font-size:0.5rem;color:#555577;">'
                + _dot_label + '</span>'
                '<span style="font-family:JetBrains Mono,monospace;font-size:0.45rem;color:' + _dot_c + ';">'
                + _a.action + '</span>'
                '</div>'
            )
        st.markdown(
            '<div class="pc" style="padding:0.75rem 1rem;">'
            '<span class="lbl">ALERT TIMELINE</span>'
            '<div style="display:flex;align-items:flex-start;gap:0.5rem;overflow-x:auto;padding:0.5rem 0;'
            'position:relative;">'
            '<div style="position:absolute;top:calc(0.5rem + 6px);left:0;right:0;height:2px;'
            'background:linear-gradient(90deg,' + COLORS["border"] + ',' + COLORS["accent_cyan"] + '44,' + COLORS["border"] + ');"></div>'
            '<div style="display:flex;align-items:flex-start;gap:0.75rem;position:relative;z-index:1;width:100%;justify-content:space-around;">'
            + _tl_dots
            + '</div></div></div>',
            unsafe_allow_html=True,
        )

        # ── Alert List ──
        for alert in alerts:
            a_color = COLORS["bullish"] if alert.action == "BUY" else (
                COLORS["bearish"] if alert.action == "SELL" else COLORS["accent_cyan"]
            )
            st.markdown(
                '<div style="display:flex;align-items:center;gap:0.75rem;padding:0.3rem 0.5rem;'
                'border-bottom:1px solid #1a1a3522;">'
                '<span class="dim" style="min-width:90px;font-family:JetBrains Mono,monospace;">'
                + alert.timestamp.strftime("%I:%M:%S %p") + '</span>'
                '<span class="sm" style="color:' + a_color + ';font-weight:600;min-width:50px;">'
                + alert.action + '</span>'
                '<span class="sm" style="font-family:JetBrains Mono,monospace;">'
                + '{:,.2f}'.format(alert.price) + '</span>'
                '<span class="dim">' + alert.ticker + '</span>'
                '<span class="dim" style="flex:1;">' + alert.message + '</span>'
                '</div>',
                unsafe_allow_html=True,
            )

        if st.button("Clear Alerts", key="clear_tv"):
            clear_alerts()
            st.rerun()
    else:
        st.markdown(
            '<div class="pc" style="text-align:center;padding:2rem;">'
            '<span class="dim">No alerts received yet</span><br><br>'
            '<span class="dim" style="font-size:0.7rem;">'
            '1. Enable webhook in sidebar<br>'
            '2. Run as admin (port 80 requires it) OR use ngrok: <b>ngrok http ' + str(TV_WEBHOOK_PORT) + '</b><br>'
            '3. Paste ngrok URL + /webhook into TradingView alert webhook field<br>'
            '4. Alert JSON format: {"action":"BUY","price":"{{close}}","message":"your note"}'
            '</span></div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════════
#  TAB 9: EDGE ANALYSIS
# ════════════════════════════════════════════════════════════════
with tab_analysis:
    st.markdown(
        '<div class="pc pc-gold">'
        '<span class="lbl"><span style="font-size:2rem;">🛡️</span> EDGE ANALYSIS -- WHAT MAKES THIS PROFITABLE</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    _risk_per_trade = STOP_POINTS * POINT_VALUE_ES * POSITION_SIZE_ES
    _max_losing = int(DAILY_LOSS_LIMIT / _risk_per_trade) if _risk_per_trade > 0 else 0

    ea1, ea2 = st.columns(2)

    with ea1:
        st.markdown(
            '<div class="pc">'
            '<span class="lbl">RISK PER TRADE</span><br><br>'
            '<span class="sm">Stop: ' + str(STOP_POINTS) + ' pts x $' + str(POINT_VALUE_ES) + ' x ' + str(POSITION_SIZE_ES)
            + ' = <b style="color:' + COLORS["bearish"] + '">$' + str(_risk_per_trade) + '</b></span><br><br>'
            '<span class="sm">Daily Cap: <b>$' + str(DAILY_LOSS_LIMIT) + '</b></span><br>'
            '<span class="dim">= ' + str(_max_losing) + ' max losing trades/day</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    with ea2:
        st.markdown(
            '<div class="pc">'
            '<span class="lbl">BREAKEVEN WIN RATE</span><br><br>'
            '<span class="sm">At 1:1 R:R &rarr; Need <b>50%</b> win rate</span><br>'
            '<span class="sm">At 1.5:1 R:R &rarr; Need <b>40%</b> win rate</span><br>'
            '<span class="sm">At 2:1 R:R &rarr; Need <b>33%</b> win rate</span><br><br>'
            '<span class="dim">Confluence zones push R:R higher</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Interactive R:R Calculator ──
    st.markdown(
        '<div style="margin-bottom:0.25rem;">'
        '<span class="lbl"><span style="font-size:2rem;">🧮</span> R:R / WIN RATE CALCULATOR</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    _rr1, _rr2 = st.columns(2)
    with _rr1:
        _calc_wr = st.slider("Your Win Rate (%)", min_value=10, max_value=90, value=55, step=1, key="edge_wr")
        _req_rr = (100.0 - _calc_wr) / _calc_wr if _calc_wr > 0 else 99
        _rr_color = COLORS["bullish"] if _req_rr <= 1.5 else (COLORS["warning"] if _req_rr <= 2.5 else COLORS["bearish"])
        st.markdown(
            '<div class="pc" style="text-align:center;">'
            '<span class="dim">At <b>' + str(_calc_wr) + '%</b> win rate you need</span><br>'
            '<span style="font-family:JetBrains Mono,monospace;font-size:1.4rem;font-weight:700;color:' + _rr_color + ';">'
            '{:.2f}'.format(_req_rr) + ':1 R:R</span><br>'
            '<span class="dim">to break even</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with _rr2:
        _calc_rr = st.slider("Your R:R Ratio", min_value=0.5, max_value=5.0, value=1.5, step=0.1, key="edge_rr")
        _req_wr = 100.0 / (1.0 + _calc_rr) if _calc_rr > 0 else 100
        _wr_color = COLORS["bullish"] if _req_wr <= 45 else (COLORS["warning"] if _req_wr <= 55 else COLORS["bearish"])
        st.markdown(
            '<div class="pc" style="text-align:center;">'
            '<span class="dim">At <b>{:.1f}'.format(_calc_rr) + ':1</b> R:R you need</span><br>'
            '<span style="font-family:JetBrains Mono,monospace;font-size:1.4rem;font-weight:700;color:' + _wr_color + ';">'
            '{:.1f}'.format(_req_wr) + '% win rate</span><br>'
            '<span class="dim">to break even</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Strategy Summary Stats (from journal if trades exist) ──
    _edge_jstats = get_journal_stats()
    if _edge_jstats["total_trades"] >= 3:
        st.markdown(
            '<div style="margin-bottom:0.25rem;">'
            '<span class="lbl"><span style="font-size:2rem;">&#128202;</span> YOUR ACTUAL EDGE (from journal)</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        _ej_wr = _edge_jstats["win_rate"]
        _ej_pf = _edge_jstats["profit_factor"]
        _ej_avg_w = _edge_jstats["avg_win"]
        _ej_avg_l = abs(_edge_jstats["avg_loss"]) if _edge_jstats["avg_loss"] != 0 else 0.01
        _ej_rr = _ej_avg_w / _ej_avg_l if _ej_avg_l > 0 else 0
        _ej_expectancy = (_ej_wr / 100.0) * _ej_avg_w + ((100 - _ej_wr) / 100.0) * _edge_jstats["avg_loss"]
        _ej_exp_color = COLORS["bullish"] if _ej_expectancy > 0 else COLORS["bearish"]

        _es1, _es2, _es3, _es4 = st.columns(4)
        with _es1:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">YOUR WIN RATE</span><br>'
                '<span class="med">{:.1f}%</span></div>'.format(_ej_wr),
                unsafe_allow_html=True,
            )
        with _es2:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">PROFIT FACTOR</span><br>'
                '<span class="med">{:.2f}</span></div>'.format(_ej_pf),
                unsafe_allow_html=True,
            )
        with _es3:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">ACTUAL R:R</span><br>'
                '<span class="med">{:.2f}:1</span></div>'.format(_ej_rr),
                unsafe_allow_html=True,
            )
        with _es4:
            st.markdown(
                '<div class="pc" style="text-align:center;">'
                '<span class="lbl">EXPECTANCY</span><br>'
                '<span class="med" style="color:' + _ej_exp_color + ';">'
                '{:+.2f} pts</span></div>'.format(_ej_expectancy),
                unsafe_allow_html=True,
            )

    # ── Position Size Calculator ──
    st.markdown(
        '<div style="margin-bottom:0.25rem;">'
        '<span class="lbl"><span style="font-size:2rem;">📐</span> POSITION SIZE CALCULATOR</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    _ps1, _ps2 = st.columns(2)
    with _ps1:
        _acct_size = st.number_input("Account Size ($)", value=25000, min_value=1000, step=1000, key="edge_acct")
        _risk_pct = st.slider("Risk Per Trade (%)", min_value=0.25, max_value=5.0, value=2.0, step=0.25, key="edge_risk_pct")
    with _ps2:
        _risk_dollars = _acct_size * (_risk_pct / 100.0)
        _es_stop_cost = STOP_POINTS * POINT_VALUE_ES
        _es_contracts = max(1, int(_risk_dollars / _es_stop_cost)) if _es_stop_cost > 0 else 1
        _spx_premium = st.number_input("SPX Option Premium ($)", value=5.0, min_value=0.5, step=0.5, key="edge_spx_prem")
        _spx_cost = _spx_premium * SPX_OPTIONS_MULTIPLIER
        _spx_contracts = max(1, int(_risk_dollars / _spx_cost)) if _spx_cost > 0 else 1

        st.markdown(
            '<div class="pc" style="padding:0.75rem 1rem;">'
            '<span class="lbl">RECOMMENDED SIZE</span><br><br>'
            '<span class="sm">Risk Budget: <b style="color:' + COLORS["accent_gold"] + ';">'
            '${:,.0f}'.format(_risk_dollars) + '</b> (' + '{:.1f}'.format(_risk_pct) + '% of ${:,.0f}'.format(_acct_size) + ')</span><br><br>'
            '<span class="sm" style="color:' + COLORS["accent_cyan"] + ';">ES Futures:</span> '
            '<span class="sm"><b>' + str(_es_contracts) + '</b> contracts</span>'
            '<span class="dim"> (' + str(STOP_POINTS) + '-pt stop = $' + str(_es_stop_cost * _es_contracts) + ' risk)</span><br>'
            '<span class="sm" style="color:' + COLORS["accent_gold"] + ';">SPX 0DTE:</span> '
            '<span class="sm"><b>' + str(_spx_contracts) + '</b> contracts</span>'
            '<span class="dim"> ($' + '{:.0f}'.format(_spx_premium) + ' prem x 100 = $' + '{:,.0f}'.format(_spx_cost * _spx_contracts) + ' risk)</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Visual Rule Cards ──
    st.markdown(
        '<div style="margin-bottom:0.25rem;">'
        '<span class="lbl"><span style="font-size:2rem;">📋</span> THE PROPHET\'S EDGE RULES</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    _take_rules = [
        "Session Quality >= B grade",
        "VIX in 14-20 range",
        "Both pivots confirmed",
        "R:R >= 1.5",
        "Confluence zone present",
        "Clean rejection wick >= 50% of body",
    ]
    _sit_rules = [
        "Session Quality D or F",
        "VIX above 28 (extreme)",
        "Pivots unconfirmed on both sides",
        "R:R below 1.0",
        "Friday afternoon",
        "FOMC / NFP / CPI day first 30 min",
    ]

    _rc1, _rc2 = st.columns(2)
    with _rc1:
        _take_html = (
            '<div class="pc pc-green" style="padding:1rem;">'
            '<span class="lbl" style="color:' + COLORS["bullish"] + ';">TAKE THE TRADE WHEN</span><br><br>'
        )
        for _rule in _take_rules:
            _take_html += (
                '<div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0.5rem;margin-bottom:0.3rem;'
                'background:#00ff8808;border-radius:4px;border-left:2px solid ' + COLORS["bullish"] + ';">'
                '<span style="color:' + COLORS["bullish"] + ';font-size:1rem;">&#10003;</span>'
                '<span class="sm">' + _rule + '</span></div>'
            )
        _take_html += '</div>'
        st.markdown(_take_html, unsafe_allow_html=True)
    with _rc2:
        _sit_html = (
            '<div class="pc pc-red" style="padding:1rem;">'
            '<span class="lbl" style="color:' + COLORS["bearish"] + ';">SIT OUT WHEN</span><br><br>'
        )
        for _rule in _sit_rules:
            _sit_html += (
                '<div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0.5rem;margin-bottom:0.3rem;'
                'background:#ff005508;border-radius:4px;border-left:2px solid ' + COLORS["bearish"] + ';">'
                '<span style="color:' + COLORS["bearish"] + ';font-size:1rem;">&#10007;</span>'
                '<span class="sm">' + _rule + '</span></div>'
            )
        _sit_html += '</div>'
        st.markdown(_sit_html, unsafe_allow_html=True)

    # ── Position Sizing by VIX Regime ──
    st.markdown(
        '<div class="pc">'
        '<span class="lbl">POSITION SIZING BY VIX REGIME</span><br><br>'
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.5rem;text-align:center;">'
        '<div>'
        '<span class="sm" style="color:' + COLORS["bullish"] + ';">LOW<br>&lt;14</span><br>'
        '<span class="dim">2 ES<br>Tight stops<br>Fade hard</span>'
        '</div>'
        '<div>'
        '<span class="sm" style="color:' + COLORS["accent_cyan"] + ';">NORMAL<br>14-20</span><br>'
        '<span class="dim">2 ES<br>Standard<br>Full rules</span>'
        '</div>'
        '<div>'
        '<span class="sm" style="color:' + COLORS["warning"] + ';">ELEVATED<br>20-28</span><br>'
        '<span class="dim">1 ES<br>Wide stops<br>Selective</span>'
        '</div>'
        '<div>'
        '<span class="sm" style="color:' + COLORS["bearish"] + ';">EXTREME<br>&gt;28</span><br>'
        '<span class="dim">Paper<br>or sit out<br>Protect capital</span>'
        '</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════
#  FOOTER
# ═══════════════════════════════════════════════════════════════════════
st.markdown(
    '<div style="text-align:center;padding:1.5rem 1rem 1rem;margin-top:1rem;border-top:1px solid #1a1a35;">'
    '<span class="dim" style="font-size:0.75rem;">'
    'SPX PROPHET &middot; LEGENDARY EDITION &middot; v2.0 &middot; Built for the '
    + str(POSITION_SIZE_ES) + '-lot warrior</span><br>'
    '<span class="dim" style="font-size:0.65rem;">'
    'Slope ' + str(SLOPE) + ' pts/hr &middot; ' + str(STOP_POINTS) + '-pt stops &middot; $'
    + str(DAILY_LOSS_LIMIT) + ' daily cap</span>'
    '</div>',
    unsafe_allow_html=True,
)
