# circles.yaml — the person's configuration (CIR-DATA-SCHEMA-*)

`circles.yaml` is the whole product surface a person (or their trusted editor) ever writes:
rings, items, labels, guardrails, links, adapters. **Nothing person-specific may live in
code** — everything custom is this file plus the data files it points at. The key example is
the fixture person: [`fixtures/alex/circles.yaml`](../../fixtures/alex/circles.yaml) — spec
rows and that file are the same doctrine (synthetic only; this repo is public).

Status resolution semantics live in [status-resolution.md](status-resolution.md); the
`freshness:` adapter in [freshness.md](freshness.md); the adapter contract in
[adapters.md](adapters.md).

## Shape (v0)

```yaml
person: <display name>            # whose circles this is (required)
timezone: <IANA name>             # optional, default "UTC" — anchors freshness math
                                  # (see ⚖ AMBIGUITY: FRESHNESS-TIMEZONE in freshness.md)
rings:                            # required, ≥1; inside-out order, index 0 = innermost
  - id: <slug>                    # stable id, referenced by tests and warnings
    label: <display label>        # required, opaque Unicode text (may carry glyphs: "① Self")
    items:                        # required, ≥1 (see ⚖ AMBIGUITY: EMPTY-RING)
      - id: <slug>                # unique within its ring
        label: <display label>    # required
        guardrail: <text>         # optional; shown on hover, never computed
        link: <url-or-path>       # optional; click-through target (CIR-DATA-SCHEMA-LINK)
        share: <number>           # optional relative arc weight, > 0, default 1
        status:                   # optional; exactly one adapter key, or absent → ⚪ unmonitored
          manual: green|yellow|red
          # OR
          freshness:
            source: <path-or-glob>   # relative to the directory containing circles.yaml
            yellow_after: <days>     # integer ≥ 1
            red_after: <days>        # integer > yellow_after
          # OR
          command: <argv>            # string array, ≥1 element; prints green|yellow|red
```

## CIR-DATA-SCHEMA-TOPLEVEL — top-level shape

| row (test id) | inputs | expected |
|---|---|---|
| minimal-valid-config | `person` + one ring with one item, no `status:` | valid; item renders ⚪ |
| person-missing | no `person:` key | validation error, bake fails |
| rings-empty | `rings: []` | validation error, bake fails |
| rings-order-is-inside-out | rings `[self, partner, children, wider]` | `self` is the innermost ring; array order is the geometry order (CIR-RENDER-GEOM-RING-ORDER) |
| timezone-omitted | no `timezone:` key | freshness math anchors to UTC dates |
| timezone-valid | `timezone: Europe/Tallinn` | freshness math anchors to that zone's calendar date |

## CIR-DATA-SCHEMA-RING — ring fields

| row (test id) | inputs | expected |
|---|---|---|
| ring-id-slug | `id: self` | accepted (slug: `[a-z0-9][a-z0-9-]*`) |
| ring-id-not-slug | `id: "My Ring!"` | validation error, bake fails |
| ring-id-duplicate | two rings with `id: self` | validation error, bake fails |
| ring-label-missing | ring without `label:` | validation error, bake fails |
| ring-label-glyphs | `label: "③ Children"` | accepted; labels are opaque Unicode, glyphs pass through untouched |

## CIR-DATA-SCHEMA-ITEM — item fields

| row (test id) | inputs | expected |
|---|---|---|
| item-minimal | `id` + `label` only | valid; ⚪ unmonitored, no guardrail/link, share 1 |
| item-id-duplicate-in-ring | two `id: sleep` in one ring | validation error, bake fails |
| item-id-reused-across-rings | `id: exercise` in rings `self` and `wider` | valid; two independent cells — see CIR-DATA-SCHEMA-CELL-IDENTITY |
| guardrail-absent | no `guardrail:` | detail line omits the guardrail segment, no placeholder text |
| share-default | no `share:` | weight 1 (CIR-DATA-SHARE-WEIGHT) |

## CIR-DATA-SCHEMA-CELL-IDENTITY — cell identity and cross-ring concerns

A cell's global identity is the `(ring id, item id)` pair; item ids are unique **within
their ring** only. The same concern appearing in several rings (e.g. "exercise" under both
`self` and `wider`) is expressed as separate item entries with their own adapters and
statuses; the model defines **no linkage, mirroring, or propagation** between them — each
renders as an independent cell.

| row (test id) | inputs | expected |
|---|---|---|
| same-concern-two-rings | `exercise` item in `self` (manual green) and in `wider` (no adapter) | two cells: 🟢 in ring `self`, ⚪ in ring `wider`; no cross-effect |

## CIR-DATA-SCHEMA-EXACTLY-ONE-ADAPTER — the status map

