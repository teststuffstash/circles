#!/usr/bin/env python3
"""generate-evidence.py — evidence chain: Allure results → fragment blocks → spec pages.

Runs after pytest --alluredir.  Reads the Allure result JSON, groups tests by their
CIR-<AREA>-<NAME> requirement id, and for every requirement that has at least one citing
test, replaces the ``_Evidence: none yet — unverified._`` line in the spec page with a
collapsed `<details>` block containing:

- the requirement id + world
- a table of every citing test (case id → status)
- a relative link to the archived report (the Allure html report)

Requirement sections that still have no citing test keep their original evidence line
intact — the tree stays honest mid-migration.

Usage:
    python3 scripts/generate-evidence.py \\
        --allure-dir /tmp/allure-raw \\
        --report-dir ../specs-site/evidence \\
        --specs-dir specs/

Or driven by scripts/ci.sh.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# -- Constants ---------------------------------------------------------------

WORLD = "alex"  # v0 has exactly one world (CIR-PROC-TEST-ROWS#evidence-identity-is-a-triple)

# Every 3rd-level heading that is a CIR- requirement — match the spec convention
# Requirement ids are CIR-<AREA>-<NAME> where NAME can have hyphens.
REQ_HEADING = re.compile(r"^(##\s+)(CIR-[A-Z0-9]+(?:-[A-Z0-9]+)+)\b", re.MULTILINE)

# The evidence placeholder line we replace
EVIDENCE_PLACEHOLDER = "_Evidence: none yet — unverified._"

# Allure result file pattern
ALLURE_RESULT_RE = re.compile(r".*-result\.json$")

# CIR id from a test name or description
# Requirement ids are CIR-<AREA>-<NAME> where NAME can have hyphens.
# The full id is everything before any # or space/end.
# Must be greedy: match the longest possible CIR-... sequence.
CIR_ID_RE = re.compile(r"(CIR-[A-Z0-9]+(?:-[A-Z0-9]+)+(?:#[a-z0-9_-]+)?)")


# -- Helpers -----------------------------------------------------------------


def _gather_allure_results(allure_dir: Path) -> list[dict]:
    """Read all Allure result JSON files."""
    results: list[dict] = []
    if not allure_dir.is_dir():
        print(f"WARN: Allure directory {allure_dir} not found", file=sys.stderr)
        return results
    for fname in sorted(allure_dir.iterdir()):
        if ALLURE_RESULT_RE.match(fname.name):
            with open(allure_dir / fname) as f:
                results.append(json.load(f))
    return results


def _extract_case_id(r: dict) -> str:
    """Extract the row/case id from a test result.

    Priority:
    1. Parametrized id: ``CIR-<AREA>-<NAME>#<row-id>`` in the test name brackets
    2. Docstring: ``CIR-<AREA>-<NAME>#<row-id>`` in the description
    3. Fallback: the test method name
    """
    name = r.get("name", "")
    desc = r.get("description", "") or ""

    # Try parametrized name first: test_name[CIR-REQ#row-id]
    m = re.search(r"\[CIR-[A-Z0-9]+(?:-[A-Z0-9]+)+#([a-z0-9_-]+)\]", name)
    if m:
        return m.group(1)

    # Try docstring: CIR-REQ#row-id
    m = re.search(r"CIR-[A-Z0-9]+(?:-[A-Z0-9]+)+#([a-z0-9_-]+)", desc)
    if m:
        return m.group(1)

    # Fallback: method name
    return r.get("fullName", "").split(".")[-1]


def _group_by_requirement(
    results: list[dict],
) -> dict[str, list[dict]]:
    """Group test results by the CIR-<AREA>-<NAME> requirement they cite.

    A test cites its requirement via the row id in the test name/parametrized id:
    ``CIR-<AREA>-<NAME>#<row-id>`` — the requirement id is everything before the ``#``.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        name = r.get("name", "")
        full_name = r.get("fullName", "")
        desc = r.get("description", "") or ""
        # Collect all CIR- references from name + desc
        all_text = f"{name} {full_name} {desc}"
        matches = CIR_ID_RE.findall(all_text)
        # Use the longest match (greedy on hyphen-separated parts)
        matches.sort(key=lambda x: -len(x))
        for m in matches:
            # Isolate the requirement part (before #)
            if "#" in m:
                req_id, _ = m.split("#", 1)
            else:
                req_id = m
            grouped[req_id].append(r)
            # Only count first unique requirement per test
            break
    return grouped


