#!/usr/bin/env bash
# Build the browsable specs site into specs-site/ — used by scripts/specs-publish.sh (upload)
# and runnable locally (devbox run specs-build) for a pre-push render check.
set -euo pipefail
cd "$(dirname "$0")/.."

# Stage the documentation roots at their repo paths (mkdocs refuses docs_dir: ".") so
# cross-tree links (specs/… ↔ docs/…) resolve as real pages. index.md is generated — this
# repo has no root README by design (CLAUDE.md is agent-facing, not site content).
rm -rf .site-src && mkdir .site-src
cp -r specs .site-src/
[ -d docs ] && cp -r docs .site-src/
{
  echo "# circles — specs & docs"
  echo
  echo "- [specs/](specs/index.html) — the product contract: requirement pages, decision tables, the ⚖ register (mkdocs renders README.md as index.html)"
  [ -d docs ] && echo "- [docs/](docs/) — working documents (arm comparisons, …)"
} > .site-src/index.md

# mkdocs via uv, not devbox: theme/extensions must live in the same python env as mkdocs,
# which the nix-packaged mkdocs can't host. EXACT pins — the mkdocs ecosystem forked in
# 2026-07 (mkdocs 2.0 vs properdocs); unpinned resolution can silently swap the engine under
# the site (rule inherited from oracle-fleet).
rm -rf specs-site
uv run --no-project --with mkdocs==1.6.1 --with mkdocs-material==9.7.6 \
  --with pymdown-extensions==11.0.1 mkdocs build --quiet

# Object-store hosting has no directory listings: give every output directory that lacks an
# index.html a minimal generated one so directory links resolve.
find specs-site -type d | while read -r d; do
  [ -f "$d/index.html" ] && continue
  {
    echo '<!doctype html><meta charset=utf-8><ul>'
    for f in "$d"/*; do b="$(basename "$f")"; echo "<li><a href=\"$b\">$b</a></li>"; done
    echo '</ul>'
  } > "$d/index.html"
done
echo "specs-site/ built"
