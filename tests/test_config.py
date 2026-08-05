"""Validation logic tests — CIR-DATA-SCHEMA-*, CIR-DATA-VALIDATION.

Each case cites its spec row verbatim: CIR-<AREA>-<NAME>#<row-id>
(CIR-PROC-TEST-ROWS). Rows are parametrised, not copy-pasted.
"""
from __future__ import annotations

import pytest

from bake.config import load_config

# ── helpers ───────────────────────────────────────────────────────────────────


def _load(yaml_text: str, path: str = "config.yaml"):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / path
        p.write_text(yaml_text)
        return load_config(str(p))


def _valid_cfg(**overrides):
    cfg = {
        "person": "Alex Example",
        "rings": [
            {"id": "self", "label": "① Self", "items": [{"id": "sleep", "label": "Sleep"}]},
        ],
    }
    cfg.update(overrides)
    return _load(_yaml(cfg))


def _yaml(cfg: dict) -> str:
    import yaml

    return yaml.safe_dump(cfg, sort_keys=False)


# ── CIR-DATA-SCHEMA-TOPLEVEL ──────────────────────────────────────────────────

TOPLEVEL_CASES = [
    # row id, config dict (or None for sentinel), expect_error bool
    ("minimal-valid-config", {"person": "Alex", "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I"}]}]}, False),
    ("person-missing", {"rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I"}]}]}, True),
    ("rings-empty", {"person": "Alex", "rings": []}, True),
    ("rings-order-is-inside-out", {"person": "Alex", "rings": [
        {"id": "self", "label": "① Self", "items": [{"id": "a", "label": "A"}]},
        {"id": "partner", "label": "② Partner", "items": [{"id": "b", "label": "B"}]},
        {"id": "children", "label": "③ Children", "items": [{"id": "c", "label": "C"}]},
        {"id": "wider", "label": "④ Wider life", "items": [{"id": "d", "label": "D"}]},
    ]}, False),
    ("timezone-omitted", {"person": "Alex", "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I"}]}]}, False),
    ("timezone-valid", {"person": "Alex", "timezone": "Europe/Tallinn", "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I"}]}]}, False),
]


@pytest.mark.parametrize("row_id,cfg,expect_error", TOPLEVEL_CASES, ids=[c[0] for c in TOPLEVEL_CASES])
def test_cir_data_schema_toplevel(row_id, cfg, expect_error):
    """CIR-DATA-SCHEMA-TOPLEVEL#{row_id}"""
    result = _valid_cfg(**cfg) if row_id not in ("person-missing",) else _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"
        assert result.config is not None


# ── CIR-DATA-SCHEMA-VERSION ───────────────────────────────────────────────────

VERSION_CASES = [
    ("version-absent-defaults-zero", {"person": "Alex", "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I"}]}]}, False),
    ("version-matches", {"spec_version": 0, "person": "Alex", "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I"}]}]}, False),
    ("version-from-the-future", {"spec_version": 1, "person": "Alex", "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I"}]}]}, True),
]


@pytest.mark.parametrize("row_id,cfg,expect_error", VERSION_CASES, ids=[c[0] for c in VERSION_CASES])
def test_cir_data_schema_version(row_id, cfg, expect_error):
    """CIR-DATA-SCHEMA-VERSION#{row_id}"""
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"
        assert result.config is not None


# ── CIR-DATA-SCHEMA-RING ──────────────────────────────────────────────────────

RING_CASES = [
    ("ring-id-slug", {"id": "self"}, False),
    ("ring-id-not-slug", {"id": "My Ring!"}, True),
    ("ring-id-duplicate", {"id": "self", "dup": True}, True),
    ("ring-label-missing", {"id": "self", "label": None}, True),
    ("ring-label-glyphs", {"id": "children", "label": "③ Children"}, False),
]


@pytest.mark.parametrize("row_id,ring_overrides,expect_error", RING_CASES, ids=[c[0] for c in RING_CASES])
def test_cir_data_schema_ring(row_id, ring_overrides, expect_error):
    """CIR-DATA-SCHEMA-RING#{row_id}"""
    if row_id == "ring-id-duplicate":
        cfg = {
            "person": "Alex",
            "rings": [
                {"id": "self", "label": "S", "items": [{"id": "a", "label": "A"}]},
                {"id": "self", "label": "S2", "items": [{"id": "b", "label": "B"}]},
            ],
        }
    else:
        rid = ring_overrides["id"]
        rlabel = ring_overrides.get("label", "S")
        cfg = {
            "person": "Alex",
            "rings": [{"id": rid, "label": rlabel, "items": [{"id": "a", "label": "A"}]}],
        }
        if "label" in ring_overrides and ring_overrides.get("label") is None:
            cfg["rings"][0].pop("label", None)
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"


# ── CIR-DATA-SCHEMA-ITEM ──────────────────────────────────────────────────────

ITEM_CASES = [
    ("item-minimal", {"id": "sleep", "label": "Sleep"}, False),
    ("item-id-duplicate-in-ring", {"id": "sleep", "label": "Sleep", "dup": True}, True),
    ("guardrail-absent", {"id": "sleep", "label": "Sleep"}, False),
    ("note-absent", {"id": "sleep", "label": "Sleep"}, False),
    ("share-default", {"id": "sleep", "label": "Sleep"}, False),
]


