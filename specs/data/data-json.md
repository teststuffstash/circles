# data.json — the baked artifact, and the bake that writes it

The rendering pipeline is **client-side interactive over baked data**: no server, no database,
SSG-agnostic. This page is the contract between the bake (writes it) and the page (reads it).
The page's consumption-side requirements live in [../render/layout.md](../render/layout.md) and
[../render/interactions.md](../render/interactions.md).

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-BAKE-ARTIFACT — what a bake produces

| output | what it is |
|---|---|
| `index.html` | the page, with the current data **inlined** (`CIR-BAKE-SELF-CONTAINED`) |
| `data.json` | the same data as a standalone machine-readable artifact |
| detail pages | one per item that has one — P2 ([`CIR-DETAIL-PAGE-SHAPE`](../render/detail-page.md)) |

```json
{
  "version": 1,
  "spec_version": 0,
  "person": "Alex Example",
  "generated_at": "2026-08-03T02:00:00Z",
  "reference_date": "2026-08-03",
  "timezone": "UTC",
  "stale_after_hours": null,
  "rings": [
    {
      "id": "self",
      "label": "① Self",
      "items": [
        {
          "id": "sleep",
          "label": "Sleep",
          "status": "green",
          "grey_reason": null,
          "guardrail": "Lights out by 23:00 on weeknights",
          "note": null,
          "link": null,
          "share": 1,
          "last_data_date": "2026-08-01",
          "detail_line": "Lights out by 23:00 on weeknights · ok · last data 2026-08-01",
          "detail_page": null
        }
      ]
    }
  ],
  "warnings": [
    { "item": "wider/plants", "message": "command exited 1" }
  ]
}
```

| field | presence | rule |
|---|---|---|
| `version` | always | integer artifact-schema version, currently `1` |
| `spec_version` | always | the config format version this bake read |
| `generated_at` | always | RFC 3339 UTC timestamp of the bake run |
| `reference_date` | always | the single date every adapter aged against (`CIR-ADAPT-REFERENCE-DATE`) |
| `timezone` | always | the IANA zone the reference date was computed in |
| `stale_after_hours` | nullable | the page banners past this age; `null` at P0, where no cadence exists (⚖-R15) |
| `person` | always | display name from `circles.yaml` |
| `rings[]` | always | config order preserved (inside-out); ring/item ids and labels pass through |
| `items[].status` | always | one of `green` / `yellow` / `red` / `grey` |
| `items[].grey_reason` | nullable | `by-choice` \| `by-failure` \| `not-evaluated` when status is `grey`, else `null` ([`CIR-DATA-GREY-REASON`](status-resolution.md), ⚖-R50) |
| `items[].guardrail`, `.note`, `.link` | nullable | `null` when absent in config — no placeholder strings |
| `items[].share` | always | the effective weight (default 1 made explicit) |
| `items[].last_data_date` | nullable | ISO date, present only when the adapter observed one |
| `items[].detail_line` | always | the composed one-line summary (`CIR-BAKE-DETAIL-FIELDS`) |
| `items[].detail_page` | nullable | path of the per-item detail payload, else `null` (P2) |
| `warnings[]` | always | possibly empty; `item` is the `<ring>/<item>` ref, `null` for config-level warnings |

| row id | inputs | expected |
|---|---|---|
| artifact-fixture-roundtrip | bake over `fixtures/alex/circles.yaml` | rings/items preserve config order and ids; `self/exercise` has `status: grey`, `grey_reason: by-choice`, `share: 1`, nulls for absent fields |
| warnings-empty-array | fully healthy bake | `warnings: []` present, never omitted |

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-ARTIFACT — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `artifact-fixture-roundtrip` | PASS | — |
| `warnings-empty-array` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-STATUS-VALUES — wire values are not display words

| row id | inputs | expected |
|---|---|---|
| status-wire-vocabulary | any item | `green` \| `yellow` \| `red` \| `grey` |
| status-never-emoji | any item | never 🟢🟡🔴⚪ in the artifact |
| status-never-display-words | any item | never `ok` / `attention` / `act` / `unmonitored` — those are the page's words ([colors.md](../render/colors.md)) |

**⚖-R19 — which vocabulary the artifact carries.** Options: (a) colour words
`green|yellow|red|grey`; (b) display words `ok|attention|act|unmonitored`. **Ruled: (a).** It is
trivial either way, but it must be *one*, and the two vocabularies must not be the same string:
the display words are a presentation choice that may be reworded or localized, while the wire
value is a stable key that tests and future consumers join on. Keeping them distinct means a
copy edit can never become a schema change.

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-STATUS-VALUES — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `status-never-display-words` | PASS | — |
| `status-never-emoji` | PASS | — |
| `status-wire-vocabulary` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-SELF-CONTAINED — one file that works alone, plus one that machines read

The goal issue says both "one self-contained, interactive HTML page" and "one static HTML asset
+ one `data.json`". Two files are not self-contained. **Both are produced**: `index.html`
inlines its data at bake time and never fetches it, and `data.json` is emitted beside it as the
artifact tests and future consumers read.

