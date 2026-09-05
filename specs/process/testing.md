# Testing doctrine

This page records the **ruled** test-tier terminology and the linkage convention between spec
decision tables and tests. The terminology is settled product doctrine, quoted from the goal
issue: **record it, don't re-litigate it.**

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-PROC-TEST-TIERS — the three tiers

| tier | ruled meaning | circles examples |
|---|---|---|
| **unit** | pure logic, in-process, no I/O beyond test doubles | date parsing (`CIR-DATA-DATE-PARSE`), window boundary math (`CIR-DATA-FRESHNESS-WINDOW`), config validation (`CIR-DATA-SCHEMA-*`), palette luminance math (`CIR-RENDER-PALETTE`) |
| **system testing** | logic against **real components in a local cluster (kind)** | the baked image serving a real artifact in kind; chart render, install and page fetch; boot-failure states over real HTTP |
| **e2e** | the **actual target environment** | the deployed page in the real cluster, fed by the real pipeline (circles-iac) — smoke level only |

Adjacent ruled facts, recorded so specs do not demand what the platform cannot give:

- **Docker-backed gates run in GitHub CI, not in a worker ride** — a ride has no daemon, so
  system tests needing kind run in CI. `kind` being present in `devbox.json` is not the same as
  a usable cluster in a ride.
- The gate is `devbox run ci` — one fail-fast seam (`scripts/ci.sh`); product lint and test steps
  are added there as the product lands, never in CI YAML. `devbox run scan-secrets` stays clean.

| row id | inputs | expected |
|---|---|---|
| tier-follows-what-the-requirement-needs | any requirement | the tier is chosen by what must be real, never by convenience |
| no-cluster-in-a-ride | a system test needing kind | runs in CI, not in a worker ride |

_Evidence: none yet — unverified._

## CIR-PROC-TEST-ROWS — a row is a test

Every decision-table row in this tree is written to be executable: the **row id** becomes the
test case id verbatim, `inputs` becomes the fixture, `expected` becomes the assertion. A test
cites its row as `CIR-<AREA>-<NAME>#<row-id>` — e.g.
`CIR-DATA-FRESHNESS-WINDOW#window-at-yellow-boundary` — in its name or an immediately adjacent
annotation, so coverage is **derivable** rather than grep-guessed.

Verified-ness is derived, never declared: a row without a citing test is unevidenced, and no
page carries a ✓ or 🚧 marker claiming otherwise.

| row id | inputs | expected |
|---|---|---|
| row-id-cited-verbatim | the test for the yellow boundary | its name or annotation contains `CIR-DATA-FRESHNESS-WINDOW#window-at-yellow-boundary` verbatim |
| rows-parametrised-not-copied | a 12-row table | one parametrised test with 12 cases, never 12 near-identical functions |
| requirement-id-stable | a requirement that changes meaning | the old ID is marked superseded in place and a new ID minted — never a silent rename |
| row-added-not-renamed | a table gaining a row | a new row id; existing row ids untouched, because they are evidence join keys |
| evidence-identity-is-a-triple | any evidence record | identity is (rule ID, world, case), per [../README.md](../README.md) |

_Evidence: none yet — unverified._

## CIR-PROC-TEST-FIXTURES — tests build from the fixture person

Tests construct inputs **from `fixtures/` rows at runtime** — no hidden or binary fixtures, and
no second synthetic person invented inside test code. Date-sensitive rows are built against the
**injected reference date** (`CIR-ADAPT-REFERENCE-DATE`) rather than by rewriting committed
dates: the committed values stay fixed and readable, and the boundary rows stay exact.

| row id | inputs | expected |
|---|---|---|
| fixture-row-is-spec-row | a spec row with a fixture example | the test builds that exact fixture case |
| dates-relative-to-injected-reference | a freshness boundary test | the reference date is set so the entry lands exactly on the boundary; committed dates are not rewritten |
| no-real-data | any test input | synthetic only — this repo is public |
| fixture-validates-against-the-schema | `fixtures/alex/circles.yaml` | validates against the authored schema, and every `source:`/`command:` path resolves |
| fixture-examples-are-relative-to-a-reference-date | the sleep-log "inside window" example | asserted against the declared fixture reference date, never against today's calendar |

**⚖-R24 — the fixture's freshness examples decay against the calendar.**
`fixtures/alex/notes/sleep-log.md` carries hard dates and is the key example for "freshness
inside window → 🟢" with `yellow_after: 7`, so the committed fixture silently flips 🟢 → 🟡 → 🔴
as time passes. No arm in the fan-out ruled it. Options: (a) rewrite the committed dates at test
time so they stay relative to today; (b) declare a **fixture reference date** and assert every
freshness example relative to it, with the bake's reference date injected to match; (c) a CI
check that fails when the fixture rots. **Ruled: (b).** The committed dates stay readable and
diffable — a reader can see exactly what the example is — and the light a spec row claims is a
statement about (source dates, reference date), which is a complete and time-independent fact.
(a) makes the committed file a lie about what tests actually run; (c) turns the calendar into a
CI outage, failing unrelated PRs on a date nobody chose.

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-PROC-TEST-FIXTURES — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `dates-relative-to-injected-reference` | PASS | — |
| `fixture-validates-against-the-schema` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-PROC-SPEC-GATE — the spec tree gates itself

