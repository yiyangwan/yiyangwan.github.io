#!/usr/bin/env bash
# Commit around-seattle.json to the data branch. Never touches main and never force-pushes.
set -euo pipefail

src="${1:?usage: publish.sh PATH_TO_JSON}"
branch="${AROUND_SEATTLE_BRANCH:-around-seattle-data}"
remote="${AROUND_SEATTLE_REMOTE:-origin}"
file="around-seattle.json"

if [ ! -s "$src" ]; then
  echo "error: $src is missing or empty" >&2
  exit 1
fi

work="$(mktemp -d)"
cleanup() { git worktree remove --force "$work" >/dev/null 2>&1 || true; rm -rf "$work"; }
trap cleanup EXIT

if git ls-remote --exit-code --heads "$remote" "$branch" >/dev/null 2>&1; then
  git fetch --quiet --depth=1 "$remote" "$branch"
  git worktree add --quiet --detach "$work" FETCH_HEAD
else
  git worktree add --quiet --detach "$work" HEAD
  git -C "$work" checkout --quiet --orphan "$branch"
  git -C "$work" rm -r -q --cached . >/dev/null
  git -C "$work" clean -fdq
fi

cp "$src" "$work/$file"
cat > "$work/README.md" <<'EOF'
Generated data for https://yiyangwan.github.io/around-seattle/.
Written every morning by .github/workflows/around-seattle.yml on main. Do not edit by hand.
EOF

git -C "$work" add "$file" README.md
if git -C "$work" diff --cached --quiet; then
  echo "no changes to publish"
  exit 0
fi
git -C "$work" -c user.name="github-actions[bot]" \
  -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
  commit --quiet -m "data: refresh $file ($(date -u +%Y-%m-%dT%H:%MZ))"
git -C "$work" push --quiet "$remote" "HEAD:refs/heads/$branch"
echo "published to $branch"
