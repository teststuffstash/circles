# Interactions — hover, click, keyboard, touch (CIR-RENDER-INTERACT-*, CIR-RENDER-DETAIL-*)

The page is client-side interactive **over baked `data.json`** — every behavior below reads
only baked fields (CIR-DATA-STATUS-RESOLUTION-TIME: no adapter code, no date math in the
page). P0/P1 ship the main page's interactions; the annotated-timeseries detail page is the
P2 contract, specified here so the P0/P1 page already leaves the right seams
(`detail_page` in `data.json` — CIR-DATA-DATAJSON-DETAIL-FILES).

## CIR-RENDER-INTERACT-HOVER — the detail line

Hovering (or focusing, or tapping — see TOUCH) a cell fills the detail strip
(CIR-RENDER-LAYOUT-CHROME) with the item's **detail line**, composed at render time from
baked fields (CIR-DATA-DATAJSON-DETAIL-FIELDS), segments joined with `·`, absent fields
omitted with no placeholder:

`<label> — <status word> · <guardrail> · last data <ISO date>` + ` · ⚠ <warning cause>` when
the item carries a build warning.

| row (test id) | inputs | expected |
|---|---|---|
| hover-full-line | `sleep` (guardrail + last-data date) | `Sleep — ok · Lights out by 23:00 on weeknights · last data 2026-08-01` |
| hover-no-guardrail | item without `guardrail:` | segment omitted, no dangling separator |
| hover-no-date | `manual:` item | no `last data` segment |
| hover-grey-unmonitored | item with no adapter | `Exercise — unmonitored` |
| hover-warning-cause | grey cell whose command failed | line ends with `⚠` + the warning cause |
| hover-leave-resets | pointer leaves the chart | strip returns to its idle text, no stale content |

## CIR-RENDER-INTERACT-CLICK — where a cell leads

Click activates the cell's destination: its `detail_page` if one is baked (P2), else its
`link`. A cell with neither is **not clickable** (no pointer cursor, no dead activation).
External (`https://`) links open in a new tab with `rel="noopener"`; root-relative links
navigate in place.

| row (test id) | inputs | expected |
|---|---|---|
| click-follows-link | item with `link: https://example.test/labs` | new tab to that URL |
| click-root-relative | item with `link: /details/self-sleep.html` | in-place navigation |
| click-no-destination | item with neither link nor detail page | activation is a no-op; cursor stays default |
| click-detail-page-wins | P2 item with both `detail_page` and `link` | detail page opens; the link is offered inside it (⚖ LINK-VS-DETAIL) |

**⚖ AMBIGUITY: LINK-VS-DETAIL** — the goal issue says "click = jump to the item's link, or
open its detail page" without ruling an item that has both. Options: (a) the detail page
wins and surfaces the link inside itself; (b) the link wins; (c) declaring both is a
validation error. **Recommendation: (a)** — the detail page is the in-product surface (it
can offer the external link as "open source"), while (b) would strand the P2 investment
whenever a link exists and (c) forbids a sensible combination (in-product trend + external
source). P2 contract; confirm at P2 kickoff.

## CIR-RENDER-INTERACT-KEYBOARD — the whole page without a mouse

Every cell is focusable in a **documented order** (ring by ring, inside-out; within a ring,
siblings in display order starting at 12 o'clock). Focus shows the detail line (same as
hover) and a visible focus indicator; `Enter` performs the click action. The cell's
accessible name is `<label>, <status word>, ring <ring label>`.

| row (test id) | inputs | expected |
|---|---|---|
| keyboard-tab-order | tabbing from page start | cells receive focus inside-out, clockwise, matching the triage reading order |
| keyboard-focus-detail | focus on a cell | detail strip shows that cell's detail line |
| keyboard-enter-activates | focus + Enter on a linked cell | the click behavior fires |
| keyboard-focus-visible | any focused cell | a focus indicator distinguishable from the status fill is visible |

## CIR-RENDER-INTERACT-TOUCH — no hover on glass

**⚖ AMBIGUITY: TOUCH-TAP** — touch has no hover; what does a tap do? Options: (a) first tap
shows the detail line, second tap on the same cell activates its destination; (b) tap
activates, long-press shows the detail line; (c) tap always shows the detail line and the
destination lives in the strip as an explicit affordance. **Recommendation: (a)** — the
standard double-stage tooltip pattern: glance (what is this cell?) precedes travel (leave
the page), matching the page's read-first purpose; (b) hides navigation behind an
undiscoverable gesture; (c) costs a second tap for *every* read, the common case. Phone-first
viewing is a later exposure path, but this ruling costs P0 nothing and must not be
retrofitted differently later.

| row (test id) | inputs | expected |
|---|---|---|
| touch-first-tap-detail | tap a linked cell | detail line shown, no navigation |
| touch-second-tap-activates | tap the same cell again | the click behavior fires |
| touch-tap-elsewhere-resets | tap outside the chart | detail strip returns to idle |

