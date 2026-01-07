# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

pycalbuddy is a macOS-only Python library and CLI for interacting with the macOS Calendar app. It uses:
- **EventKit** via `pyobjc-framework-EventKit` for reading/listing/updating calendar events

## Rules

- Keep changes minimal and scoped to the request
- Update tests alongside behavior changes; keep tests mocked (no real Calendar access)
- Do not run or require macOS-only binaries during CI; assume Linux runners
- Preserve the public CLI and library API unless asked to change them

## Common Commands

```bash
# Install dependencies
uv sync

# Run tests (requires 90% coverage)
uv run pytest

# Run CLI
uv run python -m pycalbuddy.cli daily --json
uv run python -m pycalbuddy.cli weekly --calendar "calendar@example.com" --json

# Debug mode (shows raw icalBuddy output)
PYCALBUDDY_DEBUG=1 uv run python -m pycalbuddy.cli weekly --json
```

## Architecture

```
src/pycalbuddy/
├── models.py      # Event dataclass
├── eventkit.py    # EventKit wrapper for reading/writing/updating events
├── applescript.py # Shim delegating to EventKit
├── icalbuddy.py   # Shim delegating to EventKit
├── service.py     # High-level API
└── cli.py         # CLI interface (argparse)
```

### Key Design Decisions

1. **EventKit first**: All read/write operations go through EventKit via PyObjC.

2. **No external binaries**: Only EventKit is required at runtime on macOS.

## Tools

- Python: 3.11+ (CI runs 3.11 and 3.12)
- Package manager: `uv`
- Test runner: `pytest`
- Runtime deps (macOS only): `pyobjc-framework-EventKit`

## Testing

All tests mock EventKit access; CI runs on Linux so no macOS binaries are required.

```bash
uv run pytest                    # Run all tests
uv run pytest -v                 # Verbose
uv run pytest -k test_name       # Run specific test
```

Coverage threshold is 90% (configured in pyproject.toml).

## Release

Use GitHub Actions `publish` workflow (trusted publishing).

## Important Files

- `src/pycalbuddy/eventkit.py` - EventKit integration
- `src/pycalbuddy/service.py` - Public API for daily/weekly/add/update
- `src/pycalbuddy/cli.py` - CLI entrypoint
- `tests/test_eventkit.py` - Tests for EventKit integration and helpers

## Known Issues / Gotchas

1. **icalBuddy UID bugs**: icalBuddy sometimes returns wrong UIDs. This is why we use AppleScript for UID verification.

2. **Recurring events**: icalBuddy outputs each occurrence separately, but Calendar only has the master event. Match by title+calendar.

3. **Timezone handling**: Events use `zoneinfo.ZoneInfo`; falls back to UTC if local timezone detection fails.

4. **macOS only**: The code checks `sys.platform == "darwin"` and raises RuntimeError on other platforms.
