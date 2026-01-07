import datetime as dt

import pytest

from pycalbuddy import eventkit


class FakeCalendar:
    def __init__(self, title: str):
        self._title = title

    def title(self):
        return self._title


class FakeEvent:
    def __init__(
        self,
        uid: str,
        title: str,
        start: dt.datetime,
        end: dt.datetime,
        calendar: FakeCalendar,
        all_day: bool = False,
        location: str | None = None,
        notes: str | None = None,
        url: str | None = None,
    ):
        self._uid = uid
        self._title = title
        self._start = start
        self._end = end
        self._calendar = calendar
        self._all_day = all_day
        self._location = location
        self._notes = notes
        self._url = url

    def calendarItemExternalIdentifier(self):
        return self._uid

    def eventIdentifier(self):
        return f"event-{self._uid}"

    def calendar(self):
        return self._calendar

    def startDate(self):
        return self._start

    def endDate(self):
        return self._end

    def isAllDay(self):
        return self._all_day

    def title(self):
        return self._title

    def location(self):
        return self._location

    def notes(self):
        return self._notes

    def URL(self):
        return self._url

    # Mutators for update tests
    def setTitle_(self, value):
        self._title = value

    def setStartDate_(self, value):
        self._start = value

    def setEndDate_(self, value):
        self._end = value

    def setLocation_(self, value):
        self._location = value

    def setNotes_(self, value):
        self._notes = value

    def setURL_(self, value):
        self._url = value

    def setCalendar_(self, value):
        self._calendar = value

    def setAllDay_(self, value):
        self._all_day = bool(value)


class FakeStore:
    def __init__(self, events, calendars):
        self._events = events
        self._calendars = calendars
        self.saved = []

    def calendarsForEntityType_(self, _entity):
        return self._calendars

    def predicateForEventsWithStartDate_endDate_calendars_(self, start, end, calendars):
        self.last_predicate = (start, end, calendars)
        return self.last_predicate

    def eventsMatchingPredicate_(self, predicate):
        _, _, calendars = predicate
        events = self._events
        if calendars:
            allowed = {cal.title() for cal in calendars}
            events = [evt for evt in events if evt.calendar() and evt.calendar().title() in allowed]
        return events

    def calendarItemsWithExternalIdentifier_(self, uid):
        return [evt for evt in self._events if evt.calendarItemExternalIdentifier() == uid]

    def eventWithIdentifier_(self, uid):
        for evt in self._events:
            if evt.eventIdentifier() == uid:
                return evt
        return None

    def saveEvent_span_commit_error_(self, event, span, commit, err):
        self.saved.append((event, span, commit, err))
        return True


def test_list_events_filters_and_sorts():
    work = FakeCalendar("Work")
    home = FakeCalendar("Home")
    start = dt.datetime(2024, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    events = [
        FakeEvent("u2", "Later", start + dt.timedelta(hours=2), end, work),
        FakeEvent("u1", "All day", start, end, home, all_day=True),
    ]
    store = FakeStore(events, [work, home])

    results = eventkit.list_events(start, end, calendars=["Work"], include_all_day=False, store=store)

    assert [evt.uid for evt in results] == ["u2"]
    assert results[0].calendar == "Work"
    assert results[0].start.tzinfo is not None


class BuildableEvent:
    last_created = None

    def __init__(self):
        self.calendar = None
        self.title = None
        self.start = None
        self.end = None
        self.location = None
        self.notes = None
        self.url = None
        self.all_day = False

    @classmethod
    def eventWithEventStore_(cls, store):
        cls.last_created = cls()
        cls.last_created.store = store
        return cls.last_created

    def setCalendar_(self, value):
        self.calendar = value

    def setTitle_(self, value):
        self.title = value

    def setStartDate_(self, value):
        self.start = value

    def setEndDate_(self, value):
        self.end = value

    def setLocation_(self, value):
        self.location = value

    def setNotes_(self, value):
        self.notes = value

    def setURL_(self, value):
        self.url = value

    def setAllDay_(self, value):
        self.all_day = bool(value)

    def calendarItemExternalIdentifier(self):
        return "external-123"

    def eventIdentifier(self):
        return "event-123"


def test_add_event_populates_fields(monkeypatch):
    work = FakeCalendar("Work")
    store = FakeStore([], [work])
    monkeypatch.setattr(eventkit, "EKEvent", BuildableEvent)

    uid = eventkit.add_event(
        calendar="Work",
        title="Planning",
        start=dt.datetime(2024, 1, 1, 9, 0),
        end=dt.datetime(2024, 1, 1, 10, 0),
        location="Office",
        notes="Agenda",
        url="https://example.com",
        all_day=True,
        store=store,
    )

    evt = BuildableEvent.last_created
    assert uid == "external-123"
    assert evt.calendar == work
    assert evt.all_day is True
    assert evt.location == "Office"
    assert store.saved and store.saved[0][0] is evt


def test_update_event_sets_fields_and_moves(monkeypatch):
    work = FakeCalendar("Work")
    archive = FakeCalendar("Archive")
    target = FakeEvent(
        uid="u-1",
        title="Old",
        start=dt.datetime(2024, 1, 1, 9, 0),
        end=dt.datetime(2024, 1, 1, 10, 0),
        calendar=work,
    )
    store = FakeStore([target], [work, archive])

    eventkit.update_event(
        uid="u-1",
        title="New Title",
        start=dt.datetime(2024, 1, 1, 11, 0),
        end=dt.datetime(2024, 1, 1, 12, 0),
        target_calendar="Archive",
        url="https://example.com",
        location="Office",
        notes="Bring docs",
        store=store,
    )

    assert target.title() == "New Title"
    assert target.calendar() == archive
    assert eventkit._from_ek_date(target.startDate()).hour == 11
    assert target.location() == "Office"
    assert target.notes() == "Bring docs"
    assert "example.com" in str(target.URL())
    assert store.saved  # ensure saveEvent was called


def test_helpers_and_shims(monkeypatch):
    class TimeObj:
        def __init__(self, ts: float):
            self._ts = ts

        def timeIntervalSince1970(self):
            return self._ts

    # _from_ek_date converts timestamps and attaches tz
    converted = eventkit._from_ek_date(TimeObj(0))
    assert converted.tzinfo is not None

    # _url_to_str handles absoluteString-like objects
    class URLObj:
        def absoluteString(self):
            return "https://example.test/item"

    assert "example.test" in eventkit._url_to_str(URLObj())

    class AccessStore:
        def requestAccessToEntityType_completion_(self, entity, handler):
            handler(True, None)

    assert eventkit._request_access(AccessStore(), timeout_sec=0.01) is True

    class NoCallbackStore:
        def requestAccessToEntityType_completion_(self, entity, handler):
            return None

    assert eventkit._request_access(NoCallbackStore(), timeout_sec=0.01) is False


def test_tz_prefers_local_offset(monkeypatch):
    class FixedDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            base = dt.datetime(2024, 1, 1, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=-5)))
            if tz:
                return base.astimezone(tz)
            return base

        def astimezone(self, tz=None):
            # Keep the fixed offset regardless of host timezone to make the test deterministic.
            return self

    # Ensure _tz returns the fixed offset instead of defaulting to UTC
    monkeypatch.setattr(eventkit._dt, "datetime", FixedDatetime)
    tzinfo = eventkit._tz()
    assert tzinfo.utcoffset(dt.datetime(2024, 1, 1)) == dt.timedelta(hours=-5)

    # _store_or_given rejects non-macOS when no store provided
    monkeypatch.setattr(eventkit.sys, "platform", "linux")
    with pytest.raises(RuntimeError):
        eventkit._store_or_given(None)
    monkeypatch.setattr(eventkit.sys, "platform", "darwin")

    # _find_calendar and _find_event_by_uid helpers
    work = FakeCalendar("Work")
    store = FakeStore([], [work])
    assert eventkit._find_calendar(store, "work") is work

    fallback_event = FakeEvent(
        uid="u-2",
        title="fallback",
        start=dt.datetime(2024, 1, 1, 9, 0),
        end=dt.datetime(2024, 1, 1, 10, 0),
        calendar=work,
    )
    store._events.append(fallback_event)
    found = eventkit._find_event_by_uid(store, "event-u-2", calendar=None)
    assert found is fallback_event


