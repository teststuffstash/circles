# circles.yaml — schema stub (seed)

**Status: STUB.** The authoritative schema emerges from the spec fan-out; this page fixes the
shape the product intent already decided so every draft starts from the same skeleton. The key
example is the fixture person: [`fixtures/alex/circles.yaml`](../../fixtures/alex/circles.yaml)
— spec rows and that file are the same doctrine (decision tables, synthetic only).

## Shape (v0)

```yaml
person: <display name>            # whose circles this is
rings:                            # inside-out order; index 0 = innermost
  - id: <slug>                    # stable id, referenced by items and tests
    label: <display label>
    items:
      - id: <slug>
        label: <display label>
        guardrail: <text>         # optional; shown on hover, never computed
        link: <url-or-path>       # optional; click-through target
        share: <number>           # optional arc weight within the ring (default: equal)
        status:                   # exactly one adapter, or absent → ⚪ unmonitored
          manual: green|yellow|red
          # OR
          freshness:
            source: <path>        # file/glob whose newest dated entry is read
            yellow_after: <days>
            red_after: <days>
          # OR
          command: <argv>         # prints green|yellow|red on stdout; exit≠0 → ⚪ + warning
```

## Status resolution — key rows (CIR-DATA-STATUS-RESOLUTION)

| description | inputs | expected |
|---|---|---|
| no adapter declared | item without `status:` | ⚪ unmonitored |
| manual green | `manual: green` | 🟢 |
| freshness inside window | newest date 3d old, yellow_after 7, red_after 30 | 🟢 |
| freshness stale | newest date 10d old, yellow_after 7, red_after 30 | 🟡 |
| freshness very stale | newest date 45d old, yellow_after 7, red_after 30 | 🔴 |
| freshness source missing | `source:` matches no file | ⚪ + build warning |
| command failure is not red | `command:` exits non-zero | ⚪ + build warning (never 🔴 — red means "act", not "broken tooling") |

⚖ Open (for the fan-out): timezone/DST anchoring of "days old", date formats recognized in
sources, whether `share` weights must sum per-ring, sibling half-arc ordering.
