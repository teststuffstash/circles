# The freshness adapter (CIR-DATA-FRESHNESS-*)

`freshness:` judges the **newest date found in a source** against two thresholds
(`yellow_after` / `red_after` days). It exists so any git repo of dated notes — a sleep log,
a labs file, a journal — becomes a status with zero code. The fixture examples:
[`fixtures/alex/notes/sleep-log.md`](../../fixtures/alex/notes/sleep-log.md) (inside window)
and [`fixtures/alex/notes/labs.md`](../../fixtures/alex/notes/labs.md) (very stale).

## CIR-DATA-FRESHNESS-SOURCE — locating the source

`source:` is a file path **or glob** resolved relative to the directory containing
`circles.yaml`. For a glob, the adapter reads **all** matched files and takes the newest
date across the union. Sources outside the config tree (`../…` escapes, absolute paths) are
rejected.

| row (test id) | inputs | expected |
|---|---|---|
| source-single-file | `source: notes/sleep-log.md` exists | dates read from that file |
| source-glob-union | `source: notes/lab-*.md` matches 3 files | newest date across all 3 files wins |
| source-glob-no-match | glob matches zero files | ⚪ + build warning (missing source) |
| source-path-missing | path does not exist | ⚪ + build warning (missing source) |
| source-escapes-tree | `source: ../other/file.md` or `/etc/passwd` | validation error, bake fails |

## CIR-DATA-FRESHNESS-DATE-PARSING — what counts as a date

The adapter scans the **whole file text** (no line-anchoring requirement — the fixture's
`- 2026-08-01 — 7h20m` lines match by content, not position). Recognized forms:

- ISO 8601 calendar dates `YYYY-MM-DD` (e.g. `2026-08-01`);
- ISO 8601 datetimes `YYYY-MM-DDThh:mm[:ss][Z|±hh:mm]` — the **date part** counts.

The newest recognized date in the source is the item's **last-data date**.

| row (test id) | inputs | expected |
|---|---|---|
| date-anywhere-in-line | `- 2026-08-01 — 7h20m` | 2026-08-01 recognized |
| date-datetime-form | `2026-08-01T06:30:00+03:00` | date part 2026-08-01 recognized |
| date-invalid-calendar | `2026-02-30` | not a date; ignored (a build warning if it is the only candidate — see EMPTY-SOURCE) |
| date-non-iso-form | `Aug 1, 2026` or `01/08/2026` | not recognized in v0 (see ⚖ DATE-FORMATS) |
| date-newest-wins | dates 2026-07-30, 2026-08-01, 2026-07-31 | last-data date 2026-08-01 |

**⚖ AMBIGUITY: DATE-FORMATS** — which date notations sources may use. Options: (a) ISO 8601
only; (b) ISO + a small list of common human formats (`d Mon YYYY`, …); (c) best-effort
multi-format parsing. **Recommendation: (a)** — ISO is unambiguous (no `01/08` day/month
flip), already the fixture doctrine, and a person's own notes can be normalized with one
search-replace. Multi-format parsing (b/c) silently guesses wrong on ambiguous strings —
worse than not recognizing them. If real configs later demand a format, add it explicitly to
this list (new requirement ID), never via heuristics.

## CIR-DATA-FRESHNESS-AGE — computing "days old"

`age_days = today − last_data_date`, in **whole calendar days** — there are no timestamps,
no sub-day precision, and therefore no DST arithmetic: both operands are calendar dates.
`today` is the calendar date **at bake time** in the anchoring timezone.

