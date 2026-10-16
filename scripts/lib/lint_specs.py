"""lint_specs.py — the spec-tree gate.

Mechanically enforces the conventions in `specs/README.md`. This exists because the
conventions are a *sweep*, not a per-page habit: row-id join keys, world declarations,
doctrine slots and evidence lines apply to ~400 rows across 15 pages, and nothing
hand-maintained survives that. Checks that can be mechanical are mechanical; the judgment
layer (doctrine sentences, whether a row's ruling is right) stays with review.

The evidence half is CORRESPONDENCE only (allure-behavior-snippets CONVENTIONS § The lint gate;
homelab ADR-156): the evidence itself is derived per run (`devbox run evidence`), never
committed, so the gate checks only that the page, the tests and the fragments can meet —
- a rule heading is the bare ID (RULES.md rule 3);
- every rule heading carries the evidence pointer (`--8<-- "<ID>.md"`, naming its OWN heading)
  XOR the unverified marker — never both, never neither — and the pointer exactly when a test
  carries `@rule("<ID>")` (tests/rules.py);
- every `rule("…")` label in tests/ names an existing heading;
- every parametrized test carrying a rule label has explicit intent ids.

The schema half (RULES.md rule 7 — requirement ⇄ schema coupling is mechanical): every contract
page (CONTRACT_PAGES, the one declaration) has a sibling `<name>.schema.json`, and every
`*.schema.json` is the sibling of a declared contract page; every `x-requirements` ID heads a rule
somewhere under specs/; every rule on a contract page is either annotated by its schema's
`x-requirements` or named in that schema's root `x-not-schema-shaped` map (ID → why) — never both.

Run via `scripts/lint-specs.sh`, wired into `devbox run ci`.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

# The closed area vocabulary — ruled once (⚖-R22). A new area is a spec change to
# specs/README.md's ownership table, not an authoring choice.
AREAS = {"DATA", "ADAPT", "BAKE", "RENDER", "DETAIL", "PROC"}

# The contract pages (RULES.md rule 7), relative to specs/ — the ONE place they are declared.
# Each must have a sibling `<name>.schema.json` (the machine half the implementation imports).
# Interface pages not listed here are not yet contract pages; a schema beside one is an error.
CONTRACT_PAGES = ("data/data-json.md", "data/circles-yaml.md")
SCHEMA_SUFFIX = ".schema.json"

REQ_HEADING = re.compile(r"^##\s+(CIR-[A-Z0-9-]+)\b")
REQ_ID = re.compile(r"^CIR-([A-Z]+)-([A-Z0-9-]+)$")
AMBIGUITY_REF = re.compile(r"⚖-R(\d+)")
EVIDENCE_LINE = "_Evidence: none yet — unverified._"
# The evidence pointer: pymdownx.snippets transcludes the run's fragment (specs/evidence/<ID>.md,
# written by scripts/evidence.sh) inside a collapsed <details markdown="1"> block.
EVIDENCE_POINTER = re.compile(r'^--8<-- "([^"]+)\.md"\s*$')
WORLD_DECL = re.compile(r"^\s*(?:>\s*)?\*?\*?World:\*?\*?\s+(\w+)", re.MULTILINE)
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)#]+)(#[^)]*)?\)")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")


class Findings:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, path: Path, msg: str) -> None:
        self.errors.append(f"{path}: {msg}")


def split_sections(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    """Split a page into (requirement id, start line, body lines) by H2 CIR- headings."""
    sections: list[tuple[str, int, list[str]]] = []
    current: tuple[str, int] | None = None
    body: list[str] = []
    for n, line in enumerate(lines, start=1):
        m = REQ_HEADING.match(line)
        if m:
            if current:
                sections.append((current[0], current[1], body))
            current = (m.group(1), n)
            body = []
        elif current:
            body.append(line)
    if current:
        sections.append((current[0], current[1], body))
    return sections


def tables_in(body: list[str]) -> list[list[str]]:
    """Group consecutive markdown table lines into tables."""
    tables: list[list[str]] = []
    current: list[str] = []
    for line in body:
        if TABLE_ROW.match(line):
            current.append(line)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def row_ids(table: list[str]) -> list[str]:
    """First-column cells of a table's data rows (skipping header + separator)."""
    ids: list[str] = []
    for line in table[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0]:
            ids.append(cells[0].strip("`*_ "))
    return ids


