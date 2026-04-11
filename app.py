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
    SOUND_ENABLED_DEFAULT, TV_WEBHOOK_PORT,
)
from styles import MAIN_CSS
from data_fetcher import (
    fetch_hourly_candles, fetch_current_price, fetch_vix,
    fetch_es_spx_offset, get_prior_trading_day,
    ES_SYMBOL, SPX_SYMBOL,
)
from pivot_detector import identify_upper_pivot, identify_lower_pivot
from line_calculator import (
    get_all_four_lines, detect_confluence_zones,
)
from signal_engine import (
    scan_for_signals, compute_session_quality, get_vix_regime,
)
from ui_components import (
    render_hero, render_lines_panel, render_pivot_panel,
    render_signal_panel, render_session_quality,
    render_confluence_zones, render_chart, render_trade_journal,
)
from macro_calendar import (
    get_events_for_date, get_upcoming_events,
    get_event_summary_for_week, get_worst_severity_today,
    is_macro_blackout,
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


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR — Manual Overrides & Controls
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙ COMMAND CENTER")
    st.markdown("---")

    # ── Date & Time ──
    st.markdown("##### 📅 DATE & TIME")
    today = dt.date.today()
    trade_date = st.date_input("Trading Date", value=today, key="trade_date")

    time_options = []
    for h in range(0, 24):
        for m in [0, 30]:
            time_options.append(f"{h:02d}:{m:02d}")

    now_ct = dt.datetime.now(CT)
    default_time_str = f"{now_ct.hour:02d}:{now_ct.minute // 30 * 30:02d}"
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
        st.markdown(f"""
        <div style="font-size:0.75rem; line-height:1.6;">
        <span class="prophet-data-muted">
        <b>Timeframe:</b> HOURLY ONLY<br>
        <b>Slope:</b> {SLOPE} pts/hr<br>
        <b>Lines:</b> 4 (UA, UD, LA, LD)<br>
        <b>Pivot Window:</b> 12–3 PM CT prior day<br>
        <b>Lines Lock:</b> Before 8:30 AM CT<br>
        <b>Entry:</b> Rejection + hourly CLOSE<br>
        <b>Stop:</b> {STOP_POINTS} pts beyond rejection<br>
        <b>Target:</b> Nearest remaining line<br>
        <b>Breakeven:</b> At +{STOP_POINTS} pts<br>
        <b>Max Loss:</b> ${DAILY_LOSS_LIMIT}/day<br>
        <b>Size:</b> {POSITION_SIZE_ES} ES / 4-strike OTM 0DTE<br>
        <b>Re-entry 9–11:</b> Up to 2<br>
        <b>Re-entry 11–12:</b> 1 only
        </span>
        </div>
        """, unsafe_allow_html=True)

    # ── Auto-refresh ──
    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh (2 min)", value=False, key="auto_ref")
    if auto_refresh:
        st.markdown("""
        <meta http-equiv="refresh" content="120">
        """, unsafe_allow_html=True)

    # ── Sound Notifications ──
    sound_enabled = st.checkbox("Sound Notifications", value=SOUND_ENABLED_DEFAULT, key="sound_on")

    # ── TradingView Webhook ──
    st.markdown("---")
    st.markdown("##### 📡 TRADINGVIEW LINK")
    tv_enabled = st.checkbox("Enable TV Webhook", value=False, key="tv_on")
    if tv_enabled:
        webhook_started = start_webhook_server(TV_WEBHOOK_PORT)
        if webhook_started:
            st.success(f"Webhook active on :{TV_WEBHOOK_PORT}")
        st.code(f"http://YOUR_IP:{TV_WEBHOOK_PORT}/webhook", language=None)
        st.markdown(f"""
        <span class="prophet-data-muted" style="font-size:0.65rem;">
        Set this URL in TradingView alert webhook field.
        Use ngrok to expose if running locally.
        </span>
        """, unsafe_allow_html=True)

    if st.button("🔄 Refresh Now", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════

# ── Fetch Data ────────────────────────────────────────────────────────
candles = fetch_hourly_candles(ES_SYMBOL)

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
    )
else:
    lower_pivot = identify_lower_pivot(candles, trade_date)

# ── Line Calculations ────────────────────────────────────────────────
lines = get_all_four_lines(upper_pivot, lower_pivot, ref_datetime)
confluence_zones = detect_confluence_zones(lines, CONFLUENCE_THRESHOLD)

# ── Signal Scan ───────────────────────────────────────────────────────
# Get today's candles for signal scanning
today_start = CT.localize(dt.datetime.combine(trade_date, dt.time(0, 0)))
today_candles = candles[candles.index >= today_start]

signals = scan_for_signals(today_candles, lines, confluence_zones)
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
    "DASHBOARD", "CHART", "OPTIONS", "MACRO", "BACKTEST", "MONTE CARLO", "JOURNAL", "TV ALERTS", "EDGE"
])

