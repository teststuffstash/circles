"""Tests for config validation — CIR-DATA-VALIDATION / CIR-DATA-SCHEMA-*.

Every test cites its spec row as CIR-<AREA>-<NAME>#<row-id> verbatim (CIR-PROC-TEST-ROWS).
Parametrised over table rows, never copy-pasted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bake.validate import (
    ConfigError,
    validate,
    validate_toplevel,
    validate_version,
    validate_rings,
    validate_source_paths,
    detect_mixed_shares,
    load_config,
)


# --- Helpers ---

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _cfg(**overrides) -> dict:
    """Build a minimal valid config, then override."""
    base = {
        "person": "Test Person",
        "rings": [
            {
                "id": "test",
                "label": "Test Ring",
                "items": [
                    {"id": "item1", "label": "Item 1"},
                ],
            }
        ],
    }
    base.update(overrides)
    return base


def _write_yaml(tmp_path: Path, config: dict) -> Path:
    path = tmp_path / "circles.yaml"
    with open(path, "w") as f:
        yaml.dump(config, f)
    return path


# ============================================================
# CIR-DATA-SCHEMA-TOPLEVEL
# ============================================================


class TestToplevel:
    """CIR-DATA-SCHEMA-TOPLEVEL — top-level config shape."""

    def test_person_missing(self):
        """CIR-DATA-SCHEMA-TOPLEVEL#person-missing"""
        cfg = _cfg()
        del cfg["person"]
        with pytest.raises(ConfigError, match="person"):
            validate_toplevel(cfg, Path("/fake/circles.yaml"))

    def test_rings_empty(self):
        """CIR-DATA-SCHEMA-TOPLEVEL#rings-empty"""
        cfg = _cfg(rings=[])
        with pytest.raises(ConfigError, match="rings"):
            validate_toplevel(cfg, Path("/fake/circles.yaml"))

    def test_rings_not_a_list(self):
        """CIR-DATA-SCHEMA-TOPLEVEL#rings-empty — non-list rings"""
        cfg = _cfg(rings="not-a-list")
        with pytest.raises(ConfigError, match="rings"):
            validate_toplevel(cfg, Path("/fake/circles.yaml"))


# ============================================================
# CIR-DATA-SCHEMA-VERSION
# ============================================================


class TestVersion:
    """CIR-DATA-SCHEMA-VERSION — spec_version validation."""

    def test_version_from_the_future(self):
        """CIR-DATA-SCHEMA-VERSION#version-from-the-future"""
        cfg = _cfg(spec_version=1)
        with pytest.raises(ConfigError, match="newer"):
            validate_version(cfg)

    def test_version_zero_ok(self):
        """v0 is accepted."""
        cfg = _cfg(spec_version=0)
        validate_version(cfg)  # no error

    def test_version_missing_defaults_zero(self):
        """Missing spec_version defaults to 0."""
        cfg = _cfg()
        validate_version(cfg)  # no error

    def test_version_not_int(self):
        """Non-integer spec_version is rejected."""
        cfg = _cfg(spec_version="v1")
        with pytest.raises(ConfigError, match="integer"):
            validate_version(cfg)


# ============================================================
# CIR-DATA-SCHEMA-RING
# ============================================================


class TestRings:
    """CIR-DATA-SCHEMA-RING — ring-level validation."""

    def test_ring_id_not_slug(self):
        """CIR-DATA-SCHEMA-RING#ring-id-not-slug"""
        cfg = _cfg(rings=[{"id": "Bad ID!", "label": "Bad", "items": []}])
        with pytest.raises(ConfigError, match="slug"):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    def test_ring_id_duplicate(self):
        """CIR-DATA-SCHEMA-RING#ring-id-duplicate"""
        cfg = _cfg(rings=[
            {"id": "dup", "label": "First", "items": []},
            {"id": "dup", "label": "Second", "items": []},
        ])
        with pytest.raises(ConfigError, match="duplicate"):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    def test_ring_label_missing(self):
        """CIR-DATA-SCHEMA-RING#ring-label-missing"""
        cfg = _cfg(rings=[{"id": "test", "items": []}])
        with pytest.raises(ConfigError, match="label"):
            validate_rings(cfg, Path("/fake/circles.yaml"))


