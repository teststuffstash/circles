# Layout — one screen, one A4, no network

Two constraints from the goal, written as things a test can fail: the whole picture fits one
screen without scrolling, and it prints legibly to a single A4 through the browser's own print
path — no separate PDF or SVG pipeline.

## CIR-RENDER-ONE-SCREEN — no scrolling, ever <a id="cir-render-one-screen"></a>

| description | inputs | expected |
|---|---|---|
| the reference viewport shows everything | 1280×800 CSS px, fixture person | no scrollbar in either axis; every ring, label, summary and stamp visible |
| a small laptop viewport still fits | 1024×640 | no scrolling; the picture shrinks |
| a phone viewport still fits | 390×740 (portrait) | no scrolling; layout may reflow (labels move outside, summary stacks) but nothing is cut |
| a very wide viewport does not stretch the circle | 2560×800 | the sunburst stays circular and centred; it does not become an ellipse |
| zoom does not break the contract | browser zoom 150% | still fits, or degrades by shrinking the picture — never by scrolling |
| the page has no scrollable containers | any viewport | no inner scroll areas; the warning list and detail open as overlays, not as page growth ([CIR-RENDER-CLICK](interaction.md)) |
| growing config does not grow the page | 7 rings × 12 items | still one screen ([CIR-RENDER-OVERFLOW](sunburst.md)) |

The sunburst is sized from the **smaller** viewport dimension, so a landscape screen leaves side
margins rather than clipping the circle.

⚖ **CIR-Q-23 — what is "one screen"?** A page cannot fit every viewport at a fixed font. Options:
(a) name a reference viewport (1280×800) as the contract and require graceful shrinking
elsewhere (encoded); (b) require no-scroll at any viewport above a stated minimum, with the
minimum font floor allowed to break instead; (c) define it only for print and let the screen
scroll. *Recommendation: (a) plus a stated phone minimum (360×640)* — a single number tests can
assert, and phone-first read-only viewing is an explicitly named later exposure path, so it
cannot be left undefined now.

## CIR-RENDER-A4 — one sheet from the browser's print dialog <a id="cir-render-a4"></a>

| description | inputs | expected |
|---|---|---|
| the page prints to exactly one sheet | fixture person, A4 portrait | one page; no second sheet with a stray footer |
| the picture fills the sheet | A4 portrait | sunburst scaled to the printable width, not left at screen size |
| status colours survive printing | any page | backgrounds print ([CIR-RENDER-PRINT-COLOR](color.md)) |
| interactive-only affordances are hidden in print | printed page | no hover chrome, no buttons |
| the detail lines reach paper | printed page | the accessible equivalent is printed ([CIR-RENDER-A11Y-TABLE](color.md)) — hover text cannot be printed, and a printout of unlabelled colours is not legible |
| the generated-at stamp is printed | printed page | present, with the staleness banner if applicable |
| links are not turned into footnote URLs by us | printed page | no injected `(https://…)` after every label; the browser's own setting governs |
| headers and footers are not assumed | printed page | the layout does not depend on the browser's header/footer being off |

⚖ **CIR-Q-24 — portrait or landscape, and what fixes the A4 page box?** A screen is ~16:10, A4
portrait is ~1:1.41; a circle sized for one leaves large voids in the other. Options:
(a) `@page { size: A4 portrait }` with the circle sized to the printable width and the summary
and accessible table filling the remaining height (encoded); (b) landscape, closer to screen
proportions but an unusual default for a page someone pins to a fridge; (c) no `@page` rule,
inheriting the user's dialog. *Recommendation: (a)* — one declared page box makes "one sheet" a
testable claim; under (c) it is not testable at all.

## CIR-RENDER-NO-EGRESS — the page talks to nobody <a id="cir-render-no-egress"></a>

| description | inputs | expected |
|---|---|---|
| no external requests at run time | page loaded with all non-document requests blocked | renders identically |
| no third-party origins in the markup | built page | zero references to any host other than the page's own origin (no CDN, font, analytics or map tile) |
| fonts are system fonts or inlined | built page | no webfont fetch |
| the page works from `file://` | saved copy opened locally | full render ([CIR-BAKE-SELF-CONTAINED](../data/data-json.md)) |
| the page works with no JS | JS disabled | the accessible equivalent renders with all statuses ([CIR-RENDER-NO-JS](interaction.md)) |

This is a privacy requirement before it is an operational one: the page is a person's health and
family status, and every external request tells a third party who is looking at it and when. It
is also the cheapest way to keep the served artifact honest — nothing can render differently
tomorrow because a CDN changed.

## CIR-RENDER-ASSET-BUDGET — small enough to be one file <a id="cir-render-asset-budget"></a>

| description | inputs | expected |
|---|---|---|
| the built page is small | fixture person | the single `index.html`, data inlined, stays within the stated budget |
| the budget is enforced by the gate | build exceeding it | CI failure, not a silent regression ([CIR-PROC-TEST-TIERS](../process/testing.md)) |
| adding an item does not multiply the page | 9 → 18 items | growth is linear in items, not in libraries |

A stated budget (recommended: 250 KB total, uncompressed) is what makes
[CIR-RENDER-NO-EGRESS](#cir-render-no-egress) and single-file self-containment survive contact
with the first "let's just add a chart library" change — it is the enforcement mechanism behind
the renderer choice in [CIR-Q-19](sunburst.md).