# ════════════════════════════════════════════════════════════════
#  TAB 1: DASHBOARD
# ════════════════════════════════════════════════════════════════
with tab_dashboard:
    # ── Macro Warning Banner ──
    if today_events:
        worst_color = MACRO_SEVERITY_COLORS.get(today_severity, "#888")
        event_names = ", ".join(e.title for e in today_events)
        blackout_msg = " · ⛔ BLACKOUT ACTIVE" if macro_blackout else ""
        st.markdown(f"""
        <div class="prophet-card" style="border-color:{worst_color}; border-width:2px;">
            <span class="prophet-label" style="color:{worst_color}">⚠ MACRO EVENT TODAY</span><br>
            <span class="prophet-data" style="color:{worst_color}">{event_names}</span><br>
            <span class="prophet-data-muted">Recommendation: {today_macro_rec}{blackout_msg}</span>
        </div>
        """, unsafe_allow_html=True)

    # Signal + Session Quality row
    sig_col, qual_col = st.columns([2, 1])

    with sig_col:
        st.markdown("""
        <div class="prophet-card">
            <span class="prophet-label">ACTIVE SIGNAL</span>
        </div>
        """, unsafe_allow_html=True)
        render_signal_panel(latest_signal)

    with qual_col:
        render_session_quality(session_quality)

    st.markdown("<br>", unsafe_allow_html=True)

    # Lines
    render_lines_panel(lines, es_price, offset)

    st.markdown("<br>", unsafe_allow_html=True)

    # Pivots + Confluence row
    piv_col, conf_col = st.columns([2, 1])

    with piv_col:
        render_pivot_panel(upper_pivot, lower_pivot)

    with conf_col:
        render_confluence_zones(confluence_zones, offset)

    # Signal History (today)
    if signals:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="prophet-card">
            <span class="prophet-label">TODAY'S SIGNALS</span>
        </div>
        """, unsafe_allow_html=True)

        for sig_time, sig in signals:
            color = COLORS["bullish"] if sig.direction == "LONG" else COLORS["bearish"]
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:1rem; padding:0.4rem 0; border-bottom:1px solid var(--border);">
                <span class="prophet-data" style="color:{COLORS['text_muted']}; min-width:80px;">
                    {sig_time.strftime("%I:%M %p")}
                </span>
                <span class="prophet-data" style="color:{color}; font-weight:600; min-width:60px;">
                    {sig.direction}
                </span>
                <span class="prophet-data-muted">
                    at {sig.entry_line} · {sig.entry_price:,.2f}
                </span>
                <span class="prophet-data" style="color:{COLORS['accent_gold']};">
                    R:R {sig.rr_ratio:.1f}
                </span>
                <span class="{f'strength-{sig.signal_strength.lower()}'}">
                    {sig.signal_strength}
                </span>
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 2: CHART
# ════════════════════════════════════════════════════════════════
with tab_chart:
    chart_days = st.slider("Candles to display (hours)", 12, 72, 36, step=6)
    chart_candles = candles.tail(chart_days)
    render_chart(
        chart_candles,
        upper_pivot, lower_pivot,
        lines, es_price,
        signals=signals,
        confluence_zones=confluence_zones,
    )


# ════════════════════════════════════════════════════════════════
#  TAB 3: OPTIONS P&L CALCULATOR
# ════════════════════════════════════════════════════════════════
with tab_options:
    st.markdown("""
    <div class="prophet-card prophet-card-gold">
        <span class="prophet-label">0DTE SPX OPTIONS CALCULATOR</span>
    </div>
    """, unsafe_allow_html=True)

    oc1, oc2 = st.columns(2)
    with oc1:
        opt_direction = latest_signal.direction if (latest_signal and latest_signal.direction != "NEUTRAL") else "LONG"
        opt_dir = st.selectbox("Direction", ["LONG", "SHORT"],
                               index=0 if opt_direction == "LONG" else 1, key="opt_dir")

        opt_target_pts = st.number_input("Target (ES pts)", value=float(latest_signal.reward_pts) if latest_signal else 8.0,
                                          step=0.5, key="opt_tgt")
        opt_stop_pts = st.number_input("Stop (ES pts)", value=float(latest_signal.risk_pts) if latest_signal else 5.0,
                                        step=0.5, key="opt_stp")
    with oc2:
        opt_contracts = st.number_input("Contracts", value=DEFAULT_OPTION_CONTRACTS, min_value=1, max_value=50, key="opt_ct")
        opt_hours = st.slider("Hours to Expiry", 0.5, 6.5, 5.0, step=0.5, key="opt_tte")
        opt_vix_input = st.number_input("VIX", value=vix, step=0.5, key="opt_vix")

    if st.button("Calculate Options P&L", type="primary", use_container_width=True, key="calc_opt"):
        opt_result = estimate_option_trade(
            spx_price=spx_price,
            direction=opt_dir,
            target_pts=opt_target_pts,
            stop_pts=opt_stop_pts,
            vix=opt_vix_input,
            hours_to_expiry=opt_hours,
            contracts=opt_contracts,
        )
        st.session_state["opt_result"] = opt_result

    if "opt_result" in st.session_state:
        opt = st.session_state["opt_result"]
        st.markdown("<br>", unsafe_allow_html=True)

        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">{opt.option_type}</span><br>
                <span class="prophet-price-sm">{opt.strike:.0f}</span><br>
                <span class="prophet-data-muted">Strike</span>
            </div>
            """, unsafe_allow_html=True)
        with r2:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">ENTRY PREMIUM</span><br>
                <span class="prophet-price-sm">${opt.premium_entry:.2f}</span><br>
                <span class="prophet-data-muted">Delta: {opt.delta_approx:.3f}</span>
            </div>
            """, unsafe_allow_html=True)
        with r3:
            st.markdown(f"""
            <div class="prophet-card prophet-card-bullish" style="text-align:center;">
                <span class="prophet-label">MAX PROFIT</span><br>
                <span class="prophet-price-sm" style="color:{COLORS['bullish']}">${opt.net_profit:+,.0f}</span><br>
                <span class="prophet-data-muted">Premium → ${opt.premium_target:.2f}</span>
            </div>
            """, unsafe_allow_html=True)
        with r4:
            st.markdown(f"""
            <div class="prophet-card prophet-card-bearish" style="text-align:center;">
                <span class="prophet-label">MAX LOSS</span><br>
                <span class="prophet-price-sm" style="color:{COLORS['bearish']}">-${opt.net_loss:,.0f}</span><br>
                <span class="prophet-data-muted">Premium → ${opt.premium_stop:.2f}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">TRADE SUMMARY</span><br><br>
            <span class="prophet-data">
                {opt.contracts}x SPX {opt.strike:.0f} {opt.option_type} @ ${opt.premium_entry:.2f}<br>
                Cost basis: ${opt.premium_entry * opt.contracts * SPX_OPTIONS_MULTIPLIER:,.0f}<br>
                Commission (RT): ${opt.commission_total:.2f}<br>
                Breakeven move: {opt.breakeven_move:.1f} SPX pts<br>
                Options R:R: <b style="color:{COLORS['accent_gold']}">{opt.rr_ratio:.2f}</b><br>
                Time to expiry: {opt.time_to_expiry_hours:.1f} hrs
            </span>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 4: MACRO CALENDAR
