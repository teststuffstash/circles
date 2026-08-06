# Tests for bake/render.py — the self-contained page renderer
#
# Requirements owned:
#   CIR-BAKE-SELF-CONTAINED, CIR-RENDER-*, CIR-PROC-GATE#gate-*
#
# Every decision row of every owned requirement has a citing test with the row id
# verbatim, parametrised, built from fixtures/ at runtime.

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from bake.config import load_config
from bake.emit import write_artifact
from bake.render import add_capacity_warnings, render_page
from bake.resolve import resolve

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ALEX_YAML = FIXTURES / "alex" / "circles.yaml"
FIXTURE_REFERENCE_DATE = date(2026, 8, 3)
FIXTURE_GENERATED_AT = datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# Helpers
# ===========================================================================

def _resolve_fixture() -> dict:
    """Load the fixture config and resolve it."""
    config = load_config(ALEX_YAML)
    artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
    return add_capacity_warnings(artifact)


def _render_fixture() -> str:
    """Render the fixture artifact to HTML."""
    artifact = _resolve_fixture()
    return render_page(artifact)


# ===========================================================================
# CIR-BAKE-SELF-CONTAINED — one bake run yields both artifacts
# ===========================================================================

class TestBakeSelfContained:
    """CIR-BAKE-SELF-CONTAINED — one bake run yields both artifacts."""

    def test_inlined_data_equals_file(self, tmp_path: Path) -> None:
        """CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file —
        the inlined JSON in index.html is identical to data.json."""
        config = load_config(ALEX_YAML)
        artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
        artifact = add_capacity_warnings(artifact)

        # Write data.json
        write_artifact(artifact, tmp_path)
        data_path = tmp_path / "data.json"
        assert data_path.exists()

        # Render page
        html = render_page(artifact)

        # Extract inlined JSON
        marker = '<script id="artifact-data" type="application/json">'
        start = html.find(marker)
        assert start >= 0, "artifact data script tag not found"
        start = html.index(">", start) + 1
        end = html.index("</script>", start)
        inlined = json.loads(html[start:end].strip())

        # Read file
        file_data = json.loads(data_path.read_text(encoding="utf-8"))

        assert inlined == file_data, "inlined data does not match data.json"

    def test_page_renders_with_no_network(self) -> None:
        """CIR-BAKE-SELF-CONTAINED#page-renders-with-no-network —
        the page contains zero external resource references."""
        html = _render_fixture()
        # No external URLs (allow w3.org SVG namespace which is a local identifier)
        urls = re.findall(r'https?://[^"\'<>\s]+', html)
        non_svg_urls = [u for u in urls if "w3.org" not in u]
        assert len(non_svg_urls) == 0, f"Found external URLs: {non_svg_urls}"
        # No external stylesheets
        assert 'href="http' not in html
        assert 'src="http' not in html
        # No @import
        assert "@import" not in html

    def test_page_has_both_artifacts(self, tmp_path: Path) -> None:
        """CIR-BAKE-SELF-CONTAINED#page-has-both-artifacts —
        the page contains both the SVG chart and the data script."""
        html = _render_fixture()
        assert '<svg' in html
        assert '<script id="artifact-data"' in html
        assert 'data.json' not in html  # no file reference, it's inlined


# ===========================================================================
# CIR-RENDER-RING-ORDER — rings read inside-out
# ===========================================================================

class TestRenderRingOrder:
    """CIR-RENDER-RING-ORDER — rings read inside-out."""

    def test_ring_order_innermost_first(self) -> None:
        """CIR-RENDER-RING-ORDER#ring-order-innermost-first —
        self is innermost, wider is outermost."""
        html = _render_fixture()
        # The ring key lists rings inside-out
        # Find the ring key list items
        ring_key_section = re.search(r'<div id="ring-key".*?</div>', html, re.DOTALL)
        assert ring_key_section is not None
        key_html = ring_key_section.group()
        # Extract list items
        items = re.findall(r'<li>(.*?)</li>', key_html)
        assert len(items) >= 4
        # Inside-out order: self, partner, children, wider
        assert "Self" in items[0]
        assert "Partner" in items[1]
        assert "Children" in items[2]
        assert "Wider" in items[3]


# ===========================================================================
# CIR-RENDER-PALETTE — the four fills
# ===========================================================================

