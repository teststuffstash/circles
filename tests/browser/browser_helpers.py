"""given / when / then for evidence at the PAGE's boundary — the browser tier (circles#103 step 2).

The process contract is the same as tests/evidence_helpers.py's (allure-behavior-snippets
CONVENTIONS.md: § Allure taxonomy, § Evidence row identity, § Prime rule of reporting, § The
helper razor); this module is that API's browser half. The page's boundary is headless Chromium
loading the BAKED page over real HTTP (CIR-PROC-BROWSER-EVIDENCE): what it shows the world is
computed style, DOM geometry, the accessibility tree, navigation and PDF bytes — never a source
grep, never a screenshot. A labelled browser case therefore reads:

    @rule("CIR-RENDER-<NAME>")
    def test_<row>(self, page, served, pages_dir):
        "CIR-RENDER-<NAME>#<row-id> — …"
        given_loaded(page, served, pages_dir, "index.html", "<how this variant was baked>")
        with when("pointer leaves the chart to (2, 2)"):
            page.mouse.move(2, 2)
            strip = observe(page, "() => …", "detail strip text")
        then("detail strip", strip, "Friends", op="not contains")

API (the whole of it):

- ``given_page(pages_dir, name, variant)`` — the given step: the baked page ``name`` (world
  alex, ``variant`` names how it was baked), the world seed and the page's inlined artifact
  attached; returns that artifact (a dict).
- ``given_loaded(page, served, pages_dir, name, variant)`` — ``given_page`` plus the page already
  loaded at the reference viewport (the load is arrange: a failed load dies in the given step).
- ``when(action)`` — the ONE when step, as ``with when("…"):`` around the inline Playwright call
  (the action stays in the test body — the helper razor).
- ``observe(page, js, name, arg=None)`` — what the browser reports (``page.evaluate``), attached
  as JSON under the current step.
- ``then(claim, actual, expected, op="=")`` — one then step. It IS
  ``evidence_helpers.verdict`` (one verdict implementation): ``=``, ``!=``, ``contains``,
  ``not contains`` and the measured-claim orderings ``>=``, ``<=``, ``>``, ``<``.
- ``ax_names(page)`` — data-item → the cell's COMPUTED accessible name (CDP accessibility tree).
- ``GEOMETRY`` — a ``page.evaluate`` script: every cell's polar geometry (radius range, start
  angle and span clockwise from noon, label corners) from its drawn path, in SVG user space.
- ``COVERAGE`` — a ``page.evaluate`` script (arg: a CSS selector of chart paths): the degrees of
  the circle each path's FILL covers at its mid radius, and its largest uncovered run — what
  ``GEOMETRY``'s sampled span cannot resolve for a full 360° band (a notch, a missing half).
- ``pdf_colours(pdf, palette)`` — the palette hexes actually painted on a printed PDF's page 1.
- ``REFERENCE_VIEWPORT`` (CIR-RENDER-REFERENCE-VIEWPORT, as a Playwright viewport dict) and
  ``FURNITURE`` (the page furniture CIR-RENDER-ONE-SCREEN names, as selectors).
"""

from __future__ import annotations

import io
import json
import math
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import allure
from playwright.sync_api import Page
from pypdf import PdfReader

from evidence_helpers import WORLD, verdict, world_seed

# CIR-RENDER-REFERENCE-VIEWPORT#viewport-gate-is-fixed: 1280 × 800 CSS px (⚖-R37) — the same
# numbers as tests/browser/conftest.py's tuple, in the shape Playwright's new_context takes.
REFERENCE_VIEWPORT = {"width": 1280, "height": 800}
# The page furniture CIR-RENDER-ONE-SCREEN#one-screen-reference names: "chart, ring key, legend,
# stamp and detail strip fully visible" (ids from bake/render.py).
FURNITURE = ("#chart-area", "#ring-key", "#legend", "#stamp", "#detail-strip")


# ---------------------------------------------------------------------------- given

def _inlined_artifact(html: str) -> dict:
    """The artifact the page carries (`<script id="artifact-data">`) — what the page was given."""
    m = re.search(r'<script id="artifact-data" type="application/json">(.*?)</script>', html, re.S)
    assert m is not None, "page carries no inlined artifact — arrange failure"
    return json.loads(m.group(1))


