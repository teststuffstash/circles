# Status resolution — how an item gets its light

Resolution turns one item's declared adapter into exactly one status and one detail line, once,
at bake time. The page never resolves ([`CIR-BAKE-PAGE-DOES-NOT-RESOLVE`](data-json.md)).

The traffic-light semantics are **fixed product doctrine**:

- 🟢 ok · 🟡 attention · 🔴 act — per item, from its adapter;
- ⚪ unmonitored — an item with **no adapter**, an item whose tooling failed, or an item whose
  adapter the current phase deliberately does not evaluate (⚖-R2). Grey is honest and visible:
  never hidden, never defaulted to green;
- **tooling failure is ⚪ + a build warning, never 🔴** — red means "act on your life", not
  "the tooling broke".

Two failure vocabularies meet here and the goal issue does not separate them. This page does:

- a **config error** is a defect in `circles.yaml` — it fails the bake and publishes nothing;
- an **adapter failure** is a well-formed adapter that could not answer — it resolves to ⚪ plus
  a warning, and the page still ships.

The difference is whether a human can fix it *before* anyone looks at a wrong page.

**World: alex** — every table on this page states behavior against the fixture person.

## CIR-DATA-STATUS-RESOLUTION — the canonical table

| row id | inputs | expected |
|---|---|---|
| no-adapter-declared | item without `status:` | ⚪ unmonitored, reason `by-choice` |
| manual-green | `manual: green` | 🟢 |
| manual-yellow | `manual: yellow` | 🟡 |
| manual-red | `manual: red` | 🔴 |
| freshness-inside-window | newest date 3d old, `yellow_after: 7`, `red_after: 30` | 🟢 |
| freshness-stale | newest date 10d old, `yellow_after: 7`, `red_after: 30` | 🟡 |
| freshness-very-stale | newest date 45d old, `yellow_after: 7`, `red_after: 30` | 🔴 |
| freshness-source-missing | `source:` matches no file | ⚪ + build warning, reason `by-failure` |
| freshness-source-no-dates | source file exists, zero parseable dates | ⚪ + build warning |
| freshness-all-dates-future | every parseable date is after the reference date | ⚪ + build warning (⚖-R8) |
| command-nonzero-exit | `command:` exits non-zero | ⚪ + build warning — never 🔴 |
| command-bad-stdout | `command:` prints `orange` | ⚪ + build warning naming the word |
| command-empty-stdout | empty stdout, exit 0 | ⚪ + build warning |
| command-timeout | `command:` exceeds its deadline | ⚪ + build warning (`CIR-ADAPT-COMMAND`) |
| adapter-not-evaluated-this-phase | `command:` under a P0 bake | ⚪ + warning "adapter not evaluated in this build", reason `not-evaluated` (⚖-R2, ⚖-R50) |
| two-adapters-on-one-item | `manual:` and `freshness:` both present | config error — resolution must not choose |
| empty-status-block | `status: {}` | config error (write no `status:` instead) |
| manual-unknown-word | `manual: amber` | config error — a typo here is dangerous-green, so it must not degrade to ⚪ |
| manual-declares-grey | `manual: grey` | config error (⚖-R30) |
| unknown-adapter-key | `status: {sqlite: …}` | config error, bake fails (`CIR-DATA-SCHEMA-ADAPTER-SLOT`) |

Note the deliberate asymmetry in the last rows: a bad word from a *command* is a run-time
failure (⚪ + warning), a bad word in the *config* is a config error. The config is checkable
before publishing; the command's output is not.

<details class="evidence-block">
<summary>Evidence: 10 test case(s) — alex</summary>

**Requirement:** CIR-DATA-STATUS-RESOLUTION — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `adapter-not-evaluated-this-phase` | PASS | — |
| `empty-status-block` | PASS | — |
| `manual-declares-grey` | PASS | — |
| `manual-green` | PASS | — |
| `manual-red` | PASS | — |
| `manual-unknown-word` | PASS | — |
| `manual-yellow` | PASS | — |
| `no-adapter-declared` | PASS | — |
| `two-adapters-on-one-item` | PASS | — |
| `unknown-adapter-key` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-CONFIG-ERROR-FAILS — config errors publish nothing

A config error aborts the bake with a non-zero exit and a message naming the file, the item's
ref and the offending key. **No partial artifact is written and the previously published page
is left untouched.** Publishing a half-resolved page would show 🟢 for items whose config was
never read — dangerous-green.

| row id | inputs | expected |
|---|---|---|
| config-error-aborts-whole-bake | one item with an unknown `status:` key, nine valid items | non-zero exit; no artifact written |
| published-page-survives-failed-bake | published page exists, new bake hits a config error | old page still served; it ages and eventually trips [`CIR-BAKE-STALE-SELF`](data-json.md) |
| message-names-the-item | error inside `children/kit` | message contains `children/kit` |

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-DATA-CONFIG-ERROR-FAILS — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `config-error-aborts-whole-bake` | PASS | — |
| `message-names-the-item` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-FAILURE-IS-GREY — the failure algebra

