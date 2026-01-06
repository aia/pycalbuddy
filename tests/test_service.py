import datetime as dt

from pycalbuddy import service


def test_list_daily_calls_icalbuddy(monkeypatch):
    called = {}

    def fake_list(start, end, calendars, include_all_day):
        called["start"] = start
        called["end"] = end
        called["calendars"] = calendars
        called["include_all_day"] = include_all_day
        return []

    monkeypatch.setattr(service.icalbuddy, "list_events", fake_list)
    service.list_daily_events(date=dt.date(2024, 1, 1), calendars=["Work"], include_all_day=False)

    assert called["start"].date() == dt.date(2024, 1, 1)
    assert called["end"].date() == dt.date(2024, 1, 1)
    assert called["calendars"] == ["Work"]
    assert not called["include_all_day"]


def test_update_event_delegates(monkeypatch):
    called = {}

    def fake_update(uid, calendar, title, start, end, location, notes, url, target_calendar):
        called["uid"] = uid
        called["calendar"] = calendar
        called["title"] = title
        called["start"] = start
        called["end"] = end
        called["location"] = location
        called["notes"] = notes
        called["url"] = url
        called["target_calendar"] = target_calendar

    monkeypatch.setattr(service.applescript, "update_event", fake_update)
    service.update_event(
        uid="abc",
        calendar="Work",
        title="Title",
        start=dt.datetime(2024, 1, 1, 10, 0, 0),
        end=dt.datetime(2024, 1, 1, 11, 0, 0),
        location="Office",
        notes="note",
        url="https://example.com",
        target_calendar="Home",
    )

    assert called["uid"] == "abc"
    assert called["calendar"] == "Work"
    assert called["target_calendar"] == "Home"


def test_list_weekly_span(monkeypatch):
    captured = {}

    def fake_list(start, end, calendars, include_all_day):
        captured["start"] = start
        captured["end"] = end
        return []

    monkeypatch.setattr(service.icalbuddy, "list_events", fake_list)
    service.list_weekly_events(start_date=dt.date(2024, 1, 1), days=3)

    total_days = (captured["end"] - captured["start"]).total_seconds() / 86400
    assert total_days >= 2.9
    assert captured["start"].tzinfo is not None


def test_add_event_delegates(monkeypatch):
    called = {}

    def fake_add(calendar, title, start, end, location, notes, url, all_day):
        called["calendar"] = calendar
        called["all_day"] = all_day
        return "uid-123"

    monkeypatch.setattr(service.applescript, "add_event", fake_add)
    uid = service.add_event(
        calendar="Home",
        title="Title",
        start=dt.datetime(2024, 1, 1, 10, 0, 0),
        end=dt.datetime(2024, 1, 1, 11, 0, 0),
        all_day=True,
    )

    assert uid == "uid-123"
    assert called["calendar"] == "Home"
    assert called["all_day"] is True
