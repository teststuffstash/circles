# Layout — one screen, one A4 (CIR-RENDER-LAYOUT-*)

The product's hard constraint: **the whole picture fits one screen without scrolling, and
prints legibly to a single A4 via the browser** — no separate PDF/SVG pipeline, HTML from
day one. This page turns that constraint into testable requirements: a fixed reference
viewport, a defined set of page furniture (the chrome), asset self-containment rules, and
the boot-error behavior when baked data can't be read.

## CIR-RENDER-LAYOUT-REFERENCE-VIEWPORT — the tested screen

"One screen" is tested at the **reference viewport: 1280 × 800 CSS pixels** (a small
laptop). The one-screen requirement (below) is a pass/fail gate at exactly this size with
exactly the fixture config; other sizes are governed by the scaling rules, not the gate.

**⚖ AMBIGUITY: REFERENCE-VIEWPORT** — the goal issue says "one screen" without naming one.
Options: (a) 1280×800 (small laptop); (b) 1920×1080 (desktop); (c) 390×844 (phone).
**Recommendation: (a)** — the issue's exposure path is desktop-first with phone viewing a
*later* path, and a gate pinned at the small-laptop end passes everywhere larger; (c) would
force design compromises (tiny chart, aggressive elision) for an exposure path the issue
explicitly defers. Phone reading still works through scale-to-fit (⚖ SMALL-VIEWPORT) — it
just isn't the legibility gate. The exact number is a judgment call a human can override at
merge time.

## CIR-RENDER-LAYOUT-ONE-SCREEN — no scrolling, ever

At the reference viewport, with any config inside the content envelope
(CIR-RENDER-GEOM-DENSITY), the **entire page** — chart plus all chrome
(CIR-RENDER-LAYOUT-CHROME) — fits without vertical or horizontal scrolling. The chart scales
to fill the space the chrome leaves over; the whole composition always fits (the chart
shrinks), so the one-screen invariant holds at **every** viewport size, with legibility
guaranteed only at and above the reference viewport.

| row (test id) | inputs | expected |
|---|---|---|
| one-screen-reference | fixture config, 1280×800 | no scrollbars; chart, ring key, legend, stamp, detail strip fully visible |
| one-screen-with-warnings | `data.json` with 2 warnings | banner shown; still no scrolling (chart yields the space) |
| one-screen-larger-viewport | 1920×1080 | composition scales up, no scrollbars |
| one-screen-smaller-viewport | 700×500 | still no scrollbars — chart scales down; legibility not guaranteed |

**⚖ AMBIGUITY: SMALL-VIEWPORT** — below the reference viewport, should the page keep scaling
(chart shrinks, labels elide, eventually illegible-but-complete) or enforce a minimum size
and allow scrolling? Options: (a) always scale-to-fit, no scrolling at any size; (b) minimum
size, scroll below it; (c) responsive breakpoint redesign. **Recommendation: (a)** — "the
whole picture fits one screen" reads as a product invariant, and a scaled-down complete
picture preserves the at-a-glance value (the traffic lights stay readable far below
reference size; text is what degrades first, and the detail line covers it). (c) is the
multi-page-app smell the issue warns against.

## CIR-RENDER-LAYOUT-PRINT-A4 — the paper contract

