#!/usr/bin/env bash
# test-chart.sh — helm-unittest the chart (suites under chart/tests/). Installs the plugin into
# this devbox's helm if it's missing (idempotent), so it works on a cold CI runner too.
set -euo pipefail

if ! helm plugin list 2>/dev/null | grep -q '^unittest'; then
  echo "==> installing helm-unittest plugin"
  helm plugin install https://github.com/helm-unittest/helm-unittest --verify=false
fi

echo "==> helm unittest chart/"
helm unittest chart/