# ════════════════════════════════════════════════════════════════
with tab_macro:
    st.markdown("""
    <div class="prophet-card prophet-card-gold">
        <span class="prophet-label">MACRO EVENT CALENDAR</span>
    </div>
    """, unsafe_allow_html=True)

    # ── This Week's Overview ──
    week_summary = get_event_summary_for_week(trade_date)

    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        st.markdown(f"""
        <div class="prophet-card" style="text-align:center;">
            <span class="prophet-label">THIS WEEK</span><br>
            <span class="prophet-price-sm">{week_summary['total_events']}</span><br>
            <span class="prophet-data-muted">events</span>
        </div>
        """, unsafe_allow_html=True)
    with wc2:
        extreme_count = len(week_summary['extreme_days'])
        e_color = COLORS["bearish"] if extreme_count > 0 else COLORS["bullish"]
        st.markdown(f"""
        <div class="prophet-card" style="text-align:center;">
            <span class="prophet-label">EXTREME DAYS</span><br>
            <span class="prophet-price-sm" style="color:{e_color}">{extreme_count}</span><br>
            <span class="prophet-data-muted">sit-out days</span>
        </div>
        """, unsafe_allow_html=True)
    with wc3:
        clear_count = len(week_summary['clear_days'])
        st.markdown(f"""
        <div class="prophet-card" style="text-align:center;">
            <span class="prophet-label">CLEAR DAYS</span><br>
            <span class="prophet-price-sm" style="color:{COLORS['bullish']}">{clear_count}</span><br>
            <span class="prophet-data-muted">full-size trading</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

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
                today_badge = f'<span style="background:{sev_color};color:#000;padding:2px 8px;border-radius:4px;font-size:0.6rem;margin-left:8px;font-family:Orbitron,sans-serif;">TODAY</span>'

            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:1rem; padding:0.6rem 0.5rem;
                        border-bottom:1px solid var(--border);
                        {'background:rgba(255,0,102,0.05);border-radius:6px;' if is_today else ''}">
                <span class="prophet-data" style="color:{COLORS['text_muted']}; min-width:90px; font-size:0.8rem;">
                    {event.date.strftime("%a %b %d")}
                </span>
                <span class="prophet-data" style="color:{COLORS['text_muted']}; min-width:80px; font-size:0.8rem;">
                    {time_str}
                </span>
                <span class="line-dot" style="background:{sev_color};box-shadow:0 0 6px {sev_color};"></span>
                <span class="prophet-data" style="font-size:0.85rem;">
                    {event.title}{today_badge}
                </span>
                <span class="vix-badge" style="color:{sev_color};border:1px solid {sev_color};margin-left:auto;">
                    {event.severity.upper()}
                </span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Severity Legend ──
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">SEVERITY GUIDE</span><br><br>
            <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:0.75rem; text-align:center;">
                <div>
                    <span class="line-dot" style="background:{MACRO_SEVERITY_COLORS['extreme']};"></span>
                    <span class="prophet-data" style="color:{MACRO_SEVERITY_COLORS['extreme']}; font-size:0.8rem;">EXTREME</span><br>
                    <span class="prophet-data-muted" style="font-size:0.7rem;">SIT OUT entirely<br>FOMC, CPI, NFP, Quad Witch</span>
                </div>
                <div>
                    <span class="line-dot" style="background:{MACRO_SEVERITY_COLORS['high']};"></span>
                    <span class="prophet-data" style="color:{MACRO_SEVERITY_COLORS['high']}; font-size:0.8rem;">HIGH</span><br>
                    <span class="prophet-data-muted" style="font-size:0.7rem;">HALF SIZE<br>PPI, PCE, GDP, OPEX</span>
                </div>
                <div>
                    <span class="line-dot" style="background:{MACRO_SEVERITY_COLORS['moderate']};"></span>
                    <span class="prophet-data" style="color:{MACRO_SEVERITY_COLORS['moderate']}; font-size:0.8rem;">MODERATE</span><br>
                    <span class="prophet-data-muted" style="font-size:0.7rem;">NORMAL with caution<br>ISM, Jobless Claims</span>
                </div>
                <div>
                    <span class="line-dot" style="background:{MACRO_SEVERITY_COLORS['low']};"></span>
                    <span class="prophet-data" style="color:{MACRO_SEVERITY_COLORS['low']}; font-size:0.8rem;">LOW</span><br>
                    <span class="prophet-data-muted" style="font-size:0.7rem;">FULL SIZE<br>Minor releases</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="prophet-card" style="text-align:center; padding:2rem;">
            <span class="prophet-data" style="color:{COLORS['bullish']}">ALL CLEAR</span><br>
            <span class="prophet-data-muted">No macro events in the next {look_ahead} days</span>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 4: BACKTESTER
# ════════════════════════════════════════════════════════════════
with tab_backtest:

    st.markdown("""
    <div class="prophet-card prophet-card-gold">
        <span class="prophet-label">STRATEGY BACKTESTER</span>
    </div>
    """, unsafe_allow_html=True)

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

        st.markdown("<br>", unsafe_allow_html=True)

        # Top-line stats
        s1, s2, s3, s4, s5 = st.columns(5)

        with s1:
            pnl_color = COLORS["bullish"] if r.net_pnl_dollars >= 0 else COLORS["bearish"]
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">NET P&L</span><br>
                <span class="prophet-price-sm" style="color:{pnl_color}">
                    ${r.net_pnl_dollars:+,.0f}
                </span><br>
                <span class="prophet-data-muted">{r.net_pnl_pts:+.1f} pts</span>
            </div>
            """, unsafe_allow_html=True)
        with s2:
            wr_color = COLORS["bullish"] if r.win_rate >= 50 else COLORS["bearish"]
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">WIN RATE</span><br>
                <span class="prophet-price-sm" style="color:{wr_color}">{r.win_rate:.1f}%</span><br>
                <span class="prophet-data-muted">{r.winners}W / {r.losers}L</span>
            </div>
            """, unsafe_allow_html=True)
        with s3:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">PROFIT FACTOR</span><br>
                <span class="prophet-price-sm">{r.profit_factor:.2f}</span><br>
                <span class="prophet-data-muted">Avg R:R {r.avg_rr_ratio:.2f}</span>
            </div>
            """, unsafe_allow_html=True)
        with s4:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">MAX DRAWDOWN</span><br>
                <span class="prophet-price-sm" style="color:{COLORS['bearish']}">${r.max_drawdown_dollars:,.0f}</span><br>
                <span class="prophet-data-muted">{r.max_consecutive_losses} consec losses</span>
            </div>
            """, unsafe_allow_html=True)
        with s5:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">TOTAL TRADES</span><br>
                <span class="prophet-price-sm">{r.total_trades}</span><br>
                <span class="prophet-data-muted">{r.trading_days} days</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Equity Curve ──
        if len(r.equity_curve) > 1:
            eq_fig = go.Figure()
            eq_fig.add_trace(go.Scatter(
                y=r.equity_curve,
                mode="lines",
                fill="tozeroy",
                line=dict(color=COLORS["accent_cyan"], width=2),
                fillcolor="rgba(0,212,255,0.1)",
                name="Equity",
            ))
            eq_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor=COLORS["bg_primary"],
                plot_bgcolor=COLORS["bg_card"],
                font=dict(family="JetBrains Mono", color=COLORS["text_primary"]),
                height=300,
                margin=dict(l=60, r=30, t=30, b=30),
                yaxis=dict(
                    title="P&L ($)",
                    gridcolor=COLORS["border"],
                    zeroline=True,
                    zerolinecolor=COLORS["text_dim"],
                ),
                xaxis=dict(title="Trade #", gridcolor=COLORS["border"]),
                showlegend=False,
            )
            st.plotly_chart(eq_fig, use_container_width=True, config={"displayModeBar": False})

        # ── Detailed Breakdowns ──
        bd1, bd2 = st.columns(2)

        with bd1:
            # By VIX Regime
            if r.regime_stats:
                st.markdown(f"""
                <div class="prophet-card">
                    <span class="prophet-label">P&L BY VIX REGIME</span>
                </div>
                """, unsafe_allow_html=True)
                for regime, stats in r.regime_stats.items():
                    pcolor = COLORS["bullish"] if stats["net_dollars"] >= 0 else COLORS["bearish"]
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; padding:0.4rem 0;
                                border-bottom:1px solid var(--border);">
                        <span class="prophet-data" style="font-size:0.8rem;">{regime}</span>
                        <span class="prophet-data-muted">{stats['trades']} trades</span>
                        <span class="prophet-data-muted">{stats['win_rate']:.0f}% win</span>
                        <span class="prophet-data" style="color:{pcolor};font-size:0.8rem;">${stats['net_dollars']:+,.0f}</span>
                    </div>
                    """, unsafe_allow_html=True)

            # By Signal Strength
            if r.strength_stats:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"""
                <div class="prophet-card">
                    <span class="prophet-label">P&L BY SIGNAL STRENGTH</span>
                </div>
                """, unsafe_allow_html=True)
                for strength, stats in r.strength_stats.items():
                    pcolor = COLORS["bullish"] if stats["net_dollars"] >= 0 else COLORS["bearish"]
                    badge_class = f"strength-{strength.lower()}"
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center;
                                padding:0.4rem 0; border-bottom:1px solid var(--border);">
                        <span class="{badge_class}">{strength}</span>
                        <span class="prophet-data-muted">{stats['trades']} trades</span>
                        <span class="prophet-data-muted">{stats['win_rate']:.0f}% win</span>
                        <span class="prophet-data" style="color:{pcolor};font-size:0.8rem;">${stats['net_dollars']:+,.0f}</span>
                    </div>
                    """, unsafe_allow_html=True)

        with bd2:
            # By Day of Week
            if r.dow_stats:
                st.markdown(f"""
                <div class="prophet-card">
                    <span class="prophet-label">P&L BY DAY OF WEEK</span>
                </div>
                """, unsafe_allow_html=True)
                dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                for dow in dow_order:
                    if dow in r.dow_stats:
                        stats = r.dow_stats[dow]
                        pcolor = COLORS["bullish"] if stats["net_dollars"] >= 0 else COLORS["bearish"]
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; padding:0.4rem 0;
                                    border-bottom:1px solid var(--border);">
                            <span class="prophet-data" style="font-size:0.8rem;">{dow[:3]}</span>
                            <span class="prophet-data-muted">{stats['trades']} trades</span>
                            <span class="prophet-data-muted">{stats['win_rate']:.0f}% win</span>
                            <span class="prophet-data" style="color:{pcolor};font-size:0.8rem;">${stats['net_dollars']:+,.0f}</span>
                        </div>
                        """, unsafe_allow_html=True)

            # By Entry Line
            if r.line_stats:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"""
                <div class="prophet-card">
                    <span class="prophet-label">P&L BY ENTRY LINE</span>
                </div>
                """, unsafe_allow_html=True)
                for line_label, stats in r.line_stats.items():
                    pcolor = COLORS["bullish"] if stats["net_pts"] >= 0 else COLORS["bearish"]
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; padding:0.4rem 0;
                                border-bottom:1px solid var(--border);">
                        <span class="prophet-data" style="font-size:0.8rem;">{line_label}</span>
                        <span class="prophet-data-muted">{stats['trades']} trades</span>
                        <span class="prophet-data-muted">{stats['win_rate']:.0f}% win</span>
                        <span class="prophet-data" style="color:{pcolor};font-size:0.8rem;">{stats['net_pts']:+.1f} pts</span>
                    </div>
                    """, unsafe_allow_html=True)

        # ── Macro Impact ──
        if r.macro_day_trades > 0 or r.clean_day_trades > 0:
            st.markdown("<br>", unsafe_allow_html=True)
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown(f"""
                <div class="prophet-card" style="text-align:center;">
                    <span class="prophet-label">CLEAN DAYS</span><br>
                    <span class="prophet-data" style="color:{COLORS['bullish']}">
                        {r.clean_day_trades} trades · {r.clean_day_win_rate:.0f}% win rate
                    </span>
                </div>
                """, unsafe_allow_html=True)
            with mc2:
                st.markdown(f"""
                <div class="prophet-card" style="text-align:center;">
                    <span class="prophet-label">MACRO DAYS</span><br>
                    <span class="prophet-data" style="color:{COLORS['warning']}">
                        {r.macro_day_trades} trades · {r.macro_day_win_rate:.0f}% win rate
                    </span>
                </div>
                """, unsafe_allow_html=True)

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
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">EXECUTION COSTS</span><br>
            <span class="prophet-data-muted" style="font-size:0.8rem;">
                Commission: ${BACKTEST_COMMISSION_PER_CONTRACT}/contract/side ({POSITION_SIZE_ES} contracts) ·
                Slippage: {BACKTEST_SLIPPAGE_POINTS} pts/side ·
                Total costs this backtest: ${r.total_commissions:,.2f}
            </span>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 6: MONTE CARLO SIMULATION
# ════════════════════════════════════════════════════════════════
with tab_montecarlo:

    st.markdown("""
    <div class="prophet-card prophet-card-gold">
        <span class="prophet-label">MONTE CARLO SIMULATOR</span>
    </div>
    """, unsafe_allow_html=True)

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

        st.markdown("<br>", unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            ruin_color = COLORS["bullish"] if mc.probability_of_ruin < 5 else (
                COLORS["warning"] if mc.probability_of_ruin < 15 else COLORS["bearish"]
            )
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">PROB OF RUIN</span><br>
                <span class="prophet-price-sm" style="color:{ruin_color}">{mc.probability_of_ruin:.1f}%</span><br>
                <span class="prophet-data-muted">Threshold: ${RUIN_THRESHOLD:,}</span>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">PROB OF PROFIT</span><br>
                <span class="prophet-price-sm" style="color:{COLORS['bullish']}">{mc.probability_of_profit:.1f}%</span><br>
                <span class="prophet-data-muted">{mc.simulations} sims</span>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">MEDIAN P&L</span><br>
                <span class="prophet-price-sm">${mc.median_final_pnl:+,.0f}</span><br>
                <span class="prophet-data-muted">{mc.trade_horizon} trades</span>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">KELLY FRACTION</span><br>
                <span class="prophet-price-sm" style="color:{COLORS['accent_gold']}">{mc.half_kelly_fraction:.1%}</span><br>
                <span class="prophet-data-muted">Half Kelly (safe)</span>
            </div>
            """, unsafe_allow_html=True)

        # Equity curve bands
        if mc.curve_median:
            mc_fig = go.Figure()
            x_trades = list(range(len(mc.curve_median)))

            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_best, mode="lines",
                line=dict(width=0), showlegend=False,
            ))
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_worst, mode="lines",
                fill="tonexty", fillcolor="rgba(0,212,255,0.05)",
                line=dict(width=0), name="5th–95th pct",
            ))
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_upper, mode="lines",
                line=dict(width=0), showlegend=False,
            ))
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_lower, mode="lines",
                fill="tonexty", fillcolor="rgba(0,212,255,0.12)",
                line=dict(width=0), name="25th–75th pct",
            ))
            mc_fig.add_trace(go.Scatter(
                x=x_trades, y=mc.curve_median, mode="lines",
                line=dict(color=COLORS["accent_cyan"], width=2),
                name="Median",
            ))
            mc_fig.add_hline(y=0, line_dash="dash", line_color=COLORS["text_dim"], line_width=1)
            mc_fig.add_hline(y=RUIN_THRESHOLD, line_dash="dot",
                             line_color=COLORS["bearish"], line_width=1,
                             annotation_text="Ruin Line")

            mc_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor=COLORS["bg_primary"],
                plot_bgcolor=COLORS["bg_card"],
                font=dict(family="JetBrains Mono", color=COLORS["text_primary"]),
                height=350, margin=dict(l=60, r=30, t=20, b=40),
                yaxis=dict(title="P&L ($)", gridcolor=COLORS["border"]),
                xaxis=dict(title="Trade #", gridcolor=COLORS["border"]),
                legend=dict(orientation="h", yanchor="top", y=-0.15, x=0.5, xanchor="center"),
            )
            st.plotly_chart(mc_fig, use_container_width=True, config={"displayModeBar": False})

        # Percentile table
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">OUTCOME DISTRIBUTION</span><br><br>
            <div style="display:grid; grid-template-columns:repeat(5,1fr); gap:0.5rem; text-align:center;">
                <div>
                    <span class="prophet-data" style="color:{COLORS['bearish']}">WORST 5%</span><br>
                    <span class="prophet-data-muted">${mc.pct_5:+,.0f}</span>
                </div>
                <div>
                    <span class="prophet-data">25TH</span><br>
                    <span class="prophet-data-muted">${mc.pct_25:+,.0f}</span>
                </div>
                <div>
                    <span class="prophet-data" style="color:{COLORS['accent_cyan']}">MEDIAN</span><br>
                    <span class="prophet-data-muted">${mc.pct_50:+,.0f}</span>
                </div>
                <div>
                    <span class="prophet-data">75TH</span><br>
                    <span class="prophet-data-muted">${mc.pct_75:+,.0f}</span>
                </div>
                <div>
                    <span class="prophet-data" style="color:{COLORS['bullish']}">BEST 5%</span><br>
                    <span class="prophet-data-muted">${mc.pct_95:+,.0f}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 7: PERSISTENT JOURNAL
