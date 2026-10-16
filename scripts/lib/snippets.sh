# shellcheck shell=bash
# The allure-behavior-snippets release circles renders evidence with — ONE pin, sourced by
# scripts/evidence.sh (homelab gateway scripts/lib/snippets.sh shape; homelab ADR-156 = one
# portable process, pinned per repo — circles#103). Consumed as a RELEASE WHEEL, never a git clone
# (anonymous git-upload-pack gets rate-limited from the NAT'd WAN IP — oracle-fleet#362).
# `allure-evidence` reads RAW allure results → evidence.json, <RULE>.md fragments, digest.md;
# `--spec` joins a page's tables to the evidence rows. The process docs this version runs
# (RULES.md, CONVENTIONS.md, briefs/) ship inside the wheel: `process-path` prints where.
SNIPPETS_WHEEL=https://github.com/teststuffstash/allure-behavior-snippets/releases/download/v0.5.2/allure_behavior_snippets-0.5.2-py3-none-any.whl

# allure_evidence <args…> — run the pinned tool's `allure-evidence` console script.
allure_evidence() {
  uv run --no-project --with "allure-behavior-snippets @ ${SNIPPETS_WHEEL}" allure-evidence "$@"
}
