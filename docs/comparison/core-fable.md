# Core metric — spec-arm comparison (judge: fable)

Mission: [#6](https://github.com/teststuffstash/circles/issues/6) · goal under comparison:
[#1](https://github.com/teststuffstash/circles/issues/1) · arms: `opus`, `kimi-k3`,
`deepseek-v4-flash-0731`, `mimo-v2.5-pro`.

This is a **cherry-pick map, not a ranking**. The operator merges pages across arms; "arm X wins"
is not an output of this document. Scores exist only to justify per-page picks.

## Blind decision-point checklist (phase 0)

Built from goal issue #1 + `origin/master` (`specs/README.md`, `specs/data/circles-yaml.md`,
`specs/glossary.md`, `fixtures/alex/**`, `chart/**`, `scripts/ci.sh`, `public/index.html`,
`devbox.json`) **before opening any arm branch**. This is the independent coverage rubric: every
point below is a place where the goal issue leaves a real decision open — a contradiction, an
unstated constraint, or a judgment call. It is deliberately not a list of "topics the spec should
cover"; restating the issue covers topics and still scores zero here.

Legend: **[C]** contradiction inside the goal · **[U]** unstated constraint the product cannot be
built without · **[J]** judgment call the goal defers · **[S]** defect already present in the seed
repo (master) that the spec pass should have caught.

### Area DATA — config + status resolution

| id | decision point | kind |
|---|---|---|
| DP-01 | Threshold boundary: at *exactly* `yellow_after` days, is the item 🟢 or 🟡? (same at `red_after`) — inclusive/exclusive, the classic off-by-one, and directly testable | U |
| DP-02 | Timezone/DST anchoring of "days old": whose clock, and are "days" calendar days or 24h spans? (seed ⚖'s it) | J |
| DP-03 | Date formats recognized inside a freshness source, and *where* in the file a date may appear (line prefix, anywhere, frontmatter) — fixture uses `- YYYY-MM-DD — …` bullets (seed ⚖'s it) | U |
| DP-04 | Future-dated entries: a source line dated tomorrow — freshest, ignored, or clamped/warned? | U |
| DP-05 | `share` weights: must they sum per ring, and what happens when some siblings set `share` and others don't (mixed)? (seed ⚖'s it) | J |
| DP-06 | Sibling ordering within a ring: config order, alphabetical, or by status severity? Fixture's `◀ Nova` / `Kit ▶` labels encode an *adjacency intent* that only config order preserves (seed ⚖'s it) | J |
| DP-07 | Two adapters declared on one item (`manual:` + `freshness:`) — schema error, or precedence? Seed says "exactly one" but not what violating it does | U |
| DP-08 | Glob matching zero files vs. a file that exists but contains no parseable date — same ⚪+warning, or distinguishable? | U |
| DP-09 | `yellow_after` ≥ `red_after` (misconfiguration) — validation error, or resolve-and-warn? | U |
| DP-10 | `command:` execution contract: working directory (fixture's `./notes/plants-status.sh` is relative to the config dir, never stated), timeout, environment, stdout matching (case/whitespace), stderr handling | U |
| DP-11 | `command:` exit 0 but unparseable stdout — ⚪+warning (tooling broke) or a hard error? Seed only rules on exit≠0 | U |
| DP-12 | `command:` is arbitrary code execution against a person's machine/bake job — trust boundary, sandboxing, secrets. The goal introduces the escape hatch and says nothing about who may write one | U |
| DP-13 | `id` uniqueness scope: globally unique or per-ring? IDs are the anchor tests and `data.json` key off | U |
| DP-14 | Whole-file failure (unparseable `circles.yaml`, schema violation): the ⚪+warning doctrine is stated per *item* — the goal never rules on config-level failure. Does the page render partially or not at all? | U |
| DP-15 | Degenerate configs: zero rings, a ring with zero items, a single item in a ring (full 360° arc) | U |
| DP-16 | `link:` value space: `url-or-path` — how does a path resolve from a statically-served page? | U |

### Area STATUS — semantics beyond the per-item light

| id | decision point | kind |
|---|---|---|
| DP-17 | Do rings themselves have a colour? The goal says "**every cell** is colored by its status light" while rings are composed *of* item arcs — is there a ring-level summary arc, and if so is it derived (worst-child? weighted?) or configured? The single biggest structural gap in the goal | C |
| DP-18 | Does ⚪ participate in any aggregation, and how? (worst-of over {🟢🟡🔴⚪} has no total order — ⚪ is not "between" anything) | U |
| DP-19 | "Triage reads inward-first" — doctrine only, or a computed/testable output (an ordered act-on-this-first list)? | J |
| DP-20 | Build warnings: *where do they surface*? `data.json` field, build log, or visibly on the page? The goal mandates warnings but names no destination — and any on-page surface competes with the one-screen budget | U |
| DP-21 | Meta-freshness: `data.json` carries a generated-at stamp, but the goal gives it no semantics. Bake hasn't run in N days → is the whole page stale, and does that show? (Note: this is the one legitimate case for a non-item-level signal, and it must not be 🔴 by the same "tooling ≠ act" rule) | U |
| DP-22 | The ⚪ surface "must be readable at a glance" — as an aggregate property (how much of the picture is unmonitored), not just per-arc contrast. Is there a testable measure? | J |

### Area RENDER — geometry, legibility, interaction

| id | decision point | kind |
|---|---|---|
| DP-23 | "One screen" against *which* viewport? A floor (min width/height) must exist or the requirement is untestable | U |
| DP-24 | One-screen vs. "phone-first read-only viewing is the later exposure path": a layout that fits one desktop screen and one A4 does not fit a 390px phone. Is the phone a P0 constraint or explicitly deferred? | C |
| DP-25 | A4 orientation (portrait/landscape), margins, and whether print is a separate stylesheet or the same layout | U |
| DP-26 | **Traffic lights vs. greyscale print**: 🟢🟡🔴 collapse to near-identical greys on a mono printer, so "prints legibly to a single A4" and "colored by its status light" are in direct tension. Needs a redundant channel (pattern/label/lightness ladder) | C |
| DP-27 | Colourblind safety of the four-status palette (red/green deuteranopia is the majority case for a red/green traffic light) | U |
| DP-28 | Non-colour status encoding for screen readers / a11y — the same redundant-channel decision as DP-26/27 arriving from the other side | U |
| DP-29 | "One **self-contained** HTML page" vs. a sunburst library (Plotly ≈ 3MB+): the library must be vendored/inlined (no CDN, since a self-contained page must render offline) — an unstated constraint that materially bounds the library choice | C |
| DP-30 | Library selection criteria made concrete (Plotly acceptable / D3 / ECharts "if layout fights back") — what test decides "layout fights back"? | J |
| DP-31 | Label legibility inside thin arcs: rotation, truncation, ellipsis, minimum arc angle, and what happens to a ring with a dozen items | U |
| DP-32 | Ring thickness policy (equal bands vs. inner-thicker) and whether rings always span the full 360° | J |
| DP-33 | The centre hole: what occupies it (person name, legend, overall state, nothing) — the goal specifies `person:` but never places it | U |
| DP-34 | Legend: required? Where? Does it count against the one-screen/A4 budget? | U |
| DP-35 | Hover has no touch equivalent — "hover = detail line" directly contradicts the phone read-only path; needs a tap-reveals-then-tap-navigates rule or an always-visible alternative | C |
| DP-36 | Click precedence: "jump to the item's link, **or** open its detail page" — which wins when both exist, and what happens when neither does? | C |
| DP-37 | The detail page vs. "**don't design a multi-page app**" and "one self-contained HTML page": is the detail view a modal/overlay in the same document, a second document, or a route? | C |
| DP-38 | `data.json` schema: exact shape, whether it carries *structure* (rings/items/labels/guardrails) or only statuses — the page is "client-side over baked data", so structure must be baked too, but the goal lists only "statuses, detail lines, generated-at" | U |
| DP-39 | `data.json` versioning / forward-compat, and whether the page validates it before rendering | U |
| DP-40 | Annotated timeseries (P2): the intervention-events markdown table's location and column schema, and how a detail view is bound to an item | U |

### Area PROCESS — pipeline, deploy, testing, conventions

| id | decision point | kind |
|---|---|---|
| DP-41 | **The P0 build seam**: P0 has "statuses hand-set in config" and the glossary says "P0 has no bake" — yet the page renders from `data.json`. So *something* converts `circles.yaml` → `data.json` at P0, or `data.json` is hand-authored. The goal never closes this and it is the first thing an implementer hits | C |
| DP-42 | Where does a **real** person's `circles.yaml` live and how does it reach the image? CLAUDE.md forbids committing real data here; the chart mounts nothing (`values.schema.json` has no data hook) and the Dockerfile bakes `public/`. Deploy-time content has no declared path | U |
| DP-43 | If content is deploy-time, what triggers a rebuild/redeploy on content change, given `deploy.yaml` stamps chart version == appVersion == image tag? | U |
| DP-44 | **Exposure/authn**: "the person and people they trust can see it" — the chart has a Service and no Ingress, and a life-status page is sensitive. Who can reach the deployed page is undecided | U |
| DP-45 | P1 bake job contract: the goal says the job "runs elsewhere; this repo owns the code it runs" — inputs, outputs, exit codes, where `data.json` is published, and how failure is reported back | U |
| DP-46 | Adapter plug-in seam: "design the adapter interface so [contributed built-ins] plug in **without touching the page**" — registration, discovery, and `circles.yaml` schema evolution as a testable contract | U |
| DP-47 | Test tiers (unit / system-on-kind / e2e) mapped to *actual* commands and to `scripts/ci.sh`, which is declared "the one place the gate grows"; `kind` is already in `devbox.json` | U |
| DP-48 | The decision-table→test linkage made mechanical: row description **is** the test id, verbatim — how that is enforced rather than hoped for | J |
| DP-49 | Which parts of the product run where (bake language/runtime) — `python@3.11` + `uv` are already pinned in `devbox.json`, so the repo has already half-decided | J |
| DP-50 | **Time-decaying fixture**: `fixtures/alex/notes/sleep-log.md` carries hard dates (2026-08-01…) and is the "freshness inside window → 🟢" key example with `yellow_after: 7`. The committed fixture silently flips 🟢→🟡→🔴 as the calendar advances; `fixtures/README.md` says tests "build inputs FROM these tables at runtime" and the sleep log itself hints dates may be rewritten. The spec must rule that freshness examples are *relative*, or the key example rots | S |
| DP-51 | **The glossary already violates its own rule**: `specs/README.md` mandates "one definition per term, no synonyms", and `glossary.md`'s first entry is "**circle / ring**" — two names, one definition. The goal issue then adds a third surface word, "cell" ("every cell is colored"). The spec pass should have picked one and said so | S |
| DP-52 | `CIR-<AREA>-<NAME>` id grammar: the area vocabulary is never enumerated, so parallel authors invent divergent areas and ids stop being stable anchors | U |
| DP-53 | Whether requirements carry phase (P0/P1/P2) markers at all — the mechanism for "anticipate, not overreach" is itself undecided, and it is what keeps P2 detail from being written as though it were settled | J |
| DP-54 | "Verified-ness is derived, never declared" — no ✓/🚧 coverage markers anywhere in the authored tree (a compliance check, and an easy one to fail while writing status tables) | U |

**54 decision points.** Areas: DATA 16 · STATUS 6 · RENDER 18 · PROCESS 14.

## Master decision-point matrix

Built by inventorying each arm's tree (`git show`/`git archive` from `origin/research/issue-1-*`;
no arm branch was checked out) and deduping every requirement and ⚖ against the Phase-0
checklist. **No PR body was read before this matrix was complete.**

Tree sizes, recounted from the trees (PR bodies self-report; these are mine):

| arm | pages | requirement ids | ⚖ entries | decision-table rows | files touched |
|---|---|---|---|---|---|
| `opus` | 15 | 64 | 33 (`CIR-Q-01…33`, indexed) | ~412 | `specs/` only |
| `kimi-k3` | 13 | 68 | 26 (`⚖ AMBIGUITY: <SLUG>`) | ~232 | `specs/` only |
| `deepseek-v4-flash-0731` | 8 | 37 | 24 (`⚖ <AREA>-<n>`) | ~51 | `specs/` only |
| `mimo-v2.5-pro` | 12 | 42 | 21 (`⚖ AMBIGUITY: <text>`) | ~168 | `specs/` only |

Every arm's diff against **its own merge base** touches `specs/` and nothing else. (Diffing an
arm against current `master` shows spurious `.agents/` and `.gitleaks.toml` changes — those are
merge-base artifacts from master's later recipe commits, **not** scope violations. Checked, so
no arm is scored for them.) No arm carries a ✓/🚧 coverage marker: all four pass DP-54.

