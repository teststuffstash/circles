#!/usr/bin/env -S bash -euo pipefail
# test-browser.sh — browser evidence gate (headless Chromium renders the baked page; measurable
# properties asserted — never screenshots). CIR-PROC-BROWSER-EVIDENCE, system tier (⚖-R48).
#
# Prerequisites: a browser runner — either a Docker daemon (the Microsoft Playwright image
# ships the browsers) or a local Playwright install in the `browser` dependency group with
# Chromium downloaded (`uv run --group browser playwright install chromium`).
#
# Environment:
#   CIRCLES_BROWSER_RUNNER  — auto|local|docker|skip (default: auto)
#                             auto: docker if `docker info` works, else local if the
#                             `browser` group imports playwright, else SKIPPED (exit 0)
#   PLAYWRIGHT_IMAGE        — docker runner image (default: mcr.microsoft.com/playwright/python:v1.62.0);
#                             the pip `playwright` pin is derived from its `v<version>` tag — the image
#                             ships browsers but NOT the pip package (platform-verified 2026-08-30)
#   REGISTRY_MIRROR_MCR     — mcr.microsoft.com mirror (default: http://192.168.40.31, the LAN VIP
#                             per homelab SERVICES.md §Registry mirrors, ADR-091); the image ref is
#                             rewritten to <mirror-host>/<path>. REGISTRY_MIRROR_NONE=1 pulls upstream.
#   CIRCLES_BROWSER_EVIDENCE_ROOT — where per-run evidence lands (default: browser-evidence/, gitignored)
#
# The script bakes the fixture person at the fixture reference date (2026-08-03) into a temp
# dir, writes a second page variant with exactly 2 warnings (the artifact's own warnings,
# sliced — CIR-PROC-TEST-FIXTURES), serves both to the browser via tests/browser/conftest.py
# (real HTTP, not file://) and runs pytest tests/browser with Allure raw results in
# browser-evidence/<timestamp>/.
#
# Requirements evidenced (system tier):
#   CIR-RENDER-ONE-SCREEN            (all 4 rows)
#   CIR-RENDER-REFERENCE-VIEWPORT    (both rows)
#   CIR-RENDER-A4#print-single-a4-portrait, #print-margins-are-declared, #print-chrome-complete

cd "$(dirname "$0")/.."

# devbox↔uv seam: pin uv to the project venv before any `uv run` (homelab
# docs/patterns/python-stack.md, the fleet#316 scar).
export UV_PROJECT_ENVIRONMENT=.venv

REFERENCE_DATE="2026-08-03"
RUNNER="${CIRCLES_BROWSER_RUNNER:-auto}"
IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright/python:v1.62.0}"
EVIDENCE_ROOT="${CIRCLES_BROWSER_EVIDENCE_ROOT:-browser-evidence}"
EVIDENCE_DIR="${EVIDENCE_ROOT}/$(date -u +%Y%m%dT%H%M%SZ)-$$"

# ── skip guard / runner selection (graceful skip keeps the gate usable everywhere) ─────
case "$RUNNER" in
  skip)
    echo "==> test-browser: SKIPPED (CIRCLES_BROWSER_RUNNER=skip)"
    exit 0
    ;;
  auto)
    if command -v docker &>/dev/null && docker info &>/dev/null; then
      RUNNER=docker
    elif uv run --frozen --group browser python -c "import playwright" &>/dev/null; then
      RUNNER=local
    else
      echo "==> test-browser: SKIPPED (no docker daemon and no local playwright — set CIRCLES_BROWSER_RUNNER=skip to suppress)"
      exit 0
    fi
    ;;
  local|docker) ;;
  *)
    echo "ERROR: CIRCLES_BROWSER_RUNNER=$RUNNER — expected auto|local|docker|skip" >&2
    exit 1
    ;;
esac
echo "==> test-browser: runner=$RUNNER"

# ── temp bake dir (cleaned up by trap) ───────────────────────────────────────────────
BAKE_OUT=$(mktemp -d /tmp/circles-browser-bake.XXXXXX)
cleanup() {
  set +e
  rm -rf "$BAKE_OUT"
}
trap cleanup EXIT