# ════════════════════════════════════════════════════════════════
with tab_journal:
    st.markdown("""
    <div class="prophet-card prophet-card-gold">
        <span class="prophet-label">TRADE JOURNAL</span>
    </div>
    """, unsafe_allow_html=True)

    # Stats bar
    jstats = get_journal_stats()
    if jstats["total_trades"] > 0:
        js1, js2, js3, js4, js5 = st.columns(5)
        with js1:
            pcolor = COLORS["bullish"] if jstats["net_pnl_dollars"] >= 0 else COLORS["bearish"]
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">NET P&L</span><br>
                <span class="prophet-price-sm" style="color:{pcolor}">${jstats['net_pnl_dollars']:+,.0f}</span>
            </div>
            """, unsafe_allow_html=True)
        with js2:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">WIN RATE</span><br>
                <span class="prophet-price-sm">{jstats['win_rate']:.0f}%</span>
            </div>
            """, unsafe_allow_html=True)
        with js3:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">PROFIT FACTOR</span><br>
                <span class="prophet-price-sm">{jstats['profit_factor']:.2f}</span>
            </div>
            """, unsafe_allow_html=True)
        with js4:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">TRADES</span><br>
                <span class="prophet-price-sm">{jstats['total_trades']}</span>
            </div>
            """, unsafe_allow_html=True)
        with js5:
            streak = jstats["streak_current"]
            s_color = COLORS["bullish"] if streak > 0 else (COLORS["bearish"] if streak < 0 else COLORS["text_muted"])
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="prophet-label">STREAK</span><br>
                <span class="prophet-price-sm" style="color:{s_color}">{streak:+d}</span>
            </div>
            """, unsafe_allow_html=True)

    # Log new trade
    with st.expander("LOG A TRADE", expanded=False):
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
            j_notes = st.text_input("Notes", key="pj_notes")

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
            })
            if success:
                st.success("Trade saved to journal!")
                st.rerun()

    # Display journal
    journal_df = load_journal()
    if not journal_df.empty:
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
                paper_bgcolor=COLORS["bg_primary"],
                plot_bgcolor=COLORS["bg_card"],
                font=dict(family="JetBrains Mono", color=COLORS["text_primary"]),
                height=250, margin=dict(l=60, r=30, t=20, b=40),
                yaxis=dict(title="P&L ($)", gridcolor=COLORS["border"]),
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
    st.markdown("""
    <div class="prophet-card prophet-card-gold">
        <span class="prophet-label">TRADINGVIEW WEBHOOK ALERTS</span>
    </div>
    """, unsafe_allow_html=True)

    alerts = get_alerts(20)

    if alerts:
        for alert in alerts:
            a_color = COLORS["bullish"] if alert.action == "BUY" else (
                COLORS["bearish"] if alert.action == "SELL" else COLORS["accent_cyan"]
            )
            st.markdown(f"""
            <div class="stat-row">
                <span class="prophet-data-muted" style="min-width:100px;">
                    {alert.timestamp.strftime("%I:%M:%S %p")}
                </span>
                <span class="prophet-data" style="color:{a_color}; font-weight:600; min-width:60px;">
                    {alert.action}
                </span>
                <span class="prophet-data">{alert.price:,.2f}</span>
                <span class="prophet-data-muted">{alert.ticker}</span>
                <span class="prophet-data-muted" style="flex:1;">{alert.message}</span>
            </div>
            """, unsafe_allow_html=True)

        if st.button("Clear Alerts", key="clear_tv"):
            clear_alerts()
            st.rerun()
    else:
        st.markdown(f"""
        <div class="prophet-card" style="text-align:center; padding:2rem;">
            <span class="prophet-data-muted">No alerts received yet</span><br><br>
            <span class="prophet-data-muted" style="font-size:0.7rem;">
                1. Enable webhook in sidebar<br>
                2. Set TradingView alert webhook URL to your endpoint<br>
                3. Use ngrok if running locally: ngrok http {TV_WEBHOOK_PORT}<br>
                4. Alert JSON format: {{"action":"BUY","price":"{{{{close}}}}","message":"your note"}}
            </span>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
