# Adapters — the interface every status source implements

The issue asks for contributed built-ins later (sqlite query, Prometheus query, HTTP to-do
state) that "plug in without touching the page". That only holds if the seam is written down
now, while there are three adapters, rather than discovered later from three call sites.

## CIR-ADAPT-CONTRACT — one adapter, one answer <a id="cir-adapt-contract"></a>

An adapter is a named function from *(its config block, the resolution context)* to exactly one
of: a status, or a failure. Nothing else about it reaches the rest of the system.

| the adapter receives | |
|---|---|
| its own config block | validated against **its own** schema fragment |
| the config directory | the root every path it reads is resolved under |
| the reference date + timezone | so it never reads a clock itself ([CIR-BAKE-DETERMINISM](data-json.md)) |
| a time budget | [CIR-ADAPT-BUDGET](#cir-adapt-budget) |

| the adapter returns | |
|---|---|
| `status` | `green` \| `yellow` \| `red` |
| `data_date` | optional; the date the status is *about*, for the detail line |
| `note` | optional; one short plain-text phrase for the detail line |
| — or a failure | one plain-text reason; the caller turns it into ⚪ + warning |

| description | inputs | expected |
|---|---|---|
| an adapter cannot return grey | adapter attempts to resolve ⚪ | not expressible — ⚪ comes only from absence or failure ([CIR-DATA-GREY-REASON](status-resolution.md)) |
| an adapter cannot resolve two items | one `status:` block | one status |
| an adapter never reads the clock | adapter needs "today" | uses the injected reference date |
| an adapter never writes | adapter attempts to write in the config dir | forbidden; the bake owns all output |
| an unknown adapter name | `status: {prometheus: …}` on a build without it | config error today; see ⚖ CIR-Q-01 |
| adapter failure is isolated | one of ten adapters raises an unexpected exception | that item is ⚪ + warning; the other nine resolve normally |

The last row matters more than it looks: an unhandled exception in a contributed adapter must
not take down the bake, because a failed bake means a stale page
([CIR-BAKE-STALE-SELF](data-json.md)) and a stale page is the thing this product exists to
prevent.

## CIR-ADAPT-MANUAL — hand-set light <a id="cir-adapt-manual"></a>

| description | inputs | expected |
|---|---|---|
| manual returns the declared light | `manual: green` | 🟢, no data date |
| manual has no data date | any manual item | detail line carries no "last data" segment |
| manual is always available | any phase | implemented from P0 ([CIR-PROC-PHASE-P0](../process/phases.md)) |

Manual is honest about being manual: it says what the person asserted, not when they asserted
it. If a manual light should age, that is a freshness adapter over the config file itself — a
possible contributed built-in, not a hidden behaviour of `manual:`.

## CIR-ADAPT-FRESHNESS — dates in files <a id="cir-adapt-freshness"></a>

Behaviour is [freshness.md](freshness.md). Interface-level obligations only:

| description | inputs | expected |
|---|---|---|
| freshness reads, never executes | source matching an executable script | read as text |
| freshness reports its data date | newest date 2026-08-01 | `data_date: 2026-08-01` in the detail line |
| freshness is sandboxed to the config dir | any `source:` | [CIR-DATA-SOURCE-PATH](freshness.md) |

## CIR-ADAPT-COMMAND — the escape hatch <a id="cir-adapt-command"></a>

`command:` is an **argv array**, never a shell string: a shell string invites quoting bugs and
makes every value in the config a potential injection point.

| description | inputs | expected |
|---|---|---|
| argv array is required | `command: "./x.sh --flag"` (string) | config error naming the array form |
| argv is not shell-interpreted | `command: ["./x.sh", "a b"]` | one argument `a b`; no glob or `$VAR` expansion |
| working directory is the config dir | `["./notes/plants-status.sh"]` | resolved and run under `<config-dir>` |
| the executable must exist at validation | argv[0] missing | config error (caught before publishing, not at 03:00) |
| the executable must be executable at validation | argv[0] without the exec bit | config error naming the file |
| stdout is trimmed and case-folded | `" GREEN\n"` | 🟢 |
| only the first line of stdout is read | `"green\ndebug output"` | 🟢; the rest is ignored |
| unknown word is a failure | `amber` | ⚪ + warning naming the word |
| empty stdout is a failure | `""`, exit 0 | ⚪ + warning |
| non-zero exit is a failure | exit 1 with `green` on stdout | ⚪ + warning — the exit code wins |
| stderr goes to the warning, not the page | command writes a stack trace to stderr | warning is a bounded, sanitised summary ([CIR-BAKE-EXPOSURE](data-json.md)) |
| the command cannot set a data date | any command | no "last data" segment (see ⚖ CIR-Q-13) |

⚖ **CIR-Q-13 — should `command:` be able to return more than a word?** A wearable-API script
knows the date of the reading and often a one-line summary, and the current contract throws both
away. Options: (a) first-line status word only (encoded — the simplest thing a shell script can
emit); (b) a status word plus optional `key=value` lines (`date=2026-08-01`, `note=…`);
(c) full JSON on stdout. *Recommendation: (a) now, (b) as the compatible extension* — (b) is a
superset of (a) and needs no config change, whereas (c) makes the escape hatch stop being a
one-line shell script.

## CIR-ADAPT-BUDGET — time and blast radius <a id="cir-adapt-budget"></a>

| description | inputs | expected |
|---|---|---|
| a command has a per-item timeout | command sleeps past the timeout | killed; ⚪ + warning naming the timeout |
| a killed command's children are killed | command spawns a child that outlives it | process group terminated |
| the bake has a total budget | many slow adapters | bake ends within its budget; unresolved items are ⚪ + warning |
| the environment is not inherited wholesale | bake env contains a token | the command receives a minimal, explicit environment |
| the bake exits non-zero only for config errors | some adapters failed, none was a config error | exit 0; page published with warnings |

The environment row is a public-repo consequence: whatever the bake job holds (a registry token,
a kubeconfig) must not be handed to a person's arbitrary status script by default.

⚖ **CIR-Q-14 — per-item timeout and total bake budget values.** Unruled. A 5 s per-item timeout
and a 5 min total are a sane starting point for a nightly job; a `timeout:` per command item is
the obvious escape for a slow API. *Recommendation: fixed defaults now (5 s / 5 min), a per-item
`timeout:` key only when something real needs it.*

⚖ **CIR-Q-15 — how do contributed built-ins actually plug in?** Options: (a) in-process
entry-points in this repo's bake package (typed, testable, but every adapter is a merge into
this repo); (b) a subprocess protocol — the built-in is a program the bake invokes, i.e.
`command:` with a registry of shipped programs; (c) both, with (b) as the public interface and
(a) as the private one. *Recommendation: (a) for anything shipped in this repo, and treat
`command:` as the entire third-party story* — it already absorbs every weird source, needs no
plugin loader, and keeps arbitrary third-party code out of the bake process. Under (b) the
adapter registry, its discovery order, and its versioning all become spec surface that does not
exist today.
