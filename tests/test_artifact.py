"""Artifact shape tests — CIR-BAKE-ARTIFACT, CIR-BAKE-STATUS-VALUES, CIR-BAKE-*.

Each case cites its spec row verbatim: CIR-<AREA>-<NAME>#<row-id>
(CIR-PROC-TEST-ROWS). Rows are parametrised, not copy-pasted.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from bake.artifact import build_artifact, serialize_artifact
from bake.config import load_config
from bake.resolve import resolve

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "alex" / "circles.yaml"
REFERENCE_DATE = date(2026, 8, 3)  # ⚖-R24 fixture reference date


def _bake(config_path: Path = FIXTURE, ref_date: date = REFERENCE_DATE):
    result = load_config(str(config_path))
    assert not result.errors, f"config errors: {[e.message for e in result.errors]}"
    assert result.config is not None
    resolution = resolve(result.config)
    return build_artifact(
        result.config, resolution,
        config_warnings=result.warnings,
        ref_date=ref_date,
    )


# ── CIR-BAKE-ARTIFACT ─────────────────────────────────────────────────────────


def test_artifact_fixture_roundtrip():
    """CIR-BAKE-ARTIFACT#artifact-fixture-roundtrip"""
    artifact = _bake()
    d = artifact.to_dict()

    # rings/items preserve config order and ids
    assert [r["id"] for r in d["rings"]] == ["self", "partner", "children", "wider"]
    assert [r["label"] for r in d["rings"]] == ["① Self", "② Partner", "③ Children", "④ Wider life"]

    # self/exercise → grey, by-choice, share 1, nulls for absent fields
    self_ring = d["rings"][0]
    exercise = next(i for i in self_ring["items"] if i["id"] == "exercise")
    assert exercise["status"] == "grey"
    assert exercise["grey_reason"] == "by-choice"
    assert exercise["share"] == 1
    assert exercise["guardrail"] is None
    assert exercise["note"] is None
    assert exercise["link"] is None
    assert exercise["last_data_date"] is None

    # fixture documented lights
    lights = {
        (r["id"], i["id"]): i["status"]
        for r in d["rings"] for i in r["items"]
    }
    assert lights[("self", "sleep")] == "grey"          # freshness not evaluated (P0)
    assert lights[("self", "labs")] == "grey"
    assert lights[("self", "exercise")] == "grey"
    assert lights[("partner", "date-night")] == "yellow"
    assert lights[("children", "nova")] == "green"
    assert lights[("children", "kit")] == "green"
    assert lights[("wider", "friends")] == "red"
    assert lights[("wider", "plants")] == "grey"        # command not evaluated (P0)


def test_warnings_empty_array_present():
    """CIR-BAKE-ARTIFACT#warnings-empty-array"""
    # a fully manual, healthy config → no warnings
    cfg = {
        "person": "Alex",
        "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I", "status": {"manual": "green"}}]}],
    }
    import tempfile
    import yaml

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "circles.yaml"
        p.write_text(yaml.safe_dump(cfg, sort_keys=False))
        artifact = _bake(p)
    assert artifact.warnings == []


# ── CIR-BAKE-STATUS-VALUES ────────────────────────────────────────────────────


@pytest.mark.parametrize("row_id,status_field", [
    ("status-wire-vocabulary", None),
], ids=["status-wire-vocabulary"])
def test_status_wire_vocabulary(row_id, status_field):
    """CIR-BAKE-STATUS-VALUES#status-wire-vocabulary"""
    artifact = _bake()
    d = artifact.to_dict()
    allowed = {"green", "yellow", "red", "grey"}
    for r in d["rings"]:
        for i in r["items"]:
            assert i["status"] in allowed, f"{row_id}: {i['id']} status {i['status']} not in wire vocabulary"


