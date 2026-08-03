# Sunburst geometry

**CIR-RENDER-SUNBURST** — How the circles are laid out as a sunburst chart.

## Ring layout

**CIR-RENDER-RING-ORDER** — Rings are laid out **inside-out**, ordered by their index in `circles.yaml`'s `rings:` array. Index 0 = innermost ring; the last index = outermost ring. Triage reads inward-first (the innermost ring must hold for the outer ones to matter).

### Ring order decision table

| description | inputs | expected |
|---|---|---|
| single ring | `rings:` has 1 entry | One ring centered |
| four rings | `rings:` has 4 entries (self, partner, children, wider) | Innermost = self, outermost = wider |
| ring with no items | `rings:` entry has empty `items:` | Ring rendered as an empty band (visible, no arcs) |

## Arc subdivision

**CIR-RENDER-ARC-WEIGHT** — Items within a ring are laid out as arc segments. The angular size of each arc is proportional to its `share` weight.

### Arc weight decision table

| description | inputs | expected |
|---|---|---|
| items with no share specified | ring with 3 items, none have `share:` | Equal arcs (33.3% each) |
| items with explicit share | items with `share: 0.5` and `share: 0.5` | Equal arcs (50% each) |
| mixed share and no share | item A `share: 0.6`, item B (no share) | ⚠ validation recommended (see ambiguity) |
| single item in ring | ring with 1 item | Full 360° arc |

⚖ **AMBIGUITY: Partial share sums.** If a ring has items with explicit shares that don't sum to 1.0, what happens? Options: (a) normalize shares to sum to 1.0; (b) treat remainder as empty/unused arc; (c) validation error. **Recommendation:** Normalize. Rationale: person-authored configs will have rounding errors; normalizing is the most forgiving. If shares sum to 0, validation error.

⚖ **AMBIGUITY: Share and no-share items mixed.** If a ring has some items with `share:` and some without, how are the no-share items weighted? Options: (a) no-share items divide the remaining angular space equally; (b) it's a validation error to mix; (c) no-share items default to 1.0 and are normalized together. **Recommendation:** (a) — remaining space divided equally among no-share items. Rationale: matches the simplest mental model and is backwards-compatible with fully unspecified shares.

## Angular convention

**CIR-RENDER-ARC-START** — Arcs start from the top of the chart (12 o'clock position) and proceed clockwise.

### Sibling ordering decision table

| description | inputs | expected |
|---|---|---|
| items in ring | `items:` list [A, B, C] | A at top (12 o'clock), B clockwise, C clockwise |
| two children with share 0.5 | Nova (◀), Kit (▶) | Nova = left half, Kit = right half (reading top clockwise) |

⚖ **AMBIGUITY: Arc start angle.** Options: (a) top/12 o'clock (conventional for sunburst charts); (b) right/3 o'clock (D3 default pie convention). **Recommendation:** Top (12 o'clock). Rationale: "circles" metaphor reads top-down; labels are most readable starting from top. Provenance: D3 pie layouts default to 12 o'clock with `startAngle: -π/2`; Plotly sunburst defaults to top.

⚖ **AMBIGUITY: Arc ordering direction.** Options: (a) clockwise (conventional for LTR reading); (b) counter-clockwise. **Recommendation:** Clockwise. Standard convention for sunburst charts in LTR cultures.

## Rendering technology

**CIR-RENDER-TECHNOLOGY** — The sunburst is rendered as an HTML/SVG element. Options considered:
- **Plotly sunburst** — built-in sunburst, interactive hover out of the box, large library (~3MB).
- **D3 + SVG** — full control, accessible SVG, smaller bundle but more custom code.
- **ECharts** — built-in sunburst, interactive, medium bundle size.

⚖ **AMBIGUITY: Rendering library choice.** The goal issue mentions Plotly, D3, and ECharts as acceptable. **Recommendation:** D3 + SVG for P0. Rationale: (1) SVG is natively accessible (screen readers can traverse DOM); (2) smallest bundle; (3) full control over the one-screen/A4 constraint (Plotly's auto-layout fights fixed sizing); (4) the sunburst geometry is simple enough to hand-implement in D3. Can migrate to Plotly later if the interactive feature set justifies it.

## Empty/edge cases

| description | inputs | expected |
|---|---|---|
| ring with zero items | ring exists but `items: []` | Visible empty band (ring gap, not collapsed) |
| all items ⚪ | ring where all items unmonitored | All arcs grey, ring label visible |
| very many items | ring with 20+ items | Arcs still visible (minimum arc size enforced); labels may hide below minimum |
| single item, no share | ring with 1 item, no `share:` | Full 360° donut ring |

⚖ **AMBIGUITY: Minimum arc size for visibility.** If many items share a ring, small arcs become invisible. Options: (a) enforce a max items-per-ring in validation; (b) set a minimum visible arc angle (e.g. 5°) and collapse smaller items into "other"; (c) allow overflow and let the person manage it. **Recommendation:** (c) for P0, log a build warning if any arc is below 5°. Rationale: the person authored the config; trust them but warn. A max-items constraint can be added later.
