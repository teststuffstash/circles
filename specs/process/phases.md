# Delivery phases (CIR-PHASE-*)

The goal issue rules three phases. This page pins what each phase **must** ship and —
because the instruction is *anticipate, don't overreach* — what it **must not** build yet.
Specs across this tree are tagged to phases by reference: P0/P1 requirements are contract
now; the detail-page requirements (CIR-RENDER-DETAIL-*) are the P2 contract, specified early
so P0/P1 leave the right seams.

## CIR-PHASE-P0 — hand-set statuses on the existing pipeline

**Ships:** the real page (sunburst + chrome per [../render/](../render/sunburst.md))
replacing the vanilla placeholder in the nginx image; the bake as a build-time step that
turns `circles.yaml` into `data.json`; `manual:` statuses fully supported, `freshness:` and
`command:` evaluated at image build time (the adapter code ships in P0 even though the
*schedule* arrives in P1).

**Must not build:** no scheduler, no detail pages, no metric adapters, no multi-person
switching.

| row (test id) | inputs | expected |
|---|---|---|
| p0-manual-end-to-end | fixture-style config, all `manual:` | image serves the page + `data.json` with those statuses |
| p0-page-replaces-placeholder | the deployed image | the vanilla bootstrap page is gone |
| p0-stale-is-visible | an image built days ago | the generated-at stamp shows the build-day truth (CIR-RENDER-LAYOUT-GENERATED-AT-VISIBLE) |

## CIR-PHASE-P1 — the nightly bake

**Ships:** a scheduled (nightly) run of the **same** bake, evaluating
`freshness:`/`command:` adapters against live sources and publishing `data.json`
**atomically without an image rebuild** (CIR-DATA-DATAJSON-ATOMIC-WRITE). The job runs
elsewhere (scheduler infra outside this repo); **this repo owns the bake code it runs.**

**Must not build:** detail pages; per-item metric payloads (the `detail_page` field ships
as `null`); any page change.

| row (test id) | inputs | expected |
|---|---|---|
| p1-new-data-no-redeploy | a source note dated today, baked nightly | tomorrow's page shows the updated status/stamp with the same image |
| p1-failed-bake-keeps-last-good | a nightly run that fails validation | last good `data.json` still served (CIR-DATA-DATAJSON-ATOMIC-WRITE) |

**⚖ AMBIGUITY: NIGHTLY-PUBLISH-PATH** — how the nightly `data.json` reaches the served pod.
Options: (a) an in-cluster CronJob (spec lives in circles-iac) baking to a volume the nginx
pod serves; (b) the bake commits `data.json` back to git and the normal deploy pipeline
redeploys; (c) the bake pushes to object storage and the page fetches it from there.
**Recommendation: (a)** — it needs no git-write credentials in a scheduled job, keeps the
page a pure static site on one origin (CIR-RENDER-LAYOUT-ASSETS), and the atomic-write rule
is a filesystem rename away. (b) couples a data refresh to a full deploy and puts a write
token in the nightly path; (c) breaks the single-origin rule. The choice lands in
circles-iac/chart work, not this repo — recorded here so the requirement (publish without
rebuild) is testable whichever mechanism is picked. See Follow-ups in the introducing PR.

## CIR-PHASE-P2 — the first detail page

**Ships:** the sqlite metric adapter (the first contributed built-in, via the adapter seam —
CIR-DATA-ADAPTER-REGISTRY), per-item detail payloads, and the annotated-timeseries detail
page (CIR-RENDER-DETAIL-PAGE, CIR-RENDER-DETAIL-EVENTS). A P2 spec pass finalizes the
`detail:` config schema, which this tree marks provisional.

**Must not build:** additional metric sources beyond sqlite; editing/annotation UI (events
stay markdown-in-git); drill-downs beyond one detail page per item.

| row (test id) | inputs | expected |
|---|---|---|
| p2-sqlite-metric-end-to-end | an item with `detail.metric.sqlite` + an events file | click opens its detail page with series + event markers |
| p2-page-unchanged-for-others | items without `detail:` | main page identical to P1 behavior |

## CIR-PHASE-BAKE-ONE-PATH — one bake, several triggers

The bake is **one code path** invocable identically at image build time (P0) and by the
nightly scheduler (P1): same inputs (a config tree), same outputs (atomic `data.json` +
warnings), same validation. A trigger difference may never fork behavior (no "nightly mode"
flag that changes semantics).

| row (test id) | inputs | expected |
|---|---|---|
| bake-same-binary-both-triggers | same config tree through P0 build and P1 schedule | byte-identical semantics (timestamps aside) |

## CIR-PHASE-CONFIG-PROVENANCE — where the private content lives

`circles.yaml`, the dated notes, and (P2) the sqlite file are **a real person's data** and
can never live in this public repo (the synthetic-only invariant — CLAUDE.md). Yet the P0
image build and the P1 nightly bake both need them. The goal issue does not say where they
live.

**⚖ AMBIGUITY: CONFIG-PROVENANCE** — the private content's home. Options: (a) a private git
repo holding `circles.yaml` + notes + metrics, pulled by the bake at build/scheduled time
(the freshness doctrine — "any git repo of dated notes" — already assumes git-shaped
sources); (b) Kubernetes Secrets/ConfigMaps mounted into the job; (c) an object-store bucket.
**Recommendation: (a)** — notes are naturally git-tracked text (freshness reads git repos of
dated notes), one private repo carries config + sources + (P2) the sqlite file together, and
the bake's trust model stays simple (one authenticated clone, executed as trusted input —
CIR-DATA-ADAPTER-COMMAND-EXEC). (b) scatters the content across several hand-maintained
objects; (c) loses the versioning that makes a life-log auditable. See Follow-ups in the
introducing PR.

| row (test id) | inputs | expected |
|---|---|---|
| config-never-in-public-repo | this repo's history | only the synthetic fixture person exists here |
| bake-input-is-a-tree | P0 or P1 run | the bake consumes a checked-out config tree (config + sources together), wherever it came from |

## Provenance

No external sources; phase boundaries quote the goal issue, and the ⚖ recommendations reason
from this repo's stated invariants (public repo, single-origin static page, atomic
publishing).
