# Freshness adapter

**CIR-DATA-FRESHNESS-WINDOW** — How the `freshness:` adapter determines status from dated source files.

## Mechanism

The freshness adapter scans source files matching a glob/path pattern, extracts dates from the content, finds the **newest** date, and compares its age against two thresholds:

- Age ≤ `yellow_after` days → 🟢 ok
- Age > `yellow_after` and ≤ `red_after` days → 🟡 attention
- Age > `red_after` days → 🔴 act

## Configuration

```yaml
status:
  freshness:
    source: <path-or-glob>     # relative to the repo root; supports glob patterns
    yellow_after: <integer>    # days after which status becomes 🟡
    red_after: <integer>       # days after which status becomes 🔴
```

**CIR-DATA-FRESHNESS-THRESHOLDS** — `red_after` MUST be strictly greater than `yellow_after`. Both MUST be positive integers. Violations are parse-time validation errors.

## Date extraction

**CIR-DATA-FRESHNESS-DATE-EXTRACTION** — The adapter scans the content of each matched file for ISO 8601 date strings (`YYYY-MM-DD` format). The newest date across all matched files is the reference date.

### Date format decision table

| description | inputs | expected |
|---|---|---|
| ISO 8601 date | `2026-08-01` | Parsed as 2026-Aug-01 |
| ISO 8601 datetime | `2026-08-01T14:30:00` | Parsed as 2026-Aug-01 (date component only) |
| ISO 8601 with timezone | `2026-08-01T14:30:00Z` | Parsed as 2026-Aug-01 (date component only) |
| US format (not supported) | `08/01/2026` | Not recognized — ignored |
| Bare year-month | `2026-08` | Not recognized — ignored |
| Date in comment | `# 2026-01-15 — panel done` | Parsed as 2026-Jan-15 |
| Multiple dates in file | lines with 2026-07-30 and 2026-08-01 | Newest: 2026-Aug-01 |
| No parseable dates | file with no YYYY-MM-DD patterns | ⚪ unmonitored + build warning |

## Glob/source resolution

**CIR-DATA-FRESHNESS-SOURCE** — The `source:` value is resolved relative to the repo root. It supports:
- A literal file path: `notes/sleep-log.md`
- A glob pattern: `notes/*.md`

### Source resolution decision table

| description | inputs | expected |
|---|---|---|
| single file exists | `source: notes/sleep-log.md`, file exists | Read and scan that file |
| glob matches multiple files | `source: notes/*.md`, matches 3 files | Scan all, use newest date across all |
| glob matches zero files | `source: nonexistent/*.md` | ⚪ unmonitored + build warning |
| file exists but is empty | `source: notes/empty.md`, file is 0 bytes | ⚪ unmonitored + build warning |
| file outside repo root | `source: ../../../etc/passwd` | ⚠ validation error — path traversal rejected |

⚖ **AMBIGUITY: Timezone anchoring for "days old".** The age calculation "how many days old is date X" depends on what "today" means. Options: (a) UTC calendar date arithmetic — simplest, deterministic, consistent across environments; (b) local timezone of the bake runner — matches the person's lived experience but varies by deploy; (c) configurable per-person timezone in circles.yaml. **Recommendation:** UTC calendar date arithmetic. Rationale: the bake job may run on any server; UTC is deterministic; the person's local timezone can be added as an optional `timezone:` field in a future iteration without breaking existing configs. This means a date that is "today" in UTC might be "yesterday" in UTC-8 — an acceptable trade-off for determinism.

⚖ **AMBIGUITY: Inclusive vs exclusive boundary.** When the age equals exactly `yellow_after` (e.g. date is exactly 7 days old and `yellow_after: 7`), is that 🟢 or 🟡? Options: (a) inclusive — age ≥ threshold triggers the warning (conservative, "at threshold = needs attention"); (b) exclusive — age > threshold triggers the warning (liberal, "exactly at threshold is still ok"). **Recommendation:** Inclusive (≥). Rationale: freshness thresholds are safety margins; being exactly at the boundary should trigger attention, not pass silently. The decision table in `status-resolution.md` reflects this: "freshness at yellow threshold" = 🟡.

## Fixture examples

| item | source | newest date | yellow_after | red_after | age (days from 2026-08-03) | expected |
|---|---|---|---|---|---|---|
| `sleep` | `notes/sleep-log.md` | 2026-08-01 | 7 | 30 | 2 | 🟢 ok |
| `labs` | `notes/labs.md` | 2026-01-15 | 100 | 190 | 201 | 🔴 act |

## Proposed fixture addition

A new fixture item exercising the 🟡 attention path should be added:

```yaml
# In the self ring, after exercise:
- id: hydration
  label: Hydration
  guardrail: "Log water intake daily"
  status:
    freshness:
      source: notes/hydration-log.md
      yellow_after: 3
      red_after: 14
```

With corresponding `notes/hydration-log.md` containing a date 5 days old (exercising the 🟡 path).
