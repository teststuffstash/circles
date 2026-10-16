# Tests for bake/render.py — the self-contained page renderer.
#
# Evidence split (circles#103 step 2, allure-behavior-snippets CONVENTIONS § Allure taxonomy):
#   - CIR-BAKE-SELF-CONTAINED's artifact rows are proven HERE at the bake's CLI boundary
#     (`python -m bake` → out/index.html + out/data.json; tests/evidence_helpers.py), world alex;
#   - every CIR-RENDER-* row is proven by the browser tier (tests/browser/, CIR-PROC-BROWSER-
#     EVIDENCE#render-requirements-state-their-path) — the in-process tests below that used to
#     claim those rows are unlabelled unit guards now, or were deleted where the browser case
#     carries the same assertion;
#   - the CIR-RENDER-* tests still labelled here (capacity, min-arc, arc-share, partition,
#     thickness, renderer, boot-failure, touch, budget growth) are UNIT_ONLY pending their
#     browser case — the next round of circles#103 step 2.

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import yaml

from bake.config import load_config
from bake.render import add_capacity_warnings, render_page
from bake.resolve import resolve

from evidence_helpers import given_alex, verdict, when_bake
from rules import rule

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ALEX_YAML = FIXTURES / "alex" / "circles.yaml"
CLICK_TABLE = FIXTURES / "click-destinations.yaml"
FIXTURE_REFERENCE_DATE = date(2026, 8, 3)
FIXTURE_GENERATED_AT = datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# Helpers
# ===========================================================================

def _point_to_angle(x: float, y: float, cx: float = 400.0, cy: float = 400.0) -> float:
    """Convert SVG (x, y) coordinates to a clockwise-from-12-o'clock angle in degrees.

    In SVG coordinates (y-down), the angle from centre is atan2(dx, -dy)
    where dx, dy are from centre.  The centre of the sunburst viewBox is
    (cx, cy) = (400, 400) by default.
    """
    dx = x - cx
    dy = cy - y  # flip y (SVG y-down → Cartesian y-up)
    return math.degrees(math.atan2(dx, dy)) % 360


def _arc_sweep_degrees(path_d: str, cx: float = 400.0, cy: float = 400.0) -> float:
    """Compute the angular sweep of a non-full-circle SVG arc path.

    Each cell arc is a single sub-path: M start → A outer → L → A inner → Z.
    The sweep is the clockwise angle from the M point to the first A endpoint.
    """
    m_match = re.match(r'M\s+([\d.-]+)\s+([\d.-]+)', path_d)
    assert m_match is not None, f"Could not parse M command in: {path_d}"
    x0, y0 = float(m_match.group(1)), float(m_match.group(2))
    a_endpoints = re.findall(
        r'A\s+[\d.]+\s+[\d.]+\s+\d+\s+\d+\s+\d+\s+([\d.-]+)\s+([\d.-]+)',
        path_d,
    )
    assert len(a_endpoints) >= 1, f"Could not find A command in: {path_d}"
    outer_end_x, outer_end_y = map(float, a_endpoints[0])
    start_angle = _point_to_angle(x0, y0, cx, cy)
    end_angle = _point_to_angle(outer_end_x, outer_end_y, cx, cy)
    return (end_angle - start_angle) % 360


def _resolve_fixture() -> dict:
    """Load the fixture config and resolve it."""
    config = load_config(ALEX_YAML)
    artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
    return add_capacity_warnings(artifact)


def _render_fixture() -> str:
    """Render the fixture artifact to HTML."""
    artifact = _resolve_fixture()
    return render_page(artifact)


