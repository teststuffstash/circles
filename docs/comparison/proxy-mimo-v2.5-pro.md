## Verdict (counts: 0 blockers / 8 judgment calls / 4 minors / 21 answered-by-⚖)

## Blockers (0)

No blocking gaps found. The spec tree provides enough information to implement P0 (manual-statuses-only sunburst page) with confidence. Every area — data model, status resolution, sunburst geometry, layout, interactions, colors, bake pipeline, and testing — has sufficient decision tables, fixture examples, and requirement anchors for a builder to proceed.

## Judgment calls (8)

These are decisions a builder could make without asking a human, but the resulting implementation would silently encode product policy that no spec page decided.

1. **Page generation architecture** (`process/bake.md` Overview + Phases)
   The bake pipeline overview (step 5: "Writes the static index.html page") implies the bake tool writes the HTML page, but the P0 phase says "No bake" (manual statuses only, no tool). How does the D3+SVG index.html reach nginx in P0? Options: (a) committed statically in `public/` alongside a bake script that only generates `data.json`; (b) the bake tool carries an HTML template and writes both files; (c) a separate frontend build step (vite/webpack). A builder picks (a) by inferring from the existing Dockerfile + `public/index.html` placeholder pattern — reasonable, but it's a silently made architecture decision.

2. **Ring geometry: thickness distribution and center hole radius** (`render/sunburst.md` Ring layout, `render/layout.md` Scaling)
   The spec says rings are inside-out and arc angular size is share-proportional, but says nothing about radial ring thickness or center-hole radius. A builder would default to equal-thickness rings with the center hole at ~1/6 of the viewBox width. This is a visual design decision made silently.

3. **Error/warning message format** (`data/circles-yaml.md`, `data/status-resolution.md`, `process/bake.md` Error handling)
   The spec requires parse-time validation errors and build warnings but doesn't specify their format (plain text? structured JSON? stderr prefix conventions?). A builder would invent a format (e.g. `[WARN] item 'exercise': no adapter → ⚪ unmonitored`). The spec's test-linkage convention (decision-table descriptions as test IDs) doesn't extend to error strings.

4. **Testing framework and runner configuration** (`process/testing.md` Unit tests, `scripts/ci.sh`)
   The spec says "Unit tests for status resolution logic" must be added to `scripts/ci.sh`. It doesn't say what testing framework or language. `devbox.json` has `python@3.11` and `uv@latest` (strongly implying pytest), but the spec tree doesn't declare this. A builder picks pytest; another builder might pick Go's `testing` package. The CI gate is `bash scripts/ci.sh` — the test command needs to be added there.

5. **data.json runtime validation** (`process/bake.md` data.json schema)
   The spec describes the `data.json` schema exhaustively but doesn't say whether the page (index.html) validates the fetched `data.json` at runtime or trusts it implicitly. For P0, trusting the bake output is safe, but for robustness, a builder might silently add validation. Not a blocker, but an unstated design choice.

6. **Tooling implementation language** (across `process/bake.md`, `process/testing.md`)
   The spec never declares what language implements the bake tool or tests. `devbox.json` includes `python@3.11` and `uv@latest`, which is a strong environmental hint, but a spec-first repo with agent-authored code would benefit from an explicit language declaration. A builder infers Python from the devbox environment.

7. **D3.js version** (`render/sunburst.md` ⚖ Rendering technology)
   The ⚖ recommends "D3 + SVG" but doesn't specify a version (v5, v6, v7 have different APIs for arc generators and data joins). A builder would pick D3 v7 (current). Not blocking — the SVG output is the same — but the import syntax and API calls differ significantly.

8. **Bake tool integration with CI gate** (`process/bake.md` Phases, `process/testing.md` CI gate growth plan)
   The CI gate growth plan says unit tests for status resolution are added in P0, but the bake tool runs separately (nightly or as a build step). It's not specified whether the CI gate runs the bake tool to produce a fresh `data.json` as part of testing. A builder would need to decide: does `devbox run ci` also run the bake? Likely yes for a system test, but not explicitly covered.

