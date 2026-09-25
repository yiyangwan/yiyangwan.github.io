import pytest

from around_seattle.text import (clean_inline, html_to_text, join_lines, parse_price, safe_url, scrub_contacts,
                                 tidy_summary, truncate)


def test_html_to_text_breaks_blocks_and_decodes_entities():
    raw = "<p>Brown&#8217;s &amp; Co</p><br>Line two<script>alert(1)</script><style>p{}</style>"
    assert html_to_text(raw) == "Brown’s & Co\nLine two"


def test_html_to_text_keeps_bare_angle_brackets_and_handles_empty():
    assert html_to_text("Kids <5 free") == "Kids <5 free"
    assert html_to_text(None) == ""
    assert html_to_text("") == ""


def test_clean_inline_and_join_lines():
    assert clean_inline("  Parks &amp; Recreation \n ") == "Parks & Recreation"
    assert join_lines("Ship Canal Trail<br>130 Nickerson Street Seattle WA 98109") == (
        "Ship Canal Trail, 130 Nickerson Street Seattle WA 98109")


def test_truncate_on_word_boundary():
    assert truncate("short") == "short"
    result = truncate("word " * 80, 40)
    assert len(result) <= 41
    assert result.endswith("…")
    assert not result[:-1].endswith(" ")


@pytest.mark.parametrize("raw, expected", [
    ("Free", ("Free", True)),
    ("free", ("Free", True)),
    ("0", ("Free", True)),
    ("$0.00", ("Free", True)),
    ("$22", ("$22", False)),
    ("$10 – $35 Sliding Scale", ("$10 – $35 Sliding Scale", False)),
    ("Free, donations welcome", ("Free, donations welcome", True)),
    ("Suggested donation", ("Suggested donation", None)),
    ("", (None, None)),
    (None, (None, None)),
])
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


def test_scrub_contacts_removes_emails_and_phones():
    text = "Questions? Email jane.doe@example.org or call 206-555-0100 today."
    assert scrub_contacts(text) == "Questions? Email or call today."


@pytest.mark.parametrize("raw, expected", [
    ("** 6:00 p.m. **", "6:00 p.m."),
    ("__Doors__  open   at 6", "Doors open at 6"),
    ("No markup here", "No markup here"),
    ("5 * 3 = 15", "5 * 3 = 15"),  # a single "*" is not a run
])
def test_tidy_summary_removes_markup_runs_and_collapses_whitespace(raw, expected):
    assert tidy_summary(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("https://example.org/a?b=1", "https://example.org/a?b=1"),
    ("http://example.org", "http://example.org"),
    ("  https://example.org  ", "https://example.org"),
    ("javascript:alert(1)", None),
    ("/relative/path", None),
    ("mailto:someone@example.org", None),
    ("", None),
    (None, None),
    (42, None),
])
def test_safe_url(raw, expected):
    assert safe_url(raw) == expected
