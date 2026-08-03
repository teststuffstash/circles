# specs/ — the circles contract

The approved-not-authored spec system this stack's agent loop runs on (the same shape
oracle-fleet and sleep-tracking use): **specs are the contract, code converges on them.**
Agents author spec PRs; a human approves every spec merge. The authoring PURPOSE is finding
gaps, contradictions, and ambiguities in the intended system — a spec that merely restates an
issue has failed.

## Tree

- `README.md` — this file: structure + conventions.
- `glossary.md` — every domain term, one definition each.
- `data/` — the data model: `circles.yaml` schema, status resolution, freshness semantics.
- `render/` — the page: sunburst geometry, one-screen/A4 constraint, interactions.
- `process/testing.md` — the ruled test-tier terminology + how requirements link to tests.

(The tree grows per area; this seed fixes only the conventions.)

## Current tree

- `README.md` — this file: structure + conventions.
- `glossary.md` — every domain term, one definition each.
- `data/circles-yaml.md` — the circles.yaml schema stub + status resolution decision table.
- `data/status-resolution.md` — how an item's traffic light is determined from its adapter.
- `data/freshness.md` — the freshness adapter: date extraction, thresholds, timezone anchoring.
- `data/adapters.md` — adapter taxonomy, interface contract, failure modes.
- `render/sunburst.md` — sunburst geometry: ring order, arc subdivision, angular convention.
- `render/layout.md` — one-screen/A4 constraint, scaling, page structure.
- `render/interactions.md` — hover, click, detail page (annotated timeseries).
- `render/colors.md` — traffic light palette, contrast, print/greyscale, color blindness.
- `process/testing.md` — test-tier terminology (unit/system/e2e), decision-table linkage.
- `process/bake.md` — bake pipeline: data.json schema, phases, error handling.

## Conventions

- **Requirement IDs**: stable anchors `CIR-<AREA>-<NAME>` (e.g. `CIR-DATA-FRESHNESS-WINDOW`) —
  one requirement, one anchor; tests and issues reference the ID verbatim. IDs are never
  renamed or reused.
- **Decision tables over prose** wherever behavior branches: visible `inputs || expected` rows,
  each row's description usable as a test id verbatim. The synthetic fixture person under
  `fixtures/` supplies the key examples — spec rows and fixture rows are the same doctrine.
- **⚖ AMBIGUITY entries are first-class**: a judgment call is recorded with its options and a
  recommendation, never silently decided.
- **Verified-ness is derived, never declared**: no ✓/🚧 markers claiming coverage — a
  requirement without a linked test is simply unevidenced.
- **Synthetic data only**: this repo is public; every example, fixture row, and spec value is
  invented. Real people's data is deploy-time content and never appears here.
