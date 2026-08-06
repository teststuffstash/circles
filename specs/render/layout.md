# Layout — one screen, one A4

The product's hard constraint: **the whole picture fits one screen without scrolling, and prints
legibly to a single A4 via the browser** — no separate PDF/SVG pipeline, HTML from day one. This
page turns that into testable requirements: a fixed reference viewport, a defined set of page
furniture, self-containment rules, and what the page does when its baked payload is unusable.

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-RENDER-REFERENCE-VIEWPORT — the tested screen

"One screen" is tested at the **reference viewport: 1280 × 800 CSS pixels** (a small laptop).
The one-screen requirement below is a pass/fail gate at exactly this size with exactly the
fixture config; other sizes are governed by the scaling rules, not by the gate.

| row id | inputs | expected |
|---|---|---|
| viewport-gate-is-fixed | any one-screen assertion | evaluated at 1280 × 800 CSS px |
| viewport-larger-passes-trivially | 1920 × 1080 | composition scales up; the gate does not re-run |

**⚖-R37 — which viewport "one screen" means.** The goal says "one screen" without naming one.
Options: (a) 1280×800 (small laptop); (b) 1920×1080 (desktop); (c) 390×844 (phone). **Ruled:
(a).** The exposure path is desktop-first with phone viewing an explicitly *later* path, and a
gate pinned at the small-laptop end passes everywhere larger. (c) would force design
compromises — tiny chart, aggressive elision — for a path the goal defers. Phone reading still
works through scale-to-fit (⚖-R38); it just is not the legibility gate. The exact number is a
judgment call a human can override at merge time.

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-REFERENCE-VIEWPORT — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `viewport-gate-is-fixed` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-ONE-SCREEN — no scrolling, ever

At the reference viewport, with any config inside the content envelope
([`CIR-RENDER-CAPACITY`](sunburst.md)), the **entire page** — chart plus all chrome — fits
without vertical or horizontal scrolling. The chart scales to fill whatever space the chrome
leaves, so the one-screen invariant holds at every viewport size; legibility is guaranteed only
at and above the reference viewport.

| row id | inputs | expected |
|---|---|---|
| one-screen-reference | fixture config, 1280 × 800 | no scrollbars; chart, ring key, legend, stamp and detail strip fully visible |
| one-screen-with-warnings | artifact with 2 warnings | banner shown; still no scrolling (the chart yields the space) |
| one-screen-larger-viewport | 1920 × 1080 | composition scales up, no scrollbars |
| one-screen-smaller-viewport | 700 × 500 | still no scrollbars — the chart scales down; legibility not guaranteed |

**⚖-R38 — below the reference viewport, scale or scroll?** Options: (a) always scale to fit, no
scrolling at any size; (b) a minimum size, scrolling below it; (c) a responsive breakpoint
redesign. **Ruled: (a).** "The whole picture fits one screen" reads as a product invariant, and
a scaled-down complete picture keeps the at-a-glance value — the traffic lights stay readable
far below reference size, and text is what degrades first, which the detail line covers. (c) is
the multi-page-app smell the goal warns against. This is also the honest answer to the
phone-vs-desktop tension the goal leaves open: the phone gets a complete, smaller picture rather
than a different one.

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-ONE-SCREEN — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `one-screen-proxy` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-A4 — one sheet from the browser's print dialog

The page prints via the browser's **default print flow** — no custom print button, no settings
changes — to one A4 portrait sheet, at `@page { margin: 10mm }`. Cell fills must survive
printing; browsers suppress backgrounds by default.

| row id | inputs | expected |
|---|---|---|
| print-single-a4-portrait | fixture config, print to A4 portrait | exactly 1 page; nothing clipped |
| print-picture-fills-the-sheet | A4 portrait | sunburst scaled to the printable width, not left at screen size |
| print-margins-are-declared | printed page | 10 mm page margin, not the browser default |
| print-colors-preserved | printed output | cell fills present, not knocked out to white; grey cells visibly grey ([`CIR-RENDER-PRINT-COLOR`](colors.md)) |
| print-chrome-complete | printed output | ring key, legend, generated-at stamp and text alternative all present |
| print-interactive-affordances-hidden | printed page | no hover chrome, no focus outlines, no buttons |
| print-detail-reaches-paper | printed page | the text alternative is printed — hover text cannot be, and a printout of unlabelled colours is not legible |
| print-no-injected-link-footnotes | printed page | no `(https://…)` appended after labels; the browser's own setting governs |
| print-no-header-footer-assumption | printed page | the layout does not depend on the browser's header/footer being off |
| print-warnings-shown | artifact with warnings | warnings banner printed |
| print-greyscale-legible | printed on a B&W printer | the four statuses stay pairwise distinguishable ([`CIR-RENDER-PALETTE`](colors.md)) **and** the text alternative carries the status words |

