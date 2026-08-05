# Colour and legibility

The status colours are the product's primary channel — and its biggest honesty risk. This page
pins the palette, the rules that keep ⚪ visible, and the non-colour channels that keep statuses
readable for colourblind readers and on greyscale print. Status *semantics* live in
[../data/status-resolution.md](../data/status-resolution.md); this page is about rendering.

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-RENDER-PALETTE — the four fills

| status | word | fill | approx. relative luminance |
|---|---|---|---|
| 🟢 ok | `ok` | `#00916A` (bluish green) | ≈ 0.21 |
| 🟡 attention | `attention` | `#F2B300` (amber) | ≈ 0.51 |
| 🔴 act | `act` | `#B22222` (deep red) | ≈ 0.11 |
| ⚪ unmonitored | `unmonitored` | `#9E9E9E` (neutral grey) | ≈ 0.34 |

The hexes are normative, but the **constraints below are the requirement** — a palette unit test
computes luminances from the shipped CSS and asserts them. The ≈ values above are the author's
hand computation; the test is the arbiter. That arbitration has already fired once: the
originally pinned green `#008F68` fails the ladder (green↔red gap 0.0992, below the 0.10 floor —
found and independently recomputed during the P0 build); `#00916A` passes at 0.1057 with every
other constraint intact.

1. **Luminance ladder** — the fills form a strict greyscale ordering, lightest to darkest:
   amber > grey > green > red, with **pairwise relative-luminance difference ≥ 0.10** (WCAG
   relative-luminance definition). On a B&W printer the traffic-light *hues* collapse to
   near-identical mid-greys; this is the arithmetic that survives it, and severity reads
   darker-is-urgent on paper.
2. **Label contrast** — text painted on a cell has ≥ 4.5:1 contrast against its fill (WCAG AA):
   black labels on amber, grey and green; white labels on red.
3. **Bounded fills** — every cell is visually bounded against the page background (the uniform
   inter-cell gaps of [`CIR-RENDER-ARC-SHARE`](sunburst.md)), so the light amber and grey fills
   read as deliberate surfaces rather than absence of paint.

| row id | inputs | expected |
|---|---|---|
| palette-exact-fills | shipped CSS | the four fills are exactly the pinned hexes |
| palette-luminance-ladder | computed luminances | amber > grey > green > red, every pair ≥ 0.10 apart |
| palette-label-contrast | each status's label colour vs its fill | ≥ 4.5:1 for all four |
| palette-cvd-simulation | the palette through deuteranopia and protanopia simulation | the four statuses remain pairwise distinguishable by hue and/or lightness |

**⚖-R40 — which hues.** The goal fixes the traffic-light *words* but not the hues. Options:
(a) pure signal hues (`#00C853` / `#FFD600` / `#D50000` class); (b) a colourblind-aware,
luminance-separated palette; (c) any hues plus patterns or icons as a second channel.
**Ruled: (b).** Roughly 1 in 12 men carry a red-green deficiency, and the trusted-circle audience
is exactly where an unreadable 🔴 does real harm; (b) keeps the traffic-light reading for
everyone else while adding a greyscale ladder that also fixes B&W print. (c) is rejected: hatch
patterns and per-cell icons clutter the at-a-glance read and degrade in print, and
`CIR-RENDER-STATUS-ENCODING` already covers the residual risk without painting anything on the
cells. Note what is *not* open here: the four statuses stay green/yellow/red/grey — one arm
proposed a blue/orange alternative, which reopens a decision the goal fixed.

**⚖-R41 — dark mode.** Options: (a) light theme only; (b) a second dark palette. **Ruled: (a)
for v0.** The A4 print contract fixes a light background anyway, and a second palette doubles
the ladder and contrast matrix — every constraint above re-proved per theme — for a product
whose stated exposure is a glance and a printout. If phone-first evening reading becomes real,
dark mode lands as a new requirement with its own palette rows, not as an untested media query.

_Evidence: none yet — unverified._

## CIR-RENDER-GREY-VISIBLE — the honest grey

⚪ is a first-class status. The unmonitored surface must be **readable at a glance** — never
hidden, never defaulted to green, never visually "off": no reduced opacity, no dashed ghost
styling that reads as decoration. A fully grey ring renders as a solid grey band.

| row id | inputs | expected |
|---|---|---|
| grey-distinct-from-background | ⚪ cell on the white page | clearly visible fill, contrast ≥ 2.4:1 against the background |
| grey-distinct-from-statuses | a ring containing all four statuses | ⚪ distinguishable from each at a glance, on screen and in greyscale print |
| grey-not-deemphasized | any ⚪ cell | same opacity, stroke and label treatment as coloured cells |
| grey-surface-proportion | the fixture's `self/exercise` item | the grey arc occupies its full share of the ring — its size is its honesty |
| grey-reason-distinguishable | one `by-choice` cell and one tooling-caused (`by-failure` / `not-evaluated`) cell | chosen silence and tooling-caused grey are distinguishable without hovering ([`CIR-DATA-GREY-REASON`](../data/status-resolution.md)) |

_Evidence: none yet — unverified._

