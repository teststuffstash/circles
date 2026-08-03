# Testing — test-tier terminology and requirements linkage

**CIR-PROCESS-TESTING** — The ruled test-tier terminology for the circles stack.

## Test tiers

The goal issue defines three test tiers. These are recorded here; they are not re-litigated.

### Unit tests

**CIR-PROCESS-TESTING-UNIT** — "unit" = pure logic, no I/O, no components. Runs in milliseconds.

Unit tests exercise:
- Status resolution logic (adapter → color mapping)
- Freshness date extraction and age calculation
- Share weight normalization
- YAML schema validation
- Command output parsing

Unit tests are fast, deterministic, and run in CI on every commit. They use synthetic fixture data only (from `fixtures/`).

### System tests

**CIR-PROCESS-TESTING-SYSTEM** — "system testing" = logic against real components in a local cluster (kind). A kind cluster runs the nginx image with the baked page.

System tests exercise:
- The bake job produces valid `data.json` and `index.html`
- The nginx image serves the page correctly
- The Helm chart deploys successfully
- Status resolution against real fixture files (real freshness calculation)

System tests require a kind cluster (available via `devbox` in this environment) and run in CI.

### E2E tests

**CIR-PROCESS-TESTING-E2E** — "e2e" = the actual target environment. Tests against the deployed instance.

E2E tests exercise:
- The deployed page renders correctly in a real browser
- Hover and click interactions work
- Traffic lights display correct colors
- Print layout produces valid A4 output

E2E tests run in the deployment pipeline (not in the dev sandbox).

## Decision table to test linkage

**CIR-PROCESS-TESTING-LINKAGE** — Every decision-table row in these specs has a description that serves as a test ID verbatim. The convention:

1. Spec page contains a decision table with `description` column.
2. Each `description` value is a test ID: `CIR-<AREA>-<SPEC>-<description-slug>`.
3. The test implementation references the requirement ID in its name/comments.
4. A requirement without a linked test is simply **unevidenced** — no markers, no claims.

### Linkage decision table

| description | inputs | expected |
|---|---|---|
| test references spec ID | test file contains `# CIR-DATA-STATUS-RESOLUTION` | Test is linked to that requirement |
| spec has no linked test | spec page has a decision table row with no corresponding test | Requirement is unevidenced (no marker needed) |
| test references nonexistent spec ID | test has `# CIR-FAKE-ID` | CI fails: dangling spec reference |

## Fixture data for tests

**CIR-PROCESS-TESTING-FIXTURES** — Tests use the fixture person under `fixtures/alex/` as their primary data source. Fixture data is synthetic by rule (this repo is public).

### Fixture usage decision table

| description | inputs | expected |
|---|---|---|
| freshness test | `fixtures/alex/notes/sleep-log.md` + today's date | Calculate age of 2026-08-01 from today |
| freshness stale test | `fixtures/alex/notes/labs.md` + today's date | Calculate age of 2026-01-15 from today |
| manual test | `fixtures/alex/circles.yaml` date-night | Status = yellow |
| command test | `fixtures/alex/notes/plants-status.sh` | stdout = "yellow", exit = 0 |
| unmonitored test | `fixtures/alex/circles.yaml` exercise | Status = ⚪ |

⚖ **AMBIGUITY: Date-dependent tests.** Freshness tests depend on "today" — a test that passes today (age=2) may fail in a month (age=32). Options: (a) freeze time in unit tests (inject "now" as a parameter); (b) rewrite fixture dates at runtime relative to "now"; (c) commit dates and accept that tests age. **Recommendation:** (a) — inject "now" as a parameter in all freshness calculations. Rationale: deterministic, no fixture mutation needed. The committed fixture dates are illustrative; tests override "now" to known values. The sleep-log.md fixture comment already anticipates this: "Tests may rewrite dates at runtime relative to 'today'."

## CI gate integration

**CIR-PROCESS-TESTING-CI** — The CI gate (`scripts/ci.sh`) MUST include spec-related test steps as the product lands. Currently: chart validation + chart unit tests only.

### CI gate growth plan

| phase | additions to `scripts/ci.sh` |
|---|---|
| P0 (manual statuses) | Unit tests for status resolution logic |
| P1 (freshness/command) | Unit tests for freshness date extraction + command adapter |
| P1 (bake) | System test: bake job produces valid data.json |
| P2 (detail page) | System test: detail page renders with fixture data |

## Test-tier summary

| tier | scope | environment | tooling | frequency |
|---|---|---|---|---|
| unit | pure logic | in-process (pytest/jest) | devbox | every commit |
| system | real components | kind cluster | kind + devbox | every PR |
| e2e | full deployment | target env | browser + deploy pipeline | pre-merge / on deploy |