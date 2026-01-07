"""Backwards-compatible shim that now routes to EventKit-based listing."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from . import eventkit
from .models import Event

__all__ = ["list_events"]


def list_events(
    start: _dt.datetime,
    end: _dt.datetime,
    calendars: list[str] | None = None,
    include_all_day: bool = True,
    store: Any | None = None,
) -> list[Event]:
    return eventkit.list_events(start, end, calendars, include_all_day, store=store)
