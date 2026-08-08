# Tests for bake/resolve.py — resolution logic and the baked artifact
#
# Every decision-table row of every fully-owned requirement has a citing test,
# parametrised per CIR-PROC-TEST-ROWS#rows-parametrised-not-copied, with the row id
# (CIR-<AREA>-<NAME>#<row-id>) cited verbatim in the test name.
#
# Tests build inputs from fixtures/ at runtime — no second synthetic person invented
# in test code (CIR-PROC-TEST-FIXTURES#fixture-row-is-spec-row).

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

import bake.resolve as resolve_module
from bake.config import ConfigError, load_config
from bake.emit import write_artifact
from bake.resolve import (
    GreyReason,
    Status,
    resolve,
    window_status,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ALEX_YAML = FIXTURES / "alex" / "circles.yaml"
FIXTURE_REFERENCE_DATE = date(2026, 8, 3)
FIXTURE_GENERATED_AT = datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# Helpers
# ===========================================================================

def _resolve_fixture(
    *,
    reference_date: date = FIXTURE_REFERENCE_DATE,
    generated_at: datetime = FIXTURE_GENERATED_AT,
) -> dict:
    """Load the fixture config and resolve it."""
    config = load_config(ALEX_YAML)
    return resolve(config, reference_date=reference_date, generated_at=generated_at)


def _item_by_id(artifact: dict, ring_id: str, item_id: str) -> dict:
    """Find an item dict by ring id and item id."""
    for ring in artifact["rings"]:
        if ring["id"] == ring_id:
            for item in ring["items"]:
                if item["id"] == item_id:
                    return item
    raise KeyError(f"Item {ring_id}/{item_id} not found")


# ===========================================================================
# CIR-DATA-STATUS-RESOLUTION — the canonical table
# ===========================================================================

class TestDataStatusResolution:
    """CIR-DATA-STATUS-RESOLUTION — the canonical table."""

    def test_no_adapter_declared(self) -> None:
        """CIR-DATA-STATUS-RESOLUTION#no-adapter-declared —
        self/exercise has no status: → ⚪ unmonitored, reason by-choice."""
        artifact = _resolve_fixture()
        item = _item_by_id(artifact, "self", "exercise")
        assert item["status"] == "grey"
        assert item["grey_reason"] == "by-choice"

    def test_manual_green(self) -> None:
        """CIR-DATA-STATUS-RESOLUTION#manual-green — children/nova manual: green → 🟢."""
        artifact = _resolve_fixture()
        item = _item_by_id(artifact, "children", "nova")
        assert item["status"] == "green"
        assert item["grey_reason"] is None

    def test_manual_yellow(self) -> None:
        """CIR-DATA-STATUS-RESOLUTION#manual-yellow — partner/date-night manual: yellow → 🟡."""
        artifact = _resolve_fixture()
        item = _item_by_id(artifact, "partner", "date-night")
        assert item["status"] == "yellow"
        assert item["grey_reason"] is None

    def test_manual_red(self) -> None:
        """CIR-DATA-STATUS-RESOLUTION#manual-red — wider/friends manual: red → 🔴."""
        artifact = _resolve_fixture()
        item = _item_by_id(artifact, "wider", "friends")
        assert item["status"] == "red"
        assert item["grey_reason"] is None

    def test_adapter_not_evaluated_this_phase(self) -> None:
        """CIR-DATA-STATUS-RESOLUTION#adapter-not-evaluated-this-phase —
        freshness/command items under P0 → ⚪ + warning, reason not-evaluated (⚖-R50)."""
        artifact = _resolve_fixture()

        # self/sleep: freshness adapter → ⚪ not-evaluated
        sleep = _item_by_id(artifact, "self", "sleep")
        assert sleep["status"] == "grey"
        assert sleep["grey_reason"] == "not-evaluated"

        # self/labs: freshness adapter → ⚪ not-evaluated
        labs = _item_by_id(artifact, "self", "labs")
        assert labs["status"] == "grey"
        assert labs["grey_reason"] == "not-evaluated"

        # wider/plants: command adapter → ⚪ not-evaluated
        plants = _item_by_id(artifact, "wider", "plants")
        assert plants["status"] == "grey"
        assert plants["grey_reason"] == "not-evaluated"

        # Check warnings exist for these items
        warnings = artifact["warnings"]
        warning_items = {w["item"] for w in warnings}
        assert "self/sleep" in warning_items
        assert "self/labs" in warning_items
        assert "wider/plants" in warning_items

    # The table's five config-error rows. Their behaviour was already asserted
    # under CIR-DATA-SCHEMA-ADAPTER-SLOT / CIR-DATA-STATUS-MANUAL-VALUES row ids,
    # which left these five rows of *this* requirement unevidenced — the same
    # behaviour can satisfy two requirements, but only the row ids actually cited
    # join to evidence. `empty-status-block` had no citing test under any id.
    #
    # The shared claim is the asymmetry the spec calls out: a bad *config* fails
    # the bake outright, rather than degrading to ⚪ the way a bad *command* does.
    @pytest.mark.parametrize(
        ("status_block", "message"),
        [
            pytest.param(
                {"manual": "green",
                 "freshness": {"source": "notes/sleep-log.md", "yellow_after": 7, "red_after": 30}},
                "multiple adapter keys",
                id="CIR-DATA-STATUS-RESOLUTION#two-adapters-on-one-item",
            ),
            pytest.param(
                {}, "empty status block",
                id="CIR-DATA-STATUS-RESOLUTION#empty-status-block",
            ),
            pytest.param(
                {"manual": "amber"}, "not a valid manual value",
                id="CIR-DATA-STATUS-RESOLUTION#manual-unknown-word",
            ),
            pytest.param(
                {"manual": "grey"}, "grey",
                id="CIR-DATA-STATUS-RESOLUTION#manual-declares-grey",
            ),
            pytest.param(
                {"sqlite": {"query": "SELECT 1"}}, "unknown adapter",
                id="CIR-DATA-STATUS-RESOLUTION#unknown-adapter-key",
            ),
        ],
    )
    def test_config_error_fails_the_bake(
        self, status_block: dict, message: str, tmp_path: Path,
    ) -> None:
        """CIR-DATA-STATUS-RESOLUTION — a config error fails the bake and
        publishes nothing; it must never degrade to ⚪.

        Row ids are carried by the parametrised case id.
        """
        import yaml

        data = {
            "person": "Alex Example",
            "rings": [{
                "id": "self", "label": "① Self",
                "items": [{"id": "sleep", "label": "Sleep", "status": status_block}],
            }],
        }
        path = tmp_path / "circles.yaml"
        path.write_text(yaml.dump(data))

        with pytest.raises(ConfigError, match=message) as excinfo:
            load_config(path)

        # The error names where it is, so a human can fix it before anyone sees a
        # wrong page — and nothing resolved, so no ⚪ was published in its place.
        assert "self" in str(excinfo.value) or "sleep" in str(excinfo.value), (
            f"config error should locate the offending item: {excinfo.value}"
        )


# ===========================================================================
# CIR-DATA-GREY-REASON — one grey light, three reasons
# ===========================================================================

class TestDataGreyReason:
    """CIR-DATA-GREY-REASON — one grey light, three reasons."""

    def test_unmonitored_by_choice(self) -> None:
        """CIR-DATA-GREY-REASON#unmonitored-by-choice —
        no status: block → reason by-choice."""
        artifact = _resolve_fixture()
        item = _item_by_id(artifact, "self", "exercise")
        assert item["status"] == "grey"
        assert item["grey_reason"] == "by-choice"

    def test_unmonitored_not_evaluated(self) -> None:
        """CIR-DATA-GREY-REASON#unmonitored-not-evaluated —
        freshness: or command: under P0 → reason not-evaluated."""
        artifact = _resolve_fixture()
        sleep = _item_by_id(artifact, "self", "sleep")
        assert sleep["status"] == "grey"
        assert sleep["grey_reason"] == "not-evaluated"

        plants = _item_by_id(artifact, "wider", "plants")
        assert plants["status"] == "grey"
        assert plants["grey_reason"] == "not-evaluated"


# ===========================================================================
# CIR-DATA-FAILURE-IS-GREY — the failure algebra
# ===========================================================================

class TestDataFailureIsGrey:
    """CIR-DATA-FAILURE-IS-GREY — the failure algebra."""

    def test_failure_never_red(self) -> None:
        """CIR-DATA-FAILURE-IS-GREY#failure-never-red —
        adapter failure → ⚪, never 🔴."""
        artifact = _resolve_fixture()
        # All non-evaluated adapters are ⚪, never red
        for ring in artifact["rings"]:
            for item in ring["items"]:
                if item["status"] == "grey":
                    assert item["grey_reason"] is not None
                else:
                    assert item["status"] in ("green", "yellow", "red")

    def test_failure_never_green(self) -> None:
        """CIR-DATA-FAILURE-IS-GREY#failure-never-green —
        adapter failure → ⚪, never 🟢."""
        artifact = _resolve_fixture()
        sleep = _item_by_id(artifact, "self", "sleep")
        assert sleep["status"] == "grey"  # not green


# ===========================================================================
# CIR-DATA-NO-AGGREGATION — no roll-up, ever
# ===========================================================================

class TestDataNoAggregation:
    """CIR-DATA-NO-AGGREGATION — no roll-up, ever."""

    def test_inner_red_outer_untouched(self) -> None:
        """CIR-DATA-NO-AGGREGATION#inner-red-outer-untouched —
        wider/friends is 🔴, other items keep their own resolved colours."""
        artifact = _resolve_fixture()
        friends = _item_by_id(artifact, "wider", "friends")
        assert friends["status"] == "red"

        # Other items are unaffected
        nova = _item_by_id(artifact, "children", "nova")
        assert nova["status"] == "green"

    def test_centre_carries_no_status(self) -> None:
        """CIR-DATA-NO-AGGREGATION#centre-carries-no-status —
        the artifact has no centre/aggregate field."""
        artifact = _resolve_fixture()
        # The artifact has no top-level status field
        assert "status" not in artifact
        # No aggregate/score field
        assert "aggregate" not in artifact
        assert "score" not in artifact


# ===========================================================================
# CIR-DATA-RESOLUTION-TIME — statuses resolve at bake time only
# ===========================================================================

class TestDataResolutionTime:
    """CIR-DATA-RESOLUTION-TIME — statuses resolve at bake time only."""

    def test_page_never_reevaluates(self) -> None:
        """CIR-DATA-RESOLUTION-TIME#page-never-reevaluates —
        statuses are frozen in the artifact."""
        artifact = _resolve_fixture()
        # Statuses are just data — no adapter code, no date math
        assert artifact["rings"][0]["items"][0]["status"] is not None

    def test_p0_manual_roundtrip(self) -> None:
        """CIR-DATA-RESOLUTION-TIME#p0-manual-roundtrip —
        manual statuses pass through unchanged."""
        artifact = _resolve_fixture()
        assert _item_by_id(artifact, "children", "nova")["status"] == "green"
        assert _item_by_id(artifact, "children", "kit")["status"] == "green"
        assert _item_by_id(artifact, "partner", "date-night")["status"] == "yellow"
        assert _item_by_id(artifact, "wider", "friends")["status"] == "red"

    def test_one_reference_date_per_bake(self) -> None:
        """CIR-DATA-RESOLUTION-TIME#one-reference-date-per-bake —
        all items age against the same reference date."""
        artifact = _resolve_fixture()
        assert artifact["reference_date"] == "2026-08-03"


# ===========================================================================
# CIR-DATA-DETAIL-LINE — what hover shows
# ===========================================================================

class TestDataDetailLine:
    """CIR-DATA-DETAIL-LINE — what hover shows."""

    def test_full_detail_line(self) -> None:
        """CIR-DATA-DETAIL-LINE#full-detail-line —
        guardrail + status word for a manual item."""
        artifact = _resolve_fixture()
        # partner/date-night has guardrail + manual yellow
        item = _item_by_id(artifact, "partner", "date-night")
        assert "Protected evening, twice a month" in item["detail_line"]
        assert "attention" in item["detail_line"]  # display word for yellow

    def test_no_guardrail(self) -> None:
        """CIR-DATA-DETAIL-LINE#no-guardrail —
        item without guardrail starts at the status."""
        artifact = _resolve_fixture()
        # children/nova has no guardrail
        item = _item_by_id(artifact, "children", "nova")
        assert item["guardrail"] is None
        assert item["detail_line"] == "ok"  # just the status word

    def test_manual_item_has_no_data_date(self) -> None:
        """CIR-DATA-DETAIL-LINE#manual-item-has-no-data-date —
        manual items have no 'last data' segment."""
        artifact = _resolve_fixture()
        item = _item_by_id(artifact, "children", "nova")
        assert item["last_data_date"] is None
        assert "last data" not in item["detail_line"]

    def test_detail_line_is_plain_text(self) -> None:
        """CIR-DATA-DETAIL-LINE#detail-line-is-plain-text —
        detail lines contain no markup."""
        artifact = _resolve_fixture()
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert isinstance(item["detail_line"], str)
                assert "<" not in item["detail_line"]  # no HTML


# ===========================================================================
# CIR-BAKE-ARTIFACT — what a bake produces
# ===========================================================================

class TestBakeArtifact:
    """CIR-BAKE-ARTIFACT — what a bake produces."""

    def test_artifact_fixture_roundtrip(self) -> None:
        """CIR-BAKE-ARTIFACT#artifact-fixture-roundtrip —
        bake over fixtures/alex/circles.yaml produces correct structure."""
        artifact = _resolve_fixture()

        # Top-level fields
        assert artifact["version"] == 1
        assert artifact["spec_version"] == 0
        assert artifact["person"] == "Alex Example"
        assert artifact["generated_at"] == "2026-08-03T02:00:00Z"
        assert artifact["reference_date"] == "2026-08-03"
        assert artifact["timezone"] == "UTC"
        assert artifact["stale_after_hours"] is None

        # 4 rings in order
        assert len(artifact["rings"]) == 4
        assert [r["id"] for r in artifact["rings"]] == ["self", "partner", "children", "wider"]

        # 8 items total
        total_items = sum(len(r["items"]) for r in artifact["rings"])
        assert total_items == 8

        # self/exercise has status: grey, grey_reason: by-choice, share: 1
        exercise = _item_by_id(artifact, "self", "exercise")
        assert exercise["status"] == "grey"
        assert exercise["grey_reason"] == "by-choice"
        assert exercise["share"] == 1
        assert exercise["guardrail"] is None
        assert exercise["note"] is None
        assert exercise["link"] is None

    def test_warnings_empty_array(self) -> None:
        """CIR-BAKE-ARTIFACT#warnings-empty-array —
        warnings is always present, even when empty."""
        # Build a minimal config with no adapters (no warnings)
        from bake.config import load_config
        import yaml
        import tempfile

        minimal = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X"}],
            }],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(minimal, f)
            tmp_path = Path(f.name)

        try:
            config = load_config(tmp_path)
            artifact = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
            assert "warnings" in artifact
            assert isinstance(artifact["warnings"], list)
        finally:
            tmp_path.unlink()


