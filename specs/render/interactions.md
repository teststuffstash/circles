# Interactions — hover, click, keyboard, touch

The page is client-side interactive **over baked data** — every behavior below reads only baked
fields ([`CIR-DATA-RESOLUTION-TIME`](../data/status-resolution.md): no adapter code, no date
math in the page). P0/P1 ship the main page's interactions; the annotated-timeseries detail view
is a P2 contract, specified in [detail-page.md](detail-page.md) and referenced here only so the
P0/P1 page leaves the right seams.

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-RENDER-HOVER — the detail line

Hovering, focusing or tapping a cell fills the detail strip ([`CIR-RENDER-CHROME`](layout.md))
with the item's **detail line**, taken verbatim from the artifact
([`CIR-BAKE-DETAIL-FIELDS`](../data/data-json.md)) — the page does not compose it. Three ways in,
one string out: hover, focus and tap all produce exactly the same text, which is also what
prints and what a screen reader announces.

| row id | inputs | expected |
|---|---|---|
| hover-full-line | `self/sleep` (guardrail + last-data date) | `Sleep — ok · Lights out by 23:00 on weeknights · last data 2026-08-01` |
| hover-no-guardrail | item without `guardrail:` | segment omitted, no dangling separator |
| hover-no-date | a `manual:` item | no `last data` segment |
| hover-grey-unmonitored | item with no adapter | `Exercise — unmonitored` |
| hover-warning-cause | a grey cell whose command failed | the line ends with `⚠` and the warning cause |
| hover-leave-resets | pointer leaves the chart | the strip returns to idle text, never stale content |
| hover-focus-tap-agree | the same cell reached three ways | identical string in all three |

_Evidence: none yet — unverified._

## CIR-RENDER-CLICK — where a cell leads

Click activates the cell's destination: its configured `link` if it has one, else its baked
detail page (P2). A cell with neither is **not clickable** — no pointer cursor, no dead
activation. External `https://` links open in a new tab with `rel="noopener"`; root-relative
links navigate in place. **Whichever destination loses, it stays reachable** from the detail
strip.

| row id | inputs | expected |
|---|---|---|
| click-follows-link | item with `link: https://example.test/labs` | new tab to that URL |
| click-root-relative | item with `link: /details/self-sleep.html` | in-place navigation |
| click-no-destination | item with neither link nor detail page | activation is a no-op; cursor stays default |
| click-link-wins-over-detail | P2 item with both `link` and a detail page | the link opens; the detail page is offered in the detail strip |
| click-detail-when-no-link | P2 item with a detail page and no link | the detail page opens |

**⚖-R11 — which destination wins when an item has both?** The goal says "click = jump to the
item's link, **or** open its detail page" and never rules the overlap. Three arms gave three
answers: link wins, detail wins, or the popover carries both. **Ruled: the configured `link`
wins.** `link:` is something the person deliberately wrote — "this item lives over there" — and
an explicit config should not be silently outranked by a surface the bake generated. The
decisive practical argument is the phase boundary: at P0 and P1 there are no detail pages, so
`link` is the only destination there is. If detail pages later took precedence, every linked
cell would silently change where it goes the day P2 ships, breaking the muscle memory of the one
person who uses this page every day. The loser staying reachable is what makes this cheap either
way.

_Evidence: none yet — unverified._

## CIR-RENDER-KEYBOARD — the whole page without a mouse

Every cell is focusable in a **documented order**: ring by ring, inside-out; within a ring,
siblings in display order starting at 12 o'clock — the triage reading order, not the DOM
accident. Focus shows the detail line exactly as hover does, plus a visible focus indicator;
`Enter` performs the click action.

| row id | inputs | expected |
|---|---|---|
| keyboard-tab-order | tabbing from page start | cells receive focus inside-out and clockwise |
| keyboard-focus-shows-detail | focus on a cell | the detail strip shows that cell's detail line |
| keyboard-enter-activates | focus + Enter on a linked cell | the click behavior fires |
| keyboard-focus-visible | any focused cell | a focus indicator distinguishable from the status fill |
| keyboard-accessible-name | a cell's computed name | `<label>, <status word>, ring <ring label>` |
| keyboard-no-trap | tabbing past the last cell | focus leaves the chart normally |

_Evidence: none yet — unverified._

## CIR-RENDER-TOUCH — no hover on glass

| row id | inputs | expected |
|---|---|---|
| touch-first-tap-detail | tap a linked cell | detail line shown, no navigation |
| touch-second-tap-activates | tap the same cell again | the click behavior fires |
| touch-tap-elsewhere-resets | tap outside the chart | the detail strip returns to idle |
| touch-target-size | any cell at the reference viewport | the activatable area meets the minimum touch-target size, or the cell is not activatable at all |

**⚖-R43 — what does a tap do?** Touch has no hover, which directly contradicts the goal's
"hover = the item's detail line" once phone viewing exists. Options: (a) first tap shows the
detail line, second tap on the same cell activates; (b) tap activates, long-press shows the
detail line; (c) tap always shows the detail line and the destination lives in the strip as an
explicit affordance. **Ruled: (a)** — the standard two-stage tooltip pattern, where glance
("what is this cell?") precedes travel ("leave the page"), matching the page's read-first
purpose. (b) hides navigation behind an undiscoverable gesture; (c) costs a second tap for every
read, which is the common case. Phone viewing is a later exposure path, but this ruling costs P0
nothing and must not be retrofitted differently later.

_Evidence: none yet — unverified._

## CIR-RENDER-NO-JS — the page still says something

With scripting disabled the chart may be absent, but the page must not be. The text alternative
([`CIR-RENDER-A11Y-TABLE`](colors.md)) renders from the same inlined payload and carries every
status word.

| row id | inputs | expected |
|---|---|---|
| no-js-text-alternative-renders | JS disabled | every item listed with its ring, label and status word |
| no-js-is-not-blank | JS disabled | never an empty page and never an unexplained chart frame |
| no-js-detail-lines-present | JS disabled | baked detail lines shown as text, since no composition is needed |
| no-js-links-work | JS disabled | configured links are plain anchors and still navigate |

**⚖-R44 — how much works without JS?** Options: (a) the text alternative only; (b) a fully
server-rendered static SVG chart plus the table, with JS adding only interaction; (c) nothing —
JS required. **Ruled: (b) is the target, (a) is the floor.** Because the geometry is baked and
the renderer is hand-rolled SVG (⚖-R3), emitting the chart markup at bake time costs little and
makes the no-JS page the *same* picture rather than a degraded one — but only (a) is required to
pass. (c) is rejected: a page whose entire purpose is being glanced at and printed must not
depend on a script executing.

_Evidence: none yet — unverified._