# ============================================================
# CIR-DATA-IDENTITY
# ============================================================


class TestIdentity:
    """CIR-DATA-IDENTITY — item identity validation."""

    def test_id_missing(self):
        """CIR-DATA-IDENTITY#id-missing"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"label": "No ID"}],
        }])
        with pytest.raises(ConfigError, match="id"):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    def test_id_character_set(self):
        """CIR-DATA-IDENTITY#id-character-set"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "UPPERCASE", "label": "Bad"}],
        }])
        with pytest.raises(ConfigError, match="must match"):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    def test_id_with_space_or_slash(self):
        """CIR-DATA-IDENTITY#id-with-space-or-slash"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "my/item", "label": "Bad"}],
        }])
        with pytest.raises(ConfigError, match="slash"):
            validate_rings(cfg, Path("/fake/circles.yaml"))


# ============================================================
# CIR-DATA-SCHEMA-ITEM
# ============================================================


class TestItems:
    """CIR-DATA-SCHEMA-ITEM — item-level validation."""

    def test_item_id_duplicate_in_ring(self):
        """CIR-DATA-SCHEMA-ITEM#item-id-duplicate-in-ring"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [
                {"id": "dup", "label": "First"},
                {"id": "dup", "label": "Second"},
            ],
        }])
        with pytest.raises(ConfigError, match="duplicate"):
            validate_rings(cfg, Path("/fake/circles.yaml"))


# ============================================================
# CIR-DATA-SCHEMA-LINK
# ============================================================


class TestLink:
    """CIR-DATA-SCHEMA-LINK — link field validation."""

    @pytest.mark.parametrize("link,expected", [
        pytest.param("javascript:alert(1)", "dangerous", id="link-javascript-scheme"),
        pytest.param("data:text/html,<script>", "dangerous", id="link-data-scheme"),
        pytest.param("//evil.com/foo", "scheme-relative", id="link-scheme-relative"),
        pytest.param("relative/path", "bare relative", id="link-bare-relative"),
    ])
    def test_link_rejected(self, link, expected):
        """CIR-DATA-SCHEMA-LINK — dangerous or ambiguous links."""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "item1", "label": "Item", "link": link}],
        }])
        with pytest.raises(ConfigError, match=expected):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    @pytest.mark.parametrize("link", [
        "https://example.com",
        "http://example.com",
        "/absolute/path",
    ])
    def test_link_accepted(self, link):
        """Valid links pass validation."""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "item1", "label": "Item", "link": link}],
        }])
        validate_rings(cfg, Path("/fake/circles.yaml"))  # no error


# ============================================================
# CIR-DATA-SHARE
# ============================================================


class TestShare:
    """CIR-DATA-SHARE — share field validation."""

    def test_share_zero(self):
        """CIR-DATA-SHARE#share-zero"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "item1", "label": "Item", "share": 0}],
        }])
        with pytest.raises(ConfigError, match="> 0"):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    def test_share_negative(self):
        """Negative share is rejected."""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "item1", "label": "Item", "share": -1}],
        }])
        with pytest.raises(ConfigError, match="> 0"):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    def test_shares_mixed(self):
        """CIR-DATA-SHARE#shares-mixed"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [
                {"id": "a", "label": "A", "share": 2},
                {"id": "b", "label": "B"},
            ],
        }])
        warnings = detect_mixed_shares(cfg)
        assert len(warnings) == 1
        assert "mixes declared" in warnings[0].message


# ============================================================
# CIR-DATA-SCHEMA-ADAPTER-SLOT
# ============================================================