A spec-only PR has no product tests to run, so the tree is checked mechanically instead. This is
what `scripts/lint-specs.sh` enforces today; it is the reason the conventions survive a
15-page sweep.

| row id | inputs | expected |
|---|---|---|
| spec-ids-are-unique | two requirements with one id | gate fails |
| spec-area-vocabulary-is-closed | `CIR-WIDGET-FOO` | gate fails — the area list in [../README.md](../README.md) is authoritative |
| spec-links-resolve | a link to a missing page | gate fails |
| spec-row-ids-unique-in-table | a table with two identical row ids | gate fails — row ids are evidence join keys |
| spec-evidence-line-present | a requirement with neither an evidence line nor an evidence block | gate fails |
| spec-declares-no-verifiedness | a ✓ or 🚧 marker in a requirement | gate fails |
| spec-world-declared | a page with tables and no `World:` line | gate fails |
| spec-ambiguity-indexed | a `⚖-R<n>` not listed in `open-questions.md` | gate fails |
| spec-fixture-sources-resolve | a fixture `source:` pointing nowhere | gate fails |

_Evidence: none yet — unverified._

## CIR-PROC-GATE — what `devbox run ci` must grow

`scripts/ci.sh` is the one place the gate grows. Today it is the spec gate plus chart validation
and chart unit tests. As the product lands it must gain, in this order, cheapest first:

| row id | inputs | expected |
|---|---|---|
| gate-resolution-logic-unit-tested | the bake package | unit tests run |
| gate-artifact-matches-its-schema | the baked artifact | validated against [`CIR-BAKE-ARTIFACT`](../data/data-json.md) |
| gate-asset-budget | built `index.html` | fails past the budget ([`CIR-RENDER-ASSET-BUDGET`](../render/layout.md)) |
| gate-no-external-origins | built page | fails on any third-party URL ([`CIR-RENDER-NO-EGRESS`](../render/layout.md)) |
| gate-no-dangling-spec-reference | a `CIR-*` cited in code or tests that no longer exists | fails, so a superseded id cannot rot silently |
| gate-secrets-scan-clean | any change | `devbox run scan-secrets` |

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-PROC-GATE — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `gate-no-dangling-spec-reference` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-PROC-BROWSER-EVIDENCE — the render requirements need a browser

A large share of this tree — one screen, one A4, print backgrounds, contrast, focus order, no-JS
rendering, touch targets — cannot be evidenced by any of the three tiers as they stand. It needs
a real browser rendering the built page, which is neither pure logic nor a cluster. This is a
named gap in the ruled taxonomy, not an oversight.

| row id | inputs | expected |
|---|---|---|
| render-requirements-state-their-path | any `CIR-RENDER-*` | evidenced by a headless-browser check, not a unit assertion |
| no-render-claim-from-source-alone | print colour | grepping for `print-color-adjust` is not evidence that fills print |
| screenshots-are-not-the-assertion | any visual requirement | the assertion is a measurable property — no scroll, page count, computed contrast — never an image someone eyeballs |

**P0 note — proxies must say they are proxies.** Both P0 experiment arms shipped before any
browser harness existed, and the acceptance's 1280×800 no-scroll check ran as a static
viewBox/overflow-geometry assertion (one arm added a single manual headless-Chromium run). Under
this requirement that is a **proxy, not evidence** — useful as a fast regression tripwire, never
as satisfaction of `render-requirements-state-their-path`. Until the browser harness lands (its
own issue: which browser image, how it installs, how it wires into `devbox`), a proxy check must
be labelled as such in its test id or docstring, so the evidence chain cannot silently count it.

**⚖-R48 — where do browser checks live in the ruled tiers?** Options: (a) call them *unit* tests
over a headless browser, since no cluster is involved — which stretches "pure logic" past
usefulness; (b) call them *system testing*, since a real component (the browser) renders a real
built artifact; (c) mint a fourth tier. **Ruled: (b).** The tier definitions are settled doctrine
and must not be re-litigated, and a browser rendering the real built page is exactly "logic
against real components" — the only stretch is that the real component is not in the cluster.
(c) would re-open terminology the goal explicitly closed.

_Evidence: none yet — unverified._

## CIR-PROC-BUG-CROSSES-AS-A-ROW — how a defect enters the contract

A bug found in a real deployment cannot be reproduced here with the data that produced it, since
this repo is synthetic-only. It crosses the boundary as a **new fixture row plus a new decision
row**, never as a copied real config.

| row id | inputs | expected |
|---|---|---|
| bug-becomes-a-fixture-row | a defect on a real person's page | a synthetic fixture row reproducing the shape, not the content |
| bug-becomes-a-decision-row | the same defect | a new row in the owning requirement's table, with its own row id |
| bug-fix-cites-the-row | the fixing PR | its test cites the new row id |

_Evidence: none yet — unverified._

## Provenance

No external sources; this page records ruled doctrine and platform facts only.
