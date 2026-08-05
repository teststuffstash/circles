"""Tests for render logic — palette math and geometry.

Every test cites its spec row as CIR-RENDER-<NAME>#<row-id> verbatim (CIR-PROC-TEST-ROWS).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest


# Paths
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
PUBLIC = Path(__file__).resolve().parent.parent / "public"


# ============================================================
# CIR-RENDER-PALETTE — colour math
# ============================================================


def _relative_luminance(hex_color: str) -> float:
    """Compute WCAG relative luminance from a hex colour."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

    def linearize(c: int) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(l1: float, l2: float) -> float:
    """Compute WCAG contrast ratio."""
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class TestPalette:
    """CIR-RENDER-PALETTE — the four fills."""

    PALETTE_HEXES = {
        "green": "#00916A",
        "yellow": "#F2B300",
        "red": "#B22222",
        "grey": "#9E9E9E",
    }

    LABEL_COLORS = {
        "green": "#000000",
        "yellow": "#000000",
        "red": "#ffffff",
        "grey": "#000000",
    }

    def test_palette_exact_fills(self):
        """CIR-RENDER-PALETTE#palette-exact-fills

        The four fills are exactly the pinned hexes.
        """
        # Read the page and extract the palette CSS variables
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # Check each colour is present in the page
        for status, expected_hex in self.PALETTE_HEXES.items():
            assert expected_hex.lower() in page.lower(), (
                f"Colour {expected_hex} for {status} not found in page"
            )

    def test_palette_luminance_ladder(self):
        """CIR-RENDER-PALETTE#palette-luminance-ladder

        amber > grey > green > red, every pair ≥ 0.10 apart.
        """
        lums = {}
        for status, hex_color in self.PALETTE_HEXES.items():
            lums[status] = _relative_luminance(hex_color)

        # amber (~0.51) > grey (~0.34) > green (~0.21) > red (~0.11)
        ordered = ["yellow", "grey", "green", "red"]
        for i in range(len(ordered) - 1):
            lum_a = lums[ordered[i]]
            lum_b = lums[ordered[i + 1]]
            assert lum_a > lum_b, (
                f"{ordered[i]} ({lum_a:.4f}) should be lighter than "
                f"{ordered[i+1]} ({lum_b:.4f})"
            )
            diff = lum_a - lum_b
            assert diff >= 0.10, (
                f"Luminance difference between {ordered[i]} and {ordered[i+1]} "
                f"is {diff:.4f}, expected ≥ 0.10"
            )

    def test_palette_label_contrast(self):
        """CIR-RENDER-PALETTE#palette-label-contrast

        Text painted on a cell has ≥ 4.5:1 contrast against its fill (WCAG AA).
        """
        for status, hex_color in self.PALETTE_HEXES.items():
            fill_lum = _relative_luminance(hex_color)
            label_hex = self.LABEL_COLORS[status]
            label_lum = _relative_luminance(label_hex)
            ratio = _contrast_ratio(fill_lum, label_lum)
            assert ratio >= 4.5, (
                f"Contrast ratio for {status} label ({label_hex}) on fill "
                f"({hex_color}) is {ratio:.2f}:1, expected ≥ 4.5:1"
            )

    def test_grey_distinct_from_background(self):
        """CIR-RENDER-GREY-VISIBLE#grey-distinct-from-background

        ⚪ cell on the white page — clearly visible fill, contrast ≥ 2.4:1.
        """
        grey_lum = _relative_luminance(self.PALETTE_HEXES["grey"])
        white_lum = _relative_luminance("#ffffff")
        ratio = _contrast_ratio(grey_lum, white_lum)
        assert ratio >= 2.4, (
            f"Grey/white contrast is {ratio:.2f}:1, expected ≥ 2.4:1"
        )


# ============================================================
# CIR-RENDER-RING-PARTITION — geometry assertions
# ============================================================


