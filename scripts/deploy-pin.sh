#!/usr/bin/env bash
# deploy-pin.sh — open/update the ONE deploy PR in circles-iac that bumps the circles chart pin
# (circles-iac apps/circles-page.yaml, the OCI chart Application) to $VERSION (the chart just
# published). Part of the FU-025 deploy pipeline (see .github/workflows/
# deploy.yaml + homelab docs/sleep-iac.md (the pipeline reference) §"Deploy pipeline").
#
# Why a fixed branch: GitHub allows only one open PR per head branch, so `deploy/circles`
# gives exactly one open deploy PR per app — a later build force-updates the same branch/PR instead
# of opening a second. Combined with the workflow's `concurrency: cancel-in-progress`, the newest
# master commit always wins.
#
# Monotonic guard: the pinned chart version encodes the app commit as its `-g<sha>` suffix. If that
# pinned sha is NOT an ancestor of the commit we're deploying, this run would REGRESS the deploy —
# so we bail (belt to cancel-in-progress). Needs full app history → deploy.yaml checks out depth 0.
#
# Env: GH_TOKEN (contents + pull_requests write on circles-iac), VERSION (e.g. 2026.7.4-g<sha12>),
#      GITHUB_SHA (the app commit being deployed; Actions provides it).
set -euo pipefail

IAC_REPO="teststuffstash/circles-iac"
APP="circles"
BRANCH="deploy/${APP}"
# The CHART Application (multi-source: ghcr OCI chart + $values). NOT apps/${APP}.yaml — that is
# the circles-infra GIT-directory app (path circles/infra) whose targetRevision must stay `master`:
# on 2026-08-08 this script wrote a chart CalVer there, ArgoCD sat "unable to resolve to a commit
# SHA" (a -g<sha> is a circles commit, never a circles-iac ref) until circles-iac PR #71 reverted it.
APP_FILE="apps/${APP}-page.yaml"
: "${VERSION:?set VERSION}" "${GH_TOKEN:?set GH_TOKEN}"

APP_REPO_DIR="$(git rev-parse --show-toplevel)"
NEW_SHA="${GITHUB_SHA:-$(git -C "$APP_REPO_DIR" rev-parse HEAD)}"

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
git clone --quiet "https://x-access-token:${GH_TOKEN}@github.com/${IAC_REPO}.git" "$WORK/iac"
cd "$WORK/iac"

# First (chart) targetRevision in the multi-source Application; the 2nd is the `master` $values ref.
CUR_VER="$(grep -m1 -E '^[[:space:]]*targetRevision:' "$APP_FILE" | awk '{print $2}')"
if [ "$CUR_VER" = "$VERSION" ]; then
  echo "circles-iac already pinned to ${VERSION} — nothing to do"; exit 0
fi

# --- monotonic guard ---
CUR_SHA="${CUR_VER##*-g}" # strip through '-g' → the sha (or unchanged if the pin has no -g suffix)
if [ -n "$CUR_SHA" ] && [ "$CUR_SHA" != "$CUR_VER" ] \
   && git -C "$APP_REPO_DIR" cat-file -e "${CUR_SHA}^{commit}" 2>/dev/null \
   && ! git -C "$APP_REPO_DIR" merge-base --is-ancestor "$CUR_SHA" "$NEW_SHA"; then
  echo "::notice::pinned ${CUR_SHA} is not an ancestor of ${NEW_SHA} — refusing to regress the deploy"
  exit 0
fi

git config user.name "circles-deploy[bot]"
git config user.email "circles-deploy@users.noreply.github.com"

# Reset the deploy branch onto latest master each run → the PR is always a clean single-commit diff
# (bumps only the chart source's targetRevision; the `master` $values ref is left untouched).
git checkout -q -B "$BRANCH" origin/master
sed -i "0,/^\([[:space:]]*\)targetRevision:.*/s//\1targetRevision: ${VERSION}/" "$APP_FILE"

if git diff --quiet -- "$APP_FILE"; then
  echo "no change to ${APP_FILE} (already at ${VERSION}) — nothing to push"; exit 0
fi

git add "$APP_FILE"
git commit -q -m "deploy: ${APP} ${VERSION}" \
  -m "Auto-bump from circles@${NEW_SHA}. Image tag = chart appVersion (${VERSION})."
git push -q --force origin "$BRANCH"

# Upsert the PR. The existence check MUST be OPEN-only: `gh pr view <branch>` also matches a previously
# MERGED PR on the same branch, which would fool a bare check into skipping creation.
PR="$(gh pr list --repo "$IAC_REPO" --head "$BRANCH" --state open --json number --jq '.[0].number // empty')"
if [ -z "$PR" ]; then
  PR="$(gh pr create --repo "$IAC_REPO" --base master --head "$BRANCH" \
    --title "deploy: ${APP} ${VERSION}" \
    --body "Automated deploy bump from \`circles@${NEW_SHA}\`.

Chart \`${VERSION}\` (image tag defaults to the chart appVersion — circles-iac never sets it)." \
    | grep -oE '[0-9]+$')"
fi
echo "→ deploy PR #${PR} for ${APP} ${VERSION}"

# Arm GitHub auto-merge, then we're done. circles-iac gates on ci ONLY (no required-approval — dropped in
# tofu/github because an App's Integration bypass can't waive an approval on a merge), so GitHub squash-
# merges the PR the moment ci goes green — no polling, the deploy job ends here (delete_branch_on_merge
# cleans the branch). Post-deploy handling (health check / rollback, FU-044) is done IN-CLUSTER off
# ArgoCD app-health events, deliberately not tied to this GitHub Actions run.
gh pr merge "$PR" --repo "$IAC_REPO" --auto --squash
echo "→ auto-merge armed on deploy PR #${PR} — merges when circles-iac ci is green"
