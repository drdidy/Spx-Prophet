"""
SPX PROPHET — UI Components v9.0
Legendary dark command-center theme. Vivid glowing accents on void backgrounds.
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

# ─── Color constants (dark command-center theme) ──────────────────────
GREEN = "#00ff88"
GREEN_LT = "#00ff88"
RED = "#ff0055"
RED_LT = "#ff0055"
GOLD = "#f0c040"
GOLD_LT = "#f5d060"
BLUE = "#00d4ff"
BLUE_LT = "#33ddff"
PURPLE = "#7B2CBF"
CYAN = "#00d4ff"
TXT = "#e8e8f0"
TXT2 = "#a0a0c0"
TXT3 = "#555577"


def render_hero(
    es_price: float, spx_price: float, vix: float,
    offset: float, current_time: dt.datetime, session_status: str,
):
    vix_regime, vix_color = get_vix_regime(vix)

    session_colors = {
        "RTH": GREEN, "OVERNIGHT": BLUE,
        "RTH · PIVOT WINDOW": GOLD, "CLOSED": TXT3,
    }
    sc = session_colors.get(session_status, TXT3)

    html = (
        f'<div class="hero-bar">'
        f'<div>'
        f'<div class="hero-title">SPX PROPHET</div>'
        f'<div class="hero-sub">Legendary Edition</div>'
        f'</div>'
        f'<div class="ticker-strip">'
        f'<div class="ticker-item">'
        f'<span class="lbl">ES Futures</span>'
        f'<span class="big-hero">{es_price:,.2f}</span>'
        f'</div>'
        f'<div class="ticker-item">'
        f'<span class="lbl">SPX Cash</span>'
        f'<span class="med">{spx_price:,.2f}</span><br>'
        f'<span class="dim">{offset:+.1f}</span>'
        f'</div>'
        f'<div class="ticker-item">'
        f'<span class="lbl">VIX</span>'
        f'<span class="med" style="color:{vix_color}">{vix:.2f}</span><br>'
        f'<span class="vix-badge" style="color:#fff;background:{vix_color};border:none;">{vix_regime}</span>'
        f'</div>'
        f'<div class="ticker-item">'
        f'<span class="lbl">⏰ Session</span>'
        f'<span class="sm" style="color:{sc};font-weight:600;">{session_status}</span><br>'
        f'<span class="dim">{current_time.strftime("%I:%M %p CT")}</span>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_lines_panel(lines: list, es_price: float, offset: float):
    if not lines:
        st.info("No lines calculated — check pivot detection.")
        return

    # Icons per line type
    LINE_ICONS = {
        "asc_ceiling": "📈",
        "asc_floor": "📈",
        "desc_ceiling": "📉",
        "desc_floor": "📉",
        "hw_ascending": "⬆",
        "lw_descending": "⬇",
    }
    LINE_SHORT = {
        "asc_ceiling": "AC",
        "asc_floor": "AF",
        "desc_ceiling": "DC",
        "desc_floor": "DF",
        "hw_ascending": "HW",
        "lw_descending": "LW",
    }

    cards = ""
    for line in lines:
        color = LINE_COLORS.get(line.name, BLUE)
        dist = line.price - es_price
        sign = "+" if dist >= 0 else ""
        dc = GREEN if dist >= 0 else RED
        arrow = "^" if line.direction == "ascending" else "v"
        spx = line.price - offset
        icon = LINE_ICONS.get(line.name, "")
        short = LINE_SHORT.get(line.name, line.label)

        cards += (
            f'<div class="ticker-item" style="flex:1;min-width:0;">'
            f'<div style="font-size:2.5rem;margin-bottom:8px;line-height:1;">{icon}</div>'
            f'<span class="lbl" style="color:{color}">{short}</span><br>'
            f'<span class="med" style="color:{color}">{line.price:,.2f}</span><br>'
            f'<span class="dim">SPX {spx:,.2f}</span><br>'
            f'<span class="sm" style="color:{dc};font-weight:600;">{sign}{dist:.1f} {arrow}</span>'
            f'</div>'
        )

    html = (
        f'<div class="pc pc-gold">'
        f'<span class="lbl" style="font-size:0.7rem;">📐 THE SIX LINES</span>'
        f'<div style="display:flex;gap:0.5rem;margin-top:0.6rem;flex-wrap:wrap;">'
        f'{cards}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_pivot_panel(upper: Pivot | None, lower: Pivot | None):
    def _piv_high(piv):
        """Render pivot HIGH showing both green and red candle anchors."""
        if not piv:
            return (
                '<div class="pc" style="flex:1;">'
                '<span class="lbl">🎯 PIVOT HIGH</span>'
                '<span class="dim">Not detected</span>'
                '</div>'
            )
        status = "CONFIRMED" if piv.confirmed else "UNCONFIRMED"
        s_color = GREEN if piv.confirmed else GOLD
        s_bg = "rgba(0,255,136,0.1)" if piv.confirmed else "rgba(240,192,64,0.1)"
        gh = piv.green_candle_price if piv.green_candle_price else piv.price
        rh = piv.red_candle_price if piv.red_candle_price else piv.price
        return (
            '<div class="pc pc-green" style="flex:1;">'
            '<span class="lbl">🎯 PIVOT HIGH</span>'
            '<span class="dim">' + piv.time.strftime("%b %d · %I:%M %p") + '</span><br>'
            '<div style="display:flex;gap:1rem;margin-top:0.4rem;">'
            '<div>'
            '<span class="dim" style="font-size:0.6rem;">GREEN HIGH → DC</span><br>'
            '<span class="med" style="color:' + GREEN + ';">' + f'{gh:,.2f}' + '</span>'
            '</div>'
            '<div>'
            '<span class="dim" style="font-size:0.6rem;">RED HIGH → AC</span><br>'
            '<span class="med" style="color:' + RED + ';">' + f'{rh:,.2f}' + '</span>'
            '</div>'
            '</div>'
            '<span style="font-size:0.65rem;font-weight:700;color:' + s_color
            + ';background:' + s_bg + ';padding:2px 8px;border-radius:12px;margin-top:0.3rem;display:inline-block;">'
            + status + '</span>'
            '</div>'
        )

    def _piv_low(piv):
        """Render pivot LOW showing both red and green candle anchors."""
        if not piv:
            return (
                '<div class="pc" style="flex:1;">'
                '<span class="lbl">🎯 PIVOT LOW</span>'
                '<span class="dim">Not detected</span>'
                '</div>'
            )
        status = "CONFIRMED" if piv.confirmed else "UNCONFIRMED"
        s_color = GREEN if piv.confirmed else GOLD
        s_bg = "rgba(0,255,136,0.1)" if piv.confirmed else "rgba(240,192,64,0.1)"
        rl = piv.red_candle_price if piv.red_candle_price else piv.price
        gl = piv.green_candle_price if piv.green_candle_price else piv.price
        return (
            '<div class="pc pc-red" style="flex:1;">'
            '<span class="lbl">🎯 PIVOT LOW</span>'
            '<span class="dim">' + piv.time.strftime("%b %d · %I:%M %p") + '</span><br>'
            '<div style="display:flex;gap:1rem;margin-top:0.4rem;">'
            '<div>'
            '<span class="dim" style="font-size:0.6rem;">RED LOW → AF</span><br>'
            '<span class="med" style="color:' + RED + ';">' + f'{rl:,.2f}' + '</span>'
            '</div>'
            '<div>'
            '<span class="dim" style="font-size:0.6rem;">GREEN LOW → DF</span><br>'
            '<span class="med" style="color:' + GREEN + ';">' + f'{gl:,.2f}' + '</span>'
            '</div>'
            '</div>'
            '<span style="font-size:0.65rem;font-weight:700;color:' + s_color
            + ';background:' + s_bg + ';padding:2px 8px;border-radius:12px;margin-top:0.3rem;display:inline-block;">'
            + status + '</span>'
            '</div>'
        )

    html = (
        '<div style="display:flex;gap:0.5rem;">'
        + _piv_high(upper)
        + _piv_low(lower)
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_signal_panel(signal: Signal | None):
    if signal is None or signal.direction == "NEUTRAL":
        html = (
            '<div class="pc" style="text-align:center;padding:2rem 1rem;">'
            '<div class="sig sig-scan">SCANNING</div>'
            '<div class="dim" style="margin-top:0.8rem;">Waiting for hourly rejection signal...</div>'
            '</div>'
        )
        st.markdown(html, unsafe_allow_html=True)
        return

    sig_cls = "sig-long" if signal.direction == "LONG" else "sig-short"
    str_cls = {"PREMIUM": "str-p", "HIGH": "str-h"}.get(signal.signal_strength, "str-s")
    dir_color = GREEN if signal.direction == "LONG" else RED
    confl = f'<span style="color:{GOLD};margin-left:8px;font-weight:700;">CONFLUENCE</span>' if signal.confluence_boost else ""
    card_cls = "pc-green" if signal.direction == "LONG" else "pc-red"

    badge_html = (
        f'<div class="pc {card_cls}" style="text-align:center;padding:1.5rem;">'
        f'<div class="sig {sig_cls}">{signal.direction}</div>'
        f'<div style="margin-top:0.6rem;">'
        f'<span class="badge {str_cls}">{signal.signal_strength}</span>{confl}'
        f'</div>'
        f'</div>'
    )
    st.markdown(badge_html, unsafe_allow_html=True)

    details_html = (
        f'<div style="display:flex;gap:0.5rem;">'
        f'<div class="pc" style="flex:1;text-align:center;">'
        f'<span class="lbl">Entry</span>'
        f'<span class="sm">{signal.entry_line}</span><br>'
        f'<span class="med">{signal.entry_price:,.2f}</span>'
        f'</div>'
        f'<div class="pc {card_cls}" style="flex:1;text-align:center;">'
        f'<span class="lbl">Target</span>'
        f'<span class="sm">{signal.target_line or "—"}</span><br>'
        f'<span class="med" style="color:{dir_color}">{f"{signal.target_price:,.2f}" if signal.target_price else "—"}</span><br>'
        f'<span class="dim">+{signal.reward_pts:.1f} pts / ${signal.potential_dollars:,.0f}</span>'
        f'</div>'
        f'<div class="pc pc-red" style="flex:1;text-align:center;">'
        f'<span class="lbl">Stop</span>'
        f'<span class="med" style="color:{RED}">{signal.stop_price:,.2f}</span><br>'
        f'<span class="dim">-{signal.risk_pts:.1f} pts</span><br>'
        f'<span class="sm" style="color:{GOLD};font-weight:700;">R:R {signal.rr_ratio:.1f}</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(details_html, unsafe_allow_html=True)


def render_session_quality(sq: SessionQuality):
    grade_cls = f"qring-{sq.grade.lower()}"
    pct = f"{sq.score}%"
    rec_colors = {
        "FULL SIZE": GREEN, "HALF SIZE": GOLD,
        "PAPER ONLY": RED, "SIT OUT": TXT3,
    }
    rec_bgs = {
        "FULL SIZE": "rgba(0,255,136,0.1)",
        "HALF SIZE": "rgba(240,192,64,0.1)",
        "PAPER ONLY": "rgba(255,0,85,0.1)",
        "SIT OUT": "rgba(85,85,119,0.1)",
    }
    rc = rec_colors.get(sq.recommendation, TXT3)
    rb = rec_bgs.get(sq.recommendation, "rgba(85,85,119,0.1)")

    bars = ""
    components = [
        ("VIX", sq.vix_component), ("Range", sq.range_component),
        ("Gap", sq.gap_component), ("Day", sq.time_component),
        ("Pivots", sq.pivot_component), ("Confl.", sq.confluence_component),
    ]
    for name, val in components:
        bc = GREEN if val >= 70 else (GOLD if val >= 40 else RED)
        bars += (
            f'<div style="margin:5px 0;">'
            f'<div style="display:flex;justify-content:space-between;">'
            f'<span style="font-size:0.72rem;font-weight:500;color:{TXT2};">{name}</span>'
            f'<span style="font-size:0.72rem;font-weight:700;color:{TXT};">{val:.0f}</span>'
            f'</div>'
            f'<div style="background:#1a1a35;border-radius:4px;height:6px;margin-top:3px;">'
            f'<div style="background:{bc};width:{val}%;height:100%;border-radius:4px;transition:width 0.5s ease;box-shadow:0 0 6px {bc};"></div>'
            f'</div>'
            f'</div>'
        )

    html = (
        f'<div class="pc pc-gold" style="text-align:center;">'
        f'<span class="lbl">🏆 Session Quality</span>'
        f'<div class="qring {grade_cls}" style="--pct:{pct}">'
        f'<div class="qring-inner"><span>{sq.grade}</span></div>'
        f'</div>'
        f'<div class="sm" style="margin-top:0.4rem;color:{TXT};">{sq.score:.0f} / 100</div>'
        f'<div style="margin-top:0.5rem;">'
        f'<span class="badge" style="color:{rc};background:{rb};border:1px solid {rc};">{sq.recommendation}</span>'
        f'</div>'
        f'<div style="margin-top:0.8rem;text-align:left;">'
        f'{bars}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_confluence_zones(zones: list, offset: float):
    if not zones:
        return
    z_items = ""
    for z in zones:
        names = " + ".join(z.lines)
        spx = z.price_center - offset
        z_items += (
            f'<div class="cz">'
            f'<span class="sm" style="color:{GOLD};font-weight:700;">ES {z.price_center:,.2f}</span>'
            f'<span class="dim"> / SPX {spx:,.2f} / {names} / {z.strength:.1f}x</span>'
            f'</div>'
        )

    html = (
        f'<div class="pc pc-gold">'
        f'<span class="lbl">🔥 Confluence Zones</span>'
        f'{z_items}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_chart(
    candles: pd.DataFrame, upper_pivot: Pivot | None, lower_pivot: Pivot | None,
    lines: list, es_price: float, signals: list | None = None,
    confluence_zones: list | None = None,
    rth_high: Pivot | None = None, rth_low: Pivot | None = None,
    trade_date=None, prior_day_high: float | None = None,
    prior_day_low: float | None = None,
):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.82, 0.18], vertical_spacing=0.015)

    fig.add_trace(go.Candlestick(
        x=candles.index, open=candles["Open"], high=candles["High"],
        low=candles["Low"], close=candles["Close"],
        increasing_line_color=GREEN, decreasing_line_color=RED,
        increasing_fillcolor=GREEN, decreasing_fillcolor=RED,
        name="ES", showlegend=False,
    ), row=1, col=1)

    vol_colors = [f"rgba(0,255,136,0.25)" if c >= o else f"rgba(255,0,85,0.25)"
                  for c, o in zip(candles["Close"], candles["Open"])]
    fig.add_trace(go.Bar(
        x=candles.index, y=candles["Volume"], marker_color=vol_colors,
        name="Vol", showlegend=False,
    ), row=2, col=1)

    # ── VWAP (today's candles only) ──
    if trade_date is not None:
        today_start = CT.localize(dt.datetime.combine(trade_date, dt.time(0, 0)))
        today_mask = candles.index >= today_start
        today_df = candles[today_mask]
        if len(today_df) > 1 and "Volume" in today_df.columns:
            typical = (today_df["High"] + today_df["Low"] + today_df["Close"]) / 3.0
            cum_tpv = (typical * today_df["Volume"]).cumsum()
            cum_vol = today_df["Volume"].cumsum()
            vwap = cum_tpv / cum_vol.replace(0, float("nan"))
            vwap = vwap.dropna()
            if len(vwap) > 0:
                fig.add_trace(go.Scatter(
                    x=vwap.index, y=vwap.values, mode="lines", name="VWAP",
                    line=dict(color="#FFD700", width=2, dash="dash"), opacity=0.85,
                ), row=1, col=1)

    # ── Prior Day High / Low ──
    if prior_day_high is not None:
        fig.add_hline(y=prior_day_high, line_dash="dot", line_color="#666688",
                      line_width=1, opacity=0.6, row=1, col=1,
                      annotation_text="Prev High", annotation_position="top left",
                      annotation_font=dict(size=9, color="#888899"))
    if prior_day_low is not None:
        fig.add_hline(y=prior_day_low, line_dash="dot", line_color="#666688",
                      line_width=1, opacity=0.6, row=1, col=1,
                      annotation_text="Prev Low", annotation_position="bottom left",
                      annotation_font=dict(size=9, color="#888899"))

    # ── Draw all 6 lines (only from pivot time forward) ──
    time_range = candles.index

    # Map each line name to (pivot, anchor_price, anchor_time, slope)
    from config import CHANNEL_SLOPE, SLOPE as WICK_SLOPE
    from line_calculator import get_line_series

    line_anchors = {}
    if upper_pivot:
        # Ascending ceiling: red candle HIGH at pivot HIGH
        line_anchors["asc_ceiling"] = (
            upper_pivot,
            upper_pivot.red_candle_price or upper_pivot.price,
            upper_pivot.red_candle_time or upper_pivot.time,
            CHANNEL_SLOPE,
        )
        # Descending ceiling: green candle HIGH at pivot HIGH
        line_anchors["desc_ceiling"] = (
            upper_pivot,
            upper_pivot.green_candle_price or upper_pivot.price,
            upper_pivot.green_candle_time or upper_pivot.time,
            CHANNEL_SLOPE,
        )
    if lower_pivot:
        # Ascending floor: red candle LOW at pivot LOW
        line_anchors["asc_floor"] = (
            lower_pivot,
            lower_pivot.red_candle_price or lower_pivot.price,
            lower_pivot.red_candle_time or lower_pivot.time,
            CHANNEL_SLOPE,
        )
        # Descending floor: green candle LOW at pivot LOW
        line_anchors["desc_floor"] = (
            lower_pivot,
            lower_pivot.green_candle_price or lower_pivot.price,
            lower_pivot.green_candle_time or lower_pivot.time,
            CHANNEL_SLOPE,
        )
    if rth_high:
        line_anchors["hw_ascending"] = (rth_high, rth_high.price, rth_high.time, WICK_SLOPE)
    if rth_low:
        line_anchors["lw_descending"] = (rth_low, rth_low.price, rth_low.time, WICK_SLOPE)

    for li in lines:
        anchor_data = line_anchors.get(li.name)
        if anchor_data is None:
            continue
        pivot, anchor_price, anchor_time, slope = anchor_data
        ascending = li.direction == "ascending"
        values = get_line_series(
            pivot, ascending, time_range,
            slope=slope, anchor_price=anchor_price, anchor_time=anchor_time,
        )
        color = LINE_COLORS.get(li.name, "#888")
        # Filter to only timestamps from pivot onward
        x_vals = [t for t, v in zip(time_range, values) if v is not None]
        y_vals = [v for v in values if v is not None]
        if x_vals:
            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals, mode="lines", name=li.label,
                line=dict(color=color, width=2), opacity=0.9,
                connectgaps=False,
            ), row=1, col=1)

    # Current price line
    fig.add_hline(y=es_price, line_dash="dash", line_color="#00d4ff",
                  line_width=1, opacity=0.3, row=1, col=1)

    # Pivot markers
    if upper_pivot:
        fig.add_trace(go.Scatter(
            x=[upper_pivot.time], y=[upper_pivot.price], mode="markers",
            marker=dict(size=12, color=GREEN, symbol="triangle-up",
                        line=dict(width=2, color="#e8e8f0")),
            name="High Pivot", showlegend=False,
        ), row=1, col=1)

    if lower_pivot:
        fig.add_trace(go.Scatter(
            x=[lower_pivot.time], y=[lower_pivot.price], mode="markers",
            marker=dict(size=12, color=RED, symbol="triangle-down",
                        line=dict(width=2, color="#e8e8f0")),
            name="Low Pivot", showlegend=False,
        ), row=1, col=1)

    if rth_high:
        fig.add_trace(go.Scatter(
            x=[rth_high.time], y=[rth_high.price], mode="markers",
            marker=dict(size=10, color="#a0a0c0", symbol="diamond",
                        line=dict(width=1, color="#e8e8f0")),
            name="RTH High", showlegend=False,
        ), row=1, col=1)

    if rth_low:
        fig.add_trace(go.Scatter(
            x=[rth_low.time], y=[rth_low.price], mode="markers",
            marker=dict(size=10, color="#a0a0c0", symbol="diamond",
                        line=dict(width=1, color="#e8e8f0")),
            name="RTH Low", showlegend=False,
        ), row=1, col=1)

    # Confluence zones
    if confluence_zones:
        for z in confluence_zones:
            fig.add_hrect(y0=z.price_center-2, y1=z.price_center+2,
                          fillcolor="rgba(240,192,64,0.06)",
                          line=dict(color="rgba(240,192,64,0.2)", width=1, dash="dot"),
                          row=1, col=1)

    # Signal markers
    if signals:
        for sig_time, sig in signals:
            mc = GREEN if sig.direction == "LONG" else RED
            ms = "triangle-up" if sig.direction == "LONG" else "triangle-down"
            fig.add_trace(go.Scatter(
                x=[sig_time], y=[sig.entry_price], mode="markers",
                marker=dict(size=12, color=mc, symbol=ms,
                            line=dict(width=2, color="#e8e8f0")),
                showlegend=False,
            ), row=1, col=1)

    # ── Price distance annotations (nearest line above / below) ──
    if lines:
        above_lines = [(li, li.price - es_price) for li in lines if li.price > es_price]
        below_lines = [(li, es_price - li.price) for li in lines if li.price < es_price]
        _SHORT_MAP = {
            "asc_ceiling": "AC", "asc_floor": "AF",
            "desc_ceiling": "DC", "desc_floor": "DF",
            "hw_ascending": "HW", "lw_descending": "LW",
        }
        ann_x = candles.index[-1]
        if above_lines:
            nearest_above = min(above_lines, key=lambda x: x[1])
            sn = _SHORT_MAP.get(nearest_above[0].name, nearest_above[0].label)
            fig.add_annotation(
                x=ann_x, y=es_price + nearest_above[1] * 0.5,
                text="+" + f"{nearest_above[1]:.1f} to {sn}",
                showarrow=False, font=dict(size=10, color=GREEN, family="JetBrains Mono"),
                xanchor="left", xshift=10, bgcolor="rgba(0,0,0,0.5)",
                bordercolor=GREEN, borderwidth=1, borderpad=3,
            )
        if below_lines:
            nearest_below = min(below_lines, key=lambda x: x[1])
            sn = _SHORT_MAP.get(nearest_below[0].name, nearest_below[0].label)
            fig.add_annotation(
                x=ann_x, y=es_price - nearest_below[1] * 0.5,
                text="-" + f"{nearest_below[1]:.1f} to {sn}",
                showarrow=False, font=dict(size=10, color=RED, family="JetBrains Mono"),
                xanchor="left", xshift=10, bgcolor="rgba(0,0,0,0.5)",
                bordercolor=RED, borderwidth=1, borderpad=3,
            )

    # Dark plot area
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#020209", plot_bgcolor="#060612",
        font=dict(family="JetBrains Mono", color="#a0a0c0", size=10),
        height=600, margin=dict(l=50, r=120, t=20, b=25),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0.5,
                    xanchor="center", font=dict(size=9, family="Outfit", color="#a0a0c0")),
        yaxis=dict(gridcolor="#1a1a35", side="right", gridwidth=1),
        yaxis2=dict(gridcolor="#1a1a35", side="right"),
        xaxis=dict(gridcolor="#1a1a35"),
        xaxis2=dict(gridcolor="#1a1a35"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _get_levels_at_time(
    target_time, upper_pivot, lower_pivot, rth_high, rth_low, offset,
):
    """Compute all 6 line prices at a given timestamp. Returns sorted list."""
    from line_calculator import calculate_line_value

    from config import CHANNEL_SLOPE, SLOPE as WICK_SLOPE

    DOT_COLORS = {
        "asc_ceiling": "#FF4444",
        "asc_floor": "#FF4444",
        "desc_ceiling": "#00FF88",
        "desc_floor": "#00FF88",
        "hw_ascending": "#a0a0c0",
        "lw_descending": "#a0a0c0",
    }
    SHORT_NAMES = {
        "asc_ceiling": "AC",
        "asc_floor": "AF",
        "desc_ceiling": "DC",
        "desc_floor": "DF",
        "hw_ascending": "HW",
        "lw_descending": "LW",
    }

    # Each entry: (name, anchor_price, anchor_time, ascending, slope)
    line_defs = []
    if upper_pivot:
        line_defs.append(("asc_ceiling",
            upper_pivot.red_candle_price or upper_pivot.price,
            upper_pivot.red_candle_time or upper_pivot.time,
            True, CHANNEL_SLOPE))
        line_defs.append(("desc_ceiling",
            upper_pivot.green_candle_price or upper_pivot.price,
            upper_pivot.green_candle_time or upper_pivot.time,
            False, CHANNEL_SLOPE))
    if lower_pivot:
        line_defs.append(("asc_floor",
            lower_pivot.red_candle_price or lower_pivot.price,
            lower_pivot.red_candle_time or lower_pivot.time,
            True, CHANNEL_SLOPE))
        line_defs.append(("desc_floor",
            lower_pivot.green_candle_price or lower_pivot.price,
            lower_pivot.green_candle_time or lower_pivot.time,
            False, CHANNEL_SLOPE))
    if rth_high:
        line_defs.append(("hw_ascending", rth_high.price, rth_high.time, True, WICK_SLOPE))
    if rth_low:
        line_defs.append(("lw_descending", rth_low.price, rth_low.time, False, WICK_SLOPE))

    levels = []
    for name, anchor_price, anchor_time, ascending, slope in line_defs:
        price = calculate_line_value(anchor_price, anchor_time, target_time, ascending, slope=slope)
        levels.append({
            "name": name,
            "short": SHORT_NAMES[name],
            "color": DOT_COLORS[name],
            "es": price,
            "spx": price - offset,
        })

    levels.sort(key=lambda x: x["es"], reverse=True)
    return levels


def render_9am_levels(upper_pivot, lower_pivot, rth_high, rth_low, trade_date, offset, es_price=None):
    """Panel 1: Static 9 AM CT levels with optional distance column."""
    nine_am = CT.localize(dt.datetime.combine(trade_date, dt.time(9, 0)))
    levels = _get_levels_at_time(nine_am, upper_pivot, lower_pivot, rth_high, rth_low, offset)

    if not levels:
        st.caption("No levels available")
        return

    header = (
        '<div style="margin-bottom:10px;">'
        '<span style="font-family:Orbitron,sans-serif;font-size:0.7rem;font-weight:700;'
        'letter-spacing:2.5px;color:#f0c040;text-transform:uppercase;">9 AM LEVELS</span>'
        '</div>'
    )
    rows = ""
    for lv in levels:
        dist_cell = ""
        if es_price is not None:
            dist = lv["es"] - es_price
            sign = "+" if dist >= 0 else ""
            close = abs(dist) <= 5.0
            dc = GREEN if close else TXT2
            fw = "700" if close else "500"
            dist_cell = (
                f'<td style="padding:6px 4px;font-family:JetBrains Mono,monospace;font-size:0.75rem;'
                f'font-weight:{fw};color:{dc};text-align:right;">{sign}{dist:.1f}</td>'
            )
        rows += (
            f'<tr>'
            f'<td style="padding:6px 6px;"><span style="display:inline-block;width:10px;height:10px;'
            f'border-radius:50%;background:{lv["color"]};box-shadow:0 0 6px {lv["color"]};"></span></td>'
            f'<td style="padding:6px 6px;font-family:JetBrains Mono,monospace;font-size:0.82rem;'
            f'font-weight:700;color:#e8e8f0;">{lv["short"]}</td>'
            f'<td style="padding:6px 6px;font-family:JetBrains Mono,monospace;font-size:0.85rem;'
            f'font-weight:600;color:#e8e8f0;text-align:right;">{lv["es"]:,.1f}</td>'
            f'<td style="padding:6px 6px;font-family:Outfit,sans-serif;font-size:0.75rem;'
            f'color:#a0a0c0;text-align:right;">{lv["spx"]:,.1f}</td>'
            f'{dist_cell}'
            f'</tr>'
        )

    dist_header = ""
    if es_price is not None:
        dist_header = (
            '<th style="padding:4px 4px;font-family:Outfit,sans-serif;font-size:0.65rem;font-weight:600;'
            'color:#555577;text-align:right;text-transform:uppercase;">Dist</th>'
        )

    html = (
        f'{header}'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="border-bottom:2px solid #1a1a35;">'
        f'<th></th>'
        f'<th style="padding:4px 6px;font-family:Outfit,sans-serif;font-size:0.65rem;font-weight:600;'
        f'color:#555577;text-align:left;text-transform:uppercase;">Line</th>'
        f'<th style="padding:4px 6px;font-family:Outfit,sans-serif;font-size:0.65rem;font-weight:600;'
        f'color:#555577;text-align:right;text-transform:uppercase;">ES</th>'
        f'<th style="padding:4px 6px;font-family:Outfit,sans-serif;font-size:0.65rem;font-weight:600;'
        f'color:#555577;text-align:right;text-transform:uppercase;">SPX</th>'
        f'{dist_header}'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_live_levels(upper_pivot, lower_pivot, rth_high, rth_low, trade_date, offset, es_price, ref_hour):
    """Panel 2: Live levels at next hourly candle close."""
    import datetime as _dt

    # Use trade_date for ALL date logic — NOT real "now"
    trade_dow = trade_date.weekday()  # 0=Mon..6=Sun
    is_weekend = trade_dow >= 5

    if is_weekend:
        # Weekend (Sat/Sun): futures reopen Sunday 5 PM, next full hour is 6 PM
        days_to_sun = 6 - trade_dow if trade_dow != 6 else 0
        sunday = trade_date + _dt.timedelta(days=days_to_sun)
        target_time = CT.localize(dt.datetime.combine(sunday, dt.time(18, 0)))
    elif 16 <= ref_hour < 17:
        # During daily maintenance (4-5 PM Mon-Thu): show 6 PM same day
        target_time = CT.localize(dt.datetime.combine(trade_date, dt.time(18, 0)))
    elif 9 <= ref_hour < 12:
        # During primary trading session: show next full hour
        target_hour = ref_hour + 1
        target_time = CT.localize(dt.datetime.combine(trade_date, dt.time(target_hour, 0)))
    elif ref_hour >= 17 or ref_hour < 4:
        # Overnight session: show next full hour
        next_hr = (ref_hour + 1) % 24
        if next_hr <= ref_hour:
            target_time = CT.localize(dt.datetime.combine(trade_date + _dt.timedelta(days=1), dt.time(next_hr, 0)))
        else:
            target_time = CT.localize(dt.datetime.combine(trade_date, dt.time(next_hr, 0)))
    elif ref_hour < 9:
        # Pre-market (5 AM - 9 AM): show next full hour
        target_time = CT.localize(dt.datetime.combine(trade_date, dt.time(ref_hour + 1, 0)))
    elif ref_hour >= 12 and ref_hour < 16:
        # Afternoon (12-4 PM): show next full hour
        target_time = CT.localize(dt.datetime.combine(trade_date, dt.time(ref_hour + 1, 0)))
    else:
        # Fallback
        target_time = CT.localize(dt.datetime.combine(trade_date, dt.time(10, 0)))

    time_label = target_time.strftime("%a %b %d, %I:%M %p CT")

    levels = _get_levels_at_time(target_time, upper_pivot, lower_pivot, rth_high, rth_low, offset)

    if not levels:
        st.caption("No levels available")
        return

    header = (
        '<div style="margin-bottom:2px;">'
        '<span style="font-family:Orbitron,sans-serif;font-size:0.7rem;font-weight:700;'
        'letter-spacing:2.5px;color:#00d4ff;text-transform:uppercase;">⚡ NEXT HOUR LEVELS</span>'
        '</div>'
        f'<div style="margin-bottom:10px;">'
        f'<span style="font-family:Outfit,sans-serif;font-size:0.7rem;color:#555577;">'
        f'at {time_label}</span>'
        f'</div>'
    )
    rows = ""
    for lv in levels:
        near = abs(lv["es"] - es_price) <= 3.0
        dist = lv["es"] - es_price
        sign = "+" if dist >= 0 else ""
        close = abs(dist) <= 5.0
        dc = GREEN if close else TXT2
        fw = "700" if close else "500"
        row_style = (
            'background:rgba(0,212,255,0.08);border-left:3px solid #00d4ff;'
            if near else ''
        )
        rows += (
            f'<tr style="{row_style}">'
            f'<td style="padding:6px 6px;"><span style="display:inline-block;width:10px;height:10px;'
            f'border-radius:50%;background:{lv["color"]};box-shadow:0 0 6px {lv["color"]};"></span></td>'
            f'<td style="padding:6px 6px;font-family:JetBrains Mono,monospace;font-size:0.82rem;'
            f'font-weight:700;color:#e8e8f0;">{lv["short"]}</td>'
            f'<td style="padding:6px 6px;font-family:JetBrains Mono,monospace;font-size:0.85rem;'
            f'font-weight:{"800" if near else "600"};color:{"#00d4ff" if near else "#e8e8f0"};'
            f'text-align:right;">{lv["es"]:,.1f}</td>'
            f'<td style="padding:6px 6px;font-family:Outfit,sans-serif;font-size:0.75rem;'
            f'color:#a0a0c0;text-align:right;">{lv["spx"]:,.1f}</td>'
            f'<td style="padding:6px 4px;font-family:JetBrains Mono,monospace;font-size:0.75rem;'
            f'font-weight:{fw};color:{dc};text-align:right;">{sign}{dist:.1f}</td>'
            f'</tr>'
        )

    html = (
        f'{header}'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="border-bottom:2px solid #1a1a35;">'
        f'<th></th>'
        f'<th style="padding:4px 6px;font-family:Outfit,sans-serif;font-size:0.65rem;font-weight:600;'
        f'color:#555577;text-align:left;text-transform:uppercase;">Line</th>'
        f'<th style="padding:4px 6px;font-family:Outfit,sans-serif;font-size:0.65rem;font-weight:600;'
        f'color:#555577;text-align:right;text-transform:uppercase;">ES</th>'
        f'<th style="padding:4px 6px;font-family:Outfit,sans-serif;font-size:0.65rem;font-weight:600;'
        f'color:#555577;text-align:right;text-transform:uppercase;">SPX</th>'
        f'<th style="padding:4px 4px;font-family:Outfit,sans-serif;font-size:0.65rem;font-weight:600;'
        f'color:#555577;text-align:right;text-transform:uppercase;">Dist</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_trade_journal():
    """Legacy journal — kept for backward compat. Persistent journal is in tab."""
    st.info("Use the JOURNAL tab for persistent trade logging with CSV export.")


def render_daily_pnl_card(journal_df, trade_date, daily_loss_limit: float):
    """Compact card showing today's realized P&L, trade count, remaining loss budget."""
    today_str = trade_date.strftime("%Y-%m-%d")
    today_trades = journal_df[journal_df["date"] == today_str] if not journal_df.empty else pd.DataFrame()

    if today_trades.empty:
        realized_pnl = 0.0
        num_trades = 0
        wins = 0
    else:
        today_trades_pts = pd.to_numeric(today_trades["result_dollars"], errors="coerce").fillna(0)
        realized_pnl = today_trades_pts.sum()
        num_trades = len(today_trades)
        wins = int((pd.to_numeric(today_trades["result_pts"], errors="coerce").fillna(0) > 0).sum())

    losses_today = abs(min(realized_pnl, 0))
    remaining_budget = max(daily_loss_limit - losses_today, 0)
    budget_pct = remaining_budget / daily_loss_limit * 100 if daily_loss_limit > 0 else 100

    pnl_color = GREEN if realized_pnl >= 0 else RED
    budget_color = GREEN if budget_pct > 50 else (GOLD if budget_pct > 25 else RED)
    pnl_sign = "+" if realized_pnl >= 0 else ""

    html = (
        f'<div class="pc" style="border-left:4px solid {pnl_color};">'
        f'<div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">'
        f'<div style="text-align:center;min-width:120px;">'
        f'<div style="font-size:2rem;line-height:1;margin-bottom:6px;">💰</div>'
        f'<span class="lbl">TODAY P&L</span>'
        f'<div class="big-hero" style="color:{pnl_color};font-size:1.6rem;">{pnl_sign}${realized_pnl:,.0f}</div>'
        f'</div>'
        f'<div style="text-align:center;min-width:80px;">'
        f'<span class="lbl">TRADES</span>'
        f'<div class="med" style="color:{TXT};">{num_trades}</div>'
        f'<span class="dim">{wins}W / {num_trades - wins}L</span>'
        f'</div>'
        f'<div style="flex:1;min-width:140px;">'
        f'<span class="lbl">LOSS BUDGET REMAINING</span>'
        f'<div style="display:flex;align-items:center;gap:0.5rem;margin-top:6px;">'
        f'<span class="med" style="color:{budget_color};">${remaining_budget:,.0f}</span>'
        f'<span class="dim">/ ${daily_loss_limit:,.0f}</span>'
        f'</div>'
        f'<div style="background:#1a1a35;border-radius:4px;height:8px;margin-top:6px;width:100%;">'
        f'<div style="background:{budget_color};width:{budget_pct:.0f}%;height:100%;border-radius:4px;'
        f'transition:width 0.5s ease;box-shadow:0 0 6px {budget_color};"></div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_nearest_levels(lines: list, es_price: float):
    """Show nearest line above and below current price with distance in points."""
    if not lines:
        return

    LINE_SHORT = {
        "asc_ceiling": "AC", "asc_floor": "AF",
        "desc_ceiling": "DC", "desc_floor": "DF",
        "hw_ascending": "HW", "lw_descending": "LW",
    }

    above = None
    below = None
    for line in lines:
        dist = line.price - es_price
        if dist > 0:
            if above is None or dist < (above.price - es_price):
                above = line
        elif dist < 0:
            if below is None or abs(dist) < abs(below.price - es_price):
                below = line

    def _level_block(line, label_text, direction_icon):
        if line is None:
            return (
                f'<div style="flex:1;text-align:center;padding:0.8rem;'
                f'background:rgba(26,26,53,0.5);border-radius:12px;">'
                f'<span class="lbl">{label_text}</span>'
                f'<div class="dim" style="margin-top:0.4rem;">No line detected</div>'
                f'</div>'
            )
        color = LINE_COLORS.get(line.name, BLUE)
        short = LINE_SHORT.get(line.name, line.label)
        dist = abs(line.price - es_price)
        return (
            f'<div style="flex:1;text-align:center;padding:0.8rem;'
            f'background:rgba(26,26,53,0.5);border-radius:12px;'
            f'border:1px solid {color}33;">'
            f'<div style="font-size:2rem;line-height:1;">{direction_icon}</div>'
            f'<span class="lbl">{label_text}</span>'
            f'<div style="margin-top:0.3rem;">'
            f'<span class="sm" style="color:{color};font-weight:700;">{short}</span>'
            f'<span class="med" style="color:{color};margin-left:8px;">{line.price:,.2f}</span>'
            f'</div>'
            f'<div style="margin-top:0.4rem;">'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:1.1rem;font-weight:800;'
            f'color:{CYAN};">{dist:.1f} pts</span>'
            f'</div>'
            f'</div>'
        )

    html = (
        f'<div class="pc" style="border-left:4px solid {CYAN};">'
        f'<span class="lbl" style="font-size:0.7rem;">🧭 NEAREST KEY LEVELS</span>'
        f'<div style="display:flex;gap:0.5rem;margin-top:0.6rem;">'
        f'{_level_block(above, "RESISTANCE ABOVE", "⬆")}'
        f'{_level_block(below, "SUPPORT BELOW", "⬇")}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_event_countdown(events: list, ref_datetime):
    """Show countdown to next macro event today or this week."""
    import datetime as _dt

    upcoming = []
    for e in events:
        if e.time_ct is None:
            continue
        event_dt = CT.localize(_dt.datetime.combine(e.date, e.time_ct))
        if event_dt > ref_datetime:
            delta = event_dt - ref_datetime
            upcoming.append((e, event_dt, delta))

    if not upcoming:
        return

    upcoming.sort(key=lambda x: x[2])
    next_event, next_dt, delta = upcoming[0]

    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        countdown_str = f"{hours}h {minutes}m"
    else:
        countdown_str = f"{minutes}m"

    sev_color = next_event.color
    time_str = next_dt.strftime("%I:%M %p CT")

    html = (
        f'<div class="pc" style="border-left:4px solid {sev_color};text-align:center;padding:1rem;">'
        f'<div style="font-size:2rem;line-height:1;margin-bottom:4px;">⏳</div>'
        f'<span class="lbl">NEXT MACRO EVENT</span>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:1.6rem;font-weight:800;'
        f'color:{sev_color};margin:0.3rem 0;">{countdown_str}</div>'
        f'<div class="sm" style="color:{TXT};font-weight:600;">{next_event.title}</div>'
        f'<div class="dim">{time_str} · {next_event.severity.upper()}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_trade_readiness(
    vix: float, pivots_confirmed: int, session_quality_grade: str,
    daily_pnl: float, daily_loss_limit: float, macro_blackout: bool,
):
    """Compact checklist showing trade readiness conditions."""
    from signal_engine import get_vix_regime
    vix_regime, _ = get_vix_regime(vix)

    checks = []

    # VIX in range
    vix_ok = vix_regime in ("LOW VOL", "NORMAL")
    checks.append(("VIX in Range", vix_ok, f"{vix_regime} ({vix:.1f})"))

    # Pivots confirmed
    piv_ok = pivots_confirmed >= 1
    checks.append(("Pivots Confirmed", piv_ok, f"{pivots_confirmed}/2"))

    # Session quality
    grade_ok = session_quality_grade in ("A", "B")
    checks.append(("Session Quality", grade_ok, f"Grade {session_quality_grade}"))

    # Daily loss limit
    losses = abs(min(daily_pnl, 0))
    budget_ok = losses < daily_loss_limit
    remaining = max(daily_loss_limit - losses, 0)
    checks.append(("Loss Budget OK", budget_ok, f"${remaining:,.0f} left"))

    # Macro blackout
    no_blackout = not macro_blackout
    checks.append(("No Macro Blackout", no_blackout, "BLACKOUT" if macro_blackout else "Clear"))

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)

    if passed == total:
        overall_color = GREEN
        overall_label = "GO"
    elif passed >= 3:
        overall_color = GOLD
        overall_label = "CAUTION"
    else:
        overall_color = RED
        overall_label = "NO TRADE"

    rows = ""
    for label, ok, detail in checks:
        icon = "✅" if ok else "❌"
        val_color = GREEN if ok else RED
        rows += (
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:5px 0;border-bottom:1px solid #1a1a35;">'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="font-size:1.1rem;">{icon}</span>'
            f'<span style="font-family:Outfit,sans-serif;font-size:0.82rem;color:{TXT};">{label}</span>'
            f'</div>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:0.75rem;color:{val_color};">{detail}</span>'
            f'</div>'
        )

    html = (
        f'<div class="pc" style="border-left:4px solid {overall_color};">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;">'
        f'<span class="lbl" style="font-size:0.7rem;">🚦 TRADE READINESS</span>'
        f'<span style="font-family:Orbitron,sans-serif;font-size:0.8rem;font-weight:800;'
        f'color:{overall_color};background:rgba({",".join(str(int(overall_color[i:i+2], 16)) for i in (1, 3, 5))},0.15);'
        f'padding:3px 12px;border-radius:12px;">{overall_label}</span>'
        f'</div>'
        f'<div style="font-family:Outfit,sans-serif;font-size:0.72rem;color:{TXT2};margin-bottom:0.4rem;">'
        f'{passed}/{total} conditions met</div>'
        f'{rows}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ─── Phase 1 Simplified UI: Scenario · Trade · Ladder ────────────────

_LINE_SHORT_MAP = {
    "asc_ceiling": "AC", "asc_floor": "AF",
    "desc_ceiling": "DC", "desc_floor": "DF",
    "hw_ascending": "HW", "lw_descending": "LW",
}


def render_scenario_card(
    session_quality,
    latest_signal,
    vix: float,
    pivots_confirmed: int,
    macro_blackout: bool,
    today_severity: str,
):
    """Dominant single-glance card: grade + recommendation + current scenario."""
    from signal_engine import get_vix_regime
    vix_regime, vix_color = get_vix_regime(vix)

    if macro_blackout:
        scenario = "MACRO HOLD"
        scenario_color = RED
        scenario_icon = "⛔"
    elif session_quality.recommendation == "SIT OUT":
        scenario = "SIT OUT"
        scenario_color = RED
        scenario_icon = "🚫"
    elif session_quality.recommendation == "PAPER ONLY":
        scenario = "OBSERVE ONLY"
        scenario_color = GOLD
        scenario_icon = "👁"
    elif latest_signal and latest_signal.direction == "LONG":
        ls = _LINE_SHORT_MAP.get(latest_signal.entry_line, latest_signal.entry_line.upper())
        scenario = f"LONG AT {ls}"
        scenario_color = GREEN
        scenario_icon = "↑"
    elif latest_signal and latest_signal.direction == "SHORT":
        ls = _LINE_SHORT_MAP.get(latest_signal.entry_line, latest_signal.entry_line.upper())
        scenario = f"SHORT AT {ls}"
        scenario_color = RED
        scenario_icon = "↓"
    else:
        scenario = "WAIT FOR SETUP"
        scenario_color = TXT2
        scenario_icon = "⏳"

    grade_colors = {"A": GREEN, "B": BLUE, "C": GOLD, "D": RED, "F": RED}
    grade_color = grade_colors.get(session_quality.grade, TXT)

    rec_colors = {
        "FULL SIZE": GREEN, "HALF SIZE": GOLD,
        "PAPER ONLY": GOLD, "SIT OUT": RED,
    }
    rec_color = rec_colors.get(session_quality.recommendation, TXT)

    piv_ok = pivots_confirmed >= 1
    piv_icon = "✓" if piv_ok else "✗"
    piv_color = GREEN if piv_ok else RED

    html = (
        f'<div class="pc" style="border-left:4px solid {scenario_color};height:100%;">'
        f'<div style="font-size:0.6rem;font-family:Outfit,sans-serif;font-weight:600;'
        f'color:#555577;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">SCENARIO</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:1.3rem;font-weight:900;'
        f'color:{scenario_color};line-height:1.1;margin-bottom:14px;">'
        f'{scenario_icon} {scenario}</div>'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">'
        f'<div style="background:{grade_color}22;border:1px solid {grade_color}66;border-radius:8px;'
        f'padding:6px 14px;text-align:center;min-width:52px;">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:1.7rem;font-weight:900;'
        f'color:{grade_color};line-height:1;">{session_quality.grade}</div>'
        f'<div style="font-size:0.58rem;color:#555577;text-transform:uppercase;margin-top:2px;">Grade</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.85rem;font-weight:700;'
        f'color:{rec_color};">{session_quality.recommendation}</div>'
        f'<div style="font-size:0.68rem;color:#a0a0c0;margin-top:2px;">Score: {session_quality.score:.0f} / 100</div>'
        f'</div>'
        f'</div>'
        f'<div style="display:flex;flex-direction:column;gap:6px;">'
        f'<span style="font-size:0.7rem;color:{vix_color};">VIX {vix:.1f} · {vix_regime}</span>'
        f'<span style="font-size:0.7rem;color:{piv_color};">{piv_icon} Pivots {pivots_confirmed}/2</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_trade_card(signal, offset: float, label: str = "PRIMARY"):
    """Trade setup card: direction, entry, stop, target, R:R."""
    if signal is None or signal.direction == "NEUTRAL":
        html = (
            f'<div class="pc" style="opacity:0.45;height:100%;display:flex;'
            f'flex-direction:column;align-items:center;justify-content:center;text-align:center;">'
            f'<div style="font-size:0.6rem;font-family:Outfit,sans-serif;font-weight:600;'
            f'color:#555577;text-transform:uppercase;letter-spacing:2px;margin-bottom:12px;">{label} TRADE</div>'
            f'<div style="font-size:2.2rem;color:#1a1a35;margin-bottom:8px;">—</div>'
            f'<div class="dim">No setup detected</div>'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)
        return

    is_long = signal.direction == "LONG"
    dir_color = GREEN if is_long else RED
    dir_icon = "↑" if is_long else "↓"
    ls = _LINE_SHORT_MAP.get(signal.entry_line, signal.entry_line.upper() if signal.entry_line else "?")

    target_str = f"{signal.target_price:,.2f}" if signal.target_price else "—"
    stop_str = f"{signal.stop_price:,.2f}" if signal.stop_price else "—"
    reward_str = f"+{signal.reward_pts:.1f}pt" if signal.reward_pts else ""
    risk_str = f"-{signal.risk_pts:.1f}pt" if signal.risk_pts else ""

    strength_colors = {"PREMIUM": GOLD, "HIGH": BLUE, "STANDARD": TXT2}
    strength_color = strength_colors.get(signal.signal_strength, TXT2)
    confluence_html = (
        f'<span style="font-size:0.68rem;color:{GOLD};">🔥 CONFLUENCE</span>'
        if signal.confluence_boost else ""
    )

    html = (
        f'<div class="pc" style="border-left:4px solid {dir_color};height:100%;">'
        f'<div style="font-size:0.6rem;font-family:Outfit,sans-serif;font-weight:600;'
        f'color:#555577;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">{label} TRADE</div>'
        f'<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:14px;">'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:2rem;font-weight:900;'
        f'color:{dir_color};line-height:1;">{dir_icon} {signal.direction}</span>'
        f'<span style="font-size:0.72rem;color:{dir_color}99;font-weight:600;">@ {ls}</span>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">'
        # Entry
        f'<div style="background:#1a1a35;border-radius:6px;padding:8px;">'
        f'<div style="font-size:0.58rem;color:#555577;text-transform:uppercase;margin-bottom:3px;">Entry</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.95rem;font-weight:700;'
        f'color:{TXT};">{signal.entry_price:,.2f}</div>'
        f'</div>'
        # Target
        f'<div style="background:rgba(0,255,136,0.07);border-radius:6px;padding:8px;">'
        f'<div style="font-size:0.58rem;color:#555577;text-transform:uppercase;margin-bottom:3px;">'
        f'Target {reward_str}</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.95rem;font-weight:700;'
        f'color:{GREEN};">{target_str}</div>'
        f'</div>'
        # Stop
        f'<div style="background:rgba(255,0,85,0.07);border-radius:6px;padding:8px;">'
        f'<div style="font-size:0.58rem;color:#555577;text-transform:uppercase;margin-bottom:3px;">'
        f'Stop {risk_str}</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.95rem;font-weight:700;'
        f'color:{RED};">{stop_str}</div>'
        f'</div>'
        # R:R
        f'<div style="background:#1a1a35;border-radius:6px;padding:8px;">'
        f'<div style="font-size:0.58rem;color:#555577;text-transform:uppercase;margin-bottom:3px;">R : R</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.95rem;font-weight:700;'
        f'color:{GOLD};">{signal.rr_ratio:.1f}x</div>'
        f'</div>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
        f'<span style="font-size:0.68rem;color:{strength_color};font-weight:600;">◆ {signal.signal_strength}</span>'
        f'{confluence_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_ladder(lines: list, es_price: float, offset: float):
    """Price ladder: all 6 lines sorted high→low with current price marker."""
    if not lines:
        return

    sorted_lines = sorted(lines, key=lambda l: l.price, reverse=True)
    rows = ""
    price_inserted = False

    for line in sorted_lines:
        if not price_inserted and line.price < es_price:
            rows += (
                f'<tr>'
                f'<td colspan="5" style="padding:4px 12px 8px;">'
                f'<div style="border-top:2px solid {CYAN};padding-top:6px;'
                f'display:flex;align-items:center;gap:12px;">'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.95rem;'
                f'font-weight:900;color:{CYAN};">▶ {es_price:,.2f}</span>'
                f'<span style="font-size:0.6rem;color:#555577;letter-spacing:1px;'
                f'text-transform:uppercase;">Current Price</span>'
                f'</div>'
                f'</td>'
                f'</tr>'
            )
            price_inserted = True

        color = LINE_COLORS.get(line.name, BLUE)
        dist = line.price - es_price
        sign = "+" if dist >= 0 else ""
        dist_color = RED if dist < -0.5 else (GREEN if dist > 0.5 else CYAN)
        short = _LINE_SHORT_MAP.get(line.name, line.label)
        spx = line.price - offset
        dir_arrow = "↑" if line.direction == "ascending" else "↓"
        near = abs(dist) <= 5.0
        row_bg = f'background:rgba(0,212,255,0.06);' if near else ''

        rows += (
            f'<tr style="{row_bg}border-bottom:1px solid #1a1a3522;">'
            f'<td style="padding:9px 10px;width:14px;">'
            f'<div style="width:9px;height:9px;border-radius:50%;background:{color};'
            f'box-shadow:0 0 7px {color}66;"></div>'
            f'</td>'
            f'<td style="padding:9px 8px;font-family:JetBrains Mono,monospace;'
            f'font-size:0.88rem;font-weight:800;color:{color};">{short}</td>'
            f'<td style="padding:9px 8px;font-family:JetBrains Mono,monospace;'
            f'font-size:0.92rem;font-weight:{"900" if near else "600"};'
            f'color:{"#00d4ff" if near else "#e8e8f0"};">{line.price:,.2f}</td>'
            f'<td style="padding:9px 8px;font-family:Outfit,sans-serif;'
            f'font-size:0.72rem;color:#555577;">{spx:,.1f}</td>'
            f'<td style="padding:9px 12px;font-family:JetBrains Mono,monospace;'
            f'font-size:0.82rem;font-weight:700;color:{dist_color};text-align:right;">'
            f'{sign}{dist:.1f} {dir_arrow}</td>'
            f'</tr>'
        )

    if not price_inserted:
        rows += (
            f'<tr>'
            f'<td colspan="5" style="padding:8px 12px;">'
            f'<div style="border-top:2px solid {CYAN};padding-top:6px;'
            f'display:flex;align-items:center;gap:12px;">'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:0.95rem;'
            f'font-weight:900;color:{CYAN};">▶ {es_price:,.2f}</span>'
            f'<span style="font-size:0.6rem;color:#555577;text-transform:uppercase;">'
            f'Current Price</span>'
            f'</div>'
            f'</td>'
            f'</tr>'
        )

    html = (
        f'<div class="pc" style="border-left:4px solid {GOLD};padding:1rem;">'
        f'<div style="font-size:0.6rem;font-family:Outfit,sans-serif;font-weight:600;'
        f'color:#555577;text-transform:uppercase;letter-spacing:2px;margin-bottom:0.8rem;">'
        f'⚡ Price Ladder</div>'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="border-bottom:2px solid #1a1a35;">'
        f'<th></th>'
        f'<th style="padding:3px 8px;font-size:0.58rem;color:#555577;text-align:left;'
        f'text-transform:uppercase;font-family:Outfit,sans-serif;font-weight:600;">Line</th>'
        f'<th style="padding:3px 8px;font-size:0.58rem;color:#555577;text-align:left;'
        f'text-transform:uppercase;font-family:Outfit,sans-serif;font-weight:600;">ES</th>'
        f'<th style="padding:3px 8px;font-size:0.58rem;color:#555577;text-align:left;'
        f'text-transform:uppercase;font-family:Outfit,sans-serif;font-weight:600;">SPX</th>'
        f'<th style="padding:3px 12px;font-size:0.58rem;color:#555577;text-align:right;'
        f'text-transform:uppercase;font-family:Outfit,sans-serif;font-weight:600;">Dist</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
