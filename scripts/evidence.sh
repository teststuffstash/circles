#!/usr/bin/env bash
# Raw Allure results → the reviewer's evidence pack + the spec site's fragments (homelab ADR-156;
# the gateway's scripts/gateway-evidence.sh shape — circles#103):
#
#   devbox run evidence [-- <results-dir> [<out-dir>]]     (defaults: allure-results allure-evidence)
#
# Run AFTER pytest: `devbox run ci` writes the unit tier's results to allure-results/ and ends by
# running this; `devbox run test-browser` writes the browser tier's to allure-results-browser/.
# Allure results are uuid-named files, so a whole-suite run is the two dirs copied into one
# (`cp allure-results/* allure-results-browser/* <merged>/`) and passed as <results-dir>.
#
# <out-dir> is the WHOLE reviewer pack:
#   allure-results/ a copy of the raw results (attachments, environment.properties, …)
#   evidence.json   every labelled record across the run
#   digest.md       the run's **Stamp:** line (git.commit vs this head), then every spec rule in page order — tables, findings (incl. the --spec join's
#                   ROW_UNPROVEN / CELL_MISMATCH / ROW_UNSPECIFIED) and the **Hygiene:** block
#   <RULE>.md       one fragment per rule: the spec page's tables joined to the evidence where
#                   the tool can join them (`--spec`), the plain evidence table otherwise
# The fragments are also copied into specs/evidence/ (gitignored), where the site build's
# pymdownx.snippets transcludes them under each rule's `--8<-- "<RULE>.md"` pointer
# (scripts/specs-build.sh, mkdocs.yml). Prints the finding/hygiene code counts.
# The tool runs ONCE PER SPEC PAGE: `--spec` takes one page and joins only the --rules headed on
# it. Pin: scripts/lib/snippets.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
RESULTS="${1:-allure-results}"
OUT="${2:-allure-evidence}"
SITE_FRAGMENTS=specs/evidence
# shellcheck source=lib/snippets.sh
source scripts/lib/snippets.sh

if ! ls "$RESULTS"/*-result.json >/dev/null 2>&1; then
  echo "evidence: no Allure results under $RESULTS/ — run the suite first (devbox run ci)" >&2
  exit 1
fi
rm -rf "$OUT" && mkdir -p "$OUT"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

# Spec pages that head rules, and their rules in page order. A rule heading is the bare ID
# (RULES.md rule 3). specs/evidence/ is GENERATED (this script's fragments) — never a spec page.
RULE_SED='s/^#{2,6} (CIR-[A-Z0-9-]+)\s*$/\1/p'
mapfile -t pages < <(grep -rlE '^#{2,6} CIR-[A-Z0-9-]+\s*$' specs --include='*.md' --exclude-dir=evidence | sort)
all_rules=()
for page in "${pages[@]}"; do
  mapfile -t rules < <(sed -nE "$RULE_SED" "$page")
  all_rules+=("${rules[@]}")
done
csv() { local IFS=,; echo "$*"; }

echo "== evidence: suite-wide evidence.json + fragments ($RESULTS → $OUT)"
allure_evidence --results "$RESULTS" --out "$OUT" --rules "$(csv "${all_rules[@]}")"
rm -f "$OUT/digest.md"   # rebuilt below, page by page, with the spec join

# The head/artifact stamp (CONVENTIONS § The head/artifact stamp): the run's git.commit (written
# by tests/conftest.py at session end) against the head this pack is for — CIRCLES_HEAD_SHA (CI:
# the PR head), else HEAD. Same wording as the tool's evidence-pack digest.
prop() { sed -nE "s/^$1=(.*)$/\1/p" "$RESULTS/environment.properties" 2>/dev/null | tail -1; }
run_commit=$(prop 'git\.commit')
run_digest=$(prop 'image\.digest')
head=${CIRCLES_HEAD_SHA:-$(git rev-parse HEAD 2>/dev/null || true)}
if [ -z "$run_commit" ]; then
  stamp="**Stamp:** the run names no \`git.commit\` — it cannot be tied to head ${head:0:12}; every row is unproven at this head (E-STALE)."
elif [ -n "$head" ] && [ "${#run_commit}" -ge 7 ] && { [[ "$head" == "$run_commit"* ]] || [[ "$run_commit" == "$head"* ]]; }; then
  stamp="**Stamp:** run at \`git.commit=${run_commit:0:12}\` = this head."
else
  stamp="**Stamp:** run at \`git.commit=${run_commit:0:12}\` ≠ head ${head:0:12} — stale; every row is unproven at this head (E-STALE)."
fi
if [ -n "$run_digest" ]; then
  stamp+=" Artifact: \`image.digest=${run_digest}\`."
else
  stamp+=" No \`image.digest\`: this is PR-head evidence, not built-artifact evidence."
fi

{
  echo "# circles evidence digest"
  echo
  echo "$stamp"
  echo
  if [ -f "$RESULTS/environment.properties" ]; then
    echo '```properties'
    cat "$RESULTS/environment.properties"
    echo '```'
    echo
  fi
} > "$OUT/digest.md"

for page in "${pages[@]}"; do
  mapfile -t rules < <(sed -nE "$RULE_SED" "$page")
  slug=$(echo "${page#specs/}" | tr '/' '_')
  echo "== evidence: join $page (${#rules[@]} rules)"
  allure_evidence --results "$RESULTS" --out "$scratch/$slug" --spec "$page" --rules "$(csv "${rules[@]}")" >/dev/null
  # A joined fragment replaces the plain one; a rule whose tables the tool could not join keeps it.
  for r in "${rules[@]}"; do
    [ -f "$scratch/$slug/$r.md" ] && cp "$scratch/$slug/$r.md" "$OUT/$r.md"
  done
  { echo "# ${page}"; echo; cat "$scratch/$slug/digest.md"; } >> "$OUT/digest.md"
done

# The raw results ride inside the pack: a reviewer reads <pack>/allure-results/ and
# <pack>/evidence.json from one artifact download.
cp -r "$RESULTS" "$OUT/allure-results"

# The site's copy: exactly this run's fragments (a rule without one renders nothing under its
# pointer — visibly unverified, never a stale PASS).
rm -rf "$SITE_FRAGMENTS" && mkdir -p "$SITE_FRAGMENTS"
cp "$OUT"/CIR-*.md "$SITE_FRAGMENTS"/ 2>/dev/null || true

echo "== evidence: ${stamp//\*\*/}"
echo "== evidence: codes across digest.md"
for code in NO_EVIDENCE FAILED BARE_ROW STEP_FLAT STEP_NOISE UNIT_ONLY_CANDIDATE ATTACH_BULK PARAM_BLOB \
            NAME_BLANK THREAD_BROKEN ROW_UNPROVEN CELL_MISMATCH ROW_UNSPECIFIED; do
  printf '  %-20s %s\n' "$code" "$(grep -cE "^- $code( |\$)" "$OUT/digest.md" || true)"
done
# joined = the fragment proves at least one spec row (a rule with tables but no records still
# gets an all-∅ joined fragment; that is not a join).
joined=$(grep -lE '^_spec: [0-9]+ rows · [1-9][0-9]* proven' "$OUT"/CIR-*.md 2>/dev/null | wc -l)
labelled=$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["rules"]))' "$OUT/evidence.json")
echo "evidence: $(find "$OUT" -maxdepth 1 -name 'CIR-*.md' | wc -l) fragments; $labelled rules carry records, $joined joined to their spec tables" \
     "→ $OUT/ and $SITE_FRAGMENTS/; $(find "$OUT" -type f | wc -l) files in the pack"