# ── step 1: bake the fixture person at the fixture reference date ────────────────────
echo "==> step 1/3: bake fixture (reference date $REFERENCE_DATE)"
uv run --frozen python -m bake \
  --config fixtures/alex/circles.yaml \
  --out "$BAKE_OUT" \
  --reference-date "$REFERENCE_DATE" | sed 's/^/  /'

# The 2-warnings variant: the same artifact with its own warnings sliced to exactly two —
# the construction tests/test_render.py::test_one_screen_with_warnings_proxy uses.
uv run --frozen python - "$BAKE_OUT" "$REFERENCE_DATE" <<'PY'
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from bake.config import load_config
from bake.render import add_capacity_warnings, render_page
from bake.resolve import resolve

out, reference_date = Path(sys.argv[1]), date.fromisoformat(sys.argv[2])
config = load_config(Path("fixtures/alex/circles.yaml"))
artifact = add_capacity_warnings(resolve(
    config, reference_date=reference_date,
    generated_at=datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc),
))
if len(artifact["warnings"]) < 2:
    sys.exit(f"fixture produced {len(artifact['warnings'])} warnings — need >= 2 to slice")
artifact = {**artifact, "warnings": artifact["warnings"][:2]}
path = out / "index-2-warnings.html"
path.write_text(render_page(artifact), encoding="utf-8")
print(f"  Wrote {path} ({len(artifact['warnings'])} warnings)")
PY

# ── step 2: run the browser tier ─────────────────────────────────────────────────────
mkdir -p "$EVIDENCE_DIR"
echo "==> step 2/3: pytest tests/browser ($RUNNER) — evidence: $EVIDENCE_DIR/"
# `-o addopts=` overrides pyproject's `--ignore=tests/browser` (which keeps the unit run
# in scripts/ci.sh from collecting this tier).
PYTEST_ARGS=(tests/browser -v --tb=short -p no:cacheprovider -o addopts= --alluredir "$EVIDENCE_DIR")

RC=0
if [ "$RUNNER" = "local" ]; then
  CIRCLES_PAGES_DIR="$BAKE_OUT" \
    uv run --frozen --group browser pytest "${PYTEST_ARGS[@]}" || RC=$?
else
  # Image ref through the LAN mirror unless disabled (same defaults as test-system.sh).
  IMAGE_REF="$IMAGE"
  if [ "${REGISTRY_MIRROR_NONE:-}" = "1" ]; then
    echo "  REGISTRY_MIRROR_NONE=1 — pulling $IMAGE upstream"
  else
    : "${REGISTRY_MIRROR_MCR:=http://192.168.40.31}"
    MIRROR_HOST="${REGISTRY_MIRROR_MCR#http://}"; MIRROR_HOST="${MIRROR_HOST#https://}"; MIRROR_HOST="${MIRROR_HOST%/}"
    IMAGE_REF="${MIRROR_HOST}/${IMAGE#mcr.microsoft.com/}"
    echo "  mirror: mcr.microsoft.com -> $REGISTRY_MIRROR_MCR ($IMAGE_REF)"
  fi
  # The image's browsers match the pip package of the same version — pin from the tag.
  PW_VERSION="${IMAGE##*:v}"
  docker run --rm \
    -v "$PWD:/work" -w /work \
    -v "$BAKE_OUT:/pages:ro" \
    -e CIRCLES_PAGES_DIR=/pages \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e PIP_ROOT_USER_ACTION=ignore \
    "$IMAGE_REF" \
    bash -c "pip install -q 'playwright==${PW_VERSION}' 'pytest==8.*' allure-pytest pypdf \
      && python -m pytest $(printf '%q ' "${PYTEST_ARGS[@]}")" || RC=$?
fi

# ── step 3: verdict ──────────────────────────────────────────────────────────────────
echo "==> step 3/3: verdict"
if [ "$RC" -eq 0 ]; then
  echo "==> test-browser: ALL PASS (evidence: $EVIDENCE_DIR/)"
  exit 0
fi
echo "==> test-browser: FAILED (pytest exit $RC — evidence: $EVIDENCE_DIR/)" >&2
exit "$RC"
