from __future__ import annotations

import datetime as _dt
from zoneinfo import ZoneInfo

from . import eventkit
from .models import Event


def _tz() -> ZoneInfo:
    tzinfo = _dt.datetime.now().astimezone().tzinfo
    if isinstance(tzinfo, ZoneInfo):
        return tzinfo
    return ZoneInfo("UTC")


def _date_range_for_day(target_date: _dt.date) -> tuple[_dt.datetime, _dt.datetime]:
    start = _dt.datetime.combine(target_date, _dt.time.min)
    end = start + _dt.timedelta(days=1)  # exclusive end
    return start, end


def _date_range_for_span(start_date: _dt.date, days: int) -> tuple[_dt.datetime, _dt.datetime]:
    start = _dt.datetime.combine(start_date, _dt.time.min)
    end = start + _dt.timedelta(days=days)
    return start, end


def list_daily_events(
    date: _dt.date | None = None,
    calendars: list[str] | None = None,
    include_all_day: bool = True,
) -> list[Event]:
    target_date = date or _dt.date.today()
    start, end = _date_range_for_day(target_date)
    return eventkit.list_events(start, end, calendars, include_all_day)


def list_weekly_events(
    start_date: _dt.date | None = None,
    calendars: list[str] | None = None,
    include_all_day: bool = True,
    days: int = 7,
) -> list[Event]:
    target_start = start_date or _dt.date.today()
    start, end = _date_range_for_span(target_start, days)
    return eventkit.list_events(start, end, calendars, include_all_day)


def add_event(
    calendar: str,
    title: str,
    start: _dt.datetime,
    end: _dt.datetime,
    location: str | None = None,
    notes: str | None = None,
    url: str | None = None,
    all_day: bool = False,
) -> str:
    return eventkit.add_event(calendar, title, start, end, location, notes, url, all_day)


def update_event(
    uid: str,
    calendar: str | None = None,
    title: str | None = None,
    start: _dt.datetime | None = None,
    end: _dt.datetime | None = None,
    location: str | None = None,
    notes: str | None = None,
    url: str | None = None,
    target_calendar: str | None = None,
) -> None:
    eventkit.update_event(uid, calendar, title, start, end, location, notes, url, target_calendar)
