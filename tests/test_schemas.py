# Unit guards for the contract-page schemas (RULES.md rule 7; circles#103 step 2):
#   specs/data/data-json.schema.json   — imported by bake/emit.py, which refuses to write a
#                                        violating artifact;
#   specs/data/circles-yaml.schema.json — NOT yet imported by bake/config.py (whose hand-written
#                                        checks own the contract's exact error messages); these
#                                        tests pin that the two agree on the fixture configs and
#                                        on known-bad mutations, until config.py imports it.
#
# Unlabelled on purpose: these are unit guards on the coupling, not system-boundary evidence for
# any one rule (CONVENTIONS § Allure taxonomy). Inputs are built FROM fixtures/alex at runtime.

from __future__ import annotations

import copy
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema
import pytest
import yaml

from bake.config import ConfigError, load_config
from bake.emit import ARTIFACT_SCHEMA, ArtifactSchemaError, write_artifact
from bake.render import add_capacity_warnings
from bake.resolve import resolve

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "fixtures"
ALEX_DIR = FIXTURES / "alex"
CONFIG_SCHEMA = REPO / "specs" / "data" / "circles-yaml.schema.json"
FIXTURE_REFERENCE_DATE = date(2026, 8, 3)
FIXTURE_GENERATED_AT = datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc)
FIXTURE_CONFIGS = sorted(FIXTURES.rglob("circles*.yaml"))


def _validator(path: Path) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def _schema_errors(path: Path, instance: Any) -> list[str]:
    return [e.message for e in _validator(path).iter_errors(instance)]


def _alex() -> dict:
    return yaml.safe_load((ALEX_DIR / "circles.yaml").read_text(encoding="utf-8"))


def _item(raw: dict, ref: str) -> dict:
    ring_id, item_id = ref.split("/")
    ring = next(r for r in raw["rings"] if r["id"] == ring_id)
    return next(i for i in ring["items"] if i["id"] == item_id)


def _config_accepts(tmp_path: Path, raw: dict) -> bool:
    """bake/config.py's verdict on *raw*, written into a tmp copy of fixtures/alex (so source:
    and command: paths resolve exactly as for the fixture)."""
    root = tmp_path / "alex"
    shutil.copytree(ALEX_DIR, root)
    path = root / "circles.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    try:
        load_config(path)
    except ConfigError:
        return False
    return True


# --- the schemas are themselves valid draft 2020-12 ----------------------------------------

@pytest.mark.parametrize("path", [ARTIFACT_SCHEMA, CONFIG_SCHEMA], ids=["data-json", "circles-yaml"])
def test_schema_is_valid_draft_2020_12(path: Path) -> None:
    jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


# --- circles.yaml: schema ⇄ config.py agreement -------------------------------------------

