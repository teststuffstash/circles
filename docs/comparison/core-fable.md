# Core metric — spec-arm comparison (judge: fable)

Mission: [#6](https://github.com/teststuffstash/circles/issues/6) · goal under comparison:
[#1](https://github.com/teststuffstash/circles/issues/1) · arms: `opus`, `kimi-k3`,
`deepseek-v4-flash-0731`, `mimo-v2.5-pro`.

This is a **cherry-pick map, not a ranking**. The operator merges pages across arms; "arm X wins"
is not an output of this document. Scores exist only to justify per-page picks.

## Blind decision-point checklist (phase 0)

Built from goal issue #1 + `origin/master` (`specs/README.md`, `specs/data/circles-yaml.md`,
`specs/glossary.md`, `fixtures/alex/**`, `chart/**`, `scripts/ci.sh`, `public/index.html`,
`devbox.json`) **before opening any arm branch**. This is the independent coverage rubric: every
point below is a place where the goal issue leaves a real decision open — a contradiction, an
unstated constraint, or a judgment call. It is deliberately not a list of "topics the spec should
cover"; restating the issue covers topics and still scores zero here.

Legend: **[C]** contradiction inside the goal · **[U]** unstated constraint the product cannot be
built without · **[J]** judgment call the goal defers · **[S]** defect already present in the seed
repo (master) that the spec pass should have caught.

### Area DATA — config + status resolution

| id | decision point | kind |
|---|---|---|
| DP-01 | Threshold boundary: at *exactly* `yellow_after` days, is the item 🟢 or 🟡? (same at `red_after`) — inclusive/exclusive, the classic off-by-one, and directly testable | U |
| DP-02 | Timezone/DST anchoring of "days old": whose clock, and are "days" calendar days or 24h spans? (seed ⚖'s it) | J |
| DP-03 | Date formats recognized inside a freshness source, and *where* in the file a date may appear (line prefix, anywhere, frontmatter) — fixture uses `- YYYY-MM-DD — …` bullets (seed ⚖'s it) | U |
| DP-04 | Future-dated entries: a source line dated tomorrow — freshest, ignored, or clamped/warned? | U |
| DP-05 | `share` weights: must they sum per ring, and what happens when some siblings set `share` and others don't (mixed)? (seed ⚖'s it) | J |
| DP-06 | Sibling ordering within a ring: config order, alphabetical, or by status severity? Fixture's `◀ Nova` / `Kit ▶` labels encode an *adjacency intent* that only config order preserves (seed ⚖'s it) | J |
| DP-07 | Two adapters declared on one item (`manual:` + `freshness:`) — schema error, or precedence? Seed says "exactly one" but not what violating it does | U |
| DP-08 | Glob matching zero files vs. a file that exists but contains no parseable date — same ⚪+warning, or distinguishable? | U |
| DP-09 | `yellow_after` ≥ `red_after` (misconfiguration) — validation error, or resolve-and-warn? | U |
| DP-10 | `command:` execution contract: working directory (fixture's `./notes/plants-status.sh` is relative to the config dir, never stated), timeout, environment, stdout matching (case/whitespace), stderr handling | U |
| DP-11 | `command:` exit 0 but unparseable stdout — ⚪+warning (tooling broke) or a hard error? Seed only rules on exit≠0 | U |
| DP-12 | `command:` is arbitrary code execution against a person's machine/bake job — trust boundary, sandboxing, secrets. The goal introduces the escape hatch and says nothing about who may write one | U |
| DP-13 | `id` uniqueness scope: globally unique or per-ring? IDs are the anchor tests and `data.json` key off | U |
| DP-14 | Whole-file failure (unparseable `circles.yaml`, schema violation): the ⚪+warning doctrine is stated per *item* — the goal never rules on config-level failure. Does the page render partially or not at all? | U |
| DP-15 | Degenerate configs: zero rings, a ring with zero items, a single item in a ring (full 360° arc) | U |
| DP-16 | `link:` value space: `url-or-path` — how does a path resolve from a statically-served page? | U |

### Area STATUS — semantics beyond the per-item light

| id | decision point | kind |
|---|---|---|
| DP-17 | Do rings themselves have a colour? The goal says "**every cell** is colored by its status light" while rings are composed *of* item arcs — is there a ring-level summary arc, and if so is it derived (worst-child? weighted?) or configured? The single biggest structural gap in the goal | C |
| DP-18 | Does ⚪ participate in any aggregation, and how? (worst-of over {🟢🟡🔴⚪} has no total order — ⚪ is not "between" anything) | U |
| DP-19 | "Triage reads inward-first" — doctrine only, or a computed/testable output (an ordered act-on-this-first list)? | J |
| DP-20 | Build warnings: *where do they surface*? `data.json` field, build log, or visibly on the page? The goal mandates warnings but names no destination — and any on-page surface competes with the one-screen budget | U |
| DP-21 | Meta-freshness: `data.json` carries a generated-at stamp, but the goal gives it no semantics. Bake hasn't run in N days → is the whole page stale, and does that show? (Note: this is the one legitimate case for a non-item-level signal, and it must not be 🔴 by the same "tooling ≠ act" rule) | U |
| DP-22 | The ⚪ surface "must be readable at a glance" — as an aggregate property (how much of the picture is unmonitored), not just per-arc contrast. Is there a testable measure? | J |

### Area RENDER — geometry, legibility, interaction

| id | decision point | kind |
|---|---|---|
| DP-23 | "One screen" against *which* viewport? A floor (min width/height) must exist or the requirement is untestable | U |
| DP-24 | One-screen vs. "phone-first read-only viewing is the later exposure path": a layout that fits one desktop screen and one A4 does not fit a 390px phone. Is the phone a P0 constraint or explicitly deferred? | C |
| DP-25 | A4 orientation (portrait/landscape), margins, and whether print is a separate stylesheet or the same layout | U |
| DP-26 | **Traffic lights vs. greyscale print**: 🟢🟡🔴 collapse to near-identical greys on a mono printer, so "prints legibly to a single A4" and "colored by its status light" are in direct tension. Needs a redundant channel (pattern/label/lightness ladder) | C |
| DP-27 | Colourblind safety of the four-status palette (red/green deuteranopia is the majority case for a red/green traffic light) | U |
| DP-28 | Non-colour status encoding for screen readers / a11y — the same redundant-channel decision as DP-26/27 arriving from the other side | U |
| DP-29 | "One **self-contained** HTML page" vs. a sunburst library (Plotly ≈ 3MB+): the library must be vendored/inlined (no CDN, since a self-contained page must render offline) — an unstated constraint that materially bounds the library choice | C |
| DP-30 | Library selection criteria made concrete (Plotly acceptable / D3 / ECharts "if layout fights back") — what test decides "layout fights back"? | J |
| DP-31 | Label legibility inside thin arcs: rotation, truncation, ellipsis, minimum arc angle, and what happens to a ring with a dozen items | U |
| DP-32 | Ring thickness policy (equal bands vs. inner-thicker) and whether rings always span the full 360° | J |
| DP-33 | The centre hole: what occupies it (person name, legend, overall state, nothing) — the goal specifies `person:` but never places it | U |
| DP-34 | Legend: required? Where? Does it count against the one-screen/A4 budget? | U |
| DP-35 | Hover has no touch equivalent — "hover = detail line" directly contradicts the phone read-only path; needs a tap-reveals-then-tap-navigates rule or an always-visible alternative | C |
| DP-36 | Click precedence: "jump to the item's link, **or** open its detail page" — which wins when both exist, and what happens when neither does? | C |
| DP-37 | The detail page vs. "**don't design a multi-page app**" and "one self-contained HTML page": is the detail view a modal/overlay in the same document, a second document, or a route? | C |
| DP-38 | `data.json` schema: exact shape, whether it carries *structure* (rings/items/labels/guardrails) or only statuses — the page is "client-side over baked data", so structure must be baked too, but the goal lists only "statuses, detail lines, generated-at" | U |
| DP-39 | `data.json` versioning / forward-compat, and whether the page validates it before rendering | U |
| DP-40 | Annotated timeseries (P2): the intervention-events markdown table's location and column schema, and how a detail view is bound to an item | U |

### Area PROCESS — pipeline, deploy, testing, conventions

| id | decision point | kind |
|---|---|---|
| DP-41 | **The P0 build seam**: P0 has "statuses hand-set in config" and the glossary says "P0 has no bake" — yet the page renders from `data.json`. So *something* converts `circles.yaml` → `data.json` at P0, or `data.json` is hand-authored. The goal never closes this and it is the first thing an implementer hits | C |
| DP-42 | Where does a **real** person's `circles.yaml` live and how does it reach the image? CLAUDE.md forbids committing real data here; the chart mounts nothing (`values.schema.json` has no data hook) and the Dockerfile bakes `public/`. Deploy-time content has no declared path | U |
| DP-43 | If content is deploy-time, what triggers a rebuild/redeploy on content change, given `deploy.yaml` stamps chart version == appVersion == image tag? | U |
| DP-44 | **Exposure/authn**: "the person and people they trust can see it" — the chart has a Service and no Ingress, and a life-status page is sensitive. Who can reach the deployed page is undecided | U |
| DP-45 | P1 bake job contract: the goal says the job "runs elsewhere; this repo owns the code it runs" — inputs, outputs, exit codes, where `data.json` is published, and how failure is reported back | U |
| DP-46 | Adapter plug-in seam: "design the adapter interface so [contributed built-ins] plug in **without touching the page**" — registration, discovery, and `circles.yaml` schema evolution as a testable contract | U |
| DP-47 | Test tiers (unit / system-on-kind / e2e) mapped to *actual* commands and to `scripts/ci.sh`, which is declared "the one place the gate grows"; `kind` is already in `devbox.json` | U |
| DP-48 | The decision-table→test linkage made mechanical: row description **is** the test id, verbatim — how that is enforced rather than hoped for | J |
| DP-49 | Which parts of the product run where (bake language/runtime) — `python@3.11` + `uv` are already pinned in `devbox.json`, so the repo has already half-decided | J |
| DP-50 | **Time-decaying fixture**: `fixtures/alex/notes/sleep-log.md` carries hard dates (2026-08-01…) and is the "freshness inside window → 🟢" key example with `yellow_after: 7`. The committed fixture silently flips 🟢→🟡→🔴 as the calendar advances; `fixtures/README.md` says tests "build inputs FROM these tables at runtime" and the sleep log itself hints dates may be rewritten. The spec must rule that freshness examples are *relative*, or the key example rots | S |
| DP-51 | **The glossary already violates its own rule**: `specs/README.md` mandates "one definition per term, no synonyms", and `glossary.md`'s first entry is "**circle / ring**" — two names, one definition. The goal issue then adds a third surface word, "cell" ("every cell is colored"). The spec pass should have picked one and said so | S |
| DP-52 | `CIR-<AREA>-<NAME>` id grammar: the area vocabulary is never enumerated, so parallel authors invent divergent areas and ids stop being stable anchors | U |
| DP-53 | Whether requirements carry phase (P0/P1/P2) markers at all — the mechanism for "anticipate, not overreach" is itself undecided, and it is what keeps P2 detail from being written as though it were settled | J |
| DP-54 | "Verified-ness is derived, never declared" — no ✓/🚧 coverage markers anywhere in the authored tree (a compliance check, and an easy one to fail while writing status tables) | U |

**54 decision points.** Areas: DATA 16 · STATUS 6 · RENDER 18 · PROCESS 14.

<!-- PHASE 1+ APPENDED BELOW -->
