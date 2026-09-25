"""Local preview: build the site, serve it with a data file, and capture headless Chrome screenshots.

    python -m around_seattle.preview --data /tmp/around-seattle-live.json --out /tmp/around-preview
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
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


def chrome(*args: str) -> subprocess.CompletedProcess:
    binary = shutil.which("google-chrome") or shutil.which("chromium") or "google-chrome"
    return subprocess.run([binary, *CHROME_FLAGS, *args], capture_output=True, text=True, timeout=180, check=False)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Preview /around-seattle/ locally with headless Chrome.")
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args(argv)
    site = args.out / "site"
    args.out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["bundle", "exec", "jekyll", "build", "--config", "_config.yml,_config.dev.yml", "-d", str(site)],
                   cwd=REPO, check=True, capture_output=True)
    data = json.loads(args.data.read_text(encoding="utf-8"))
    for name, variant in variants(data).items():
        (site / "around-seattle" / f"dev-{name}.json").write_text(json.dumps(variant), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(QuietHandler, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for name in [*variants(data), "error"]:
            query = f"?data=/around-seattle/dev-{name}.json" if name != "error" else "?data=/around-seattle/missing.json"
            url = f"http://localhost:{args.port}/around-seattle/{query}"
            for label, (width, height) in SIZES.items():
                target = capture_url(site, url, f"{name}-{label}", width, height)
                chrome(f"--window-size={width},{height}", f"--screenshot={args.out / f'{name}-{label}.png'}", target)
            dom = chrome("--enable-logging=stderr", "--v=0", "--dump-dom", url)
            (args.out / f"{name}.html").write_text(dom.stdout, encoding="utf-8")
            errors = [line for line in dom.stderr.splitlines() if "Uncaught" in line or "CONSOLE" in line and "rror" in line]
            print(f"{name}: {dom.stdout.count('class=\"around-ev ')} items rendered; console errors: {len(errors)}")
            for line in errors[:5]:
                print("   ", line[:200])
    finally:
        server.shutdown()
    print(f"screenshots and DOM dumps in {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
