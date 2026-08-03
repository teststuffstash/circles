# Glossary

One definition per term; specs use these words and no synonyms.

- **circle / ring** — one concentric band of the sunburst; rings order life areas
  inside-out (the innermost ring must hold for the outer ones to matter — triage reads
  inward-first).
- **item** — one arc segment within a ring: a concern with a label, an optional guardrail,
  and a status. Items may subdivide a ring (e.g. two children as two half-arcs of the same
  ring).
- **status** — the resolved traffic light of an item: 🟢 ok · 🟡 attention · 🔴 act ·
  ⚪ unmonitored. Grey is honest and visible — the unmonitored surface must be readable at a
  glance, never hidden.
- **adapter** — the declared source an item's status comes from (`manual:`, `freshness:`,
  `command:`; contributed built-ins later). An item without an adapter is ⚪.
- **freshness** — a status rule over a date: "the newest date for X is younger than N days."
  Stale → 🟡, very stale → 🔴 (two thresholds).
- **guardrail** — the standing protective habit/threshold an item carries (text, shown on
  hover); guardrails are content, not computed.
- **circles.yaml** — a person's configuration: their rings, items, labels, links, adapters.
  Schema: [data/circles-yaml.md](data/circles-yaml.md).
- **data.json** — the baked render input: statuses + detail lines + generated-at stamp; the
  page is client-side interactive over this static file.
- **bake** — the job that evaluates adapters and writes `data.json` + the page. From P1 it runs
  nightly; in P0 it already exists but implements only the `manual:` adapter
  ([CIR-PROC-PHASE-P0](process/phases.md)).
- **detail page / annotated timeseries** — the click-through view of an item: a metric
  series overlaid with dated intervention events (the generic "metric × events" chart).
- **fixture person** — the invented person under `fixtures/` whose `circles.yaml` + rows are
  the specs' key examples and the tests' inputs. Synthetic by rule.

Terms this pass adds (each is used by a requirement, not decoration):

- **resolution** — the bake-time act of turning one item's declared adapter into exactly one
  status plus one detail line. Resolution happens at bake; the page never resolves
  ([CIR-DATA-STATUS-RESOLUTION](data/status-resolution.md)).
- **config error** — a defect in `circles.yaml` itself: unknown key, unparseable YAML,
  thresholds out of order, two adapters on one item. Config errors **fail the bake loudly and
  publish nothing**; they are never a status ([CIR-DATA-CONFIG-ERROR-FAILS](data/status-resolution.md)).
- **adapter failure** — a well-formed adapter that could not produce an answer at run time:
  source vanished, command exited non-zero, timeout, unrecognised output. Resolves to ⚪ plus a
  warning, never 🔴 ([CIR-DATA-FAILURE-IS-GREY](data/status-resolution.md)).
- **warning** — a bake-time message attached to an item or to the page, explaining a ⚪ or a
  degraded render. Warnings are content of the artifact — counted and shown on the page — not
  log-only ([CIR-BAKE-WARNINGS](data/data-json.md)).
- **unmonitored reason** — which road led to ⚪: *by choice* (no adapter declared) or *by
  failure* (adapter declared, no answer). One grey light, two reasons; the difference must
  survive into the detail line and the page summary ([CIR-DATA-GREY-REASON](data/status-resolution.md)).
- **dangerous-green** — any path by which an item shows 🟢 while its underlying data is absent,
  stale, unparsed, mistyped, or unevaluated. A defect class, not a trade-off.
- **stale bake** — the page's own freshness failing: `data.json` whose `generated_at` is older
  than the staleness threshold. Its lights are history, not status
  ([CIR-BAKE-STALE-SELF](data/data-json.md)).
- **age (days)** — the whole number of calendar days between a source date and the reference
  date, in the configured timezone. Not an elapsed-hours division
  ([CIR-DATA-AGE-CALENDAR](data/freshness.md)).
- **reference date** — the calendar date a bake resolves *as of*: the bake clock, injectable for
  tests. Every age in one bake uses one reference date ([CIR-BAKE-DETERMINISM](data/data-json.md)).
- **source** — the file or glob a `freshness:` adapter reads, resolved relative to the directory
  holding `circles.yaml` ([CIR-DATA-SOURCE-PATH](data/freshness.md)).
- **capacity** — how many rings × items a page can carry with every label still legible at
  one-screen and A4 size ([CIR-RENDER-CAPACITY](render/sunburst.md)).
- **accessible equivalent** — the tabular rendering of the same statuses that screen readers,
  greyscale print, and no-JS clients get ([CIR-RENDER-A11Y-TABLE](render/color.md)).
- **exposure surface** — everything a person who can reach the page URL can read: the HTML, the
  `data.json` beside it, and every warning baked into them. Access control is deploy-time and
  out of this repo ([CIR-BAKE-EXPOSURE](data/data-json.md)).
- **ring rollup** — a status computed for a whole ring from its items. Deliberately **not** a
  concept in v0; the page carries a summary count instead ([CIR-RENDER-SUMMARY](render/sunburst.md)).
