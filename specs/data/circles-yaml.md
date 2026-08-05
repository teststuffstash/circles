# circles.yaml — the person's configuration

`circles.yaml` is the whole product surface a person (or their trusted editor) ever writes:
rings, items, labels, guardrails, links, adapters. **Nothing person-specific may live in
code** — everything custom is this file plus the data files it points at. The key example is
the fixture person: [`fixtures/alex/circles.yaml`](../../fixtures/alex/circles.yaml) — spec
rows and that file are the same doctrine (synthetic only; this repo is public).

Status resolution semantics live in [status-resolution.md](status-resolution.md); the
`freshness:` adapter in [freshness.md](freshness.md); the adapter contract in
[adapters.md](adapters.md).

**World: alex** — every table on this page states behavior against the fixture person.

## Shape (v0)

```yaml
spec_version: 0                   # optional; absent means 0
person: <display name>            # whose circles this is (required)
timezone: <IANA name>             # optional, default "UTC" — anchors freshness math (⚖-R18)
rings:                            # required, ≥1; inside-out order, index 0 = innermost
  - id: <slug>                    # stable id, referenced by tests and warnings
    label: <display label>        # required, opaque Unicode text (may carry glyphs: "① Self")
    items:                        # required key; may be empty (⚖-R13)
      - id: <slug>                # unique within its ring
        label: <display label>    # required
        guardrail: <text>         # optional; shown on hover, never computed
        note: <text>              # optional; why this item is here, or why it is unmonitored
        link: <url-or-path>       # optional; click-through target (CIR-DATA-SCHEMA-LINK)
        share: <number>           # optional relative arc weight, > 0, default 1
        status:                   # optional; exactly one adapter key, or absent → ⚪
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

| row id | inputs | expected |
|---|---|---|
| minimal-valid-config | `person` + one ring with one item, no `status:` | valid; item renders ⚪ |
| person-missing | no `person:` key | config error, bake fails |
| rings-empty | `rings: []` | config error, bake fails (nothing to draw) |
| rings-order-is-inside-out | rings `[self, partner, children, wider]` | `self` is the innermost ring; array order is the geometry order (`CIR-RENDER-RING-ORDER`) |
| timezone-omitted | no `timezone:` key | freshness math anchors to UTC calendar dates |
| timezone-valid | `timezone: Europe/Tallinn` | freshness math anchors to that zone's calendar date |

_Evidence: none yet — unverified._

## CIR-DATA-SCHEMA-VERSION — `spec_version` guards the format

A config declaring a version **newer than the bake understands is a config error**, never a
best-effort render — a partially understood config is dangerous-green by construction.

| row id | inputs | expected |
|---|---|---|
| version-absent-defaults-zero | no `spec_version` | validates as v0 |
| version-matches | `spec_version: 0`, bake understands 0 | validates |
| version-from-the-future | `spec_version: 1`, bake understands 0 | config error: "config is newer than this build" |

**⚖-R25 — is `spec_version` per-file or per-adapter?** Contributed adapters will version
independently of the core schema. Options: (a) a single integer for the whole file;
(b) `spec_version` plus per-adapter `api:` fields. **Ruled: (a)** — one integer until a
third-party adapter exists; revisit with the first one.

_Evidence: none yet — unverified._

## CIR-DATA-SCHEMA-RING — ring fields

| row id | inputs | expected |
|---|---|---|
| ring-id-slug | `id: self` | accepted (slug: `^[a-z0-9][a-z0-9-]*$`) |
| ring-id-not-slug | `id: "My Ring!"` | config error, bake fails |
| ring-id-duplicate | two rings with `id: self` | config error, bake fails |
| ring-label-missing | ring without `label:` | config error, bake fails |
| ring-label-glyphs | `label: "③ Children"` | accepted; labels are opaque Unicode, glyphs pass through untouched |

_Evidence: none yet — unverified._

## CIR-DATA-SCHEMA-ITEM — item fields

| row id | inputs | expected |
|---|---|---|
| item-minimal | `id` + `label` only | valid; ⚪ unmonitored, no guardrail/link, share 1 |
| item-id-duplicate-in-ring | two `id: sleep` in one ring | config error, bake fails |
| guardrail-absent | no `guardrail:` | detail line omits the guardrail segment, no placeholder text |
| note-absent | no `note:` | nothing rendered; `note` never substitutes for a guardrail |
| share-default | no `share:` | weight 1 (`CIR-DATA-SHARE`) |

_Evidence: none yet — unverified._

## CIR-DATA-IDENTITY — ids, uniqueness and the item ref

Ring ids are unique in the file. Item ids are unique **within their ring**. The reference used
by the baked artifact, links, tests and warnings is the pair, written `<ring-id>/<item-id>`
(e.g. `self/sleep`) — which is why the slash is excluded from the id character set.

The same concern appearing in several rings is expressed as separate item entries with their
own adapters; the model defines **no linkage, mirroring, or propagation** between them.

| row id | inputs | expected |
|---|---|---|
| id-character-set | id matching `^[a-z0-9][a-z0-9-]*$` | valid |
| id-with-space-or-slash | `id: date night`, `id: a/b` | config error (the slash is the ref separator) |
| id-missing | item with `label:` only | config error — ids are how tests and warnings name rows |
| same-id-different-rings | `self/sleep` and `wider/sleep` | valid; two independent cells |
| same-concern-two-rings | `exercise` in `self` (manual green) and in `wider` (no adapter) | two cells: 🟢 in `self`, ⚪ in `wider`; no cross-effect |

**⚖-R17 — is an item id unique per ring or globally?** Options: (a) unique within its ring, with
the ref `<ring>/<item>`; (b) globally unique across the file. **Ruled: (a).** Three of four arms
converged here, and it decides the ref grammar every test, warning and artifact key uses — a
person should be able to have `exercise` under both *self* and *wider life* without inventing
`exercise-2`. The cost is that the ref is a pair rather than a single token, which is why the
slash is excluded from the id charset above.

**⚖-R26 — a concern that genuinely belongs to two rings.** Today `self/sleep` and
`partner/sleep` are two independent items resolved twice — two adapter runs that can disagree,
which is worse than either answer alone. Options: (a) status quo, duplication is the person's
problem; (b) an `alias: <ring>/<item>` item form rendering in a second ring from one
resolution; (c) items declared once in a top-level map and *referenced* by rings.
**Ruled: (a) for v0, with (b) as the named growth path** — (c) is a whole-file restructure that
buys nothing until someone actually has a shared concern.

_Evidence: none yet — unverified._

## CIR-DATA-SCHEMA-ADAPTER-SLOT — the status map

An unrecognized adapter must never resolve to ⚪. Honest grey is a statement that nothing is
watching; a typo'd adapter key wearing that grey is dangerous-green with extra steps.

| row id | inputs | expected |
|---|---|---|
| status-absent | item without `status:` | ⚪ unmonitored by choice (`CIR-DATA-STATUS-RESOLUTION`) |
| status-two-adapters | `status:` with both `manual:` and `freshness:` | config error, bake fails |
| status-unknown-adapter | `status: {sqlite: …}` on a v0 bake | config error, bake fails (the v0 adapter set is closed: `manual`, `freshness`, `command`) |
| manual-invalid-word | `manual: blue` | config error, bake fails |

_Evidence: none yet — unverified._

## CIR-DATA-SCHEMA-LINK — click-through targets

`link:` accepts an absolute `https://` (or `http://`) URL, or a root-relative path (`/…`).
Everything else — including `javascript:`, `data:`, and scheme-relative `//…` — is a config
error. Configs are trusted input, but the page is static HTML and a typo'd scheme must fail
loudly at bake time, not silently at click time.