Legend: **✓** covered as a decided requirement · **⚖** covered *and* recorded as an ambiguity ·
**~** touched but weak/partial (not testable as written, or named without a rule) ·
**—** missed · **!** covered but the encoded ruling is itself defective (footnoted).

| id | decision point | opus | kimi-k3 | deepseek | mimo |
|---|---|---|---|---|---|
| DP-01 | threshold boundary inclusive/exclusive | ⚖ | ✓ | ✓ | ⚖ |
| DP-02 | timezone/DST anchoring of "days old" | ⚖ | ⚖ | ⚖ | ⚖ |
| DP-03 | date formats + where in the file a date may sit | ⚖⚖ | ⚖ | ⚖ | ✓ |
| DP-04 | future-dated entries | ✓ | ⚖ | ⚖! [^ds-future] | — |
| DP-05 | `share` sums / mixed declared+undeclared | ⚖ | ⚖ | ⚖~ [^ds-share] | ⚖⚖ |
| DP-06 | sibling order **and** start angle/direction | ~ [^op-angle] | ⚖ | ⚖~ | ⚖⚖! [^mi-nova] |
| DP-07 | two adapters on one item | ✓ | ✓ | ✓ | ✓ |
| DP-08 | glob-matches-nothing vs file-with-no-date | ✓ | ⚖ | ~ | ✓ |
| DP-09 | `yellow_after` ≥ `red_after` | ✓ | ✓ | ✓ | ✓ |
| DP-10 | `command:` exec contract (cwd, timeout, env, stdout) | ✓✓ | ✓✓ | ~ | ⚖! [^mi-cwd] |
| DP-11 | exit 0 with unparseable stdout | ✓ | ✓ | ✓ | ✓ |
| DP-12 | `command:` as arbitrary code / trust boundary | ✓ | ✓ | — | — |
| DP-13 | id uniqueness scope + the item ref | ⚖ | ✓ | ⚖✗ [^ds-fab] | — |
| DP-14 | whole-file config failure; what stays served | ✓✓ | ✓✓ | ✓ | ✓ |
| DP-15 | degenerate configs (0 rings, empty ring, 1 item) | ✓ | ⚖ | ⚖ | ✓ |
| DP-16 | `link:` value space + path resolution | ✓ | ✓✓ | — | ~ |
| DP-17 | **do rings have a colour / ring rollup** | ⚖ | ✓ | — | — |
| DP-18 | ⚪ in aggregation (no total order over 4 states) | ✓ | ✓ | — | — |
| DP-19 | triage inward-first: doctrine or computed? | ✓ | ✓ | ~ | ~ |
| DP-20 | **where build warnings surface** | ✓✓ | ⚖✓ | — | ~! [^mi-warn] |
| DP-21 | meta-freshness: the bake itself going stale | ⚖✓✓ | ⚖ | ~ | ~ |
| DP-22 | the ⚪ surface as an aggregate property | ✓ | ✓ | — | — |
| DP-23 | which viewport is "one screen" | ⚖ | ⚖ | ⚖ | ~ |
| DP-24 | one-screen vs phone-first (contradiction) | ✓ | ⚖ | ⚖ | ~ |
| DP-25 | A4 orientation, margins, print stylesheet | ⚖ | ✓ | ⚖ | ⚖⚖ |
| DP-26 | **traffic lights collapse in greyscale print** | ✓✓ | ⚖✓✓ | ⚖~ | ⚖✓ |
| DP-27 | colourblind safety of a red/green light | ✓ | ⚖✓ | ⚖ | ⚖ |
| DP-28 | non-colour channel / screen-reader path | ✓✓✓ | ✓✓ | ⚖~ | ✓ |
| DP-29 | "self-contained" vs a ~1 MB chart library / no CDN | ✓✓✓ | ✓✓ | ~ | — |
| DP-30 | **renderer choice made concrete** | ⚖✓✓ | ⚖✓✓ | ⚖~ | ⚖ |
| DP-31 | thin-arc label legibility / min arc | ✓✓ | ✓✓ | ⚖~ | ⚖ |
| DP-32 | ring radial thickness policy | ⚖ | ✓ | — | — |
| DP-33 | what fills the centre hole | ⚖ | ✓ | — | ~ |
| DP-34 | legend: required, where, in the budget? | ✓ | ✓✓ | ⚖ | ✓ |
| DP-35 | hover has no touch equivalent | ✓✓ | ⚖✓ | ⚖ | ~ |
| DP-36 | click precedence: `link:` vs detail page | ⚖ | ⚖ | ⚖ | — |
| DP-37 | detail page vs "don't design a multi-page app" | ⚖ | ✓ | ⚖✓✓ | — |
| DP-38 | does `data.json` carry structure, not just statuses | ✓✓ | ✓✓ | ✗⚖ [^ds-unenc] | ✓ |
| DP-39 | `data.json` versioning; does the page validate it | ✓ | ✓✓ | ~ | — |
| DP-40 | intervention-events table contract | ⚖ | ✓✓ | — | — |
| DP-41 | **the P0 build seam ("no bake" vs a data.json)** | ⚖✓✓ | ✓✓ | — | ⚖✓ |
| DP-42 | **where a real person's config lives / deploy seam** | ⚖✓✓ | ⚖✓✓ | — | !! [^mi-deploy] |
| DP-43 | does a content change force an image rebuild | ✓ | ⚖✓ | — | — |
| DP-44 | **exposure: who can read the artifact** | ✓✓✓ | ~ | — | — |
| DP-45 | the P1 bake job's contract | ✓ | ⚖✓ | — | ~ |
| DP-46 | adapter plug-in seam as a real interface | ✓✓✓ | ✓✓ | ✓ | ✓ |
| DP-47 | test tiers → actual commands / `scripts/ci.sh` | ⚖✓✓ | ✓✓ | ⚖ | ✓! [^mi-kind] |
| DP-48 | decision-table row → test id, mechanically | ✓✓ | ✓✓✓ | ✓ | ✓ |
| DP-49 | bake runtime/language (devbox already pins python) | — | — | — | ~ |
| DP-50 | **the time-decaying fixture** (`sleep-log.md` rots) | ✓✓✓ | ✓✓ | — | ⚖✓ |
| DP-51 | **glossary's own "circle / ring" synonym violation** | — | — | — | — |
| DP-52 | `CIR-<AREA>` vocabulary never enumerated | ✓ | ✓ | ✓ | — |
| DP-53 | phase markers / the anti-overreach mechanism | ✓✓ | ✓✓ | ✓ | ✓ |
| DP-54 | no ✓/🚧 coverage markers | ✓ | ✓ | ✓ | ✓ |