## Minors (4)

1. **Manual adapter detail string format** (`process/bake.md` data.json schema `detail` field)
   The `data.json` schema has a `detail` string for the hover tooltip. For freshness adapters, the spec says "Last data: 2026-08-01". For manual adapters, the format is unspecified. Options include `"Manual: yellow"`, `"Hand-set: yellow"`, or `"Status: yellow"`. Trivial but unspecified.

2. **Font family** (`render/layout.md`, `render/colors.md`)
   No font family is specified for labels, tooltips, or legend text. A builder would default to system-ui or sans-serif. Acceptable but silent.

3. **Focus ring exact style** (`render/interactions.md` CIR-RENDER-A11Y)
   "Arc receives visible focus ring" — no color, width, or style specified. A builder would use a 2px blue (`#3b82f6`) outline. Small visual detail.

4. **Tooltip positioning** (`render/interactions.md` CIR-RENDER-HOVER)
   The hover tooltip content is specified (label, status, guardrail, last-data date) but its position relative to the arc is not. Options: above the arc, following the cursor, in a fixed legend area. A builder would choose "above the arc" or "near the cursor."

## Answered by ⚖ (21)

The spec tree flagged 21 ambiguities with explicit recommendations. Each ⚖ entry resolves a decision point that would otherwise be a judgment call. These count as the spec doing its job.

| # | Ambiguity | Location | ⚖ Recommendation |
|---|---|---|---|
| 1 | Rendering library choice | `render/sunburst.md` | D3 + SVG for P0 |
| 2 | P0 data path (no bake vs minimal bake) | `process/bake.md` | Minimal bake: reads manual statuses, writes `data.json` |
| 3 | Timezone anchoring for "days old" | `data/freshness.md` | UTC calendar date arithmetic |
| 4 | Inclusive vs exclusive threshold boundary | `data/freshness.md` | Inclusive (≥) — age ≥ threshold = warning |
| 5 | Partial share sums (not summing to 1.0) | `render/sunburst.md` | Normalize to 1.0; if sum=0, validation error |
| 6 | Mix of share and no-share items in a ring | `render/sunburst.md` | No-share items divide remaining space equally |
| 7 | Arc start angle | `render/sunburst.md` | 12 o'clock (top) |
| 8 | Arc ordering direction | `render/sunburst.md` | Clockwise |
| 9 | Minimum arc size for visibility | `render/sunburst.md` | P0: no minimum, log warning below 5° |
| 10 | A4 orientation | `render/layout.md` | Portrait with landscape CSS fallback |
| 11 | A4 margin specification | `render/layout.md` | 10mm via `@page` CSS |
| 12 | Link navigation behavior (same vs new tab) | `render/interactions.md` | Always new tab (`target="_blank" rel="noopener"`) |
| 13 | Metric value parsing for detail page | `render/interactions.md` | Raw text for P0; adapter-specific format in P2+ |
| 14 | Green `#22c55e` WCAG AA contrast | `render/colors.md` | White text on green arc (badge approach) |
| 15 | Greyscale/print fallback encoding | `render/colors.md` | Stroke width secondary encoding (thin/medium/thick) |
| 16 | CVD-friendly color palette | `render/colors.md` | Standard traffic lights + stroke-width + text redundancies |
| 17 | Label truncation for narrow arcs | `render/colors.md` | Hide label below threshold, show on hover |
| 18 | Date-dependent freshness tests | `process/testing.md` | Inject "now" as a parameter (deterministic) |
| 19 | Adapter timeout for `command:` | `data/adapters.md` | Configurable per-adapter, 30-second default |
| 20 | Command working directory | `data/adapters.md` | Repo root (consistent with `freshness:` source resolution) |
| 21 | `generated_at` format in `data.json` | `process/bake.md` | ISO 8601 with Z (`2026-08-03T19:00:00Z`) |

## Answered well (no question needed)

The following areas of the spec are sufficiently complete that a builder would not form a question at all:

