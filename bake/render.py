# bake/render.py — the complete self-contained index.html with the artifact inlined
#
# Requirements owned:
#   CIR-BAKE-SELF-CONTAINED, CIR-RENDER-RING-ORDER, -RING-PARTITION, -ARC-SHARE,
#   -SIBLING-ORDER, -RING-THICKNESS, -MIN-ARC, -LABELS, -SUMMARY, -CAPACITY,
#   -RENDERER, -PALETTE, -GREY-VISIBLE, -STATUS-ENCODING, -LEGEND, -A11Y-TABLE,
#   -CHROME, -GENERATED-AT, -BOOT-FAILURE, -NO-EGRESS, -ASSET-BUDGET,
#   -NO-JS, -HOVER, -KEYBOARD, -TOUCH, -CLICK,
#   -ONE-SCREEN, -REFERENCE-VIEWPORT, -STALE-MARK
#   CIR-BAKE-STALE-SELF (the page judges its own staleness at view time)
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
# The outermost ring's outer edge never passes this radius: the viewBox is 800×800 (half-extent
# 400), less a margin for the hover/focus stroke — so every ring at every ring count is drawn
# inside the chart (CIR-RENDER-CAPACITY#capacity-at-limit, #capacity-exceeded-ring-count).
CHART_RADIUS = 396.0
# The centre hole (CIR-RENDER-RING-THICKNESS#centre-hole-is-not-zero) is sized to hold the
# identity — name, summary counts, stamp (#centre-disc-holds-identity); its texts are fitted
# to it (_fit_font).
CENTRE_RADIUS = 100.0
RING_GAP = 4.0
BASE_THICKNESS = 80.0
THICKNESS_DECAY = 10.0
MIN_THICKNESS = 30.0
CELL_GAP_DEG = 2.0
# Gaps never take more than this share of a ring's circle, so a ring holding more cells than
# the 2° gaps allow still closes at 360° with every arc wider than 0°
# (CIR-RENDER-MIN-ARC#overflow-capped-at-total-deg, #overflow-no-negative-arcs).
MAX_GAP_SHARE = 0.5
MIN_ARC_DEG = 3.0  # minimum arc angle after gap
# Centre-disc text: nominal sizes (user units), and a conservative average glyph advance in em
# for the bake-time width estimate (sans-serif mixed case/digits measures ≈ 0.49 em).
NAME_FONT = 11.0
SUMMARY_FONT = 8.0
STAMP_FONT = 7.0
GLYPH_EM = 0.55

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


def _gap_deg(num_items: int) -> float:
    """The inter-cell gap for a ring of ``num_items`` cells.

    A single-item ring has no gap (CIR-RENDER-ARC-SHARE#arc-share-single-item-ring). Otherwise
    the gap is CELL_GAP_DEG, shrunk only when a ring's gaps would take more than MAX_GAP_SHARE
    of the circle — the overflow case, where fixed gaps alone would run past 360°
    (CIR-RENDER-MIN-ARC#overflow-no-negative-arcs).
    """
    if num_items <= 1:
        return 0.0
    return min(CELL_GAP_DEG, 360.0 * MAX_GAP_SHARE / num_items)


def _total_deg(num_items: int) -> float:
    """Compute total degrees available for arc placement (360° less the ring's gaps).

    A single-item ring spans the full 360° with no visible gap
    (CIR-RENDER-ARC-SHARE#arc-share-single-item-ring,
     CIR-RENDER-RING-PARTITION#partition-full-circle-per-ring). Never ≤ 0: the gaps are capped
    (_gap_deg), so arcs plus gaps always make exactly 360°.
    """
    return 360.0 - _gap_deg(num_items) * num_items


def _compute_radii(num_rings: int) -> list[tuple[float, float]]:
    """Compute (inner_radius, outer_radius) for each ring, inside-out.

    Thickness is non-increasing outward (CIR-RENDER-RING-THICKNESS, ⚖-R10 (b)). The nominal
    thicknesses are scaled down uniformly — which keeps them non-increasing — when the rings
    would otherwise pass CHART_RADIUS, so every ring at every ring count is drawn inside the
    chart (CIR-RENDER-CAPACITY). The centre hole is never scaled away
    (#centre-hole-is-not-zero).
    """
    if num_rings <= 0:
        return []
    nominal = [max(BASE_THICKNESS - i * THICKNESS_DECAY, MIN_THICKNESS) for i in range(num_rings)]
    available = CHART_RADIUS - CENTRE_RADIUS - RING_GAP * (num_rings - 1)
    scale = min(1.0, available / sum(nominal))
    radii: list[tuple[float, float]] = []
    inner = CENTRE_RADIUS
    for thickness in nominal:
        outer = inner + thickness * scale
        radii.append((inner, outer))
        inner = outer + RING_GAP
    return radii


