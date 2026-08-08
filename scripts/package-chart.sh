#!/usr/bin/env bash
# Package the circles Helm chart and push it to ghcr.io as an OCI artifact.
#
# The version comes from $VERSION (deploy.yaml’s calver-gsha version); chart version AND
# appVersion are both set to it, so chart : image : app commit all move in lockstep (the -g<sha>
# suffix carries the commit).
#
# CI: .github/workflows/deploy.yaml (calver-gsha on master push). Locally:
#   echo "$GHCR_TOKEN" | helm registry login ghcr.io -u <github-user> --password-stdin
#   VERSION=0.2.0 devbox run package-chart
set -euo pipefail
VERSION="${VERSION:?set VERSION (no leading v), e.g. VERSION=0.2.0}"
CHART_REPO="${CHART_REPO:-oci://ghcr.io/teststuffstash/charts}"

echo "==> helm package circles $VERSION (version + appVersion = $VERSION)"
helm package chart/ --version "$VERSION" --app-version "$VERSION"

echo "==> helm push → $CHART_REPO"
helm push "circles-${VERSION}.tgz" "$CHART_REPO"
echo "==> pushed $CHART_REPO/circles:$VERSION"
