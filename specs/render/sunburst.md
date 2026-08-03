# Sunburst geometry (CIR-RENDER-GEOM-*)

The page's shape: concentric rings of arc cells, one cell per item, colored per
[colors.md](colors.md). Geometry requirements here are **library-agnostic** — whatever
renders the page must satisfy them (see ⚖ RENDER-TECH). Data-side concepts (rings, items,
shares) are defined in [../data/circles-yaml.md](../data/circles-yaml.md); the page consumes
them only via baked `data.json` ([../data/data-json.md](../data/data-json.md)).

## CIR-RENDER-GEOM-RING-ORDER — rings read inside-out

`data.json` ring array order **is** the geometry order: `rings[0]` is the innermost ring,
adjacent to the center disc. Triage reads inward-first — the innermost ring must hold for
the outer ones to matter — so no rendering, sorting, or layout step may reorder rings.

| row (test id) | inputs | expected |
|---|---|---|
| ring-order-innermost-first | `data.json` rings `[self, partner, children, wider]` | `self` is the innermost rendered ring, `wider` the outermost |
| ring-order-never-resorted | rings whose labels sort differently alphabetically (`wider`, `self`) | rendered order still follows the array, never alphabetical/status sorting |

## CIR-RENDER-GEOM-RING-PARTITION — the independent ring partition

**Each ring subdivides the full 360° circle on its own.** An outer ring's arcs never nest
inside an inner item's arc: no angular containment, no parent-child geometry between rings.
The fixture's key example: `nova` and `kit` (`share: 0.5` each) are two half-arcs spanning
the **whole** `children` ring, not the arc of any `partner` item.