**⚖ AMBIGUITY: FRESHNESS-TIMEZONE** — which clock "today" comes from. Options: (a) UTC,
always; (b) a per-config `timezone:` (IANA name), default UTC; (c) the bake runner's local
zone. **Recommendation: (b)** — "3 days since my last log entry" is a statement about the
person's days, and a nightly bake scheduled at a fixed UTC time lands on different local
dates across the year in some zones; anchoring to the person's zone keeps thresholds honest
(the person notices their own midnight, not UTC's). Whole-day granularity makes the choice
DST-immune either way — the ⚖ is only about *whose midnight*. (c) is rejected: runner-local
makes statuses depend on CI infrastructure location.

| row (test id) | inputs | expected |
|---|---|---|
| age-whole-days | today 2026-08-03, last-data 2026-08-01 | age 2 days (no time-of-day effect) |
| age-today-is-zero | last-data date == today | age 0 → 🟢 for any `yellow_after ≥ 1` |
| age-year-boundary | today 2026-01-02, last-data 2025-12-29 | age 4 days |
| age-anchored-to-config-zone | `timezone: Pacific/Kiritimati` (UTC+14), bake at UTC 20:00 | "today" is the Kiritimati date (already tomorrow in UTC) |

## CIR-DATA-FRESHNESS-WINDOW — thresholds and boundaries

An item is 🟢 while `age_days < yellow_after`, 🟡 while
`yellow_after ≤ age_days < red_after`, 🔴 once `age_days ≥ red_after`. **Boundary days
belong to the worse status** (the day the threshold is reached, the light has already
changed).

| row (test id) | inputs | expected |
|---|---|---|
| window-inside | age 6, `yellow_after: 7`, `red_after: 30` | 🟢 |
| window-at-yellow-boundary | age 7, `yellow_after: 7`, `red_after: 30` | 🟡 |
| window-mid | age 29, `yellow_after: 7`, `red_after: 30` | 🟡 |
| window-at-red-boundary | age 30, `yellow_after: 7`, `red_after: 30` | 🔴 |
| window-past-red | age 45, `yellow_after: 7`, `red_after: 30` | 🔴 (the fixture's labs case: 2026-01-15 vs a 2026-08 bake) |

## CIR-DATA-FRESHNESS-THRESHOLDS — threshold validity

`yellow_after` and `red_after` are integers in whole days with `1 ≤ yellow_after <
red_after`. Violations are validation errors (bake fails) — a config whose yellow can never
show (`red_after ≤ yellow_after`) is a typo, not a policy.

| row (test id) | inputs | expected |
|---|---|---|
| thresholds-valid | `yellow_after: 100`, `red_after: 190` | valid (the fixture's labs item) |
| thresholds-equal | `yellow_after: 7`, `red_after: 7` | validation error, bake fails |
| thresholds-inverted | `yellow_after: 30`, `red_after: 7` | validation error, bake fails |
| threshold-zero | `yellow_after: 0` | validation error, bake fails |
| threshold-fractional | `yellow_after: 3.5` | validation error, bake fails |

## CIR-DATA-FRESHNESS-EMPTY — a source with no usable dates

| row (test id) | inputs | expected |
|---|---|---|
| source-file-empty | file exists, zero bytes | ⚪ + build warning |
| source-no-parseable-dates | file exists, text contains no recognized dates | ⚪ + build warning |

**⚖ AMBIGUITY: EMPTY-SOURCE** — a source that exists but yields no dates could mean "the
person never logged anything" — arguably 🔴 ("act: start logging") rather than ⚪. Options:
(a) ⚪ + warning; (b) 🔴; (c) configurable per item. **Recommendation: (a)** — the tooling
cannot distinguish "never did the thing" from "wrong file / unrecognized format", and red
must never be a tooling guess (CIR-DATA-STATUS-TOOLING-FAILURE). The build warning carries
the signal to the person who can actually tell the difference. A person who *wants* "no log
entries ⇒ act" can express it today with `command:` (count entries, print red when zero).

## CIR-DATA-FRESHNESS-FUTURE — dates after "today"

| row (test id) | inputs | expected |
|---|---|---|
| future-date-mixed | dates 2026-08-01 and 2099-01-01, today 2026-08-03 | 2099-01-01 excluded with a build warning; last-data date 2026-08-01 |
| future-dates-only | every parseable date is in the future | ⚪ + build warning |

**⚖ AMBIGUITY: FUTURE-DATES** — a date after "today" is clock skew, a typo'd year, or a
template line. Options: (a) exclude future dates with a warning, all-future ⇒ ⚪ + warning;
(b) clamp future dates to "today" (age 0, 🟢); (c) any future date ⇒ ⚪ + warning for the
whole source. **Recommendation: (a)** — (b) converts bad data into a green light, the exact
dishonesty the failure algebra forbids; (c) punishes an otherwise readable source. Excluding
is the only option that neither invents green nor discards good data.

## Proposed fixture rows (for the builder to land — not landed by this spec pass)

- `notes/future-date.md` — one entry dated 2099-01-01 plus one recent entry (exercises
  `future-date-mixed`);
- `notes/empty-log.md` — a header, no dated lines (exercises `source-no-parseable-dates`);
- tests rewrite committed dates relative to bake "today" at runtime (fixture doctrine,
  [../process/testing.md](../process/testing.md)) — the boundary rows above must be built
  that way, not from hardcoded dates.

## Provenance

ISO 8601 forms, IANA timezone behavior, and the DST-immunity of whole-day date arithmetic
are reasoned from training knowledge — this ride has no WebSearch/WebFetch tool, so nothing
here was verified against a live source. No claim in this page depends on a specific library.
