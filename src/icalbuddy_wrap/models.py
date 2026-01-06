from __future__ import annotations

from dataclasses import dataclass
import datetime as _dt


@dataclass
class Event:
    uid: str | None
    calendar: str | None
    title: str
    start: _dt.datetime | None
    end: _dt.datetime | None
    all_day: bool
    location: str | None
    notes: str | None
    url: str | None
