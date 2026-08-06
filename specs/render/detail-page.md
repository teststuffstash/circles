# The detail page — a generic annotated timeseries

One metric series overlaid with dated intervention events: "medication changes × nightly sleep"
for one person, "training load × resting heart rate" for another. The genericity is the point —
nothing person-specific lives in code
([circles-yaml.md](../data/circles-yaml.md)).

This is a **P2** surface ([`CIR-PROC-PHASE-P2`](../process/phases.md)); it is specified now only
far enough to keep P0/P1 decisions from foreclosing it. Where a decision can be deferred without
cost it is left as a ⚖ rather than guessed.

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-DETAIL-PAGE-SHAPE — what a detail page is

| row id | inputs | expected |
|---|---|---|
| detail-is-a-baked-static-page | item with a metric source | its own HTML file, self-contained, same doctrine as the main page ([`CIR-BAKE-SELF-CONTAINED`](../data/data-json.md)) |
| detail-reachable-from-its-item | any item with one | via [`CIR-RENDER-CLICK`](interactions.md) |
| detail-way-back-always-present | detail page open | a link back to the sunburst |
| detail-absent-when-no-metric | plain item | no dead link, no empty page |
| detail-makes-no-network-requests | any detail page | [`CIR-RENDER-NO-EGRESS`](layout.md) |
| detail-does-not-restate-the-status | any detail page | the status shown is the same resolved value from the artifact, never recomputed |

**⚖-R45 — one page per item, or one page parameterized by item?** Options: (a) one baked file
per item; (b) one page reading `?item=self/sleep` from a combined data file; (c) a section on
the main page. **Ruled: (a)** — self-contained, printable, linkable, and no client routing.
(b) is one artifact but leaks every item's series to anyone who opens any detail page
([`CIR-BAKE-EXPOSURE`](../data/data-json.md)); (c) breaks the one-screen constraint. This is also
how the goal's own tension resolves: separate baked files are not "a multi-page app" — there is
no routing, no shared state and no client-side navigation, just static siblings.

_Evidence: none yet — unverified._

## CIR-DETAIL-SERIES — where the numbers come from

A metric series is *(date, value)* pairs. The status adapters answer a different question — a
light — so the metric source is a **separate declaration** on the item, not a reinterpretation of
`status:`.

| row id | inputs | expected |
|---|---|---|
| metric-declared-separately | item with `metric:` and `status:` | both evaluated; the metric does not change the light |
| series-is-date-value-list | any metric source | one value per date, dates ascending |
| series-dates-use-freshness-parser | metric source with ISO dates | [`CIR-DATA-DATE-PARSE`](../data/freshness.md) |
| series-gaps-are-gaps | series with a 3-day hole | drawn as a gap; never silently interpolated |
| series-unit-declared | `unit: hours` | axis labelled with the unit; no unitless axis |
| series-empty-is-honest | metric source with no rows | the page states "no data", never an empty chart that reads as zero |

**⚖-R46 — does `metric:` reuse the adapter interface?** Options: (a) a parallel `metric:` block
with its own small adapter set (`csv:`, `sqlite:`, `command:` returning rows); (b) extend
[`CIR-ADAPT-CONTRACT`](../data/adapters.md) so one adapter returns both a status and a series;
(c) derive the status *from* the metric, by thresholds on recent values. **Ruled: (a) for P2,
with (c) opened as a product question before P2 starts.** (c) is genuinely attractive — it would
make "sleep below 6 h for 3 nights → 🟡" expressible, which neither `manual:` nor `freshness:`
can — and it deserves a decision rather than a default, because it would be the first adapter
whose light means "your data says act" rather than "your notes are old".

_Evidence: none yet — unverified._

## CIR-DETAIL-EVENTS — the dated interventions

Events come from a **markdown table** the person maintains — the same doctrine as fixtures:
human-readable rows, no hidden format.

| row id | inputs | expected |
|---|---|---|
| events-from-markdown-table | file with a `date`/`event` table | one marker per row |
| events-row-needs-date-and-label | row missing a date | ignored + warning naming the row |
| events-dates-use-freshness-parser | ISO dates | [`CIR-DATA-DATE-PARSE`](../data/freshness.md) |
| events-outside-window-dropped | event dated before the first sample | not drawn; counted in a warning |
| events-same-date-grouped | 3 events on one date | one marker carrying all three labels in its detail |
| events-text-is-content | any label | rendered as plain text, never interpreted as markup ([`CIR-BAKE-EXPOSURE`](../data/data-json.md)) |
| events-absent-is-valid | metric with no events file | series drawn alone |

**⚖-R47 — the events table's exact contract.** Deliberately unruled: the required column names
(`date`, `event`, optional `note`), whether the table may live in the same file a freshness
adapter reads, and whether more than one events file may feed one page. **Ruled: specify at P2
kickoff**, with a fixture row landing at the same time; the shape recorded here (a dedicated
`events:` path per item, a two-column minimum, extra columns carried into the marker detail) is
the anticipated direction, not a settled schema. Settling it now would be overreach — the goal
says anticipate, not design.

_Evidence: none yet — unverified._

## CIR-DETAIL-LAYOUT — legibility rules carry over

This chart exists to let a person *notice* that a change coincided with a shift. A page that
draws the inference for them, from a handful of self-reported points, would be making a medical
claim out of a hobby dataset.

| row id | inputs | expected |
|---|---|---|
| detail-one-screen | reference viewport | same rule as the main page ([`CIR-RENDER-ONE-SCREEN`](layout.md)) |
| detail-prints-to-one-a4 | print | [`CIR-RENDER-A4`](layout.md) |
| detail-colour-not-only-channel | events vs series | markers distinguishable in greyscale ([`CIR-RENDER-STATUS-ENCODING`](colors.md)) |
| detail-accessible-equivalent | any detail page | a table of samples and events ([`CIR-RENDER-A11Y-TABLE`](colors.md)) |
| detail-y-axis-does-not-lie | any series | zero baseline, or an explicitly labelled truncated axis |
| detail-correlation-not-asserted | series with events | no trend line and no claim drawn between an event and the series; the reader draws the conclusion |

_Evidence: none yet — unverified._
