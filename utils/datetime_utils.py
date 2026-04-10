# utils/datetime_utils.py
# ══════════════════════════════════════════════════════════════
#  Central Datetime Utility — ALL timezone conversions go here.
#  No other module may construct UTC datetimes independently.
#
#  Public API
#  ──────────
#  to_utc(date_val, time_str, tz_name)       → UTC datetime
#  from_utc(dt_utc, tz_name)                 → local datetime
#  normalize_datetime(date_val, dt_field)     → UTC datetime (backward-compat)
#  format_display(dt_utc, tz_name, fmt)       → str for UI
#  validate_time_str(time_str)               → bool
#  time_options(step_minutes)                → list[str]
#  TIMEZONES                                 → canonical list (single source)
# ══════════════════════════════════════════════════════════════

from __future__ import annotations

from datetime import date, datetime, timezone as _stdlib_utc
from typing import Optional

import pytz

# ── Single source of truth for timezone list ─────────────────
# Full IANA list from pytz — keeps backward-compat for any code
# that does `from utils.datetime_utils import TIMEZONES`.
TIMEZONES: list[str] = sorted(pytz.all_timezones)
COUNTRY_TZ_MAP = {
    # Core
    "india": "Asia/Kolkata",
    "england": "Europe/London",
    "australia": "Australia/Sydney",

    # Caribbean (granular)
    "barbados": "America/Barbados",
    "trinidad and tobago": "America/Port_of_Spain",
    "st lucia": "America/St_Lucia",
    "jamaica": "America/Jamaica",
    "guyana": "America/Guyana",

    # Regional fallback
    "west indies": "America/Port_of_Spain",
    "caribbean": "America/Port_of_Spain",
}

VENUE_TZ_MAP = {
    "mindoo phillip park": "America/St_Lucia",
    "daren sammy stadium": "America/St_Lucia",
    "gros islet": "America/St_Lucia",
    "queen's park oval": "America/Port_of_Spain",
    "kensington oval": "America/Barbados",
}
_UTC = pytz.UTC


def _resolve_tz(tz_name: str) -> pytz.BaseTzInfo:
    """Return a pytz timezone, falling back to UTC on any error."""
    try:
        return pytz.timezone(tz_name)
    except Exception:
        return _UTC


def _to_date(val) -> Optional[date]:
    """Coerce date / datetime / str to a plain date."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        import pandas as pd
        return pd.to_datetime(val).date()
    except Exception:
        return None


# ── Core conversion functions ─────────────────────────────────

def to_utc(date_val: date, time_str: str, tz_name: str) -> datetime:
    """
    Combine a date + "HH:MM" string + IANA tz name into a UTC-aware datetime.

    Fallback rules:
      - Invalid time_str  → 00:00
      - Invalid tz_name   → UTC
      - None / unparseable date_val → raises ValueError
    """
    d = _to_date(date_val)
    if d is None:
        raise ValueError(f"Invalid date provided: {date_val!r}")

    # Parse time
    h, m = 0, 0
    if time_str:
        try:
            parts = str(time_str).strip().split(":")
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                h, m = 0, 0
        except Exception:
            h, m = 0, 0

    tz = _resolve_tz(tz_name)
    naive_local = datetime(d.year, d.month, d.day, h, m, 0)

    # DST-safe localize: try strict first, fall back to is_dst=False
    try:
        aware_local = tz.localize(naive_local, is_dst=None)
    except pytz.exceptions.AmbiguousTimeError:
        aware_local = tz.localize(naive_local, is_dst=False)
    except pytz.exceptions.NonExistentTimeError:
        aware_local = tz.localize(naive_local, is_dst=False)

    return aware_local.astimezone(_UTC)


def from_utc(dt_utc: datetime, tz_name: str) -> datetime:
    """
    Convert a UTC datetime to the given IANA timezone.
    Naive datetimes are assumed to be UTC.
    Returns the original value unchanged if conversion fails.
    """
    if dt_utc is None:
        return dt_utc
    try:
        tz = _resolve_tz(tz_name)
        if dt_utc.tzinfo is None:
            dt_utc = _UTC.localize(dt_utc)
        return dt_utc.astimezone(tz)
    except Exception:
        return dt_utc


def normalize_datetime(
    date_val,
    dt_field: Optional[datetime],
) -> datetime:
    """
    Return a UTC-aware datetime for any entity that has both a DATE column
    and a TIMESTAMPTZ column (matches, auctions).

    Rules:
      1. dt_field set + tz-aware  → normalize to UTC
      2. dt_field set + tz-naive  → assume UTC
      3. dt_field is None/NaT     → fallback: date_val at 00:00 UTC
                                    raises ValueError if date_val is unparseable
    """
    import pandas as pd

    # Handle pandas NaT
    if dt_field is not None:
        try:
            if pd.isna(dt_field):
                dt_field = None
        except (TypeError, ValueError):
            pass

    if dt_field is not None and isinstance(dt_field, datetime):
        if dt_field.tzinfo is None:
            return _UTC.localize(dt_field)
        return dt_field.astimezone(_UTC)

    # Fallback to date at midnight UTC — fail loudly on bad input
    d = _to_date(date_val)
    if d is None:
        raise ValueError(f"Invalid date provided: {date_val!r}")
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=_stdlib_utc)


def format_display(
    dt_utc: Optional[datetime],
    tz_name: str,
    fmt: str = "%d %b %Y %H:%M",
) -> str:
    """
    Format a UTC datetime for display in the user's timezone.
    Always returns a string; returns "—" if dt_utc is None or conversion fails.
    """
    if dt_utc is None:
        return "—"
    try:
        local = from_utc(dt_utc, tz_name)
        return local.strftime(fmt)
    except Exception:
        return "—"


def validate_time_str(time_str: str) -> bool:
    """
    Return True only for a valid "HH:MM" string (00:00 – 23:59).
    Rejects partial formats, extra segments, and out-of-range values.
    """
    try:
        s = str(time_str).strip()
        parts = s.split(":")
        if len(parts) != 2:
            return False
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        return False


def time_options(step_minutes: int = 15) -> list[str]:
    """Return HH:MM strings at regular intervals for a selectbox."""
    opts = []
    for h in range(24):
        for m in range(0, 60, step_minutes):
            opts.append(f"{h:02d}:{m:02d}")
    return opts

def resolve_timezone(
    tz_name: str | None = None,
    event_tz: str | None = None,
    country: str | None = None,
    venue: str | None = None,
) -> str:
    """
    Smart timezone resolver.

    Priority:
    1. Explicit timezone (user input)
    2. Event timezone
    3. Venue-based detection
    4. Country-based detection
    5. Default UTC
    """

    # 1. Direct input
    if tz_name:
        try:
            pytz.timezone(tz_name)
            return tz_name
        except Exception:
            pass

    # 2. Event timezone
    if event_tz:
        return event_tz

    # 3. Venue detection
    if venue:
        v = venue.lower()
        for key, tz in VENUE_TZ_MAP.items():
            if key in v:
                return tz

    # 4. Country detection
    if country:
        c = country.lower()
        if c in COUNTRY_TZ_MAP:
            return COUNTRY_TZ_MAP[c]

    # 5. Fallback
    return "UTC"