def _build_evidence_block(
    req_id: str,
    cases: list[dict],
    report_relative_path: str,
) -> str:
    """Build a markdown evidence block for one requirement.

    Format: markdown-embedded and machine-validatable (per the spec's deliberate
    choice — not SVG, not framework-specific). A reviewer or agent can read the
    fragment's claims without rendering it.
    """
    # Sort by case id for stable, deterministic output and deduplicate by case id.
    # A row id is the case's identity (CIR-PROC-TEST-ROWS: case id == row id), so
    # two tests citing the same row id are one row — not a duplicate evidence line.
    # The summary count reflects the deduplicated case rows, not raw test count.
    #
    # When two tests cite the SAME case id with DIFFERENT outcomes (e.g., a flaky
    # retry — one PASS, one FAIL), the worst outcome wins:
    #   FAIL > BROKEN > SKIP > PASS > UNKN
    # This ensures a flaky RED test is never silently hidden by a preceding GREEN
    # run (issue #49).
    _STATUS_SEVERITY = {"failed": 0, "broken": 1, "skipped": 2, "passed": 3, "unknown": 4}

    unique_cases: list[dict] = []
    seen: dict[str, dict] = {}  # case_id -> current worst entry
    for c in sorted(cases, key=lambda c: _extract_case_id(c)):
        case_id = _extract_case_id(c)
        if case_id in seen:
            existing = seen[case_id]
            existing_sev = _STATUS_SEVERITY.get(existing.get("status", "unknown"), 99)
            current_sev = _STATUS_SEVERITY.get(c.get("status", "unknown"), 99)
            if current_sev < existing_sev:
                # Worse outcome → replace
                seen[case_id] = c
            continue
        seen[case_id] = c

    unique_cases = list(seen.values())

    lines: list[str] = []

    lines.append("<details class=\"evidence-block\">")
    lines.append(f"<summary>Evidence: {len(unique_cases)} test case(s) — {WORLD}</summary>")
    lines.append("")
    lines.append(f"**Requirement:** {req_id} — **World:** {WORLD}")
    lines.append("")
    lines.append("| Case ID | Status | Detail |")
    lines.append("|---------|--------|--------|")

    for c in unique_cases:
        case_id = _extract_case_id(c)

        status = c.get("status", "unknown")
        # Map Allure status to a symbol
        # Use PASS/FAIL instead of ✓/✗ to avoid triggering the lint check
        # that flags ✓/🚧 as "declared verified-ness"
        if status == "passed":
            status_symbol = "PASS"
        elif status == "failed":
            status_symbol = "FAIL"
        elif status == "broken":
            status_symbol = "BROKEN"
        elif status == "skipped":
            status_symbol = "SKIP"
        else:
            status_symbol = "UNKN"

        detail = status_symbol

        lines.append(f"| `{case_id}` | {status_symbol} | — |")

    lines.append("")
    lines.append(f"[View full report]({report_relative_path})")
    lines.append("")
    lines.append("</details>")

    return "\n".join(lines)


