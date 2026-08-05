# specs/ — the circles contract

The approved-not-authored spec system this stack's agent loop runs on (the same shape
oracle-fleet and sleep-tracking use): **specs are the contract, code converges on them.**
Agents author spec PRs; a human approves every spec merge. The authoring PURPOSE is finding
gaps, contradictions, and ambiguities in the intended system — a spec that merely restates an
issue has failed.

## Tree

- `README.md` — this file: structure + conventions.
- `glossary.md` — every domain term, one definition each.
- [open-questions.md](open-questions.md) — the index of every ⚖ AMBIGUITY in the tree, one row
  each, with the ruling the specs currently encode. **Read it first** to see what is settled by
  judgment rather than by the goal, and what a different answer would change.
- `data/` — the data model:
  - [data/circles-yaml.md](data/circles-yaml.md) — the person's configuration schema: rings,
    items, adapters, identity, link safety, validation.
  - [data/status-resolution.md](data/status-resolution.md) — how an item's light is resolved;
    the failure algebra (tooling failure ⇒ ⚪ + warning, never 🔴); config error vs adapter
    failure.
  - [data/freshness.md](data/freshness.md) — the freshness adapter: sources, date parsing, the
    two windows, edge cases (empty/missing/future dates, timezone anchoring).
  - [data/adapters.md](data/adapters.md) — the adapter interface contract and the v0 taxonomy
    (`manual:` / `freshness:` / `command:`), plus the plug-in seam for later built-ins.
  - [data/data-json.md](data/data-json.md) — the baked render input the page consumes
    (statuses, detail lines, generated-at stamp, warnings) and the bake that writes it.
- `render/` — the page:
  - [render/sunburst.md](render/sunburst.md) — sunburst geometry: ring order, the independent
    ring partition, arc subdivision and shares, labels, capacity.
  - [render/layout.md](render/layout.md) — the one-screen / A4 constraints as testable
    requirements; asset self-containment; boot-failure behavior.
  - [render/colors.md](render/colors.md) — the status palette, ⚪ visibility, the greyscale
    luminance ladder, print survival, the legend.
  - [render/interactions.md](render/interactions.md) — hover/focus/tap detail, click targets,
    keyboard and screen-reader paths over baked data.
  - [render/detail-page.md](render/detail-page.md) — the generic annotated timeseries
    (metric × dated events). P2 boundary only.
- `process/` — how the contract is kept:
  - [process/testing.md](process/testing.md) — the ruled test-tier terminology, how
    decision-table rows link to tests, and the spec-tree gate.
  - [process/phases.md](process/phases.md) — what P0/P1/P2 each own, and what a phase may not
    assume.

## Requirement IDs

Stable anchors `CIR-<AREA>-<NAME>` (e.g. `CIR-DATA-FRESHNESS-WINDOW`) — one requirement, one
anchor; tests and issues reference the ID verbatim. **IDs are never renamed or reused**; a
requirement may move between pages (the ID follows it, the old page keeps a pointer), and a
requirement that changes meaning gets a new ID with the old one marked superseded in place.

The area vocabulary is **closed** — ruled once (⚖-R22) so parallel authors cannot mint
divergent areas and stop IDs being stable anchors. A new area is a spec change, not an
authoring choice:

| area | owns | pages |
|---|---|---|
| `CIR-DATA-*` | `circles.yaml` schema, identity, validation, status resolution, freshness | `data/circles-yaml.md`, `data/status-resolution.md`, `data/freshness.md` |
| `CIR-ADAPT-*` | the adapter interface every status source implements, and the v0 taxonomy | `data/adapters.md` |
| `CIR-BAKE-*` | the bake step and the `data.json` artifact it writes | `data/data-json.md` |
| `CIR-RENDER-*` | geometry, layout, colour, interaction of the one page | `render/sunburst.md`, `render/layout.md`, `render/colors.md`, `render/interactions.md` |
| `CIR-DETAIL-*` | the annotated-timeseries detail view | `render/detail-page.md` |
| `CIR-PROC-*` | test tiers, the spec gate, phase boundaries | `process/testing.md`, `process/phases.md` |

## Conventions

- **Decision tables over prose** wherever behavior branches: visible `inputs || expected` rows,
  each row's description usable as a test id verbatim. The synthetic fixture person under
  `fixtures/` supplies the key examples — spec rows and fixture rows are the same doctrine.
- **⚖ AMBIGUITY entries are first-class**: a judgment call is recorded with its options and a
  recommendation, never silently decided. Each carries an id `⚖-R<NN>` so the index in
  [open-questions.md](open-questions.md), a follow-up issue, and a review comment can name the
  same thing. The **ruling is what the surrounding requirement already encodes** — a
  requirement is never left blank pending an answer; the ⚖ records what would change if the
  answer differs.
- **Verified-ness is derived, never declared**: no ✓/🚧 markers claiming coverage — a
  requirement without a linked test is simply unevidenced.
