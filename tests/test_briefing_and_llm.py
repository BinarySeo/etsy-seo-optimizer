from datetime import date

import pytest

from analysis.ai_briefing import SEASONAL_EVENTS, event_date, get_upcoming_events, nth_weekday
from analysis.ga4_analysis import parse_json_reply
from analysis.llm import LLMUnavailableError, complete, get_client, llm_available


def by_name(name):
    return next(e for e in SEASONAL_EVENTS if e["name"] == name)


@pytest.mark.parametrize("year, name, expected", [
    (2026, "Mother's Day", date(2026, 5, 10)),
    (2027, "Mother's Day", date(2027, 5, 9)),
    (2026, "Father's Day", date(2026, 6, 21)),
    (2026, "Thanksgiving", date(2026, 11, 26)),
    (2027, "Thanksgiving", date(2027, 11, 25)),
    (2026, "Christmas", date(2026, 12, 25)),
])
def test_holiday_dates_are_correct_each_year(year, name, expected):
    assert event_date(by_name(name), year) == expected


def test_nth_weekday_when_month_starts_on_that_weekday():
    # November 2029 starts on a Thursday, so the 4th Thursday is the 22nd
    assert nth_weekday(2029, 11, 4, 3) == date(2029, 11, 22)


def test_upcoming_events_wrap_into_next_year():
    events = get_upcoming_events(within_days=20, today=date(2026, 12, 20))
    assert [e["name"] for e in events] == ["Christmas", "New Year"]
    assert [e["days_away"] for e in events] == [5, 12]


def test_event_today_is_included():
    events = get_upcoming_events(within_days=0, today=date(2026, 12, 25))
    assert [e["name"] for e in events] == ["Christmas"]


def test_ai_calls_fail_clearly_without_a_key():
    get_client.cache_clear()
    assert not llm_available()
    with pytest.raises(LLMUnavailableError, match="OPENAI_API_KEY"):
        complete("hello")


@pytest.mark.parametrize("raw", ['{"a": 1}', '```json\n{"a": 1}\n```', '```\n{"a": 1}```'])
def test_parse_json_reply_handles_code_fences(raw):
    assert parse_json_reply(raw) == {"a": 1}


def test_parse_json_reply_keeps_unparseable_text():
    assert parse_json_reply("not json") == {"raw": "not json"}
