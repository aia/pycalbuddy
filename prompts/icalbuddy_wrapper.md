You are implementing a Python module that wraps macOS Calendar access using:
- icalBuddy for *reading/listing* events
- AppleScript via `osascript` for *creating/updating* events

Toolchain requirements:
- Use `uv` for project management (pyproject.toml, lockfile)
- Use `pytest` + `pytest-cov` for tests and coverage
- Keep runtime deps minimal; standard library preferred where reasonable

Deliverables:
1) A Python package with a clean API (importable library)
2) A CLI entrypoint for humans
3) Full pytest suite with coverage config and CI-friendly mocking (no real Calendar access required)

Project layout (create this):
- pyproject.toml (uv-compatible)
- src/pycalbuddy/
    __init__.py
    models.py
    icalbuddy.py
    applescript.py
    service.py
    cli.py
- tests/
    test_icalbuddy_parsing.py
    test_icalbuddy_cmd.py
    test_applescript_cmd.py
    test_service.py
    test_cli.py
- README.md

Core features (must implement):
A) Get the daily calendar (events for a given date; default “today”)
B) Get the weekly calendar (7-day view starting a given date; default “today”)
C) Add a calendar event (calendar name, title, start/end, optional location/notes/url, all-day optional)
D) Update a given calendar event (identified by UID; update any subset of fields)

Important behavior constraints:
- Assume macOS only. If not macOS, raise a clear error.
- Detect missing binaries:
  - `icalBuddy` must be located via `shutil.which("icalBuddy")` with helpful error if missing
  - `osascript` must be located similarly
- Calendar permissions: if commands fail due to privacy permissions, surface a helpful, actionable message.
- Do NOT require real user calendars during tests. Mock subprocess calls.

Library API (design exactly these functions; type annotated):
- list_daily_events(
    date: datetime.date | None = None,
    calendars: list[str] | None = None,
    include_all_day: bool = True,
) -> list[Event]

- list_weekly_events(
    start_date: datetime.date | None = None,
    calendars: list[str] | None = None,
    include_all_day: bool = True,
    days: int = 7,
) -> list[Event]

- add_event(
    calendar: str,
    title: str,
    start: datetime.datetime,
    end: datetime.datetime,
    location: str | None = None,
    notes: str | None = None,
    url: str | None = None,
    all_day: bool = False,
) -> str
  Returns the created event UID (string).

- update_event(
    uid: str,
    calendar: str | None = None,
    title: str | None = None,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    location: str | None = None,
    notes: str | None = None,
    url: str | None = None,
) -> None

Data model:
Create `Event` as a dataclass in models.py:
- uid: str | None
- calendar: str | None
- title: str
- start: datetime.datetime | None
- end: datetime.datetime | None
- all_day: bool
- location: str | None
- notes: str | None
- url: str | None

Implementation details:

1) Reading/listing with icalBuddy (src/pycalbuddy/icalbuddy.py):
- Use `subprocess.run(..., check=True, capture_output=True, text=True)`
- Build robust command lines:
  - Daily: use `eventsFrom:START to:END` where START is date at 00:00:00 and END is date at 23:59:59 (or next day 00:00:00 depending on icalBuddy behavior) and ensure timezone is local.
  - Weekly: same but for 7-day window.
- Always request UIDs from icalBuddy output (use its UID show option).
- Force parse-friendly output:
  - Use a stable property order and custom property separators so each event becomes one machine-parseable line.
  - Prefer a delimiter unlikely to appear naturally (e.g., ASCII Unit Separator \x1F) and set separators accordingly.
  - Ensure newlines inside notes are replaced (use icalBuddy’s notes newline replacement option if available; otherwise post-process).
- Implement a parser that converts the delimited output into `Event` objects.
- Support calendar filtering using include/exclude calendars flags if available; otherwise filter in Python.

2) Writing/updating with AppleScript (src/pycalbuddy/applescript.py):
- Implement `osascript` execution helper that takes an AppleScript string and returns stdout.
- Add event AppleScript:
  - `tell application "Calendar" ... tell calendar "<name>" ... make new event ... set uidVar to uid of newEvent ... return uidVar`
- Update event AppleScript:
  - Locate event by `uid` (first event where its uid = "<uid>")
  - Update only provided fields; leave others unchanged.
  - Allow (optional) calendar change: if calendar parameter is provided, move/duplicate event into specified calendar carefully (or document limitations and keep same-calendar update only if moving is too complex).
- Be careful with quoting/escaping user strings (title/location/notes/url). Implement a safe AppleScript string escaping function.

3) Service layer (src/pycalbuddy/service.py):
- Expose the four library functions calling into icalbuddy.py and applescript.py.
- Handle timezone/local conversion using standard library `zoneinfo` and clearly document assumptions.

4) CLI (src/pycalbuddy/cli.py):
- Provide a console script `pycalbuddy` with subcommands:
  - `daily [--date YYYY-MM-DD] [--calendar NAME ...] [--no-all-day] [--json]`
  - `weekly [--start YYYY-MM-DD] [--days N] [--calendar NAME ...] [--no-all-day] [--json]`
  - `add --calendar NAME --title TITLE --start ISO --end ISO [--location ...] [--notes ...] [--url ...] [--all-day]`
  - `update --uid UID [--calendar NAME] [--title ...] [--start ISO] [--end ISO] [--location ...] [--notes ...] [--url ...]`
- Output default as nice human-readable text; `--json` prints JSON array of events (serialize dataclass).

Testing requirements (pytest):
- No real Calendar access. Mock subprocess for both icalBuddy and osascript.
- Provide fixture sample icalBuddy output (multiple events, all-day, missing location, notes with separators, etc.).
- Unit test:
  - command construction
  - parser correctness
  - applescript escaping function
  - update_event generates AppleScript that updates only the fields passed
  - CLI argument parsing + output mode (human vs json)

Coverage:
- Add pytest-cov and configure:
  - `uv run pytest --cov=pycalbuddy --cov-report=term-missing`
- Fail tests if coverage < 90% (configure via pytest.ini or pyproject).

README:
- Document:
  - Installation with uv
  - Installing icalBuddy (brew) and granting Calendar permissions
  - Example CLI usage
  - Programmatic usage examples

Acceptance checklist (you must satisfy):
- `uv run pytest` passes
- `uv run pytest --cov=pycalbuddy --cov-report=term-missing` passes with >=90%
- `uv run pycalbuddy daily --json` works (mocked in tests; real usage documented)

Start now by scaffolding the project, then implement the library, then CLI, then tests, then README.

