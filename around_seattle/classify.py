"""Noise rules and event types. Patterns match whole words, case-insensitively."""
from __future__ import annotations

import re

from .models import Event, SourceConfig
from .text import clean_inline

TYPE_ORDER = ("festival", "music", "market", "outdoors", "arts")
TITLE_WEIGHT = 2
OTHER_WEIGHT = 1
MAX_HITS_PER_TEXT = 2
ONLINE_LOCATIONS = frozenset({"online", "virtual", "zoom", "online event", "virtual event", "webinar"})


def _words(*patterns: str) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(patterns) + r")\b", re.IGNORECASE)


# Deliberately absent: bare "council" (Fremont Arts Council runs parades), bare "volunteer"
# (Volunteer Park), "suite" (The Nutcracker Suite), and "parking" (PARK(ing) Day).
NOISE = _words(
    r"city council", r"council meetings?", r"councilmembers?", r"community council",
    r"commissions?", r"committees?", r"board meetings?", r"public hearings?", r"hearings?",
    r"advisory (?:board|council|group|committee)s?", r"meetings?",
    r"office hours", r"info(?:rmation)? sessions?", r"webinars?", r"orientations?",
    r"story ?times?", r"baby ?times?", r"toddlers?", r"preschool",
    r"class(?:es)?", r"courses?", r"lessons?", r"trainings?",
    r"online only", r"virtual (?:event|program|session)s?", r"via zoom", r"on zoom", r"zoom meetings?",
    r"livestream(?:ed)? only",
    r"cancell?ed", r"postponed", r"closed", r"closures?",
    r"volunteer (?:opportunit(?:y|ies)|events?|shifts?|orientations?)", r"work part(?:y|ies)", r"ivy pulls?",
    r"support groups?", r"tax help", r"job fairs?", r"career fairs?", r"hiring events?",
    r"blood drives?", r"vaccin(?:e|ation) clinics?", r"flu shots?",
    r"deadlines?", r"applications?", r"registration (?:opens|closes|deadline)",
)

TYPE_PATTERNS = {
    "festival": _words(
        r"festivals?", r"fests?", r"fairs?", r"block part(?:y|ies)", r"parades?", r"carnivals?",
        r"celebrations?", r"oktoberfest", r"lanterns?", r"mid-autumn", r"diwali", r"lunar new year",
        r"d[ií]a de (?:los )?muertos", r"pride", r"juneteenth", r"tree lighting", r"holiday lights",
        r"ethnic/cultural",
    ),
    "music": _words(
        r"concerts?", r"live music", r"music", r"musicians?", r"symphon(?:y|ies)", r"orchestras?",
        r"philharmonic", r"choirs?", r"chorus", r"chorale", r"jazz", r"blues", r"bluegrass", r"dj",
        r"bands?", r"quartets?", r"recitals?", r"opera", r"musicals?", r"theat(?:er|re)", r"ballet",
        r"dance", r"comedy", r"comedians?", r"stand-up", r"improv", r"films?", r"screenings?",
        r"cinema", r"movies?", r"performances?", r"cabaret",
    ),
    "market": _words(
        r"farmers'? markets?", r"markets?", r"night markets?", r"food", r"beverages?", r"tastings?",
        r"wines?", r"winer(?:y|ies)", r"beers?", r"brewer(?:y|ies)", r"cider", r"distiller(?:y|ies)",
        r"food trucks?", r"dinners?", r"suppers?", r"brunch", r"bazaars?", r"flea",
    ),
    "outdoors": _words(
        r"parks?", r"gardens?", r"arboretum", r"hikes?", r"hiking", r"walks?", r"walking tours?",
        r"trails?", r"nature", r"outdoors?", r"birds?", r"birding", r"salmon", r"forests?",
        r"trees?", r"beach(?:es)?", r"kayak(?:ing)?", r"paddl(?:e|ing)", r"bike rides?", r"cycling",
        r"fun runs?", r"5k", r"10k", r"pumpkins?", r"corn maze", r"farms?", r"orchards?",
        r"stargazing", r"tide ?pools?", r"picnics?", r"wildlife", r"boating",
    ),
    "arts": _words(
        r"exhibits?", r"exhibitions?", r"galler(?:y|ies)", r"museums?", r"art walks?", r"artwalk",
        r"open studios?", r"studio tours?", r"authors?", r"readings?", r"books?", r"lectures?",
        r"talks?", r"conversations?", r"panels?", r"poetry", r"literary", r"arts?", r"artists?",
        r"science", r"history", r"civics", r"seminars?",
    ),
}


def _norm(value: str) -> str:
    return clean_inline(value).casefold()


def is_noise(event: Event, config: SourceConfig) -> bool:
    excluded = {_norm(name) for name in config.exclude_categories}
    if any(_norm(name) in excluded for name in event.raw_categories):
        return True
    if NOISE.search(event.title) or any(NOISE.search(name) for name in event.raw_categories):
        return True
    return _norm(event.location_text or "") in ONLINE_LOCATIONS


def categorize(event: Event) -> str:
    texts = (
        (event.title, TITLE_WEIGHT),
        (" | ".join(event.raw_categories), OTHER_WEIGHT),
        (event.summary or "", OTHER_WEIGHT),
    )
    scores = {name: 0 for name in TYPE_ORDER}
    for text, weight in texts:
        for name, pattern in TYPE_PATTERNS.items():
            scores[name] += min(len(pattern.findall(text)), MAX_HITS_PER_TEXT) * weight
    best = max(TYPE_ORDER, key=lambda name: (scores[name], -TYPE_ORDER.index(name)))
    return best if scores[best] > 0 else "other"
