"""
SPX PROPHET — Macro Event Calendar
Tracks FOMC, CPI, NFP, PPI, PCE, OPEX, and other market-moving events.
Warns the trader when signals coincide with macro catalysts.

Data sources:
  1. Built-in known dates for 2025-2026 (FOMC, OPEX, quad witch)
  2. Web-scraped economic calendar (optional, with fallback)
  3. Manual override entries
  4. Live RSS news feeds (MarketWatch, CNBC)
"""

import datetime as dt
import logging
import re as _re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

import pytz
import requests
import streamlit as st

from config import MACRO_EVENT_TYPES, MACRO_SEVERITY_COLORS, TIMEZONE

CT = pytz.timezone(TIMEZONE)
ET = pytz.timezone("US/Eastern")


@dataclass
class MacroEvent:
    date: dt.date
    time_ct: Optional[dt.time]  # None = all-day event (like OPEX)
    event_type: str             # key into MACRO_EVENT_TYPES
    title: str
    severity: str               # "extreme", "high", "moderate", "low"
    recommendation: str
    description: str = ""
    buffer_before: int = 0      # minutes
    buffer_after: int = 0       # minutes

    @property
    def color(self) -> str:
        return MACRO_SEVERITY_COLORS.get(self.severity, "#888888")

    def is_active_at(self, check_time: dt.datetime) -> bool:
        """Check if this event's buffer window is active at a given time."""
        if self.time_ct is None:
            # All-day event — active entire trading day
            return check_time.date() == self.date

        event_dt = CT.localize(dt.datetime.combine(self.date, self.time_ct))
        window_start = event_dt - dt.timedelta(minutes=self.buffer_before)
        window_end = event_dt + dt.timedelta(minutes=self.buffer_after)

        if check_time.tzinfo is None:
            check_time = CT.localize(check_time)

        return window_start <= check_time <= window_end


# ═══════════════════════════════════════════════════════════════════════
#  KNOWN EVENT DATES — 2025-2026
#  These are fixed-schedule events from the Fed and BLS calendars.
# ═══════════════════════════════════════════════════════════════════════