def given_page(pages_dir: Path, name: str, variant: str) -> dict:
    """Given: the baked page ``name`` (world alex, ``variant``) — the world seed and the page's
    inlined artifact attached. Returns that artifact (wire format: a dict)."""
    with allure.step(f"Given: page {name} (world {WORLD}: {variant})"):
        allure.attach(world_seed(), name=f"world: {WORLD} — seed (sha256 + circles.yaml)",
                      attachment_type=allure.attachment_type.TEXT)
        artifact = _inlined_artifact((pages_dir / name).read_text(encoding="utf-8"))
        allure.attach(json.dumps(artifact, indent=2, ensure_ascii=False),
                      name=f"{name} — inlined artifact (world: {WORLD}, {variant})",
                      attachment_type=allure.attachment_type.JSON)
    return artifact


def given_loaded(page: Page, served: str, pages_dir: Path, name: str, variant: str) -> dict:
    """Given: ``name`` as given_page, already loaded in the browser (the load is arrange here —
    asserted internally, so a failed load dies in the given step)."""
    artifact = given_page(pages_dir, name, variant)
    with allure.step(f"Given: browser has {name} open at "
                     f"{REFERENCE_VIEWPORT['width']}×{REFERENCE_VIEWPORT['height']}"):
        response = page.goto(f"{served}/{name}")
        assert response is not None and response.ok, f"loading {name}: {response}"
    return artifact


# ---------------------------------------------------------------------------- when / observe

def when(action: str):
    """When: the ONE browser action under test — used as ``with when("…"):`` around the inline
    Playwright call, so the action stays in the test body (CONVENTIONS § The helper razor)."""
    return allure.step(f"When: {action}")


def observe(page: Page, js: str, name: str, arg: Any = None) -> Any:
    """What the browser reports (``page.evaluate``), attached as JSON under the current step."""
    result = page.evaluate(js, arg)
    allure.attach(json.dumps(result, indent=2, ensure_ascii=False), name=name,
                  attachment_type=allure.attachment_type.JSON)
    return result


# ---------------------------------------------------------------------------- then

# One verdict implementation for both tiers: the browser's measured claims (>=, <, !=, …) are
# evidence_helpers.verdict's own ops.
then = verdict


# ---------------------------------------------------------------------------- measurements

# Polar geometry of every cell, in the SVG's user space (centre = the viewBox centre): each
# path is sampled along its length; radius = distance from the centre, angle = degrees
# clockwise from 12 o'clock. The angular span is the circle minus the largest gap between
# sampled angles, so a cell starting exactly at noon is not split in two.
GEOMETRY = """() => {
  const svg = document.querySelector('#chart-area svg');
  const vb = svg.viewBox.baseVal, cx = vb.x + vb.width / 2, cy = vb.y + vb.height / 2;
  const polar = (x, y) => ({r: Math.hypot(x - cx, y - cy),
                            a: ((Math.atan2(x - cx, cy - y) * 180 / Math.PI) + 360) % 360});
  return Array.from(document.querySelectorAll('.cell')).map(c => {
    const p = c.querySelector('path'), len = p.getTotalLength(), n = 720;
    const pts = [];
    for (let i = 0; i <= n; i++) { const q = p.getPointAtLength(len * i / n); pts.push(polar(q.x, q.y)); }
    const angles = pts.map(q => q.a).sort((x, y) => x - y);
    let gap = 360 - angles[angles.length - 1] + angles[0], start = angles[0];
    for (let i = 1; i < angles.length; i++) {
      if (angles[i] - angles[i - 1] > gap) { gap = angles[i] - angles[i - 1]; start = angles[i]; }
    }
    const span = 360 - gap;
    // label corners, mapped from the text's own box through its transform into user space
    const t = c.querySelector('text'), bb = t.getBBox(), m = t.transform.baseVal.consolidate();
    const corners = [[bb.x, bb.y], [bb.x + bb.width, bb.y], [bb.x, bb.y + bb.height],
                     [bb.x + bb.width, bb.y + bb.height]].map(([x, y]) => {
      const pt = m ? new DOMPoint(x, y).matrixTransform(m.matrix) : new DOMPoint(x, y);
      return polar(pt.x, pt.y);
    });
    return {item: c.getAttribute('data-item'),
            rMin: Math.min(...pts.map(q => q.r)), rMax: Math.max(...pts.map(q => q.r)),
            start: start, span: span, labelCorners: corners};
  });
}"""