def check_page(
    path: Path, repo: Path, f: Findings, seen_ids: dict[str, Path],
    labelled: set[str] | None = None,
) -> set[int]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    refs: set[int] = {int(n) for n in AMBIGUITY_REF.findall(text)}

    # --- relative links resolve -------------------------------------------------
    for target, _anchor in MD_LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            f.error(path, f"dead relative link: {target}")

    for n, line in enumerate(lines, start=1):
        m = REQ_HEADING.match(line)
        if m and line.rstrip() != f"## {m.group(1)}":
            f.error(path, f"line {n}: rule heading is decorated ({line.strip()!r}) — the heading "
                          f"is the bare ID, the anchor every link and evidence fragment joins on")

    sections = split_sections(lines)

    # --- world declaration: any page carrying a decision table must name its world ---
    has_table = any(tables_in(body) for _id, _n, body in sections)
    if has_table and not WORLD_DECL.search(text):
        f.error(path, "page has decision tables but no 'World:' declaration")

    for req_id, line_no, body in sections:
        # --- ID grammar + closed area vocabulary --------------------------------
        m = REQ_ID.match(req_id)
        if not m:
            f.error(path, f"line {line_no}: malformed requirement id {req_id!r}")
            continue
        area = m.group(1)
        if area not in AREAS:
            f.error(
                path,
                f"line {line_no}: {req_id} uses area {area!r}, "
                f"not in the closed vocabulary {sorted(AREAS)}",
            )

        # --- IDs are never reused -----------------------------------------------
        if req_id in seen_ids:
            f.error(path, f"line {line_no}: duplicate requirement id {req_id} "
                          f"(also in {seen_ids[req_id]})")
        else:
            seen_ids[req_id] = path

        # --- evidence: pointer XOR marker; verified-ness is derived, never declared
        check_evidence_slot(path, req_id, body, f, labelled)
        # A coverage claim is a cell that *leads* with the marker (the ✓ column pattern).
        # Prose mentioning the marker — process/testing.md states the prohibition, and
        # open-questions.md discusses it — is not itself a violation.
        # Evidence blocks inside <details> are exempt — they report test results, not
        # declare coverage.
        in_details = False
        for line in body:
            if "<details" in line:
                in_details = True
            if "</details>" in line:
                in_details = False
            if in_details:
                continue
            if line.lstrip().startswith("|"):
                for cell in line.strip().strip("|").split("|"):
                    if cell.strip().startswith(("✓", "🚧")):
                        f.error(path, f"{req_id}: declares verified-ness (✓/🚧 marker) — "
                                      f"coverage is derived from evidence, never declared")
                        break

        # --- row ids are join keys: unique within their table -------------------
        for table in tables_in(body):
            if len(table) < 3:
                continue
            ids = row_ids(table)
            dupes = {i for i in ids if ids.count(i) > 1}
            for d in sorted(dupes):
                f.error(path, f"{req_id}: duplicate row id {d!r} — row ids are "
                              f"evidence join keys and must be unique in their table")
            for rid in ids:
                if not rid:
                    f.error(path, f"{req_id}: table row with an empty row id")

    return refs


def check_ambiguity_index(repo: Path, refs: set[int], f: Findings) -> None:
    """Every ⚖-R<NN> referenced anywhere must be indexed in open-questions.md."""
    index = repo / "specs" / "open-questions.md"
    if not index.exists():
        f.error(index, "the ⚖ index is missing")
        return
    text = index.read_text(encoding="utf-8")
    indexed = {int(n) for n in AMBIGUITY_REF.findall(text)}
    for ref in sorted(refs - indexed):
        f.error(index, f"⚖-R{ref} is referenced in the tree but not indexed here")


def check_evidence_slot(
    path: Path, req_id: str, body: list[str], f: Findings, labelled: set[str] | None,
) -> None:
    """One rule section's evidence slot: the pointer to its own fragment XOR the marker.

    ``labelled`` (the rule IDs some test labels, ``rule_labels``) adds the correspondence: the
    pointer exactly when a labelled test exists. None skips that half (a page linted alone).
    """
    pointers = [m.group(1) for m in map(EVIDENCE_POINTER.match, body) if m]
    marker = any(line.strip() == EVIDENCE_LINE for line in body)
    if pointers and marker:
        f.error(path, f"{req_id}: both an evidence pointer and the unverified marker — "
                      f"exactly one of them")
        return
    if not pointers and not marker:
        f.error(path, f"{req_id}: no evidence slot — add the pointer "
                      f'(--8<-- "{req_id}.md") or the marker ({EVIDENCE_LINE!r})')
        return
    for target in pointers:
        if target != req_id:
            f.error(path, f'{req_id}: evidence pointer names "{target}.md" — a rule transcludes '
                          f"only its own fragment")
    if len(pointers) > 1:
        f.error(path, f"{req_id}: {len(pointers)} evidence pointers — exactly one")
    if labelled is None:
        return
    if pointers and req_id not in labelled:
        f.error(path, f"{req_id}: evidence pointer but no test carries @rule({req_id!r}) — "
                      f"the fragment can never exist; use the marker")
    if marker and req_id in labelled:
        f.error(path, f"{req_id}: a test carries @rule({req_id!r}) but the page says "
                      f"{EVIDENCE_LINE!r} — use the evidence pointer")


