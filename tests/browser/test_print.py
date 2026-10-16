# Browser evidence for the A4 print rows — CIR-RENDER-A4 (specs/render/layout.md), system
# tier (⚖-R48). First slice: page count, declared margin, print chrome present. The
# remaining A4 rows (picture fills the sheet, colours preserved, ...) are the next slice.
#
# Every row is cited verbatim as CIR-<AREA>-<NAME>#<row-id> on the docstring's first line.
# The assertion is always a measurable property — a page count, a CSSOM value, a computed
# style — never a rendered image (CIR-PROC-BROWSER-EVIDENCE#screenshots-are-not-the-assertion).

from __future__ import annotations

import io

import pytest
from playwright.sync_api import Page
from pypdf import PdfReader

pytestmark = pytest.mark.browser

# CIR-RENDER-A4#print-chrome-complete: "ring key, legend, generated-at stamp and text
# alternative all present". The text alternative is `<details id="a11y-table">` holding
# the `<table>` (bake/render.py `_render_a11y_table`, CIR-RENDER-A11Y-TABLE).
PRINT_CHROME = ("#ring-key", "#legend", "#stamp", "#a11y-table", "#a11y-table table")

_PAGE_RULE_MARGINS = """() => {
  const found = [];
  const walk = (rules) => {
    for (const r of rules) {
      if (r instanceof CSSPageRule) found.push(r.style.margin);
      else if (r.cssRules) walk(r.cssRules);   // @media print { @page {...} } nests
    }
  };
  for (const sheet of document.styleSheets) walk(sheet.cssRules);
  return found;
}"""

_COMPUTED = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const cs = getComputedStyle(el);
  return {display: cs.display, visibility: cs.visibility};
}"""


class TestPrintA4:
    """CIR-RENDER-A4 — one sheet from the browser's print dialog."""

    def test_print_single_a4_portrait(self, page: Page, served: str) -> None:
        """CIR-RENDER-A4#print-single-a4-portrait — fixture config printed to A4
        portrait: exactly 1 page.

        Expected from the contract (⚖-R39): the page declares `@page { size: A4
        portrait; margin: 10mm }`, so a print with the CSS page size preferred and
        backgrounds kept yields a PDF whose page count is exactly 1 — counted by
        pypdf, not eyeballed."""
        page.goto(f"{served}/index.html")
        page.emulate_media(media="print")
        pdf = page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
        pages = len(PdfReader(io.BytesIO(pdf)).pages)
        assert pages == 1, f"print produced {pages} A4 pages, expected exactly 1"

    def test_print_margins_are_declared(self, page: Page, served: str) -> None:
        """CIR-RENDER-A4#print-margins-are-declared — printed page has a 10 mm page
        margin, not the browser default.

        Expected: walking every stylesheet's cssRules (recursing through @media)
        finds at least one CSSPageRule, and every one of them declares
        `margin: 10mm` (⚖-R39 rules the number). No @page rule at all is RED."""
        page.goto(f"{served}/index.html")
        margins = page.evaluate(_PAGE_RULE_MARGINS)
        assert margins, "no @page rule in any stylesheet — the browser default margin applies"
        assert all(m == "10mm" for m in margins), f"@page margins declared: {margins}"

    def test_print_chrome_complete(self, page: Page, served: str) -> None:
        """CIR-RENDER-A4#print-chrome-complete — printed output: ring key, legend,
        generated-at stamp and text alternative all present.

        Expected: under print media emulation each element's computed `display` is
        not `none` and `visibility` is not `hidden` — the print stylesheet hides only
        `.detail-idle` (bake/render.py), none of these."""
        page.goto(f"{served}/index.html")
        page.emulate_media(media="print")
        for selector in PRINT_CHROME:
            cs = page.evaluate(_COMPUTED, selector)
            assert cs is not None, f"{selector} is not in the page"
            assert cs["display"] != "none", f"{selector} is display:none under print: {cs}"
            assert cs["visibility"] != "hidden", f"{selector} is hidden under print: {cs}"
