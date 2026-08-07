# Sunburst geometry

The page's shape: concentric rings of arc cells, one cell per item, coloured per
[colors.md](colors.md). Requirements here are **library-agnostic** — whatever renders the page
must satisfy them (⚖-R3). Data-side concepts (rings, items, shares) are defined in
[../data/circles-yaml.md](../data/circles-yaml.md); the page consumes them only via the baked
artifact ([../data/data-json.md](../data/data-json.md)).

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-RENDER-RING-ORDER — rings read inside-out

The artifact's ring array order **is** the geometry order: `rings[0]` is the innermost ring,
adjacent to the centre disc. Triage reads inward-first, so no rendering, sorting or layout step
may reorder rings.

| row id | inputs | expected |
|---|---|---|
| ring-order-innermost-first | rings `[self, partner, children, wider]` | `self` is the innermost rendered ring, `wider` the outermost |
| ring-order-never-resorted | rings whose labels sort differently alphabetically | rendered order still follows the array, never alphabetical or status sorting |

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-RING-ORDER — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `ring-order-innermost-first` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-RING-PARTITION — rings are independent, not a hierarchy

A classic sunburst is a hierarchy: each ring subdivides its parent's arc, so an outer segment is
angularly contained by its parent. **circles is not that.** *Self*, *Partner*, *Children* and
*Wider life* are independent life areas ordered by dependency, not a parent-child tree —
`children/nova` is not "part of" any item in the *self* ring. Each ring spans the full 360° on
its own angular scale.

| row id | inputs | expected |
|---|---|---|
| partition-full-circle-per-ring | ring with 1 item | one 360° band |
| partition-independent-scales | inner ring 3 items, outer ring 2 items | 120°/120°/120° and 180°/180°; no alignment between rings |
| partition-no-containment | item counts differ per ring (3 / 1 / 2 / 2) | no ring's arc is clipped or bounded by another ring's |
| partition-no-parent-field | any baked artifact | rendering needs no parent pointer; cell identity stays `(ring, item)` |
| partition-ring-boundaries-visible | adjacent rings, both 🟢 | a gap or stroke separates the bands so they do not read as one blob |
| partition-item-boundaries-visible | two adjacent 🟢 items | separated by a gap or stroke |

This is a **direct constraint on the renderer** and the reason ⚖-R3 exists: a hierarchical
sunburst primitive cannot express it. The fixture's key example is `nova` and `kit`
(`share: 0.5` each) spanning the **whole** `children` ring, not the arc of any `partner` item.

**⚖-R29 — do outer rings nest?** The goal issue calls the form "a sunburst chart", and classic
sunburst implementations nest each ring's segments inside their parent's arc; the issue never
states whether circles' outer rings nest. Options: (a) independent partition — every ring spans
the full circle and subdivides by its own items' shares; (b) nested — outer items declare a
parent and share its arc. **Ruled: (a).** The goal's own schema sketch and the fixture have no
parent field (rings are flat lists, and the `children` ring's two half-arcs sum to the whole
ring), and the triage doctrine is per-ring, not per-branch. Nesting would also force outer-ring
emptiness wherever an inner item has no outer children. Recorded as an ⚖ rather than assumed,
because "sunburst" usually implies (b) — this entry is where to overrule.

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-RING-PARTITION — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `partition-full-circle-per-ring` | PASS | — |
| `partition-ring-boundaries-visible` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-ARC-SHARE — arc angles from shares

