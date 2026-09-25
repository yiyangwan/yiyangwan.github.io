"""City detection and the Seattle / Eastside region map."""
from __future__ import annotations

import re
from dataclasses import replace

from .models import Event

SEATTLE_CITIES = ("Seattle",)
EASTSIDE_CITIES = (
    "Bellevue", "Kirkland", "Redmond", "Issaquah", "Sammamish", "Woodinville", "Bothell", "Kenmore",
    "Mercer Island", "Newcastle", "Medina", "Clyde Hill", "Yarrow Point", "Hunts Point",
    "Beaux Arts Village", "Carnation", "Duvall", "Fall City", "Snoqualmie", "North Bend",
)
OTHER_CITIES = (
    "Tacoma", "Everett", "Renton", "Shoreline", "Lynnwood", "Edmonds", "Burien", "Tukwila", "Kent",
    "Federal Way", "Auburn", "Puyallup", "Olympia", "Bremerton", "Lake Forest Park", "SeaTac",
    "Des Moines", "Mukilteo", "Marysville", "Monroe", "Maple Valley", "Covington", "Enumclaw",
    "Gig Harbor", "Bainbridge Island", "Vashon", "Port Townsend", "Mount Vernon", "Bellingham",
    "Lakewood", "University Place", "Silverdale", "Poulsbo", "Arlington", "Snohomish", "Mill Creek",
    "Mountlake Terrace", "Normandy Park", "Black Diamond", "Spokane", "Portland", "Vancouver",
)
_REGION_BY_CITY = {
    **{city.casefold(): "seattle" for city in SEATTLE_CITIES},
    **{city.casefold(): "eastside" for city in EASTSIDE_CITIES},
    **{city.casefold(): None for city in OTHER_CITIES},
}
_DISPLAY = {city.casefold(): city for city in SEATTLE_CITIES + EASTSIDE_CITIES + OTHER_CITIES}


def _alternation(cities) -> str:
    return "|".join(re.escape(city) for city in sorted(cities, key=len, reverse=True))


# Feeds sometimes drop the separator ("160th Ave NERedmond, WA"), so the state anchors this match.
_BEFORE_STATE = re.compile(rf"({_alternation(_DISPLAY.values())})(?=\s*,?\s*(?:WA|Washington)\b)", re.IGNORECASE)
# Without a state, only in-area names count, so "123 Kent St" does not drop an event.
_AS_WORD = re.compile(rf"\b({_alternation(SEATTLE_CITIES + EASTSIDE_CITIES)})\b", re.IGNORECASE)


def detect_city(*texts: str | None) -> str | None:
    for pattern in (_BEFORE_STATE, _AS_WORD):
        for text in texts:
            if text:
                match = pattern.search(text)
                if match:
                    return _DISPLAY[match.group(1).casefold()]
    return None


def assign_region(event: Event, default_region: str | None) -> Event | None:
    """Return the event with city and region set, or None when it is outside the area."""
    structured = (event.city or "").strip().casefold()
    if structured:
        region = _REGION_BY_CITY.get(structured)
        return None if region is None else replace(event, city=_DISPLAY[structured], region=region)
    city = detect_city(event.location_text)
    if city is not None:
        region = _REGION_BY_CITY[city.casefold()]
        return None if region is None else replace(event, city=city, region=region)
    return None if default_region is None else replace(event, region=default_region)
