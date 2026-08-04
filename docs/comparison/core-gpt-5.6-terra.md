# Core comparison — issue #1 spec arms

Scope: independent judge report for issue #6. This report compares the four named arm trees, not their PR prose. Statuses below are frozen per phase commit.

## Blind decision-point checklist (phase 0)

Rubric built before reading any arm tree from issue #1 and master only. `P0` means a release-blocking contract decision; `P1/P2` means it must be bounded rather than exhaustively designed now.

| ID | Decision point left open by the goal / master seed | Phase | Grounding |
|---|---|---|---|
| DP-01 | Canonical `circles.yaml` root fields, requiredness, types, unknown-key policy, and stable-id grammar | P0 | issue + schema stub |
| DP-02 | Ring/item cardinality, ID uniqueness scope, empty rings, and duplicate labels | P0 | issue |
| DP-03 | Config path resolution: config directory versus repo root; relative source/link/command working directory | P0 | fixture uses relative paths |
| DP-04 | URL/path link allowlist and safe click behavior (external URL versus detail route) | P0 | issue says link or detail page |
| DP-05 | Whether `status` is mutually exclusive, validation/error behavior for absent, malformed, or multiple adapters | P0 | stub says “exactly one” but lacks invalid cases |
| DP-06 | Canonical status tokens versus display glyphs and validation of manual values | P0 | fixed semantics |
| DP-07 | Status precedence and warning aggregation when config/source/adapter failures occur | P0/P1 | fixed “failure is grey + warning” |
| DP-08 | Freshness date extraction locations, supported formats, invalid/future dates, newest-selection tie-break | P1 | goal + seed’s explicit open date formats |
| DP-09 | Freshness age boundary inclusivity, threshold ordering/equality, units, and timezone/DST anchor | P1 | goal + seed opens timezone/DST |
| DP-10 | Source glob semantics, recursion, deterministic ordering, unreadable/empty/missing source cases | P1 | goal says file/glob |
| DP-11 | Command argv/no-shell execution, stdout grammar, timeout/environment/cwd, nonzero/invalid-output warnings | P1 | fixture command + escape hatch |
| DP-12 | `share`: numeric domain, omitted-share distribution, sum/normalization, zero/negative values | P0 | stub opens sum; geometry depends on it |
| DP-13 | Sibling arc ordering and start-angle/orientation; deterministic mapping to fixture half-arcs | P0 | stub opens ordering |
| DP-14 | Ring geometry for unequal item shares, ring gap/padding, and one/many-item behavior | P0 | required sunburst form |
| DP-15 | Ring ordering validation and visual/accessibility cue that triage is inward-first | P0 | fixed inside-out dependency |
| DP-16 | Empty/no-data sunburst rendering and graceful invalid/bake-failure presentation | P0 | static page must remain honest |
| DP-17 | `data.json` contract: schema/version, item identity join, status/detail fields, generated-at format/timezone, validation | P0 | issue fixes baked asset but not shape |
| DP-18 | P0 source of baked data: how hand-set config becomes data.json; generated-at/warning provenance | P0 | P0 manual, static asset |
| DP-19 | Static asset paths/cache/loading failure behavior and no-server boundary | P0 | issue says static HTML + data.json |
| DP-20 | Color palette mapping including grey, non-color encoding, contrast, legends/text alternatives | P0 | legibility + grey visibility |
| DP-21 | Hover/focus/touch equivalent content, placement, dismissibility, and detail-line missing fields | P0 | hover requirement + phone-later |
| DP-22 | Click priority/target: link versus generic detail page, keyboard activation, unavailable target behavior | P0 | issue uses “or” |
| DP-23 | One-screen viewport definition, overflow prohibition, responsive breakpoint/minimum supported dimensions | P0 | hard constraint, phone later |
| DP-24 | A4 print definition: orientation, margins, print CSS, scaling, colors/legend, and what may be omitted | P0 | hard constraint |
| DP-25 | Labels/long text/large item counts: truncation/wrapping/tooltip and collision policy | P0 | chart legibility |
| DP-26 | Accessibility baseline: semantic alternative, keyboard navigation, focus, screen-reader names, motion | P0 | interactive visual page |
| DP-27 | Detail-page route/data contract and generic metric/event series schema | P2 boundary | goal defines first P2 instance only |
| DP-28 | Timeseries time/value units, event markdown-table grammar/validation, annotations, no-data/error states | P2 boundary | goal leaves mechanics open |
| DP-29 | Adapter interface extension boundary for later built-ins; common input/output/warning model | P1 boundary | plug-ins without page changes |
| DP-30 | Nightly bake execution contract: deterministic clock, output atomics, warning surfacing, exit policy | P1 boundary | job elsewhere, repo owns code |
| DP-31 | Deploy integration: served asset location/image/chart path and P0 verification without asserting nonexistent pipeline details | P0 | current chart serves bootstrap; circles-iac has no chart pin yet |
| DP-32 | Test terminology exactly as ruled: unit, local-kind system testing, target-environment e2e; decision-row-to-test linkage | P0 | explicit issue requirement |
| DP-33 | Fixture doctrine: Alex rows used as synthetic test inputs; no real-person data or invented fixture fields | P0 | fixtures README + issue |
| DP-34 | Requirement convention enforcement: CIR grammar/unique anchors, executable decision-row descriptions, no declared verifiedness | P0 | specs README |
| DP-35 | Glossary coverage and one-definition/no-synonym discipline for newly introduced terms | P0 | specs README |
| DP-36 | Explicit ambiguity treatment: genuine choices carry options/recommendation; facts fixed by goal are not falsely opened | P0 | specs README + issue |

