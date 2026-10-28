# Tests for bake/render.py — the self-contained page renderer.
#
# Evidence split (circles#103 step 2, allure-behavior-snippets CONVENTIONS § Allure taxonomy):
#   - CIR-BAKE-SELF-CONTAINED's artifact rows are proven HERE at the bake's CLI boundary
#     (`python -m bake` → out/index.html + out/data.json; tests/evidence_helpers.py), world alex;
#   - every CIR-RENDER-* row is proven by the browser tier (tests/browser/, CIR-PROC-BROWSER-
#     EVIDENCE#render-requirements-state-their-path) — the in-process tests below that used to
#     claim those rows are unlabelled unit guards now, or were deleted where the browser case
#     carries the same assertion;
#   - CIR-RENDER-ASSET-BUDGET#budget-growth-is-linear is proven HERE too: page size is the
#     bake's artifact, measured at its CLI boundary across item counts;
#   - CIR-RENDER-TOUCH#touch-target-size moved to the browser tier once ⚖-R56 gave it a number
#     (24 × 24 CSS px); its source-grep proxy here was deleted — the browser case measures the
#     drawn cells, and keyboard-tab-order already proves the cells are in the tab order.

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import allure
import pytest
import yaml

from bake.config import load_config
from bake.render import add_capacity_warnings, render_page
from bake.resolve import resolve

from evidence_helpers import given_alex, given_prior_bake, verdict, when_bake
from rules import rule

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ALEX_YAML = FIXTURES / "alex" / "circles.yaml"
CLICK_TABLE = FIXTURES / "click-destinations.yaml"
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

def _grow(config: dict, total: int) -> None:
    """Add `manual: green` items "Extra <n>" round the rings (inside-out, skipping a ring at the
    envelope's 8) until the page holds ``total`` items — no ring past CIR-RENDER-CAPACITY's
    envelope, so no capacity warning joins the page; an extra in a ring that declares shares
    (children: 0.5) declares 0.5 too, so no mixed-shares warning joins either."""
    rings = config["rings"]
    n, k = sum(len(r["items"]) for r in rings), 0
    while n < total:
        ring = rings[k % len(rings)]
        k += 1
        if len(ring["items"]) >= 8:
            continue
        extra = {"id": f"extra-{n + 1}", "label": f"Extra {n + 1}", "status": {"manual": "green"}}
        if any("share" in i for i in ring["items"]):
            extra["share"] = 0.5
        ring["items"].append(extra)
        n += 1


class TestRenderAssetBudget:
    """CIR-RENDER-ASSET-BUDGET — #budget-built-page-is-small is the browser's
    (tests/browser/test_render_rows.py); #budget-growth-is-linear is measured here, on the page
    the bake writes."""

    @rule("CIR-RENDER-ASSET-BUDGET")
    def test_budget_growth_is_linear(self, alex_copy, tmp_path: Path) -> None:
        """CIR-RENDER-ASSET-BUDGET#budget-growth-is-linear — 9 → 18 items: growth is linear in
        items, not in libraries.

        Linear in items = every item costs the page the same bytes, whatever the count: pages at
        9, 18 and 27 items (equal steps of 9) grow by equal amounts. The criterion: the 18 → 27
        step is within 10% of the 9 → 18 step — the only per-item variation is the digits of
        coordinates and ids ("extra-9" vs "extra-10"); a per-page cost that grew with the item
        count (anything not linear) breaks it. Rings stay inside the envelope, so no warning
        text joins one page and not the other."""
        config = given_alex(alex_copy, "items added round the rings to 18 in total (Extra <n>, manual: green)",
                            lambda c: _grow(c, 18))
        sizes = {}
        for total in (9, 27):
            data = yaml.safe_load((FIXTURES / "alex" / "circles.yaml").read_text(encoding="utf-8"))
            _grow(data, total)
            other = config.parent / f"circles-{total}.yaml"
            # (the derived config is not attached: the prior bake's data.json, attached, shows it)
            with allure.step(f"Given: alex/circles-{total}.yaml — items added round the rings to {total} in total"):
                other.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            given_prior_bake(tmp_path, other, why=f"the {total}-item page")
            sizes[total] = (tmp_path / "out" / "index.html").stat().st_size
        run = when_bake(config)
        sizes[18] = (run.out_dir / "index.html").stat().st_size
        step_1, step_2 = sizes[18] - sizes[9], sizes[27] - sizes[18]
        verdict("exit code", run.exit_code, 0)
        verdict(f"index.html bytes at 9 / 18 / 27 items: {sizes[9]} / {sizes[18]} / {sizes[27]} — "
                f"|step 18→27 − step 9→18| (step 9→18 = {step_1})", abs(step_2 - step_1), round(0.1 * step_1), op="<=")


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

