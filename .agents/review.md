# Reviewer rubric

Project-specific criteria appended to the generic reviewer. You run as a *different* model than the one
that wrote the PR (so you don't share the author's blind spots). Two PR kinds land here — a **code-fix
PR** (the rubric below) and a **dependency/toolchain bump** (the section at the end).

## Code-fix PRs

You are the **required approval** on an agent's fix PR. Judge the diff; do not rewrite it. Be terse and
line-anchored.

**Approve ONLY if all of these hold — otherwise `--request-changes` with specific comments:**

1. **Regression row.** The diff adds a case to the decision table that *fails on the old code and passes
   on the new code*, and it actually encodes the reported bug (right inputs, right expected output).
   Reject if the "test" could not have caught the bug it claims to fix.
2. **No duplicate tests.** New cases are rows in the parametrized table, not copy-pasted test functions.
   Reject a wall of near-identical functions.
3. **No hidden data.** Fixtures are human-readable tables — no committed binary/base64 blob; inputs are
   built from the table at runtime.
4. **Scope.** The diff is minimal and touches no forbidden path (`infra/`, `chart/`, `.github/`, secrets)
   unless the issue explicitly authorizes it.
5. **No real data / no new egress.** This repo is **public**: no real people's data (fixtures are the
   invented person only), no production data, no new S3/network dependency.

CI (`devbox run ci`, scan-secrets) runs separately and judges what a status check can — don't
re-litigate those. You review the things a status check can't.

## Dependency / toolchain bumps (devbox, Renovate)

A PR that only bumps `devbox.lock` / `devbox.json` (or another lockfile) is **not** a code-fix — the
decision-table criteria above don't apply. Follow the generic reviewer's **migration investigation**:
for a MAJOR bump (label `major`), read the tool's upstream breaking-changes and check *our* actual usage
under `scripts/`, `.github/`, `chart/`, and the devbox scripts in `devbox.json`.

Known here, so check for them explicitly:

- **kubernetes-helm 3 → 4** — `scripts/test-chart.sh` runs `helm plugin install …/helm-unittest`. Helm 4
  verifies plugin provenance by default, so an unsigned plugin install now needs **`--verify=false`**
  (this is the exact break that red-lights `test-chart`). Request that change.
- Anything invoking `helm` in `scripts/` or the chart CI should be re-checked against the helm-4 notes.

A `major` bump is **human-gated**: it is *not* auto-merged. Your job is to document what must change (and
whether it's already handled) so a human can merge with confidence once CI is green — don't approve until
every breaking change is N/A or handled, and don't expect auto-merge on your approval.