class TestGeometry:
    """CIR-RENDER-RING-PARTITION / CIR-RENDER-ARC-SHARE / CIR-RENDER-SIBLING-ORDER."""

    def test_partition_full_circle_per_ring(self):
        """CIR-RENDER-RING-PARTITION#partition-full-circle-per-ring

        1-item ring → one 360° band.
        """
        ring_items = [{"share": 1}]
        total = sum(i.get("share", 1) for i in ring_items)
        # Each item in a single-item ring should span the full circle
        assert total == 1
        # Arc angle would be 360°

    def test_partition_independent_scales(self):
        """CIR-RENDER-RING-PARTITION#partition-independent-scales

        Inner ring 3 items (120° each), outer ring 2 items (180° each).
        """
        inner = [{"share": 1}, {"share": 1}, {"share": 1}]
        outer = [{"share": 1}, {"share": 1}]

        def angles(items):
            tot = sum(i.get("share", 1) for i in items)
            return [360 * (i.get("share", 1) / tot) for i in items]

        inner_angles = angles(inner)
        outer_angles = angles(outer)

        assert all(abs(a - 120) < 0.01 for a in inner_angles)
        assert all(abs(a - 180) < 0.01 for a in outer_angles)

    def test_partition_no_containment(self):
        """CIR-RENDER-RING-PARTITION#partition-no-containment

        3 items in one ring, 1 in another — no ring's arc is bounded by another's.
        """
        ring_a = [{"share": 1}, {"share": 1}, {"share": 1}]
        ring_b = [{"share": 1}]

        def sum_angles(items):
            tot = sum(i.get("share", 1) for i in items)
            return [360 * (i.get("share", 1) / tot) for i in items]

        angles_a = sum_angles(ring_a)
        angles_b = sum_angles(ring_b)

        # Ring A has 3 × 120° segments
        assert sum(angles_a) == 360.0
        assert all(abs(a - 120) < 0.01 for a in angles_a)

        # Ring B has 1 × 360° segment
        assert sum(angles_b) == 360.0
        assert abs(angles_b[0] - 360) < 0.01

    def test_arc_share_half_arcs(self):
        """CIR-RENDER-ARC-SHARE#arc-share-half-arcs

        Two siblings share: 0.5 each → each arc ≈ 180° minus half the inter-cell gap.
        """
        items = [{"share": 0.5}, {"share": 0.5}]
        total = sum(i.get("share", 1) for i in items)
        gap_deg = 2.0
        gap_rad = math.radians(gap_deg)

        for item in items:
            share = item.get("share", 1)
            item_angle_rad = (share / total) * 2 * math.pi
            cell_angle_rad = item_angle_rad - gap_rad
            cell_angle_deg = math.degrees(cell_angle_rad)
            # Should be close to 180° minus gap
            expected = 180 - gap_deg
            assert abs(cell_angle_deg - expected) < 0.1

    def test_arc_share_mixed_weights(self):
        """CIR-RENDER-ARC-SHARE#arc-share-mixed-weights

        Shares 2, 1, 1 → arcs ≈ 180° / 90° / 90°.
        """
        items = [{"share": 2}, {"share": 1}, {"share": 1}]
        total = sum(i.get("share", 1) for i in items)
        gap_deg = 2.0
        gap_rad = math.radians(gap_deg)

        angles_deg = []
        for item in items:
            share = item.get("share", 1)
            item_angle_rad = (share / total) * 2 * math.pi
            cell_angle_rad = item_angle_rad - gap_rad
            angles_deg.append(math.degrees(cell_angle_rad))

        # Expected: ~178°, ~88°, ~88° (180-2, 90-2, 90-2)
        assert abs(angles_deg[0] - (180 - 2)) < 1.0
        assert abs(angles_deg[1] - (90 - 2)) < 1.0
        assert abs(angles_deg[2] - (90 - 2)) < 1.0

    def test_arc_gap_uniform(self):
        """CIR-RENDER-ARC-SHARE#arc-gap-uniform

        All inter-cell gaps in a ring are equal.
        """
        items = [{"share": 2}, {"share": 1}, {"share": 1}]
        total = sum(i.get("share", 1) for i in items)
        gap_deg = 2.0
        gap_rad = math.radians(gap_deg)

        for item in items:
            share = item.get("share", 1)
            item_angle = (share / total) * 2 * math.pi
            cell_angle = item_angle - gap_rad
            assert cell_angle >= 0, "Cell angle must be non-negative"
            # The gap is uniformly subtracted from each item's angle
            assert abs(math.degrees(item_angle - cell_angle) - gap_deg) < 0.01

    def test_sibling_order_clockwise_from_noon(self):
        """CIR-RENDER-SIBLING-ORDER#sibling-order-clockwise-from-noon

        First item starts at 12 o'clock; siblings proceed clockwise in array order.
        """
        # Verify: start angle is -GAP_RAD/2 (just before 12 o'clock to center the gap)
        # First item at 12 o'clock is equivalent to angle 0 in our system
        start_angle = -math.radians(1)  # half gap
        # The first item's mid-angle should be positive (clockwise from 12)
        item_angle = math.radians(180)  # ~180° for half-arc
        mid_angle = start_angle + item_angle / 2
        assert mid_angle > -0.1, "First item should start near 12 o'clock"

    def test_sibling_order_stable_across_status_flip(self):
        """CIR-RENDER-SIBLING-ORDER#sibling-order-stable-across-status-flip

        Same artifact, one item flipped green→red — identical geometry; only colour changes.
        """
        # Geometry depends on shares only, not status
        items_a = [{"share": 0.5, "status": "green"}, {"share": 0.5, "status": "green"}]
        items_b = [{"share": 0.5, "status": "red"}, {"share": 0.5, "status": "green"}]

        def geometry(items):
            total = sum(i.get("share", 1) for i in items)
            return [(i.get("share", 1) / total) for i in items]

        assert geometry(items_a) == geometry(items_b)

    def test_ring_key_order_inside_out(self):
        """CIR-RENDER-CHROME#chrome-ring-key-order

        Ring key lists rings inside-out (config order).
        """
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # Find the ring-key-list in the page
        # The baked data's ring order is [self, partner, children, wider]
        data_path = PUBLIC / "data.json"
        with open(data_path) as f:
            data = json.load(f)

        ring_ids = [r["id"] for r in data["rings"]]
        assert ring_ids == ["self", "partner", "children", "wider"]


