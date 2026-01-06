from __future__ import annotations

import datetime as _dt
import shutil
import subprocess
import sys

from .icalbuddy import _ensure_macos


def _find_osascript() -> str:
    path = shutil.which("osascript")
    if not path:
        raise FileNotFoundError(
            "osascript is required but missing. It should be available on macOS."
        )
    return path


def escape_applescript_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return escaped


def _run_osascript(script: str) -> str:
    _ensure_macos()
    command = [_find_osascript(), "-e", script]
    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
    except FileNotFoundError:
        raise
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        if "not authorised" in stderr.lower() or "not authorized" in stderr.lower():
            raise RuntimeError(
                "Calendar access denied. Allow Terminal (or calling app) to control Calendar in System Settings > Privacy."
            ) from exc
        raise RuntimeError(f"osascript failed: {stderr.strip()}") from exc
    return (result.stdout or "").strip()


def _format_datetime(value: _dt.datetime) -> str:
    # AppleScript requires US locale format: "January 11, 2026 3:45:00 PM"
    return value.strftime("%B %d, %Y %I:%M:%S %p")


def build_add_script(
    calendar: str,
    title: str,
    start: _dt.datetime,
    end: _dt.datetime,
    location: str | None = None,
    notes: str | None = None,
    url: str | None = None,
    all_day: bool = False,
) -> str:
    start_str = _format_datetime(start)
    end_str = _format_datetime(end)
    props = [
        f'summary:"{escape_applescript_string(title)}"',
        f"start date:date \"{start_str}\"",
        f"end date:date \"{end_str}\"",
    ]
    if location:
        props.append(f'location:"{escape_applescript_string(location)}"')
    if notes:
        props.append(f'description:"{escape_applescript_string(notes)}"')
    if url:
        props.append(f'url:"{escape_applescript_string(url)}"')
    if all_day:
        props.append("allday event:true")

    return f'''
set startDate to date "{start_str}"
set endDate to date "{end_str}"
tell application "Calendar"
  tell calendar "{escape_applescript_string(calendar)}"
    set newEvent to make new event with properties {{{", ".join(props)}}}
    set uidValue to uid of newEvent
    return uidValue
  end tell
end tell
'''.strip()


def build_update_script(
    uid: str,
    calendar: str | None = None,
    target_calendar: str | None = None,
    title: str | None = None,
    start: _dt.datetime | None = None,
    end: _dt.datetime | None = None,
    location: str | None = None,
    notes: str | None = None,
    url: str | None = None,
) -> str:
    updates: list[str] = []
    if title is not None:
        updates.append(f'set summary of targetEvent to "{escape_applescript_string(title)}"')
    if start is not None:
        start_str = _format_datetime(start)
        updates.append(f'set start date of targetEvent to date "{start_str}"')
    if end is not None:
        end_str = _format_datetime(end)
        updates.append(f'set end date of targetEvent to date "{end_str}"')
    if location is not None:
        updates.append(
            f'set location of targetEvent to "{escape_applescript_string(location)}"'
        )
    if notes is not None:
        updates.append(
            f'set description of targetEvent to "{escape_applescript_string(notes)}"'
        )
    if url is not None:
        updates.append(f'set url of targetEvent to "{escape_applescript_string(url)}"')
    if target_calendar is not None:
        updates.append(
            f'move targetEvent to calendar "{escape_applescript_string(target_calendar)}"'
        )

    updates_body = "\n    ".join(updates) if updates else "-- no updates requested"

    if calendar:
        # Search within specific calendar
        return f'''
tell application "Calendar"
  tell calendar "{escape_applescript_string(calendar)}"
    set targetEvent to (first event whose uid is "{escape_applescript_string(uid)}")
    {updates_body}
  end tell
end tell
'''.strip()
    else:
        # Search across all calendars
        return f'''
tell application "Calendar"
  repeat with cal in calendars
    try
      set targetEvent to (first event of cal whose uid is "{escape_applescript_string(uid)}")
      {updates_body}
      return
    end try
  end repeat
  error "Event not found with uid: {escape_applescript_string(uid)}"
end tell
'''.strip()


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
    script = build_add_script(calendar, title, start, end, location, notes, url, all_day)
    return _run_osascript(script)


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
    script = build_update_script(uid, calendar, target_calendar, title, start, end, location, notes, url)
    _run_osascript(script)
