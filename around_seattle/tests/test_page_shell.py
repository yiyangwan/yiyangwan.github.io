import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
PAGE = (REPO / "_pages" / "around-seattle.html").read_text(encoding="utf-8") if (REPO / "_pages" / "around-seattle.html").exists() else ""
ICONS = REPO / "_includes" / "around-seattle" / "weather-icons.svg"
CONDITIONS = ["clear", "partly", "mostly-cloudy", "cloudy", "fog", "smoke", "rain", "snow", "storm"]


def test_page_has_every_hook_app_needs():
    for hook in ["id=\"around\"", "data-src=", "data-fallback-src=", "data-sky=\"loading\"", "id=\"around-headline\"",
                 "id=\"around-forecast\"", "id=\"around-week\"", "id=\"around-filters\"", "id=\"around-status\"",
                 "id=\"around-notice\"", "id=\"around-today\"", "id=\"around-weekend\"", "id=\"around-weekend-h\"",
                 "id=\"around-coming\"", "id=\"around-further\"", "id=\"around-season\"",
                 "id=\"around-source-links\"", "id=\"around-footer\"", "permalink: /around-seattle/"]:
        assert hook in PAGE, hook
    assert sorted(re.findall(r'name="type" value="([a-z-]+)"', PAGE)) == sorted(
        ["festival", "music", "market", "outdoors", "arts"])
    assert re.findall(r'name="region" value="([a-z]+)"', PAGE) == ["all", "seattle", "eastside"]



def test_root_opts_out_of_mathjax_in_markup():
    root = re.search(r'<div class="([^"]*)" id="around"', PAGE)
    assert root, "root element"
    assert {"tex2jax_ignore", "mathjax_ignore"} <= set(root.group(1).split())

def test_weather_sprite_has_a_symbol_per_condition():
    ids = re.findall(r'<symbol id="wx-([a-z-]+)"', ICONS.read_text(encoding="utf-8"))
    assert sorted(ids) == sorted(CONDITIONS)


def test_nav_has_the_tab_after_cv():
    nav = yaml.safe_load((REPO / "_data" / "navigation.yml").read_text(encoding="utf-8"))["main"]
    titles = [link["title"] for link in nav]
    assert titles[-1] == "Around Seattle"
    assert titles[-2] == "CV"
    assert nav[-1]["url"] == "/around-seattle/"
