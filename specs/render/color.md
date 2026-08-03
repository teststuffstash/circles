# Colour, legibility and the accessible equivalent

The whole product is a colour encoding, so every place colour can fail — colour-vision
deficiency, greyscale printing, a browser that strips backgrounds, a screen reader — is a place
the product fails silently. This page makes colour redundant everywhere.

## CIR-RENDER-STATUS-ENCODING — colour is never the only channel <a id="cir-render-status-encoding"></a>

Each status is carried by **colour plus a second, non-colour channel** (a glyph or fill pattern)
and by text in the accessible equivalent.

| description | inputs | expected |
|---|---|---|
| each status has a distinct glyph | 🟢🟡🔴⚪ items | four distinguishable glyphs/patterns, present in the arc or its label |
| greyscale keeps the statuses apart | page rendered in greyscale | the four statuses remain distinguishable |
| red and green are distinguishable under deuteranopia/protanopia | simulated CVD render | ok and act remain distinguishable without colour alone |
| a legend is always present | any page | legend maps colour+glyph → word, on screen and in print |
| status words match the glossary | any page | "ok", "attention", "act", "unmonitored" — no synonyms |
| colour is not used for anything else | any page | no decorative colour that could be mistaken for a status |

Red/green is the most common colour-vision deficiency and it is exactly the distinction this page
exists to make; a page that encodes "act" only as a hue is unreadable to a substantial share of
the people the person might show it to.

## CIR-RENDER-GREY-VISIBLE — honest grey, and its two reasons <a id="cir-render-grey-visible"></a>

⚪ must read as *a deliberate state*, never as background, empty space, or a rendering gap.

| description | inputs | expected |
|---|---|---|
| grey is distinguishable from the page background | ⚪ item on the page | outlined and filled distinctly from the background; not white-on-white |
| grey is distinguishable from a gap | ⚪ item adjacent to a ring boundary | the arc is clearly an arc |
| grey survives print | printed page | visible fill/pattern, not blank paper |
| by-choice and by-failure differ visually | one of each on the page | distinguishable without interaction ([CIR-DATA-GREY-REASON](../data/status-resolution.md)) — e.g. plain grey vs grey with a warning mark |
| grey is never quietly upgraded | any config | no default-to-green path exists anywhere in the render |
| an all-grey page is still a page | config with no adapters | full picture, all grey, summary reads all unmonitored |

## CIR-RENDER-CONTRAST — text on arcs <a id="cir-render-contrast"></a>

| description | inputs | expected |
|---|---|---|
| label text meets contrast on every status fill | labels on all four fills | ≥ 4.5:1 for normal text, ≥ 3:1 for large text |
| the palette itself is fixed in one place | built page | one declared palette; no per-item colour in `circles.yaml` |
| a person cannot recolour statuses | config attempting a colour key | config error ([CIR-DATA-SCHEMA-STRICT](../data/circles-yaml.md)) — recolouring the traffic lights breaks the shared vocabulary |
| adjacent statuses are distinguishable | 🟡 next to 🟢 | boundary visible at A4 size |

⚖ **CIR-Q-25 — which palette, and which second channel?** Encoded: one fixed palette, contrast
floors as above, and a non-colour channel per status. Unruled: the exact hues, and whether the
second channel is a glyph in the arc (readable, costs arc space), a fill pattern (survives
photocopying, can look noisy), or a shape on the ring's outer edge. *Recommendation: a
CVD-safe four-colour palette plus a small glyph in the arc, falling back to the label's ordinal
when the arc is too narrow ([CIR-RENDER-LABEL-BUDGET](sunburst.md)).*

## CIR-RENDER-PRINT-COLOR — backgrounds must be forced on <a id="cir-render-print-color"></a>

Browsers default to `print-color-adjust: economy`: background colours and images are omitted
unless the user ticks "background graphics" in the print dialog. For this page that default
prints **four blank rings**. The print stylesheet therefore sets `print-color-adjust: exact`
(with the `-webkit-` prefix for older WebKit) on the sunburst.

| description | inputs | expected |
|---|---|---|
| status fills print without the user changing settings | default print dialog | all fills present |
| the printed page is legible with fills stripped anyway | forced `economy` render | statuses still readable from glyphs, outlines and the accessible table ([CIR-RENDER-STATUS-ENCODING](#cir-render-status-encoding)) |
| the print stylesheet is part of the single file | built page | inline, no separate stylesheet fetch ([CIR-RENDER-NO-EGRESS](layout.md)) |

The second row is the belt-and-braces rule: `print-color-adjust: exact` overrides the user's
setting in modern browsers, but a page whose entire meaning vanishes when one CSS property is
unsupported is not a page you can hand to a doctor. Provenance: MDN `print-color-adjust`
(`economy` default; backgrounds printed only if the user allows, or if `exact` is set).

## CIR-RENDER-STALE-MARK — showing that the lights are history <a id="cir-render-stale-mark"></a>

| description | inputs | expected |
|---|---|---|
| a stale bake marks the whole picture | `generated_at` past `stale_after_hours` | banner in the centre plus a page-wide stale treatment ([CIR-BAKE-STALE-SELF](../data/data-json.md)) |
| the stale treatment is not a fifth colour | stale page | statuses keep their colours; staleness is a separate visual channel (e.g. desaturation plus a hatched overlay) |
| staleness is stated in words too | stale page | "built <n> hours ago" in text, printed and read aloud |
| a fresh page carries no stale chrome | fresh bake | no banner, no overlay |

⚖ **CIR-Q-26 — how loud is the stale treatment?** Options: (a) banner + desaturation + hatch
(encoded); (b) banner only, colours untouched; (c) the picture is replaced by the accessible
table with the banner above it. (b) risks being ignored; (c) is the most honest and the most
disruptive. *Recommendation: (a)*, with (c) reserved for an extreme threshold (e.g. a week of
failed bakes) if one is ever ruled.

## CIR-RENDER-A11Y-TABLE — the accessible equivalent <a id="cir-render-a11y-table"></a>

One table, generated from the same `data.json`, listing every item with ring, label, status word,
guardrail, data date and any warning. It is the screen-reader path, the no-JS path, the print
detail, and the fallback whenever the picture cannot carry a label.

| description | inputs | expected |
|---|---|---|
| every item appears in the table | 9 items | 9 rows, ring-ordered inside-out |
| the table states status in words | any item | "attention", not a colour swatch alone |
| the table is present without JS | JS disabled | table renders ([CIR-RENDER-NO-JS](interaction.md)) |
| the table is printed | printed page | present on the single A4 sheet ([CIR-RENDER-A4](layout.md)) |
| the sunburst is not read arc-by-arc by a screen reader | any page | the picture is labelled as an image with a text summary; the table is the readable path |
| the table carries the warnings | 2 warnings | both, keyed to their items |
| the table is not a duplicate source of truth | any page | rendered from the same `data.json` fields as the arcs; no second resolution ([CIR-BAKE-PAGE-DOES-NOT-RESOLVE](../data/data-json.md)) |

The accessible equivalent is not an accessibility afterthought here — it is simultaneously the
cheapest way to satisfy print detail, no-JS rendering, sliver labelling and screen readers, which
is why one artifact serves all four.