def _test_files(repo: Path) -> list[Path]:
    return sorted((repo / "tests").rglob("test_*.py"))


def _labels_in(tree: ast.Module) -> list[str]:
    """IDs a module labels: ``@rule("ID")`` on a function/class, ``pytestmark = rule("ID")``
    (the touched-rules shapes — by ast walk, so a string or a plain call never counts)."""
    exprs: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exprs += node.decorator_list
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets):
            exprs += node.value.elts if isinstance(node.value, (ast.List, ast.Tuple)) else [node.value]
    return [e.args[0].value for e in exprs
            if _is_rule_decorator(e) and e.args and isinstance(e.args[0], ast.Constant)
            and isinstance(e.args[0].value, str)]


def rule_labels(repo: Path) -> dict[str, list[Path]]:
    """rule ID → the test files labelling it with ``rule("…")``."""
    out: dict[str, list[Path]] = {}
    for path in _test_files(repo):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for rule_id in _labels_in(tree):
            out.setdefault(rule_id, []).append(path)
    return out


def check_labels(labels: dict[str, list[Path]], seen_ids: dict[str, Path], f: Findings) -> None:
    """Every rule label names an existing heading (label → heading; tests/rules.py fails the
    same mislabel at collection — this catches it without running pytest)."""
    for rule_id, paths in sorted(labels.items()):
        if rule_id not in seen_ids:
            for path in sorted(set(paths)):
                f.error(path, f"rule({rule_id!r}) names no `## {rule_id}` heading under specs/")


def _is_rule_decorator(node: ast.expr) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "rule")


def _parametrize(node: ast.expr) -> ast.Call | None:
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "parametrize"):
        return node
    return None


def _explicit_ids(call: ast.Call) -> bool:
    """``ids=`` given, or every argvalue a literal ``pytest.param(..., id=...)``."""
    if any(kw.arg == "ids" for kw in call.keywords):
        return True
    values = call.args[1] if len(call.args) > 1 else next(
        (kw.value for kw in call.keywords if kw.arg == "argvalues"), None)
    if not isinstance(values, (ast.List, ast.Tuple)) or not values.elts:
        return False
    for elt in values.elts:
        if not (isinstance(elt, ast.Call) and isinstance(elt.func, ast.Attribute)
                and elt.func.attr == "param" and any(kw.arg == "id" for kw in elt.keywords)):
            return False
    return True


def check_param_ids(path: Path, f: Findings) -> int:
    """Every rule-labelled parametrized test carries explicit intent ids (CONVENTIONS § The
    intent column: an auto-generated id restates the input). Returns how many were checked."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    checked = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(_is_rule_decorator(d) for d in node.decorator_list):
            continue
        for deco in node.decorator_list:
            call = _parametrize(deco)
            if call is None:
                continue
            checked += 1
            if not _explicit_ids(call):
                f.error(path, f"line {deco.lineno}: {node.name} carries a rule label but its "
                              f"parametrize has no explicit ids — add ids= or "
                              f"pytest.param(..., id=<intent>)")
    return checked


def _schema_requirements(node: object, out: list[str], f: Findings, path: Path) -> None:
    """Collect every ``x-requirements`` list anywhere in a schema document."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "x-requirements":
                if not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
                    f.error(path, f"x-requirements must be a list of rule IDs, got {value!r}")
                    continue
                out.extend(value)
            else:
                _schema_requirements(value, out, f, path)
    elif isinstance(node, list):
        for value in node:
            _schema_requirements(value, out, f, path)


