# Delivery phases

The goal issue rules three phases. This page pins what each phase **must** ship and — because the
instruction is *anticipate, don't overreach* — what it **must not** build yet. Requirements
elsewhere in this tree are tagged to phases by reference: P0/P1 requirements are contract now;
the `CIR-DETAIL-*` requirements are the P2 contract, specified early only so P0/P1 leave the
right seams.

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-PROC-PHASE-P0 — hand-set statuses on the existing pipeline

**Ships:** the real page (sunburst + chrome per [../render/sunburst.md](../render/sunburst.md))
replacing the vanilla placeholder in the nginx image; the bake as a build-time step turning
`circles.yaml` into the baked artifact; `manual:` statuses fully supported.

**Must not build:** no scheduler, no `freshness:`/`command:` evaluation, no detail pages, no
metric adapters, no multi-person switching.

| row id | inputs | expected |
|---|---|---|
| p0-manual-end-to-end | fixture-style config, all `manual:` | the image serves the page and the artifact with those statuses |
| p0-page-replaces-placeholder | the deployed image | the vanilla bootstrap page is gone |
| p0-unevaluated-adapters-are-grey | the fixture's `freshness:` and `command:` items | ⚪ + warning "adapter not evaluated in this build", `grey_reason: not-evaluated` (⚖-R50) |
| p0-config-stays-valid | the fixture config unchanged | validates at P0 and at P1; no migration between them |
| p0-stamp-is-build-day-truth | an image built days ago | the generated-at stamp shows the build day ([`CIR-RENDER-GENERATED-AT`](../render/layout.md)) |

**⚖-R2 — the P0 build seam.** The goal says "P0: statuses hand-set in config", the seed glossary
said "P0 has no bake", and yet the page renders from a baked artifact — so *something* converts
config to data at P0. This is the first thing an implementer hits. Options: (a) P0 has no bake
and only `manual:` items may exist, so the fixture becomes invalid and the first real config is
thrown away at P1; (b) the bake exists from P0 and implements `manual:` only, with other adapters
resolving to ⚪ + "not evaluated in this build"; (c) P0 evaluates every adapter at image-build
time, collapsing P0 and P1 into a scheduling difference. **Ruled: (b).** It keeps the fixture
legal, keeps the honest-grey doctrine true and visible ("we are not watching this yet" is a fact,
not a failure), makes P1 a pure implementation step with no config migration, and honors the
goal's own phasing — under (c) P0 is no longer "hand-set" in any meaningful sense. (a) throws
away the fixture, which is also the spec's key example.

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-PROC-PHASE-P0 — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `p0-config-stays-valid` | PASS | — |
| `p0-manual-end-to-end` | PASS | — |
| `p0-unevaluated-adapters-are-grey` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-PROC-PHASE-P1 — the nightly bake

**Ships:** a scheduled nightly run of the **same** bake, evaluating `freshness:` and `command:`
adapters against live sources and publishing the artifact **atomically without an image
rebuild** ([`CIR-BAKE-ATOMIC-WRITE`](../data/data-json.md)). The job runs elsewhere; **this repo
owns the bake code it runs.** `stale_after_hours` becomes non-null, because a cadence now exists
([`CIR-BAKE-STALE-SELF`](../data/data-json.md)).

**Must not build:** detail pages; per-item metric payloads (`detail_page` still ships `null`);
any page change at all.

| row id | inputs | expected |
|---|---|---|
| p1-new-data-no-redeploy | a source note dated today, baked nightly | tomorrow's page shows the updated status and stamp from the same image |
| p1-failed-bake-keeps-last-good | a nightly run that fails validation | the last good artifact is still served |
| p1-adds-no-page-code | the page before and after P1 | byte-identical page logic; only data changes |
| p1-cadence-enables-stale-banner | `stale_after_hours` set, bake skipped two nights | the stale banner appears |

_Evidence: none yet — unverified._

## CIR-PROC-PHASE-P2 — the first detail page

**Ships:** the sqlite metric adapter (the first contributed built-in, through the adapter seam),
per-item detail payloads, and the annotated-timeseries detail page
([detail-page.md](../render/detail-page.md)). A P2 spec pass finalizes the `metric:`/`events:`
config schema, which this tree deliberately marks provisional.

**Must not build:** additional metric sources beyond sqlite; any editing or annotation UI (events
stay markdown in git); drill-downs beyond one detail page per item.

| row id | inputs | expected |
|---|---|---|
| p2-sqlite-metric-end-to-end | an item with a sqlite metric and an events file | click opens its detail page with series and event markers |
| p2-page-unchanged-for-others | items without a metric | main page identical to P1 behavior |