def _build_known_events() -> List[MacroEvent]:
    """
    Hard-coded calendar of major macro events.
    FOMC dates from federalreserve.gov, BLS dates from bls.gov.
    OPEX = 3rd Friday of each month. Quad witch = Mar/Jun/Sep/Dec.
    """
    events = []

    def _add(date_str: str, etype: str, title: str, time_ct_str: str = None):
        info = MACRO_EVENT_TYPES.get(etype, {})
        t = None
        if time_ct_str:
            h, m = map(int, time_ct_str.split(":"))
            t = dt.time(h, m)

        events.append(MacroEvent(
            date=dt.date.fromisoformat(date_str),
            time_ct=t,
            event_type=etype,
            title=title,
            severity=info.get("severity", "moderate"),
            recommendation=info.get("recommendation", "NORMAL"),
            description=info.get("description", ""),
            buffer_before=info.get("buffer_minutes_before", 0),
            buffer_after=info.get("buffer_minutes_after", 0),
        ))

    # ── FOMC Decisions 2025 ──────────────────────────────────────────
    for d in [
        "2025-01-29", "2025-03-19", "2025-05-07",
        "2025-06-18", "2025-07-30", "2025-09-17",
        "2025-10-29", "2025-12-17",
    ]:
        _add(d, "FOMC", "FOMC Rate Decision", "13:00")

    # ── FOMC Decisions 2026 ──────────────────────────────────────────
    for d in [
        "2026-01-28", "2026-03-18", "2026-04-29",
        "2026-06-17", "2026-07-29", "2026-09-16",
        "2026-10-28", "2026-12-16",
    ]:
        _add(d, "FOMC", "FOMC Rate Decision", "13:00")

    # ── FOMC Minutes 2025 (3 weeks after decision) ───────────────────
    for d in [
        "2025-02-19", "2025-04-09", "2025-05-28",
        "2025-07-09", "2025-08-20", "2025-10-08",
        "2025-11-26",
    ]:
        _add(d, "FOMC_MINUTES", "FOMC Minutes", "13:00")

    # ── FOMC Minutes 2026 ────────────────────────────────────────────
    for d in [
        "2026-02-18", "2026-04-08", "2026-05-27",
        "2026-07-08", "2026-08-19", "2026-10-07",
        "2026-11-25",
    ]:
        _add(d, "FOMC_MINUTES", "FOMC Minutes", "13:00")

    # ── CPI 2025 (8:30 AM ET = 7:30 AM CT) ──────────────────────────
    for d in [
        "2025-01-15", "2025-02-12", "2025-03-12",
        "2025-04-10", "2025-05-13", "2025-06-11",
        "2025-07-15", "2025-08-12", "2025-09-10",
        "2025-10-14", "2025-11-12", "2025-12-10",
    ]:
        _add(d, "CPI", "CPI Report", "7:30")

    # ── CPI 2026 (verified against BLS schedule) ─────────────────────
    for d in [
        "2026-01-14", "2026-02-11", "2026-03-11",
        "2026-04-10", "2026-05-12", "2026-06-10",
        "2026-07-14", "2026-08-12", "2026-09-16",
        "2026-10-13", "2026-11-12", "2026-12-10",
    ]:
        _add(d, "CPI", "CPI Report", "7:30")

    # ── NFP 2025 (first Friday, 8:30 AM ET = 7:30 AM CT) ────────────
    for d in [
        "2025-01-10", "2025-02-07", "2025-03-07",
        "2025-04-04", "2025-05-02", "2025-06-06",
        "2025-07-03", "2025-08-01", "2025-09-05",
        "2025-10-03", "2025-11-07", "2025-12-05",
    ]:
        _add(d, "NFP", "Non-Farm Payrolls", "7:30")

    # ── NFP 2026 ────────────────────────────────────────────────────
    for d in [
        "2026-01-09", "2026-02-06", "2026-03-06",
        "2026-04-03", "2026-05-08", "2026-06-05",
        "2026-07-02", "2026-08-07", "2026-09-04",
        "2026-10-02", "2026-11-06", "2026-12-04",
    ]:
        _add(d, "NFP", "Non-Farm Payrolls", "7:30")

    # ── PPI 2025 ─────────────────────────────────────────────────────
    for d in [
        "2025-01-14", "2025-02-13", "2025-03-13",
        "2025-04-11", "2025-05-15", "2025-06-12",
        "2025-07-15", "2025-08-14", "2025-09-11",
        "2025-10-09", "2025-11-13", "2025-12-11",
    ]:
        _add(d, "PPI", "PPI Report", "7:30")

    # ── PPI 2026 (verified against BLS schedule) ─────────────────────
    for d in [
        "2026-01-15", "2026-02-12", "2026-03-12",
        "2026-04-14", "2026-05-14", "2026-06-11",
        "2026-07-16", "2026-08-13", "2026-09-15",
        "2026-10-15", "2026-11-13", "2026-12-11",
    ]:
        _add(d, "PPI", "PPI Report", "7:30")

    # ── PCE 2025 (last Friday of month, 8:30 AM ET) ──────────────────
    for d in [
        "2025-01-31", "2025-02-28", "2025-03-28",
        "2025-04-25", "2025-05-30", "2025-06-27",
        "2025-07-25", "2025-08-29", "2025-09-26",
        "2025-10-31", "2025-11-26", "2025-12-19",
    ]:
        _add(d, "PCE", "PCE Inflation", "7:30")

    # ── PCE 2026 ─────────────────────────────────────────────────────
    for d in [
        "2026-01-30", "2026-02-27", "2026-03-27",
        "2026-04-30", "2026-05-29", "2026-06-26",
        "2026-07-31", "2026-08-28", "2026-09-25",
        "2026-10-30", "2026-11-25", "2026-12-23",
    ]:
        _add(d, "PCE", "PCE Inflation", "7:30")

    # ── Monthly OPEX (3rd Friday) 2025-2026 ──────────────────────────
    for year in [2025, 2026]:
        for month in range(1, 13):
            # Find 3rd Friday
            first_day = dt.date(year, month, 1)
            # weekday(): 0=Mon, 4=Fri
            first_friday = first_day + dt.timedelta(
                days=(4 - first_day.weekday()) % 7
            )
            third_friday = first_friday + dt.timedelta(weeks=2)

            # Quad witch months
            if month in [3, 6, 9, 12]:
                _add(third_friday.isoformat(), "QUAD_WITCH",
                     "Quad Witching OPEX", None)
            else:
                _add(third_friday.isoformat(), "OPEX",
                     "Monthly OPEX", None)

    return events


