# Phases — what each one owns, and what it may not assume

The goal names three phases. Specs anticipate them; they do not build them early. This page
records the boundary each phase must not cross, and one seam the goal does not mention at all:
how a real person's data reaches a deployed page from a public repo that may never contain it.

## CIR-PROC-PHASE-P0 — hand-set statuses on the existing pipeline <a id="cir-proc-phase-p0"></a>

| description | inputs | expected |
|---|---|---|
| the bake exists in P0 | any config | a bake step runs and writes the artifact ([CIR-BAKE-ARTIFACT](../data/data-json.md)) |
| P0 implements `manual:` only | config with `manual:` items | resolved normally |
| other adapters resolve to grey in P0 | config with `freshness:`/`command:` | ⚪ + warning "adapter not evaluated in this build" ([CIR-Q-06](../data/status-resolution.md)) |
| P0 configs stay valid at P1 | the fixture person | no config change when adapters land — only the lights change |
| P0 ships on the existing deploy | nginx image + Helm chart | the page replaces the vanilla `public/index.html` ([CLAUDE.md](../../CLAUDE.md)) |
| P0 does not bake nightly | any config | the bake runs at build time; there is no scheduler yet |

This is the resolution of the goal's own tension: "P0: statuses hand-set" reads as *no bake*, but
the fixture person already declares `freshness:` and `command:` items, and something must decide
what they show. A bake that exists from day one with one adapter implemented keeps every config
legal across the phase boundary and keeps the grey honest — "we are not watching this yet" is
true, visible, and exactly what ⚪ means.

## CIR-PROC-PHASE-P1 — the nightly bake <a id="cir-proc-phase-p1"></a>

| description | inputs | expected |
|---|---|---|
| P1 implements `freshness:` and `command:` | the fixture person | lights come from the sources |
| the schedule is external | nightly run | the job runs elsewhere; this repo owns the code it runs, not the scheduler ([CIR-Q-33](#cir-q-33)) |
| a failed nightly run does not publish | config error or crash | the previous artifact stays; it ages into the stale banner ([CIR-BAKE-STALE-SELF](../data/data-json.md)) |
| the stale banner is a P0 requirement, not a P1 one | P0 page | shipped from the start — a page that cannot say "I am old" is dangerous-green the moment bakes exist |
| P1 adds no config keys | P0 config | unchanged |

## CIR-PROC-PHASE-P2 — the first annotated timeseries <a id="cir-proc-phase-p2"></a>

| description | inputs | expected |
|---|---|---|
| P2 adds a metric source and a detail page | one item | [CIR-DETAIL-PAGE-SHAPE](../render/detail-page.md) |
| P2 does not change the sunburst contract | main page | unchanged; the detail page is reachable, not required |
| a sqlite-backed metric is one metric source among several | sqlite item | no sqlite assumption leaks into the page or the artifact schema |

## CIR-PROC-DEPLOY-SEAM — how a real person's data reaches a deployed page <a id="cir-proc-deploy-seam"></a>

This repo is public and may contain **only synthetic data** (`CLAUDE.md`), while the deployable
unit is an nginx image whose content is `COPY public/`. Nothing states how a real person's
`circles.yaml`, their note sources, or their baked artifact get into a running deployment.
Until it is stated, every phase above is undeployable for its actual purpose.

| description | inputs | expected |
|---|---|---|
| no real config is ever committed here | any PR | synthetic only; the gate's secret scan is not the control that enforces this — review is |
| the image is buildable from this repo alone | CI build | the fixture person's page builds and serves, so the pipeline is provable without real data |
| real content enters at deploy time | a real deployment | via a mechanism named in the chart's values, not by rebuilding this repo's image with private files |
| the chart declares the seam | `values.schema.json` | whatever the mechanism is, it is authoritative there ([CLAUDE.md](../../CLAUDE.md) read order) |
| the person's sources are not in the cluster by accident | freshness sources | whatever mounts them is deliberate and stated |

The chart today has no volume, ConfigMap or init step for any of this. That gap is a follow-up
for the chart and for circles-iac, not something a spec PR can fix — but a spec tree that
described the bake without saying where its inputs live would be describing a demo.

⚖ **CIR-Q-33 — where does the bake run, and how does its output reach nginx?**<a id="cir-q-33"></a>
Options: (a) the bake runs in a private repo/job holding the person's config and notes, and
publishes an artifact the chart mounts (private data never touches this repo or its image);
(b) the bake runs as an init container or sidecar in the deployment, with the config and notes
mounted from a Secret/PVC (one moving part, but private notes end up in the cluster);
(c) the bake produces a per-person image built by a private pipeline `FROM` this repo's image.
*Recommendation: (a)* — it keeps the public repo's image generic and testable with the fixture
person, keeps note repositories where they already live, and makes the chart's only new surface
a mount path. (b) is the fastest to build and the hardest to undo.

## CIR-PROC-NOT-YET — what specs deliberately do not decide <a id="cir-proc-not-yet"></a>

Named so a later pass does not mistake silence for oversight:

| deferred | why |
|---|---|
| authentication and who may see a page | deploy-time concern (circles-iac), not a property of the artifact ([CIR-BAKE-EXPOSURE](../data/data-json.md)) |
| multiple people per deployment | one config, one page; nothing in the artifact prevents a second deployment |
| history / trend of statuses over time | the artifact is a snapshot; a status history is a different product, and P2's timeseries is about *metrics*, not lights |
| editing the config from the page | the config is a file in a git repo, on purpose |
| notifications when an item turns red | a page that is looked at is the product; alerting is a separate decision with its own failure modes |
| contributed built-in adapters | the interface is fixed ([CIR-ADAPT-CONTRACT](../data/adapters.md)); the registry is not ([CIR-Q-15](../data/adapters.md)) |
