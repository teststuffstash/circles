"""Resolution logic tests — CIR-DATA-STATUS-RESOLUTION, CIR-PROC-PHASE-P0.

Each case cites its spec row verbatim: CIR-<AREA>-<NAME>#<row-id>
(CIR-PROC-TEST-ROWS). Rows are parametrised, not copy-pasted.
"""
from __future__ import annotations

import pytest

from bake.config import load_config
from bake.resolve import GreyReason, resolve


def _resolve_yaml(yaml_text: str):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "circles.yaml"
        p.write_text(yaml_text)
        result = load_config(str(p))
        assert not result.errors, f"config errors: {[e.message for e in result.errors]}"
        assert result.config is not None
        return resolve(result.config)


def _one_item(item_dict: dict, ring_id: str = "self", ring_label: str = "① Self"):
    import yaml

    cfg = {
        "person": "Alex",
        "rings": [{"id": ring_id, "label": ring_label, "items": [item_dict]}],
    }
    res = _resolve_yaml(yaml.safe_dump(cfg, sort_keys=False))
    return res.items[0]


# ── CIR-DATA-STATUS-RESOLUTION ────────────────────────────────────────────────

RESOLUTION_CASES = [
    # (row_id, status_block, expected_status, expected_grey_reason)
    ("no-adapter-declared", None, "grey", GreyReason.BY_CHOICE),
    ("manual-green", {"manual": "green"}, "green", None),
    ("manual-yellow", {"manual": "yellow"}, "yellow", None),
    ("manual-red", {"manual": "red"}, "red", None),
    ("adapter-not-evaluated-this-phase", {"command": ["./x.sh"]}, "grey", "by-failure"),
    ("two-adapters-on-one-item", {"manual": "green", "freshness": {"source": "n.md", "yellow_after": 7, "red_after": 30}}, "error", None),
    ("empty-status-block", {}, "error", None),
    ("manual-unknown-word", {"manual": "amber"}, "error", None),
    ("manual-declares-grey", {"manual": "grey"}, "error", None),
    ("unknown-adapter-key", {"sqlite": {}}, "error", None),
]


@pytest.mark.parametrize(
    "row_id,status_block,expected_status,expected_grey_reason",
    RESOLUTION_CASES,
    ids=[c[0] for c in RESOLUTION_CASES],
)
def test_cir_data_status_resolution(row_id, status_block, expected_status, expected_grey_reason):
    """CIR-DATA-STATUS-RESOLUTION#{row_id}"""
    import yaml

    item = {"id": "i", "label": "I"}
    if status_block is not None:
        item["status"] = status_block
    cfg = {"person": "Alex", "rings": [{"id": "s", "label": "S", "items": [item]}]}

    if expected_status == "error":
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "circles.yaml"
            p.write_text(yaml.safe_dump(cfg, sort_keys=False))
            result = load_config(str(p))
            assert result.errors, f"{row_id}: expected config error"
        return

    resolved = _one_item(item)
    assert resolved.status == expected_status, (
        f"{row_id}: expected {expected_status}, got {resolved.status}"
    )
    assert resolved.grey_reason == expected_grey_reason, (
        f"{row_id}: expected grey_reason {expected_grey_reason}, got {resolved.grey_reason}"
    )


# ── CIR-DATA-GREY-REASON ──────────────────────────────────────────────────────


def test_unmonitored_by_failure_detail_line_names_failure():
    """CIR-DATA-GREY-REASON#unmonitored-by-failure"""
    item = _one_item({"id": "plants", "label": "Plants", "status": {"command": ["./x.sh"]}})
    assert item.status == "grey"
    assert item.grey_reason == "by-failure"
    assert "not evaluated in this build" in item.detail_line


def test_unmonitored_by_choice_detail_line():
    """CIR-DATA-GREY-REASON#unmonitored-by-choice"""
    item = _one_item({"id": "exercise", "label": "Exercise"})
    assert item.status == "grey"
    assert item.grey_reason == "by-choice"
    assert item.detail_line == "not monitored"


# ── CIR-DATA-STATUS-MANUAL-VALUES ─────────────────────────────────────────────


@pytest.mark.parametrize("word,expected", [
    ("green", "green"),
    ("yellow", "yellow"),
    ("red", "red"),
], ids=["green", "yellow", "red"])
def test_manual_word_to_status(word, expected):
    """CIR-ADAPT-MANUAL#manual-returns-declared-light"""
    item = _one_item({"id": "i", "label": "I", "status": {"manual": word}})
    assert item.status == expected


# ── CIR-PROC-PHASE-P0 ─────────────────────────────────────────────────────────


