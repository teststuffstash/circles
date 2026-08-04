# Downstream proxy comparison — opus arm

Arm slug: `opus` · Branch: `research/issue-1-opus` · PR: #3

Spec tree read end-to-end as the P0 build contract (P0 scope from `process/phases.md`). A
builder asked to ship P0 — bake exists, `manual:` adapter only, other adapters ⚪ + warning,
stale banner shipped, page renders the fixture person, existing deploy pipeline carries it.

## Verdict (counts: blockers / judgment calls / minors / answered-by-⚖)

**0 / 4 / 3 / 33**

All 33 ⚖ ambiguities from `open-questions.md` carry explicit recommendations that the spec
encodes — the builder can follow them without re-asking. Every gap below is what remains
after the ⚖ mechanism has done its work.

---

## Blockers — 0

**None.** Every product decision a builder would need to make before shipping P0 is either
specified in a decision table (fully testable), answered with an ⚖ recommendation the builder
can follow, or deferred to P1+ with a named growth path. No requirement is left blank or
contradictory.

This is a spec tree a builder can implement P0 from, one decision at a time, without
interrupting anyone.

---

## Judgment calls — 4

Questions where the spec gives sufficient constraint that P0 is buildable, but the builder
would silently pick a product-facing value or architecture with no spec guidance on which
choice is correct.

### 1. Bake implementation language and toolchain

**Where:** The entire `data/` tree (bake contract), `process/phases.md` (P0 bake exists), the
existing `devbox.json`, `scripts/`, and `Dockerfile`.

**The gap:** The spec describes what the bake does (read `circles.yaml`, validate, resolve
statuses, write `data.json` + `index.html` + detail pages) but never states what
language/runtime implements it. The devbox has `python@3.11` + `uv` as its only language
tooling, but no Go, Node.js, or TypeScript — and `public/index.html` is currently a vanilla
HTML hello page. The builder must decide the stack (Python CLI script? Python with Jinja2 for
HTML generation? Something else?) with no spec statement that constrains or guides the choice.
A wrong choice here (e.g. Python if the page-rendering eventually needs heavy SVG libraries)
could be costly.

**Can build P0 without asking?** Yes — Python is available and adequate for P0's scope. The
builder can proceed, but the language choice is a product-architecture decision the spec does
not address.

### 2. Exact SVG arc geometry parameters

**Where:** `render/sunburst.md` (CIR-RENDER-*- requirements).

