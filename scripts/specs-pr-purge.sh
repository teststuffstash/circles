#!/usr/bin/env bash
# specs-pr-purge.sh <pr-number> — delete this PR's specs-site prefix (circles-specs/pr-<N>/)
# from the Garage specs bucket when the PR closes (specs-pr-site.yaml).
#
# rclone against an env-configured remote `specs:` (RCLONE_CONFIG_SPECS_* — no config file;
# Garage = region `garage`, path-style, see homelab SERVICES.md). A missing prefix purges
# clean (rc 0); rclone rc 3/4 (directory/file not found) = "already absent"; any other rc —
# auth, network, server error — fails the step.
set -euo pipefail

PR="${1:?usage: specs-pr-purge.sh <pr-number>}"
rc=0
rclone purge "specs:circles-specs/pr-${PR}/" || rc=$?
case "$rc" in
  0) echo "purged circles-specs/pr-${PR}/" ;;
  3|4) echo "prefix pr-${PR}/ already absent" ;;
  *) echo "rclone purge of circles-specs/pr-${PR}/ failed (rc ${rc})" >&2; exit "$rc" ;;
esac
