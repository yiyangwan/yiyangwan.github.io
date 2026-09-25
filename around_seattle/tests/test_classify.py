import pytest

from around_seattle.classify import categorize, is_noise
from around_seattle.tests.conftest import make_config, make_event


@pytest.mark.parametrize("title", [
    "Seattle City Council Briefing",
    "Planning Commission",
    "Toddler Storytime",
    "Watercolor Class for Adults",
    "Park Cleanup Work Party",
    "Grant Application Deadline",
    "Info Session: Study Abroad",
    "CANCELLED: Jazz in the Park",
    "Virtual Event: Author Talk",
    "Public Hearing on Zoning",
    "Park Closed for Maintenance",
    "Zoning Hearing",
])
def test_noise_titles(title):
    assert is_noise(make_event(title=title), make_config())


@pytest.mark.parametrize("title", [
    "Volunteer Park Halloween Pet Parade",
    "Classical Guitar Night",
    "Boardwalk Stroll",
    "Town Hall Seattle Presents: Naomi Klein",
    "Masterclass Recital",
    "Salmon Days Festival",
    "World-Class Jazz Festival",
    "Closed Captioned Screening: Coco",
    "Hearing Loop Concert",
])
def test_not_noise_titles(title):
    assert not is_noise(make_event(title=title), make_config())


def test_excluded_source_category_is_noise_after_normalizing():
    config = make_config(exclude_categories=("Boards & Commissions", "Volunteer"))
    assert is_noise(make_event(title="Arts Commission", raw_categories=("Boards &amp; Commissions",)), config)
    assert is_noise(make_event(title="Beach cleanup", raw_categories=("Volunteer",)), config)
    assert not is_noise(make_event(title="Beach walk", raw_categories=("Parks & Recreation",)), config)


def test_noise_in_raw_categories_and_online_locations():
    assert is_noise(make_event(title="Husky Tips", raw_categories=("Information Sessions",)), make_config())
    assert is_noise(make_event(title="Author talk", location_text="Online"), make_config())
    assert not is_noise(make_event(title="Author talk", location_text="Online Park, Seattle"), make_config())


@pytest.mark.parametrize("title, raw, summary, expected", [
    ("Mid-Autumn Lantern Walk", ("Festivals/Fairs", "Ethnic/Cultural", "Outdoor"), None, "festival"),
    ("Summer Concerts at Chateau Ste. Michelle Winery: Hermanos Gutiérrez", ("Concerts",), None, "music"),
    ("Remlinger Farms Concerts: Big Thief", ("Concerts",), None, "music"),
    ("Ballard Farmers Market", (), None, "market"),
    ("Arboretum Walking Tour", (), None, "outdoors"),
    ("Jason Dove Mark with Lynda Mapes", ("Science",), "A conversation about climate.", "arts"),
    ("Redmond Town Center Exotics Car Show", (), None, "other"),
    ("Garden Concert", (), None, "music"),  # tie between music and outdoors breaks toward music
])
def test_categorize(title, raw, summary, expected):
    assert categorize(make_event(title=title, raw_categories=raw, summary=summary)) == expected
