# bake/render.py — the complete self-contained index.html with the artifact inlined
#
# Requirements owned:
#   CIR-BAKE-SELF-CONTAINED, CIR-RENDER-RING-ORDER, -RING-PARTITION, -ARC-SHARE,
#   -SIBLING-ORDER, -RING-THICKNESS, -MIN-ARC, -LABELS, -SUMMARY, -CAPACITY,
#   -RENDERER, -PALETTE, -GREY-VISIBLE, -STATUS-ENCODING, -LEGEND, -A11Y-TABLE,
#   -CHROME, -GENERATED-AT, -BOOT-FAILURE, -NO-EGRESS, -ASSET-BUDGET,
#   -NO-JS, -HOVER, -KEYBOARD, -TOUCH, -CLICK,
#   -ONE-SCREEN, -REFERENCE-VIEWPORT
#   CIR-PROC-GATE#gate-asset-budget, CIR-PROC-GATE#gate-no-external-origins

from __future__ import annotations

import html
import math
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CX = 400.0  # SVG centre X
CY = 400.0  # SVG centre Y
CENTRE_RADIUS = 60.0
RING_GAP = 4.0
BASE_THICKNESS = 80.0
THICKNESS_DECAY = 10.0
MIN_THICKNESS = 30.0
CELL_GAP_DEG = 2.0
MIN_ARC_DEG = 3.0  # minimum arc angle after gap

# Palette (CIR-RENDER-PALETTE)
STATUS_COLORS: dict[str, str] = {
    "green": "#00916A",
    "yellow": "#F2B300",
    "red": "#B22222",
    "grey": "#9E9E9E",
}

STATUS_WORDS: dict[str, str] = {
    "green": "ok",
    "yellow": "attention",
    "red": "act",
    "grey": "unmonitored",
}

# Label colours per status (CIR-RENDER-PALETTE#label-contrast)
LABEL_COLORS: dict[str, str] = {
    "green": "#000000",
    "yellow": "#000000",
    "red": "#FFFFFF",
    "grey": "#000000",
}

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _compute_radii(num_rings: int) -> list[tuple[float, float]]:
    """Compute (inner_radius, outer_radius) for each ring, inside-out.

    Thickness is non-increasing outward (CIR-RENDER-RING-THICKNESS).
    """
    radii: list[tuple[float, float]] = []
    inner = CENTRE_RADIUS
    for i in range(num_rings):
        thickness = max(BASE_THICKNESS - i * THICKNESS_DECAY, MIN_THICKNESS)
        outer = inner + thickness
        radii.append((inner, outer))
        inner = outer + RING_GAP
    return radii


def _arc_path(
    start_angle: float,
    end_angle: float,
    inner_r: float,
    outer_r: float,
) -> str:
    """Return SVG path d attribute for an arc segment.

    Angles in degrees, clockwise from 12 o'clock.
    """
    start_rad = math.radians(start_angle)
    end_rad = math.radians(end_angle)

    # Outer arc endpoints
    x1o = CX + outer_r * math.sin(start_rad)
    y1o = CY - outer_r * math.cos(start_rad)
    x2o = CX + outer_r * math.sin(end_rad)
    y2o = CY - outer_r * math.cos(end_rad)

    # Inner arc endpoints
    x1i = CX + inner_r * math.sin(start_rad)
    y1i = CY - inner_r * math.cos(start_rad)
    x2i = CX + inner_r * math.sin(end_rad)
    y2i = CY - inner_r * math.cos(end_rad)

    sweep = end_angle - start_angle
    large_arc = 1 if sweep > 180 else 0

    return (
        f"M {x1o:.2f} {y1o:.2f}"
        f" A {outer_r:.2f} {outer_r:.2f} 0 {large_arc} 1 {x2o:.2f} {y2o:.2f}"
        f" L {x2i:.2f} {y2i:.2f}"
        f" A {inner_r:.2f} {inner_r:.2f} 0 {large_arc} 0 {x1i:.2f} {y1i:.2f}"
        f" Z"
    )