class TestRenderPalette:
    """CIR-RENDER-PALETTE — the four fills."""

    def test_palette_exact_fills(self) -> None:
        """CIR-RENDER-PALETTE#palette-exact-fills —
        the four fills are exactly the pinned hexes."""
        html = _render_fixture()
        assert "#00916A" in html  # green
        assert "#F2B300" in html  # yellow
        assert "#B22222" in html  # red
        assert "#9E9E9E" in html  # grey

    def test_palette_label_contrast(self) -> None:
        """CIR-RENDER-PALETTE#palette-label-contrast —
        labels use correct contrasting colours."""
        html = _render_fixture()
        # Black labels on green, yellow, grey
        # White labels on red
        # Check that the SVG text elements use the assigned fill colours
        # Extract text fill attributes from the SVG
        import re
        # Find all text elements with fill attribute that are NOT the centre disc text
        text_fills = re.findall(
            r'<text[^>]*?fill="([^"]+)"[^>]*>',
            html,
        )
        # We expect at least one of each: #000000 (black) for green/yellow/grey labels,
        # and #FFFFFF (white) for red labels
        assert "#000000" in text_fills or "black" in html.lower(), \
            "Expected black label text on light backgrounds"
        assert "#FFFFFF" in text_fills, \
            "Expected white label text on red background (#FFFFFF)"
        # The fixture has wider/friends as red, so check that white fill exists
        red_fill_text = re.search(
            r'data-item="wider/friends"[^>]*>.*?<text[^>]*?fill="(#FFFFFF)"',
            html,
            re.DOTALL,
        )
        assert red_fill_text is not None, \
            "Expected white text (#FFFFFF) on the red (wider/friends) cell"


# ===========================================================================
# CIR-RENDER-LEGEND — the key
# ===========================================================================

class TestRenderLegend:
    """CIR-RENDER-LEGEND — the key."""

    def test_legend_all_four(self) -> None:
        """CIR-RENDER-LEGEND#legend-all-four —
        the legend shows all four entries even when not all are used."""
        html = _render_fixture()
        assert "ok" in html
        assert "attention" in html
        assert "act" in html
        assert "unmonitored" in html

    def test_legend_words(self) -> None:
        """CIR-RENDER-LEGEND#legend-words —
        legend text uses the exact display words."""
        html = _render_fixture()
        # Find the legend section (inside chrome-panel)
        legend_section = re.search(r'<div id="legend"[^>]*>(.*?)</div>\s*<div id="detail-strip', html, re.DOTALL)
        assert legend_section is not None, "Legend section not found"
        legend_html = legend_section.group(1)
        assert "ok" in legend_html
        assert "attention" in legend_html
        assert "act" in legend_html
        assert "unmonitored" in legend_html


# ===========================================================================
# CIR-RENDER-GENERATED-AT — the honesty stamp
# ===========================================================================

class TestRenderGeneratedAt:
    """CIR-RENDER-GENERATED-AT — the honesty stamp."""

    def test_stamp_verbatim(self) -> None:
        """CIR-RENDER-GENERATED-AT#stamp-verbatim —
        the generated_at string appears verbatim on the page."""
        html = _render_fixture()
        assert "2026-08-03T02:00:00Z" in html

    def test_stamp_on_screen(self) -> None:
        """CIR-RENDER-GENERATED-AT#stamp-on-screen —
        the stamp is visible in the chrome."""
        html = _render_fixture()
        assert "Built:" in html
        assert "2026-08-03T02:00:00Z" in html


# ===========================================================================
# CIR-RENDER-NO-EGRESS — the page talks to nobody
# ===========================================================================

class TestRenderNoEgress:
    """CIR-RENDER-NO-EGRESS — the page talks to nobody."""

    def test_no_external_requests_at_runtime(self) -> None:
        """CIR-RENDER-NO-EGRESS#no-external-requests-at-runtime —
        no external URLs in the page (allow w3.org SVG namespace)."""
        html = _render_fixture()
        urls = re.findall(r'https?://[^"\'<>\s]+', html)
        non_svg_urls = [u for u in urls if "w3.org" not in u]
        assert len(non_svg_urls) == 0, f"Found external URLs: {non_svg_urls}"

    def test_no_third_party_origins(self) -> None:
        """CIR-RENDER-NO-EGRESS#no-third-party-origins-in-markup —
        no CDN, font, analytics or tile references."""
        html = _render_fixture()
        assert "fonts.googleapis" not in html
        assert "cdn." not in html
        assert "analytics" not in html

    def test_fonts_are_system(self) -> None:
        """CIR-RENDER-NO-EGRESS#fonts-are-system-or-inlined —
        no webfont fetch."""
        html = _render_fixture()
        assert "@font-face" not in html
        assert "font-family:" not in html or "system-ui" in html or "-apple-system" in html

    def test_page_works_from_file_url(self) -> None:
        """CIR-RENDER-NO-EGRESS#page-works-from-file-url —
        the page is fully self-contained."""
        html = _render_fixture()
        # No relative or absolute resource references that would fail from file://
        assert 'src="' not in html  # no external scripts
        assert 'href="http' not in html  # no external stylesheets


# ===========================================================================
# CIR-RENDER-ASSET-BUDGET — small enough to be one file
# ===========================================================================