Phase-0 method notes: master confirms `fixtures/alex/circles.yaml` has `person`, ordered `rings`, item `id`/`label`/optional `guardrail`/`share`, and the three adapters; it does **not** contain a baked-data schema or detail-series fixture. `scripts/ci.sh` presently validates/tests only the Helm chart. `public/index.html` is a bootstrap page. Context evidence (read-only): `circles-iac` calls its chart application/pin a future first-published-chart step, so a spec must not claim an existing circles chart deployment path beyond this repo’s nginx image + Helm chart.

## Per-arm inventory (phase 1 working record)

Inventory is tree-derived after Phase 0; **Y** means the text supplies a concrete assertion/table outcome sufficient to start a test, **N** means it is a genuine ⚖ choice. IDs are requirement anchors, not PR-body counts. Repeated anchor references are not recounted.

### opus — 64 requirement anchors; 28 ⚖ entries

Requirements: `CIR-DATA-SCHEMA-STRICT` schema/unknown-key validation Y; `-VERSION` schema version Y; `-IDENTITY` ring/item identity Y; `-SHARE` shares Y; `-STATUS-RESOLUTION` fixed status table Y; `-FAILURE-IS-GREY` failure algebra Y; `-GREY-REASON` absent-versus-failed grey Y; `-DATE-PARSE` parsing Y; `-AGE-CALENDAR` age bands Y; `-TIMEZONE` time anchor Y; `-SOURCE-PATH` path/glob containment Y; `-CONTENT` config/data content Y; `-DETAIL-LINE` display fields Y; `CIR-ADAPT-CONTRACT`, `-MANUAL`, `-FRESHNESS`, `-COMMAND`, `-BUDGET` adapter interface/execution/budgets Y; `CIR-BAKE-ARTIFACT`, `-DETERMINISM`, `-EXPOSURE`, `-PAGE-DOES-NOT-RESOLVE`, `-SELF-CONTAINED`, `-STALE-SELF`, `-WARNINGS` bake/data publishing Y; `CIR-RENDER-RING-ORDER`, `-RINGS-INDEPENDENT`, `-MIN-ARC`, `-INNER-LEGIBILITY`, `-CAPACITY`, `-OVERFLOW`, `-SUMMARY` geometry/density Y; `-ONE-SCREEN`, `-A4`, `-ASSET-BUDGET`, `-NO-EGRESS`, `-NO-JS` layout Y; `-GREY-VISIBLE`, `-CONTRAST`, `-STATUS-ENCODING`, `-PRINT-COLOR`, `-LABEL-BUDGET`, `-STALE-MARK` presentation Y; `-DETAIL-REVEAL`, `-CLICK`, `-KEYBOARD`, `-TOUCH` interaction Y; `-A11Y-TABLE` text alternative Y; `CIR-DETAIL-PAGE-SHAPE`, `-SERIES`, `-EVENTS`, `-LAYOUT` P2 boundary Y; `CIR-PROC-PHASE-P0/-P1/-P2`, `-DEPLOY-SEAM`, `-NOT-YET`, `-TEST-TIERS`, `-TEST-ROWS`, `-GATE`, `-BROWSER-EVIDENCE`, `-BUG-CROSSES-AS-A-ROW` process Y.

