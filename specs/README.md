# specs/ — the circles contract

The approved-not-authored spec system this stack's agent loop runs on (the same shape
oracle-fleet and sleep-tracking use): **specs are the contract, code converges on them.**
Agents author spec PRs; a human approves every spec merge. The authoring PURPOSE is finding
gaps, contradictions, and ambiguities in the intended system — a spec that merely restates an
issue has failed.

## Tree

- `README.md` — this file: structure + conventions.
- `glossary.md` — every domain term, one definition each.
- `open-questions.md` — the index of every ⚖ AMBIGUITY in the tree, one row each, with the
  recommendation the specs currently encode. Read it first to see what is still undecided.
- `data/` — the data model:
  - `circles-yaml.md` — the person's configuration: schema, strictness, validation.
  - `status-resolution.md` — how an item gets its light; config error vs adapter failure.
  - `freshness.md` — date parsing, age arithmetic, the two thresholds, dangerous-green.
  - `adapters.md` — the adapter interface contract (the plug-in seam for later built-ins).
  - `data-json.md` — the baked artifact: shape, staleness of the bake itself, exposure.
- `render/` — the page:
  - `sunburst.md` — ring/arc geometry, inside-out order, subdivision, capacity.
  - `layout.md` — the one-screen and single-A4 constraints as testable requirements.
  - `color.md` — status encoding, contrast, ⚪ visibility, print and colour-vision survival.
  - `interaction.md` — hover/focus/tap detail, click targets, keyboard and screen-reader paths.
  - `detail-page.md` — the generic annotated timeseries (metric × dated events).
- `process/` — how the contract is kept:
  - `testing.md` — the ruled test-tier terminology + how decision-table rows link to tests.
  - `phases.md` — what P0/P1/P2 each own, and what a phase may not assume.

## Requirement IDs

Stable anchors `CIR-<AREA>-<NAME>` (e.g. `CIR-DATA-FRESHNESS-WINDOW`) — one requirement, one
anchor; tests and issues reference the ID verbatim. **IDs are never renamed or reused**; a
requirement may move between pages (the ID follows it, the old page keeps a pointer).

| area | owns | pages |
|---|---|---|
| `CIR-DATA-*` | `circles.yaml` schema, validation, status resolution, freshness | `data/circles-yaml.md`, `data/status-resolution.md`, `data/freshness.md` |
| `CIR-ADAPT-*` | the adapter interface every status source implements | `data/adapters.md` |
| `CIR-BAKE-*` | the bake step and the `data.json` artifact it writes | `data/data-json.md` |
| `CIR-RENDER-*` | geometry, layout, colour, interaction of the one page | `render/*.md` |
| `CIR-DETAIL-*` | the annotated-timeseries detail view | `render/detail-page.md` |
| `CIR-PROC-*` | test tiers, phase boundaries | `process/*.md` |

## Conventions

- **Decision tables over prose** wherever behavior branches: visible `inputs || expected` rows,
  each row's description usable as a test id verbatim. The synthetic fixture person under
  `fixtures/` supplies the key examples — spec rows and fixture rows are the same doctrine.
- **⚖ AMBIGUITY entries are first-class**: a judgment call is recorded with its options and a
  recommendation, never silently decided. Each carries an id `CIR-Q-<NN>` so the index in
  `open-questions.md`, a follow-up issue, and a review comment can name the same thing. The
  **recommendation is what the surrounding requirement already encodes** — a requirement is
  never left blank pending an answer; the ⚖ records what would change if the answer differs.
- **Verified-ness is derived, never declared**: no ✓/🚧 markers claiming coverage — a
  requirement without a linked test is simply unevidenced.
- **Synthetic data only**: this repo is public; every example, fixture row, and spec value is
  invented. Real people's data is deploy-time content and never appears here.
- **The failure mode that matters is dangerous-green.** Any path by which an item shows 🟢
  while its data is absent, stale, unparsed, mistyped, or never evaluated is a defect class,
  not a trade-off. Every rule here that could tip either way tips away from green — toward
  ⚪ or 🟡 plus a visible warning. This is the tie-breaker the rest of the tree appeals to.
