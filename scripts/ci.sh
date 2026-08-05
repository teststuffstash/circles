#!/usr/bin/env bash
# ci.sh — the circles CI gate.
#
# Single fail-fast command. This is the *seam*: the GitHub Actions workflow (and any future
# runner — Blacksmith/Chainguard) just calls `devbox run ci`, so the logic + tool versions live
# here / in devbox.json, not in CI YAML. Run it locally the same way: `devbox run ci`.
#
# Vanilla stage (new-stack bootstrap): the chart IS the product — the gate is chart validation
# + chart unit tests. When the real product shape lands via specs, its lint/test steps are ADDED
# here (this file is the one place the gate grows).
#
# First growth (issue #1 weave): the spec tree is now a contract with mechanical conventions,
# so it gets a gate. Product lint/tests follow when product code lands.
set -euo pipefail

bash scripts/lint-specs.sh
bash scripts/validate-chart.sh
bash scripts/test-chart.sh

# ── bake resolution + validation unit tests ─────────────────────────────────
echo "==> bake unit tests (pytest)"
uv run python -m pytest tests/ -q --tb=short