_Evidence: none yet — unverified._

## CIR-PROC-BAKE-ONE-PATH — one bake, several triggers

The bake is **one code path**, invoked identically at image-build time (P0) and by the nightly
scheduler (P1): same inputs, same outputs, same validation. The phase difference is which
adapters are enabled and who pulls the trigger — never a second implementation.

| row id | inputs | expected |
|---|---|---|
| bake-same-code-both-triggers | build-time run and scheduled run | the same entry point, differing only in configuration |
| bake-same-validation-both-triggers | an invalid config | fails identically in both |
| bake-runtime-is-declared | the repo | the bake runs on the Python already pinned in `devbox.json` (⚖-R49) |

**⚖-R49 — what language the bake is written in.** `devbox.json` already pins `python@3.11` and
`uv`, and `CLAUDE.md` says this repo owns the code the bake runs — so the repo has half-decided
and no arm in the fan-out said so. Options: (a) Python, as already pinned; (b) an explicit
re-decision at implementation time. **Ruled: (a).** A spec tree that defines an adapter interface
without naming the language that interface is *in* leaves the first implementation PR to decide
it by accident. Recorded here rather than assumed, because it is a real decision that the
toolchain made implicitly.

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-PROC-BAKE-ONE-PATH — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `bake-same-code-both-triggers` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-PROC-DEPLOY-SEAM — how a real person's data reaches a deployed page

This repo is public and may contain **only synthetic data** (`CLAUDE.md`), while the deployable
unit is an nginx image whose content is `COPY public/`. Nothing today states how a real person's
`circles.yaml`, their note sources, or their baked artifact get into a running deployment. Until
that is stated, every phase above is undeployable for its actual purpose.

| row id | inputs | expected |
|---|---|---|
| no-real-config-committed-here | any PR | synthetic only; the secret scan is not the control that enforces this — review is |
| image-buildable-from-this-repo-alone | CI build | the fixture person's page builds and serves, so the pipeline is provable without real data |
| real-content-enters-at-deploy-time | a real deployment | via a mechanism named in the chart's values, never by rebuilding this repo's image with private files |
| chart-declares-the-seam | `values.schema.json` | whatever the mechanism is, it is authoritative there |
| publish-without-rebuild-is-testable | a data refresh | new statuses served without a new image tag, whichever mechanism is chosen |

**⚖-R1 — where the private config lives, and how its output reaches nginx.** Two arms
independently recommended the same shape: a private repo or job publishes an artifact the chart
mounts, rather than baking a person's life into a public image. Options for the publish path:
(a) an in-cluster CronJob baking to a volume the nginx pod serves; (b) the bake commits the
artifact back to git and the normal deploy pipeline redeploys; (c) the bake pushes to object
storage and the page fetches from there. **Ruled: (a) is the recommendation, and the decision
itself belongs in circles-iac, not here.** (a) needs no git-write credential in a scheduled job,
keeps the page a pure static site on one origin, and makes the atomic-write rule a filesystem
rename. (b) couples a data refresh to a full deploy and puts a write token in the nightly path;
(c) breaks the single-origin rule that ⚖-R4 and `CIR-RENDER-NO-EGRESS` depend on.

**This is the ⚖ to ratify first, and it is deliberately not settled inside this repo.** It spans
circles-iac (which has no chart pin yet) and the real-person-data boundary in `CLAUDE.md`, so
the honest thing a spec tree can do is state the *seam* as a testable requirement — which the
rows above do — and let the mechanism land in an ADR next door. A spec that claimed an existing
deploy route here would be asserting infrastructure that does not exist.

_Evidence: none yet — unverified._

## CIR-PROC-NOT-YET — what these specs deliberately do not decide

Named so a later pass does not mistake silence for oversight.

| deferred | why |
|---|---|
| authentication and who may see a page | a deploy-time concern (circles-iac), not a property of the artifact ([`CIR-BAKE-EXPOSURE`](../data/data-json.md)) |
| multiple people per deployment | one config, one page; nothing in the artifact prevents a second deployment |
| history or trend of statuses over time | the artifact is a snapshot; a status history is a different product, and P2's timeseries is about *metrics*, not lights |
| editing the config from the page | the config is a file in a git repo, on purpose |
| notifications when an item turns red | a page that gets looked at is the product; alerting is a separate decision with its own failure modes |
| the contributed-adapter registry | the interface is fixed ([`CIR-ADAPT-CONTRACT`](../data/adapters.md)); the registry is not (⚖-R33) |

_Evidence: none yet — unverified._
