# specs/ — the circles contract

The approved-not-authored spec system this stack's agent loop runs on (the same shape
oracle-fleet and sleep-tracking use): **specs are the contract, code converges on them.**
Agents author spec PRs; a human approves every spec merge. The authoring PURPOSE is finding
gaps, contradictions, and ambiguities in the intended system — a spec that merely restates an
issue has failed.

## Tree

- `README.md` — this file: structure + conventions.
- `glossary.md` — every domain term, one definition each.
- `data/` — the data model: `circles.yaml` schema, status resolution, freshness semantics.
- `render/` — the page: sunburst geometry, one-screen/A4 constraint, interactions.
- `process/testing.md` — the ruled test-tier terminology + how requirements link to tests.

(The tree grows per area; this seed fixes only the conventions.)

## Conventions

- **Requirement IDs**: stable anchors `CIR-<AREA>-<NAME>` (e.g. `CIR-DATA-FRESHNESS-WINDOW`) —
  one requirement, one anchor; tests and issues reference the ID verbatim. IDs are never
  renamed or reused.
- **Decision tables over prose** wherever behavior branches: visible `inputs || expected` rows,
  each row's description usable as a test id verbatim. The synthetic fixture person under
  `fixtures/` supplies the key examples — spec rows and fixture rows are the same doctrine.
- **⚖ AMBIGUITY entries are first-class**: a judgment call is recorded with its options and a
  recommendation, never silently decided.
- **Verified-ness is derived, never declared**: no ✓/🚧 markers claiming coverage — a
  requirement without a linked test is simply unevidenced.
- **Synthetic data only**: this repo is public; every example, fixture row, and spec value is
  invented. Real people's data is deploy-time content and never appears here.
- **Row ids are join keys, not prose** (ruled 2026-08-04, from the FU-126 arm comparison):
  every decision-table row carries a stable, human-authored intent id in its first column
  (kebab or short intent phrase — `palette-luminance-ladder`, `"missing challenge"`). That id
  is the evidence join key: spec row → test case id → report story fragment → rendered back
  under this heading. A row whose id changes orphans its evidence; renames follow the same
  discipline as requirement IDs.
  **Ids are correlational by default; a meaning-bearing label is a judgment call, not a sin**
  (ruled 2026-08-04): prefer tables that read complete with the id column deleted, but when
  reasoning a row out of its columns is disproportionate effort, the label may carry meaning —
  deliberately, sparingly, and as a flag for review attention.
  The double edge either way: a legible label is the cheapest thing to read, so it becomes the
  ONLY thing read, and the row's judgment stops being contested (the author thought; nobody
  after has to). **The defense lives in the projection layer, not in prohibition** — the
  markdown source is the complete document, every render a disposable projection (same family
  as evidence-collapsed-by-default): human renders may demote ids to hover/tooltips beside the
  cells; review and verification projections strip ids — wholly, or sampled (e.g. half the
  rows) — so blind re-derivation from `inputs || expected` stays structural rather than a
  discipline. A derivation↔label mismatch is the named defect class **label laundering** (the
  fan-out's "defective rulings" were exactly this, caught by judges that recounted instead of
  reading labels).
- **Every table names its world.** Expected behavior is a function of (system, world); a table
  that doesn't name its fixture set lies by omission. v0 has ONE world — the fixture person
  `alex` (`fixtures/`) — declared once per page ("World: alex") until a second world exists;
  from then on it's a column. Future worlds are named YAML personas (`specs/worlds/`), the
  IdP/oracle convention; evidence row identity is **(rule ID, world, case)**.
- **Doctrine slots are first-class.** Each requirement may carry 1–3 short normative
  invariant sentences above its table — negative space and policy ("no default-to-green path
  exists anywhere", "a failing adapter never inherits its last light"). Doctrine is the
  judgment layer: review flags it for attention, tests enforce it via census/audit-style rows
  where possible, and it is never flattened into pseudo-rows to look mechanical.
- **External claims carry citations.** A requirement that rides an external source states it:
  `External: MUST — <spec/section or URL>`. A claim from training knowledge that no ride
  verified is marked as such (provenance notes) — never presented as checked.

## Evidence — the contract, with the format deliberately unpinned

Every requirement section is born evidence-ready and honestly unverified:

- Until a linked test exists, the section ends with the literal line
  `_Evidence: none yet — unverified._` — the visible-grey doctrine applied to the spec itself.
- When evidence lands it replaces that line with a collapsed block (`<details>`): a transcluded
  per-rule fragment + a link into the archived report. **Links are relative** so each published
  site (master, per-PR preview) shows *its own run's* evidence, never master's.
- The join contract is fixed NOW; the fragment **format is deliberately not**: story/test id ==
  rule id exactly, case id == row id, identity == (rule, world, case), report digest-stamped.
  The SVG fragments oracle uses are a Confluence-era relic under active rethink
  (allure-behavior-snippets#6) — the successor should be markdown-embedded and
  machine-validatable (agents/reviewers parse it, not just view it), likely a generated table +
  JSON sidecar. Circles specs must not bake any SVG assumption in; only the anchors and ids
  above, so the format swaps under stable joins.
- **Framework-neutral by construction**: circles evidence is pytest+Allure, the IdP's will be
  Spock+Allure (tara-test lineage). Everything the spec relies on lives in spec text + the
  Allure result JSON (`behaviors.json` post-processing — ids, categories, tags — is an accepted
  lever), never in a framework-specific feature.

Circles is the cheap rehearsal of this exact chain before the IdP runs it for real
(rule → intent row → named world → fragment → digest-stamped report — the auditor's
traceability chain).

## Seeding state (2026-08-04) — TRANSIENT, delete this section when the weave lands

The first real tree is being merged from the FU-126 four-model fan-out (issue #1, arms on
PRs #2–#5) using the comparison mission (issue #6): downstream-proxy reports PRs #7–#10,
judge reports PRs #11 (nemotron) / #12 (terra) / #13 (fable), all under `docs/comparison/`
on their branches. Rendered arm previews: `specs-<PR>.circles.teststuff.net` (2–5), master
site `specs.circles.teststuff.net`.

**Ruling: kimi-k3 chassis + opus doctrine grafts.** Per-page: start from terra's map
(#12 `core-gpt-5.6-terra.md`) for which body to take; apply fable's graft list
(#13 `core-fable.md`) for what must survive from the other arm — the two maps agree on every
best-in-fan-out artifact and differ only on warp vs weft. While weaving, retrofit the three
conventions above (row-id normalization on grafted opus tables, world declaration per page,
doctrine slots for opus's invariant prose) so the tree lands on the final genre instead of
migrating later.

Next session start: branch `research/issue-1-weave` → weave page-by-page (its PR gets a
rendered preview automatically) → consolidate the deduped ⚖ register (fable's ⚖-R1–R4 name
the live cross-arm conflicts needing an operator ruling) → land through the human gate →
close arms #2–#5 → delete this section.