# Angular coverage of chart paths, measured by hit-testing the painted fill: for each path matched
# by the selector (arg), points on the circle at the path's mid radius are tested every 0.1°
# with isPointInFill. covered = degrees inside the fill; maxGap = the longest run of degrees
# outside it (0 for a band closed all the way round). item = the enclosing cell's data-item, or
# null for a path that is not a cell (an empty ring's band).
COVERAGE = """(sel) => {
  const svg = document.querySelector('#chart-area svg');
  const vb = svg.viewBox.baseVal, cx = vb.x + vb.width / 2, cy = vb.y + vb.height / 2;
  return Array.from(svg.querySelectorAll(sel)).map(p => {
    const len = p.getTotalLength(); let rMin = Infinity, rMax = 0;
    for (let i = 0; i <= 120; i++) {
      const q = p.getPointAtLength(len * i / 120), r = Math.hypot(q.x - cx, q.y - cy);
      rMin = Math.min(rMin, r); rMax = Math.max(rMax, r);
    }
    const rMid = (rMin + rMax) / 2, n = 3600;
    let inside = 0, run = 0, maxGap = 0;
    const hit = [];
    for (let i = 0; i < n; i++) {
      const a = i * 2 * Math.PI / n;
      hit.push(p.isPointInFill(new DOMPoint(cx + rMid * Math.sin(a), cy - rMid * Math.cos(a))));
    }
    // longest run of misses, wrapping round noon
    for (let i = 0; i < 2 * n; i++) {
      if (hit[i % n]) { run = 0; } else { run++; maxGap = Math.max(maxGap, Math.min(run, n)); }
    }
    inside = hit.filter(Boolean).length;
    const cell = p.closest('[data-item]');
    return {item: cell ? cell.getAttribute('data-item') : null, rMin: rMin, rMax: rMax,
            covered: inside * 360 / n, maxGap: maxGap * 360 / n};
  });
}"""


def ax_names(page: Page) -> dict[str, str]:
    """data-item → the cell's COMPUTED accessible name, from Chromium's accessibility tree (CDP
    Accessibility.getFullAXTree) — what a screen reader is handed, not the markup."""
    cdp = page.context.new_cdp_session(page)
    try:
        cdp.send("DOM.getDocument", {"depth": -1})
        names: dict[str, str] = {}
        for node in cdp.send("Accessibility.getFullAXTree")["nodes"]:
            if node.get("ignored") or "backendDOMNodeId" not in node:
                continue
            role = node.get("role", {}).get("value")
            if role not in ("button", "link"):
                continue
            desc = cdp.send("DOM.describeNode", {"backendNodeId": node["backendDOMNodeId"]})["node"]
            attrs = dict(zip(desc.get("attributes", [])[::2], desc.get("attributes", [])[1::2]))
            if "data-item" in attrs:
                names[attrs["data-item"]] = node.get("name", {}).get("value", "")
        return names
    finally:
        cdp.detach()


def pdf_colours(pdf: bytes, palette: dict[str, str] | Iterable[str]) -> list[str]:
    """The ``palette`` hexes (``#RRGGBB``; a dict's values) painted in a PDF: every
    non-stroking/stroking RGB colour operator in the first page's content stream, matched to the
    palette within 0.002 per channel. Returned in palette order."""
    hexes = list(palette.values()) if isinstance(palette, dict) else list(palette)
    data = PdfReader(io.BytesIO(pdf)).pages[0].get_contents().get_data().decode("latin-1")
    triples = {tuple(float(v) for v in m) for m in re.findall(r"([\d.]+) ([\d.]+) ([\d.]+) (?:rg|RG)\b", data)}
    found = []
    for hexa in hexes:
        want = tuple(int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
        if any(all(math.isclose(a, b, abs_tol=0.002) for a, b in zip(t, want)) for t in triples):
            found.append(hexa)
    return found
