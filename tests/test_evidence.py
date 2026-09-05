# Tests for scripts/generate-evidence.py — evidence dedup logic
#
# Every decision-table row from fixtures/evidence-dedup.yaml is parametrised
# per CIR-PROC-TEST-ROWS#rows-parametrised-not-copied.
#
# These tests exercise _extract_case_id and _build_evidence_block directly.

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# We import the private functions via importlib since the module file has a hyphen
# in its name (generate-evidence.py), which prevents a regular `import` statement.
import importlib.util
import sys

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location(
    "generate_evidence",
    str(_SCRIPTS / "generate-evidence.py"),
)
_EV = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_EV)  # type: ignore[union-attr]
_extract_case_id = _EV._extract_case_id
_build_evidence_block = _EV._build_evidence_block

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
DEDUP_YAML = FIXTURES / "evidence-dedup.yaml"


def _load_rows() -> list[dict[str, Any]]:
    """Load fixture rows from evidence-dedup.yaml."""
    with open(DEDUP_YAML) as f:
        data = yaml.safe_load(f)
    return data["rows"]


# Tests
# =====


class TestEvidenceDedup:
    """CIR-... evidence dedup: _build_evidence_block handles same-case-id collisions."""

    @pytest.mark.parametrize("row", _load_rows(), ids=lambda r: r["description"])
    def test_dedup(self, row: dict[str, Any]) -> None:
        """_build_evidence_block dedup aggregates status correctly.

        When two Allure results cite the same case id, the block should
        show the worst outcome (FAIL > BROKEN > SKIP > PASS). Distinct
        case ids are all shown.

        When a case has no #<row-id> citation, _extract_case_id must
        hard-fail (ValueError) rather than silently falling back to the
        method name.
        """
        cases: list[dict] = row["cases"]

        if row.get("expect_error"):
            # Row signals that _extract_case_id should hard-fail
            with pytest.raises(ValueError, match=r"#<row-id>"):
                _build_evidence_block("CIR-DATA-FRESHNESS-WINDOW", cases, "../report/")
            return

        expected: dict[str, str] = row["expected"]

        # Build the block with a dummy report path
        block = _build_evidence_block("CIR-DATA-FRESHNESS-WINDOW", cases, "../report/")

        # Extract status symbols from the generated table rows
        # The table rows look like: | `window-inside` | FAIL | — |
        import re
        statuses: dict[str, str] = {}
        for m in re.finditer(r"\|\s*`([^`]+)`\s*\|\s*([A-Z]+)\s*\|", block):
            statuses[m.group(1)] = m.group(2)

        assert statuses == expected, (
            f"Mismatch for cases={cases}\n"
            f"Expected: {expected}\n"
            f"Got: {statuses}\n"
            f"Block:\n{block}"
        )

    def test_count_reflects_dedup(self) -> None:
        """The <summary> count shows deduplicated case count, not raw test count.

        3 tests, 2 distinct case ids → count should be 2.
        """
        cases = [
            {"name": "[CIR-FOO-BAR#case-a]", "fullName": "test.test_case_a", "status": "passed"},
            {"name": "[CIR-FOO-BAR#case-a]", "fullName": "test.test_case_a_retry", "status": "passed"},
            {"name": "[CIR-FOO-BAR#case-b]", "fullName": "test.test_case_b", "status": "passed"},
        ]
        block = _build_evidence_block("CIR-FOO-BAR", cases, "../report/")
        assert "2 test case(s)" in block, (
            f"Expected count 2 in summary, got block:\n{block}"
        )
