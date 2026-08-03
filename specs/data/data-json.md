# data.json — the baked render input (CIR-DATA-DATAJSON-*)

The rendering pipeline is **client-side interactive over baked data**: one static HTML asset
+ one `data.json`, no server, no database, SSG-agnostic. This page is the contract between
the bake (writes it) and the page (reads it). The page's consumption-side requirements live
in [../render/layout.md](../render/layout.md) and
[../render/interactions.md](../render/interactions.md).

## CIR-DATA-DATAJSON-SCHEMA — the shape

```json
{
  "version": 1,
  "generated_at": "2026-08-03T02:00:00Z",
  "person": "Alex Example",
  "rings": [
    {
      "id": "self",
      "label": "① Self",
      "items": [
        {
          "id": "sleep",
          "label": "Sleep",
          "status": "green",
          "guardrail": "Lights out by 23:00 on weeknights",
          "link": null,
          "share": 1,
          "last_data_date": "2026-08-01",
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
| `version` | always | integer schema version, currently `1` |
| `generated_at` | always | RFC 3339 UTC timestamp of the bake run |
| `person` | always | display name from `circles.yaml` |
| `rings[]` | always | config order preserved (inside-out); ring/item ids and labels pass through |
| `items[].status` | always | one of `green` / `yellow` / `red` / `grey` (wire values, spelled out) |
| `items[].guardrail`, `.link` | nullable | `null` when absent in config — no placeholder strings |
| `items[].share` | always | the effective weight (default 1 made explicit) |
| `items[].last_data_date` | nullable | ISO date, present only when the adapter observed one |
| `items[].detail_page` | nullable | path of the per-item detail payload, else `null` (P2 — see CIR-DATA-DATAJSON-DETAIL-FILES) |
| `warnings[]` | always | possibly empty; `item` is the `<ring>/<item>` cell identity, `null` for config-level warnings |

| row (test id) | inputs | expected |
|---|---|---|
| schema-fixture-roundtrip | bake over `fixtures/alex/circles.yaml` | rings/items preserve config order and ids; `exercise` has `status: grey`, `share: 1`, nulls for absent fields |
| warnings-empty-array | fully healthy bake | `warnings: []` present, not omitted |
| status-wire-values | any item | status spelled `green|yellow|red|grey` — never emoji, never `ok/attention/act` (those are display words, [colors.md](../render/colors.md)) |

## CIR-DATA-DATAJSON-VERSION — schema versioning

`version` is an integer bumped on any breaking shape change. The page must **refuse an
unrecognized major version with a visible error state** (CIR-RENDER-LAYOUT-BOOT-ERROR) rather
than render best-effort guesses. Additive fields within a version are ignored by older pages.

## CIR-DATA-DATAJSON-GENERATED-AT — the honesty stamp

`generated_at` is written by the bake in UTC and displayed verbatim by the page
(CIR-RENDER-LAYOUT-GENERATED-AT-VISIBLE). It is the only freshness signal for the pipeline
itself: since statuses freeze at bake time (CIR-DATA-STATUS-RESOLUTION-TIME), the stamp is
what separates "current page" from "the bake died three weeks ago".

**⚖ AMBIGUITY: PAGE-STALENESS-BANNER** — should the page compute "this data is N days old"
and warn? Options: (a) display the stamp only; (b) banner when the stamp is older than a
fixed age; (c) banner when older than a config-declared bake cadence. **Recommendation: (a)
in v0** — P0 has no schedule, so any threshold invents an expectation the product hasn't
declared; when P1 lands the nightly cadence, (c) becomes well-defined and can be added as a
new requirement. The stamp alone already keeps a dead pipeline visible to an attentive
reader.

## CIR-DATA-DATAJSON-WARNINGS — where build warnings live

Every build warning is recorded in `warnings[]` with its cell identity.

**⚖ AMBIGUITY: WARNINGS-SURFACING** — the goal issue mandates "⚪ + a build warning" but
never says where the warning surfaces. Options: (a) build log only; (b) `data.json`
`warnings[]` + a page banner; (c) build log + `data.json`, no page surface.
**Recommendation: (b)** — the honest-and-visible doctrine for ⚪ extends to its cause: a
reader staring at a grey cell should be able to learn *why* from the page itself, and the
person's trusted circle reads the page, not CI logs. The banner lists count + first cause;
full text stays in the baked fields. If exposure concerns arise (the page may be shared),
that is the same audience question as the page itself — see Follow-ups in the introducing PR.

## CIR-DATA-DATAJSON-ATOMIC-WRITE — publishing discipline

The bake writes `data.json` **atomically** (write to a sibling temp file, then rename) and a
**failed bake publishes nothing**: the last good file stays live. A half-written JSON must
never be observable by the page (which would then hit its boot-error state for no product
reason).

| row (test id) | inputs | expected |
|---|---|---|
| failed-bake-keeps-last-good | bake fails validation on run N | run N−1's `data.json` still served, unchanged |
| interrupted-write-atomic | bake killed mid-write | served file is either the old or the new `data.json`, never a truncated one |

## CIR-DATA-DATAJSON-DETAIL-FIELDS — structured, not pre-composed

`data.json` carries **structured fields** (guardrail, status, last-data date separately);
the page composes the detail line at render time (CIR-RENDER-INTERACT-HOVER). Pre-composed
display strings in the bake would freeze wording into a data file and block page-side
formatting (print vs screen, future locales).

## CIR-DATA-DATAJSON-DETAIL-FILES — per-item detail payloads (P2 contract)

Items with a detail page get a baked per-item payload (metric series + intervention events —
[../render/interactions.md](../render/interactions.md) § CIR-RENDER-DETAIL-PAGE), pointed to
by `detail_page`. **⚖ AMBIGUITY: DETAIL-DATA-PACKAGING** — Options: (a) per-item payload
files fetched lazily on click; (b) everything inlined in `data.json`; (c) one bundle for all
detail pages. **Recommendation: (a)** — the main file stays small for the phone-read path,
series data (P2, potentially years of daily points) never taxes the landing view, and items
without detail pages cost nothing. Path convention: `details/<ring-id>--<item-id>.json`
sibling to `data.json`.
