from __future__ import annotations

import datetime as _dt
import sys
import time
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .models import Event

try:  # pragma: no cover - exercised in real macOS environments
    from EventKit import EKEntityTypeEvent, EKEvent, EKEventStore, EKSpanFutureEvents, EKSpanThisEvent
except Exception:  # pragma: no cover - fallback for non-macOS test environments
    EKEntityTypeEvent = 0
    EKEvent = None
    EKEventStore = None
    EKSpanFutureEvents = 1
    EKSpanThisEvent = 0

try:  # pragma: no cover - exercised in real macOS environments
    from Foundation import NSDate, NSURL
except Exception:  # pragma: no cover - fallback for non-macOS test environments
    NSDate = None
    NSURL = None


def _tz() -> ZoneInfo:
    tzinfo = _dt.datetime.now().astimezone().tzinfo
    if tzinfo is not None:
        return tzinfo
    return ZoneInfo("UTC")


def _to_ek_date(value: _dt.datetime) -> Any:
    if NSDate is None:
        return value
    ts = value.timestamp()
    return NSDate.dateWithTimeIntervalSince1970_(ts)


def _from_ek_date(value: Any) -> _dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=_tz())
    if hasattr(value, "timeIntervalSince1970"):
        ts = float(value.timeIntervalSince1970())
        return _dt.datetime.fromtimestamp(ts, tz=_tz())
    return None


def _url_to_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "absoluteString"):
        try:
            return str(value.absoluteString())
        except Exception:
            pass
    return str(value)


def _store_or_given(store: Any | None) -> Any:
    if store is not None:
        return store
    if sys.platform != "darwin":
        raise RuntimeError("pycalbuddy EventKit access requires macOS.")
    if EKEventStore is None:
        raise RuntimeError("pyobjc-framework-EventKit is required on macOS.")

    ek_store = EKEventStore.alloc().init()
    if not _request_access(ek_store):
        raise RuntimeError(
            "Calendar access not granted. Enable it in System Settings → Privacy & Security → Calendars."
        )
    return ek_store


def _request_access(store: Any, timeout_sec: float = 10.0) -> bool:
    result = {"done": False, "ok": False}

    def handler(ok: Any, _err: Any) -> None:
        result["ok"] = bool(ok)
        result["done"] = True

    store.requestAccessToEntityType_completion_(EKEntityTypeEvent, handler)

    t0 = time.time()
    while not result["done"] and (time.time() - t0) < timeout_sec:
        time.sleep(0.05)
    return result["ok"]


def _select_calendars(store: Any, calendars: list[str] | None) -> Iterable[Any] | None:
    if not calendars:
        return None
    wanted = {c.lower() for c in calendars}
    selected = []
    for cal in store.calendarsForEntityType_(EKEntityTypeEvent) or []:
        title = cal.title() if callable(getattr(cal, "title", None)) else None
        if title and title.lower() in wanted:
            selected.append(cal)
    return selected


def _event_sort_key(value: Any) -> float:
    dt_value = _from_ek_date(value)
    if dt_value is None:
        return 0.0
    return dt_value.timestamp()


def _convert_event(raw: Any) -> Event:
    calendar_obj = raw.calendar() if callable(getattr(raw, "calendar", None)) else None
    calendar_title = calendar_obj.title() if calendar_obj and callable(getattr(calendar_obj, "title", None)) else None

    url_obj = raw.URL() if callable(getattr(raw, "URL", None)) else None
    location_val = raw.location() if callable(getattr(raw, "location", None)) else None
    notes_val = raw.notes() if callable(getattr(raw, "notes", None)) else None

    return Event(
        uid=(raw.calendarItemExternalIdentifier() if callable(getattr(raw, "calendarItemExternalIdentifier", None)) else None)
        or (raw.eventIdentifier() if callable(getattr(raw, "eventIdentifier", None)) else None),
        calendar=calendar_title,
        title=(raw.title() if callable(getattr(raw, "title", None)) else "") or "",
        start=_from_ek_date(raw.startDate() if callable(getattr(raw, "startDate", None)) else None),
        end=_from_ek_date(raw.endDate() if callable(getattr(raw, "endDate", None)) else None),
        all_day=bool(raw.isAllDay() if callable(getattr(raw, "isAllDay", None)) else False),
        location=location_val or None,
        notes=notes_val or None,
        url=_url_to_str(url_obj),
    )


