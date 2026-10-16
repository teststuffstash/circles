# Evidence for the circles.yaml rules — config shape, config errors, build warnings.
#
# World: alex — every case starts from fixtures/alex (the spec pages' declared world:
# specs/data/circles-yaml.md "World: alex") and turns at most one knob; the knob and its value
# name the given step. The system boundary these rules are stated against is the bake CLI
# (`python -m bake`): its exit code, its stderr, and the artifact it writes (out/data.json). Each
# labelled case therefore reads given (world + knob) → when (ONE bake run) → then (one verdict
# per claim) — tests/evidence_helpers.py, after allure-behavior-snippets CONVENTIONS § Prime rule
# of reporting. Each case cites its spec row as CIR-<AREA>-<NAME>#<row-id> (the case title the
# spec join matches — tests/rules.py `case_title`).
#
# Expected values come from the spec row (and, for the unmodified world, the fixture comments in
# fixtures/alex/circles.yaml), never from running the bake. The stderr fragments are the
# message words each config-error row has always been held to.

from __future__ import annotations

import pytest

from bake.config import ConfigError, load_config
from evidence_helpers import given_alex, given_file, item, item_of, ring, then_config_error, verdict, when_bake
from rules import rule


# ===========================================================================
# CIR-DATA-SCHEMA-TOPLEVEL — top-level shape
# ===========================================================================

