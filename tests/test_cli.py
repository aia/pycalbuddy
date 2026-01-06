import datetime as dt
import json

from pycalbuddy import cli
from pycalbuddy.models import Event


def test_cli_daily_json(monkeypatch, capsys):
    fake_event = Event(
        uid="uid-1",
        calendar="Work",
        title="Meeting",
        start=dt.datetime(2024, 1, 1, 10, 0, 0),
        end=dt.datetime(2024, 1, 1, 11, 0, 0),
        all_day=False,
        location=None,
        notes=None,
        url=None,
    )

    monkeypatch.setattr(cli.service, "list_daily_events", lambda **kwargs: [fake_event])
    code = cli.main(["daily", "--date", "2024-01-01", "--json"])
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert code == 0
    assert payload[0]["title"] == "Meeting"
    assert payload[0]["calendar"] == "Work"


def test_cli_weekly_no_all_day(monkeypatch):
    events_args = {}

    def fake_weekly(**kwargs):
        events_args.update(kwargs)
        return []

    monkeypatch.setattr(cli.service, "list_weekly_events", fake_weekly)
    code = cli.main(["weekly", "--start", "2024-01-01", "--days", "3", "--no-all-day"])
    assert code == 0
    assert events_args["include_all_day"] is False
    assert events_args["days"] == 3


def test_cli_add_prints_uid(monkeypatch, capsys):
    monkeypatch.setattr(cli.service, "add_event", lambda **kwargs: "new-uid")
    code = cli.main(
        [
            "add",
            "--calendar",
            "Work",
            "--title",
            "Title",
            "--start",
            "2024-01-01T10:00:00",
            "--end",
            "2024-01-01T11:00:00",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "new-uid" in out


def test_cli_update_invokes_service(monkeypatch):
    called = {}

    def fake_update(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(cli.service, "update_event", fake_update)
    code = cli.main(["update", "--uid", "abc", "--title", "New Title"])

    assert code == 0
    assert called["uid"] == "abc"
    assert called["title"] == "New Title"


def test_cli_add_all_day(monkeypatch):
    captured = {}

    def fake_add(**kwargs):
        captured.update(kwargs)
        return "uid-1"

    monkeypatch.setattr(cli.service, "add_event", fake_add)
    code = cli.main(
        [
            "add",
            "--calendar",
            "Work",
            "--title",
            "All-day",
            "--start",
            "2024-01-01T00:00:00",
            "--end",
            "2024-01-02T00:00:00",
            "--all-day",
        ]
    )

    assert code == 0
    assert captured["all_day"] is True


def test_cli_update_move_to(monkeypatch):
    captured = {}

    def fake_update(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli.service, "update_event", fake_update)
    code = cli.main(["update", "--uid", "abc", "--move-to", "Home"])

    assert code == 0
    assert captured["target_calendar"] == "Home"


def test_print_events_human_format(capsys):
    event = Event(
        uid="u1",
        calendar="Cal",
        title="Title",
        start=dt.datetime(2024, 1, 1, 9, 0, 0),
        end=dt.datetime(2024, 1, 1, 10, 0, 0),
        all_day=False,
        location="Office",
        notes="Bring slides",
        url="https://example.com",
    )

    cli._print_events([event], json_output=False)
    out = capsys.readouterr().out
    assert "Office" in out
    assert "Bring slides" in out
    assert "example.com" in out