def test_p0_unevaluated_adapters_are_grey():
    """CIR-PROC-PHASE-P0#p0-unevaluated-adapters-are-grey"""
    import yaml

    cfg = {
        "person": "Alex",
        "rings": [{
            "id": "self", "label": "① Self",
            "items": [
                {"id": "sleep", "label": "Sleep", "status": {"freshness": {"source": "notes/sleep-log.md", "yellow_after": 7, "red_after": 30}}},
                {"id": "labs", "label": "Labs", "status": {"freshness": {"source": "notes/labs.md", "yellow_after": 100, "red_after": 190}}},
                {"id": "exercise", "label": "Exercise"},
            ],
        }],
    }
    res = _resolve_yaml(yaml.safe_dump(cfg, sort_keys=False))
    by_id = {i.id: i for i in res.items}
    assert by_id["sleep"].status == "grey"
    assert by_id["sleep"].grey_reason == "by-failure"
    assert by_id["labs"].status == "grey"
    assert by_id["exercise"].status == "grey"
    assert by_id["exercise"].grey_reason == "by-choice"
    # every freshness item carries a build warning
    warn_refs = {w.item_ref for w in res.warnings}
    assert "self/sleep" in warn_refs
    assert "self/labs" in warn_refs


def test_p0_manual_end_to_end():
    """CIR-PROC-PHASE-P0#p0-manual-end-to-end"""
    import yaml

    cfg = {
        "person": "Alex",
        "rings": [{
            "id": "partner", "label": "② Partner",
            "items": [{"id": "date-night", "label": "Date night", "status": {"manual": "yellow"}}],
        }],
    }
    res = _resolve_yaml(yaml.safe_dump(cfg, sort_keys=False))
    assert res.items[0].status == "yellow"


# ── CIR-DATA-DETAIL-LINE ──────────────────────────────────────────────────────


def test_manual_item_has_no_data_date():
    """CIR-DATA-DETAIL-LINE#manual-item-has-no-data-date"""
    item = _one_item({"id": "i", "label": "I", "status": {"manual": "green"}})
    assert "last data" not in item.detail_line
    assert item.last_data_date is None


def test_full_detail_line_guardrail_first():
    """CIR-DATA-DETAIL-LINE#full-detail-line"""
    item = _one_item({
        "id": "sleep", "label": "Sleep",
        "guardrail": "Lights out by 23:00 on weeknights",
        "status": {"manual": "green"},
    })
    assert item.detail_line.startswith("Lights out by 23:00 on weeknights")
    assert "ok" in item.detail_line


def test_no_guardrail_no_empty_separator():
    """CIR-DATA-DETAIL-LINE#no-guardrail"""
    item = _one_item({"id": "i", "label": "I", "status": {"manual": "red"}})
    assert item.detail_line == "act"


# ── CIR-DATA-NO-AGGREGATION ───────────────────────────────────────────────────


def test_inner_red_outer_untouched():
    """CIR-DATA-NO-AGGREGATION#inner-red-outer-untouched"""
    import yaml

    cfg = {
        "person": "Alex",
        "rings": [
            {"id": "self", "label": "① Self", "items": [{"id": "sleep", "label": "S", "status": {"manual": "red"}}]},
            {"id": "partner", "label": "② Partner", "items": [{"id": "date-night", "label": "D", "status": {"manual": "yellow"}}]},
        ],
    }
    res = _resolve_yaml(yaml.safe_dump(cfg, sort_keys=False))
    by_id = {(i.ring_id, i.id): i for i in res.items}
    assert by_id[("self", "sleep")].status == "red"
    assert by_id[("partner", "date-night")].status == "yellow"


# ── CIR-ADAPT-CONTRACT ────────────────────────────────────────────────────────


def test_adapter_failure_is_isolated():
    """CIR-ADAPT-CONTRACT#adapter-failure-is-isolated"""
    import yaml

    cfg = {
        "person": "Alex",
        "rings": [{
            "id": "self", "label": "① Self",
            "items": [
                {"id": "a", "label": "A", "status": {"manual": "green"}},
                {"id": "b", "label": "B", "status": {"command": ["./missing.sh"]}},
                {"id": "c", "label": "C", "status": {"manual": "red"}},
            ],
        }],
    }
    res = _resolve_yaml(yaml.safe_dump(cfg, sort_keys=False))
    by_id = {i.id: i for i in res.items}
    assert by_id["a"].status == "green"
    assert by_id["b"].status == "grey"  # not-evaluated at P0
    assert by_id["c"].status == "red"


def test_adapter_cannot_return_grey():
    """CIR-ADAPT-CONTRACT#adapter-cannot-return-grey"""
    # manual: grey is rejected at validation (CIR-DATA-STATUS-MANUAL-VALUES)
    import yaml
    import tempfile
    from pathlib import Path

    cfg = {
        "person": "Alex",
        "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I", "status": {"manual": "grey"}}]}],
    }
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "circles.yaml"
        p.write_text(yaml.safe_dump(cfg, sort_keys=False))
        result = load_config(str(p))
        assert result.errors, "manual: grey must be a config error — grey is not a manual value"