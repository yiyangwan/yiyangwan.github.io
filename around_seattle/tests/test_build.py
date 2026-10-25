import json
from datetime import datetime

import pytest

from around_seattle import build, schema, seasonal, signature
from around_seattle.models import LA, SourceError, SourceResult, SourceSkipped, Window
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
TEST_SIGNATURE = """
- {id: lantern-walk, title: Mid-Autumn Lantern Walk, summary: Lanterns light a walk through the park., place: Volunteer Park,
   city: Seattle, region: seattle, category: festival, url: "https://example.org/lanterns", free: true,
   usually: early October, match: [Lantern Walk],
   dates: [{from: 2026-10-03, to: 2026-10-04, source: "https://example.org/lanterns", verified: 2026-09-25}]}
- {id: folklife, title: Northwest Folklife Festival, summary: Music and dance across Seattle Center., place: Seattle Center,
   city: Seattle, region: seattle, category: festival, url: "https://www.nwfolklife.org/", usually: Memorial Day weekend}
"""


@pytest.fixture
def config_dir(tmp_path):
    folder = tmp_path / "config"
    folder.mkdir()
    (folder / "sources.yml").write_text(TEST_SOURCES, encoding="utf-8")
    (folder / "seasonal.yml").write_text(TEST_SEASONAL, encoding="utf-8")
    (folder / "signature.yml").write_text(TEST_SIGNATURE, encoding="utf-8")
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
    configs, limits = build.load_sources(build.DEFAULT_CONFIG_DIR / "sources.yml")
    assert [c.id for c in configs] == ["woodland-park-zoo", "downtown-seattle", "town-hall", "seattle-gov",
                                       "experience-redmond", "redmond-city", "ticketmaster"]
    assert limits == {"near_min_score": 55, "min_score": 66, "max_events": 10}
    ticketmaster = configs[-1]
    assert (ticketmaster.secret_env, ticketmaster.respect_robots, ticketmaster.region) == (
        "TICKETMASTER_API_KEY", False, None)
    assert "Climate Pledge Arena" in ticketmaster.arena_venues and "Paramount Theatre" in ticketmaster.major_venues
    assert "Neptune Theatre" in ticketmaster.midsize_venues
    assert [c.day_cap for c in configs] == [None] * 6 + [1]
    assert {c.id: c.include_categories for c in configs if c.include_categories} == {
        "town-hall": ("Town Hall Presents",),
        "seattle-gov": ("Festivals/Fairs", "Holiday/Seasonal Events"),
        "experience-redmond": ("Featured Events", "Holiday", "Concerts", "Redmond Arts"),
    }
    picks = seasonal.load(build.DEFAULT_CONFIG_DIR / "seasonal.yml")
    assert picks
    assert len({pick.id for pick in picks}) == len(picks)
    highlights = signature.load(build.DEFAULT_CONFIG_DIR / "signature.yml")
    assert highlights
    assert all(when.verified for pick in highlights for when in pick.dates)


def test_load_sources_reads_limits_and_per_source_lists(tmp_path):
    path = tmp_path / "sources.yml"
    path.write_text("""
near: {min_score: 40}
sources:
  - {id: tm, name: TM, homepage: "https://tm.example", type: ticketmaster, url: "https://tm.example/api",
     region: null, weight: 14, include_categories: [Music], arena_venues: [Arena], major_venues: [Theatre],
     midsize_venues: [Hall]}
""", encoding="utf-8")
    configs, limits = build.load_sources(path)
    assert limits == {"near_min_score": 40, "min_score": 50, "max_events": 30}
    assert (configs[0].include_categories, configs[0].arena_venues, configs[0].major_venues,
            configs[0].midsize_venues) == (("Music",), ("Arena",), ("Theatre",), ("Hall",))


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
    highlights = [event for event in data["events"] if event["highlight"]]
    assert [(e["title"], e["source"], e["allDay"]) for e in highlights] == [
        ("Mid-Autumn Lantern Walk", "signature", True)]


def test_main_logs_signature_events_that_need_dates(config_dir, tmp_path, capsys):
    code, out = run_main(config_dir, tmp_path, fixture_http())
    assert code == 0
    assert "signature: 1 entry needs its next dates (folklife)" in capsys.readouterr().out


