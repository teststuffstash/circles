#!/usr/bin/env bash
# specs-preview-comment.sh <pr-number> — upsert the sticky "specs preview" comment on a PR.
#
# Called by ci.yaml right after `specs-publish` on pull_request runs, so the URL lands on the
# PR the moment its site content exists (the preview-deploy pattern: the PR page is the front
# door, the comment is the link — the authoritative route list lives in circles-iac
# circles/infra/specs-pr-<N>.yaml).
#
# Sticky: one comment per PR, found by the HTML marker and edited in place — reruns update the
# run pointer instead of stacking comments.
#
# Env: GH_TOKEN (issues write; the workflow's GITHUB_TOKEN), GITHUB_REPOSITORY,
#      GITHUB_RUN_ID/GITHUB_SERVER_URL (optional — run link in the footer).
set -euo pipefail

N="${1:?usage: specs-preview-comment.sh <pr-number>}"
REPO="${GITHUB_REPOSITORY:-teststuffstash/circles}"
URL="https://specs-${N}.circles.teststuff.net/"
MARKER="<!-- specs-preview-comment -->"
RUN_LINE=""
if [ -n "${GITHUB_RUN_ID:-}" ]; then
  RUN_LINE="Rendered by [this CI run](${GITHUB_SERVER_URL:-https://github.com}/${REPO}/actions/runs/${GITHUB_RUN_ID})."
fi

BODY="${MARKER}
📖 **Specs preview: ${URL}**

This PR's rendered spec site (bucket prefix \`pr-${N}/\`; the \`specs-${N}.circles\` route
syncs within ~2 min of PR open — LAN/VPN only). ${RUN_LINE}
Master specs: https://specs.circles.teststuff.net/ · Removed automatically when the PR closes."

EXISTING="$(gh api "repos/${REPO}/issues/${N}/comments" --paginate \
  --jq "[.[] | select(.body | startswith(\"${MARKER}\"))][0].id // empty")"

if [ -n "$EXISTING" ]; then
  gh api -X PATCH "repos/${REPO}/issues/comments/${EXISTING}" -f body="$BODY" >/dev/null
  echo "→ updated specs-preview comment ${EXISTING} on PR #${N}"
else
  gh api "repos/${REPO}/issues/${N}/comments" -f body="$BODY" >/dev/null
  echo "→ posted specs-preview comment on PR #${N}"
fi
