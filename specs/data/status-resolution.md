# Status resolution (CIR-DATA-STATUS-*)

How an item's light is resolved. The traffic-light semantics are **fixed product doctrine**:

- 🟢 ok · 🟡 attention · 🔴 act — per item, from its adapter;
- ⚪ unmonitored — an item with **no adapter**, or an item whose tooling failed. Grey is
  honest and visible: never hidden, never defaulted to green;
- **tooling failure is ⚪ + a build warning, never 🔴** — red means "act on your life",
  not "the tooling broke".

## CIR-DATA-STATUS-RESOLUTION — the canonical table

| row (test id) | inputs | expected |
|---|---|---|
| no-adapter-declared | item without `status:` | ⚪ unmonitored |
| manual-green | `manual: green` | 🟢 |
| manual-yellow | `manual: yellow` | 🟡 |
| manual-red | `manual: red` | 🔴 |
| freshness-inside-window | newest date 3d old, `yellow_after: 7`, `red_after: 30` | 🟢 |
| freshness-stale | newest date 10d old, `yellow_after: 7`, `red_after: 30` | 🟡 |
| freshness-very-stale | newest date 45d old, `yellow_after: 7`, `red_after: 30` | 🔴 |
| freshness-source-missing | `source:` matches no file | ⚪ + build warning |
| freshness-source-no-dates | source file exists, zero parseable dates | ⚪ + build warning (see ⚖ EMPTY-SOURCE) |
| freshness-all-dates-future | every parseable date is after "today" | ⚪ + build warning (see ⚖ FUTURE-DATES) |
| command-nonzero-exit | `command:` exits non-zero | ⚪ + build warning — never 🔴 |
| command-bad-stdout | `command:` prints `orange` | ⚪ + build warning |
| command-timeout | `command:` exceeds its execution deadline | ⚪ + build warning (see ⚖ COMMAND-TIMEOUT) |
| unknown-adapter-key | `status: {sqlite: …}` | not a status outcome: validation error, bake fails (CIR-DATA-SCHEMA-EXACTLY-ONE-ADAPTER) |

## CIR-DATA-STATUS-TOOLING-FAILURE — the failure algebra

Every adapter-runtime failure mode — missing source, unreadable file, zero parseable dates,
command non-zero exit, command timeout, unparseable command output, future-only dates —
resolves to the **same outcome**: ⚪ + a build warning naming the item and the cause. No
failure mode may synthesize 🔴 (red is reserved for "your life needs action" judgments: a
hand-set red, or data that is present and very stale). No failure mode may synthesize 🟢
either: broken tooling must never masquerade as ok.

| row (test id) | inputs | expected |
|---|---|---|
| failure-never-red | any adapter failure | outcome ∈ {⚪ + warning}; 🔴 impossible |
| failure-never-green | any adapter failure | outcome ∈ {⚪ + warning}; 🟢 impossible |
| warning-names-item | `plants` command exits 3 | warning identifies cell `wider/plants` and the exit code |

## CIR-DATA-STATUS-MANUAL-VALUES — the manual adapter's vocabulary

`manual:` accepts exactly `green`, `yellow`, `red` (lowercase). **There is no `manual: grey`**:
the way to be ⚪ is to omit `status:` entirely — grey means "unmonitored", and a hand-set
grey would conflate "deliberately unmonitored" with "forgot to wire the adapter". An item the
person deliberately leaves unmonitored simply declares no adapter; its grey is then true.

## CIR-DATA-STATUS-NO-AGGREGATION — no roll-up, ever

Statuses exist **per item only**. The page computes and displays no ring-level or page-level
aggregate (no "worst-of" ring tint, no overall score, no center summary light). "The
innermost ring must hold for the outer ones to matter" is **reading doctrine for the human**,
not a computation: a 🔴 in ring 1 does not recolor, dim, or flag outer rings. This keeps
every visible light traceable to exactly one adapter verdict.

| row (test id) | inputs | expected |
|---|---|---|
| inner-red-outer-untouched | `self/sleep` 🔴, `partner/date-night` 🟡 | outer cells keep their own resolved colors |
| fully-grey-ring | a ring whose items all lack adapters | the whole band renders ⚪; no special treatment |

## CIR-DATA-STATUS-RESOLUTION-TIME — statuses resolve at bake time only

Statuses are resolved **when the bake runs** and frozen into `data.json`. The page is a pure
renderer of baked verdicts: it contains no adapter code, no date math, no re-evaluation on
load. Consequences:

| row (test id) | inputs | expected |
|---|---|---|
| page-never-reevaluates | `data.json` says 🟡; viewer opens the page days later | still 🟡 — the generated-at stamp (CIR-RENDER-LAYOUT-GENERATED-AT-VISIBLE) is the honesty mechanism, not live recomputation |
| p0-manual-roundtrip | P0 bake over a `manual:`-only config | statuses pass through unchanged into `data.json` |
