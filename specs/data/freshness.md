# freshness — the `freshness:` adapter

The `freshness:` adapter resolves an item's status from the newest dated entry found in a
source file/glob, judged against two thresholds. This page owns the semantics; the schema and
the status-resolution table live in [circles-yaml.md](circles-yaml.md).

## Requirements

### CIR-DATA-FRESHNESS-WINDOW — two-threshold window
An item's age is the calendar-day difference between the newest date found in `source` and the
bake's "today" anchor (see CIR-DATA-FRESHNESS-TIMEZONE). Resolution is:
- age < `yellow_after` → 🟢
- `yellow_after` ≤ age < `red_after` → 🟡
- age ≥ `red_after` → 🔴

The lower bound of each band is inclusive, the upper bound exclusive, so a date exactly
`yellow_after` days old is 🟡 and exactly `red_after` days old is 🔴. Phase: P1.

| description | inputs | expected |
|---|---|---|
| inside window | age 3d, yellow_after 7, red_after 30 | 🟢 |
| exactly at yellow boundary | age 7d, yellow_after 7, red_after 30 | 🟡 (inclusive lower) |
| between thresholds | age 10d, yellow_after 7, red_after 30 | 🟡 |
| exactly at red boundary | age 30d, yellow_after 7, red_after 30 | 🔴 (inclusive lower) |
| past red | age 45d, yellow_after 7, red_after 30 | 🔴 |
| zero-age | age 0d (today), yellow_after 7, red_after 30 | 🟢 |

### CIR-DATA-FRESHNESS-DATE-PARSING — recognized date formats
The adapter recognizes ISO-8601 `YYYY-MM-DD` dates appearing in a source line (matching the
fixture's markdown list items, e.g. `- 2026-08-01 — 7h20m`). The newest date is the maximum
recognized date across all lines of all files matched by `source`. Phase: P1.

| description | inputs | expected |
|---|---|---|
| markdown list date | line `- 2026-08-01 — 7h20m` | date 2026-08-01 recognized |
| multiple dates, newest wins | lines dated 2026-07-30, 2026-08-01 | newest = 2026-08-01 |
| glob across files | `source: notes/*.md` with dates in two files | newest across both |
| no recognized date | file has text but no `YYYY-MM-DD` | ⚪ + build warning |

### CIR-DATA-FRESHNESS-TIMEZONE — timezone/DST anchoring
"Days old" is computed in the config's `timezone` (IANA name, default UTC). The bake's "today"
is the current date in that timezone; a date's age is the calendar-day difference there. This
makes the bake deterministic across hosts and DST transitions. Phase: P1.

| description | inputs | expected |
|---|---|---|
| default UTC | no `timezone`, newest date 2026-08-01, bake 2026-08-04 UTC | age 3d |
| explicit timezone | `timezone: America/New_York`, bake just after local midnight | age anchored to local date |
| DST spring-forward | bake on a 23-hour local day | calendar-day age, not elapsed-hours age |

### CIR-DATA-FRESHNESS-MISSING-SOURCE — missing source is tooling failure
If `source` matches no file, or matches files with no recognized date, the item is ⚪ + a build
warning — never 🔴 (CIR-DATA-TOOLING-FAILURE). Phase: P1.

### CIR-DATA-FRESHNESS-FUTURE-DATE — future dates
A recognized date later than the bake's "today" is treated as age 0 (🟢) and emits a build
warning (data anomaly). It never drives the item red. Phase: P1.

| description | inputs | expected |
|---|---|---|
| future date | newest date 2026-09-01, bake 2026-08-04 | 🟢 + build warning |
| future date with old others | newest 2026-09-01, next 2026-01-01 | 🟢 + build warning (newest wins) |

## ⚖ AMBIGUITY entries

### ⚖ FRESH-1 — what "newest date" means when formats mix
If a source mixes recognized and unrecognized date-like text, only recognized `YYYY-MM-DD`
dates count (per CIR-DATA-FRESHNESS-DATE-PARSING). This is a consequence of ⚖ DATA-2, not a
new fork; recorded here so the builder does not re-open it.

### ⚖ FRESH-2 — freshness computed at bake time, not view time
The goal's "last-data date" shown on hover could be interpreted as live (recomputed on page
load) or baked. Because the page is static over `data.json` with no server, freshness must be
computed at bake time and baked in; the page never recomputes against the viewer's clock.
- Options: (a) bake-time only (baked into `data.json`); (b) recompute on page load from the
  viewer's clock.
- **Recommendation: (a)** — deterministic, timezone-safe, and consistent with the no-server
  constraint. Specified as [CIR-RENDER-DATA-JSON](../render/interactions.md) (the
  `generated-at` stamp is the anchor).
