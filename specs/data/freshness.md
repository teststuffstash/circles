# Freshness — dates, ages and the two thresholds

The `freshness:` adapter answers one question: *how old is the newest dated entry for this
item?* It is the adapter that makes any git repo of dated notes into a life-area monitor, and
it is where dangerous-green hides — an unparsed date, a future typo, or an off-by-one at the
boundary all end in a light that looks fine.

## CIR-DATA-FRESHNESS-WINDOW — the two thresholds <a id="cir-data-freshness-window"></a>

`yellow_after` and `red_after` are **whole days**, and the comparison is *strictly greater
than*: "younger than or equal to N days is still fine".

| description | inputs | expected |
|---|---|---|
| today's date is green | age 0, yellow_after 7, red_after 30 | 🟢 |
| age one below the yellow threshold | age 6, yellow_after 7 | 🟢 |
| age exactly at the yellow threshold | age 7, yellow_after 7 | 🟢 (boundary is inclusive of "still fine") |
| age one past the yellow threshold | age 8, yellow_after 7 | 🟡 |
| age exactly at the red threshold | age 30, yellow_after 7, red_after 30 | 🟡 |
| age one past the red threshold | age 31, yellow_after 7, red_after 30 | 🔴 |
| thresholds out of order | yellow_after 30, red_after 7 | config error |
| thresholds equal | yellow_after 7, red_after 7 | config error (yellow would be unreachable — a threshold no state can occupy is a typo, not a design) |
| missing red_after | only `yellow_after: 7` | config error (both are required; a one-sided window is silently half-monitored) |
| negative or fractional threshold | `yellow_after: -1`, `yellow_after: 3.5` | config error |

⚖ **CIR-Q-08 — is the threshold boundary inclusive or exclusive?** `yellow_after: 7` reads as
"yellow after 7 days", which could mean age 7 is already yellow. The table encodes *strictly
greater* (age 7 is still green). Options: (a) `age > threshold` (encoded); (b)
`age >= threshold`. *Recommendation: (a)* — "every 7 days" habits are kept *on* day 7, and a
person doing the right thing must not be shown 🟡 for it. The cost is one day of latency before
a lapse shows. Whichever way it is ruled, the three boundary rows above (6/7/8) are the tests
that pin it, and the field names should be read as "still fine up to and including N days".

## CIR-DATA-AGE-CALENDAR — age is calendar days in the config's timezone <a id="cir-data-age-calendar"></a>

Age is the number of **calendar day boundaries** between the source date and the reference date,
evaluated in the config's `timezone:` ([CIR-DATA-TIMEZONE](circles-yaml.md)). It is not
`(now - then) / 86400`, and it never consults the bake host's zone.

| description | inputs | expected |
|---|---|---|
| same calendar day is age 0 | source 2026-08-03, reference 2026-08-03 | 0 |
| yesterday is age 1 | source 2026-08-02, reference 2026-08-03 | 1 |
| age is unaffected by time of day | source date-only, bake at 00:05 or 23:55 local | same age both times |
| a DST spring-forward day still counts as one day | 23-hour local day between source and reference | age increments by 1, not 0 |
| a DST fall-back day still counts as one day | 25-hour local day | age increments by 1, not 2 |
| host timezone does not change the age | same config baked with `TZ=UTC` and `TZ=Pacific/Auckland` | identical ages |
| a date-time source is reduced to its local date | source `2026-08-02T23:30:00Z`, timezone `Pacific/Auckland` | the local date is 2026-08-03 → age 0 on a 2026-08-03 reference |

⚖ **CIR-Q-09 — which clock anchors "days old"?** Options: (a) calendar-day difference in the
config's timezone (encoded); (b) elapsed hours ÷ 24 from a timestamp; (c) the viewer's browser
timezone, recomputed client-side. (b) makes a status flip mid-afternoon and makes DST shift a
threshold by an hour — invisible and unreproducible in tests. (c) breaks
[CIR-BAKE-DETERMINISM](data-json.md) (two people looking at the same page would see different
lights) and would require the page to resolve, which it must not.
*Recommendation: (a)* — one zone, whole days, one answer per bake.

## CIR-DATA-DATE-PARSE — which date tokens count <a id="cir-data-date-parse"></a>

Sources are human notes, so parsing is deliberately narrow: **ISO-8601 dates only**,
`YYYY-MM-DD` optionally followed by a time and offset. Anything else is not a date. A narrow
parser that misses a date shows ⚪/🟡; a wide parser that misreads `03/04/2026` shows a
confident wrong 🟢.