class TestAdapterSlot:
    """CIR-DATA-SCHEMA-ADAPTER-SLOT — status block validation."""

    def test_empty_status_block(self):
        """CIR-DATA-STATUS-RESOLUTION#empty-status-block"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "item1", "label": "Item", "status": {}}],
        }])
        with pytest.raises(ConfigError, match="empty"):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    def test_status_two_adapters(self):
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#status-two-adapters"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{
                "id": "item1", "label": "Item",
                "status": {"manual": "green", "freshness": {"source": "x", "yellow_after": 1, "red_after": 2}},
            }],
        }])
        with pytest.raises(ConfigError, match="2 adapters"):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    def test_status_unknown_adapter(self):
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#status-unknown-adapter"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "item1", "label": "Item", "status": {"sqlite": {}}}],
        }])
        with pytest.raises(ConfigError, match="unknown adapter"):
            validate_rings(cfg, Path("/fake/circles.yaml"))


# ============================================================
# CIR-DATA-STATUS-MANUAL-VALUES
# ============================================================


class TestManualValues:
    """CIR-DATA-STATUS-MANUAL-VALUES — manual adapter vocabulary."""

    @pytest.mark.parametrize("value,expected_match", [
        pytest.param("Green", "not valid", id="manual-lowercase-only"),
        pytest.param("grey", "not valid", id="manual-grey-rejected"),
        pytest.param("amber", "not valid", id="manual-unknown-word"),
    ])
    def test_manual_invalid(self, value, expected_match):
        """CIR-DATA-STATUS-MANUAL-VALUES — invalid manual values."""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "item1", "label": "Item", "status": {"manual": value}}],
        }])
        with pytest.raises(ConfigError, match=expected_match):
            validate_rings(cfg, Path("/fake/circles.yaml"))

    @pytest.mark.parametrize("value", ["green", "yellow", "red"])
    def test_manual_valid(self, value):
        """Valid manual values pass."""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "item1", "label": "Item", "status": {"manual": value}}],
        }])
        validate_rings(cfg, Path("/fake/circles.yaml"))  # no error


# ============================================================
# CIR-DATA-FRESHNESS-THRESHOLDS
# ============================================================


class TestFreshnessThresholds:
    """CIR-DATA-FRESHNESS-THRESHOLDS — freshness adapter validation."""

    @pytest.mark.parametrize("thresholds,expected_match", [
        pytest.param(
            {"source": "x", "yellow_after": 1.5, "red_after": 30},
            "integer",
            id="threshold-fractional-yellow",
        ),
        pytest.param(
            {"source": "x", "yellow_after": 7, "red_after": 30.5},
            "integer",
            id="threshold-fractional-red",
        ),
        pytest.param(
            {"source": "x", "yellow_after": 0, "red_after": 30},
            "≥ 1",
            id="threshold-zero-yellow",
        ),
        pytest.param(
            {"source": "x", "yellow_after": 7, "red_after": 0},
            "≥ 1",
            id="threshold-zero-red",
        ),
        pytest.param(
            {"source": "x", "yellow_after": 30, "red_after": 7},
            "must be <",
            id="thresholds-equal-or-inverted",
        ),
        pytest.param(
            {"source": "x", "yellow_after": 7, "red_after": 7},
            "must be <",
            id="thresholds-equal",
        ),
    ])
    def test_threshold_invalid(self, thresholds, expected_match):
        """CIR-DATA-FRESHNESS-THRESHOLDS — invalid threshold values."""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{"id": "item1", "label": "Item", "status": {"freshness": thresholds}}],
        }])
        with pytest.raises(ConfigError, match=expected_match):
            validate_rings(cfg, Path("/fake/circles.yaml"))


# ============================================================
# CIR-DATA-SOURCE-PATH
# ============================================================


class TestSourcePath:
    """CIR-DATA-SOURCE-PATH — source path validation."""

    def test_source_parent_traversal(self, tmp_path):
        """CIR-DATA-SOURCE-PATH#source-parent-traversal"""
        config_path = tmp_path / "circles.yaml"
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{
                "id": "item1", "label": "Item",
                "status": {"freshness": {"source": "../outside.yaml", "yellow_after": 7, "red_after": 30}},
            }],
        }])
        with pytest.raises(ConfigError, match="escapes"):
            validate_source_paths(cfg, config_path)

    def test_source_absolute_path(self, tmp_path):
        """CIR-DATA-SOURCE-PATH#source-absolute-path"""
        config_path = tmp_path / "circles.yaml"
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [{
                "id": "item1", "label": "Item",
                "status": {"freshness": {"source": "/etc/passwd", "yellow_after": 7, "red_after": 30}},
            }],
        }])
        with pytest.raises(ConfigError, match="escapes"):
            validate_source_paths(cfg, config_path)


# ============================================================
# CIR-DATA-STATUS-RESOLUTION — full resolution table
# ============================================================


