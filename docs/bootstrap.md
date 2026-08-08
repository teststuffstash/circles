# How this repo was bootstrapped — the research + weave stage

This page is the durable record of stage 1 of the circles bootstrap: how an empty scaffold
became a 91-requirement product contract, written **before any product code existed**, by
dispatching the same brief to several models in parallel and weaving the results. The pull
requests that carried this work were archive-closed once the contract landed on master; their
full diffs and review threads remain on the closed PRs, and every arm's head commit is
preserved under an `archive/` tag. This page is the map to them.

Scope: this covers the spec research fan-out and the weave only (2026-08-03 → 2026-08-06).
The build experiments that followed — the one-shot vs fan-out comparison on goal #17 and the
P0-complete goal #29 — are the next stage and are recorded in their issues, not here.

## 1. Scaffold (2026-08-03)

- `a34b261` — `new-stack --from sleep-tracking --chainless` scaffold + LLM-adaptation pass:
  chart, CI seam (`devbox run ci`), vanilla placeholder page proving the deploy pipeline.
- `d583f79` — the spec conventions seed: requirement-ID grammar, decision-table doctrine,
  `circles.yaml` schema stub, and the synthetic fixture person (`fixtures/alex/` — invented,
  doubling as the spec's key examples; this repo is public, committed data is synthetic only).

## 2. Spec fan-out — issue [#1](https://github.com/teststuffstash/circles/issues/1)

One self-contained brief (the full product intent: sunburst of life areas,
traffic-light freshness semantics, one-screen/A4 constraint, adapter taxonomy) was dispatched
to four models in parallel. Each arm authored a complete `specs/` tree on its own branch,
blind to the others. None of these PRs was ever meant to merge — the plan was always an
operator cherry-pick.

| arm | PR | tag | headline |
|---|---|---|---|
| opus | [#3](https://github.com/teststuffstash/circles/pull/3) | `archive/research/issue-1-opus` | 15 pages, 64 requirements, 33 ⚖ |
| kimi-k3 | [#4](https://github.com/teststuffstash/circles/pull/4) | `archive/research/issue-1-kimi-k3` | 13 pages, 68 requirements, 26 ⚖ |
| deepseek-v4-flash-0731 | [#2](https://github.com/teststuffstash/circles/pull/2) | `archive/research/issue-1-deepseek-v4-flash-0731` | first arm in |
| mimo-v2.5-pro | [#5](https://github.com/teststuffstash/circles/pull/5) | `archive/research/issue-1-mimo-v2.5-pro` | |

## 3. Comparison mission — issue [#6](https://github.com/teststuffstash/circles/issues/6)

Two kinds of one-shot comparison runs scored the four arms so the operator could cherry-pick
per page (reports live under `docs/comparison/` on each archived branch):

- **Core-metric judges** — same brief, different judge models, each producing a blind
  decision-point checklist → union matrix → scorecard + per-page cherry-pick map:
  [#11](https://github.com/teststuffstash/circles/pull/11) (nemotron-3-ultra),
  [#12](https://github.com/teststuffstash/circles/pull/12) (gpt-5.6-terra),
  [#13](https://github.com/teststuffstash/circles/pull/13) (fable) —
  tags `archive/research/issue-6-compare-<slug>`.
- **Downstream proxies** — one cell per arm, deliberately isolated (no issue #1, no sibling
  arms): read that arm's `specs/` tree as the *only* product source and enumerate every
  question a builder must still ask before P0.
  Result across all four: **0 blockers**; most builder questions were already
  answered-by-⚖ (21–33 per arm), the rest were judgment calls or minors.
  [#7](https://github.com/teststuffstash/circles/pull/7) (opus),
  [#8](https://github.com/teststuffstash/circles/pull/8) (kimi-k3),
  [#9](https://github.com/teststuffstash/circles/pull/9) (mimo-v2.5-pro),
  [#10](https://github.com/teststuffstash/circles/pull/10) (deepseek-v4-flash-0731) —
  tags `archive/research/issue-6-proxy-<slug>`.

## 4. The weave (2026-08-05)

An operator-driven session cherry-picked across the four arms into one contract: **15 pages,
91 requirement ids, 49 ⚖ register entries** — opened as PR
[#16](https://github.com/teststuffstash/circles/pull/16). #16 was closed by a branch rename
(the weave branch became the goal #17 integration branch; a rename closes the PR whose head
it is) and reopened content-identical as draft PR
[#25](https://github.com/teststuffstash/circles/pull/25).

## 5. Landing on master (2026-08-06)

The weave did not merge directly. It first served as the contract for the goal #17 build
experiment (one-shot vs fan-out — the next stage's story), and the weave **plus that
experiment's findings** (⚖-R50–R52, corrected palette hexes, and the amendments recorded in
`specs/open-questions.md` §Provenance) reached master together as PR
[#28](https://github.com/teststuffstash/circles/pull/28) (`specs/harvest-17`): 15 pages,
91 requirement ids, 52 ⚖. Both experimental implementations were discarded by design — the
spec tree, not the code, is what the bootstrap was building.

## Archive conventions

- Every research branch's head commit is tagged `archive/<branch-name>` before the branch was
  deleted, so each arm stays checkout-able by name forever.
- The PRs are **closed, not deleted** — GitHub keeps a closed PR's diff, commits, comments,
  and review threads indefinitely; the closing comment on each names its tag and verdict.
- What came next: the build experiments live in issues
  [#17](https://github.com/teststuffstash/circles/issues/17) /
  [#27](https://github.com/teststuffstash/circles/issues/27) /
  [#29](https://github.com/teststuffstash/circles/issues/29), and the operational history of
  the agent loop that ran them lives in the homelab repo's coordinator tick-log.