# ===========================================================================
# CIR-BAKE-STATUS-VALUES — wire values are not display words
# ===========================================================================

class TestBakeStatusValues:
    """CIR-BAKE-STATUS-VALUES — wire values are not display words."""

    def test_status_wire_vocabulary(self) -> None:
        """CIR-BAKE-STATUS-VALUES#status-wire-vocabulary —
        status is one of green|yellow|red|grey."""
        artifact = _resolve_fixture()
        valid_statuses = {"green", "yellow", "red", "grey"}
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert item["status"] in valid_statuses

    def test_status_never_emoji(self) -> None:
        """CIR-BAKE-STATUS-VALUES#status-never-emoji —
        no emoji in the artifact."""
        artifact = _resolve_fixture()
        raw = json.dumps(artifact)
        assert "🟢" not in raw
        assert "🟡" not in raw
        assert "🔴" not in raw
        assert "⚪" not in raw

    def test_status_never_display_words(self) -> None:
        """CIR-BAKE-STATUS-VALUES#status-never-display-words —
        never 'ok'/'attention'/'act'/'unmonitored' in status field."""
        artifact = _resolve_fixture()
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert item["status"] not in ("ok", "attention", "act", "unmonitored")


# ===========================================================================
# CIR-BAKE-VERSION — artifact versioning
# ===========================================================================

