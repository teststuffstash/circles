#!/usr/bin/env bash
# lint-specs.sh — the spec-tree gate.
#
# The conventions in specs/README.md (closed area vocabulary, row-id join keys, world
# declarations, evidence lines, indexed ⚖ entries) are a sweep across every page, not a habit
# a page-by-page author can be trusted to keep. This is the mechanical half; review keeps the
# judgment half.
#
# Also gates the fixture person against the specs: nothing in the FU-126 fan-out checked that
# fixtures/alex/circles.yaml's sources actually resolve, which is the cheapest guard there is.
#
# Run as `devbox run ci` does, or directly: bash scripts/lint-specs.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> lint specs tree"
python3 "${REPO_ROOT}/scripts/lib/lint_specs.py"
