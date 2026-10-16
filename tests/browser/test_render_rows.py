# Browser evidence for the render rows that tests/test_render.py used to claim in-process —
# CIR-PROC-BROWSER-EVIDENCE#render-requirements-state-their-path (specs/process/testing.md):
# every CIR-RENDER-* row is evidenced by headless Chromium measuring the BAKED page served over
# real HTTP — computed style, DOM geometry, the accessibility tree, navigation, PDF bytes —
# never a source grep (#no-render-claim-from-source-alone) and never a screenshot
# (#screenshots-are-not-the-assertion).
#
# World: alex. Every page variant is the fixture person baked by scripts/test-browser.sh:
#   index.html                  the fixture as the image build bakes it (adapters not evaluated)
#   index-no-threshold.html     the same artifact at generated_at 2026-08-03T02:00:00Z
#   index-evaluated.html        the fixture baked with --evaluate (the nightly bake): every
#                               adapter resolves, no warnings
#   index-only-green.html       the fixture's `manual: green` items only
#   index-click-<row_id>.html   one row of fixtures/click-destinations.yaml spliced into a
#                               one-ring config for Alex
#
# Each labelled case reads given (the page variant, world seed + the page's inlined artifact
# attached, loaded in the browser where the action is not the load itself) → ONE when (the
# browser action: load / Tab / Enter / hover / click / print) with what the browser reported
# attached under it → one then per claim (CONVENTIONS § Prime rule of reporting). Expected
# values come from the spec rows and the fixture comments (fixtures/alex/circles.yaml), cited
# beside each claim — never from running the page.
#
# The given/when/then helpers below are this module's own (tests/evidence_helpers.py is the
# CLI boundary's); `verdict` is reused from there.

from __future__ import annotations

import io
import json
import math
import operator
import re
import shutil
from pathlib import Path
from typing import Any, Iterator

import allure
import pytest
import yaml
from playwright.sync_api import Browser, Page
from pypdf import PdfReader

from evidence_helpers import _shown, verdict, world_seed
from rules import rule

pytestmark = pytest.mark.browser

REPO = Path(__file__).resolve().parents[2]
WORLD = "alex"
REFERENCE_VIEWPORT = {"width": 1280, "height": 800}  # CIR-RENDER-REFERENCE-VIEWPORT (⚖-R37)

# CIR-RENDER-PALETTE: the four pinned fills (specs/render/colors.md, palette table).
PALETTE = {"green": "#00916A", "yellow": "#F2B300", "red": "#B22222", "grey": "#9E9E9E"}
# The status words (same table; CIR-RENDER-LEGEND#legend-words).
WORDS = {"green": "ok", "yellow": "attention", "red": "act", "grey": "unmonitored"}
LEGEND_WORDS = ["ok", "attention", "act", "unmonitored"]

# The fixture person, from fixtures/alex/circles.yaml: rings inside-out, items in config order
# (CIR-DATA-SCHEMA-TOPLEVEL / -RING: array order is geometry order).
RING_LABELS = ["① Self", "② Partner", "③ Children", "④ Wider life"]
CELL_ORDER = ["self/sleep", "self/labs", "self/exercise", "partner/date-night",
              "children/nova", "children/kit", "wider/friends", "wider/plants"]
ITEM_LABELS = {"self/sleep": "Sleep", "self/labs": "Quarterly labs", "self/exercise": "Exercise",
               "partner/date-night": "Date night", "children/nova": "◀ Nova",
               "children/kit": "Kit ▶", "wider/friends": "Friends", "wider/plants": "Plants"}
RING_OF = {ref: RING_LABELS[["self", "partner", "children", "wider"].index(ref.split("/")[0])]
           for ref in CELL_ORDER}
# Statuses as the image build bakes the fixture (adapters not evaluated — fixture comments:
# freshness/command items are ⚪ not-evaluated, exercise ⚪ by-choice, the manual ones as set).
UNEVALUATED_STATUS = {"self/sleep": "grey", "self/labs": "grey", "self/exercise": "grey",
                      "partner/date-night": "yellow", "children/nova": "green",
                      "children/kit": "green", "wider/friends": "red", "wider/plants": "grey"}

CLICK_TABLE = REPO / "fixtures" / "click-destinations.yaml"
STAMP = "2026-08-03T02:00:00Z"  # CIR-RENDER-GENERATED-AT#stamp-verbatim's input, verbatim
BUDGET_BYTES = 250_000          # CIR-RENDER-ASSET-BUDGET: "250 KB total, uncompressed"


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

_CMP = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt,
        "!=": operator.ne}


def then(claim: str, actual: Any, expected: Any, *, op: str = "=") -> None:
    """evidence_helpers.verdict, plus the ordering ops a measured geometry claim needs."""
    if op not in _CMP:
        verdict(claim, actual, expected, op=op)
        return
    with allure.step(f"Then: {claim} {op} {_shown(expected)}"):
        assert _CMP[op](actual, expected), (
            f"{claim}: expected {op} {_shown(expected)}, actual {_shown(actual)}")


# ---------------------------------------------------------------------------- measurements

_CELLS = """() => Array.from(document.querySelectorAll('.cell')).map(c => {
  const p = c.querySelector('path'), t = c.querySelector('text');
  const ps = getComputedStyle(p), r = t.getBoundingClientRect(), b = c.getBoundingClientRect();
  return {item: c.getAttribute('data-item'), status: c.getAttribute('data-status'),
          tag: c.tagName.toLowerCase(), href: c.getAttribute('href'),
          fill: ps.fill, stroke: ps.stroke, strokeWidth: ps.strokeWidth,
          dash: ps.strokeDasharray, opacity: ps.opacity, cursor: ps.cursor,
          labelText: t.textContent, labelFill: getComputedStyle(t).fill,
          at: {x: r.left + r.width / 2, y: r.top + r.height / 2},
          box: {w: b.width, h: b.height}};
})"""

# Polar geometry of every cell, in the SVG's user space (centre = the viewBox centre): each
# path is sampled along its length; radius = distance from the centre, angle = degrees
# clockwise from 12 o'clock. The angular span is the circle minus the largest gap between
# sampled angles, so a cell starting exactly at noon is not split in two.
_GEOMETRY = """() => {
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

_A11Y_TABLE = """() => {
  const head = Array.from(document.querySelectorAll('#a11y-table thead th')).map(th => th.textContent.trim());
  const rows = Array.from(document.querySelectorAll('#a11y-table tbody tr')).map(
    tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim()));
  return {head: head, rows: rows};
}"""

_STRIP = "() => document.getElementById('detail-content').textContent.trim()"

_ACTIVE = """() => { const a = document.activeElement;
  return {item: a ? a.getAttribute('data-item') : null, tag: a ? a.tagName.toLowerCase() : null,
          inChart: !!(a && a.closest('#chart-area svg'))}; }"""


def _ax_names(page: Page) -> dict[str, str]:
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


def _rgb(hex_colour: str) -> str:
    """A pinned hex as Chromium's computed-style string."""
    h = hex_colour.lstrip("#")
    return "rgb({}, {}, {})".format(*(int(h[i:i + 2], 16) for i in (0, 2, 4)))


