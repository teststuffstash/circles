"""Generate the self-contained HTML page from the baked artifact.

Hand-rolled SVG concentric bands (⚖-R3). The page is fully self-contained with
inlined data (CIR-BAKE-SELF-CONTAINED), no external requests
(CIR-RENDER-NO-EGRESS), fits one screen (CIR-RENDER-ONE-SCREEN), and renders
its picture + a11y table with scripting disabled (CIR-RENDER-NO-JS — the
geometry and table are baked, JS adds only interaction).
"""
from __future__ import annotations

import json
import math
from typing import Any

from bake.artifact import BakedArtifact

# ── palette (CIR-RENDER-PALETTE) ─────────────────────────────────────────────
COLORS = {
    "ok": "#008F68",
    "attention": "#F2B300",
    "act": "#B22222",
    "unmonitored": "#9E9E9E",
}
STATUS_TO_COLOR = {"green": "#008F68", "yellow": "#F2B300", "red": "#B22222", "grey": "#9E9E9E"}
STATUS_TO_WORD = {"green": "ok", "yellow": "attention", "red": "act", "grey": "unmonitored"}
LABEL_COLOR = {"green": "#ffffff", "yellow": "#000000", "red": "#ffffff", "grey": "#000000"}

CX, CY = 200.0, 200.0
HOLE_R = 40.0
GAP_DEG = 1.5
MAX_R = 155.0


def _to_rad(deg: float) -> float:
    return deg * math.pi / 180.0


def _describe_arc(r1: float, r2: float, start_deg: float, sweep_deg: float) -> str:
    """SVG path for an annular sector centered at (CX, CY)."""
    start = _to_rad(start_deg)
    end = _to_rad(start_deg + sweep_deg)
    x1 = CX + r1 * math.sin(start)
    y1 = CY - r1 * math.cos(start)
    x2 = CX + r2 * math.sin(start)
    y2 = CY - r2 * math.cos(start)
    x3 = CX + r2 * math.sin(end)
    y3 = CY - r2 * math.cos(end)
    x4 = CX + r1 * math.sin(end)
    y4 = CY - r1 * math.cos(end)
    large = 1 if sweep_deg > 180 else 0
    return (
        f"M{x1:.2f},{y1:.2f} L{x2:.2f},{y2:.2f} "
        f"A{r2:.2f},{r2:.2f} 0 {large} 1 {x3:.2f},{y3:.2f} "
        f"L{x4:.2f},{y4:.2f} A{r1:.2f},{r1:.2f} 0 {large} 0 {x1:.2f},{y1:.2f} Z"
    )


def _ring_thicknesses(ring_count: int) -> list[float]:
    """Non-increasing outward (CIR-RENDER-RING-THICKNESS), scaled to the viewBox."""
    if ring_count == 0:
        return []
    base = [max(36 - i * 4, 18) for i in range(ring_count)]
    total = sum(base)
    scale = (MAX_R - HOLE_R) / total
    return [round(t * scale, 1) for t in base]


def _summarize(artifact: BakedArtifact) -> str:
    """One-line summary counts (CIR-RENDER-SUMMARY), separated by grey reason."""
    counts: dict[str, int] = {"green": 0, "yellow": 0, "red": 0, "by-choice": 0, "by-failure": 0}
    for ring in artifact.rings or []:
        for item in ring.get("items", []) or []:
            status = item.get("status")
            if status == "grey":
                if item.get("grey_reason") == "by-choice":
                    counts["by-choice"] += 1
                else:
                    counts["by-failure"] += 1
            elif status in counts:
                counts[status] += 1
    parts: list[str] = []
    for key, label in (
        ("green", "ok"),
        ("yellow", "attention"),
        ("red", "act"),
        ("by-choice", "unmonitored"),
        ("by-failure", "not evaluated"),
    ):
        if counts.get(key):
            parts.append(f"{counts[key]} {label}")
    return " · ".join(parts)


