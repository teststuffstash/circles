# Testing doctrine (CIR-TEST-*)

This page records the **ruled** test-tier terminology and the linkage convention between
spec decision tables and tests. The terminology is settled product doctrine (quoted from
the goal issue): **record it, don't re-litigate it.**

## CIR-TEST-TIERS — the three tiers

| tier | ruled meaning | circles examples |
|---|---|---|
| **unit** | pure logic, in-process, no I/O beyond test doubles | date parsing (CIR-DATA-FRESHNESS-DATE-PARSING), window boundary math (CIR-DATA-FRESHNESS-WINDOW), config validation rows (CIR-DATA-SCHEMA-*), palette luminance math (CIR-RENDER-COLOR-PALETTE) |
| **system testing** | logic against **real components in a local cluster (kind)** | the baked image serving a real `data.json` in kind; chart render + deploy + page fetch; boot-error states against real HTTP |
| **e2e** | the **actual target environment** | the deployed page in the real cluster, fed by the real pipeline (circles-iac) — smoke-level only |

Adjacent ruled facts:

- **Docker-backed gates run in GitHub CI, not in a worker ride** — a ride has no daemon;
  system tests that need kind run in CI. (Platform fact, recorded so specs don't demand
  ride-local clusters.)
- The gate is `devbox run ci` — one fail-fast seam (`scripts/ci.sh`); product lint/test
  steps are added there as the product lands, never in CI YAML. `devbox run scan-secrets`
  stays clean.

## CIR-TEST-ROW-LINKAGE — decision-table rows are test ids

Each decision table's first column is a kebab-case **row slug**; a test cites its row
verbatim as `CIR-<AREA>-<NAME>#<row-slug>` — e.g.
`CIR-DATA-FRESHNESS-WINDOW#window-at-yellow-boundary`. The citation lives in the test's
name or an immediately adjacent annotation, so a coverage report can derive, mechanically,
which requirement rows have evidence. **Verified-ness is derived, never declared**: a row
without a citing test is unevidenced, and specs carry no ✓/🚧 markers claiming otherwise.

| row (test id) | inputs | expected |
|---|---|---|
| row-slug-verbatim | test for the yellow boundary | its name/annotation contains `CIR-DATA-FRESHNESS-WINDOW#window-at-yellow-boundary` verbatim |
| requirement-id-stable | a requirement that changes meaning | old ID marked superseded in place, new ID minted — never a silent rename (specs/README.md) |
| row-added-not-renamed | a table gaining a row | new kebab-case slug; existing slugs untouched |

## CIR-TEST-FIXTURES — tests build from the fixture person

Tests construct their inputs **from `fixtures/` rows at runtime** — no hidden or binary
fixtures, no second synthetic person invented inside test code (fixtures/README.md:
bug reports cross the boundary as new fixture rows, not as real data). Date-sensitive rows
(freshness windows, future dates) are built by **rewriting committed fixture dates relative
to the bake's "today"** at runtime — the committed values are illustrative only, so boundary
rows (`window-at-yellow-boundary`: entry date = today − `yellow_after`) stay exact without a
clock-injection seam in the bake.

| row (test id) | inputs | expected |
|---|---|---|
| fixture-row-is-spec-row | a spec decision-table row with a fixture example | the test builds that exact fixture case |
| dates-relative-to-today | a freshness boundary test | fixture file copied, dates rewritten relative to bake day, then baked |
| no-real-data | any test input | synthetic only — this repo is public |

## CIR-TEST-GATES — what must run where

| row (test id) | inputs | expected |
|---|---|---|
| ci-green-before-pr | any PR | `devbox run ci` green, `devbox run scan-secrets` clean |
| spec-prs-add-no-tests | a specs/-only PR (like the one introducing this tree) | no test changes; evidence linkage comes with the builders' PRs |
| code-pr-cites-ids | a PR implementing a requirement | its tests cite the requirement rows they evidence |

## Provenance

No external sources; this page records ruled doctrine and platform facts only.
