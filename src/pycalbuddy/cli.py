from __future__ import annotations

import argparse
import datetime as _dt
import json
from dataclasses import asdict
from typing import Any

from . import service
from .models import Event


def _parse_date(value: str) -> _dt.date:
    return _dt.date.fromisoformat(value)


def _parse_datetime(value: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(value)


def _serialize_event(event: Event) -> dict[str, Any]:
    data = asdict(event)
    if event.start:
        data["start"] = event.start.isoformat()
    if event.end:
        data["end"] = event.end.isoformat()
    return data


def _print_events(events: list[Event], json_output: bool) -> None:
    if json_output:
        print(json.dumps([_serialize_event(evt) for evt in events], indent=2))
        return
    for evt in events:
        start = evt.start.isoformat() if evt.start else "-"
        end = evt.end.isoformat() if evt.end else "-"
        all_day_flag = " [all-day]" if evt.all_day else ""
        cal = f" ({evt.calendar})" if evt.calendar else ""
        print(f"{start} -> {end} | {evt.title}{cal}{all_day_flag}")
        if evt.location:
            print(f"  location: {evt.location}")
        if evt.url:
            print(f"  url: {evt.url}")
        if evt.notes:
            print(f"  notes: {evt.notes}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pycalbuddy", description="icalBuddy wrapper for Calendar")
    sub = parser.add_subparsers(dest="command", required=True)

    daily = sub.add_parser("daily", help="List daily events")
    daily.add_argument("--date", type=_parse_date, help="Date in YYYY-MM-DD")
    daily.add_argument("--calendar", action="append", help="Calendar name (repeatable)")
    daily.add_argument("--no-all-day", action="store_true", help="Exclude all-day events")
    daily.add_argument("--json", action="store_true", help="Output JSON")

    weekly = sub.add_parser("weekly", help="List weekly events")
    weekly.add_argument("--start", type=_parse_date, help="Start date in YYYY-MM-DD")
    weekly.add_argument("--days", type=int, default=7, help="Number of days (default 7)")
    weekly.add_argument("--calendar", action="append", help="Calendar name (repeatable)")
    weekly.add_argument("--no-all-day", action="store_true", help="Exclude all-day events")
    weekly.add_argument("--json", action="store_true", help="Output JSON")

    add = sub.add_parser("add", help="Add event")
    add.add_argument("--calendar", required=True, help="Calendar name")
    add.add_argument("--title", required=True, help="Event title")
    add.add_argument("--start", required=True, type=_parse_datetime, help="Start datetime ISO")
    add.add_argument("--end", required=True, type=_parse_datetime, help="End datetime ISO")
    add.add_argument("--location", help="Location")
    add.add_argument("--notes", help="Notes")
    add.add_argument("--url", help="URL")
    add.add_argument("--all-day", action="store_true", help="Create all-day event")

    update = sub.add_parser("update", help="Update event")
    update.add_argument("--uid", required=True, help="Event UID")
    update.add_argument("--calendar", help="Calendar containing the event (speeds up search)")
    update.add_argument("--move-to", dest="move_to", help="Move event to this calendar")
    update.add_argument("--title", help="New title")
    update.add_argument("--start", type=_parse_datetime, help="New start datetime ISO")
    update.add_argument("--end", type=_parse_datetime, help="New end datetime ISO")
    update.add_argument("--location", help="New location")
    update.add_argument("--notes", help="New notes")
    update.add_argument("--url", help="New URL")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "daily":
        events = service.list_daily_events(
            date=args.date,
            calendars=args.calendar,
            include_all_day=not args.no_all_day,
        )
        _print_events(events, args.json)
        return 0

    if args.command == "weekly":
        events = service.list_weekly_events(
            start_date=args.start,
            calendars=args.calendar,
            include_all_day=not args.no_all_day,
            days=args.days,
        )
        _print_events(events, args.json)
        return 0

    if args.command == "add":
        uid = service.add_event(
            calendar=args.calendar,
            title=args.title,
            start=args.start,
            end=args.end,
            location=args.location,
            notes=args.notes,
            url=args.url,
            all_day=args.all_day,
        )
        print(uid)
        return 0

    if args.command == "update":
        service.update_event(
            uid=args.uid,
            calendar=args.calendar,
            title=args.title,
            start=args.start,
            end=args.end,
            location=args.location,
            notes=args.notes,
            url=args.url,
            target_calendar=args.move_to,
        )
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
