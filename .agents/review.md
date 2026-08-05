# Reviewer rubric

Project-specific criteria appended to the generic reviewer. You run as a *different* model than the one
that wrote the PR (so you don't share the author's blind spots). Four PR kinds land here — a **code-fix
PR**, a **build/feature PR**, an **integration/assembly PR**, and a **dependency/toolchain bump**.
Pick the section that matches what the PR actually is, and say which one you applied.

The build and assembly sections also exist as standalone files keyed for future task-label routing
(`task/build` → `.agents/review-build.md`, `task/goal` → `.agents/review-goal.md`). Until that
routing lands, THIS file is what the reviewer reads, so the sections are duplicated here verbatim —
if you edit one copy, edit both.

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

## Build / feature PRs (`task/build`)

A PR that CREATES a deliverable against a `task/build` issue — a module, a gate, a page. The
code-fix regression-row criterion does **not** apply: there is no old-code bug to encode. Judge instead:

1. **Deliverable == the issue's scope.** Read the issue (`gh issue view <n> --json title,body` —
   the plain form renders empty under the pod token). The diff builds what the Deliverables
   section names, honours the "do not build" list, and stays inside its `Touches:` line. Code
   beyond the slice — even good code — is scope creep: request its removal (an unwired
   `resolve_freshness()` importing an undeclared `pytz` is the canonical case; it shipped dead
   and buggy).
2. **Tests exercise the shipped artifact, not a reimplementation of it.** A pytest that re-derives
   the page's JS math in Python proves the math, not the page. Spec citations
   (`CIR-<AREA>-<NAME>#<row-id>`) must be verbatim, parametrised over table rows, and attached to
   tests that would actually fail if the cited row regressed.
3. **Acceptance claims are checkable.** The PR body's "gate ran and passed" is the author's claim.
   Corroborate what you can from your sandbox (fixture replay by hand, file presence on the
   branch, which checks actually ran on THIS PR) and state plainly which claims you could not
   check.
4. **Seams.** If the diff produces or consumes an artifact another issue owns (a `Depends-on:`
   edge, a shared file or format), pull the sibling PR's diff (`gh pr diff <n>`) and check the two
   sides agree: who writes it, who reads it, whether the shapes match, and whether anything
   between them is owned by nobody. If you can only make sense of this PR by reading the
   sibling's issue body, say so — that is a decomposition finding, worth reporting on the parent,
   on top of any code finding.
5. **Standard floors** from the code-fix rubric still hold: no hidden/binary data, no real
   people's data, no new egress, no forbidden paths beyond what the issue authorizes.

**Verdict scope: wide eyes, narrow veto.** Block only on defects inside THIS PR's own issue.
Anything discovered beyond the slice routes outward — a non-blocking comment naming the open issue
that owns it (`gh issue list` for titles), or a recommendation to file one if none does. Never
request changes on a child for work its issue never claimed.

CI (`devbox run ci`, scan-secrets) runs separately and judges what a status check can — don't
re-litigate those. You review the things a status check can't.

## Integration / assembly PRs (a goal branch → master, `task/goal`)

The cumulative diff of several separately-reviewed PRs landing at once (the #25 shape). Child
reviews judged the slices; you judge the whole — and you should be a different model from the one
that decomposed the goal, not just from the writers. Do not re-litigate what child reviews
approved except where slices meet.

If the goal issue number isn't given, derive it from the branch name (`goal/<n>-…`) or the PR
body, and read it: its scope and acceptance list are your contract.

1. **Coverage first — spec→code, not code→spec.** Enumerate the requirement ids in the
   contract's scope and demand each resolves to an owner: implemented and cited by a test, or
   explicitly deferred to a named follow-up issue. A diff-anchored read structurally cannot see
   absent work — `CIR-BAKE-SELF-CONTAINED` survived four diff-anchored reviews exactly this way.
   Mechanical helper: diff {ids in scope} against {ids cited under `tests/`}; investigate every
   id in the remainder. An unowned requirement blocks — where the right fix is filing the owned
   deferral, ask for that, not for code.
2. **Seams compose end-to-end.** Walk each produced-artifact → consumer chain across the merged
   slices and check it actually connects in one pipeline run (one bake must yield BOTH
   `data.json` and the page that inlines it — the exact chain that fell between two
   individually-approved children). Hand-assembled artifacts standing in for a pipeline step are
   a blocking finding.
3. **Then correctness — code→spec.** Spot-check cited rows against their implementations,
   determinism, failure isolation, data hygiene. This is the pass diff-review does well; it comes
   third because it is the only one the child reviews already partially did.
4. **Claims audit.** Child PR bodies' delivered-claims versus the assembled reality. A claim the
   assembly contradicts blocks here even if the child review let it pass.

Deferrals must be issues, never silence. Once the evidence chain lands (spec row → test →
rendered evidence block), step 1 becomes reading the rendered coverage instead of grepping — the
rubric's direction stays the same.

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