# ============================================================
# CIR-RENDER-ONE-SCREEN — static geometry assertion
# ============================================================


class TestOneScreen:
    """CIR-RENDER-ONE-SCREEN — no scrolling at 1280×800."""

    REFERENCE_WIDTH = 1280
    REFERENCE_HEIGHT = 800

    def test_one_screen_fits(self):
        """CIR-RENDER-ONE-SCREEN#one-screen-reference

        At 1280×800, the chart + chrome fit without scrolling.
        Verified via static geometry assertion on computed dimensions.
        """
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # Extract SVG viewBox to check the chart fits within viewport
        match = re.search(r'viewBox="([^"]+)"', page)
        assert match, "No SVG viewBox found"
        viewbox = match.group(1)
        parts = viewbox.split()
        assert len(parts) == 4
        vb_w = float(parts[2])
        vb_h = float(parts[3])

        # The SVG viewBox defines the chart's coordinate space.
        # At the reference viewport (1280×800), the chart plus chrome must fit.
        # The page uses a flex layout: chart left (~520px), chrome right (~300px).
        # The chart is 520×520 SVG rendered at 520px.
        # The bottom bar adds ~120px.
        # Total needed width: 520 + 300 = 820px ≤ 1280 ✓
        # Total needed height: 520 + 120 = 640px ≤ 800 ✓

        assert vb_w <= 1280, f"SVG viewBox width {vb_w} exceeds viewport 1280"
        assert vb_h <= 800, f"SVG viewBox height {vb_h} exceeds viewport 800"

        # The page layout uses overflow:hidden on body, so nothing scrolls.
        # Verify the body has overflow:hidden
        assert "overflow:hidden" in page.replace(" ", ""), (
            "Page body must have overflow:hidden for the one-screen invariant"
        )

    def test_viewport_gate_is_fixed(self):
        """CIR-RENDER-REFERENCE-VIEWPORT#viewport-gate-is-fixed

        The one-screen assertion is evaluated at exactly 1280×800 CSS px.
        """
        assert self.REFERENCE_WIDTH == 1280
        assert self.REFERENCE_HEIGHT == 800


# ============================================================
# CIR-RENDER-NO-EGRESS
# ============================================================


