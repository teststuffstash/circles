# Adapters — the interface and the v0 taxonomy (CIR-DATA-ADAPTER-*)

An **adapter** is how an item gets its light. The taxonomy: `manual:` (hand-set, v0),
`freshness:` (newest date in a source vs thresholds — see [freshness.md](freshness.md)),
`command:` (user script prints the status — the escape hatch that absorbs every weird
personal data source). Contributed built-ins come later (sqlite query, Prometheus query,
HTTP/REST to-do state); the interface below is the seam they plug into.

## CIR-DATA-ADAPTER-INTERFACE — the contract

An adapter is a **bake-time** evaluation: `adapter(config fragment, source tree) → outcome`,
where an outcome is:

| field | presence | meaning |
|---|---|---|
| `status` | always | `green` \| `yellow` \| `red` \| `grey` |
| `last_data_date` | optional | ISO date the adapter observed (drives the detail line) |
| `warning` | optional | human-readable build warning text (rides with ⚪ outcomes) |

Adapters are **normalized at the boundary**: whatever the source, the outcome is the same
three fields, frozen into `data.json` (CIR-DATA-DATAJSON-SCHEMA). The page never sees adapter
types — a consequence testable as "the renderer contains no adapter-specific code paths".

| row (test id) | inputs | expected |
|---|---|---|
| outcome-shape-manual | `manual: green` | `{status: green}`, no last-data date, no warning |
| outcome-shape-freshness | freshness inside window | `{status: green, last_data_date: <newest date>}` |
| outcome-shape-failure | command exits 1 | `{status: grey, warning: <cause>}` |

## CIR-DATA-ADAPTER-REGISTRY — a closed v0 set with a plug-in seam

v0 recognizes exactly three adapter keys: `manual`, `freshness`, `command`. Unknown keys fail
validation (CIR-DATA-SCHEMA-EXACTLY-ONE-ADAPTER). Later built-ins (sqlite, Prometheus,
HTTP/REST) join by **registering a new key + evaluator in the bake**, producing the same
normalized outcome — **no page change, no `data.json` shape change**. A config using a future
adapter on an old bake fails validation loudly rather than rendering silent grey (the
UNKNOWN-KEYS exception, [circles-yaml.md](circles-yaml.md)).

## CIR-DATA-ADAPTER-MANUAL — hand-set lights

`manual:` passes the configured word through as the status; it cannot fail and has no
last-data date. Vocabulary: `green | yellow | red` only — no manual grey
(CIR-DATA-STATUS-MANUAL-VALUES). Manual statuses are how P0 works entirely
([../process/phases.md](../process/phases.md)).

## CIR-DATA-ADAPTER-COMMAND-EXEC — the escape hatch's execution contract

`command:` is an **argv array executed without a shell** (no interpolation, no globbing, no
pipes — a command needing shell features must be wrapped in a script file, like the fixture's
[`plants-status.sh`](../../fixtures/alex/notes/plants-status.sh)). Execution context:

- **cwd** = the directory containing `circles.yaml` (relative argv paths resolve from there);
- **stdout contract**: the **first non-empty line**, trimmed, matched case-insensitively,
  must be exactly `green`, `yellow`, or `red`;
- **exit code** non-zero ⇒ ⚪ + build warning (never 🔴);
- **unparseable stdout** ⇒ ⚪ + build warning;
- **stderr** is captured into the build log, included in the warning text when non-empty;
- **trust**: `circles.yaml` is trusted input on par with code — the bake executes it with the
  bake's own identity. Configs from untrusted sources must never be baked.

| row (test id) | inputs | expected |
|---|---|---|
| command-prints-yellow | script prints `yellow` | 🟡 (the fixture's plants item) |
| command-case-insensitive | prints `Green\n` | 🟢 |
| command-leading-noise | first line blank, second line `red` | 🔴 (first non-empty line wins) |
| command-extra-output-after | `yellow` then 40 lines of diagnostics | 🟡; later lines ignored (diagnostics stay free) |
| command-nonzero-with-valid-word | prints `red`, exits 1 | ⚪ + build warning — exit code dominates stdout |
| command-shell-metachars | `command: ["sh", "-c", "echo green; rm -rf x"]` | runs exactly that argv; no shell features implied by the contract itself |
| command-hangs | script never exits | ⚪ + build warning after the deadline (⚖ COMMAND-TIMEOUT) |
| command-cwd-relative | `command: ["./notes/plants-status.sh"]` | resolves from the circles.yaml directory (the fixture case) |

**⚖ AMBIGUITY: COMMAND-TIMEOUT** — a hanging command would hang the nightly bake. Options:
(a) fixed timeout hardcoded in the bake (e.g. 30 s); (b) per-adapter `timeout:` config key
with a default; (c) no timeout. **Recommendation: (a), 30 s fixed in v0** — a status probe
that needs > 30 s is a data source that needs its own caching, not a longer leash; adding a
config knob (b) before anyone has asked for it violates the anticipate-don't-overreach rule
(the key can be added later without breaking (a) configs). (c) is rejected: one wedged
script must not silence the whole page's nightly refresh.

## CIR-DATA-ADAPTER-NO-PAGE-LOGIC — the page is adapter-blind

Statuses, dates, and warnings reach the page only as baked fields in `data.json`
(CIR-DATA-STATUS-RESOLUTION-TIME). Adding the P2 sqlite metric adapter, or any contributed
built-in, is a bake-side change only. The single page-side hook a future adapter may use is
the per-item detail payload pointer (CIR-DATA-DATAJSON-DETAIL-FILES) — already part of the
baked schema.
