# Glossary

One definition per term; specs use these words and no synonyms.

> **On "circle" vs "ring"** (⚖-R23). The seed glossary's first entry was `circle / ring` —
> two names, one definition, in the file whose own rule is "no synonyms"; issue #1 then added a
> third surface word, "cell". Ruled: **ring** is the spec term (it is the config key `rings:`
> and the geometric band). **circle** is the product's name for the same thing — it appears in
> the repo name, the page title, and prose *about* the product, and is never used as a spec
> term or in a requirement. **cell** is a genuinely distinct term, defined below: an item is a
> configured thing, a cell is its rendered arc.

## Domain model

- **ring** — one concentric band of the sunburst; rings order life areas inside-out (the
  innermost ring must hold for the outer ones to matter — triage reads inward-first). The
  product calls a ring a "circle"; specs do not.
- **item** — one concern configured within a ring: a label, an optional guardrail, an optional
  link, and exactly one adapter (or none). Items may subdivide a ring (e.g. two children as two
  half-arcs of the same ring). An item is a *configured* thing; what the page draws for it is a
  cell.
- **cell** — the rendered arc of one item on the page; the visual unit that carries a status
  colour. A cell's identity is the `(ring id, item id)` pair (`CIR-DATA-IDENTITY`).
- **sibling** — one of the items of the same ring; siblings subdivide their ring's full circle
  among themselves.
- **half-arc** — an item whose arc spans half its ring (its share equals half the ring's share
  total); the canonical two-children case.
- **share** — an item's relative arc weight within its ring (a positive number); arc angles are
  proportional to shares within the ring (`CIR-DATA-SHARE`).
- **status** — the resolved traffic light of an item: 🟢 ok · 🟡 attention · 🔴 act ·
  ⚪ unmonitored. Grey is honest and visible — the unmonitored surface must be readable at a
  glance, never hidden.
- **ok / attention / act / unmonitored** — the four status words, the text form of
  🟢 / 🟡 / 🔴 / ⚪. Statuses are spelled with these words wherever text is shown to a person
  (legend, detail line, text alternative). They are **display words, not wire values** —
  `data.json` carries `green` / `yellow` / `red` / `grey` (⚖-R19, `CIR-BAKE-STATUS-VALUES`).
- **guardrail** — the standing protective habit/threshold an item carries (text, shown on
  hover); guardrails are content, not computed.
- **circles.yaml** — a person's configuration: their rings, items, labels, links, adapters.
  Schema: [data/circles-yaml.md](data/circles-yaml.md).

## Adapters and status resolution

- **adapter** — the declared source an item's status comes from (`manual:`, `freshness:`,
  `command:`; contributed built-ins later). An item without an adapter is ⚪ by choice.
- **freshness** — a status rule over a date: "the newest date for X is younger than N days."
  Stale → 🟡, very stale → 🔴 (two thresholds).
- **source** — the file path or glob a `freshness:` adapter scans for dates, resolved relative
  to the directory containing `circles.yaml` (`CIR-DATA-SOURCE-PATH`).
- **yellow_after / red_after** — the two freshness thresholds in whole days. An item whose
  newest date is **strictly more than** `yellow_after` days old is 🟡, and strictly more than
  `red_after` days old is 🔴; at exactly the threshold the item still holds its better light
  (⚖-R6, `CIR-DATA-FRESHNESS-WINDOW`).
- **last-data date** — the newest date an adapter observed for an item (for `freshness:`: the
  newest parseable date in the source); part of the item's detail line.
- **reference date** — the single "now" the whole bake resolves against, injected once and
  shared by every adapter, so one bake never mixes two clocks and tests can freeze it
  (`CIR-ADAPT-REFERENCE-DATE`).
- **build warning** — a non-fatal finding emitted by the bake (tooling failure, suspicious
  data). Build warnings never turn an item 🔴 and never fail the bake; they accompany ⚪ (or the
  affected status) and are surfaced per `CIR-BAKE-WARNINGS`.
- **config error** — a fault in `circles.yaml` itself (schema violation, two adapters on one
  item, mixed shares). Unlike a build warning, a config error **fails the bake** and publishes
  nothing — the last good artifact stays served (`CIR-DATA-VALIDATION`).
- **bake** — the job that evaluates adapters and writes `data.json`. It runs at P0 too, one
  shot at image-build time, but P0 evaluates `manual:` adapters **only**: `freshness:` and
  `command:` items bake to ⚪ + a "not evaluated in this build" warning (⚖-R2). P1 schedules the
  same bake nightly with all adapters live (see [process/phases.md](process/phases.md)).
