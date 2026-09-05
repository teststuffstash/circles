# Browser evidence for the one-screen invariant — CIR-RENDER-ONE-SCREEN and
# CIR-RENDER-REFERENCE-VIEWPORT (specs/render/layout.md), system tier (⚖-R48).
#
# Every row is cited verbatim as CIR-<AREA>-<NAME>#<row-id> on the docstring's first line or
# in the pytest.param id. Expectations are computed from the contract in comments, never
# from running the page.

from __future__ import annotations

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.browser

# The page furniture CIR-RENDER-ONE-SCREEN#one-screen-reference names: "chart, ring key,
# legend, stamp and detail strip fully visible" (ids from bake/render.py).
FURNITURE = ("#chart-area", "#ring-key", "#legend", "#stamp", "#detail-strip")

_MEASURE_SCROLL = """() => {
  const d = document.documentElement, b = document.body;
  return {
    doc:  {scrollWidth: d.scrollWidth, clientWidth: d.clientWidth,
           scrollHeight: d.scrollHeight, clientHeight: d.clientHeight},
    body: {scrollWidth: b.scrollWidth, clientWidth: b.clientWidth,
           scrollHeight: b.scrollHeight, clientHeight: b.clientHeight},
    inner: {width: window.innerWidth, height: window.innerHeight},
  };
}"""