**The gap:** The spec gives excellent geometric constraints — non-increasing radial thickness
(`CIR-RENDER-INNER-LEGIBILITY`), minimum arc angle (`CIR-RENDER-MIN-ARC`), centre hole exists
(`⚖ CIR-Q-22`), visible boundaries between rings and items, capacity at 4 rings × ~8 items.
But the builder must pick the concrete values:
- Ring inner/outer radii as a function of the number of rings
- Exact arc gap (in SVG units) between rings and between items
- Centre hole diameter (it must fit the person's name, stamp, summary)
- Exact minimum arc angle in degrees
- Exact minimum font size
- Label positioning algorithm (horizontal text, radial text, or arc-following)

Each choice affects the visual result at the reference viewport (1280×800) and at A4
(portrait). A builder can pick reasonable values that satisfy all the constraints, but they
are silently deciding what the page looks like.

### 3. Exact colour palette hex values

**Where:** `render/color.md` (CIR-RENDER-STATUS-ENCODING), ⚖ CIR-Q-25.

**The gap:** The spec requires a CVD-safe four-colour palette (🟢🟡🔴⚪) with a non-colour
channel per status (glyph in the arc). It requires ≥4.5:1 contrast and greyscale
distinguishability. But the exact hex values are unstated — the builder must select four
specific colours that satisfy all constraints. This is a product-visibility decision (the
whole page is a colour code) with real impact on readability, accessibility, and aesthetics.

### 4. Client-side JavaScript architecture

**Where:** `render/interaction.md` (CIR-RENDER-DETAIL-REVEAL, CIR-RENDER-CLICK),
`render/color.md` (CIR-RENDER-STALE-MARK), ⚖ CIR-Q-28.

**The gap:** The stale-bake banner (required in P0 per `CIR-PROC-PHASE-P0`) compares the
viewer's clock against `generated_at` via client-side JS per ⚖ CIR-Q-28. The detail overlay
(hover/focus/tap) also needs JS. The spec says "hand-rolled inline SVG" with "no library"
(⚖ CIR-Q-19) and no external dependencies (CIR-RENDER-NO-EGRESS). The builder must decide:
- Single inline `<script>` tag with vanilla JS, or a module pattern?
- How is the stale comparison structured — polling, on-load only?
- Overlay rendering — DOM manipulation or overlay on the SVG itself?
- State management for open/close of detail overlays?
- Touch interactions on phone — tap detection, dismiss handling?

All buildable without asking, but the architecture is a silent product choice that affects
maintainability and future feature additions.

---

## Minors — 3

Questions that are genuinely nice to clarify but would not block or meaningfully bias a P0
build.

### 1. Detail page shape deferred to P2

**Where:** `render/detail-page.md`, ⚖ CIR-Q-29, CIR-Q-30, CIR-Q-31.

**The gap:** The detail page is P2 and the spec explicitly defers its full shape ("specified
now only far enough to keep P0/P1 decisions from foreclosing it"). The builder knows not to
build it in P0. But the spec's minimal outline — one baked file per item, a separate `metric:`
block, events from markdown tables — leaves significant contract details unresolved
(column names, multi-file support, metric adapter interface). These will need to be specified
before P2 starts.

### 2. Fixture label numerals conflict with derived ring numbering

**Where:** `data/circles-yaml.md` (CIR-DATA-CONTENT), `render/sunburst.md`
(CIR-RENDER-RING-ORDER), `fixtures/alex/circles.yaml`.

**The gap:** The fixture person hard-codes ordinal numerals in ring labels (`"① Self"`,
`"② Partner"`, etc.). The spec says "the renderer numbers rings 1..n outward; labels do not
carry numerals." The spec flags this as a recorded follow-up (not editable by this pass). A
builder would need to fix the fixture when implementing the ring-numbering requirement. Not a
P0 blocker because P0 could render the fixture as-is and defer numbering, but the spec says
it's a P0 requirement.

### 3. Missing fixture example for `note:` + no adapter

**Where:** `data/circles-yaml.md` (end of page, proposed fixture rows),
`data/status-resolution.md` (CIR-DATA-GREY-REASON).

**The gap:** The spec proposes but does not commit a fixture row where an item has `note:`
and no adapter — the example that visually distinguishes "unmonitored by choice" from
"unmonitored by failure." The builder implementing grey-reason rendering (CIR-DATA-GREY-REASON
and CIR-RENDER-GREY-VISIBLE) would benefit from this fixture being present at test time. A
minor gap: the builder can create their own test data.

---

## Answered by ⚖ — 33

Every one of the 33 ⚖ ambiguities in `open-questions.md` carries an explicit recommendation
that the spec encodes in the surrounding requirements. The builder following the spec already
has a decision to implement, even when the author flagged the question as unresolved. The ⚖
mechanism worked exactly as designed for all entries:

| ⚖ ID | Recommendation (what the spec encodes) |
|---|---|
| Q-01 | Closed schema; unknown key = config error |
| Q-02 | One integer per file |
| Q-03 | Same id in two rings = two independent items |
| Q-04 | All-or-nothing `share` per ring; mixing = config error |
| Q-05 | File-level timezone only |
| Q-06 | Bake from P0; `manual:` only; other adapters → ⚪ + "not evaluated" |
| Q-07 | Infer unmonitored from absence; `note:` carries the why |
| Q-08 | `age > threshold` — age 7 with `yellow_after: 7` is still 🟢 |
| Q-09 | Calendar days in the config's timezone |
| Q-10 | ISO-8601 only, in file text |
| Q-11 | Anywhere in the text; newest non-future wins |
| Q-12 | Cap exists; exceeding = ⚪ + warning; 1 MB / 100 files recommended |
| Q-13 | Status word only on stdout |
| Q-14 | 5 s per-item / 5 min total defaults; `timeout:` key when needed |
| Q-15 | In-process built-ins + `command:` as third-party story |
| Q-16 | Inline in HTML + sibling `data.json` |
| Q-17 | Keep the lights + banner + stale treatment |
| Q-18 | Per-config `stale_after_hours`; 36 h recommended |
| Q-19 | Hand-rolled inline SVG arcs, no library |
| Q-20 | Non-increasing radial thickness outward with a floor |
| Q-21 | Warning; page still drawn |
| Q-22 | No rollup; hole = name + stamp + summary |
| Q-23 | Reference viewport 1280×800; phone minimum 360×640 |
| Q-24 | `@page { size: A4 portrait }` |
| Q-25 | CVD-safe palette + glyph; hues unruled |
| Q-26 | Banner + desaturation + hatch |
| Q-27 | Authored `link:` wins; detail page reachable from overlay |
| Q-28 | JS computes the banner; stamp always visible in words |
| Q-29 | One baked file per item |
| Q-30 | Separate `metric:` block (for P2); metric never sets the light |
| Q-31 | Dedicated `events:` path, `date`+`event` columns (for P2) |
| Q-32 | Run in kind where cheap, otherwise system testing |
| Q-33 | Private job publishes artifact the chart mounts (for P1+) |

---

## Answered well — no question needed

Several areas of the spec are so well-structured that a builder would not need to stop at all.
These are the strongest parts of this arm:

### The status resolution decision table (`data/status-resolution.md`)

18 rows covering the full adapter-to-status mapping, including the deliberate asymmetry
(known-bad word from a `command:` → ⚪ + warning; same word from `manual:` → config error),
the "no adapter → ⚪ by-choice" baseline, the "adapter not implemented → ⚪ + warning" P0
behaviour, and the critical "never carry the last light forward" rule. Every row is a
testable assertion. A builder could code this table directly as test cases and then implement
against them.

### The freshness arithmetic (`data/freshness.md`)

The decision table for `age > threshold` boundary is pinned by six concrete rows (ages
0/6/7/8/30/31). The "impossible date ignored with warning", "future date ignored", and
"narrow parser" rules are each decision-tabled. The calendar-day arithmetic (DST-safe, host-TZ-independent) is specified with concrete examples. A builder never wonders what
"days old" means.

### The stale bake defence (`data/data-json.md`)

Nine rows covering fresh → banner → "lights are history" → "never turn stale items red" →
"manual items are stale too" → "clock-skewed future stamp treated as stale". Every edge
case is a row. The "this is not a trade-off" language in the `Dangerous-green` doctrine and
the specific rejection of "carry yesterday's light forward" as "the most attractive
dangerous-green" gives the builder clear design intent, not just a table.

### The accessible equivalent as four-in-one (`render/color.md`)

The spec doesn't treat accessibility as an afterthought — it describes the table
(CIR-RENDER-A11Y-TABLE) as simultaneously serving screen readers, no-JS rendering, print
detail, and sliver labelling. The five requirements for that table are all concrete and
testable. This unified design is stronger than bolting on each concern separately.

### The phase boundaries (`process/phases.md`)

The P0/P1/P2 boundaries are the cleanest part of the tree. P0 explicitly says what it owns
(bake exists, `manual:` only, stale banner) and what it does not (nightly schedule, other
adapters). The CIR-PROC-PHASE-P0 section resolves the goal's inherent tension ("hand-set
statuses" vs. a fixture person with `freshness:` and `command:` items) by encoding bake-from-P0
with adapters-that-are-not-implemented → ⚪. The "P0 configs stay valid at P1" row and the
"P1 adds no config keys" row together make the phase boundary invisible to the person writing
the config — the cleanest possible contract.

---

## Method notes

**What was read:** The full `specs/` tree of the `research/issue-1-opus` branch (9 files in
`data/`, 6 files in `render/`, 2 files in `process/`, plus `README.md`, `glossary.md`, and
`open-questions.md`). Also examined `fixtures/`, `scripts/`, `chart/`, `public/`, `Dockerfile`,
`devbox.json`, `devbox.lock`, and `CLAUDE.md` for build-context that a real builder would have.

**What was deliberately not read:** Issue #1 (the original spec goal), PR #3's body (the opus
arm's self-reported counts), the other three arm branches (`research/issue-1-kimi-k3`,
`research/issue-1-deepseek-v4-flash-0731`, `research/issue-1-mimo-v2.5-pro`), the
`specs/open-questions.md` index pages of other arms, any documentation or trackers in
`/work/context/homelab/` (meta-state, TICK-LOG, retros, follow-ups), and any PR bodies.

**P0 scope assumed from the spec:** The bake exists and runs at build time, `manual:` adapter
only is implemented, other adapters resolve to ⚪ + "not evaluated in this build", the stale
banner is shipped, the page renders the fixture person with all four status colours, the
accessible table is present, and the deploy pipeline carries the baked page. No scheduler,
no nightly bake, no freshness/command adapters implemented.