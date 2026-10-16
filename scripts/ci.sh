#!/usr/bin/env -S bash -euo pipefail
# ci.sh — CI entry point for the circles project
cd "$(dirname "$0")/.."

# Repo-local Allure results (gitignored, wiped here): the evidence run at the end of this script
# reads them, and the CI job uploads them. Repo-local, so two checkouts never share a dir.
ALLURE_RESULTS=allure-results
rm -rf "$ALLURE_RESULTS"

echo "=== validate-chart ==="
./scripts/validate-chart.sh

echo "=== test-chart ==="
./scripts/test-chart.sh

echo "=== specs-build ==="
./scripts/specs-build.sh

echo "=== bake unit tests (with Allure evidence) ==="
uv run --frozen pytest tests/ -v --tb=short --alluredir="$ALLURE_RESULTS"

echo "=== bake artifact-schema check ==="
# Bake the fixture through the real entry point, then validate the written data.json against the
# contract page's machine half (specs/data/data-json.schema.json — RULES rule 7). The bake already
# refuses to write an artifact that fails it; this re-reads what actually landed on disk.
uv run --frozen python -m bake \
  --config fixtures/alex/circles.yaml \
  --out /tmp/circles-bake-test \
  --reference-date 2026-08-03

uv run --frozen python -c "
import json, sys, jsonschema
schema = json.load(open('specs/data/data-json.schema.json'))
art = json.load(open('/tmp/circles-bake-test/data.json'))
errors = [f'{\"/\".join(map(str, e.absolute_path)) or \"<root>\"}: {e.message}'
          for e in jsonschema.Draft202012Validator(schema).iter_errors(art)]
# Not shape but phase: a bake without --stale-after-hours (P0) declares no cadence.
if art['stale_after_hours'] is not None:
    errors.append(f'stale_after_hours: expected None, got {art[\"stale_after_hours\"]}')
for e in errors:
    print(f'  FAIL: {e}', file=sys.stderr)
if errors:
    sys.exit(1)
print('  artifact schema check (data-json.schema.json): PASS')
"

echo "=== lint-specs ==="
./scripts/lint-specs.sh

echo "=== page render test ==="
# Bake the page and verify it produces both files
rm -rf /tmp/circles-bake-test
uv run --frozen python -m bake \
  --config fixtures/alex/circles.yaml \
  --out /tmp/circles-bake-test \
  --reference-date 2026-08-03

# Both files exist? (CIR-BAKE-SELF-CONTAINED)
if [ ! -f /tmp/circles-bake-test/data.json ]; then
  echo "FAIL: data.json not produced" >&2
  exit 1
fi
if [ ! -f /tmp/circles-bake-test/index.html ]; then
  echo "FAIL: index.html not produced" >&2
  exit 1
fi
echo "  both artifacts produced: PASS"

# Inlined data equals the file (CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file)
uv run --frozen python -c "
import json, sys
with open('/tmp/circles-bake-test/data.json') as f:
    file_data = json.load(f)
with open('/tmp/circles-bake-test/index.html') as f:
    html = f.read()
# Extract the JSON from the script tag
marker = '<script id=\"artifact-data\" type=\"application/json\">'
start = html.find(marker)
if start < 0:
    print('FAIL: artifact data script tag not found in index.html', file=sys.stderr)
    sys.exit(1)
start = html.index('>', start) + 1
end = html.index('</script>', start)
inlined = json.loads(html[start:end].strip())
if inlined != file_data:
    print('FAIL: inlined data does not match data.json', file=sys.stderr)
    sys.exit(1)
print('  inlined-data-equals-the-file: PASS')
"

echo "=== asset budget gate (CIR-PROC-GATE#gate-asset-budget) ==="
SIZE=$(stat -f%z /tmp/circles-bake-test/index.html 2>/dev/null || stat --format=%s /tmp/circles-bake-test/index.html 2>/dev/null)
if [ -z "$SIZE" ]; then SIZE=$(wc -c < /tmp/circles-bake-test/index.html | tr -d ' '); fi
echo "  index.html: ${SIZE} bytes"
if [ "$SIZE" -gt 256000 ]; then
  echo "FAIL: index.html (${SIZE} bytes) exceeds 250 KB budget" >&2
  exit 1
fi
echo "  asset-budget: PASS"

echo "=== no-external-origins gate (CIR-PROC-GATE#gate-no-external-origins) ==="
# Check for any references to external hosts (http:// or https://) in the built page
# that are NOT the page's own origin (we allow nothing — no-egress means no external
# requests at all, not even to ourselves which doesn't apply for file://)
EXTERNAL_REFS=$(grep -cP 'https?://' /tmp/circles-bake-test/index.html || true)
# The inlined data.json does NOT contain any URLs by default for the fixture, but check anyway
# We expect zero non-document external requests
# The only http:// should be in specifically allowed patterns (none at P0)
# Actually let's parse properly
uv run --frozen python -c "
import re, sys
with open('/tmp/circles-bake-test/index.html') as f:
    html = f.read()
# Find all http/https references (allow w3.org SVG namespace — it is a local identifier)
urls = re.findall(r'https?://[^\"\\'\\s<>]+', html)
external = [u for u in urls if 'w3.org' not in u]
if external:
    print(f'FAIL: found external URL(s) in page: {external}', file=sys.stderr)
    sys.exit(1)
print('  no-external-origins: PASS')
"

echo "=== page renders from file:// test ==="
uv run --frozen python -c "
import sys
with open('/tmp/circles-bake-test/index.html') as f:
    html = f.read()
# Check that the SVG contains the expected lights
checks = [
    ('self/sleep', 'self/sleep'),
    ('self/labs', 'self/labs'),
    ('self/exercise', 'self/exercise'),
    ('partner/date-night', 'partner/date-night'),
    ('children/nova', 'children/nova'),
    ('children/kit', 'children/kit'),
    ('wider/friends', 'wider/friends'),
    ('wider/plants', 'wider/plants'),
    ('ok', 'status word ok'),
    ('attention', 'status word attention'),
    ('act', 'status word act'),
    ('unmonitored', 'status word unmonitored'),
    ('not evaluated', 'grey reason text'),
    ('by-choice', 'by-choice reference'),
]
for needle, label in checks:
    if needle not in html:
        print(f'FAIL: expected \"{needle}\" ({label}) not found in index.html', file=sys.stderr)
        sys.exit(1)
print('  page-content-check: PASS')
"

# Clean up
rm -rf /tmp/circles-bake-test

echo ""
echo "=== test-system (skippable: set CIRCLES_SYSTEM_TEST_SKIP=1) ==="
./scripts/test-system.sh

echo ""
echo "=== evidence (devbox run evidence over the unit results) ==="
# allure-results/ → allure-evidence/ (the reviewer pack) + specs/evidence/ (the fragments the
# specs site transcludes). The browser tier's results join in CI's evidence job (#103 PR 2).
./scripts/evidence.sh "$ALLURE_RESULTS"
