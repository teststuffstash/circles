# specs/ — the circles contract

The approved-not-authored spec system this stack's agent loop runs on (the same shape
oracle-fleet and sleep-tracking use): **specs are the contract, code converges on them.**
Agents author spec PRs; a human approves every spec merge. The authoring PURPOSE is finding
gaps, contradictions, and ambiguities in the intended system — a spec that merely restates an
issue has failed.

## Tree

- `README.md` — this file: structure + conventions.
- `glossary.md` — every domain term, one definition each.
- `data/` — the data model:
  - [data/circles-yaml.md](data/circles-yaml.md) — the person's configuration schema:
    rings, items, adapters, validation rules.
  - [data/status-resolution.md](data/status-resolution.md) — how an item's light is resolved;
    the failure algebra (tooling failure ⇒ ⚪ + warning, never 🔴).
  - [data/freshness.md](data/freshness.md) — the freshness adapter: sources, date parsing,
    freshness windows, edge cases (empty/missing/future dates, timezone anchoring).
  - [data/adapters.md](data/adapters.md) — the adapter interface contract and the v0 taxonomy
    (`manual:` / `freshness:` / `command:`), plus the plug-in seam for later built-ins.
  - [data/data-json.md](data/data-json.md) — the baked render input the page consumes
    (statuses, detail fields, generated-at stamp, warnings).
- `render/` — the page:
  - [render/sunburst.md](render/sunburst.md) — sunburst geometry: ring order, the independent
    ring partition, arc subdivision and shares, labels, density.
  - [render/layout.md](render/layout.md) — the one-screen / A4 constraint as testable
    requirements; asset self-containment; boot-error behavior.
  - [render/colors.md](render/colors.md) — the status palette, ⚪ visibility, legibility,
    the legend.
  - [render/interactions.md](render/interactions.md) — hover/click/keyboard behavior over
    baked `data.json`; the P2 annotated-timeseries detail-page contract.
- `process/`
  - [process/testing.md](process/testing.md) — the ruled test-tier terminology + how
    decision-table rows link to tests.
  - [process/phases.md](process/phases.md) — the P0/P1/P2 scope boundaries: what each phase
    must and must not build (anticipate, don't overreach).

## How to read requirement IDs

- **Requirement IDs**: stable anchors `CIR-<AREA>-<NAME>` (e.g. `CIR-DATA-FRESHNESS-WINDOW`) —
  one requirement, one anchor; tests and issues reference the ID verbatim. IDs are never
  renamed or reused; a requirement that changes meaning gets a new ID and the old one is
  marked superseded in place.
- Areas minted so far: `CIR-DATA` (data model), `CIR-RENDER` (the page), `CIR-TEST` (test
  doctrine), `CIR-PHASE` (delivery phases).
- **Decision-table rows are test ids**: each table's first column is a kebab-case row slug;
  a test cites its row as `CIR-<AREA>-<NAME>#<row-slug>` verbatim (see
  [process/testing.md](process/testing.md)).
- **⚖ AMBIGUITY entries are first-class**: a judgment call is recorded in place with its
  options and a recommendation, keyed `⚖ AMBIGUITY: <SLUG>`, never silently decided. The PR
  body that introduces an ⚖ entry lists it one line per entry so the human can confirm or
  override the recommendation at merge time.

## Conventions

- **Decision tables over prose** wherever behavior branches: visible `inputs || expected` rows,
  each row's description usable as a test id verbatim. The synthetic fixture person under
  `fixtures/` supplies the key examples — spec rows and fixture rows are the same doctrine.
- **Verified-ness is derived, never declared**: no ✓/🚧 markers claiming coverage — a
  requirement without a linked test is simply unevidenced.
- **Synthetic data only**: this repo is public; every example, fixture row, and spec value is
  invented. Real people's data is deploy-time content and never appears here.
- **Provenance notes**: where a page leans on external knowledge (library behavior, print
  CSS, accessibility thresholds) it says so at the bottom and whether that knowledge was
  verified against a source in this ride or reasoned from training data.
