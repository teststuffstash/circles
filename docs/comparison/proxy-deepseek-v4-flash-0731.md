# Downstream proxy: deepseek-v4-flash-0731

Specs tree end-to-end read as the P0 build contract. Every requirement, decision-table row,
⚖ entry, and fixture row was read before enumerating questions. No other arm, no issue #1
body, no PR body was consulted.

## Verdict (counts: blockers / judgment calls / minors / answered-by-⚖)

**0 / 5 / 5 / 23**

## Blockers (0)

None. The spec is comprehensive enough that a builder can implement P0 from the
requirements, decision tables, and ⚖ recommendations without needing to ask a human
for permission. Every architectural decision point either has a requirement or a ⚖
recommendation that resolves it.

## Judgment calls (5)

These are decisions the builder would silently make, implementing de facto product
policy without spec guidance.

1. **data.json exact schema (⚖ INTERACT-4 not resolved).**
   CIR-RENDER-DATA-JSON says `data.json` contains "per item its status, detail line
   (guardrail, status, last-data date), link, and the bake's generated-at stamp" — a
   textual description, not a schema. ⚖ INTERACT-4 recommends "fix a minimal schema"
   but the spec does NOT contain one; it is flagged as a PR Follow-up. The builder
   must silently decide field names, nesting (flat vs grouped), data types (ISO string
   for dates vs epoch), and the exact contract shape. This becomes the de facto standard
   until the operator ratifies a schema.

2. **Detail popover UX.**
   CIR-RENDER-CLICK + ⚖ INTERACT-2 say clicking always opens a "detail popover" (an
   in-page overlay per ⚖ INTERACT-3). But: positioning (relative to the clicked arc,
   centered, fixed position?), size, animation/transition, close trigger (Escape key?
   click-outside? close button?) are all unspecified. The builder makes the UX product
   decision.

3. **Keyboard interaction keybindings.**
   CIR-RENDER-KEYBOARD requires all interactions to be keyboard-reachable but specifies
   no key assignments. Tab order through cells? Arrow keys for arc navigation?
   Enter/Space to activate (click)? Escape to close popover? The builder decides the
   keybinding scheme.

4. **data.json loading mechanism.**
   CIR-RENDER-DATA-JSON says the page reads `data.json` but not how. Options: Fetch API
   at load time, inline `<script>` tag embedding, server-side include in an SSG pipeline.
   The mechanism affects deployment, caching, and the "single HTML asset" constraint
   (CIR-RENDER-SINGLE-ASSET). The builder chooses.

5. **Hover card behavior.**
   CIR-RENDER-HOVER says hovering shows the "detail line" (guardrail, status, last-data
   date). Not specified: hover delay/ debounce, card positioning (follow cursor? fixed
   overlay near the arc? offset?), styling, transition, or what happens when the cursor
   leaves (immediate fade? brief linger?). The builder silently defines the hover UX.

## Minors (5)

Small implementation details the builder can fill without product-significant decisions.

1. **In-cell ⚪ glyph.**
   ⚖ COLOR-2 suggests `—` as an example. The builder picks the actual glyph or icon
   (e.g. `—`, `○`, `·`, a dash icon SVG) for the ⚪ cell.

2. **Legend compact layout.**
   ⚖ RENDER-6 says "compact legend" but does not specify its layout: inline colored
   dots with labels, a small table, a row of chips, a tooltip-only legend? The builder
   chooses a reasonable layout.

3. **"No data" empty state message.**
   CIR-RENDER-EMPTY-STATE says the page shows a "no data state" without specifying the
   text string or visual treatment (centered text, icon, illustration).

4. **Error state for missing data.json.**
   CIR-RENDER-DATA-JSON says the page shows "a load error, not a broken chart" without
   specifying appearance (text content, styling, retry affordance?).

5. **Page title and meta tags.**
   Not specified — the builder chooses `<title>`, `<meta description>`, favicon, and
   HTML shell boilerplate.

## Answered by ⚖ (23)

Every ⚖ ambiguity entry below has an explicit recommendation that resolves the question
for the builder. The builder can follow the recommendation without asking a human.