def _label_transform(
    start_angle: float,
    end_angle: float,
    inner_r: float,
    outer_r: float,
) -> tuple[float, float, float]:
    """Return (x, y, rotation_degrees) for a label at the arc's centre."""
    mid_angle = (start_angle + end_angle) / 2.0
    mid_r = (inner_r + outer_r) / 2.0
    mid_rad = math.radians(mid_angle)

    x = CX + mid_r * math.sin(mid_rad)
    y = CY - mid_r * math.cos(mid_rad)

    # Normalise mid_angle to -180..180 for flip logic
    norm = mid_angle % 360
    if norm > 180:
        norm -= 360

    if -90 <= norm <= 90:
        rotation = mid_angle
    else:
        rotation = mid_angle + 180

    return x, y, rotation


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------


def _compute_summary(artifact: dict) -> dict[str, int]:
    """Count items by status and grey_reason."""
    counts: dict[str, int] = {
        "green": 0,
        "yellow": 0,
        "red": 0,
        "grey_by_choice": 0,
        "grey_by_failure": 0,
        "grey_not_evaluated": 0,
    }
    for ring in artifact.get("rings", []):
        for item in ring.get("items", []):
            status = item.get("status", "grey")
            if status == "green":
                counts["green"] += 1
            elif status == "yellow":
                counts["yellow"] += 1
            elif status == "red":
                counts["red"] += 1
            elif status == "grey":
                reason = item.get("grey_reason")
                if reason == "by-choice":
                    counts["grey_by_choice"] += 1
                elif reason == "by-failure":
                    counts["grey_by_failure"] += 1
                else:
                    counts["grey_not_evaluated"] += 1
    return counts


def _summary_text(counts: dict[str, int]) -> str:
    """Build the summary line from counts."""
    parts: list[str] = []
    if counts["green"]:
        parts.append(f"{counts['green']} ok")
    if counts["yellow"]:
        parts.append(f"{counts['yellow']} attention")
    if counts["red"]:
        parts.append(f"{counts['red']} act")
    if counts["grey_by_choice"]:
        parts.append(f"{counts['grey_by_choice']} unmonitored")
    if counts["grey_by_failure"]:
        parts.append(f"{counts['grey_by_failure']} adapter failing")
    if counts["grey_not_evaluated"]:
        parts.append(f"{counts['grey_not_evaluated']} not evaluated")
    return " · ".join(parts) if parts else "0 items"


# ---------------------------------------------------------------------------
# SVG generation
# ---------------------------------------------------------------------------


def _render_svg(artifact: dict) -> str:
    """Render the sunburst SVG."""
    rings_data = artifact.get("rings", [])
    num_rings = len(rings_data)
    radii = _compute_radii(num_rings)

    parts: list[str] = []

    # --- Centre disc ---
    person = html.escape(artifact.get("person", ""))
    generated_at = html.escape(artifact.get("generated_at", ""))
    counts = _compute_summary(artifact)
    summary = html.escape(_summary_text(counts))

    parts.append(f'<circle cx="{CX}" cy="{CY}" r="{CENTRE_RADIUS}" fill="#f8f8f8" stroke="#ccc" stroke-width="1"/>')
    parts.append(f'<text x="{CX}" y="{CY - 8}" text-anchor="middle" dominant-baseline="central" font-size="11" font-weight="bold" fill="#333">{person}</text>')
    parts.append(f'<text x="{CX}" y="{CY + 10}" text-anchor="middle" dominant-baseline="central" font-size="8" fill="#666">{summary}</text>')
    parts.append(f'<text x="{CX}" y="{CY + 28}" text-anchor="middle" dominant-baseline="central" font-size="7" fill="#999">{generated_at}</text>')

    # --- Rings ---
    for ring_idx, ring in enumerate(rings_data):
        if ring_idx >= len(radii):
            break
        inner_r, outer_r = radii[ring_idx]
        items = ring.get("items", [])

        if not items:
            # Empty ring: draw full grey band
            d = _arc_path(0, 360, inner_r, outer_r)
            parts.append(
                f'<path d="{d}" fill="{STATUS_COLORS["grey"]}" '
                f'stroke="#ccc" stroke-width="0.5" opacity="0.5"/>'
            )
            continue

        total_share = sum(item.get("share", 1.0) for item in items)
        total_deg = 360.0 - CELL_GAP_DEG * len(items)

        # Compute raw arc angles first, floor at MIN_ARC_DEG, then rebalance
        # so the sum never overshoots 360° (CIR-RENDER-MIN-ARC).
        raw_arcs: list[float] = []
        for item in items:
            share = item.get("share", 1.0)
            arc_deg = total_deg * share / total_share
            raw_arcs.append(max(arc_deg, MIN_ARC_DEG))

        sum_arcs = sum(raw_arcs)
        # If floored arcs exceed the available degrees, scale them proportionally
        # so they fit within total_deg.
        if sum_arcs > total_deg and total_deg > 0:
            scale = total_deg / sum_arcs
            raw_arcs = [a * scale for a in raw_arcs]

        current_angle = -90.0  # 12 o'clock

        for item, arc_deg in zip(items, raw_arcs):
            start_angle = current_angle
            end_angle = current_angle + arc_deg

            status = item.get("status", "grey")
            color = STATUS_COLORS.get(status, STATUS_COLORS["grey"])
            label_color = LABEL_COLORS.get(status, "#000000")
            item_id = html.escape(item.get("id", ""))
            ring_id = html.escape(ring.get("id", ""))
            label = html.escape(item.get("label", ""))
            detail_line = html.escape(item.get("detail_line", ""))
            full_id = f"{ring_id}/{item_id}"

            d = _arc_path(start_angle, end_angle, inner_r, outer_r)
            lx, ly, lrot = _label_transform(start_angle, end_angle, inner_r, outer_r)

            # Arc cell
            parts.append(
                f'<g class="cell" data-item="{full_id}" data-detail="{detail_line}" '
                f'data-label="{label}" data-status="{status}" '
                f'tabindex="0" role="button" aria-label="{label}, {STATUS_WORDS.get(status, status)}, ring {html.escape(ring.get("label", ""))}">'
            )
            parts.append(
                f'<path d="{d}" fill="{color}" stroke="#fff" stroke-width="0.5"/>'
            )
            # Label
            parts.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="9" fill="{label_color}" '
                f'transform="rotate({lrot:.1f} {lx:.2f} {ly:.2f})" '
                f'pointer-events="none">{label}</text>'
            )
            parts.append("</g>")

            current_angle = end_angle + CELL_GAP_DEG

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------


