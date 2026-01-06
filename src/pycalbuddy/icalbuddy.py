from __future__ import annotations

import datetime as _dt
import os
import re
import shutil
import subprocess
import sys
from typing import Iterable
from zoneinfo import ZoneInfo

from .models import Event

PROPERTY_SEPARATOR = "#ICALBUDDY-PROPERTY-SEPARATOR#"
SECTION_SEPARATOR = "#ICALBUDDY-SECTION-SEPARATOR#"
NOTES_NEWLINE = "#ICALBUDDY-NEW-LINE#"
DELIMITER = PROPERTY_SEPARATOR
PROPERTIES = [
    "title",
    "datetime",
    "notes",
    "location",
    "url",
    "uid",
    "calendarName",
    "datetimeEnd",
    "allDayEvent",
]
URL_PATTERN = re.compile(r"https?://[a-zA-Z0-9~#%&_+=,.?/-]+")
DATE_LINE = re.compile(r"^\d{4}-\d{2}-\d{2}:?$")
UID_IN_TITLE = re.compile(r"[\[(]uid[:=]\s*([^\]\)]+)[\])]", re.IGNORECASE)


def _ensure_macos() -> None:
    if sys.platform != "darwin":
        raise RuntimeError("pycalbuddy only works on macOS.")


def _find_icalbuddy() -> str:
    path = shutil.which("icalBuddy")
    if not path:
        raise FileNotFoundError(
            "icalBuddy is required but not found. Install via Homebrew: brew install ical-buddy"
        )
    return path


def _local_tz() -> ZoneInfo:
    tzinfo = _dt.datetime.now().astimezone().tzinfo
    if isinstance(tzinfo, ZoneInfo):
        return tzinfo
    return ZoneInfo("UTC")


def _build_command(
    start: _dt.datetime, end: _dt.datetime, calendars: list[str] | None
) -> list[str]:
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")
    calendar_args: list[str] = []
    if calendars:
        calendar_args = ["--includeCals", ",".join(calendars)]

    return [
        _find_icalbuddy(),
        "--separateByDate",
        "--showEmptyDates",
        "--sectionSeparator",
        SECTION_SEPARATOR,
        "--uid",
        "--includeUIDs",
        "--includeEventProps",
        ",".join(PROPERTIES),
        "--propertyOrder",
        ",".join(PROPERTIES),
        "--noPropNames",
        "--propertySeparators",
        f"|{PROPERTY_SEPARATOR}|",
        "--notesNewlineReplacement",
        NOTES_NEWLINE,
        "--noRelativeDates",
        "--bullet",
        "",
        "--dateFormat",
        "%Y-%m-%d",
        "--timeFormat",
        "%H:%M",
        *calendar_args,
        f"eventsFrom:{start_str}",
        f"to:{end_str}",
    ]


def _parse_datetime(value: str) -> _dt.datetime | None:
    if not value:
        return None
    normalized = value.replace(" at ", " ")
    try:
        parsed = _dt.datetime.fromisoformat(normalized)
    except ValueError:
        try:
            date_only = _dt.date.fromisoformat(normalized)
        except ValueError:
            return None
        return _dt.datetime.combine(date_only, _dt.time.min).replace(tzinfo=_local_tz())
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=_local_tz())
    return parsed


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "yes", "1"}


def _parse_default_line(line: str, tzinfo: ZoneInfo) -> tuple[_dt.datetime | None, _dt.datetime | None, bool]:
    stripped = line.strip()
    if not stripped:
        return None, None, False
    # Pattern: YYYY-MM-DD at HH:MM:SS - HH:MM:SS
    if " at " in stripped and " - " in stripped:
        try:
            date_part, times_part = stripped.split(" at ", 1)
            start_str, end_str = times_part.split(" - ", 1)
            date = _dt.date.fromisoformat(date_part)
            start_dt = _dt.datetime.combine(date, _dt.time.fromisoformat(start_str)).replace(tzinfo=tzinfo)
            end_dt = _dt.datetime.combine(date, _dt.time.fromisoformat(end_str)).replace(tzinfo=tzinfo)
            return start_dt, end_dt, False
        except Exception:
            return None, None, False
    # Pattern: YYYY-MM-DD (all-day)
    try:
        date = _dt.date.fromisoformat(stripped)
    except ValueError:
        return None, None, False
    start_dt = _dt.datetime.combine(date, _dt.time.min).replace(tzinfo=tzinfo)
    end_dt = start_dt + _dt.timedelta(days=1) - _dt.timedelta(seconds=1)
    return start_dt, end_dt, True


