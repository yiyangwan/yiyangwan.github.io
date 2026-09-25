import json
from datetime import datetime

import pytest

from around_seattle import build, schema, seasonal
from around_seattle.models import LA, SourceError, SourceResult, SourceSkipped
from around_seattle.tests.conftest import NOW, FakeHttp, make_config, make_event, read_fixture
from around_seattle.weather import FORECAST_URLS

TEST_SOURCES = """
further_ahead: {min_score: 50, max_events: 30}
sources:
  - {id: seattle-gov, name: City of Seattle, homepage: "https://www.seattle.gov/event-calendar", type: ics,
     url: "https://example.org/seattle.ics", region: seattle, weight: 20, exclude_categories: [Seattle City Council]}
  - {id: town-hall, name: Town Hall Seattle, homepage: "https://townhallseattle.org/events/", type: tribe,
     url: "https://example.org/tribe", region: seattle, weight: 30}
  - {id: redmond-city, name: City of Redmond, homepage: "https://www.redmond.gov/calendar.aspx", type: civicplus,
     url: "https://example.org/redmond.xml", region: eastside, weight: 18}
  - {id: ticketmaster, name: Ticketmaster, homepage: "https://www.ticketmaster.com/", type: ticketmaster,
     url: "https://example.org/tm", region: null, weight: 20, respect_robots: false, secret_env: TICKETMASTER_API_KEY}
"""
TEST_SEASONAL = """
- {id: kubota, title: Fall color at Kubota Garden, summary: Maples turn., place: Kubota Garden, city: Seattle,
   region: seattle, category: outdoors, url: "https://www.kubotagarden.org/", free: true, from: "09-01", to: "11-15",
   source: "https://www.kubotagarden.org/", verified: 2026-09-25}
"""


@pytest.fixture
def config_dir(tmp_path):
    folder = tmp_path / "config"
    folder.mkdir()
    (folder / "sources.yml").write_text(TEST_SOURCES, encoding="utf-8")
    (folder / "seasonal.yml").write_text(TEST_SEASONAL, encoding="utf-8")
    return folder


def fixture_http():
    def tribe_pages(params):
        return read_fixture("tribe_page1.json" if params["page"] == 1 else "tribe_page2.json")
    return FakeHttp({
        "https://example.org/seattle.ics": read_fixture("trumba_seattle.ics"),
        "https://example.org/tribe": tribe_pages,
        "https://example.org/redmond.xml": read_fixture("civicplus_redmond.xml"),
        FORECAST_URLS["seattle"]: read_fixture("nws_seattle.json"),
        FORECAST_URLS["eastside"]: read_fixture("nws_seattle.json"),
    })


def run_main(config_dir, tmp_path, http):
    out = tmp_path / "out" / "around-seattle.json"
    code = build.main(["--out", str(out), "--now", NOW.isoformat(), "--config-dir", str(config_dir)],
                      http=http, env={})
    return code, out


def test_repo_config_and_seasonal_picks_load():
    configs, further = build.load_sources(build.DEFAULT_CONFIG_DIR / "sources.yml")
    assert [c.id for c in configs] == ["seattle-gov", "town-hall", "uw-seattle", "experience-redmond",
                                       "redmond-city", "issaquah-city", "ticketmaster"]
    assert further == {"min_score": 50, "max_events": 30}
    ticketmaster = configs[-1]
    assert (ticketmaster.secret_env, ticketmaster.respect_robots, ticketmaster.region) == (
        "TICKETMASTER_API_KEY", False, None)
    picks = seasonal.load(build.DEFAULT_CONFIG_DIR / "seasonal.yml")
    assert picks
    assert len({pick.id for pick in picks}) == len(picks)


def test_unknown_source_type_is_rejected(tmp_path):
    path = tmp_path / "sources.yml"
    path.write_text("sources:\n  - {id: x, name: X, homepage: 'https://x.org', type: rss2, url: 'https://x.org', "
                    "region: seattle, weight: 1}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown type"):
        build.load_sources(path)


def test_main_writes_valid_output(config_dir, tmp_path):
    code, out = run_main(config_dir, tmp_path, fixture_http())
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    schema.validate(data)
    assert {s["id"]: s["status"] for s in data["sources"]} == {
        "seattle-gov": "ok", "town-hall": "ok", "redmond-city": "ok", "ticketmaster": "skipped"}
    titles = {event["title"]: event for event in data["events"]}
    assert "Seattle City Council Briefing" not in titles
    assert "City Council Business Meeting" not in titles
    lantern = titles["Mid-Autumn Lantern Walk"]
    assert (lantern["category"], lantern["region"], lantern["free"]) == ("festival", "seattle", True)
    assert titles["Fall Harvest Festival at Remlinger’s"]["region"] == "eastside"
    assert titles["2nd Annual Flapjacks & Flannel Breakfast"]["region"] == "eastside"
    assert titles["Watercolor paintings of a floral world"]["ongoing"] is True
    assert "Perfume Genius (Duo)" not in titles  # far window keeps only notable priority types
    assert len(data["weather"]["seattle"]["periods"]) == 6
    assert "2026-09-25" in data["sun"]
    assert [pick["id"] for pick in data["seasonal"]] == ["kubota"]


def test_main_fails_when_every_source_fails(config_dir, tmp_path):
    code, out = run_main(config_dir, tmp_path, FakeHttp({}))
    assert code == 2
    assert not out.exists()