def _render_chrome(artifact: dict) -> str:
    """Render the chrome panel HTML (ring key, legend, detail strip, stamp, warnings)."""
    rings_data = artifact.get("rings", [])
    warnings_list = artifact.get("warnings", [])
    generated_at = html.escape(artifact.get("generated_at", ""))

    lines: list[str] = []

    # --- Ring key ---
    lines.append('<div id="ring-key" class="chrome-section">')
    lines.append("<h2>Rings</h2>")
    lines.append("<ol>")
    for ring in rings_data:
        label = html.escape(ring.get("label", ""))
        lines.append(f"<li>{label}</li>")
    lines.append("</ol>")
    lines.append("</div>")

    # --- Legend ---
    lines.append('<div id="legend" class="chrome-section">')
    lines.append("<h2>Legend</h2>")
    for status in ("green", "yellow", "red", "grey"):
        color = STATUS_COLORS[status]
        word = STATUS_WORDS[status]
        lines.append(
            f'<div class="legend-item">'
            f'<span class="legend-swatch" style="background:{color}"></span>'
            f'<span class="legend-word">{word}</span>'
            f'</div>'
        )
    lines.append("</div>")

    # --- Detail strip ---
    lines.append('<div id="detail-strip" class="chrome-section">')
    lines.append('<div id="detail-content" class="detail-idle">Hover or focus a cell to see details</div>')
    lines.append("</div>")

    # --- Generated-at stamp ---
    lines.append('<div id="stamp" class="chrome-section stamp">')
    lines.append(f"Built: {generated_at}")
    lines.append("</div>")

    # --- Warnings banner ---
    if warnings_list:
        lines.append('<div id="warnings" class="chrome-section warnings">')
        count = len(warnings_list)
        first = html.escape(warnings_list[0].get("message", ""))
        lines.append(f'<details>')
        lines.append(f'<summary>{count} warning{"s" if count != 1 else ""} — {first}</summary>')
        lines.append("<ul>")
        for w in warnings_list:
            item_ref = html.escape(w.get("item", "")) if w.get("item") else ""
            msg = html.escape(w.get("message", ""))
            if item_ref:
                lines.append(f"<li><strong>{item_ref}:</strong> {msg}</li>")
            else:
                lines.append(f"<li>{msg}</li>")
        lines.append("</ul>")
        lines.append("</details>")
        lines.append("</div>")

    return "\n".join(lines)