[^ds-future]: deepseek ⚖ DATA-7 rules a future-dated entry **🟢 + warning (age 0)**. A mistyped
    year (`2027-…`) then pins the item green for a year — the exact dangerous-green both opus and
    kimi identified and rejected. Covered, but the ruling should not be cherry-picked.
[^ds-share]: deepseek ⚖ DATA-3 recommends "relative weights, normalised per ring" *and*
    "no-share items split the remainder" — under normalisation there is no remainder, so the
    mixed case stays undetermined. The ⚖ is real; the encoded rule does not close it.
[^op-angle]: opus fixes ring order and focus order but never states a start angle or sweep
    direction, so "which half is Nova" is unspecified in its tree. kimi and mimo both rule it.
[^mi-nova]: mimo's row reads "Nova = left half, Kit = right half (reading top clockwise)" — but
    clockwise from 12 o'clock puts the *first* item in the **right** half. The row contradicts
    its own convention (and see the fixture-glyph miss below).
[^mi-cwd]: mimo rules `command:` cwd = **repo root**, justified as "the fixture's
    `./notes/plants-status.sh` path assumes repo-relative resolution". It does not: that script
    is at `fixtures/alex/notes/plants-status.sh`, i.e. relative to the *config directory*. Same
    error in `CIR-DATA-FRESHNESS-SOURCE` ("`source:` … relative to the repo root"), which makes
    every fixture freshness source unresolvable. Verified against the committed fixture.