| row id | inputs | expected |
|---|---|---|
| link-https | `link: https://example.test/labs` | accepted |
| link-root-relative | `link: /details/self-sleep.html` | accepted |
| link-javascript-scheme | `link: javascript:alert(1)` | config error, bake fails |
| link-data-scheme | `link: data:text/html,…` | config error, bake fails |
| link-scheme-relative | `link: //example.test/x` | config error, bake fails |
| link-bare-relative | `link: details/sleep.html` | config error, bake fails (page-relative vs source-relative is ambiguous, so it is rejected rather than guessed) |

**⚖-R16 — the `link:` value space.** Options: (a) any url-or-path, relative resolved against the
served page; (b) `https?` and root-relative only, with `javascript:`, `data:` and `//…` rejected
at bake time. **Ruled: (b).** The two arms that specified this at all disagreed, and (b) is the
security-relevant answer: the page is static HTML built from a config file, so a dangerous scheme
must fail where a human is watching (the bake) rather than where nobody is (the click). Bare
relative paths are rejected rather than resolved because "relative to what" has two plausible
answers here — the served page, or the config directory that every other path is relative to.

_Evidence: none yet — unverified._

## CIR-DATA-SHARE — arc weights within a ring

`share` is a **relative weight normalized within its ring**, not a fraction that must sum to 1.
An item's arc angle is `360° × share ÷ (sum of the ring's shares)`; absent `share` means
weight 1. Shares are per-ring; there is no cross-ring constraint. Geometry consequences —
minimum arc angle — are [`CIR-RENDER-MIN-ARC`](../render/sunburst.md).

| row id | inputs | expected |
|---|---|---|
| shares-equal-halves | two siblings, `share: 0.5` each | two 180° half-arcs (the fixture's Nova/Kit case) |
| shares-absent-equal | three siblings, no `share:` | three 120° arcs |
| shares-mixed | `nova: share 2`, `kit:` no share (weight 1) | arcs 240° / 120°, plus a build warning |
| shares-mixed-fractional | `nova: share 0.5`, `kit:` no share | arcs 120° / 240°, plus a build warning |
| share-zero | `share: 0` | config error, bake fails |
| share-negative | `share: -1` | config error, bake fails |

**⚖-R12 — mixed declared and undeclared `share` in one ring.** Options: (a) relative weights,
undeclared = 1; (b) config error, all-or-nothing per ring; (c) declared shares take that
absolute fraction and the remainder splits among the rest. **Ruled: (a), plus a build warning
whenever one ring mixes declared and undeclared shares.** (a) is the only reading under which
`share` means the same thing everywhere, and it keeps every fixture row correct without edits.
But the `shares-mixed-fractional` row is the trap the warning exists for: someone writing
`share: 0.5` on one of two siblings almost certainly meant "half the ring" and will get a
third. (b) rejects a config that is perfectly reasonable under (a); (c) makes the same number
mean a fraction in one ring and a weight in another. The warning is the honest middle — the
render stays predictable, and the person is told their ring is mixed.

_Evidence: none yet — unverified._

## CIR-DATA-VALIDATION — fail vs warn

**Config errors fail the bake; build warnings never do.** A failed bake publishes nothing: the
last good artifact stays live (`CIR-BAKE-ATOMIC-WRITE`). Validation is whole-config — one bad
item fails the bake, and there are no partial renders.

| row id | inputs | expected |
|---|---|---|
| one-bad-item-fails-bake | 8 valid items + 1 with `manual: blue` | bake fails, last good artifact retained |
| unknown-toplevel-key | `sprinkles: true` at the top level | key ignored, build warning, bake proceeds |
| unknown-item-key | item with `prioritiy: high` (typo) | key ignored, build warning, bake proceeds |
| unknown-status-key | `status: {freshnes: …}` (typo) | config error, bake fails |
| empty-ring | ring with `items: []` | ring renders as an empty band, build warning, bake proceeds |

**⚖-R7 — unknown keys.** Options: (a) any unknown key fails validation; (b) unknown keys are
ignored with a build warning; (c) silently ignored. **Ruled: (b) for non-`status` keys, (a)
inside `status:`.** Forward compatibility is worth having — a newer config on an older bake
should degrade to warnings, not death — and typos still surface in the warnings list. But the
carve-out is where the whole argument lives: an unrecognized *adapter* key silently rendering
⚪ hides a completely unmonitored item behind an honest-looking grey, so it fails instead. (a)
everywhere makes a typo'd cosmetic key as fatal as a typo'd adapter, which is not the same
risk.

**⚖-R13 — a ring with no items.** Options: (a) config error; (b) the ring renders as an empty
band plus a warning; (c) the ring is skipped silently. **Ruled: (b).** Rings are life areas
from the person's own taxonomy; an area with nothing monitored in it yet is a real state, and
an empty band is exactly what honest grey means. (c) is the worst option — a missing band
reads as *no such area*, which is a lie about the person's life. (a) blocks the whole page over
a state that is probably deliberate. Zero rings is still a config error
(`CIR-DATA-SCHEMA-TOPLEVEL#rings-empty`): there is nothing to draw at all.

_Evidence: none yet — unverified._

## Proposed fixture rows (for the builder to land — not landed by this spec pass)

- a `wider`-ring sibling pair exercising `shares-mixed` (`share: 2` + absent → 240°/120°);
- an item with `link: https://example.test/…` exercising `link-https` and the click table in
  [../render/interactions.md](../render/interactions.md);
- an item with a deliberate unknown item key exercising `unknown-item-key`.
