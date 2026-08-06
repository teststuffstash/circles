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
