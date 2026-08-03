# circles.yaml — the person's configuration

A person's rings, items, labels, guardrails, links and adapters. **Nothing person-specific may
live in code**: if a page shows it, this file (or a source it points at) supplies it. The key
example is the fixture person [`fixtures/alex/circles.yaml`](../../fixtures/alex/circles.yaml) —
spec rows and that file are the same doctrine (decision tables, synthetic only).

Status *resolution* moved to [status-resolution.md](status-resolution.md); freshness arithmetic
to [freshness.md](freshness.md). `CIR-DATA-STATUS-RESOLUTION` now lives on that page (the ID did
not change).

## Shape (v0)

```yaml
spec_version: 0                   # optional; absent means 0
person: <display name>            # whose circles this is
timezone: <IANA zone>             # optional; default UTC — anchors every age computation
rings:                            # inside-out order; index 0 = innermost
  - id: <slug>                    # stable id, referenced by items, links and tests
    label: <display label>
    items:
      - id: <slug>                # unique within its ring
        label: <display label>
        guardrail: <text>         # optional; shown on hover, never computed
        note: <text>              # optional; why this item is here / why it is unmonitored
        link: <url-or-path>       # optional; click-through target
        share: <number>           # optional arc weight within the ring (default: equal)
        status:                   # exactly one adapter, or absent → ⚪ unmonitored
          manual: green|yellow|red
          # OR
          freshness:
            source: <path-or-glob>  # newest date found in the matched files
            yellow_after: <days>
            red_after: <days>
          # OR
          command: <argv>         # array; prints green|yellow|red on stdout
```

## CIR-DATA-SCHEMA-STRICT — unknown keys are config errors <a id="cir-data-schema-strict"></a>

The bake validates `circles.yaml` against a closed schema before resolving anything. **Any key
not in the schema fails the bake.** A tolerated typo is the cheapest route to dangerous-green:
a misspelled `yellow_after` would silently take a default and paint an unwatched item 🟢.

| description | inputs | expected |
|---|---|---|
| unknown key at item level | item with `guardrails: "..."` (plural typo) | config error naming the key + the item id; nothing published |
| unknown key inside freshness | `yellow_afer: 7` | config error naming the key |
| unknown top-level key | `people: Alex` | config error |
| known key, wrong type | `share: "half"` | config error naming expected type |
| empty file | zero bytes | config error (`rings` is required) |
| unparseable YAML | tab-indented block | config error with line number |

⚖ **CIR-Q-01 — strict schema vs. forward-compatible passthrough.** Strictness blocks the
"contributed built-in adapter" story: a config written for a newer circles would fail on an
older one. Options: (a) closed schema, every unknown key is an error; (b) unknown keys under
`status:` tolerated as unknown adapters → ⚪ + warning, unknown keys elsewhere fatal;
(c) tolerate everything, warn. *Recommendation: (a) now, (b) when the first contributed adapter
lands*, gated on `spec_version`. (a) is encoded above. Under (b) the "unknown adapter" row
becomes ⚪ + warning rather than a config error — a behaviour change for exactly one row.

## CIR-DATA-SCHEMA-VERSION — `spec_version` guards the format <a id="cir-data-schema-version"></a>

`spec_version` is an integer; absent means `0`. A config declaring a version **newer than the
bake understands is a config error**, never a best-effort render (a partially understood config
is dangerous-green by construction).

| description | inputs | expected |
|---|---|---|
| version absent defaults to 0 | no `spec_version` | validates as v0 |
| version matches | `spec_version: 0`, bake understands 0 | validates |
| version from the future | `spec_version: 1`, bake understands 0 | config error: "config is newer than this build" |

⚖ **CIR-Q-02 — is `spec_version` per-file or per-adapter?** Contributed adapters will version
independently of the core schema. Options: (a) single integer for the whole file;
(b) `spec_version` plus per-adapter `api:` fields. *Recommendation: (a) — one integer until a
third-party adapter exists; revisit with the first one.*

## CIR-DATA-IDENTITY — ids, uniqueness and the item ref <a id="cir-data-identity"></a>

Ring ids are unique in the file. Item ids are unique **within their ring**. The reference used by
`data.json`, links, tests and issues is the pair, written `<ring-id>/<item-id>`
(e.g. `self/sleep`).

| description | inputs | expected |
|---|---|---|
| duplicate ring id | two rings `id: self` | config error |
| duplicate item id in one ring | two items `id: sleep` in `self` | config error |
| same item id in different rings | `self/sleep` and `wider/sleep` | valid; two independent items |
| id character set | id matching `^[a-z0-9][a-z0-9-]*$` | valid |
| id with spaces or slash | `id: date night`, `id: a/b` | config error (the slash is the ref separator) |
| missing id | item with `label:` only | config error — ids are how tests name rows |

