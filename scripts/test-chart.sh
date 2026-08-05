#!/usr/bin/env bash
# test-chart.sh — helm-unittest the chart (suites under chart/tests/).
#
# The plugin comes from devbox (nixpkgs kubernetes-helmPlugins.helm-unittest), NOT from a
# `helm plugin install` over the WAN. That fetch pulled ~23 MB from GitHub releases on EVERY run
# with --verify=false — unauthenticated third-party code into the gate that decides what merges —
# and it hangs, rather than fails, once agent-ride egress enforces its allowlist (homelab FU-130).
# nix installs plugins as a DIRECTORY, and helm discovers them by scanning $HELM_PLUGINS, so the
# devbox profile root IS the plugin dir. Same rule as everywhere else here: tools via devbox, never
# a download (a hand-placed binary also isn't on CI's PATH).
set -euo pipefail

PROFILE="${DEVBOX_PROJECT_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/.devbox/nix/profile/default"
[ -d "$PROFILE/helm-unittest" ] && export HELM_PLUGINS="$PROFILE"

if ! helm plugin list 2>/dev/null | grep -q '^unittest'; then
  echo "helm-unittest is missing. It ships with the devbox toolchain — run 'devbox install'." >&2
  echo "(If devbox.json lost it: devbox add kubernetes-helmPlugins.helm-unittest. Never curl it.)" >&2
  exit 1
fi

echo "==> helm unittest chart/"
helm unittest chart/
