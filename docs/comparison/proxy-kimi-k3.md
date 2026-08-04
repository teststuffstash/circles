# Downstream proxy: kimi-k3 arm

**Spec completeness checklist for the `research/issue-1-kimi-k3` arm, read as the sole
product source for a P0 build.** Every question a builder needs answered before implementing
— and what the spec answered so well no question survived.

---

## Verdict (counts: blockers / judgment calls / minors / answered-by-⚖)

| metric | count |
|---|---|
| **blockers** | 0 |
| **judgment calls** | 8 |
| **minors** | 3 |
| **answered-by-⚖** | 26 |

**P0 buildable with confidence.** No true blockers: the tree's decision tables, schema
definitions, and ⚖ recommendations are detailed enough that a builder can implement the
bake and the page without guessing product policy. Every ambiguity the tree itself
identified is recorded as an ⚖ entry with a clear recommendation. The 8 judgment calls
below are genuinely buildable — a builder would make internally-consistent choices —
but they are silent product-policy decisions the human author may wish to confirm.

---

## Blockers

**None.** Every requirement that P0 must land has at least one decision table or schema
definition a builder can implement against. The following were examined and found sufficient:

- **circles.yaml schema** — field-by-field decision tables with validation rules,
  required/optional, and ⚖ for the open semantic questions.
- **data.json schema** — explicit field table, wire values, nullability, versioning.
- **Status resolution** — full adapter×outcome table; the failure algebra (tooling failure
  ⇒ ⚪ + warning, never 🔴/🟢) is unambiguous.
- **Freshness window** — boundary-day-belong-to-worse-status rule spelled out in rows.
- **Command execution** — stdout contract, exit-code dominance, edge cases.
- **Sunburst geometry** — share→angle formula, independent partition, sibling order,
  label elision rules.
- **Color palette** — pinned hexes, luminance ladder with pairwise ≥0.10 gap, label
  contrast requirements.
- **Layout** — reference viewport, one-screen invariance (chart scales), print contract,
  boot-error states.
- **Phase boundaries** — P0/P1/P2 scoped with explicit must-not-build lists.

A builder would reach for implementation without being blocked by missing knowledge.

---

## Judgment calls

*Buildable, but the builder would be silently deciding product policy. Each choice
affects the user-visible product but has no spec anchor to verify against.*

### J1. Bake CLI interface

**Where I looked:** `process/phases.md` (CIR-PHASE-BAKE-ONE-PATH), `data/data-json.md`
(CIR-DATA-DATAJSON-ATOMIC-WRITE). The bake is the central P0 artifact, invoked at image
build time and later by a scheduler. Its interface is never specified.

**What I'd build:** `bake <config-dir>` — reads `circles.yaml` from the given directory,
writes `data.json` into the same directory. No flags, no env vars. Atomic write via temp
file + rename in the output directory. This is the simplest interface; a `--output` flag
could be added later if the nightly bake (P1) needs a different output path. But I am
deciding the naming, the positional vs flag style, and the default output location with no
spec guidance.

### J2. Inter-cell gap size

**Where I looked:** `render/sunburst.md` (CIR-RENDER-GEOM-ARC-SHARE). "Uniform visual
gap" — "never so large that a single-item ring shows a visible notch."

**What I'd build:** 2 CSS pixels per side of each cell (4 px total gap between adjacent
cells). At the reference viewport (1280×800) a single-item ring would lose ~4 px out of
360°, invisible. For a 4-ring sunburst with equal thickness, each arc's angular range is
reduced by `4 / (2πr)` radians — negligible. But I am choosing the gap size, not the spec.

### J3. Text alternative generation: server-side vs client-side

**Where I looked:** `render/colors.md` (CIR-RENDER-A11Y-TEXT-ALTERNATIVE),
`render/layout.md` (CIR-RENDER-LAYOUT-PRINT-A4). "Generated from the same `data.json`" —
a requirement satisfied by both approaches.

