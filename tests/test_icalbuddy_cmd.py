import datetime as dt
from types import SimpleNamespace

from pycalbuddy import icalbuddy


def test_builds_expected_command(monkeypatch):
    monkeypatch.setattr(icalbuddy.sys, "platform", "darwin")
    monkeypatch.setattr(icalbuddy.shutil, "which", lambda name: "/usr/local/bin/icalBuddy")
    captured = {}

    def fake_run(cmd, check, capture_output, text):
        captured["cmd"] = cmd
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(icalbuddy.subprocess, "run", fake_run)

    start = dt.datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    icalbuddy.list_events(start, end, calendars=["Work"], include_all_day=False)

    assert captured["cmd"][0] == "/usr/local/bin/icalBuddy"
    assert "--separateByDate" in captured["cmd"]
    assert "--sectionSeparator" in captured["cmd"]
    assert "--includeUIDs" in captured["cmd"]
    assert "--uid" in captured["cmd"]
    assert "--includeEventProps" in captured["cmd"]
    assert "--propertySeparators" in captured["cmd"]
    assert any("|" in part for part in captured["cmd"] if "--propertySeparators" in captured["cmd"])
    assert "--includeCals" in captured["cmd"]
    assert any(str(start.date()) in part for part in captured["cmd"])
    assert any(str(end.date()) in part for part in captured["cmd"])


def test_filters_all_day(monkeypatch):
    monkeypatch.setattr(icalbuddy.sys, "platform", "darwin")
    monkeypatch.setattr(icalbuddy.shutil, "which", lambda name: "/usr/local/bin/icalBuddy")

    def fake_run(cmd, check, capture_output, text):
        sep = icalbuddy.DELIMITER
        output = (
            f"2024-01-01{icalbuddy.SECTION_SEPARATOR}\n"
            f"All day{sep}{sep}{sep}{sep}{sep}uid-1{sep}Work{sep}{sep}true\n"
            f"Timed{sep}09:00 - 10:00{sep}{sep}{sep}{sep}uid-2{sep}Work{sep}{sep}false\n"
        )
        return SimpleNamespace(stdout=output)

    monkeypatch.setattr(icalbuddy.subprocess, "run", fake_run)

    start = dt.datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    events = icalbuddy.list_events(start, end, include_all_day=False)

    assert len(events) == 1
    assert events[0].title == "Timed"


