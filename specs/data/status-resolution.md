# Status resolution — how an item gets its light

Resolution turns one item's declared adapter into exactly one status and one detail line, once,
at bake time. The page never resolves ([CIR-BAKE-PAGE-DOES-NOT-RESOLVE](data-json.md)).

Two failure vocabularies meet here and the issue does not separate them. This page does:

- a **config error** is a defect in `circles.yaml` — it fails the bake and publishes nothing;
- an **adapter failure** is a well-formed adapter that could not answer — it resolves to ⚪ plus
  a warning and the page still ships.

The difference is whether a human can fix it *before* anyone looks at a wrong page.

## CIR-DATA-STATUS-RESOLUTION — the resolution table <a id="cir-data-status-resolution"></a>

The seed rows, kept verbatim as the anchor's core, plus the cases the seed left open:

| description | inputs | expected |
|---|---|---|
| no adapter declared | item without `status:` | ⚪ unmonitored, reason `by-choice` |
| manual green | `manual: green` | 🟢 |
| manual yellow | `manual: yellow` | 🟡 |
| manual red | `manual: red` | 🔴 |
| freshness inside window | newest date 3d old, yellow_after 7, red_after 30 | 🟢 |
| freshness stale | newest date 10d old, yellow_after 7, red_after 30 | 🟡 |
| freshness very stale | newest date 45d old, yellow_after 7, red_after 30 | 🔴 |
| freshness source missing | `source:` matches no file | ⚪ + warning, reason `by-failure` |
| command failure is not red | `command:` exits non-zero | ⚪ + warning (never 🔴 — red means "act", not "broken tooling") |
| command prints an unknown word | stdout `amber` | ⚪ + warning naming the word |
| command prints nothing | empty stdout, exit 0 | ⚪ + warning |
| adapter not implemented in this phase | `command:` under a P0 bake | ⚪ + warning "adapter not evaluated in this build" (see ⚖ CIR-Q-06) |
| two adapters on one item | `manual:` and `freshness:` both present | config error — resolution must not choose |
| empty status block | `status: {}` | config error (write no `status:` instead) |
| manual with an unknown word | `manual: amber` | config error (a typo here is dangerous-green: it must not silently degrade to ⚪) |
| manual cannot declare grey | `manual: grey` | config error (see ⚖ CIR-Q-07) |

Note the deliberate asymmetry in the last rows: a bad word from a *command* is a run-time
failure (⚪ + warning), a bad word in the *config* is a config error. The config is checkable
before publishing; the command's output is not.

## CIR-DATA-CONFIG-ERROR-FAILS — config errors publish nothing <a id="cir-data-config-error-fails"></a>

A config error aborts the bake with a non-zero exit and a message naming the file, the item's
ref and the offending key. **No partial `data.json` is written and the previously published
page is left untouched.** Publishing a half-resolved page would show 🟢 for items whose config
was never read — dangerous-green.

| description | inputs | expected |
|---|---|---|
| config error aborts the whole bake | one item with an unknown key, nine valid items | non-zero exit; no `data.json` written |
| a previously published page survives a failed bake | published page exists, new bake hits a config error | old page still served; it ages and eventually trips [CIR-BAKE-STALE-SELF](data-json.md) |
| the message names the item | error inside `children/kit` | message contains `children/kit` |

## CIR-DATA-FAILURE-IS-GREY — tooling failure is ⚪, never 🔴 <a id="cir-data-failure-is-grey"></a>

Every adapter failure resolves to ⚪ with a warning. 🔴 is reserved for "act on your life".

| description | inputs | expected |
|---|---|---|
| non-zero exit is grey | `command:` exits 1 | ⚪ + warning |
| timeout is grey | `command:` exceeds the timeout ([CIR-ADAPT-COMMAND](adapters.md)) | ⚪ + warning naming the timeout |
| missing source is grey | `freshness:` source glob matches nothing | ⚪ + warning |
| unreadable source is grey | source exists, permission denied | ⚪ + warning |
| no dates in a matched source | source file contains no parseable date | ⚪ + warning ([CIR-DATA-DATE-PARSE](freshness.md)) |
| a failing adapter never inherits its last light | item was 🟢 in yesterday's bake, adapter fails today | ⚪ — statuses are never carried over between bakes |

