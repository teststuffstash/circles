# render — traffic-light colors, ⚪ visibility, accessibility

Every cell is colored by its status light. This page owns the color/legibility contract and
how ⚪ stays honest and visible.

## Requirements

### CIR-RENDER-COLOR-STATUS — status colors
The four statuses map to distinct, stable colors: 🟢 ok, 🟡 attention, 🔴 act, ⚪ unmonitored.
The exact values are theme tokens (see ⚖ COLOR-1), but the four must be mutually
distinguishable and distinguishable from the page background. Phase: P0.

### CIR-RENDER-COLOR-UNMONITORED — ⚪ is visible, not empty
⚪ cells render with a distinct grey fill plus a visible stroke/border and a label, so they read
as "present but unmonitored" — never as blank space or as green. The unmonitored surface must
be readable at a glance. Phase: P0.

| description | inputs | expected |
|---|---|---|
| unmonitored cell visible | item with no adapter | grey fill + stroke + label, distinct from background and from 🟢 |
| unmonitored never green | item with no adapter | not rendered as 🟢 |

### CIR-RENDER-COLOR-ACCESSIBILITY — not color-only
Status must be distinguishable by more than color: each status carries a non-color channel
(icon/glyph and/or text label) in the legend and on hover, so the chart is readable by
color-blind users and in low-contrast/print contexts. Phase: P0.

| description | inputs | expected |
|---|---|---|
| legend has non-color channel | legend rendered | each status shown with icon + label, not color alone |
| hover shows status text | hover an item | status named in text (e.g. "attention"), not color alone |

### CIR-RENDER-COLOR-CONTRAST — legibility floor
Text and status glyphs meet a minimum contrast against their cell fill and the page background
(WCAG AA for text). Phase: P0.

## ⚖ AMBIGUITY entries

### ⚖ COLOR-1 — exact color values
The goal names the four statuses but not their exact colors, and the emoji (🟢🟡🔴⚪) are not a
stable palette.
- Options: (a) fix exact hex tokens in the spec; (b) fix only the distinguishability contract
  and let the theme choose values.
- **Recommendation: (a)** — fix a small token set (e.g. green `#2e7d32`, yellow `#f9a825`, red
  `#c62828`, grey `#9e9e9e`) so tests can assert exact colors and the operator has a concrete
  default. The ⚪ grey must sit clearly between the page background and the other three.

### ⚖ COLOR-2 — how ⚪ stays visible without a legend
The goal says grey must be "honest and visible" but not how a viewer knows grey means
"unmonitored" rather than "empty".
- Options: (a) rely on a legend; (b) put a small glyph (e.g. `—`) in every ⚪ cell; (c) both.
- **Recommendation: (c)** — legend plus an in-cell glyph, so the unmonitored surface is
  self-explanatory even without the legend. Specified as [CIR-RENDER-COLOR-UNMONITORED](#cir-render-color-unmonitored).

### ⚖ COLOR-3 — color-blind-safe palette
The goal's 🟢/🟡/🔴 are a classic red-green confusion pair.
- Options: (a) rely on the non-color channel only (icon/label); (b) also pick a
  color-blind-safe palette (e.g. blue/orange instead of green/red).
- **Recommendation: (a)** — keep the conventional traffic-light colors (they are the product's
  language) and make the non-color channel mandatory. Flagged as a PR Follow-up if the operator
  prefers a palette change.