| row id | inputs | expected |
|---|---|---|
| page-renders-with-no-network | `index.html` opened from `file://` | full page, all statuses |
| page-makes-no-runtime-requests | page loaded with all non-document requests blocked | renders identically; zero requests ([`CIR-RENDER-NO-EGRESS`](../render/layout.md)) |
| inlined-data-equals-the-file | `index.html` vs `data.json` from one bake | identical data |
| page-has-both-artifacts | one bake run | `index.html` contains both the SVG chart and the inlined `<script id="artifact-data">` |
| page-survives-save-and-mail | save-as from a browser | still renders, still prints |

**⚖-R4 — inline the data, or fetch it?** Options: (a) inline, plus a sibling `data.json`;
(b) fetch `data.json` at load, with a boot-error state. **Ruled: (a).** A page that fetches is
not self-contained: it dies from `file://`, breaks when saved or mailed, and adds a failure mode
(a fetch that hangs) to a product whose whole point is showing an honest picture. Inlining costs
one duplication of a small payload. The sibling file keeps the goal's "one asset + one
`data.json`" literally true and gives P1 something to publish. Under (b) the boot-failure state
would be about network errors; under (a) it is about a malformed embedded payload, which is why
[`CIR-RENDER-BOOT-FAILURE`](../render/layout.md) is written the way it is.

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-SELF-CONTAINED — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `inlined-data-equals-the-file` | PASS | — |
| `page-has-both-artifacts` | PASS | — |
| `page-renders-with-no-network` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-VERSION — artifact versioning

`version` is an integer bumped on any breaking shape change. The page must **refuse an
unrecognized version with a visible error state** ([`CIR-RENDER-BOOT-FAILURE`](../render/layout.md))
rather than render best-effort guesses — a partially understood artifact is dangerous-green.
Additive fields within a version are ignored by older pages.

| row id | inputs | expected |
|---|---|---|
| version-recognized | `version: 1`, page understands 1 | renders |
| version-from-the-future | `version: 2`, page understands 1 | boot failure state, no chart drawn |
| version-additive-field | `version: 1` plus an unknown field | rendered normally, unknown field ignored |

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-VERSION — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `version-recognized` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-GENERATED-AT — the honesty stamp

`generated_at` is written by the bake in UTC and displayed verbatim by the page
(`CIR-RENDER-GENERATED-AT`). Since statuses freeze at bake time
([`CIR-DATA-RESOLUTION-TIME`](status-resolution.md)), the stamp is what separates "current
page" from "the bake died three weeks ago".

_Evidence: none yet — unverified._

## CIR-BAKE-STALE-SELF — the page's own freshness

If the bake stops running, every light freezes at its last value and the page keeps looking
healthy. That is the product's own dangerous-green, and the page must defend against it with no
help from the bake that failed.

| row id | inputs | expected |
|---|---|---|
| stamp-always-visible | any page | stamp shown in a fixed place, never only on hover |
| no-threshold-no-banner | `stale_after_hours: null` (P0) | stamp only; no banner, no invented expectation |
| fresh-bake-shows-no-banner | `generated_at` 6 h old, `stale_after_hours: 36` | no banner |
| stale-bake-shows-banner | `generated_at` 50 h old, `stale_after_hours: 36` | banner: "this page was built <n> hours ago; the lights below are history" |
| stale-lights-marked-not-recoloured | stale bake, item was 🟢 | still 🟢 in place, with the stale treatment ([`CIR-RENDER-STALE-MARK`](../render/colors.md)) |
| stale-bake-never-turns-items-red | stale bake, item was 🟢 | not 🔴 — a dead pipeline is not "act on your life" |
| manual-items-are-stale-too | stale bake with only `manual:` items | the banner applies to the whole page |
| threshold-comes-from-the-artifact | `stale_after_hours: 36` | the page reads it; no hard-coded value in the page |

**⚖-R15 — should the page banner its own staleness?** Options: (a) display the stamp only;
(b) banner past a fixed age baked into the page; (c) banner past a cadence the artifact
declares. **Ruled: (c), with the field null at P0.** The mechanism is specified now so P1 needs
no page change, and the threshold is data rather than code so a cadence change is a config
change. But at P0 there is no schedule at all — statuses are hand-set — so any threshold would
invent an expectation the product has not earned, and the field is `null`, which the page reads
as "no banner". (a) alone leaves the product's own dangerous-green undefended once a nightly
bake exists; (b) puts a number in the page that only the pipeline knows.

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-STALE-SELF — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `no-threshold-no-banner` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-WARNINGS — where build warnings surface

Every build warning is recorded in `warnings[]` with its cell ref **and** surfaced on the page
itself. A reader staring at a grey cell must be able to learn *why* from the page.

| row id | inputs | expected |
|---|---|---|
| warning-carries-cell-ref | plants command exits 1 | `{"item": "wider/plants", …}` |
| config-level-warning-has-null-item | unknown top-level key | `{"item": null, …}` |
| warnings-reach-the-page | any non-empty `warnings[]` | the warnings banner shows the count and a reachable list ([`CIR-RENDER-CHROME`](../render/layout.md)) |
| no-warnings-no-banner | `warnings: []` | no banner element and no reserved empty space |

