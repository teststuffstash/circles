# Tests for scripts/lib/lint_specs.py — the evidence join (check 3).
#
# check_evidence_join's third check diffs a <details class="evidence-block"> block's own
# case-id rows against the corresponding evidence-manifest.json entry, so a stale or
# hand-edited block is caught mechanically instead of only by review (issue #46).
#
# The check itself cites CIR-PROC-GATE#gate-no-dangling-spec-reference; no decision-table
# row names this exact drift, so these tests cite the same row the check does.

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_LIB = Path(__file__).resolve().parent.parent / "scripts" / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import lint_specs  # noqa: E402

REQ = "CIR-PROC-GATE"
MISMATCH = "evidence block case ids don't match manifest"


def _write_repo(root: Path, block_ids: list[str], manifest_ids: list[str]) -> None:
    """A one-page spec tree whose decision table knows rows `a` and `b`, plus an evidence
    block citing `block_ids` and a manifest entry citing `manifest_ids`."""
    specs = root / "specs"
    specs.mkdir()
    rows = "\n".join(f"| `{cid}` | PASS | — |" for cid in block_ids)
    (specs / "page.md").write_text(
        f"## {REQ} — a requirement\n\n"
        "| row id | inputs | expected |\n|---|---|---|\n| a | x | y |\n| b | x | y |\n\n"
        '<details class="evidence-block">\n<summary>Evidence</summary>\n\n'
        f"| Case ID | Status | Detail |\n|---|---|---|\n{rows}\n\n</details>\n",
        encoding="utf-8",
    )
    (specs / "evidence-manifest.json").write_text(
        json.dumps({"requirements": {REQ: manifest_ids}}), encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("block_ids", "manifest_ids", "expected"),
    [
        (["a", "b"], ["a"], "extra case ids in block: ['b']"),
        (["a"], ["a", "b"], "missing case ids from block: ['b']"),
        (["a", "b"], ["a", "b"], None),
    ],
    ids=["block-has-extra-id", "block-lacks-manifest-id", "block-matches-manifest"],
)
def test_evidence_block_diffed_against_manifest(
    tmp_path: Path, block_ids: list[str], manifest_ids: list[str], expected: str | None
) -> None:
    """CIR-PROC-GATE#gate-no-dangling-spec-reference — an evidence block whose case ids
    diverge from its manifest entry, in either direction, fails the spec gate."""
    _write_repo(tmp_path, block_ids, manifest_ids)
    findings = lint_specs.Findings()

    lint_specs.check_evidence_join(tmp_path, findings)

    if expected is None:
        assert findings.errors == []
    else:
        assert len(findings.errors) == 1
        assert MISMATCH in findings.errors[0]
        assert expected in findings.errors[0]
