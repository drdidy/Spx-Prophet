"""
SPX PROPHET — UI Components
Reusable rendering functions for the dashboard panels.
"""

import datetime as dt
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pytz

from config import (
    COLORS, LINE_COLORS, LINE_LABELS, POSITION_SIZE_ES, POINT_VALUE_ES,
    STOP_POINTS, DAILY_LOSS_LIMIT, TIMEZONE,
)
from line_calculator import LineValue, ConfluenceZone
from signal_engine import Signal, SessionQuality, get_vix_regime
from pivot_detector import Pivot

CT = pytz.timezone(TIMEZONE)


# ─── Hero Section ─────────────────────────────────────────────────────

def render_hero(
    es_price: float,
    spx_price: float,
    vix: float,
    offset: float,
    current_time: dt.datetime,
    session_status: str,
):
    """Top banner with prices and status."""
    vix_regime, vix_color = get_vix_regime(vix)

    st.markdown('<div class="grid-bg"></div>', unsafe_allow_html=True)

    col_title, col_session = st.columns([3, 1])
    with col_title:
        st.markdown('<p class="prophet-title">SPX PROPHET</p>', unsafe_allow_html=True)
        st.markdown('<p class="prophet-subtitle">Legendary Edition</p>', unsafe_allow_html=True)
    with col_session:
        session_color = COLORS["bullish"] if session_status == "RTH" else (
            COLORS["accent_cyan"] if session_status == "OVERNIGHT" else COLORS["text_muted"]
        )
        st.markdown(f"""
        <div style="text-align:right; padding-top:0.5rem;">
            <span class="prophet-label">SESSION</span><br>
            <span class="prophet-data" style="color:{session_color}; font-size:1rem;">{session_status}</span><br>
            <span class="prophet-data-muted">{current_time.strftime("%I:%M %p CT")}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">ES FUTURES</span><br>
            <span class="prophet-price">{es_price:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">SPX CASH</span><br>
            <span class="prophet-price-sm">{spx_price:,.2f}</span><br>
            <span class="prophet-data-muted">Offset: {offset:+.1f}</span>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">VIX</span><br>
            <span class="prophet-price-sm" style="color:{vix_color}">{vix:.2f}</span><br>
            <span class="vix-badge" style="color:{vix_color}; border:1px solid {vix_color};">{vix_regime}</span>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="prophet-card">
            <span class="prophet-label">DAILY LOSS LIMIT</span><br>
            <span class="prophet-price-sm">${DAILY_LOSS_LIMIT}</span><br>
            <span class="prophet-data-muted">{POSITION_SIZE_ES} ES / ${POINT_VALUE_ES}/pt</span>
        </div>
        """, unsafe_allow_html=True)


# ─── Four Lines Panel ─────────────────────────────────────────────────

def render_lines_panel(lines: list, es_price: float, offset: float):
    """Display the 4 dynamic trend lines with distances."""
    st.markdown(f"""
    <div class="prophet-card">
        <span class="prophet-label">THE FOUR LINES</span>
    </div>
    """, unsafe_allow_html=True)

    if not lines:
        st.info("No lines calculated. Check pivot detection.")
        return

    cols = st.columns(len(lines))
    for i, line in enumerate(lines):
        color = LINE_COLORS.get(line.name, COLORS["accent_cyan"])
        dist = line.price - es_price
        dist_sign = "+" if dist >= 0 else ""
        spx_val = line.price - offset
        arrow = "▲" if line.direction == "ascending" else "▼"

        with cols[i]:
            st.markdown(f"""
            <div class="prophet-card" style="text-align:center;">
                <span class="line-dot" style="background:{color};box-shadow:0 0 8px {color};"></span>
                <span class="prophet-label" style="color:{color}">{line.label}</span><br>
                <span class="prophet-price-sm" style="color:{color}">{line.price:,.2f}</span><br>
                <span class="prophet-data-muted">SPX {spx_val:,.2f}</span><br>
                <span class="prophet-data" style="color:{'#00ff88' if dist >= 0 else '#ff0066'};font-size:0.85rem;">
                    {dist_sign}{dist:.2f} pts {arrow}
                </span>
            </div>
            """, unsafe_allow_html=True)


# ─── Pivot Info Panel ─────────────────────────────────────────────────

