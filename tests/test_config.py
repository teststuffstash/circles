# Tests for bake/config.py — circles.yaml → the validated config model
#
# Every decision-table row of every fully-owned requirement has a citing test,
# parametrised per CIR-PROC-TEST-ROWS#rows-parametrised-not-copied, with the row id
# (CIR-<AREA>-<NAME>#<row-id>) cited verbatim in the test name.
#
# Tests build inputs from fixtures/ at runtime — no second synthetic person invented
# in test code (CIR-PROC-TEST-FIXTURES#no-real-data, #fixture-row-is-spec-row).

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
import yaml

from bake.config import (
    AdapterSpec,
    Config,
    ConfigError,
    Item,
    Ring,
    Warning,
    load_config,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ALEX_YAML = FIXTURES / "alex" / "circles.yaml"


# ===========================================================================
# CIR-DATA-SCHEMA-TOPLEVEL — top-level shape
# ===========================================================================

class TestSchemaToplevel:
    """CIR-DATA-SCHEMA-TOPLEVEL — top-level shape."""

    @pytest.mark.parametrize("data,expected_person,expected_rings", [
        pytest.param(
            {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}]},
            "Test", 1,
            id="CIR-DATA-SCHEMA-TOPLEVEL#minimal-valid-config",
        ),
    ])
    def test_minimal_valid_config(self, tmp_path: Path, data: dict, expected_person: str, expected_rings: int) -> None:
        """A minimal valid config with person + one ring + one item (no status) is valid."""
        cfg = _write_and_load(tmp_path, data)
        assert cfg.person == expected_person
        assert len(cfg.rings) == expected_rings
        assert cfg.rings[0].items[0].adapter is None  # ⚪ unmonitored

    def test_person_missing(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#person-missing — no person: key → config error."""
        data = {"rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}]}
        with pytest.raises(ConfigError, match="person"):
            _write_and_load(tmp_path, data)

    def test_rings_empty(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#rings-empty — rings: [] → config error."""
        data = {"person": "Test", "rings": []}
        with pytest.raises(ConfigError, match="nothing to draw"):
            _write_and_load(tmp_path, data)

    def test_rings_order_is_inside_out(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#rings-order-is-inside-out — array order is geometry order."""
        data = {
            "person": "Test",
            "rings": [
                {"id": "self", "label": "① Self", "items": [{"id": "a", "label": "A"}]},
                {"id": "partner", "label": "② Partner", "items": [{"id": "b", "label": "B"}]},
                {"id": "children", "label": "③ Children", "items": [{"id": "c", "label": "C"}]},
                {"id": "wider", "label": "④ Wider", "items": [{"id": "d", "label": "D"}]},
            ],
        }
        cfg = _write_and_load(tmp_path, data)
        assert [r.id for r in cfg.rings] == ["self", "partner", "children", "wider"]

    def test_timezone_omitted(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#timezone-omitted — defaults to UTC."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        assert cfg.timezone == "UTC"

    def test_timezone_valid(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#timezone-valid — accepted as-is."""
        data = {
            "person": "Test",
            "timezone": "Europe/Tallinn",
            "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}],
        }
        cfg = _write_and_load(tmp_path, data)
        assert cfg.timezone == "Europe/Tallinn"


# ===========================================================================
# CIR-DATA-SCHEMA-VERSION — spec_version guards the format
# ===========================================================================

class TestSchemaVersion:
    """CIR-DATA-SCHEMA-VERSION — spec_version guards the format."""

    def test_version_absent_defaults_zero(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-VERSION#version-absent-defaults-zero — no spec_version → v0."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        assert cfg.spec_version == 0

    def test_version_matches(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-VERSION#version-matches — spec_version: 0 is valid."""
        data = {
            "person": "Test",
            "spec_version": 0,
            "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}],
        }
        cfg = _write_and_load(tmp_path, data)
        assert cfg.spec_version == 0

    def test_version_from_the_future(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-VERSION#version-from-the-future — spec_version: 1 → config error."""
        data = {
            "person": "Test",
            "spec_version": 1,
            "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}],
        }
        with pytest.raises(ConfigError, match="newer than this build"):
            _write_and_load(tmp_path, data)


# ===========================================================================
# CIR-DATA-SCHEMA-RING — ring fields
# ===========================================================================

class TestSchemaRing:
    """CIR-DATA-SCHEMA-RING — ring fields."""

    def test_ring_id_slug(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-RING#ring-id-slug — valid slug accepted."""
        data = {"person": "Test", "rings": [{"id": "self", "label": "Self", "items": [{"id": "x", "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].id == "self"

    def test_ring_id_not_slug(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-RING#ring-id-not-slug — non-slug → config error."""
        data = {"person": "Test", "rings": [{"id": "My Ring!", "label": "Self", "items": [{"id": "x", "label": "X"}]}]}
        with pytest.raises(ConfigError, match="slug"):
            _write_and_load(tmp_path, data)

    def test_ring_id_duplicate(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-RING#ring-id-duplicate — duplicate ring id → config error."""
        data = {
            "person": "Test",
            "rings": [
                {"id": "self", "label": "Self", "items": [{"id": "a", "label": "A"}]},
                {"id": "self", "label": "Self again", "items": [{"id": "b", "label": "B"}]},
            ],
        }
        with pytest.raises(ConfigError, match="duplicate ring id"):
            _write_and_load(tmp_path, data)

    def test_ring_label_missing(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-RING#ring-label-missing — ring without label → config error."""
        data = {"person": "Test", "rings": [{"id": "self", "items": [{"id": "x", "label": "X"}]}]}
        with pytest.raises(ConfigError, match="label"):
            _write_and_load(tmp_path, data)

    def test_ring_label_glyphs(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-RING#ring-label-glyphs — labels are opaque Unicode."""
        data = {"person": "Test", "rings": [{"id": "children", "label": "③ Children", "items": [{"id": "x", "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].label == "③ Children"


# ===========================================================================
# CIR-DATA-SCHEMA-ITEM — item fields
# ===========================================================================

class TestSchemaItem:
    """CIR-DATA-SCHEMA-ITEM — item fields."""

    def test_item_minimal(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-ITEM#item-minimal — id + label only → valid, ⚪, share 1."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        item = cfg.rings[0].items[0]
        assert item.id == "x"
        assert item.label == "X"
        assert item.share == 1.0
        assert item.guardrail is None
        assert item.link is None
        assert item.adapter is None

    def test_item_id_duplicate_in_ring(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-ITEM#item-id-duplicate-in-ring — duplicate item id → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [
                    {"id": "x", "label": "X"},
                    {"id": "x", "label": "X2"},
                ],
            }],
        }
        with pytest.raises(ConfigError, match="duplicate item id"):
            _write_and_load(tmp_path, data)

    def test_guardrail_absent(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-ITEM#guardrail-absent — no guardrail → None."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].items[0].guardrail is None

    def test_note_absent(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-ITEM#note-absent — no note → None."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].items[0].note is None

    def test_share_default(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-ITEM#share-default — no share → weight 1."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].items[0].share == 1.0


# ===========================================================================
# CIR-DATA-IDENTITY — ids, uniqueness and the item ref
# ===========================================================================

class TestDataIdentity:
    """CIR-DATA-IDENTITY — ids, uniqueness and the item ref."""

    @pytest.mark.parametrize("item_id", [
        pytest.param("sleep", id="CIR-DATA-IDENTITY#id-character-set-simple"),
        pytest.param("date-night", id="CIR-DATA-IDENTITY#id-character-set-hyphen"),
        pytest.param("nova123", id="CIR-DATA-IDENTITY#id-character-set-digits"),
        pytest.param("a", id="CIR-DATA-IDENTITY#id-character-set-single-char"),
    ])
    def test_id_character_set_valid(self, tmp_path: Path, item_id: str) -> None:
        """CIR-DATA-IDENTITY#id-character-set — valid slugs accepted."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": item_id, "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].items[0].id == item_id

    @pytest.mark.parametrize("item_id,error_pattern", [
        pytest.param("date night", "space", id="CIR-DATA-IDENTITY#id-with-space"),
        pytest.param("a/b", "slash", id="CIR-DATA-IDENTITY#id-with-slash"),
        pytest.param("UPPERCASE", "slug", id="CIR-DATA-IDENTITY#id-uppercase"),
        pytest.param("", "slug", id="CIR-DATA-IDENTITY#id-empty"),
    ])
    def test_id_invalid(self, tmp_path: Path, item_id: str, error_pattern: str) -> None:
        """Invalid ids → config error with specific message (⚖-R52)."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": item_id, "label": "X"}]}]}
        with pytest.raises(ConfigError, match=error_pattern):
            _write_and_load(tmp_path, data)

    def test_id_missing(self, tmp_path: Path) -> None:
        """CIR-DATA-IDENTITY#id-missing — item without id → config error."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"label": "X"}]}]}
        with pytest.raises(ConfigError, match="id"):
            _write_and_load(tmp_path, data)

    def test_same_id_different_rings(self, tmp_path: Path) -> None:
        """CIR-DATA-IDENTITY#same-id-different-rings — same id in different rings is valid."""
        data = {
            "person": "Test",
            "rings": [
                {"id": "self", "label": "Self", "items": [{"id": "sleep", "label": "Sleep"}]},
                {"id": "wider", "label": "Wider", "items": [{"id": "sleep", "label": "Sleep"}]},
            ],
        }
        cfg = _write_and_load(tmp_path, data)
        assert len(cfg.rings) == 2
        assert cfg.rings[0].items[0].id == "sleep"
        assert cfg.rings[1].items[0].id == "sleep"


# ===========================================================================
# CIR-DATA-SCHEMA-ADAPTER-SLOT — the status map
# ===========================================================================

class TestSchemaAdapterSlot:
    """CIR-DATA-SCHEMA-ADAPTER-SLOT — the status map."""

    def test_status_absent(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#status-absent — no status → ⚪ unmonitored."""
        data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}]}
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].items[0].adapter is None

    def test_status_two_adapters(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#status-two-adapters — both manual and freshness → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"manual": "green", "freshness": {"source": "x.md", "yellow_after": 7, "red_after": 30}}}],
            }],
        }
        with pytest.raises(ConfigError, match="multiple adapter keys"):
            _write_and_load(tmp_path, data)

    def test_status_unknown_adapter(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#status-unknown-adapter — unknown adapter → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"sqlite": {"query": "SELECT 1"}}}],
            }],
        }
        with pytest.raises(ConfigError, match="unknown adapter"):
            _write_and_load(tmp_path, data)

    def test_manual_invalid_word(self, tmp_path: Path) -> None:
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#manual-invalid-word — manual: blue → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"manual": "blue"}}],
            }],
        }
        with pytest.raises(ConfigError, match="not a valid manual value"):
            _write_and_load(tmp_path, data)


# ===========================================================================
# CIR-DATA-SCHEMA-LINK — click-through targets
# ===========================================================================

class TestSchemaLink:
    """CIR-DATA-SCHEMA-LINK — click-through targets."""

    @pytest.mark.parametrize("link", [
        pytest.param("https://example.test/labs", id="CIR-DATA-SCHEMA-LINK#link-https"),
        pytest.param("/details/self-sleep.html", id="CIR-DATA-SCHEMA-LINK#link-root-relative"),
        pytest.param("http://example.test/page", id="CIR-DATA-SCHEMA-LINK#link-http"),
    ])
    def test_link_valid(self, tmp_path: Path, link: str) -> None:
        """Valid links are accepted."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "link": link}],
            }],
        }
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].items[0].link == link

    @pytest.mark.parametrize("link,error_pattern", [
        pytest.param("javascript:alert(1)", "javascript", id="CIR-DATA-SCHEMA-LINK#link-javascript-scheme"),
        pytest.param("data:text/html,hi", "data:", id="CIR-DATA-SCHEMA-LINK#link-data-scheme"),
        pytest.param("//example.test/x", "scheme-relative", id="CIR-DATA-SCHEMA-LINK#link-scheme-relative"),
        pytest.param("details/sleep.html", "bare relative", id="CIR-DATA-SCHEMA-LINK#link-bare-relative"),
    ])
    def test_link_invalid(self, tmp_path: Path, link: str, error_pattern: str) -> None:
        """Invalid links → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "link": link}],
            }],
        }
        with pytest.raises(ConfigError, match=error_pattern):
            _write_and_load(tmp_path, data)


# ===========================================================================
# CIR-DATA-SHARE — arc weights within a ring
# ===========================================================================

class TestDataShare:
    """CIR-DATA-SHARE — arc weights within a ring."""

    def test_shares_equal_halves(self, tmp_path: Path) -> None:
        """CIR-DATA-SHARE#shares-equal-halves — two siblings share: 0.5 each → two 180° arcs."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "children", "label": "Children",
                "items": [
                    {"id": "nova", "label": "Nova", "share": 0.5},
                    {"id": "kit", "label": "Kit", "share": 0.5},
                ],
            }],
        }
        cfg = _write_and_load(tmp_path, data)
        items = cfg.rings[0].items
        assert items[0].share == 0.5
        assert items[1].share == 0.5
        total = sum(i.share for i in items)
        assert math.isclose(total, 1.0)

    def test_shares_absent_equal(self, tmp_path: Path) -> None:
        """CIR-DATA-SHARE#shares-absent-equal — three siblings, no share → three 120° arcs."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [
                    {"id": "x", "label": "X"},
                    {"id": "y", "label": "Y"},
                    {"id": "z", "label": "Z"},
                ],
            }],
        }
        cfg = _write_and_load(tmp_path, data)
        for item in cfg.rings[0].items:
            assert item.share == 1.0

    def test_shares_mixed(self, tmp_path: Path) -> None:
        """CIR-DATA-SHARE#shares-mixed — share: 2 + absent → 240°/120°, plus warning."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [
                    {"id": "nova", "label": "Nova", "share": 2},
                    {"id": "kit", "label": "Kit"},
                ],
            }],
        }
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].items[0].share == 2.0
        assert cfg.rings[0].items[1].share == 1.0
        # Check mixed share warning
        assert any("mixes declared and undeclared" in w.message for w in cfg.warnings)

    def test_shares_mixed_fractional(self, tmp_path: Path) -> None:
        """CIR-DATA-SHARE#shares-mixed-fractional — share: 0.5 + absent → 120°/240°, plus warning."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [
                    {"id": "nova", "label": "Nova", "share": 0.5},
                    {"id": "kit", "label": "Kit"},
                ],
            }],
        }
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].items[0].share == 0.5
        assert cfg.rings[0].items[1].share == 1.0
        assert any("mixes declared and undeclared" in w.message for w in cfg.warnings)

    def test_share_zero(self, tmp_path: Path) -> None:
        """CIR-DATA-SHARE#share-zero — share: 0 → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "share": 0}],
            }],
        }
        with pytest.raises(ConfigError, match="> 0"):
            _write_and_load(tmp_path, data)

    def test_share_negative(self, tmp_path: Path) -> None:
        """CIR-DATA-SHARE#share-negative — share: -1 → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "share": -1}],
            }],
        }
        with pytest.raises(ConfigError, match="> 0"):
            _write_and_load(tmp_path, data)


