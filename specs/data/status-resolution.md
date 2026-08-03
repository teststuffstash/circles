# Status resolution

**CIR-DATA-STATUS-RESOLUTION** — How an item's traffic light is determined from its adapter declaration.

## Principle

Exactly one adapter source resolves to exactly one status color. An item without a `status:` key is ⚪ unmonitored — this is honest, visible, and intentional.

## Adapter precedence

An item's `status:` block contains **exactly one** key among `manual:`, `freshness:`, and `command:`. If the YAML contains more than one, validation MUST fail at parse time (not silently pick one).

## Resolution decision table

| description | inputs | expected |
|---|---|---|
| no adapter declared | item with no `status:` key | ⚪ unmonitored |
| manual: green | `manual: green` | 🟢 ok |
| manual: yellow | `manual: yellow` | 🟡 attention |
| manual: red | `manual: red` | 🔴 act |
| manual: invalid value | `manual: blue` | ⚠ validation error at parse time — invalid manual status |
| freshness inside window | newest date 3 days old, `yellow_after: 7`, `red_after: 30` | 🟢 ok |
| freshness at yellow threshold | newest date 7 days old, `yellow_after: 7`, `red_after: 30` | 🟡 attention |
| freshness stale | newest date 10 days old, `yellow_after: 7`, `red_after: 30` | 🟡 attention |
| freshness at red threshold | newest date 30 days old, `yellow_after: 7`, `red_after: 30` | 🔴 act |
| freshness very stale | newest date 45 days old, `yellow_after: 7`, `red_after: 30` | 🔴 act |
| freshness source missing | `source:` glob matches zero files | ⚪ unmonitored + build warning |
| freshness source empty file | source file exists but contains no parseable dates | ⚪ unmonitored + build warning |
| freshness thresholds out of order | `yellow_after: 30`, `red_after: 7` | ⚠ validation error at parse time — red_after must be > yellow_after |
| freshness thresholds equal | `yellow_after: 7`, `red_after: 7` | ⚠ validation error — red_after must be strictly > yellow_after |
| command prints green | command stdout `green\n`, exit 0 | 🟢 ok |
| command prints yellow | command stdout `yellow\n`, exit 0 | 🟡 attention |
| command prints red | command stdout `red\n`, exit 0 | 🔴 act |
| command exit non-zero | command exits 1 (any stdout) | ⚪ unmonitored + build warning (NEVER 🔴) |
| command timeout | command exceeds configured timeout | ⚪ unmonitored + build warning |
| command prints unexpected output | command stdout `blue\n`, exit 0 | ⚪ unmonitored + build warning |
| command prints with extra whitespace | command stdout `  yellow  \n`, exit 0 | 🟡 attention (stdout is trimmed) |

**Key invariant:** 🔴 means "act on your life" — it NEVER signals tooling failure. A broken adapter is ⚪ + a warning, always.

## Multiple adapters

A `status:` block with more than one key (e.g. both `manual:` and `freshness:`) is a schema error. The bake tool MUST reject the configuration at parse time with a clear error message identifying the item.

## Fixture examples

The fixture person Alex exercises each adapter path:

| item | adapter | key example |
|---|---|---|
| `sleep` | `freshness:` (source: `notes/sleep-log.md`) | freshness inside window — 🟢 |
| `labs` | `freshness:` (source: `notes/labs.md`) | freshness very stale — 🔴 |
| `exercise` | (none) | no adapter → ⚪ unmonitored |
| `date-night` | `manual: yellow` | hand-set light |
| `nova` | `manual: green` | hand-set light |
| `kit` | `manual: green` | hand-set light |
| `friends` | `manual: red` | hand-set light |
| `plants` | `command:` (`./notes/plants-status.sh`) | command adapter → 🟡 (prints "yellow") |
