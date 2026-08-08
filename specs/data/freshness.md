# The freshness adapter

`freshness:` judges the **newest date found in a source** against two thresholds
(`yellow_after` / `red_after` days). It exists so any git repo of dated notes — a sleep log, a
labs file, a journal — becomes a status with zero code. The fixture examples:
[`fixtures/alex/notes/sleep-log.md`](../../fixtures/alex/notes/sleep-log.md) (inside window)
and [`fixtures/alex/notes/labs.md`](../../fixtures/alex/notes/labs.md) (very stale).

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-DATA-SOURCE-PATH — where sources are read from

`source:` is a path **or glob** resolved relative to the directory holding `circles.yaml` (the
fixture's `notes/sleep-log.md` is `fixtures/alex/notes/sleep-log.md`). It **may not escape that
directory**: a config is not a licence to read the bake host's filesystem. For a glob, the
adapter reads all matched files and takes the newest date across the union.

| row id | inputs | expected |
|---|---|---|
| source-single-file | `source: notes/sleep-log.md` exists | dates read from that file |
| source-glob-union | `source: notes/lab-*.md` matches 3 files | newest date across all 3 files wins |
| source-glob-no-match | glob matches zero files | ⚪ + build warning (missing source) |
| source-path-missing | path does not exist | ⚪ + build warning (missing source) |
| source-parent-traversal | `source: ../../etc/hosts` | config error, bake fails — the escape message |
| source-non-literal-parent-traversal | `source: sub/../../etc/hosts` | config error, bake fails — does not start with `..` but normalizes to an escape |
| source-absolute-path | `source: /etc/hosts` | config error, bake fails — the absolute-path message, decided syntactically before any resolution (⚖-R52) |
| source-unreadable | file exists, permission denied | ⚪ + build warning |

The two escape rows overlap — an absolute path is also outside the config directory. Per
⚖-R52 ([`CIR-DATA-IDENTITY`](circles-yaml.md)) the more specific check runs first:
absoluteness is a syntactic property tested before resolution, so each row's message is
independently triggerable.

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-DATA-SOURCE-PATH — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `source-absolute-path` | PASS | — |
| `source-non-literal-parent-traversal` | PASS | — |
| `source-parent-traversal` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-DATE-PARSE — which date tokens count

Sources are human notes, so parsing is deliberately narrow: **ISO-8601 dates only**,
`YYYY-MM-DD`, optionally followed by a time and offset. Anything else is not a date. A narrow
parser that misses a date shows ⚪ or 🟡; a wide parser that misreads `03/04/2026` shows a
confident wrong 🟢.

The adapter scans the whole file text — the fixture's `- 2026-08-01 — 7h20m` lines match by
content, not by position.

| row id | inputs | expected |
|---|---|---|
| date-iso-calendar | `2026-08-01` | recognized |
| date-anywhere-in-line | `- 2026-08-01 — 7h20m` | recognized |
| date-heading-prose | `## Session on 2026-08-01 (evening)` | recognized |
| date-datetime-form | `2026-08-01T22:10:00+03:00` | reduced to its local date per `CIR-DATA-AGE-CALENDAR` |
| date-slash-format | `03/04/2026` | ignored (day/month order is ambiguous) |
| date-written-month | `1 August 2026` | ignored |
| date-impossible-calendar | `2026-02-30` | ignored + warning naming the file |
| date-iso-substring | `v2026-08-01-rc1`, `id=2026-08-013` | ignored — an ISO-looking substring of a longer token is not a date |
| date-newest-wins | dates 2026-07-30, 2026-08-01, 2026-07-31 | last-data date 2026-08-01 |
| date-none-parseable | prose with no ISO dates | ⚪ + warning (never 🟢) |

**⚖-R27 — which date notations sources may use.** Options: (a) ISO 8601 only; (b) ISO plus a
small list of common human formats (`d Mon YYYY`, …); (c) best-effort multi-format parsing.
**Ruled: (a)** — ISO is unambiguous (no `01/08` day/month flip), it is already the fixture
doctrine, and a person's own notes can be normalized with one search-replace. (b) and (c)
silently guess wrong on ambiguous strings, which is worse than not recognizing them. If a real
config later demands a format, it is added to this list explicitly under a new requirement ID,
never via heuristics.

_Evidence: none yet — unverified._

## CIR-DATA-AGE-CALENDAR — age is calendar days in the config's timezone

Age is the number of **calendar day boundaries** between the source date and the reference
date, evaluated in the config's `timezone:`. It is not `(now − then) ÷ 86400`, and it never
consults the bake host's zone.

| row id | inputs | expected |
|---|---|---|
| age-same-day-is-zero | source 2026-08-03, reference 2026-08-03 | 0 |
| age-yesterday-is-one | source 2026-08-02, reference 2026-08-03 | 1 |
| age-ignores-time-of-day | date-only source, bake at 00:05 or 23:55 local | same age both times |
| age-dst-spring-forward | 23-hour local day between source and reference | age increments by 1, not 0 |
| age-dst-fall-back | 25-hour local day | age increments by 1, not 2 |
| age-host-zone-irrelevant | same config baked with `TZ=UTC` and `TZ=Pacific/Auckland` | identical ages |
| age-datetime-reduced-to-local-date | source `2026-08-02T23:30:00Z`, timezone `Pacific/Auckland` | local date 2026-08-03 → age 0 on a 2026-08-03 reference |
| age-year-boundary | reference 2026-01-02, source 2025-12-29 | age 4 |

**⚖-R18 — which clock anchors "days old".** Options: (a) a per-config `timezone:` (IANA name),
default UTC; (b) UTC always; (c) the bake runner's local zone; (d) the viewer's browser zone,
recomputed client-side. **Ruled: (a).** "Three days since my last log entry" is a statement
about the person's days, and a nightly bake at a fixed UTC time lands on different local dates
across the year in some zones. (c) makes statuses depend on where CI happens to run. (d) breaks
determinism — two people looking at the same page would see different lights — and requires the
page to resolve, which it must not. Whole-day granularity makes the choice DST-immune either
way; the ⚖ is only about *whose midnight*.

_Evidence: none yet — unverified._

## CIR-DATA-FRESHNESS-WINDOW — thresholds and boundaries

An item is 🟢 while `age_days ≤ yellow_after`, 🟡 while `yellow_after < age_days ≤ red_after`,
and 🔴 once `age_days > red_after`. **At exactly the threshold the item still holds its better
light**; the change happens on the day *after* the threshold.

| row id | inputs | expected |
|---|---|---|
| window-inside | age 6, `yellow_after: 7`, `red_after: 30` | 🟢 |
| window-at-yellow-boundary | age 7, `yellow_after: 7`, `red_after: 30` | 🟢 |
| window-just-past-yellow | age 8, `yellow_after: 7`, `red_after: 30` | 🟡 |
| window-mid | age 29, `yellow_after: 7`, `red_after: 30` | 🟡 |
| window-at-red-boundary | age 30, `yellow_after: 7`, `red_after: 30` | 🟡 |
| window-just-past-red | age 31, `yellow_after: 7`, `red_after: 30` | 🔴 |
| window-far-past-red | age 45, `yellow_after: 7`, `red_after: 30` | 🔴 (the fixture's labs case) |

**⚖-R6 — is age exactly `yellow_after` still 🟢?** Three of the four fan-out arms ruled `≥`
(the boundary day is already 🟡); opus alone ruled `>`. **Ruled: `>` — the boundary day keeps
the better light.** The field is named `yellow_after`, and "after 7 days" has not elapsed while
exactly 7 days have. Concretely: a person keeping an every-7-days habit, doing the thing
exactly on schedule, must not be shown 🟡 for doing it right — that trains them to distrust the
light. This is a deliberate 1-of-4 minority ruling and it is cheap to flip (three rows above,
plus the glossary entry), but it must be flipped *before* tests exist, because row ids are
evidence join keys.

<details class="evidence-block">
<summary>Evidence: 7 test case(s) — alex</summary>

**Requirement:** CIR-DATA-FRESHNESS-WINDOW — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `window-at-red-boundary` | PASS | — |
| `window-at-yellow-boundary` | PASS | — |
| `window-far-past-red` | PASS | — |
| `window-inside` | PASS | — |
| `window-just-past-red` | PASS | — |
| `window-just-past-yellow` | PASS | — |
| `window-mid` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-FRESHNESS-THRESHOLDS — threshold validity

`yellow_after` and `red_after` are integers in whole days with `1 ≤ yellow_after < red_after`.
Violations are config errors — a config whose yellow can never show is a typo, not a policy.

| row id | inputs | expected |
|---|---|---|
| thresholds-valid | `yellow_after: 100`, `red_after: 190` | valid (the fixture's labs item) |
| thresholds-equal | `yellow_after: 7`, `red_after: 7` | config error, bake fails |
| thresholds-inverted | `yellow_after: 30`, `red_after: 7` | config error, bake fails |
| threshold-zero | `yellow_after: 0` | config error, bake fails |
| threshold-fractional | `yellow_after: 3.5` | config error, bake fails |
| threshold-missing | `freshness:` with `source:` only | config error, bake fails |

<details class="evidence-block">
<summary>Evidence: 6 test case(s) — alex</summary>

**Requirement:** CIR-DATA-FRESHNESS-THRESHOLDS — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `threshold-fractional` | PASS | — |
| `threshold-missing` | PASS | — |
| `threshold-zero` | PASS | — |
| `thresholds-equal` | PASS | — |
| `thresholds-inverted` | PASS | — |
| `thresholds-valid` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-FRESHNESS-EMPTY — a source with no usable dates

| row id | inputs | expected |
|---|---|---|
| source-file-empty | file exists, zero bytes | ⚪ + build warning |
| source-no-parseable-dates | file exists, text contains no recognized dates | ⚪ + build warning |

**⚖-R31 — a source that exists but yields no dates.** It could mean "the person never logged
anything", which is arguably 🔴 ("act: start logging") rather than ⚪. Options: (a) ⚪ + warning;
(b) 🔴; (c) configurable per item. **Ruled: (a)** — the tooling cannot distinguish "never did
the thing" from "wrong file, or a format it does not recognize", and red must never be a
tooling guess (`CIR-DATA-FAILURE-IS-GREY`). The build warning carries the signal to the person
who *can* tell the difference. Someone who genuinely wants "no entries ⇒ act" can express it
today with `command:` — count the entries, print red when zero.

_Evidence: none yet — unverified._

## CIR-DATA-FRESHNESS-FUTURE — dates after the reference date

| row id | inputs | expected |
|---|---|---|
| future-date-mixed | dates 2026-08-01 and 2099-01-01, reference 2026-08-03 | 2099-01-01 excluded with a warning; last-data date 2026-08-01 |
| future-date-tomorrow | source dated one day ahead of the reference date | excluded with a warning, not treated as age 0 |
| future-dates-only | every parseable date is in the future | ⚪ + build warning |

**⚖-R8 — a date after the reference date** is clock skew, a typo'd year, or a template line.
Options: (a) exclude future dates with a warning, all-future ⇒ ⚪ + warning; (b) clamp them to
the reference date (age 0, 🟢); (c) any future date poisons the whole source ⇒ ⚪ + warning.
**Ruled: (a).** (b) converts bad data into a green light — a mistyped year would pin an item
green for a year, the exact dishonesty the failure algebra forbids. (c) punishes an otherwise
readable source. Excluding is the only option that neither invents green nor discards good
data. Note this is ruled without a skew tolerance: a single day of forward skew is harmless to
exclude (the next-newest date is almost certainly today), while a one-day tolerance is exactly
the window a typo slips through.

_Evidence: none yet — unverified._

## Proposed fixture rows (for the builder to land — not landed by this spec pass)

- `notes/future-date.md` — one entry dated 2099-01-01 plus one recent entry (exercises
  `future-date-mixed`);
- `notes/empty-log.md` — a header, no dated lines (exercises `source-no-parseable-dates`);
- tests build the boundary rows above from the reference date at runtime, never from hardcoded
  dates (fixture doctrine, [../process/testing.md](../process/testing.md)).

## Provenance

ISO 8601 forms, IANA timezone behavior, and the DST-immunity of whole-day date arithmetic are
reasoned from training knowledge — the authoring rides had no web access, so nothing here was
verified against a live source. No claim on this page depends on a specific library.
