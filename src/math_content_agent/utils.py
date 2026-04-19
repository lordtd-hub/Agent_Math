"""Shared utility helpers for date and time handling."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_FALLBACK_TIMEZONES = {
    "UTC": timezone.utc,
    "Asia/Bangkok": timezone(timedelta(hours=7), name="Asia/Bangkok"),
}


def get_timezone(timezone_name: str):
    """Return a timezone object with a fixed-offset fallback for common deployments."""

    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        if timezone_name in _FALLBACK_TIMEZONES:
            return _FALLBACK_TIMEZONES[timezone_name]
        raise


def normalize_now(now: datetime | None, timezone_name: str) -> datetime:
    """Return a timezone-aware current time in the requested timezone."""

    tz = get_timezone(timezone_name)
    if now is None:
        return datetime.now(tz)
    if now.tzinfo is None:
        return now.replace(tzinfo=tz)
    return now.astimezone(tz)


def is_weekday(target_date: date) -> bool:
    """Return `True` for Monday-Friday."""

    return target_date.weekday() < 5


def weekday_name(target_date: date) -> str:
    """Return the English weekday name used by the config files."""

    return target_date.strftime("%A")