[^mi-warn]: mimo puts build warnings **on stderr** only. Nothing reaches `data.json` or the page,
    so a reader looking at a grey cell cannot learn why — the honest-grey doctrine stops at the
    build log.
[^ds-fab]: deepseek ⚖ DATA-5 states "the goal **explicitly lists** 'items that belong to several
    rings' as an edge to hunt". Issue #1 contains no such text (verified: no match for
    "several rings"/"belong"/"cross-ring"). The requirement it encodes is fine; the citation is
    fabricated.
[^ds-unenc]: deepseek ⚖ INTERACT-4 recommends "(a) fix a minimal schema in the spec now" — and
    then does not. No `data.json` schema exists anywhere in its tree. Two more ⚖s (RENDER-5
    accessible alternative, COLOR-1 hex tokens) likewise recommend something the tree never
    encodes, deferring to "a PR Follow-up" instead.
[^mi-deploy]: `CIR-PROCESS-BAKE-DEPLOY` has the bake write `public/index.html` + `public/data.json`
    which the Dockerfile copies into the image. Applied to a real person, that bakes private life
    data into a public repo's build — the inverse of `CLAUDE.md`'s synthetic-only invariant. Not
    a miss but an actively wrong answer; scored `!!`.

**Recall against the 54-point checklist** (counting ✓/⚖/~ as covered, `—` as missed):

| arm | covered | missed | recall |
|---|---|---|---|
| `opus` | 52 | 2 (DP-49, DP-51) | **96%** |
| `kimi-k3` | 52 | 2 (DP-49, DP-51) | **96%** |
| `mimo-v2.5-pro` | 37 | 17 | **69%** |
| `deepseek-v4-flash-0731` | 36 | 18 | **67%** |

Volume did not drive this. `mimo` (42 requirements) out-recalls `deepseek` (37) by one point
while `kimi` (68 requirements) ties `opus` (64) — and `deepseek`'s 24 ⚖ entries against opus's 33
buy it 18 misses, because several of deepseek's ⚖s are filed on questions the goal already
answers or that its own tree then declines to encode.

## Per-arm scorecard