def _parse_delimited_lines(lines: list[str]) -> list[Event]:
    tzinfo = _local_tz()
    events: list[Event] = []
    for raw_line in lines:
        if not raw_line.strip():
            continue
        parts = raw_line.split(DELIMITER)
        padded: Iterable[str] = list(parts) + [""] * (len(PROPERTIES) - len(parts))
        (
            title_raw,
            datetime_value,
            notes,
            location,
            url,
            uid,
            calendar_name,
            datetime_end,
            all_day_str,
        ) = list(padded)[: len(PROPERTIES)]
        title, calendar_from_title, uid_from_title = _extract_title_and_calendar(title_raw)
        calendar = calendar_name or calendar_from_title
        start, end, all_day = _parse_time_range(
            None, datetime_value, datetime_end, _parse_bool(all_day_str), tzinfo
        )
        notes_clean = _clean_notes(notes)
        url_value = url or _extract_first_url(notes_clean)
        events.append(
            Event(
                uid=(uid or uid_from_title) or None,
                calendar=calendar or None,
                title=title or "",
                start=start,
                end=end,
                all_day=all_day,
                location=location or None,
                notes=notes_clean,
                url=url_value or None,
            )
        )
    return events


def _parse_default_output(lines: list[str]) -> list[Event]:
    tzinfo = _local_tz()
    events: list[Event] = []
    current: Event | None = None
    for raw in lines:
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")):
            if not current:
                continue
            line = raw.strip()
            if line.startswith("- "):
                line = line[2:]
            start, end, all_day = _parse_default_line(line, tzinfo)
            if start and end:
                current.start = start
                current.end = end
                current.all_day = all_day
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                key_lower = key.strip().lower()
                value = value.strip()
                if key_lower in {"location"}:
                    current.location = value or None
                elif key_lower in {"notes", "note"}:
                    current.notes = value or None
                elif key_lower in {"url"}:
                    current.url = value or None
                elif key_lower in {"calendar", "calendarname"}:
                    current.calendar = value or None
                elif key_lower in {"uid"}:
                    current.uid = value or None
                elif key_lower in {"datetime", "start", "start date"}:
                    current.start = _parse_datetime(value)
                elif key_lower in {"datetimeend", "end", "end date"}:
                    current.end = _parse_datetime(value)
                elif key_lower in {"alldayevent", "all-day"}:
                    current.all_day = _parse_bool(value)
        else:
            if current:
                events.append(current)
            title, calendar_from_title, uid_from_title = _extract_title_and_calendar(raw.strip())
            current = Event(
                uid=uid_from_title,
                calendar=calendar_from_title,
                title=title,
                start=None,
                end=None,
                all_day=False,
                location=None,
                notes=None,
                url=None,
            )
    if current:
        events.append(current)
    return events


def _extract_title_and_calendar(raw_title: str) -> tuple[str, str | None, str | None]:
    cleaned = raw_title.strip()
    uid_match = UID_IN_TITLE.search(cleaned)
    uid = uid_match.group(1).strip() if uid_match else None
    if uid_match:
        start, end = uid_match.span()
        cleaned = (cleaned[:start] + cleaned[end:]).strip()

    if "(" in cleaned and cleaned.endswith(")"):
        title_part, cal_part = cleaned.rsplit("(", 1)
        return title_part.strip(), cal_part.rstrip(")").strip() or None, uid
    return cleaned, None, uid


