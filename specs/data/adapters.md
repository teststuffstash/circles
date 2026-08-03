# Adapter taxonomy

**CIR-DATA-ADAPTERS** — The interface for how an item's status is sourced.

## Available adapters

| adapter | key in `status:` | description | phase |
|---|---|---|---|
| `manual:` | `manual: green\|yellow\|red` | Hand-set by the person | P0 |
| `freshness:` | `freshness: {source, yellow_after, red_after}` | Date-age-based from source files | P1 |
| `command:` | `command: [<argv>]` | User-supplied script prints status to stdout | P1 |
| sqlite (future) | `sqlite: {path, query}` | Query a SQLite database | P2 |
| prometheus (future) | `prometheus: {url, query}` | PromQL query | P2+ |
| http (future) | `http: {url, json_path}` | HTTP GET + JSON extraction | P2+ |

## Adapter interface contract

**CIR-DATA-ADAPTER-INTERFACE** — Every adapter MUST resolve to exactly one of the four status colors: 🟢, 🟡, 🔴, or ⚪. The interface for a contributed built-in adapter is:

1. **Input:** adapter-specific configuration (from `circles.yaml`) + repo root path (for relative file resolution).
2. **Output:** one status color + optional detail string (for hover).
3. **Failure mode:** any error (missing source, timeout, invalid output) → ⚪ unmonitored + build warning. NEVER 🔴.

### Adapter failure decision table

| description | inputs | expected |
|---|---|---|
| adapter source is missing | freshness source glob matches nothing | ⚪ + build warning |
| adapter source is empty | freshness source file has no dates | ⚪ + build warning |
| adapter command exits non-zero | command: exit code ≠ 0 | ⚪ + build warning |
| adapter command times out | command exceeds timeout | ⚪ + build warning |
| adapter command prints garbage | command stdout not green/yellow/red | ⚪ + build warning |
| adapter throws exception | any unhandled exception | ⚪ + build warning |
| network unreachable (future http/prometheus) | connection refused | ⚪ + build warning |

**Key invariant:** `🔴` means "act on your life", never "tooling is broken". A tooling failure is always ⚪ + warning.

## Configuration rules

- An item's `status:` block contains **exactly one** adapter key. Multiple keys → validation error.
- An item with no `status:` block → ⚪ unmonitored (the default is honest grey).
- Adapter configuration values are validated at parse time:
  - `freshness:` requires `source` (string), `yellow_after` (positive int), `red_after` (positive int > yellow_after).
  - `command:` requires a non-empty array.
  - `manual:` requires one of `green`, `yellow`, `red`.

## Future extensibility

**CIR-DATA-ADAPTER-CONTRIBUTION** — New adapters (sqlite, prometheus, http) MUST:
1. Implement the same resolve-to-color contract.
2. Use the same failure mode (⚪ + warning).
3. Not require changes to the page renderer or data.json schema.
4. Be registered as a new key alongside the existing three.

⚖ **AMBIGUITY: Adapter timeout for command:.** The goal issue specifies `command:` as a user-supplied script but does not define a timeout. Options: (a) hardcoded 10 seconds; (b) configurable per-adapter with a default; (c) configurable globally in circles.yaml. **Recommendation:** Configurable per-adapter with 30-second default. Rationale: some scripts (wearable API calls) may legitimately take longer, but runaway processes must not block the bake.

⚖ **AMBIGUITY: Command working directory.** When a `command:` adapter runs, what is its working directory? Options: (a) repo root; (b) the directory containing circles.yaml; (c) left to the OS default. **Recommendation:** Repo root. Rationale: consistent with how `freshness:` resolves `source:` paths, and the fixture's `./notes/plants-status.sh` path assumes repo-relative resolution.

## Fixture examples

| item | adapter | exercises |
|---|---|---|
| `sleep` | `freshness:` | date-age freshness from file |
| `labs` | `freshness:` | very stale → 🔴 |
| `exercise` | (none) | ⚪ unmonitored |
| `date-night` | `manual: yellow` | hand-set P0 mode |
| `nova` | `manual: green` | hand-set P0 mode |
| `kit` | `manual: green` | hand-set P0 mode |
| `friends` | `manual: red` | hand-set P0 mode |
| `plants` | `command:` | script-based light |

**Gap:** No fixture item exercises `freshness:` in the 🟡 attention range (between yellow_after and red_after). The spec recommends adding one (`hydration` item, see `freshness.md`).