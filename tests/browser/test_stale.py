# Browser evidence for the page's own staleness — CIR-BAKE-STALE-SELF (specs/data/data-json.md)
# and CIR-RENDER-STALE-MARK (specs/render/colors.md), system tier (⚖-R48).
#
# Staleness is judged by the page at VIEW time: the browser's clock against the artifact's
# `generated_at`, past the artifact's `stale_after_hours` (⚖-R15 (c)). The tests drive the
# browser clock with Playwright's clock API — the page bytes never change between a fresh
# and a stale view.
#
# Inputs (scripts/test-browser.sh): every variant is the fixture artifact with
# generated_at = 2026-08-03T02:00:00Z.
#   index-no-threshold.html  stale_after_hours: null (P0)
#   index-stale.html         stale_after_hours: 36
#   index-stale-72.html      stale_after_hours: 72
#   index-stale-manual.html  stale_after_hours: 36, manual items only
#
# Every row is cited verbatim as CIR-<AREA>-<NAME>#<row-id> in the docstring. Expected values
# come from the spec rows; measurable properties only (text, computed style, geometry, PDF
# page count / text) — never a screenshot.

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import Page
from pypdf import PdfReader

from browser.browser_helpers import FURNITURE  # CIR-RENDER-ONE-SCREEN's named furniture
from rules import rule

pytestmark = pytest.mark.browser

GENERATED_AT = datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc)
GENERATED_AT_TEXT = "2026-08-03T02:00:00Z"  # the artifact's generated_at as baked

# CIR-BAKE-STALE-SELF#stale-bake-shows-banner — the row's wording, <n> = whole hours.
def _banner_text(hours: int) -> str:
    return f"this page was built {hours} hours ago; the lights below are history"


# CIR-RENDER-PALETTE (bake/render.py STATUS_COLORS) as computed-style rgb() strings.
GREEN_RGB = "rgb(0, 145, 106)"   # #00916A
RED_RGB = "rgb(178, 34, 34)"     # #B22222


_STATE = """() => {
  const banner = document.getElementById('stale-banner');
  const overlay = document.getElementById('stale-overlay');
  const svg = document.querySelector('#chart-area svg');
  const stamp = document.getElementById('stamp');
  return {
    bannerPresent: !!banner,
    bannerVisible: !!banner && !banner.hidden && banner.getClientRects().length > 0,
    bannerText: banner ? banner.textContent.trim() : null,
    overlayDisplay: overlay ? getComputedStyle(overlay).display : null,
    svgFilter: getComputedStyle(svg).filter,
    stampText: stamp ? stamp.textContent.trim() : null,
    stampDisplay: stamp ? getComputedStyle(stamp).display : null,
  };
}"""

_CELL_FILLS = """() => Array.from(document.querySelectorAll('.cell')).map(c => {
  const p = c.querySelector('path');
  return {item: c.getAttribute('data-item'), status: c.getAttribute('data-status'),
          fillAttr: p.getAttribute('fill'), fill: getComputedStyle(p).fill};
})"""

_OVERLAY_COVERS_CELLS = """() => {
  const o = document.getElementById('stale-overlay').getBoundingClientRect();
  const out = [];
  for (const c of document.querySelectorAll('.cell')) {
    const r = c.getBoundingClientRect();
    if (r.left < o.left - 1 || r.top < o.top - 1 || r.right > o.right + 1 || r.bottom > o.bottom + 1)
      out.push(c.getAttribute('data-item'));
  }
  return {overlay: {w: o.width, h: o.height}, uncovered: out};
}"""

_MEASURE_SCROLL = """() => {
  const d = document.documentElement, b = document.body;
  return [[d.scrollWidth, d.clientWidth, d.scrollHeight, d.clientHeight],
          [b.scrollWidth, b.clientWidth, b.scrollHeight, b.clientHeight]];
}"""


def _view(page: Page, served: str, name: str, hours_after_build: float) -> dict:
    """Open `name` with the browser clock fixed at generated_at + hours_after_build."""
    page.clock.set_fixed_time(GENERATED_AT + timedelta(hours=hours_after_build))
    page.goto(f"{served}/{name}")
    return page.evaluate(_STATE)