- **Synthetic data only**: this repo is public; every example, fixture row, and spec value is
  invented. Real people's data is deploy-time content and never appears here.
- **Row ids are join keys, not prose** (ruled 2026-08-04, from the FU-126 arm comparison):
  every decision-table row carries a stable, human-authored intent id in its first column
  (kebab or short intent phrase — `palette-luminance-ladder`, `"missing challenge"`). That id
  is the evidence join key: spec row → test case id → report story fragment → rendered back
  under this heading. A row whose id changes orphans its evidence; renames follow the same
  discipline as requirement IDs. A test cites its row as `CIR-<AREA>-<NAME>#<row-id>` verbatim.
  **Ids are correlational by default; a meaning-bearing label is a judgment call, not a sin**
  (ruled 2026-08-04): prefer tables that read complete with the id column deleted, but when
  reasoning a row out of its columns is disproportionate effort, the label may carry meaning —
  deliberately, sparingly, and as a flag for review attention.
  The double edge either way: a legible label is the cheapest thing to read, so it becomes the
  ONLY thing read, and the row's judgment stops being contested (the author thought; nobody
  after has to). **The defense lives in the projection layer, not in prohibition** — the
  markdown source is the complete document, every render a disposable projection (same family
  as evidence-collapsed-by-default): human renders may demote ids to hover/tooltips beside the
  cells; review and verification projections strip ids — wholly, or sampled (e.g. half the
  rows) — so blind re-derivation from `inputs || expected` stays structural rather than a
  discipline. A derivation↔label mismatch is the named defect class **label laundering** (the
  fan-out's "defective rulings" were exactly this, caught by judges that recounted instead of
  reading labels).
- **Every table names its world.** Expected behavior is a function of (system, world); a table
  that doesn't name its fixture set lies by omission. v0 has ONE world — the fixture person
  `alex` (`fixtures/`) — declared once per page ("World: alex") until a second world exists;
  from then on it's a column. Future worlds are named YAML personas (`specs/worlds/`), the
  IdP/oracle convention; evidence row identity is **(rule ID, world, case)**.
- **Doctrine slots are first-class.** Each requirement may carry 1–3 short normative
  invariant sentences above its table — negative space and policy ("no default-to-green path
  exists anywhere", "a failing adapter never inherits its last light"). Doctrine is the
  judgment layer: review flags it for attention, tests enforce it via census/audit-style rows
  where possible, and it is never flattened into pseudo-rows to look mechanical.
- **External claims carry citations.** A requirement that rides an external source states it:
  `External: MUST — <spec/section or URL>`. A claim from training knowledge that no ride
  verified is marked as such (provenance notes) — never presented as checked.

## The tie-breaker: dangerous-green

**Any path by which an item shows 🟢 while its data is absent, stale, unparsed, mistyped, or
never evaluated is a defect class, not a trade-off.** Every rule in this tree that could tip
either way tips away from green — toward ⚪ or 🟡 plus a visible warning. Where two readings of
the goal issue are otherwise equally defensible, this is what decides.

This is a derivation, not an invention: the goal fixes "grey is *honest and visible* — the
unmonitored surface must be readable at a glance, never hidden or defaulted to green", and
fixes tooling failure as ⚪ + warning rather than 🔴. Dangerous-green is that doctrine stated
once, at the top, so the rest of the tree can appeal to it instead of re-deriving it per page.

## Evidence — the contract, with the format deliberately unpinned

Every requirement section is born evidence-ready and honestly unverified:

- Until a linked test exists, the section ends with the literal line
  `_Evidence: none yet — unverified._` — the visible-grey doctrine applied to the spec itself.
- When evidence lands it replaces that line with a collapsed block (`<details>`): a transcluded
  per-rule fragment + a link into the archived report. **Links are relative** so each published
  site (master, per-PR preview) shows *its own run's* evidence, never master's.
- The join contract is fixed NOW; the fragment **format is deliberately not**: story/test id ==
  rule id exactly, case id == row id, identity == (rule, world, case), report digest-stamped.
  The SVG fragments oracle uses are a Confluence-era relic under active rethink
  (allure-behavior-snippets#6) — the successor should be markdown-embedded and
  machine-validatable (agents/reviewers parse it, not just view it), likely a generated table +
  JSON sidecar. Circles specs must not bake any SVG assumption in; only the anchors and ids
  above, so the format swaps under stable joins.
- **Framework-neutral by construction**: circles evidence is pytest+Allure, the IdP's will be
  Spock+Allure (tara-test lineage). Everything the spec relies on lives in spec text + the
  Allure result JSON (`behaviors.json` post-processing — ids, categories, tags — is an accepted
  lever), never in a framework-specific feature.

Circles is the cheap rehearsal of this exact chain before the IdP runs it for real
(rule → intent row → named world → fragment → digest-stamped report — the auditor's
traceability chain).
