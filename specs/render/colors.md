# Colors and legibility

**CIR-RENDER-COLORS** — Status colors for the sunburst chart and their legibility requirements.

## Traffic light palette

| status | color name | hex | background usage | text/icon |
|---|---|---|---|---|
| 🟢 ok | green | `#22c55e` | arc fill | white text |
| 🟡 attention | amber | `#eab308` | arc fill | dark text |
| 🔴 act | red | `#ef4444` | arc fill | white text |
| ⚪ unmonitored | grey | `#9ca3af` | arc fill | dark text |

**CIR-RENDER-COLORS-UNMONITORED** — ⚪ unmonitored grey MUST be visually distinct from the chart background. Grey is honest and visible — the unmonitored surface must be readable at a glance, never hidden or defaulted to green.

### Color decision table

| description | inputs | expected |
|---|---|---|
| ⚪ on white background | unmonitored arc, white page bg | Grey arc clearly visible |
| ⚪ on light grey background | unmonitored arc, grey page bg | Grey arc uses border/stroke for contrast |
| 🟢 next to ⚪ | ok arc adjacent to unmonitored arc | Visually distinguishable at a glance |
| 🔴 next to 🟡 | act arc adjacent to attention arc | Red and amber clearly distinct |

## Contrast and accessibility

**CIR-RENDER-COLORS-CONTRAST** — All status colors MUST meet WCAG 2.1 AA contrast ratio (4.5:1) against the page background for text, and 3:1 for non-text UI components (arcs).

### Contrast decision table

| description | inputs | expected |
|---|---|---|
| green text on white | `#22c55e` text, white bg | ⚠ fails 4.5:1 (green is light) — use white text ON green arc |
| red text on white | `#ef4444` text, white bg | ✅ passes |
| grey arc on white bg | `#9ca3af` fill, white bg | ✅ passes 3:1 for non-text |
| amber arc on white bg | `#eab308` fill, white bg | ✅ passes 3:1 |

⚖ **AMBIGUITY: Green contrast.** The chosen green `#22c55e` has a contrast ratio of ~2.6:1 against white, failing WCAG AA for text. Options: (a) use white text on green arc badge (badge background, not text color); (b) darken green to `#16a34a` or `#15803d` for text; (c) use green arcs with no text on them (label via tooltip). **Recommendation:** (a) + (c) — arcs are colored fills with white text overlaid (text sits inside the arc), and arc labels outside use the neutral dark color. This is the standard approach for sunburst charts.

**CIR-RENDER-COLORS-PRINT** — Status colors MUST print distinguishably in greyscale (for "save ink" mode or B&W printers).

### Print/greyscale decision table

| description | inputs | expected |
|---|---|---|
| all colors in greyscale | B&W printer | Each status uses a distinct grey value + a pattern/texture as secondary encoding |
| "save ink" mode | browser background color disabled | ⚪ uses stroke/border to remain visible against white |

⚖ **AMBIGUITY: Greyscale fallback.** Options: (a) rely on distinct grey values alone (green→light grey, amber→medium grey, red→dark grey, grey→medium-light grey — susceptible to confusion between amber and unmonitored); (b) add a secondary encoding (hatching patterns, borders, or labels on every arc). **Recommendation:** (b) — add a distinct border/stroke width to each status arc: ok=thin, attention=medium, act=thick. Combined with grey fills, this provides a reliable second encoding that survives B&W printing and color-blindness. Provenance: WCAG guidelines recommend redundant encoding for color-dependent information.

## Color blindness

**CIR-RENDER-COLORS-CVD** — The traffic light metaphor relies on red/green/yellow distinction. For people with color vision deficiency:
- The legend includes text labels alongside color icons.
- Hover tooltips include the text status ("ok", "attention", "act", "unmonitored").
- The print/greyscale secondary encoding (stroke width) also serves CVD.

### Color blindness decision table

| description | inputs | expected |
|---|---|---|
| protanopia (red-blind) | 🔴 and 🟢 look similar | Distinguishable via stroke width + label text on hover |
| deuteranopia (green-blind) | 🟢 and 🟡 look similar | Distinguishable via stroke width + label text |
| greyscale (achromatopsia) | all colors grey | Stroke width encoding + labels |

⚖ **AMBIGUITY: CVD-friendly color palette.** Options: (a) standard traffic light colors with CVD accommodations as specified above; (b) use a CVD-safe palette like blue/orange/grey instead of green/yellow/red. **Recommendation:** (a). Rationale: the goal issue explicitly names "traffic lights" 🟢🟡🔴; changing the palette would break the core metaphor. The stroke-width + text redundancies are sufficient accommodations.

## Ring labels

**CIR-RENDER-LABELS** — Ring labels (e.g. "① Self") are rendered inside or beside their ring band:
- Inner rings (small circumference): labels outside the ring, or in the center.
- Outer rings (large circumference): labels inside the ring band.
- Labels use the ring's configured `label:` string.

### Label decision table

| description | inputs | expected |
|---|---|---|
| label on innermost ring | 1 item, small ring | Label at center or in cap |
| label on outer ring | 4th ring, wide | Label inside the arc band |
| long label on narrow ring | label "Quarterly labs" on small arc | Label truncated or hidden below min arc size |

⚖ **AMBIGUITY: Label truncation.** When an arc is too narrow for its label text, options: (a) truncate with ellipsis; (b) hide label, show on hover only; (c) rotate label to fit along the arc. **Recommendation:** (b) — hide label for arcs below a minimum angular threshold, show on hover. Rationale: rotated text in SVG is hard to read; truncated text is confusing. Hover provides the information accessibly.