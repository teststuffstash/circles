# Open questions — the ⚖ index

Every ⚖ AMBIGUITY in this tree, with the option the surrounding requirement currently encodes.
**Nothing here is blocking**: each requirement is written and testable as it stands; this index
records what would change if a question is ruled the other way. Ids are stable
(`CIR-Q-<NN>`) — an issue, a review comment and a spec page can all name the same question.

Answering a question means editing the requirement it belongs to and deleting its row here; the
recommendation is not an answer.

| id | question | encoded now | what changes if ruled otherwise | page |
|---|---|---|---|---|
| CIR-Q-01 | Closed schema, or forward-compatible passthrough for unknown keys? | closed schema; unknown key = config error | unknown `status:` blocks become ⚪ + warning; one row flips | [data/circles-yaml.md](data/circles-yaml.md) |
| CIR-Q-02 | Is `spec_version` per-file or per-adapter? | one integer per file | per-adapter `api:` fields appear in the schema | [data/circles-yaml.md](data/circles-yaml.md) |
| CIR-Q-03 | May one concern appear in several rings? | no — same id in two rings means two independent items | an `alias:` item form, or a top-level `items:` map rings reference | [data/circles-yaml.md](data/circles-yaml.md) |
| CIR-Q-04 | Mixing declared and undeclared `share` in one ring? | config error (all-or-nothing per ring) | undeclared defaults to 1, or splits the remainder — both silently resize siblings | [data/circles-yaml.md](data/circles-yaml.md) |
| CIR-Q-05 | One timezone per config, or per item? | file-level only | a second place a date can be anchored | [data/circles-yaml.md](data/circles-yaml.md) |
| CIR-Q-06 | What does an unimplemented adapter show in P0? | bake exists from P0, `manual:` only; others ⚪ + "not evaluated" | the fixture person becomes invalid at P0, or P0 and P1 collapse | [data/status-resolution.md](data/status-resolution.md) |
| CIR-Q-07 | Should "deliberately unmonitored" be declarable rather than inferred? | inferred from absence; `note:` carries the why | an explicit `unmonitored:` adapter, or `strict_coverage:`; fixture `self/exercise` changes | [data/status-resolution.md](data/status-resolution.md) |
| CIR-Q-08 | Is the freshness threshold boundary inclusive or exclusive? | `age > threshold` — age 7 with `yellow_after: 7` is still 🟢 | every boundary row shifts by one day; three tests pin it | [data/freshness.md](data/freshness.md) |
| CIR-Q-09 | Which clock anchors "days old"? | calendar days in the config's timezone | elapsed-hours or browser-local ages: statuses flip mid-day and stop being reproducible | [data/freshness.md](data/freshness.md) |
| CIR-Q-10 | Which date formats are recognised in sources? | ISO-8601 only, in file text | filename dates or a configurable format; day/month ambiguity returns | [data/freshness.md](data/freshness.md) |
| CIR-Q-11 | Where in a source may a date appear? | anywhere in the text, newest non-future wins | a `pattern:` restricting dates to marked lines | [data/freshness.md](data/freshness.md) |
| CIR-Q-12 | Is there a source read cap, and what is it? | a cap exists; exceeding it is ⚪ + warning; value unruled | a large legitimate journal greys out, or a huge repo eats the bake window | [data/freshness.md](data/freshness.md) |
| CIR-Q-13 | Should `command:` return more than a status word? | first line, status word only | `key=value` lines add a data date and note to the detail line | [data/adapters.md](data/adapters.md) |
| CIR-Q-14 | Per-item timeout and total bake budget values? | defaults recommended (5 s / 5 min), unruled | a per-item `timeout:` key appears in the schema | [data/adapters.md](data/adapters.md) |
| CIR-Q-15 | How do contributed built-in adapters plug in? | in-process in this repo; `command:` is the third-party story | a plugin registry, discovery order and versioning become spec surface | [data/adapters.md](data/adapters.md) |
| CIR-Q-16 | Inline the data in the page, or fetch `data.json`? | inline, plus a sibling `data.json` | a fetch that can fail silently; `file://` viewing stops working | [data/data-json.md](data/data-json.md) |
| CIR-Q-17 | Should a stale bake grey out its adapter-derived items? | keep the lights, add the banner + stale treatment | one missed nightly run blanks the page | [data/data-json.md](data/data-json.md) |
| CIR-Q-18 | What is `stale_after_hours` for a nightly bake? | per-config value; 36 h recommended, unruled | a noisier or a later-warning page | [data/data-json.md](data/data-json.md) |
| CIR-Q-19 | Which renderer draws the rings? | hand-rolled inline SVG arcs, no library | ECharts multi-series pie, or Plotly with a synthetic hierarchy that misstates the data model; asset budget and no-JS rendering both change | [render/sunburst.md](render/sunburst.md) |
| CIR-Q-20 | How is inner-ring legibility bought? | non-increasing radial thickness outward, with a floor | equal thickness (picture contradicts the triage doctrine) or leader-line labels | [render/sunburst.md](render/sunburst.md) |
| CIR-Q-21 | Is exceeding capacity a warning or a build failure? | warning; the page is still drawn | a person cannot publish a dense config, or the table becomes the primary view | [render/sunburst.md](render/sunburst.md) |
| CIR-Q-22 | Do rings roll up to a status, and what fills the centre hole? | no rollup; hole carries name, stamp, summary, stale banner | a fabricated status with no adapter behind it | [render/sunburst.md](render/sunburst.md) |
| CIR-Q-23 | What exactly is "one screen"? | reference viewport 1280×800, phone minimum 360×640 | the no-scroll claim stops being testable | [render/layout.md](render/layout.md) |
| CIR-Q-24 | Portrait or landscape, and what fixes the A4 page box? | `@page { size: A4 portrait }`, circle sized to printable width | "one sheet" is untestable without a declared page box | [render/layout.md](render/layout.md) |
| CIR-Q-25 | Which palette, and which non-colour channel per status? | fixed CVD-safe palette + glyph in the arc; hues unruled | pattern fills or edge shapes; contrast floors stay either way | [render/color.md](render/color.md) |
| CIR-Q-26 | How loud is the stale-bake treatment? | banner + desaturation + hatch | banner alone (ignored within a week) or replacing the picture with the table | [render/color.md](render/color.md) |
| CIR-Q-27 | Link or detail page, when an item has both? | the authored `link:` wins; detail page reachable from the overlay | the generated page wins, or a new `click:` config key | [render/interaction.md](render/interaction.md) |
| CIR-Q-28 | Can the stale banner work without JS? | no — JS computes it; the stamp is always printed in words | the only client-side-JS dependency in the tree disappears or grows | [render/interaction.md](render/interaction.md) |
| CIR-Q-29 | One detail page per item, or one parameterised page? | one baked file per item | a combined data file exposes every series to anyone opening any detail page | [render/detail-page.md](render/detail-page.md) |
| CIR-Q-30 | Does `metric:` reuse the status adapter interface — or drive the status? | a separate `metric:` block; the metric never sets the light | thresholds on a metric would be the first adapter whose light means "your data says act" | [render/detail-page.md](render/detail-page.md) |
| CIR-Q-31 | What is the events table's exact contract? | dedicated `events:` path, `date`+`event` columns minimum; unruled until P2 | column names and multi-file support change the fixture rows | [render/detail-page.md](render/detail-page.md) |
| CIR-Q-32 | Where do browser-based checks live in the ruled test tiers? | run in kind where cheap, otherwise called system testing | a fourth tier, or render requirements stay unevidenced | [process/testing.md](process/testing.md) |
| CIR-Q-33 | Where does the bake run, and how does its output reach nginx? | a private job publishes an artifact the chart mounts | an init container with the person's notes mounted into the cluster, or per-person images | [process/phases.md](process/phases.md) |

## The three that most change the product

Not all questions cost the same. If only three are ruled before building starts, these:

1. **CIR-Q-33** — until the deploy seam is decided, the bake has nowhere to run and no way to
   reach a real page, and every phase is a demo over the fixture person.
2. **CIR-Q-19** — the renderer choice decides whether the page can be self-contained, printable,
   keyboard-navigable and no-JS-readable at all; it is the one decision the other render
   requirements sit on top of, and the named candidate (Plotly) cannot draw the data model.
3. **CIR-Q-30** — whether a metric can set a light is the difference between a page that reports
   "your notes are old" and one that reports "your data says act". It changes what the product
   is, and it is cheapest to answer before P1 fixes the adapter contract.
