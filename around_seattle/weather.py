"""NWS 7-day forecasts for Seattle and Bellevue, mapped to a small condition vocabulary."""
from __future__ import annotations

from urllib.parse import urlsplit

from .models import SourceError

FORECAST_URLS = {
    "seattle": "https://api.weather.gov/gridpoints/SEW/125,68/forecast",
    "eastside": "https://api.weather.gov/gridpoints/SEW/129,67/forecast",
}
SEVERITY = ("clear", "partly", "mostly-cloudy", "cloudy", "fog", "smoke", "rain", "snow", "storm")
# NWS icon codes: https://api.weather.gov/icons. "sct" is "Mostly Sunny" by day, "bkn" is "Partly Sunny".
ICON_CONDITIONS = {
    "skc": "clear", "few": "clear", "hot": "clear", "cold": "clear", "wind_skc": "clear", "wind_few": "clear",
    "sct": "partly", "wind_sct": "partly",
    "bkn": "mostly-cloudy", "wind_bkn": "mostly-cloudy",
    "ovc": "cloudy", "wind_ovc": "cloudy",
    "fog": "fog",
    "smoke": "smoke", "haze": "smoke", "dust": "smoke",
    "rain": "rain", "rain_showers": "rain", "rain_showers_hi": "rain", "rain_sleet": "rain", "rain_fzra": "rain",
    "fzra": "rain",
    "snow": "snow", "sleet": "snow", "rain_snow": "snow", "snow_sleet": "snow", "snow_fzra": "snow",
    "blizzard": "snow",
    "tsra": "storm", "tsra_sct": "storm", "tsra_hi": "storm", "tornado": "storm", "hurricane": "storm",
    "tropical_storm": "storm",
}
_TEXT_RULES = (  # checked in order; the first rule with a matching phrase wins
    ("storm", ("thunder",)),
    ("snow", ("snow", "sleet", "blizzard", "flurr")),
    ("rain", ("rain", "shower", "drizzle")),
    ("smoke", ("smoke", "haze", "dust")),
    ("fog", ("fog",)),
    ("partly", ("mostly sunny", "partly cloudy", "mostly clear")),
    ("mostly-cloudy", ("partly sunny", "mostly cloudy")),
    ("cloudy", ("cloudy", "overcast")),
    ("clear", ("sunny", "clear")),
)


def condition_from_text(text: str | None) -> str:
    lowered = (text or "").lower()
    for condition, phrases in _TEXT_RULES:
        if any(phrase in lowered for phrase in phrases):
            return condition
    return "cloudy"


def condition_for(icon_url: str | None, short_forecast: str | None) -> str:
    segments = urlsplit(icon_url or "").path.split("/")[4:]  # /icons/land/{day|night}/{code[,pct]}/...
    found = [ICON_CONDITIONS[code] for code in (segment.split(",")[0] for segment in segments)
             if code in ICON_CONDITIONS]
    if found:
        return max(found, key=SEVERITY.index)
    return condition_from_text(short_forecast)


def _period(raw: dict) -> dict:
    chance = (raw.get("probabilityOfPrecipitation") or {}).get("value")
    return {
        "name": str(raw["name"]),
        "start": str(raw["startTime"]),
        "end": str(raw["endTime"]),
        "isDaytime": bool(raw["isDaytime"]),
        "temperature": int(raw["temperature"]),
        "unit": str(raw.get("temperatureUnit") or "F"),
        "shortForecast": str(raw.get("shortForecast") or ""),
        "condition": condition_for(raw.get("icon"), raw.get("shortForecast")),
        "precipChance": int(chance) if isinstance(chance, (int, float)) else 0,
    }


def collect(http) -> dict | None:
    result = {}
    for region, url in FORECAST_URLS.items():
        try:
            # api.weather.gov's robots.txt disallows crawlers, but NWS documents this API for applications.
            data = http.get_json(url, respect_robots=False, headers={"Accept": "application/geo+json"})
            periods = [_period(raw) for raw in data["properties"]["periods"]]
        except (SourceError, KeyError, TypeError, ValueError, AttributeError, OverflowError):
            result[region] = None
            continue
        result[region] = {"periods": periods} if periods else None
    return result if any(result.values()) else None