⚖: Q01 strict schema; Q02 schema version location; Q03 cross-ring item; Q04 mixed share; Q05 timezone scope; Q06 P0 unimplemented adapters; Q07 explicit grey; Q08 boundary; Q09 clock; Q10 formats; Q11 date location; Q12 read cap; Q13 command metadata; Q14 command/bake budgets; Q15 plug-in form; Q16 inline/fetch; Q17 stale bake status; Q18 stale threshold; Q19 renderer; Q20 ring thickness; Q21 over-capacity failure; Q22 rollup/centre; Q23 viewport; Q24 A4 box; Q25 palette; Q26 stale visual; Q27 link/detail priority; Q28 stale no-JS; Q29 detail routing; Q30 metric interface; Q31 event table; Q32 browser tier; Q33 bake/publish path — all N. (The apparent `Q01` reference for unknown adapter is a defect: it points to a schema ambiguity, not an adapter registry question.)

### kimi-k3 — 68 valid requirement anchors; 20 ⚖ entries

Requirements: `CIR-DATA-SCHEMA-TOPLEVEL/-RING/-ITEM/-CELL-IDENTITY/-EXACTLY-ONE-ADAPTER/-LINK/-VALIDATION` config Y; `-SHARE-WEIGHT` share Y; `CIR-DATA-STATUS-RESOLUTION/-TOOLING-FAILURE/-MANUAL-VALUES/-NO-AGGREGATION/-RESOLUTION-TIME` status Y; `CIR-DATA-FRESHNESS-SOURCE/-DATE-PARSING/-AGE/-WINDOW/-THRESHOLDS/-EMPTY/-FUTURE` freshness Y; `CIR-DATA-ADAPTER-INTERFACE/-REGISTRY/-MANUAL/-COMMAND-EXEC/-NO-PAGE-LOGIC` adapter seam Y; `CIR-DATA-DATAJSON-SCHEMA/-VERSION/-GENERATED-AT/-WARNINGS/-ATOMIC-WRITE/-DETAIL-FIELDS/-DETAIL-FILES` baked contract Y; `CIR-RENDER-GEOM-RING-ORDER/-RING-PARTITION/-ARC-SHARE/-SIBLING-ORDER/-RING-THICKNESS/-LABELS/-DENSITY` geometry Y; `CIR-RENDER-LAYOUT-REFERENCE-VIEWPORT/-ONE-SCREEN/-PRINT-A4/-CHROME/-GENERATED-AT-VISIBLE/-BOOT-ERROR/-ASSETS/-DATA-FETCH/-NO-JS` layout Y; `CIR-RENDER-COLOR-PALETTE/-GREY-VISIBLE/-NOT-ONLY-CHANNEL/-LEGEND`, `CIR-RENDER-A11Y-TEXT-ALTERNATIVE` presentation Y; `CIR-RENDER-INTERACT-HOVER/-CLICK/-KEYBOARD/-TOUCH`, `CIR-RENDER-DETAIL-PAGE/-EVENTS` interaction/P2 Y; `CIR-PHASE-P0/-P1/-P2/-BAKE-ONE-PATH/-CONFIG-PROVENANCE`, `CIR-TEST-TIERS/-ROW-LINKAGE/-FIXTURES/-GATES` process Y.