@pytest.mark.parametrize("row_id,item_overrides,expect_error", ITEM_CASES, ids=[c[0] for c in ITEM_CASES])
def test_cir_data_schema_item(row_id, item_overrides, expect_error):
    """CIR-DATA-SCHEMA-ITEM#{row_id}"""
    if row_id == "item-id-duplicate-in-ring":
        cfg = {
            "person": "Alex",
            "rings": [{
                "id": "self", "label": "S",
                "items": [
                    {"id": "sleep", "label": "Sleep"},
                    {"id": "sleep", "label": "Sleep 2"},
                ],
            }],
        }
    else:
        cfg = {
            "person": "Alex",
            "rings": [{
                "id": "self", "label": "S",
                "items": [{"id": item_overrides["id"], "label": item_overrides["label"]}],
            }],
        }
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"


# ── CIR-DATA-IDENTITY ─────────────────────────────────────────────────────────

IDENTITY_CASES = [
    ("id-character-set", {"id": "sleep"}, False),
    ("id-with-space-or-slash", {"id": "date night"}, True),
    ("id-missing", {"id": None}, True),
    ("same-id-different-rings", {"id": "sleep", "other_ring": True}, False),
    ("same-concern-two-rings", {"id": "exercise", "other_ring": True}, False),
]


@pytest.mark.parametrize("row_id,item_cfg,expect_error", IDENTITY_CASES, ids=[c[0] for c in IDENTITY_CASES])
def test_cir_data_identity(row_id, item_cfg, expect_error):
    """CIR-DATA-IDENTITY#{row_id}"""
    if item_cfg.get("other_ring"):
        cfg = {
            "person": "Alex",
            "rings": [
                {"id": "self", "label": "S", "items": [{"id": item_cfg["id"], "label": "L"}]},
                {"id": "wider", "label": "W", "items": [{"id": item_cfg["id"], "label": "L2"}]},
            ],
        }
    elif item_cfg.get("id") is None:
        cfg = {
            "person": "Alex",
            "rings": [{"id": "self", "label": "S", "items": [{"label": "Only label"}]}],
        }
    else:
        cfg = {
            "person": "Alex",
            "rings": [{"id": "self", "label": "S", "items": [{"id": item_cfg["id"], "label": "L"}]}],
        }
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"


# ── CIR-DATA-SCHEMA-ADAPTER-SLOT ──────────────────────────────────────────────

ADAPTER_SLOT_CASES = [
    ("status-absent", {}, False),
    ("status-two-adapters", {"status": {"manual": "green", "freshness": {"source": "n.md", "yellow_after": 7, "red_after": 30}}}, True),
    ("status-unknown-adapter", {"status": {"sqlite": {}}}, True),
    ("manual-invalid-word", {"status": {"manual": "blue"}}, True),
]


@pytest.mark.parametrize("row_id,item_cfg,expect_error", ADAPTER_SLOT_CASES, ids=[c[0] for c in ADAPTER_SLOT_CASES])
def test_cir_data_schema_adapter_slot(row_id, item_cfg, expect_error):
    """CIR-DATA-SCHEMA-ADAPTER-SLOT#{row_id}"""
    item = {"id": "i", "label": "I"}
    item.update(item_cfg)
    cfg = {"person": "Alex", "rings": [{"id": "s", "label": "S", "items": [item]}]}
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"


# ── CIR-DATA-SCHEMA-LINK ──────────────────────────────────────────────────────

LINK_CASES = [
    ("link-https", "https://example.test/labs", False),
    ("link-root-relative", "/details/self-sleep.html", False),
    ("link-javascript-scheme", "javascript:alert(1)", True),
    ("link-data-scheme", "data:text/html,hi", True),
    ("link-scheme-relative", "//example.test/x", True),
    ("link-bare-relative", "details/sleep.html", True),
]


@pytest.mark.parametrize("row_id,link,expect_error", LINK_CASES, ids=[c[0] for c in LINK_CASES])
def test_cir_data_schema_link(row_id, link, expect_error):
    """CIR-DATA-SCHEMA-LINK#{row_id}"""
    cfg = {
        "person": "Alex",
        "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I", "link": link}]}],
    }
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"


# ── CIR-DATA-SHARE ────────────────────────────────────────────────────────────

SHARE_CASES = [
    ("shares-equal-halves", [{"id": "nova", "label": "N", "share": 0.5}, {"id": "kit", "label": "K", "share": 0.5}], False),
    ("shares-absent-equal", [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}], False),
    ("shares-mixed", [{"id": "nova", "label": "N", "share": 2}, {"id": "kit", "label": "K"}], False),
    ("shares-mixed-fractional", [{"id": "nova", "label": "N", "share": 0.5}, {"id": "kit", "label": "K"}], False),
    ("share-zero", [{"id": "a", "label": "A", "share": 0}], True),
    ("share-negative", [{"id": "a", "label": "A", "share": -1}], True),
]


