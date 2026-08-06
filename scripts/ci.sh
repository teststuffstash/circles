#!/usr/bin/env -S bash -euo pipefail
# ci.sh — CI entry point for the circles project
cd "$(dirname "$0")/.."

echo "=== validate-chart ==="
bash scripts/validate-chart.sh

echo "=== test-chart ==="
bash scripts/test-chart.sh

echo "=== lint-specs ==="
bash scripts/lint-specs.sh

echo "=== specs-build ==="
bash scripts/specs-build.sh

echo "=== bake unit tests ==="
uv run --frozen pytest tests/ -v --tb=short

echo "=== bake artifact-schema check ==="
# Build the artifact from the fixture and validate its structure
uv run --frozen python -m bake \
  --config fixtures/alex/circles.yaml \
  --out /tmp/circles-bake-test \
  --reference-date 2026-08-03

# Validate the artifact has the expected structure
uv run --frozen python -c "
import json, sys
with open('/tmp/circles-bake-test/data.json') as f:
    art = json.load(f)
errors = []
if art['version'] != 1: errors.append(f'version: expected 1, got {art[\"version\"]}')
if art['stale_after_hours'] is not None: errors.append(f'stale_after_hours: expected None, got {art[\"stale_after_hours\"]}')
if not isinstance(art['rings'], list): errors.append('rings: expected list')
if not isinstance(art['warnings'], list): errors.append('warnings: expected list')
for ring in art['rings']:
    for item in ring['items']:
        if item['status'] not in ('green','yellow','red','grey'):
            errors.append(f'{ring[\"id\"]}/{item[\"id\"]}: invalid status {item[\"status\"]}')
        if item['grey_reason'] not in (None, 'by-choice', 'by-failure', 'not-evaluated'):
            errors.append(f'{ring[\"id\"]}/{item[\"id\"]}: invalid grey_reason {item[\"grey_reason\"]}')
if errors:
    for e in errors: print(f'  FAIL: {e}', file=sys.stderr)
    sys.exit(1)
print('  artifact schema check: PASS')
"

# Clean up
rm -rf /tmp/circles-bake-test