## CIR-RENDER-STATUS-ENCODING — status is never colour alone

Everywhere a status is conveyed, its **word** is available without colour perception: the legend
pairs each fill with its word, the detail line includes it, each cell's accessible name includes
it, and the text alternative lists every cell with it — and prints.

| row id | inputs | expected |
|---|---|---|
| status-word-in-detail-line | hover a 🔴 cell | the detail line contains the word `act` |
| status-word-in-a11y-name | a cell's computed accessible name | contains label + status word |
| no-color-only-cells | whole-page audit | no status appears as colour without a reachable word form |
| legible-with-fills-stripped | render forced to `print-color-adjust: economy` | statuses still readable from outlines and the text alternative |

_Evidence: none yet — unverified._

## CIR-RENDER-LEGEND — the key

The legend maps all four fills to their words — `ok`, `attention`, `act`, `unmonitored`,
lowercase — present **at all times** (never behind a hover) on screen and on the A4 print. All
four entries show even when the current artifact uses only two statuses: the legend teaches the
language, not the current census.

| row id | inputs | expected |
|---|---|---|
| legend-all-four | artifact with only green items | the legend still shows all four entries |
| legend-words | legend text | exactly `ok` / `attention` / `act` / `unmonitored` |
| legend-on-print | browser print | present on the A4 page |

_Evidence: none yet — unverified._

## CIR-RENDER-PRINT-COLOR — backgrounds must be forced on

Browsers default to `print-color-adjust: economy`: background colours and images are omitted
unless the user ticks "background graphics" in the print dialog. For this page that default
prints **four blank rings**. The print stylesheet therefore sets `print-color-adjust: exact`
(with the `-webkit-` prefix for older WebKit) on the sunburst — and the page stays legible even
if that is ignored.

| row id | inputs | expected |
|---|---|---|
| print-fills-without-user-settings | default print dialog | all fills present |
| print-legible-with-fills-stripped | forced `economy` render | statuses still readable from outlines and the text alternative |
| print-stylesheet-is-inline | built page | inline, no separate stylesheet fetch ([`CIR-RENDER-NO-EGRESS`](layout.md)) |

_Evidence: none yet — unverified._

## CIR-RENDER-STALE-MARK — showing that the lights are history

| row id | inputs | expected |
|---|---|---|
| stale-marks-whole-picture | `generated_at` past `stale_after_hours` | banner plus a page-wide stale treatment ([`CIR-BAKE-STALE-SELF`](../data/data-json.md)) |
| stale-is-not-a-fifth-colour | stale page | statuses keep their colours; staleness is a separate visual channel (desaturation plus a hatched overlay) |
| stale-stated-in-words | stale page | "built <n> hours ago" in text, printed and read aloud |
| fresh-page-has-no-stale-chrome | fresh bake | no banner, no overlay |
| no-threshold-no-stale-chrome | `stale_after_hours: null` (P0) | no banner, no overlay, stamp still shown |

**⚖-R42 — how loud is the stale treatment?** Options: (a) banner plus desaturation and hatch;
(b) banner only, colours untouched; (c) the picture is replaced by the text alternative with the
banner above it. **Ruled: (a)**, with (c) reserved for an extreme threshold if one is ever
declared. (b) risks being ignored, which defeats the point — a stale page that still looks
healthy is the product's own dangerous-green.

_Evidence: none yet — unverified._

## CIR-RENDER-A11Y-TABLE — the accessible equivalent

One table, generated from the same artifact, listing every item with ring, label, status word,
guardrail, data date and any warning. It is the screen-reader path, the no-JS path, the print
detail, and the fallback whenever the picture cannot carry a label — one artifact serving four
jobs, which is why it is a requirement rather than a nicety. On screen it sits behind a
disclosure control and is always present in the accessibility tree; in print it is always
rendered.

| row id | inputs | expected |
|---|---|---|
| a11y-table-complete | fixture artifact | every cell appears under its ring, ring-ordered inside-out |
| a11y-table-states-status-in-words | any item | "attention", never a colour swatch alone |
| a11y-table-same-source | any render | built from the same parsed artifact as the chart, so it cannot drift |
| a11y-table-without-js | JS disabled | the table renders |
| a11y-table-in-print | browser print | present on the single A4 sheet ([`CIR-RENDER-A4`](layout.md)) |
| a11y-table-reachable-by-screen-reader | accessibility tree | reachable without expanding the disclosure |
| sunburst-not-read-arc-by-arc | any page | the picture is labelled as an image with a text summary; the table is the readable path |

_Evidence: none yet — unverified._

## Provenance

The luminance-ladder approach to B&W print legibility, the 4.5:1 WCAG AA text-contrast
threshold, red-green deficiency prevalence, the bluish-green/amber/vermillion colourblind-safe
hue family (Okabe-Ito tradition), and `print-color-adjust` browser defaults are training
knowledge — the authoring rides had no web access, so none were verified against live sources.
The pinned hexes are chosen to satisfy the stated constraints under the WCAG relative-luminance
formula; the palette test recomputes them exactly, and small channel adjustments that keep every
constraint green are palette tuning, not spec changes.
