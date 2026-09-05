# Shared fixtures for the bake tests.
#
# Fixture doctrine (fixtures/README.md, CIR-PROC-TEST-FIXTURES): tests build their inputs FROM
# fixtures/alex at runtime — a tmp COPY of the tree with one knob turned — never a second
# synthetic person, never inline note text. Date-sensitive rows vary the injected reference
# date, never the committed dates.

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

import pytest
import yaml

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
ALEX_DIR = FIXTURES / "alex"

AlexCopy = Callable[..., Path]


@pytest.fixture
def alex_copy(tmp_path: Path) -> AlexCopy:
    """Factory: copy fixtures/alex into tmp_path/alex and return its circles.yaml path.

    Keyword knobs re-point the sleep item's ``freshness:`` block (``sleep_source``,
    ``yellow_after``, ``red_after``) or set the top-level ``timezone``. Everything else
    stays the fixture person's.
    """
    def make(
        *,
        sleep_source: str | None = None,
        yellow_after: int | None = None,
        red_after: int | None = None,
        timezone: str | None = None,
    ) -> Path:
        root = tmp_path / "alex"
        shutil.copytree(ALEX_DIR, root)
        config_path = root / "circles.yaml"
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if timezone is not None:
            data["timezone"] = timezone
        self_ring = next(r for r in data["rings"] if r["id"] == "self")
        sleep = next(i for i in self_ring["items"] if i["id"] == "sleep")
        freshness = sleep["status"]["freshness"]
        if sleep_source is not None:
            freshness["source"] = sleep_source
        if yellow_after is not None:
            freshness["yellow_after"] = yellow_after
        if red_after is not None:
            freshness["red_after"] = red_after
        config_path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        return config_path

    return make
