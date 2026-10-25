from datetime import datetime

import pytest

from around_seattle.classify import categorize, fix_implausible_time, is_noise
from around_seattle.models import LA
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
    "Park Board",
    "Transportation Advisory Board",
    "Issaquah Police Town Hall",
    "BALLOTS & BOBA: ELECTIONS TOWN HALL",
    "Free Paint Recycling Collection Event",
    "Hard-to-Recycle Collection Event",
    "Miyawaki Maintenance Event",
    "Lake Washington Girls Middle School Open House",
    "Open House: South Lake Sammamish Neighborhood",
    "Clean Start Adoption Event",
    "Spot Reservation",
    "Basics of Emergency Prep",
    "Winter Clothing Fest: Clothing Donation Day",
    "Laboratory Medicine Grand Rounds: Design of Smart Medicines",
    "Research Computing Symposium",
    "16th John D. Loeser Pain Conference",
    "HCDE Research Speaker Series: David Ribes",
    "Fundamentals For Startups: AI investment trends",
    "Trivia at Flatstick Pub",
    "Flatstick Pub Bingo",
    "Happy Hour at Brown’s Stockyard Exchange",
    "Flatstick Pub Study Hall",
    "Boots & Brews Line Dancing",
    "Drop-In Play at the Redmond Community Center",
    "Open Mic Night",
    "Lumen Field Stadium Tours",
    "Seattle Mariners Ballpark Tour",
    "All Access Pass – Climate Pledge Arena Tours",
    "Members-Only Pilot Tour: Explore the Historic Eng Family Home",
    "Pines on Pike Christmas Tree Lot",
    "City Holiday: Veterans Day",
    "Civic Coffee Caregiver Support",
    "Ribbon Cutting - Alki Playground and Parkway",
    "Black Futures Book Club",
    "Aussies & Kiwis Meetup",
    "Holiday Senior Stroll",
    "Low Sensory Nights at WildLanterns",
    "Sneaky with Snicket (Children’s Concert) – SENSORY FRIENDLY",
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
    "Freddy Fuego Orchestra (Sunday Matinee) @ Town Hall Seattle",
    "Snowboard Film Night",
    "Chinese Cultural Open House",
    "Kacey Musgraves - Middle of Nowhere Tour",
    "Seattle Coffee Festival",
    "Tree Lighting Celebration at Westlake Park",
    "Stand Up Paddle Board Yoga",
    "Summit Hike to Mount Si",
    "Western Conference Finals Watch Party",
    "Harvest Festival (Reservations Required)",
    "Spooky Spectacular at the Redmond Senior & Community Center",
    "Research Vessel Open Deck",
])
def test_not_noise_titles(title):
    assert not is_noise(make_event(title=title), make_config())


def test_town_hall_presents_category_is_not_noise():
    event = make_event(title="Claudia Rankine", raw_categories=("Town Hall Presents", "Arts & Culture"))
    assert not is_noise(event, make_config())


def test_member_only_category_is_noise():
    assert is_noise(make_event(title="Downtown Preview", raw_categories=("DSA Member-Only",)), make_config())


def test_include_categories_keeps_only_listed_categories_after_normalizing():
    config = make_config(include_categories=("Town Hall Presents", "Festivals/Fairs"))
    assert not is_noise(make_event(title="Valeria Luiselli", raw_categories=("Town Hall Presents",)), config)
    assert not is_noise(make_event(title="Odunde Fest", raw_categories=("Arts", "Festivals&#47;Fairs")), config)
    assert is_noise(make_event(title="Spotlight Concert", raw_categories=("Rentals",)), config)
    assert is_noise(make_event(title="Spotlight Concert"), config)


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


def test_a_timed_start_between_1_and_5_am_keeps_its_date_but_not_its_hours():
    def at(hour, all_day=False):
        return make_event(title="Odunde Fest", start=datetime(2026, 10, 23, hour, 0, tzinfo=LA),
                          end=datetime(2026, 10, 23, hour + 6, 0, tzinfo=LA), all_day=all_day)
    fixed = fix_implausible_time(at(3))
    assert (fixed.start, fixed.end, fixed.all_day) == (datetime(2026, 10, 23, 0, 0, tzinfo=LA),
                                                       datetime(2026, 10, 24, 0, 0, tzinfo=LA), True)
    assert fix_implausible_time(at(1)).all_day is True
    assert not is_noise(at(3), make_config())
    for unchanged in (at(5), at(0), at(3, all_day=True)):  # midnight starts are how some feeds mark all-day listings
        assert fix_implausible_time(unchanged) is unchanged
