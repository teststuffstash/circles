"""rule() — the one evidence label (allure-behavior-snippets CONVENTIONS § The rule() decorator).

A test proves a spec rule by carrying ``@rule("CIR-…")``. One string, every duty:

- ``allure.story(<ID>)`` — the join key: ``devbox run evidence`` (scripts/evidence.sh) emits one
  ``<ID>.md`` fragment per story and the spec page transcludes it under the ``## <ID>`` heading;
- ``allure.epic`` (the spec page, path under specs/ without suffix) and ``allure.feature`` (the
  page section the rule sits under) — derived here, never hand-written;
- ``allure.link`` to the rule's anchor on the specs site (the URL pattern lives only here);
- the ``world`` label: v0 has one world, the fixture person ``alex`` (specs/README.md §Conventions);
- the ``rule`` pytest marker, which conftest.py reads to title the case with its cited row id
  (``case_title``) so the tool's ``--spec`` join can match the spec table's ``row id`` column.

It fails COLLECTION when the ID heads no ``## <ID>`` heading under specs/ — a mislabelled test
cannot produce evidence that files under a ghost rule (CIR-PROC-GATE#gate-no-dangling-spec-reference).

Use per test function (one story per test function — CONVENTIONS § Allure taxonomy):

    @rule("CIR-ADAPT-CONTRACT")
    def test_adapter_resolves_one_item(): ...
"""

from __future__ import annotations

import functools
import os
import re
from pathlib import Path
from typing import Any

import allure
import pytest

REPO = Path(__file__).resolve().parent.parent
SPECS = REPO / "specs"
# Generated fragments (scripts/evidence.sh copies them here for the site build) — never a spec page.
GENERATED = SPECS / "evidence"
WORLD = "alex"
# The ONE place the spec-site URL pattern lives (mkdocs.yml: use_directory_urls: false).
SPECS_BASE_URL = os.environ.get("SPECS_BASE_URL", "https://specs.circles.teststuff.net").rstrip("/")
SPEC_URL = SPECS_BASE_URL + "/specs/{page}.html#{anchor}"

# A rule heading is the bare ID (RULES.md rule 3: heading == anchor == ID, never decorated).
RULE_HEADING = re.compile(r"^#{2,6}\s+(CIR-[A-Z0-9-]+)\s*$")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CITATION = re.compile(r"(CIR-[A-Z0-9]+(?:-[A-Z0-9]+)+)#([a-z0-9-]+)")


@functools.cache
def rule_pages(specs: Path = SPECS) -> dict[str, tuple[str, str]]:
    """rule ID → (page path under specs/ without suffix, enclosing section title)."""
    index: dict[str, tuple[str, str]] = {}
    for md in sorted(specs.rglob("*.md")):
        if GENERATED in md.parents:
            continue
        page = md.relative_to(specs).with_suffix("").as_posix()
        sections: dict[int, str] = {}
        for line in md.read_text(encoding="utf-8").splitlines():
            head = _HEADING.match(line)
            if not head:
                continue
            level = len(head.group(1))
            m = RULE_HEADING.match(line)
            if m:
                parent = next((sections[lv] for lv in range(level - 1, 0, -1) if lv in sections), page)
                index[m.group(1)] = (page, parent)
            else:
                sections[level] = head.group(2)
                for deeper in [lv for lv in sections if lv > level]:
                    del sections[deeper]
    return index


class _Rule(list):
    """The rule's marks: a list (``pytestmark = rule(...)`` accepts it) that is also a decorator."""

    def __call__(self, obj: Any) -> Any:
        for mark in self:
            obj = mark(obj)
        return obj


def rule(rule_id: str, *, specs: Path = SPECS) -> _Rule:
    """The marks for a test proving ``rule_id``; ValueError (a collection error) on an unknown ID."""
    pages = rule_pages(specs)
    if rule_id not in pages:
        raise ValueError(
            f"rule({rule_id!r}): no `## {rule_id}` heading under {specs} — a label must name an "
            f"existing rule, so this fails collection loudly ({len(pages)} rules known)"
        )
    page, section = pages[rule_id]
    return _Rule([
        pytest.mark.rule(rule_id),
        allure.story(rule_id),
        allure.epic(page),
        allure.feature(section),
        allure.label("world", WORLD),
        allure.link(SPEC_URL.format(page=page, anchor=rule_id.lower()), name=f"spec: {rule_id}"),
    ])


def case_title(rule_id: str, param_id: str | None, docstring: str | None) -> str | None:
    """The spec row a labelled case proves — its Allure title, so the evidence tool's spec join
    (description cell == case) matches the page's ``row id`` column.

    The citation is the source of truth (specs/README.md: a test cites its row as
    ``CIR-<AREA>-<NAME>#<row-id>`` verbatim): the parametrised case id first, else the first
    citation of ``rule_id`` in the docstring's first paragraph. None when neither cites a row.
    """
    for text in (param_id or "", (docstring or "").strip().split("\n\n", 1)[0]):
        for req, row in CITATION.findall(text):
            if req == rule_id:
                return row
    return None
