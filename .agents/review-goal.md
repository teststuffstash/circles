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
