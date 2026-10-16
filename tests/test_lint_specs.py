# Tests for the evidence half of the spec gate (scripts/lib/lint_specs.py) and the rule() label
# (tests/rules.py) — the correspondence between spec headings, evidence slots and test labels
# that the portable process needs (allure-behavior-snippets CONVENTIONS § The lint gate,
# homelab ADR-156; circles#103).
#
# Every case builds a one-page spec tree in tmp_path and drives the real check through its seam;
# expected findings are derived from the rows cited (specs/process/testing.md).

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

_LIB = Path(__file__).resolve().parent.parent / "scripts" / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import lint_specs  # noqa: E402

from rules import case_title, rule  # noqa: E402

REQ = "CIR-PROC-GATE"
POINTER = f'<details markdown="1"><summary>Evidence — latest run</summary>\n\n--8<-- "{REQ}.md"\n\n</details>'
MARKER = "_Evidence: none yet — unverified._"


def _page(root: Path, heading: str, slot: str) -> Path:
    """A one-requirement page: ``heading``, a one-row decision table, then ``slot``."""
    specs = root / "specs"
    specs.mkdir(exist_ok=True)
    page = specs / "page.md"
    page.write_text(
        f"# A page\n\n**World: alex**\n\n{heading}\n\n**— a requirement**\n\n"
        "| row id | inputs | expected |\n|---|---|---|\n| a | x | y |\n\n"
        f"{slot}\n",
        encoding="utf-8",
    )
    return page


def _lint_page(root: Path, page: Path, labelled: set[str] | None) -> list[str]:
    findings = lint_specs.Findings()
    lint_specs.check_page(page, root, findings, {}, labelled)
    return findings.errors


@rule("CIR-PROC-SPEC-GATE")
@pytest.mark.parametrize(
    ("slot", "labelled", "expected"),
    [
        pytest.param(POINTER, {REQ}, None, id="pointer, labelled test exists"),
        pytest.param(MARKER, set(), None, id="marker, no labelled test"),
        pytest.param(f"{POINTER}\n\n{MARKER}", {REQ}, "both an evidence pointer and the unverified marker",
                     id="pointer and marker both"),
        pytest.param("", set(), "no evidence slot", id="neither pointer nor marker"),
        pytest.param(POINTER.replace(f'"{REQ}.md"', '"CIR-PROC-GATE-OTHER.md"'), {REQ},
                     'evidence pointer names "CIR-PROC-GATE-OTHER.md"', id="pointer to another rule's fragment"),
        pytest.param(POINTER, set(), "evidence pointer but no test carries", id="pointer, no labelled test"),
        pytest.param(MARKER, {REQ}, "but the page says", id="marker despite a labelled test"),
    ],
)
def test_evidence_slot_pointer_xor_marker(
    tmp_path: Path, slot: str, labelled: set[str], expected: str | None
) -> None:
    """CIR-PROC-SPEC-GATE#spec-evidence-line-present — a rule heading carries its own pointer
    XOR the marker, and the pointer exactly when a test labels the rule."""
    errors = _lint_page(tmp_path, _page(tmp_path, f"## {REQ}", slot), labelled)

    if expected is None:
        assert errors == []
    else:
        assert len(errors) == 1, errors
        assert expected in errors[0]


@rule("CIR-PROC-SPEC-GATE")
def test_decorated_heading_fails(tmp_path: Path) -> None:
    """CIR-PROC-SPEC-GATE#spec-heading-is-the-id — `## CIR-PROC-GATE — a decoration` fails;
    the decoration belongs on the line below the bare-id heading."""
    errors = _lint_page(tmp_path, _page(tmp_path, f"## {REQ} — a decoration", MARKER), set())

    assert len(errors) == 1, errors
    assert "rule heading is decorated" in errors[0]