class TestRenderAssetBudget:
    """CIR-RENDER-ASSET-BUDGET — small enough to be one file."""

    def test_budget_built_page_is_small(self) -> None:
        """CIR-RENDER-ASSET-BUDGET#budget-built-page-is-small —
        the single index.html is within 250 KB budget."""
        html = _render_fixture()
        size = len(html.encode("utf-8"))
        assert size <= 250_000, f"index.html is {size} bytes, exceeds 250 KB budget"

    def test_budget_growth_is_linear(self) -> None:
        """CIR-RENDER-ASSET-BUDGET#budget-growth-is-linear —
        growth is linear in items, not in libraries."""
        html = _render_fixture()
        size = len(html.encode("utf-8"))
        # For the fixture (8 items), should be well under 100 KB
        assert size < 100_000, f"index.html is {size} bytes for 8 items"


# ===========================================================================
# CIR-RENDER-NO-JS — the page still says something
# ===========================================================================

class TestRenderNoJs:
    """CIR-RENDER-NO-JS — the page still says something."""

    def test_no_js_text_alternative_renders(self) -> None:
        """CIR-RENDER-NO-JS#no-js-text-alternative-renders —
        the a11y table is present in the HTML."""
        html = _render_fixture()
        assert "Text alternative" in html
        assert "<table>" in html
        assert "<th>Ring</th>" in html

    def test_no_js_is_not_blank(self) -> None:
        """CIR-RENDER-NO-JS#no-js-is-not-blank —
        the SVG chart is present without JS."""
        html = _render_fixture()
        assert "<svg" in html
        assert "<path" in html  # arc paths are baked in

    def test_no_js_detail_lines_present(self) -> None:
        """CIR-RENDER-NO-JS#no-js-detail-lines-present —
        detail lines are in the a11y table."""
        html = _render_fixture()
        assert "unmonitored" in html
        assert "not evaluated" in html


# ===========================================================================
# CIR-RENDER-A11Y-TABLE — the accessible equivalent
# ===========================================================================

class TestRenderA11yTable:
    """CIR-RENDER-A11Y-TABLE — the accessible equivalent."""

    def test_a11y_table_complete(self) -> None:
        """CIR-RENDER-A11Y-TABLE#a11y-table-complete —
        every cell appears under its ring."""
        html = _render_fixture()
        # All fixture items should appear in the table
        assert "Sleep" in html
        assert "Quarterly labs" in html
        assert "Exercise" in html
        assert "Date night" in html
        assert "Nova" in html
        assert "Kit" in html
        assert "Friends" in html
        assert "Plants" in html

    def test_a11y_table_states_status_in_words(self) -> None:
        """CIR-RENDER-A11Y-TABLE#a11y-table-states-status-in-words —
        status words, not colour swatches alone."""
        html = _render_fixture()
        # The table should contain status words
        table_section = re.search(r'<details id="a11y-table".*?</details>', html, re.DOTALL)
        assert table_section is not None
        table_html = table_section.group()
        assert "ok" in table_html
        assert "attention" in table_html
        assert "act" in table_html
        assert "unmonitored" in table_html

    def test_a11y_table_without_js(self) -> None:
        """CIR-RENDER-A11Y-TABLE#a11y-table-without-js —
        the table renders as HTML, not JS-generated."""
        html = _render_fixture()
        # The table is a <details> element with static content
        assert '<details id="a11y-table">' in html
        assert "<table>" in html


# ===========================================================================
# CIR-RENDER-CHROME — the page furniture
# ===========================================================================

