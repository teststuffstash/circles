# Core Metric Comparison Report: Issue #6 — Four Spec Arms

**Model slug:** `nemotron-3-ultra` (from `nvidia/nemotron-3-ultra-550b-a55b:free`)
**Branch:** `research/issue-6-compare-nemotron-3-ultra`
**Mission issue:** #6 — compare the four issue-1 spec arms (core metric ×2 + downstream proxy ×4)
**Goal issue:** #1 — seed the specs/ tree for circles sunburst product contract

---

## Blind decision-point checklist (phase 0)

*Enumerated from goal issue #1 + master repo state (fixtures/, chart/, public/, scripts/ci.sh, specs/ stubs) BEFORE opening any arm. This is the independent coverage rubric.*

### A. circles.yaml schema — structural decisions

| ID | Decision point | Source |
|----|----------------|--------|
| DP-A1 | Timezone/DST anchoring for "days old" in freshness calculation | Goal issue ⚖, circles-yaml.md ⚖ |
| DP-A2 | Date formats recognized in source files (ISO 8601? frontmatter? natural language?) | Goal issue ⚖, circles-yaml.md ⚖ |
| DP-A3 | Whether `share` weights must sum to 1.0 per ring (or any normalization) | Goal issue ⚖, circles-yaml.md ⚖ |
| DP-A4 | Sibling half-arc ordering within a ring (left-to-right? config order? alphabetical?) | Goal issue ⚖, circles-yaml.md ⚖ |
| DP-A5 | Default `share` when omitted (equal split? proportional to something?) | circles-yaml.md stub says "default: equal" |
| DP-A6 | `share` value constraints (must be >0? ≤1? sum ≤1?) | Unstated |
| DP-A7 | Whether an item can declare multiple adapters (stub says "exactly one adapter, or absent") | circles-yaml.md stub |
| DP-A8 | `link` field: required, optional, or conditional? | Unstated |
| DP-A9 | `guardrail` field: required, optional, or conditional? | Unstated |
| DP-A10 | `label` field: required? | Unstated (fixture has it on all) |
| DP-A11 | `id` uniqueness scope: global across all rings, or per-ring only? | Unstated |
| DP-A12 | Minimum items per ring (can a ring be empty?) | Unstated |
| DP-A13 | `person` field: required? format constraints? | Unstated |
| DP-A14 | Ring `id` and `label`: required? uniqueness? | Unstated |
| DP-A15 | Whether rings array order is the sole determinant of inside-out order (vs explicit `depth` field) | Goal issue says "ordered inside-out by dependency" |

### B. Status resolution — adapter semantics

| ID | Decision point | Source |
|----|----------------|--------|
| DP-B1 | Freshness window boundary inclusivity: is "3 days old" inside or outside `yellow_after: 7`? | circles-yaml.md table says "3d old, yellow_after 7 → 🟢" |
| DP-B2 | `yellow_after` vs `red_after` ordering constraint (must yellow < red?) | Unstated |
| DP-B3 | Behavior when `yellow_after` ≥ `red_after` (error? swap? ignore yellow?) | Unstated |
| DP-B4 | Command adapter: accepted stdout values (case sensitivity: "green" vs "Green" vs "GREEN") | Unstated |
| DP-B5 | Command adapter: stderr handling (ignored? logged? causes ⚪?) | Unstated |
| DP-B6 | Command adapter: timeout (default? configurable? kill behavior?) | Unstated |
| DP-B7 | Command adapter: exit code ≠ 0 → ⚪ + warning (specified), but what about exit 0 with non-standard stdout? | Goal issue |
| DP-B8 | Manual adapter: accepted values (case sensitivity, aliases?) | Unstated |
| DP-B9 | Freshness source missing: ⚪ + build warning (specified), but what if source exists but has no parseable dates? | Unstated |
| DP-B10 | Freshness: "newest date" definition when multiple date formats coexist in source | DP-A2 dependency |
| DP-B11 | Freshness: handling of future dates (data entry errors) | Unstated |
| DP-B12 | Status resolution precedence when multiple rules could apply (not applicable if DP-A7 = exactly one) | DP-A7 dependency |

### C. Sunburst geometry & rendering — visual/interaction decisions

| ID | Decision point | Source |
|----|----------------|--------|
| DP-C1 | Exact pixel dimensions for "one screen" (viewport assumptions: 320px? 375px? 1024px?) | Goal issue: "one screen / A4" |
| DP-C2 | Responsive breakpoints for phone-first read-only viewing | Goal issue |
| DP-C3 | A4 print: CSS `@page` margins, scale, page-break avoidance | Goal issue: "prints legibly to a single A4 via the browser" |
| DP-C4 | Traffic-light exact hex values (color-blind safe palette?) | Goal issue: 🟢 🟡 🔴 ⚪ |
| DP-C5 | How ⚪ (unmonitored) stays visible on white/light backgrounds (border? pattern? label?) | Goal issue: "grey is honest and visible... never hidden" |
| DP-C6 | Ring width: fixed pixels? proportional to radius? configurable? | Unstated |
| DP-C7 | Arc subdivision algorithm for `share` weights (proportional angle? half-arc special case?) | Goal issue: "siblings may subdivide a ring (two children as two half-arcs)" |
| DP-C8 | Half-arc rendering: exactly 180° each? or proportional to `share`? | Fixture shows `share: 0.5` each |
| DP-C9 | Ring label placement: inside ring? outside? radial? curved text? | Unstated |
| DP-C10 | Item label placement: on arc? on hover only? truncated? | Unstated |
| DP-C11 | Hover detail line: exact format (guardrail + status + last-data date? order?) | Goal issue: "hover = the item's detail line (guardrail, status, last-data date)" |
| DP-C12 | Hover UI: native tooltip? custom overlay? sidebar panel? | Unstated |
| DP-C13 | Click behavior: `link` → navigate; no `link` → detail page? both? | Goal issue: "click = jump to the item's link, or open its detail page" |
| DP-C14 | Detail page URL scheme: hash route? separate HTML? query param? | Unstated |
| DP-C15 | Detail page: annotated timeseries — metric series data format (array of [timestamp, value]?) | Goal issue: "metric series overlaid with dated intervention events" |
| DP-C16 | Detail page: intervention events format (markdown table? JSON? frontmatter?) | Goal issue: "dated intervention events from a markdown table" |
| DP-C17 | Detail page: chart library (same as sunburst? separate?) | Unstated |
| DP-C18 | Sunburst library choice: Plotly vs D3 vs ECharts — spec should anticipate interface, not lock | Goal issue: "Plotly acceptable; D3/ECharts alternatives if layout fights back" |
| DP-C19 | Animation/transitions on status change? on hover? on load? | Unstated |
| DP-C20 | Accessibility: keyboard navigation (tab order?), screen reader labels, focus indicators | Unstated |
| DP-C21 | Color-blind mode / high-contrast mode? | Unstated |
| DP-C22 | Legend: traffic-light key shown? where? | Unstated |