_MEASURE_RECT = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  return {left: r.left, top: r.top, right: r.right, bottom: r.bottom,
          width: r.width, height: r.height,
          display: cs.display, visibility: cs.visibility};
}"""


def _assert_no_scroll(page: Page, viewport: tuple[int, int]) -> dict:
    """The measurable no-scroll property: for BOTH the document element and the body,
    scrollWidth <= clientWidth and scrollHeight <= clientHeight. In standards mode
    documentElement.clientHeight is the viewport height, so any content taller than
    the viewport shows up as scrollHeight > clientHeight (the seat's probe: a 900px
    body at 1280×800 reports scrollHeight 900 vs innerHeight 800)."""
    m = page.evaluate(_MEASURE_SCROLL)
    assert (m["inner"]["width"], m["inner"]["height"]) == viewport, m
    for which in ("doc", "body"):
        box = m[which]
        assert box["scrollWidth"] <= box["clientWidth"], (
            f"{which}: horizontal scroll at {viewport[0]}x{viewport[1]} — "
            f"scrollWidth={box['scrollWidth']} > clientWidth={box['clientWidth']}"
        )
        assert box["scrollHeight"] <= box["clientHeight"], (
            f"{which}: vertical scroll at {viewport[0]}x{viewport[1]} — "
            f"scrollHeight={box['scrollHeight']} > clientHeight={box['clientHeight']}"
        )
    return m


def _assert_visible_inside(page: Page, selector: str, viewport: tuple[int, int]) -> dict:
    """`selector` has a non-empty bounding rect fully inside [0,w]×[0,h]."""
    width, height = viewport
    r = page.evaluate(_MEASURE_RECT, selector)
    assert r is not None, f"{selector} is not in the page"
    assert r["display"] != "none" and r["visibility"] != "hidden", f"{selector}: {r}"
    assert r["width"] > 0 and r["height"] > 0, f"{selector} has an empty box: {r}"
    assert r["left"] >= 0 and r["top"] >= 0, f"{selector} starts off-screen: {r}"
    assert r["right"] <= width and r["bottom"] <= height, (
        f"{selector} extends past the {width}x{height} viewport: {r}"
    )
    return r


class TestOneScreen:
    """CIR-RENDER-ONE-SCREEN — no scrolling, ever."""

    def test_one_screen_reference(
        self, page: Page, served: str, reference_viewport: tuple[int, int]
    ) -> None:
        """CIR-RENDER-ONE-SCREEN#one-screen-reference — fixture config at 1280 × 800:
        no scrollbars; chart, ring key, legend, stamp and detail strip fully visible.

        Expected from the contract: the viewport is exactly the reference one (⚖-R37),
        both scroll inequalities hold, and each of the five furniture ids has a box of
        positive size inside [0,1280]×[0,800]."""
        page.goto(f"{served}/index.html")
        _assert_no_scroll(page, reference_viewport)
        for selector in FURNITURE:
            _assert_visible_inside(page, selector, reference_viewport)

    def test_one_screen_with_warnings(
        self, page: Page, served: str, reference_viewport: tuple[int, int]
    ) -> None:
        """CIR-RENDER-ONE-SCREEN#one-screen-with-warnings — artifact with 2 warnings:
        banner shown; still no scrolling (the chart yields the space).

        index-2-warnings.html is the fixture artifact with `warnings[:2]` (the same
        construction as the unit proxy). Expected: the same no-scroll and furniture
        assertions as the reference row, plus `#warnings` shown inside the viewport."""
        page.goto(f"{served}/index-2-warnings.html")
        assert "2 warnings" in page.inner_text("#warnings"), "banner must say how many"
        _assert_no_scroll(page, reference_viewport)
        for selector in (*FURNITURE, "#warnings"):
            _assert_visible_inside(page, selector, reference_viewport)

    @pytest.mark.parametrize(
        "viewport",
        [
            pytest.param((1920, 1080), id="CIR-RENDER-ONE-SCREEN#one-screen-larger-viewport"),
            pytest.param((700, 500), id="CIR-RENDER-ONE-SCREEN#one-screen-smaller-viewport"),
        ],
    )
    def test_one_screen_other_viewports(
        self, page: Page, served: str, reference_viewport: tuple[int, int],
        viewport: tuple[int, int],
    ) -> None:
        """CIR-RENDER-ONE-SCREEN — away from the reference viewport the picture scales
        rather than scrolls (⚖-R38): 1920 × 1080 scales up, 700 × 500 scales down,
        neither shows scrollbars. Legibility is not asserted at 700 × 500.

        "Scales up" is measured at 1920 × 1080: the chart is wider than at 1280 × 800.
        Expected from bake/render.py's CSS: #chrome-panel is a fixed 320px column and
        #chart-area is the flexible one with 10px padding holding a square viewBox
        capped by max-height 100%, so the chart's width is bounded by the shorter of
        (viewport width − 320 − 20) and (viewport height − 20): at most 780 at
        1280 × 800 and at most 1060 at 1920 × 1080 — strictly larger at the bigger
        viewport."""
        page.goto(f"{served}/index.html")
        reference = _assert_visible_inside(page, "#chart-area svg", reference_viewport)

        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        _assert_no_scroll(page, viewport)
        if viewport > reference_viewport:
            larger = _assert_visible_inside(page, "#chart-area svg", viewport)
            assert larger["width"] > reference["width"], (
                f"chart did not scale up: {reference['width']} at 1280x800 vs "
                f"{larger['width']} at {viewport[0]}x{viewport[1]}"
            )


class TestReferenceViewport:
    """CIR-RENDER-REFERENCE-VIEWPORT — the tested screen."""

    def test_viewport_gate_is_fixed(
        self, page: Page, reference_viewport: tuple[int, int]
    ) -> None:
        """CIR-RENDER-REFERENCE-VIEWPORT#viewport-gate-is-fixed — any one-screen
        assertion is evaluated at 1280 × 800 CSS px (⚖-R37).

        The harness constant is the row's number, and the page every test receives is
        opened at that constant — read back from the real browser context, not from
        the constant itself."""
        assert reference_viewport == (1280, 800)
        assert page.viewport_size == {"width": 1280, "height": 800}

    def test_viewport_larger_passes_trivially(self, page: Page, served: str) -> None:
        """CIR-RENDER-REFERENCE-VIEWPORT#viewport-larger-passes-trivially — at
        1920 × 1080 the composition scales up and the gate does not re-run.

        Why it need not re-run: the browser at 1920 × 1080 receives the SAME page bytes
        it receives at the reference viewport (the server has nothing to negotiate) and
        those bytes carry no viewport-conditional markup (no `@media (min-width` /
        `(max-width`), so a larger viewport cannot produce a different composition to
        gate. What is measured: identical response bodies and no scroll."""
        at_reference = page.goto(f"{served}/index.html")
        assert at_reference is not None and at_reference.ok
        reference_bytes = at_reference.body()

        page.set_viewport_size({"width": 1920, "height": 1080})
        at_larger = page.goto(f"{served}/index.html")
        assert at_larger is not None and at_larger.ok
        larger_bytes = at_larger.body()

        assert larger_bytes == reference_bytes, "page bytes differ between viewports"
        html = larger_bytes.decode("utf-8")
        assert "@media (min-width" not in html and "@media (max-width" not in html, (
            "viewport-conditional markup would make the gate size-dependent"
        )
        _assert_no_scroll(page, (1920, 1080))