def test_debug_output_and_default_format(monkeypatch, capsys):
    import datetime as dt

    monkeypatch.setenv("PYCALBUDDY_DEBUG", "1")
    monkeypatch.setattr(icalbuddy.sys, "platform", "darwin")
    monkeypatch.setattr(icalbuddy.shutil, "which", lambda name: "/usr/local/bin/icalBuddy")

    def fake_run(cmd, check, capture_output, text):
        # Default (non-delimited) format with a bare date to exercise date-only parsing.
        output = "Simple Event [uid: uid-xyz]\n\t- datetime: 2024-03-01\n"
        return SimpleNamespace(stdout=output, stderr="note")

    monkeypatch.setattr(icalbuddy.subprocess, "run", fake_run)

    start = dt.datetime(2024, 3, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    events = icalbuddy.list_events(start, end)

    err = capsys.readouterr().err
    assert "[pycalbuddy] Command" in err
    assert events[0].uid == "uid-xyz"
    assert events[0].start.date() == dt.date(2024, 3, 1)


def test_fallback_uid_lookup(monkeypatch):
    import datetime as dt

    monkeypatch.setattr(icalbuddy.sys, "platform", "darwin")
    monkeypatch.setattr(icalbuddy.shutil, "which", lambda name: "/usr/local/bin/icalBuddy")
    calls = []

    def fake_run(cmd, check, capture_output, text):
        calls.append(cmd)
        if len(calls) == 1:
            # First pass: grouped output with no properties/UIDs.
            output = f"2024-01-01{icalbuddy.SECTION_SEPARATOR}\nEvent (Cal)\n"
        elif len(calls) == 2:
            sep = icalbuddy.DELIMITER
            output = (
                f"Event{sep}2024-01-01{sep}{sep}{sep}{sep}uid-123{sep}Cal{sep}{sep}true\n"
            )
        else:
            output = "Event (Cal)\n\t- uid: uid-123\n"
        return SimpleNamespace(stdout=output, stderr="")

    monkeypatch.setattr(icalbuddy.subprocess, "run", fake_run)

    start = dt.datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    events = icalbuddy.list_events(start, end, calendars=["Cal"])

    assert len(calls) == 2  # fallback triggered
    assert events[0].uid == "uid-123"
    assert calls[1][0].endswith("icalBuddy")
    assert "--propertySeparators" in calls[1]


def test_plain_uid_lookup_when_property_lookup_missing(monkeypatch):
    import datetime as dt

    monkeypatch.setattr(icalbuddy.sys, "platform", "darwin")
    monkeypatch.setattr(icalbuddy.shutil, "which", lambda name: "/usr/local/bin/icalBuddy")
    calls = []

    def fake_run(cmd, check, capture_output, text):
        calls.append(cmd)
        if len(calls) == 1:
            output = f"2024-01-01{icalbuddy.SECTION_SEPARATOR}\nEvent (Cal)\n"
        elif len(calls) == 2:
            sep = icalbuddy.DELIMITER
            output = f"Event{sep}2024-01-01{sep}{sep}{sep}{sep}{sep}Cal{sep}{sep}true\n"
        elif len(calls) == 3:
            output = "Event (Cal)\n\t- uid: uid-999\n"
        else:
            output = ""
        return SimpleNamespace(stdout=output, stderr="")

    monkeypatch.setattr(icalbuddy.subprocess, "run", fake_run)

    start = dt.datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    events = icalbuddy.list_events(start, end, calendars=["Cal"])

    assert len(calls) == 3  # plain fallback used
    assert events[0].uid == "uid-999"


def test_text_uid_lookup_as_last_resort(monkeypatch):
    import datetime as dt

    monkeypatch.setattr(icalbuddy.sys, "platform", "darwin")
    monkeypatch.setattr(icalbuddy.shutil, "which", lambda name: "/usr/local/bin/icalBuddy")
    calls = []

    def fake_run(cmd, check, capture_output, text):
        calls.append(cmd)
        if len(calls) == 1:
            output = f"2024-01-01{icalbuddy.SECTION_SEPARATOR}\nEvent (Cal)\n"
        elif len(calls) == 2:
            sep = icalbuddy.DELIMITER
            output = f"Event{sep}2024-01-01{sep}{sep}{sep}{sep}{sep}Cal{sep}{sep}true\n"
        elif len(calls) == 3:
            # Plain separator run still missing UID.
            output = "Event (Cal)\n"
        else:
            output = "Event (Cal)\n\t- uid: uid-text\n"
        return SimpleNamespace(stdout=output, stderr="")

    monkeypatch.setattr(icalbuddy.subprocess, "run", fake_run)

    start = dt.datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    events = icalbuddy.list_events(start, end, calendars=["Cal"])

    assert len(calls) == 4  # text fallback used
    assert events[0].uid == "uid-text"


def test_sc_uid_lookup(monkeypatch):
    import datetime as dt

    monkeypatch.setattr(icalbuddy.sys, "platform", "darwin")
    monkeypatch.setattr(icalbuddy.shutil, "which", lambda name: "/usr/local/bin/icalBuddy")
    calls = []

    def fake_run(cmd, check, capture_output, text):
        calls.append(cmd)
        if len(calls) == 1:
            output = f"2024-01-01{icalbuddy.SECTION_SEPARATOR}\nEvent (Cal)\n"
        elif len(calls) == 2:
            sep = icalbuddy.DELIMITER
            output = f"Event{sep}2024-01-01{sep}{sep}{sep}{sep}{sep}Cal{sep}{sep}true\n"
        elif len(calls) == 3:
            output = "Event (Cal)\n"
        else:
            output = (
                "Cal:\n"
                "------------------------\n"
                "USAMTS Y37: Round 3 Due\n"
                "    2024-01-01\n"
                "    uid: uid-sc\n"
            )
        return SimpleNamespace(stdout=output, stderr="")

    monkeypatch.setattr(icalbuddy.subprocess, "run", fake_run)

    start = dt.datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    events = icalbuddy.list_events(start, end, calendars=["Cal"])

    # First run + property lookup + plain + text + sc
    assert len(calls) == 5  # sc fallback used
    assert events[0].uid == "uid-sc"


def test_non_macos_rejected(monkeypatch):
    import pytest

    monkeypatch.setattr(icalbuddy.sys, "platform", "linux")
    start = dt.datetime(2024, 1, 1, 0, 0, 0)
    end = start + dt.timedelta(days=1)
    with pytest.raises(RuntimeError):
        icalbuddy.list_events(start, end)


def test_missing_icalbuddy(monkeypatch):
    import pytest

    monkeypatch.setattr(icalbuddy.sys, "platform", "darwin")
    monkeypatch.setattr(icalbuddy.shutil, "which", lambda name: None)
    start = dt.datetime(2024, 1, 1, 0, 0, 0)
    end = start + dt.timedelta(days=1)
    with pytest.raises(FileNotFoundError):
        icalbuddy.list_events(start, end)


def test_icalbuddy_permission_error(monkeypatch):
    import subprocess
    import pytest

    monkeypatch.setattr(icalbuddy.sys, "platform", "darwin")
    monkeypatch.setattr(icalbuddy.shutil, "which", lambda name: "/usr/local/bin/icalBuddy")

    def fake_run(cmd, check, capture_output, text):
        raise subprocess.CalledProcessError(1, cmd, stderr="not allowed to send Apple events")

    monkeypatch.setattr(icalbuddy.subprocess, "run", fake_run)

    start = dt.datetime(2024, 1, 1, 0, 0, 0)
    end = start + dt.timedelta(days=1)
    with pytest.raises(RuntimeError):
        icalbuddy.list_events(start, end)