- **circles.yaml v0 schema shape** (`data/circles-yaml.md`): The YAML structure with `manual:`, `freshness:`, `command:` adapters, the `share` field, `guardrail`, and `link` is fully specified with the fixture person exercising all paths.
- **Status resolution decision table** (`data/status-resolution.md`): Every adapter type × every input combination is enumerated with the expected color. The invariant "🔴 means act, never broken tooling" is reinforced across adapters.md, status-resolution.md, and bake.md.
- **Freshness date extraction** (`data/freshness.md`): The ISO 8601 date parsing, the date-format decision table (with supported and unsupported formats), source resolution with glob support, and the path-traversal rejection rule are comprehensive.
- **Adapter interface contract** (`data/adapters.md`): The input/output/failure contract, the five-phase roadmap with explicit P0/P1/P2/P2+ boundaries, and the future-extensibility rules cover what a builder needs.
- **Sunburst ring layout** (`render/sunburst.md`): Ring order (inside-out, index 0 = innermost), arc subdivision (share-proportional), angular convention (12 o'clock, clockwise), and the empty-ring/empty-item edge cases are all specified.
- **One-screen / A4 constraint** (`render/layout.md`): The viewport-sizing math (`width: min(100vw, 100vh)`), SVG viewBox with `preserveAspectRatio`, the page structure (title, sunburst, generated-at stamp, legend), and print CSS approach are concrete enough to implement.
- **Hover and click interaction behavior** (`render/interactions.md`): Tooltip content, hover vs tap, keyboard accessibility, click navigation, and the detail-page P2+ roadmap are fully decision-tabled.
- **Color palette and legibility** (`render/colors.md`): The four-status hex palette, contrast requirements, WCAG AA mention, print/greyscale strategy, and color-blindness accommodations are specified with decision tables.
- **data.json schema** (`process/bake.md`): Every field, its type, nullability, and semantics are defined. The full example JSON is concrete.
- **Bake error handling** (`process/bake.md`): The error decision table covers six distinct failure modes with expected behavior (fail vs warn).
- **Test tier definitions** (`process/testing.md`): The three-tier terminology (unit/system/e2e), scope boundaries, environment requirements, and the decision-table-to-test-ID linkage convention are precise.
- **Fixture person Alex** (`fixtures/alex/circles.yaml`): Every adapter type and status combination is exercised by a named item, providing concrete, testable examples that match the spec decision tables row-for-row.

## Method notes

**What was read:**
- All 10 spec files under `specs/` on the arm branch `research/issue-1-mimo-v2.5-pro` (commit 7c63da4), end-to-end: `README.md`, `glossary.md`, `data/circles-yaml.md`, `data/status-resolution.md`, `data/adapters.md`, `data/freshness.md`, `render/sunburst.md`, `render/layout.md`, `render/interactions.md`, `render/colors.md`, `process/bake.md`, `process/testing.md`.
- Fixture person files under `fixtures/alex/` (circles.yaml, notes/*.md, notes/*.sh) — fair game as build environment a real builder would have.
- Infrastructure files under `chart/`, `public/`, `scripts/`, `Dockerfile`, `devbox.json`, `CLAUDE.md` — fair game as build environment.
- Context repo `/work/context/homelab/SERVICES.md` and `/work/context/circles-iac/circles/agent/agentstack.yaml` — platform facts a real builder would have access to.

**What was deliberately NOT read:**
- The mission issue #6 beyond the arm table.
- Issue #1, its body, or any PR bodies (PRs #2, #3, #4, #5).
- The other three arm branches (`research/issue-1-opus`, `research/issue-1-kimi-k3`, `research/issue-1-deepseek-v4-flash-0731`).
- `docs/comparison/` on the main branch (any prior reports).
- Homelab agent docs, trackers (TICK-LOG), retros, follow-ups, or any meta-state that discusses the arms.

**P0 scope assumed for this analysis:** manual adapter only (`manual: green|yellow|red`), minimal bake converting manual statuses to `data.json`, sunburst page with hover + click interactions, one-screen/A4 constraint, unit tests for status resolution. Freshness, command, and detail pages are P1/P2+ and were not evaluated as part of P0 buildability.