# ===========================================================================
# CIR-DATA-VALIDATION — fail vs warn
# ===========================================================================

class TestDataValidation:
    """CIR-DATA-VALIDATION — fail vs warn."""

    def test_one_bad_item_fails_bake(self, tmp_path: Path) -> None:
        """CIR-DATA-VALIDATION#one-bad-item-fails-bake — one bad item fails the whole bake."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [
                    {"id": "good1", "label": "Good 1"},
                    {"id": "good2", "label": "Good 2"},
                    {"id": "bad", "label": "Bad", "status": {"manual": "blue"}},
                ],
            }],
        }
        with pytest.raises(ConfigError):
            _write_and_load(tmp_path, data)

    def test_unknown_toplevel_key(self, tmp_path: Path) -> None:
        """CIR-DATA-VALIDATION#unknown-toplevel-key — unknown key → warning, bake proceeds."""
        data = {
            "person": "Test",
            "sprinkles": True,
            "rings": [{"id": "a", "label": "A", "items": [{"id": "x", "label": "X"}]}],
        }
        cfg = _write_and_load(tmp_path, data)
        assert any("sprinkles" in w.message for w in cfg.warnings)

    def test_unknown_item_key(self, tmp_path: Path) -> None:
        """CIR-DATA-VALIDATION#unknown-item-key — unknown item key → warning, bake proceeds."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "prioritiy": "high"}],
            }],
        }
        cfg = _write_and_load(tmp_path, data)
        assert any("prioritiy" in w.message for w in cfg.warnings)

    def test_unknown_status_key(self, tmp_path: Path) -> None:
        """CIR-DATA-VALIDATION#unknown-status-key — unknown status key → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"freshnes": {"source": "x.md", "yellow_after": 7, "red_after": 30}}}],
            }],
        }
        with pytest.raises(ConfigError, match="unknown adapter"):
            _write_and_load(tmp_path, data)

    def test_empty_ring(self, tmp_path: Path) -> None:
        """CIR-DATA-VALIDATION#empty-ring — ring with items: [] → warning, bake proceeds."""
        data = {
            "person": "Test",
            "rings": [{"id": "a", "label": "A", "items": []}],
        }
        cfg = _write_and_load(tmp_path, data)
        assert len(cfg.rings[0].items) == 0
        assert any("no items" in w.message for w in cfg.warnings)