**What I'd build:** Client-side generation from the parsed `data.json` at page load.
Rationale: (a) consistent with "client-side interactive over baked data" doctrine;
(b) no bake change needed; (c) the text alternative must be in the accessibility tree
and in print — a JS-generated list satisfies both when JS is on (the normal case).
The ⚖ NO-JS-FALLBACK vote for a `<noscript>` notice confirms JS is expected.
But the alternative approach (bake-time generation, inlined in HTML) would also satisfy
the requirement, and would survive no-JS.

### J4. Idle text for the detail strip

**Where I looked:** `render/layout.md` (CIR-RENDER-LAYOUT-CHROME). "Strip shows a neutral
idle line (e.g. 'hover a cell')".

**What I'd build:** `" — "` (an em-dash between thin spaces), matching the strip's
non-interactive aesthetic. No cell's content leaked into idle. But the exact text is not
specified — "hover a cell" is an example, not a requirement.

### J5. Visual layout of chrome elements

**Where I looked:** `render/layout.md` (CIR-RENDER-LAYOUT-CHROME). Chrome reading order is
specified (a11y tree), but visual positions (CSS layout) are not — sidebar vs footer vs
overlay, left vs right.

**What I'd build:** Single-column layout: title top-left, sunburst centered, ring key and
legend in a right sidebar (stacked), generated-at stamp bottom-right of the sidebar,
warnings banner above the chart, detail strip below the chart. This is one reasonable
layout — other builders would pick different arrangements.

### J6. Scale-to-fill implementation

**Where I looked:** `render/layout.md` (CIR-RENDER-LAYOUT-ONE-SCREEN). "The chart scales to
fill the space the chrome leaves over."

**What I'd build:** SVG with `viewBox` sized to a fixed coordinate system (e.g.
400×400 for the sunburst), CSS `width: 100%; height: auto; max-height: calc(100vh - chromeHeight)`.
The chrome elements' heights are measured dynamically via `ResizeObserver` to set the SVG
container's available height. This handles any viewport. Alternative: percentage-based
container with flex-grow. Both work; the spec doesn't choose.

### J7. Warnings banner expand mechanism

**Where I looked:** `render/layout.md` (CIR-RENDER-LAYOUT-CHROME), `data/data-json.md`
(CIR-DATA-DATAJSON-WARNINGS). "Expands to the full list."

**What I'd build:** Click the banner to toggle between the truncated view
("3 warnings — command exited 1") and the full expanded list. A small chevron icon
indicates expandability. This is interaction-pattern territory the spec delegates; the
builder chooses.

### J8. Minimum hover/focus target size

**Where I looked:** `render/sunburst.md` (CIR-RENDER-GEOM-DENSITY). "Every cell ≥ the
minimum hover/focus target" within the content envelope.

**What I'd build:** WCAG 2.1 Target Size minimum (24×24 CSS px) as the floor. WCAG
recommended (44×44) would be a tighter constraint on dense rings. The spec doesn't
pick a number, so the builder picks. The correct answer depends on what fits in a
6-ring × 8-item ring at the reference viewport — the builder discovers this during
implementation.

---

## Minors

*Small decisions the spec leaves open. Each has a trivial default, but they add up
to visual/behavioral surface the spec tree doesn't control.*

### M1. Font sizes

**Where I looked:** `render/sunburst.md` (CIR-RENDER-GEOM-LABELS), `render/colors.md`
(CIR-RENDER-COLOR-LEGEND), `render/layout.md` (CIR-RENDER-LAYOUT-CHROME). No font sizes
are specified for any page element.

**What I'd build:** Cell labels 11 px, legend 12 px, ring key 13 px, detail strip 14 px,
title 20 px, stamp 10 px. All system-ui stack. These fit at the reference viewport for
the content envelope; no constraint is violated.

### M2. Print-specific CSS: interactive element enumeration