def render_pivot_panel(upper: Pivot | None, lower: Pivot | None):
    """Show pivot details."""
    c1, c2 = st.columns(2)

    with c1:
        if upper:
            status = "✅ CONFIRMED" if upper.confirmed else "⚠️ UNCONFIRMED"
            st.markdown(f"""
            <div class="prophet-card prophet-card-bullish">
                <span class="prophet-label">UPPER PIVOT (HIGH)</span><br>
                <span class="prophet-price-sm" style="color:{COLORS['bullish']}">{upper.price:,.2f}</span><br>
                <span class="prophet-data-muted">{upper.time.strftime("%b %d, %I:%M %p")}</span><br>
                <span class="prophet-data" style="font-size:0.75rem;">{status}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="prophet-card">
                <span class="prophet-label">UPPER PIVOT</span><br>
                <span class="prophet-data-muted">Not detected</span>
            </div>
            """, unsafe_allow_html=True)

    with c2:
        if lower:
            status = "✅ CONFIRMED" if lower.confirmed else "⚠️ UNCONFIRMED"
            st.markdown(f"""
            <div class="prophet-card prophet-card-bearish">
                <span class="prophet-label">LOWER PIVOT (LOW)</span><br>
                <span class="prophet-price-sm" style="color:{COLORS['bearish']}">{lower.price:,.2f}</span><br>
                <span class="prophet-data-muted">{lower.time.strftime("%b %d, %I:%M %p")}</span><br>
                <span class="prophet-data" style="font-size:0.75rem;">{status}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="prophet-card">
                <span class="prophet-label">LOWER PIVOT</span><br>
                <span class="prophet-data-muted">Not detected</span>
            </div>
            """, unsafe_allow_html=True)


# ─── Signal Panel ─────────────────────────────────────────────────────