@pytest.mark.parametrize("row_id,items,expect_error", SHARE_CASES, ids=[c[0] for c in SHARE_CASES])
def test_cir_data_share(row_id, items, expect_error):
    """CIR-DATA-SHARE#{row_id}"""
    cfg = {"person": "Alex", "rings": [{"id": "s", "label": "S", "items": items}]}
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"


# ── CIR-DATA-VALIDATION ───────────────────────────────────────────────────────

VALIDATION_CASES = [
    # (row_id, config-mutator, expect_error, expect_warning_count)
    ("one-bad-item-fails-bake", lambda cfg: cfg["rings"][0]["items"].append(
        {"id": "bad", "label": "Bad", "status": {"manual": "blue"}}), True, 0),
    ("unknown-toplevel-key", lambda cfg: cfg.update({"sprinkles": True}), False, 1),
    ("unknown-item-key", lambda cfg: cfg["rings"][0]["items"][0].update({"prioritiy": "high"}), False, 1),
    ("unknown-status-key", lambda cfg: cfg["rings"][0]["items"][0].update(
        {"status": {"freshnes": {"source": "x.md", "yellow_after": 7, "red_after": 30}}}), True, 0),
    ("empty-ring", lambda cfg: cfg["rings"].append({"id": "empty", "label": "Empty", "items": []}), False, 1),
]


@pytest.mark.parametrize("row_id,mutate,expect_error,expect_warnings", VALIDATION_CASES, ids=[c[0] for c in VALIDATION_CASES])
def test_cir_data_validation(row_id, mutate, expect_error, expect_warnings):
    """CIR-DATA-VALIDATION#{row_id}"""
    cfg = {
        "person": "Alex",
        "rings": [{"id": "s", "label": "S", "items": [{"id": "a", "label": "A"}]}],
    }
    mutate(cfg)
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"
        assert len(result.warnings) == expect_warnings, (
            f"{row_id}: expected {expect_warnings} warnings, got {len(result.warnings)}"
        )


# ── CIR-DATA-SCHEMA-ADAPTER-SLOT: status empty block ──────────────────────────


def test_empty_status_block_is_config_error():
    """CIR-DATA-STATUS-RESOLUTION#empty-status-block"""
    cfg = {
        "person": "Alex",
        "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I", "status": {}}]}],
    }
    result = _load(_yaml(cfg))
    assert result.errors, "expected config error for empty status block"


# ── CIR-DATA-STATUS-MANUAL-VALUES ─────────────────────────────────────────────


@pytest.mark.parametrize("row_id,value,expect_error", [
    ("manual-lowercase-only", "Green", True),
    ("manual-grey-rejected", "grey", True),
], ids=["manual-lowercase-only", "manual-grey-rejected"])
def test_cir_data_status_manual_values(row_id, value, expect_error):
    """CIR-DATA-STATUS-MANUAL-VALUES#{row_id}"""
    cfg = {
        "person": "Alex",
        "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I", "status": {"manual": value}}]}],
    }
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors"


# ── CIR-DATA-SOURCE-PATH (validation half) ────────────────────────────────────


@pytest.mark.parametrize("row_id,source,expect_error", [
    ("source-parent-traversal", "../../etc/hosts", True),
    ("source-absolute-path", "/etc/hosts", True),
], ids=["source-parent-traversal", "source-absolute-path"])
def test_cir_data_source_path_validation(row_id, source, expect_error):
    """CIR-DATA-SOURCE-PATH#{row_id} — escaping the config dir is a config error"""
    cfg = {
        "person": "Alex",
        "rings": [{"id": "s", "label": "S", "items": [
            {"id": "i", "label": "I", "status": {"freshness": {"source": source, "yellow_after": 7, "red_after": 30}}},
        ]}],
    }
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors"


# ── CIR-DATA-FRESHNESS-THRESHOLDS (validation half) ───────────────────────────


@pytest.mark.parametrize("row_id,yellow,red,expect_error", [
    ("thresholds-valid", 100, 190, False),
    ("thresholds-equal", 7, 7, True),
    ("thresholds-inverted", 30, 7, True),
    ("threshold-zero", 0, 30, True),
    ("threshold-fractional", 3.5, 30, True),
    ("threshold-missing", None, 30, True),
], ids=["thresholds-valid", "thresholds-equal", "thresholds-inverted", "threshold-zero", "threshold-fractional", "threshold-missing"])
def test_cir_data_freshness_thresholds(row_id, yellow, red, expect_error):
    """CIR-DATA-FRESHNESS-THRESHOLDS#{row_id}"""
    status = {"source": "notes/x.md"}
    if yellow is not None:
        status["yellow_after"] = yellow
    if red is not None:
        status["red_after"] = red
    cfg = {
        "person": "Alex",
        "rings": [{"id": "s", "label": "S", "items": [{"id": "i", "label": "I", "status": {"freshness": status}}]}],
    }
    result = _load(_yaml(cfg))
    if expect_error:
        assert result.errors, f"{row_id}: expected config error"
    else:
        assert not result.errors, f"{row_id}: unexpected errors: {[e.message for e in result.errors]}"