**Where I looked:** `render/layout.md` (CIR-RENDER-LAYOUT-PRINT-A4). "Interactive-only
elements (the detail strip's live area, focus outlines) print as their static equivalents
or are omitted deliberately."

**What I'd build:** `@media print { .detail-strip { outline: none; } .warnings-banner
{ break-inside: avoid; } .focus-ring { display: none; } }`. The focus outline and live
detail-strip `:focus` state are the only interactive-only elements — the detail strip's
*content* (the last hovered cell) is useful on paper and should print as static text.
The builder enumerates these; the spec doesn't.

### M3. Generated-at stamp visual position

**Where I looked:** `render/layout.md` (CIR-RENDER-LAYOUT-GENERATED-AT-VISIBLE). "In a
fixed chrome position" — the position is unspecified within the composition.

**What I'd build:** Bottom-right of the right sidebar, below the legend, in 10 px text.
Small enough to not attract attention, visible enough to be found. A different builder
might put it below the chart.

---

## Answered by ⚖ (spec flagged it and recommended)

Every ⚖ AMBIGUITY entry in the tree records a judgment call the spec authors identified,
documented the options for, and recommended one path. The 26 entries below are **not gaps**
— they are the spec doing its job by flagging the ambiguity and resolving it with a
recommendation. The builder implements the recommendation and moves on.

| ⚖ slug | page | recommendation | notes |
|---|---|---|---|
| `SHARE-WEIGHT-SEMANTICS` | `data/circles-yaml.md` | (b) relative weights, normalized per ring | Keeps all fixture correct without edits |
| `UNKNOWN-KEYS` | `data/circles-yaml.md` | (b) ignore with build warning (except `status:` adapter keys) | Forward-compatible; typos surface |
| `EMPTY-RING` | `data/circles-yaml.md` | (a) validation error | Half-written config catches early |
| `PAGE-STALENESS-BANNER` | `data/data-json.md` | (a) display stamp only in v0 | No schedule to compute staleness against |
| `WARNINGS-SURFACING` | `data/data-json.md` | (b) `data.json` + page banner | Honest-and-visible doctrine |
| `DETAIL-DATA-PACKAGING` | `data/data-json.md` | (a) per-item payload files (P2) | Keeps main payload lean |
| `DATE-FORMATS` | `data/freshness.md` | (a) ISO 8601 only | Unambiguous; no silent guessing |
| `FRESHNESS-TIMEZONE` | `data/freshness.md` | (b) per-config IANA name, default UTC | Anchors to the person's day |
| `EMPTY-SOURCE` | `data/freshness.md` | (a) ⚪ + warning | Tooling cannot distinguish "never logged" from "wrong file" |
| `FUTURE-DATES` | `data/freshness.md` | (a) exclude with warning | Never invents green from bad data |
| `COMMAND-TIMEOUT` | `data/adapters.md` | (a) fixed 30 s in v0 | One hanging script must not silence the page |
| `TOUCH-TAP` | `render/interactions.md` | (a) double-stage: first tap → detail, second → activate | Standard glance-before-travel pattern |
| `LINK-VS-DETAIL` | `render/interactions.md` | (a) detail page wins, surfaces link (P2) | Detail page is the richer surface |
| `EVENTS-TABLE-PARSING` | `render/interactions.md` | (a) skip bad rows + warning (P2) | Consistent with freshness doctrine |
| `SERIES-GAPS` | `render/interactions.md` | (a) break line, do not connect (P2) | Never fabricate health data |
| `COLORBLIND-PALETTE` | `render/colors.md` | (b) bluish green / amber / deep red / grey | Luminance ladder also fixes B&W print |
| `DARK-MODE` | `render/colors.md` | (a) light only for v0 | A4 print + glance exposure don't need it |
| `REFERENCE-VIEWPORT` | `render/layout.md` | (a) 1280×800 (small laptop) | Desktop-first; passes everywhere larger |
| `SMALL-VIEWPORT` | `render/layout.md` | (a) always scale-to-fit, never scroll | Preserves at-a-glance value |
| `RENDER-TECH` | `render/layout.md` | (a) hand-rolled SVG arcs, → (c) D3 if interactions fight | Nested-sunburst libraries fight the independent partition |
| `NO-JS-FALLBACK` | `render/layout.md` | (a) `<noscript>` notice for P0/P1 | Assistive tech runs with JS |
| `CONTENT-ENVELOPE` | `render/sunburst.md` | (b) documented 6 rings × 8 items + warning + graceful elision | Failing the bake would take the page dark |
| `SIBLING-ORDER` | `render/sunburst.md` | (a) config order, clockwise from 12 o'clock | Spatial memory survives status changes |
| `RING-PARTITION` | `render/sunburst.md` | (a) independent — each ring spans full circle | No parent field in schema; triage is per-ring |
| `NIGHTLY-PUBLISH-PATH` | `process/phases.md` | (a) in-cluster CronJob (P1) | No git-write credentials; atomic rename easy |
| `CONFIG-PROVENANCE` | `process/phases.md` | (a) private git repo | Notes are naturally git-tracked; one authenticated clone |

---

## Answered well (no question needed)

Places where I expected a gap or ambiguity and found the spec had already answered it with
a decision table, schema definition, or rule — so well that no builder question survives.

### Data model

- **circles.yaml field schema** — every field (rings, items, adapters, share, link, etc.)
  has a named decision table with explicit valid/invalid examples. The `CIR-DATA-SCHEMA-*`
  rows cover minimal config, duplicate IDs, missing fields, glyphs in labels, cross-ring
  identity, unknown keys, and every adapter variant.
- **data.json shape** — the example JSON + field presence table is contract-grade: which
  fields are always present, which are nullable (`null` vs omitted), what wire values are
  (`green`/`yellow`/`red`/`grey`, never emoji). The `warnings` array is always `[]` even
  when empty; `share` defaults are made explicit.
- **Cell identity** — `(ring id, item id)` pair, items unique within-ring only, the same
  concern in multiple rings is independent cells with no propagation. Decision table at
  `CIR-DATA-SCHEMA-CELL-IDENTITY` makes this unmissable.
- **Share weight semantics** — the ⚖ resolves the open question (relative normalization,
  not sum-to-1, not absolute fractions) and the fixture rows confirm the math (0.5/0.5 ⇒
  halves, absent ⇒ equal thirds). The proposed fixture for `shares-mixed` (2 + absent ⇒
  240°/120°) gives the builder a concrete test case.

### Status resolution

- **Failure algebra** — `CIR-DATA-STATUS-TOOLING-FAILURE`: every failure mode maps to the
  same outcome (⚪ + warning). Red is reserved for life-action judgments — never a
  tooling synthesis. The "failure-never-red" and "failure-never-green" rows close the loop.
- **Manual adapter vocabulary** — `CIR-DATA-STATUS-MANUAL-VALUES`: exactly `green/yellow/red`,
  no manual grey. Grey = absent adapter. The rationale ("a hand-set grey would conflate
  deliberately unmonitored with forgot to wire") is a product-policy anchor.
- **No aggregation** — `CIR-DATA-STATUS-NO-AGGREGATION`: statuses are per-item only, no
  ring-level or page-level roll-up. The `inner-red-outer-untouched` row stops any builder
  from wondering about cascading colors.
- **Resolution time** — `CIR-DATA-STATUS-RESOLUTION-TIME`: statuses freeze at bake time,
  page never re-evaluates. The `p0-manual-roundtrip` row says "statuses pass through
  unchanged". No ambiguity.

### Freshness adapter

- **Date parsing** — `CIR-DATA-FRESHNESS-DATE-PARSING`: recognized forms (ISO 8601
  calendar dates and datetimes, date part only). ⚖ DATE-FORMATS narrows to ISO only,
  with rationale. Non-ISO forms are explicitly not recognized — no heuristic guessing.
- **Age computation** — `CIR-DATA-FRESHNESS-AGE`: whole calendar days, no timestamps,
  no DST math. The anchoring timezone's calendar date at bake time. Rows cover
  same-day (age 0 → 🟢), year boundary, and timezone effect (Kiritimati at UTC+14).
- **Window boundaries** — `CIR-DATA-FRESHNESS-WINDOW`: boundary days belong to the
  worse status. Five rows test every boundary case (inside, at-yellow, mid, at-red,
  past-red).
- **Threshold validation** — `CIR-DATA-FRESHNESS-THRESHOLDS`: integer ≥1, yellow < red.
  Equal, inverted, zero, fractional cases all fail validation. No silent fallback.
- **Empty source / all-future** — both produce ⚪ + warning with an ⚖ rationale and
  decision-table rows. The "no red from tooling" invariant holds.

### Command adapter

- **Execution contract** — `CIR-DATA-ADAPTER-COMMAND-EXEC`: argv array, no shell,
  cwd = config directory, stdout first-non-empty-line matched case-insensitively,
  exit-code-dominates (non-zero → ⚪ regardless of stdout). Seven rows cover every
  edge case a builder might wonder about (leading noise, extra output, shell metachars
  in argv, timeout). The ⚖ COMMAND-TIMEOUT recommends 30 s fixed.

### Geometry

- **Independent ring partition** — `CIR-RENDER-GEOM-RING-PARTITION` + ⚖ RING-PARTITION:
  the spec explicitly acknowledges the classic sunburst nesting assumption and overrules
  it. The "partition-independent-full-circle" row with the fixture's Nova/Kit case makes
  the geometry unambiguous.
- **Arc share formula** — `CIR-RENDER-GEOM-ARC-SHARE`: `360° × share / Σ shares`, minus
  inter-cell gap. Rows cover half-arcs, single-item ring (full 360° band), mixed weights,
  uniform gap.
- **Sibling order** — `CIR-RENDER-GEOM-SIBLING-ORDER`: config order, clockwise from
  12 o'clock. Explicitly sets start-angle and direction, warns that library defaults vary
  and must be overridden.
- **Label rendering** — `CIR-RENDER-GEOM-LABELS`: inside arc, centered, elided with `…`,
  omitted when too tiny, full label in detail line. Glyph passthrough confirmed.
- **Content envelope** — `CIR-RENDER-GEOM-DENSITY`: 6 rings × 8 items. Overflow produces
  a build warning + graceful elision, never a failed bake. The envelope is sized to A4
  print, not arbitrary.

### Color and legibility

- **Palette hexes** — pinned to exact values. The luminance ladder (amber > grey > green >
  red) with pairwise ≥0.10 gap is specified as a testable constraint.
- **Label contrast** — WCAG AA (≥4.5:1), black on amber/grey/green, white on red.
- **Grey visibility** — `CIR-RENDER-COLOR-GREY-VISIBLE`: full opacity, same stroke as
  colored cells, distinct from background (≥2.4:1). The grey arc occupies its full share —
  size is its honesty. Five decision-table rows prevent any "grey is off/dim/hidden"
  interpretation.
- **Not-only-channel** — `CIR-RENDER-COLOR-NOT-ONLY-CHANNEL`: four concrete places the
  status word appears without color perception. The "no-color-only-cells" audit row is
  a verification anchor.
- **Legend** — all four entries always visible, even if only two statuses are used. On
  screen and in print. "The legend teaches the language, not the current census."
- **Text alternative** — `CIR-RENDER-A11Y-TEXT-ALTERNATIVE`: per-ring list with each
  item's label + status word, generated from the same `data.json` (drift-proof).
  Always in a11y tree, always in print, on screen behind a disclosure.

### Layout and page

- **One-screen invariant** — `CIR-RENDER-LAYOUT-ONE-SCREEN`: no scrolling at any viewport
  size; chart scales to fill remaining space. Testable at 1280×800. ⚖ SMALL-VIEWPORT
  confirms always-scale, never-scroll.
- **Print contract** — `CIR-RENDER-LAYOUT-PRINT-A4`: single portrait page, default
  margins, `print-color-adjust: exact`, chrome (ring key, legend, stamp, text alternative)
  all present. Four testable rows.
- **Boot error** — `CIR-RENDER-LAYOUT-BOOT-ERROR`: every failure mode (404, malformed
  JSON, version mismatch, missing keys, empty rings) produces a visible error state,
  never a blank page. Five rows.
- **Self-containment** — `CIR-RENDER-LAYOUT-ASSETS`: zero external requests, system
  fonts, ≤300 KB uncompressed. Offline-capable on origin alone.
- **Cache discipline** — `CIR-RENDER-LAYOUT-DATA-FETCH`: `Cache-Control: no-cache`
  on the fetch, fixed relative path `data.json` beside `index.html`.

### Interactions

- **Hover detail line** — composed at render time from baked fields, segments joined with
  `·`, absent fields omitted (no placeholder). Rows cover full line, no guardrail, no date,
  grey unmonitored, warning cause, hover-leave resets.
- **Click behavior** — detail_page wins over link (P2), external links open with
  `rel="noopener"`, root-relative navigates in place, no-destination is a no-op with
  default cursor.
- **Keyboard** — focusable in ring-by-ring inside-out order, clockwise within ring. Focus
  shows detail line and visible indicator. `Enter` fires click. Accessible name includes
  label + status word + ring label.

### Process

- **Phase boundaries** — `CIR-PHASE-P0/P1/P2`: explicit lists of what ships and what must
  not build yet. The "must not build" lists are as important as the "ships" lists for
  preventing overreach. The bake-is-one-path invariant (`CIR-PHASE-BAKE-ONE-PATH`) prevents
  a "nightly mode" flag.
- **Testing doctrine** — `CIR-TEST-TIERS`: unit/system/e2e with concrete circles examples.
  Decision-table row linkage (`CIR-<AREA>-<NAME>#<row-slug>`) is a naming convention, not
  a test framework. Fixture-based testing with runtime date rewriting is specified.