def test_main_logs_signature_dates_to_check_again(config_dir, tmp_path, capsys):
    text = TEST_SIGNATURE.replace("verified: 2026-09-25}]}", "verified: 2026-05-01}]}", 1)
    (config_dir / "signature.yml").write_text(text, encoding="utf-8")
    code, out = run_main(config_dir, tmp_path, fixture_http())
    assert code == 0
    assert "signature: check these dates again: lantern-walk (verified 2026-05-01)" in capsys.readouterr().out


def test_main_marks_maintenance_lines_as_warnings_in_github_actions(config_dir, tmp_path, capsys):
    out = tmp_path / "out" / "around-seattle.json"
    code = build.main(["--out", str(out), "--now", NOW.isoformat(), "--config-dir", str(config_dir)],
                      http=fixture_http(), env={"GITHUB_ACTIONS": "true"})
    assert code == 0
    assert "::warning::signature: 1 entry needs its next dates (folklife)" in capsys.readouterr().out


def test_main_does_not_publish_signature_events_alone_when_the_feeds_have_nothing(config_dir, tmp_path, capsys):
    next_year = TEST_SIGNATURE.replace("{from: 2026-10-03, to: 2026-10-04,", "{from: 2027-10-02, to: 2027-10-03,")
    (config_dir / "signature.yml").write_text(next_year, encoding="utf-8")
    code, out = run_a_year_later(config_dir, tmp_path, fixture_http())  # every feed event has ended by then
    assert code == 2
    assert not out.exists()
    assert "error: no events after filtering; nothing written" in capsys.readouterr().err


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
        raise RuntimeError("boom with fake-value inside")

    monkeypatch.setattr(build, "ADAPTERS", {"a": ok, "b": forbidden, "c": dormant, "d": bug})
    configs = [make_config(id=kind, type=kind) for kind in "abcd"]
    results = build.run_sources(configs, None, window, {"TICKETMASTER_API_KEY": "fake-value"})
    assert [(r.status, r.error) for r in results] == [
        ("ok", None), ("error", "HTTP 403"), ("skipped", "no API key configured"), ("error", "RuntimeError")]
    assert len(results[0].events) == 1


def test_run_sources_redacts_a_configs_own_secret_env(monkeypatch, window):
    def forbidden(config, http, window, env):
        raise SourceError("blocked: fake-other-value")

    monkeypatch.setattr(build, "ADAPTERS", {"a": forbidden})
    config = make_config(id="a", type="a", secret_env="OTHER_API_KEY")
    results = build.run_sources([config], None, window, {"OTHER_API_KEY": "fake-other-value"})
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


def test_process_adds_signature_events_and_absorbs_their_feed_listings(window, tmp_path):
    (tmp_path / "signature.yml").write_text(TEST_SIGNATURE, encoding="utf-8")
    picks = signature.load(tmp_path / "signature.yml")
    city = make_config(id="city", region="seattle", weight=20)
    feed = (make_event(source_id="city", uid="1", title="Lantern Walk", start=datetime(2026, 10, 3, 18, 0, tzinfo=LA),
                       end=None),
            make_event(source_id="city", uid="2", title="Harvest Festival"))
    events = build.process([SourceResult(city, "ok", feed)], [city], window, {"min_score": 50, "max_events": 30},
                           picks)
    assert [(e.title, e.highlight) for e in events] == [("Harvest Festival", False), ("Mid-Autumn Lantern Walk", True)]
    assert events[1].ongoing is False


def test_process_drops_near_events_below_the_floor(window):
    city = make_config(id="city", region="seattle", weight=20)
    feed = (make_event(source_id="city", uid="1", title="Harvest Festival"),
            make_event(source_id="city", uid="2", title="Car Show"))
    limits = {"near_min_score": 45, "min_score": 50, "max_events": 30}
    events = build.process([SourceResult(city, "ok", feed)], [city], window, limits)
    assert [(e.title, e.score) for e in events] == [("Harvest Festival", 55)]


def test_cap_per_day_ranks_a_sources_extra_events_last():
    friday = datetime(2026, 10, 2, 19, 0, tzinfo=LA)
    shows = [make_event(source_id="tm", uid=f"tm{n}", title=f"Show {n}", start=friday, end=None, score=score)
             for n, score in enumerate((46, 51, 46))]
    local = make_event(source_id="city", uid="c1", title="Harvest Fair", start=friday, end=None, score=30)
    saturday = make_event(source_id="tm", uid="tm9", title="Show 9", start=datetime(2026, 10, 3, 19, 0, tzinfo=LA),
                          end=None, score=46)
    capped = build.cap_per_day([*shows, local, saturday], {"tm": 2})
    assert [event.score for event in capped] == [46, 51, 0, 30, 46]
    assert [event.score for event in build.cap_per_day(shows, {"tm": 0})] == [0, 0, 0]