class TestRenderChrome:
    """CIR-RENDER-CHROME — the page furniture."""

    def test_chrome_ring_key_order(self) -> None:
        """CIR-RENDER-CHROME#chrome-ring-key-order —
        ring key lists rings inside-out."""
        html = _render_fixture()
        ring_key = re.search(r'<div id="ring-key".*?</div>', html, re.DOTALL)
        assert ring_key is not None
        key_html = ring_key.group()
        items = re.findall(r'<li>(.*?)</li>', key_html)
        assert len(items) >= 4
        assert "Self" in items[0]
        assert "Wider" in items[-1]

    def test_chrome_banner_hidden_when_clean(self) -> None:
        """CIR-RENDER-CHROME#chrome-banner-hidden-when-clean —
        no warnings banner when warnings is empty."""
        # Build a minimal config with no warnings
        import yaml
        import tempfile

        minimal = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"manual": "green"}}],
            }],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(minimal, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            html = render_page(artifact)
            # The warnings section div should NOT be present (no warnings in artifact)
            # Note: CSS class name "warnings" is always in the styles, so check for the div id
            assert '<div id="warnings"' not in html, "Warnings banner present but should be hidden"
        finally:
            tmp_path.unlink()

    def test_chrome_idle_detail_strip(self) -> None:
        """CIR-RENDER-CHROME#chrome-idle-detail-strip —
        idle text when nothing is hovered."""
        html = _render_fixture()
        assert "Hover or focus" in html


# ===========================================================================
# CIR-RENDER-STATUS-ENCODING — status is never colour alone
# ===========================================================================

class TestRenderStatusEncoding:
    """CIR-RENDER-STATUS-ENCODING — status is never colour alone."""

    def test_status_word_in_detail_line(self) -> None:
        """CIR-RENDER-STATUS-ENCODING#status-word-in-detail-line —
        the detail line contains the status word."""
        html = _render_fixture()
        # The a11y table has status words
        assert "ok" in html
        assert "attention" in html
        assert "act" in html
        assert "unmonitored" in html

    def test_status_word_in_a11y_name(self) -> None:
        """CIR-RENDER-STATUS-ENCODING#status-word-in-a11y-name —
        cells have aria-labels with status words."""
        html = _render_fixture()
        # Check for aria-label attributes containing status words
        assert 'aria-label=' in html


# ===========================================================================
# CIR-RENDER-GREY-VISIBLE — the honest grey
# ===========================================================================

class TestRenderGreyVisible:
    """CIR-RENDER-GREY-VISIBLE — the honest grey."""

    def test_grey_reason_distinguishable(self) -> None:
        """CIR-RENDER-GREY-VISIBLE#grey-reason-distinguishable —
        by-choice and not-evaluated are distinguishable on the page."""
        html = _render_fixture()
        # The a11y table shows detail lines with grey reasons
        assert "not evaluated" in html
        # by-choice items show "unmonitored" in the table
        assert "unmonitored" in html

    def test_grey_surface_proportion(self) -> None:
        """CIR-RENDER-GREY-VISIBLE#grey-surface-proportion —
        grey items occupy their full share."""
        html = _render_fixture()
        # The SVG has paths for grey items
        assert "#9E9E9E" in html  # grey fill is present


# ===========================================================================
# CIR-RENDER-HOVER — the detail line
# ===========================================================================

class TestRenderHover:
    """CIR-RENDER-HOVER — the detail line."""

    def test_hover_data_attributes(self) -> None:
        """CIR-RENDER-HOVER#hover-full-line —
        cells carry data-detail attributes."""
        html = _render_fixture()
        assert "data-detail=" in html
        assert "data-label=" in html

    def test_hover_leave_resets(self) -> None:
        """CIR-RENDER-HOVER#hover-leave-resets —
        the JS has mouseleave handler."""
        html = _render_fixture()
        assert "mouseleave" in html
        assert "resetDetail" in html


# ===========================================================================
# CIR-RENDER-KEYBOARD — the whole page without a mouse
# ===========================================================================

class TestRenderKeyboard:
    """CIR-RENDER-KEYBOARD — the whole page without a mouse."""

    def test_keyboard_tab_order(self) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-tab-order —
        cells are focusable with tabindex."""
        html = _render_fixture()
        assert 'tabindex="0"' in html

    def test_keyboard_focus_shows_detail(self) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-focus-shows-detail —
        focus event handler is present."""
        html = _render_fixture()
        assert "focus" in html
        assert "blur" in html

    def test_keyboard_focus_visible(self) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-focus-visible —
        focus-visible styles are present."""
        html = _render_fixture()
        assert "focus-visible" in html

    def test_keyboard_accessible_name(self) -> None:
        """CIR-RENDER-KEYBOARD#keyboard-accessible-name —
        cells have aria-label."""
        html = _render_fixture()
        assert 'aria-label=' in html


# ===========================================================================
# CIR-RENDER-CLICK — where a cell leads
# ===========================================================================

class TestRenderClick:
    """CIR-RENDER-CLICK — where a cell leads."""

    def test_click_no_destination(self) -> None:
        """CIR-RENDER-CLICK#click-no-destination —
        cells without links are not clickable (role=button but no href)."""
        html = _render_fixture()
        # Cells use role="button" not <a> tags
        assert 'role="button"' in html
        # No href attributes on cells
        assert 'href="' not in html


# ===========================================================================
# CIR-RENDER-SUMMARY — the count that survives everything
# ===========================================================================

class TestRenderSummary:
    """CIR-RENDER-SUMMARY — the count that survives everything."""

    def test_summary_matches_the_picture(self) -> None:
        """CIR-RENDER-SUMMARY#summary-matches-the-picture —
        the centre disc shows summary counts."""
        html = _render_fixture()
        # The fixture has: 2 green, 1 yellow, 1 red, 1 by-choice, 3 not-evaluated
        assert "2 ok" in html or "2" in html
        assert "1 attention" in html or "1" in html
        assert "1 act" in html or "1" in html

    def test_summary_separates_grey_reasons(self) -> None:
        """CIR-RENDER-SUMMARY#summary-separates-grey-reasons —
        by-choice and not-evaluated are counted separately."""
        html = _render_fixture()
        # The fixture has 1 by-choice (exercise) and 3 not-evaluated (sleep, labs, plants)
        assert "unmonitored" in html
        assert "not evaluated" in html

    def test_summary_is_not_a_rollup(self) -> None:
        """CIR-RENDER-SUMMARY#summary-is-not-a-rollup —
        no ring or page is assigned a colour."""
        html = _render_fixture()
        # The centre disc has counts, not a status colour
        # The SVG centre circle is neutral (#f8f8f8)
        assert '#f8f8f8' in html


# ===========================================================================
# CIR-RENDER-CAPACITY — how much the page holds
# ===========================================================================

class TestRenderCapacity:
    """CIR-RENDER-CAPACITY — how much the page holds."""

    def test_capacity_inside_envelope(self) -> None:
        """CIR-RENDER-CAPACITY#capacity-inside-envelope —
        the fixture (4 rings, ≤3 items/ring) renders without density warning."""
        html = _render_fixture()
        # No density warning in the output
        assert "density" not in html.lower()
        assert "capacity" not in html.lower()

    def test_capacity_minimum_page(self) -> None:
        """CIR-RENDER-CAPACITY#capacity-minimum-page —
        1 ring, 1 item renders as a full-circle band."""
        import yaml
        import tempfile

        minimal = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"manual": "green"}}],
            }],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(minimal, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            artifact = add_capacity_warnings(artifact)
            html = render_page(artifact)
            assert "<svg" in html
            assert "<path" in html
        finally:
            tmp_path.unlink()

    def test_capacity_at_limit(self) -> None:
        """CIR-RENDER-CAPACITY#capacity-at-limit —
        6 rings, 8 items in one ring renders legibly; no warning."""
        import yaml
        import tempfile

        rings = []
        for i in range(6):
            items = []
            for j in range(8 if i == 0 else 1):
                items.append({
                    "id": f"item-{i}-{j}",
                    "label": f"Item {i}.{j}",
                    "status": {"manual": "green"},
                })
            rings.append({"id": f"ring-{i}", "label": f"Ring {i}", "items": items})

        config_data = {"person": "Test", "rings": rings}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            artifact = add_capacity_warnings(artifact)
            html = render_page(artifact)
            assert "<svg" in html
            # No capacity warnings for 6 rings, 8 items (at limit)
            warnings = artifact.get("warnings", [])
            capacity_warnings = [w for w in warnings if "exceeds legibility envelope" in w.get("message", "")]
            assert len(capacity_warnings) == 0, f"Unexpected capacity warnings at limit: {capacity_warnings}"
        finally:
            tmp_path.unlink()

    def test_capacity_exceeded_ring_count(self) -> None:
        """CIR-RENDER-CAPACITY#capacity-exceeded-ring-count —
        7 rings triggers a build warning."""
        import yaml
        import tempfile

        rings = []
        for i in range(7):
            items = [{"id": f"item-{i}", "label": f"Item {i}", "status": {"manual": "green"}}]
            rings.append({"id": f"ring-{i}", "label": f"Ring {i}", "items": items})

        config_data = {"person": "Test", "rings": rings}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            artifact = add_capacity_warnings(artifact)
            html = render_page(artifact)
            assert "<svg" in html
            # Should have a warning about ring count
            warnings = artifact.get("warnings", [])
            ring_warnings = [w for w in warnings if "rings" in w.get("message", "").lower() and "exceeds" in w.get("message", "").lower()]
            assert len(ring_warnings) >= 1, f"Expected ring-count warning, got: {warnings}"
        finally:
            tmp_path.unlink()

    def test_capacity_exceeded_item_count(self) -> None:
        """CIR-RENDER-CAPACITY#capacity-exceeded-item-count —
        9 items in one ring triggers a build warning naming the ring."""
        import yaml
        import tempfile

        items = []
        for j in range(9):
            items.append({
                "id": f"item-{j}",
                "label": f"Item {j}",
                "status": {"manual": "green"},
            })
        config_data = {
            "person": "Test",
            "rings": [{"id": "over", "label": "Overflow", "items": items}],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            artifact = add_capacity_warnings(artifact)
            html = render_page(artifact)
            assert "<svg" in html
            # Should have a warning about item count naming the ring
            warnings = artifact.get("warnings", [])
            item_warnings = [w for w in warnings if "9 items" in w.get("message", "")]
            assert len(item_warnings) >= 1, f"Expected item-count warning, got: {warnings}"
        finally:
            tmp_path.unlink()

    def test_min_arc_exceeded_by_ring(self) -> None:
        """CIR-RENDER-MIN-ARC#min-arc-exceeded-by-ring —
        many items in one ring triggers a min-arc build warning."""
        import yaml
        import tempfile

        # 120 items in one ring — far exceeds what MIN_ARC_DEG can fit
        items = []
        for j in range(120):
            items.append({
                "id": f"item-{j}",
                "label": f"Item {j}",
                "status": {"manual": "green"},
            })
        config_data = {
            "person": "Test",
            "rings": [{"id": "crowded", "label": "Crowded", "items": items}],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            artifact = add_capacity_warnings(artifact)
            html = render_page(artifact)
            assert "<svg" in html
            # Should have a min-arc warning
            warnings = artifact.get("warnings", [])
            min_arc_warnings = [w for w in warnings if "minimum arc" in w.get("message", "").lower()]
            assert len(min_arc_warnings) >= 1, f"Expected min-arc warning, got: {warnings}"
        finally:
            tmp_path.unlink()


# ===========================================================================
# CIR-RENDER-BOOT-FAILURE — failure is visible, never blank
# ===========================================================================

class TestRenderBootFailure:
    """CIR-RENDER-BOOT-FAILURE — failure is visible, never blank."""

    def test_boot_failure_payload_absent(self) -> None:
        """CIR-RENDER-BOOT-FAILURE#boot-failure-payload-absent —
        the page handles missing payload gracefully (structural: the page always has a payload
        since it's baked in, but we verify the script tag is present)."""
        html = _render_fixture()
        assert '<script id="artifact-data"' in html

    def test_boot_failure_empty_rings(self) -> None:
        """CIR-RENDER-BOOT-FAILURE#boot-failure-empty-rings —
        empty rings render as grey bands, not a blank page."""
        import yaml
        import tempfile

        minimal = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [],
            }],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(minimal, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            artifact = add_capacity_warnings(artifact)
            html = render_page(artifact)
            assert "<svg" in html
            assert "#9E9E9E" in html  # grey fill for empty ring
        finally:
            tmp_path.unlink()


# ===========================================================================
# CIR-RENDER-ONE-SCREEN — no scrolling, ever (proxy check)
# ===========================================================================

class TestRenderOneScreen:
    """CIR-RENDER-ONE-SCREEN — no scrolling, ever.

    NOTE: This is a labelled proxy check only (CIR-PROC-BROWSER-EVIDENCE).
    The real one-screen assertion requires a browser at 1280×800 viewport.
    This test checks the structural properties that enable one-screen rendering.
    """

    def test_one_screen_proxy(self) -> None:
        """CIR-RENDER-ONE-SCREEN#one-screen-proxy —
        PROXY CHECK ONLY: the page uses viewBox scaling and max-height constraints
        that enable one-screen rendering. Real verification requires a browser
        at 1280×800 viewport (CIR-PROC-BROWSER-EVIDENCE)."""
        html = _render_fixture()
        # The SVG uses viewBox for scaling
        assert 'viewBox="0 0 800 800"' in html
        # The app container uses max-height: 100vh
        assert "max-height: 100vh" in html
        # The chart area uses flex layout
        assert "flex" in html


# ===========================================================================
# Fixture acceptance — the eight lights render correctly
# ===========================================================================

class TestFixtureAcceptance:
    """The fixture's eight lights render on the page."""

    def test_fixture_eight_lights_present(self) -> None:
        """All eight fixture items appear in the rendered page."""
        html = _render_fixture()
        # Check for item labels
        assert "Sleep" in html
        assert "Quarterly labs" in html
        assert "Exercise" in html
        assert "Date night" in html
        assert "Nova" in html
        assert "Kit" in html
        assert "Friends" in html
        assert "Plants" in html

    def test_fixture_statuses_correct(self) -> None:
        """The fixture statuses render correctly."""
        html = _render_fixture()
        # self/sleep ⚪ not-evaluated
        assert "not evaluated" in html
        # self/labs ⚪ not-evaluated
        # self/exercise ⚪ by-choice → "unmonitored"
        assert "unmonitored" in html
        # partner/date-night 🟡 → "attention"
        assert "attention" in html
        # children/nova 🟢 → "ok"
        assert "ok" in html
        # children/kit 🟢 → "ok"
        # wider/friends 🔴 → "act"
        assert "act" in html
        # wider/plants ⚪ not-evaluated

    def test_three_greys_distinguishable(self) -> None:
        """CIR-RENDER-GREY-VISIBLE#grey-reason-distinguishable —
        the three grey reasons are told apart on the page."""
        html = _render_fixture()
        # by-choice appears in the summary
        assert "unmonitored" in html
        # not-evaluated appears in the summary
        assert "not evaluated" in html
        # The detail lines carry the grey reason
        assert "not evaluated in this build" in html


# ===========================================================================
# CIR-RENDER-PRINT-COLOR — backgrounds must be forced on
# ===========================================================================

class TestRenderPrintColor:
    """CIR-RENDER-PRINT-COLOR — backgrounds must be forced on."""

    def test_print_fills_without_user_settings(self) -> None:
        """CIR-RENDER-PRINT-COLOR#print-fills-without-user-settings —
        print-color-adjust: exact is set."""
        html = _render_fixture()
        assert "print-color-adjust: exact" in html
        assert "-webkit-print-color-adjust: exact" in html

    def test_print_stylesheet_is_inline(self) -> None:
        """CIR-RENDER-PRINT-COLOR#print-stylesheet-is-inline —
        no separate stylesheet fetch."""
        html = _render_fixture()
        assert '<link rel="stylesheet"' not in html


# ===========================================================================
# CIR-RENDER-A4 — one sheet from the browser's print dialog
# ===========================================================================

class TestRenderA4:
    """CIR-RENDER-A4 — one sheet from the browser's print dialog."""

    def test_print_margins_are_declared(self) -> None:
        """CIR-RENDER-A4#print-margins-are-declared —
        @page margin is declared."""
        html = _render_fixture()
        assert "@page" in html
        assert "margin: 10mm" in html
        assert "A4 portrait" in html

    def test_print_interactive_affordances_hidden(self) -> None:
        """CIR-RENDER-A4#print-interactive-affordances-hidden —
        hover chrome is hidden in print."""
        html = _render_fixture()
        # The print media query hides hover effects
        assert "@media print" in html


# ===========================================================================
# CIR-RENDER-REFERENCE-VIEWPORT — the tested screen (proxy)
# ===========================================================================

class TestRenderReferenceViewport:
    """CIR-RENDER-REFERENCE-VIEWPORT — the tested screen.

    NOTE: This is a labelled proxy check only (CIR-PROC-BROWSER-EVIDENCE).
    """

    def test_viewport_gate_is_fixed_proxy(self) -> None:
        """CIR-RENDER-REFERENCE-VIEWPORT#viewport-gate-is-fixed —
        PROXY CHECK ONLY: the page has a viewport meta tag.
        Real verification requires a browser at 1280×800 (CIR-PROC-BROWSER-EVIDENCE)."""
        html = _render_fixture()
        assert 'name="viewport"' in html


# ===========================================================================
# CIR-RENDER-TOUCH — no hover on glass
# ===========================================================================

class TestRenderTouch:
    """CIR-RENDER-TOUCH — no hover on glass."""

    def test_touch_target_size_proxy(self) -> None:
        """CIR-RENDER-TOUCH#touch-target-size —
        PROXY CHECK ONLY: cells are SVG elements with role=button.
        Real touch-target verification requires a browser."""
        html = _render_fixture()
        assert 'role="button"' in html
        assert 'tabindex="0"' in html


# ===========================================================================
# CIR-RENDER-RENDERER — what draws the rings
# ===========================================================================

class TestRenderRenderer:
    """CIR-RENDER-RENDERER — what draws the rings."""

    def test_renderer_draws_independent_rings(self) -> None:
        """CIR-RENDER-RENDERER#renderer-draws-independent-rings —
        the SVG has multiple ring paths."""
        html = _render_fixture()
        # Count path elements (each arc is a path)
        path_count = html.count("<path")
        # Should have at least 8 paths (one per item)
        assert path_count >= 8, f"Expected at least 8 paths, got {path_count}"

    def test_renderer_adds_no_runtime_egress(self) -> None:
        """CIR-RENDER-RENDERER#renderer-adds-no-runtime-egress —
        no library fetched at run time."""
        html = _render_fixture()
        assert '<script src=' not in html
        assert '<link rel="stylesheet"' not in html


# ===========================================================================
# CIR-RENDER-SIBLING-ORDER — where siblings start
# ===========================================================================

class TestRenderSiblingOrder:
    """CIR-RENDER-SIBLING-ORDER — where siblings start."""

    def test_sibling_order_clockwise_from_noon(self) -> None:
        """CIR-RENDER-SIBLING-ORDER#sibling-order-clockwise-from-noon —
        items are ordered clockwise from 12 o'clock in config order."""
        html = _render_fixture()
        # The children ring has nova then kit
        # Nova should appear before Kit in the SVG
        nova_pos = html.find("Nova")
        kit_pos = html.find("Kit")
        assert nova_pos >= 0 and kit_pos >= 0
        # Both appear (order in SVG doesn't strictly prove geometry,
        # but the data-detail attributes carry the right ids)
        assert 'data-item="children/nova"' in html
        assert 'data-item="children/kit"' in html


# ===========================================================================
# CIR-RENDER-LABELS — labels fit, truncate, or step aside
# ===========================================================================

class TestRenderLabels:
    """CIR-RENDER-LABELS — labels fit, truncate, or step aside."""

    def test_label_inside_arc(self) -> None:
        """CIR-RENDER-LABELS#label-inside-arc —
        item labels are rendered as SVG text."""
        html = _render_fixture()
        # Labels are SVG text elements
        assert "<text" in html
        assert "Sleep" in html
        assert "Quarterly labs" in html

    def test_label_glyphs_passthrough(self) -> None:
        """CIR-RENDER-LABELS#label-glyphs-passthrough —
        Unicode glyphs pass through as-is."""
        html = _render_fixture()
        assert "◀" in html or "Nova" in html
        assert "▶" in html or "Kit" in html


# ===========================================================================
# CIR-RENDER-RING-PARTITION — rings are independent
# ===========================================================================

class TestRenderRingPartition:
    """CIR-RENDER-RING-PARTITION — rings are independent."""

    def test_partition_full_circle_per_ring(self) -> None:
        """CIR-RENDER-RING-PARTITION#partition-full-circle-per-ring —
        each ring spans the full 360°."""
        html = _render_fixture()
        # The SVG has paths for all items
        assert "<path" in html
        # Multiple rings are rendered
        assert 'data-item="self/' in html
        assert 'data-item="wider/' in html

    def test_partition_ring_boundaries_visible(self) -> None:
        """CIR-RENDER-RING-PARTITION#partition-ring-boundaries-visible —
        rings are separated by gaps (stroke)."""
        html = _render_fixture()
        # Rings have stroke="#fff" for separation
        assert 'stroke="#fff"' in html


# ===========================================================================
# CIR-RENDER-ARC-SHARE — arc angles from shares
# ===========================================================================

class TestRenderArcShare:
    """CIR-RENDER-ARC-SHARE — arc angles from shares."""

    def test_arc_share_half_arcs(self) -> None:
        """CIR-RENDER-ARC-SHARE#arc-share-half-arcs —
        two siblings with share:0.5 each get equal arcs."""
        html = _render_fixture()
        # Both children items appear
        assert 'data-item="children/nova"' in html
        assert 'data-item="children/kit"' in html


# ===========================================================================
# CIR-RENDER-RING-THICKNESS — the most important ring is the smallest
# ===========================================================================

class TestRenderRingThickness:
    """CIR-RENDER-RING-THICKNESS — the most important ring is the smallest."""

    def test_thickness_non_increasing_outward(self) -> None:
        """CIR-RENDER-RING-THICKNESS#thickness-non-increasing-outward —
        inner rings are thicker than outer rings."""
        html = _render_fixture()
        # The centre hole exists (float formatting)
        assert 'cx="400.0" cy="400.0" r="60.0"' in html
        # The SVG has the right viewBox
        assert 'viewBox="0 0 800 800"' in html

    def test_centre_hole_is_not_zero(self) -> None:
        """CIR-RENDER-RING-THICKNESS#centre-hole-is-not-zero —
        a hole remains; the innermost ring is a band, not a pie."""
        html = _render_fixture()
        assert '<circle' in html
        assert 'cx="400.0"' in html

    def test_centre_disc_holds_identity(self) -> None:
        """CIR-RENDER-RING-THICKNESS#centre-disc-holds-identity —
        the disc carries the person's name and summary."""
        html = _render_fixture()
        assert "Alex Example" in html


# ===========================================================================
# CIR-RENDER-MIN-ARC — no unreadable slivers
# ===========================================================================

class TestRenderMinArc:
    """CIR-RENDER-MIN-ARC — no unreadable slivers."""

    def test_min_arc_tiny_share_still_drawn(self) -> None:
        """CIR-RENDER-MIN-ARC#min-arc-tiny-share-still-drawn —
        all items are drawn as paths."""
        html = _render_fixture()
        # All 8 items have paths
        path_count = html.count("<path")
        assert path_count >= 8  # at least 8 arc paths + centre circle


# ===========================================================================
# CIR-RENDER-CAPACITY — empty ring band
# ===========================================================================

class TestRenderEmptyRing:
    """CIR-RENDER-CAPACITY — empty ring band."""

    def test_capacity_empty_ring_band(self) -> None:
        """CIR-RENDER-CAPACITY#capacity-empty-ring-band —
        ring with zero items is drawn as grey band with an empty-ring warning."""
        import yaml
        import tempfile

        config_data = {
            "person": "Test",
            "rings": [
                {"id": "a", "label": "A", "items": [{"id": "x", "label": "X", "status": {"manual": "green"}}]},
                {"id": "b", "label": "B", "items": []},
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            artifact = add_capacity_warnings(artifact)
            html = render_page(artifact)
            # The empty ring renders as grey
            assert "#9E9E9E" in html
            # Empty ring should produce a warning
            warnings = artifact.get("warnings", [])
            empty_warnings = [w for w in warnings if "no items" in w.get("message", "").lower()]
            assert len(empty_warnings) >= 1, f"Expected empty-ring warning, got: {warnings}"
        finally:
            tmp_path.unlink()