class TestStatusResolution:
    """CIR-DATA-STATUS-RESOLUTION — the canonical resolution table."""

    @pytest.mark.parametrize("config_mod,expected_status,expected_reason", [
        pytest.param(
            {"rings": [{"id": "t", "label": "T", "items": [{"id": "a", "label": "A"}]}]},
            "grey", "by-choice",
            id="no-adapter-declared",
        ),
        pytest.param(
            {"rings": [{"id": "t", "label": "T", "items": [{"id": "a", "label": "A", "status": {"manual": "green"}}]}]},
            "green", None,
            id="manual-green",
        ),
        pytest.param(
            {"rings": [{"id": "t", "label": "T", "items": [{"id": "a", "label": "A", "status": {"manual": "yellow"}}]}]},
            "yellow", None,
            id="manual-yellow",
        ),
        pytest.param(
            {"rings": [{"id": "t", "label": "T", "items": [{"id": "a", "label": "A", "status": {"manual": "red"}}]}]},
            "red", None,
            id="manual-red",
        ),
    ])
    def test_resolution(self, config_mod, expected_status, expected_reason):
        """CIR-DATA-STATUS-RESOLUTION — adapter resolution produces correct status."""
        from bake.adapters import resolve_adapter_p0

        cfg = _cfg(**config_mod)
        ring = cfg["rings"][0]
        item = ring["items"][0]
        status = item.get("status")

        if status is None:
            # No adapter — result is None
            result = None
        else:
            adapter_key = next(iter(status.keys()))
            adapter_value = status[adapter_key]
            result = resolve_adapter_p0(adapter_key, adapter_value)

        if result is None or (result.is_failure and not result.is_success):
            assert expected_status == "grey"
            if result is not None and result.failure_reason:
                assert expected_reason == "by-failure"
            else:
                assert expected_reason == "by-choice"
        else:
            assert result.status == expected_status


# ============================================================
# CIR-DATA-CONFIG-ERROR-FAILS
# ============================================================


class TestConfigErrorFails:
    """CIR-DATA-CONFIG-ERROR-FAILS — config errors abort the bake."""

    def test_config_error_aborts_whole_bake(self, tmp_path):
        """CIR-DATA-CONFIG-ERROR-FAILS#config-error-aborts-whole-bake"""
        cfg = _cfg(rings=[{
            "id": "test", "label": "Test",
            "items": [
                {"id": "good", "label": "Good"},
                {"id": "bad", "label": "Bad", "status": {"manual": "green", "freshness": {"source": "x", "yellow_after": 1, "red_after": 2}}},
            ],
        }])
        config_path = _write_yaml(tmp_path, cfg)
        loaded = load_config(config_path)
        with pytest.raises(ConfigError, match="2 adapters"):
            validate(loaded, config_path)

    def test_message_names_the_item(self, tmp_path):
        """CIR-DATA-CONFIG-ERROR-FAILS#message-names-the-item"""
        cfg = _cfg(rings=[{
            "id": "children", "label": "Children",
            "items": [
                {"id": "kit", "label": "Kit", "status": {"manual": "green", "freshness": {"source": "x", "yellow_after": 1, "red_after": 2}}},
            ],
        }])
        config_path = _write_yaml(tmp_path, cfg)
        loaded = load_config(config_path)
        with pytest.raises(ConfigError) as exc:
            validate(loaded, config_path)
        assert "children/kit" in str(exc.value)


# ============================================================
# CIR-DATA-FAILURE-IS-GREY
# ============================================================


class TestFailureIsGrey:
    """CIR-DATA-FAILURE-IS-GREY — adapter failures are always grey."""

    def test_failure_never_red(self):
        """CIR-DATA-FAILURE-IS-GREY#failure-never-red"""
        from bake.adapters import resolve_adapter_p0
        result = resolve_adapter_p0("freshness", {"source": "x", "yellow_after": 7, "red_after": 30})
        assert result.is_failure
        assert not result.is_success

    def test_failure_never_green(self):
        """CIR-DATA-FAILURE-IS-GREY#failure-never-green"""
        from bake.adapters import resolve_adapter_p0
        result = resolve_adapter_p0("command", ["./script.sh"])
        assert result.is_failure
        assert not result.is_success


# ============================================================
# CIR-DATA-GREY-REASON
# ============================================================


