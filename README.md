# pycalbuddy

Small macOS-only wrapper around EventKit (via `pyobjc-framework-EventKit`) for listing and updating Calendar events without any external binaries.

## Installation

```bash
uv sync
```

Runtime dependency:
- macOS EventKit (provided by the OS, surfaced through `pyobjc-framework-EventKit`; installed automatically on macOS)

Grant Calendar permissions to the calling terminal/app in **System Settings → Privacy & Security → Automation/Calendars** if commands are denied.

## CLI usage

```bash
uv run pycalbuddy daily --json
uv run pycalbuddy weekly --start 2024-01-01 --days 10
uv run pycalbuddy add --calendar Work --title "Demo" --start 2024-02-01T10:00:00 --end 2024-02-01T11:00:00
uv run pycalbuddy add --calendar Work --title "Offsite" --start 2024-02-03T00:00:00 --end 2024-02-04T00:00:00 --all-day
uv run pycalbuddy update --uid ABC123 --title "Updated title"
uv run pycalbuddy update --uid ABC123 --move-to Archive
```

Use `--json` on listing commands for machine-readable output. Add `--calendar NAME` multiple times to filter specific calendars. `--no-all-day` excludes all-day entries.

## Library usage

```python
import datetime as dt
from pycalbuddy import list_daily_events, add_event, update_event

events = list_daily_events()

uid = add_event(
    calendar="Work",
    title="Planning",
    start=dt.datetime(2024, 2, 1, 9, 0),
    end=dt.datetime(2024, 2, 1, 10, 0),
)

update_event(uid=uid, notes="Bring slides", target_calendar="Archive")
```

## Testing

All external commands are mocked; no real Calendar access is needed.

```bash
uv run pytest
uv run pytest --cov=pycalbuddy --cov-report=term-missing
```