@rule("CIR-PROC-SPEC-GATE")
@pytest.mark.parametrize(
    ("source", "expected_errors"),
    [
        pytest.param('@rule("X")\n@pytest.mark.parametrize("v", [1, 2])\ndef test_a(v): ...\n', 1,
                     id="labelled, auto ids"),
        pytest.param('@rule("X")\n@pytest.mark.parametrize("v", [pytest.param(1, id="one"), 2])\n'
                     "def test_a(v): ...\n", 1, id="labelled, one row without id"),
        pytest.param('@rule("X")\n@pytest.mark.parametrize("v", [1, 2], ids=["one", "two"])\n'
                     "def test_a(v): ...\n", 0, id="labelled, ids= given"),
        pytest.param('@rule("X")\n@pytest.mark.parametrize("v", [pytest.param(1, id="one")])\n'
                     "def test_a(v): ...\n", 0, id="labelled, every row pytest.param(id=)"),
        pytest.param('@pytest.mark.parametrize("v", [1, 2])\ndef test_a(v): ...\n', 0,
                     id="unlabelled, auto ids allowed"),
    ],
)
def test_labelled_parametrization_has_explicit_ids(
    tmp_path: Path, source: str, expected_errors: int
) -> None:
    """CIR-PROC-SPEC-GATE#spec-labelled-params-have-ids — a rule-labelled parametrized test
    with any auto-generated id fails; an unlabelled one is not the gate's business."""
    path = tmp_path / "test_x.py"
    path.write_text(source, encoding="utf-8")
    findings = lint_specs.Findings()

    lint_specs.check_param_ids(path, findings)

    assert len(findings.errors) == expected_errors, findings.errors
    for error in findings.errors:
        assert "no explicit ids" in error


@rule("CIR-PROC-GATE")
def test_label_naming_no_heading_fails_the_lint(tmp_path: Path) -> None:
    """CIR-PROC-GATE#gate-no-dangling-spec-reference — a `rule("CIR-…")` label in tests/
    naming no spec heading fails the gate, without running pytest."""
    _page(tmp_path, f"## {REQ}", MARKER)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_x.py").write_text(
        f'@rule("{REQ}")\ndef test_ok(): ...\n\n@rule("CIR-PROC-NOPE")\ndef test_ghost(): ...\n',
        encoding="utf-8",
    )
    findings = lint_specs.Findings()

    lint_specs.check_labels(lint_specs.rule_labels(tmp_path), {REQ: tmp_path / "specs" / "page.md"}, findings)

    assert len(findings.errors) == 1, findings.errors
    assert "CIR-PROC-NOPE" in findings.errors[0]


@rule("CIR-PROC-GATE")
def test_rule_unknown_id_fails(tmp_path: Path) -> None:
    """CIR-PROC-GATE#gate-no-dangling-spec-reference — `rule("CIR-PROC-NOPE")` raises (a
    collection error for the module using it), naming the ID; a known ID yields its labels."""
    _page(tmp_path, f"## {REQ}", MARKER)
    specs = tmp_path / "specs"

    with pytest.raises(ValueError, match="CIR-PROC-NOPE"):
        rule("CIR-PROC-NOPE", specs=specs)

    marks = rule(REQ, specs=specs)
    labels = {(m.kwargs.get("label_type"), m.args[0]) for m in marks if m.name == "allure_label"}
    # story == the ID; epic == the page path under specs/ without suffix; feature == the
    # section the rule sits under (the page title); world == the one v0 world.
    assert ("story", REQ) in labels
    assert ("epic", "page") in labels
    assert ("feature", "A page") in labels
    assert ("world", "alex") in labels


@pytest.mark.parametrize(
    ("param_id", "docstring", "expected"),
    [
        pytest.param("CIR-PROC-GATE#gate-a", "CIR-PROC-GATE#gate-b — x", "gate-a", id="param id wins"),
        pytest.param(None, "CIR-PROC-GATE#gate-b — x", "gate-b", id="docstring first paragraph"),
        pytest.param("fresh", textwrap.dedent("""\
            CIR-OTHER-RULE#x — first, then CIR-PROC-GATE#gate-c.

            CIR-PROC-GATE#gate-d is a later paragraph."""), "gate-c", id="own rule's first citation"),
        pytest.param(None, "Prose.\n\nCIR-PROC-GATE#gate-d", None, id="no citation in first paragraph"),
    ],
)
def test_case_title_is_the_cited_row(param_id: str | None, docstring: str, expected: str | None) -> None:
    """The Allure title a labelled case gets is the row id it cites — the evidence join key."""
    assert case_title(REQ, param_id, docstring) == expected


# --- the schema half: requirement ⇄ schema coupling (RULES.md rule 7) -----------------------

A, B = "CIR-PROC-SCHEMA-A", "CIR-PROC-SCHEMA-B"