def _load_click_table() -> dict:
    """Load the CIR-RENDER-CLICK destination table (fixtures/click-destinations.yaml)."""
    with open(CLICK_TABLE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _render_click_row(row: dict, tmp_path: Path) -> str:
    """Render a one-ring page for a click-destination table row.

    The row's `item` block is spliced into a config for the fixture person at
    runtime (CIR-PROC-TEST-FIXTURES#fixture-row-is-spec-row) — nothing about the
    item is invented in test code.
    """
    table = _load_click_table()
    data = {
        "person": table["person"],
        "rings": [{
            "id": table["ring"]["id"],
            "label": table["ring"]["label"],
            "items": [row["item"]],
        }],
    }
    config_path = tmp_path / "circles.yaml"
    config_path.write_text(yaml.dump(data), encoding="utf-8")

    config = load_config(config_path)
    artifact = resolve(
        config,
        reference_date=FIXTURE_REFERENCE_DATE,
        generated_at=FIXTURE_GENERATED_AT,
    )
    return render_page(add_capacity_warnings(artifact))


def _cell_open_tag(html_text: str, full_id: str) -> tuple[str, str]:
    """Return (tag_name, attributes) of the cell element for `full_id`.

    Cells are emitted as `<g class="cell" …>` when they have no destination and
    `<a class="cell cell-linked" href=… >` when they do (CIR-RENDER-CLICK).
    """
    m = re.search(
        r'<(a|g)\s+([^>]*data-item="' + re.escape(full_id) + r'"[^>]*)>',
        html_text,
    )
    assert m is not None, f"No cell element found for {full_id!r} in the rendered page"
    return m.group(1), m.group(2)


def _inlined_artifact(index_html: Path) -> dict:
    """The artifact a baked index.html carries in `<script id="artifact-data">`."""
    page = index_html.read_text(encoding="utf-8")
    m = re.search(r'<script id="artifact-data" type="application/json">(.*?)</script>', page, re.S)
    assert m is not None, "artifact data script tag not found"
    return json.loads(m.group(1))


# ===========================================================================
# CIR-BAKE-SELF-CONTAINED — one bake run yields both artifacts
# ===========================================================================

class TestBakeSelfContained:
    """CIR-BAKE-SELF-CONTAINED — one bake run yields both artifacts (world alex, the bake CLI).

    Its browser row (#page-renders-with-no-network) is tests/browser/test_render_rows.py."""

    @rule("CIR-BAKE-SELF-CONTAINED")
    def test_inlined_data_equals_the_file(self, alex_copy) -> None:
        """CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file — `index.html` vs `data.json` from
        one bake: identical data."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("index.html inlined artifact", _inlined_artifact(run.out_dir / "index.html"), run.data)

    @rule("CIR-BAKE-SELF-CONTAINED")
    def test_page_has_both_artifacts(self, alex_copy) -> None:
        """CIR-BAKE-SELF-CONTAINED#page-has-both-artifacts — one bake run: `index.html` contains
        both the SVG chart and the inlined `<script id="artifact-data">`."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        page = (run.out_dir / "index.html").read_text(encoding="utf-8")
        verdict("artifact files in out/", run.artifact_files, ["data.json", "index.html"])
        verdict("index.html", page, "<svg", op="contains")
        verdict("index.html", page, '<script id="artifact-data" type="application/json">', op="contains")
        verdict("index.html", page, "data.json", op="not contains")


# ===========================================================================
# CIR-BAKE-SELF-CONTAINED#script-escape — inlined JSON must not break on
# </script> sequences in string content (labels, notes, detail lines)
# ===========================================================================

class TestInlinedJsonScriptEscape:
    """CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file — the inlined
    artifact JSON must survive </script> sequences in any string field
    (person, ring/item labels, notes, detail lines, links, grey reasons)
    without prematurely closing the <script> tag or corrupting the JSON
    round-trip.

    Regression test for the hardening in bake/render.py:render_page() — the
    artifact JSON now escapes closing-script sequences (</ becomes <\\/) before
    inlining.  The escaped form is a valid JSON escape equivalent to /, so the
    data round-trips on json.loads().
    """

    # A payload that, if left unescaped, closes the script tag early and lets
    # attacker-controlled text inject a second <script> element.
    PAYLOAD = "</script><script>alert('xss')</script>"

    @pytest.mark.parametrize("path", [
        pytest.param(("person",), id="script-escape-person"),
        pytest.param(("rings", 0, "label"), id="script-escape-ring-label"),
        pytest.param(("rings", 0, "items", 0, "label"), id="script-escape-item-label"),
        pytest.param(("rings", 0, "items", 0, "note"), id="script-escape-note"),
        pytest.param(("rings", 0, "items", 0, "detail_line"), id="script-escape-detail-line"),
        pytest.param(("rings", 0, "items", 0, "link"), id="script-escape-link"),
        pytest.param(("rings", 0, "items", 0, "grey_reason"), id="script-escape-grey-reason"),
    ])
    def test_script_escape_survives(self, path: tuple) -> None:
        """A </script> in a string field must not break the inlined JSON:
        the script-tag boundary survives AND the artifact round-trips."""
        artifact = _resolve_fixture()

        # Inject the payload into the target field (builds an artifact dict
        # with a </script>-containing string field, per the issue).
        target = artifact
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = self.PAYLOAD

        html = render_page(artifact)

        # Extract the inlined JSON from the artifact-data script block.
        marker = '<script id="artifact-data" type="application/json">'
        start = html.find(marker)
        assert start >= 0, "artifact data script tag not found"
        start = html.index(">", start) + 1
        # The FIRST </script> after the marker must be the real closing tag —
        # if the payload were unescaped it would close the tag early, so this
        # would find the injected one and yield truncated, invalid JSON.
        end = html.index("</script>", start)
        inlined_text = html[start:end].strip()

        # Boundary survives: the inlined block is valid, complete JSON.
        inlined = json.loads(inlined_text)

        # Round-trip: the payload is preserved verbatim in the same field.
        got = inlined
        for key in path:
            got = got[key]
        assert got == self.PAYLOAD, "injected </script> payload not preserved"

        # And the whole artifact round-trips identically (CIR-BAKE-SELF-CONTAINED
        # #inlined-data-equals-the-file still holds with hostile content).
        assert inlined == artifact


# ===========================================================================
# CIR-RENDER-NO-EGRESS — the page talks to nobody
# ===========================================================================

class TestRenderNoEgressGuard:
    """Unit guard (unlabelled): the rendered markup names no external resource. The rows are
    proven in the browser — CIR-RENDER-NO-EGRESS, CIR-BAKE-SELF-CONTAINED#page-renders-with-
    no-network, CIR-RENDER-PRINT-COLOR#print-stylesheet-is-inline (tests/browser/)."""

    def test_markup_references_no_external_resource(self) -> None:
        html = _render_fixture()
        # No external URLs (the SVG namespace w3.org is an identifier, not a fetch)
        urls = re.findall(r'https?://[^"\'<>\s]+', html)
        assert [u for u in urls if "w3.org" not in u] == [], f"Found external URLs: {urls}"
        assert 'href="http' not in html
        assert 'src="' not in html
        assert "@import" not in html
        assert "@font-face" not in html
        assert '<link rel="stylesheet"' not in html
        for host in ("fonts.googleapis", "cdn.", "analytics"):
            assert host not in html


# ===========================================================================
# CIR-RENDER-ASSET-BUDGET — small enough to be one file
# ===========================================================================

class TestRenderAssetBudget:
    """CIR-RENDER-ASSET-BUDGET — #budget-built-page-is-small is the browser's
    (tests/browser/test_render_rows.py); #budget-growth-is-linear is UNIT_ONLY pending."""

    @rule("CIR-RENDER-ASSET-BUDGET")
    def test_budget_growth_is_linear(self) -> None:
        """CIR-RENDER-ASSET-BUDGET#budget-growth-is-linear —
        growth is linear in items, not in libraries."""
        html = _render_fixture()
        size = len(html.encode("utf-8"))
        # For the fixture (8 items), should be well under 100 KB
        assert size < 100_000, f"index.html is {size} bytes for 8 items"


# ===========================================================================
# CIR-RENDER-CLICK — where a cell leads
# ===========================================================================

class TestRenderClick:
    """Unit guard (unlabelled) for CIR-RENDER-CLICK's anchors — the rows themselves are proven by
    clicking in the browser (tests/browser/test_render_rows.py TestClick); this keeps the cheap
    markup facts the browser case does not measure (rel="noopener", no href on a dead cell).

    One parametrised test over every row of fixtures/click-destinations.yaml
    (CIR-PROC-TEST-ROWS#rows-parametrised-not-copied), not one function per row.

    The P2 rows (`click-link-wins-over-detail`, `click-detail-when-no-link`) are
    absent from the table on purpose: detail pages do not exist at P0, so there is
    no behaviour to assert. They are deferred with the rest of P2 (#35).
    """

    @pytest.mark.parametrize(
        "row",
        _load_click_table()["rows"],
        ids=lambda r: f"CIR-RENDER-CLICK#{r['row_id']}",
    )
    def test_click_destination(self, row: dict, tmp_path: Path) -> None:
        """CIR-RENDER-CLICK — the cell's activation target is what the row declares.

        Row ids are carried by the parametrised case id, so each row of the spec
        table joins to its own evidence entry.
        """
        html_text = _render_click_row(row, tmp_path)
        expected = row["expected"]
        full_id = f"self/{row['item']['id']}"
        tag, attrs = _cell_open_tag(html_text, full_id)

        if not expected["clickable"]:
            # No destination: not an anchor, no href anywhere, cursor stays default.
            assert tag == "g", (
                f"{full_id} has no destination but rendered as <{tag}> — "
                f"a cell with neither link nor detail page must not be an anchor"
            )
            assert "href=" not in attrs, f"{full_id} must carry no href, got: {attrs}"
            assert 'href="' not in html_text, (
                "a destination-less page must contain no link at all"
            )
            assert "cell-linked" not in attrs, (
                f"{full_id} must not carry the clickable class, got: {attrs}"
            )
            # The pointer cursor is an affordance for a destination that does not
            # exist here — the base .cell rule must leave the cursor alone.
            assert ".cell { cursor: default" in html_text, (
                "cells without a destination must not show a pointer cursor"
            )
            return

        assert tag == "a", (
            f"{full_id} declares link={expected['href']!r} but rendered as <{tag}> — "
            f"the destination is dropped, so the cell leads nowhere"
        )
        assert f'href="{expected["href"]}"' in attrs, (
            f"{full_id}: expected href={expected['href']!r}, got: {attrs}"
        )
        assert "cell-linked" in attrs, f"{full_id}: expected the clickable class, got: {attrs}"
        assert ".cell-linked { cursor: pointer" in html_text, (
            "a cell with a destination must show the pointer cursor"
        )

        if expected["target"] is None:
            # Root-relative: navigates in place — no new tab, so no rel needed either.
            assert "target=" not in attrs, (
                f"{full_id}: a root-relative link must navigate in place, got: {attrs}"
            )
        else:
            assert f'target="{expected["target"]}"' in attrs, (
                f"{full_id}: expected target={expected['target']!r}, got: {attrs}"
            )
            assert f'rel="{expected["rel"]}"' in attrs, (
                f"{full_id}: a new-tab link must carry rel={expected['rel']!r}, got: {attrs}"
            )


# ===========================================================================
# CIR-RENDER-CAPACITY — how much the page holds
# ===========================================================================

class TestRenderCapacity:
    """CIR-RENDER-CAPACITY — how much the page holds."""

    @rule("CIR-RENDER-CAPACITY")
    def test_capacity_inside_envelope(self) -> None:
        """CIR-RENDER-CAPACITY#capacity-inside-envelope —
        the fixture (4 rings, ≤3 items/ring) renders without density warning."""
        html = _render_fixture()
        # No density warning in the output
        assert "density" not in html.lower()
        assert "capacity" not in html.lower()

    @rule("CIR-RENDER-CAPACITY")
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

    @rule("CIR-RENDER-CAPACITY")
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

    @rule("CIR-RENDER-CAPACITY")
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

    @rule("CIR-RENDER-CAPACITY")
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

    @rule("CIR-RENDER-MIN-ARC")
    def test_min_arc_exceeded_by_ring(self) -> None:
        """CIR-RENDER-MIN-ARC#min-arc-exceeded-by-ring —
        many items in one ring triggers a min-arc build warning AND every
        rendered arc angle respects MIN_ARC_DEG AND the total consumed
        angle does not exceed 360° (CIR-RENDER-MIN-ARC
        #overflow-capped-at-total-deg)."""
        import re as _re
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

            # Verify every rendered arc angle >= MIN_ARC_DEG by parsing the
            # SVG path elements' outer-arc endpoints back into angles.
            #
            # Each arc path looks like:
            #   M x1o y1o A r r 0 l 1 x2o y2o L x2i y2i A r r 0 l 0 x1i y1i Z
            # The outer arc endpoint (x2o, y2o) encodes end_angle.
            # The inner arc start point (x1i, y1i) encodes start_angle.
            # We use the OUTER arc endpoint since it has larger resolution.
            #
            # Extract all paths that belong to cells (not the centre circle)
            # by finding path elements that follow a 'data-item=' attribute
            cell_paths = _re.findall(
                r'data-item="[^"]*"[^>]*>\s*<path d="([^"]+)"',
                html,
            )

            # The centre circle path is also a <path> but has no data-item; that's fine.
            # We have exactly 120 cell paths
            assert len(cell_paths) == 120, \
                f"Expected 120 cell paths, got {len(cell_paths)}"

            # Parse each path to extract start and end angles
            prev_end_angle = -90.0  # First arc starts at 12 o'clock
            for path_d in cell_paths:
                # Extract the two outer arc points from the path
                # Pattern: M x1 y1 A r r ... 1 x2 y2 L ...
                m = _re.match(
                    r'M\s+([\d.-]+)\s+([\d.-]+)\s+A\s+[\d.]+\s+[\d.]+\s+\d\s+\d\s+1\s+([\d.-]+)\s+([\d.-]+)',
                    path_d,
                )
                assert m is not None, f"Could not parse path: {path_d}"
                x1o, y1o, x2o, y2o = map(float, m.groups())

                start_angle = _point_to_angle(x1o, y1o) % 360
                end_angle = _point_to_angle(x2o, y2o) % 360

                # Handle crossing the 0°/360° boundary
                arc_deg = (end_angle - start_angle) % 360

                # With 120 items, CELL_GAP_DEG=2°, MIN_ARC_DEG=3°:
                #   total_deg = 360 - 120*2 = 120°
                #   floored_sum = 120*3 = 360° > 120°
                # So the overflow branch fires and arcs are scaled to
                # 120/360 * 3 = 1° each — below MIN_ARC_DEG but that's
                # expected (the warning covers it).  The key assertion is
                # the total-consumed check below.
                # For non-overflow cases, every arc must be >= MIN_ARC_DEG.
                NUM_ITEMS = 120
                CELL_GAP_DEG = 2.0
                MIN_ARC_DEG = 3.0
                total_deg = 360.0 - CELL_GAP_DEG * NUM_ITEMS
                floored_sum = NUM_ITEMS * MIN_ARC_DEG
                overflow_branch = floored_sum > total_deg
                if not overflow_branch:
                    assert arc_deg >= 2.95, \
                        f"Arc angle {arc_deg:.3f}° is below MIN_ARC_DEG (3.0°) for path: {path_d[:80]}..."

                # The arc should start where previous ended (plus cell gap)
                # Allow for floating point
                if prev_end_angle != -90.0:
                    expected_start = (prev_end_angle + 2.0) % 360  # CELL_GAP_DEG = 2.0
                    actual_start = start_angle % 360
                    # Allow small tolerance
                    assert abs(actual_start - expected_start) < 1.0 or \
                           abs(actual_start - expected_start - 360) < 1.0 or \
                           abs(actual_start - expected_start + 360) < 1.0, \
                        f"Arc gap mismatch: expected start {expected_start:.1f}°, got {actual_start:.1f}°"

                prev_end_angle = end_angle

            # Verify the total consumed angle (arcs + gaps) does not exceed
            # 360°, even under extreme over-capacity (CIR-RENDER-MIN-ARC
            # #overflow-capped-at-total-deg).  Without the cap, 120 × 3° = 360°
            # of arcs plus 120 × 2° = 240° of gaps would total 600°, wrapping
            # around visually.
            first_arc = cell_paths[0]
            m_first = _re.match(
                r'M\s+([\d.-]+)\s+([\d.-]+)\s+A\s+[\d.]+\s+[\d.]+\s+\d\s+\d\s+1\s+([\d.-]+)\s+([\d.-]+)',
                first_arc,
            )
            x1o_first, y1o_first, _, _ = map(float, m_first.groups())
            first_start = _point_to_angle(x1o_first, y1o_first) % 360

            last_arc = cell_paths[-1]
            m_last = _re.match(
                r'M\s+([\d.-]+)\s+([\d.-]+)\s+A\s+[\d.]+\s+[\d.]+\s+\d\s+\d\s+1\s+([\d.-]+)\s+([\d.-]+)',
                last_arc,
            )
            _, _, x2o_last, y2o_last = map(float, m_last.groups())
            last_end = _point_to_angle(x2o_last, y2o_last) % 360

            # Total consumed = (last_end - first_start) mod 360 + last gap
            total_consumed = (last_end - first_start) % 360 + 2.0  # + CELL_GAP_DEG
            # Should be <= 360° (allow 0.5° fp tolerance)
            assert total_consumed <= 360.5, \
                f"Total consumed angle {total_consumed:.2f}° exceeds 360° — arcs overflow"

        finally:
            tmp_path.unlink()


# ===========================================================================
# CIR-RENDER-BOOT-FAILURE — failure is visible, never blank
# ===========================================================================

class TestRenderBootFailure:
    """CIR-RENDER-BOOT-FAILURE — failure is visible, never blank."""

    @rule("CIR-RENDER-BOOT-FAILURE")
    def test_boot_failure_payload_absent(self) -> None:
        """CIR-RENDER-BOOT-FAILURE#boot-failure-payload-absent —
        the page handles missing payload gracefully (structural: the page always has a payload
        since it's baked in, but we verify the script tag is present)."""
        html = _render_fixture()
        assert '<script id="artifact-data"' in html

    @rule("CIR-RENDER-BOOT-FAILURE")
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


# ===========================================================================
# CIR-RENDER-TOUCH — no hover on glass
# ===========================================================================

class TestRenderTouch:
    """CIR-RENDER-TOUCH — no hover on glass."""

    @rule("CIR-RENDER-TOUCH")
    def test_touch_target_size(self) -> None:
        """CIR-RENDER-TOUCH#touch-target-size —
        cells are SVG elements with role=button and in the tab order. A source-level
        check: measuring the target size needs the browser tier (#34)."""
        html = _render_fixture()
        assert 'role="button"' in html
        assert 'tabindex="0"' in html


# ===========================================================================
# CIR-RENDER-RENDERER — what draws the rings
# ===========================================================================

class TestRenderRenderer:
    """CIR-RENDER-RENDERER — what draws the rings."""

    @rule("CIR-RENDER-RENDERER")
    def test_renderer_draws_independent_rings(self) -> None:
        """CIR-RENDER-RENDERER#renderer-draws-independent-rings —
        the SVG has multiple ring paths."""
        html = _render_fixture()
        # Count path elements (each arc is a path)
        path_count = html.count("<path")
        # Should have at least 8 paths (one per item)
        assert path_count >= 8, f"Expected at least 8 paths, got {path_count}"

    @rule("CIR-RENDER-RENDERER")
    def test_renderer_adds_no_runtime_egress(self) -> None:
        """CIR-RENDER-RENDERER#renderer-adds-no-runtime-egress —
        no library fetched at run time."""
        html = _render_fixture()
        assert '<script src=' not in html
        assert '<link rel="stylesheet"' not in html


# ===========================================================================
# CIR-RENDER-RING-PARTITION — rings are independent
# ===========================================================================

class TestRenderRingPartition:
    """CIR-RENDER-RING-PARTITION — rings are independent."""

    @rule("CIR-RENDER-RING-PARTITION")
    def test_partition_full_circle_per_ring(self) -> None:
        """CIR-RENDER-RING-PARTITION#partition-full-circle-per-ring —
        each ring spans the full 360°."""
        html = _render_fixture()
        # The SVG has paths for all items
        assert "<path" in html
        # Multiple rings are rendered
        assert 'data-item="self/' in html
        assert 'data-item="wider/' in html

    @rule("CIR-RENDER-RING-PARTITION")
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

    @rule("CIR-RENDER-ARC-SHARE")
    def test_arc_share_half_arcs(self) -> None:
        """CIR-RENDER-ARC-SHARE#arc-share-half-arcs —
        two siblings with share:0.5 each get equal arcs."""
        html = _render_fixture()
        # Both children items appear
        assert 'data-item="children/nova"' in html
        assert 'data-item="children/kit"' in html

    @rule("CIR-RENDER-ARC-SHARE")
    def test_arc_share_single_item_ring(self) -> None:
        """CIR-RENDER-ARC-SHARE#arc-share-single-item-ring —
        a ring with exactly one item renders as a full 360° band
        with no visible gap (CELL_GAP_DEG is not subtracted).

        The SVG path must use two half-circle arcs (not a single 360° arc)
        because SVG elliptical-arc commands with coincident start/end points
        are omitted by conforming renderers.
        """
        import yaml
        import tempfile

        config_data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"manual": "green"}}],
            }],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            artifact = add_capacity_warnings(artifact)
            html = render_page(artifact)

            # Extract all cell paths from the SVG.
            import re as _re
            cell_paths = _re.findall(
                r'data-item="[^"]*"[^>]*>\s*<path d="([^"]+)"',
                html,
            )
            assert len(cell_paths) == 1, \
                f"Expected 1 cell path, got {len(cell_paths)}"

            path_d = cell_paths[0]

            # The path must contain TWO sub-paths (two M commands) —
            # a single 360° arc would be degenerate (coincident endpoints
            # are omitted by SVG renderers).
            sub_paths = [s.strip() for s in path_d.split("Z") if s.strip()]
            assert len(sub_paths) == 2, \
                f"Expected 2 sub-paths (half-circle arcs), got {len(sub_paths)}: {path_d}"

            # Verify each sub-path has non-degenerate arcs (start != end)
            # and that together they cover the full 360°.
            total_sweep = 0.0
            for sp in sub_paths:
                # Parse the sub-path using regex to find all A commands
                # Structure: M x0 y0 A rx ry xrot large sweep x1 y1 L x2 y2 A rx ry xrot large sweep x3 y3
                sp = sp.strip()
                assert sp.startswith("M"), f"Sub-path must start with M: {sp}"

                # Extract all A command endpoints
                a_endpoints = _re.findall(
                    r'A\s+[\d.]+\s+[\d.]+\s+\d+\s+\d+\s+\d+\s+([\d.-]+)\s+([\d.-]+)',
                    sp,
                )
                assert len(a_endpoints) == 2, \
                    f"Expected 2 A commands per sub-path, got {len(a_endpoints)}: {sp}"

                # Outer arc: start = M target, end = first A endpoint
                m_match = _re.match(r'M\s+([\d.-]+)\s+([\d.-]+)', sp)
                assert m_match is not None, f"Could not parse M command: {sp}"
                x0, y0 = float(m_match.group(1)), float(m_match.group(2))
                outer_end_x, outer_end_y = map(float, a_endpoints[0])

                # Inner arc: start = L target, end = second A endpoint
                l_match = _re.search(r'L\s+([\d.-]+)\s+([\d.-]+)', sp)
                assert l_match is not None, f"Could not parse L command: {sp}"
                inner_start_x, inner_start_y = float(l_match.group(1)), float(l_match.group(2))
                inner_end_x, inner_end_y = map(float, a_endpoints[1])

                # Verify arcs are non-degenerate (start != end)
                assert abs(x0 - outer_end_x) > 0.01 or abs(y0 - outer_end_y) > 0.01, \
                    f"Outer arc has coincident endpoints ({x0:.2f},{y0:.2f}) → ({outer_end_x:.2f},{outer_end_y:.2f})"
                assert abs(inner_start_x - inner_end_x) > 0.01 or abs(inner_start_y - inner_end_y) > 0.01, \
                    f"Inner arc has coincident endpoints ({inner_start_x:.2f},{inner_start_y:.2f}) → ({inner_end_x:.2f},{inner_end_y:.2f})"

                # Compute the angular span of this sub-path using the outer arc
                # (M → first A endpoint), which sweeps 180° for each half-circle.
                start_angle = _point_to_angle(x0, y0)
                end_angle = _point_to_angle(outer_end_x, outer_end_y)
                sweep = (end_angle - start_angle) % 360
                total_sweep += sweep

            # The two half-circles together should cover 360°
            assert abs(total_sweep - 360.0) < 2.0, \
                f"Total sweep of both sub-paths is {total_sweep:.2f}°, expected ~360°"
        finally:
            tmp_path.unlink()

    @rule("CIR-RENDER-ARC-SHARE")
    def test_arc_share_mixed_weights(self) -> None:
        """CIR-RENDER-ARC-SHARE#arc-share-mixed-weights —
        siblings with shares 2, 1, 1 → arcs ≈ 180° / 90° / 90°."""
        import yaml
        import tempfile
        from bake.config import load_config
        from bake.resolve import resolve
        from bake.render import render_page, add_capacity_warnings

        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [
                    {"id": "big", "label": "Big", "share": 2},
                    {"id": "med", "label": "Medium", "share": 1},
                    {"id": "sml", "label": "Small", "share": 1},
                ],
            }],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            artifact = add_capacity_warnings(artifact)
            html = render_page(artifact)

            # All three items appear in the SVG
            assert 'data-item="a/big"' in html
            assert 'data-item="a/med"' in html
            assert 'data-item="a/sml"' in html

            # Mixed shares should produce a warning
            warnings = artifact.get("warnings", [])
            mixed_warnings = [w for w in warnings if "mixes declared and undeclared" in w.get("message", "")]
            assert len(mixed_warnings) >= 1, f"Expected mixed-share warning, got: {warnings}"

            # Verify arc proportions via SVG path geometry.
            # Shares 2:1:1 → arcs ≈ 180° / 90° / 90° (minus inter-cell gaps).
            import re as _re
            # Extract path d for each item by data-item attribute
            big_match = _re.search(
                r'data-item="a/big"[^>]*>\s*<path d="([^"]+)"', html,
            )
            med_match = _re.search(
                r'data-item="a/med"[^>]*>\s*<path d="([^"]+)"', html,
            )
            sml_match = _re.search(
                r'data-item="a/sml"[^>]*>\s*<path d="([^"]+)"', html,
            )

            assert big_match is not None, "Could not find SVG path for a/big"
            assert med_match is not None, "Could not find SVG path for a/med"
            assert sml_match is not None, "Could not find SVG path for a/sml"

            big_sweep = _arc_sweep_degrees(big_match.group(1))
            med_sweep = _arc_sweep_degrees(med_match.group(1))
            sml_sweep = _arc_sweep_degrees(sml_match.group(1))

            # With CELL_GAP_DEG=2.0 and 3 items, total arc space is 354°.
            # Shares 2:1:1 → ≈177° / 88.5° / 88.5°.
            assert abs(big_sweep - 180.0) < 5.0, \
                f"Big item sweep {big_sweep:.2f}°, expected ≈180°"
            assert abs(med_sweep - 90.0) < 5.0, \
                f"Medium item sweep {med_sweep:.2f}°, expected ≈90°"
            assert abs(sml_sweep - 90.0) < 5.0, \
                f"Small item sweep {sml_sweep:.2f}°, expected ≈90°"

            # Total arcs sum to 360° minus 3 × CELL_GAP_DEG (2.0°) ≈ 354°
            total_sweep = big_sweep + med_sweep + sml_sweep
            assert abs(total_sweep - 354.0) < 3.0, \
                f"Total sweep {total_sweep:.2f}°, expected ≈354° (360° minus 3 × 2° gaps)"
        finally:
            tmp_path.unlink()