def test_eventkit_error_paths(monkeypatch):
    # Fallback sort key path
    assert eventkit._event_sort_key(None) == 0.0
    assert eventkit._from_ek_date(None) is None
    assert eventkit._url_to_str("https://example.com") == "https://example.com"
    monkeypatch.setattr(eventkit, "NSDate", None)
    assert isinstance(eventkit._to_ek_date(dt.datetime(2024, 1, 1, 9, 0)), dt.datetime)
    assert eventkit._select_calendars(FakeStore([], [FakeCalendar("Work")]), None) is None

    # When EventKit store is unavailable on macOS path
    monkeypatch.setattr(eventkit.sys, "platform", "darwin")
    monkeypatch.setattr(eventkit, "EKEventStore", None)
    with pytest.raises(RuntimeError):
        eventkit._store_or_given(None)

    # Missing calendar lookup
    with pytest.raises(ValueError):
        eventkit.add_event(
            calendar="Missing",
            title="Title",
            start=dt.datetime(2024, 1, 1, 9, 0),
            end=dt.datetime(2024, 1, 1, 10, 0),
            store=FakeStore([], []),
        )

    # Event creation requires EKEvent
    monkeypatch.setattr(eventkit, "EKEvent", None)
    with pytest.raises(RuntimeError):
        eventkit.add_event(
            calendar="Work",
            title="Title",
            start=dt.datetime(2024, 1, 1, 9, 0),
            end=dt.datetime(2024, 1, 1, 10, 0),
            store=FakeStore([], [FakeCalendar("Work")]),
        )

    # add_event falls back to plain URL when NSURL is missing
    monkeypatch.setattr(eventkit, "EKEvent", BuildableEvent)
    monkeypatch.setattr(eventkit, "NSURL", None)
    store = FakeStore([], [FakeCalendar("Work")])
    uid = eventkit.add_event(
        calendar="Work",
        title="Title",
        start=dt.datetime(2024, 1, 1, 9, 0),
        end=dt.datetime(2024, 1, 1, 10, 0),
        url="https://example.com",
        store=store,
    )
    assert uid == "external-123"
    assert BuildableEvent.last_created.url == "https://example.com"

    other_cal = FakeCalendar("Other")
    filtered_store = FakeStore(
        [FakeEvent("u3", "Title", dt.datetime(2024, 1, 1), dt.datetime(2024, 1, 2), other_cal)],
        [other_cal],
    )
    assert eventkit._find_event_by_uid(filtered_store, "u3", calendar="Work") is None

    # update_event error paths
    with pytest.raises(ValueError):
        eventkit.update_event(uid="none", store=FakeStore([], [FakeCalendar("Work")]))

    with pytest.raises(ValueError):
        eventkit.update_event(
            uid="u-err",
            target_calendar="Missing",
            store=FakeStore(
                [FakeEvent("u-err", "Title", dt.datetime(2024, 1, 1), dt.datetime(2024, 1, 2), FakeCalendar("Work"))],
                [FakeCalendar("Work")],
            ),
        )
