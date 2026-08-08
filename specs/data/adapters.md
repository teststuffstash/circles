# Adapters — the interface every status source implements

The goal issue asks for contributed built-ins later (sqlite query, Prometheus query, HTTP to-do
state) that "plug in without touching the page". That only holds if the seam is written down
now, while there are three adapters, rather than discovered later from three call sites.

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-ADAPT-CONTRACT — one adapter, one answer

An adapter is a named function from *(its config block, the resolution context)* to exactly one
of: a status, or a failure. Nothing else about it reaches the rest of the system.

| the adapter receives | |
|---|---|
| its own config block | validated against **its own** schema fragment |
| the config directory | the root every path it reads is resolved under |
| the reference date + timezone | so it never reads a clock itself (`CIR-ADAPT-REFERENCE-DATE`) |
| a time budget | `CIR-ADAPT-BUDGET` |

| the adapter returns | |
|---|---|
| `status` | `green` \| `yellow` \| `red` |
| `data_date` | optional; the date the status is *about*, for the detail line |
| `note` | optional; one short plain-text phrase for the detail line |
| — or a failure | one plain-text reason; the caller turns it into ⚪ + warning |

An adapter cannot return grey, and an adapter's failure is never allowed to become another
item's problem.

| row id | inputs | expected |
|---|---|---|
| adapter-cannot-return-grey | adapter attempts to resolve ⚪ | not expressible — ⚪ comes only from absence or failure ([`CIR-DATA-GREY-REASON`](status-resolution.md)) |
| adapter-resolves-one-item | one `status:` block | exactly one status |
| adapter-never-reads-the-clock | adapter needs "today" | uses the injected reference date |
| adapter-never-writes | adapter attempts to write in the config dir | forbidden; the bake owns all output |
| adapter-unknown-name | `status: {prometheus: …}` on a build without it | config error (`CIR-DATA-SCHEMA-ADAPTER-SLOT`) |
| adapter-failure-is-isolated | one of ten adapters raises an unexpected exception | that item is ⚪ + warning; the other nine resolve normally |

The last row matters more than it looks: an unhandled exception in a contributed adapter must
not take down the bake, because a failed bake means a stale page
([`CIR-BAKE-STALE-SELF`](data-json.md)) and a stale page is the thing this product exists to
prevent.

<details class="evidence-block">
<summary>Evidence: 6 test case(s) — alex</summary>

**Requirement:** CIR-ADAPT-CONTRACT — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `adapter-cannot-return-grey` | PASS | — |
| `adapter-failure-is-isolated` | PASS | — |
| `adapter-never-reads-the-clock` | PASS | — |
| `adapter-never-writes` | PASS | — |
| `adapter-resolves-one-item` | PASS | — |
| `adapter-unknown-name` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-ADAPT-REFERENCE-DATE — one clock per bake, injected

Every adapter resolves against a single reference date, injected by the bake, so one bake never
mixes two clocks and a test can freeze it. An adapter that calls the system clock itself is a
defect: it makes the artifact non-reproducible and puts a date-dependent test beyond control.

The injection point is the bake's own invocation (a flag or argument). Production omits it and
gets today — computed in the config's `timezone:`, never the host's local zone. Fixture bakes
and tests always inject the fixture reference date (`fixtures/README.md`, ⚖-R24).

| row id | inputs | expected |
|---|---|---|
| reference-date-shared | two freshness items in one bake | both age against the same reference date |
| reference-date-injectable | test supplies a fixed reference date | ages are deterministic and reproducible |
| reference-date-crosses-midnight | bake starts 23:59:59 and runs past midnight | every item uses the reference date captured at bake start |
| reference-date-default-is-config-timezone | bake invoked with no injected date | today derived from the current instant in the config's `timezone:` — the host's local zone must not leak ([`CIR-BAKE-DETERMINISM`](data-json.md)) |
| reference-date-fixture-pinned | any bake or test over `fixtures/alex` | injected `2026-08-03`, never the running day's calendar (⚖-R24) |

<details class="evidence-block">
<summary>Evidence: 5 test case(s) — alex</summary>

**Requirement:** CIR-ADAPT-REFERENCE-DATE — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `reference-date-crosses-midnight` | PASS | — |
| `reference-date-default-is-config-timezone` | PASS | — |
| `reference-date-fixture-pinned` | PASS | — |
| `reference-date-injectable` | PASS | — |
| `reference-date-shared` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-ADAPT-MANUAL — hand-set light

Manual is honest about being manual: it says what the person asserted, not when they asserted
it. If a manual light should age, that is a freshness adapter over the config file itself — a
possible contributed built-in, never a hidden behavior of `manual:`.

| row id | inputs | expected |
|---|---|---|
| manual-returns-declared-light | `manual: green` | 🟢, no data date |
| manual-has-no-data-date | any manual item | detail line carries no "last data" segment |
| manual-available-in-every-phase | any phase | implemented from P0 ([`CIR-PROC-PHASE-P0`](../process/phases.md)) |

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-ADAPT-MANUAL — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `manual-available-in-every-phase` | PASS | — |
| `manual-has-no-data-date` | PASS | — |
| `manual-returns-declared-light` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-ADAPT-FRESHNESS — dates in files

Behavior is [freshness.md](freshness.md); interface-level obligations only here.

| row id | inputs | expected |
|---|---|---|
| freshness-reads-never-executes | `source:` matching an executable script | read as text |
| freshness-reports-its-data-date | newest date 2026-08-01 | `data_date: 2026-08-01` in the detail line |
| freshness-sandboxed-to-config-dir | any `source:` | resolved per [`CIR-DATA-SOURCE-PATH`](freshness.md) |