**⚖-R39 — portrait or landscape, and what fixes the A4 page box?** A screen is ~16:10 and A4
portrait is ~1:1.41, so a circle sized for one leaves voids in the other. Options: (a) portrait,
fixed; (b) landscape, fixed; (c) auto-select by aspect. **Ruled: (a) with a declared 10 mm
margin.** Portrait is what a person gets when they hit print without thinking, and surprising
them with a rotated sheet is worse than a little unused paper. The 10 mm margin is ruled rather
than left to the browser because browser defaults vary and the single-sheet gate has to be
reproducible. (c) makes the printed artifact depend on the window shape at print time, which is
untestable in the way that matters.

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-A4 — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `print-interactive-affordances-hidden` | PASS | — |
| `print-margins-are-declared` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-RENDERER — what draws the rings

The page's geometry is **independent concentric bands**
([`CIR-RENDER-RING-PARTITION`](sunburst.md)), not a hierarchy. This constrains the renderer
directly, and the constraint is a requirement rather than an implementation note because every
other render requirement — print path, focus order, ARIA, asset budget, no-JS — sits on top of
it.

| row id | inputs | expected |
|---|---|---|
| renderer-draws-independent-rings | 3-item inner ring, 2-item outer ring | both rings span 360° on their own scale, with no parent-child binding |
| renderer-adds-no-runtime-egress | built page | no library fetched at run time ([`CIR-RENDER-NO-EGRESS`](#cir-render-no-egress)) |
| renderer-within-asset-budget | built page | the drawing code is part of the budget below, not an exemption from it |

**⚖-R3 — is Plotly usable at all?** The goal issue names Plotly first ("a sunburst library
(e.g. Plotly) is acceptable; D3/ECharts are alternatives if layout fights back"). Two arms of
the fan-out independently concluded **no**: Plotly's sunburst is hierarchical — sectors are
bound to a parent's arc — and circles' rings are independent, so the model cannot be expressed
without fighting the library into a shape it does not have. Both recommended hand-rolled SVG.
Options: (a) hand-rolled SVG; (b) Plotly as the goal suggests; (c) D3 or ECharts.
**Ruled: (a), as an explicit override of the goal issue.** This is the one place in the tree
that contradicts issue #1 outright, so it is flagged for the human gate rather than quietly
encoded. The supporting argument is independent of the library question: a hand-rolled SVG of
concentric bands is a few hundred lines, keeps the asset budget and no-egress rules trivially
satisfiable, and gives direct control over the print path, focus order and ARIA — all of which a
charting library would fight. Note the library claims are training-knowledge, unverified in any
authoring ride (see Provenance); if Plotly *can* express independent rings, this ruling should
be revisited rather than defended.

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-RENDERER — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `renderer-adds-no-runtime-egress` | PASS | — |
| `renderer-draws-independent-rings` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-CHROME — the page furniture

Everything on the page besides the chart, in this reading order:

| element | content | conditional |
|---|---|---|
| title | the person's display name (also the document `<title>`) | always |
| centre disc | the person's name and the summary counts ([`CIR-RENDER-SUMMARY`](sunburst.md)) | always |
| ring key | ring labels listed inside-out — the triage reading order | always |
| legend | the four status colours with their words ([colors.md](colors.md)) | always |
| generated-at stamp | the artifact's `generated_at` value | always |
| stale banner | the stale-bake warning | only when `stale_after_hours` is set and exceeded |
| warnings banner | `N warnings — <first cause>`; expands to the full list | only when `warnings[]` is non-empty |
| detail strip | one line: the hovered/focused/tapped cell's detail line | idle text when nothing is selected |

| row id | inputs | expected |
|---|---|---|
| chrome-ring-key-order | fixture rings | key lists ① Self, ② Partner, ③ Children, ④ Wider life top to bottom |
| chrome-banner-hidden-when-clean | `warnings: []` | no banner and no empty placeholder; the chart uses the space |
| chrome-banner-content | 3 warnings | count plus the first cause; the full list reachable without leaving the page |
| chrome-idle-detail-strip | nothing hovered | a neutral idle line, never a stale cell's content |

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-CHROME — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `chrome-banner-hidden-when-clean` | PASS | — |
| `chrome-idle-detail-strip` | PASS | — |
| `chrome-ring-key-order` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-GENERATED-AT — the honesty stamp on screen

The stamp is displayed **verbatim** — the baked UTC string, no local-time conversion, no "3 days
ago" rewording — in a fixed chrome position, visible without interaction, on screen and in
print.

| row id | inputs | expected |
|---|---|---|
| stamp-verbatim | `generated_at: "2026-08-03T02:00:00Z"` | the page shows that exact string |
| stamp-no-localization | viewer in a UTC+14 zone | still the baked UTC string, unconverted |
| stamp-on-print | browser print | present on the A4 page |

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-GENERATED-AT — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `stamp-on-screen` | PASS | — |
| `stamp-verbatim` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-BOOT-FAILURE — failure is visible, never blank

The page carries its data inline ([`CIR-BAKE-SELF-CONTAINED`](../data/data-json.md)), so boot
failure is not a network condition — it is an **unusable embedded payload**: absent, malformed,
missing required keys, or an unrecognized `version`. Any of these produces a visible boot-failure
state naming the failure class in plain language. Never a blank page, never a half-rendered
chart, and never a page of default-coloured cells.

| row id | inputs | expected |
|---|---|---|
| boot-failure-payload-absent | the inlined payload block is missing | boot-failure state, no chart |
| boot-failure-malformed-json | truncated payload | boot-failure state, no chart |
| boot-failure-version-mismatch | `version: 2`, page understands 1 | boot-failure state naming the version problem, never a best-effort render |
| boot-failure-shape-mismatch | `rings` key absent | boot-failure state |
| boot-failure-empty-rings | `rings: []` (hand-edited; the bake would never emit it) | boot-failure state |
| boot-failure-is-not-green | any boot failure | no cell is drawn in any status colour |

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-BOOT-FAILURE — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `boot-failure-empty-rings` | PASS | — |
| `boot-failure-payload-absent` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-NO-EGRESS — the page talks to nobody

This is a privacy requirement before it is an operational one: the page is a person's health and
family status, and every external request tells a third party who is looking at it and when. It
is also the cheapest way to keep the served artifact honest — nothing can render differently
tomorrow because a CDN changed.

| row id | inputs | expected |
|---|---|---|
| no-external-requests-at-runtime | page loaded with all non-document requests blocked | renders identically |
| no-third-party-origins-in-markup | built page | zero references to any host other than the page's own origin — no CDN, font, analytics or tile |
| fonts-are-system-or-inlined | built page | no webfont fetch |
| page-works-from-file-url | saved copy opened locally | full render |
| page-works-with-no-js | JS disabled | the text alternative renders with all statuses ([`CIR-RENDER-A11Y-TABLE`](colors.md)) |

<details class="evidence-block">
<summary>Evidence: 4 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-NO-EGRESS — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `fonts-are-system-or-inlined` | PASS | — |
| `no-external-requests-at-runtime` | PASS | — |
| `no-third-party-origins-in-markup` | PASS | — |
| `page-works-from-file-url` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-RENDER-ASSET-BUDGET — small enough to be one file

A stated budget — **250 KB total, uncompressed** — is what makes no-egress and single-file
self-containment survive contact with the first "let's just add a chart library" change. It is
the enforcement mechanism behind ⚖-R3.

| row id | inputs | expected |
|---|---|---|
| budget-built-page-is-small | fixture person | the single `index.html`, data inlined, within budget |
| budget-enforced-by-the-gate | a build exceeding it | CI failure, not a silent regression ([`CIR-PROC-TEST-TIERS`](../process/testing.md)) |
| budget-growth-is-linear | 9 → 18 items | growth is linear in items, not in libraries |

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-RENDER-ASSET-BUDGET — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `budget-built-page-is-small` | PASS | — |
| `budget-growth-is-linear` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## Provenance

Print-CSS behavior (`print-color-adjust`, `@page` margin support), browser default margins, and
chart-library payload sizes are reasoned from training knowledge — the authoring rides had no
web access, so none of it was verified against a live source. The ⚖-R3 ruling rests on a claim
about Plotly's sunburst model that two independent arms reached but neither verified; treat
convergence as evidence, not proof.
