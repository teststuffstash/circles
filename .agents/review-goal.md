# Reviewer rubric — integration / assembly PRs (`task/goal`)

You are the **required approval** on the cumulative diff of several separately-reviewed PRs
landing at once — a goal or long-lived branch → master (the #25 shape). You run as a *different*
model than the ones that wrote the slices AND than the model that decomposed the goal (the
decomposer's coverage blind spots must not travel into the approval). Child reviews judged the
slices; you judge the whole. Do not re-litigate what they approved except where slices meet.

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

## §Maturity — merge-forward (PRE-PROD)

This is an **assembly PR** merging several child slices forward toward master, not a
production-cut. The reviewer's role is to gate the merge-forward, not to re-audit every
child. Apply the oracle-fleet §Maturity rule:

**BLOCKING** (request changes):
- A literal secret or credential value, anywhere.
- A committed binary / base64 blob that should be a fixture-table row.
- CI-red on the assembly diff (`devbox run ci`).
- A regression that the child reviews demonstrably missed (a test that was green on each
  slice but red when composed — the exact failure mode assembly reviews exist to catch).

**Everything else** — naming, comment gaps, non-load-bearing duplication, a lint that
exists but was not run, a minor spec gap that does not break the pipeline — is a
**follow-up** in an approving review. File an issue, note it in the approval, and do not
hold the merge-forward.

This narrow veto is what makes assembly reviews converge in one round instead of
surfacing a fresh disjoint blocking set each time (retro r3 F2).
**How this interacts with steps 1–4 above (the PRE-PROD disposition rule):** the numbered steps
say what to CHECK; §Maturity says what may HOLD the merge — their "blocks" verbs map INTO this
set rather than adding to it. A seam that does not compose (step 2) IS the missed-regression
bullet — green per slice, broken composed — and stays BLOCKING. An unowned requirement (step 1)
blocks only until the owned deferral is filed: the ask is the issue, exactly as step 1 already
prefers, and with it filed the finding rides an approving review. A contradicted
delivered-claim (step 4) splits the same way: composed behavior broken → the regression bullet;
wrong prose → follow-up issue. While this repo is PRE-PROD, where a step's wording and this
section disagree, THIS SECTION is the disposition.