_Evidence: none yet — unverified._

## CIR-ADAPT-COMMAND — the escape hatch

`command:` is an **argv array, never a shell string**: a shell string invites quoting bugs and
makes every value in the config a potential injection point.

**`circles.yaml` is trusted input on par with code** — the bake executes it with the bake's own
identity. A config from an untrusted source must never be baked. This is a stated trust
boundary rather than a sandbox: the escape hatch exists precisely so a person can run their own
code, and pretending otherwise would be security theatre.

| row id | inputs | expected |
|---|---|---|
| command-argv-array-required | `command: "./x.sh --flag"` (string) | config error naming the array form |
| command-not-shell-interpreted | `command: ["./x.sh", "a b"]` | one argument `a b`; no glob or `$VAR` expansion |
| command-cwd-is-config-dir | `["./notes/plants-status.sh"]` | resolved and run under `<config-dir>` (the fixture case) |
| command-executable-exists-at-validation | argv[0] missing | config error — caught before publishing, not at 03:00 |
| command-executable-bit-at-validation | argv[0] without the exec bit | config error naming the file |
| command-prints-yellow | script prints `yellow` | 🟡 (the fixture's plants item) |
| command-stdout-trimmed-and-folded | `" GREEN\n"` | 🟢 |
| command-first-non-empty-line-wins | first line blank, second line `red` | 🔴 |
| command-extra-output-ignored | `yellow` then 40 lines of diagnostics | 🟡; diagnostics stay free |
| command-unknown-word | `amber` | ⚪ + warning naming the word |
| command-empty-stdout | `""`, exit 0 | ⚪ + warning |
| command-nonzero-exit-dominates | prints `red`, exits 1 | ⚪ + warning — the exit code wins over stdout |
| command-stderr-not-on-the-page | command writes a stack trace to stderr | warning is a bounded, sanitized summary ([`CIR-BAKE-EXPOSURE`](data-json.md)) |
| command-cannot-set-a-data-date | any command | no "last data" segment (⚖-R32) |

**⚖-R32 — should `command:` be able to return more than a word?** A wearable-API script knows
the date of the reading and often a one-line summary, and the current contract throws both
away. Options: (a) first-line status word only; (b) a status word plus optional `key=value`
lines (`date=2026-08-01`, `note=…`); (c) full JSON on stdout. **Ruled: (a) now, (b) as the
compatible extension** — (b) is a superset of (a) and needs no config change, whereas (c) makes
the escape hatch stop being a one-line shell script.

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-ADAPT-COMMAND — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `command-argv-array-required` | PASS | — |
| `command-executable-bit-at-validation` | PASS | — |
| `command-executable-exists-at-validation` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-ADAPT-BUDGET — time and blast radius

Whatever the bake job holds — a registry token, a kubeconfig — must not be handed to a person's
arbitrary status script by default.

| row id | inputs | expected |
|---|---|---|
| command-per-item-timeout | command sleeps past 30 s | killed; ⚪ + warning naming the timeout |
| command-children-killed | command spawns a child that outlives it | the process group is terminated |
| bake-total-budget | many slow adapters | the bake ends within 5 min; unresolved items are ⚪ + warning |
| environment-not-inherited-wholesale | bake env contains a token | the command receives a minimal, explicit environment |
| bake-exit-code-only-for-config-errors | some adapters failed, none was a config error | exit 0; page published with warnings |

**⚖-R21 — the per-item timeout and total bake budget.** The fan-out proposed 5 s (opus), 30 s
fixed (kimi) and 30 s configurable (mimo). **Ruled: 30 s per item, 5 min total, both fixed in
v0.** A status probe that needs more than 30 s is a data source that needs its own caching, not
a longer leash — but 5 s is too tight for a real API probe over a home connection, which is
exactly the case `command:` exists to absorb. A per-item `timeout:` key is a compatible
addition when something real needs it; adding the knob before anyone asks violates
anticipate-don't-overreach. No timeout at all is rejected outright: one wedged script must not
silence the whole page's nightly refresh.

_Evidence: none yet — unverified._

## CIR-ADAPT-NO-PAGE-LOGIC — the page is adapter-blind

Statuses, dates and warnings reach the page only as baked fields
(`CIR-DATA-RESOLUTION-TIME`). Adding the P2 sqlite metric adapter, or any contributed built-in,
is a bake-side change only — this is what "plug in without touching the page" has to mean if it
is to be testable.

| row id | inputs | expected |
|---|---|---|
| new-adapter-changes-no-page-code | a contributed adapter is added | no change under the page's source; the artifact shape is unchanged |
| page-has-no-adapter-vocabulary | any artifact | the page never branches on which adapter produced a status |

**⚖-R33 — how do contributed built-ins actually plug in?** Options: (a) in-process entry points
in this repo's bake package (typed and testable, but every adapter is a merge into this repo);
(b) a subprocess protocol — the built-in is a program the bake invokes, i.e. `command:` with a
registry of shipped programs; (c) both, with (b) public and (a) private. **Ruled: (a) for
anything shipped in this repo, and `command:` is the entire third-party story.** It already
absorbs every weird source, needs no plugin loader, and keeps arbitrary third-party code out of
the bake process. Under (b) the adapter registry, its discovery order and its versioning all
become spec surface that does not exist today.

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-ADAPT-NO-PAGE-LOGIC — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `new-adapter-changes-no-page-code` | PASS | — |
| `page-has-no-adapter-vocabulary` | PASS | — |

[View full report](../../specs-site/evidence)

</details>
