# Sunburst geometry

The page is one sunburst: concentric rings of coloured arcs. This page fixes what the geometry
must satisfy — including the contradiction between "sunburst" as the named form and the
independent-rings model the product actually describes.

## CIR-RENDER-RINGS-INDEPENDENT — rings are independent, not a hierarchy <a id="cir-render-rings-independent"></a>

A classic sunburst is a hierarchy: each ring subdivides its parent's arc, so an outer segment is
angularly contained by its parent. **circles is not that.** *Self*, *Partner*, *Children* and
*Wider life* are independent life areas ordered by dependency, not a parent-child tree —
`children/nova` is not "part of" any item in the *self* ring. Each ring therefore spans the full
360° on its own angular scale.

| description | inputs | expected |
|---|---|---|
| every ring spans the full circle | ring with 1 item | one 360° arc |
| rings have independent angular scales | inner ring 3 items, outer ring 2 items | 120°/120°/120° and 180°/180°; no alignment between rings |
| an outer arc need not nest in an inner arc | any config | no containment constraint is drawn or implied |
| ring boundaries are visible | adjacent rings, both 🟢 | a gap or stroke separates the bands so they do not read as one blob |
| item boundaries within a ring are visible | two adjacent 🟢 items | separated by a gap or stroke |

This is a **direct constraint on the library choice**. Plotly's sunburst is hierarchical: sectors
are defined by `labels`/`parents` (or a `path`), and every ring's sector widths are bound to
their parent's arc — there is no supported way to draw independent concentric rings, only a
synthetic-root workaround. ECharts renders this natively as one pie series per ring with
non-overlapping `radius: [inner, outer]` bands; `d3.arc()` renders it directly with no hierarchy
assumption at all.

⚖ **CIR-Q-19 — which renderer?** Options: (a) hand-rolled inline SVG with arc-path maths
(~a page of code: polar-to-cartesian plus `A` path commands), no dependency, full control of
print, focus order and the accessible equivalent; (b) ECharts multi-series pie; (c) Plotly with
a synthetic parent per ring. *Recommendation: (a).* The page is a static, baked, non-zooming
picture of at most a few dozen arcs, so the library buys tooltips and animation the product does
not want, while costing ~1 MB of inlined JS (the page must be self-contained and make no network
requests — [CIR-RENDER-NO-EGRESS](layout.md)), a print path nobody controls, and canvas output
that cannot carry per-arc focus and ARIA. (c) is rejected outright: a synthetic hierarchy makes
the geometry lie about the data model. Provenance: Plotly sunburst docs (labels/parents/path),
ECharts doughnut/`radius` docs, D3 `d3.arc`.

## CIR-RENDER-RING-ORDER — inside-out is dependency order <a id="cir-render-ring-order"></a>

| description | inputs | expected |
|---|---|---|
| file order is inside-out | rings `self, partner, children, wider` | `self` innermost, `wider` outermost |
| ring index is derived, not authored | any config | the renderer numbers rings 1..n outward; labels do not carry numerals |
| the ordinal is shown next to the ring label | ring 0 labelled "Self" | rendered as "① Self" (or an equivalent ordinal) without the config saying so |
| reordering the file reorders the page | swap two rings | rings swap bands; ids, links and tests are unaffected |

The fixture person currently writes the numerals into its labels (`① Self`); with derived
numbering that would double them. Recorded as a follow-up for the builder — this pass may not
edit `fixtures/`.

## CIR-RENDER-INNER-LEGIBILITY — the most important ring is the smallest <a id="cir-render-inner-legibility"></a>

