# Shared fixtures for the bake tests.
#
# Fixture doctrine (fixtures/README.md, CIR-PROC-TEST-FIXTURES): tests build their inputs FROM
# fixtures/alex at runtime — a tmp COPY of the tree with one knob turned — never a second
# synthetic person, never inline note text. Date-sensitive rows vary the injected reference
# date, never the committed dates.

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

import allure
import pytest
import yaml

from rules import case_title

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "fixtures"
ALEX_DIR = FIXTURES / "alex"

AlexCopy = Callable[..., Path]


@pytest.fixture
def alex_copy(tmp_path: Path) -> AlexCopy:
    """Factory: copy fixtures/alex into tmp_path/alex and return its circles.yaml path.

    Keyword knobs re-point the sleep item's ``freshness:`` block (``sleep_source``,
    ``yellow_after``, ``red_after``) or set the top-level ``timezone``. ``commands`` maps
    a cell ref (``"wider/plants"``) to the argv its ``status:`` becomes (``command: argv``) —
    the command-adapter knob; the caller writes the script into the copy before loading.
    Everything else stays the fixture person's.
    """
    def make(
        *,
        sleep_source: str | None = None,
        yellow_after: int | None = None,
        red_after: int | None = None,
        timezone: str | None = None,
        commands: dict[str, list[str]] | None = None,
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
        for ref, argv in (commands or {}).items():
            ring_id, item_id = ref.split("/")
            ring = next(r for r in data["rings"] if r["id"] == ring_id)
            item = next(i for i in ring["items"] if i["id"] == item_id)
            item["status"] = {"command": list(argv)}
        config_path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        return config_path

    return make



@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> None:
    """Title a ``@rule``-labelled case with the spec row it cites (tests/rules.py ``case_title``),
    so its evidence row joins the spec table's ``row id`` column. Unlabelled tests keep their name.

    At CALL time, not in a fixture: allure-pytest re-derives the result's name when setup ends."""
    marker = item.get_closest_marker("rule")
    if marker is None:
        return
    callspec = getattr(item, "callspec", None)
    row = case_title(marker.args[0], callspec.id if callspec else None,
                     getattr(getattr(item, "function", None), "__doc__", None))
    if row:
        allure.dynamic.title(row)


# ---------------------------------------------------------------------------- the head stamp
# CONVENTIONS § The head/artifact stamp (allure-behavior-snippets): every Allure results dir
# carries environment.properties (`git.commit=<sha>` — the commit the suite ran at) and
# executor.json (the CI run URL). No `image.digest`: these runs exercise the PR head's source,
# not the built image, so this is PR-head evidence and the stamp says so by omission.

def head_commit() -> str | None:
    """The commit the suite proves: ``CIRCLES_HEAD_SHA`` (CI exports the PR head there — on a
    pull_request event ``GITHUB_SHA`` is the test-merge commit, not the head), else HEAD."""
    sha = os.environ.get("CIRCLES_HEAD_SHA", "").strip()
    if sha:
        return sha
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                             text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def executor() -> dict:
    """Allure's executor.json: the CI run when GitHub Actions env names one, else a local run."""
    server, repo, run_id = (os.environ.get(k) for k in
                            ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    if server and repo and run_id:
        url = f"{server}/{repo}/actions/runs/{run_id}"
        return {"name": "GitHub Actions", "type": "github", "url": f"{server}/{repo}",
                "buildName": f"{os.environ.get('GITHUB_WORKFLOW', 'run')} #{run_id}",
                "buildUrl": url, "reportName": "circles evidence"}
    return {"name": "local", "type": "local", "reportName": "circles evidence"}


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Stamp the --alluredir results dir (no-op when the run writes no Allure results)."""
    results = getattr(session.config.option, "allure_report_dir", None)
    if not results:
        return
    results_dir = Path(results)
    results_dir.mkdir(parents=True, exist_ok=True)
    commit = head_commit()
    lines = [f"git.commit={commit}"] if commit else []
    (results_dir / "environment.properties").write_text(
        "".join(line + "\n" for line in lines), encoding="utf-8")
    (results_dir / "executor.json").write_text(json.dumps(executor(), indent=2) + "\n",
                                               encoding="utf-8")
