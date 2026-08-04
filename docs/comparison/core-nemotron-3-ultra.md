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