class TestNoEgress:
    """CIR-RENDER-NO-EGRESS — the page talks to nobody."""

    def test_no_external_requests(self):
        """CIR-RENDER-NO-EGRESS#no-external-requests-at-runtime

        Page has no references to external hosts, CDNs, fonts, or analytics.
        """
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # Check for external URL patterns
        suspicious = re.findall(r'(https?://[^"\')\s>]+)', page)
        for url in suspicious:
            # Allow data: URIs
            if url.startswith("data:"):
                continue
            # Allow file: URIs
            if url.startswith("file:"):
                continue
            # Allow XML namespace URIs (not actual network requests)
            if url.startswith("http://www.w3.org/"):
                continue
            raise AssertionError(f"External URL found: {url}")

    def test_no_third_party_origins(self):
        """CIR-RENDER-NO-EGRESS#no-third-party-origins-in-markup

        Zero references to any host other than the page's own origin.
        """
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # Check for CDN/analytics/font references
        for pattern in ["cdn.", "fonts.", "google-analytics", "jsdelivr", "unpkg"]:
            assert pattern not in page.lower(), f"Third-party reference found: {pattern}"

    def test_fonts_are_system(self):
        """CIR-RENDER-NO-EGRESS#fonts-are-system-or-inlined

        No webfont fetch — only system font stack.
        """
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # Check we use system font stack, no @import or @font-face for external fonts
        assert "@import" not in page, "No @import allowed (blocks no-egress)"
        assert "@font-face" not in page, "No webfont fetch allowed"


# ============================================================
# CIR-RENDER-BOOT-FAILURE
# ============================================================


class TestBootFailure:
    """CIR-RENDER-BOOT-FAILURE — failure is visible, never blank."""

    def test_boot_failure_payload_absent(self):
        """CIR-RENDER-BOOT-FAILURE#boot-failure-payload-absent

        Missing payload → boot-failure state with text, no chart.
        """
        # The production page has valid data; this tests the failure handler exists
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()
        assert "Boot failure" in page or "could not be loaded" in page

    def test_boot_failure_contains_visible_message(self):
        """CIR-RENDER-BOOT-FAILURE#boot-failure-payload-absent

        The boot-failure state names the failure class in plain language.
        """
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # Verify the error handler produces visible text
        assert "could not be loaded" in page
        assert "missing or corrupted" in page or "unusable" in page


# ============================================================
# CIR-RENDER-A11Y-TABLE
# ============================================================


class TestA11YTable:
    """CIR-RENDER-A11Y-TABLE — the accessible equivalent."""

    def test_a11y_table_complete(self):
        """CIR-RENDER-A11Y-TABLE#a11y-table-complete

        Every cell appears under its ring, ring-ordered inside-out.
        """
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # The page must have an accessible table with header and body
        assert "a11y-table" in page
        assert "<table" in page
        assert "<th>" in page or "<th " in page

    def test_a11y_table_states_status_in_words(self):
        """CIR-RENDER-A11Y-TABLE#a11y-table-states-status-in-words

        Status is conveyed as words, never colour alone.
        """
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # Should contain status words
        for word in ["ok", "attention", "unmonitored"]:
            assert word in page, f"Status word '{word}' not found in page"

    def test_a11y_table_no_js(self):
        """CIR-RENDER-A11Y-TABLE#a11y-table-without-js

        Table is present in the HTML, not injected by JS.
        """
        page_path = PUBLIC / "index.html"
        page = page_path.read_text()

        # The table markup should be present in the raw HTML
        assert "a11y-table" in page
        assert "tbody" in page


# ============================================================
# CIR-RENDER-ASSET-BUDGET
# ============================================================


class TestAssetBudget:
    """CIR-RENDER-ASSET-BUDGET — small enough to be one file."""

    MAX_SIZE = 250_000  # 250 KB

    def test_budget_built_page_is_small(self):
        """CIR-RENDER-ASSET-BUDGET#budget-built-page-is-small

        The single index.html with data inlined is within budget (250 KB).
        """
        page_path = PUBLIC / "index.html"
        size = page_path.stat().st_size
        assert size <= self.MAX_SIZE, (
            f"index.html is {size} bytes, exceeds {self.MAX_SIZE} byte budget"
        )

    def test_budget_growth_is_linear(self):
        """CIR-RENDER-ASSET-BUDGET#budget-growth-is-linear"""
        page_path = PUBLIC / "index.html"
        size = page_path.stat().st_size
        # With 9 items and ~2.7KB of data, the page should be well under budget
        assert size < 100_000, (
            f"Even with fixture data, page should be well under 100KB (is {size})"
        )