# Cache the known events
_KNOWN_EVENTS = _build_known_events()


# ═══════════════════════════════════════════════════════════════════════
#  LIVE MARKET NEWS (RSS)
# ═══════════════════════════════════════════════════════════════════════

_RSS_FEEDS = {
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "CNBC": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "Reuters": "https://feeds.reuters.com/reuters/businessNews",
    "AP Business": "https://rsshub.app/apnews/topics/business",
}

# ── SPX-relevant keyword filter ─────────────────────────────────────
_MARKET_KEYWORDS = [
    # Market / index terms
    r"stock", r"market", r"s&p", r"spx", r"dow", r"nasdaq", r"futures",
    r"index", r"rally", r"selloff", r"sell-off", r"correction", r"crash",
    r"bear", r"bull", r"wall\s*street", r"trading",
    # Fed / policy
    r"fed\b", r"fomc", r"\brate\b", r"interest\s*rate", r"powell",
    r"inflation", r"\bcpi\b", r"\bppi\b", r"\bgdp\b", r"jobs",
    r"employment", r"payroll", r"\bnfp\b", r"unemployment", r"recession",
    r"monetary",
    # Geopolitical
    r"tariff", r"trade\s*war", r"sanction", r"\bwar\b", r"conflict",
    r"china", r"russia", r"iran", r"\boil\b", r"crude", r"opec",
    r"geopolitical", r"missile", r"cease-?fire",
    # Trump / political
    r"trump", r"white\s*house", r"executive\s*order", r"treasury",
    r"yellen", r"congress", r"debt\s*ceiling", r"shutdown",
    # Macro events
    r"earnings", r"bond", r"yield", r"dollar", r"currency", r"bitcoin",
    r"crypto", r"volatility", r"\bvix\b",
]

_MARKET_PATTERN = _re.compile(
    "|".join(_MARKET_KEYWORDS), _re.IGNORECASE
)

_FALLBACK_KEYWORDS = [
    r"money", r"percent", r"billion", r"million", r"quarter",
    r"fiscal", r"economic",
]

_FALLBACK_PATTERN = _re.compile(
    "|".join(_FALLBACK_KEYWORDS), _re.IGNORECASE
)

_logger = logging.getLogger(__name__)


def _parse_rss_with_feedparser(url: str, source: str) -> List[Dict]:
    """Parse RSS feed using the feedparser library (preferred)."""
    import feedparser  # noqa: delay import

    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = dt.datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            published = dt.datetime(*entry.updated_parsed[:6], tzinfo=pytz.utc)

        items.append({
            "title": getattr(entry, "title", ""),
            "published": published,
            "source": source,
            "link": getattr(entry, "link", ""),
        })
    return items


def _parse_rss_with_requests(url: str, source: str) -> List[Dict]:
    """Fallback RSS parser using requests + xml.etree (no feedparser)."""
    resp = requests.get(url, timeout=10, headers={
        "User-Agent": "SPXProphet/1.0",
    })
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.content)

    items = []
    # RSS 2.0 items live under <channel><item>
    for item_el in root.iter("item"):
        title_el = item_el.find("title")
        link_el = item_el.find("link")
        pub_el = item_el.find("pubDate")

        published = None
        if pub_el is not None and pub_el.text:
            try:
                from email.utils import parsedate_to_datetime
                published = parsedate_to_datetime(pub_el.text)
                if published.tzinfo is None:
                    published = pytz.utc.localize(published)
            except Exception:
                pass

        items.append({
            "title": title_el.text if title_el is not None else "",
            "published": published,
            "source": source,
            "link": link_el.text if link_el is not None else "",
        })
    return items


