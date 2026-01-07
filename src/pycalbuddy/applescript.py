"""Backwards-compatible shim that now routes to EventKit-based operations."""

from __future__ import annotations

import datetime as _dt

from . import eventkit

__all__ = ["add_event", "update_event"]


def add_event(
    calendar: str,
    title: str,
    start: _dt.datetime,
    end: _dt.datetime,
    location: str | None = None,
    notes: str | None = None,
    url: str | None = None,
    all_day: bool = False,
    store=None,
) -> str:
    return eventkit.add_event(calendar, title, start, end, location, notes, url, all_day, store=store)


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
    store=None,
) -> None:
    eventkit.update_event(uid, calendar, title, start, end, location, notes, url, target_calendar, store=store)