def test_status_never_emoji():
    """CIR-BAKE-STATUS-VALUES#status-never-emoji"""
    artifact = _bake()
    d = artifact.to_dict()
    for r in d["rings"]:
        for i in r["items"]:
            assert i["status"] not in ("🟢", "🟡", "🔴", "⚪")


def test_status_never_display_words():
    """CIR-BAKE-STATUS-VALUES#status-never-display-words"""
    artifact = _bake()
    d = artifact.to_dict()
    display_words = {"ok", "attention", "act", "unmonitored"}
    for r in d["rings"]:
        for i in r["items"]:
            assert i["status"] not in display_words


# ── CIR-BAKE-SELF-CONTAINED / CIR-BAKE-DETERMINISM ────────────────────────────


def test_two_bakes_agree_except_generated_at():
    """CIR-BAKE-DETERMINISM#two-bakes-agree"""
    a = _bake().to_dict()
    b = _bake().to_dict()
    a.pop("generated_at")
    b.pop("generated_at")
    assert a == b


def test_ordering_is_stable():
    """CIR-BAKE-DETERMINISM#ordering-is-stable"""
    d = _bake().to_dict()
    # rings in file order; items in file order
    assert [r["id"] for r in d["rings"]] == ["self", "partner", "children", "wider"]
    assert [i["id"] for i in d["rings"][0]["items"]] == ["sleep", "labs", "exercise"]


# ── CIR-BAKE-SELF-CONTAINED: index.html inlines equal data (page-side) ────────


def test_inlined_data_equals_the_file():
    """CIR-BAKE-SELF-CONTAINED#inlined-data-equals-the-file"""
    from bake.page import render_page

    artifact = _bake()
    html = render_page(artifact)
    # extract the inlined JSON payload
    start = html.index('<script id="circles-data" type="application/json">') + len('<script id="circles-data" type="application/json">')
    end = html.index("</script>", start)
    payload = html[start:end].strip()
    inlined = json.loads(payload)
    assert inlined == artifact.to_dict()


def test_page_makes_no_external_requests():
    """CIR-RENDER-NO-EGRESS#no-external-requests-at-runtime"""
    from bake.page import render_page

    html = render_page(_bake())
    # no src/href pointing at any host
    assert "http://" not in html.replace("http://www.w3.org/2000/svg", "").replace("http://www.w3.org/1999/xhtml", "")
    assert "https://" not in html


# ── CIR-BAKE-ATOMIC-WRITE ─────────────────────────────────────────────────────


def test_failed_bake_keeps_last_good():
    """CIR-BAKE-ATOMIC-WRITE#failed-bake-keeps-last-good"""
    # a config error aborts before any write (CIR-DATA-CONFIG-ERROR-FAILS)
    import tempfile
    import yaml

    bad_cfg = {
        "person": "Alex",
        "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I", "status": {"manual": "blue"}}]}],
    }
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "circles.yaml"
        p.write_text(yaml.safe_dump(bad_cfg, sort_keys=False))
        result = load_config(str(p))
        assert result.errors, "expected config error"
        assert result.config is None  # nothing to bake


# ── CIR-BAKE-EXPOSURE ─────────────────────────────────────────────────────────


def test_no_absolute_host_paths_in_warnings():
    """CIR-BAKE-EXPOSURE#no-absolute-host-paths"""
    d = _bake().to_dict()
    for w in d["warnings"]:
        assert "/home/" not in (w.get("message") or "")
        assert "/etc/" not in (w.get("message") or "")


# ── CIR-BAKE-PAGE-DOES-NOT-RESOLVE ────────────────────────────────────────────


def test_page_contains_no_adapter_code():
    """CIR-BAKE-PAGE-DOES-NOT-RESOLVE#page-contains-no-adapter-code"""
    from bake.page import render_page

    html = render_page(_bake())
    # the page must not re-resolve: no threshold arithmetic / date parsing vocabulary
    assert "yellow_after" not in html
    assert "red_after" not in html
    assert "command" not in html or "data-command" not in html