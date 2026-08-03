#!/usr/bin/env bash
# Build the circles image and push it to ghcr.io — the canonical registry the homelab
# Deployment pulls (ghcr.io/teststuffstash/circles:<tag>). The image is amd64 (it
# runs in-cluster on x86), so a plain build on an amd64 host (pop-os) — no buildx/QEMU. This is
# the manual/off-cluster fallback; CI (.github/workflows/deploy.yaml) is the normal path.
# Run on the Docker host, from the repo root.
#
#   echo "$GHCR_TOKEN" | docker login ghcr.io -u <github-user> --password-stdin
#   devbox run build-image                            # or: CIRCLES_TAG=0.1.1 devbox run build-image
set -euo pipefail

IMG="${CIRCLES_IMAGE:-ghcr.io/teststuffstash/circles}"
TAG="${CIRCLES_TAG:-0.1.0}"

command -v docker >/dev/null || { echo "ERROR: docker not found — run on the Docker host (pop-os), not the jail."; exit 1; }

echo "==> building $IMG:$TAG (amd64)…"
docker build -t "$IMG:$TAG" -t "$IMG:latest" .
echo "==> pushing…"
docker push "$IMG:$TAG"
docker push "$IMG:latest"
echo "==> pushed $IMG:$TAG (+ :latest)"