def _fit_font(text: str, nominal: float, centre_dy: float, pad: float = 6.0) -> float:
    """Font size for one centre-disc line: the nominal size, shrunk until the line's estimated
    box fits inside the centre hole (CIR-RENDER-RING-THICKNESS#centre-disc-holds-identity).

    The width is estimated from the character count at GLYPH_EM per em (no font metrics at
    bake time); the line's box spans ``centre_dy`` ± half a line height from the centre.
    """
    if not text:
        return nominal
    font = nominal
    for _ in range(4):  # the box's height depends on the font; converge
        reach = abs(centre_dy) + 0.6 * font
        if reach >= CENTRE_RADIUS:
            break
        chord = 2.0 * math.sqrt(CENTRE_RADIUS ** 2 - reach ** 2) - 2.0 * pad
        font = min(nominal, chord / (GLYPH_EM * len(text)))
    return round(font, 2)


def _arc_path(
    start_angle: float,
    end_angle: float,
    inner_r: float,
    outer_r: float,
) -> str:
    """Return SVG path d attribute for an arc segment.

    Angles in degrees, clockwise from 12 o'clock.

    Full-circle arcs (sweep ≈ 360°) are split into two half-circle arcs
    because SVG elliptical-arc commands with coincident start/end points
    are omitted by conforming renderers (CIR-RENDER-ARC-SHARE
    #arc-share-single-item-ring).
    """
    sweep = end_angle - start_angle

    # Full circle: split into two half-circle arcs so no single A command
    # has coincident start/end points.
    if abs(sweep) >= 359.999:
        mid = start_angle + sweep / 2.0
        return (
            _arc_path(start_angle, mid, inner_r, outer_r)
            + " "
            + _arc_path(mid, end_angle, inner_r, outer_r)
        )

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


