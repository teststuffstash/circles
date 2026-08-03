# Color and legibility (CIR-RENDER-COLOR-*, CIR-RENDER-A11Y-*)

The status colors are the product's primary channel — and its biggest honesty risk. This
page pins the palette, the rules that keep ⚪ visible, and the non-color channels that keep
statuses readable for colorblind readers and on grayscale print. Status *semantics* live in
[../data/status-resolution.md](../data/status-resolution.md); this page is about rendering.

## CIR-RENDER-COLOR-PALETTE — the four fills

| status | word | fill | approx. relative luminance |
|---|---|---|---|
| 🟢 ok | `ok` | `#008F68` (bluish green) | ≈ 0.21 |
| 🟡 attention | `attention` | `#F2B300` (amber) | ≈ 0.51 |
| 🔴 act | `act` | `#B22222` (deep red) | ≈ 0.11 |
| ⚪ unmonitored | `unmonitored` | `#9E9E9E` (neutral grey) | ≈ 0.34 |

The hexes are normative; the **constraints below are the requirement** (a palette unit test
computes luminances from the shipped CSS and asserts them — the ≈ values above are the
author's hand computation, the test is the arbiter):

1. **Luminance ladder** — the fills form a strict grayscale ordering, lightest to darkest:
   amber > grey > green > red, with **pairwise relative-luminance difference ≥ 0.10**
   (WCAG relative-luminance definition). Rationale: on a B&W printer the traffic-light
   *hues* collapse to near-identical mid-greys — the classic failure this palette is built
   to survive (see ⚖ COLORBLIND-PALETTE). Severity reads darker-is-urgent on paper.
2. **Label contrast** — text painted on a cell has ≥ 4.5:1 contrast against its fill
   (WCAG AA): black labels on amber, grey, and green; white labels on red.
3. **Bounded fills** — every cell is visually bounded against the page background (the
   uniform inter-cell gaps of CIR-RENDER-GEOM-ARC-SHARE), so the light amber and grey fills
   read as deliberate surfaces, not absence-of-paint.

| row (test id) | inputs | expected |
|---|---|---|
| palette-exact-fills | shipped CSS | the four fills are exactly the pinned hexes |
| palette-luminance-ladder | computed luminances | amber > grey > green > red, every pair ≥ 0.10 apart |
| palette-label-contrast | each status's label color vs its fill | ≥ 4.5:1 for all four |
| palette-cvd-simulation | the palette rendered through deuteranopia/protanopia simulation | the four statuses remain pairwise distinguishable (hue and/or lightness channel) |

**⚖ AMBIGUITY: COLORBLIND-PALETTE** — the goal issue fixes the traffic-light *words* but
not the hues. Options: (a) pure signal hues (`#00C853` / `#FFD600` / `#D50000` class);
(b) a colorblind-aware, luminance-separated palette (bluish green / amber / deep red /
grey); (c) any hues plus patterns or icons as a second channel. **Recommendation: (b)** —
roughly 1 in 12 men carry red-green deficiency, and the trusted-circle audience is exactly
where an unreadable 🔴 does real harm; (b) keeps the traffic-light reading for everyone
else while adding a grayscale ladder that also fixes B&W print. (c) is rejected: hatch
patterns and per-cell icons clutter the at-a-glance read and degrade in print — the
non-color channel requirement (CIR-RENDER-COLOR-NOT-ONLY-CHANNEL) already covers the
residual risk without painting anything on the cells.

**⚖ AMBIGUITY: DARK-MODE** — should the page honor `prefers-color-scheme: dark`? Options:
(a) light theme only; (b) a second dark palette. **Recommendation: (a) for v0** — the A4
print contract fixes a light background anyway, and a second palette doubles the ladder and
contrast matrix (every constraint above re-proved per theme) for a product whose stated
exposure is a glance and a printout. If phone-first evening reading becomes real, dark mode
lands as a new requirement with its own palette rows, not as an untested media query.

## CIR-RENDER-COLOR-GREY-VISIBLE — the honest grey

⚪ is a first-class status, and the unmonitored surface must be **readable at a glance** —
never hidden, never defaulted to green, never visually "off" (no reduced opacity, no dashed
ghost styling that reads as decoration). Concretely: the grey fill is visibly distinct from
the page background *and* from each of the other three fills in both hue and luminance
(the ladder above), and a fully grey ring renders as a solid grey band
(CIR-DATA-STATUS-NO-AGGREGATION).

| row (test id) | inputs | expected |
|---|---|---|
| grey-distinct-from-background | ⚪ cell on the white page | clearly visible fill (bounded by gaps; contrast ≥ 2.4:1 against the background) |
| grey-distinct-from-statuses | a ring containing all four statuses | ⚪ distinguishable from each at a glance, on screen and in grayscale print |
| grey-not-deemphasized | any ⚪ cell | same opacity, stroke, and label treatment as colored cells |
| grey-surface-proportion | the fixture's `exercise` item | the grey arc occupies its full share of the `self` ring — its size is its honesty |

## CIR-RENDER-COLOR-NOT-ONLY-CHANNEL — status is never color alone

Everywhere a status is conveyed, its **word** is available without color perception:

- the legend pairs each fill with its word (CIR-RENDER-COLOR-LEGEND);
- the detail line includes the status word (CIR-RENDER-INTERACT-HOVER);
- each cell's accessible name includes the status word
  (CIR-RENDER-INTERACT-KEYBOARD);
- the text alternative lists every cell with its status word
  (CIR-RENDER-A11Y-TEXT-ALTERNATIVE) — and prints.

| row (test id) | inputs | expected |
|---|---|---|
| status-word-in-detail-line | hover a 🔴 cell | detail line contains the word `act` |
| status-word-in-a11y-name | cell's computed accessible name | contains label + status word |
| no-color-only-cells | whole page audit | no status appears as color without any reachable word form |

## CIR-RENDER-COLOR-LEGEND — the key

The legend maps all four fills to their words — `ok`, `attention`, `act`, `unmonitored`
(glossary words, lowercase) — present **at all times** (not behind a hover) on screen and
on the A4 print. All four entries show even if the current `data.json` happens to use only
two statuses: the legend teaches the language, not the current census.

| row (test id) | inputs | expected |
|---|---|---|
| legend-all-four | `data.json` with only green items | legend still shows all four entries |
| legend-words | legend text | exactly `ok` / `attention` / `act` / `unmonitored` |
| legend-on-print | browser print | legend present on the A4 page |

## CIR-RENDER-A11Y-TEXT-ALTERNATIVE — the page in words

The page includes a complete **text alternative**: a per-ring list of every item with its
label and status word, generated from the same `data.json` (never separately maintained, so
it cannot drift). On screen it lives behind a disclosure control ("view as list") and is
always present in the accessibility tree; **in print it is always rendered** — it is the
paper's substitute for hover (CIR-RENDER-LAYOUT-PRINT-A4) and the grayscale-safety net for
the palette.

| row (test id) | inputs | expected |
|---|---|---|
| text-alternative-complete | fixture `data.json` | every cell appears under its ring with label + status word |
| text-alternative-same-source | any render | alternative built from the same parsed `data.json` as the chart |
| text-alternative-in-print | browser print | the list prints in full |
| text-alternative-screen-reader | accessibility tree | the list is reachable without expanding the disclosure |

## Provenance

- The luminance-ladder approach to B&W print legibility, the 4.5:1 WCAG AA text-contrast
  threshold, red-green deficiency prevalence, and the bluish-green/amber/vermillion
  colorblind-safe hue family (Okabe-Ito tradition) are training knowledge — this ride has no
  WebSearch/WebFetch tool, so none were verified against live sources. The pinned hexes are
  chosen to satisfy the stated constraints under the WCAG relative-luminance formula; the
  palette test recomputes them exactly, and ±small channel adjustments that keep every
  constraint green are palette-tuning, not spec changes.
