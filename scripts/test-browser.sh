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
#   PLAYWRIGHT_IMAGE        — docker runner image (default: mcr.microsoft.com/playwright/python:v<pin>,
#                             <pin> = the `playwright==` pin in pyproject.toml's `browser` group — ONE
#                             source, so a Renovate bump of the pip pin moves the image with it and
#                             the local and docker runners never test different browsers). The pip
#                             `playwright` installed in the container is derived from the image's
#                             `v<version>` tag — the image ships browsers but NOT the pip package
#                             (platform-verified 2026-08-30)
#   REGISTRY_MIRROR_MCR     — mcr.microsoft.com mirror (default: http://192.168.40.31, the LAN VIP
#                             per homelab SERVICES.md §Registry mirrors, ADR-091); the image ref is
#                             rewritten to <mirror-host>/<path>. REGISTRY_MIRROR_NONE=1 pulls upstream.
#
# The script bakes the fixture person at the fixture reference date (2026-08-03) into a temp
# dir, writes a second page variant with exactly 2 warnings (the artifact's own warnings,
# sliced — CIR-PROC-TEST-FIXTURES) and the stale-threshold variants (index-stale*.html, the
# fixture with stale_after_hours: 36), serves them to the browser via tests/browser/conftest.py
# (real HTTP, not file://) and runs pytest tests/browser with Allure raw results in
# allure-results-browser/ (repo-local, gitignored, wiped per run). Results are uuid-named files:
# copy this dir and the unit tier's allure-results/ into one dir and pass it to
# `devbox run evidence -- <merged> <out>` for the whole-suite evidence (scripts/evidence.sh).
#
# Requirements evidenced (system tier):
#   CIR-RENDER-ONE-SCREEN            (all 4 rows)
#   CIR-RENDER-REFERENCE-VIEWPORT    (both rows)
#   CIR-RENDER-A4#print-single-a4-portrait, #print-margins-are-declared, #print-chrome-complete
#   CIR-BAKE-STALE-SELF, CIR-RENDER-STALE-MARK (all rows)
#   the render rows of tests/browser/test_render_rows.py (keyboard, hover, click, palette,
#   no-JS, legend, summary, grey, status encoding, chrome, a11y table, stamp, egress, …)

cd "$(dirname "$0")/.."

# devbox↔uv seam: pin uv to the project venv before any `uv run` (homelab
# docs/patterns/python-stack.md, the fleet#316 scar).
export UV_PROJECT_ENVIRONMENT=.venv

REFERENCE_DATE="2026-08-03"
RUNNER="${CIRCLES_BROWSER_RUNNER:-auto}"
PW_PIN=$(sed -nE 's/^[[:space:]]*"playwright==([0-9.]+)".*/\1/p' pyproject.toml)
[ -n "$PW_PIN" ] || { echo "ERROR: no playwright==<version> pin in pyproject.toml" >&2; exit 1; }
IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright/python:v${PW_PIN}}"
EVIDENCE_DIR=allure-results-browser

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

# The evaluated variant: the same fixture baked the way the nightly bake runs it (--evaluate):
# its freshness/command adapters resolve, so self/sleep carries the guardrail + last-data
# detail line of CIR-RENDER-HOVER#hover-full-line and the artifact has no warnings
# (CIR-RENDER-CHROME#chrome-banner-hidden-when-clean). tests/browser/test_render_rows.py.
uv run --frozen python -m bake \
  --config fixtures/alex/circles.yaml \
  --out "$BAKE_OUT/evaluated" \
  --reference-date "$REFERENCE_DATE" --evaluate | sed 's/^/  /'
cp "$BAKE_OUT/evaluated/index.html" "$BAKE_OUT/index-evaluated.html"
echo "  Wrote $BAKE_OUT/index-evaluated.html (--evaluate)"

# The 2-warnings variant: the same artifact with its own warnings sliced to exactly two
# (CIR-RENDER-ONE-SCREEN#one-screen-with-warnings, tests/browser/test_one_screen.py).
uv run --frozen python - "$BAKE_OUT" "$REFERENCE_DATE" <<'PY'
import dataclasses
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