**⚖-R14 — where a build warning surfaces.** The goal mandates "⚪ + a build warning" and never
says where. Options: (a) the build log only; (b) the artifact plus a page banner; (c) log and
artifact but no page surface. **Ruled: (b).** The honest-and-visible doctrine for ⚪ extends to
its cause — otherwise grey is honest but unexplained, and the person's trusted circle reads the
page, not CI logs. Exposure is bounded by `CIR-BAKE-EXPOSURE`.

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-WARNINGS — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `config-level-warning-has-null-item` | PASS | — |
| `warning-carries-cell-ref` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-DETAIL-FIELDS — structured fields *and* one composed line

The artifact carries both the structured fields (`guardrail`, `status`, `last_data_date`,
`note`, `grey_reason`) and the `detail_line` composed from them at bake time.

| row id | inputs | expected |
|---|---|---|
| detail-line-is-baked | any item | `detail_line` present, composed by the bake |
| structured-fields-also-present | any item | the components remain individually addressable |
| line-matches-its-components | any item | `detail_line` is derivable from the fields beside it |
| no-js-path-needs-no-composition | page with scripting disabled | the printed line and the text alternative use `detail_line` verbatim |

**⚖-R20 — is the detail line baked or composed page-side?** Options: (a) baked as one string;
(b) structured fields only, composed at render time. **Ruled: both, with (a) authoritative.**
Composing page-side means the print path, the no-JS path and the accessibility table each need
composition logic — three chances to disagree about the same sentence. Baking it makes one
string serve all of them. The structured fields stay because tests, future consumers and any
re-formatting need the parts; what they must not do is *re-compose* a second version of the
line. The cost is that wording is frozen in a data file until the next bake, which is
acceptable for a file that is rewritten nightly.

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-DETAIL-FIELDS — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `detail-line-is-baked` | PASS | — |
| `structured-fields-also-present` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-ATOMIC-WRITE — publishing discipline

The bake writes atomically (temp file, then rename) and a **failed bake publishes nothing**: the
last good artifact stays live. A half-written file must never be observable by the page.

| row id | inputs | expected |
|---|---|---|
| failed-bake-keeps-last-good | bake fails validation on run N | run N−1's artifact still served, unchanged |
| interrupted-write-is-atomic | bake killed mid-write | the served file is either the old or the new one, never truncated |

_Evidence: none yet — unverified._

## CIR-BAKE-DETERMINISM — same inputs, same output

| row id | inputs | expected |
|---|---|---|
| two-bakes-agree | same config, same injected reference date | byte-identical artifact except `generated_at` |
| ordering-is-stable | any config | rings and items in file order; warnings in item order |
| host-locale-does-not-leak | bake under a non-English locale | identical output |
| host-timezone-does-not-leak | bake under a non-UTC `TZ` | identical output; the config's `timezone:` governs |

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-DETERMINISM — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `ordering-is-stable` | PASS | — |
| `two-bakes-agree` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-EXPOSURE — everything in the artifact is public

`data.json` sits next to `index.html` and is fetchable by anyone who can reach the page. Nothing
may be in the artifact that is not intended for everyone who can reach the URL — **including
anything the UI merely does not display**.

| row id | inputs | expected |
|---|---|---|
| no-absolute-host-paths | missing source `/home/alex/notes/x.md` | the warning names the config-relative path only |
| command-stderr-not-passed-through | command prints a stack trace with paths and env | warning is a bounded, sanitized summary |
| warning-text-is-bounded | command prints 10 MB to stderr | truncated at a fixed cap |
| no-source-content-in-the-artifact | freshness source with private notes | only the date is carried, never the surrounding text |

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-EXPOSURE — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `no-absolute-host-paths` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-PAGE-DOES-NOT-RESOLVE — the page renders, it never decides

| row id | inputs | expected |
|---|---|---|
| page-contains-no-adapter-code | any build | no date parsing, no threshold arithmetic, no command execution in the page |
| page-recomputes-nothing-on-load | artifact says 🟡 | 🟡, whatever the viewer's clock says |

<details class="evidence-block">
<summary>Evidence: 1 test case(s) — alex</summary>

**Requirement:** CIR-BAKE-PAGE-DOES-NOT-RESOLVE — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `page-contains-no-adapter-code` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-BAKE-DETAIL-FILES — per-item detail payloads (P2 boundary)

Items with a detail page get a baked per-item payload (metric series + intervention events —
[`CIR-DETAIL-PAGE-SHAPE`](../render/detail-page.md)), pointed to by `detail_page`.

**⚖-R34 — how detail data is packaged.** Options: (a) per-item payload files, fetched or linked
per item; (b) everything inlined in the main artifact; (c) one bundle for all detail pages.
**Ruled: (a)**, path convention `details/<ring-id>--<item-id>.json`. The main artifact stays
small for the phone-read path, series data (potentially years of daily points) never taxes the
landing view, and items without detail pages cost nothing. This is a P2 boundary: the shape is
named so P2 does not have to renegotiate it, and nothing more is specified.

_Evidence: none yet — unverified._