Within a ring, an item's arc angle is `360° × share ÷ (Σ shares of the ring's items)`
([`CIR-DATA-SHARE`](../data/circles-yaml.md)). Cells of one ring are separated by a uniform
visual gap; the gap is constant per ring and never so large that a single-item ring shows a
visible notch.

| row id | inputs | expected |
|---|---|---|
| arc-share-half-arcs | two siblings `share: 0.5` each | each arc ≈ 180° minus half the inter-cell gap (the fixture's Nova/Kit case) |
| arc-share-single-item-ring | one item in a ring | a full 360° band, gap invisible |
| arc-share-mixed-weights | siblings with shares 2, 1, 1 | arcs ≈ 180° / 90° / 90° |
| arc-gap-uniform | any ring | all inter-cell gaps in the ring equal |

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-ARC-SHARE — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `arc-share-half-arcs` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-SIBLING-ORDER — where siblings start

The first item of each ring's array starts at **12 o'clock**; siblings proceed **clockwise** in
array order. Every ring starts its own first sibling at 12 o'clock — a consequence of the
independent partition, not a separate choice. The page must set start angle and sweep direction
**explicitly**; library defaults for both vary.

| row id | inputs | expected |
|---|---|---|
| sibling-order-clockwise-from-noon | ring items `[nova, kit]` | `nova` spans 12 → 6 o'clock (the right half), `kit` 6 → 12 |
| sibling-order-stable-across-status-flip | same artifact, one item flipped 🟢→🔴 | identical geometry; only the colour changes |
| sibling-order-follows-config | items reordered in `circles.yaml` | rendered order follows the file, never status severity |

**⚖-R28 — the fixture's `◀ Nova` / `Kit ▶` glyphs.** The arrows point outward-left and
outward-right, which reads as an intent: Nova on the left half, Kit on the right. Clockwise from
12 o'clock puts the *first* item in the **right** half — so under the rule above, Nova is on the
right and the arrows point the wrong way. No arm in the fan-out noticed the conflict; two ruled
the convention without checking the fixture, one asserted both in the same table. Options:
(a) the glyphs are decoration and carry no geometric meaning; (b) they are a requirement, so the
sweep runs counter-clockwise; (c) they are a requirement, so the sweep starts at 6 o'clock.
**Ruled: (a).** Labels are opaque Unicode passed through untouched
([`CIR-DATA-SCHEMA-RING`](../data/circles-yaml.md)), and a label's *content* must never
influence geometry — that would make every future person's label text load-bearing. The glyphs
stay in the fixture because they exercise Unicode passthrough, and this entry exists so nobody
later reads them as a placement rule. The P0 build confirmed the ruling holds in practice:
labels rendered as opaque text with no geometric effect, Nova landed on the right half, and the
arrows visibly point "wrong" on the rendered page — that is the accepted cost of never letting
label content drive geometry.

**⚖-R36 — sibling ordering itself.** Options: (a) config order, clockwise from 12 o'clock;
(b) config order, counter-clockwise; (c) sorted by status, worst first. **Ruled: (a).** Config
order is what the person wrote and changes only when they change it, so spatial memory survives
status changes — a cell going 🔴 stays where it was. (c) is rejected outright: a page whose
geometry reshuffles as statuses change cannot be read "at a glance" day over day.

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-SIBLING-ORDER — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `sibling-order-clockwise-from-noon` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-RING-THICKNESS — the most important ring is the smallest

Inside-out ordering puts the ring that matters most at the smallest radius, where arc length is
shortest and labels fit worst. Radial thickness is the only lever that can compensate.

| row id | inputs | expected |
|---|---|---|
| thickness-non-increasing-outward | 4 rings | radial thickness is non-increasing from the innermost ring outward |
| innermost-legible-at-capacity | 4 rings × 3 items each, one-screen size | every innermost label readable at the minimum font (`CIR-RENDER-LABELS`) |
| centre-hole-is-not-zero | any config | a hole remains; the innermost ring is a band, not a pie — a filled centre has no room for its label and reads as a fifth status |
| centre-disc-holds-identity | any config | the disc carries the person's name, the generated-at stamp and the summary counts, never a light |

**⚖-R10 — how inner-ring legibility is bought.** Options: (a) equal thickness for every ring,
with small inner labels and the detail on interaction; (b) non-increasing thickness outward, so
inner bands are proportionally thicker and arc *area* is closer to equal; (c) a leader line or
outside label for the innermost ring only. **Ruled: (b).** Under (a) — which is the other arm's
answer — the innermost ring is both the shortest arc and the same thickness as everything else,
so the ring the doctrine calls most important is the least visible cell on the page, and at A4
size it is the first thing to become unreadable. (c) buys legibility at the cost of the
one-screen budget. Nobody else in the fan-out raised this; it has a real consequence at print
size, which is why it is recorded rather than left to the implementer.

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-RING-THICKNESS — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `centre-disc-holds-identity` | PASS | — |
| `centre-hole-is-not-zero` | PASS | — |
| `thickness-non-increasing-outward` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-MIN-ARC — no unreadable slivers

A sliver that cannot be seen, hovered or tapped is an item the person believes is monitored and
never actually looks at — dangerous-green by geometry rather than by data.

| row id | inputs | expected |
|---|---|---|
| min-arc-tiny-share-still-drawn | shares 100 and 1 in one ring | the small item is drawn at the minimum arc angle; the others absorb the difference |
| min-arc-exceeded-by-ring | 30 items in one ring against the minimum angle | build warning; the page still draws |
| min-arc-adjustment-is-disclosed | an item whose arc was widened to the minimum | the detail line states the declared share, so geometry never silently misreports a weight |
| overflow-capped | 120 items in one ring (even floored arcs alone overflow) | build warning; arcs capped to fit 360°, preventing visual overlap |

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-MIN-ARC — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `min-arc-exceeded-by-ring` | PASS | — |
| `min-arc-tiny-share-still-drawn` | PASS | — |
| `overflow-capped` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-LABELS — labels fit, truncate, or step aside

Item labels render **inside their cell's arc**, centred on the arc's mid-angle. A label never
overflows its cell. Ring labels never appear on the chart — the ring key names them
([`CIR-RENDER-CHROME`](layout.md)).

| row id | inputs | expected |
|---|---|---|
| label-inside-arc | fixture config | each item label rendered within its own cell's bounds |
| label-elided-when-tight | a label that exceeds its arc | truncated with `…`, never painted outside the cell |
| label-omitted-when-tiny | an arc too small for any elided label | no label painted; the cell stays hoverable and focusable with the full label in its detail line |
| label-full-text-always-reachable | any elided or omitted label | full text present in the detail line and the text alternative |
| label-glyphs-passthrough | label `◀ Nova` | glyph rendered as-is |

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-LABELS — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `label-glyphs-passthrough` | PASS | — |
| `label-inside-arc` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-CAPACITY — how much the page holds

One screen must hold the whole picture, but config is unbounded — so capacity is pinned as a
**legibility envelope**: at the reference viewport, configs within **≤ 6 rings and ≤ 8 items per
ring** render with every label legible (not elided) and every cell at or above the minimum
hover/focus target. Beyond the envelope the bake still succeeds and the page still renders, with
a build warning naming the overflow.

| row id | inputs | expected |
|---|---|---|
| capacity-inside-envelope | 4 rings, ≤ 3 items/ring (the fixture) | no density warning; all labels legible at the reference viewport |
| capacity-at-limit | 6 rings, 8 items in one ring | renders legibly; no warning |
| capacity-exceeded-ring-count | 7 rings | bake succeeds with a build warning; page renders with elision in force |
| capacity-exceeded-item-count | 9 items in one ring | bake succeeds with a build warning naming the ring |
| capacity-minimum-page | 1 ring, 1 item | a single full-circle band; never an empty picture |
| capacity-empty-ring-band | ring with zero items | the band is drawn in the unmonitored treatment with its ring label, plus a warning; never omitted |

**⚖-R35 — what happens when a config outgrows one legible screen.** Options: (a) hard
validation limits, bake fails; (b) a documented envelope plus a build warning and graceful
elision; (c) silent best effort. **Ruled: (b).** The one-screen constraint is a product promise
about *legibility*; failing the bake would take the whole page dark because someone added a
ninth friend, and silence hides a real product signal. The envelope numbers are sized to the A4
print constraint (see [layout.md](layout.md)). If real use outgrows them, the answer is a spec
change, not a bigger default.

<details class="evidence-block">
<summary>Evidence: 6 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-CAPACITY — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `capacity-at-limit` | PASS | — |
| `capacity-empty-ring-band` | PASS | — |
| `capacity-exceeded-item-count` | PASS | — |
| `capacity-exceeded-ring-count` | PASS | — |
| `capacity-inside-envelope` | PASS | — |
| `capacity-minimum-page` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-SUMMARY — the count that survives everything

The page carries a one-line summary of its own statuses — greens, yellows, reds, and the grey
reasons counted separately: unmonitored by choice, adapter failing, not evaluated — taken
verbatim from the artifact. The wording is reason-accurate by construction: it derives from
`grey_reason` (⚖-R50), so a phase that evaluates nothing never reads as a page full of failures.

| row id | inputs | expected |
|---|---|---|
| summary-matches-the-picture | 9 items | counts equal the drawn arcs |
| summary-separates-grey-reasons | 1 by-choice, 1 by-failure, 1 not-evaluated (P0 `command:` item) | "1 unmonitored · 1 adapter failing · 1 not evaluated", never "3 unmonitored" ([`CIR-DATA-GREY-REASON`](../data/status-resolution.md)) |
| summary-survives-print | printed page | present in the printed output |
| summary-is-not-a-rollup | any config | no ring and no page is assigned a colour |

**⚖-R9 — should rings roll up to a status, and what lives in the centre hole?** The "innermost
must hold" doctrine invites an aggregate light per ring, and the hole invites an overall one.
Options: (a) no rollup — the hole carries the person's name, the stamp and the summary counts;
(b) worst-item rollup per ring, shown on the ring label; (c) an overall light in the centre.
**Ruled: (a).** A rollup is a fabricated status: no adapter stands behind it, so it cannot be
traced, tested or acted on. Worst-wins in particular trains the reader to ignore a permanently
red area — the opposite of what the page is for. Counts give the same at-a-glance signal without
inventing a verdict.

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-SUMMARY — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `summary-is-not-a-rollup` | PASS | — |
| `summary-matches-the-picture` | PASS | — |
| `summary-separates-grey-reasons` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## Proposed fixture rows (for the builder to land — not landed by this spec pass)

- a second fixture person exercising the density boundary: 6 rings, one 8-item ring with long
  labels (exercises `capacity-at-limit`, `label-elided-when-tight`, `label-omitted-when-tiny`);
- a sibling trio with `share: 2, 1, 1` (exercises `arc-share-mixed-weights`);
- a single-item ring (exercises `arc-share-single-item-ring`).

## Provenance

Classic sunburst libraries implement **nested** parent→child angular containment (Plotly's
`sunburst`, D3's `partition` layout); ECharts can draw independent concentric rings via multiple
`pie` series with explicit `radius` bands. The 12-o'clock-clockwise convention is the common
pie-chart default in some libraries and not others. All of this is reasoned from training
knowledge — the authoring rides had no web access, so no library behavior here was verified
against a live source. The requirements above are deliberately library-agnostic; only ⚖-R3 in
[layout.md](layout.md) touches implementation.