# The stale-threshold variants (CIR-BAKE-STALE-SELF, CIR-RENDER-STALE-MARK): the fixture
# artifact as baked above (generated_at 2026-08-03T02:00:00Z) with the cadence the P1
# nightly bake will declare — stale_after_hours: 36. Fresh vs stale is decided by the
# browser clock the test sets, not by the bytes.
fixture = add_capacity_warnings(resolve(
    config, reference_date=reference_date,
    generated_at=datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc),
))
# P0 as baked (stale_after_hours: null), at the same fixed generated_at so the test clock
# can be set relative to it (index.html carries the wall-clock bake time).
assert fixture["stale_after_hours"] is None
path = out / "index-no-threshold.html"
path.write_text(render_page(fixture), encoding="utf-8")
print(f"  Wrote {path} (stale_after_hours: null)")
path = out / "index-stale.html"
path.write_text(render_page({**fixture, "stale_after_hours": 36}), encoding="utf-8")
print(f"  Wrote {path} (stale_after_hours: 36)")
# A second cadence, so a threshold hard-coded in the page cannot pass for one read from the
# artifact (CIR-BAKE-STALE-SELF#threshold-comes-from-the-artifact).
path = out / "index-stale-72.html"
path.write_text(render_page({**fixture, "stale_after_hours": 72}), encoding="utf-8")
print(f"  Wrote {path} (stale_after_hours: 72)")

# Manual-only: the same config with every non-`manual:` item dropped
# (CIR-BAKE-STALE-SELF#manual-items-are-stale-too).
manual_rings = tuple(
    dataclasses.replace(ring, items=tuple(
        i for i in ring.items if i.adapter is not None and i.adapter.kind == "manual"))
    for ring in config.rings
)
manual_config = dataclasses.replace(config, rings=tuple(r for r in manual_rings if r.items))
manual = resolve(
    manual_config, reference_date=reference_date,
    generated_at=datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc),
)
path = out / "index-stale-manual.html"
path.write_text(render_page({**manual, "stale_after_hours": 36}), encoding="utf-8")
print(f"  Wrote {path} (manual items only, stale_after_hours: 36)")

# Only-green: the same config with every item but the `manual: green` ones dropped
# (CIR-RENDER-LEGEND#legend-all-four — "artifact with only green items").
green_rings = tuple(
    dataclasses.replace(ring, items=tuple(
        i for i in ring.items
        if i.adapter is not None and i.adapter.kind == "manual" and i.adapter.raw.get("manual") == "green"))
    for ring in config.rings
)
green = resolve(
    dataclasses.replace(config, rings=tuple(r for r in green_rings if r.items)),
    reference_date=reference_date,
    generated_at=datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc),
)
assert {i["status"] for r in green["rings"] for i in r["items"]} == {"green"}
path = out / "index-only-green.html"
path.write_text(render_page(add_capacity_warnings(green)), encoding="utf-8")
print(f"  Wrote {path} (manual: green items only)")

# The click-destination rows (CIR-RENDER-CLICK, fixtures/click-destinations.yaml): each row's
# `item` spliced into a one-ring config for the fixture person — the same splice the table's
# header describes — one page per row: index-click-<row_id>.html.
import tempfile
import yaml
table = yaml.safe_load(Path("fixtures/click-destinations.yaml").read_text(encoding="utf-8"))
for row in table["rows"]:
    one_ring = {"person": table["person"], "rings": [{**table["ring"], "items": [row["item"]]}]}
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "circles.yaml"
        cfg.write_text(yaml.dump(one_ring, allow_unicode=True), encoding="utf-8")
        art = add_capacity_warnings(resolve(
            load_config(cfg), reference_date=reference_date,
            generated_at=datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc),
        ))
    path = out / f"index-click-{row['row_id']}.html"
    path.write_text(render_page(art), encoding="utf-8")
    print(f"  Wrote {path} (click row {row['row_id']})")

