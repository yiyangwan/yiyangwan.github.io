from datetime import datetime

import pytest

from around_seattle import sun, weather
from around_seattle.tests.conftest import FakeHttp, read_fixture

ICON = "https://api.weather.gov/icons/land/day/{}?size=medium"


@pytest.mark.parametrize("icon, short, expected", [
    (ICON.format("rain,70/tsra,100"), "", "storm"),
    (ICON.format("sct"), "Mostly Sunny", "partly"),
    (ICON.format("bkn"), "Partly Sunny", "mostly-cloudy"),
    (ICON.format("ovc"), "Cloudy", "cloudy"),
    (ICON.format("few"), "Sunny", "clear"),
    (ICON.format("fog"), "Patchy Fog", "fog"),
    (ICON.format("smoke"), "Areas Of Smoke", "smoke"),
    (ICON.format("snow,40"), "", "snow"),
    (None, "Chance Rain Showers then Mostly Sunny", "rain"),
    (ICON.format("unknowncode"), "Partly Cloudy", "partly"),
    (None, "", "cloudy"),
])
def test_condition_for(icon, short, expected):
    assert weather.condition_for(icon, short) == expected


def test_collect_maps_periods_and_tolerates_one_failure():
    http = FakeHttp({weather.FORECAST_URLS["seattle"]: read_fixture("nws_seattle.json")})
    data = weather.collect(http)
    assert data["eastside"] is None
    periods = data["seattle"]["periods"]
    assert [p["condition"] for p in periods] == ["rain", "storm", "rain", "partly", "mostly-cloudy", "mostly-cloudy"]
    assert periods[1] == {"name": "Friday", "start": "2026-09-25T06:00:00-07:00", "end": "2026-09-25T18:00:00-07:00",
                          "isDaytime": True, "temperature": 62, "unit": "F",
                          "shortForecast": "Rain then Showers And Thunderstorms", "condition": "storm",
                          "precipChance": 96}
    assert periods[4]["precipChance"] == 0
    assert http.calls[0][2] == {"respect_robots": False, "headers": {"Accept": "application/geo+json"}}


def test_collect_returns_none_when_both_fail():
    assert weather.collect(FakeHttp({})) is None


def test_collect_treats_malformed_payload_as_failure():
    http = FakeHttp({url: '{"properties": {}}' for url in weather.FORECAST_URLS.values()})
    assert weather.collect(http) is None


def test_collect_treats_null_periods_as_failure():
    http = FakeHttp({url: '{"properties": {"periods": [null]}}' for url in weather.FORECAST_URLS.values()})
    assert weather.collect(http) is None


def test_collect_isolates_a_wrongly_typed_period_to_its_region():
    good = read_fixture("nws_seattle.json")
    bad = good.replace('"probabilityOfPrecipitation": {"unitCode": "wmoUnit:percent", "value": 94}',
                       '"probabilityOfPrecipitation": 5', 1)
    http = FakeHttp({weather.FORECAST_URLS["seattle"]: bad, weather.FORECAST_URLS["eastside"]: good})
    data = weather.collect(http)
    assert data["seattle"] is None
    assert len(data["eastside"]["periods"]) == 6


def test_sun_for_window(window):
    days = sun.for_window(window)
    assert len(days) == 15
    assert min(days) == "2026-09-25" and max(days) == "2026-10-09"
    sunset = datetime.fromisoformat(days["2026-09-25"]["sunset"])
    sunrise = datetime.fromisoformat(days["2026-09-25"]["sunrise"])
    assert sunset.tzinfo is not None and sunset.second == 0
    assert (18, 50) <= (sunset.hour, sunset.minute) <= (19, 10)
    assert (6, 50) <= (sunrise.hour, sunrise.minute) <= (7, 15)