**⚖ AMBIGUITY: RING-PARTITION** — the goal issue calls the form "a sunburst chart", and
classic sunburst implementations nest each ring's segments inside their parent item's arc.
The issue never states whether outer rings nest. Options: (a) independent partition — every
ring spans the full circle and subdivides by its own items' shares; (b) nested — outer items
declare a parent item and share its arc. **Recommendation: (a)** — the issue's own schema
sketch and the fixture have **no parent field** (rings are flat lists; the `children` ring's
two half-arcs sum to the whole ring), and triage doctrine is per-ring ("the innermost ring
must hold"), not per-branch. Nested geometry would also force outer-ring emptiness when an
inner item has no outer children. Recorded as an ⚖ because "sunburst" usually implies (b) —
if the human intended nesting, this entry is where to overrule. See Follow-ups in the
introducing PR.

| row (test id) | inputs | expected |
|---|---|---|
| partition-independent-full-circle | ring `children` with two `share: 0.5` items under a one-item `partner` ring | the two half-arcs span the full 360°, independent of the `partner` arc |
| partition-no-containment | item counts differ per ring (3 / 1 / 2 / 2) | every ring still spans the full circle; no ring's arc is clipped by another ring |
| partition-no-parent-field | any baked `data.json` | rendering needs no parent pointer; cell identity stays `(ring, item)` (CIR-DATA-SCHEMA-CELL-IDENTITY) |

## CIR-RENDER-GEOM-ARC-SHARE — arc angles from shares

Within a ring, an item's arc angle is `360° × share ÷ (Σ shares of the ring's items)`
(CIR-DATA-SHARE-WEIGHT). Cells of one ring are separated by a uniform visual gap so adjacent
cells read as distinct cells; the gap is constant per ring and never so large that a
single-item ring shows a visible notch.

| row (test id) | inputs | expected |
|---|---|---|
| arc-share-half-arcs | two siblings `share: 0.5` each | each arc ≈ 180° minus half the inter-cell gap (the fixture's Nova/Kit case) |
| arc-share-single-item-ring | one item in a ring | a full 360° band (gap invisible) |
| arc-share-mixed-weights | siblings with shares 2, 1, 1 | arcs ≈ 180° / 90° / 90° |
| arc-gap-uniform | any ring | all inter-cell gaps in the ring equal |

## CIR-RENDER-GEOM-SIBLING-ORDER — where siblings start

The first item of each ring's array starts at **12 o'clock**; siblings proceed **clockwise**
in array order. Every ring starts its own first sibling at 12 o'clock (a consequence of the
independent partition, not a separate choice).

**⚖ AMBIGUITY: SIBLING-ORDER** — the goal issue lists "sibling ordering" among its open
questions. Options: (a) config order, clockwise from 12 o'clock; (b) config order,
counterclockwise from 12 o'clock; (c) sorted by status (worst first). **Recommendation:
(a)** — config order is what the person wrote and reorders only when they reorder it
(spatial memory survives status changes — a cell going 🔴 stays in place); 12 o'clock
clockwise is the dominant pie/sunburst convention. (c) is rejected outright: a page whose
geometry reshuffles as statuses change can't be read "at a glance" day over day. Note for
the builder: chart-library defaults for start angle and direction vary by library — the
page must set both **explicitly**, never inherit a default (see Provenance).

| row (test id) | inputs | expected |
|---|---|---|
| sibling-order-clockwise-from-noon | ring items `[nova, kit]` | `nova` spans 12 o'clock → 6 o'clock, `kit` 6 → 12 |
| sibling-order-stable-across-status-flip | same `data.json`, one item flipped 🟢→🔴 | identical geometry; only the color changes |

## CIR-RENDER-GEOM-RING-THICKNESS — radial layout

All rings have **equal radial thickness**; the center disc (carrying the person's name —
CIR-RENDER-LAYOUT-CHROME) has radius ≈ one ring thickness. Equal thickness keeps the
innermost ring — the most important one — as readable as the outer rings, which compensate
with longer arc length.

| row (test id) | inputs | expected |
|---|---|---|
| ring-thickness-equal | 4-ring config | all ring thicknesses within rendering tolerance of each other |
| center-disc-holds-name | any config | center disc radius ≈ 1 ring thickness; person name fits inside at the reference viewport |

## CIR-RENDER-GEOM-LABELS — labels on cells

Item labels render **inside their cell's arc**, centered on the arc's mid-angle. A label
never overflows its cell: if the label does not fit the arc (at the rendered size), the page
elides it with `…`, and if even an elided form does not fit, the cell shows **no label** —
the full label is always available in the detail line (CIR-RENDER-INTERACT-HOVER) and the
text alternative (CIR-RENDER-A11Y-TEXT-ALTERNATIVE). Ring labels never appear on the chart;
the ring key names the rings (CIR-RENDER-LAYOUT-CHROME). Labels are opaque Unicode — glyphs
like `①` and `◀` pass through untouched (CIR-DATA-SCHEMA-RING).

| row (test id) | inputs | expected |
|---|---|---|
| label-inside-arc | fixture config | each item label rendered within its own cell's bounds |
| label-elided-when-tight | an item whose label exceeds its arc | label truncated with `…`, never painted outside the cell |
| label-omitted-when-tiny | an arc too small for any elided label | no label painted; cell still hoverable/focusable with full label in the detail line |
| label-glyphs-passthrough | label `◀ Nova` | glyph rendered as-is |

## CIR-RENDER-GEOM-DENSITY — the content envelope

One screen must hold the whole picture — but config is unbounded, so the spec pins a
**legibility envelope**: at the reference viewport (CIR-RENDER-LAYOUT-ONE-SCREEN), configs
within **≤ 6 rings and ≤ 8 items per ring** must render with every label legible (not
elided) and every cell ≥ the minimum hover/focus target. Beyond the envelope the bake still
succeeds and the page still renders (label elision and omission absorb the pressure), but
the bake emits a **build warning** naming the overflow.

**⚖ AMBIGUITY: CONTENT-ENVELOPE** — what happens when a config grows past one legible
screen. Options: (a) hard validation limits (bake fails); (b) documented envelope + build
warning + graceful elision; (c) silent best-effort. **Recommendation: (b)** — the
one-screen constraint is a product promise about *legibility*, and failing the bake (a)
would take the whole page dark because a person added a ninth friend; silence (c) hides a
real product signal. The envelope numbers (6 rings × 8 items) are sized to the A4 print
constraint: 6 rings × ~13 mm radial thickness plus center disc ≈ the printable width of an
A4 portrait chart — see [layout.md](layout.md). If real use outgrows the envelope, the
answer is a spec change, not a bigger default.

| row (test id) | inputs | expected |
|---|---|---|
| envelope-inside | 4 rings, ≤ 3 items/ring (the fixture) | no density warning; all labels legible at reference viewport |
| envelope-at-limit | 6 rings, 8 items in one ring | renders legibly; no warning |
| envelope-exceeded-ring-count | 7 rings | bake succeeds with a build warning; page renders with elision rules in force |
| envelope-exceeded-item-count | 9 items in one ring | bake succeeds with a build warning naming the ring |

## Proposed fixture rows (for the builder to land — not landed by this spec pass)

- a second fixture person exercising the density boundary: 6 rings, one 8-item ring with
  long labels (exercises `envelope-at-limit`, `label-elided-when-tight`,
  `label-omitted-when-tiny`);
- a sibling trio with `share: 2, 1, 1` (exercises `arc-share-mixed-weights`);
- a single-item ring (exercises `arc-share-single-item-ring`).

## Provenance

- Classic sunburst libraries implement **nested** parent→child angular containment (Plotly's
  `sunburst`, D3's `partition` layout); ECharts can draw independent concentric rings via
  multiple `pie` series with explicit `radius` bands. Reasoned from training knowledge —
  this ride has no WebSearch/WebFetch tool, so library behavior was not verified against a
  live source. The requirements above are deliberately library-agnostic; only ⚖ RENDER-TECH
  in [layout.md](layout.md) touches implementation.
- The 12-o'clock-clockwise convention is the common pie-chart default (D3); some libraries
  default elsewhere — hence the "set explicitly" note in SIBLING-ORDER. Training knowledge,
  unverified in this ride.
