import datetime as dt
from types import SimpleNamespace

from pycalbuddy import applescript


def test_escape_applescript_string():
    text = 'He said "Hello"\nbackslash: \\'
    escaped = applescript.escape_applescript_string(text)
    assert '\\"' in escaped
    assert "\\n" in escaped
    assert "\\\\" in escaped


def test_update_script_contains_only_set_fields():
    script = applescript.build_update_script(uid="abc123", title="New Title", url=None, notes=None)
    assert 'summary of targetEvent' in script
    assert 'url of targetEvent' not in script
    assert 'description of targetEvent' not in script


def test_add_event_calls_osascript(monkeypatch):
    monkeypatch.setattr(applescript.sys, "platform", "darwin")
    monkeypatch.setattr(applescript.shutil, "which", lambda name: "/usr/bin/osascript")
    captured = {}

    def fake_run(cmd, check, capture_output, text):
        captured["cmd"] = cmd
        return SimpleNamespace(stdout="uid-123")

    monkeypatch.setattr(applescript.subprocess, "run", fake_run)

    uid = applescript.add_event(
        calendar="Work",
        title="Title",
        start=dt.datetime(2024, 1, 1, 10, 0, 0),
        end=dt.datetime(2024, 1, 1, 11, 0, 0),
        location="Office",
        all_day=False,
    )

    assert uid == "uid-123"
    assert captured["cmd"][0] == "/usr/bin/osascript"
    script = captured["cmd"][2]
    assert "make new event" in script
    assert "Work" in script


def test_update_event_permission_error(monkeypatch):
    import subprocess
    import pytest

    monkeypatch.setattr(applescript.sys, "platform", "darwin")
    monkeypatch.setattr(applescript.shutil, "which", lambda name: "/usr/bin/osascript")

    def fake_run(cmd, check, capture_output, text):
        raise subprocess.CalledProcessError(1, cmd, stderr="Not authorised to send Apple events")

    monkeypatch.setattr(applescript.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError):
        applescript.update_event(uid="abc123")


def test_missing_osascript_binary(monkeypatch):
    import pytest

    monkeypatch.setattr(applescript.sys, "platform", "darwin")
    monkeypatch.setattr(applescript.shutil, "which", lambda name: None)

    with pytest.raises(FileNotFoundError):
        applescript.add_event(
            calendar="Work",
            title="Title",
            start=dt.datetime(2024, 1, 1, 10, 0, 0),
            end=dt.datetime(2024, 1, 1, 11, 0, 0),
        )


def test_build_add_script_includes_optional_fields():
    script = applescript.build_add_script(
        calendar="Cal",
        title="Title",
        start=dt.datetime(2024, 1, 1, 10, 0, 0),
        end=dt.datetime(2024, 1, 1, 11, 0, 0),
        location="Office",
        notes="note",
        url="https://example.com",
        all_day=True,
    )
    assert "location" in script
    assert "description" in script
    assert "url" in script
    assert "allday event:true" in script


def test_build_update_script_move_to():
    script = applescript.build_update_script(
        uid="abc123",
        target_calendar="Archive",
    )
    assert 'move targetEvent to calendar "Archive"' in script
