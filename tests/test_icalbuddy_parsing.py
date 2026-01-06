import datetime as dt

from pycalbuddy import icalbuddy
from pycalbuddy.icalbuddy import _merge_uids, _parse_sc_uid_output


def test_parse_events_output_handles_notes_and_all_day():
    sep = icalbuddy.DELIMITER
    output = (
        f"2024-01-01{icalbuddy.SECTION_SEPARATOR}\n"
        f"Meeting (Work){sep}09:00 - 10:00{sep}Line1{icalbuddy.NOTES_NEWLINE}Line2"
        f"{sep}Office{sep}https://example.com{sep}uid-1{sep}Work{sep}{sep}false\n"
        f"2024-01-02{icalbuddy.SECTION_SEPARATOR}\n"
        f"Holiday (Home){sep}{sep}{sep}{sep}{sep}uid-2{sep}Home{sep}{sep}true\n"
    )

    events = icalbuddy.parse_events_output(output)

    assert len(events) == 2
    first = events[0]
    assert first.title == "Meeting"
    assert first.calendar == "Work"
    assert isinstance(first.start, dt.datetime)
    assert first.notes == "Line1\nLine2"
    assert first.url == "https://example.com"
    assert not first.all_day

    second = events[1]
    assert second.all_day
    assert second.location is None


def test_parse_events_handles_bad_datetime():
    sep = icalbuddy.DELIMITER
    output = (
        f"Broken{sep}not-a-date{sep}{sep}{sep}{sep}uid-x{sep}Work{sep}also-bad{sep}false\n"
    )
    events = icalbuddy.parse_events_output(output)
    assert events[0].start is None
    assert events[0].end is None


def test_grouped_output_without_section_separator_parses_dates_and_urls():
    sep = icalbuddy.DELIMITER
    output = (
        "2024-02-01\n"
        f"Morning (Cal){sep}2024-02-01 08:00{sep}note with https://example.org link"
        f"{sep}{sep}{sep}uid-9{sep}{sep}{sep}false\n"
        "2024-02-02\n"
        f"All day (Cal){sep}{sep}{sep}{sep}{sep}uid-10{sep}{sep}{sep}true\n"
    )

    events = icalbuddy.parse_events_output(output)
    assert len(events) == 2

    first, second = events
    assert first.start is not None and first.start.hour == 8
    assert first.url == "https://example.org"

    assert second.all_day
    assert second.start is not None
    assert second.end is not None


def test_grouped_output_with_colon_section_header_sets_all_day():
    sep = icalbuddy.DELIMITER
    output = (
        f"2026-01-05:{icalbuddy.SECTION_SEPARATOR}\n"
        f"USAMTS Y37: Round 3 Due (alexandra@veremey.net) [uid: abc-123]\n"
    )

    events = icalbuddy.parse_events_output(output)
    assert len(events) == 1
    evt = events[0]
    assert evt.all_day is True
    assert evt.start is not None
    assert evt.end is not None
    assert evt.calendar == "alexandra@veremey.net"
    assert evt.uid == "abc-123"


def test_merge_uids_last_resort_when_titles_differ():
    primary = [
        icalbuddy.Event(
            uid=None,
            calendar="Cal",
            title="Title A",
            start=dt.datetime(2024, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
            end=dt.datetime(2024, 1, 1, 23, 59, 59, tzinfo=dt.timezone.utc),
            all_day=True,
            location=None,
            notes=None,
            url=None,
        )
    ]
    fallback = [
        icalbuddy.Event(
            uid="uid-fb",
            calendar="Cal",
            title="Other",
            start=dt.datetime(2024, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
            end=dt.datetime(2024, 1, 1, 23, 59, 59, tzinfo=dt.timezone.utc),
            all_day=True,
            location=None,
            notes=None,
            url=None,
        )
    ]

    merged = _merge_uids(primary, fallback)
    assert merged[0].uid == "uid-fb"


def test_parse_sc_uid_output_handles_plain_title_and_date(monkeypatch):
    sc_output = (
        "alexandra@veremey.net:\n"
        "------------------------\n"
        "USAMTS Y37: Round 3 Due\n"
        "    2026-01-05\n"
        "    uid: uid-sc\n"
        "Meeting title\n"
        "    2026-01-06 at 09:00 - 10:00\n"
        "    uid: uid-time\n"
    )

    events = _parse_sc_uid_output(sc_output)
    assert len(events) == 2
    evt = events[0]
    assert evt.uid == "uid-sc"
    assert evt.calendar == "alexandra@veremey.net"
    assert evt.all_day
    assert evt.start is not None and evt.start.year == 2026
    timed = events[1]
    assert timed.uid == "uid-time"
    assert timed.start.hour == 9


def test_parse_sc_uid_output_handles_multi_day_span():
    sc_output = (
        "Work:\n"
        "------------------------\n"
        "Conference\n"
        "    2026-01-09 - 2026-01-11\n"
        "    uid: uid-span\n"
    )

    events = _parse_sc_uid_output(sc_output)
    assert len(events) == 1
    evt = events[0]
    assert evt.uid == "uid-span"
    assert evt.all_day is True
    assert evt.start is not None
    assert evt.end is not None


def test_parse_default_format_multiline():
    output = (
        "Meeting title\n"
        "\t- 2024-01-01 at 09:00:00 - 10:00:00\n"
        "\t- location: Office\n"
        "\t- uid: abc123\n"
        "\t- calendarName: Work\n"
        "Holiday\n"
        "\t- 2024-01-02\n"
    )
    events = icalbuddy.parse_events_output(output)
    assert len(events) == 2
    first, second = events
    assert first.title == "Meeting title"
    assert first.start.hour == 9
    assert first.location == "Office"
    assert first.uid == "abc123"
    assert first.calendar == "Work"
    assert second.all_day