def _parse_single_feed(url: str, source: str) -> List[Dict]:
    """Try feedparser first, fall back to requests-based parser."""
    try:
        return _parse_rss_with_feedparser(url, source)
    except ImportError:
        _logger.debug("feedparser not installed, using requests fallback")
    except Exception as exc:
        _logger.debug("feedparser failed for %s: %s", source, exc)

    return _parse_rss_with_requests(url, source)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_news(max_items: int = 15) -> List[Dict]:
    """
    Fetch recent market-moving headlines from RSS feeds.
    Results are cached for 5 minutes.

    Headlines are filtered to only include SPX/ES-relevant news
    (macro, Fed, geopolitical, earnings, etc.).  Personal-finance
    noise (FICO scores, Roth IRAs, car buying tips) is dropped.

    Returns a list of dicts with keys: title, published, source, link.
    Sorted by published date (newest first).
    """
    all_items: List[Dict] = []

    for source, url in _RSS_FEEDS.items():
        try:
            items = _parse_single_feed(url, source)
            all_items.extend(items)
        except Exception as exc:
            _logger.warning("Failed to fetch %s feed: %s", source, exc)

    # Sort newest first; items without a date go to the end
    epoch = dt.datetime(2000, 1, 1, tzinfo=pytz.utc)
    all_items.sort(
        key=lambda x: x.get("published") or epoch,
        reverse=True,
    )

    # ── Filter to SPX-relevant headlines ────────────────────────────
    filtered = [
        item for item in all_items
        if _MARKET_PATTERN.search(item.get("title", ""))
    ]

    # If too few results, relax to any broadly financial headline
    if len(filtered) < 5:
        filtered = [
            item for item in all_items
            if _MARKET_PATTERN.search(item.get("title", ""))
            or _FALLBACK_PATTERN.search(item.get("title", ""))
        ]

    return filtered[:max_items]


def time_ago(published: Optional[dt.datetime]) -> str:
    """
    Return a human-readable relative time string.

    Today:     'Xm ago' or 'Xh ago'
    Yesterday: 'Yesterday'
    Older:     'Apr 09' (short date)
    """
    if published is None:
        return ""
    now = dt.datetime.now(pytz.utc)
    delta = now - published
    total_seconds = int(delta.total_seconds())

    if total_seconds < 0:
        return "just now"
    if total_seconds < 60:
        return "just now"

    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"

    # Check calendar day boundaries (in UTC)
    today = now.date()
    pub_date = published.date()
    if pub_date == today - dt.timedelta(days=1):
        return "Yesterday"

    # Older than yesterday — show short date
    return pub_date.strftime("%b %d")


# ═══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════

def get_events_for_date(target_date: dt.date) -> List[MacroEvent]:
    """Return all macro events for a specific date."""
    return [e for e in _KNOWN_EVENTS if e.date == target_date]


def get_events_in_range(
    start_date: dt.date, end_date: dt.date
) -> List[MacroEvent]:
    """Return all macro events in a date range (inclusive)."""
    return [
        e for e in _KNOWN_EVENTS
        if start_date <= e.date <= end_date
    ]


def get_active_events_at(check_time: dt.datetime) -> List[MacroEvent]:
    """Return events whose buffer window is active right now."""
    return [e for e in _KNOWN_EVENTS if e.is_active_at(check_time)]


def get_worst_severity_today(target_date: dt.date) -> Tuple[str, str]:
    """
    Return the worst severity level for today and the recommendation.
    Used by session quality to downgrade scores on macro days.
    """
    events = get_events_for_date(target_date)
    if not events:
        return "none", "FULL SIZE"

    severity_rank = {"extreme": 4, "high": 3, "moderate": 2, "low": 1}
    worst = max(events, key=lambda e: severity_rank.get(e.severity, 0))
    return worst.severity, worst.recommendation