⚖ **CIR-Q-03 — may one concern appear in several rings?** The recipe asks for it and real life
has it (a shared health concern belonging to both *self* and *partner*). Today the table above
makes `self/sleep` and `wider/sleep` two independent items resolved twice — two adapter runs,
and they can disagree, which is worse than either answer. Options: (a) status quo — duplication
is the person's problem; (b) an `alias: <ring>/<item>` item form that renders in a second ring
from one resolution; (c) items declared once in a top-level `items:` map and *referenced* by
rings. *Recommendation: (a) for v0 with (b) as the named growth path* — (c) is a whole-file
restructure that buys nothing until someone actually has a shared concern. Encoded above: (a).

## CIR-DATA-SHARE — arc weights within a ring <a id="cir-data-share"></a>

`share` is a **relative weight, normalised within its ring**, not a fraction that must sum to 1.
Rendering consequences (minimum arc angle) are [CIR-RENDER-MIN-ARC](../render/sunburst.md).

| description | inputs | expected |
|---|---|---|
| no shares declared | 3 items, none with `share` | three equal arcs of 120° |
| all shares equal | 2 items, `share: 0.5` each (the fixture's children) | two 180° half-arcs |
| shares need not sum to 1 | shares `3` and `1` | 270° and 90° |
| some declared, some not | items with `share: 2`, `share: 2`, and one without | config error (see ⚖ CIR-Q-04) |
| zero or negative share | `share: 0`, `share: -1` | config error |
| non-numeric share | `share: "big"` | config error |

⚖ **CIR-Q-04 — mixing declared and undeclared `share` in one ring.** Options: (a) config error
(above); (b) undeclared defaults to `1`; (c) undeclared items split the remainder after declared
fractions. (b) surprises: adding one `share: 4` sibling silently shrinks the others to a sliver.
(c) only works if declared shares are fractions summing below 1, contradicting "relative
weights". *Recommendation: (a)* — all-or-nothing per ring is the only rule with no silent
resize, and the error message can suggest the shares to write.

## CIR-DATA-CONTENT — labels, guardrails, notes, links <a id="cir-data-content"></a>

| description | inputs | expected |
|---|---|---|
| label required | item without `label` | config error |
| guardrail optional | item without `guardrail` | valid; detail line omits the guardrail line, never prints "None" |
| note carries the why | `note: "deliberately not tracked"` | shown in the detail line; never affects the status |
| link is optional | item without `link` | valid; item is not a click target unless it has a detail page ([CIR-RENDER-CLICK](../render/interaction.md)) |
| link may be external | `https://example.invalid/x` | valid; opened in a new context |
| link may be a relative path | `notes/sleep-log.md` | valid; resolved against the served page, not the config dir |
| label length is bounded | label longer than [CIR-RENDER-LABEL-BUDGET](../render/sunburst.md) | valid config, render warning + truncation with full text in the detail |
| person is required | no `person:` | config error (the page title needs it) |

**Labels are content, not layout.** Ring ordering numerals (`① Self`) belong to the renderer,
which numbers rings by their index ([CIR-RENDER-RING-ORDER](../render/sunburst.md)). The fixture
person currently bakes the numerals into its labels; that is a fixture change for the builder,
recorded as a follow-up, not something this page can edit.

## CIR-DATA-TIMEZONE — one zone per config <a id="cir-data-timezone"></a>

`timezone:` is an IANA zone name (`Europe/Tallinn`), default `UTC`. It anchors every age
computation in the file ([CIR-DATA-AGE-CALENDAR](freshness.md)) — not the bake host's zone,
which is an artifact of where the job happens to run.

| description | inputs | expected |
|---|---|---|
| timezone absent defaults to UTC | no `timezone:` | ages computed in UTC |
| timezone is validated | `timezone: Mars/Olympus` | config error |
| host zone is never consulted | bake host `TZ=America/Los_Angeles`, config `Europe/Tallinn` | ages identical to a bake on any other host |

⚖ **CIR-Q-05 — one zone per config, or per item?** A person travelling, or an item whose source
is written by someone in another zone, would want per-item. *Recommendation: file-level only* —
per-item zones buy at most a one-day difference on a threshold measured in days, at the cost of
a second place to get it wrong.

## Whole-file examples

The fixture person is the key example and exercises: freshness inside window (`self/sleep`),
freshness very stale (`self/labs`), no adapter → ⚪ (`self/exercise`), manual yellow
(`partner/date-night`), two half-arc siblings (`children/nova`, `children/kit`), manual red
(`wider/friends`), command adapter (`wider/plants`).

Cases it does **not** yet exercise, proposed as fixture rows for the builder (this pass may not
touch `fixtures/`):

| proposed fixture | why it is needed |
|---|---|
| an item with `note:` and no adapter | distinguishes *unmonitored by choice* from *by failure* ([CIR-DATA-GREY-REASON](status-resolution.md)) |
| a `freshness:` item whose `source:` glob matches nothing | the ⚪ + warning path has no committed example |
| a ring with three unequal `share`s | normalisation is only shown at 0.5/0.5, where every rule agrees |
| a second fixture person with one ring and one item | the minimum viable page; also the capacity floor |
| a fixture person with 7 rings / 40 items | the capacity ceiling ([CIR-RENDER-CAPACITY](../render/sunburst.md)) has no example |