def _cell_element(item: dict) -> tuple[str, str]:
    """Return the (opening prefix, closing tag) for one cell, per CIR-RENDER-CLICK.

    A cell's destination is its configured ``link`` if it has one, else its baked
    detail page — the latter is P2, so only ``link`` is a destination here (⚖-R11
    rules ``link`` the winner when both exist, which keeps this ordering stable when
    P2 lands).  A cell with no destination is **not clickable**: it stays a
    ``<g role="button">`` with no href and, via the stylesheet, no pointer cursor
    (``#click-no-destination``).

    A cell with a destination is rendered as the anchor itself rather than wrapped in
    one, so it remains a single focus stop.  Absolute ``http(s)://`` destinations open
    in a new tab with ``rel="noopener"`` (``#click-follows-link``); root-relative ones
    navigate in place (``#click-root-relative``).  ``link:`` values are restricted to
    those two shapes at bake time (CIR-DATA-SCHEMA-LINK), so no other case can arrive.

    The opening prefix is returned unterminated — the caller appends the shared cell
    attributes and the closing ``>``.
    """
    link = item.get("link")
    if not link:
        return '<g class="cell" role="button" ', "</g>"

    href = html.escape(link, quote=True)
    if link.startswith("http://") or link.startswith("https://"):
        return (
            f'<a class="cell cell-linked" role="link" href="{href}" '
            f'target="_blank" rel="noopener" ',
            "</a>",
        )
    return f'<a class="cell cell-linked" role="link" href="{href}" ', "</a>"


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

    # Hatch pattern for the stale overlay (CIR-RENDER-STALE-MARK, ⚖-R42). Lines, not
    # paths, so the cell-path count stays the arc count.
    parts.append(
        '<defs><pattern id="stale-hatch" width="12" height="12" '
        'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="12" stroke="#ffffff" stroke-width="5" '
        'stroke-opacity="0.55"/></pattern></defs>'
    )
    parts.append(f'<circle cx="{CX}" cy="{CY}" r="{CENTRE_RADIUS}" fill="#f8f8f8" stroke="#ccc" stroke-width="1"/>')
    # The identity sits inside the hole (CIR-RENDER-RING-THICKNESS#centre-disc-holds-identity):
    # the summary — the longest line — on the centre line where the hole is widest, the name
    # above it, the stamp below; each line's font fitted to the hole's chord at its height.
    # Sizes are computed on the unescaped text (what is drawn).
    name_font = _fit_font(artifact.get("person", ""), NAME_FONT, -18.0)
    summary_font = _fit_font(_summary_text(counts), SUMMARY_FONT, 0.0)
    stamp_font = _fit_font(artifact.get("generated_at", ""), STAMP_FONT, 15.0)
    parts.append(f'<text x="{CX}" y="{CY - 18}" text-anchor="middle" dominant-baseline="central" font-size="{name_font}" font-weight="bold" fill="#333">{person}</text>')
    parts.append(f'<text x="{CX}" y="{CY}" text-anchor="middle" dominant-baseline="central" font-size="{summary_font}" fill="#666">{summary}</text>')
    parts.append(f'<text x="{CX}" y="{CY + 15}" text-anchor="middle" dominant-baseline="central" font-size="{stamp_font}" fill="#999">{generated_at}</text>')

    # --- Rings ---
    for ring_idx, ring in enumerate(rings_data):
        if ring_idx >= len(radii):
            break
        inner_r, outer_r = radii[ring_idx]
        items = ring.get("items", [])

        if not items:
            # Empty ring: a full band in the unmonitored treatment — the very paint an
            # unmonitored ⚪ cell gets, no reduced opacity, no ghost stroke
            # (CIR-RENDER-CAPACITY#capacity-empty-ring-band, CIR-RENDER-GREY-VISIBLE).
            d = _arc_path(0, 360, inner_r, outer_r)
            parts.append(
                f'<path d="{d}" fill="{STATUS_COLORS["grey"]}" stroke="#fff" stroke-width="0.5"/>'
            )
            continue

        total_share = sum(item.get("share", 1.0) for item in items)

        total_deg = _total_deg(len(items))
        gap_deg = _gap_deg(len(items))

        # Compute natural arc angles, then iteratively floor-and-redistribute
        # so floored arcs keep MIN_ARC_DEG and remaining arcs absorb the
        # reduction proportionally (CIR-RENDER-MIN-ARC).
        # A naive proportional rescale after flooring is self-defeating:
        # when every arc floors, rescaling pushes them all back below MIN_ARC_DEG.
        raw_arcs = [total_deg * item.get("share", 1.0) / total_share for item in items]

        while True:
            floored = [i for i, a in enumerate(raw_arcs) if a < MIN_ARC_DEG]
            natural = [i for i, a in enumerate(raw_arcs) if a >= MIN_ARC_DEG]

            floored_sum = len(floored) * MIN_ARC_DEG

            if floored_sum > total_deg:
                # Even floored arcs alone overflow — divide total_deg
                # equally among all items so the total consumed angle never
                # exceeds total_deg (CIR-RENDER-MIN-ARC
                # #overflow-capped-at-total-deg).  When floored arcs alone
                # exceed the available space, every arc must be smaller than
                # MIN_ARC_DEG, so distribute evenly.
                raw_arcs = [total_deg / len(raw_arcs)] * len(raw_arcs)
                break

            if not natural:
                # All arcs floored and they fit within total_deg.
                for i in floored:
                    raw_arcs[i] = MIN_ARC_DEG
                break

            remaining_deg = total_deg - floored_sum
            natural_total = sum(raw_arcs[i] for i in natural)

            # Rescale natural arcs to fill remaining space
            for i in natural:
                raw_arcs[i] = remaining_deg * raw_arcs[i] / natural_total

            # Apply floor to floored arcs
            for i in floored:
                raw_arcs[i] = MIN_ARC_DEG

            # Check if any rescaled natural arc fell below MIN_ARC_DEG
            new_floored = [i for i in natural if raw_arcs[i] < MIN_ARC_DEG]
            if not new_floored:
                break
            # Continue loop — newly floored arcs will be handled next iteration

        # 0° IS 12 o'clock in this frame (x = cx + r·sin, y = cy − r·cos); -90 started every ring
        # at 9 o'clock (CIR-RENDER-SIBLING-ORDER#sibling-order-clockwise-from-noon, caught by the
        # browser tier in circles#103).
        current_angle = 0.0

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

            # Build aria-label: include grey reason for grey cells
            # (CIR-RENDER-GREY-VISIBLE — per-cell hover-free path for screen-reader users)
            aria_label = f"{label}, {STATUS_WORDS.get(status, status)}, ring {html.escape(ring.get('label', ''))}"
            if status == "grey":
                reason = item.get("grey_reason", "")
                if reason == "by-choice":
                    aria_label += ", by choice"
                elif reason == "by-failure":
                    aria_label += ", adapter failing"
                else:
                    aria_label += ", not evaluated"
            # The cell's destination (CIR-RENDER-CLICK).  A cell with a `link:` IS
            # the anchor rather than being wrapped in one, so a linked cell stays a
            # single tab stop (CIR-RENDER-KEYBOARD#keyboard-no-trap) and navigates
            # with scripting disabled (CIR-RENDER-NO-JS#no-js-links-work).
            open_tag, close_tag = _cell_element(item)
            parts.append(
                f'{open_tag}data-item="{full_id}" data-detail="{detail_line}" '
                f'data-label="{label}" data-status="{status}" '
                f'tabindex="0" aria-label="{aria_label}">'
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
            parts.append(close_tag)

            current_angle = end_angle + gap_deg

    # Stale overlay (CIR-RENDER-STALE-MARK#stale-is-not-a-fifth-colour): one hatched disc
    # over the whole picture, a separate visual channel ON TOP of the cells — the cells'
    # fills are never touched. Hidden by the stylesheet unless the page script marks the
    # page stale; pointer-events none so hover/focus/click still reach the cells.
    outer = radii[-1][1] if radii else CENTRE_RADIUS
    parts.append(
        f'<circle id="stale-overlay" cx="{CX}" cy="{CY}" r="{outer:.2f}" '
        f'fill="url(#stale-hatch)" pointer-events="none" aria-hidden="true"/>'
    )

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

    # --- Stale banner (CIR-BAKE-STALE-SELF, CIR-RENDER-STALE-MARK) ---
    # Baked empty and hidden; the page script fills and shows it at VIEW time when the
    # browser's clock says `generated_at` is older than the artifact's
    # `stale_after_hours`. First in the chrome column so it is the first thing read.
    lines.append('<div id="stale-banner" class="chrome-section stale-banner" role="alert" hidden></div>')

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
/* Stale treatment (CIR-RENDER-STALE-MARK, ⚖-R42 (a)): banner + desaturation + hatched
   overlay, all keyed off one class the page script sets. Statuses keep their colours
   (fills are untouched); never red — a dead pipeline is not "act on your life". */
.stale-banner { font-size: 12px; font-weight: 600; color: #333; background: #eeeeee; border-left: 4px solid #666; padding: 6px 8px; }
#stale-overlay { display: none; }
#app.is-stale #chart-area svg { filter: saturate(0.35); }
#app.is-stale #stale-overlay { display: inline; }
.warnings summary { cursor: pointer; color: #b22222; font-weight: 500; }
.warnings ul { margin: 6px 0 0 16px; }
.warnings li { margin: 2px 0; color: #555; }
/* Cell hover/focus */
/* Only a cell with a destination gets the pointer cursor — a cell with neither a
   link nor a detail page is not clickable (CIR-RENDER-CLICK#click-no-destination). */
.cell { cursor: default; outline: none; }
.cell-linked { cursor: pointer; }
.cell:hover path, .cell:focus-visible path { stroke: #333; stroke-width: 2; }
.cell:focus-visible path { stroke-dasharray: 3 2; }
/* A11y table */
/* The text alternative lives INSIDE the chrome column (which scrolls on its own), never
   after the 100vh #app box — a sibling below it overflows the viewport
   (CIR-RENDER-ONE-SCREEN, issue #93). */
#a11y-table { font-size: 12px; }
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
  #chart-area svg { max-width: 100%; max-height: 62vh; }
  /* One A4 portrait sheet (CIR-RENDER-A4#print-single-a4-portrait): under the chart the
     chrome packs into two columns — ring key | legend — with the stamp, warnings and the
     text alternative spanning full width. The detail strip is hover-only, not paper. */
  #chrome-panel { border-left: none; padding: 6px 0 0; overflow: visible; display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px; }
  #stale-banner, #stamp, #warnings, #a11y-table { grid-column: 1 / -1; }
  .stale-banner { padding: 3px 6px; font-size: 10px; }
  #detail-strip { display: none; }
  .cell:hover path, .cell:focus-visible path { stroke: #fff; stroke-width: 0.5; }
  .cell:focus-visible path { stroke-dasharray: none; }
  /* A closed <details> does not print its body; force it open on paper
     (CIR-RENDER-A4#print-detail-reaches-paper). */
  #a11y-table::details-content { content-visibility: visible; display: block; }
  #a11y-table summary { list-style: none; padding: 0; }
  #a11y-table table { font-size: 9px; margin-top: 4px; }
  #a11y-table th, #a11y-table td { padding: 1px 4px; }
  .detail-idle { display: none; }
}
@media print and (prefers-color-scheme: dark) {
  /* Force light background for print */
  html, body { background: #fff !important; color: #000 !important; }
}
"""


def _render_script() -> str:
    """Render the inline JS: the view-time stale check, then hover/focus interaction."""
    return """// Page self-staleness (CIR-BAKE-STALE-SELF, CIR-RENDER-STALE-MARK). Judged at VIEW
// time: the browser's clock against the artifact's generated_at, past the artifact's own
// stale_after_hours (threshold-comes-from-the-artifact — no number lives in this code).
// null (P0) => no banner, no overlay; the stamp is shown regardless. This check needs JS:
// with scripting off the page renders exactly as baked (no stale chrome), and everything
// else — picture, stamp, links, text alternative — still works without it.
(function() {
  var data;
  try { data = JSON.parse(document.getElementById('artifact-data').textContent); }
  catch (e) { return; }
  var limit = data && data.stale_after_hours;
  if (typeof limit !== 'number' || !isFinite(limit)) return;
  var built = Date.parse(data.generated_at);
  if (isNaN(built)) return;
  var ageMs = Date.now() - built;
  if (ageMs <= limit * 3600000) return;
  var n = Math.floor(ageMs / 3600000);
  var banner = document.getElementById('stale-banner');
  var app = document.getElementById('app');
  if (!banner || !app) return;
  banner.textContent = 'this page was built ' + n + (n === 1 ? ' hour' : ' hours') +
    ' ago; the lights below are history';
  banner.hidden = false;
  app.className = (app.className ? app.className + ' ' : '') + 'is-stale';
})();
(function() {
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

        # An empty ring is warned about by the config loader (CIR-DATA-VALIDATION#empty-ring,
        # ⚖-R13) — that one warning is CIR-RENDER-CAPACITY#capacity-empty-ring-band's "plus a
        # warning"; repeating it here would warn twice about one ring.
        if num_items > 8:
            warnings.append({
                "item": None,  # ring-level: not an item ref (CIR-BAKE-WARNINGS)
                "message": f"Ring \"{ring_label}\" ({ring_id}) has {num_items} items — "
                           f"exceeds legibility envelope of 8 per ring. "
                           f"Labels may be elided and cells below minimum hover target.",
            })

        # CIR-RENDER-MIN-ARC: check if items per ring would squeeze arcs below minimum
        if num_items > 0:
            available_deg = _total_deg(num_items)
            max_items_at_min = int(available_deg / MIN_ARC_DEG) if available_deg > 0 else 0
            if num_items > max_items_at_min:
                warnings.append({
                    "item": None,  # ring-level: not an item ref (CIR-BAKE-WARNINGS)
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
    # Escape </script> sequences in string content to prevent premature script tag
    # closure (CIR-BAKE-SELF-CONTAINED#script-escape).  \/ is a valid JSON escape
    # sequence equivalent to /, so the JSON data round-trips correctly.
    artifact_json = json.dumps(artifact, indent=2, ensure_ascii=False).replace("</", "<\\/")

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
{a11y_html}
</div>
</div>
<script id="artifact-data" type="application/json">
{artifact_json}
</script>
<script>{script}</script>
</body>
</html>"""