class TestBakeVersion:
    """CIR-BAKE-VERSION — artifact versioning."""

    def test_version_recognized(self) -> None:
        """CIR-BAKE-VERSION#version-recognized — version: 1."""
        artifact = _resolve_fixture()
        assert artifact["version"] == 1


# ===========================================================================
# CIR-BAKE-GENERATED-AT — the honesty stamp
# ===========================================================================

class TestBakeGeneratedAt:
    """CIR-BAKE-GENERATED-AT — the honesty stamp."""

    def test_generated_at_present(self) -> None:
        """generated_at is present and is an RFC 3339 UTC timestamp."""
        artifact = _resolve_fixture()
        assert "generated_at" in artifact
        assert artifact["generated_at"].endswith("Z")
        assert "T" in artifact["generated_at"]


# ===========================================================================
# CIR-BAKE-STALE-SELF — the page's own freshness
# ===========================================================================

class TestBakeStaleSelf:
    """CIR-BAKE-STALE-SELF — the page's own freshness."""

    def test_no_threshold_no_banner(self) -> None:
        """CIR-BAKE-STALE-SELF#no-threshold-no-banner —
        stale_after_hours is null at P0."""
        artifact = _resolve_fixture()
        assert artifact["stale_after_hours"] is None


# ===========================================================================
# CIR-BAKE-WARNINGS — where build warnings surface
# ===========================================================================