| metric | opus | kimi-k3 | deepseek-v4-flash-0731 | mimo-v2.5-pro |
|---|---|---|---|---|
| recall vs the 54-point checklist | 52 (96%) | 52 (96%) | 36 (67%) | 37 (69%) |
| unique finds (in no other arm) | 10 | 10 | 4 | 5 |
| false-⚖ (open on something the goal decides, or ⚖ that isn't a fork) | 0 | 0 | 3 | 0 |
| ⚖ whose recommendation the tree never encodes | 0 | 0 | 3 | 0 |
| defective rulings (encoded answer is wrong) | 0 | 0 | 1 | 4 |
| fabricated citations (repo/goal artifacts that don't say that) | 0 | 0 | 1 | 2 |
| testability spot-check (10 sampled rows writable as-is) | 8/10 | 9/10 | 5/10 | 6/10 |
| id-grammar compliance | pass | pass | pass | **fail** |
| verified-ness never declared (DP-54) | pass | pass | pass | pass |
| glossary one-definition-per-term | inherited breach | inherited breach + 0 new | inherited + 1 new | inherited + 2 new |
| overreach (premature P2 depth) | 1, self-limited | 3 | 0 (under-reach) | 2 |
| restatement ratio | very low | very low | moderate | moderate-high |

**Testability spot-check method.** Ten rows sampled per arm across data/render/process; a row
passes if a test could be written from the text alone, using the fixture person as data.

- `opus` — 8/10. The two that fail are browser-dependent (`print without the user changing
  settings`; `labels never overlap` with no config pinned). Notably opus *itself* flags this
  class as unevidenceable under the ruled tiers (`CIR-PROC-BROWSER-EVIDENCE`).
- `kimi-k3` — 9/10. Row slugs make citation mechanical, and
  `CIR-RENDER-COLOR-PALETTE#palette-luminance-ladder` is the single most testable requirement in
  the fan-out: a pure unit test computing luminance from the shipped CSS. The failure is
  `envelope-at-limit` → "renders legibly", which names no observable.
- `deepseek` — 5/10. Several requirements are one normative sentence with no table
  (`CIR-RENDER-A4-PRINT`, `CIR-RENDER-KEYBOARD`), and tables assert unquantified adjectives
  ("distinct from background", "is the priority read").
- `mimo` — 6/10, and **two of the ten are wrong as written**: a test built from
  `CIR-DATA-FRESHNESS-SOURCE#single file exists` fails against the committed fixture (repo-root
  resolution), and one built from `CIR-RENDER-ARC-START#two children with share 0.5` would assert
  Nova on the left, which its own clockwise-from-noon rule puts on the right.

**Convention compliance — the one hard failure.** `mimo` never edited
`specs/data/circles-yaml.md` (byte-identical to the seed stub) while adding
`specs/data/status-resolution.md` under the **same anchor** `CIR-DATA-STATUS-RESOLUTION`. One
requirement now has two anchors on two pages carrying two different tables — a direct breach of
"one requirement, one anchor; IDs are never renamed or reused". It also mints `CIR-PROCESS-*`
where every other arm uses `CIR-PROC-*`, and declares no area vocabulary.

**Cost context** (from the mission issue; feeds $/unique-find, not merit): `kimi-k3` $4.33 —
10 unique finds; `mimo` and `deepseek` under the $2 ESCALATE cap — 5 and 4 unique finds
respectively; `opus` rode the subscription and is not comparable. Per dollar, `mimo` and `kimi`
are close; `deepseek` is the weakest of the metered three.

## Per-page cherry-pick map

Union of every `specs/` page across the four trees, canonicalised. **Structural mismatch warning:
the arms do not agree on the page split** — `deepseek` folds geometry+layout into `geometry.md`
and has no `data-json.md`/`adapters.md`/`phases.md`; `mimo` splits process into `bake.md` +
`testing.md` with no `phases.md`; only `opus` has `open-questions.md` and `detail-page.md`; and
`kimi`/`deepseek`/`mimo` fold the detail page into `interactions.md`. Picking per page therefore
implies picking opus's 15-page split as the skeleton.

| page | take from | why |
|---|---|---|
| `specs/README.md` | **opus** | Only arm enumerating the full area→page ownership table (the DP-52 fix). Graft kimi's row-slug linkage sentence; decide consciously whether to keep opus's added "dangerous-green" tie-breaker doctrine — it is load-bearing for the rest of opus's tree but is not in the goal. |
| `specs/glossary.md` | **kimi-k3** | 110 lines, sectioned domain/adapter/page/process, defines `cell`, `sibling`, `half-arc`, and separates display words from `data.json` wire values. Fix the inherited `circle / ring` synonym on merge (no arm did). |
| `specs/open-questions.md` | **opus** (sole) | The only ⚖ index in the fan-out, and its "three that most change the product" ranking *is* the operator's agenda. Must be re-keyed if ⚖s from other arms are grafted in. |
| `specs/data/circles-yaml.md` | **opus** | `spec_version`, the `<ring>/<item>` ref grammar, id charset, timezone, closed schema. Graft **kimi's `CIR-DATA-SCHEMA-LINK`** (`javascript:`/`data:` rejection) — opus has no link-scheme rule at all. |
| `specs/data/status-resolution.md` | **opus** | The config-error vs adapter-failure split is the page's whole value, plus "a failing adapter never inherits its last light" and the by-choice/by-failure grey reasons. kimi's failure algebra is a clean second. |
| `specs/data/freshness.md` | **opus** (body) | DST rows, future-date handling, source-path sandboxing, ISO-substring rejection. **But its boundary ruling is the 1-of-4 minority** — see ⚖-R1 before merging; flipping it edits three rows. |
| `specs/data/adapters.md` | **opus** | The only real interface contract (injected reference date, adapter-cannot-return-grey, failure isolation, minimal environment). Graft kimi's explicit trust sentence and its 30 s timeout if you want a ruled number now. |
| `specs/data/data-json.md` | **opus** + kimi graft | opus for the artifact shape, stale-bake defence and `CIR-BAKE-EXPOSURE`; **kimi for `CIR-DATA-DATAJSON-VERSION` + `CIR-RENDER-LAYOUT-BOOT-ERROR`** (nobody else specs what the page does when its data is broken). Blocked on ⚖-R2 — the two arms disagree on inline-vs-fetch, and boot-error only exists under fetch. |
| `specs/render/sunburst.md` | **opus** | `CIR-RENDER-RINGS-INDEPENDENT` (with the finding that Plotly structurally cannot draw this model), capacity, min-arc, label budget. **Graft kimi's `CIR-RENDER-GEOM-SIBLING-ORDER`** — opus specifies no start angle or sweep direction, which is a hole a builder hits on day one. Optionally graft kimi's 6×8 content envelope. |
| `specs/render/layout.md` | **opus** | One-screen rows incl. phone/zoom/very-wide, A4 with the browser-header caveat, `NO-EGRESS` argued as privacy first, and an asset budget the gate enforces. Graft **mimo's `@page { margin: 10mm }`** — the only concrete margin spec in the fan-out. |
| `specs/render/color.md` | **kimi-k3** | The luminance ladder with a ≥0.10 pairwise floor and a palette unit test as arbiter is the strongest single artifact anywhere in the fan-out — it turns "prints legibly in greyscale" into arithmetic. **Graft opus's `CIR-RENDER-PRINT-COLOR`** (the `print-color-adjust: economy` default, plus the belt-and-braces "still legible with fills stripped") and **opus's `CIR-RENDER-A11Y-TABLE`**, which serves screen-reader + no-JS + print-detail + sliver-labelling from one artifact. |
| `specs/render/interaction.md` | **opus** | Three ways in / one detail string; keyboard; touch targets; no-JS. Two live conflicts: ⚖-R3 (click precedence) and ⚖-R4 (no-JS floor). |
| `specs/render/detail-page.md` | **opus** (sole page) | Correctly shallow for a P2 surface, and "correlation is not asserted" is a real product rule nobody else states. Take kimi's events-table column contract **only if** you want P2 settled now — opus deliberately left it ⚖ (CIR-Q-31), and the goal says anticipate, don't overreach. |
| `specs/process/testing.md` | **opus** | `CIR-PROC-GATE`'s three spec-tree checks (unique ids, resolving links, every ⚖ indexed) are the only gate a spec-only PR can be judged by *today*, and `CIR-PROC-BROWSER-EVIDENCE` names a real gate-capability gap. **Must-graft: kimi's `CIR-TEST-ROW-LINKAGE` row-slug grammar** — see the cost note below. Graft mimo's dangling-spec-reference gate row. |
| `specs/process/phases.md` | **opus** | P0/P1/P2 boundaries, `CIR-PROC-DEPLOY-SEAM`, and `CIR-PROC-NOT-YET`. Graft kimi's "**Ships:** / **Must not build:**" framing (the crispest anti-overreach device here) and its ⚖ NIGHTLY-PUBLISH-PATH. `mimo/process/bake.md` has one taking: its P0-data-path ⚖. Do **not** take `CIR-PROCESS-BAKE-DEPLOY`. |

**Two costs the map hides, both real:**

1. **ID re-keying.** The arms mint incompatible area vocabularies — opus `DATA/ADAPT/BAKE/
   RENDER/DETAIL/PROC`, kimi `DATA/RENDER/TEST/PHASE`, deepseek `DATA/RENDER/PROC`, mimo
   `DATA/RENDER/PROCESS`. Every kimi graft into an opus skeleton needs its ID rewritten
   (`CIR-RENDER-COLOR-PALETTE` → `CIR-RENDER-*` is fine; `CIR-TEST-*` and `CIR-PHASE-*` are not).
   Since IDs are "never renamed or reused", **fix the vocabulary before the first cherry-pick**,
   not after.
2. **The row-slug convention is not a graft, it is a sweep.** Adopting kimi's
   `CIR-<AREA>-<NAME>#<row-slug>` citation means rewriting the first column of every decision
   table in the merged tree (~400 rows if the skeleton is opus). It is the right convention —
   it makes coverage derivable rather than grep-guessed — but it is hours, not minutes.

## Deduped ⚖ register (ratification agenda)

Ordered by how much the answer changes downstream. "Split" shows how the four arms ruled; a
split is itself evidence the goal left the question open.

| # | question | split | note |
|---|---|---|---|
| ⚖-R1 | **Where does the private config live, and how does its output reach nginx?** | opus + kimi independently recommend the same: a private repo/job publishes an artifact the chart mounts; deepseek and mimo silent (mimo's answer bakes it into the public image) | Nothing here is deployable for its actual purpose until this is ruled. Two arms converged from opposite trees — strong signal. Ratify first. |
| ⚖-R2 | **The P0 build seam**: "P0 has no bake" vs a page that renders from `data.json` | opus + mimo: a minimal bake exists at P0 (`manual:` only; other adapters ⚪ "not evaluated in this build"); kimi: P0 evaluates *everything* at image-build time; deepseek silent | Decides whether the fixture person is legal at P0 and whether P0→P1 is a migration or a no-op. opus's reading keeps every config valid across the boundary. |
| ⚖-R3 | **The renderer**: is Plotly usable at all? | opus + kimi independently: **no** — Plotly's sunburst is hierarchical (sectors bound to a parent's arc) and circles' rings are independent; both recommend hand-rolled SVG. mimo: D3+SVG. deepseek: leave open | The goal names Plotly first, so this needs an explicit operator override. Every other render requirement (print path, focus order, ARIA, asset budget, no-JS) sits on top of it. |
| ⚖-R4 | Inline the data in the page, or fetch `data.json`? | opus: inline + a sibling file (works from `file://`, survives being saved/mailed/printed); kimi: fetch, with a boot-error state and cache revalidation | Decides whether a boot-error state exists at all, whether the page is offline-viewable, and what "one self-contained HTML page" means when the goal also says "one asset + one `data.json`". |
| ⚖-R5 | Detail view: a separate baked page per item, or an in-page overlay? | opus + kimi: separate baked file; **deepseek: in-page overlay**, explicitly framed as resolving the goal's own "detail page" vs "don't design a multi-page app" contradiction; mimo: unaddressed | A genuine contradiction in the goal. deepseek's is the only reading that keeps the single-asset claim literally true; opus's is the only one that keeps one-screen true. |
| ⚖-R6 | Freshness boundary: is age == `yellow_after` still 🟢? | **opus alone says 🟢** (`age > threshold`); kimi, deepseek and mimo all say 🟡 (`age >= threshold`) | 3:1 against the recommended skeleton. Cheap to flip (three rows) but it must be flipped *before* the tests exist. opus's argument — "a person keeping an every-7-days habit on day 7 must not be shown 🟡" — is the better one; the operator should rule, not inherit. |
| ⚖-R7 | Unknown keys in `circles.yaml` | opus: closed schema, any unknown key fails the bake (a tolerated typo is the cheapest route to dangerous-green); kimi: ignore + warn, **except** unknown `status:` adapter keys which fail | Direct conflict, and it decides whether forward-compatible configs are possible. Both reasoned; kimi's carve-out is the subtler answer. |
| ⚖-R8 | Future-dated entries in a source | opus + kimi: ignore future dates, all-future ⇒ ⚪ + warning; **deepseek: treat as age 0 ⇒ 🟢 + warning**; mimo: unaddressed | Ratify ignore. deepseek's ruling makes a mistyped year pin an item green for a year — do not cherry-pick it. |
| ⚖-R9 | Do rings roll up to a status; what fills the centre hole? | opus (⚖) + kimi (decided): **no rollup**; hole carries name/stamp/summary. deepseek + mimo: silent | Two arms converged. opus's reason is the keeper: a rollup is a fabricated status with no adapter behind it, and worst-wins trains the reader to ignore a permanently-red area. |
| ⚖-R10 | Ring radial thickness | opus: non-increasing outward (inner bands thicker, because inside-out puts the most important ring at the smallest radius); kimi: equal thickness (outer rings compensate with arc length) | A real design disagreement with a legibility consequence at A4 size. Nobody else raised it. |
| ⚖-R11 | Click precedence when an item has both `link:` and a detail page | opus: link wins, detail reachable from the overlay; kimi: detail page wins, link offered inside it; deepseek: the popover carries both; mimo: unaddressed | Three arms, three answers. Whatever is ruled, opus's constraint holds: the loser must stay reachable. |
| ⚖-R12 | Mixed declared/undeclared `share` in one ring | opus: config error (all-or-nothing); kimi: undeclared = weight 1; mimo: undeclared split the remaining angle equally; deepseek: underdetermined | Four arms, three-and-a-half answers. opus's is the only rule with no silent resize of a sibling. |
| ⚖-R13 | Empty ring / zero rings | opus: draw an empty band + warning ("a missing band reads as *no such area*"); kimi: validation error; deepseek: omit the ring; mimo: visible empty band | Four arms, three answers. |
| ⚖-R14 | Where build warnings surface | opus + kimi: in `data.json` **and** on the page (count + reachable list); mimo: stderr only; deepseek: unaddressed | The goal mandates the warning and names no destination. Ratify the page surface — otherwise ⚪ is honest but unexplained. |
| ⚖-R15 | Stale-bake banner | opus: banner + desaturation + hatch, threshold from the artifact, clock-skew handled; kimi: **stamp only in v0** — no threshold until P1 declares a cadence | Philosophical split, both defensible. opus's version is the product's own dangerous-green defence; kimi's avoids inventing an expectation P0 hasn't earned. |
| ⚖-R16 | `link:` value space | opus: any url-or-path, relative resolved against the served page; kimi: `https`/root-relative only, `javascript:`/`data:`/`//…` rejected at bake time | Security-relevant. Recommend kimi's. |
| ⚖-R17 | Item-id uniqueness scope | opus + kimi: unique per ring, ref is `<ring>/<item>`; deepseek: globally unique | Decides the ref grammar every test, warning and `data.json` key uses. |
| ⚖-R18 | Timezone anchoring | opus, kimi, deepseek: a per-config `timezone:` (IANA), default UTC; **mimo: UTC-only, defer the field** | 3:1. Ratify the field. |
| ⚖-R19 | `data.json` status wire values | opus + kimi: `green\|yellow\|red\|grey`; mimo: `ok\|attention\|act\|unmonitored` (display words as wire values) | Trivial, but it must be one, and kimi's glossary already separates the two vocabularies. |
| ⚖-R20 | Detail line: baked string or composed at render time? | opus: baked (`detail_line` in the artifact, one string serving hover/table/print); kimi: structured fields only, composed page-side | Decides whether wording is frozen in a data file — matters for print vs screen. |
| ⚖-R21 | `command:` timeout | opus: 5 s/item + 5 min bake, values unruled; kimi: 30 s fixed, config knob deferred; mimo: 30 s configurable per adapter; deepseek: unaddressed | Pick a number now; all three proposals are compatible in shape. |
| ⚖-R22 | **Requirement-ID area vocabulary** | opus `DATA/ADAPT/BAKE/RENDER/DETAIL/PROC`; kimi `DATA/RENDER/TEST/PHASE`; deepseek `DATA/RENDER/PROC`; mimo `DATA/RENDER/PROCESS` | Not a product question, but it blocks the cherry-pick: IDs are "never renamed or reused", so the vocabulary must be fixed *before* the first page lands, not reconciled after. |

## What all arms missed

From the Phase-0 checklist, the items no arm covered — plus two errors visible only across arms.

1. **The glossary violates the rule it sits under (DP-51).** `specs/README.md` mandates "one
   definition per term, no synonyms"; `glossary.md`'s first entry is "**circle / ring**" — two
   names, one definition — and issue #1 adds a third surface word, "cell". All four arms copied
   the entry verbatim. Three then compounded it: kimi added `cell` and `sibling` (defensibly
   distinct), deepseek added `status light` beside `status`, mimo added `traffic light` and
   `bake job` beside `bake`. The spec pass whose stated purpose is finding contradictions missed
   the one sitting in its own conventions file.
2. **Nothing gates the fixture against the authored schema.** No arm proposed a CI check that
   `fixtures/alex/circles.yaml` validates against the schema the specs describe, or that its
   sources resolve. It is the cheapest possible guard against spec/fixture drift — and it would
   have caught mimo's repo-root `source:` rule instantly, since every fixture freshness source
   becomes unresolvable under it. opus came closest (`CIR-PROC-GATE` gates `data.json` against
   its schema) but not the config side.
3. **The fixture's own `◀ Nova` / `Kit ▶` glyphs encode a placement intent nobody reconciled.**
   The arrows point outward-left and outward-right, i.e. Nova on the left half, Kit on the right.
   Clockwise-from-12-o'clock — the convention kimi and mimo both rule — puts the *first* item in
   the **right** half, i.e. Nova right, Kit left. kimi specified the convention without noticing
   the fixture disagrees; mimo asserted the convention *and* "Nova = left half" in the same table;
   opus and deepseek specified no start angle at all. Either the glyphs are decoration (say so)
   or they are a requirement (then the sweep starts counter-clockwise, or at 6 o'clock).
4. **The bake's runtime is already half-decided and nobody said so (DP-49).** `devbox.json` pins
   `python@3.11` and `uv`, and `CLAUDE.md` says this repo owns the code the bake runs. Only mimo
   mentions a runtime at all (an aside about "pytest/jest"). A spec tree that specifies an
   adapter interface without naming the language it is an interface *in* leaves the first
   implementation PR to decide it by accident.

Two near-misses worth recording: `CIR-BAKE-EXPOSURE`-class reasoning (what a public URL leaks)
exists only in opus, and the "does a content change force an image rebuild" question (DP-43)
exists in full only in kimi — each is a single point of failure in the merged tree.

## Confidence & method notes

**What was verified.** Arm trees were read from `origin/research/issue-1-*` via `git archive`
into a scratch directory; no arm branch was checked out over the working tree and no arm branch
was modified. Requirement counts, ⚖ counts, page counts, `✓/🚧` compliance and area vocabularies
were produced by grep over the trees, not taken from PR bodies. The scope check ("only `specs/`
touched") was recomputed against each arm's **own merge base** after the naive
`diff master..arm` produced false `.agents/` hits.

**Fabrication checks I actually ran.** deepseek's ⚖ DATA-5 claim that the goal "explicitly lists"
cross-ring items was tested against the issue body (`grep -i 'several rings|belong|cross-ring'`
→ no match). mimo's repo-root `source:`/cwd rules were tested against
`fixtures/alex/circles.yaml` + the real paths of `notes/sleep-log.md` and `plants-status.sh`.
mimo's "kind available via devbox in this environment" was checked against this ride's platform
card (kind is in `devbox.json`; there is **no docker daemon in the ride**, so the claim is a
binary-present/unusable overclaim — kimi, deepseek and opus each record the CI-only fact
correctly). mimo's labs age arithmetic ("201 days from 2026-08-03") is off by one — 2026-01-15 to
2026-08-03 is 200 days; immaterial to the ruling, recorded for completeness.

**What I could not verify.**
- Every arm's external-knowledge claims — Plotly's hierarchical sunburst model, ECharts'
  multi-series-pie workaround, `print-color-adjust: economy` defaults, WCAG luminance formulae,
  library payload sizes — are reasoned from training knowledge on my side too. I did not fetch
  docs to adjudicate them. Two arms (opus, kimi) label these claims as provenance; kimi does so
  per page. Where opus and kimi *independently* reach the same conclusion (Plotly cannot express
  independent rings) I treat convergence as evidence, not proof.
- kimi's pinned hexes were not recomputed against the WCAG relative-luminance formula. Its own
  requirement makes the test the arbiter, which is the right structure; the ≈ values are the
  author's hand computation and remain unchecked.
- No requirement was executed. Testability is a reading judgment over a 10-row sample per arm,
  not a measured result, and the sample is small enough that ±1 is noise.
- Recall is measured against **my** 54-point checklist, not an objective ground truth. A
  different judge's Phase-0 would shift the denominator; the *ordering* of the arms is more
  robust than the percentages, and the two ~96% arms are tied within the method's resolution.

**Blinding caveat.** Branch names embed model slugs, so this was never blind. Every score above
was computed from the trees before any PR body was opened, and no PR body was read at any point
during scoring — but I knew which arm was which while reading, and the arm identities appear in
the mission issue's arm table. One partial leak to declare: the anomaly circuit-breaker check
(`gh pr list`) at the start of the run surfaced arm PR **titles**, two of which self-report counts
("15 pages, 64 requirements, 33 ⚖"; "13 pages, 68 requirements, 26 ⚖"). I recounted from the trees
regardless and the numbers agreed, which is corroboration rather than independence — the counts
for `opus` and `kimi-k3` should be read as confirmed, not blindly derived. The `deepseek` and
`mimo` counts had no such prior. Treat arm identity as an appendix fact. The one place it could
have leaked is the tie at the top: `opus` and `kimi-k3` land at the same recall, and the map
leans on opus as the skeleton mainly because its 15-page split is the superset the other trees
fit into — a structural argument, not a quality verdict. A defensible alternative is a kimi
skeleton with opus grafts; it would produce the same merged content with more re-keying.

**One thing this report is not.** It is not a ranking, and the two low-recall arms are not
discardable: `deepseek`'s in-page-overlay reading of the detail-page contradiction and its
per-requirement `Phase:` tag, and `mimo`'s P0-data-path ⚖, stroke-width greyscale channel and
`@page` margin are all things the two strong arms do not have.