Every adapter-runtime failure mode — missing source, unreadable file, zero parseable dates,
command non-zero exit, command timeout, unparseable command output, future-only dates —
resolves to the **same outcome**: ⚪ + a build warning naming the item and the cause. No failure
mode may synthesize 🔴 (red is reserved for "your life needs action": a hand-set red, or data
that is present and very stale). No failure mode may synthesize 🟢 either.

| row id | inputs | expected |
|---|---|---|
| failure-never-red | any adapter failure | outcome is ⚪ + warning; 🔴 unreachable |
| failure-never-green | any adapter failure | outcome is ⚪ + warning; 🟢 unreachable |
| warning-names-item | `plants` command exits 3 | warning identifies cell `wider/plants` and the exit code |
| unreadable-source-is-grey | source exists, permission denied | ⚪ + warning |
| failing-adapter-never-inherits-last-light | item was 🟢 in yesterday's bake, adapter fails today | ⚪ — statuses are never carried over between bakes |

The last row is the one implementations get wrong. Carrying yesterday's light forward is the
most attractive dangerous-green there is: the page looks healthy for weeks while the tooling
rots. Yesterday's answer is available in yesterday's artifact; it is not a status today.

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-DATA-FAILURE-IS-GREY — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `failure-never-green` | PASS | — |
| `failure-never-red` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-GREY-REASON — one grey light, three reasons

⚪ has three roads, and conflating them hides broken tooling behind deliberate silence — or
dresses a phase boundary up as a failure. The light is the same (the glossary fixes four
statuses, not five); the **reason** rides in the artifact, shows in the detail line, and is
counted separately in the page summary ([`CIR-RENDER-SUMMARY`](../render/sunburst.md)):

- `by-choice` — no adapter declared; the silence is the person's decision;
- `by-failure` — an adapter was declared and could not answer;
- `not-evaluated` — an adapter was declared and the current phase deliberately does not run it
  (⚖-R2, ⚖-R50). Neither a choice nor a failure: a build honestly reporting its own boundary.

In every grey detail line the status word is the display word `unmonitored` — the same word the
legend teaches — with the reason as its own following segment (⚖-R51).

| row id | inputs | expected |
|---|---|---|
| unmonitored-by-choice | no `status:` block | reason `by-choice`; detail line "unmonitored", plus `note:` if present |
| unmonitored-by-failure | adapter declared, adapter failed | reason `by-failure`; detail line "unmonitored · <the failure cause>" |
| unmonitored-not-evaluated | `freshness:` or `command:` under a P0 bake | reason `not-evaluated`; detail line "unmonitored · not evaluated in this build" |
| summary-separates-all-three | 3 items with no adapter, 1 failing adapter, 2 P0 `command:` items | summary reads "3 unmonitored · 1 adapter failing · 2 not evaluated", never "6 unmonitored" |
| by-failure-visually-distinguishable | one `by-choice` cell and one tooling-caused (`by-failure` / `not-evaluated`) cell | chosen silence and tooling-caused grey are distinguishable without hovering ([`CIR-RENDER-GREY-VISIBLE`](../render/colors.md)) |

**⚖-R30 — should "deliberately unmonitored" be declarable rather than inferred?** Today
absence-of-adapter means by-choice, so *forgetting* to add an adapter is indistinguishable from
*choosing* not to. Options: (a) infer from absence, with `note:` as the human signal;
(b) require an explicit `status: {unmonitored: <reason>}` so silence is always a by-omission
warning; (c) a config-level `strict_coverage: true` that turns any adapterless item into a
warning. **Ruled: (a) now, (c) as a one-line addition when a person's config grows past the
size where they can eyeball it.** Under (b) the fixture's `self/exercise` row becomes a config
error — a fixture change, hence the ⚖ rather than a silent decision.

**⚖-R50 — the wire value for the phase road.** ⚖-R2 mints a third reason a light can be grey —
the build deliberately did not evaluate the adapter — and the artifact vocabulary had no word for
it: both P0 experiment arms mapped it to `by-failure` plus a warning, which lies in the wire data
("the tooling broke" for items whose tooling was never run). Options: (a) keep two values and
document the mapping; (b) add `not-evaluated` as a third `grey_reason`. **Ruled: (b).** The
summary must count a phase gap differently from a tooling failure, and under (a) that distinction
can only be recovered by matching warning prose — making display text load-bearing, which
⚖-R19 exists to prevent. The cost is a wire-vocabulary addition that P1 will mostly retire;
acceptable while `version` is 1 and no external consumer exists.

