"""Local preview: build the site, serve it with a data file, and capture headless Chrome screenshots.

    python -m around_seattle.preview --data /tmp/around-seattle-live.json --out /tmp/around-preview
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SIZES = {"phone": (390, 2600), "desktop": (1280, 2600)}
# Screenshots fire before CSS transitions finish (the virtual time budget does not drive them), so the captures take
# the page's reduced-motion path and show the settled sky and fog instead of the first frames of the fade.
CHROME_FLAGS = ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--virtual-time-budget=10000",
                "--force-prefers-reduced-motion"]
# Headless Chrome lays pages out at least this wide whatever --window-size says, then crops the screenshot. Narrower
# sizes load the page in a same-origin iframe of the exact size instead, so the phone capture is a real 390px layout.
MIN_WINDOW_WIDTH = 500
FRAME = ('<!doctype html><meta charset="utf-8"><title>Preview frame</title>'
         '<style>html, body {{ margin: 0; }} iframe {{ display: block; border: 0; }}</style>'
         '<iframe src="{src}" width="{width}" height="{height}" title="Preview"></iframe>\n')
# Chrome's log gives every console line the same level, so the served copy of the page records its own errors: any
# console.error call, uncaught error, unhandled rejection, or failed load lands on <html data-preview-errors>, which
# the DOM dump keeps.
ERROR_HOOK = """<script>(() => {
  const seen = [];
  const note = (text) => {
    seen.push(String(text).slice(0, 300));
    document.documentElement.setAttribute("data-preview-errors", JSON.stringify(seen));
  };
  const original = console.error;
  console.error = function (...args) { note(args.map(String).join(" ")); return original.apply(this, args); };
  addEventListener("error", (event) => note(event.target instanceof Element
    ? `Failed to load ${event.target.src || event.target.href || event.target.tagName}` : `Uncaught ${event.message}`),
    true);
  addEventListener("unhandledrejection",
    (event) => note(`Uncaught (in promise) ${event.reason?.stack ?? event.reason}`));
})();</script>"""
TAIL = 2000


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def variants(data: dict) -> dict[str, dict]:
    stale = (datetime.now(timezone.utc) - timedelta(days=3)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "normal": data,
        "no-weather": {**data, "weather": None},
        "stale": {**data, "generatedAt": stale},
        "empty": {**data, "events": [], "seasonal": []},
    }


def capture_url(site: Path, url: str, name: str, width: int, height: int) -> str:
    """Return the URL to screenshot at this size: the page itself, or a frame page holding it at the exact width."""
    if width >= MIN_WINDOW_WIDTH:
        return url
    frame = site / "around-seattle" / f"dev-frame-{name}.html"
    frame.write_text(FRAME.format(src=html.escape(url), width=width, height=height), encoding="utf-8")
    return url.split("/around-seattle/")[0] + f"/around-seattle/{frame.name}"


def add_error_hook(page: Path) -> None:
    text = page.read_text(encoding="utf-8")
    if "<head>" not in text:
        raise SystemExit(f"cannot add the error hook: no <head> in {page}")
    page.write_text(text.replace("<head>", "<head>" + ERROR_HOOK, 1), encoding="utf-8")


def page_errors(dom: str) -> list[str]:
    match = re.search(r'<html[^>]*\sdata-preview-errors="([^"]*)"', dom)
    return json.loads(html.unescape(match.group(1))) if match else []


def chrome(*args: str) -> subprocess.CompletedProcess:
    binary = shutil.which("google-chrome") or shutil.which("chromium") or "google-chrome"
    try:
        return subprocess.run([binary, *CHROME_FLAGS, *args], capture_output=True, text=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess([binary, *args], returncode=-1, stdout="", stderr=str(error))


def build_site(site: Path) -> int:
    command = ["bundle", "exec", "jekyll", "build", "--config", "_config.yml,_config.dev.yml", "-d", str(site)]
    build = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if build.returncode != 0:
        print(f"jekyll build failed with exit code {build.returncode}:", file=sys.stderr)
        print((build.stdout + build.stderr)[-TAIL:], file=sys.stderr)
    return build.returncode


def capture(name: str, url: str, site: Path, out: Path) -> list[str]:
    """Save the phone and desktop screenshots and the DOM dump for one variant; return any failures."""
    failures = []
    for label, (width, height) in SIZES.items():
        shot = out / f"{name}-{label}.png"
        shot.unlink(missing_ok=True)
        target = capture_url(site, url, f"{name}-{label}", width, height)
        result = chrome(f"--window-size={width},{height}", f"--screenshot={shot}", target)
        if result.returncode != 0 or not shot.exists():
            failures.append(f"{shot.name}: chrome exit {result.returncode}: {result.stderr[-TAIL:].strip()}")
    dom = chrome("--dump-dom", url)
    if dom.returncode != 0 or "<html" not in dom.stdout:
        failures.append(f"{name}.html: chrome exit {dom.returncode}: {dom.stderr[-TAIL:].strip()}")
    (out / f"{name}.html").write_text(dom.stdout, encoding="utf-8")
    errors = page_errors(dom.stdout)
    print(f"{name}: {dom.stdout.count('class=\"around-ev ')} items rendered; console errors: {len(errors)}")
    for line in errors[:5]:
        print("   ", " ".join(line.split())[:200])
    return failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Preview /around-seattle/ locally with headless Chrome.")
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args(argv)
    site = args.out / "site"
    args.out.mkdir(parents=True, exist_ok=True)
    if build_site(site) != 0:
        return 1
    add_error_hook(site / "around-seattle" / "index.html")
    data = json.loads(args.data.read_text(encoding="utf-8"))
    for name, variant in variants(data).items():
        (site / "around-seattle" / f"dev-{name}.json").write_text(json.dumps(variant), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(QuietHandler, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    failures = []
    try:
        for name in [*variants(data), "error"]:
            query = f"?data=/around-seattle/dev-{name}.json" if name != "error" else "?data=/around-seattle/missing.json"
            failures += capture(name, f"http://localhost:{args.port}/around-seattle/{query}", site, args.out)
    finally:
        server.shutdown()
    for failure in failures:
        print(f"chrome failed: {failure}", file=sys.stderr)
    print(f"screenshots and DOM dumps in {args.out}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