# The geometry/capacity variants (CIR-RENDER-CAPACITY, -MIN-ARC, -ARC-SHARE, -RING-PARTITION;
# tests/browser/test_render_rows.py TestCapacity/TestMinArc/TestArcShare/TestPartition): the
# fixture's circles.yaml mutated as a dict, baked from a copy of the world dir (so its notes
# resolve) at the fixed generated_at. Extra items are `manual: green`, labelled "Extra <n>";
# extras in a ring that declares shares (children) declare share 0.5, so no variant gains a
# mixed-shares warning it did not ask for.
import copy
import re
import shutil

ALEX = yaml.safe_load(Path("fixtures/alex/circles.yaml").read_text(encoding="utf-8"))
GENERATED_AT = datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc)


def ring_of(data, ring_id):
    return next(r for r in data["rings"] if r["id"] == ring_id)


def extras(n, start=1, share=None):
    out_items = []
    for k in range(start, start + n):
        extra = {"id": f"extra-{k}", "label": f"Extra {k}", "status": {"manual": "green"}}
        if share is not None:
            extra["share"] = share
        out_items.append(extra)
    return out_items


def pad(ring_id, total):
    def edit(data):
        items = ring_of(data, ring_id)["items"]
        items.extend(extras(total - len(items)))
    return edit


def extra_rings(labels):
    def edit(data):
        for k, label in enumerate(labels, start=1):
            data["rings"].append({"id": f"extra-ring-{k}", "label": label,
                                  "items": [{"id": "one", "label": f"Area {k}",
                                             "status": {"manual": "green"}}]})
    return edit


def both(*edits):
    def edit(data):
        for e in edits:
            e(data)
    return edit


def bake_variant(name, why, edit):
    data = copy.deepcopy(ALEX)
    edit(data)
    with tempfile.TemporaryDirectory() as tmp:
        world = Path(tmp) / "alex"
        shutil.copytree("fixtures/alex", world)
        cfg = world / "circles.yaml"
        cfg.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        art = add_capacity_warnings(resolve(load_config(cfg), reference_date=reference_date,
                                            generated_at=GENERATED_AT))
    path = out / name
    path.write_text(render_page(art), encoding="utf-8")
    print(f"  Wrote {path} ({why})")


def set_items(ring_id, items):
    def edit(data):
        ring_of(data, ring_id)["items"] = items
    return edit


def set_shares(ring_id, shares, more=()):
    def edit(data):
        items = ring_of(data, ring_id)["items"]
        for it, share in zip(items, shares):
            it["share"] = share
        items.extend(more)
    return edit


def manual(ref, light):
    def edit(data):
        ring_id, item_id = ref.split("/")
        next(i for i in ring_of(data, ring_id)["items"] if i["id"] == item_id)["status"] = {"manual": light}
    return edit


# CIR-RENDER-CAPACITY rows
bake_variant("index-cap-at-limit.html", "6 rings; ① Self holds 8 items",
             both(pad("self", 8), extra_rings(["⑤ Community", "⑥ Work"])))
bake_variant("index-cap-7-rings.html", "7 rings",
             extra_rings(["⑤ Community", "⑥ Work", "⑦ Faith"]))
bake_variant("index-cap-9-items.html", "④ Wider life holds 9 items", pad("wider", 9))
bake_variant("index-cap-minimum.html", "1 ring (② Partner), 1 item",
             lambda d: d.update(rings=[ring_of(d, "partner")]))
bake_variant("index-cap-empty-ring.html", "② Partner holds zero items", set_items("partner", []))
# CIR-RENDER-RING-PARTITION#partition-ring-boundaries-visible: adjacent rings both 🟢
bake_variant("index-adjacent-green.html", "partner/date-night manual: green (② and ③ both all-green)",
             manual("partner/date-night", "green"))
# CIR-RENDER-ARC-SHARE#arc-share-mixed-weights and CIR-RENDER-MIN-ARC#min-arc-tiny-share-still-drawn
bake_variant("index-shares-2-1-1.html", "③ Children shares 2 / 1 / 1 (nova, kit, Extra 1)",
             set_shares("children", [2, 1], more=extras(1, share=1)))
bake_variant("index-shares-100-1.html", "③ Children shares 100 / 1 (nova, kit)",
             set_shares("children", [100, 1]))
