# Open questions — the ⚖ register

Every judgment call in this tree, indexed once. A ⚖ entry records a decision the goal issue left
open, the options, and **the ruling the surrounding requirement already encodes** — a requirement
is never left blank pending an answer. This page is the operator's agenda: to overrule any
ruling, change it here and in the requirement that encodes it.

Numbering follows the FU-126 comparison register (⚖-R1…R22 keep the numbers the judge reports
used, so a review comment naming ⚖-R6 means the same thing across repos and reports); R23–R49
were minted during the weave; R50 and above during the P0 build harvest (issue #27), where the
first implementations put the contract under load.

## Read these first

Six entries change the product rather than a detail, and three of those go against either the
goal issue or the majority of the fan-out. They are where review attention is worth spending.

| # | question | ruling | why it needs your eye |
|---|---|---|---|
| ⚖-R1 | Where the private config lives, and how its output reaches nginx | the seam is specified here; the mechanism belongs in a circles-iac ADR | **nothing is deployable for its actual purpose until this is ruled**, and it is deliberately not ruled inside this repo |
| ⚖-R3 | Is Plotly usable at all? | no — hand-rolled SVG | **an explicit override of issue #1**, which names Plotly first. Every other render requirement sits on top of it |
| ⚖-R6 | Is age exactly `yellow_after` still 🟢? | yes (`>`, not `≥`) | **1-of-4 minority ruling.** Cheap to flip (three rows) but only before tests exist |
| ⚖-R11 | Link or detail page, when an item has both? | the configured `link` wins | goes against the chassis arm; three arms gave three answers |
| ⚖-R28 | The fixture's `◀ Nova` / `Kit ▶` glyphs | decoration, no geometric meaning | the fixture visibly disagrees with the ruled sweep direction; nobody in the fan-out noticed |
| ⚖-R46 | Should a metric be able to *set* a status? | not in P2 as specified — opened as a product question first | it would be the first adapter whose light means "your data says act" |

## The register

| # | question | ruling | encoded in |
|---|---|---|---|
| ⚖-R1 | private config location + publish path | seam specified; CronJob-to-volume recommended, decision in circles-iac | [`CIR-PROC-DEPLOY-SEAM`](process/phases.md) |
| ⚖-R2 | the P0 build seam | a bake exists at P0, `manual:` only; other adapters ⚪ + "not evaluated" | [`CIR-PROC-PHASE-P0`](process/phases.md) |
| ⚖-R3 | the renderer | hand-rolled SVG; Plotly cannot express independent rings | [`CIR-RENDER-RENDERER`](render/layout.md) |
| ⚖-R4 | inline the data or fetch it | inline, plus a sibling `data.json` | [`CIR-BAKE-SELF-CONTAINED`](data/data-json.md) |
| ⚖-R5 | detail view: separate page or in-page overlay | separate baked static files — no routing, so not a "multi-page app" | [`CIR-DETAIL-PAGE-SHAPE`](render/detail-page.md) |
| ⚖-R6 | freshness boundary inclusivity | `>` — the boundary day keeps the better light | [`CIR-DATA-FRESHNESS-WINDOW`](data/freshness.md) |
| ⚖-R7 | unknown keys in `circles.yaml` | ignore + warn, **except** inside `status:` where they fail | [`CIR-DATA-VALIDATION`](data/circles-yaml.md) |
| ⚖-R8 | future-dated entries | excluded with a warning; all-future ⇒ ⚪ + warning | [`CIR-DATA-FRESHNESS-FUTURE`](data/freshness.md) |
| ⚖-R9 | ring rollup, and what fills the centre | no rollup; the hole carries name, stamp and counts | [`CIR-RENDER-SUMMARY`](render/sunburst.md) |
| ⚖-R10 | ring radial thickness | non-increasing outward — inner bands at least as thick | [`CIR-RENDER-RING-THICKNESS`](render/sunburst.md) |
| ⚖-R11 | click precedence | the configured `link` wins; the loser stays reachable | [`CIR-RENDER-CLICK`](render/interactions.md) |
| ⚖-R12 | mixed declared/undeclared `share` | relative weights, undeclared = 1, **plus a build warning** | [`CIR-DATA-SHARE`](data/circles-yaml.md) |
| ⚖-R13 | a ring with no items | renders as an empty band + warning; zero rings is a config error | [`CIR-DATA-VALIDATION`](data/circles-yaml.md) |
| ⚖-R14 | where build warnings surface | the artifact **and** the page | [`CIR-BAKE-WARNINGS`](data/data-json.md) |
| ⚖-R15 | stale-bake banner | threshold declared by the artifact, `null` at P0 | [`CIR-BAKE-STALE-SELF`](data/data-json.md) |
| ⚖-R16 | `link:` value space | `https?` and root-relative only; dangerous schemes fail at bake | [`CIR-DATA-SCHEMA-LINK`](data/circles-yaml.md) |
| ⚖-R17 | item-id uniqueness scope | unique per ring; the ref is `<ring>/<item>` | [`CIR-DATA-IDENTITY`](data/circles-yaml.md) |
| ⚖-R18 | timezone anchoring | per-config IANA `timezone:`, default UTC | [`CIR-DATA-AGE-CALENDAR`](data/freshness.md) |
| ⚖-R19 | artifact status vocabulary | `green` / `yellow` / `red` / `grey`, distinct from display words | [`CIR-BAKE-STATUS-VALUES`](data/data-json.md) |
| ⚖-R20 | detail line baked or composed | both; the baked string is authoritative | [`CIR-BAKE-DETAIL-FIELDS`](data/data-json.md) |
| ⚖-R21 | command timeout and bake budget | 30 s per item, 5 min total, both fixed in v0 | [`CIR-ADAPT-BUDGET`](data/adapters.md) |
| ⚖-R22 | requirement-ID area vocabulary | six closed areas: DATA, ADAPT, BAKE, RENDER, DETAIL, PROC | [README.md](README.md) |
| ⚖-R23 | "circle" vs "ring" vs "cell" | `ring` is the spec term, `circle` the product word, `cell` the rendered arc | [glossary.md](glossary.md) |
| ⚖-R24 | the fixture's decaying freshness examples | declare a fixture reference date; examples are relative to it | [`CIR-PROC-TEST-FIXTURES`](process/testing.md) |
| ⚖-R25 | `spec_version` per-file or per-adapter | one integer for the whole file | [`CIR-DATA-SCHEMA-VERSION`](data/circles-yaml.md) |
| ⚖-R26 | a concern belonging to two rings | duplication in v0; an `alias:` form is the named growth path | [`CIR-DATA-IDENTITY`](data/circles-yaml.md) |
| ⚖-R27 | recognized date notations | ISO 8601 only | [`CIR-DATA-DATE-PARSE`](data/freshness.md) |
| ⚖-R28 | the fixture's directional glyphs | decoration; label content never influences geometry | [`CIR-RENDER-SIBLING-ORDER`](render/sunburst.md) |
| ⚖-R29 | do outer rings nest? | no — independent partition, every ring spans 360° | [`CIR-RENDER-RING-PARTITION`](render/sunburst.md) |
| ⚖-R30 | should "deliberately unmonitored" be declarable | inferred from absence now; `strict_coverage:` later | [`CIR-DATA-GREY-REASON`](data/status-resolution.md) |
| ⚖-R31 | a source with no usable dates | ⚪ + warning, never 🔴 | [`CIR-DATA-FRESHNESS-EMPTY`](data/freshness.md) |
| ⚖-R32 | may `command:` return more than a word | status word only; `key=value` lines are the compatible extension | [`CIR-ADAPT-COMMAND`](data/adapters.md) |
| ⚖-R33 | how contributed built-ins plug in | in-process for this repo; `command:` is the whole third-party story | [`CIR-ADAPT-NO-PAGE-LOGIC`](data/adapters.md) |
| ⚖-R34 | detail-data packaging | per-item payload files, `details/<ring>--<item>.json` | [`CIR-BAKE-DETAIL-FILES`](data/data-json.md) |
| ⚖-R35 | outgrowing one legible screen | documented envelope + build warning + graceful elision | [`CIR-RENDER-CAPACITY`](render/sunburst.md) |
| ⚖-R36 | sibling ordering | config order, clockwise from 12 o'clock | [`CIR-RENDER-SIBLING-ORDER`](render/sunburst.md) |
| ⚖-R37 | which viewport is "one screen" | 1280 × 800 CSS px | [`CIR-RENDER-REFERENCE-VIEWPORT`](render/layout.md) |
| ⚖-R38 | below the reference viewport | always scale to fit; never scroll | [`CIR-RENDER-ONE-SCREEN`](render/layout.md) |
| ⚖-R39 | A4 orientation and page box | portrait, `@page { margin: 10mm }` | [`CIR-RENDER-A4`](render/layout.md) |
| ⚖-R40 | which hues | colourblind-aware, luminance-separated; statuses stay green/yellow/red/grey | [`CIR-RENDER-PALETTE`](render/colors.md) |
| ⚖-R41 | dark mode | light theme only in v0 | [`CIR-RENDER-PALETTE`](render/colors.md) |
| ⚖-R42 | how loud the stale treatment is | banner + desaturation + hatch | [`CIR-RENDER-STALE-MARK`](render/colors.md) |
| ⚖-R43 | what a tap does | first tap reveals, second tap activates | [`CIR-RENDER-TOUCH`](render/interactions.md) |
| ⚖-R44 | how much works without JS | text alternative is the floor; a baked static chart is the target | [`CIR-RENDER-NO-JS`](render/interactions.md) |
| ⚖-R45 | one detail page per item, or parameterized | one baked file per item | [`CIR-DETAIL-PAGE-SHAPE`](render/detail-page.md) |
| ⚖-R46 | does `metric:` reuse the adapter interface | parallel `metric:` block for P2; status-from-metric opened first | [`CIR-DETAIL-SERIES`](render/detail-page.md) |
| ⚖-R47 | the events-table contract | deliberately unruled; specified at P2 kickoff | [`CIR-DETAIL-EVENTS`](render/detail-page.md) |
| ⚖-R48 | where browser checks live in the ruled tiers | system testing | [`CIR-PROC-BROWSER-EVIDENCE`](process/testing.md) |
| ⚖-R49 | the bake's implementation language | Python, as `devbox.json` already pins | [`CIR-PROC-BAKE-ONE-PATH`](process/phases.md) |
| ⚖-R50 | the wire value for phase-unevaluated adapters | `grey_reason: not-evaluated`, a third value | [`CIR-DATA-GREY-REASON`](data/status-resolution.md) |
| ⚖-R51 | the grey status word in detail lines | always `unmonitored`; the reason follows as its own segment | [`CIR-DATA-GREY-REASON`](data/status-resolution.md) |
| ⚖-R52 | overlapping validation checks | most-specific error wins; every row independently triggerable | [`CIR-DATA-IDENTITY`](data/circles-yaml.md) |

## What the fan-out missed entirely

Recorded because a gap no arm found is worth more attention than a gap four arms argued about.

1. **The glossary violated the rule it sits under.** `specs/README.md` mandates "one definition
   per term, no synonyms", and the seed glossary's first entry was `circle / ring`. All four arms
   copied it verbatim, and three compounded it by adding further near-synonyms. Fixed by ⚖-R23.
2. **Nothing gated the fixture against the authored schema.** No arm proposed a check that
   `fixtures/alex/circles.yaml` validates against the schema its own specs describe, or that its
   sources resolve — the cheapest possible guard against spec/fixture drift. Now part of
   [`CIR-PROC-SPEC-GATE`](process/testing.md).
3. **The fixture's directional glyphs encode a placement intent nobody reconciled.** ⚖-R28.
4. **The bake's runtime was already half-decided and unstated.** ⚖-R49.

## Provenance

This register is the deduped output of the FU-126 arm comparison (issue #6): the judge reports
`docs/comparison/core-gpt-5.6-terra.md` and `docs/comparison/core-fable.md` supplied the
cross-arm splits, and the four downstream-proxy reports supplied the builder-facing gaps. Where
this page says "the fan-out split 3:1", that count is from those reports, not re-derived here.

R50–R52 and the amendments beside them (the palette green, the hover-row format, the
reference-date defaults, the browser-proxy note) are the harvest of the P0 build experiment
(issue #27): the one-shot arm (PR #21) and the fan-out arm (PRs #24/#26) each built the P0 MVP
against this tree, and their PR bodies and reviews supplied the findings. Both implementations
were deliberately discarded — the findings folded back here are the experiment's yield, and this
tree is what the next build starts from.