**⚖-R51 — one word for grey in every detail line.** As woven, the by-choice detail line read
"not monitored" while the legend and status word are "unmonitored" — two display words for one
status, never reconciled (found by the one-shot arm). Options: (a) keep both; (b) the detail
line's status word is always the display word `unmonitored`, with the reason as its own
following segment. **Ruled: (b).** The reader matches the detail line against the legend, and
the glossary's one-definition-no-synonyms rule applies with extra force to strings a reader must
visually join.

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-DATA-GREY-REASON — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `unmonitored-by-choice` | PASS | — |
| `unmonitored-not-evaluated` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-STATUS-MANUAL-VALUES — the manual adapter's vocabulary

`manual:` accepts exactly `green`, `yellow`, `red` (lowercase). **There is no `manual: grey`.**
The way to be ⚪ is to omit `status:` entirely — grey means "unmonitored", and a hand-set grey
would conflate "deliberately unmonitored" with "forgot to wire the adapter". An item the person
deliberately leaves unmonitored declares no adapter, and its grey is then true.

| row id | inputs | expected |
|---|---|---|
| manual-lowercase-only | `manual: Green` | config error |
| manual-grey-rejected | `manual: grey` | config error, pointing at omitting `status:` |

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-DATA-STATUS-MANUAL-VALUES — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `manual-grey-rejected` | PASS | — |
| `manual-lowercase-only` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-NO-AGGREGATION — no roll-up, ever

Statuses exist **per item only**. The page computes and displays no ring-level or page-level
aggregate: no "worst-of" ring tint, no overall score, no centre summary light. "The innermost
ring must hold for the outer ones to matter" is **reading doctrine for the human**, not a
computation — a 🔴 in ring 1 does not recolor, dim, or flag outer rings.

A rolled-up status is a fabricated status: no adapter stands behind it, so it cannot be traced,
tested, or acted on. Worst-wins in particular trains the reader to ignore a permanently-red
area, which is the opposite of what the page is for.

| row id | inputs | expected |
|---|---|---|
| inner-red-outer-untouched | `self/sleep` 🔴, `partner/date-night` 🟡 | outer cells keep their own resolved colours |
| fully-grey-ring | a ring whose items all lack adapters | the whole band renders ⚪; no special treatment |
| centre-carries-no-status | any config | the centre disc carries name, stamp and counts, never a light (⚖-R9) |

<details class="evidence-block">
<summary>Evidence: 2 test case(s) — alex</summary>

**Requirement:** CIR-DATA-NO-AGGREGATION — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `centre-carries-no-status` | PASS | — |
| `inner-red-outer-untouched` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-RESOLUTION-TIME — statuses resolve at bake time only

Statuses are resolved **when the bake runs** and frozen into the artifact. The page is a pure
renderer of baked verdicts: no adapter code, no date math, no re-evaluation on load.

| row id | inputs | expected |
|---|---|---|
| page-never-reevaluates | artifact says 🟡; viewer opens the page days later | still 🟡 — the generated-at stamp (`CIR-RENDER-GENERATED-AT`) is the honesty mechanism, not live recomputation |
| p0-manual-roundtrip | P0 bake over a `manual:`-only config | statuses pass through unchanged into the artifact |
| one-reference-date-per-bake | two freshness items in one bake | both age against the same reference date (`CIR-ADAPT-REFERENCE-DATE`) |

<details class="evidence-block">
<summary>Evidence: 3 test case(s) — alex</summary>

**Requirement:** CIR-DATA-RESOLUTION-TIME — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `one-reference-date-per-bake` | PASS | — |
| `p0-manual-roundtrip` | PASS | — |
| `page-never-reevaluates` | PASS | — |

[View full report](../../specs-site/evidence)

</details>

## CIR-DATA-DETAIL-LINE — what hover shows

Every item resolves a detail line: the guardrail (if any), the status word, the last-data date
(if the adapter has one), the note (if any), and the failure reason (if any). Order is fixed so
the eye lands in the same place on every item. The line is composed **at bake time** and
carried as one string (⚖-R20), so print and no-JS paths render it without composing anything.

| row id | inputs | expected |
|---|---|---|
| full-detail-line | guardrail + freshness adapter with a date | "guardrail · status · last data YYYY-MM-DD" |
| no-guardrail | item without `guardrail` | line starts at the status; no empty separator |
| manual-item-has-no-data-date | `manual: green` | no date segment — printing the bake date here would imply a freshness the config does not have |
| failure-reason-is-shown | command timed out | line ends with the reason, not a stack trace ([`CIR-BAKE-EXPOSURE`](data-json.md)) |
| detail-line-is-plain-text | any item | no markup; the same string serves hover, the accessible table, and print |

<details class="evidence-block">
<summary>Evidence: 4 test case(s) — alex</summary>

**Requirement:** CIR-DATA-DETAIL-LINE — **World:** alex

| Case ID | Status | Detail |
|---------|--------|--------|
| `detail-line-is-plain-text` | PASS | — |
| `full-detail-line` | PASS | — |
| `manual-item-has-no-data-date` | PASS | — |
| `no-guardrail` | PASS | — |

[View full report](../../specs-site/evidence)

</details>
