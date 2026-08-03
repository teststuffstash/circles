# The bake and `data.json`

The bake is the only thing that resolves statuses; the page only draws what it is handed. This
page fixes the artifact between them — and the three things the issue leaves unsaid about it:
what "self-contained" means when there are two files, what happens when the bake itself stops
running, and what a public URL exposes.

## CIR-BAKE-ARTIFACT — what a bake writes <a id="cir-bake-artifact"></a>

One bake writes, atomically, a directory containing:

| file | contents |
|---|---|
| `index.html` | the page, with the current `data.json` **inlined** ([CIR-BAKE-SELF-CONTAINED](#cir-bake-self-contained)) |
| `data.json` | the same data as a standalone machine-readable artifact |
| detail pages | one per item that has one ([CIR-DETAIL-PAGE-SHAPE](../render/detail-page.md)) |

`data.json` shape:

```json
{
  "spec_version": 0,
  "person": "Alex Example",
  "generated_at": "2026-08-03T02:00:00Z",
  "reference_date": "2026-08-03",
  "timezone": "UTC",
  "stale_after_hours": 36,
  "rings": [
    { "id": "self", "label": "Self", "index": 0,
      "items": [
        { "ref": "self/sleep", "id": "sleep", "label": "Sleep", "share": 1,
          "status": "green", "reason": null, "data_date": "2026-08-01",
          "guardrail": "Lights out by 23:00 on weeknights", "note": null,
          "link": null, "detail": null,
          "detail_line": "Lights out by 23:00 on weeknights · ok · last data 2026-08-01" }
      ] }
  ],
  "warnings": [ { "ref": "wider/plants", "text": "command exited 1" } ],
  "summary": { "green": 4, "yellow": 2, "red": 1, "unmonitored_by_choice": 1, "unmonitored_by_failure": 1 }
}
```

| description | inputs | expected |
|---|---|---|
| every item appears exactly once | config with 9 items | 9 item objects |
| status is one of four words | any item | `green`\|`yellow`\|`red`\|`unmonitored` |
| grey carries its reason | ⚪ item | `reason` is `by-choice` or `by-failure`, never null |
| a coloured item has no reason | 🟢 item | `reason: null` |
| ring order is explicit | rings in file order | `index` 0 = innermost, ascending outward |
| the artifact is written atomically | bake interrupted mid-write | no half-written `data.json` is ever served |
| summary equals the counts | 9 items | summary numbers sum to 9 |

## CIR-BAKE-SELF-CONTAINED — one file that works alone, plus one that machines read <a id="cir-bake-self-contained"></a>

The issue says both "one self-contained, interactive HTML page" and "one static HTML asset +
one `data.json`". Two files are not self-contained. **Both are produced**: `index.html` inlines
its data at bake time and never fetches it, and `data.json` is emitted beside it as the artifact
tests and future consumers read.

| description | inputs | expected |
|---|---|---|
| the page renders with no network | `index.html` opened from `file://` | full page, all statuses |
| the page makes no requests at run time | page loaded with all non-document requests blocked | renders identically; zero requests ([CIR-RENDER-NO-EGRESS](../render/layout.md)) |
| the inlined data equals the file | `index.html` vs `data.json` from one bake | identical data |
| the page can be saved and mailed | save-as from a browser | still renders, still prints |

⚖ **CIR-Q-16 — inline the data, or fetch it?** Options: (a) inline, plus a sibling `data.json`
(encoded); (b) fetch `data.json` so the page asset is cacheable and only the data changes;
(c) inline only, no `data.json`. (b) breaks `file://` viewing and adds a fetch that can fail
silently, showing an empty or stale page. (c) leaves tests parsing HTML. *Recommendation: (a)* —
the duplication is a few KB written by one bake, and a single file is what survives being saved,
printed, or mailed to the person's doctor.

## CIR-BAKE-STALE-SELF — the page's own freshness <a id="cir-bake-stale-self"></a>

If the bake stops running, every light freezes at its last value and the page keeps looking
healthy. That is the product's own dangerous-green, and the page must defend against it with
no help from the bake that failed.

| description | inputs | expected |
|---|---|---|
| the generated-at stamp is always visible | any page | stamp shown in a fixed place, not only on hover |
| a fresh bake shows no banner | `generated_at` 6 h old, `stale_after_hours` 36 | no banner |
| a stale bake shows a banner | `generated_at` 50 h old | prominent banner: "this page was built <n> hours ago; the lights below are history" |
| stale lights are marked, not recoloured | stale bake, item was 🟢 | still 🟢 in place, with the stale treatment ([CIR-RENDER-STALE-MARK](../render/color.md)) |
| a stale bake never turns items red | stale bake, item was 🟢 | not 🔴 — tooling failure is never "act on your life" |
| manual items are stale too | stale bake with only `manual:` items | banner applies to the whole page |
| the threshold comes from the artifact | `stale_after_hours: 36` | the page reads it; there is no hard-coded value in the page |
| a clock-skewed future stamp is treated as stale | `generated_at` two days ahead of the viewer's clock | banner shown ("built in the future" is broken tooling) |

⚖ **CIR-Q-17 — should a stale bake grey out its adapter-derived items?** Options: (a) keep the
last lights and add the banner + stale treatment (encoded); (b) force every adapter-derived item
to ⚪ once the bake is stale, since an unrefreshed status is unknown; (c) banner only.
(b) is the most honest reading of "grey means we are not watching this" and the most aggressive:
a one-night bake outage would blank a page whose statuses are mostly measured in weeks.
*Recommendation: (a)* — the lights are still the best information available and the banner
removes the false confidence; revisit if a real outage ever produced a wrong decision. (c) alone
is rejected: a banner that colours nothing is read as decoration within a week.

⚖ **CIR-Q-18 — what is `stale_after_hours` for a nightly bake?** Encoded as a per-config value
with no ruled default. 36 h (one missed nightly run plus slack) is the recommended default;
items whose freshness windows are measured in months make a shorter threshold noisy, and the
value is arguably per-person rather than per-product.

## CIR-BAKE-DETERMINISM — same inputs, same output <a id="cir-bake-determinism"></a>

| description | inputs | expected |
|---|---|---|
| two bakes of one config agree | same config, same injected reference date | byte-identical `data.json` except `generated_at` |
| the reference date is injectable | tests pass a fixed date | ages are exact and reproducible |
| adapters do not read the clock | any adapter | [CIR-ADAPT-CONTRACT](adapters.md) |
| ordering is stable | any config | rings and items in file order; warnings in item order |
| the host's locale does not leak | bake under a non-English locale | identical output |

Without an injectable reference date, every freshness test would have to rewrite fixture dates
relative to "today" — which is exactly what `fixtures/alex/notes/sleep-log.md` warns tests may
do. Both work; the injected date is preferred because it lets committed fixture rows stay
fixed and readable ([CIR-PROC-TEST-ROWS](../process/testing.md)).

## CIR-BAKE-WARNINGS — warnings are content, not logs <a id="cir-bake-warnings"></a>

Every ⚪ by failure, every ignored date, every skipped source produces a warning that ships in
the artifact and is reachable from the page.

| description | inputs | expected |
|---|---|---|
| a warning names its item | failing command on `wider/plants` | warning carries the ref `wider/plants` |
| page-level warnings exist | a source glob skipped a binary file | warning with no item ref |
| the page shows the warning count | 2 warnings | visible count, one click/tap to the list |
| warnings survive print | printed page | count and list are in the accessible equivalent ([CIR-RENDER-A11Y-TABLE](../render/color.md)) |
| a bake with warnings still exits 0 | 3 warnings, no config error | exit 0 |

## CIR-BAKE-EXPOSURE — everything in the artifact is public <a id="cir-bake-exposure"></a>

`data.json` sits next to `index.html` and is fetchable by anyone who can reach the page. Nothing
may be in the artifact that is not intended for everyone who can reach the URL — including
anything the UI merely does not display.

| description | inputs | expected |
|---|---|---|
| no absolute host paths in warnings | missing source `/home/alex/notes/x.md` | warning names the config-relative path only |
| command stderr is not passed through | command prints a stack trace with paths and env | warning is a bounded, sanitised summary |
| the warning text length is bounded | command prints 10 MB to stderr | truncated at a fixed cap |
| no environment values are baked | any bake | none of the bake's environment appears in the artifact |
| no source file contents are baked | freshness source with a private note line | only the matched date is carried, never the line |
| nothing is hidden-but-present | an item the person removes from the config | absent from `data.json`, not merely unrendered |

The last row is the rule that makes the others verifiable: "hidden in the UI" is not a privacy
mechanism for a static file. Access control for the deployed page is deploy-time (ingress
authentication in circles-iac), not a property of this repo — and this repo must not commit any
real config to be baked, per `CLAUDE.md`.

## CIR-BAKE-PAGE-DOES-NOT-RESOLVE — the page draws, it does not decide <a id="cir-bake-page-does-not-resolve"></a>

| description | inputs | expected |
|---|---|---|
| the page does not compute ages | page open across local midnight | no light changes ([CIR-BAKE-STALE-SELF](#cir-bake-stale-self) is the only time-dependent behaviour) |
| the page does not run adapters | any page | no code path evaluates `freshness:`/`command:` |
| the page does not read the config | any page | `circles.yaml` is not served |
| two viewers see the same lights | different timezones, same artifact | identical statuses |

The page's only clock use is comparing `generated_at` against `stale_after_hours` — the one
place where the viewer's own "now" is the right question.
