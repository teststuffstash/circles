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
  Schema stub: [data/circles-yaml.md](data/circles-yaml.md).
- **data.json** — the baked render input: statuses + detail lines + generated-at stamp; the
  page is client-side interactive over this static file.
- **bake** — the (nightly, later phase) job that evaluates adapters and writes `data.json` +
  the page. P0 has no bake: statuses are hand-set.
- **detail page / annotated timeseries** — the click-through view of an item: a metric
  series overlaid with dated intervention events (the generic "metric × events" chart).
- **fixture person** — the invented person under `fixtures/` whose `circles.yaml` + rows are
  the specs' key examples and the tests' inputs. Synthetic by rule.