def _render_static_svg(artifact: BakedArtifact) -> str:
    """The sunburst as static SVG markup (baked, so no-JS sees the picture)."""
    rings_data = artifact.rings or []
    thicknesses = _ring_thicknesses(len(rings_data))
    radii: list[dict[str, float]] = []
    inner = HOLE_R
    for t in thicknesses:
        radii.append({"inner": inner, "outer": inner + t, "mid": inner + t / 2})
        inner += t

    parts: list[str] = []
    for ri, ring in enumerate(rings_data):
        rr = radii[ri]
        items = ring.get("items", []) or []
        n = len(items)
        if n == 0:
            # empty band (⚖-R13) — draw the band in the unmonitored treatment
            parts.append(
                f'<path d="{_describe_arc(rr["inner"], rr["outer"], 0, 360)}" '
                f'fill="{STATUS_TO_COLOR["grey"]}" stroke="#fff" stroke-width="1.5"/>'
            )
            continue
        sum_shares = sum(float(it.get("share", 1)) for it in items)
        gap = GAP_DEG if n > 1 else 0.0
        available = 360.0 - n * gap
        start = 0.0  # 12 o'clock, clockwise (CIR-RENDER-SIBLING-ORDER)
        for it in items:
            sweep = float(it.get("share", 1)) / sum_shares * available
            status = it.get("status", "grey")
            color = STATUS_TO_COLOR.get(status, STATUS_TO_COLOR["grey"])
            path = _describe_arc(rr["inner"], rr["outer"], start, sweep)
            parts.append(
                f'<path class="cell" data-ring="{_escape_html(ring.get("id", ""))}" '
                f'data-item="{_escape_html(it.get("id", ""))}" d="{path}" fill="{color}" '
                f'stroke="#fff" stroke-width="1.5" tabindex="0" '
                f'aria-label="{_escape_html(_cell_aria(ring, it))}"/>'
            )
            parts.append(_label_markup(rr["mid"], start + sweep / 2, status, str(it.get("label", ""))))
            start += sweep + gap

    # centre disc (⚖-R9 — name, summary; never a light)
    parts.append(
        f'<circle cx="{CX}" cy="{CY}" r="{HOLE_R}" fill="#f8f8f8" stroke="#dddddd"/>'
    )
    person = _escape_html(artifact.person or "")
    summary = _escape_html(_summarize(artifact))
    parts.append(
        f'<text x="{CX}" y="{CY - 6}" text-anchor="middle" dominant-baseline="auto" '
        f'font-size="12" font-weight="600" fill="#333">{person}</text>'
    )
    parts.append(
        f'<text x="{CX}" y="{CY + 10}" text-anchor="middle" dominant-baseline="hanging" '
        f'font-size="8.5" fill="#666">{summary}</text>'
    )

    return "".join(parts)


def _cell_aria(ring: dict[str, Any], item: dict[str, Any]) -> str:
    """Accessible name: <label>, <status word>, ring <ring label> (CIR-RENDER-KEYBOARD)."""
    label = item.get("label", "")
    word = STATUS_TO_WORD.get(item.get("status", ""), "?")
    ring_label = ring.get("label", "")
    return f"{label}, {word}, ring {ring_label}"


def _label_markup(mid_r: float, mid_angle: float, status: str, label: str) -> str:
    """A radial label centered on the cell's mid-angle (CIR-RENDER-LABELS)."""
    if not label:
        return ""
    # flip on the left half so text stays upright
    angle = mid_angle + 180 if 90 < mid_angle < 270 else mid_angle
    rad = _to_rad(angle)
    x = CX + mid_r * math.sin(rad)
    y = CY - mid_r * math.cos(rad)
    fill = LABEL_COLOR.get(status, "#000000")
    # estimate: truncate with … when it would overflow the arc chord
    font_size = 9.5
    est_width = len(label) * font_size * 0.6
    chord = 2 * mid_r * math.sin(_to_rad(min(45, 360 - 0)))  # placeholder
    # chord at half-sweep is not available here; use a conservative cap instead
    max_len = max(1, int((mid_r * 0.9) / (font_size * 0.6)))
    if len(label) > max_len:
        label = label[: max_len - 1] + "…"
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="central" '
        f'font-size="{font_size}" fill="{fill}" pointer-events="none" '
        f'data-mid-angle="{mid_angle:.1f}">{_escape_html(label)}</text>'
    )


def _render_ring_key(artifact: BakedArtifact) -> str:
    rows = [
        f'<li>{_escape_html(ring.get("label", ""))}</li>' for ring in (artifact.rings or [])
    ]
    return "\n".join(rows)


def _render_legend() -> str:
    entries = [
        ("ok", COLORS["ok"]),
        ("attention", COLORS["attention"]),
        ("act", COLORS["act"]),
        ("unmonitored", COLORS["unmonitored"]),
    ]
    parts = []
    for word, color in entries:
        parts.append(
            f'<div class="legend-item"><span class="legend-swatch" '
            f'style="background:{color}"></span><span>{word}</span></div>'
        )
    return "\n".join(parts)