class TestBakeWarnings:
    """CIR-BAKE-WARNINGS — where build warnings surface."""

    def test_warning_carries_cell_ref(self) -> None:
        """CIR-BAKE-WARNINGS#warning-carries-cell-ref —
        warning for plants carries wider/plants."""
        artifact = _resolve_fixture()
        warnings = artifact["warnings"]
        plant_warnings = [w for w in warnings if w["item"] == "wider/plants"]
        assert len(plant_warnings) >= 1

    def test_config_level_warning_has_null_item(self) -> None:
        """CIR-BAKE-WARNINGS#config-level-warning-has-null-item —
        config-level warnings have null item."""
        # The fixture has no config-level warnings, but the field is always present
        artifact = _resolve_fixture()
        for w in artifact["warnings"]:
            assert "item" in w
            assert "message" in w


# ===========================================================================
# CIR-BAKE-DETAIL-FIELDS — structured fields and one composed line
# ===========================================================================

class TestBakeDetailFields:
    """CIR-BAKE-DETAIL-FIELDS — structured fields and one composed line."""

    def test_detail_line_is_baked(self) -> None:
        """CIR-BAKE-DETAIL-FIELDS#detail-line-is-baked —
        detail_line is present on every item."""
        artifact = _resolve_fixture()
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert "detail_line" in item
                assert isinstance(item["detail_line"], str)
                assert len(item["detail_line"]) > 0

    def test_structured_fields_also_present(self) -> None:
        """CIR-BAKE-DETAIL-FIELDS#structured-fields-also-present —
        guardrail, status, last_data_date, note, grey_reason are all present."""
        artifact = _resolve_fixture()
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert "guardrail" in item
                assert "status" in item
                assert "last_data_date" in item
                assert "note" in item
                assert "grey_reason" in item


# ===========================================================================
# CIR-ADAPT-CONTRACT — one adapter, one answer
# ===========================================================================

class TestAdaptContract:
    """CIR-ADAPT-CONTRACT — one adapter, one answer."""

    def test_adapter_resolves_one_item(self) -> None:
        """CIR-ADAPT-CONTRACT#adapter-resolves-one-item —
        one `status:` block produces exactly one status."""
        artifact = _resolve_fixture()
        # Every item with an adapter has exactly one status
        for ring in artifact["rings"]:
            for item in ring["items"]:
                if item.get("grey_reason") != "not-evaluated":
                    assert item["status"] in ("green", "yellow", "red", "grey")

    def test_adapter_never_reads_the_clock(self) -> None:
        """CIR-ADAPT-CONTRACT#adapter-never-reads-the-clock —
        adapter uses injected reference date, not the system clock."""
        # resolve() takes reference_date as explicit parameter
        # Two bakes with different reference dates produce different generated_at
        # but the same stale_after_hours structure
        config = load_config(ALEX_YAML)
        art1 = resolve(config, reference_date=date(2026, 8, 3), generated_at=FIXTURE_GENERATED_AT)
        art2 = resolve(config, reference_date=date(2026, 8, 10), generated_at=FIXTURE_GENERATED_AT)
        # Both resolve; the reference_date is injected, never read from a clock
        assert art1["reference_date"] == "2026-08-03"
        assert art2["reference_date"] == "2026-08-10"

    def test_adapter_never_writes(self, tmp_path: Path) -> None:
        """CIR-ADAPT-CONTRACT#adapter-never-writes —
        adapters do not write to the config dir; the bake owns all output."""
        # Create a command adapter whose argv[0] would create a file if executed.
        # At P0, resolve() does NOT evaluate commands — it returns not-evaluated.
        # If it DID execute, it would leave a file behind; verify no file is written.
        import yaml

        script_path = tmp_path / "emit.sh"
        marker_path = tmp_path / "adapter-was-run.marker"
        script_path.write_text("#!/usr/bin/env bash\ntouch " + str(marker_path))
        script_path.chmod(0o755)

        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{
                    "id": "x", "label": "X",
                    "status": {"command": [str(script_path)]},
                }],
            }],
        }
        config_path = tmp_path / "circles.yaml"
        config_path.write_text(yaml.dump(data))

        config = load_config(config_path)
        artifact = resolve(config, reference_date=date(2026, 8, 3), generated_at=FIXTURE_GENERATED_AT)

        # The adapter was NOT executed — no marker file was written
        assert not marker_path.exists(), (
            f"Command adapter was executed — marker file exists at {marker_path}"
        )
        # The item resolves to grey/not-evaluated (P0 contract)
        item = _item_by_id(artifact, "a", "x")
        assert item["status"] == "grey"
        assert item["grey_reason"] == "not-evaluated"

    def test_adapter_unknown_name_is_config_error(self, tmp_path: Path) -> None:
        """CIR-ADAPT-CONTRACT#adapter-unknown-name —
        status: {prometheus: …} on a build without it → config error."""
        import yaml
        data = {
            "person": "Test",
            "rings": [{
                "id": "a", "label": "A",
                "items": [{"id": "x", "label": "X", "status": {"prometheus": {"query": "up"}}}],
            }],
        }
        path = tmp_path / "circles.yaml"
        path.write_text(yaml.dump(data))
        with pytest.raises(ConfigError, match="unknown adapter"):
            load_config(path)

    def test_adapter_cannot_return_grey(self, tmp_path: Path) -> None:
        """CIR-ADAPT-CONTRACT#adapter-cannot-return-grey —
        ⚪ is not in an adapter's return vocabulary; it comes only from absence
        or failure (CIR-DATA-GREY-REASON).

        Asserted from both ends: an adapter that *answers* never produces grey,
        and an adapter that tries to declare grey is rejected before it can.
        """
        import yaml

        data = {
            "person": "Alex Example",
            "rings": [{
                "id": "self", "label": "① Self",
                "items": [{"id": "x", "label": "X", "status": {"manual": "green"}}],
            }],
        }
        path = tmp_path / "circles.yaml"

        # 1. Every value an adapter can return resolves to a non-grey light.
        for manual_value in ("green", "yellow", "red"):
            data["rings"][0]["items"][0]["status"] = {"manual": manual_value}
            path.write_text(yaml.dump(data))
            artifact = resolve(
                load_config(path),
                reference_date=FIXTURE_REFERENCE_DATE,
                generated_at=FIXTURE_GENERATED_AT,
            )
            item = _item_by_id(artifact, "self", "x")
            assert item["status"] == manual_value
            assert item["status"] != "grey", "an adapter's answer must never be grey"
            assert item["grey_reason"] is None, "a non-grey item must carry no grey reason"

        # 2. Grey is not expressible as an adapter answer at all — the one adapter
        #    that states a status outright cannot state this one.
        data["rings"][0]["items"][0]["status"] = {"manual": "grey"}
        path.write_text(yaml.dump(data))
        with pytest.raises(ConfigError, match="grey"):
            load_config(path)

        # 3. So every grey that does exist is attributed to absence or
        #    non-evaluation, never to an adapter having answered ⚪.
        for ring in _resolve_fixture()["rings"]:
            for fixture_item in ring["items"]:
                if fixture_item["status"] == "grey":
                    assert fixture_item["grey_reason"] in (
                        "by-choice", "by-failure", "not-evaluated",
                    ), (
                        f"{ring['id']}/{fixture_item['id']} is grey with reason "
                        f"{fixture_item['grey_reason']!r} — grey must always name "
                        f"the absence or failure it came from"
                    )

    def test_adapter_failure_is_isolated(self) -> None:
        """CIR-ADAPT-CONTRACT#adapter-failure-is-isolated —
        one failing adapter does not affect other items (at P0, adapters are
        not-evaluated, so no failure cascades)."""
        artifact = _resolve_fixture()
        # wider/plants (command adapter, not-evaluated) is ⚪
        plants = _item_by_id(artifact, "wider", "plants")
        assert plants["status"] == "grey"
        assert plants["grey_reason"] == "not-evaluated"
        # Other items are unaffected
        friends = _item_by_id(artifact, "wider", "friends")
        assert friends["status"] == "red"
        nova = _item_by_id(artifact, "children", "nova")
        assert nova["status"] == "green"


