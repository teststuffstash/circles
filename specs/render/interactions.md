# Interactions — hover, click, detail page

**CIR-RENDER-HOVER** — Hovering over an item's arc segment shows its detail line.

## Hover behavior

**CIR-RENDER-HOVER-CONTENT** — On hover (desktop) or tap (mobile), the item's arc shows a tooltip with:
1. **Item label** (from `circles.yaml` `label:`)
2. **Status light** (the emoji/icon)
3. **Guardrail text** (if present)
4. **Last-data date** (from adapter resolution — the newest date for freshness, or "manual" for manual items)

### Hover decision table

| description | inputs | expected |
|---|---|---|
| hover on 🟢 item | item with freshness adapter, recent date | Tooltip: label, 🟢, guardrail, "Last data: 2026-08-01" |
| hover on ⚪ item | item with no adapter | Tooltip: label, ⚪, "Unmonitored" |
| hover on ⚪ item with guardrail | item with guardrail, no adapter | Tooltip: label, ⚪, guardrail, "Unmonitored" |
| hover on ring (not item) | cursor on ring label/gap area | No tooltip (only item arcs have hover) |
| touch on mobile | tap on item arc | Tooltip shows (stays until tap elsewhere) |

## Click behavior

**CIR-RENDER-CLICK** — Clicking an item's arc segment navigates to the item's `link:` target.

### Click decision table

| description | inputs | expected |
|---|---|---|
| click item with link | `link: /notes/sleep-log.md` | Navigate to that URL |
| click item with absolute URL | `link: https://example.com` | Navigate to that URL (new tab) |
| click item without link | no `link:` key | No-op (no navigation, no error) |

⚖ **AMBIGUITY: Link navigation behavior.** Options: (a) same-tab navigation; (b) new tab (`target="_blank"`); (c) depends on whether link is relative (same tab) vs absolute (new tab). **Recommendation:** (b) always new tab with `target="_blank" rel="noopener"`. Rationale: the circles page is a dashboard; navigating away loses the overview. Relative links (e.g. to a detail page) should also open in a new tab for consistency.

## Detail page — annotated timeseries

**CIR-RENDER-DETAIL** — The detail page (P2+) is a generic "annotated timeseries": a metric series from an adapter overlaid with dated intervention events from a markdown table.

### Detail page decision table

| description | inputs | expected |
|---|---|---|
| P0 — no detail page | item clicked, P0 phase | Navigate to link (or no-op if no link) |
| P1 — link-based detail | item with `link:` | Navigate to link (static page or external) |
| P2 — timeseries detail | item with freshness adapter + intervention events | Show chart: metric line + event markers |
| P2 — timeseries with no interventions | item with freshness adapter, no events table | Show chart: metric line only |

### Annotated timeseries anatomy

The "metric × events" chart has:
1. **X-axis:** dates (from the freshness source data)
2. **Y-axis:** the metric values (from the source file's numeric entries)
3. **Event markers:** vertical lines/bands for intervention events (from a companion markdown table)

**CIR-RENDER-DETAIL-EXAMPLES** — The goal issue gives concrete examples:
- "medication changes × nightly sleep" — sleep hours (from sleep-log.md) with medication change events
- "training load × resting heart rate" — heart rate with training load events

### Metric extraction from source files

**CIR-RENDER-DETAIL-METRIC** — The freshness source file (`notes/sleep-log.md`) already contains dated entries. The detail page extracts:
- The date (YYYY-MM-DD)
- The numeric value on the same line (e.g. "7h20m" → parseable as hours+minutes, or just the raw text for v0)

⚖ **AMBIGUITY: Metric value parsing.** How are numeric values extracted from source files? The sleep-log.md has entries like `7h20m` — is this parsed as 7.33 hours? Options: (a) raw text display only (P0 no parsing); (b) regex for common patterns (hours+minutes, bare numbers); (c) adapter-specific parsing rules. **Recommendation:** (a) raw text for P0, (c) for P2+ with adapter-declared format spec. Rationale: parsing is complex and adapter-specific; start simple.

## Accessibility

**CIR-RENDER-A11Y** — The interactive sunburst MUST be accessible:
- SVG arcs have `role="img"` and `aria-label` with the item label and status.
- Hover tooltips are keyboard-accessible (focus via Tab key).
- The status legend is readable by screen readers.

### Accessibility decision table

| description | inputs | expected |
|---|---|---|
| screen reader on arc | NVDA/JAWS on item arc | Reads: "Sleep, ok, guardrail: Lights out by 23:00" |
| keyboard tab to arc | Tab key | Arc receives visible focus ring, tooltip shows |
| keyboard escape | Escape key while tooltip shown | Tooltip dismisses |
