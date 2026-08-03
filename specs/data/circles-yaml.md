# circles.yaml — schema, status resolution, validation

The authoritative schema for a person's configuration. The key example is the fixture person:
[`fixtures/alex/circles.yaml`](../../fixtures/alex/circles.yaml) — spec rows and that file are
the same doctrine (decision tables, synthetic only). Nothing person-specific may live in code;
everything custom is config/data.

## Shape (v0)

```yaml
person: <display name>            # whose circles this is
timezone: <IANA tz>               # OPTIONAL; freshness "days old" anchor (default UTC) — CIR-DATA-FRESHNESS-TIMEZONE
rings:                            # inside-out order; index 0 = innermost
  - id: <slug>                    # stable id, referenced by items and tests
    label: <display label>
    items:
      - id: <slug>                # unique across the WHOLE config (CIR-DATA-ITEM-UNIQUENESS)
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

## Requirements

### CIR-DATA-SCHEMA — config shape
`circles.yaml` is a single YAML document with exactly one `person` (string), an optional
`timezone` (IANA name), and a non-empty `rings` list. Each ring has a unique `id` (slug) and a
`label`; each ring has an `items` list. Each item has a unique `id`, a `label`, and optional
`guardrail`, `link`, `share`, and `status`. Phase: P0.

### CIR-DATA-STATUS-RESOLUTION — status resolution
Every item resolves to exactly one status: 🟢 ok · 🟡 attention · 🔴 act · ⚪ unmonitored. An
item with no `status:` is ⚪. An item with exactly one adapter resolves per that adapter's
rules. An item with more than one adapter is a config error (CIR-DATA-VALIDATION). Phase: P0.

| description | inputs | expected |
|---|---|---|
| no adapter declared | item without `status:` | ⚪ unmonitored |
| manual green | `manual: green` | 🟢 |
| manual yellow | `manual: yellow` | 🟡 |
| manual red | `manual: red` | 🔴 |
| freshness inside window | newest date 3d old, yellow_after 7, red_after 30 | 🟢 |
| freshness stale | newest date 10d old, yellow_after 7, red_after 30 | 🟡 |
| freshness very stale | newest date 45d old, yellow_after 7, red_after 30 | 🔴 |
| freshness source missing | `source:` matches no file | ⚪ + build warning |
| command failure is not red | `command:` exits non-zero | ⚪ + build warning (never 🔴 — red means "act", not "broken tooling") |
| command prints yellow | `command:` prints `yellow` | 🟡 |
| command prints garbage | `command:` prints `maybe` | ⚪ + build warning |

### CIR-DATA-UNMONITORED — grey is honest and visible
⚪ is a first-class status, never a hidden default. An item with no adapter renders as
visibly-grey unmonitored (see [CIR-RENDER-COLOR-UNMONITORED](../render/color.md)); it is never
silently promoted to 🟢. Phase: P0.

### CIR-DATA-TOOLING-FAILURE — tooling failure is never red
Any adapter error or missing source resolves to ⚪ + a build warning, never 🔴. Red is reserved
for "act on your life". Phase: P0.

### CIR-DATA-ADAPTER-MANUAL — manual adapter
`manual:` accepts exactly one of `green|yellow|red`. Any other value is a config error
(CIR-DATA-VALIDATION). Phase: P0.

### CIR-DATA-ADAPTER-FRESHNESS — freshness adapter
`freshness:` declares a `source` (file or glob), `yellow_after` (days), and `red_after` (days).
Resolution semantics live in [freshness.md](freshness.md). Phase: P1 (bake); P0 hand-set only.

### CIR-DATA-ADAPTER-COMMAND — command adapter
`command:` is an argv list. The bake runs it; the status is read from stdout per
[CIR-DATA-COMMAND-OUTPUT](../data/circles-yaml.md#cir-data-command-output). A non-zero exit
code is a tooling failure → ⚪ + warning. Phase: P1.

### CIR-DATA-COMMAND-OUTPUT — command output parsing
The status is the first non-empty line of stdout, trimmed and lowercased. It must be one of
`green|yellow|red`; anything else (including empty output) is ⚪ + a build warning. Phase: P1.

| description | inputs | expected |
|---|---|---|
| command prints padded yellow | stdout `"  yellow\n"` | 🟡 (trimmed) |
| command prints uppercase | stdout `"RED\n"` | 🔴 (lowercased) |
| command prints multi-line | stdout `"green\n# note\n"` | 🟢 (first non-empty line) |
| command prints unknown token | stdout `"maybe\n"` | ⚪ + build warning |
| command prints nothing | stdout empty | ⚪ + build warning |

### CIR-DATA-ADAPTER-INTERFACE — contributed adapters plug in
The adapter interface is a stable contract: an adapter takes an item's config block and the
bake context (source files, "today" anchor) and returns a status + optional detail line. A
contributed built-in (sqlite query, Prometheus query, HTTP/REST to-do state) implements this
interface without touching the page or the render pipeline. Phase: P2 (interface fixed in P1).

### CIR-DATA-VALIDATION — config errors fail the build
A malformed config is a build error (the bake/validate step fails loudly), not a silent ⚪.
This includes: duplicate ring ids, duplicate item ids, an item with more than one adapter, an
unknown `manual:` value, `yellow_after >= red_after`, negative thresholds, and a `share` that
is not a positive number. Phase: P0 (schema), P1 (bake).

| description | inputs | expected |
|---|---|---|
| duplicate ring id | two rings `id: self` | build error |
| duplicate item id | two items `id: sleep` in different rings | build error |
| two adapters on one item | `manual:` and `freshness:` both present | build error |
| unknown manual value | `manual: blue` | build error |
| inverted freshness thresholds | yellow_after 30, red_after 7 | build error |
| negative threshold | red_after -1 | build error |
| non-positive share | `share: 0` | build error |

### CIR-DATA-ITEM-UNIQUENESS — one ring per item
An item id is unique across the whole config and an item belongs to exactly one ring (its
parent). Cross-ring membership is not supported in v0 — see ⚖ below and the PR Follow-ups.
Phase: P0.

### CIR-DATA-SHARE-WEIGHTS — arc weights
`share` is an optional positive number giving an item's arc weight within its ring. Items
without `share` split the remaining weight equally. See ⚖ below for normalization. Phase: P0.

### CIR-DATA-SIBLING-ORDER — sibling arc order
Within a ring, sibling arcs are laid out in config declaration order (stable, author-controlled).
Phase: P0.

## ⚖ AMBIGUITY entries

### ⚖ DATA-1 — timezone/DST anchoring of "days old"
The goal says freshness judges "the newest date … younger than N days" but never says which
clock "today" is anchored to. A nightly bake runs in some host timezone; the person lives in
another; DST transitions make "N days ago" ambiguous (a 23-hour or 25-hour day).
- Options: (a) UTC always; (b) a per-config `timezone` field (default UTC); (c) the bake host's
  local timezone.
- **Recommendation: (b)** — a configurable `timezone` (IANA) defaulting to UTC, and "days old"
  is the calendar-day difference between the newest date and "today" in that timezone. This
  keeps the bake deterministic across hosts and lets a person anchor to their own life.
  Specified as [CIR-DATA-FRESHNESS-TIMEZONE](freshness.md).

### ⚖ DATA-2 — date formats recognized in freshness sources
The goal says "the newest date found in a source file/glob" but not which date formats count.
The fixture uses markdown list items `- YYYY-MM-DD — text`.
- Options: (a) ISO-8601 `YYYY-MM-DD` only, in markdown list items; (b) ISO plus common variants
  (`YYYY/MM/DD`, `DD Mon YYYY`); (c) a per-source configurable format.
- **Recommendation: (a)** — recognize ISO-8601 `YYYY-MM-DD` anywhere in a line, matching the
  fixture doctrine; extend formats later behind the adapter interface. Specified as
  [CIR-DATA-FRESHNESS-DATE-PARSING](freshness.md).

### ⚖ DATA-3 — share normalization
The goal gives `share: 0.5` twice as "two half-arcs" but never says whether shares must sum to
1 per ring, or what happens with mixed share/no-share items.
- Options: (a) require shares to sum to 1 per ring (build error otherwise); (b) treat shares as
  relative weights, normalize per ring, and give no-share items the equal remainder.
- **Recommendation: (b)** — relative weights normalized per ring; no-share items split the
  remainder equally. More forgiving, and the two-children `0.5/0.5` example still yields two
  half-arcs. Specified as [CIR-DATA-SHARE-WEIGHTS](#cir-data-share-weights).

### ⚖ DATA-4 — sibling ordering
The goal does not say how sibling arcs are ordered within a ring.
- Options: (a) config declaration order; (b) alphabetical by label; (c) by share descending.
- **Recommendation: (a)** — declaration order is stable and author-controlled. Specified as
  [CIR-DATA-SIBLING-ORDER](#cir-data-sibling-order).

### ⚖ DATA-5 — item in several rings
The goal explicitly lists "items that belong to several rings" as an edge to hunt, but the
schema nests items under exactly one ring.
- Options: (a) disallow — an item belongs to exactly one ring (unique id); (b) allow an item id
  to be referenced from multiple rings (shared status).
- **Recommendation: (a)** for v0 — one ring per item, unique ids. Cross-ring membership is a
  real product question (e.g. "sleep" touching both Self and Health) and is flagged as a PR
  Follow-up for the operator. Specified as [CIR-DATA-ITEM-UNIQUENESS](#cir-data-item-uniqueness).

### ⚖ DATA-6 — command output parsing
The goal says the command "prints the status" but not how to parse it (whitespace, case,
multiple lines, unknown tokens).
- Options: (a) first non-empty line, trimmed, lowercased, must be green|yellow|red; (b) whole
  stdout must be exactly one token; (c) accept any line containing a token.
- **Recommendation: (a)** — forgiving on whitespace/case, strict on the token set, unknown →
  ⚪ + warning. Specified as [CIR-DATA-COMMAND-OUTPUT](#cir-data-command-output).

### ⚖ DATA-7 — future-dated entries in a freshness source
A source may contain a date in the future (clock skew, a typo, a scheduled entry).
- Options: (a) treat as fresh (age 0) and emit a build warning; (b) treat as a tooling failure
  → ⚪ + warning; (c) ignore future dates and use the newest non-future date.
- **Recommendation: (a)** — a future date is almost certainly a data anomaly, so warn, but the
  item is genuinely "recent" and should not go red. Specified as
  [CIR-DATA-FRESHNESS-FUTURE-DATE](freshness.md).

### ⚖ DATA-8 — empty rings / empty config
The goal does not say what renders when a ring has no items, or when the config has no rings.
- Options: (a) omit empty rings; empty config renders a single "no data" state; (b) render an
  empty band for every declared ring.
- **Recommendation: (a)** — an empty ring carries no triage signal and an empty band wastes the
  one-screen budget. Specified as [CIR-RENDER-EMPTY-STATE](../render/geometry.md).