def _luminance(rgb: str) -> float:
    """WCAG 2.x relative luminance of a computed ``rgb(r, g, b)`` string."""
    chans = [int(v) / 255 for v in re.findall(r"\d+", rgb)[:3]]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in chans]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _click_rows() -> dict[str, dict]:
    return {r["row_id"]: r for r in yaml.safe_load(CLICK_TABLE.read_text(encoding="utf-8"))["rows"]}


@pytest.fixture
def nojs_page(browser: Browser) -> Iterator[Page]:
    """A fresh page at the reference viewport with JavaScript DISABLED (CIR-RENDER-NO-JS)."""
    context = browser.new_context(viewport=REFERENCE_VIEWPORT, java_script_enabled=False)
    try:
        yield context.new_page()
    finally:
        context.close()


# ===========================================================================
# CIR-RENDER-KEYBOARD — the whole page without a mouse
# ===========================================================================

class TestKeyboard:
    """CIR-RENDER-KEYBOARD (specs/render/interactions.md)."""

    @rule("CIR-RENDER-KEYBOARD")
    def test_keyboard_tab_order(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-tab-order — tabbing from page start: cells receive focus
        inside-out and clockwise.

        Expected: ring by ring inside-out (self, partner, children, wider), within a ring in
        config order — which CIR-RENDER-SIBLING-ORDER draws clockwise from 12 o'clock."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        with when("Tab ×8 from page start"):
            focused = []
            for _ in range(8):
                page.keyboard.press("Tab")
                focused.append(page.evaluate(_ACTIVE)["item"])
            allure.attach(json.dumps(focused, indent=2, ensure_ascii=False),
                          name="focused data-item after each Tab", attachment_type=allure.attachment_type.JSON)
        then("focus sequence", focused, CELL_ORDER)

    @rule("CIR-RENDER-KEYBOARD")
    def test_keyboard_no_trap(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-no-trap — tabbing past the last cell: focus leaves the
        chart normally.

        The fixture draws 8 cells, so the 9th Tab from page start must land outside the chart."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        with when("Tab ×9 from page start (8 cells + 1)"):
            for _ in range(9):
                page.keyboard.press("Tab")
            active = observe(page, _ACTIVE, "focused element after Tab ×9")
        then("focused element is inside the chart", active["inChart"], False)
        then("focused element is a cell (data-item)", active["item"], None)

    @rule("CIR-RENDER-KEYBOARD")
    def test_keyboard_focus_shows_detail(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-focus-shows-detail — focus on a cell: the detail strip
        shows that cell's detail line.

        The first Tab focuses self/sleep (keyboard-tab-order); the strip's format is
        `<label> — <detail_line>` with the detail line verbatim from the artifact
        (CIR-RENDER-HOVER) — the given's inlined artifact carries it."""
        artifact = given_loaded(page, served, pages_dir, "index.html", "unmodified")
        sleep = artifact["rings"][0]["items"][0]
        with when("Tab ×1 (focus self/sleep)"):
            page.keyboard.press("Tab")
            strip = observe(page, _STRIP, "detail strip text")
        then("detail strip", strip, f"{sleep['label']} — {sleep['detail_line']}")

    @rule("CIR-RENDER-KEYBOARD")
    def test_keyboard_enter_activates(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-enter-activates — focus + Enter on a linked cell: the
        click behavior fires.

        The click-root-relative row (fixtures/click-destinations.yaml): self/sleep with
        `link: /details/self-sleep.html` navigates in place — so Enter must too."""
        name = "index-click-click-root-relative.html"
        given_loaded(page, served, pages_dir, name, "click row click-root-relative")
        with allure.step("Given: self/sleep focused by Tab ×1"):
            page.keyboard.press("Tab")
            assert page.evaluate(_ACTIVE)["item"] == "self/sleep"
        with when("Enter on the focused self/sleep"):
            page.keyboard.press("Enter")
            page.wait_for_url("**/details/self-sleep.html", timeout=5000)
            allure.attach(page.url.replace(served, ""), name="page URL after Enter (origin stripped)",
                          attachment_type=allure.attachment_type.TEXT)
        then("page URL path", page.url.replace(served, ""), "/details/self-sleep.html")

    @rule("CIR-RENDER-KEYBOARD")
    def test_keyboard_focus_visible(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-focus-visible — any focused cell: a focus indicator
        distinguishable from the status fill.

        Measured on the focused cell (self/sleep, first Tab) against its own fill and against an
        unfocused sibling (self/labs, same ring and status): the outline colour differs from the
        fill, it is wider than the resting outline, and it is dashed."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        with when("Tab ×1 (keyboard focus on self/sleep)"):
            page.keyboard.press("Tab")
            cells = {c["item"]: c for c in observe(page, _CELLS, "cells: computed path style")}
        focused, resting = cells["self/sleep"], cells["self/labs"]
        then("focused outline colour differs from its fill", focused["stroke"] != focused["fill"], True)
        then("focused outline width (px)", float(focused["strokeWidth"].rstrip("px")),
             float(resting["strokeWidth"].rstrip("px")), op=">")
        then("focused outline dash pattern", focused["dash"], "none", op="!=")

    @rule("CIR-RENDER-KEYBOARD")
    def test_keyboard_accessible_name(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-accessible-name — a cell's computed name:
        `<label>, <status word>, ring <ring label>`.

        Expected per cell from the fixture labels, the image-build statuses and the palette
        words, e.g. `Friends, act, ring ④ Wider life`. A ⚪ cell may append its grey reason
        (CIR-RENDER-GREY-VISIBLE), so the claim is on the name's leading three parts."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        with when("Chromium computes the accessibility tree of the loaded page"):
            names = _ax_names(page)
            allure.attach(json.dumps(names, indent=2, ensure_ascii=False),
                          name="computed accessible name per cell", attachment_type=allure.attachment_type.JSON)
        expected = {ref: f"{ITEM_LABELS[ref]}, {WORDS[UNEVALUATED_STATUS[ref]]}, ring {RING_OF[ref]}"
                    for ref in CELL_ORDER}
        leading = {ref: ", ".join(names.get(ref, "").split(", ")[:3]) for ref in CELL_ORDER}
        then("wider/friends accessible name", names.get("wider/friends"), "Friends, act, ring ④ Wider life")
        then("every cell's name, leading <label>, <word>, ring <ring>", leading, expected)


# ===========================================================================
# CIR-RENDER-HOVER — the detail line
# ===========================================================================

class TestHover:
    """CIR-RENDER-HOVER (specs/render/interactions.md)."""

    @rule("CIR-RENDER-HOVER")
    def test_hover_full_line(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-HOVER#hover-full-line — `self/sleep` (guardrail + last-data date):
        `Sleep — Lights out by 23:00 on weeknights · ok · last data 2026-08-01`.

        The evaluated bake resolves sleep's freshness adapter at the reference date (fixture
        comment: 🟢, age 2), so the row's input exists exactly; the expected string is the row's."""
        given_loaded(page, served, pages_dir, "index-evaluated.html", "baked with --evaluate")
        at = {c["item"]: c["at"] for c in page.evaluate(_CELLS)}["self/sleep"]
        with when(f"pointer hovers self/sleep at ({at['x']:.0f}, {at['y']:.0f})"):
            page.mouse.move(at["x"], at["y"])
            strip = observe(page, _STRIP, "detail strip text")
        then("detail strip", strip, "Sleep — Lights out by 23:00 on weeknights · ok · last data 2026-08-01")

    @rule("CIR-RENDER-HOVER")
    def test_hover_grey_unmonitored(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-HOVER#hover-grey-unmonitored — item with no adapter: `Exercise — unmonitored`.

        self/exercise is the fixture's adapter-less item (fixture comment: ⚪ unmonitored)."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        at = {c["item"]: c["at"] for c in page.evaluate(_CELLS)}["self/exercise"]
        with when(f"pointer hovers self/exercise at ({at['x']:.0f}, {at['y']:.0f})"):
            page.mouse.move(at["x"], at["y"])
            strip = observe(page, _STRIP, "detail strip text")
        then("detail strip", strip, "Exercise — unmonitored")

    @rule("CIR-RENDER-HOVER")
    def test_hover_leave_resets(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-HOVER#hover-leave-resets — pointer leaves the chart: the strip returns to
        idle text, never stale content.

        Idle text is what the strip shows at load, before any pointer (measured in the given);
        the pointer then rests on wider/friends and leaves to the page's top-left corner."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        with allure.step("Given: idle strip at load, then pointer on wider/friends"):
            idle = page.evaluate(_STRIP)
            allure.attach(idle, name="detail strip text at load (idle)", attachment_type=allure.attachment_type.TEXT)
            at = {c["item"]: c["at"] for c in page.evaluate(_CELLS)}["wider/friends"]
            page.mouse.move(at["x"], at["y"])
            assert page.evaluate(_STRIP).startswith("Friends"), "hover did not reach wider/friends"
        with when("pointer leaves the chart to (2, 2)"):
            page.mouse.move(2, 2)
            strip = observe(page, _STRIP, "detail strip text")
        then("detail strip", strip, idle)
        then("detail strip", strip, "Friends", op="not contains")


# ===========================================================================
# CIR-RENDER-CLICK — where a cell leads
# ===========================================================================

class TestClick:
    """CIR-RENDER-CLICK (specs/render/interactions.md) — one case per P0 row of
    fixtures/click-destinations.yaml (the P2 rows have no behaviour at P0: #35)."""

    @rule("CIR-RENDER-CLICK")
    @pytest.mark.parametrize("row_id", [
        pytest.param("click-follows-link", id="CIR-RENDER-CLICK#click-follows-link"),
        pytest.param("click-root-relative", id="CIR-RENDER-CLICK#click-root-relative"),
        pytest.param("click-no-destination", id="CIR-RENDER-CLICK#click-no-destination"),
    ])
    def test_click_destination(self, page: Page, served: str, pages_dir: Path, row_id: str) -> None:
        """CIR-RENDER-CLICK — the cell's activation does what the row declares: a new tab to
        the https link, in-place navigation for a root-relative one, nothing (and a default
        cursor) for a cell with no destination.

        Expected per row from fixtures/click-destinations.yaml `expected`: new tabs opened =
        [href] when target is _blank, else []; page path after = href when it navigates in
        place, else unchanged; cursor = pointer when clickable, else default. example.test
        resolves nowhere, so the new tab is answered by a route stub — its URL is the claim."""
        row = _click_rows()[row_id]
        exp = row["expected"]
        ref = f"self/{row['item']['id']}"
        name = f"index-click-{row_id}.html"
        given_loaded(page, served, pages_dir, name, f"click row {row_id}")
        page.context.route("https://example.test/**", lambda route: route.fulfill(body="stub"))
        popups: list[str] = []
        page.context.on("page", lambda p: popups.append(p))
        cell = {c["item"]: c for c in page.evaluate(_CELLS)}[ref]
        with when(f"click {ref} at ({cell['at']['x']:.0f}, {cell['at']['y']:.0f})"):
            page.mouse.click(cell["at"]["x"], cell["at"]["y"])
            page.wait_for_timeout(750)
            for p in popups:
                p.wait_for_load_state()
            seen = {"new_tabs": [p.url for p in popups], "path": page.url.replace(served, "")}
            allure.attach(json.dumps(seen, indent=2), name=f"navigation after the click ({row_id})",
                          attachment_type=allure.attachment_type.JSON)
        in_place = exp["clickable"] and exp["target"] is None
        then("new tabs opened", seen["new_tabs"], [exp["href"]] if exp["target"] == "_blank" else [])
        then("page URL path", seen["path"], exp["href"] if in_place else f"/{name}")
        then(f"{ref} cursor", cell["cursor"], "pointer" if exp["clickable"] else "default")


# ===========================================================================
# CIR-RENDER-PALETTE — the four fills
# ===========================================================================

class TestPalette:
    """CIR-RENDER-PALETTE (specs/render/colors.md)."""

    @rule("CIR-RENDER-PALETTE")
    def test_palette_exact_fills(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-PALETTE#palette-exact-fills — shipped CSS: the four fills are exactly the
        pinned hexes.

        Measured as computed `fill` per drawn cell, grouped by status, and the legend swatches'
        computed background in legend order — each the palette table's hex as rgb()."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            cells = observe(page, _CELLS, "cells: computed path fill")
            swatches = observe(page, "() => Array.from(document.querySelectorAll('.legend-swatch'))"
                                     ".map(s => getComputedStyle(s).backgroundColor)",
                               "legend swatches: computed background")
        fills: dict[str, list[str]] = {}
        for c in cells:
            fills.setdefault(c["status"], [])
            if c["fill"] not in fills[c["status"]]:
                fills[c["status"]].append(c["fill"])
        then("cell fills by status", fills, {s: [_rgb(h)] for s, h in PALETTE.items()})
        then("legend swatch fills", swatches, [_rgb(PALETTE[s]) for s in ("green", "yellow", "red", "grey")])

    @rule("CIR-RENDER-PALETTE")
    def test_palette_label_contrast(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-PALETTE#palette-label-contrast — each status's label colour vs its fill:
        ≥ 4.5:1 for all four.

        Contrast is the WCAG ratio of the label's computed fill against its cell's computed
        fill, the lowest per status; the fixture draws all four statuses."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            cells = observe(page, _CELLS, "cells: computed label + path fill")
        lowest: dict[str, float] = {}
        for c in cells:
            ratio = round(_contrast(c["labelFill"], c["fill"]), 2)
            lowest[c["status"]] = min(ratio, lowest.get(c["status"], ratio))
        for status in ("green", "yellow", "red", "grey"):
            then(f"lowest label contrast on {status} cells", lowest.get(status, 0.0), 4.5, op=">=")


# ===========================================================================
# CIR-RENDER-NO-JS — the page still says something
# ===========================================================================

class TestNoJs:
    """CIR-RENDER-NO-JS (specs/render/interactions.md) — every case runs with JS disabled."""

    @rule("CIR-RENDER-NO-JS")
    def test_no_js_text_alternative_renders(self, nojs_page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-NO-JS#no-js-text-alternative-renders — JS disabled: every item listed with
        its ring, label and status word.

        Expected rows, inside-out and in config order: (ring label, item label, status word) from
        the fixture and its image-build statuses."""
        given_page(pages_dir, "index.html", "unmodified, JS disabled")
        with when("browser (JS disabled) loads index.html"):
            nojs_page.goto(f"{served}/index.html")
            table = observe(nojs_page, _A11Y_TABLE, "text alternative: rows")
        then("text alternative rows (ring, item, status)", [r[:3] for r in table["rows"]],
             [[RING_OF[ref], ITEM_LABELS[ref], WORDS[UNEVALUATED_STATUS[ref]]] for ref in CELL_ORDER])

    @rule("CIR-RENDER-NO-JS")
    def test_no_js_is_not_blank(self, nojs_page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-NO-JS#no-js-is-not-blank — JS disabled: never an empty page and never an
        unexplained chart frame.

        ⚖-R44 (b): the chart is baked markup, so with scripting off the picture is the same
        picture — all 8 fixture cells drawn with a positive box, the chart labelled as an image."""
        given_page(pages_dir, "index.html", "unmodified, JS disabled")
        with when("browser (JS disabled) loads index.html"):
            nojs_page.goto(f"{served}/index.html")
            cells = observe(nojs_page, _CELLS, "cells: drawn boxes")
            chart = observe(nojs_page, """() => { const s = document.querySelector('#chart-area svg');
                const r = s.getBoundingClientRect();
                return {w: r.width, h: r.height, label: s.getAttribute('aria-label')}; }""", "chart box")
        then("cells drawn with a positive box", [c["item"] for c in cells if c["box"]["w"] > 0 and c["box"]["h"] > 0],
             CELL_ORDER)
        then("chart accessible label", chart["label"], "Alex Example", op="contains")

    @rule("CIR-RENDER-NO-JS")
    def test_no_js_detail_lines_present(self, nojs_page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-NO-JS#no-js-detail-lines-present — JS disabled: baked detail lines shown
        as text, since no composition is needed.

        Expected: the text alternative's Detail column is each item's baked `detail_line`,
        verbatim and in order, from the artifact the page carries (the given)."""
        artifact = given_page(pages_dir, "index.html", "unmodified, JS disabled")
        with when("browser (JS disabled) loads index.html"):
            nojs_page.goto(f"{served}/index.html")
            table = observe(nojs_page, _A11Y_TABLE, "text alternative: rows")
        then("Detail column", [r[3] for r in table["rows"]],
             [i["detail_line"] for r in artifact["rings"] for i in r["items"]])

    @rule("CIR-RENDER-NO-JS")
    def test_no_js_links_work(self, nojs_page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-NO-JS#no-js-links-work — JS disabled: configured links are plain anchors
        and still navigate.

        The click-root-relative row: clicking self/sleep with scripting off lands on its
        `link: /details/self-sleep.html`."""
        name = "index-click-click-root-relative.html"
        given_page(pages_dir, name, "click row click-root-relative, JS disabled")
        with allure.step(f"Given: browser (JS disabled) has {name} open"):
            assert nojs_page.goto(f"{served}/{name}").ok
            at = {c["item"]: c["at"] for c in nojs_page.evaluate(_CELLS)}["self/sleep"]
        with when(f"click self/sleep at ({at['x']:.0f}, {at['y']:.0f}) with JS disabled"):
            nojs_page.mouse.click(at["x"], at["y"])
            nojs_page.wait_for_url("**/details/self-sleep.html", timeout=5000)
            allure.attach(nojs_page.url.replace(served, ""), name="page URL after the click",
                          attachment_type=allure.attachment_type.TEXT)
        then("page URL path", nojs_page.url.replace(served, ""), "/details/self-sleep.html")


# ===========================================================================
# CIR-RENDER-A11Y-TABLE — the accessible equivalent
# ===========================================================================

class TestA11yTable:
    """CIR-RENDER-A11Y-TABLE (specs/render/colors.md)."""

    @rule("CIR-RENDER-A11Y-TABLE")
    def test_a11y_table_complete(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-A11Y-TABLE#a11y-table-complete — fixture artifact: every cell appears under
        its ring, ring-ordered inside-out.

        Expected (ring label, item label) pairs: the fixture's 8 items, rings inside-out."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            table = observe(page, _A11Y_TABLE, "text alternative: rows")
        then("text alternative (ring, item)", [r[:2] for r in table["rows"]],
             [[RING_OF[ref], ITEM_LABELS[ref]] for ref in CELL_ORDER])

    @rule("CIR-RENDER-A11Y-TABLE")
    def test_a11y_table_states_status_in_words(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-A11Y-TABLE#a11y-table-states-status-in-words — any item: "attention",
        never a colour swatch alone.

        Expected Status column: the palette word of each image-build status; and no element in
        the table paints a background (no swatch stands in for a word)."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            table = observe(page, _A11Y_TABLE, "text alternative: rows")
            painted = observe(page, """() => Array.from(document.querySelectorAll('#a11y-table *'))
                .filter(e => !['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(e).backgroundColor))
                .map(e => e.tagName.toLowerCase())""", "table elements with a painted background")
        then("Status column", [r[2] for r in table["rows"]], [WORDS[UNEVALUATED_STATUS[r]] for r in CELL_ORDER])
        then("partner/date-night status", table["rows"][3][2], "attention")
        then("table elements painting a background", painted, [])

    @rule("CIR-RENDER-A11Y-TABLE")
    def test_a11y_table_without_js(self, nojs_page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-A11Y-TABLE#a11y-table-without-js — JS disabled: the table renders.

        Expected: header Ring / Item / Status / Detail and one row per fixture item (8)."""
        given_page(pages_dir, "index.html", "unmodified, JS disabled")
        with when("browser (JS disabled) loads index.html"):
            nojs_page.goto(f"{served}/index.html")
            table = observe(nojs_page, _A11Y_TABLE, "text alternative: header + rows")
        then("table header", table["head"], ["Ring", "Item", "Status", "Detail"])
        then("table rows", len(table["rows"]), len(CELL_ORDER))


# ===========================================================================
# CIR-RENDER-CHROME — the page furniture
# ===========================================================================

class TestChrome:
    """CIR-RENDER-CHROME (specs/render/layout.md)."""

    @rule("CIR-RENDER-CHROME")
    def test_chrome_ring_key_order(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-CHROME#chrome-ring-key-order — fixture rings: key lists ① Self, ② Partner,
        ③ Children, ④ Wider life top to bottom.

        Measured: the key entries' rendered text, sorted by their on-screen top edge."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            entries = observe(page, """() => Array.from(document.querySelectorAll('#ring-key li'))
                .map(li => ({text: li.innerText.trim(), top: li.getBoundingClientRect().top}))""",
                              "ring key entries (text, top)")
        then("ring key, top to bottom", [e["text"] for e in sorted(entries, key=lambda e: e["top"])], RING_LABELS)

    @rule("CIR-RENDER-CHROME")
    def test_chrome_banner_hidden_when_clean(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-CHROME#chrome-banner-hidden-when-clean — `warnings: []`: no banner and no
        empty placeholder; the chart uses the space.

        The evaluated bake of the fixture carries no warnings (every adapter resolves). Expected:
        no warnings element at all in the page."""
        artifact = given_page(pages_dir, "index-evaluated.html", "baked with --evaluate")
        assert artifact["warnings"] == [], "arrange: the evaluated fixture must have no warnings"
        with when("browser loads index-evaluated.html"):
            page.goto(f"{served}/index-evaluated.html")
            found = observe(page, "() => document.querySelectorAll('#warnings, .warnings').length",
                            "warnings elements in the page")
        then("warnings elements (warnings: [])", found, 0)

    @rule("CIR-RENDER-CHROME")
    def test_chrome_idle_detail_strip(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-CHROME#chrome-idle-detail-strip — nothing hovered: a neutral idle line,
        never a stale cell's content.

        Expected: at load, with no pointer or focus, the strip shows a non-empty line naming no
        item."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html (no pointer, no focus)"):
            page.goto(f"{served}/index.html")
            strip = observe(page, _STRIP, "detail strip text")
        then("item labels named in the detail strip", [l for l in ITEM_LABELS.values() if l in strip], [])
        then("detail strip is non-empty", bool(strip), True)


# ===========================================================================
# CIR-RENDER-STATUS-ENCODING — status is never colour alone
# ===========================================================================

class TestStatusEncoding:
    """CIR-RENDER-STATUS-ENCODING (specs/render/colors.md)."""

    @rule("CIR-RENDER-STATUS-ENCODING")
    def test_status_word_in_detail_line(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-STATUS-ENCODING#status-word-in-detail-line — hover a 🔴 cell: the detail
        line contains the word `act`.

        wider/friends is the fixture's 🔴 (`manual: red`)."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        at = {c["item"]: c["at"] for c in page.evaluate(_CELLS)}["wider/friends"]
        with when(f"pointer hovers wider/friends at ({at['x']:.0f}, {at['y']:.0f})"):
            page.mouse.move(at["x"], at["y"])
            strip = observe(page, _STRIP, "detail strip text")
        then("detail strip", strip, "act", op="contains")

    @rule("CIR-RENDER-STATUS-ENCODING")
    def test_status_word_in_a11y_name(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-STATUS-ENCODING#status-word-in-a11y-name — a cell's computed accessible
        name: contains label + status word.

        Expected: for every drawn cell, Chromium's computed name contains the fixture label and
        the palette word of its image-build status."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        with when("Chromium computes the accessibility tree of the loaded page"):
            names = _ax_names(page)
            allure.attach(json.dumps(names, indent=2, ensure_ascii=False),
                          name="computed accessible name per cell", attachment_type=allure.attachment_type.JSON)
        missing = [ref for ref in CELL_ORDER
                   if ITEM_LABELS[ref] not in names.get(ref, "")
                   or WORDS[UNEVALUATED_STATUS[ref]] not in names.get(ref, "")]
        then("cells whose name lacks label or status word", missing, [])


# ===========================================================================
# CIR-RENDER-LEGEND — the key
# ===========================================================================

_LEGEND = """() => Array.from(document.querySelectorAll('#legend .legend-item')).map(i => {
  const s = i.querySelector('.legend-swatch'), r = s.getBoundingClientRect();
  return {word: i.innerText.trim(), swatch: getComputedStyle(s).backgroundColor,
          visible: r.width > 0 && r.height > 0 && getComputedStyle(i).visibility !== 'hidden'};
})"""


class TestLegend:
    """CIR-RENDER-LEGEND (specs/render/colors.md)."""

    @rule("CIR-RENDER-LEGEND")
    def test_legend_all_four(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-LEGEND#legend-all-four — artifact with only green items: the legend still
        shows all four entries.

        index-only-green.html keeps the fixture's `manual: green` items only (nova, kit).
        Expected: four visible entries, the palette's four fills with their words."""
        given_page(pages_dir, "index-only-green.html", "manual: green items only")
        with when("browser loads index-only-green.html"):
            page.goto(f"{served}/index-only-green.html")
            legend = observe(page, _LEGEND, "legend entries (word, swatch, visible)")
            statuses = observe(page, "() => [...new Set(Array.from(document.querySelectorAll('.cell'))"
                                     ".map(c => c.getAttribute('data-status')))]", "statuses drawn")
        then("statuses drawn", statuses, ["green"])
        then("visible legend entries (word, swatch)", [[e["word"], e["swatch"]] for e in legend if e["visible"]],
             [[WORDS[s], _rgb(PALETTE[s])] for s in ("green", "yellow", "red", "grey")])

    @rule("CIR-RENDER-LEGEND")
    def test_legend_words(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-LEGEND#legend-words — legend text: exactly `ok` / `attention` / `act` /
        `unmonitored`."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            legend = observe(page, _LEGEND, "legend entries (word, swatch, visible)")
        then("legend words", [e["word"] for e in legend], LEGEND_WORDS)


# ===========================================================================
# CIR-RENDER-SUMMARY — the count that survives everything
# ===========================================================================

_CENTRE = """() => Array.from(document.querySelectorAll('#chart-area svg > text')).map(t => t.textContent.trim())"""


class TestSummary:
    """CIR-RENDER-SUMMARY (specs/render/sunburst.md)."""

    @rule("CIR-RENDER-SUMMARY")
    def test_summary_matches_the_picture(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-SUMMARY#summary-matches-the-picture — counts equal the drawn arcs.

        The fixture as the image build bakes it: 2 🟢 (nova, kit), 1 🟡 (date-night), 1 🔴
        (friends), 4 ⚪ (exercise by choice; sleep, labs, plants not evaluated). Measured: the
        centre summary's counts, and the drawn cells counted by their computed fill."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            centre = observe(page, _CENTRE, "centre disc texts")
            cells = observe(page, _CELLS, "cells: computed fill")
        summary = next(t for t in centre if " · " in t)
        said = {"green": 0, "yellow": 0, "red": 0, "grey": 0}
        for n, what in re.findall(r"(\d+) ([a-z ]+?)(?: · |$)", summary):
            key = {"ok": "green", "attention": "yellow", "act": "red"}.get(what, "grey")
            said[key] += int(n)
        by_fill = {s: sum(1 for c in cells if c["fill"] == _rgb(h)) for s, h in PALETTE.items()}
        expected = {"green": 2, "yellow": 1, "red": 1, "grey": 4}
        then("summary counts", said, expected)
        then("drawn cells by fill", by_fill, expected)

    @rule("CIR-RENDER-SUMMARY")
    def test_summary_separates_grey_reasons(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-SUMMARY#summary-separates-grey-reasons — grey reasons counted separately,
        never lumped ("never 3 unmonitored").

        The fixture's greys are 1 by-choice (exercise) and 3 not-evaluated (sleep, labs, plants
        — no by-failure item exists in the world), so: "1 unmonitored" and "3 not evaluated",
        never "4 unmonitored"."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            centre = observe(page, _CENTRE, "centre disc texts")
        summary = next(t for t in centre if " · " in t)
        then("centre summary", summary, "1 unmonitored", op="contains")
        then("centre summary", summary, "3 not evaluated", op="contains")
        then("centre summary", summary, "4 unmonitored", op="not contains")

    @rule("CIR-RENDER-SUMMARY")
    def test_summary_is_not_a_rollup(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-SUMMARY#summary-is-not-a-rollup — any config: no ring and no page is
        assigned a colour.

        Measured: the computed paint of the page background, the centre disc and every ring-key
        entry — none of them may be one of the four status fills."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            paint = observe(page, """() => {
                const cs = e => getComputedStyle(e);
                const disc = document.querySelector('#chart-area svg > circle');
                const out = {body: cs(document.body).backgroundColor, disc: cs(disc).fill};
                document.querySelectorAll('#ring-key li').forEach((li, i) => {
                  out['ring ' + i + ' text'] = cs(li).color; out['ring ' + i + ' bg'] = cs(li).backgroundColor; });
                return out; }""", "computed paint: page, centre disc, ring key")
        palette = {_rgb(h) for h in PALETTE.values()}
        then("page/ring surfaces painted a status colour", sorted(k for k, v in paint.items() if v in palette), [])


# ===========================================================================
# CIR-RENDER-GREY-VISIBLE — the honest grey
# ===========================================================================

class TestGreyVisible:
    """CIR-RENDER-GREY-VISIBLE (specs/render/colors.md)."""

    @rule("CIR-RENDER-GREY-VISIBLE")
    def test_grey_reason_distinguishable(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-GREY-VISIBLE#grey-reason-distinguishable — one by-choice cell and one
        tooling-caused cell are distinguishable without hovering, via the text alternative's
        Detail cell and the separated summary counts — never via the fill (CIR-DATA-GREY-REASON).

        self/exercise is by-choice, self/sleep not-evaluated (fixture comments). Expected: their
        Detail cells differ; the summary names both reasons; their accessible names carry the
        reason; every ⚪ cell computes the one grey fill."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            table = observe(page, _A11Y_TABLE, "text alternative: rows")
            centre = observe(page, _CENTRE, "centre disc texts")
            cells = observe(page, _CELLS, "cells: computed fill")
            names = _ax_names(page)
        detail = {row[1]: row[3] for row in table["rows"]}
        summary = next(t for t in centre if " · " in t)
        then("Exercise (by-choice) Detail cell", detail["Exercise"], "unmonitored")
        then("Sleep (not-evaluated) Detail cell", detail["Sleep"], "not evaluated in this build", op="contains")
        then("centre summary", summary, "1 unmonitored · 3 not evaluated", op="contains")
        then("accessible names: exercise / sleep reason",
             [names.get("self/exercise", "").endswith("by choice"), names.get("self/sleep", "").endswith("not evaluated")],
             [True, True])
        then("computed fills of ⚪ cells", sorted({c["fill"] for c in cells if c["status"] == "grey"}),
             [_rgb(PALETTE["grey"])])

    @rule("CIR-RENDER-GREY-VISIBLE")
    def test_grey_surface_proportion(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-GREY-VISIBLE#grey-surface-proportion — the fixture's `self/exercise`: the
        grey arc occupies its full share of the ring.

        self's three items declare no share, so each holds an equal third (CIR-DATA-SHARE):
        exercise's measured angular span equals each coloured-or-not sibling's, to 0.1°, and
        its radial band is the ring's full thickness."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            geo = {g["item"]: g for g in observe(page, _GEOMETRY, "cell geometry (polar, user space)")}
        span = {ref: round(geo[ref]["span"], 1) for ref in ("self/sleep", "self/labs", "self/exercise")}
        band = {ref: round(geo[ref]["rMax"] - geo[ref]["rMin"], 1) for ref in span}
        then("self/exercise span (°)", span["self/exercise"], span["self/sleep"])
        then("self/exercise span (°)", span["self/exercise"], span["self/labs"])
        then("self/exercise band thickness", band["self/exercise"], band["self/sleep"])


# ===========================================================================
# CIR-RENDER-GENERATED-AT — the honesty stamp
# ===========================================================================

class TestGeneratedAt:
    """CIR-RENDER-GENERATED-AT (specs/render/layout.md)."""

    @rule("CIR-RENDER-GENERATED-AT")
    def test_stamp_verbatim(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-GENERATED-AT#stamp-verbatim — `generated_at: "2026-08-03T02:00:00Z"`: the
        page shows that exact string.

        index-no-threshold.html is the fixture baked at exactly that generated_at. Measured: the
        stamp's rendered text, and that it is visible without interaction."""
        artifact = given_page(pages_dir, "index-no-threshold.html", f"generated_at {STAMP}")
        assert artifact["generated_at"] == STAMP, "arrange: the variant's generated_at"
        with when("browser loads index-no-threshold.html"):
            page.goto(f"{served}/index-no-threshold.html")
            stamp = observe(page, "() => document.getElementById('stamp').innerText.trim()", "stamp text")
            visible = page.locator("#stamp").is_visible()
        then("stamp text", stamp, STAMP, op="contains")
        then("stamp visible without interaction", visible, True)


# ===========================================================================
# CIR-RENDER-NO-EGRESS / CIR-BAKE-SELF-CONTAINED / CIR-RENDER-ASSET-BUDGET — talks to nobody
# ===========================================================================

def _load_recording(page: Page, url: str, *, block: bool) -> dict:
    """Load ``url`` recording every request the page makes; with ``block`` every request other
    than the document itself is aborted. The record is attached by the caller's when step."""
    requests: list[dict] = []
    page.on("request", lambda r: requests.append({"url": r.url, "type": r.resource_type}))
    if block:
        page.route("**/*", lambda route: route.continue_() if route.request.resource_type == "document"
                   else route.abort())
    response = page.goto(url)
    return {"status": response.status if response else None, "bytes": len(response.body()) if response else 0,
            "requests": requests}


class TestNoEgress:
    """CIR-RENDER-NO-EGRESS (specs/render/layout.md)."""

    @rule("CIR-RENDER-NO-EGRESS")
    def test_no_external_requests_at_runtime(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-NO-EGRESS#no-external-requests-at-runtime — page loaded with all
        non-document requests blocked: renders identically.

        Expected: the only request is the document itself, and the full picture renders — all 8
        fixture cells drawn, the stamp shown."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html with every non-document request aborted"):
            rec = _load_recording(page, f"{served}/index.html", block=True)
            rec["cells"] = [c["item"] for c in page.evaluate(_CELLS) if c["box"]["w"] > 0]
            allure.attach(json.dumps(rec, indent=2), name="requests + drawn cells", attachment_type=allure.attachment_type.JSON)
        then("requests other than the document", [r for r in rec["requests"] if r["type"] != "document"], [])
        then("cells drawn", rec["cells"], CELL_ORDER)

    @rule("CIR-RENDER-NO-EGRESS")
    def test_no_third_party_origins(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-NO-EGRESS#no-third-party-origins-in-markup — built page: zero references to
        any host other than the page's own origin.

        Measured over the live DOM: every URL-bearing attribute (href, src, xlink:href, action,
        srcset, poster) and every url()/@import in the page's stylesheets, resolved against the
        page; expected: no origin but the page's own."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            foreign = observe(page, """() => {
                const refs = [];
                for (const e of document.querySelectorAll('*'))
                  for (const a of ['href', 'src', 'xlink:href', 'action', 'srcset', 'poster'])
                    if (e.getAttribute(a)) refs.push(e.getAttribute(a));
                for (const s of document.styleSheets) for (const r of s.cssRules) {
                  for (const m of r.cssText.matchAll(/url\\(["']?([^"')]+)/g)) refs.push(m[1]);
                  if (r instanceof CSSImportRule) refs.push(r.href);
                }
                return refs.filter(u => !u.startsWith('#'))
                           .filter(u => new URL(u, location.href).origin !== location.origin);
              }""", "references to another origin")
        then("references to another origin", foreign, [])

    @rule("CIR-RENDER-NO-EGRESS")
    def test_fonts_are_system(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-NO-EGRESS#fonts-are-system-or-inlined — built page: no webfont fetch.

        Measured after the page's fonts settle: font resources the browser fetched, and the
        @font-face faces the document declares — both empty."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html and its fonts settle"):
            page.goto(f"{served}/index.html")
            fonts = observe(page, """async () => { await document.fonts.ready;
                return {fetched: performance.getEntriesByType('resource')
                                   .filter(e => e.initiatorType === 'css' || /\\.(woff2?|ttf|otf)/.test(e.name))
                                   .map(e => e.name),
                        faces: Array.from(document.fonts).map(f => f.family)}; }""", "font fetches + faces")
        then("font resources fetched", fonts["fetched"], [])
        then("@font-face faces declared", fonts["faces"], [])

    @rule("CIR-RENDER-NO-EGRESS")
    def test_page_works_from_file_url(self, page: Page, pages_dir: Path, tmp_path: Path) -> None:
        """CIR-RENDER-NO-EGRESS#page-works-from-file-url — saved copy opened locally: full render.

        The page is copied alone into an empty directory (a saved copy) and opened from file://.
        Expected: all 8 fixture cells drawn, the stamp shown, the text alternative complete."""
        given_page(pages_dir, "index.html", "unmodified")
        with allure.step("Given: index.html saved alone into an empty directory"):
            saved = tmp_path / "saved" / "index.html"
            saved.parent.mkdir()
            shutil.copy(pages_dir / "index.html", saved)
        with when("browser opens the saved copy from file://"):
            page.goto(saved.as_uri())
            cells = observe(page, _CELLS, "cells: drawn boxes")
            table = observe(page, _A11Y_TABLE, "text alternative: rows")
            stamp = page.locator("#stamp").is_visible()
        then("cells drawn", [c["item"] for c in cells if c["box"]["w"] > 0], CELL_ORDER)
        then("text alternative rows", len(table["rows"]), len(CELL_ORDER))
        then("stamp visible", stamp, True)


class TestSelfContainedInBrowser:
    """CIR-BAKE-SELF-CONTAINED (specs/data/data-json.md) — its browser-observable row."""

    @rule("CIR-BAKE-SELF-CONTAINED")
    def test_page_renders_with_no_network(self, page: Page, pages_dir: Path, tmp_path: Path) -> None:
        """CIR-BAKE-SELF-CONTAINED#page-renders-with-no-network — `index.html` opened from
        `file://`: full page, all statuses.

        Expected: the copy opened from file:// with every non-document request aborted makes no
        request, and draws the fixture's four statuses (🟢 nova/kit, 🟡 date-night, 🔴 friends,
        ⚪ the rest) in their palette fills."""
        given_page(pages_dir, "index.html", "unmodified")
        with allure.step("Given: index.html copied alone into an empty directory"):
            saved = tmp_path / "index.html"
            shutil.copy(pages_dir / "index.html", saved)
        with when("browser opens the copy from file:// with the network blocked"):
            rec = _load_recording(page, saved.as_uri(), block=True)
            cells = page.evaluate(_CELLS)
            rec["fills"] = sorted({c["fill"] for c in cells})
            allure.attach(json.dumps(rec, indent=2), name="requests + computed fills",
                          attachment_type=allure.attachment_type.JSON)
        then("requests other than the document", [r for r in rec["requests"] if r["type"] != "document"], [])
        then("status fills drawn", rec["fills"], sorted(_rgb(h) for h in PALETTE.values()))


class TestAssetBudget:
    """CIR-RENDER-ASSET-BUDGET (specs/render/layout.md)."""

    @rule("CIR-RENDER-ASSET-BUDGET")
    def test_budget_built_page_is_small(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-ASSET-BUDGET#budget-built-page-is-small — fixture person: the single
        `index.html`, data inlined, within budget.

        The budget is "250 KB total, uncompressed" (the rule's text), held here as 250 000
        bytes. Measured: everything the browser fetches to show the page — the document is the
        only request, and its body is within budget."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            rec = _load_recording(page, f"{served}/index.html", block=False)
            allure.attach(json.dumps(rec, indent=2), name="requests + document bytes",
                          attachment_type=allure.attachment_type.JSON)
        then("requests made", [r["type"] for r in rec["requests"]], ["document"])
        then("document bytes", rec["bytes"], BUDGET_BYTES, op="<=")


# ===========================================================================
# CIR-RENDER-PRINT-COLOR / CIR-RENDER-A4 — on paper
# ===========================================================================

def _pdf_colours(pdf: bytes) -> list[str]:
    """The palette hexes painted in a PDF: every non-stroking/stroking RGB colour operator in the
    first page's content stream, matched to the palette within 0.002 per channel."""
    data = PdfReader(io.BytesIO(pdf)).pages[0].get_contents().get_data().decode("latin-1")
    triples = {tuple(float(v) for v in m) for m in re.findall(r"([\d.]+) ([\d.]+) ([\d.]+) (?:rg|RG)\b", data)}
    found = []
    for status, hexa in PALETTE.items():
        want = tuple(int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
        if any(all(math.isclose(a, b, abs_tol=0.002) for a, b in zip(t, want)) for t in triples):
            found.append(hexa)
    return found


class TestPrintColor:
    """CIR-RENDER-PRINT-COLOR (specs/render/colors.md)."""

    @rule("CIR-RENDER-PRINT-COLOR")
    def test_print_fills_without_user_settings(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-PRINT-COLOR#print-fills-without-user-settings — default print dialog: all
        fills present.

        The default dialog prints without "background graphics", so the PDF is produced with
        `print_background=False`. Measured: the colours actually painted in the PDF's content
        stream — all four palette fills (#no-render-claim-from-source-alone)."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        with when("print to A4 PDF with the dialog's defaults (background graphics off)"):
            page.emulate_media(media="print")
            pdf = page.pdf(format="A4", print_background=False, prefer_css_page_size=True)
            found = _pdf_colours(pdf)
            allure.attach(json.dumps(found), name="palette colours painted in the PDF",
                          attachment_type=allure.attachment_type.JSON)
        then("palette fills painted in the PDF", found, list(PALETTE.values()))

    @rule("CIR-RENDER-PRINT-COLOR")
    def test_print_stylesheet_is_inline(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-PRINT-COLOR#print-stylesheet-is-inline — built page: inline, no separate
        stylesheet fetch.

        Measured: stylesheet requests the browser made (none), and that every stylesheet the
        document has — the print rules among them — is inline (no href)."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            rec = _load_recording(page, f"{served}/index.html", block=False)
            sheets = observe(page, """() => Array.from(document.styleSheets).map(s => ({href: s.href,
                print: Array.from(s.cssRules).some(r => r.media && r.media.mediaText.includes('print'))}))""",
                             "document stylesheets")
        then("stylesheet requests", [r["url"] for r in rec["requests"] if r["type"] == "stylesheet"], [])
        then("stylesheets loaded from a URL", [s["href"] for s in sheets if s["href"]], [])
        then("an inline stylesheet carries the print rules", any(s["print"] for s in sheets), True)


class TestPrintA4Affordances:
    """CIR-RENDER-A4 (specs/render/layout.md) — the affordances row (test_print.py has the rest)."""

    @rule("CIR-RENDER-A4")
    def test_print_interactive_affordances_hidden(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-A4#print-interactive-affordances-hidden — printed page: no hover chrome,
        no focus outlines, no buttons.

        A cell is keyboard-focused (its focus outline showing) before the page is printed.
        Measured under print media: the focused cell's outline is the resting one (white,
        undashed — the same as an unfocused sibling's), the hover detail strip is not displayed,
        and no <button> is rendered."""
        given_loaded(page, served, pages_dir, "index.html", "unmodified")
        with allure.step("Given: self/sleep keyboard-focused (focus outline on screen)"):
            page.keyboard.press("Tab")
            on_screen = {c["item"]: c for c in page.evaluate(_CELLS)}["self/sleep"]
            assert on_screen["dash"] != "none", "arrange: focus outline expected on screen"
        with when("the page is rendered for print (print media)"):
            page.emulate_media(media="print")
            cells = {c["item"]: c for c in observe(page, _CELLS, "cells under print media")}
            chrome = observe(page, """() => ({strip: getComputedStyle(document.getElementById('detail-strip')).display,
                buttons: Array.from(document.querySelectorAll('button')).filter(b => b.getClientRects().length).length})""",
                             "detail strip display + rendered buttons")
        focused, resting = cells["self/sleep"], cells["self/labs"]
        then("focused cell outline (stroke, width, dash)", [focused["stroke"], focused["strokeWidth"], focused["dash"]],
             [resting["stroke"], resting["strokeWidth"], resting["dash"]])
        then("detail strip display", chrome["strip"], "none")
        then("rendered buttons", chrome["buttons"], 0)


# ===========================================================================
# CIR-RENDER-RING-ORDER / -SIBLING-ORDER / -RING-THICKNESS / -LABELS — the measured picture
# ===========================================================================

class TestGeometry:
    """Sunburst geometry rows (specs/render/sunburst.md), measured from the drawn paths."""

    @rule("CIR-RENDER-RING-ORDER")
    def test_ring_order_innermost_first(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-RING-ORDER#ring-order-innermost-first — rings `[self, partner, children,
        wider]`: `self` is the innermost rendered ring, `wider` the outermost.

        Measured: each ring's innermost drawn radius (from its cells' paths); rings sorted by it."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            geo = observe(page, _GEOMETRY, "cell geometry (polar, user space)")
        inner: dict[str, float] = {}
        for g in geo:
            ring_id = g["item"].split("/")[0]
            inner[ring_id] = min(g["rMin"], inner.get(ring_id, math.inf))
        then("rings from the centre outward", sorted(inner, key=inner.get), ["self", "partner", "children", "wider"])

    @rule("CIR-RENDER-SIBLING-ORDER")
    @pytest.mark.xfail(strict=True, reason=(
        "RED against the spec: bake/render.py starts every ring at current_angle = -90 in a frame "
        "where 0 is 12 o'clock (x = cx + r·sin, y = cy − r·cos), so the first sibling starts at "
        "9 o'clock — nova measures 270°→88°, not 0°→180°. Product fix is outside this chunk; strict, "
        "so the fix turns this XPASS red and the marker must go."))
    def test_sibling_order_clockwise_from_noon(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-SIBLING-ORDER#sibling-order-clockwise-from-noon — ring items `[nova, kit]`:
        `nova` spans 12 → 6 o'clock (the right half), `kit` 6 → 12.

        Measured in degrees clockwise from 12 o'clock: nova starts at noon (0°) and its whole
        span lies in [0°, 180°]; kit's lies in [180°, 360°]."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            geo = {g["item"]: g for g in observe(page, _GEOMETRY, "cell geometry (polar, user space)")}
        nova, kit = geo["children/nova"], geo["children/kit"]
        then("nova start (° from noon, rounded)", round(nova["start"]) % 360, 0)
        then("nova end (°)", nova["start"] + nova["span"], 180.5, op="<=")
        then("kit start (°)", kit["start"], 179.5, op=">=")
        then("kit end (°)", kit["start"] + kit["span"], 360.5, op="<=")

    @rule("CIR-RENDER-LABELS")
    def test_label_inside_arc(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-LABELS#label-inside-arc — fixture config: each item label rendered within
        its own cell's bounds.

        Measured: every corner of each label's box, mapped through its rotation into the
        chart's polar coordinates, lies within its cell's radial band and angular span."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            geo = observe(page, _GEOMETRY, "cell geometry + label corners (polar, user space)")
        outside = []
        for g in geo:
            for corner in g["labelCorners"]:
                off = (corner["a"] - g["start"]) % 360
                if not (g["rMin"] - 0.5 <= corner["r"] <= g["rMax"] + 0.5 and off <= g["span"] + 0.5):
                    outside.append(g["item"])
                    break
        then("labels with a corner outside their cell", outside, [])

    @rule("CIR-RENDER-LABELS")
    def test_label_glyphs_passthrough(self, page: Page, served: str, pages_dir: Path) -> None:
        """CIR-RENDER-LABELS#label-glyphs-passthrough — label `◀ Nova`: glyph rendered as-is.

        Measured: the rendered label text of children/nova and children/kit (fixture labels
        `◀ Nova`, `Kit ▶`), and that each paints with a positive width."""
        given_page(pages_dir, "index.html", "unmodified")
        with when("browser loads index.html"):
            page.goto(f"{served}/index.html")
            labels = observe(page, """() => Object.fromEntries(['children/nova', 'children/kit'].map(id => {
                const t = document.querySelector(`[data-item="${id}"] text`);
                return [id, {text: t.textContent, width: t.getComputedTextLength()}]; }))""", "nova/kit label text + width")
        then("children/nova label", labels["children/nova"]["text"], "◀ Nova")
        then("children/kit label", labels["children/kit"]["text"], "Kit ▶")
        then("narrower label width (px)", min(v["width"] for v in labels.values()), 0, op=">")
