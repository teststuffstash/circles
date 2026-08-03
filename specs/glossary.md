# Glossary

One definition per term; specs use these words and no synonyms. Extend by adding a term with
exactly one definition — never two words for the same concept, never two definitions for one
word.

- **circle / ring** — one concentric band of the sunburst; rings order life areas
  inside-out (the innermost ring must hold for the outer ones to matter — triage reads
  inward-first).
- **item** — one arc segment within a ring: a concern with a label, an optional guardrail,
  and a status. Items may subdivide a ring (e.g. two children as two half-arcs of the same
  ring).
- **status** — the resolved traffic light of an item: 🟢 ok · 🟡 attention · 🔴 act ·
  ⚪ unmonitored. Grey is honest and visible — the unmonitored surface must be readable at a
  glance, never hidden.
- **status light** — the visual encoding of a status on a cell (color, and per
  [CIR-RENDER-COLOR-ACCESSIBILITY](render/color.md) a non-color channel).
- **adapter** — the declared source an item's status comes from (`manual:`, `freshness:`,
  `command:`; contributed built-ins later). An item without an adapter is ⚪.
- **adapter interface** — the stable contract contributed adapters plug into so a new source
  (sqlite, Prometheus, HTTP/REST) needs no page change ([CIR-DATA-ADAPTER-INTERFACE](data/circles-yaml.md)).
- **manual adapter** — a hand-set green/yellow/red status in config (v0 mode).
- **freshness adapter** — a status rule over a date: "the newest date for X is younger than N
  days." Stale → 🟡, very stale → 🔴 (two thresholds).
- **command adapter** — a user-supplied script that prints the status on stdout; the escape
  hatch for any personal data source.
- **unmonitored** — the ⚪ status of an item with no adapter (or whose adapter failed). Grey is
  honest and visible, never defaulted to green.
- **tooling failure** — an adapter error or missing source. Resolves to ⚪ + a build warning,
  **never 🔴** — red means "act on your life", not "the tooling broke".
- **build warning** — a non-fatal diagnostic emitted during bake/validation when an adapter
  cannot resolve; the page still renders with ⚪.
- **guardrail** — the standing protective habit/threshold an item carries (text, shown on
  hover); guardrails are content, not computed.
- **share** — an item's optional arc weight within its ring (default: equal). Siblings'
  shares subdivide the ring; two `0.5` shares are two half-arcs.
- **half-arc** — a sibling arc occupying half its ring (the two-children example).
- **triage order** — the inward-first reading order of rings: the innermost ring is read
  first because it must hold for the outer ones to matter.
- **circles.yaml** — a person's configuration: their rings, items, labels, links, adapters.
  Schema: [data/circles-yaml.md](data/circles-yaml.md).
- **data.json** — the baked render input: statuses + detail lines + generated-at stamp; the
  page is client-side interactive over this static file. Contract:
  [render/interactions.md](render/interactions.md).
- **generated-at** — the timestamp baked into `data.json` marking when the bake ran; the page
  shows freshness relative to this stamp, never the viewer's clock.
- **bake** — the (nightly, later phase) job that evaluates adapters and writes `data.json` +
  the page. P0 has no bake: statuses are hand-set.
- **bake job** — the P1 process that runs adapters and writes `data.json`; it runs elsewhere;
  this repo owns the code it runs.
- **detail page / annotated timeseries** — the click-through view of an item: a metric
  series overlaid with dated intervention events (the generic "metric × events" chart).
- **metric series** — the time-ordered numeric series an adapter supplies for a detail page.
- **intervention event** — a dated, human-authored markdown-table row overlaid on a metric
  series (e.g. "medication change", "training block").
- **one-screen constraint** — the hard requirement that the whole picture fits one screen
  without scrolling and prints legibly to a single A4 via the browser.
- **reference viewport** — the testable screen size that defines "fits one screen"
  ([CIR-RENDER-ONE-SCREEN](render/geometry.md)).
- **sunburst** — the chart form: concentric rings of arc segments, each cell colored by its
  status light.
- **cell** — one rendered arc segment (an item's visual presence on the sunburst).
- **fixture person** — the invented person under `fixtures/` whose `circles.yaml` + rows are
  the specs' key examples and the tests' inputs. Synthetic by rule.