def test_day_cap_also_keeps_extra_events_out_of_further_out(window):
    config = make_config(id="tm", region="seattle", weight=30, day_cap=1)
    shows = tuple(make_event(source_id="tm", uid=f"tm{n}", title=f"Concert {n}", category="music",
                             start=datetime(2026, 10, 24, 19 + n, 0, tzinfo=LA), end=None) for n in range(2))
    kept = build.process([SourceResult(config, "ok", shows)], [config], window, {"min_score": 50, "max_events": 30})
    assert [event.title for event in kept] == ["Concert 0"]


def test_process_applies_a_sources_day_cap(window):
    config = make_config(id="tm", region="seattle", day_cap=1)
    shows = tuple(make_event(source_id="tm", uid=f"tm{n}", title=f"Concert {n}", category="music",
                             start=datetime(2026, 9, 26, 19 + n, 0, tzinfo=LA), end=None) for n in range(2))
    kept = build.process([SourceResult(config, "ok", shows)], [config], window, {"min_score": 50, "max_events": 30})
    assert [(event.title, event.score > 0) for event in kept] == [("Concert 0", True), ("Concert 1", False)]


def test_process_keeps_a_category_the_source_set(window):
    config = make_config(id="tm", region="seattle")
    events = (make_event(source_id="tm", uid="1", title="Hail The Sun w/ A Lot Like Birds", category="music"),
              make_event(source_id="tm", uid="2", title="Birds of the Arboretum"))
    kept = build.process([SourceResult(config, "ok", events)], [config], window, {"min_score": 50, "max_events": 30})
    assert {event.title: event.category for event in kept} == {
        "Hail The Sun w/ A Lot Like Birds": "music", "Birds of the Arboretum": "outdoors"}


def test_process_absorbs_feed_listings_of_seasonal_picks(window, tmp_path):
    (tmp_path / "seasonal.yml").write_text(TEST_SEASONAL.replace("free: true,", "free: true, match: [Maple Tour],"),
                                           encoding="utf-8")
    picks = seasonal.load(tmp_path / "seasonal.yml")
    city = make_config(id="city", region="seattle", weight=20)
    feed = (make_event(source_id="city", uid="1", title="Kubota Maple Tour Festival"),
            make_event(source_id="city", uid="2", title="Harvest Festival"))
    events = build.process([SourceResult(city, "ok", feed)], [city], window, {"min_score": 50, "max_events": 30},
                           seasonal_picks=picks)
    assert [e.title for e in events] == ["Harvest Festival"]


@pytest.mark.parametrize("field", ["include_categories", "exclude_categories", "arena_venues", "major_venues",
                                   "midsize_venues"])
def test_load_sources_rejects_a_scalar_where_a_list_belongs(tmp_path, field):
    path = tmp_path / "sources.yml"
    path.write_text(f"sources:\n  - {{id: x, name: X, homepage: 'https://x.org', type: tribe, url: 'https://x.org', "
                    f"region: seattle, weight: 1, {field}: Town Hall Presents}}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=f"source x: {field} must be a list of names"):
        build.load_sources(path)


def test_process_keeps_feed_listings_of_a_seasonal_pick_that_is_not_shown_yet(tmp_path):
    (tmp_path / "seasonal.yml").write_text(TEST_SEASONAL.replace("free: true,", "free: true, match: [Maple Tour],")
                                           .replace('from: "09-01"', 'from: "11-01"'), encoding="utf-8")
    picks = seasonal.load(tmp_path / "seasonal.yml")
    city = make_config(id="city", region="seattle", weight=20)
    tour = make_event(source_id="city", uid="1", title="Kubota Maple Tour Festival", end=None,
                      start=datetime(2026, 11, 7, 11, 0, tzinfo=LA))
    events = build.process([SourceResult(city, "ok", (tour,))], [city], Window.starting(NOW),
                           {"min_score": 50, "max_events": 30}, seasonal_picks=picks)
    assert [e.title for e in events] == ["Kubota Maple Tour Festival"]
