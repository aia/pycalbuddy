# AGENTS.md

## Rules
- Keep changes minimal and scoped to the request.
- Prefer updating tests alongside behavior changes; keep tests mocked (no real Calendar access).
- Do not run or require macOS-only binaries during CI; assume Linux runners.
- Preserve the public CLI and library API unless asked to change them.

## Workflows
- Setup: `uv sync`
- Tests: `uv run pytest` (coverage configured in `pyproject.toml`)
- Release: use GitHub Actions `publish` workflow (trusted publishing)

## Tools
- Python: 3.11+ (CI runs 3.11 and 3.12)
- Package manager: `uv`
- Test runner: `pytest`
- Runtime deps (macOS only): `icalBuddy`, `osascript`