⚖: ring partition; sibling order; content envelope; renderer; reference viewport; small viewport; no-JS floor; CVD palette; dark mode; link/detail; touch; series gaps; event parsing; nightly publish path; config provenance; unknown keys; empty ring; date formats; timezone; empty/future source; command timeout; warning surfacing; page staleness; detail packaging — N. (24 actual entries; four labels are duplicated/references, not separate decisions.)

### deepseek-v4-flash-0731 — 37 requirement anchors; 21 ⚖ entries

Requirements: `CIR-DATA-SCHEMA/-VALIDATION/-ITEM-UNIQUENESS/-SHARE-WEIGHTS/-SIBLING-ORDER` config Y; `-STATUS-RESOLUTION/-UNMONITORED/-TOOLING-FAILURE/-ADAPTER-MANUAL/-ADAPTER-FRESHNESS/-ADAPTER-COMMAND/-COMMAND-OUTPUT/-ADAPTER-INTERFACE` adapter/status Y; `CIR-DATA-FRESHNESS-WINDOW/-DATE-PARSING/-TIMEZONE/-MISSING-SOURCE/-FUTURE-DATE` freshness Y; `CIR-RENDER-RING-ORDER/-ARC-SUBDIVISION/-EMPTY-STATE/-ONE-SCREEN/-A4-PRINT/-OVERFLOW/-REFERENCE-VIEWPORT` geometry/layout Y; `CIR-RENDER-COLOR-STATUS/-UNMONITORED/-CONTRAST/-ACCESSIBILITY` color Y; `CIR-RENDER-SINGLE-ASSET/-DATA-JSON/-HOVER/-CLICK/-DETAIL-PAGE/-KEYBOARD` interaction/data Y; `CIR-PROC-TEST-TIERS/-TABLE-LINKAGE` process Y.

⚖: DATA-1 timezone; DATA-2 formats; DATA-3 share; DATA-4 ordering; DATA-5 cross-ring; DATA-6 command output; DATA-7 future dates; DATA-8 empty config; FRESH-1 mixed formats (derivative, false-new); FRESH-2 bake-time resolution; RENDER-1 viewport; RENDER-2 overflow; RENDER-3 phone scope; RENDER-4 renderer; RENDER-5 chart accessibility; RENDER-6 print content; COLOR-1 exact values; COLOR-2 grey visibility; COLOR-3 CVD palette; INTERACT-1 touch; INTERACT-2 target; INTERACT-3 detail/multipage; INTERACT-4 data schema; PROC-1 gate — N. Two defects: `FRESH-1` calls an already-decided consequence an ambiguity; `INTERACT-4` says to fix a schema but the arm supplies no actual JSON schema.

### mimo-v2.5-pro — 42 requirement anchors; 16 ⚖ entries

Requirements: `CIR-DATA-ADAPTERS/-ADAPTER-INTERFACE/-ADAPTER-CONTRIBUTION`, `CIR-DATA-STATUS-RESOLUTION`, `CIR-DATA-FRESHNESS-WINDOW/-THRESHOLDS/-DATE-EXTRACTION/-SOURCE` adapter/data Y; `CIR-RENDER-SUNBURST/-RING-ORDER/-ARC-WEIGHT/-ARC-START/-TECHNOLOGY`, `-ONE-SCREEN/-A4-PRINT/-SCALING`, `-COLORS/-COLORS-UNMONITORED/-CONTRAST/-PRINT/-CVD/-LABELS`, `-HOVER/-HOVER-CONTENT/-CLICK/-DETAIL/-DETAIL-EXAMPLES/-DETAIL-METRIC/-A11Y` render Y; `CIR-PROCESS-BAKE/-P0/-SCHEMA/-GENERATED-AT/-WARNINGS/-DEPLOY`, `CIR-PROCESS-TESTING/-UNIT/-SYSTEM/-E2E/-LINKAGE/-FIXTURES/-CI` process Y.

⚖: partial/mixed shares; arc start/direction; renderer; minimum arc; A4 orientation/margins; link navigation; metric parsing; P0 data path; generated-at format; green contrast; greyscale/CVD palette; label truncation; timezone; threshold inclusivity; command timeout/cwd; date-dependent tests — N. False-⚖: CVD-friendly *blue/orange* alternative reopens the goal’s fixed green/yellow/red traffic-light statuses; freshness threshold inclusivity is useful but should be a direct requirement after ratification, not simultaneously described as settled table behavior.