#  TAB 9: EDGE ANALYSIS
# ════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════
with tab_analysis:
    st.markdown("""
    <div class="prophet-card prophet-card-gold">
        <span class="prophet-label">EDGE ANALYSIS — WHAT MAKES THIS PROFITABLE</span>
    </div>
    """, unsafe_allow_html=True)

    ea1, ea2 = st.columns(2)

    with ea1:
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">RISK PER TRADE</span><br><br>
            <span class="prophet-data">
                Stop: {STOP_POINTS} pts × ${POINT_VALUE_ES} × {POSITION_SIZE_ES} = 
                <b style="color:{COLORS['bearish']}">${STOP_POINTS * POINT_VALUE_ES * POSITION_SIZE_ES}</b>
            </span><br><br>
            <span class="prophet-data">Daily Cap: <b>${DAILY_LOSS_LIMIT}</b></span><br>
            <span class="prophet-data-muted">= {DAILY_LOSS_LIMIT / (STOP_POINTS * POINT_VALUE_ES * POSITION_SIZE_ES):.0f} max losing trades/day</span>
        </div>
        """, unsafe_allow_html=True)

    with ea2:
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">BREAKEVEN WIN RATE</span><br><br>
            <span class="prophet-data">At 1:1 R:R → Need <b>50%</b> win rate</span><br>
            <span class="prophet-data">At 1.5:1 R:R → Need <b>40%</b> win rate</span><br>
            <span class="prophet-data">At 2:1 R:R → Need <b>33%</b> win rate</span><br><br>
            <span class="prophet-data-muted">Confluence zones push R:R higher</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="prophet-card">
        <span class="prophet-label">THE PROPHET'S EDGE RULES</span><br><br>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
            <div>
                <span class="prophet-data" style="color:{COLORS['bullish']}">✓ TAKE THE TRADE WHEN</span><br>
                <span class="prophet-data-muted" style="font-size:0.8rem; line-height:1.8;">
                    Session Quality ≥ B grade<br>
                    VIX in 14–20 range<br>
                    Both pivots confirmed<br>
                    R:R ≥ 1.5<br>
                    Confluence zone present<br>
                    Clean rejection wick ≥ 50% of body
                </span>
            </div>
            <div>
                <span class="prophet-data" style="color:{COLORS['bearish']}">✗ SIT OUT WHEN</span><br>
                <span class="prophet-data-muted" style="font-size:0.8rem; line-height:1.8;">
                    Session Quality D or F<br>
                    VIX above 28 (extreme)<br>
                    Pivots unconfirmed on both sides<br>
                    R:R below 1.0<br>
                    Friday afternoon<br>
                    FOMC / NFP / CPI day first 30 min
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="prophet-card">
        <span class="prophet-label">POSITION SIZING BY VIX REGIME</span><br><br>
        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:0.5rem; text-align:center;">
            <div>
                <span class="prophet-data" style="color:{COLORS['bullish']}">LOW<br>&lt;14</span><br>
                <span class="prophet-data-muted">2 ES<br>Tight stops<br>Fade hard</span>
            </div>
            <div>
                <span class="prophet-data" style="color:{COLORS['accent_cyan']}">NORMAL<br>14–20</span><br>
                <span class="prophet-data-muted">2 ES<br>Standard<br>Full rules</span>
            </div>
            <div>
                <span class="prophet-data" style="color:{COLORS['warning']}">ELEVATED<br>20–28</span><br>
                <span class="prophet-data-muted">1 ES<br>Wide stops<br>Selective</span>
            </div>
            <div>
                <span class="prophet-data" style="color:{COLORS['bearish']}">EXTREME<br>&gt;28</span><br>
                <span class="prophet-data-muted">Paper<br>or sit out<br>Protect capital</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  FOOTER
# ═══════════════════════════════════════════════════════════════════════
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align:center; padding:1rem; border-top:1px solid var(--border);">
    <span class="prophet-data-muted" style="font-size:0.7rem;">
        SPX PROPHET · LEGENDARY EDITION · v2.0 · Built for the {POSITION_SIZE_ES}-lot warrior
    </span><br>
    <span class="prophet-data-muted" style="font-size:0.6rem;">
        Slope {SLOPE} pts/hr · {STOP_POINTS}-pt stops · ${DAILY_LOSS_LIMIT} daily cap
    </span>
</div>
""", unsafe_allow_html=True)