def render_signal_panel(signal: Signal | None):
    """Active signal display with entry/target/stop."""
    if signal is None or signal.direction == "NEUTRAL":
        st.markdown("""
        <div class="prophet-card" style="text-align:center; padding:2rem;">
            <span class="signal-neutral">SCANNING</span><br>
            <span class="prophet-data-muted" style="margin-top:0.5rem;display:block;">
                Waiting for hourly rejection signal...
            </span>
        </div>
        """, unsafe_allow_html=True)
        return

    css_class = "signal-long" if signal.direction == "LONG" else "signal-short"
    strength_class = f"strength-{signal.signal_strength.lower()}"

    st.markdown(f"""
    <div class="prophet-card {'prophet-card-bullish' if signal.direction == 'LONG' else 'prophet-card-bearish'}"
         style="text-align:center; padding:1.5rem;">
        <span class="{css_class}">{signal.direction}</span>
        <span class="{strength_class}" style="margin-left:8px;">{signal.signal_strength}</span>
        {"<span style='color:#f0c040;margin-left:6px;'>⚡ CONFLUENCE</span>" if signal.confluence_boost else ""}
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="prophet-card" style="text-align:center;">
            <span class="prophet-label">ENTRY</span><br>
            <span class="prophet-data">{signal.entry_line}</span><br>
            <span class="prophet-price-sm">{signal.entry_price:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        color = COLORS["bullish"] if signal.direction == "LONG" else COLORS["bearish"]
        st.markdown(f"""
        <div class="prophet-card" style="text-align:center;">
            <span class="prophet-label">TARGET</span><br>
            <span class="prophet-data">{signal.target_line or '---'}</span><br>
            <span class="prophet-price-sm" style="color:{color}">
                {signal.target_price:,.2f if signal.target_price else '---'}
            </span><br>
            <span class="prophet-data-muted">+{signal.reward_pts:.1f} pts / ${signal.potential_dollars:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="prophet-card" style="text-align:center;">
            <span class="prophet-label">STOP</span><br>
            <span class="prophet-price-sm" style="color:{COLORS['bearish']}">{signal.stop_price:,.2f}</span><br>
            <span class="prophet-data-muted">-{signal.risk_pts:.1f} pts</span><br>
            <span class="prophet-data" style="color:{COLORS['accent_gold']}">R:R {signal.rr_ratio:.1f}</span>
        </div>
        """, unsafe_allow_html=True)


# ─── Session Quality Score ────────────────────────────────────────────

def render_session_quality(sq: SessionQuality):
    """Render the composite session quality gauge."""
    grade_class = f"quality-{sq.grade.lower()}"
    pct = f"{sq.score}%"

    rec_colors = {
        "FULL SIZE": COLORS["bullish"],
        "HALF SIZE": COLORS["warning"],
        "PAPER ONLY": COLORS["bearish"],
        "SIT OUT": COLORS["text_muted"],
    }
    rec_color = rec_colors.get(sq.recommendation, COLORS["text_muted"])

    st.markdown(f"""
    <div class="prophet-card prophet-card-gold" style="text-align:center;">
        <span class="prophet-label">SESSION QUALITY</span>
        <div class="quality-score {grade_class}" style="--pct:{pct}; margin:0.75rem auto;">
            <div class="quality-inner">
                <span>{sq.grade}</span>
            </div>
        </div>
        <span class="prophet-data" style="font-size:1.1rem;">{sq.score:.0f}/100</span><br>
        <span class="vix-badge" style="color:{rec_color};border:1px solid {rec_color};margin-top:0.5rem;">
            {sq.recommendation}
        </span>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Quality Breakdown"):
        components = [
            ("VIX Regime", sq.vix_component),
            ("Range Profile", sq.range_component),
            ("Gap Size", sq.gap_component),
            ("Day of Week", sq.time_component),
            ("Pivot Clarity", sq.pivot_component),
            ("Confluence", sq.confluence_component),
        ]
        for name, val in components:
            bar_pct = val
            bar_color = COLORS["bullish"] if val >= 70 else (
                COLORS["warning"] if val >= 40 else COLORS["bearish"]
            )
            st.markdown(f"""
            <div style="margin:0.3rem 0;">
                <span class="prophet-data-muted" style="font-size:0.7rem;">{name}</span>
                <div style="background:var(--border);border-radius:4px;height:6px;margin-top:2px;">
                    <div style="background:{bar_color};width:{bar_pct}%;height:100%;border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ─── Confluence Zones ─────────────────────────────────────────────────

def render_confluence_zones(zones: list, offset: float):
    """Highlight confluence zones where lines converge."""
    if not zones:
        return

    st.markdown(f"""
    <div class="prophet-card prophet-card-gold">
        <span class="prophet-label">⚡ CONFLUENCE ZONES</span>
    </div>
    """, unsafe_allow_html=True)

    for zone in zones:
        line_names = " + ".join(zone.lines)
        spx_val = zone.price_center - offset
        st.markdown(f"""
        <div class="confluence-zone">
            <span class="prophet-data" style="color:{COLORS['accent_gold']};">
                ES {zone.price_center:,.2f} / SPX {spx_val:,.2f}
            </span><br>
            <span class="prophet-data-muted" style="font-size:0.7rem;">
                {line_names} · Strength: {zone.strength:.1f}x
            </span>
        </div>
        """, unsafe_allow_html=True)


# ─── Candlestick Chart ───────────────────────────────────────────────

def render_chart(
    candles: pd.DataFrame,
    upper_pivot: Pivot | None,
    lower_pivot: Pivot | None,
    lines: list,
    es_price: float,
    signals: list | None = None,
    confluence_zones: list | None = None,
):
    """Plotly candlestick chart with the 4 dynamic lines."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.8, 0.2],
        vertical_spacing=0.02,
    )

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=candles.index,
        open=candles["Open"],
        high=candles["High"],
        low=candles["Low"],
        close=candles["Close"],
        increasing_line_color=COLORS["bullish"],
        decreasing_line_color=COLORS["bearish"],
        increasing_fillcolor=COLORS["bullish"],
        decreasing_fillcolor=COLORS["bearish"],
        name="ES",
        showlegend=False,
    ), row=1, col=1)

    # Volume
    vol_colors = [
        COLORS["bullish"] if c >= o else COLORS["bearish"]
        for c, o in zip(candles["Close"], candles["Open"])
    ]
    fig.add_trace(go.Bar(
        x=candles.index,
        y=candles["Volume"],
        marker_color=vol_colors,
        opacity=0.3,
        name="Volume",
        showlegend=False,
    ), row=2, col=1)

    # Plot the 4 lines
    time_range = candles.index

    for line_info in lines:
        from line_calculator import get_line_series
        pivot = upper_pivot if "upper" in line_info.name else lower_pivot
        if pivot is None:
            continue
        ascending = "ascending" in line_info.name
        values = get_line_series(pivot, ascending, time_range)
        color = LINE_COLORS.get(line_info.name, "#ffffff")

        fig.add_trace(go.Scatter(
            x=time_range,
            y=values,
            mode="lines",
            name=line_info.label,
            line=dict(color=color, width=2, dash="dot"),
            opacity=0.85,
        ), row=1, col=1)

    # Current price line
    fig.add_hline(
        y=es_price, line_dash="dash",
        line_color=COLORS["accent_cyan"], line_width=1,
        opacity=0.5, row=1, col=1,
    )

    # Pivot markers
    if upper_pivot:
        fig.add_trace(go.Scatter(
            x=[upper_pivot.time],
            y=[upper_pivot.price],
            mode="markers+text",
            marker=dict(size=12, color=COLORS["bullish"], symbol="triangle-up"),
            text=["▲ HIGH PIVOT"],
            textposition="top center",
            textfont=dict(size=9, color=COLORS["bullish"]),
            name="Upper Pivot",
            showlegend=False,
        ), row=1, col=1)

    if lower_pivot:
        fig.add_trace(go.Scatter(
            x=[lower_pivot.time],
            y=[lower_pivot.price],
            mode="markers+text",
            marker=dict(size=12, color=COLORS["bearish"], symbol="triangle-down"),
            text=["▼ LOW PIVOT"],
            textposition="bottom center",
            textfont=dict(size=9, color=COLORS["bearish"]),
            name="Lower Pivot",
            showlegend=False,
        ), row=1, col=1)

    # Confluence zone shading
    if confluence_zones:
        for zone in confluence_zones:
            fig.add_hrect(
                y0=zone.price_center - 2,
                y1=zone.price_center + 2,
                fillcolor="rgba(240,192,64,0.08)",
                line=dict(color="rgba(240,192,64,0.3)", width=1, dash="dot"),
                row=1, col=1,
            )

    # Signal markers
    if signals:
        for sig_time, sig in signals:
            marker_color = COLORS["bullish"] if sig.direction == "LONG" else COLORS["bearish"]
            marker_symbol = "triangle-up" if sig.direction == "LONG" else "triangle-down"
            fig.add_trace(go.Scatter(
                x=[sig_time],
                y=[sig.entry_price],
                mode="markers",
                marker=dict(size=14, color=marker_color, symbol=marker_symbol,
                            line=dict(width=2, color="#ffffff")),
                name=f"{sig.direction} Signal",
                showlegend=False,
            ), row=1, col=1)

    # Layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLORS["bg_primary"],
        plot_bgcolor=COLORS["bg_card"],
        font=dict(family="JetBrains Mono, monospace", color=COLORS["text_primary"]),
        height=600,
        margin=dict(l=60, r=30, t=30, b=30),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10),
        ),
        xaxis2=dict(gridcolor=COLORS["border"]),
        yaxis=dict(gridcolor=COLORS["border"], side="right"),
        yaxis2=dict(gridcolor=COLORS["border"], side="right"),
    )

    fig.update_xaxes(
        gridcolor=COLORS["border"],
        showgrid=True,
        gridwidth=1,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─── Trade Journal ────────────────────────────────────────────────────

def render_trade_journal():
    """Simple trade journal stored in session state."""
    st.markdown("""
    <div class="prophet-card prophet-card-gold">
        <span class="prophet-label">TRADE JOURNAL</span>
    </div>
    """, unsafe_allow_html=True)

    if "journal" not in st.session_state:
        st.session_state.journal = []

    with st.expander("Log a Trade", expanded=False):
        jc1, jc2 = st.columns(2)
        with jc1:
            j_dir = st.selectbox("Direction", ["LONG", "SHORT"], key="j_dir")
            j_entry = st.number_input("Entry Price", value=0.0, key="j_entry")
            j_result = st.number_input("Result (pts)", value=0.0, step=0.25, key="j_result")
        with jc2:
            j_line = st.text_input("Entry Line", placeholder="e.g. UA ↗", key="j_line")
            j_quality = st.slider("Session Quality", 0, 100, 50, key="j_quality")
            j_notes = st.text_input("Notes", key="j_notes")

        if st.button("Save Trade", type="primary"):
            trade = {
                "date": dt.datetime.now(CT).strftime("%Y-%m-%d %H:%M"),
                "direction": j_dir,
                "entry_price": j_entry,
                "entry_line": j_line,
                "result_pts": j_result,
                "result_dollars": j_result * POINT_VALUE_ES * POSITION_SIZE_ES,
                "session_quality": j_quality,
                "notes": j_notes,
            }
            st.session_state.journal.append(trade)
            st.success("Trade logged!")

    if st.session_state.journal:
        import pandas as pd
        df = pd.DataFrame(st.session_state.journal)
        total_pts = df["result_pts"].sum()
        total_dollars = df["result_dollars"].sum()
        win_rate = (df["result_pts"] > 0).mean() * 100

        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            color = COLORS["bullish"] if total_pts >= 0 else COLORS["bearish"]
            st.markdown(f"""
            <div style="text-align:center;">
                <span class="prophet-label">NET P&L</span><br>
                <span class="prophet-data" style="color:{color};font-size:1.1rem;">
                    {total_pts:+.2f} pts / ${total_dollars:+,.0f}
                </span>
            </div>
            """, unsafe_allow_html=True)
        with mc2:
            st.markdown(f"""
            <div style="text-align:center;">
                <span class="prophet-label">WIN RATE</span><br>
                <span class="prophet-data" style="font-size:1.1rem;">{win_rate:.0f}%</span>
            </div>
            """, unsafe_allow_html=True)
        with mc3:
            st.markdown(f"""
            <div style="text-align:center;">
                <span class="prophet-label">TRADES</span><br>
                <span class="prophet-data" style="font-size:1.1rem;">{len(df)}</span>
            </div>
            """, unsafe_allow_html=True)

        st.dataframe(df, use_container_width=True, hide_index=True)
