# Layout — one screen / A4

**CIR-RENDER-ONE-SCREEN** — The entire circles page MUST fit within a single screen viewport without scrolling.

## Core constraint

The hard constraint from the goal issue: "The whole picture fits one screen without scrolling, and prints legibly to a single A4 via the browser."

### Screen layout decision table

| description | inputs | expected |
|---|---|---|
| desktop viewport (1920×1080) | full page render | No vertical or horizontal scroll needed |
| laptop viewport (1366×768) | full page render | No scroll needed; content scales down |
| mobile viewport (375×667) | full page render | No scroll; rings scale to fit (phone-first is later; basic read-only ok) |
| 4+ rings on small screen | 4 rings, 768px height | Sunburst scales proportionally; labels may truncate |
| many items in outer ring | 20+ items in widest ring | Arcs visible; labels may be hidden below minimum size |

## A4 print

**CIR-RENDER-A4-PRINT** — The page MUST print legibly to a single A4 page via the browser's native print (Ctrl+P / Cmd+P). No separate PDF or SVG pipeline.

### Print decision table

| description | inputs | expected |
|---|---|---|
| A4 portrait (210×297mm) | browser print, A4 portrait | Sunburst fits, colors print, page 1 of 1 |
| A4 landscape | browser print, A4 landscape | Sunburst fits (more horizontal space) |
| print without background colors | browser "save ink" mode | Status colors MUST be distinguishable (use stroke/pattern fallback — see colors.md) |

⚖ **AMBIGUITY: A4 orientation.** Options: (a) portrait (standard A4 default); (b) landscape (more horizontal space for sunburst); (c) best-fit auto. **Recommendation:** Portrait with @media print CSS that allows landscape fallback. Rationale: portrait is the default; a sunburst (square aspect ratio) fits better in landscape, but forcing landscape is surprising. Use `@media print and (orientation: landscape)` if the viewport is wider than tall.

⚖ **AMBIGUITY: Margin specification.** How much margin does the A4 print have? Options: (a) browser default margins (~12mm); (b) custom CSS `@page { margin: 10mm }`; (c) no margin override. **Recommendation:** Custom 10mm margins via `@page` CSS. Rationale: browser defaults vary; consistent margins ensure the sunburst fits predictably. 10mm is enough for legibility while maximizing print area.

## Scaling approach

**CIR-RENDER-SCALING** — The sunburst is sized relative to the viewport, not at a fixed pixel size.

- The sunburst container uses `width: min(100vw, 100vh)` and is centered.
- SVG viewBox is set to a square coordinate system (e.g. 800×800) and scales with `preserveAspectRatio="xMidYMid meet"`.
- Labels use relative font sizes (em/rem) that scale with the container.

### Scaling decision table

| description | inputs | expected |
|---|---|---|
| wide viewport | 1920×1080 | Sunburst limited by viewport height (square) |
| tall viewport | 1080×1920 | Sunburst limited by viewport width (square) |
| very small viewport | 320×480 | Sunburst renders at minimum legible size; labels may be hidden |

## Page structure

The page layout (outside the sunburst) contains:
1. **Title area** — person's name from `circles.yaml` `person:` field.
2. **Sunburst chart** — the core visualization, centered.
3. **Generated-at stamp** — from `data.json` "when was this baked" timestamp.
4. **Legend** — traffic light key (🟢 ok · 🟡 attention · 🔴 act · ⚪ unmonitored).

No additional chrome, navigation, or footer. The sunburst IS the page.

## Proposed fixture rows

The layout spec requires no additional fixture data — it operates on the existing Alex fixture's rendered output. Test fixtures for layout are viewport dimensions (synthetic test inputs, not committed data).
