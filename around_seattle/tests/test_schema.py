import copy
from datetime import datetime, timezone

import pytest

from around_seattle import schema
from around_seattle.models import LA, SeasonalPick, SourceResult, Window, effective_end
from around_seattle.tests.conftest import NOW, make_config, make_event

PICK = SeasonalPick(id="kubota", title="Fall color at Kubota Garden", summary="Maples turn.", place="Kubota Garden",
                    city="Seattle", region="seattle", category="outdoors", url="https://www.kubotagarden.org/",
                    start_md="09-01", end_md="11-15", free=True, source="https://www.kubotagarden.org/",
                    verified="2026-09-25")
WEATHER = {"seattle": {"periods": [{"name": "Friday", "start": "2026-09-25T06:00:00-07:00",
                                    "end": "2026-09-25T18:00:00-07:00", "isDaytime": True, "temperature": 62,
                                    "unit": "F", "shortForecast": "Rain", "condition": "rain", "precipChance": 90}]},
           "eastside": None}


def build_output():
    event = make_event(region="seattle", category="festival", score=61, url="https://example.org/e",
                       more_dates=tuple(datetime(2026, 10, day, 11, 0, tzinfo=LA) for day in range(1, 9)))
    results = [SourceResult(make_config(), "ok", (event,)),
               SourceResult(make_config(id="tm", name="Ticketmaster"), "skipped", error="no API key configured")]
    return schema.to_output(generated_at=datetime(2026, 9, 25, 13, 17, 42, 123, tzinfo=timezone.utc),
                            window=Window.starting(NOW), results=results, events=[event], weather=WEATHER,
                            sun={"2026-09-25": {"sunrise": "2026-09-25T07:02:00-07:00",
                                                "sunset": "2026-09-25T19:01:00-07:00"}},
                            seasonal=[PICK])


def test_to_output_shape():
    output = build_output()
    assert output["schemaVersion"] == 1
    assert output["generatedAt"] == "2026-09-25T13:17:42Z"
    assert output["timezone"] == "America/Los_Angeles"
    assert output["window"] == {"start": "2026-09-25", "nearEnd": "2026-10-09", "farEnd": "2026-11-24"}
    assert output["sources"][1] == {"id": "tm", "name": "Ticketmaster", "homepage": "https://example.org/",
                                    "status": "skipped", "count": 0, "error": "no API key configured"}
    event = output["events"][0]
    assert set(event) == schema.EVENT_KEYS
    assert event["start"] == "2026-09-26T11:00:00-07:00"
    assert len(event["moreDates"]) == 6
    assert len(event["id"]) == 12
    assert output["seasonal"][0]["until"] == "2026-11-15"
    assert output["seasonal"][0]["free"] is True
    schema.validate(output)


def test_event_all_day_with_no_end_emits_effective_end():
    event = make_event(all_day=True, end=None, start=datetime(2026, 9, 26, 0, 0, tzinfo=LA))
    data = schema._event(event)
    assert data["end"] == effective_end(event).isoformat() == "2026-09-27T00:00:00-07:00"


@pytest.mark.parametrize("start, expected", [
    (datetime(2026, 11, 1, tzinfo=LA), ("2026-11-01T00:00:00-07:00", "2026-11-02T00:00:00-08:00")),  # falls back
    (datetime(2027, 3, 14, tzinfo=LA), ("2027-03-14T00:00:00-08:00", "2027-03-15T00:00:00-07:00")),  # springs ahead
])
def test_event_all_day_with_no_end_on_a_dst_day_ends_at_the_next_local_midnight(start, expected):
    data = schema._event(make_event(all_day=True, end=None, start=start))
    assert (data["start"], data["end"]) == expected


def test_event_timed_with_no_end_still_emits_null():
    event = make_event(all_day=False, end=None)
    data = schema._event(event)
    assert data["end"] is None


@pytest.mark.parametrize("mutate, message", [
    (lambda o: o.update(schemaVersion=2), "schemaVersion"),
    (lambda o: o.update(generatedAt="yesterday"), "generatedAt"),
    (lambda o: o["events"][0].update(category="sports"), "category"),
    (lambda o: o["events"][0].update(region="tacoma"), "region"),
    (lambda o: o["events"][0].update(url="javascript:alert(1)"), "url"),
    (lambda o: o["events"][0].update(score=101), "score"),
    (lambda o: o["events"][0].update(free="yes"), "free"),
    (lambda o: o["events"][0].pop("ongoing"), "keys"),
    (lambda o: o["events"].append(dict(o["events"][0])), "duplicate id"),
    (lambda o: o["sources"][0].update(status="maybe"), "status"),
    (lambda o: o["weather"]["seattle"]["periods"][0].update(condition="hail"), "condition"),
    (lambda o: o["seasonal"][0].update(url="ftp://example.org"), "seasonal"),
])
def test_validate_rejects(mutate, message):
    output = copy.deepcopy(build_output())
    mutate(output)
    with pytest.raises(schema.SchemaError, match=message):
        schema.validate(output)