def run_a_year_later(config_dir, tmp_path, http):
    """Build a year after the fixtures' dates: every feed still parses, but every event in it has ended."""
    out = tmp_path / "out" / "around-seattle.json"
    later = NOW.replace(year=NOW.year + 1)
    code = build.main(["--out", str(out), "--now", later.isoformat(), "--config-dir", str(config_dir)],
                      http=http, env={})
    return code, out


def test_main_writes_nothing_when_no_events_are_left(config_dir, tmp_path, capsys):
    code, out = run_a_year_later(config_dir, tmp_path, fixture_http())
    captured = capsys.readouterr()
    assert code == 2
    assert not out.exists()
    assert "error: no events after filtering; nothing written" in captured.err
    assert "seattle-gov: ok, 0 events" in captured.out


def test_main_writes_nothing_when_no_events_are_left_and_one_source_failed(config_dir, tmp_path, capsys):
    http = fixture_http()
    http.routes = {url: text for url, text in http.routes.items() if url != "https://example.org/redmond.xml"}
    code, out = run_a_year_later(config_dir, tmp_path, http)
    captured = capsys.readouterr()
    assert code == 2
    assert not out.exists()
    assert "redmond-city: error, 0 events (HTTP 404)" in captured.out
    assert "error: no events after filtering; nothing written" in captured.err


def test_main_fails_on_invalid_output(config_dir, tmp_path, monkeypatch):
    def reject(output):
        raise schema.SchemaError("events[0]: bad")
    monkeypatch.setattr(build.schema, "validate", reject)
    code, out = run_main(config_dir, tmp_path, fixture_http())
    assert code == 2
    assert not out.exists()


def test_weather_failure_becomes_null_and_is_logged(config_dir, tmp_path, monkeypatch, capsys):
    def boom(client):
        raise RuntimeError("nws down")
    monkeypatch.setattr(build.weather, "collect", boom)
    code, out = run_main(config_dir, tmp_path, fixture_http())
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["weather"] is None
    assert "weather: error (RuntimeError)" in capsys.readouterr().out


def test_weather_unavailable_is_logged_without_an_exception(config_dir, tmp_path, capsys):
    http = fixture_http()
    http.routes = {url: text for url, text in http.routes.items() if url not in FORECAST_URLS.values()}
    code, out = run_main(config_dir, tmp_path, http)
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["weather"] is None
    assert "weather: unavailable" in capsys.readouterr().out


def test_weather_ok_is_logged_with_the_regions_present(config_dir, tmp_path, capsys):
    code, out = run_main(config_dir, tmp_path, fixture_http())
    assert code == 0
    assert "weather: ok (seattle, eastside)" in capsys.readouterr().out


def test_run_sources_isolates_failures_and_redacts_secrets(monkeypatch, window):
    def ok(config, http, window, env):
        return [make_event()]

    def forbidden(config, http, window, env):
        raise SourceError("HTTP 403")

    def dormant(config, http, window, env):
        raise SourceSkipped("no API key configured")

    def bug(config, http, window, env):
        raise RuntimeError("boom with s3cret-key inside")

    monkeypatch.setattr(build, "ADAPTERS", {"a": ok, "b": forbidden, "c": dormant, "d": bug})
    configs = [make_config(id=kind, type=kind) for kind in "abcd"]
    results = build.run_sources(configs, None, window, {"TICKETMASTER_API_KEY": "s3cret-key"})
    assert [(r.status, r.error) for r in results] == [
        ("ok", None), ("error", "HTTP 403"), ("skipped", "no API key configured"), ("error", "RuntimeError")]
    assert len(results[0].events) == 1


def test_run_sources_redacts_a_configs_own_secret_env(monkeypatch, window):
    def forbidden(config, http, window, env):
        raise SourceError("blocked: s3cret-other-key")

    monkeypatch.setattr(build, "ADAPTERS", {"a": forbidden})
    config = make_config(id="a", type="a", secret_env="OTHER_API_KEY")
    results = build.run_sources([config], None, window, {"OTHER_API_KEY": "s3cret-other-key"})
    assert results[0].error == "blocked: ***"


def test_process_filters_places_and_selects(window):
    city = make_config(id="city", region="seattle", weight=20, exclude_categories=("Volunteer",))
    uw = make_config(id="uw", region="seattle", weight=10, require_category=True)
    city_events = (
        make_event(source_id="city", uid="1", title="Harvest Festival"),
        make_event(source_id="city", uid="2", title="City Council Briefing"),
        make_event(source_id="city", uid="3", title="Harvest Festival Tacoma", city="Tacoma"),
        make_event(source_id="city", uid="4", title="Beach Cleanup", raw_categories=("Volunteer",)),
        make_event(source_id="city", uid="5", title="Lantern Festival", end=None,
                   start=datetime(2026, 11, 7, 18, 0, tzinfo=LA)),
        make_event(source_id="city", uid="6", title="Car Show", end=None, start=datetime(2026, 11, 8, 10, 0, tzinfo=LA)),
    )
    uw_events = (make_event(source_id="uw", uid="7", title="Car Show Two"),)
    results = [SourceResult(city, "ok", city_events), SourceResult(uw, "ok", uw_events)]
    events = build.process(results, [city, uw], window, {"min_score": 50, "max_events": 30})
    assert [event.title for event in events] == ["Harvest Festival", "Lantern Festival"]
    assert (events[0].score, events[0].region, events[0].category) == (55, "seattle", "festival")