- **Validation fail vs warn** — `CIR-DATA-SCHEMA-VALIDATION`: shape errors fail the bake,
  unknown non-`status` keys warn. A failed bake retains the last good `data.json`.

---

## Method notes

**What I read:** All 11 files in the `/tmp/arm/specs/` tree of the
`research/issue-1-kimi-k3` branch at commit `7b7d576`:
- `README.md`, `glossary.md`
- `data/circles-yaml.md`, `data/status-resolution.md`, `data/freshness.md`,
  `data/adapters.md`, `data/data-json.md`
- `render/sunburst.md`, `render/layout.md`, `render/colors.md`,
  `render/interactions.md`
- `process/phases.md`, `process/testing.md`

**What I deliberately did NOT read:**
- Issue #1 (the original spec goal) — isolation rule: the arm's specs/ tree is the only
  product source.
- The other three arm branches (`research/issue-1-opus`, `...-deepseek-v4-flash-0731`,
  `...-mimo-v2.5-pro`) — contamination rule.
- The mission issue's PR bodies (#2, #3, #4, #5) — isolation rule.
- The context repos under `/work/context/` (homelab, circles-iac) — the environment card
  lists them as build environment, but reading homelab's agent docs/trackers/meta-state
  would contaminate the metric. I read none of them.
- The arm's `fixtures/`, `chart/`, `public/`, `scripts/`, `.agents/` directories — these
  are build artifacts, not the spec contract. (A real builder would read `fixtures/`; a
  completeness metric read of the spec tree should not depend on fixture examples
  independently from their spec references.)

**P0 scope used:** The spec tree's own definition at `process/phases.md` § CIR-PHASE-P0:
hand-set statuses, the page replacing the nginx placeholder, the bake at image build time,
`freshness:` and `command:` evaluated (adapter code ships) even though scheduling arrives
in P1. **No scheduler, no detail pages, no metric adapters, no multi-person switching.**