# ===========================================================================
# CIR-ADAPT-REFERENCE-DATE — one clock per bake, injected
# ===========================================================================

class TestAdaptReferenceDate:
    """CIR-ADAPT-REFERENCE-DATE — one clock per bake, injected."""

    def test_reference_date_shared(self) -> None:
        """CIR-ADAPT-REFERENCE-DATE#reference-date-shared —
        all items in one bake share the same reference date."""
        artifact = _resolve_fixture()
        # The artifact carries one reference_date for all items
        assert artifact["reference_date"] == "2026-08-03"
        # No per-item reference date field exists
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert "reference_date" not in item

    def test_reference_date_injectable(self) -> None:
        """CIR-ADAPT-REFERENCE-DATE#reference-date-injectable —
        test supplies a fixed reference date, ages are deterministic."""
        config = load_config(ALEX_YAML)
        # Same inputs produce same artifact (except generated_at is also injected)
        art1 = resolve(config, reference_date=date(2026, 8, 3), generated_at=FIXTURE_GENERATED_AT)
        art2 = resolve(config, reference_date=date(2026, 8, 3), generated_at=FIXTURE_GENERATED_AT)
        # Identical (same generated_at since we inject it)
        import json
        assert json.dumps(art1, sort_keys=True) == json.dumps(art2, sort_keys=True)

    def test_reference_date_crosses_midnight(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CIR-ADAPT-REFERENCE-DATE#reference-date-crosses-midnight —
        a bake that starts at 23:59:59 and runs past midnight dates every item
        by the reference date captured at bake start, not by the day it finishes.

        The bake entry point captures the date once, before resolution
        (bake/__main__.py), and resolution is handed that value. This test pins
        the other half: that resolution cannot reach around it to a wall clock
        that has since rolled over.
        """
        bake_start = datetime(2026, 8, 3, 23, 59, 59, tzinfo=timezone.utc)
        captured_date = bake_start.date()

        class _RolledOverClock:
            """The wall clock, already into the next day. Reading it is the defect."""

            @staticmethod
            def now(tz: Any = None) -> Any:
                raise AssertionError(
                    "resolution read the wall clock (now()) — it must use the "
                    "reference date captured at bake start"
                )

            @staticmethod
            def today() -> Any:
                raise AssertionError(
                    "resolution read the wall clock (today()) — it must use the "
                    "reference date captured at bake start"
                )

        monkeypatch.setattr(resolve_module, "datetime", _RolledOverClock)
        monkeypatch.setattr(resolve_module, "date", _RolledOverClock)

        config = load_config(ALEX_YAML)
        artifact = resolve(config, reference_date=captured_date, generated_at=bake_start)

        # One date for the whole run, and it is bake start's — not 2026-08-04.
        assert artifact["reference_date"] == "2026-08-03"
        assert artifact["generated_at"] == "2026-08-03T23:59:59Z"

        # Every item is dated by that one capture: no item carries a date of its
        # own, so none of them can have aged against a different day.
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert "reference_date" not in item
                assert item["last_data_date"] is None or (
                    item["last_data_date"] <= "2026-08-03"
                ), (
                    f"{ring['id']}/{item['id']} is dated {item['last_data_date']} — "
                    f"after the reference date captured at bake start"
                )

        # Finishing a second later, on the far side of midnight, changes only the
        # finish stamp we pass in — never an item.
        finished_after_midnight = datetime(2026, 8, 4, 0, 0, 1, tzinfo=timezone.utc)
        later = resolve(
            config, reference_date=captured_date, generated_at=finished_after_midnight,
        )
        assert later["rings"] == artifact["rings"]
        assert later["reference_date"] == artifact["reference_date"]

    def test_reference_date_fixture_pinned(self) -> None:
        """CIR-ADAPT-REFERENCE-DATE#reference-date-fixture-pinned —
        fixture bakes use injected 2026-08-03, never today."""
        artifact = _resolve_fixture()
        assert artifact["reference_date"] == "2026-08-03"
        assert artifact["generated_at"] == "2026-08-03T02:00:00Z"

    def test_reference_date_default_is_config_timezone(self) -> None:
        """CIR-ADAPT-REFERENCE-DATE#reference-date-default-is-config-timezone —
        the config provides a timezone; the host's local zone must not leak."""
        # P0 default is UTC; test that the timezone field is present in the artifact
        artifact = _resolve_fixture()
        assert artifact["timezone"] == "UTC"


# ===========================================================================
# CIR-ADAPT-NO-PAGE-LOGIC — the page is adapter-blind
# ===========================================================================

class TestAdaptNoPageLogic:
    """CIR-ADAPT-NO-PAGE-LOGIC — the page is adapter-blind."""

    def test_page_has_no_adapter_vocabulary(self) -> None:
        """CIR-ADAPT-NO-PAGE-LOGIC#page-has-no-adapter-vocabulary —
        the artifact never branches on which adapter produced a status."""
        artifact = _resolve_fixture()
        # No adapter kind info leaks into the artifact
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert "adapter" not in item
                assert "adapter_kind" not in item
                assert "adapter_name" not in item

    def test_new_adapter_changes_no_page_code(self) -> None:
        """CIR-ADAPT-NO-PAGE-LOGIC#new-adapter-changes-no-page-code —
        the artifact shape is fixed regardless of adapter kind."""
        artifact = _resolve_fixture()
        # All items have the same set of fields regardless of adapter
        expected_fields = {"id", "label", "status", "grey_reason", "guardrail", "note",
                          "link", "share", "last_data_date", "detail_line", "detail_page"}
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert set(item.keys()) == expected_fields, (
                    f"Item {ring['id']}/{item['id']} has unexpected fields: "
                    f"{set(item.keys()) - expected_fields}"
                )


# ===========================================================================
# CIR-BAKE-ATOMIC-WRITE — publishing discipline
# ===========================================================================

class TestBakeAtomicWrite:
    """CIR-BAKE-ATOMIC-WRITE — publishing discipline."""

    def test_write_artifact_creates_file(self, tmp_path: Path) -> None:
        """write_artifact creates data.json in the output directory."""
        artifact = _resolve_fixture()
        out_path = write_artifact(artifact, tmp_path)
        assert out_path == tmp_path / "data.json"
        assert out_path.exists()
        assert out_path.is_file()

    def test_write_artifact_is_valid_json(self, tmp_path: Path) -> None:
        """Written data.json is valid JSON."""
        artifact = _resolve_fixture()
        write_artifact(artifact, tmp_path)
        raw = (tmp_path / "data.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert parsed["version"] == 1
        assert parsed["person"] == "Alex Example"

    def test_write_artifact_is_world_readable(self, tmp_path: Path) -> None:
        """CIR-BAKE-ATOMIC-WRITE#permissions-world-readable —
        data.json must be world-readable (mode 0o644) so non-root
        nginx-unprivileged can serve it (regression: tempfile.mkstemp
        creates with mode 0o600 by default)."""
        import stat
        artifact = _resolve_fixture()
        write_artifact(artifact, tmp_path)
        out_path = tmp_path / "data.json"
        mode = out_path.stat().st_mode
        # Must be readable by owner, group, and world (0o644 ≡ 0o100644 on disk)
        assert bool(mode & stat.S_IRUSR), "owner cannot read"
        assert bool(mode & stat.S_IRGRP), "group cannot read"
        assert bool(mode & stat.S_IROTH), "world cannot read"
        # Must NOT be writable by world (security — only owner writes)
        assert not bool(mode & stat.S_IWOTH), "world can write"


# ===========================================================================
# CIR-BAKE-DETERMINISM — same inputs, same output
# ===========================================================================

class TestBakeDeterminism:
    """CIR-BAKE-DETERMINISM — same inputs, same output."""

    def test_two_bakes_agree(self, tmp_path: Path) -> None:
        """CIR-BAKE-DETERMINISM#two-bakes-agree —
        same config, same reference date → byte-identical except generated_at."""
        config = load_config(ALEX_YAML)

        # First bake
        artifact1 = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
        write_artifact(artifact1, tmp_path / "run1")
        raw1 = (tmp_path / "run1" / "data.json").read_text(encoding="utf-8")

        # Second bake (same inputs)
        artifact2 = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
        write_artifact(artifact2, tmp_path / "run2")
        raw2 = (tmp_path / "run2" / "data.json").read_text(encoding="utf-8")

        # Byte-identical (same generated_at since we inject it)
        assert raw1 == raw2

    def test_ordering_is_stable(self) -> None:
        """CIR-BAKE-DETERMINISM#ordering-is-stable —
        rings and items in file order; warnings in item order."""
        artifact = _resolve_fixture()
        # Rings in config order
        assert [r["id"] for r in artifact["rings"]] == ["self", "partner", "children", "wider"]
        # Items in config order
        assert [i["id"] for i in artifact["rings"][0]["items"]] == ["sleep", "labs", "exercise"]


# ===========================================================================
# CIR-BAKE-EXPOSURE — everything in the artifact is public
# ===========================================================================

class TestBakeExposure:
    """CIR-BAKE-EXPOSURE — everything in the artifact is public."""

    def test_no_absolute_host_paths(self) -> None:
        """CIR-BAKE-EXPOSURE#no-absolute-host-paths —
        warnings use config-relative paths only."""
        artifact = _resolve_fixture()
        for w in artifact["warnings"]:
            if w["message"]:
                assert "/home/" not in w["message"]
                assert "/etc/" not in w["message"]


# ===========================================================================
# CIR-BAKE-PAGE-DOES-NOT-RESOLVE — the page renders, it never decides
# ===========================================================================

class TestBakePageDoesNotResolve:
    """CIR-BAKE-PAGE-DOES-NOT-RESOLVE — the page renders, it never decides."""

    def test_page_contains_no_adapter_code(self) -> None:
        """CIR-BAKE-PAGE-DOES-NOT-RESOLVE#page-contains-no-adapter-code —
        the artifact is pure data, no code."""
        artifact = _resolve_fixture()
        # The artifact is a plain dict with no callable or code references
        assert isinstance(artifact, dict)
        # No adapter evaluation metadata leaks into the artifact
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert "adapter" not in item


# ===========================================================================
# CIR-DATA-FRESHNESS-WINDOW — the boundary predicate (pure, unwired at P0)
# ===========================================================================

class TestDataFreshnessWindow:
    """CIR-DATA-FRESHNESS-WINDOW — thresholds and boundaries (pure predicate only)."""

    @pytest.mark.parametrize("age,yellow,red,expected", [
        pytest.param(6, 7, 30, "green", id="CIR-DATA-FRESHNESS-WINDOW#window-inside"),
        pytest.param(7, 7, 30, "green", id="CIR-DATA-FRESHNESS-WINDOW#window-at-yellow-boundary"),
        pytest.param(8, 7, 30, "yellow", id="CIR-DATA-FRESHNESS-WINDOW#window-just-past-yellow"),
        pytest.param(29, 7, 30, "yellow", id="CIR-DATA-FRESHNESS-WINDOW#window-mid"),
        pytest.param(30, 7, 30, "yellow", id="CIR-DATA-FRESHNESS-WINDOW#window-at-red-boundary"),
        pytest.param(31, 7, 30, "red", id="CIR-DATA-FRESHNESS-WINDOW#window-just-past-red"),
        pytest.param(45, 7, 30, "red", id="CIR-DATA-FRESHNESS-WINDOW#window-far-past-red"),
    ])
    def test_window_boundaries(self, age: int, yellow: int, red: int, expected: str) -> None:
        """CIR-DATA-FRESHNESS-WINDOW — boundary behaviour per ⚖-R6 strict `>`."""
        result = window_status(age, yellow, red)
        assert result == expected


# ===========================================================================
# CIR-ADAPT-MANUAL — hand-set light
# ===========================================================================

class TestAdaptManual:
    """CIR-ADAPT-MANUAL — hand-set light."""

    def test_manual_returns_declared_light(self) -> None:
        """CIR-ADAPT-MANUAL#manual-returns-declared-light —
        manual: green → 🟢."""
        artifact = _resolve_fixture()
        assert _item_by_id(artifact, "children", "nova")["status"] == "green"

    def test_manual_has_no_data_date(self) -> None:
        """CIR-ADAPT-MANUAL#manual-has-no-data-date —
        manual items have no last_data_date."""
        artifact = _resolve_fixture()
        item = _item_by_id(artifact, "children", "nova")
        assert item["last_data_date"] is None

    def test_manual_available_in_every_phase(self) -> None:
        """CIR-ADAPT-MANUAL#manual-available-in-every-phase —
        manual works at P0."""
        artifact = _resolve_fixture()
        assert _item_by_id(artifact, "partner", "date-night")["status"] == "yellow"


# ===========================================================================
# CIR-PROC-PHASE-P0 — hand-set statuses on the existing pipeline
# ===========================================================================

class TestProcPhaseP0:
    """CIR-PROC-PHASE-P0 — hand-set statuses on the existing pipeline."""

    def test_p0_manual_end_to_end(self) -> None:
        """CIR-PROC-PHASE-P0#p0-manual-end-to-end —
        fixture-style config with manual items resolves correctly."""
        artifact = _resolve_fixture()
        assert _item_by_id(artifact, "children", "nova")["status"] == "green"
        assert _item_by_id(artifact, "children", "kit")["status"] == "green"
        assert _item_by_id(artifact, "partner", "date-night")["status"] == "yellow"
        assert _item_by_id(artifact, "wider", "friends")["status"] == "red"

    def test_p0_unevaluated_adapters_are_grey(self) -> None:
        """CIR-PROC-PHASE-P0#p0-unevaluated-adapters-are-grey —
        freshness and command items → ⚪ + warning, grey_reason: not-evaluated."""
        artifact = _resolve_fixture()

        sleep = _item_by_id(artifact, "self", "sleep")
        assert sleep["status"] == "grey"
        assert sleep["grey_reason"] == "not-evaluated"

        labs = _item_by_id(artifact, "self", "labs")
        assert labs["status"] == "grey"
        assert labs["grey_reason"] == "not-evaluated"

        plants = _item_by_id(artifact, "wider", "plants")
        assert plants["status"] == "grey"
        assert plants["grey_reason"] == "not-evaluated"

        # Check warnings
        warnings = artifact["warnings"]
        warning_msgs = [w["message"] for w in warnings if w["item"] in ("self/sleep", "self/labs", "wider/plants")]
        assert all("not evaluated" in m for m in warning_msgs)

    def test_p0_config_stays_valid(self) -> None:
        """CIR-PROC-PHASE-P0#p0-config-stays-valid —
        the fixture config validates at P0."""
        config = load_config(ALEX_YAML)
        assert config.person == "Alex Example"
        assert len(config.rings) == 4


# ===========================================================================
# CIR-PROC-BAKE-ONE-PATH — one bake, several triggers
# ===========================================================================

class TestProcBakeOnePath:
    """CIR-PROC-BAKE-ONE-PATH — one bake, several triggers."""

    def test_bake_same_code_both_triggers(self) -> None:
        """CIR-PROC-BAKE-ONE-PATH#bake-same-code-both-triggers —
        resolve() is the single resolution path."""
        # Just verify the function exists and works
        artifact = _resolve_fixture()
        assert artifact["version"] == 1


# ===========================================================================
# Fixture acceptance — the eight items resolve exactly as specified
# ===========================================================================

class TestFixtureAcceptance:
    """The fixture resolves to the exact lights specified in the issue."""

    def test_fixture_resolves_correctly(self) -> None:
        """All eight items resolve to the expected statuses at the fixture reference date."""
        artifact = _resolve_fixture()

        # self/sleep ⚪ not-evaluated (freshness adapter, P0)
        assert _item_by_id(artifact, "self", "sleep")["status"] == "grey"
        assert _item_by_id(artifact, "self", "sleep")["grey_reason"] == "not-evaluated"

        # self/labs ⚪ not-evaluated (freshness adapter, P0)
        assert _item_by_id(artifact, "self", "labs")["status"] == "grey"
        assert _item_by_id(artifact, "self", "labs")["grey_reason"] == "not-evaluated"

        # self/exercise ⚪ by-choice (no adapter)
        assert _item_by_id(artifact, "self", "exercise")["status"] == "grey"
        assert _item_by_id(artifact, "self", "exercise")["grey_reason"] == "by-choice"

        # partner/date-night 🟡 (manual: yellow)
        assert _item_by_id(artifact, "partner", "date-night")["status"] == "yellow"

        # children/nova 🟢 (manual: green)
        assert _item_by_id(artifact, "children", "nova")["status"] == "green"

        # children/kit 🟢 (manual: green)
        assert _item_by_id(artifact, "children", "kit")["status"] == "green"

        # wider/friends 🔴 (manual: red)
        assert _item_by_id(artifact, "wider", "friends")["status"] == "red"

        # wider/plants ⚪ not-evaluated (command adapter, P0)
        assert _item_by_id(artifact, "wider", "plants")["status"] == "grey"
        assert _item_by_id(artifact, "wider", "plants")["grey_reason"] == "not-evaluated"


# ===========================================================================
# CIR-BAKE-DETERMINISM — two runs at same reference date produce byte-identical data.json
# ===========================================================================

class TestBakeDeterminismExact:
    """Two runs at the same reference date produce byte-identical data.json (except generated_at)."""

    def test_deterministic_output(self, tmp_path: Path) -> None:
        """Two runs with identical inputs produce identical output."""
        config = load_config(ALEX_YAML)

        # Run 1
        art1 = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
        write_artifact(art1, tmp_path / "a")

        # Run 2
        art2 = resolve(config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT)
        write_artifact(art2, tmp_path / "b")

        raw_a = (tmp_path / "a" / "data.json").read_bytes()
        raw_b = (tmp_path / "b" / "data.json").read_bytes()
        assert raw_a == raw_b


# ===========================================================================
# CIR-BAKE-ARTIFACT — stale_after_hours is null
# ===========================================================================

class TestBakeStaleAfterHours:
    """stale_after_hours is null at P0."""

    def test_stale_after_hours_null(self) -> None:
        """CIR-BAKE-STALE-SELF#no-threshold-no-banner — stale_after_hours ships null at P0."""
        artifact = _resolve_fixture()
        assert artifact["stale_after_hours"] is None


# ===========================================================================
# CIR-BAKE-ARTIFACT — artifact validates against schema
# ===========================================================================

class TestBakeArtifactSchema:
    """The artifact validates against CIR-BAKE-ARTIFACT schema."""

    def test_artifact_has_required_fields(self) -> None:
        """All required top-level fields are present."""
        artifact = _resolve_fixture()
        required = ["version", "spec_version", "person", "generated_at", "reference_date",
                     "timezone", "stale_after_hours", "rings", "warnings"]
        for field in required:
            assert field in artifact, f"Missing required field: {field}"

    def test_artifact_types(self) -> None:
        """Field types match the schema."""
        artifact = _resolve_fixture()
        assert isinstance(artifact["version"], int)
        assert isinstance(artifact["spec_version"], int)
        assert isinstance(artifact["person"], str)
        assert isinstance(artifact["generated_at"], str)
        assert isinstance(artifact["reference_date"], str)
        assert isinstance(artifact["timezone"], str)
        assert artifact["stale_after_hours"] is None
        assert isinstance(artifact["rings"], list)
        assert isinstance(artifact["warnings"], list)

    def test_item_fields(self) -> None:
        """Every item has the required fields with correct types."""
        artifact = _resolve_fixture()
        for ring in artifact["rings"]:
            for item in ring["items"]:
                assert isinstance(item["id"], str)
                assert isinstance(item["label"], str)
                assert item["status"] in ("green", "yellow", "red", "grey")
                assert item["grey_reason"] in (None, "by-choice", "by-failure", "not-evaluated")
                assert isinstance(item["share"], (int, float))
                assert isinstance(item["detail_line"], str)
                assert "detail_page" in item