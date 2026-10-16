#!/usr/bin/env bash
# validate-chart.sh — helm lint + values.schema.json + kubeconform
#
# Runs as a single command. Exits non-zero on any failure.
# Intended for CI and local dev.

set -euo pipefail

CHART_DIR="${1:-chart}"
echo "==> helm lint ${CHART_DIR}"
helm lint "${CHART_DIR}" --strict

echo ""
echo "==> helm template (default values)"
RENDERED=$(mktemp /tmp/rendered.XXXXXX.yaml)
trap 'rm -f "${RENDERED}"' EXIT
helm template test-validate "${CHART_DIR}" > "${RENDERED}"

echo "==> kubeconform (strict)"
kubeconform -summary -strict "${RENDERED}"

echo ""
echo "==> helm template (existing-secret mode)"
RENDERED2=$(mktemp /tmp/rendered.XXXXXX.yaml)
trap 'rm -f "${RENDERED2}"' EXIT
helm template test-validate "${CHART_DIR}" \
  --set secret.create=false \
  --set secret.existingName="test-existing" > "${RENDERED2}"

echo "==> kubeconform (strict, existing-secret mode)"
kubeconform -summary -strict "${RENDERED2}"

echo ""
echo "==> helm template (deploy seam: bake.enabled + content.mode=volume)"
RENDERED3=$(mktemp /tmp/rendered.XXXXXX.yaml)
trap 'rm -f "${RENDERED}" "${RENDERED2}" "${RENDERED3}"' EXIT
helm template test-validate "${CHART_DIR}" \
  --set bake.enabled=true \
  --set content.mode=volume > "${RENDERED3}"

echo "==> kubeconform (strict, deploy-seam mode)"
kubeconform -summary -strict "${RENDERED3}"

echo ""
echo "✓ chart validation passed"