| description | inputs | expected |
|---|---|---|
| ISO date is parsed | `- 2026-08-01 — 7h20m` | 2026-08-01 |
| ISO date-time is parsed | `2026-08-01T22:10:00+03:00` | reduced to its local date per [CIR-DATA-AGE-CALENDAR](#cir-data-age-calendar) |
| date anywhere in the line counts | `## Session on 2026-08-01 (evening)` | 2026-08-01 |
| slash formats are not dates | `03/04/2026` | ignored (ambiguous day/month) |
| written months are not dates | `1 August 2026` | ignored |
| impossible date is ignored with a warning | `2026-02-30` | ignored + warning naming the file and line |
| an ISO-looking substring of a longer token is not a date | `v2026-08-01-rc1`, `id=2026-08-013` | ignored |
| a file with no parseable date | prose with no ISO dates | ⚪ + warning (never 🟢) |
| the newest date wins | file with 2026-07-30, 2026-08-01, 2026-07-31 | 2026-08-01 |
| newest across a glob | `notes/*.md`, newest date in any matched file | the maximum over all matches |

### Future dates

| description | inputs | expected |
|---|---|---|
| a date after the reference date is ignored | source 2027-08-01, reference 2026-08-03 | ignored + warning; the newest *non-future* date is used |
| all dates in the future | only 2027 dates | ⚪ + warning (not 🟢) |
| a small forward skew is tolerated | source dated tomorrow (age -1) | treated as age 0, no warning |

A mistyped year is the single most dangerous entry a person can make in their notes: `2027-08-01`
would pin the item 🟢 for a year. Ignoring future dates converts that typo into a visible ⚪.
The one-day skew tolerance exists because a person can legitimately write tomorrow's date in a
zone ahead of the config's.

⚖ **CIR-Q-10 — narrow ISO-only parsing vs. the person's actual notes.** Real notes contain
`3 Aug`, `2026/08/01`, and filenames like `2026-08-01-labs.md`. Options: (a) ISO-only, in text
(encoded); (b) ISO in text plus ISO in the filename; (c) a configurable `date_format:` per
source. *Recommendation: (a), with (b) as the first extension* — filename dates are the common
"one file per day" journal shape, and adding them is additive and testable. (c) invites the
day/month ambiguity back in.

⚖ **CIR-Q-11 — where in a source may a date appear?** Encoded: anywhere in the text of any
matched file, newest wins. This means an unrelated ISO date in a footer ("template updated
2026-08-01") pins the item green forever. Options: (a) whole-file text scan (encoded); (b) only
lines matching a configurable marker (`- <date> — …`, the fixture's shape); (c) only the first
date of each line. *Recommendation: (a) with the shape in (b) as an opt-in `pattern:` when the
first false-green is reported* — the fixture's own `labs.md` shows why (a) is enough for notes
written by the person, and why any file the person does not fully control needs (b).

## CIR-DATA-SOURCE-PATH — where sources are read from <a id="cir-data-source-path"></a>

`source:` is a path or glob resolved **relative to the directory holding `circles.yaml`**
(the fixture's `notes/sleep-log.md` is `fixtures/alex/notes/sleep-log.md`). It may not escape
that directory.

| description | inputs | expected |
|---|---|---|
| relative path resolves under the config dir | `notes/sleep-log.md` | reads `<config-dir>/notes/sleep-log.md` |
| glob matches several files | `notes/*.md` | all matches read |
| glob matches nothing | `notes/nope/*.md` | ⚪ + warning |
| parent traversal is refused | `../../etc/hosts` | config error |
| absolute path is refused | `/etc/hosts` | config error |
| symlink out of the config dir is refused | `notes/link → /etc` | config error |
| a matched directory is skipped | glob matching a directory | skipped, no warning |
| an oversized file is refused | file above the read cap | ⚪ + warning naming the cap |
| a binary file is skipped | glob matching a `.png` | skipped + warning |

Traversal and absolute paths are config errors rather than warnings because this repo is public
and the bake runs where the person's private notes live: a `source:` that can reach outside the
config directory can quietly bake a line of `/etc/passwd` into a published detail line.

⚖ **CIR-Q-12 — is there a read cap, and what is it?** Encoded: yes, a cap exists and exceeding
it is ⚪ + warning. The value is unruled — a bake that walks a 2 GB note repo is a denial of the
nightly window, but a cap set too low silently greys a legitimately large journal. *Options: 1 MB
per file / 100 files per glob (recommended starting point), or no cap with a total bake timeout
([CIR-ADAPT-BUDGET](adapters.md)).*