class TestGreyReason:
    """CIR-DATA-GREY-REASON — two reasons for grey."""

    def test_unmonitored_by_choice(self):
        """CIR-DATA-GREY-REASON#unmonitored-by-choice"""
        from bake.artifact import _build_item_artifact
        item = {"id": "test", "label": "Test"}
        artifact = _build_item_artifact(item, "ring/test", None)
        assert artifact["status"] == "grey"
        assert artifact["grey_reason"] == "by-choice"

    def test_unmonitored_by_failure(self):
        """CIR-DATA-GREY-REASON#unmonitored-by-failure"""
        from bake.artifact import _build_item_artifact
        from bake.adapters import AdapterResult
        item = {"id": "test", "label": "Test"}
        result = AdapterResult(failure_reason="something broke")
        artifact = _build_item_artifact(item, "ring/test", result)
        assert artifact["status"] == "grey"
        assert artifact["grey_reason"] == "by-failure"


# ============================================================
# CIR-ADAPT-MANUAL
# ============================================================


class TestManualAdapter:
    """CIR-ADAPT-MANUAL — manual adapter resolution."""

    @pytest.mark.parametrize("value,expected", [
        pytest.param("green", "green", id="manual-green"),
        pytest.param("yellow", "yellow", id="manual-yellow"),
        pytest.param("red", "red", id="manual-red"),
    ])
    def test_resolve_manual(self, value, expected):
        """CIR-ADAPT-MANUAL — manual adapter returns the declared status."""
        from bake.adapters import resolve_manual
        result = resolve_manual(value)
        assert result.status == expected
        assert result.is_success


# ============================================================
# CIR-BAKE-ARTIFACT — artifact shape
# ============================================================


class TestArtifactShape:
    """CIR-BAKE-ARTIFACT — the baked artifact shape."""

    def test_artifact_fixture_roundtrip(self, tmp_path):
        """CIR-BAKE-ARTIFACT#artifact-fixture-roundtrip

        Bake the fixture at the reference date and verify the artifact shape.
        """
        from bake.cli import main

        output_dir = tmp_path / "out"
        exit_code = main([
            str(FIXTURES / "alex" / "circles.yaml"),
            "--reference-date", "2026-08-03",
            "--output-dir", str(output_dir),
        ])
        assert exit_code == 0

        import json
        with open(output_dir / "data.json") as f:
            artifact = json.load(f)

        # Top-level fields
        assert artifact["version"] == 1
        assert artifact["spec_version"] == 0
        assert artifact["person"] == "Alex Example"
        assert artifact["reference_date"] == "2026-08-03"
        assert artifact["timezone"] == "UTC"
        assert artifact["stale_after_hours"] is None
        assert isinstance(artifact["warnings"], list)

        # Rings in order
        ring_ids = [r["id"] for r in artifact["rings"]]
        assert ring_ids == ["self", "partner", "children", "wider"]

        # self/exercise: no adapter → grey by-choice
        exercise = self._find_item(artifact, "self", "exercise")
        assert exercise["status"] == "grey"
        assert exercise["grey_reason"] == "by-choice"
        assert exercise["share"] == 1
        assert exercise["guardrail"] is None
        assert exercise["note"] is None
        assert exercise["link"] is None

        # self/sleep: freshness at P0 → grey by-failure + "not evaluated"
        sleep = self._find_item(artifact, "self", "sleep")
        assert sleep["status"] == "grey"
        assert sleep["grey_reason"] == "by-failure"
        assert "not evaluated" in sleep["detail_line"]

        # self/labs: freshness at P0 → grey by-failure + "not evaluated"
        labs = self._find_item(artifact, "self", "labs")
        assert labs["status"] == "grey"
        assert labs["grey_reason"] == "by-failure"
        assert "not evaluated" in labs["detail_line"]

        # partner/date-night: manual yellow → yellow
        date_night = self._find_item(artifact, "partner", "date-night")
        assert date_night["status"] == "yellow"
        assert date_night["grey_reason"] is None

        # children/nova: manual green → green
        nova = self._find_item(artifact, "children", "nova")
        assert nova["status"] == "green"
        assert nova["share"] == 0.5

        # children/kit: manual green → green
        kit = self._find_item(artifact, "children", "kit")
        assert kit["status"] == "green"
        assert kit["share"] == 0.5

        # wider/friends: manual red → red
        friends = self._find_item(artifact, "wider", "friends")
        assert friends["status"] == "red"

        # wider/plants: command at P0 → grey by-failure + "not evaluated"
        plants = self._find_item(artifact, "wider", "plants")
        assert plants["status"] == "grey"
        assert plants["grey_reason"] == "by-failure"
        assert "not evaluated" in plants["detail_line"]

        # Warnings for unevaluated adapters
        warning_items = {w["item"] for w in artifact["warnings"]}
        assert "self/sleep" in warning_items
        assert "self/labs" in warning_items
        assert "wider/plants" in warning_items

    def test_warnings_empty_array(self, tmp_path):
        """CIR-BAKE-ARTIFACT#warnings-empty-array

        A fully healthy bake has warnings: [] present, never omitted.
        """
        from bake.cli import main

        # A config with only manual adapters — no warnings
        cfg = {
            "person": "Test",
            "rings": [{
                "id": "test", "label": "Test",
                "items": [{"id": "a", "label": "A", "status": {"manual": "green"}}],
            }],
        }
        config_path = _write_yaml(tmp_path, cfg)
        output_dir = tmp_path / "out"
        exit_code = main([str(config_path), "--reference-date", "2026-08-03", "--output-dir", str(output_dir)])
        assert exit_code == 0

        import json
        with open(output_dir / "data.json") as f:
            artifact = json.load(f)

        assert artifact["warnings"] == []

    @staticmethod
    def _find_item(artifact, ring_id, item_id):
        for ring in artifact["rings"]:
            if ring["id"] == ring_id:
                for item in ring["items"]:
                    if item["id"] == item_id:
                        return item
        raise AssertionError(f"Item {ring_id}/{item_id} not found")