def _assert_no_stale_chrome(state: dict) -> None:
    assert state["bannerPresent"], "the banner slot is part of the baked page"
    assert not state["bannerVisible"], f"banner shown: {state['bannerText']!r}"
    assert state["overlayDisplay"] == "none", f"overlay rendered: {state}"
    assert "saturate" not in state["svgFilter"], f"picture desaturated: {state}"


def _fresh_and_stale(page: Page, served: str) -> tuple[list, list, dict]:
    """index-stale.html (threshold 36 h) viewed fresh (+6 h) then stale (+50 h): the cell
    fills of each view, and the stale view's state."""
    _view(page, served, "index-stale.html", 6)
    fresh = page.evaluate(_CELL_FILLS)
    state = _view(page, served, "index-stale.html", 50)
    stale = page.evaluate(_CELL_FILLS)
    return fresh, stale, state


def _assert_stamp(state: dict) -> None:
    assert state["stampDisplay"] != "none"
    assert GENERATED_AT_TEXT in (state["stampText"] or ""), state


class TestStaleSelf:
    """CIR-BAKE-STALE-SELF — the page's own freshness."""

    @rule("CIR-BAKE-STALE-SELF")
    @pytest.mark.parametrize(
        ("name", "hours"),
        [
            pytest.param("index-no-threshold.html", 50, id="null-threshold"),
            pytest.param("index-stale.html", 6, id="fresh"),
            pytest.param("index-stale.html", 50, id="stale"),
        ],
    )
    def test_stamp_always_visible(self, page: Page, served: str, name: str, hours: int) -> None:
        """CIR-BAKE-STALE-SELF#stamp-always-visible — any page: stamp shown in a fixed
        place, never only on hover.

        Expected: with no pointer or focus interaction at all, #stamp is visible and
        carries the artifact's generated_at, whatever the threshold and clock."""
        state = _view(page, served, name, hours)
        _assert_stamp(state)
        assert page.locator("#stamp").is_visible()

    @rule("CIR-BAKE-STALE-SELF")
    def test_no_threshold_no_banner(self, page: Page, served: str) -> None:
        """CIR-BAKE-STALE-SELF#no-threshold-no-banner — `stale_after_hours: null` (P0):
        stamp only; no banner, no invented expectation.
        (Its CIR-RENDER-STALE-MARK twin: TestStaleMark.test_no_threshold_no_stale_chrome.)

        Viewed 1000 h after the build: with no declared cadence no age is "stale"."""
        state = _view(page, served, "index-no-threshold.html", 1000)
        _assert_no_stale_chrome(state)
        _assert_stamp(state)

    @rule("CIR-BAKE-STALE-SELF")
    def test_fresh_bake_shows_no_banner(self, page: Page, served: str) -> None:
        """CIR-BAKE-STALE-SELF#fresh-bake-shows-no-banner — `generated_at` 6 h old,
        `stale_after_hours: 36`: no banner.
        (Its CIR-RENDER-STALE-MARK twin: TestStaleMark.test_fresh_page_has_no_stale_chrome.)

        6 h <= 36 h, so the page is fresh."""
        _assert_no_stale_chrome(_view(page, served, "index-stale.html", 6))

    @rule("CIR-BAKE-STALE-SELF")
    def test_stale_bake_shows_banner(self, page: Page, served: str) -> None:
        """CIR-BAKE-STALE-SELF#stale-bake-shows-banner — `generated_at` 50 h old,
        `stale_after_hours: 36`: banner "this page was built <n> hours ago; the lights
        below are history".

        50 h > 36 h → stale; <n> = 50."""
        state = _view(page, served, "index-stale.html", 50)
        assert state["bannerVisible"], state
        assert state["bannerText"] == _banner_text(50)

    @rule("CIR-BAKE-STALE-SELF")
    def test_stale_lights_marked_not_recoloured(self, page: Page, served: str) -> None:
        """CIR-BAKE-STALE-SELF#stale-lights-marked-not-recoloured — stale bake, item was
        🟢: still 🟢 in place, with the stale treatment.

        Expected: the same bytes viewed fresh (+6 h) and stale (+50 h) give every cell the
        same status, fill attribute and computed fill; every 🟢 cell computes to the palette
        green; and the stale view carries the treatment (banner, desaturation, overlay)."""
        fresh, stale, state = _fresh_and_stale(page, served)

        assert fresh and stale == fresh, "stale view recoloured or moved a cell"
        greens = [c for c in stale if c["status"] == "green"]
        assert greens, "fixture has 🟢 items (CIR-PROC-TEST-FIXTURES)"
        assert all(c["fill"] == GREEN_RGB for c in greens), greens

        assert state["bannerVisible"], state
        assert "saturate" in state["svgFilter"], f"no desaturation: {state['svgFilter']}"
        assert state["overlayDisplay"] != "none", "no hatched overlay"

    @rule("CIR-BAKE-STALE-SELF")
    def test_stale_bake_never_turns_items_red(self, page: Page, served: str) -> None:
        """CIR-BAKE-STALE-SELF#stale-bake-never-turns-items-red — stale bake: not 🔴.

        Expected: viewed stale (+50 h), no cell that was not 🔴 computes to the palette red,
        and no cell changed status against the fresh view (+6 h)."""
        fresh, stale, state = _fresh_and_stale(page, served)

        assert state["bannerVisible"], state
        assert fresh and stale == fresh, "stale view recoloured or moved a cell"
        not_red = [c for c in stale if c["status"] != "red"]
        assert all(c["fill"] != RED_RGB for c in not_red), not_red

    @rule("CIR-BAKE-STALE-SELF")
    def test_manual_items_are_stale_too(self, page: Page, served: str) -> None:
        """CIR-BAKE-STALE-SELF#manual-items-are-stale-too — stale bake with only `manual:`
        items: the banner applies to the whole page.

        index-stale-manual.html keeps only the fixture's `manual:` items; at +50 h with
        threshold 36 the banner shows exactly as for the full page, and the overlay
        renders."""
        state = _view(page, served, "index-stale-manual.html", 50)
        statuses = {c["status"] for c in page.evaluate(_CELL_FILLS)}
        assert statuses <= {"green", "yellow", "red"}, f"non-manual cell present: {statuses}"
        assert state["bannerVisible"] and state["bannerText"] == _banner_text(50), state
        assert state["overlayDisplay"] != "none", state

    @rule("CIR-BAKE-STALE-SELF")
    @pytest.mark.parametrize(
        ("name", "hours", "stale"),
        [
            pytest.param("index-stale.html", 35, False, id="36h-at-35h"),
            pytest.param("index-stale.html", 37, True, id="36h-at-37h"),
            pytest.param("index-stale-72.html", 50, False, id="72h-at-50h"),
            pytest.param("index-stale-72.html", 73, True, id="72h-at-73h"),
        ],
    )
    def test_threshold_comes_from_the_artifact(
        self, page: Page, served: str, name: str, hours: int, stale: bool
    ) -> None:
        """CIR-BAKE-STALE-SELF#threshold-comes-from-the-artifact — `stale_after_hours: 36`:
        the page reads it; no hard-coded value in the page.

        Two cadences bracket the age: 36 → fresh at 35 h, stale at 37 h; 72 → fresh at
        50 h (stale under 36), stale at 73 h. Any single number baked into the page fails
        at least one of the four."""
        state = _view(page, served, name, hours)
        if stale:
            assert state["bannerVisible"] and state["bannerText"] == _banner_text(hours), state
        else:
            _assert_no_stale_chrome(state)