Inside-out ordering puts the ring that matters most at the smallest radius, where arc length is
shortest and labels fit worst. Equal radial thickness makes the doctrine ("triage reads
inward-first") fight the picture ("the inner ring is a thin sliver").

| description | inputs | expected |
|---|---|---|
| inner rings are not thinner than outer rings | 4 rings | radial thickness is non-increasing outward |
| the innermost ring is legible at capacity | 4 rings × 3 items each, one-screen size | every innermost label is readable at the minimum font ([CIR-RENDER-LABEL-BUDGET](#cir-render-label-budget)) |
| the centre hole is not zero | any config | a hole remains; the innermost ring is a band, not a pie (a filled centre has no room for a label and reads as a fifth status) |
| ring labels are anchored consistently | any config | every ring's label sits in the same angular position |

⚖ **CIR-Q-20 — how is inner-ring legibility bought?** Options: (a) equal thickness, small inner
labels with the detail on interaction; (b) non-increasing thickness outward — inner bands
proportionally thicker so arc *area* is closer to equal (encoded); (c) a leader-line/outside
label for the innermost ring only; (d) a fixed minimum thickness in absolute units, with the
outer rings absorbing what is left. *Recommendation: (b) with a floor from (d).* Under (a) the
picture contradicts the triage doctrine; (c) adds a label-placement engine.

## CIR-RENDER-MIN-ARC — no unreadable slivers <a id="cir-render-min-arc"></a>

| description | inputs | expected |
|---|---|---|
| a tiny share still gets a minimum angle | shares 100 and 1 in one ring | the small item is drawn at the minimum arc angle; the others absorb the difference |
| the minimum is exceeded by the ring | 30 items in one ring, minimum angle 12° | render warning; the page still draws ([CIR-RENDER-OVERFLOW](#cir-render-overflow)) |
| minimum-angle adjustment is visible in the detail | adjusted item | detail line states the declared share; the geometry does not silently misreport weights |

A sliver that cannot be seen, hovered or tapped is an item the person thinks is monitored and
never looks at — a dangerous-green by geometry rather than by data.

## CIR-RENDER-LABEL-BUDGET — labels fit or truncate loudly <a id="cir-render-label-budget"></a>

| description | inputs | expected |
|---|---|---|
| a label that fits is drawn in full | short label, wide arc | full text inside the arc |
| a label that does not fit is truncated | long label, narrow arc | truncated with an ellipsis; full text in the detail line and the accessible equivalent |
| a label is never drawn below the minimum font | any arc | minimum font size is a hard floor; shrink-to-fit stops there and truncation takes over |
| labels never overlap | adjacent narrow arcs | no overlapping glyphs at one-screen or A4 size |
| an arc too narrow for any label carries an ordinal | sliver item | a number keyed to the accessible table, never an unlabelled colour |

## CIR-RENDER-CAPACITY — how much the page holds <a id="cir-render-capacity"></a>

The one-screen/A4 constraint ([CIR-RENDER-ONE-SCREEN](layout.md)) is a hard cap on how much
config a page can honestly draw. Capacity is expressed as the point where labels stop fitting,
not as an arbitrary count.

| description | inputs | expected |
|---|---|---|
| the reference capacity renders cleanly | 4 rings × up to 8 items, at the reference viewport and A4 | every label legible, nothing truncated below the floor |
| the minimum page renders | 1 ring, 1 item | a single full-circle band; no empty picture |
| an empty ring renders as an empty band | ring with zero items | the band is drawn in the unmonitored treatment with the ring label and a warning; it is never omitted (a missing band reads as "no such area", not "nothing configured") |
| a config with zero rings is a config error | `rings: []` | config error ([CIR-DATA-SCHEMA-STRICT](../data/circles-yaml.md)) |
| past capacity, the page warns | 7 rings × 12 items | render warning naming the ring, page still drawn |

## CIR-RENDER-OVERFLOW — what happens past capacity <a id="cir-render-overflow"></a>

| description | inputs | expected |
|---|---|---|
| no item is ever dropped | any oversized config | every item is drawn; overflow degrades labels, never coverage |
| overflow is announced | oversized config | a page warning; the count is visible ([CIR-BAKE-WARNINGS](../data/data-json.md)) |
| overflow never scrolls the page | oversized config | [CIR-RENDER-ONE-SCREEN](layout.md) still holds; the picture shrinks, the page does not grow |

⚖ **CIR-Q-21 — should past-capacity be a build failure instead of a warning?** Options:
(a) warn and draw (encoded); (b) fail the bake so a person cannot publish an illegible page;
(c) warn, draw, and additionally render the accessible table as the primary view past a
threshold. *Recommendation: (a)* — the person's config is their life, and refusing to draw it
because it is complicated is worse than drawing it densely with a warning. (c) is a strong
second and can be added without any config change.

## CIR-RENDER-SUMMARY — the count that survives everything <a id="cir-render-summary"></a>

The page carries a one-line summary of its own statuses (greens, yellows, reds, unmonitored by
choice, unmonitored by failure) taken verbatim from `data.json`.

| description | inputs | expected |
|---|---|---|
| the summary matches the picture | 9 items | counts equal the drawn arcs |
| unmonitored reasons are counted separately | 1 by-choice, 1 by-failure | "1 unmonitored · 1 adapter failing", never "2 unmonitored" ([CIR-DATA-GREY-REASON](../data/status-resolution.md)) |
| the summary survives print and greyscale | printed page | present in the printed output |
| the summary is not a ring rollup | any config | no ring or page is assigned a colour |

⚖ **CIR-Q-22 — should rings roll up to a status, and what lives in the centre hole?** The
"innermost must hold" doctrine invites an aggregate light per ring, and the hole invites an
overall one. Options: (a) no rollup; the hole carries the person's name, the generated-at stamp
and the summary (encoded); (b) worst-item rollup per ring, shown on the ring label; (c) an
overall light in the centre. *Recommendation: (a).* A rollup is a fabricated status with no
adapter behind it, and "worst wins" makes one deliberately-red item paint a whole life area red
forever, training the person to ignore it. The hole is where the stale-bake banner and summary
belong, because that is where the eye starts.
