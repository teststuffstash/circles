# render — interactions, the detail page, and the baked data contract

The page is client-side interactive over baked data: one static HTML asset + one `data.json`,
no server, no DB, SSG-agnostic. This page owns hover/click, the detail page, and the
`data.json` contract.

## Requirements

### CIR-RENDER-SINGLE-ASSET — one static HTML asset
The product is one self-contained HTML page plus one `data.json`; there is no server, no DB,
and no multi-page app. The detail view is an in-page overlay within the same asset (see
CIR-RENDER-DETAIL-PAGE), not a separate URL/page. Phase: P0.

### CIR-RENDER-DATA-JSON — the baked render input
The page reads all render input from `data.json`: per item its status, detail line (guardrail,
status, last-data date), link, and the bake's `generated-at` stamp. The page never recomputes
freshness against the viewer's clock (⚖ FRESH-2). Phase: P0 (hand-set), P1 (baked).

| description | inputs | expected |
|---|---|---|
| page reads data.json | `data.json` present | page renders from it, no other source |
| generated-at is the anchor | `generated-at: 2026-08-04T00:00:00Z` | freshness/last-data shown relative to it |
| missing data.json | no `data.json` | page shows a load error, not a broken chart |

### CIR-RENDER-HOVER — hover shows the detail line
Hovering a cell shows the item's detail line: guardrail, status, and last-data date. On
touch/phone (no hover), see ⚖ INTERACT-1. Phase: P0.

### CIR-RENDER-CLICK — click opens detail or navigates
Clicking a cell opens the item's detail popover (which contains its link and a "details"
affordance) — see ⚖ INTERACT-2 for the link-vs-detail resolution. Phase: P0.

### CIR-RENDER-DETAIL-PAGE — the annotated-timeseries detail view
The detail view is a generic annotated timeseries: a metric series (from an adapter) overlaid
with dated intervention events from a markdown table. It is an in-page overlay, not a separate
page. Phase: P2 (the overlay shell is P0; the metric/event data is P2).

### CIR-RENDER-KEYBOARD — keyboard access
All interactions (hover-equivalent focus, click, detail open/close) are reachable by keyboard.
Phase: P0.

## ⚖ AMBIGUITY entries

### ⚖ INTERACT-1 — hover vs click on touch devices
The goal defines hover (detail line) and click (navigate/detail) as separate gestures, but
touch devices have no hover.
- Options: (a) tap toggles the detail popover; navigation via an explicit link affordance;
  (b) first tap shows detail, second tap navigates; (c) long-press for detail.
- **Recommendation: (a)** — tap toggles the detail popover; the popover carries the link and a
  "details" button. Predictable and matches the desktop click behavior.

### ⚖ INTERACT-2 — click target when an item has both a link and a detail page
The goal says "click = jump to the item's link, or open its detail page" — it does not say what
happens when an item has both.
- Options: (a) click opens the detail popover, which contains the link and a details button;
  (b) click navigates to the link, detail via a separate affordance; (c) click navigates to the
  link if present, else opens detail.
- **Recommendation: (a)** — click always opens the detail popover; the popover exposes both the
  link and the details view. No hidden behavior depending on which fields are set.

### ⚖ INTERACT-3 — detail page vs "no multi-page app" (goal contradiction)
The goal both says "don't design a multi-page app" and "open its detail page". These conflict
if the detail page is a separate page.
- Options: (a) the detail view is an in-page overlay within the single HTML asset; (b) the
  detail page is a second HTML page.
- **Recommendation: (a)** — an in-page overlay keeps the single-asset constraint intact.
  This is a genuine contradiction in the goal and is flagged as a PR Follow-up for the operator.

### ⚖ INTERACT-4 — data.json schema
The goal names `data.json` (statuses, detail lines, generated-at) but not its exact shape.
- Options: (a) fix a JSON schema in the spec now; (b) leave the shape to the builder.
- **Recommendation: (a)** — fix a minimal schema (per-item status, detail, link, last-data,
  plus a top-level `generated-at`) so the bake→render handoff is a stable contract. Flagged as
  a PR Follow-up for the operator to ratify.
