# fixtures/ — the synthetic person

**Everything here is invented.** This repo is public; real people's data is deploy-time content
and never appears in git (the same trust boundary the platform's other stacks use: workers get
synthetic tables, never production data). The fixture person "Alex" exists so that:

- spec pages have concrete key examples (decision-table doctrine — rows here and rows in
  `specs/` are the same thing);
- tests build their inputs FROM these tables at runtime (no hidden/binary fixtures);
- bug reports cross the boundary as new fixture rows, not as real data.

Layout: one directory per fixture person (`alex/` today) — `circles.yaml` plus whatever fake
source files their adapters read (`notes/`).

Variants: the same person, re-cut so one spec row has a committed key example — never a second
person. `alex/circles-zero-warnings.yaml` is Alex with every adapter hand-set (`manual:`) so the
bake is clean (`CIR-BAKE-ARTIFACT#warnings-empty-array`); `click-destinations.yaml` is the
per-row click-destination table for `CIR-RENDER-CLICK`; `evidence-dedup.yaml` is the case-id
collision table for the evidence join (`scripts/generate-evidence.py`).

## The fixture reference date — 2026-08-03

**Every dated example here is read relative to this date, never relative to today's calendar**
(⚖-R24, `CIR-PROC-TEST-FIXTURES`). The dates in `alex/notes/` are committed constants, so the
lights they produce would otherwise drift as the calendar advances: `notes/sleep-log.md`'s newest
entry is 2026-08-01 with `yellow_after: 7`, which is the key example for "freshness inside window
→ 🟢" and would silently become 🟡 a week later, then 🔴.

So a claim like "sleep is 🟢" is never a claim about now. It is a claim about
*(these source dates, this reference date)* — a complete, time-independent fact that a test
reproduces by injecting the reference date into the bake (`CIR-ADAPT-REFERENCE-DATE`). The
committed dates stay fixed and readable; nothing rewrites them at test time.

`notes/future-date.md` (one entry dated 2099-01-01, one dated 2026-08-01) and
`notes/empty-log.md` (a heading, no dated lines) are the future-date and no-dates key examples,
read against this same reference date. When the fixture gains dated rows, they are chosen relative to this date. Moving the reference
date is a fixture change like any other: it changes which lights the examples produce, so the
spec rows that cite them move with it.
