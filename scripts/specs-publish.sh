#!/usr/bin/env bash
# Publish the browsable specs site to the `circles-specs` bucket, served by the circles gateway
# (ADR-092 subdomain delegation):
#
#   master runs (SITE_PREFIX empty) → bucket root  → https://specs.circles.teststuff.net
#   PR runs   (SITE_PREFIX=pr-<N>)  → pr-<N>/      → https://specs-<N>.circles.teststuff.net
#     (the per-PR HTTPRoute in circles-iac rewrites host → circles-specs + path → /pr-<N>/;
#      created/removed by .github/workflows/specs-pr-site.yaml via scripts/specs-pr-route.sh)
#
# Infra: bucket + writer grant in circles-iac circles/infra/specs-workspace.yaml; gateway +
# routes in circles/infra/gateway.yaml + httproute-specs.yaml (same repo).
#
# Soft-skips when creds are absent (local runs, forks) — oracle-fleet convention.
set -euo pipefail
cd "$(dirname "$0")/.."
# Parallel upload path (oracle-fleet #129 lesson): small-object PUTs go out concurrently
# instead of one-per-second serial against Garage's replicated fsync.
source scripts/lib/s3-publish.sh

if [ -z "${SPECS_S3_ACCESS_KEY_ID:-}" ] || [ -z "${SPECS_S3_SECRET_ACCESS_KEY:-}" ]; then
  echo "specs-publish: no S3 credentials in env — skipping (local run?)"
  exit 0
fi
ENDPOINT="${SPECS_S3_ENDPOINT:-https://s3.teststuff.net}"
BUCKET=circles-specs
PREFIX="${SITE_PREFIX:-}"

bash scripts/specs-build.sh

echo "== upload =="
s3_publish_alias specs "$ENDPOINT" "$SPECS_S3_ACCESS_KEY_ID" "$SPECS_S3_SECRET_ACCESS_KEY"
if [ -n "$PREFIX" ]; then
  # A PR prefix is wholly owned by its PR: --remove keeps it an exact mirror of this build.
  s3_publish_mirror --overwrite --remove specs-site/ "specs/$BUCKET/$PREFIX/"
  echo "published: https://specs-${PREFIX#pr-}.circles.teststuff.net/  (bucket $BUCKET/$PREFIX via $ENDPOINT)"
else
  # Bucket root also holds the pr-*/ prefixes — NEVER --remove here.
  s3_publish_mirror --overwrite specs-site/ "specs/$BUCKET/"
  echo "published: https://specs.circles.teststuff.net/  (bucket $BUCKET via $ENDPOINT)"
fi