class TestSchemaToplevel:
    """CIR-DATA-SCHEMA-TOPLEVEL — top-level shape."""

    @rule("CIR-DATA-SCHEMA-TOPLEVEL")
    def test_minimal_valid_config(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#minimal-valid-config — person + one ring with one item, no
        status: → valid; the item renders ⚪ (grey, unmonitored by choice)."""
        def minimal(c):
            exercise = item(c, "self/exercise")  # alex's id+label-only item
            c.clear()
            c.update(person="Alex Example", rings=[{"id": "self", "label": "① Self", "items": [exercise]}])
        config = given_alex(alex_copy, "only person + rings: [self: [exercise]]", minimal)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("person", run.data["person"], "Alex Example")
        verdict("ring ids", [r["id"] for r in run.data["rings"]], ["self"])
        verdict("self/exercise status", item_of(run.data, "self/exercise")["status"], "grey")
        verdict("self/exercise grey_reason", item_of(run.data, "self/exercise")["grey_reason"], "by-choice")

    @rule("CIR-DATA-SCHEMA-TOPLEVEL")
    def test_person_missing(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#person-missing — no person: key → config error."""
        config = given_alex(alex_copy, "person: deleted", lambda c: c.pop("person"))
        then_config_error(when_bake(config), "person")

    @rule("CIR-DATA-SCHEMA-TOPLEVEL")
    def test_rings_empty(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#rings-empty — rings: [] → config error (nothing to draw)."""
        config = given_alex(alex_copy, "rings: []", lambda c: c.update(rings=[]))
        then_config_error(when_bake(config), "nothing to draw")

    @rule("CIR-DATA-SCHEMA-TOPLEVEL")
    def test_rings_order_is_inside_out(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#rings-order-is-inside-out — alex's rings [self, partner,
        children, wider]: array order is geometry order, carried into the artifact as-is."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("ring ids", [r["id"] for r in run.data["rings"]], ["self", "partner", "children", "wider"])

    @rule("CIR-DATA-SCHEMA-TOPLEVEL")
    def test_timezone_omitted(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#timezone-omitted — alex has no timezone: → UTC."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("timezone", run.data["timezone"], "UTC")

    @rule("CIR-DATA-SCHEMA-TOPLEVEL")
    def test_timezone_valid(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-TOPLEVEL#timezone-valid — timezone: Europe/Tallinn accepted as-is."""
        config = given_alex(alex_copy, "timezone: Europe/Tallinn",
                            lambda c: c.update(timezone="Europe/Tallinn"))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("timezone", run.data["timezone"], "Europe/Tallinn")


# ===========================================================================
# CIR-DATA-SCHEMA-VERSION — spec_version guards the format
# ===========================================================================

class TestSchemaVersion:
    """CIR-DATA-SCHEMA-VERSION — spec_version guards the format."""

    @rule("CIR-DATA-SCHEMA-VERSION")
    def test_version_absent_defaults_zero(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-VERSION#version-absent-defaults-zero — alex has no spec_version → v0."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("spec_version", run.data["spec_version"], 0)

    @rule("CIR-DATA-SCHEMA-VERSION")
    def test_version_matches(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-VERSION#version-matches — spec_version: 0 is valid."""
        config = given_alex(alex_copy, "spec_version: 0", lambda c: c.update(spec_version=0))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("spec_version", run.data["spec_version"], 0)

    @rule("CIR-DATA-SCHEMA-VERSION")
    def test_version_from_the_future(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-VERSION#version-from-the-future — spec_version: 1 → config error
        "config is newer than this build"."""
        config = given_alex(alex_copy, "spec_version: 1", lambda c: c.update(spec_version=1))
        then_config_error(when_bake(config), "newer than this build")


# ===========================================================================
# CIR-DATA-SCHEMA-RING — ring fields
# ===========================================================================

class TestSchemaRing:
    """CIR-DATA-SCHEMA-RING — ring fields."""

    @rule("CIR-DATA-SCHEMA-RING")
    def test_ring_id_slug(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-RING#ring-id-slug — alex's `id: self` is a slug → accepted."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("rings[0].id", run.data["rings"][0]["id"], "self")

    @rule("CIR-DATA-SCHEMA-RING")
    def test_ring_id_not_slug(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-RING#ring-id-not-slug — `id: "My Ring!"` → config error."""
        config = given_alex(alex_copy, "ring self renamed: id = 'My Ring!'",
                            lambda c: ring(c, "self").update(id="My Ring!"))
        then_config_error(when_bake(config), "slug")

    @rule("CIR-DATA-SCHEMA-RING")
    def test_ring_id_duplicate(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-RING#ring-id-duplicate — two rings with `id: self` → config error."""
        config = given_alex(alex_copy, "ring partner renamed: id = 'self' (a second self)",
                            lambda c: ring(c, "partner").update(id="self"))
        then_config_error(when_bake(config), "duplicate ring id")

    @rule("CIR-DATA-SCHEMA-RING")
    def test_ring_label_missing(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-RING#ring-label-missing — ring without label: → config error."""
        config = given_alex(alex_copy, "ring self label: deleted", lambda c: ring(c, "self").pop("label"))
        then_config_error(when_bake(config), "label")

    @rule("CIR-DATA-SCHEMA-RING")
    def test_ring_label_glyphs(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-RING#ring-label-glyphs — alex's `label: "③ Children"`: labels are
        opaque Unicode, glyphs pass through untouched."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("children label", next(r for r in run.data["rings"] if r["id"] == "children")["label"],
                "③ Children")


# ===========================================================================
# CIR-DATA-SCHEMA-ITEM — item fields
# ===========================================================================

class TestSchemaItem:
    """CIR-DATA-SCHEMA-ITEM — item fields. alex's self/exercise is the id + label-only item."""

    @rule("CIR-DATA-SCHEMA-ITEM")
    def test_item_minimal(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-ITEM#item-minimal — id + label only (self/exercise) → valid,
        ⚪ unmonitored, no guardrail/link, share 1."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        exercise = item_of(run.data, "self/exercise")
        verdict("self/exercise label", exercise["label"], "Exercise")
        verdict("self/exercise status, grey_reason", [exercise["status"], exercise["grey_reason"]],
                ["grey", "by-choice"])
        verdict("self/exercise guardrail, link", [exercise["guardrail"], exercise["link"]], [None, None])
        verdict("self/exercise share", exercise["share"], 1.0)

    @rule("CIR-DATA-SCHEMA-ITEM")
    def test_item_id_duplicate_in_ring(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-ITEM#item-id-duplicate-in-ring — two `id: sleep` in one ring → config error."""
        config = given_alex(alex_copy, "self/labs renamed: id = 'sleep' (a second self/sleep)",
                            lambda c: item(c, "self/labs").update(id="sleep"))
        then_config_error(when_bake(config), "duplicate item id")

    @rule("CIR-DATA-SCHEMA-ITEM")
    def test_guardrail_absent(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-ITEM#guardrail-absent — self/exercise has no guardrail: → none in the artifact."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("self/exercise guardrail", item_of(run.data, "self/exercise")["guardrail"], None)

    @rule("CIR-DATA-SCHEMA-ITEM")
    def test_note_absent(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-ITEM#note-absent — self/exercise has no note: → none in the artifact."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("self/exercise note", item_of(run.data, "self/exercise")["note"], None)

    @rule("CIR-DATA-SCHEMA-ITEM")
    def test_share_default(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-ITEM#share-default — self/exercise has no share: → weight 1."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("self/exercise share", item_of(run.data, "self/exercise")["share"], 1.0)


# ===========================================================================
# CIR-DATA-IDENTITY — ids, uniqueness and the item ref
# ===========================================================================

class TestDataIdentity:
    """CIR-DATA-IDENTITY — ids, uniqueness and the item ref."""

    @rule("CIR-DATA-IDENTITY")
    @pytest.mark.parametrize("item_id", [
        pytest.param("sleep", id="valid-simple"),
        pytest.param("date-night", id="valid-hyphen"),
        pytest.param("nova123", id="valid-digits"),
        pytest.param("a", id="valid-single-char"),
    ])
    def test_id_character_set_valid(self, alex_copy, item_id: str) -> None:
        """CIR-DATA-IDENTITY#id-character-set — ids matching ^[a-z0-9][a-z0-9-]*$ are valid."""
        config = given_alex(alex_copy, f"self/sleep renamed: item_id = {item_id!r}",
                            lambda c: item(c, "self/sleep").update(id=item_id))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("self item ids", [i["id"] for i in run.data["rings"][0]["items"]], item_id, op="contains")

    @rule("CIR-DATA-IDENTITY")
    @pytest.mark.parametrize("item_id,error_pattern", [
        pytest.param("date night", "space", id="invalid-space"),
        pytest.param("a/b", "slash", id="invalid-slash"),
        pytest.param("UPPERCASE", "slug", id="invalid-uppercase"),
        pytest.param("", "slug", id="invalid-empty"),
    ])
    def test_id_invalid(self, alex_copy, item_id: str, error_pattern: str) -> None:
        """CIR-DATA-IDENTITY#id-with-space-or-slash — invalid ids → config error naming the
        specific rule (⚖-R52)."""
        config = given_alex(alex_copy, f"self/sleep renamed: item_id = {item_id!r}",
                            lambda c: item(c, "self/sleep").update(id=item_id))
        then_config_error(when_bake(config), error_pattern)

    @rule("CIR-DATA-IDENTITY")
    def test_id_missing(self, alex_copy) -> None:
        """CIR-DATA-IDENTITY#id-missing — item with label: only → config error."""
        config = given_alex(alex_copy, "self/exercise id: deleted", lambda c: item(c, "self/exercise").pop("id"))
        then_config_error(when_bake(config), "'id' is required")

    @rule("CIR-DATA-IDENTITY")
    def test_same_id_different_rings(self, alex_copy) -> None:
        """CIR-DATA-IDENTITY#same-id-different-rings — self/sleep and wider/sleep → valid; two
        independent cells."""
        config = given_alex(alex_copy, "wider/sleep added (id + label)",
                            lambda c: ring(c, "wider")["items"].append({"id": "sleep", "label": "Sleep"}))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("ring count", len(run.data["rings"]), 4)
        verdict("self/sleep id", item_of(run.data, "self/sleep")["id"], "sleep")
        verdict("wider/sleep id", item_of(run.data, "wider/sleep")["id"], "sleep")


# ===========================================================================
# CIR-DATA-SCHEMA-ADAPTER-SLOT — the status map
# ===========================================================================

class TestSchemaAdapterSlot:
    """CIR-DATA-SCHEMA-ADAPTER-SLOT — the status map."""

    @rule("CIR-DATA-SCHEMA-ADAPTER-SLOT")
    def test_status_absent(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#status-absent — self/exercise has no status: → ⚪
        unmonitored by choice."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        exercise = item_of(run.data, "self/exercise")
        verdict("self/exercise status, grey_reason", [exercise["status"], exercise["grey_reason"]],
                ["grey", "by-choice"])

    @rule("CIR-DATA-SCHEMA-ADAPTER-SLOT")
    def test_status_two_adapters(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#status-two-adapters — both manual: and freshness: → config error."""
        config = given_alex(alex_copy, "self/sleep status: freshness + manual: green",
                            lambda c: item(c, "self/sleep")["status"].update(manual="green"))
        then_config_error(when_bake(config), "multiple adapter keys")

    @rule("CIR-DATA-SCHEMA-ADAPTER-SLOT")
    def test_status_unknown_adapter(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#status-unknown-adapter — status: {sqlite: …} → config error."""
        config = given_alex(alex_copy, "self/exercise status: sqlite",
                            lambda c: item(c, "self/exercise").update(status={"sqlite": {"query": "SELECT 1"}}))
        then_config_error(when_bake(config), "unknown adapter")

    @rule("CIR-DATA-SCHEMA-ADAPTER-SLOT")
    def test_manual_invalid_word(self, alex_copy) -> None:
        """CIR-DATA-SCHEMA-ADAPTER-SLOT#manual-invalid-word — manual: blue → config error."""
        config = given_alex(alex_copy, "partner/date-night status: manual: blue",
                            lambda c: item(c, "partner/date-night").update(status={"manual": "blue"}))
        then_config_error(when_bake(config), "not a valid manual value")


# ===========================================================================
# CIR-DATA-SCHEMA-LINK — click-through targets
# ===========================================================================

class TestSchemaLink:
    """CIR-DATA-SCHEMA-LINK — click-through targets (on alex's self/labs)."""

    @rule("CIR-DATA-SCHEMA-LINK")
    @pytest.mark.parametrize("link", [
        pytest.param("https://example.test/labs", id="CIR-DATA-SCHEMA-LINK#link-https"),
        pytest.param("/details/self-sleep.html", id="CIR-DATA-SCHEMA-LINK#link-root-relative"),
        pytest.param("http://example.test/page", id="CIR-DATA-SCHEMA-LINK#link-http"),
    ])
    def test_link_valid(self, alex_copy, link: str) -> None:
        """Valid links are accepted and carried into the artifact."""
        config = given_alex(alex_copy, f"self/labs link = {link!r}",
                            lambda c: item(c, "self/labs").update(link=link))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("self/labs link", item_of(run.data, "self/labs")["link"], link)

    @rule("CIR-DATA-SCHEMA-LINK")
    @pytest.mark.parametrize("link,error_pattern", [
        pytest.param("javascript:alert(1)", "javascript", id="CIR-DATA-SCHEMA-LINK#link-javascript-scheme"),
        pytest.param("data:text/html,hi", "data:", id="CIR-DATA-SCHEMA-LINK#link-data-scheme"),
        pytest.param("//example.test/x", "scheme-relative", id="CIR-DATA-SCHEMA-LINK#link-scheme-relative"),
        pytest.param("details/sleep.html", "bare relative", id="CIR-DATA-SCHEMA-LINK#link-bare-relative"),
    ])
    def test_link_invalid(self, alex_copy, link: str, error_pattern: str) -> None:
        """Invalid links → config error."""
        config = given_alex(alex_copy, f"self/labs link = {link!r}",
                            lambda c: item(c, "self/labs").update(link=link))
        then_config_error(when_bake(config), error_pattern)


# ===========================================================================
# CIR-DATA-SHARE — arc weights within a ring
# ===========================================================================

class TestDataShare:
    """CIR-DATA-SHARE — arc weights within a ring (alex's children: nova + kit)."""

    @rule("CIR-DATA-SHARE")
    def test_shares_equal_halves(self, alex_copy) -> None:
        """CIR-DATA-SHARE#shares-equal-halves — alex's nova/kit share: 0.5 each → two halves."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        shares = [item_of(run.data, ref)["share"] for ref in ("children/nova", "children/kit")]
        verdict("children/nova, children/kit share", shares, [0.5, 0.5])
        verdict("children share sum", sum(shares), 1.0)

    @rule("CIR-DATA-SHARE")
    def test_shares_absent_equal(self, alex_copy) -> None:
        """CIR-DATA-SHARE#shares-absent-equal — alex's self ring: three siblings, no share: →
        three equal weights."""
        config = given_alex(alex_copy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("self shares", [i["share"] for i in run.data["rings"][0]["items"]], [1.0, 1.0, 1.0])

    @rule("CIR-DATA-SHARE")
    def test_shares_mixed(self, alex_copy) -> None:
        """CIR-DATA-SHARE#shares-mixed — nova share: 2, kit no share → weights 2 / 1, plus a
        build warning (⚖-R12)."""
        def mixed(c):
            item(c, "children/nova")["share"] = 2
            item(c, "children/kit").pop("share")
        config = given_alex(alex_copy, "children/nova share: 2, children/kit share: deleted", mixed)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("children/nova, children/kit share",
                [item_of(run.data, ref)["share"] for ref in ("children/nova", "children/kit")], [2.0, 1.0])
        verdict("build warnings", run.warnings, "mixes declared and undeclared", op="contains")

    @rule("CIR-DATA-SHARE")
    def test_shares_mixed_fractional(self, alex_copy) -> None:
        """CIR-DATA-SHARE#shares-mixed-fractional — nova share: 0.5, kit no share → weights
        0.5 / 1, plus a build warning (⚖-R12)."""
        config = given_alex(alex_copy, "children/kit share: deleted (nova keeps 0.5)",
                            lambda c: item(c, "children/kit").pop("share"))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("children/nova, children/kit share",
                [item_of(run.data, ref)["share"] for ref in ("children/nova", "children/kit")], [0.5, 1.0])
        verdict("build warnings", run.warnings, "mixes declared and undeclared", op="contains")

    @rule("CIR-DATA-SHARE")
    def test_share_zero(self, alex_copy) -> None:
        """CIR-DATA-SHARE#share-zero — share: 0 → config error."""
        config = given_alex(alex_copy, "children/kit share: 0",
                            lambda c: item(c, "children/kit").update(share=0))
        then_config_error(when_bake(config), "> 0")

    @rule("CIR-DATA-SHARE")
    def test_share_negative(self, alex_copy) -> None:
        """CIR-DATA-SHARE#share-negative — share: -1 → config error."""
        config = given_alex(alex_copy, "children/kit share: -1",
                            lambda c: item(c, "children/kit").update(share=-1))
        then_config_error(when_bake(config), "> 0")


# ===========================================================================
# CIR-DATA-VALIDATION — fail vs warn
# ===========================================================================

class TestDataValidation:
    """CIR-DATA-VALIDATION — fail vs warn."""

    @rule("CIR-DATA-VALIDATION")
    def test_one_bad_item_fails_bake(self, alex_copy) -> None:
        """CIR-DATA-VALIDATION#one-bad-item-fails-bake — alex's 8 valid items + 1 with
        manual: blue → the whole bake fails, nothing written."""
        config = given_alex(alex_copy, "wider/bad added with status: manual: blue",
                            lambda c: ring(c, "wider")["items"].append(
                                {"id": "bad", "label": "Bad", "status": {"manual": "blue"}}))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 1)
        verdict("artifact files in out/", run.artifact_files, [])

    @rule("CIR-DATA-VALIDATION")
    def test_unknown_toplevel_key(self, alex_copy) -> None:
        """CIR-DATA-VALIDATION#unknown-toplevel-key — sprinkles: true → warning, bake proceeds."""
        config = given_alex(alex_copy, "sprinkles: true", lambda c: c.update(sprinkles=True))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("build warnings", run.warnings, "sprinkles", op="contains")

    @rule("CIR-DATA-VALIDATION")
    def test_unknown_item_key(self, alex_copy) -> None:
        """CIR-DATA-VALIDATION#unknown-item-key — item with prioritiy: high → warning, bake proceeds."""
        config = given_alex(alex_copy, "self/exercise prioritiy: high",
                            lambda c: item(c, "self/exercise").update(prioritiy="high"))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("build warnings", run.warnings, "prioritiy", op="contains")

    @rule("CIR-DATA-VALIDATION")
    def test_unknown_status_key(self, alex_copy) -> None:
        """CIR-DATA-VALIDATION#unknown-status-key — status: {freshnes: …} (typo) → config error."""
        def typo(c):
            status = item(c, "self/sleep")["status"]
            status["freshnes"] = status.pop("freshness")
        config = given_alex(alex_copy, "self/sleep status key: freshness → freshnes", typo)
        then_config_error(when_bake(config), "unknown adapter")

    @rule("CIR-DATA-VALIDATION")
    def test_empty_ring(self, alex_copy) -> None:
        """CIR-DATA-VALIDATION#empty-ring — ring with items: [] → warning, bake proceeds."""
        config = given_alex(alex_copy, "ring partner items: []",
                            lambda c: ring(c, "partner").update(items=[]))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("partner items", next(r for r in run.data["rings"] if r["id"] == "partner")["items"], [])
        verdict("build warnings", run.warnings, "no items", op="contains")


# ===========================================================================
# CIR-DATA-FRESHNESS-THRESHOLDS — threshold validation (on alex's self/sleep, 7 / 30)
# ===========================================================================

class TestDataFreshnessThresholds:
    """CIR-DATA-FRESHNESS-THRESHOLDS — threshold validation."""

    @rule("CIR-DATA-FRESHNESS-THRESHOLDS")
    def test_thresholds_valid(self, alex_copy) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#thresholds-valid — alex's self/labs (yellow_after 100,
        red_after 190) is valid and drives its light: evaluated at the fixture reference date the
        labs entry is 200 days old > red_after 190 → red (fixtures/alex/circles.yaml comment)."""
        config = given_alex(alex_copy)
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("self/labs status", item_of(run.data, "self/labs")["status"], "red")

    @rule("CIR-DATA-FRESHNESS-THRESHOLDS")
    def test_thresholds_equal(self, alex_copy) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#thresholds-equal — yellow == red → config error."""
        config = given_alex(alex_copy, "self/sleep yellow_after: 7, red_after: 7",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(yellow_after=7, red_after=7))
        then_config_error(when_bake(config), "strictly less")

    @rule("CIR-DATA-FRESHNESS-THRESHOLDS")
    def test_thresholds_inverted(self, alex_copy) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#thresholds-inverted — yellow > red → config error."""
        config = given_alex(alex_copy, "self/sleep yellow_after: 30, red_after: 7",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(yellow_after=30, red_after=7))
        then_config_error(when_bake(config), "strictly less")

    @rule("CIR-DATA-FRESHNESS-THRESHOLDS")
    def test_threshold_zero(self, alex_copy) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#threshold-zero — yellow_after: 0 → config error."""
        config = given_alex(alex_copy, "self/sleep yellow_after: 0",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(yellow_after=0))
        then_config_error(when_bake(config), "≥ 1")

    @rule("CIR-DATA-FRESHNESS-THRESHOLDS")
    def test_threshold_fractional(self, alex_copy) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#threshold-fractional — yellow_after: 3.5 → config error."""
        config = given_alex(alex_copy, "self/sleep yellow_after: 3.5",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(yellow_after=3.5))
        then_config_error(when_bake(config), "integer")

    @rule("CIR-DATA-FRESHNESS-THRESHOLDS")
    def test_threshold_missing(self, alex_copy) -> None:
        """CIR-DATA-FRESHNESS-THRESHOLDS#threshold-missing — freshness: with source: only → config error."""
        def source_only(c):
            freshness = item(c, "self/sleep")["status"]["freshness"]
            del freshness["yellow_after"], freshness["red_after"]
        config = given_alex(alex_copy, "self/sleep freshness: source only (thresholds deleted)", source_only)
        then_config_error(when_bake(config), "required")


# ===========================================================================
# CIR-DATA-CONFIG-ERROR-FAILS — config errors publish nothing
# ===========================================================================

class TestDataConfigErrorFails:
    """CIR-DATA-CONFIG-ERROR-FAILS — config errors publish nothing."""

    @rule("CIR-DATA-CONFIG-ERROR-FAILS")
    def test_config_error_aborts_whole_bake(self, alex_copy) -> None:
        """CIR-DATA-CONFIG-ERROR-FAILS#config-error-aborts-whole-bake — one item with an unknown
        status: key, nine valid items (alex's 8 + wider/pets) → non-zero exit; no artifact written."""
        def one_bad_of_ten(c):
            ring(c, "wider")["items"] += [{"id": "pets", "label": "Pets"},
                                          {"id": "bad", "label": "Bad", "status": {"freshnes": {}}}]
        config = given_alex(alex_copy, "wider/pets added (valid), wider/bad added with status: freshnes",
                            one_bad_of_ten)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 1)
        verdict("artifact files in out/", run.artifact_files, [])

    @rule("CIR-DATA-CONFIG-ERROR-FAILS")
    def test_message_names_the_item(self, alex_copy) -> None:
        """CIR-DATA-CONFIG-ERROR-FAILS#message-names-the-item — error inside children/kit →
        message contains children/kit."""
        config = given_alex(alex_copy, "children/kit status: manual: blue",
                            lambda c: item(c, "children/kit").update(status={"manual": "blue"}))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 1)
        verdict("stderr", run.stderr, "children/kit", op="contains")


# ===========================================================================
# CIR-DATA-SOURCE-PATH — config-error rows only (on alex's self/sleep freshness source)
# ===========================================================================

class TestDataSourcePath:
    """CIR-DATA-SOURCE-PATH — config-error rows (validation only)."""

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_parent_traversal(self, alex_copy) -> None:
        """CIR-DATA-SOURCE-PATH#source-parent-traversal — parent traversal → config error."""
        config = given_alex(alex_copy, "self/sleep source: ../../etc/hosts",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(source="../../etc/hosts"))
        then_config_error(when_bake(config), "escape")

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_absolute_path(self, alex_copy) -> None:
        """CIR-DATA-SOURCE-PATH#source-absolute-path — absolute path → config error (⚖-R52)."""
        config = given_alex(alex_copy, "self/sleep source: /etc/hosts",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(source="/etc/hosts"))
        then_config_error(when_bake(config), "absolute path")

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_non_literal_parent_traversal(self, alex_copy) -> None:
        """CIR-DATA-SOURCE-PATH#source-non-literal-parent-traversal — 'sub/../../etc/hosts' does
        not start with '..' but normalizes to an escape → config error."""
        config = given_alex(alex_copy, "self/sleep source: sub/../../etc/hosts",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(source="sub/../../etc/hosts"))
        then_config_error(when_bake(config), "escape")


# ===========================================================================
# CIR-ADAPT-COMMAND — config-error rows only (on alex's wider/plants command)
# ===========================================================================

class TestAdaptCommand:
    """CIR-ADAPT-COMMAND — config-error rows (validation only)."""

    @rule("CIR-ADAPT-COMMAND")
    def test_command_argv_array_required(self, alex_copy) -> None:
        """CIR-ADAPT-COMMAND#command-argv-array-required — string → config error naming the array form."""
        config = given_alex(alex_copy, "wider/plants command: './x.sh --flag' (a string)",
                            lambda c: item(c, "wider/plants").update(status={"command": "./x.sh --flag"}))
        then_config_error(when_bake(config), "array")

    @rule("CIR-ADAPT-COMMAND")
    def test_command_executable_not_found(self, alex_copy) -> None:
        """CIR-ADAPT-COMMAND#command-executable-exists-at-validation — argv[0] missing → config error."""
        config = given_alex(alex_copy, "wider/plants command: ['./nonexistent.sh']",
                            lambda c: item(c, "wider/plants").update(status={"command": ["./nonexistent.sh"]}))
        then_config_error(when_bake(config), "not found")

    @rule("CIR-ADAPT-COMMAND")
    def test_command_executable_not_executable(self, alex_copy) -> None:
        """CIR-ADAPT-COMMAND#command-executable-bit-at-validation — argv[0] without the exec bit
        → config error naming the file."""
        def noexec(c):
            item(c, "wider/plants").update(status={"command": ["./noexec.sh"]})
        config = given_alex(alex_copy, "wider/plants command: ['./noexec.sh'] (mode 0644)", noexec)
        script = given_file(config, "noexec.sh", "#!/bin/sh\necho green\n")
        script.chmod(0o644)  # no exec bit — the row's input
        run = when_bake(config)
        then_config_error(run, "not executable")
        verdict("stderr", run.stderr, "noexec.sh", op="contains")


# ===========================================================================
# CIR-DATA-STATUS-MANUAL-VALUES — the manual adapter's vocabulary (on partner/date-night)
# ===========================================================================

class TestDataStatusManualValues:
    """CIR-DATA-STATUS-MANUAL-VALUES — the manual adapter's vocabulary."""

    @rule("CIR-DATA-STATUS-MANUAL-VALUES")
    def test_manual_lowercase_only(self, alex_copy) -> None:
        """CIR-DATA-STATUS-MANUAL-VALUES#manual-lowercase-only — 'Green' → config error."""
        config = given_alex(alex_copy, "partner/date-night manual: Green",
                            lambda c: item(c, "partner/date-night").update(status={"manual": "Green"}))
        then_config_error(when_bake(config), "lowercase")

    @rule("CIR-DATA-STATUS-MANUAL-VALUES")
    def test_manual_grey_rejected(self, alex_copy) -> None:
        """CIR-DATA-STATUS-MANUAL-VALUES#manual-grey-rejected — 'grey' → config error."""
        config = given_alex(alex_copy, "partner/date-night manual: grey",
                            lambda c: item(c, "partner/date-night").update(status={"manual": "grey"}))
        then_config_error(when_bake(config), "grey")


# ===========================================================================
# Fixture acceptance — CIR-PROC-TEST-FIXTURES#fixture-validates-against-the-schema
# ===========================================================================

class TestFixtureAcceptance:
    """The fixture validates against the schema, and every source:/command: path resolves."""

    @rule("CIR-PROC-TEST-FIXTURES")
    def test_fixture_alex_validates(self, alex_copy) -> None:
        """CIR-PROC-TEST-FIXTURES#fixture-validates-against-the-schema — the unmodified world bakes
        (--evaluate, so every freshness source and the plants command actually resolves) into
        4 rings / 8 items with the lights, shares and guardrails fixtures/alex/circles.yaml states.

        Expected lights at the fixture reference date, from the fixture's own comments and the
        spec rows it is the key example of: sleep 🟢 (age 2 < yellow_after 7), labs 🔴 (age 200 >
        red_after 190), exercise ⚪ by-choice (no adapter), date-night / nova / kit / friends
        their manual words, plants 🟡 (CIR-ADAPT-COMMAND#command-prints-yellow)."""
        config = given_alex(alex_copy)
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("person, spec_version, timezone",
                [run.data["person"], run.data["spec_version"], run.data["timezone"]],
                ["Alex Example", 0, "UTC"])
        verdict("items per ring", {r["id"]: [i["id"] for i in r["items"]] for r in run.data["rings"]}, {
            "self": ["sleep", "labs", "exercise"],
            "partner": ["date-night"],
            "children": ["nova", "kit"],
            "wider": ["friends", "plants"],
        })
        verdict("lights", {f"{r['id']}/{i['id']}": i["status"] for r in run.data["rings"] for i in r["items"]}, {
            "self/sleep": "green", "self/labs": "red", "self/exercise": "grey",
            "partner/date-night": "yellow",
            "children/nova": "green", "children/kit": "green",
            "wider/friends": "red", "wider/plants": "yellow",
        })
        verdict("children/nova, children/kit share",
                [item_of(run.data, ref)["share"] for ref in ("children/nova", "children/kit")], [0.5, 0.5])
        verdict("guardrails", {ref: item_of(run.data, ref)["guardrail"]
                               for ref in ("self/sleep", "self/labs", "partner/date-night")}, {
            "self/sleep": "Lights out by 23:00 on weeknights",
            "self/labs": "Blood panel every 90 days",
            "partner/date-night": "Protected evening, twice a month",
        })


# ===========================================================================
# Unlabelled unit guards — internals the CLI cases do not reach (CONVENTIONS § Allure
# taxonomy: unit tests stay unlabelled and are never evidence)
# ===========================================================================

def test_command_empty_argv(alex_copy) -> None:
    """Empty argv array → config error (no spec row; guards bake/config.py's argv check)."""
    config = alex_copy(commands={"wider/plants": []})
    with pytest.raises(ConfigError, match="at least one"):
        load_config(config)
