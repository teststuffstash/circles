# Glossary

One definition per term; specs use these words and no synonyms.

## Domain model

- **circle / ring** — one concentric band of the sunburst; rings order life areas
  inside-out (the innermost ring must hold for the outer ones to matter — triage reads
  inward-first).
- **item** — one arc segment within a ring: a concern with a label, an optional guardrail,
  and a status. Items may subdivide a ring (e.g. two children as two half-arcs of the same
  ring).
- **cell** — the rendered arc of one item on the page; the visual unit that carries a status
  color. A cell's identity is the (ring id, item id) pair.
- **sibling** — one of the items of the same ring; siblings subdivide their ring's full
  circle among themselves.
- **half-arc** — an item whose arc spans half its ring (its share equals half the ring's
  share total); the canonical two-children case.
- **share** — an item's relative arc weight within its ring (a positive number, default 1);
  arc angles are proportional to shares (see `CIR-DATA-SHARE-WEIGHT`).
- **status** — the resolved traffic light of an item: 🟢 ok · 🟡 attention · 🔴 act ·
  ⚪ unmonitored. Grey is honest and visible — the unmonitored surface must be readable at a
  glance, never hidden.
- **ok / attention / act / unmonitored** — the four status words, the text form of
  🟢 / 🟡 / 🔴 / ⚪. Statuses are spelled with these words wherever text is needed
  (legend, detail line, `data.json` uses `green`/`yellow`/`red`/`grey` as the wire values).
- **guardrail** — the standing protective habit/threshold an item carries (text, shown on
  hover); guardrails are content, not computed.
- **circles.yaml** — a person's configuration: their rings, items, labels, links, adapters.
  Schema: [data/circles-yaml.md](data/circles-yaml.md).

## Adapters and status resolution

- **adapter** — the declared source an item's status comes from (`manual:`, `freshness:`,
  `command:`; contributed built-ins later). An item without an adapter is ⚪.
- **freshness** — a status rule over a date: "the newest date for X is younger than N days."
  Stale → 🟡, very stale → 🔴 (two thresholds).
- **source** — the file path or glob a `freshness:` adapter scans for dates, resolved
  relative to the directory containing `circles.yaml`.
- **yellow_after / red_after** — the two freshness thresholds in whole days: an item whose
  newest date is `yellow_after` days old or older is 🟡; `red_after` days old or older is 🔴.
- **last-data date** — the newest date an adapter observed for an item (for `freshness:`:
  the newest parseable date in the source); part of the item's detail line.
- **build warning** — a non-fatal finding emitted by the bake (tooling failure, suspicious
  data). Build warnings never turn an item 🔴 and never fail the bake; they accompany ⚪
  (or the affected status) and are surfaced per `CIR-DATA-DATAJSON-WARNINGS`.
- **bake** — the job that evaluates adapters and writes `data.json` (+ per-item detail
  payloads in P2). P0 runs the same bake one shot at image build time; P1 schedules it
  nightly (see [process/phases.md](process/phases.md)).
- **data.json** — the baked render input: statuses + detail fields + generated-at stamp +
  warnings; the page is client-side interactive over this static file.
- **generated-at stamp** — the UTC timestamp the bake wrote into `data.json`, displayed on
  the page so a stale bake is visible.

## The page

- **independent ring partition** — the geometry doctrine: each ring subdivides the full
  circle on its own; an outer ring's arcs never nest inside an inner item's arc
  (`CIR-RENDER-GEOM-RING-PARTITION`).
- **center disc** — the innermost circle of the sunburst, inside ring 1.
- **ring key** — the page element that names the rings in inside-out order (the reading
  order for triage).
- **legend** — the page's fixed key mapping the four status colors to their words; present
  on screen and on the A4 print.
- **detail line** — the one-line item summary shown on hover/focus/tap: guardrail, status
  word, last-data date.
- **detail page / annotated timeseries** — the click-through view of an item: a metric
  series overlaid with dated intervention events (the generic "metric × events" chart).
- **metric series** — the dated numeric values behind a detail page (P2), produced by a
  metric adapter.
- **intervention event** — a dated annotation overlaid on a detail page's metric series,
  parsed from a markdown table.
- **reference viewport** — the fixed CSS-pixel viewport the one-screen constraint is tested
  at: 1280×800 CSS px (`CIR-RENDER-LAYOUT-REFERENCE-VIEWPORT`).
- **chrome** — the page furniture around the chart: title, center-disc name, ring key,
  legend, generated-at stamp, warnings banner, detail strip
  (`CIR-RENDER-LAYOUT-CHROME`).
- **detail strip** — the fixed one-line chrome area the detail line appears in on
  hover/focus/tap.
- **warnings banner** — the chrome element summarizing build warnings (count + causes);
  present only when `warnings[]` is non-empty.
- **boot error** — the page's visible failure state when `data.json` is missing, malformed,
  or an unrecognized version; never a blank page (`CIR-RENDER-LAYOUT-BOOT-ERROR`).
- **text alternative** — the complete per-ring list of items with status words, generated
  from the same `data.json`; always in the accessibility tree and in print
  (`CIR-RENDER-A11Y-TEXT-ALTERNATIVE`).
- **detail payload** — the per-item baked JSON (`details/<ring>--<item>.json`) behind a
  detail page: metric series + intervention events (P2).
- **content envelope** — the legibility bound the one-screen gate is tested within (≤ 6
  rings, ≤ 8 items per ring at the reference viewport); beyond it the bake warns and the
  page elides (`CIR-RENDER-GEOM-DENSITY`).
- **luminance ladder** — the palette's strict grayscale ordering (amber > grey > green >
  red) that keeps statuses pairwise distinguishable on B&W print
  (`CIR-RENDER-COLOR-PALETTE`).

## Process

- **requirement ID** — the stable `CIR-<AREA>-<NAME>` anchor of one requirement; never
  renamed or reused.
- **decision table** — a visible `inputs || expected` table whose first-column row slugs
  become test ids verbatim.
- **evidence** — a passing test that cites a requirement ID. Coverage is derived from
  evidence, never declared in the spec.
- **⚖ AMBIGUITY** — a recorded judgment call with options and a recommendation; first-class
  spec content awaiting human confirmation, keyed `⚖ AMBIGUITY: <SLUG>`.
- **P0 / P1 / P2** — the delivery phases defined in
  [process/phases.md](process/phases.md) (P0: hand-set statuses on the existing deploy
  pipeline; P1: nightly bake; P2: first detail page).
- **fixture person** — the invented person under `fixtures/` whose `circles.yaml` + rows are
  the specs' key examples and the tests' inputs. Synthetic by rule.