# CIR-RENDER-MIN-ARC rows: one crowded ring (the outermost, ④ Wider life)
bake_variant("index-min-arc-30.html", "④ Wider life holds 30 items", pad("wider", 30))
bake_variant("index-min-arc-120.html", "④ Wider life holds 120 items", pad("wider", 120))
bake_variant("index-min-arc-mixed.html", "④ Wider life holds 20 items share 50 + 100 items share 1",
             set_items("wider", extras(20, share=50) + extras(100, start=21, share=1)))
bake_variant("index-min-arc-200.html", "④ Wider life holds 200 items", pad("wider", 200))

# CIR-RENDER-BOOT-FAILURE inputs: pages whose embedded payload is unusable. The fixture page as
# baked above at the fixed generated_at (index-no-threshold.html) is the base.
base = (out / "index-no-threshold.html").read_text(encoding="utf-8")
block = re.search(r'<script id="artifact-data" type="application/json">.*?</script>\n?', base, re.S)
assert block is not None
path = out / "index-boot-no-payload.html"
path.write_text(base.replace(block.group(0), ""), encoding="utf-8")
print(f"  Wrote {path} (the inlined payload block removed)")
# `rings: []` — the hand-edited artifact the bake would never emit, rendered by the page renderer.
path = out / "index-boot-empty-rings.html"
path.write_text(render_page({**fixture, "rings": []}), encoding="utf-8")
print(f"  Wrote {path} (artifact rings: [])")
PY

# ── step 2: run the browser tier ─────────────────────────────────────────────────────
rm -rf "$EVIDENCE_DIR" && mkdir -p "$EVIDENCE_DIR"
echo "==> step 2/3: pytest tests/browser ($RUNNER) — evidence: $EVIDENCE_DIR/"
# `-o addopts=` overrides pyproject's `--ignore=tests/browser` (which keeps the unit run
# in scripts/ci.sh from collecting this tier).
PYTEST_ARGS=(tests/browser -v --tb=short -p no:cacheprovider -o addopts= --alluredir "$EVIDENCE_DIR")

RC=0
if [ "$RUNNER" = "local" ]; then
  CIRCLES_PAGES_DIR="$BAKE_OUT" \
    uv run --frozen --group browser pytest "${PYTEST_ARGS[@]}" || RC=$?
else
  # The evidence stamp + executor (tests/conftest.py) are written INSIDE the container, where git
  # may be absent: hand it the head sha (CI's CIRCLES_HEAD_SHA, else the host checkout's HEAD) and
  # the run identity, or the browser results carry an empty stamp into the evidence job's merge.
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
  # pytest also loads tests/conftest.py (the unit tier's), which imports the project's runtime
  # deps — keep this list in step with pyproject.toml [project].dependencies.
  docker run --rm \
    -v "$PWD:/work" -w /work \
    -v "$BAKE_OUT:/pages:ro" \
    -e CIRCLES_PAGES_DIR=/pages \
    -e CIRCLES_HEAD_SHA="${CIRCLES_HEAD_SHA:-$(git rev-parse HEAD 2>/dev/null || true)}" \
    -e GITHUB_SERVER_URL -e GITHUB_REPOSITORY -e GITHUB_RUN_ID \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e PIP_ROOT_USER_ACTION=ignore \
    "$IMAGE_REF" \
    bash -c "pip install -q 'playwright==${PW_VERSION}' 'pytest==8.*' allure-pytest pypdf 'PyYAML>=6.0' tzdata \
      && { python -m pytest $(printf '%q ' "${PYTEST_ARGS[@]}"); rc=\$?; \
           chown -R $(id -u):$(id -g) $(printf '%q' "$EVIDENCE_DIR"); exit \$rc; }" || RC=$?
  # (the chown hands the results back to the invoking user: the next run wipes the dir)
fi

# ── step 3: verdict ──────────────────────────────────────────────────────────────────
echo "==> step 3/3: verdict"
if [ "$RC" -eq 0 ]; then
  echo "==> test-browser: ALL PASS (evidence: $EVIDENCE_DIR/)"
  exit 0
fi
echo "==> test-browser: FAILED (pytest exit $RC — evidence: $EVIDENCE_DIR/)" >&2
exit "$RC"