## CIR-RENDER-DETAIL-PAGE — the annotated timeseries (P2 contract)

The detail page is the generic **annotated timeseries**: a metric series overlaid with dated
intervention events — "medication changes × nightly sleep" is one instance, "training load ×
resting heart rate" another. The page is a sibling static asset (`details/<ring>--<item>.html`
rendering the baked payload `details/<ring>--<item>.json` —
CIR-DATA-DATAJSON-DETAIL-FILES), obeys the same layout, color, and print rules as the main
page, and always offers a way back to the main page.

**Config sketch (P2, provisional — a P2 spec pass owns the final schema):**

```yaml
items:
  - id: sleep
    status: { … }                  # unchanged — detail is orthogonal to status
    detail:
      metric:                      # a metric adapter (P2's first: sqlite)
        sqlite: { path: metrics.db, query: "SELECT date, hours FROM sleep" }
        unit: hours                # y-axis label
      events: notes/sleep-interventions.md   # markdown table of dated events
```

An item may declare `detail:` with any, or no, `status:` adapter — the two are orthogonal
(a ⚪ item can still carry a detail page).

**Baked payload shape (P2, provisional):**

```json
{
  "item": "self/sleep",
  "metric": { "unit": "hours", "series": [ { "date": "2026-08-01", "value": 7.33 } ] },
  "events": [ { "date": "2026-06-14", "event": "Started melatonin 1mg", "note": null } ]
}
```

| row (test id) | inputs | expected |
|---|---|---|
| detail-renders-series-and-events | payload with series + 2 events | line/point series plotted, 2 event markers at their dates |
| detail-axes-honest | any payload | y-axis labeled with `unit`; x-axis spans the series' actual date range; dates, not datetimes (same calendar-date doctrine as freshness) |
| detail-event-hover | hover/focus an event marker | its date + event text |
| detail-back-to-main | any detail page | a visible "back to circles" control + browser back both work |
| detail-empty-series | payload with zero series points | the events still render over an empty plot; no fabricated zero line |
| detail-print | browser print | chart + events legend fit one A4 (same print contract as the main page) |

**⚖ AMBIGUITY: SERIES-GAPS** — a metric with missing dates (a wearable gap, a skipped
week). Options: (a) break the line across gaps; (b) connect across gaps; (c) interpolate
values. **Recommendation: (a)** — a connected line claims data that was never observed, and
interpolation is worse (invented numbers on a health-adjacent page); a visible gap *is* the
honest rendering, the same doctrine that keeps tooling failure off the red channel.

## CIR-RENDER-DETAIL-EVENTS — the intervention-event table (P2 contract)

Events come from a **markdown pipe table** in a file resolved like a freshness `source:`
(relative to the `circles.yaml` directory — CIR-DATA-FRESHNESS-SOURCE). The **first** pipe
table in the file is the event table; required columns `date` (ISO 8601, the same parsing
rules as CIR-DATA-FRESHNESS-DATE-PARSING) and `event` (text), optional `note` (text);
header matching is case-insensitive; unknown columns are ignored.

| row (test id) | inputs | expected |
|---|---|---|
| events-table-basic | `\| date \| event \|` table with 2 rows | 2 events baked with date + text |
| events-table-with-note | a `note` column present | notes carried into the payload |
| events-table-extra-column | an extra `owner` column | ignored |
| events-row-bad-date | a row with `next Tuesday` | row skipped + build warning (⚖ EVENTS-TABLE-PARSING) |
| events-file-missing | `events:` path absent | item bakes without events + build warning (never a failed bake — the freshness missing-source doctrine) |
| events-table-none-in-file | file with no pipe table | zero events + build warning |

**⚖ AMBIGUITY: EVENTS-TABLE-PARSING** — how strict the events table is. Options: (a) skip
bad rows with a build warning; (b) any bad row fails the bake; (c) silent skip.
**Recommendation: (a)** — consistent with the freshness doctrine (bad data ⇒ ⚪/warning,
never a tooling-synthesized verdict, never a dead pipeline over one typo'd row); (b) lets a
markdown typo take the whole nightly page down; (c) hides the typo forever.

## Proposed fixture rows (for the builder to land — not landed by this spec pass)

- an item carrying both `link:` and (P2) a detail page (exercises `click-detail-page-wins`);
- an events file with one bad-date row among good rows (exercises `events-row-bad-date`);
- a metric series with a deliberate two-week gap (exercises ⚖ SERIES-GAPS rendering);
- these are P2-dated; P0/P1 needs no new fixture beyond what the data pages already propose.

## Provenance

The double-stage touch pattern (⚖ TOUCH-TAP) and `rel="noopener"` on `target="_blank"` are
training-knowledge web conventions, unverified against live docs in this ride (no
WebSearch/WebFetch tool). Nothing else on this page leans on external sources.