@pytest.mark.parametrize("path", FIXTURE_CONFIGS, ids=[p.name for p in FIXTURE_CONFIGS])
def test_fixture_config_valid_under_both(path: Path) -> None:
    """Every committed fixture config is accepted by the schema AND by config.py."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert _schema_errors(CONFIG_SCHEMA, raw) == []
    load_config(path)  # raises ConfigError on disagreement


def _drop_person(raw: dict) -> None:
    del raw["person"]                                       # CIR-DATA-SCHEMA-TOPLEVEL#person-missing


def _empty_rings(raw: dict) -> None:
    raw["rings"] = []                                       # CIR-DATA-SCHEMA-TOPLEVEL#rings-empty


def _future_version(raw: dict) -> None:
    raw["spec_version"] = 1                                 # CIR-DATA-SCHEMA-VERSION#version-from-the-future


def _ring_id_not_slug(raw: dict) -> None:
    raw["rings"][0]["id"] = "My Ring!"                      # CIR-DATA-SCHEMA-RING#ring-id-not-slug


def _ring_label_missing(raw: dict) -> None:
    del raw["rings"][0]["label"]                            # CIR-DATA-SCHEMA-RING#ring-label-missing


def _item_id_with_slash(raw: dict) -> None:
    _item(raw, "self/exercise")["id"] = "a/b"               # CIR-DATA-IDENTITY#id-with-space-or-slash


def _two_adapters(raw: dict) -> None:
    _item(raw, "partner/date-night")["status"]["freshness"] = (
        copy.deepcopy(_item(raw, "self/sleep")["status"]["freshness"]))  # ...#status-two-adapters


def _unknown_adapter(raw: dict) -> None:
    _item(raw, "partner/date-night")["status"] = {"sqlite": "q"}  # ...#status-unknown-adapter


def _manual_blue(raw: dict) -> None:
    _item(raw, "partner/date-night")["status"]["manual"] = "blue"  # ...#manual-invalid-word


def _link_javascript(raw: dict) -> None:
    _item(raw, "self/exercise")["link"] = "javascript:alert(1)"  # CIR-DATA-SCHEMA-LINK#link-javascript-scheme


def _link_scheme_relative(raw: dict) -> None:
    _item(raw, "self/exercise")["link"] = "//example.test/x"  # CIR-DATA-SCHEMA-LINK#link-scheme-relative


def _share_zero(raw: dict) -> None:
    _item(raw, "children/nova")["share"] = 0                # CIR-DATA-SHARE#share-zero


def _threshold_fractional(raw: dict) -> None:
    _item(raw, "self/sleep")["status"]["freshness"]["yellow_after"] = 3.5  # ...#threshold-fractional


def _source_absolute(raw: dict) -> None:
    _item(raw, "self/sleep")["status"]["freshness"]["source"] = "/etc/hosts"  # CIR-DATA-SOURCE-PATH


def _command_string(raw: dict) -> None:
    _item(raw, "wider/plants")["status"]["command"] = "./notes/plants-status.sh"  # CIR-ADAPT-COMMAND#command-argv-array-required


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(_drop_person, id="person-missing"),
        pytest.param(_empty_rings, id="rings-empty"),
        pytest.param(_future_version, id="version-from-the-future"),
        pytest.param(_ring_id_not_slug, id="ring-id-not-slug"),
        pytest.param(_ring_label_missing, id="ring-label-missing"),
        pytest.param(_item_id_with_slash, id="id-with-slash"),
        pytest.param(_two_adapters, id="status-two-adapters"),
        pytest.param(_unknown_adapter, id="status-unknown-adapter"),
        pytest.param(_manual_blue, id="manual-invalid-word"),
        pytest.param(_link_javascript, id="link-javascript-scheme"),
        pytest.param(_link_scheme_relative, id="link-scheme-relative"),
        pytest.param(_share_zero, id="share-zero"),
        pytest.param(_threshold_fractional, id="threshold-fractional"),
        pytest.param(_source_absolute, id="source-absolute"),
        pytest.param(_command_string, id="command-argv-array-required"),
    ],
)
def test_known_bad_config_rejected_by_both(tmp_path: Path, mutate: Callable[[dict], None]) -> None:
    """Each mutation is a config-error row on its spec page, so both halves must reject it."""
    raw = _alex()
    mutate(raw)
    assert _schema_errors(CONFIG_SCHEMA, raw) != [], "schema accepted a config-error row"
    assert not _config_accepts(tmp_path, raw), "config.py accepted a config-error row"


def _unknown_toplevel(raw: dict) -> None:
    raw["sprinkles"] = True                                 # CIR-DATA-VALIDATION#unknown-toplevel-key


def _unknown_item_key(raw: dict) -> None:
    _item(raw, "self/exercise")["prioritiy"] = "high"       # CIR-DATA-VALIDATION#unknown-item-key


def _empty_ring(raw: dict) -> None:
    raw["rings"][-1]["items"] = []                          # CIR-DATA-VALIDATION#empty-ring


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(_unknown_toplevel, id="unknown-toplevel-key"),
        pytest.param(_unknown_item_key, id="unknown-item-key"),
        pytest.param(_empty_ring, id="empty-ring"),
    ],
)
def test_warning_rows_accepted_by_both(tmp_path: Path, mutate: Callable[[dict], None]) -> None:
    """Build-warning rows (⚖-R7, ⚖-R13) are not config errors: the schema stays open there."""
    raw = _alex()
    mutate(raw)
    assert _schema_errors(CONFIG_SCHEMA, raw) == []
    assert _config_accepts(tmp_path, raw)


# --- data.json: the bake imports the schema -------------------------------------------------

def _fixture_artifact(config_path: Path = ALEX_DIR / "circles.yaml") -> dict:
    config = load_config(config_path)
    return add_capacity_warnings(resolve(
        config, reference_date=FIXTURE_REFERENCE_DATE, generated_at=FIXTURE_GENERATED_AT))


def test_fixture_artifact_valid() -> None:
    assert _schema_errors(ARTIFACT_SCHEMA, _fixture_artifact()) == []


def test_empty_ring_artifact_valid(tmp_path: Path) -> None:
    """A ring-level warning (empty band) carries item: null — the spec's `item` is the
    <ring>/<item> ref or null (data-json.md field table), never a bare ring id."""
    raw = _alex()
    _empty_ring(raw)
    root = tmp_path / "alex"
    shutil.copytree(ALEX_DIR, root)
    path = root / "circles.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")

    artifact = _fixture_artifact(path)

    assert _schema_errors(ARTIFACT_SCHEMA, artifact) == []
    assert any(w["item"] is None and "wider" in w["message"] for w in artifact["warnings"])


@pytest.mark.parametrize(
    "break_it",
    [
        pytest.param(lambda a: a.pop("generated_at"), id="generated_at-dropped"),
        pytest.param(lambda a: a["rings"][0]["items"][0].update(status="🟢"), id="status-emoji"),
        pytest.param(lambda a: a.update(extra="leak"), id="undeclared-field"),
        # rings[1].items[0] is partner/date-night, manual: yellow in the fixture
        pytest.param(lambda a: a["rings"][1]["items"][0].update(grey_reason="by-choice"),
                     id="grey_reason-on-a-yellow-item"),
    ],
)
def test_write_artifact_refuses_invalid_and_writes_nothing(
    tmp_path: Path, break_it: Callable[[dict], Any]
) -> None:
    artifact = _fixture_artifact()
    break_it(artifact)
    out = tmp_path / "dist"

    with pytest.raises(ArtifactSchemaError):
        write_artifact(artifact, out)

    assert not out.exists()
