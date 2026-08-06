"""lint_specs.py — the spec-tree gate.

Mechanically enforces the conventions in `specs/README.md`. This exists because the
conventions are a *sweep*, not a per-page habit: row-id join keys, world declarations,
doctrine slots and evidence lines apply to ~400 rows across 15 pages, and nothing
hand-maintained survives that. Checks that can be mechanical are mechanical; the judgment
layer (doctrine sentences, whether a row's ruling is right) stays with review.

Run via `scripts/lint-specs.sh`, wired into `devbox run ci`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# The closed area vocabulary — ruled once (⚖-R22). A new area is a spec change to
# specs/README.md's ownership table, not an authoring choice.
AREAS = {"DATA", "ADAPT", "BAKE", "RENDER", "DETAIL", "PROC"}

REQ_HEADING = re.compile(r"^##\s+(CIR-[A-Z0-9-]+)\b")
REQ_ID = re.compile(r"^CIR-([A-Z]+)-([A-Z0-9-]+)$")
AMBIGUITY_REF = re.compile(r"⚖-R(\d+)")
EVIDENCE_LINE = "_Evidence: none yet — unverified._"
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


def check_page(path: Path, repo: Path, f: Findings, seen_ids: dict[str, Path]) -> set[int]:
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

        # --- evidence line: verified-ness is derived, never declared ------------
        joined = "\n".join(body)
        if EVIDENCE_LINE not in joined and "<details>" not in joined:
            f.error(path, f"{req_id}: missing evidence line ({EVIDENCE_LINE!r}) "
                          f"or an evidence <details> block")
        # A coverage claim is a cell that *leads* with the marker (the ✓ column pattern).
        # Prose mentioning the marker — process/testing.md states the prohibition, and
        # open-questions.md discusses it — is not itself a violation.
        if any(
            cell.strip().startswith(("✓", "🚧"))
            for line in body
            if line.lstrip().startswith("|")
            for cell in line.strip().strip("|").split("|")
        ):
            f.error(path, f"{req_id}: declares verified-ness (✓/🚧 marker) — "
                          f"coverage is derived from evidence, never declared")

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

    pages = sorted(specs.rglob("*.md"))
    if not pages:
        print("lint-specs: no spec pages found", file=sys.stderr)
        return 1

    for page in pages:
        all_refs |= check_page(page, repo, f, seen_ids)

    check_ambiguity_index(repo, all_refs, f)
    check_fixture(repo, f)

    if f.errors:
        print(f"lint-specs: {len(f.errors)} problem(s)\n", file=sys.stderr)
        for e in f.errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"lint-specs: OK — {len(pages)} pages, {len(seen_ids)} requirement ids, "
          f"{len(all_refs)} ⚖ entries indexed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
