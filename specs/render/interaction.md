# Interaction — hover, focus, tap, click

The goal says "hover = the item's detail line; click = jump to the item's link, or open its
detail page", and separately that phone-first read-only viewing is the later exposure path.
Hover does not exist on a phone. This page resolves that and the click precedence the goal
leaves open.

## CIR-RENDER-DETAIL-REVEAL — three ways in, one detail <a id="cir-render-detail-reveal"></a>

The detail line ([CIR-DATA-DETAIL-LINE](../data/status-resolution.md)) is reachable by pointer
hover, keyboard focus and touch tap — the same string in all three.

| description | inputs | expected |
|---|---|---|
| hover shows the detail | pointer over an arc | detail line appears near the arc |
| focus shows the detail | keyboard Tab to an arc | same detail, same placement |
| tap shows the detail | touch on an arc, item has no link | detail appears and stays until dismissed |
| tap on an item with a link does not navigate immediately | touch on a linked arc | first tap reveals the detail; the link is a distinct target within it (see ⚖ CIR-Q-27) |
| the detail is dismissible | detail open, Esc or tap outside | closes; focus returns to the arc |
| the detail never covers the arc it describes | any arc, any position | placement avoids the source arc |
| the detail does not scroll the page | any viewport | overlay only ([CIR-RENDER-ONE-SCREEN](layout.md)) |
| only one detail is open at a time | second arc activated | first closes |

## CIR-RENDER-CLICK — what a click does <a id="cir-render-click"></a>

| description | inputs | expected |
|---|---|---|
| item with a link, no detail page | `link:` set | activation opens the link |
| item with a detail page, no link | metric-capable item ([CIR-DETAIL-PAGE-SHAPE](detail-page.md)) | activation opens the detail page |
| item with both | `link:` set and a detail page exists | the link wins; the detail page is reachable from the detail overlay as a second, labelled target (see ⚖ CIR-Q-27) |
| item with neither | plain item | activation reveals the detail only; the arc is not a link |
| external links open in a new context | `https://…` | new tab/window, `rel="noopener noreferrer"` |
| link targets are not fetched by the page | any link | no prefetch, no preview ([CIR-RENDER-NO-EGRESS](layout.md)) |
| a broken link is not a status | link 404s | the item's light is unaffected — a link is content, not an adapter |

⚖ **CIR-Q-27 — precedence when an item has both a link and a detail page.** Options: (a) link
wins, detail page reachable from the overlay (encoded); (b) detail page wins, link reachable
from the overlay; (c) an explicit `click:` key in the config choosing one. *Recommendation:
(a)* — a `link:` is an explicit authored intent, a detail page is generated. (c) is a config key
that exists only to express a preference nobody has yet stated. Whichever is ruled, the loser
must remain reachable: a generated detail page nothing links to is dead weight.

## CIR-RENDER-KEYBOARD — the whole page without a mouse <a id="cir-render-keyboard"></a>

| description | inputs | expected |
|---|---|---|
| every item is focusable | Tab through the page | each arc receives focus exactly once |
| focus order follows the data | Tab order | inside-out by ring, then item order within the ring |
| focus is visible | focused arc | visible focus indicator meeting contrast against every status fill |
| Enter/Space activate | focused arc | same as click ([CIR-RENDER-CLICK](#cir-render-click)) |
| the warning list is reachable | Tab | the warning count is a focusable control |
| no keyboard trap | detail open | Esc closes; Tab does not cycle inside forever |

## CIR-RENDER-NO-JS — the page still says something without scripts <a id="cir-render-no-js"></a>

| description | inputs | expected |
|---|---|---|
| statuses render without JS | JS disabled | the sunburst is static markup (inline SVG); all fills and labels present |
| the accessible table renders without JS | JS disabled | full table ([CIR-RENDER-A11Y-TABLE](color.md)) |
| the stale banner renders without JS | stale bake, JS disabled | see ⚖ CIR-Q-28 |
| interaction degrades, content does not | JS disabled | overlays are unavailable; every detail line is still readable in the table |

Because the picture is baked markup rather than a script-drawn canvas, "no JS" costs only the
overlays — which is the strongest argument for the renderer choice in
[CIR-Q-19](sunburst.md).

⚖ **CIR-Q-28 — can the stale-bake banner work without JS?** The banner compares the viewer's
"now" against `generated_at`, which needs a script; a purely static page cannot know it has gone
stale. Options: (a) JS computes the banner, and with JS disabled the page prints the stamp in
words and lets the reader judge (encoded); (b) the bake writes a "valid until" timestamp and
the page uses CSS/`<meta http-equiv="refresh">` tricks — fragile and still not a comparison;
(c) accept that no-JS viewers see no banner. *Recommendation: (a)* — the timestamp in words is
always visible, so the no-JS reader has the fact even without the judgement. This is the only
requirement in the tree that depends on client-side JS at all, which is worth stating plainly.

## CIR-RENDER-TOUCH — phone-first read-only <a id="cir-render-touch"></a>

| description | inputs | expected |
|---|---|---|
| every target meets the minimum touch size | 390 px-wide viewport | each arc's hit area is at least the minimum target size, or the accessible table is offered as the primary control surface |
| no interaction requires hover | touch device | every detail reachable by tap |
| no interaction requires precision | narrow arcs on a phone | slivers below the touch minimum are reachable from the table row |
| the page does not zoom-lock | phone | pinch-zoom is not disabled (a person may need to magnify a dense picture) |
| orientation change re-fits | rotate | still one screen, still no scroll |