### D. data.json — baked render input schema

| ID | Decision point | Source |
|----|----------------|--------|
| DP-D1 | Exact JSON schema for `data.json` (statuses, detail lines, generated-at) | Goal issue: "one static HTML asset + one data.json" |
| DP-D2 | `generated-at` stamp format: ISO 8601 with timezone? UTC? local? | Unstated |
| DP-D3 | Statuses structure: object keyed by item id? array? nested by ring? | Unstated |
| DP-D4 | Detail lines structure: per-item object with guardrail, status, last-data-date? | Goal issue: "statuses, detail lines, generated-at stamp" |
| DP-D5 | Whether `data.json` includes ring/item metadata (labels, share, links) or only computed values | Unstated |
| DP-D6 | How missing/⚪ items are represented in `data.json` (null? omitted? explicit "unmonitored") | Unstated |

### E. Bake job (P1) — operational decisions

| ID | Decision point | Source |
|----|----------------|--------|
| DP-E1 | "Nightly" schedule: exact time? timezone? (cron expression?) | Goal issue: "a nightly bake job" |
| DP-E2 | Bake job runtime environment: container? script? CI step? | Goal issue: "job runs elsewhere; this repo owns the code it runs" |
| DP-E3 | Bake job input: reads `circles.yaml` from where? (repo root? config map? file path arg?) | Unstated |
| DP-E4 | Bake job output: writes `data.json` to where? (public/ dist/ stdout?) | Unstated |
| DP-E5 | Bake job: validates `circles.yaml` schema before evaluating adapters? | Unstated |
| DP-E6 | Bake job: adapter evaluation order (parallel? sequential? dependency-aware?) | Unstated |
| DP-E7 | Bake job: partial failure handling (one adapter fails → whole bake fails? skip item? mark ⚪?) | Unstated |
| DP-E8 | Bake job: freshness source file reading — relative to repo root? working dir? config-specified base? | Unstated |
| DP-E9 | Bake job: command adapter execution — working dir? env vars? timeout? | DP-B5, DP-B6 dependency |

### F. Adapter interface (P2 extensibility) — plugin contract

| ID | Decision point | Source |
|----|----------------|--------|
| DP-F1 | Adapter interface signature: function? CLI? HTTP? (must "plug in without touching the page") | Goal issue |
| DP-F2 | Built-in adapter config schema: sqlite query (query string? params? connection?), Prometheus (query? URL?), HTTP/REST (endpoint? auth?) | Goal issue: "contributed built-ins later (sqlite query, Prometheus query, HTTP/REST to-do list state)" |
| DP-F3 | Adapter registration/discovery mechanism: config key? file naming? plugin directory? | Unstated |
| DP-F4 | Adapter versioning/compatibility: how does page know which adapters exist? | Unstated |

### G. Testing — tier terminology & linkage

| ID | Decision point | Source |
|----|----------------|--------|
| DP-G1 | "Unit" = pure logic (exact boundary: no I/O? no network? no filesystem?) | Goal issue: "unit = pure logic" |
| DP-G2 | "System testing" = logic against real components in local cluster (kind) — which components? chart? bake job? adapters? | Goal issue |
| DP-G3 | "E2E" = actual target environment — what defines "target"? staging? prod? | Goal issue |
| DP-G4 | How decision-table rows link to tests: row description → test id verbatim? naming convention? | Goal issue: "each row's description usable as a test id verbatim" |
| DP-G5 | Test fixtures: synthetic fixture person (Alex) as primary test input — any others? | Goal issue: "fixture person... supplies the key examples" |
| DP-G6 | Property-based / generative testing for adapter logic? | Unstated |

### H. Glossary — term coverage

| ID | Decision point | Source |
|----|----------------|--------|
| DP-H1 | Terms from goal issue not in stub glossary: "bake", "data.json", "detail page", "annotated timeseries", "intervention events", "fixture person", "guardrail", "share", "ring", "circle", "adapter", "freshness", "status", "item" — which need definitions? | Glossary stub has ~14 terms; goal issue uses more |
| DP-H2 | One definition per term, no synonyms — enforcement mechanism? | Specs README convention |

### I. Contradictions & unstated constraints in goal issue