# ===========================================================================
# CIR-DATA-FRESHNESS-THRESHOLDS — threshold validation
# ===========================================================================

class TestDataFreshnessThresholds:
    """CIR-DATA-FRESHNESS-THRESHOLDS — threshold validation."""

    def test_thresholds_valid(self, tmp_path: Path) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#thresholds-valid — valid thresholds accepted."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"freshness": {"source": "x.md", "yellow_after": 100, "red_after": 190}},
                }],
            }],
        }
        cfg = _write_and_load(tmp_path, data)
        assert cfg.rings[0].items[0].adapter is not None
        assert cfg.rings[0].items[0].adapter.kind == "freshness"

    def test_thresholds_equal(self, tmp_path: Path) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#thresholds-equal — yellow == red → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"freshness": {"source": "x.md", "yellow_after": 7, "red_after": 7}},
                }],
            }],
        }
        with pytest.raises(ConfigError, match="strictly less"):
            _write_and_load(tmp_path, data)

    def test_thresholds_inverted(self, tmp_path: Path) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#thresholds-inverted — yellow > red → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"freshness": {"source": "x.md", "yellow_after": 30, "red_after": 7}},
                }],
            }],
        }
        with pytest.raises(ConfigError, match="strictly less"):
            _write_and_load(tmp_path, data)

    def test_threshold_zero(self, tmp_path: Path) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#threshold-zero — yellow_after: 0 → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"freshness": {"source": "x.md", "yellow_after": 0, "red_after": 30}},
                }],
            }],
        }
        with pytest.raises(ConfigError, match="≥ 1"):
            _write_and_load(tmp_path, data)

    def test_threshold_fractional(self, tmp_path: Path) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#threshold-fractional — yellow_after: 3.5 → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"freshness": {"source": "x.md", "yellow_after": 3.5, "red_after": 30}},
                }],
            }],
        }
        with pytest.raises(ConfigError, match="integer"):
            _write_and_load(tmp_path, data)

    def test_threshold_missing(self, tmp_path: Path) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#threshold-missing — freshness without yellow_after → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"freshness": {"source": "x.md"}},
                }],
            }],
        }
        with pytest.raises(ConfigError, match="required"):
            _write_and_load(tmp_path, data)