def _clean_notes(notes: str | None) -> str | None:
    if not notes:
        return None
    cleaned = notes.replace(NOTES_NEWLINE, "\n").replace("\\n", "\n")
    return cleaned or None


def _extract_first_url(notes: str | None) -> str | None:
    if not notes:
        return None
    match = URL_PATTERN.search(notes)
    if match:
        return match.group(0)
    return None


def _combine_date_time(date_str: str, time_str: str, tzinfo: ZoneInfo) -> _dt.datetime | None:
    try:
        date = _dt.date.fromisoformat(date_str)
        time = _dt.time.fromisoformat(time_str)
    except ValueError:
        return None
    return _dt.datetime.combine(date, time).replace(tzinfo=tzinfo)


def _parse_time_range(
    current_date: str | None,
    datetime_value: str,
    datetime_end: str,
    all_day_flag: bool,
    tzinfo: ZoneInfo,
) -> tuple[_dt.datetime | None, _dt.datetime | None, bool]:
    datetime_value = datetime_value.strip() if datetime_value else ""
    datetime_end = datetime_end.strip() if datetime_end else ""
    start = _parse_datetime(datetime_value)
    end = _parse_datetime(datetime_end)
    all_day = all_day_flag

    if current_date and not start and datetime_value and " - " in datetime_value:
        start_str, end_str = datetime_value.split(" - ", 1)
        start = _combine_date_time(current_date, start_str.strip(), tzinfo)
        end = _combine_date_time(current_date, end_str.strip(), tzinfo)

    if current_date and not start and datetime_value and " - " not in datetime_value:
        start = _combine_date_time(current_date, datetime_value, tzinfo)

    if current_date and not end and datetime_end:
        end = _combine_date_time(current_date, datetime_end, tzinfo)

    if (current_date and not datetime_value and not datetime_end) or all_day:
        try:
            date = _dt.date.fromisoformat(current_date) if current_date else None
        except ValueError:
            date = None
        if date:
            start = _dt.datetime.combine(date, _dt.time.min).replace(tzinfo=tzinfo)
            end = start + _dt.timedelta(days=1) - _dt.timedelta(seconds=1)
            all_day = True

    return start, end, all_day


def _parse_grouped_output(lines: list[str]) -> list[Event]:
    tzinfo = _local_tz()
    events: list[Event] = []
    current_date: str | None = None

    for raw in lines:
        if not raw.strip():
            continue

        stripped = raw.strip()
        if stripped.endswith(SECTION_SEPARATOR):
            current_date = stripped[: -len(SECTION_SEPARATOR)].rstrip(":")
            continue

        if DATE_LINE.match(stripped):
            current_date = stripped.rstrip(":")
            continue

        if raw == "Nothing.":
            continue

        parts = raw.split(PROPERTY_SEPARATOR)
        padded: Iterable[str] = list(parts) + [""] * (len(PROPERTIES) - len(parts))
        (
            title_raw,
            datetime_value,
            notes,
            location,
            url,
            uid,
            calendar_name,
            datetime_end,
            all_day_str,
        ) = list(padded)[: len(PROPERTIES)]

        title, calendar_from_title, uid_from_title = _extract_title_and_calendar(title_raw)
        calendar = calendar_name or calendar_from_title
        notes_clean = _clean_notes(notes)
        url_value = url or _extract_first_url(notes_clean)
        start, end, all_day = _parse_time_range(
            current_date, datetime_value, datetime_end, _parse_bool(all_day_str), tzinfo
        )

        events.append(
            Event(
                uid=(uid or uid_from_title) or None,
                calendar=calendar or None,
                title=title or "",
                start=start,
                end=end,
                all_day=all_day,
                location=location or None,
                notes=notes_clean,
                url=url_value or None,
            )
        )
    return events


def parse_events_output(output: str) -> list[Event]:
    lines = [line.rstrip("\n") for line in output.splitlines()]
    if any(SECTION_SEPARATOR in line for line in lines) or any(DATE_LINE.match(line.strip()) for line in lines):
        return _parse_grouped_output(lines)
    if any(DELIMITER in line for line in lines):
        return _parse_delimited_lines(lines)
    return _parse_default_output(lines)