def list_events(
    start: _dt.datetime,
    end: _dt.datetime,
    calendars: list[str] | None = None,
    include_all_day: bool = True,
    store: Any | None = None,
) -> list[Event]:
    ek_store = _store_or_given(store)
    predicate = ek_store.predicateForEventsWithStartDate_endDate_calendars_(
        _to_ek_date(start),
        _to_ek_date(end),
        _select_calendars(ek_store, calendars),
    )
    events = list(ek_store.eventsMatchingPredicate_(predicate) or [])
    events.sort(key=lambda e: _event_sort_key(e.startDate() if callable(getattr(e, "startDate", None)) else None))
    converted = [_convert_event(e) for e in events]
    if not include_all_day:
        converted = [evt for evt in converted if not evt.all_day]
    return converted


def _find_calendar(store: Any, calendar: str) -> Any | None:
    calendars = store.calendarsForEntityType_(EKEntityTypeEvent) or []
    for cal in calendars:
        title = cal.title() if callable(getattr(cal, "title", None)) else None
        if title and title.lower() == calendar.lower():
            return cal
    return None


def add_event(
    calendar: str,
    title: str,
    start: _dt.datetime,
    end: _dt.datetime,
    location: str | None = None,
    notes: str | None = None,
    url: str | None = None,
    all_day: bool = False,
    store: Any | None = None,
) -> str:
    ek_store = _store_or_given(store)
    cal_obj = _find_calendar(ek_store, calendar)
    if cal_obj is None:
        raise ValueError(f"Calendar not found: {calendar}")
    if EKEvent is None:
        raise RuntimeError("pyobjc-framework-EventKit is required to create events.")

    event = EKEvent.eventWithEventStore_(ek_store)
    event.setCalendar_(cal_obj)
    event.setTitle_(title)
    event.setStartDate_(_to_ek_date(start))
    event.setEndDate_(_to_ek_date(end))
    event.setAllDay_(bool(all_day))
    if location is not None:
        event.setLocation_(location)
    if notes is not None:
        event.setNotes_(notes)
    if url is not None:
        if NSURL is not None:
            event.setURL_(NSURL.URLWithString_(url))
        else:
            event.setURL_(url)

    ok = ek_store.saveEvent_span_commit_error_(event, EKSpanThisEvent, True, None)
    if not ok:
        raise RuntimeError("Failed to save event.")
    uid = event.calendarItemExternalIdentifier() or event.eventIdentifier()
    if not uid:
        raise RuntimeError("Event saved but no identifier returned.")
    return uid


def _find_event_by_uid(store: Any, uid: str, calendar: str | None) -> Any | None:
    candidates = store.calendarItemsWithExternalIdentifier_(uid) or []
    events = []
    for cand in candidates:
        if not callable(getattr(cand, "startDate", None)):
            continue
        cal_obj = cand.calendar() if callable(getattr(cand, "calendar", None)) else None
        if calendar and cal_obj:
            title = cal_obj.title() if callable(getattr(cal_obj, "title", None)) else None
            if not title or title.lower() != calendar.lower():
                continue
        events.append(cand)
    if not events and callable(getattr(store, "eventWithIdentifier_", None)):
        fallback = store.eventWithIdentifier_(uid)
        if fallback:
            events = [fallback]
    return events[0] if events else None


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
    store: Any | None = None,
) -> None:
    ek_store = _store_or_given(store)
    target = _find_event_by_uid(ek_store, uid, calendar)
    if target is None:
        raise ValueError(f"Event not found for UID: {uid}")

    if title is not None:
        target.setTitle_(title)
    if start is not None:
        target.setStartDate_(_to_ek_date(start))
    if end is not None:
        target.setEndDate_(_to_ek_date(end))
    if location is not None:
        target.setLocation_(location)
    if notes is not None:
        target.setNotes_(notes)
    if url is not None:
        if NSURL is not None:
            target.setURL_(NSURL.URLWithString_(url))
        else:
            target.setURL_(url)
    if target_calendar is not None:
        new_cal = _find_calendar(ek_store, target_calendar)
        if new_cal is None:
            raise ValueError(f"Calendar not found: {target_calendar}")
        target.setCalendar_(new_cal)

    ok = ek_store.saveEvent_span_commit_error_(target, EKSpanThisEvent, True, None)
    if not ok:
        raise RuntimeError("Failed to update event.")