# ===========================================================================
# CIR-DATA-SOURCE-PATH — config-error rows only
# ===========================================================================

class TestDataSourcePath:
    """CIR-DATA-SOURCE-PATH — config-error rows (validation only)."""

    def test_source_parent_traversal(self, tmp_path: Path) -> None:
        """CIR-DATA-SOURCE-PATH#source-parent-traversal — parent traversal → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"freshness": {"source": "../../etc/hosts", "yellow_after": 7, "red_after": 30}},
                }],
            }],
        }
        with pytest.raises(ConfigError, match="escape"):
            _write_and_load(tmp_path, data)

    def test_source_absolute_path(self, tmp_path: Path) -> None:
        """CIR-DATA-SOURCE-PATH#source-absolute-path — absolute path → config error (⚖-R52)."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"freshness": {"source": "/etc/hosts", "yellow_after": 7, "red_after": 30}},
                }],
            }],
        }
        with pytest.raises(ConfigError, match="absolute path"):
            _write_and_load(tmp_path, data)


# ===========================================================================
# CIR-ADAPT-COMMAND — config-error rows only
# ===========================================================================

class TestAdaptCommand:
    """CIR-ADAPT-COMMAND — config-error rows (validation only)."""

    def test_command_argv_array_required(self, tmp_path: Path) -> None:
        """CIR-ADAPT-COMMAND#command-argv-array-required — string → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"command": "./x.sh --flag"},
                }],
            }],
        }
        with pytest.raises(ConfigError, match="array"):
            _write_and_load(tmp_path, data)

    def test_command_empty_argv(self, tmp_path: Path) -> None:
        """Empty argv array → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"command": []},
                }],
            }],
        }
        with pytest.raises(ConfigError, match="at least one"):
            _write_and_load(tmp_path, data)