| ⚖ ID | Question | Recommendation |
|---|---|---|
| ⚖ DATA-1 | Timezone/DST anchor for "days old" | Config `timezone` (IANA), default UTC; calendar-day diff |
| ⚖ DATA-2 | Recognised date formats in freshness source | ISO-8601 `YYYY-MM-DD` only |
| ⚖ DATA-3 | Share normalization | Relative weights normalized per ring; no-share items split remainder equally |
| ⚖ DATA-4 | Sibling arc order | Config declaration order |
| ⚖ DATA-5 | Item in several rings | Disallow for v0 — one ring, unique ids |
| ⚖ DATA-6 | Command output parsing | First non-empty line, trimmed, lowercased; unknown token → ⚪ + warning |
| ⚖ DATA-7 | Future-dated entries in freshness source | Age 0 (🟢) + build warning |
| ⚖ DATA-8 | Empty rings / empty config | Omit empty rings; empty config → "no data" state |
| ⚖ FRESH-1 | Mixing recognised and unrecognised formats | Only ISO `YYYY-MM-DD` counts (derivative of DATA-2) |
| ⚖ FRESH-2 | Freshness computed at bake-time vs view-time | Bake-time only; page never recomputes against viewer's clock |
| ⚖ RENDER-1 | Reference viewport value | 1280×800 CSS pixels |
| ⚖ RENDER-2 | Overflow below minimum legibility | Keep scaling for v0; flag legibility floor as follow-up |
| ⚖ RENDER-3 | Phone scope vs the one-screen constraint | Desktop-only P0; phone is a later pass |
| ⚖ RENDER-4 | What the sunburst library must guarantee | Fix the geometry contract; let the builder choose the library |
| ⚖ RENDER-5 | Accessibility of the chart as a whole | Hidden-but-accessible list of items + statuses |
| ⚖ RENDER-6 | What prints on A4 | Sunburst + compact legend; interactive elements excluded from print |
| ⚖ COLOR-1 | Exact color values | Fix a token set (e.g. green `#2e7d32`, yellow `#f9a825`, red `#c62828`, grey `#9e9e9e`) |
| ⚖ COLOR-2 | How ⚪ stays visible without a legend | Legend + in-cell glyph (e.g. `—`) |
| ⚖ COLOR-3 | Color-blind-safe palette | Keep traffic-light colors; make the non-color channel mandatory |
| ⚖ INTERACT-1 | Hover vs click on touch devices | Tap toggles the detail popover; link via explicit affordance |
| ⚖ INTERACT-2 | Click target when item has both link and detail | Click always opens the detail popover; popover exposes both |
| ⚖ INTERACT-3 | Detail page vs "no multi-page app" (goal contradiction) | In-page overlay within the single HTML asset |
| ⚖ PROC-1 | Where the gate grows | `devbox run ci`: unit + chart locally; system/e2e in CI |

## Answered well (no question needed)

These requirements and decision tables are specified with enough precision that a builder
can implement and test them without ambiguity. No follow-up question needed.

### Data model — circles-yaml.md

| Requirement | Why it works |
|---|---|
| CIR-DATA-SCHEMA — config shape | Full YAML example with in-line comments; all fields explicitly optional/required |
| CIR-DATA-STATUS-RESOLUTION — status resolution | Complete decision table: 10 rows covering all adapters, missing source, command failure |
| CIR-DATA-UNMONITORED — grey is honest and visible | Clear: first-class status, never hidden, never promoted to green |
| CIR-DATA-TOOLING-FAILURE — tooling failure never red | Explicit rule + rationale ("red means act, not broken tooling") |
| CIR-DATA-ADAPTER-MANUAL — manual adapter | Exact accepted values listed |
| CIR-DATA-ADAPTER-FRESHNESS — freshness adapter | Semantics delegated to freshness.md; schema complete |
| CIR-DATA-ADAPTER-COMMAND — command adapter | Argv list; output rules in CIR-DATA-COMMAND-OUTPUT |
| CIR-DATA-COMMAND-OUTPUT — command output parsing | Complete decision table: 5 rows (padded, uppercase, multi-line, unknown, empty) |
| CIR-DATA-VALIDATION — config errors fail the build | Comprehensive decision table: 7 rows (duplicate rings, duplicate items, two adapters, unknown manual, inverted thresholds, negative thresholds, non-positive share) |
| CIR-DATA-ITEM-UNIQUENESS — one ring per item | Explicit rule + ⚖ recommendation for v0 |
| CIR-DATA-SHARE-WEIGHTS — arc weights | Normalization rule specified with ⚖ recommendation |
| CIR-DATA-SIBLING-ORDER — sibling arc order | Declaration order, ⚖ recommendation |

### Freshness — freshness.md

