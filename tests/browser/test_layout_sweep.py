# Responsive layout gate — CIR-RENDER-ONE-SCREEN#layout-sweep-clean and #layout-zoom-200
# (specs/render/layout.md), system tier (⚖-R48). Ported from oracle-fleet's DEP-STATIC-LAYOUT
# sweep (scripts/e2e/test_static_site.py, ReDeCheck method): the same in-page checks
# (layout_checks.js, next to this file — its header names the two circles changes), run at every
# width 320 → 1280 px in 16 px steps.
#
# Expectations come from the contract: ZERO findings. A finding is reported with the check, the
# element and the viewport, so a red run names the size to reproduce at.

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page

from rules import rule

pytestmark = pytest.mark.browser

LAYOUT_CHECKS_JS = Path(__file__).with_name("layout_checks.js").read_text(encoding="utf-8")

# CIR-RENDER-ONE-SCREEN#layout-sweep-clean: 320 → 1280 in 16 px steps (61 widths) at a tall-phone
# height (844, portrait below 844 wide) and at the reference height (800), plus two landscape phones.
WIDTHS = list(range(320, 1280 + 1, 16))
SWEEP = [(w, h) for h in (844, 800) for w in WIDTHS] + [(844, 390), (667, 375)]
# CIR-RENDER-ONE-SCREEN#layout-zoom-200: 390 px wide, root font size 200 % of 16 px.
ZOOM_VIEWPORT = (390, 844)
ZOOM_FONT_SIZE_PX = 32


# layout_checks.js's page-overflow is horizontal only — oracle's pages scroll vertically by design.
# circles never scrolls on EITHER axis (CIR-RENDER-ONE-SCREEN), so the sweep adds the vertical leg:
# the same scrollHeight > clientHeight probe test_one_screen.py's _assert_no_scroll uses, for the
# document element and the body.
_PAGE_SCROLL_Y = """() => [document.documentElement, document.body]
  .filter(e => e.scrollHeight > e.clientHeight + 1)
  .map(e => ({check: 'page-overflow-y', selector: e.tagName.toLowerCase(),
              detail: 'scrollHeight ' + e.scrollHeight + ' > clientHeight ' + e.clientHeight}))"""


def _findings(page: Page, viewport: tuple[int, int]) -> list[str]:
    return [
        f"{f['check']} {f['selector']} at {viewport[0]}x{viewport[1]}: {f['detail']}"
        for f in [*page.evaluate(LAYOUT_CHECKS_JS), *page.evaluate(_PAGE_SCROLL_Y)]
    ]


class TestLayoutSweep:
    """CIR-RENDER-ONE-SCREEN — the page lays out cleanly at every size, not just the gate's."""

    @rule("CIR-RENDER-ONE-SCREEN")
    def test_layout_sweep_clean(self, page: Page, served: str) -> None:
        """CIR-RENDER-ONE-SCREEN#layout-sweep-clean — fixture config at every width
        320 → 1280 px in 16 px steps, heights 844 and 800, plus 844 × 390 and 667 × 375:
        no page scroll on either axis and no clipped, collision, crushed or ellipsis finding."""
        page.goto(f"{served}/index.html")
        found: list[str] = []
        for width, height in SWEEP:
            page.set_viewport_size({"width": width, "height": height})
            found += _findings(page, (width, height))
        assert len(SWEEP) == 124
        assert not found, f"{len(found)} layout findings, first 20:\n" + "\n".join(found[:20])

    @rule("CIR-RENDER-ONE-SCREEN")
    def test_layout_zoom_200(self, page: Page, served: str) -> None:
        """CIR-RENDER-ONE-SCREEN#layout-zoom-200 — fixture config at 390 × 844 with the root
        font size at 200 % (32 px): no page scroll on either axis, no layout finding."""
        page.set_viewport_size({"width": ZOOM_VIEWPORT[0], "height": ZOOM_VIEWPORT[1]})
        page.goto(f"{served}/index.html")
        page.evaluate(f"document.documentElement.style.fontSize = '{ZOOM_FONT_SIZE_PX}px'")
        found = _findings(page, ZOOM_VIEWPORT)
        assert not found, "\n".join(found[:20])