- **data.json** — the baked render input: statuses + detail fields + generated-at stamp +
  warnings. It is both embedded in the page and published as a sibling file (⚖-R4,
  `CIR-BAKE-ARTIFACT`).
- **generated-at stamp** — the UTC timestamp the bake wrote into `data.json`, displayed on the
  page so a stale bake is visible.

## The page

- **independent ring partition** — the geometry doctrine: each ring subdivides the full circle
  on its own; an outer ring's arcs never nest inside an inner item's arc
  (`CIR-RENDER-RING-PARTITION`). This is what a hierarchical sunburst library cannot express
  (⚖-R3).
- **center disc** — the innermost circle of the sunburst, inside ring 1. It carries the
  person's name, the generated-at stamp and the unmonitored count — never a rolled-up status
  (⚖-R9).
- **ring key** — the page element that names the rings in inside-out order (the reading order
  for triage).
- **legend** — the page's fixed key mapping the four status colours to their words; present on
  screen and on the A4 print.
- **detail line** — the one-line item summary shown on hover/focus/tap: guardrail, status word,
  last-data date. Composed **at bake time** and carried as one string in the artifact, so print
  and no-JS paths render it without composing anything (⚖-R20).
- **detail page / annotated timeseries** — the click-through view of an item: a metric series
  overlaid with dated intervention events (the generic "metric × events" chart). A separately
  baked static file, not a client-side route (⚖-R5). P2.
- **metric series** — the dated numeric values behind a detail page (P2), produced by a metric
  adapter.
- **intervention event** — a dated annotation overlaid on a detail page's metric series, parsed
  from a markdown table.
- **reference viewport** — the fixed CSS-pixel viewport the one-screen constraint is tested at:
  1280×800 CSS px (`CIR-RENDER-REFERENCE-VIEWPORT`).
- **chrome** — the page furniture around the chart: title, center-disc text, ring key, legend,
  generated-at stamp, warnings banner, detail strip (`CIR-RENDER-CHROME`).
- **detail strip** — the fixed one-line chrome area the detail line appears in on
  hover/focus/tap.
- **warnings banner** — the chrome element summarizing build warnings (count + a reachable
  list); present only when `warnings[]` is non-empty.
- **boot failure** — the page's visible failure state when its embedded payload is absent,
  malformed, or an unrecognized version; never a blank page and never a page of green
  (`CIR-RENDER-BOOT-FAILURE`).
- **text alternative** — the complete per-ring list of items with status words, generated from
  the same baked data; always in the accessibility tree and in print
  (`CIR-RENDER-A11Y-TABLE`).
- **content envelope** — the legibility bound the one-screen gate is tested within (≤ 6 rings,
  ≤ 8 items per ring at the reference viewport); beyond it the bake warns and the page elides
  (`CIR-RENDER-CAPACITY`).
- **luminance ladder** — the palette's strict greyscale ordering with a pairwise floor, which
  keeps the four statuses distinguishable on a mono printer (`CIR-RENDER-PALETTE`).

## Process

- **requirement ID** — the stable `CIR-<AREA>-<NAME>` anchor of one requirement; never renamed
  or reused. The area vocabulary is closed (see [README.md](README.md)).
- **decision table** — a visible `inputs || expected` table whose first-column row ids are the
  evidence join keys.
- **row id** — the stable intent id in a decision table's first column; cited by a test as
  `CIR-<AREA>-<NAME>#<row-id>` verbatim.
- **world** — the named fixture set a table's expectations are a function of. v0 has one world,
  `alex`; every page declares it once.
- **evidence** — a passing test that cites a requirement ID and row id. Coverage is derived
  from evidence, never declared in the spec.
- **⚖ AMBIGUITY** — a recorded judgment call with its options and the ruling the specs encode;
  first-class spec content, keyed `⚖-R<NN>` and indexed in
  [open-questions.md](open-questions.md).
- **dangerous-green** — the named defect class this tree's tie-breaker exists to prevent: any
  path by which an item shows 🟢 while its data is absent, stale, unparsed, mistyped or never
  evaluated (see [README.md](README.md)).
- **spec gate** — the checks `scripts/lint-specs.sh` runs over this tree (unique IDs, closed
  area vocabulary, resolving links, unique row ids, evidence lines, world declarations, every ⚖
  indexed); part of `devbox run ci` (`CIR-PROC-SPEC-GATE`).
- **P0 / P1 / P2** — the delivery phases defined in [process/phases.md](process/phases.md)
  (P0: hand-set statuses on the existing deploy pipeline; P1: nightly bake; P2: first detail
  page).
- **fixture person** — the invented person under `fixtures/` whose `circles.yaml` + rows are
  the specs' key examples and the tests' inputs. Synthetic by rule.