def _build_uid_lookup_command(
    start: _dt.datetime, end: _dt.datetime, calendars: list[str] | None
) -> list[str]:
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")
    calendar_args: list[str] = []
    if calendars:
        calendar_args = ["--includeCals", ",".join(calendars)]

    props = ["title", "uid", "calendarName", "datetime", "datetimeEnd", "allDayEvent"]
    return [
        _find_icalbuddy(),
        "--includeUIDs",
        "--includeEventProps",
        ",".join(props),
        "--propertyOrder",
        ",".join(props),
        "--noPropNames",
        "--propertySeparators",
        f"|{PROPERTY_SEPARATOR}|",
        "--noRelativeDates",
        "--bullet",
        "",
        "--dateFormat",
        "%Y-%m-%d",
        "--timeFormat",
        "%H:%M",
        *calendar_args,
        f"eventsFrom:{start_str}",
        f"to:{end_str}",
    ]


def _merge_uids(primary: list[Event], fallback: list[Event]) -> list[Event]:
    index = {}
    for evt in fallback:
        start_iso = evt.start.isoformat() if evt.start else None
        end_iso = evt.end.isoformat() if evt.end else None
        start_date = evt.start.date() if evt.start else None
        end_date = evt.end.date() if evt.end else None
        start_time = evt.start.timetz() if evt.start else None
        start_time_naive = evt.start.time() if evt.start else None

        key = (evt.title, evt.calendar, start_iso, end_iso)
        index.setdefault(key, []).append(evt)
        short_key = (evt.title, evt.calendar)
        index.setdefault(short_key, []).append(evt)
        all_day_key = (evt.title, evt.calendar, start_date)
        index.setdefault(all_day_key, []).append(evt)
        date_only_key = (evt.title, evt.calendar, start_date, end_date)
        time_key = (evt.title, evt.calendar, start_date, start_time)
        time_naive_key = (evt.title, evt.calendar, start_date, start_time_naive)
        index.setdefault(date_only_key, []).append(evt)
        index.setdefault(time_key, []).append(evt)
        index.setdefault(time_naive_key, []).append(evt)
        index.setdefault(date_only_key, []).append(evt)

    for evt in primary:
        if evt.uid:
            continue
        start_iso = evt.start.isoformat() if evt.start else None
        end_iso = evt.end.isoformat() if evt.end else None
        start_date = evt.start.date() if evt.start else None
        end_date = evt.end.date() if evt.end else None
        start_time = evt.start.timetz() if evt.start else None
        start_time_naive = evt.start.time() if evt.start else None

        key = (evt.title, evt.calendar, start_iso, end_iso)
        all_day_key = (evt.title, evt.calendar, start_date)
        date_only_key = (evt.title, evt.calendar, start_date, end_date)
        time_key = (evt.title, evt.calendar, start_date, start_time)
        time_naive_key = (evt.title, evt.calendar, start_date, start_time_naive)
        candidates = (
            index.get(key)
            or index.get((evt.title, evt.calendar))
            or index.get(all_day_key)
            or index.get(date_only_key)
            or index.get(time_key)
            or index.get(time_naive_key)
            or []
        )
        if candidates:
            evt.uid = candidates[0].uid
    if any(evt.uid is None for evt in primary) and fallback:
        # Last-resort: if only one primary event, copy the first fallback UID.
        missing = [evt for evt in primary if evt.uid is None]
        if len(primary) == 1 and missing:
            primary[0].uid = fallback[0].uid
    return primary


def _is_sc_metadata_line(line: str) -> bool:
    """Check if line is metadata (uid, date, time, property) rather than an event title."""
    lower = line.lower()
    if lower.startswith(("uid:", "location:", "notes:", "url:", "attendees:", "organizer:")):
        return True
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", line):
        return True
    if " at " in line and " - " in line:
        return True
    if " - " in line and re.match(r"\d{4}-\d{2}-\d{2}", line):
        return True
    return False