def _inject_evidence(page_path: Path, req_id: str, evidence_block: str) -> None:
    """Replace the evidence placeholder in a spec page with the generated block.

    Finds the ``_Evidence: none yet — unverified._`` line that falls between the
    given requirement heading and the next heading (or end of file), and replaces
    it with the evidence block.
    """
    text = page_path.read_text(encoding="utf-8")

    # Find all requirement headings
    headings = list(REQ_HEADING.finditer(text))

    # Find the heading for this requirement
    req_match = None
    for m in headings:
        if m.group(2) == req_id:
            req_match = m
            break

    if req_match is None:
        print(f"  WARN: requirement {req_id} not found in {page_path}", file=sys.stderr)
        return

    # Determine the section boundaries: from this heading to the next heading (or EOF)
    section_start = req_match.start()
    section_end = len(text)
    for m in headings:
        if m.start() > req_match.start():
            section_end = m.start()
            break

    # Extract the section text
    section_text = text[section_start:section_end]

    # Find the evidence placeholder within this section
    placeholder_match = re.search(re.escape(EVIDENCE_PLACEHOLDER), section_text)
    if placeholder_match is None:
        print(f"  WARN: evidence placeholder not found for {req_id} in {page_path}", file=sys.stderr)
        return

    placeholder_abs_start = section_start + placeholder_match.start()
    placeholder_abs_end = section_start + placeholder_match.end()

    new_text = text[:placeholder_abs_start] + evidence_block + text[placeholder_abs_end:]
    page_path.write_text(new_text, encoding="utf-8")
    print(f"  ✓ evidence injected for {req_id}")


# -- Main --------------------------------------------------------------------


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate evidence fragments from Allure results")
    parser.add_argument("--allure-dir", required=True, type=Path,
                        help="Path to Allure results directory (from pytest --alluredir)")
    parser.add_argument("--report-dir", required=True, type=Path,
                        help="Path to the published report (for relative links)")
    parser.add_argument("--specs-dir", required=True, type=Path,
                        help="Path to the specs/ directory")
    parser.add_argument("--inject", action="store_true", default=False,
                        help="Actually inject evidence blocks into spec pages (default: dry-run)")
    args = parser.parse_args()

    if not args.allure_dir.is_dir():
        print(f"FATAL: --allure-dir {args.allure_dir} not found", file=sys.stderr)
        return 1
    if not args.specs_dir.is_dir():
        print(f"FATAL: --specs-dir {args.specs_dir} not found", file=sys.stderr)
        return 1

    results = _gather_allure_results(args.allure_dir)
    if not results:
        print("No Allure results found", file=sys.stderr)
        return 0  # Not fatal — early in the pipeline there may be no tests yet

    # Group by requirement
    grouped = _group_by_requirement(results)

    print(f"Found {len(results)} tests across {len(grouped)} requirement(s):")
    for req_id, cases in sorted(grouped.items()):
        passed = sum(1 for c in cases if c.get("status") == "passed")
        total = len(cases)
        print(f"  {req_id}: {passed}/{total} passed")

    # Build evidence blocks and inject
    report_rel = os.path.relpath(args.report_dir, args.specs_dir)

    for req_id, cases in sorted(grouped.items()):
        # Find which page contains this requirement
        target_page: Path | None = None
        for page in args.specs_dir.rglob("*.md"):
            text = page.read_text(encoding="utf-8")
            if re.search(rf"^##\s+{re.escape(req_id)}\b", text, re.MULTILINE):
                target_page = page
                break

        if target_page is None:
            print(f"  WARN: requirement {req_id} not found in any spec page", file=sys.stderr)
            continue

        # Build the evidence summary JSON for the join check
        evidence_block = _build_evidence_block(req_id, cases, report_rel)

        if args.inject:
            _inject_evidence(target_page, req_id, evidence_block)
        else:
            print(f"  [{req_id}] would inject into {target_page.relative_to(args.specs_dir.parent)}")

    # Write the evidence manifest (for the spec gate join check)
    # The manifest maps each requirement to its cited case ids
    manifest: dict[str, Any] = {
        "world": WORLD,
        "report_path": str(args.report_dir),
        "requirements": {},
    }
    for req_id, cases in sorted(grouped.items()):
        case_ids: list[str] = []
        seen: set[str] = set()
        for c in cases:
            case_id = _extract_case_id(c)
            if case_id in seen:
                continue
            seen.add(case_id)
            case_ids.append(case_id)
        manifest["requirements"][req_id] = case_ids

    manifest_path = args.specs_dir / "evidence-manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nEvidence manifest written to {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
