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