def _parse_sc_uid_output(output: str) -> list[Event]:
    events: list[Event] = []
    current_calendar: str | None = None
    current_event: Event | None = None
    tzinfo = _local_tz()

    for raw in output.splitlines():
        line = raw.strip()
        if not line or line == "------------------------":
            continue

        # Calendar header
        if line.endswith(":") and not line.startswith("•"):
            current_calendar = line.rstrip(":")
            continue

        # Event title (with or without bullet)
        if line.startswith("•") or (current_calendar and not _is_sc_metadata_line(line)):
            title = line.lstrip("•").strip()
            current_event = Event(
                uid=None, calendar=current_calendar, title=title,
                start=None, end=None, all_day=False,
                location=None, notes=None, url=None,
            )
            events.append(current_event)
            continue

        if not current_event:
            continue

        # UID
        if line.lower().startswith("uid:"):
            current_event.uid = line.split(":", 1)[1].strip()
        # Timed event: 2026-01-06 at 16:00 - 17:00
        elif " at " in line and " - " in line:
            try:
                date_part, times_part = line.split(" at ", 1)
                start_str, end_str = times_part.split(" - ", 1)
                date = _dt.date.fromisoformat(date_part)
                current_event.start = _dt.datetime.combine(date, _dt.time.fromisoformat(start_str)).replace(tzinfo=tzinfo)
                current_event.end = _dt.datetime.combine(date, _dt.time.fromisoformat(end_str)).replace(tzinfo=tzinfo)
            except Exception:
                pass
        # Multi-day: 2026-01-09 - 2026-01-11
        elif " - " in line:
            try:
                start_date = _dt.date.fromisoformat(line.split(" - ")[0])
                end_date = _dt.date.fromisoformat(line.split(" - ")[1])
                current_event.start = _dt.datetime.combine(start_date, _dt.time.min).replace(tzinfo=tzinfo)
                current_event.end = _dt.datetime.combine(end_date, _dt.time.max).replace(tzinfo=tzinfo)
                current_event.all_day = True
            except Exception:
                pass
        # Single all-day: 2026-01-05
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", line):
            try:
                date = _dt.date.fromisoformat(line)
                current_event.start = _dt.datetime.combine(date, _dt.time.min).replace(tzinfo=tzinfo)
                current_event.end = current_event.start + _dt.timedelta(days=1) - _dt.timedelta(seconds=1)
                current_event.all_day = True
            except Exception:
                pass

    return events


def _build_plain_uid_command(
    start: _dt.datetime, end: _dt.datetime, calendars: list[str] | None
) -> list[str]:
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")
    calendar_args: list[str] = []
    if calendars:
        calendar_args = ["--includeCals", ",".join(calendars)]

    return [
        _find_icalbuddy(),
        "--uid",
        "--separateByDate",
        "--noRelativeDates",
        "--bullet",
        "",
        "--dateFormat",
        "%Y-%m-%d",
        "--timeFormat",
        "%H:%M",
        *calendar_args,
        f"eventsFrom:{start_str}",
        f"to:{end_str}",
    ]


def _build_plain_text_uid_command(
    start: _dt.datetime, end: _dt.datetime, calendars: list[str] | None
) -> list[str]:
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")
    calendar_args: list[str] = []
    if calendars:
        calendar_args = ["--includeCals", ",".join(calendars)]

    return [
        _find_icalbuddy(),
        "--uid",
        "--noRelativeDates",
        "--bullet",
        "",
        "--dateFormat",
        "%Y-%m-%d",
        "--timeFormat",
        "%H:%M",
        *calendar_args,
        f"eventsFrom:{start_str}",
        f"to:{end_str}",
    ]


def _build_sc_uid_command(
    start: _dt.datetime, end: _dt.datetime, calendars: list[str] | None
) -> list[str]:
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")
    calendar_args: list[str] = []
    if calendars:
        calendar_args = ["--includeCals", ",".join(calendars)]

    return [
        _find_icalbuddy(),
        "-uid",
        "-sc",
        "--noRelativeDates",
        "--bullet",
        "",
        "--dateFormat",
        "%Y-%m-%d",
        "--timeFormat",
        "%H:%M",
        *calendar_args,
        f"eventsFrom:{start_str}",
        f"to:{end_str}",
    ]