def _render_a11y_table(artifact: dict) -> str:
    """Render the accessible text alternative table (CIR-RENDER-A11Y-TABLE)."""
    rings_data = artifact.get("rings", [])
    lines: list[str] = []

    lines.append('<details id="a11y-table">')
    lines.append("<summary>Text alternative</summary>")
    lines.append('<table>')
    lines.append("<thead><tr><th>Ring</th><th>Item</th><th>Status</th><th>Detail</th></tr></thead>")
    lines.append("<tbody>")

    for ring in rings_data:
        ring_label = html.escape(ring.get("label", ""))
        for item in ring.get("items", []):
            label = html.escape(item.get("label", ""))
            status = item.get("status", "grey")
            word = STATUS_WORDS.get(status, status)
            detail = html.escape(item.get("detail_line", ""))
            lines.append(f"<tr><td>{ring_label}</td><td>{label}</td><td>{word}</td><td>{detail}</td></tr>")

    lines.append("</tbody>")
    lines.append("</table>")
    lines.append("</details>")

    return "\n".join(lines)


def _render_styles() -> str:
    """Render the inline CSS."""
    return """* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #fff; color: #333; }
#app { display: flex; flex-direction: row; height: 100vh; max-height: 100vh; overflow: hidden; }
#chart-area { flex: 1 1 60%; display: flex; align-items: center; justify-content: center; min-width: 0; padding: 10px; }
#chart-area svg { max-width: 100%; max-height: 100%; }
#chrome-panel { flex: 0 0 320px; overflow-y: auto; padding: 20px; border-left: 1px solid #e0e0e0; display: flex; flex-direction: column; gap: 16px; }
.chrome-section h2 { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #888; margin-bottom: 6px; }
#ring-key ol { list-style: none; padding: 0; }
#ring-key li { font-size: 13px; padding: 2px 0; color: #444; }
#ring-key li::before { content: "— "; color: #aaa; }
.legend-item { display: flex; align-items: center; gap: 8px; padding: 3px 0; }
.legend-swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.1); flex-shrink: 0; }
.legend-word { font-size: 13px; color: #444; }
#detail-strip { min-height: 40px; }
.detail-idle { font-size: 12px; color: #aaa; font-style: italic; }
.detail-active { font-size: 13px; color: #222; font-weight: 500; }
.stamp { font-size: 11px; color: #999; }
.warnings { font-size: 12px; }
.warnings summary { cursor: pointer; color: #b22222; font-weight: 500; }
.warnings ul { margin: 6px 0 0 16px; }
.warnings li { margin: 2px 0; color: #555; }
/* Cell hover/focus */
.cell { cursor: pointer; outline: none; }
.cell:hover path, .cell:focus-visible path { stroke: #333; stroke-width: 2; }
.cell:focus-visible path { stroke-dasharray: 3 2; }
/* A11y table */
#a11y-table { margin: 0 20px 20px; font-size: 12px; }
#a11y-table summary { cursor: pointer; font-size: 13px; color: #555; padding: 4px 0; }
#a11y-table table { width: 100%; border-collapse: collapse; margin-top: 8px; }
#a11y-table th, #a11y-table td { text-align: left; padding: 4px 8px; border-bottom: 1px solid #eee; }
#a11y-table th { font-weight: 600; color: #666; font-size: 11px; text-transform: uppercase; }
/* Print styles */
@media print {
  @page { margin: 10mm; size: A4 portrait; }
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  #app { display: block; height: auto; max-height: none; overflow: visible; }
  #chart-area { display: block; text-align: center; padding: 0; }
  #chart-area svg { max-width: 100%; max-height: 70vh; }
  #chrome-panel { border-left: none; padding: 10px 0; overflow: visible; }
  .cell:hover path, .cell:focus-visible path { stroke: #fff; stroke-width: 0.5; }
  .cell:focus-visible path { stroke-dasharray: none; }
  #a11y-table { margin: 10px 0; }
  #a11y-table table { font-size: 10px; }
  .detail-idle { display: none; }
}
@media print and (prefers-color-scheme: dark) {
  /* Force light background for print */
  html, body { background: #fff !important; color: #000 !important; }
}
"""