def _contract_tree(root: Path, schema: dict | None, *, sibling_of: str = "page") -> Path:
    """specs/c/page.md with rules A and B; ``schema`` (if given) written as
    specs/c/<sibling_of>.schema.json. Returns the specs root."""
    import json

    specs = root / "specs"
    (specs / "c").mkdir(parents=True)
    body = "".join(f"## {rid}\n\n**— a rule**\n\n{MARKER}\n\n" for rid in (A, B))
    (specs / "c" / "page.md").write_text(f"# A contract page\n\n{body}", encoding="utf-8")
    if schema is not None:
        (specs / "c" / f"{sibling_of}.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    return specs


def _lint_schemas(specs: Path) -> list[str]:
    findings = lint_specs.Findings()
    seen: dict[str, Path] = {}
    lint_specs.check_page(specs / "c" / "page.md", specs.parent, findings, seen, None)
    assert findings.errors == []  # the page itself is clean; only the coupling is under test
    lint_specs.check_schemas(specs, seen, findings, contract_pages=("c/page.md",))
    return findings.errors


# A annotated deep inside the schema (the gate walks every node), B declared not schema-shaped.
COUPLED = {"x-not-schema-shaped": {B: "a behaviour, not a shape"},
           "properties": {"x": {"x-requirements": [A]}}}


@rule("CIR-PROC-SPEC-GATE")
@pytest.mark.parametrize(
    ("schema", "sibling_of", "expected"),
    [
        pytest.param(COUPLED, "page", None, id="every rule annotated or declared not schema-shaped"),
        pytest.param(None, "page", "has no sibling page.schema.json",
                     id="contract page without its schema"),
        pytest.param(COUPLED, "other", "not the sibling of a declared contract page",
                     id="schema beside an undeclared page"),
    ],
)
def test_contract_page_has_schema(
    tmp_path: Path, schema: dict | None, sibling_of: str, expected: str | None
) -> None:
    """CIR-PROC-SPEC-GATE#spec-contract-page-has-schema — a declared contract page has its
    sibling schema; a schema beside an undeclared page is an error. (The undeclared-page case
    also leaves the declared page sibling-less: two findings.)"""
    errors = _lint_schemas(_contract_tree(tmp_path, schema, sibling_of=sibling_of))

    if expected is None:
        assert errors == []
    else:
        assert any(expected in e for e in errors), errors


@rule("CIR-PROC-SPEC-GATE")
@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        pytest.param({"x-requirements": [A, "CIR-NOPE"], "x-not-schema-shaped": {B: "why"}},
                     "x-requirements names 'CIR-NOPE'", id="x-requirements names no heading"),
        pytest.param({"x-requirements": [A], "x-not-schema-shaped": {B: "why", "CIR-NOPE": "why"}},
                     "x-not-schema-shaped lists 'CIR-NOPE'", id="not-schema-shaped names no rule on the page"),
        pytest.param({"x-requirements": "CIR-PROC-SCHEMA-A", "x-not-schema-shaped": {B: "why"}},
                     "x-requirements must be a list", id="x-requirements not a list"),
    ],
)
def test_schema_annotations_resolve(tmp_path: Path, schema: dict, expected: str) -> None:
    """CIR-PROC-SPEC-GATE#spec-schema-annotations-resolve — an annotation naming no rule
    heading fails the gate (the orphan in the schema → spec direction)."""
    errors = _lint_schemas(_contract_tree(tmp_path, schema))

    assert any(expected in e for e in errors), errors


@rule("CIR-PROC-SPEC-GATE")
@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        pytest.param({"x-requirements": [A]}, f"{B} is on a contract page but neither annotated",
                     id="rule neither annotated nor declared not schema-shaped"),
        pytest.param({"x-requirements": [A, B], "x-not-schema-shaped": {B: "why"}},
                     f"{B} is both annotated", id="rule both annotated and not schema-shaped"),
    ],
)
def test_contract_rules_coupled(tmp_path: Path, schema: dict, expected: str) -> None:
    """CIR-PROC-SPEC-GATE#spec-contract-rules-coupled — every rule on a contract page is
    either in the schema's x-requirements or in its x-not-schema-shaped map, exactly one."""
    errors = _lint_schemas(_contract_tree(tmp_path, schema))

    assert len(errors) == 1, errors
    assert expected in errors[0]