The page prints via the browser's **default print flow** (no custom print button required,
no user settings changes) to **one A4 portrait page** at default margins: chart, ring key,
legend, generated-at stamp, and the text alternative
(CIR-RENDER-A11Y-TEXT-ALTERNATIVE) — the words-on-paper fallback, since hover doesn't
exist in print. Cell colors must survive printing (`print-color-adjust: exact` or
equivalent — browsers suppress backgrounds by default). Interactive-only elements (the
detail strip's live area, focus outlines) print as their static equivalents or are omitted
deliberately.

| row (test id) | inputs | expected |
|---|---|---|
| print-single-a4-portrait | fixture config, browser print to A4 portrait, default margins | exactly 1 page; nothing clipped |
| print-colors-preserved | printed output | cell fills present (not knocked out to white); grey cells visibly grey |
| print-chrome-complete | printed output | ring key, legend, generated-at stamp, text alternative all on the page |
| print-grayscale-legible | A4 printed on a B&W printer (or print preview in grayscale) | the four statuses remain pairwise distinguishable (palette luminance ladder, CIR-RENDER-COLOR-PALETTE) **and** the text alternative carries the status words |
| print-warnings-shown | `data.json` with warnings | warnings banner printed |

## CIR-RENDER-LAYOUT-CHROME — the page furniture

Everything on the page besides the chart, always present (some elements conditional as
noted), in this reading order:

| element | content | conditional |
|---|---|---|
| title | the person's display name (also the document `<title>`) | always |
| center disc | the person's name, inside ring 1 (CIR-RENDER-GEOM-RING-THICKNESS) | always |
| ring key | ring labels listed inside-out — the triage reading order | always |
| legend | the four status colors with their words ([colors.md](colors.md)) | always |
| generated-at stamp | the `data.json` `generated_at` value | always |
| warnings banner | `N warnings — <first cause>`; expands to the full list | only when `warnings[]` is non-empty |
| detail strip | one line: the hovered/focused/tapped cell's detail line | idle text when nothing is selected |

| row (test id) | inputs | expected |
|---|---|---|
| chrome-ring-key-order | fixture rings | key lists ① Self, ② Partner, ③ Children, ④ Wider life top-to-bottom |
| chrome-banner-hidden-when-clean | `warnings: []` | no banner, no empty placeholder; chart uses the space |
| chrome-banner-content | 3 warnings | banner shows the count and the first cause; full list reachable without leaving the page |
| chrome-idle-detail-strip | nothing hovered | strip shows a neutral idle line (e.g. "hover a cell"), never a stale cell's content |

## CIR-RENDER-LAYOUT-GENERATED-AT-VISIBLE — the honesty stamp on screen

The `generated_at` stamp is displayed **verbatim** (the baked UTC string, no local-time
conversion, no "3 days ago" rewording — CIR-DATA-DATAJSON-GENERATED-AT) in a fixed chrome
position, visible without interaction, on screen and in print. It is the only signal that
separates a current page from a dead pipeline (statuses freeze at bake time,
CIR-DATA-STATUS-RESOLUTION-TIME).

| row (test id) | inputs | expected |
|---|---|---|
| stamp-verbatim | `generated_at: "2026-08-03T02:00:00Z"` | page shows that exact string |
| stamp-no-localization | viewer in a UTC+14 zone | stamp still shows the baked UTC string, unconverted |
| stamp-on-print | browser print | stamp present on the A4 page |

## CIR-RENDER-LAYOUT-BOOT-ERROR — failure is visible, never blank

The page fetches `data.json` at load and **renders nothing from unverifiable data**. Any of
— fetch failure, HTTP error, malformed JSON, missing required keys, unrecognized `version`
(CIR-DATA-DATAJSON-VERSION) — produces a **visible boot-error state**: a plain-language
message naming the failure class (e.g. "status data could not be loaded" / "status data has
an unrecognized format"), never a blank page, never a half-rendered chart.

| row (test id) | inputs | expected |
|---|---|---|
| boot-error-missing-data | `data.json` 404 | boot-error state, no chart |
| boot-error-malformed-json | truncated JSON | boot-error state, no chart |
| boot-error-version-mismatch | `version: 2` page doesn't know | boot-error state naming the version problem (never best-effort render) |
| boot-error-shape-mismatch | `rings` key absent | boot-error state |
| boot-error-empty-rings | `rings: []` (hand-edited; the bake would never emit it) | boot-error state |

## CIR-RENDER-LAYOUT-ASSETS — self-containment

The page is served as static files from the existing nginx image + Helm chart and must make
**zero network requests beyond its own origin**: no CDN, no web fonts, no analytics, no
third-party anything (it is a person's life status — it phones nowhere). JavaScript and CSS
are either inlined or shipped as same-origin sibling assets; fonts come from the system
stack. The total asset payload stays small enough for the phone-read path (a slow
connection must not gate a glance).

**⚖ AMBIGUITY: RENDER-TECH** — how the sunburst is drawn. The goal issue allows "a sunburst
library (e.g. Plotly)" with D3/ECharts as alternatives "if layout fights back". Options:
(a) hand-rolled SVG arcs (no dependency, or a vendored micro-helper); (b) vendored Plotly
sunburst; (c) vendored D3 (the `arc`/`pie` pieces) driving hand-authored SVG; (d) vendored
ECharts with stacked `pie` series (its SVG renderer). **Recommendation: (a), growing to (c)
the moment interactivity fights back** — the independent ring partition
(CIR-RENDER-GEOM-RING-PARTITION) is a *poor* fit for classic sunburst widgets, which nest
children inside parent arcs (Plotly's sunburst and D3's partition both assume containment —
using them means dummy parents and fighting the layout, the failure mode the issue
anticipates). Independent concentric rings are a few arc paths per cell: simple SVG, DOM-
focusable for keyboard support (CIR-RENDER-INTERACT-KEYBOARD), natively accessible, and
tiny — which also keeps "one static HTML asset + one data.json" literally true. ECharts (d)
is the honest fallback if hand-rolled interactions sprawl, at the cost of a ~1 MB asset.
Plotly (b) is the worst fit: it fights the geometry doctrine *and* weighs ~1 MB. Recorded
as ⚖ because the issue names Plotly first; the geometry finding above is why this spec
recommends against it. See Provenance.

| row (test id) | inputs | expected |
|---|---|---|
| assets-no-external-requests | page load with a request log | every request same-origin; zero third-party requests |
| assets-total-budget | all page assets except `data.json` | ≤ 300 KB uncompressed total (hand-rolled SVG target; revisit only via ⚖ RENDER-TECH override) |
| assets-offline-capable | origin serving only the static files | full render with no other network dependency |

## CIR-RENDER-LAYOUT-DATA-FETCH — cache discipline

`data.json` is fetched from a fixed same-origin relative path (`data.json` beside
`index.html`) with **revalidation requested** (`Cache-Control: no-cache` on the fetch or
equivalent): a nightly bake that publishes a new file must be visible on next load, and an
aggressively cached old file must not silently defeat the honesty stamp.

| row (test id) | inputs | expected |
|---|---|---|
| data-fetch-path | page served at any path | `data.json` resolved relative to the page, same origin |
| data-fetch-revalidates | server holding a newer `data.json` | next load renders the newer file's stamp |

## CIR-RENDER-LAYOUT-NO-JS — the no-script floor

**⚖ AMBIGUITY: NO-JS-FALLBACK** — what a browser without JavaScript sees. Options: (a) a
`<noscript>` notice only; (b) the bake stamps a static HTML fallback (the text alternative
table) into the page; (c) nothing. **Recommendation: (a) for P0/P1** — the pipeline is
defined as client-side rendering over baked data, and (b) adds a second render path the
bake must keep in lockstep with the page (exactly the overreach P0 forbids); assistive
technology runs *with* JavaScript, so the text alternative
(CIR-RENDER-A11Y-TEXT-ALTERNATIVE) already covers the accessibility case. If the phone-first
exposure path later demands no-JS resilience, (b) becomes a new requirement.

| row (test id) | inputs | expected |
|---|---|---|
| no-js-notice | JavaScript disabled | a readable notice states the page needs JavaScript; no blank page |

## Provenance

- `print-color-adjust` behavior (browsers dropping backgrounds in print by default) and the
  `Cache-Control: no-cache` fetch semantics are reasoned from training knowledge — this ride
  has no WebSearch/WebFetch tool, so they were not verified against live docs. Both are
  load-bearing for PRINT-A4 and DATA-FETCH; the builder should verify against MDN when
  implementing.
- Library size/weight claims in ⚖ RENDER-TECH (~1 MB class for Plotly/ECharts, tiny for
  hand-rolled SVG) are order-of-magnitude training knowledge, unverified in this ride; the
  geometry-fit argument (nested vs independent rings) does not depend on them.
- The 300 KB asset budget is this spec's chosen round number, not an external standard.
