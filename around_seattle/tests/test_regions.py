import pytest

from around_seattle.regions import assign_region, detect_city
from around_seattle.tests.conftest import make_event


@pytest.mark.parametrize("text, expected", [
    ("8703 160th Ave NERedmond, WA 98052", "Redmond"),
    ("Ship Canal Trail, 130 Nickerson Street Seattle WA 98109", "Seattle"),
    ("Elisabeth Miller Library, 3501 NE 41st St, WA, 98105", None),
    ("Downtown Issaquah", "Issaquah"),
    ("Kent Station, 417 Ramsay Way, Kent, WA 98032", "Kent"),
    ("123 Kent St", None),
    ("Mercer Island Community Center, Mercer Island, Washington", "Mercer Island"),
    (None, None),
])
def test_detect_city(text, expected):
    assert detect_city(text) == expected


def test_structured_city_sets_region():
    placed = assign_region(make_event(city="Carnation"), "seattle")
    assert (placed.city, placed.region) == ("Carnation", "eastside")
    assert assign_region(make_event(city="seattle"), None).city == "Seattle"


def test_structured_city_outside_the_area_drops_the_event():
    assert assign_region(make_event(city="Tacoma"), "seattle") is None
    assert assign_region(make_event(city="Preston"), "eastside") is None


def test_location_text_city_and_defaults():
    assert assign_region(make_event(location_text="Kent Station, Kent, WA"), "seattle") is None
    placed = assign_region(make_event(location_text="Bellevue Downtown Park, Bellevue, WA"), "seattle")
    assert (placed.city, placed.region) == ("Bellevue", "eastside")
    assert assign_region(make_event(location_text="Magnuson Park"), "seattle").region == "seattle"
    assert assign_region(make_event(), None) is None
