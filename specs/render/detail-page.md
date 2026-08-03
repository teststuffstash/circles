# The detail page — a generic annotated timeseries

One metric series overlaid with dated intervention events: "medication changes × nightly sleep"
for one person, "training load × resting heart rate" for another. The genericity is the point —
nothing person-specific in code ([CIR-DATA-CONTENT](../data/circles-yaml.md)).

This is a **P2** surface ([CIR-PROC-PHASE-P2](../process/phases.md)); it is specified now only
far enough to keep P0/P1 decisions from foreclosing it. Where a decision can be deferred without
cost, it is left as a ⚖ rather than guessed.

## CIR-DETAIL-PAGE-SHAPE — what a detail page is <a id="cir-detail-page-shape"></a>

| description | inputs | expected |
|---|---|---|
| a detail page is a baked static page | item with a metric source | its own HTML file, self-contained, same doctrine as the main page ([CIR-BAKE-SELF-CONTAINED](../data/data-json.md)) |
| a detail page is reachable from its item | any item with one | via [CIR-RENDER-CLICK](interaction.md) |
| the way back is always present | detail page open | a link back to the sunburst |
| an item without a metric source has no detail page | plain item | no dead link, no empty page |
| the detail page makes no network requests | any detail page | [CIR-RENDER-NO-EGRESS](layout.md) |
| the detail page does not restate the status | any detail page | the status shown is the same resolved value from `data.json`, not recomputed |

⚖ **CIR-Q-29 — one page per item, or one page parameterised by item?** Options: (a) one baked
file per item (encoded — self-contained, printable, linkable, no client routing); (b) one page
reading `?item=self/sleep` from a combined data file, which is one artifact but leaks every
item's series to anyone opening any detail page ([CIR-BAKE-EXPOSURE](../data/data-json.md));
(c) a section on the main page, which breaks the one-screen constraint.
*Recommendation: (a).*

## CIR-DETAIL-SERIES — where the numbers come from <a id="cir-detail-series"></a>

A metric series is *(date, value)* pairs. The status adapters answer a different question
(a light), so the metric source is a **separate declaration** on the item, not a reinterpretation
of `status:`.

| description | inputs | expected |
|---|---|---|
| a metric source is declared separately | item with `metric:` and `status:` | both evaluated; the metric does not change the light |
| the series is a date→value list | any metric source | one value per date, dates ascending |
| dates use the same parser as freshness | metric source with ISO dates | [CIR-DATA-DATE-PARSE](../data/freshness.md) |
| missing days are gaps, not zeros | series with a 3-day hole | drawn as a gap; never interpolated silently |
| the unit is declared, not guessed | `unit: hours` | axis labelled with the unit; no unitless axis |
| an empty series is honest | metric source with no rows | the page states "no data", never an empty chart that reads as zero |

⚖ **CIR-Q-30 — does `metric:` reuse the adapter interface?** Options: (a) a parallel `metric:`
block with its own small adapter set (`csv:`, `sqlite:`, `command:` returning rows) — encoded
as the shape above; (b) extend [CIR-ADAPT-CONTRACT](../data/adapters.md) so one adapter can
return both a status and a series; (c) derive the status *from* the metric (thresholds on the
latest value). (c) is attractive and is a real product question — it would make "sleep below 6 h
for 3 nights → 🟡" expressible, which `manual:`/`freshness:` cannot. *Recommendation: (a) for
P2, and open (c) as a product question before P2 starts*, because a threshold-on-metric adapter
would be the first adapter whose light means "your data says act", not "your notes are old".

## CIR-DETAIL-EVENTS — the dated interventions <a id="cir-detail-events"></a>

Events come from a **markdown table** the person maintains — the same doctrine as fixtures:
human-readable rows, no hidden format.

| description | inputs | expected |
|---|---|---|
| events are read from a markdown table | file with a `date`/`event` table | one marker per row |
| a row needs a date and a label | row missing a date | ignored + warning naming the row |
| dates use the same parser | ISO dates | [CIR-DATA-DATE-PARSE](../data/freshness.md) |
| events outside the series window are dropped | event dated before the first sample | not drawn; counted in a warning |
| many events on one date do not overlap illegibly | 3 events, same date | grouped into one marker with all labels in its detail |
| an event's text is content | any label | rendered as plain text, never interpreted as markup ([CIR-BAKE-EXPOSURE](../data/data-json.md)) |
| no events is a valid page | metric with no events file | series drawn alone |

⚖ **CIR-Q-31 — what exactly is the events table's contract?** Unruled: the required column
names (`date`, `event`, optional `note`), whether the table may live in the same file as the
notes a freshness adapter reads, and whether more than one events file may feed one page.
*Recommendation: a dedicated `events:` path per item, a two-column minimum (`date`, `event`),
extra columns carried into the marker detail* — specified when P2 starts, with a fixture person
row landing at the same time.

## CIR-DETAIL-LAYOUT — legibility rules carry over <a id="cir-detail-layout"></a>

| description | inputs | expected |
|---|---|---|
| one screen, no scrolling | reference viewport | same rule as the main page ([CIR-RENDER-ONE-SCREEN](layout.md)) |
| prints to one A4 | print | [CIR-RENDER-A4](layout.md) |
| colour is not the only channel | events vs series | markers distinguishable in greyscale ([CIR-RENDER-STATUS-ENCODING](color.md)) |
| an accessible equivalent exists | any detail page | a table of samples and events ([CIR-RENDER-A11Y-TABLE](color.md)) |
| the y-axis does not lie | any series | zero baseline or an explicitly labelled truncated axis |
| correlation is not asserted | series with events | no trend line or claim is drawn between an event and the series; the reader draws the conclusion |

The last row is a product rule, not a styling one: this chart exists to let a person *notice*
that a change coincided with a shift. A page that draws the inference for them, from a handful of
self-reported points, would be making a medical claim out of a hobby dataset.
