"""Text helpers: feed HTML to plain text, prices, contact scrubbing, and URL safety."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

_BLOCK_TAGS = frozenset({"br", "p", "div", "li", "ul", "ol", "tr", "h1", "h2", "h3", "h4", "h5", "h6"})
_SKIP_TAGS = frozenset({"script", "style"})
_SPACES = re.compile(r"[ \t ​]+")
_FREE = re.compile(r"^(?:free|free admission|free entry|no cost|\$?0(?:\.00)?)$", re.IGNORECASE)
_HAS_FREE = re.compile(r"\bfree\b", re.IGNORECASE)
_PAID = re.compile(r"\$\s*[1-9]")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
_MARKUP_RUN = re.compile(r"[*_]{2,}")
# Half of a UTF-16 pair, which a JSON "\ud83c" escape decodes to; UTF-8 cannot encode it, so writing the output fails.
_SURROGATES = re.compile(r"[\ud800-\udfff]")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(value: object) -> str:
    """Plain text with one line per block; entities decoded; blank lines and lone surrogates dropped."""
    if not value:
        return ""
    parser = _TextExtractor()
    parser.feed(_SURROGATES.sub("", str(value)))
    parser.close()
    lines = (_SPACES.sub(" ", line).strip() for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def clean_inline(value: object) -> str:
    """Single-line plain text, for titles, venues, and categories."""
    return " ".join(html_to_text(value).split())


def join_lines(value: object, sep: str = ", ") -> str:
    """Plain text with block breaks joined by sep, for addresses."""
    return sep.join(html_to_text(value).splitlines())


def truncate(text: str, limit: int = 240) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    base = cut[:space] if space > limit * 0.6 else text[:limit]
    return base.rstrip(" ,;:.-–—") + "…"


def parse_price(value: object) -> tuple[str | None, bool | None]:
    """Return (display price, free?) from a feed's free-text cost field."""
    text = clean_inline(value)
    if not text:
        return None, None
    if _FREE.match(text):
        return "Free", True
    if _HAS_FREE.search(text) and not _PAID.search(text):
        return truncate(text, 60), True
    if _PAID.search(text):
        return truncate(text, 60), False
    return truncate(text, 60), None


def scrub_contacts(text: str) -> str:
    """Remove email addresses and phone numbers (feeds often include staff contacts)."""
    return " ".join(_PHONE.sub(" ", _EMAIL.sub(" ", text)).split())


def tidy_summary(text: str) -> str:
    """Strip markdown-style emphasis runs (``** bold **``, ``__underline__``) and collapse whitespace."""
    return " ".join(_MARKUP_RUN.sub(" ", text).split())


def safe_url(value: object) -> str | None:
    """The URL if it is absolute http(s), otherwise None."""
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return None
    return candidate