def is_macro_blackout(check_time: dt.datetime) -> bool:
    """
    Return True if we are inside an 'extreme' severity event's buffer.
    Trading should be halted or paper-only during these windows.
    """
    active = get_active_events_at(check_time)
    return any(e.severity == "extreme" for e in active)


def get_upcoming_events(
    from_date: dt.date, days_ahead: int = 7
) -> List[MacroEvent]:
    """Get upcoming events for the next N days."""
    end = from_date + dt.timedelta(days=days_ahead)
    return get_events_in_range(from_date, end)


def get_event_summary_for_week(ref_date: dt.date) -> dict:
    """
    Returns a dict summarizing this week's macro landscape:
    {
        "total_events": int,
        "extreme_days": [dates],
        "high_days": [dates],
        "clear_days": [dates],  # no events
        "events": [MacroEvent],
    }
    """
    # Get Monday of this week
    monday = ref_date - dt.timedelta(days=ref_date.weekday())
    friday = monday + dt.timedelta(days=4)

    events = get_events_in_range(monday, friday)

    extreme_days = list(set(e.date for e in events if e.severity == "extreme"))
    high_days = list(set(e.date for e in events if e.severity == "high"))

    all_event_days = set(e.date for e in events)
    all_weekdays = [monday + dt.timedelta(days=i) for i in range(5)]
    clear_days = [d for d in all_weekdays if d not in all_event_days]

    return {
        "total_events": len(events),
        "extreme_days": sorted(extreme_days),
        "high_days": sorted(high_days),
        "clear_days": sorted(clear_days),
        "events": events,
    }


def get_next_event_countdown(from_date: dt.date) -> Optional[Dict]:
    """
    Return the next upcoming macro event with countdown info.
    Returns dict with 'event', 'days', 'hours', 'minutes' or None.
    """
    now = dt.datetime.now(CT)
    upcoming = get_upcoming_events(from_date, days_ahead=30)
    for event in upcoming:
        if event.time_ct is not None:
            event_dt = CT.localize(dt.datetime.combine(event.date, event.time_ct))
        else:
            event_dt = CT.localize(dt.datetime.combine(event.date, dt.time(8, 30)))
        if event_dt > now:
            delta = event_dt - now
            total_seconds = int(delta.total_seconds())
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            return {
                "event": event,
                "days": days,
                "hours": hours,
                "minutes": minutes,
            }
    return None


# ── Historical average SPX moves per event type ──────────────────────
EVENT_HISTORICAL_IMPACT: Dict[str, str] = {
    "FOMC": "Avg +/-1.3% SPX move on FOMC days",
    "FOMC_MINUTES": "Avg +/-0.6% SPX move on Minutes days",
    "CPI": "Avg +/-1.2% SPX move on CPI days",
    "NFP": "Avg +/-0.9% SPX move on NFP days",
    "PPI": "Avg +/-0.7% SPX move on PPI days",
    "PCE": "Avg +/-0.8% SPX move on PCE days",
    "OPEX": "Avg +/-0.5% SPX move, high volume pin risk",
    "QUAD_WITCH": "Avg +/-1.0% SPX move, extreme volume + volatility",
}


def get_week_day_severities(ref_date: dt.date) -> List[Dict]:
    """
    Return a list of 5 dicts (Mon-Fri) with date, day name,
    worst severity, and list of events for that day.
    Used for the weekly heatmap visualization.
    """
    monday = ref_date - dt.timedelta(days=ref_date.weekday())
    result = []
    severity_rank = {"extreme": 4, "high": 3, "moderate": 2, "low": 1}
    for i in range(5):
        day = monday + dt.timedelta(days=i)
        day_events = get_events_for_date(day)
        if day_events:
            worst = max(day_events, key=lambda e: severity_rank.get(e.severity, 0))
            worst_sev = worst.severity
        else:
            worst_sev = "clear"
        result.append({
            "date": day,
            "day_name": day.strftime("%a"),
            "severity": worst_sev,
            "events": day_events,
        })
    return result