The last row is the one implementations get wrong. Carrying yesterday's light forward is the
most attractive dangerous-green there is: the page looks healthy for weeks while the tooling
rots. Yesterday's answer is available in yesterday's artifact; it is not a status today.

⚖ **CIR-Q-06 — what does an unimplemented adapter show in P0?** The issue says "P0: statuses
hand-set in config", while the fixture person already declares `freshness:` and `command:`
items. Something must resolve them. Options: (a) P0 has no bake and only `manual:` items may
exist — the fixture becomes invalid, and the first real config is thrown away at P1; (b) the
bake exists from P0 and implements `manual:` only, with other adapters resolving to ⚪ + "not
evaluated in this build"; (c) P0 evaluates everything, collapsing P0 and P1. *Recommendation:
(b)* — encoded in the resolution table above and in
[CIR-PROC-PHASE-P0](../process/phases.md). It keeps the fixture legal, keeps the honest-grey
doctrine ("we are not watching this yet" is true and visible), and makes P1 a pure
implementation step with no config migration.

## CIR-DATA-GREY-REASON — one grey light, two reasons <a id="cir-data-grey-reason"></a>

⚪ has two roads, and conflating them hides broken tooling behind deliberate silence. The light
is the same (the glossary fixes four statuses, not five); the **reason** is carried in
`data.json`, shown in the detail line, and counted separately in the page summary
([CIR-RENDER-SUMMARY](../render/sunburst.md)).

| description | inputs | expected |
|---|---|---|
| unmonitored by choice | no `status:` block | reason `by-choice`; detail line "not monitored" plus `note:` if present |
| unmonitored by failure | adapter declared, adapter failed | reason `by-failure`; detail line names the failure |
| the summary separates them | 3 items with no adapter, 1 failing adapter | summary reads "3 unmonitored · 1 adapter failing", not "4 unmonitored" |
| by-failure is visually distinguishable | one of each on the page | the two are distinguishable without hovering ([CIR-RENDER-GREY-VISIBLE](../render/color.md)) |

⚖ **CIR-Q-07 — should "deliberately unmonitored" be declarable rather than inferred?** Today
absence-of-adapter means by-choice, so *forgetting* to add an adapter is indistinguishable from
*choosing* not to. Options: (a) infer from absence, with `note:` as the human signal (encoded
above); (b) require an explicit `status: {unmonitored: <reason>}` so silence is always a
by-omission warning; (c) a config-level `strict_coverage: true` that turns any adapterless item
into a warning. *Recommendation: (a) now, (c) as a one-line addition when a person's config
grows past the size where they can eyeball it.* Under (b), the fixture's `self/exercise` row
becomes a config error — a fixture change, hence the ⚖ rather than a silent decision.

## CIR-DATA-DETAIL-LINE — what hover shows <a id="cir-data-detail-line"></a>

Every item resolves a detail line: the guardrail (if any), the status word, the last-data date
(if the adapter has one), the note (if any), and the failure reason (if any). Order is fixed so
the eye lands in the same place on every item.

| description | inputs | expected |
|---|---|---|
| full detail line | guardrail + freshness adapter with a date | "guardrail · status · last data YYYY-MM-DD" |
| no guardrail | item without `guardrail` | line starts at the status; no empty separator |
| manual item has no last-data date | `manual: green` | no date segment (a manual light has no data date — printing the bake date here would imply freshness the config does not have) |
| failure reason is shown | command timed out | line ends with the reason, not a stack trace ([CIR-BAKE-EXPOSURE](data-json.md)) |
| detail line is plain text | any item | no markup; the same string serves hover, the accessible table, and print |
