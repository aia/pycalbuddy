# icalbuddy-wrap

Small macOS-only wrapper around `icalBuddy` (read/list) and AppleScript via `osascript` (write/update) for Calendar events.

## Installation

```bash
uv sync
```

Runtime dependencies are only the macOS binaries:
- `icalBuddy` (install with Homebrew: `brew install ical-buddy`)
- `osascript` (bundled with macOS)

Grant Calendar permissions to the calling terminal/app in **System Settings → Privacy & Security → Automation/Calendars** if commands are denied.

## CLI usage

```bash
uv run icalbuddy-wrap daily --json
uv run icalbuddy-wrap weekly --start 2024-01-01 --days 10
uv run icalbuddy-wrap add --calendar Work --title "Demo" --start 2024-02-01T10:00:00 --end 2024-02-01T11:00:00
uv run icalbuddy-wrap update --uid ABC123 --title "Updated title"
```

Use `--json` on listing commands for machine-readable output. Add `--calendar NAME` multiple times to filter specific calendars. `--no-all-day` excludes all-day entries.

## Library usage

```python
import datetime as dt
from icalbuddy_wrap import list_daily_events, add_event, update_event

events = list_daily_events()

uid = add_event(
    calendar="Work",
    title="Planning",
    start=dt.datetime(2024, 2, 1, 9, 0),
    end=dt.datetime(2024, 2, 1, 10, 0),
)

update_event(uid=uid, notes="Bring slides")
```

## Testing

All external commands are mocked; no real Calendar access is needed.

```bash
uv run pytest
uv run pytest --cov=icalbuddy_wrap --cov-report=term-missing
```