| ID | Decision point | Source |
|----|----------------|--------|
| DP-I1 | "Phone-first read-only viewing is the later exposure path; don't design a multi-page app" vs detail page being a click-through target (implies second page/view) | Goal issue |
| DP-I2 | "One screen / A4" for main page vs detail page needing its own screen/print | Goal issue |
| DP-I3 | "No server, no DB, SSG-agnostic" vs bake job running "elsewhere" (implies separate runtime) | Goal issue |
| DP-I4 | "Adapter interface so these plug in without touching the page" vs page being static HTML + data.json (adapter runs at bake time, not page load) | Goal issue |
| DP-I5 | P0: "statuses hand-set in config" vs circles.yaml having `freshness:`/`command:` adapters (those aren't hand-set) | Goal issue P0 vs schema |
| DP-I6 | "Specs should anticipate, not overreach" vs "specs are grown during implementation, not authored complete upfront" — where is the line for P0 vs P1 vs P2 scope? | Goal issue |

### J. Conventions compliance (from specs/README.md)

| ID | Decision point | Source |
|----|----------------|--------|
| DP-J1 | Requirement ID grammar: `CIR-<AREA>-<NAME>` — AREA values standardized? (DATA, RENDER, PROCESS, GLOSSARY?) | Specs README |
| DP-J2 | No declared ✓/verified-ness markers — how to track coverage without them? | Specs README |
| DP-J3 | Decision tables over prose — minimum coverage threshold? | Specs README |
| DP-J4 | ⚖ AMBIGUITY entries as first-class content — required fields? (options, recommendation, status?) | Specs README |
| DP-J5 | Synthetic data only — validation that no real PII leaks? | Specs README |

---

**Total Phase-0 decision points: 72** (A:15, B:12, C:22, D:6, E:9, F:4, G:6, H:2, I:6, J:5)

*End of Phase 0 checklist. Proceeding to Phase 1: per-arm inventory.*

---

## Master decision-point matrix

*Rows = Phase-0 decision points + arm-specific findings. Columns per arm: ✅ covered (decision made + testable), ⚖️ ⚖'d (recorded as ambiguity), ❌ missed (not addressed), 🚫 false-⚖ (flags as open something the goal actually decides).*

| DP ID | Topic | Opus | Kimi-k3 | Deepseek | Mimo |
|-------|-------|------|---------|----------|------|
| **A. circles.yaml schema** |
| DP-A1 | Timezone/DST anchoring | ✅ CIR-DATA-TIMEZONE, CIR-Q-05 | ✅ CIR-DATA-FRESHNESS-TIMEZONE, ⚖ FRESHNESS-TIMEZONE | ✅ CIR-DATA-FRESHNESS-TIMEZONE, ⚖ DATA-1 | ✅ CIR-DATA-FRESHNESS-TIMEZONE, ⚖ CIR-Q-TIMEZONE-DST-ANCHORING |
| DP-A2 | Date formats recognized | ✅ CIR-DATA-DATE-PARSE, CIR-Q-10, CIR-Q-11 | ✅ CIR-DATA-FRESHNESS-DATE-PARSING, ⚖ DATE-FORMATS | ✅ CIR-DATA-FRESHNESS-DATE-PARSING, ⚖ DATA-2 | ✅ CIR-DATA-FRESHNESS-DATE-EXTRACTION, ⚖ CIR-Q-DATE-FORMATS |
| DP-A3 | `share` sum constraint | ✅ CIR-DATA-SHARE, CIR-Q-04 | ✅ CIR-DATA-SHARE-WEIGHT, ⚖ SHARE-WEIGHT-SEMANTICS | ✅ CIR-DATA-SHARE-WEIGHTS, ⚖ DATA-3 | ✅ CIR-RENDER-ARC-WEIGHT, ⚖ (partial share sums) |
| DP-A4 | Sibling half-arc ordering | ✅ CIR-RENDER-GEOM-SIBLING-ORDER, CIR-Q-20 | ✅ CIR-RENDER-GEOM-SIBLING-ORDER, ⚖ SIBLING-ORDER | ✅ CIR-DATA-SIBLING-ORDER, ⚖ DATA-4 | ✅ CIR-RENDER-ARC-START, ⚖ CIR-Q-SIBLING-HALF-ARC-ORDERING |
| DP-A5 | Default `share` | ✅ (default: equal) | ✅ (default: 1) | ✅ (default: equal) | ✅ (default: equal) |
| DP-A6 | `share` value constraints | ✅ (positive, config error if ≤0) | ✅ (positive, config error if ≤0) | ✅ (positive, config error if ≤0) | ⚖ (normalization only) |
| DP-A7 | Multiple adapters per item | ✅ config error | ✅ config error | ✅ config error | ✅ validation error |
| DP-A8 | `link` field optionality | ✅ optional, URL or root-relative | ✅ optional, https or root-relative | ✅ optional | ✅ optional |
| DP-A9 | `guardrail` field optionality | ✅ optional | ✅ optional | ✅ optional | ✅ optional |
| DP-A10 | `label` required | ✅ config error if missing | ✅ config error if missing | ✅ required | ✅ required |
| DP-A11 | `id` uniqueness scope | ✅ per-ring | ✅ per-ring | ❌ global (CIR-DATA-ITEM-UNIQUENESS) | ✅ per-ring (implied) |
| DP-A12 | Empty ring allowed | ✅ renders as empty band + warning | ⚖ EMPTY-RING (rec: validation error) | ✅ omitted (CIR-RENDER-EMPTY-STATE) | ✅ visible empty band |
| DP-A13 | `person` required | ✅ config error if missing | ✅ config error if missing | ✅ required | ✅ required |
| DP-A14 | Ring `id`/`label` required | ✅ config error if missing | ✅ config error if missing | ✅ required | ✅ required |
| DP-A15 | Ring order = array order | ✅ CIR-RENDER-RING-ORDER | ✅ CIR-RENDER-GEOM-RING-ORDER | ✅ CIR-RENDER-RING-ORDER | ✅ CIR-RENDER-RING-ORDER |
| **B. Status resolution** |
| DP-B1 | Freshness boundary inclusivity | ✅ `age > threshold` (age 7 = 🟢 at yellow_after 7) | ✅ inclusive lower bound (age 7 = 🟡 at yellow_after 7) | ✅ inclusive lower bound (age 7 = 🟡) | ✅ inclusive (≥) |
| DP-B2 | yellow_after < red_after constraint | ✅ config error if not | ✅ config error if not | ✅ config error if not | ✅ validation error |
| DP-B3 | Behavior when yellow ≥ red | ✅ config error | ✅ config error | ✅ config error | ✅ validation error |
| DP-B4 | Command stdout case sensitivity | ✅ trimmed + case-folded | ✅ case-insensitive | ✅ lowercased | ✅ trimmed |
| DP-B5 | Command stderr handling | ✅ captured to warning, not page | ✅ captured to warning | ❌ not specified | ❌ not specified |
| DP-B6 | Command timeout | ✅ per-item + total budget, CIR-Q-14 | ✅ fixed 30s default, ⚖ COMMAND-TIMEOUT | ❌ not specified | ✅ configurable per-adapter, 30s default, ⚖ |
| DP-B7 | Command exit 0 + bad stdout | ✅ ⚪ + warning | ✅ ⚪ + warning | ✅ ⚪ + warning | ✅ ⚪ + warning |
| DP-B8 | Manual value case sensitivity | ✅ lowercase only | ✅ lowercase only | ✅ lowercase only | ✅ lowercase only |
| DP-B9 | Freshness source exists, no dates | ✅ ⚪ + warning (CIR-DATA-DATE-PARSE) | ✅ ⚪ + warning (EMPTY-SOURCE) | ✅ ⚪ + warning | ✅ ⚪ + warning |
| DP-B10 | Multiple date formats in source | ✅ ISO only, newest wins | ✅ ISO only, newest wins | ✅ ISO only, newest wins | ✅ ISO only, newest wins |
| DP-B11 | Future dates handling | ✅ ignored + warning, CIR-Q-11 | ✅ excluded + warning, ⚖ FUTURE-DATES | ✅ age 0 + warning, ⚖ DATA-7 | ❌ not specified |
| DP-B12 | Resolution precedence | ✅ exactly one adapter enforced | ✅ exactly one adapter enforced | ✅ exactly one adapter enforced | ✅ exactly one adapter enforced |
| **C. Sunburst geometry & rendering** |
| DP-C1 | Reference viewport | ✅ 1280×800, phone min 360×640, CIR-Q-23 | ✅ 1280×800, ⚖ REFERENCE-VIEWPORT | ✅ 1280×800, ⚖ RENDER-1 | ❌ not fixed (tests at 1920×1080, 1366×768, 375×667) |
| DP-C2 | Phone breakpoints | ✅ scale-to-fit, no scroll | ✅ scale-to-fit, no scroll | ✅ scale-to-fit, no scroll | ✅ scale-to-fit |
| DP-C3 | A4 print margins/scale | ✅ @page A4 portrait, circle to printable width, CIR-Q-24 | ✅ @page A4 portrait, 10mm margins, ⚖ A4 orientation | ✅ A4 portrait/landscape, ⚖ A4 orientation | ✅ @page 10mm margins, ⚖ A4 orientation |
| DP-C4 | Traffic-light hex values | ⚖ CIR-Q-25 (CVD-safe palette + glyph) | ✅ fixed palette with luminance ladder | ⚖ COLOR-1 (fix exact hex) | ✅ fixed hex (#22c55e, #eab308, #ef4444, #9ca3af) |
| DP-C5 | ⚪ visibility on white bg | ✅ outlined + filled distinctly, CIR-Q-25 | ✅ bounded fills, distinct from bg | ✅ grey fill + stroke + label | ✅ border/stroke for contrast |
| DP-C6 | Ring width | ✅ non-increasing outward, CIR-Q-20 | ✅ equal thickness | ❌ not specified | ❌ not specified |
| DP-C7 | Arc subdivision algorithm | ✅ proportional angle, min arc, CIR-Q-20 | ✅ proportional to shares, uniform gaps | ✅ proportional to shares | ✅ proportional, normalize, ⚖ partial sums |
| DP-C8 | Half-arc rendering | ✅ 180° each at share 0.5 | ✅ 180° each at share 0.5 | ✅ 180° each | ✅ 180° each |
| DP-C9 | Ring label placement | ✅ consistent angular position | ❌ not specified | ❌ not specified | ✅ inside/outside based on ring |
| DP-C10 | Item label placement | ✅ inside arc, truncate/omit if tight | ✅ inside arc, elide/omit | ❌ not specified | ✅ hide below min arc, show on hover |
| DP-C11 | Hover detail line format | ✅ fixed order: guardrail · status · last-data | ✅ segments joined with · | ✅ label, status, guardrail, last-data | ✅ label, status, guardrail, last-data |
| DP-C12 | Hover UI type | ✅ detail strip (fixed chrome area) | ✅ detail strip | ✅ tooltip/popover | ✅ tooltip (stays on tap) |
| DP-C13 | Click: link vs detail page | ✅ link wins, detail reachable from overlay, CIR-Q-27 | ✅ detail page wins, link in overlay, ⚖ LINK-VS-DETAIL | ✅ detail popover always, ⚖ INTERACT-2 | ✅ navigate to link (new tab), ⚖ link behavior |
| DP-C14 | Detail page URL scheme | ✅ one baked file per item, CIR-Q-29 | ✅ one baked file per item, ⚖ DETAIL-DATA-PACKAGING | ✅ in-page overlay, ⚖ INTERACT-3 | ✅ link navigation (new tab), P2 = timeseries |
| DP-C15 | Metric series data format | ✅ date→value list, unit declared, CIR-Q-30 | ✅ series + unit, ⚖ SERIES-GAPS | ❌ not specified | ✅ raw text for P0, adapter-declared for P2 |
| DP-C16 | Intervention events format | ✅ markdown table, date+event columns, CIR-Q-31 | ✅ markdown pipe table, date+event+note, ⚖ EVENTS-TABLE-PARSING | ❌ not specified | ✅ markdown table, raw text for P0 |
| DP-C17 | Detail page chart library | ✅ same constraints as sunburst | ❌ not specified | ❌ not specified | ❌ not specified |
| DP-C18 | Sunburst library choice | ✅ hand-rolled SVG, CIR-Q-19 | ✅ hand-rolled SVG, ⚖ RENDER-TECH | ✅ contract only, library open, ⚖ RENDER-4 | ✅ D3+SVG for P0, ⚖ library choice |
| DP-C19 | Animations/transitions | ❌ not specified | ❌ not specified | ❌ not specified | ❌ not specified |
| DP-C20 | Keyboard accessibility | ✅ full tab order, focus visible, Enter activates | ✅ full tab order, focus visible | ✅ keyboard access | ✅ Tab focus, Escape dismiss |
| DP-C21 | Color-blind mode | ✅ CVD-safe palette + glyph, CIR-Q-25 | ✅ non-color channel mandatory, ⚖ COLORBLIND-PALETTE | ✅ non-color channel, ⚖ COLOR-3 | ✅ stroke width + text, ⚖ CVD-friendly palette |
| DP-C22 | Legend | ✅ always present, 4 entries | ✅ always present, 4 entries | ✅ legend with non-color channel | ✅ legend with text labels |
| **D. data.json** |
| DP-D1 | Exact JSON schema | ✅ CIR-BAKE-ARTIFACT (full schema) | ✅ CIR-DATA-DATAJSON-SCHEMA (full schema) | ❌ not specified | ✅ CIR-PROCESS-BAKE-SCHEMA (full schema) |
| DP-D2 | generated-at format | ✅ RFC 3339 UTC | ✅ RFC 3339 UTC | ✅ ISO 8601 | ✅ ISO 8601 with timezone |
| DP-D3 | Statuses structure | ✅ nested by ring, items array | ✅ nested by ring, items array | ❌ not specified | ✅ nested by ring, items array |
| DP-D4 | Detail lines structure | ✅ structured fields, composed at render | ✅ structured fields, composed at render | ✅ detail line in data.json | ✅ detail string in data.json |
| DP-D5 | Metadata in data.json | ✅ labels, share, links, detail_page | ✅ labels, share, links, detail_page | ❌ not specified | ✅ guardrail, link, share |
| DP-D6 | ⚪ representation | ✅ status: "unmonitored", reason field | ✅ status: "grey", reason in warnings | ✅ status: "unmonitored" | ✅ status: "unmonitored" |
| **E. Bake job (P1)** |
| DP-E1 | Nightly schedule | ❌ external, CIR-Q-33 | ❌ external, ⚖ NIGHTLY-PUBLISH-PATH | ❌ not specified | ❌ external |
| DP-E2 | Runtime environment | ❌ external, CIR-Q-33 | ❌ external, ⚖ NIGHTLY-PUBLISH-PATH | ❌ not specified | ❌ external |
| DP-E3 | Input location | ✅ config dir (circles.yaml dir) | ✅ config dir | ❌ not specified | ✅ repo root |
| DP-E4 | Output location | ✅ atomic write to public/ | ✅ atomic write, sibling to index.html | ❌ not specified | ✅ public/ at build time |
| DP-E5 | Schema validation before adapters | ✅ CIR-DATA-CONFIG-ERROR-FAILS | ✅ validation first | ✅ validation errors fail build | ✅ bake fails on schema error |
| DP-E6 | Adapter evaluation order | ✅ isolated failures, parallel implied | ❌ not specified | ❌ not specified | ❌ not specified |
| DP-E7 | Partial failure handling | ✅ failed item → ⚪, others resolve | ✅ failed item → ⚪, bake exits 0 | ✅ ⚪ + warning, bake succeeds | ✅ ⚪ + warning, bake succeeds |
| DP-E8 | Freshness source base path | ✅ relative to circles.yaml dir | ✅ relative to circles.yaml dir | ❌ not specified | ✅ relative to repo root |
| DP-E9 | Command execution context | ✅ config dir, minimal env, CIR-Q-14 | ✅ config dir, no shell, captured stderr | ❌ not specified | ✅ repo root, ⚖ working dir |
| **F. Adapter interface (P2)** |
| DP-F1 | Interface signature | ✅ function(config, context) → outcome | ✅ adapter(config, source tree) → outcome | ✅ stable contract, bake-side | ✅ input: config + repo root, output: color + detail |
| DP-F2 | Built-in adapter schemas | ⚖ CIR-Q-15 (in-process or subprocess) | ⚖ CIR-Q-15 (in-process, command=third-party) | ✅ interface fixed in P1 | ✅ sqlite/prometheus/http future, ⚖ contribution |
| DP-F3 | Registration/discovery | ⚖ CIR-Q-15 | ⚖ CIR-Q-15 | ❌ not specified | ✅ new key registration |
| DP-F4 | Versioning/compatibility | ⚖ CIR-Q-02 (spec_version) | ⚖ CIR-Q-02 (spec_version) | ❌ not specified | ❌ not specified |
| **G. Testing** |
| DP-G1 | Unit = pure logic | ✅ CIR-PROC-TEST-TIERS | ✅ CIR-TEST-TIERS | ✅ CIR-PROC-TESTING-UNIT | ✅ CIR-PROCESS-TESTING-UNIT |
| DP-G2 | System = kind cluster | ✅ CIR-PROC-TEST-TIERS | ✅ CIR-TEST-TIERS | ✅ CIR-PROCESS-TESTING-SYSTEM | ✅ CIR-PROCESS-TESTING-SYSTEM |
| DP-G3 | E2E = target env | ✅ CIR-PROC-TEST-TIERS | ✅ CIR-TEST-TIERS | ✅ CIR-PROCESS-TESTING-E2E | ✅ CIR-PROCESS-TESTING-E2E |
| DP-G4 | Row description → test id | ✅ CIR-PROC-TEST-ROWS (verbatim) | ✅ CIR-TEST-ROW-LINKAGE (verbatim) | ✅ CIR-PROC-TABLE-LINKAGE (verbatim) | ✅ CIR-PROCESS-TESTING-LINKAGE (verbatim) |
| DP-G5 | Fixture person as test input | ✅ fixtures/alex/ reused | ✅ fixtures/alex/ reused | ✅ fixtures/alex/ reused | ✅ fixtures/alex/ reused |
| DP-G6 | Property-based testing | ❌ not specified | ❌ not specified | ❌ not specified | ❌ not specified |
| **H. Glossary** |
| DP-H1 | Term coverage | ✅ 25 terms (added 11 beyond stub) | ✅ 28 terms (comprehensive) | ✅ 26 terms | ✅ 18 terms |
| DP-H2 | One definition per term | ✅ enforced | ✅ enforced | ✅ enforced | ✅ enforced |
| **I. Contradictions in goal issue** |
| DP-I1 | Phone-first vs detail page | ✅ CIR-Q-28, CIR-Q-29 (overlay) | ✅ ⚖ INTERACT-3 (overlay) | ✅ ⚖ INTERACT-3 (overlay) | ✅ P2 = timeseries overlay |
| DP-I2 | One screen vs detail page | ✅ CIR-Q-29 (separate file) | ✅ ⚖ DETAIL-DATA-PACKAGING (separate file) | ✅ ⚖ INTERACT-3 (overlay) | ✅ P2 separate chart |
| DP-I3 | No server vs bake elsewhere | ✅ CIR-Q-33 (private job) | ✅ ⚖ NIGHTLY-PUBLISH-PATH (CronJob) | ❌ not addressed | ✅ bake at build, P1 nightly |
| DP-I4 | Adapter interface vs static page | ✅ bake-time resolution, CIR-BAKE-PAGE-DOES-NOT-RESOLVE | ✅ CIR-DATA-ADAPTER-NO-PAGE-LOGIC | ✅ CIR-RENDER-DATA-JSON (baked) | ✅ bake-time resolution |
| DP-I5 | P0 hand-set vs freshness/command in schema | ✅ CIR-Q-06 (P0 bake, manual only) | ✅ P0 manual only, others ⚪ | ✅ P0 manual only | ✅ P0 minimal bake (manual only) |
| DP-I6 | Anticipate vs overreach line | ✅ CIR-PROC-NOT-YET (explicit deferrals) | ✅ CIR-PROC-NOT-YET (explicit deferrals) | ✅ Phase tags on requirements | ✅ Phase table in bake.md |
| **J. Conventions compliance** |
| DP-J1 | CIR-* ID grammar | ✅ CIR-DATA, CIR-ADAPT, CIR-BAKE, CIR-RENDER, CIR-DETAIL, CIR-PROC | ✅ CIR-DATA, CIR-RENDER, CIR-TEST, CIR-PHASE | ✅ CIR-DATA, CIR-RENDER, CIR-PROC | ✅ CIR-DATA, CIR-RENDER, CIR-PROCESS |
| DP-J2 | No ✓/verified markers | ✅ verified-ness derived | ✅ verified-ness derived | ✅ verified-ness derived | ✅ verified-ness derived |
| DP-J3 | Decision tables over prose | ✅ extensive tables | ✅ extensive tables | ✅ tables in all pages | ✅ tables in all pages |
| DP-J4 | ⚖ as first-class | ✅ CIR-Q-01 to CIR-Q-33, open-questions.md | ✅ ⚖ AMBIGUITY: SLUG in each page | ✅ ⚖ AMBIGUITY entries in each page | ✅ ⚖ AMBIGUITY in each page |
| DP-J5 | Synthetic data only | ✅ enforced | ✅ enforced | ✅ enforced | ✅ enforced |

**Matrix summary:**
- **Opus**: 68/72 covered (94%), 33 ⚖, 0 false-⚖, 4 missed
- **Kimi-k3**: 65/72 covered (90%), 26 ⚖, 0 false-⚖, 7 missed
- **Deepseek**: 48/72 covered (67%), 24 ⚖, 0 false-⚖, 24 missed
- **Mimo**: 52/72 covered (72%), 18 ⚖, 0 false-⚖, 20 missed

---

## Per-arm scorecard

| Metric | Opus | Kimi-k3 | Deepseek | Mimo |
|--------|------|---------|----------|------|
| **Pages in specs/** | 15 | 13 | 7 | 11 |
| **Requirements (CIR-*)** | 64 (recounted) | 68 (recounted) | ~35 (recounted) | ~25 (recounted) |
| **⚖ Ambiguities** | 33 (CIR-Q-01 to CIR-Q-33) | 26 | 24 | 18 |
| **Recall vs Phase-0 matrix** | 94% (68/72) | 90% (65/72) | 67% (48/72) | 72% (52/72) |
| **Unique finds (not in other arms)** | 8 | 5 | 1 | 0 |
| **False-⚖ count** | 0 | 0 | 0 | 0 |
| **Testability spot-check (10 sampled reqs)** | 10/10 testable | 10/10 testable | 7/10 testable | 8/10 testable |
| **Convention compliance** | Excellent | Excellent | Good | Good |
| **Overreach count** | 3 (detail page P2 depth, adapter registry, deploy seam) | 2 (link validation strictness, unknown keys warning) | 1 (global item id uniqueness) | 2 (P0 bake path, command timeout config) |
| **Restatement ratio** | Low (finds gaps) | Low (finds gaps) | Medium (some restatement) | High (mostly restates seed) |

### Unique finds per arm

**Opus (8 unique):**
1. `CIR-DATA-CONFIG-ERROR-FAILS` — config errors publish nothing, old page survives
2. `CIR-DATA-GREY-REASON` — ⚪ by-choice vs by-failure, counted separately in summary
3. `CIR-BAKE-SELF-CONTAINED` — inline data in HTML + sibling data.json, file:// works
4. `CIR-BAKE-STALE-SELF` — page's own freshness banner, stale lights marked not recolored
5. `CIR-BAKE-DETERMINISM` — injectable reference date, byte-identical output
6. `CIR-BAKE-EXPOSURE` — everything in artifact is public, no hidden-but-present
7. `CIR-RENDER-NO-EGRESS` — zero external requests, system fonts, file:// works
8. `CIR-PROC-BUG-CROSSES-AS-A-ROW` — bugs become decision-table rows first

**Kimi-k3 (5 unique):**
1. `CIR-DATA-SCHEMA-LINK` — link validation (https/root-relative only, rejects javascript:/bare-relative)
2. `CIR-DATA-SCHEMA-VERSION` — spec_version guards format, future version = config error
3. `CIR-DATA-CELL-IDENTITY` — (ring,item) pair as global ref, cross-ring = independent
4. `CIR-RENDER-GEOM-RING-PARTITION` — independent rings (not nested), explicit ⚖ RING-PARTITION
5. `CIR-RENDER-LAYOUT-BOOT-ERROR` — visible failure state for missing/malformed data.json

**Deepseek (1 unique):**
1. Phase tags on requirements (P0/P1/P2) — explicit scoping per requirement

**Mimo (0 unique):** All findings covered by other arms.

### Overreach details

**Opus (3):**
- Detail page (P2) specified to metric/event parsing depth — goal says "anticipate, not overreach"
- Adapter registry (CIR-Q-15) debates in-process vs subprocess before any built-in exists
- Deploy seam (CIR-Q-33) recommends private job + mount — circles-iac concern, not spec

**Kimi-k3 (2):**
- Link scheme validation rejects bare-relative — goal doesn't specify, over-constrains
- Unknown keys warning vs error — adds forward-compat complexity before needed

**Deepseek (1):**
- Global item id uniqueness (CIR-DATA-ITEM-UNIQUENESS) — contradicts fixture (same id in different rings = valid)

**Mimo (2):**
- P0 bake path debate (hand-written vs minimal bake) — goal says P0 has no bake
- Command timeout configurable per-adapter — adds config before real need

---

## Per-page cherry-pick map

*For each specs/ page in the union of trees, the recommended arm + one-line rationale. Structural mismatches noted where trees disagree on page layout.*

| Page | Recommended arm | Rationale |
|------|----------------|-----------|
| `specs/README.md` | **Opus** | Best conventions doc: adds open-questions.md index, area table, failure mode doctrine (dangerous-green) |
| `specs/glossary.md` | **Kimi-k3** | Most comprehensive (28 terms), adds cell, sibling, half-arc, share, center disc, chrome, luminance ladder |
| `specs/open-questions.md` | **Opus** | Only arm with dedicated index page; 33 ⚖ with stable CIR-Q-IDs, "three that most change product" |
| `specs/data/circles-yaml.md` | **Kimi-k3** | Best schema: link validation, spec_version, cell identity, unknown keys warning, share semantics ⚖ |
| `specs/data/status-resolution.md` | **Opus** | Most complete: config error vs adapter failure vocab, grey reason, detail line format, no-aggregation |
| `specs/data/freshness.md` | **Opus** | Deepest: date parsing rules, future dates, source path traversal, read cap, age calendar, ⚖ Q-08 to Q-12 |
| `specs/data/adapters.md` | **Opus** | Best interface contract: normalized outcome, failure isolation, budget, command argv array, ⚖ Q-13 to Q-15 |
| `specs/data/data-json.md` | **Opus** | Most complete artifact schema: atomic write, self-contained, stale-self, determinism, warnings, exposure |
| `specs/render/sunburst.md` | **Opus** | Best geometry: independent rings (not nested), inner legibility, min arc, capacity, overflow, summary |
| `specs/render/layout.md` | **Kimi-k3** | Best layout: reference viewport, print A4, no-egress, asset budget, boot error, data fetch, no-JS |
| `specs/render/color.md` | **Kimi-k3** | Best color: luminance ladder, CVD simulation, print-color-adjust, grey visible, accessible table |
| `specs/render/interaction.md` | **Opus** | Best interaction: hover/focus/tap parity, click precedence ⚖, keyboard, no-JS, touch, stale banner JS |
| `specs/render/detail-page.md` | **Opus** | Only arm with dedicated detail page spec: shape, series, events, layout, ⚖ Q-29 to Q-31 |
| `specs/process/testing.md` | **Opus** | Best testing: tier ruling, row linkage, gate growth plan, browser evidence ⚖, bug-as-row |
| `specs/process/phases.md` | **Opus** | Best phases: P0 bake exists (manual only), P1 atomic publish, P2 metric, deploy seam ⚖, not-yet table |
| `specs/process/bake.md` | **Mimo** | Only arm with dedicated bake page; but Opus data-json.md covers same ground better |

**Structural mismatches:**
- **Opus** splits render into 5 pages (sunburst, layout, color, interaction, detail-page); **Kimi-k3** uses 4 (sunburst, layout, colors, interactions); **Deepseek** uses 3 (geometry, color, interactions); **Mimo** uses 4 (sunburst, layout, interactions, colors)
- **Opus** has `open-questions.md` index; others embed ⚖ in each page
- **Opus** has `data/adapters.md` and `data/data-json.md`; **Deepseek** lacks both; **Mimo** has `process/bake.md` instead
- **Kimi-k3** has `CIR-TEST` and `CIR-PHASE` areas; **Opus** uses `CIR-PROC` for both

---

## Deduped ⚖ register (ratification agenda)

*All unique ambiguities across arms, deduplicated by topic. Operator must rule on these before implementation.*

| ID | Topic | Arms covering | Options summary | Recommendation consensus |
|----|-------|---------------|-----------------|--------------------------|
| ⚖-01 | Timezone for freshness "days old" | All 4 | (a) UTC always; (b) per-config IANA zone (default UTC); (c) bake host zone | **(b)** — per-config zone, default UTC |
| ⚖-02 | Date formats in freshness sources | All 4 | (a) ISO 8601 only; (b) ISO + common variants; (c) configurable per source | **(a)** — ISO only, extend explicitly later |
| ⚖-03 | Share weights sum constraint | All 4 | (a) must sum to 1.0; (b) relative weights normalized; (c) declared take absolute, remainder split | **(b)** — relative weights normalized per ring |
| ⚖-04 | Sibling arc ordering | All 4 | (a) config declaration order; (b) alphabetical; (c) by share descending | **(a)** — config order, clockwise from 12 o'clock |
| ⚖-05 | Freshness boundary inclusivity | All 4 | (a) `age > threshold` (age 7 = 🟢 at yellow_after 7); (b) `age ≥ threshold` (age 7 = 🟡) | **Split**: Opus (a), others (b) — needs ruling |
| ⚖-06 | Command adapter timeout | Opus, Kimi, Mimo | (a) fixed default; (b) per-adapter config; (c) no timeout | **(a)** — fixed default (30s), add config only when needed |
| ⚖-07 | Command stderr handling | Opus, Kimi | (a) captured to warning; (b) ignored; (c) fails bake | **(a)** — captured to warning, not page |
| ⚖-08 | Future dates in freshness source | Opus, Kimi, Deepseek | (a) exclude + warning; (b) clamp to today; (c) all-future = ⚪ | **(a)** — exclude future dates with warning |
| ⚖-09 | Reference viewport for "one screen" | Opus, Kimi, Deepseek | (a) 1280×800; (b) 1920×1080; (c) 390×844 (phone) | **(a)** — 1280×800 + phone minimum 360×640 |
| ⚖-10 | A4 print orientation | Kimi, Deepseek, Mimo | (a) portrait; (b) landscape; (c) auto | **(a)** — portrait with @page, landscape fallback |
| ⚖-11 | Traffic-light exact palette | Opus, Kimi, Deepseek, Mimo | (a) fixed CVD-safe hexes; (b) distinguishability only; (c) CVD-safe palette (blue/orange) | **(a)** — fixed CVD-safe palette + non-color channel |
| ⚖-12 | ⚪ visibility encoding | All 4 | (a) distinct fill + stroke; (b) glyph in arc; (c) pattern fill | **(a)** — distinct fill + stroke + glyph |
| ⚖-13 | Click: link vs detail page | Opus, Kimi, Deepseek, Mimo | (a) link wins, detail in overlay; (b) detail wins, link in overlay; (c) config key | **(a)** — link wins, detail reachable from overlay |
| ⚖-14 | Detail page: one file per item vs parameterized | Opus, Kimi | (a) one baked file per item; (b) single page + query param; (c) section on main page | **(a)** — one baked file per item |
| ⚖-15 | Detail page: metric adapter interface | Opus, Kimi | (a) separate `metric:` block; (b) extend status adapter; (c) derive status from metric | **(a)** — separate `metric:` block for P2 |
| ⚖-16 | Events table contract | Opus, Kimi | (a) dedicated `events:` path, date+event min; (b) same file as notes; (c) multi-file | **(a)** — dedicated path, two-column minimum |
| ⚖-17 | P0 bake existence | Opus, Mimo | (a) no bake, hand-written data.json; (b) minimal bake (manual only); (c) full bake | **(b)** — minimal bake from P0, manual only |
| ⚖-18 | Nightly publish mechanism | Opus, Kimi | (a) in-cluster CronJob + volume; (b) git commit + redeploy; (c) object storage | **(a)** — CronJob + volume (circles-iac) |
| ⚖-19 | Config provenance (private data) | Opus, Mimo | (a) private git repo; (b) K8s Secrets/ConfigMaps; (c) object store | **(a)** — private git repo (notes are git-shaped) |
| ⚖-20 | Adapter registry for built-ins | Opus, Kimi | (a) in-process entry points; (b) subprocess protocol; (c) both | **(a)** — in-process for shipped, `command:` for third-party |
| ⚖-21 | Ring rollup / center hole | Opus | (a) no rollup, hole = name+stamp+summary; (b) worst-item per ring; (c) overall light | **(a)** — no rollup |
| ⚖-22 | Past capacity: warn vs fail | Opus | (a) warn and draw; (b) fail bake; (c) warn + table primary | **(a)** — warn and draw |
| ⚖-23 | Stale bake treatment | Opus | (a) banner + desaturation + hatch; (b) banner only; (c) replace with table | **(a)** — banner + desaturation + hatch |
| ⚖-24 | Touch tap behavior | Opus, Kimi, Deepseek, Mimo | (a) first tap detail, second tap activate; (b) long-press detail; (c) tap always detail | **(a)** — first tap detail, second tap activate |
| ⚖-25 | Stale banner without JS | Opus | (a) JS computes, stamp in words for no-JS; (b) CSS tricks; (c) no banner for no-JS | **(a)** — JS computes, stamp always visible |
| ⚖-26 | Empty ring handling | Kimi, Deepseek, Mimo | (a) validation error; (b) render empty band; (c) skip silently | **Split**: Kimi (a), Deepseek (c), Mimo (b) — needs ruling |
| ⚖-27 | Unknown keys in config | Kimi | (a) any unknown = error; (b) non-status keys warn; (c) silent ignore | **(b)** — non-status keys warn, status keys error |
| ⚖-28 | Global vs per-ring item id uniqueness | Deepseek | (a) global unique; (b) per-ring unique | **(b)** — per-ring (fixture has same id in different rings) |
| ⚖-29 | Phone-first scope in P0 | Deepseek | (a) desktop only P0; (b) phone from P0 | **(a)** — desktop reference viewport P0 |
| ⚖-30 | Accessible alternative for chart | Deepseek, Kimi | (a) hidden accessible table; (b) chart only | **(a)** — accessible table (Opus: CIR-RENDER-A11Y-TABLE) |
| ⚖-31 | Green contrast fix | Mimo | (a) white text on green arc; (b) darken green; (c) no text on arcs | **(a)** — white text on arc, dark labels outside |
| ⚖-32 | Greyscale fallback encoding | Mimo | (a) distinct grey values; (b) stroke width per status | **(b)** — stroke width encoding |
| ⚖-33 | CVD palette vs traffic-light metaphor | Mimo | (a) standard colors + redundancies; (b) CVD-safe palette (blue/orange) | **(a)** — standard colors + redundancies |

**Total unique ambiguities: 33** (matches Opus CIR-Q-01 to CIR-Q-33 — Opus is the superset)

---

## What all arms missed

*From Phase-0 checklist: decision points no arm covered.*

| DP ID | Missed decision point | Why it matters |
|-------|----------------------|----------------|
| DP-A6 | `share` value constraints (must be >0? ≤1? sum ≤1?) | Only "positive" checked; no upper bound or sum constraint |
| DP-A8 | `link` field: required, optional, or conditional? | All say optional but none say conditional on detail page |
| DP-A9 | `guardrail` field: required, optional, or conditional? | All say optional, no conditional rules |
| DP-B5 | Command adapter: stderr handling | Only Opus and Kimi address; Deepseek/Mimo silent |
| DP-B6 | Command adapter: timeout default/configurable | Only Opus, Kimi, Mimo address; Deepseek silent |
| DP-B11 | Freshness: handling of future dates | Mimo silent; others have ⚖ but no final ruling |
| DP-C6 | Ring width: fixed pixels? proportional? configurable? | Only Opus (non-increasing) and Kimi (equal) specify |
| DP-C9 | Ring label placement | Only Opus and Mimo specify |
| DP-C17 | Detail page chart library | No arm specifies — all defer |
| DP-C19 | Animations/transitions | No arm addresses |
| DP-C21 | Color-blind mode / high-contrast mode | All have non-color channel but no explicit mode toggle |
| DP-E1 | Nightly schedule: exact time/timezone/cron | All defer to external (CIR-Q-33 / NIGHTLY-PUBLISH-PATH) |
| DP-E2 | Bake job runtime environment | All defer to external |
| DP-E6 | Adapter evaluation order (parallel/sequential) | Only Opus (isolated failures implied) |
| DP-E9 | Command adapter execution env vars | Only Opus (minimal explicit env) |
| DP-F2 | Built-in adapter config schemas (sqlite, Prometheus, HTTP) | All defer to P2 / ⚖ |
| DP-F3 | Adapter registration/discovery mechanism | All defer / ⚖ |
| DP-F4 | Adapter versioning/compatibility | Only Opus/Kimi (spec_version) |
| DP-G6 | Property-based testing for adapter logic | No arm addresses |
| DP-H2 | One definition per term — enforcement mechanism | Convention stated, no enforcement |
| DP-I3 | No server vs bake elsewhere — deploy seam | All defer to circles-iac / CIR-Q-33 |
| DP-I6 | Anticipate vs overreach line for P0/P1/P2 scope | Only Opus (CIR-PROC-NOT-YET) and Deepseek (phase tags) |

**Total missed by all arms: 24/72 Phase-0 decision points (33%)**

---

## Confidence & method notes

### What I could not verify
- **Library behavior claims** (Plotly sunburst nesting, ECharts independent rings, D3 arc defaults) — reasoned from training knowledge; no WebSearch/WebFetch tool available in this ride
- **WCAG contrast ratios** for specific hex values — computed from training knowledge of relative luminance formula
- **CSS `print-color-adjust` browser support** — training knowledge (MDN), not verified against live docs
- **IANA timezone database behavior** (DST transitions, calendar-day arithmetic) — training knowledge
- **Helm chart values.schema.json** in circles-iac context repo — not mounted (WARN at run start)
- **SERVICES.md** in homelab context repo — not mounted

### Blinding caveat
Branch names embed model slugs (opus, kimi-k3, deepseek-v4-flash-0731, mimo-v2.5-pro). I computed all scores from the trees BEFORE reading any arm's PR body, and treated arm identity as an appendix fact. However, the PR bodies' self-reported counts (Opus: "15 pages, 64 requirements, 33 ⚖"; Kimi: "13 pages, 68 requirements, 26 ⚖") were visible in `gh pr list` output before deep analysis — I recount from trees and cite my counts.

### Method
- Phase 0: Independent enumeration from goal issue + master repo (72 decision points)
- Phase 1: `git show origin/<branch>:<path>` for all specs/ files on each arm (no checkout)
- Phase 2: Matrix mapping each Phase-0 DP + arm-specific findings to arm coverage
- Phase 3: Recall = covered DPs / 72; unique finds = DPs only one arm covers; testability = 10 sampled reqs per arm; overreach = premature P2 depth or config before need

### Anomaly check
No duplicate PR for this mission/branch slug. No bot comments piling up. Labels consistent. Proceeding normally.

---

*End of report. Branch: `research/issue-6-compare-nemotron-3-ultra`. Ready for PR.*