def check_schemas(
    specs: Path, seen_ids: dict[str, Path], f: Findings,
    contract_pages: tuple[str, ...] = CONTRACT_PAGES,
) -> int:
    """The requirement ⇄ schema coupling (RULES.md rule 7). Returns how many schemas were checked."""
    declared = {(specs / rel).resolve() for rel in contract_pages}
    for page in sorted(declared):
        if not page.exists():
            f.error(page, "declared contract page (CONTRACT_PAGES) does not exist")
        elif not page.with_suffix(SCHEMA_SUFFIX).exists():
            f.error(page, f"contract page has no sibling {page.stem}{SCHEMA_SUFFIX} "
                          f"(RULES.md rule 7 — the machine half)")

    schemas = sorted(p for p in specs.rglob(f"*{SCHEMA_SUFFIX}")
                     if (specs / "evidence") not in p.parents)
    for schema_path in schemas:
        page = schema_path.with_name(schema_path.name[: -len(SCHEMA_SUFFIX)] + ".md").resolve()
        if page not in declared:
            f.error(schema_path, f"schema is not the sibling of a declared contract page "
                                 f"({page.name} is not in CONTRACT_PAGES)")
            continue
        try:
            doc = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            f.error(schema_path, f"not valid JSON: {e}")
            continue

        annotated: list[str] = []
        _schema_requirements(doc, annotated, f, schema_path)
        for rule_id in sorted(set(annotated)):
            if rule_id not in seen_ids:
                f.error(schema_path, f"x-requirements names {rule_id!r}, which heads no rule "
                                     f"under specs/ (an orphan annotation)")

        not_shaped = doc.get("x-not-schema-shaped", {}) if isinstance(doc, dict) else {}
        if not isinstance(not_shaped, dict):
            f.error(schema_path, "x-not-schema-shaped must be a map of rule ID → reason")
            not_shaped = {}
        page_rules = {rid for rid, where in seen_ids.items() if where.resolve() == page}
        for rule_id in sorted(not_shaped):
            if rule_id not in page_rules:
                f.error(schema_path, f"x-not-schema-shaped lists {rule_id!r}, which heads no "
                                     f"rule on {page.name}")
            if rule_id in annotated:
                f.error(schema_path, f"{rule_id} is both annotated (x-requirements) and listed "
                                     f"in x-not-schema-shaped — pick one")
        for rule_id in sorted(page_rules - set(annotated) - set(not_shaped)):
            f.error(page, f"{rule_id} is on a contract page but neither annotated in "
                          f"{schema_path.name} (x-requirements) nor listed in its "
                          f"x-not-schema-shaped — an orphan rule")
    return len(schemas)


def check_fixture(repo: Path, f: Findings) -> None:
    """Guard the fixture against spec drift.

    Nothing in the fan-out gated the fixture person against the schema the specs describe —
    the cheapest possible guard, and the one that catches an unresolvable `source:` instantly.
    """
    config = repo / "fixtures" / "alex" / "circles.yaml"
    if not config.exists():
        f.error(config, "fixture person's circles.yaml is missing")
        return
    text = config.read_text(encoding="utf-8")
    base = config.parent

    for m in re.finditer(r"^\s*(source|command):\s*(.+?)\s*(?:#.*)?$", text, re.MULTILINE):
        kind, raw = m.group(1), m.group(2).strip()
        if kind == "command":
            # `command:` is an argv list (CIR-ADAPT-COMMAND: no shell); only argv[0] — the
            # program the bake will execute — is a path this gate can resolve.
            argv = re.findall(r"[\"']([^\"']+)[\"']|(\S+)", raw.strip("[]"))
            flat = [a or b for a, b in argv]
            if not flat:
                f.error(config, "command: empty argv")
                continue
            target = flat[0].rstrip(",")
        else:
            target = raw.strip("\"'")
        if any(ch in target for ch in "*?["):
            if not list(base.glob(target)):
                f.error(config, f"{kind}: glob {target!r} matches no file")
            continue
        if not (base / target).exists():
            f.error(config, f"{kind}: {target!r} does not resolve under {base}")

    # DP-50: the fixture's freshness examples decay with the calendar. The dates are
    # illustrative only if a reference date is declared alongside them; without one, the
    # committed values silently stop demonstrating the light the spec claims for them.
    readme = repo / "fixtures" / "README.md"
    if readme.exists() and "reference date" not in readme.read_text(encoding="utf-8").lower():
        f.error(readme, "fixture declares no reference date — freshness key examples "
                        "decay against the calendar (⚖-R24)")


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    specs = repo / "specs"
    f = Findings()
    seen_ids: dict[str, Path] = {}
    all_refs: set[int] = set()

    # specs/evidence/ holds the GENERATED fragments (scripts/evidence.sh) — never a spec page.
    pages = sorted(p for p in specs.rglob("*.md") if (specs / "evidence") not in p.parents)
    if not pages:
        print("lint-specs: no spec pages found", file=sys.stderr)
        return 1

    labels = rule_labels(repo)
    labelled = set(labels)
    for page in pages:
        all_refs |= check_page(page, repo, f, seen_ids, labelled)

    check_ambiguity_index(repo, all_refs, f)
    check_labels(labels, seen_ids, f)
    params = sum(check_param_ids(path, f) for path in _test_files(repo))
    schemas = check_schemas(specs, seen_ids, f)
    check_fixture(repo, f)

    if f.errors:
        print(f"lint-specs: {len(f.errors)} problem(s)\n", file=sys.stderr)
        for e in f.errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"lint-specs: OK — {len(pages)} pages, {len(seen_ids)} requirement ids "
          f"({len(labelled & set(seen_ids))} labelled by tests), {params} labelled "
          f"parametrizations with explicit ids, {schemas} contract-page schemas coupled, "
          f"{len(all_refs)} ⚖ entries indexed")
    return 0


if __name__ == "__main__":
    sys.exit(main())