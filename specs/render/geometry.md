# render — sunburst geometry, one-screen/A4, overflow

The page is a sunburst: concentric rings of arc segments, each cell colored by its status
light. This page owns geometry and the one-screen/A4 constraint; color and interactions live in
[color.md](color.md) and [interactions.md](interactions.md).

## Requirements

### CIR-RENDER-RING-ORDER — rings inside-out, triage inward-first
Rings render inside-out in config order: index 0 is the innermost ring. The innermost ring must
hold for the outer ones to matter, so triage reads inward-first. Ring taxonomy comes from the
person's config, never from code. Phase: P0.

| description | inputs | expected |
|---|---|---|
| config order preserved | rings self, partner, children, wider | self innermost, wider outermost |
| triage reads inward-first | 🔴 on self, 🟢 on wider | self (inner) is the priority read |

### CIR-RENDER-ARC-SUBDIVISION — items subdivide a ring
Each item in a ring is an arc segment; sibling arcs subdivide the ring's full circle. Arc angle
is proportional to the item's share (CIR-DATA-SHARE-WEIGHTS). Two `0.5` shares are two
half-arcs. Phase: P0.

| description | inputs | expected |
|---|---|---|
| two equal siblings | shares 0.5, 0.5 | two half-arcs (180° each) |
| three equal siblings | no shares, 3 items | three 120° arcs |
| weighted siblings | shares 0.75, 0.25 | arcs 270° and 90° |

### CIR-RENDER-ONE-SCREEN — fits one screen without scrolling
The whole picture fits one screen without scrolling at the reference viewport
([CIR-RENDER-REFERENCE-VIEWPORT](#cir-render-reference-viewport)). This is a hard constraint,
not a preference. Phase: P0.

### CIR-RENDER-REFERENCE-VIEWPORT — the testable "one screen"
"Fits one screen" is defined against a reference viewport of **1280×800 CSS pixels** (a common
laptop). The requirement is testable: render the page at that viewport and assert no scrollbars
and no clipping. Phase: P0.

### CIR-RENDER-A4-PRINT — prints legibly to one A4
The page prints legibly to a single A4 page via the browser's print (no separate PDF/SVG
pipeline — HTML from day one). Print CSS must fit the sunburst (plus legend, per ⚖ RENDER-6)
onto one A4 sheet. Phase: P0.

### CIR-RENDER-OVERFLOW — too many rings/items still fits
When the config has more rings/items than comfortably fit, the renderer scales the sunburst to
fit the viewport (fit-to-screen) rather than scrolling or truncating. Arcs may shrink but must
stay above a minimum legible size; if the minimum cannot be met, see ⚖ RENDER-2. Phase: P0.

### CIR-RENDER-EMPTY-STATE — empty rings and empty config
A ring with no items is omitted (renders nothing). A config with no rings renders a single
"no data" state (a message, not a broken chart). Phase: P0.

| description | inputs | expected |
|---|---|---|
| empty ring omitted | a ring with `items: []` | ring not rendered |
| empty config | no rings | "no data" state, no chart |

## ⚖ AMBIGUITY entries

### ⚖ RENDER-1 — reference viewport value
The goal says "one screen" but never fixes a resolution, so "fits one screen" is untestable
until a reference is chosen.
- Options: (a) 1280×800; (b) 1920×1080; (c) 1366×768 (most common laptop).
- **Recommendation: (a) 1280×800** — a common, conservative laptop size; a page that fits it
  also fits larger screens. Specified as [CIR-RENDER-REFERENCE-VIEWPORT](#cir-render-reference-viewport).

### ⚖ RENDER-2 — overflow behavior below minimum legibility
If scaling to fit would make arcs illegibly small (many rings/items), the goal's "no scrolling"
and "readable at a glance" collide.
- Options: (a) keep scaling (arcs get tiny); (b) allow a bounded scroll only in the extreme;
  (c) collapse low-priority rings into a summary.
- **Recommendation: (a)** for v0 — keep scaling and rely on hover for detail; flag the
  legibility floor as a Follow-up for the operator. The one-screen constraint is hard.

### ⚖ RENDER-3 — phone scope vs the hard one-screen constraint
The goal calls phone "the later exposure path" but also calls one-screen "hard". It is unclear
whether the one-screen requirement must hold on a phone in P0.
- Options: (a) one-screen is desktop-only in P0; phone is a later, separate pass; (b) one-screen
  must hold on phone from P0.
- **Recommendation: (a)** — P0 targets the desktop reference viewport; phone-first read-only is
  a later phase. Flagged as a PR Follow-up.

### ⚖ RENDER-4 — what the sunburst library must guarantee
The goal allows Plotly/D3/ECharts but does not say which. The spec should not pick a library,
but must fix the geometry contract any library must satisfy (ring order, arc subdivision,
fit-to-screen, print).
- Options: (a) leave the library open, fix only the contract; (b) mandate Plotly.
- **Recommendation: (a)** — fix the contract (these requirements), let the builder choose the
  library that satisfies it. No ⚖ needed beyond this note; recorded for provenance.

### ⚖ RENDER-5 — accessibility of the chart as a whole
The sunburst is a visual chart; the goal does not say how its information is exposed to
screen readers or keyboard users.
- Options: (a) provide an accessible text/table alternative (a list of items + statuses);
  (b) rely on the sunburst alone.
- **Recommendation: (a)** — a hidden-but-accessible list of every item and its status, so the
  "readable at a glance" promise extends to non-visual readers. Flagged as a PR Follow-up.

### ⚖ RENDER-6 — what prints on A4
The goal says the page "prints legibly to a single A4" but not what content prints.
- Options: (a) the sunburst only; (b) the sunburst plus a compact legend; (c) the sunburst plus
  a full item/status list.
- **Recommendation: (b)** — sunburst + compact legend; interactive elements (hover popovers)
  are excluded from print. A full list would overflow one A4.
