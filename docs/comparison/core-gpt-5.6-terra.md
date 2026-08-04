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