def list_events(
    start: _dt.datetime,
    end: _dt.datetime,
    calendars: list[str] | None = None,
    include_all_day: bool = True,
) -> list[Event]:
    _ensure_macos()
    command = _build_command(start, end, calendars)
    debug = (
        os.getenv("PYCALBUDDY_DEBUG")
        or os.getenv("PYCALLBUDDY_DEBUG")
        or os.getenv("ICALBUDDY_WRAP_DEBUG")
    )
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        if "not allowed to send Apple events" in stderr.lower():
            raise RuntimeError(
                "icalBuddy could not access Calendar. Grant Calendar permissions in System Settings > Privacy."
            ) from exc
        raise RuntimeError(f"icalBuddy failed: {stderr.strip()}") from exc

    if debug:  # pragma: no cover - debug-only branch
        sys.stderr.write(f"[pycalbuddy] Command: {' '.join(command)}\n")
        sys.stderr.write(f"[pycalbuddy] STDOUT:\n{result.stdout}\n")
        if result.stderr:
            sys.stderr.write(f"[pycalbuddy] STDERR:\n{result.stderr}\n")

    events = parse_events_output(result.stdout)
    if any(evt.uid is None for evt in events):
        try:
            fallback_cmd = _build_uid_lookup_command(start, end, calendars)
            fallback_result = subprocess.run(
                fallback_cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            if debug:  # pragma: no cover - debug-only branch
                sys.stderr.write(f"[pycalbuddy] UID lookup command: {' '.join(fallback_cmd)}\n")
                sys.stderr.write(f"[pycalbuddy] UID lookup STDOUT:\n{fallback_result.stdout}\n")
            fallback_events = parse_events_output(fallback_result.stdout)
            events = _merge_uids(events, fallback_events)
            if any(evt.uid is None for evt in events):
                plain_cmd = _build_plain_uid_command(start, end, calendars)
                plain_result = subprocess.run(
                    plain_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if debug:  # pragma: no cover - debug-only branch
                    sys.stderr.write(f"[pycalbuddy] UID plain command: {' '.join(plain_cmd)}\n")
                    sys.stderr.write(f"[pycalbuddy] UID plain STDOUT:\n{plain_result.stdout}\n")
                plain_events = parse_events_output(plain_result.stdout)
                events = _merge_uids(events, plain_events)
            if any(evt.uid is None for evt in events):
                text_cmd = _build_plain_text_uid_command(start, end, calendars)
                text_result = subprocess.run(
                    text_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if debug:  # pragma: no cover - debug-only branch
                    sys.stderr.write(f"[pycalbuddy] UID text command: {' '.join(text_cmd)}\n")
                    sys.stderr.write(f"[pycalbuddy] UID text STDOUT:\n{text_result.stdout}\n")
                text_events = parse_events_output(text_result.stdout)
                events = _merge_uids(events, text_events)
            if any(evt.uid is None for evt in events):
                sc_cmd = _build_sc_uid_command(start, end, calendars)
                sc_result = subprocess.run(
                    sc_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if debug:  # pragma: no cover - debug-only branch
                    sys.stderr.write(f"[pycalbuddy] UID sc command: {' '.join(sc_cmd)}\n")
                    sys.stderr.write(f"[pycalbuddy] UID sc STDOUT:\n{sc_result.stdout}\n")
                sc_events = _parse_sc_uid_output(sc_result.stdout)
                events = _merge_uids(events, sc_events)
        except Exception:
            # Best-effort; ignore failures and return what we have.
            if debug:  # pragma: no cover - debug-only branch
                sys.stderr.write("[pycalbuddy] UID lookup failed; continuing without UIDs\n")

    if not include_all_day:
        events = [evt for evt in events if not evt.all_day]
    return events