## Master decision-point matrix

Legend: **C** covered by a testable requirement/table; **⚖** genuine ambiguity with options/recommendation; **M** missed; **F⚖** false ambiguity (the arm presents a goal-decided fact as open). Matrix rows are the deduped Phase-0 rubric; nested details are not rewarded merely because an arm has more prose.

| DP | Decision point | opus | kimi-k3 | deepseek | mimo-v2.5-pro |
|---|---|---:|---:|---:|---:|
| 01 | Config shape/keys/IDs | C | C | C | M |
| 02 | Cardinality/identity | C | C | C | M |
| 03 | Relative config/source/command paths | C | C | M | C |
| 04 | Link safety/target | C | C | M | M |
| 05 | Exactly-one adapter/errors | C | C | C | C |
| 06 | Status token vocabulary | C | C | C | M |
| 07 | Failure/status warning algebra | C | C | C | C |
| 08 | Date extraction/newest selection | C | C | C | C |
| 09 | Age boundaries/timezone/DST | C | C | C | C |
| 10 | Globs/missing/unreadable sources | C | C | M | C |
| 11 | Command execution/output/security | C | C | C | C |
| 12 | Share domain/default/normalization | C | C | C | ⚖ |
| 13 | Sibling ordering/orientation | C | C | C | C |
| 14 | Ring/arc geometry | C | C | C | C |
| 15 | Inward triage/order semantics | C | C | C | C |
| 16 | Empty/no-data rendering | C | ⚖ | C | M |
| 17 | `data.json` schema/version/identity | C | C | ⚖ | C |
| 18 | P0 config→baked-data path | C | C | M | ⚖ |
| 19 | Static asset/load/cache behavior | C | C | C | M |
| 20 | Palette/grey/non-color/contrast | C | C | C | C |
| 21 | Hover/focus/touch/detail contents | C | C | C | C |
| 22 | Click priority/keyboard/unavailable | C | ⚖ | ⚖ | ⚖ |
| 23 | One-screen viewport/overflow | ⚖ | ⚖ | ⚖ | M |
| 24 | A4 print box/colors/margins | ⚖ | C | ⚖ | ⚖ |
| 25 | Label/density collision behavior | C | C | M | ⚖ |
| 26 | Accessibility baseline | C | C | ⚖ | C |
| 27 | Detail route/data contract P2 boundary | ⚖ | C | ⚖ | M |
| 28 | Series/events grammar/no-data P2 boundary | ⚖ | ⚖ | M | M |
| 29 | Later built-in adapter seam | ⚖ | C | C | C |
| 30 | Nightly bake determinism/publish/error | C | ⚖ | M | C |
| 31 | Deploy seam grounded in current platform | ⚖ | ⚖ | M | F⚖ |
| 32 | Ruled test tiers/row linkage | C | C | C | C |
| 33 | Fixture/public-data doctrine | C | C | C | C |
| 34 | CIR IDs/row grammar/no verification claim | C | C | C | C |
| 35 | Glossary one-definition discipline | C | C | M | M |
| 36 | Genuine, non-false ambiguity discipline | C | C | C | F⚖ |

Counts from matrix: opus **27 C / 8 ⚖ / 1 M**; kimi-k3 **27 C / 7 ⚖ / 2 M**; deepseek **22 C / 9 ⚖ / 5 M**; mimo-v2.5-pro **17 C / 9 ⚖ / 8 M / 2 F⚖**. “Recall” below is `(C + genuine ⚖) / 36`: an honest unresolved choice is coverage, but false ⚖ is separately penalized. Unique finds are decision points materially covered (C or ⚖) by only that arm: opus 0, kimi-k3 1, deepseek 0, mimo-v2.5-pro 0. Kimi’s unique find is explicit safe link scheme/path validation (DP-04); its cache stipulation is not unique (opus also defines no-runtime-egress) and is therefore not counted.