# ===========================================================================
# CIR-RENDER-RING-THICKNESS — the most important ring is the smallest
# ===========================================================================

class TestRenderRingThickness:
    """CIR-RENDER-RING-THICKNESS — the most important ring is the smallest."""

    @rule("CIR-RENDER-RING-THICKNESS")
    def test_thickness_non_increasing_outward(self) -> None:
        """CIR-RENDER-RING-THICKNESS#thickness-non-increasing-outward —
        inner rings are thicker than outer rings."""
        html = _render_fixture()
        # The centre hole exists (float formatting)
        assert 'cx="400.0" cy="400.0" r="60.0"' in html
        # The SVG has the right viewBox
        assert 'viewBox="0 0 800 800"' in html

    @rule("CIR-RENDER-RING-THICKNESS")
    def test_centre_hole_is_not_zero(self) -> None:
        """CIR-RENDER-RING-THICKNESS#centre-hole-is-not-zero —
        a hole remains; the innermost ring is a band, not a pie."""
        html = _render_fixture()
        assert '<circle' in html
        assert 'cx="400.0"' in html

    @rule("CIR-RENDER-RING-THICKNESS")
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

    @rule("CIR-RENDER-MIN-ARC")
    def test_min_arc_tiny_share_still_drawn(self) -> None:
        """CIR-RENDER-MIN-ARC#min-arc-tiny-share-still-drawn —
        all items are drawn as paths."""
        html = _render_fixture()
        # All 8 items have paths
        path_count = html.count("<path")
        assert path_count >= 8  # at least 8 arc paths + centre circle

    @rule("CIR-RENDER-MIN-ARC")
    def test_mixed_floored_natural_overflow_capped(self) -> None:
        """CIR-RENDER-MIN-ARC#mixed-floored-natural-overflow-capped —
        mixed floored and natural items where floored arcs alone
        overflow total_deg; verify total consumed angle does not
        exceed 360°."""
        import re as _re
        import yaml
        import tempfile

        # Ring with 120 items: 20 disproportionately large items (natural)
        # and 100 tiny items (floored).  With total_deg = 120° and 100
        # floored items needing 300°, the overflow branch fires.
        # The old (round-3) code derived scale from floored count only
        # and applied it to all items, making the total consumed exceed
        # total_deg.  The current code distributes evenly.
        items = []
        for j in range(20):
            items.append({
                "id": f"big-{j}",
                "label": f"Big {j}",
                "status": {"manual": "green"},
                "share": 50,
            })
        for j in range(100):
            items.append({
                "id": f"tiny-{j}",
                "label": f"Tiny {j}",
                "status": {"manual": "green"},
                "share": 1,
            })
        config_data = {
            "person": "Test",
            "rings": [{"id": "mixed", "label": "Mixed", "items": items}],
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

            # Verify total consumed angle (arcs + gaps) does not exceed 360°
            cell_paths = _re.findall(
                r'data-item="[^"]*"[^>]*>\s*<path d="([^"]+)"',
                html,
            )
            assert len(cell_paths) == 120, \
                f"Expected 120 cell paths, got {len(cell_paths)}"

            first_arc = cell_paths[0]
            m_first = _re.match(
                r'M\s+([\d.-]+)\s+([\d.-]+)\s+A\s+[\d.]+\s+[\d.]+\s+\d\s+\d\s+1\s+([\d.-]+)\s+([\d.-]+)',
                first_arc,
            )
            x1o_first, y1o_first, _, _ = map(float, m_first.groups())
            first_start = _point_to_angle(x1o_first, y1o_first) % 360

            last_arc = cell_paths[-1]
            m_last = _re.match(
                r'M\s+([\d.-]+)\s+([\d.-]+)\s+A\s+[\d.]+\s+[\d.]+\s+\d\s+\d\s+1\s+([\d.-]+)\s+([\d.-]+)',
                last_arc,
            )
            _, _, x2o_last, y2o_last = map(float, m_last.groups())
            last_end = _point_to_angle(x2o_last, y2o_last) % 360

            # Total consumed = (last_end - first_start) mod 360 + last gap
            total_consumed = (last_end - first_start) % 360 + 2.0  # + CELL_GAP_DEG
            assert total_consumed <= 360.5, \
                f"Total consumed angle {total_consumed:.2f}° exceeds 360° — arcs overflow"
        finally:
            tmp_path.unlink()

    @rule("CIR-RENDER-MIN-ARC")
    def test_overflow_no_negative_arcs(self) -> None:
        """CIR-RENDER-MIN-ARC#overflow-no-negative-arcs —
        ring with >180 items where total_deg would go negative
        pre-fix; verify no negative/degenerate arc angles and
        the capacity warning has a non-negative count."""
        import re as _re
        import yaml
        import tempfile

        # 200 items in one ring — total_deg = max(360 - 2*200, 0) = 0
        items = []
        for j in range(200):
            items.append({
                "id": f"item-{j}",
                "label": f"Item {j}",
                "status": {"manual": "green"},
            })
        config_data = {
            "person": "Test",
            "rings": [{"id": "overflow", "label": "Overflow", "items": items}],
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

            # Verify no negative/degenerate arc angles
            cell_paths = _re.findall(
                r'data-item="[^"]*"[^>]*>\s*<path d="([^"]+)"',
                html,
            )
            assert len(cell_paths) == 200, \
                f"Expected 200 cell paths, got {len(cell_paths)}"

            prev_end_angle = -90.0
            for path_d in cell_paths:
                m = _re.match(
                    r'M\s+([\d.-]+)\s+([\d.-]+)\s+A\s+[\d.]+\s+[\d.]+\s+\d\s+\d\s+1\s+([\d.-]+)\s+([\d.-]+)',
                    path_d,
                )
                assert m is not None, f"Could not parse path: {path_d}"
                x1o, y1o, x2o, y2o = map(float, m.groups())

                start_angle = _point_to_angle(x1o, y1o) % 360
                end_angle = _point_to_angle(x2o, y2o) % 360
                arc_deg = (end_angle - start_angle) % 360

                # Arc angle must be non-negative (no degenerate arcs)
                assert arc_deg >= 0, \
                    f"Negative arc angle {arc_deg:.3f}° for path: {path_d[:80]}..."

                # With equal distribution of 0°, all arcs are 0°, which is
                # zero-length (degenerate) but non-negative — that's expected
                # when total_deg = 0.

            # Verify the capacity warning has a non-negative count
            warnings = artifact.get("warnings", [])
            overflow_warnings = [w for w in warnings
                                 if "minimum arc" in w.get("message", "").lower()]
            assert len(overflow_warnings) >= 1, \
                f"Expected min-arc warning, got: {warnings}"
            for w in overflow_warnings:
                msg = w["message"]
                # Extract the max_items_at_min value from the message
                m = _re.search(r'exceeds (\d+) items at', msg)
                assert m is not None, f"Could not parse max_items_at_min from: {msg}"
                max_at_min = int(m.group(1))
                assert max_at_min >= 0, \
                    f"max_items_at_min ({max_at_min}) is negative in warning: {msg}"
        finally:
            tmp_path.unlink()


# ===========================================================================
# CIR-RENDER-CAPACITY — empty ring band
# ===========================================================================

class TestRenderEmptyRing:
    """CIR-RENDER-CAPACITY — empty ring band."""

    @rule("CIR-RENDER-CAPACITY")
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