# ============================================================
# CIR-BAKE-STATUS-VALUES
# ============================================================


class TestStatusValues:
    """CIR-BAKE-STATUS-VALUES — wire values are not display words."""

    @pytest.mark.parametrize("status", ["green", "yellow", "red", "grey"])
    def test_status_wire_vocabulary(self, status):
        """CIR-BAKE-STATUS-VALUES#status-wire-vocabulary"""
        from bake.artifact import _build_item_artifact
        from bake.adapters import AdapterResult

        if status == "grey":
            item = {"id": "test", "label": "Test"}
            artifact = _build_item_artifact(item, "ring/test", None)
        else:
            item = {"id": "test", "label": "Test"}
            result = AdapterResult(status=status)
            artifact = _build_item_artifact(item, "ring/test", result)

        assert artifact["status"] == status

    def test_status_never_emoji(self, tmp_path):
        """CIR-BAKE-STATUS-VALUES#status-never-emoji"""
        from bake.cli import main

        cfg = {
            "person": "Test",
            "rings": [{
                "id": "test", "label": "Test",
                "items": [{"id": "a", "label": "A", "status": {"manual": "green"}}],
            }],
        }
        config_path = _write_yaml(tmp_path, cfg)
        output_dir = tmp_path / "out"
        main([str(config_path), "--reference-date", "2026-08-03", "--output-dir", str(output_dir)])

        import json
        with open(output_dir / "data.json") as f:
            text = f.read()

        # No emoji in the artifact
        for emoji in ["🟢", "🟡", "🔴", "⚪"]:
            assert emoji not in text, f"emoji {emoji} found in artifact"

    def test_status_never_display_words(self, tmp_path):
        """CIR-BAKE-STATUS-VALUES#status-never-display-words"""
        from bake.cli import main

        cfg = {
            "person": "Test",
            "rings": [{
                "id": "test", "label": "Test",
                "items": [{"id": "a", "label": "A", "status": {"manual": "green"}}],
            }],
        }
        config_path = _write_yaml(tmp_path, cfg)
        output_dir = tmp_path / "out"
        main([str(config_path), "--reference-date", "2026-08-03", "--output-dir", str(output_dir)])

        import json
        with open(output_dir / "data.json") as f:
            artifact = json.load(f)

        # The status field must be the wire value, not the display word
        item = artifact["rings"][0]["items"][0]
        assert item["status"] == "green"  # not "ok"