def _render_a11y_table(artifact: BakedArtifact) -> str:
    rows = []
    for ring in artifact.rings or []:
        for item in ring.get("items", []) or []:
            word = STATUS_TO_WORD.get(item.get("status", ""), "?")
            rows.append(
                "<tr>"
                f"<td>{_escape_html(ring.get('label', ''))}</td>"
                f"<td>{_escape_html(item.get('label', ''))}</td>"
                f"<td>{word}</td>"
                f"<td>{_escape_html(item.get('guardrail') or '—')}</td>"
                f"<td>{_escape_html(item.get('note') or '—')}</td>"
                f"<td>{_escape_html(item.get('link') or '—')}</td>"
                "</tr>"
            )
    return "\n".join(rows)


def _render_warnings_banner(artifact: BakedArtifact) -> str:
    warnings = artifact.warnings or []
    if not warnings:
        return ""
    list_items = []
    for w in warnings:
        ref = f"[{_escape_html(w.get('item') or '')}] " if w.get("item") else ""
        list_items.append(f"<li>{ref}{_escape_html(w.get('message', ''))}</li>")
    count = len(warnings)
    return (
        f'<div class="warnings-banner visible" id="warnings-banner">'
        f"<details open><summary>{count} warning{'s' if count != 1 else ''}</summary>"
        f'<ul class="warn-list">{"".join(list_items)}</ul></details></div>'
    )


def _escape_html(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_page(artifact: BakedArtifact) -> str:
    """Render the complete self-contained HTML page."""
    data_json = json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False)
    svg_markup = _render_static_svg(artifact)
    ring_key = _render_ring_key(artifact)
    legend = _render_legend()
    a11y_rows = _render_a11y_table(artifact)
    warnings_banner = _render_warnings_banner(artifact)
    person = _escape_html(artifact.person or "circles")
    stamp = _escape_html(artifact.generated_at or "")
    summary = _escape_html(_summarize(artifact))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{person} — circles</title>
