# specs/ — the circles contract

The approved-not-authored spec system this stack's agent loop runs on (the same shape
oracle-fleet and sleep-tracking use): **specs are the contract, code converges on them.**
Agents author spec PRs; a human approves every spec merge. The authoring PURPOSE is finding
gaps, contradictions, and ambiguities in the intended system — a spec that merely restates an
issue has failed.

## Tree

- `README.md` — this file: structure + conventions + how to read requirement IDs.
- `glossary.md` — every domain term, one definition each.
- `data/` — the data model:
  - `circles-yaml.md` — the `circles.yaml` schema, status resolution, validation, adapter
    interface, share/sibling semantics.
  - `freshness.md` — the `freshness:` adapter: date parsing, windows/boundaries, timezone/DST
    anchoring, missing/future sources.
- `render/` — the page:
  - `geometry.md` — sunburst geometry: ring order, arc subdivision, half-arcs, the
    one-screen/A4 constraint, overflow.
  - `color.md` — traffic-light colors, ⚪ unmonitored visibility, accessibility.
  - `interactions.md` — hover/click, the detail page, the baked `data.json` contract, the
    single-asset constraint.
- `process/testing.md` — the ruled test-tier terminology + how decision-table rows link to
  tests.

## Conventions

- **Requirement IDs**: stable anchors `CIR-<AREA>-<NAME>` (e.g. `CIR-DATA-FRESHNESS-WINDOW`) —
  one requirement, one anchor; tests and issues reference the ID verbatim. IDs are never
  renamed or reused. Areas today: `CIR-DATA-*`, `CIR-RENDER-*`, `CIR-PROC-*`. A requirement
  appears exactly once, in the page that owns its area; other pages link to it by ID.
- **Decision tables over prose** wherever behavior branches: visible `inputs || expected` rows,
  each row's description usable as a test id verbatim. The synthetic fixture person under
  `fixtures/` supplies the key examples — spec rows and fixture rows are the same doctrine.
- **⚖ AMBIGUITY entries are first-class**: a judgment call is recorded with its options and a
  recommendation, never silently decided. Every ⚖ is a real fork the goal issue left open —
  not a placeholder. The recommendation is the spec's default until the operator rules.
- **Verified-ness is derived, never declared**: no ✓/🚧 markers claiming coverage — a
  requirement without a linked test is simply unevidenced. Evidence linkage is added later by
  the builder, never fabricated here.
- **Synthetic data only**: this repo is public; every example, fixture row, and spec value is
  invented. Real people's data is deploy-time content and never appears here.
- **Phases are scoped, not overreached**: requirements carry a `Phase:` tag (P0/P1/P2) where
  the goal phases them, so the builder knows what to land when — but the spec does not invent
  P2 machinery the goal did not ask for.

## How to read a requirement ID

`CIR-<AREA>-<NAME>` — e.g. `CIR-DATA-FRESHNESS-WINDOW`:

- `CIR` — this stack's spec prefix (circles).
- `<AREA>` — the owning page: `DATA` (data model), `RENDER` (the page), `PROC` (process/testing).
- `<NAME>` — a stable, descriptive slug unique within the area.

A requirement is a single normative sentence (or a decision-table row) under its ID. Tests and
issues cite the ID verbatim; the ID is the join key between spec, fixture row, and test.