| row (test id) | inputs | expected |
|---|---|---|
| status-absent | item without `status:` | ⚪ unmonitored (honest grey, CIR-DATA-STATUS-RESOLUTION) |
| status-two-adapters | `status:` with both `manual:` and `freshness:` | validation error, bake fails |
| status-unknown-adapter | `status: {sqlite: …}` on a v0 bake | validation error, bake fails (v0 adapter set is closed: `manual`, `freshness`, `command`) |
| manual-invalid-word | `manual: blue` | validation error, bake fails |

## CIR-DATA-SCHEMA-LINK — click-through targets

`link:` accepts an absolute `https://` (or `http://`) URL, or a root-relative path
(`/…`). Everything else — including `javascript:`, `data:`, and scheme-relative `//…` — is a
validation error. Rationale: configs are trusted input, but the page is static HTML and a
typo'd scheme must fail loudly at bake time, not silently at click time.

| row (test id) | inputs | expected |
|---|---|---|
| link-https | `link: https://example.test/labs` | accepted |
| link-root-relative | `link: /details/self-sleep.html` | accepted |
| link-javascript-scheme | `link: javascript:alert(1)` | validation error, bake fails |
| link-bare-relative | `link: details/sleep.html` | validation error, bake fails (ambiguity between page-relative and source-relative is rejected) |

## CIR-DATA-SHARE-WEIGHT — arc weights

`share` is a **relative** weight: an item's arc angle is `360° × share ÷ (sum of the ring's
shares)`. Absent `share` means weight 1. Shares are per-ring; there is no cross-ring
constraint. See geometry application in [../render/sunburst.md](../render/sunburst.md)
(CIR-RENDER-GEOM-ARC-SHARE).

| row (test id) | inputs | expected |
|---|---|---|
| shares-equal-halves | two siblings, `share: 0.5` each | two 180° half-arcs (the fixture's Nova/Kit case) |
| shares-absent-equal | three siblings, no `share:` | three 120° arcs |
| shares-mixed | `nova: share 2`, `kit:` no share (weight 1) | arcs 240° / 120° |
| share-zero | `share: 0` | validation error, bake fails |
| share-negative | `share: -1` | validation error, bake fails |

**⚖ AMBIGUITY: SHARE-WEIGHT-SEMANTICS** — the goal issue leaves open "whether `share`
weights must sum per-ring". Options: (a) shares must sum to 1.0 per ring, else validation
error; (b) shares are relative weights normalized per ring (missing = 1); (c) items with
`share` take that absolute fraction, the remainder splits equally among shareless items.
**Recommendation: (b)** — it makes every fixture row correct without edits (0.5/0.5 ⇒ halves,
absent ⇒ equal thirds), needs no awkward `0.3333` values, and gives a clean answer for mixed
rings (2 + absent ⇒ ⅔/⅓). (a) is brittle under edits; (c) has surprising non-linear effects
when a share exceeds the remaining fraction.

## CIR-DATA-SCHEMA-VALIDATION — fail vs warn

**Shape errors fail the bake; build warnings never do** (warnings ride with ⚪ — see
[status-resolution.md](status-resolution.md)). A failed bake publishes nothing: the last good
`data.json` stays live (CIR-DATA-DATAJSON-ATOMIC-WRITE). Validation is whole-config: one bad
item fails the bake, no partial renders.

| row (test id) | inputs | expected |
|---|---|---|
| one-bad-item-fails-bake | 8 valid items + 1 with `manual: blue` | bake fails, last good `data.json` retained |
| unknown-toplevel-key | `circles.yaml` with `sprinkles: true` | key ignored, build warning, bake proceeds (see ⚖ UNKNOWN-KEYS) |
| unknown-item-key | item with `prioritiy: high` (typo) | key ignored, build warning, bake proceeds |

**⚖ AMBIGUITY: UNKNOWN-KEYS** — how to treat unknown keys. Options: (a) any unknown key
fails validation; (b) unknown keys are ignored with a build warning; (c) silently ignored.
**Recommendation: (b)** for non-`status` keys — forward-compatible (a newer config on an
older bake degrades to warnings, not death) while typos still surface in the warnings list.
Unknown **`status:` adapter keys are the exception and fail** (CIR-DATA-SCHEMA-EXACTLY-ONE-ADAPTER):
an unrecognized adapter silently rendering ⚪ would hide a completely unmonitored item
behind an honest-looking grey.

**⚖ AMBIGUITY: EMPTY-RING** — a ring with `items: []` (or a config with zero rings).
Options: (a) validation error; (b) ring renders as an empty grey band; (c) ring skipped
silently. **Recommendation: (a)** — an empty ring is almost certainly a half-written config,
and a visible-but-meaningless band (b) violates the honest-grey doctrine (grey is a status,
not padding). A person mid-authoring comments the ring out instead.

## Proposed fixture rows (for the builder to land — not landed by this spec pass)

- a `wider`-ring sibling pair exercising `shares-mixed` (`share: 2` + absent → 240°/120°);
- an item with `link: https://example.test/…` exercising `link-https` and the click table
  in [../render/interactions.md](../render/interactions.md);
- an item with a deliberate unknown item key exercising `unknown-item-key`.