class TestStaleMark:
    """CIR-RENDER-STALE-MARK — showing that the lights are history."""

    @rule("CIR-RENDER-STALE-MARK")
    def test_no_threshold_no_stale_chrome(self, page: Page, served: str) -> None:
        """CIR-RENDER-STALE-MARK#no-threshold-no-stale-chrome — no banner, no overlay,
        stamp still shown.

        `stale_after_hours: null` (P0) viewed 1000 h after the build: with no declared
        cadence no age is "stale"."""
        state = _view(page, served, "index-no-threshold.html", 1000)
        _assert_no_stale_chrome(state)
        _assert_stamp(state)

    @rule("CIR-RENDER-STALE-MARK")
    def test_fresh_page_has_no_stale_chrome(self, page: Page, served: str) -> None:
        """CIR-RENDER-STALE-MARK#fresh-page-has-no-stale-chrome — no banner, no overlay.

        `generated_at` 6 h old, `stale_after_hours: 36`: 6 h <= 36 h, so the page is fresh."""
        _assert_no_stale_chrome(_view(page, served, "index-stale.html", 6))

    @rule("CIR-RENDER-STALE-MARK")
    def test_stale_is_not_a_fifth_colour(self, page: Page, served: str) -> None:
        """CIR-RENDER-STALE-MARK#stale-is-not-a-fifth-colour — statuses keep their colours;
        staleness is a separate visual channel (desaturation plus a hatched overlay).

        Expected: the same bytes viewed fresh (+6 h) and stale (+50 h) give every cell the
        same status, fill attribute and computed fill; the stale view adds the separate
        channel — the picture's filter desaturates and the hatch overlay is rendered."""
        fresh, stale, state = _fresh_and_stale(page, served)

        assert fresh and stale == fresh, "stale view recoloured or moved a cell"
        assert "saturate" in state["svgFilter"], f"no desaturation: {state['svgFilter']}"
        assert state["overlayDisplay"] != "none", "no hatched overlay"

    @rule("CIR-RENDER-STALE-MARK")
    def test_stale_marks_whole_picture(self, page: Page, served: str) -> None:
        """CIR-RENDER-STALE-MARK#stale-marks-whole-picture — `generated_at` past
        `stale_after_hours`: banner plus a page-wide stale treatment.

        Expected: banner visible; the whole picture is desaturated (the filter sits on
        the chart's <svg>, so it reaches every cell); the hatch overlay is rendered and
        its box contains every cell's box."""
        state = _view(page, served, "index-stale.html", 50)
        assert state["bannerVisible"], state
        assert "saturate" in state["svgFilter"], state
        assert state["overlayDisplay"] != "none", state
        cover = page.evaluate(_OVERLAY_COVERS_CELLS)
        assert cover["overlay"]["w"] > 0 and cover["overlay"]["h"] > 0, cover
        assert cover["uncovered"] == [], f"cells outside the overlay: {cover}"

    @rule("CIR-RENDER-STALE-MARK")
    def test_stale_stated_in_words(self, page: Page, served: str) -> None:
        """CIR-RENDER-STALE-MARK#stale-stated-in-words — stale page: "built <n> hours ago"
        in text, printed and read aloud.

        Read aloud: the banner is exposed in the accessibility tree as an alert carrying
        the words. Printed: under print media the stale page still yields exactly one A4
        sheet (CIR-RENDER-A4#print-single-a4-portrait) and the PDF's own text contains
        "built 50 hours ago"."""
        _view(page, served, "index-stale.html", 50)
        alert = page.get_by_role("alert")
        assert alert.count() == 1
        assert "built 50 hours ago" in alert.inner_text()

        page.emulate_media(media="print")
        pdf = page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
        reader = PdfReader(io.BytesIO(pdf))
        assert len(reader.pages) == 1, f"stale page printed {len(reader.pages)} sheets"
        text = " ".join(reader.pages[0].extract_text().split())
        assert "built 50 hours ago" in text, text[:400]

    @rule("CIR-RENDER-STALE-MARK")
    def test_stale_banner_keeps_one_screen(self, page: Page, served: str) -> None:
        """CIR-RENDER-STALE-MARK#stale-marks-whole-picture under
        CIR-RENDER-ONE-SCREEN#one-screen-reference — the banner lands inside the #app
        box: at 1280 × 800 with the banner up, no scrolling, and the furniture plus the
        banner are fully inside the viewport."""
        state = _view(page, served, "index-stale.html", 50)
        assert state["bannerVisible"], state
        for sw, cw, sh, ch in page.evaluate(_MEASURE_SCROLL):
            assert sw <= cw and sh <= ch, (sw, cw, sh, ch)
        for sel in (*FURNITURE, "#stale-banner"):
            box = page.locator(sel).bounding_box()
            assert box is not None and box["width"] > 0 and box["height"] > 0, sel
            assert box["x"] >= 0 and box["y"] >= 0, (sel, box)
            assert box["x"] + box["width"] <= 1280 and box["y"] + box["height"] <= 800, (sel, box)
