#!/usr/bin/env bash
#
# Compile the CV directly to files/yiyangwang_cv.pdf — the PDF the site links to.
# No manual copy/rename step: tectonic's output basename already matches the
# published filename, so it overwrites the live PDF in place.
#
# The previous published PDF is copied to CV/backups/ first, so a bad build can
# always be rolled back (files/ is git-tracked, CV/ is gitignored).
#
# Usage: ./CV/build.sh
set -euo pipefail

CV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$CV_DIR/.." && pwd)"
OUT_DIR="$REPO_ROOT/files"
BACKUP_DIR="$CV_DIR/backups"
PDF="$OUT_DIR/yiyangwang_cv.pdf"

command -v tectonic >/dev/null 2>&1 || {
  echo "error: tectonic not found. Install it (brew install tectonic) or compile" >&2
  echo "       CV/yiyangwang_cv.tex with xelatex -- the class needs fontspec." >&2
  exit 1
}

# Snapshot the currently published PDF before overwriting it.
if [[ -f "$PDF" ]]; then
  mkdir -p "$BACKUP_DIR"
  BACKUP="$BACKUP_DIR/yiyangwang_cv_$(date +%Y%m%d-%H%M%S).pdf"
  cp "$PDF" "$BACKUP"
  echo "backed up previous PDF -> ${BACKUP#$REPO_ROOT/}"
fi

# Build in a temp dir so a failed run can never leave a truncated PDF in files/.
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

# cd into CV/ so the class can resolve its relative font paths (fonts/georgia/...).
cd "$CV_DIR"
tectonic -X compile yiyangwang_cv.tex --outdir "$BUILD_DIR" --keep-logs

mv "$BUILD_DIR/yiyangwang_cv.pdf" "$PDF"
echo "wrote ${PDF#$REPO_ROOT/} ($(du -h "$PDF" | cut -f1))"
