import datetime as dt

from pycalbuddy import applescript, icalbuddy


def test_shims_delegate(monkeypatch):
    calls = {}

    monkeypatch.setattr(applescript.eventkit, "add_event", lambda *args, **kwargs: "shim-uid")
    monkeypatch.setattr(applescript.eventkit, "update_event", lambda *args, **kwargs: calls.update({"uid": args[0]}) or None)
    monkeypatch.setattr(icalbuddy.eventkit, "list_events", lambda *args, **kwargs: ["ok"])

    assert applescript.add_event("Cal", "Title", dt.datetime(2024, 1, 1), dt.datetime(2024, 1, 1)) == "shim-uid"
    applescript.update_event("uid-1")
    assert calls["uid"] == "uid-1"

    events = icalbuddy.list_events(dt.datetime(2024, 1, 1), dt.datetime(2024, 1, 2))
    assert events == ["ok"]