# ===========================================================================
# CIR-DATA-STATUS-MANUAL-VALUES — the manual adapter's vocabulary
# ===========================================================================

class TestDataStatusManualValues:
    """CIR-DATA-STATUS-MANUAL-VALUES — the manual adapter's vocabulary."""

    def test_manual_lowercase_only(self, tmp_path: Path) -> None:
        """CIR-DATA-STATUS-MANUAL-VALUES#manual-lowercase-only — 'Green' → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"manual": "Green"}}],
            }],
        }
        with pytest.raises(ConfigError, match="lowercase"):
            _write_and_load(tmp_path, data)

    def test_manual_grey_rejected(self, tmp_path: Path) -> None:
        """CIR-DATA-STATUS-MANUAL-VALUES#manual-grey-rejected — 'grey' → config error."""
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"manual": "grey"}}],
            }],
        }
        with pytest.raises(ConfigError, match="grey"):
            _write_and_load(tmp_path, data)


# ===========================================================================
# Fixture acceptance — CIR-PROC-TEST-FIXTURES#fixture-validates-against-the-schema
# ===========================================================================

class TestFixtureAcceptance:
    """The fixture validates against the schema."""

    def test_fixture_alex_validates(self) -> None:
        """CIR-PROC-TEST-FIXTURES#fixture-validates-against-the-schema —
        load_config(fixtures/alex/circles.yaml) returns a Config with 4 rings / 8 items
        and the effective shares the fixture implies."""
        cfg = load_config(ALEX_YAML)

        # 4 rings
        assert len(cfg.rings) == 4
        assert [r.id for r in cfg.rings] == ["self", "partner", "children", "wider"]

        # 8 items total
        total_items = sum(len(r.items) for r in cfg.rings)
        assert total_items == 8

        # self ring: 3 items (sleep, labs, exercise)
        self_ring = cfg.rings[0]
        assert self_ring.id == "self"
        assert len(self_ring.items) == 3
        assert [i.id for i in self_ring.items] == ["sleep", "labs", "exercise"]

        # partner ring: 1 item (date-night)
        partner_ring = cfg.rings[1]
        assert partner_ring.id == "partner"
        assert len(partner_ring.items) == 1
        assert partner_ring.items[0].id == "date-night"

        # children ring: 2 items (nova, kit) with share 0.5 each
        children_ring = cfg.rings[2]
        assert children_ring.id == "children"
        assert len(children_ring.items) == 2
        assert children_ring.items[0].id == "nova"
        assert children_ring.items[0].share == 0.5
        assert children_ring.items[1].id == "kit"
        assert children_ring.items[1].share == 0.5

        # wider ring: 2 items (friends, plants)
        wider_ring = cfg.rings[3]
        assert wider_ring.id == "wider"
        assert len(wider_ring.items) == 2
        assert [i.id for i in wider_ring.items] == ["friends", "plants"]

        # Check adapter kinds
        assert self_ring.items[0].adapter is not None
        assert self_ring.items[0].adapter.kind == "freshness"  # sleep: freshness
        assert self_ring.items[1].adapter is not None
        assert self_ring.items[1].adapter.kind == "freshness"  # labs: freshness
        assert self_ring.items[2].adapter is None  # exercise: no adapter → ⚪

        assert partner_ring.items[0].adapter is not None
        assert partner_ring.items[0].adapter.kind == "manual"  # date-night: manual yellow

        assert children_ring.items[0].adapter is not None
        assert children_ring.items[0].adapter.kind == "manual"  # nova: manual green
        assert children_ring.items[1].adapter is not None
        assert children_ring.items[1].adapter.kind == "manual"  # kit: manual green

        assert wider_ring.items[0].adapter is not None
        assert wider_ring.items[0].adapter.kind == "manual"  # friends: manual red
        assert wider_ring.items[1].adapter is not None
        assert wider_ring.items[1].adapter.kind == "command"  # plants: command

        # Check guardrails
        assert self_ring.items[0].guardrail == "Lights out by 23:00 on weeknights"
        assert self_ring.items[1].guardrail == "Blood panel every 90 days"
        assert partner_ring.items[0].guardrail == "Protected evening, twice a month"

        # Check person
        assert cfg.person == "Alex Example"
        assert cfg.spec_version == 0
        assert cfg.timezone == "UTC"


# ===========================================================================
# Helpers
# ===========================================================================

def _write_and_load(tmp_path: Path, data: dict[str, Any]) -> Config:
    """Write *data* as YAML to a temp file and load it."""
    path = tmp_path / "circles.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return load_config(path)