def _render_script() -> str:
    """Render the inline JS for hover/focus interaction."""
    return """(function() {
  var strip = document.getElementById('detail-content');
  if (!strip) return;
  var cells = document.querySelectorAll('.cell');
  function showDetail(e) {
    var cell = e.currentTarget;
    var detail = cell.getAttribute('data-detail') || '';
    var label = cell.getAttribute('data-label') || '';
    if (detail) {
      strip.textContent = label + ' — ' + detail;
      strip.className = 'detail-active';
    } else {
      strip.textContent = label;
      strip.className = 'detail-active';
    }
  }
  function resetDetail() {
    strip.textContent = 'Hover or focus a cell to see details';
    strip.className = 'detail-idle';
  }
  for (var i = 0; i < cells.length; i++) {
    cells[i].addEventListener('mouseenter', showDetail);
    cells[i].addEventListener('mouseleave', resetDetail);
    cells[i].addEventListener('focus', showDetail);
    cells[i].addEventListener('blur', resetDetail);
  }
})();
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _add_capacity_warnings(artifact: dict) -> list[dict]:
    """Check capacity envelope and return any additional warnings.

    CIR-RENDER-CAPACITY: ≤6 rings, ≤8 items/ring for legibility.
    CIR-RENDER-MIN-ARC: warn when many items force tiny arcs.
    """
    warnings: list[dict] = []
    rings = artifact.get("rings", [])

    num_rings = len(rings)
    if num_rings > 6:
        warnings.append({
            "item": None,
            "message": f"Page has {num_rings} rings — exceeds legibility envelope of 6. "
                       f"Labels may be elided and cells may be smaller than the minimum "
                       f"hover/focus target.",
        })

    for ring in rings:
        ring_id = ring.get("id", "")
        ring_label = ring.get("label", "")
        items = ring.get("items", [])
        num_items = len(items)

        if num_items == 0:
            warnings.append({
                "item": f"{ring_id}",
                "message": f"Ring \"{ring_label}\" ({ring_id}) has no items — "
                           f"rendered as unmonitored band.",
            })
        elif num_items > 8:
            warnings.append({
                "item": f"{ring_id}",
                "message": f"Ring \"{ring_label}\" ({ring_id}) has {num_items} items — "
                           f"exceeds legibility envelope of 8 per ring. "
                           f"Labels may be elided and cells below minimum hover target.",
            })

        # CIR-RENDER-MIN-ARC: check if items per ring would squeeze arcs below minimum
        if num_items > 0:
            available_deg = 360.0 - CELL_GAP_DEG * num_items
            max_items_at_min = int(available_deg / MIN_ARC_DEG)
            if num_items > max_items_at_min:
                warnings.append({
                    "item": f"{ring_id}",
                    "message": f"Ring \"{ring_label}\" ({ring_id}) has {num_items} items — "
                               f"exceeds {max_items_at_min} items at {MIN_ARC_DEG}° minimum arc. "
                               f"Arcs are scaled proportionally to fit within 360°.",
                })

    return warnings


def add_capacity_warnings(artifact: dict) -> dict:
    """Add capacity/min-arc warnings to the artifact (CIR-RENDER-CAPACITY, CIR-RENDER-MIN-ARC).

    Returns a new dict with the warnings appended. Call this between resolve()
    and both write_artifact()/render_page() so both data.json and index.html
    carry the same warnings (CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file).
    """
    capacity_warnings = _add_capacity_warnings(artifact)
    if not capacity_warnings:
        return artifact
    result = dict(artifact)
    result["warnings"] = artifact.get("warnings", []) + capacity_warnings
    return result


def render_page(artifact: dict) -> str:
    """Return the complete self-contained index.html with the artifact inlined.

    The artifact dict is inlined as a JSON script block AND rendered as SVG.
    A test asserts the inlined data is identical to the file
    (CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file).
    """
    import json

    person = html.escape(artifact.get("person", "circles"))
    title = f"{person} — circles"

    svg_content = _render_svg(artifact)
    chrome_html = _render_chrome(artifact)
    a11y_html = _render_a11y_table(artifact)
    styles = _render_styles()
    script = _render_script()

    # Inline the artifact as JSON for testability (CIR-BAKE-SELF-CONTAINED)
    artifact_json = json.dumps(artifact, indent=2, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{styles}</style>
</head>
<body>
<div id="app">
<div id="chart-area">
<svg viewBox="0 0 800 800" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="circles sunburst chart for {person}">
{svg_content}
</svg>
</div>
<div id="chrome-panel">
{chrome_html}
</div>
</div>
{a11y_html}
<script id="artifact-data" type="application/json">
{artifact_json}
</script>
<script>{script}</script>
</body>
</html>"""