<style>
html,body{{height:100%;overflow:hidden;margin:0}}
body{{display:flex;flex-direction:column;height:100vh;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:14px;color:#222;background:#fff}}
*{{box-sizing:border-box}}
header{{display:flex;justify-content:space-between;align-items:baseline;padding:8px 16px;border-bottom:1px solid #ddd;flex-shrink:0}}
header h1{{font-size:17px;margin:0}}
.stamp{{font-size:11px;color:#777}}
main{{flex:1;display:flex;min-height:0}}
.chart-pane{{flex:1;display:flex;align-items:center;justify-content:center;min-width:0}}
#sunburst-svg{{max-width:100%;max-height:100%;width:auto;height:auto}}
.sidebar{{width:230px;flex-shrink:0;overflow:hidden;border-left:1px solid #ddd;padding:10px 14px;display:flex;flex-direction:column;gap:12px;font-size:13px}}
.sidebar h2{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#888;margin:0 0 4px}}
.ring-key{{list-style:none;margin:0;padding:0}}
.ring-key li{{padding:1px 0}}
.legend-item{{display:flex;align-items:center;gap:7px;margin:2px 0}}
.legend-swatch{{width:14px;height:14px;border-radius:3px;border:1px solid rgba(0,0,0,.15);flex-shrink:0}}
.summary{{font-size:12px;line-height:1.5;color:#444}}
.warnings-banner{{background:#fff8e1;border-bottom:1px solid #e6c852;padding:4px 16px;font-size:12px;flex-shrink:0}}
.warnings-banner summary{{cursor:pointer;font-weight:600;color:#7a5c00}}
.warn-list{{margin:4px 0 0 18px;padding:0}}
.warn-list li{{margin:1px 0}}
.detail-strip{{border-top:1px solid #ddd;padding:7px 16px;font-size:13px;color:#555;flex-shrink:0;min-height:32px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.a11y-section{{flex-shrink:0;border-top:1px solid #eee}}
.a11y-section summary{{cursor:pointer;padding:6px 16px;font-size:12px;color:#666;user-select:none}}
.a11y-section .table-wrap{{max-height:150px;overflow:auto;border-top:1px solid #eee}}
table{{border-collapse:collapse;width:100%;font-size:11px}}
th,td{{text-align:left;padding:3px 10px;border-bottom:1px solid #eee;white-space:nowrap}}
th{{background:#fafafa;position:sticky;top:0}}
.boot-failure{{padding:40px;text-align:center}}
.boot-failure h2{{color:#b22222;margin:0 0 12px}}
.boot-failure p{{color:#555}}
.cell{{outline:none}}
.cell:focus{{stroke:#111;stroke-width:3}}
.cell:hover{{stroke:#111;stroke-width:2.5}}
</style>
</head>
<body>
<script id="circles-data" type="application/json">{data_json}</script>
<header>
<h1>{person}</h1>
<span class="stamp" id="stamp">built {stamp}</span>
</header>
{warnings_banner}
<main>
<div class="chart-pane">
<svg id="sunburst-svg" viewBox="0 0 400 400" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="circles chart for {person}">
{svg_markup}
</svg>
</div>
<aside class="sidebar">
<section>
<h2>Rings</h2>
<ul class="ring-key" id="ring-key">{ring_key}</ul>
</section>
<section>
<h2>Legend</h2>
{legend}
</section>
<section>
<h2>Summary</h2>
<div class="summary" id="summary-text">{summary}</div>
</section>
</aside>
</main>
<div class="detail-strip" id="detail-strip" aria-live="polite">Hover or focus a cell to see its detail</div>
<details class="a11y-section">
<summary>Accessibility table — every item, ring-ordered</summary>
<div class="table-wrap">
<table>
<thead><tr><th>Ring</th><th>Item</th><th>Status</th><th>Guardrail</th><th>Note</th><th>Link</th></tr></thead>
<tbody id="a11y-body">{a11y_rows}</tbody>
</table>
</div>
</details>
<script>
(function () {{
'use strict';
var DATA;
try {{
  var el = document.getElementById('circles-data');
  if (!el || !el.textContent) throw new Error('payload absent');
  DATA = JSON.parse(el.textContent);
  if (!DATA || typeof DATA !== 'object') throw new Error('payload is not an object');
  if (DATA.version !== 1) throw new Error('unrecognized artifact version: ' + DATA.version);
  if (!Array.isArray(DATA.rings)) throw new Error('rings key missing or not an array');
  if (DATA.rings.length === 0) throw new Error('rings is empty');
}} catch (e) {{
  var app = document.querySelector('main');
  if (app) {{
    app.innerHTML = '<div class="boot-failure"><h2>circles — boot failure</h2>' +
      '<p>' + String(e.message || e) + '</p>' +
      '<p>The inlined artifact is absent, malformed, or from a version this page does not understand. No cells are drawn.</p></div>';
  }}
  return;
}}

var RINGS = DATA.rings;
var STATUS_WORD = {{green:'ok', yellow:'attention', red:'act', grey:'unmonitored'}};

var strip = document.getElementById('detail-strip');
var IDLE = 'Hover or focus a cell to see its detail';

function findItem(ringId, itemId) {{
  for (var i = 0; i < RINGS.length; i++) {{
    var items = RINGS[i].items || [];
    for (var j = 0; j < items.length; j++) {{
      if (RINGS[i].id === ringId && items[j].id === itemId) return items[j];
    }}
  }}
  return null;
}}

var svg = document.getElementById('sunburst-svg');
if (svg) {{
  svg.addEventListener('mouseover', function (ev) {{
    var cell = ev.target.closest ? ev.target.closest('.cell') : null;
    if (cell && strip) showDetail(cell);
  }});
  svg.addEventListener('mouseout', function (ev) {{
    var cell = ev.target.closest ? ev.target.closest('.cell') : null;
    if (cell && strip) strip.textContent = IDLE;
  }});
  svg.addEventListener('focusin', function (ev) {{
    var cell = ev.target.closest ? ev.target.closest('.cell') : null;
    if (cell && strip) showDetail(cell);
  }});
  svg.addEventListener('focusout', function (ev) {{
    var cell = ev.target.closest ? ev.target.closest('.cell') : null;
    if (cell && strip) strip.textContent = IDLE;
  }});
  svg.addEventListener('click', function (ev) {{
    var cell = ev.target.closest ? ev.target.closest('.cell') : null;
    if (!cell) return;
    var item = findItem(cell.getAttribute('data-ring'), cell.getAttribute('data-item'));
    if (item && item.link) window.open(item.link, '_blank', 'noopener');
  }});
}}

function showDetail(cell) {{
  var item = findItem(cell.getAttribute('data-ring'), cell.getAttribute('data-item'));
  if (item && strip) {{
    strip.textContent = item.detail_line || (item.label + ' — ' + (STATUS_WORD[item.status] || '?'));
  }}
}}
}})();
</script>
</body>
</html>
"""