| Requirement | Why it works |
|---|---|
| CIR-DATA-FRESHNESS-WINDOW — two-threshold window | Inclusive/exclusive boundaries specified with decision table: 6 rows including zero-age and exact-boundary |
| CIR-DATA-FRESHNESS-DATE-PARSING — recognised date formats | ISO-8601 only, decision table: 4 rows covering markdown list, multiple dates, glob, no date |
| CIR-DATA-FRESHNESS-TIMEZONE — timezone/DST anchoring | IANA config field, default UTC, calendar-day difference not elapsed-hours; 3-row table |
| CIR-DATA-FRESHNESS-MISSING-SOURCE — missing source | ⚪ + build warning, never red |
| CIR-DATA-FRESHNESS-FUTURE-DATE — future dates | Age 0, 🟢 + build warning; 2-row table |

### Render — geometry.md

| Requirement | Why it works |
|---|---|
| CIR-RENDER-RING-ORDER — rings inside-out | Explicit inside-out + triage inward-first; 2-row table |
| CIR-RENDER-ARC-SUBDIVISION — items subdivide a ring | Share-proportional angles; 3-row table (half-arcs, equal thirds, weighted) |
| CIR-RENDER-ONE-SCREEN — fits one screen | Hard constraint with testable reference |
| CIR-RENDER-REFERENCE-VIEWPORT — testable "one screen" | 1280×800 CSS pixels; specific assertion: no scrollbars, no clipping |
| CIR-RENDER-A4-PRINT — prints legibly | HTML print via browser; sunburst + legend per ⚖ RENDER-6 |
| CIR-RENDER-OVERFLOW — too many rings/items | Fit-to-screen scaling; minimum legibility handled by ⚖ RENDER-2 |
| CIR-RENDER-EMPTY-STATE — empty rings/config | Omit empty rings; "no data" state for empty config; 2-row table |

### Render — color.md

| Requirement | Why it works |
|---|---|
| CIR-RENDER-COLOR-STATUS — status colors | Four distinct statuses, mutually distinguishable from background |
| CIR-RENDER-COLOR-UNMONITORED — ⚪ is visible | Grey fill + stroke + label; distinct from background and 🟢; 2-row table |
| CIR-RENDER-COLOR-ACCESSIBILITY — not color-only | Non-color channel (icon/glyph + text label) in legend and on hover; 2-row table |
| CIR-RENDER-COLOR-CONTRAST — legibility floor | WCAG AA for text |

### Render — interactions.md

| Requirement | Why it works |
|---|---|
| CIR-RENDER-SINGLE-ASSET — one static HTML | One HTML + data.json; no server, no DB, no multi-page |
| CIR-RENDER-DATA-JSON — baked render input | Content enumerated; generated-at is the anchor; missing file → load error (3-row table) |
| CIR-RENDER-HOVER — hover shows detail line | Detail: guardrail, status, last-data date |
| CIR-RENDER-CLICK — click opens detail popover | Popover contains link + "details" button per ⚖ INTERACT-2 |
| CIR-RENDER-DETAIL-PAGE — annotated-timeseries overlay | In-page overlay; P0 shell, P2 data |
| CIR-RENDER-KEYBOARD — keyboard access | Required for all interactions |

### Process — testing.md

| Requirement | Why it works |
|---|---|
| CIR-PROC-TEST-TIERS — tier assignment | Clear unit/system/e2e definitions; pure-logic requirements are unit-tier |
| CIR-PROC-TABLE-LINKAGE — rows become test ids | Decision-table `description` is a stable test id; adding behavior = adding a row |

## Method notes

- **What was read (arm branch `research/issue-1-deepseek-v4-flash-0731`):**
  - `specs/README.md`
  - `specs/glossary.md`
  - `specs/data/circles-yaml.md`
  - `specs/data/freshness.md`
  - `specs/render/geometry.md`
  - `specs/render/color.md`
  - `specs/render/interactions.md`
  - `specs/process/testing.md`
  - `fixtures/README.md`
  - `fixtures/alex/circles.yaml`
  - `fixtures/alex/notes/sleep-log.md`
  - `fixtures/alex/notes/labs.md`
  - `fixtures/alex/notes/plants-status.sh`

- **What was deliberately not read:** Issue #1 body or comments, the other three arm branches (`research/issue-1-opus`, `research/issue-1-kimi-k3`, `research/issue-1-mimo-v2.5-pro`), any PR body (#2, #3, #4, #5), homelab agent docs/trackers/TICK-LOG/retros from `/work/context/homelab`. No cross-contamination.

- **Build environment facts noted** (from environment card, not specs): devbox for tool installs, no Docker daemon in this ride, egress monitored but not blocked, proxy mirrors for nix/pip. These affect only how a builder would set up their local toolchain, not the product spec.

- **Fixture `circles.yaml` dates** (sleep-log.md newest: 2026-08-01; labs.md: 2026-01-15) are synthetic and illustrative — tests rewrite dates at runtime relative to "today" per the fixture README. Not a gap.