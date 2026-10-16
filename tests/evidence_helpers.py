"""given / when / then for evidence at the bake's system boundary (circles#103 step 2).

The process contract is allure-behavior-snippets' CONVENTIONS.md (scripts/lib/snippets.sh pins
the release): § Allure taxonomy (only a test that observes the system boundary carries a
``@rule`` label), § Evidence row identity (the world is named on every case), § Prime rule of
reporting (top-level steps read given / when / then; ONE when; one then per claim, named with
the claimed value) and § The helper razor (helpers arrange or observe — they never build the
action's cleverness).

The bake's boundary is its CLI: ``python -m bake --config <circles.yaml> --out <dir> [...]``.
What it shows the world is the exit code, stdout/stderr, and ``<out>/data.json`` +
``<out>/index.html``. A labelled bake case therefore reads:

    @rule("CIR-DATA-CONFIG-ERROR-FAILS")
    def test_message_names_the_item(alex_copy):
        "CIR-DATA-CONFIG-ERROR-FAILS#message-names-the-item — …"
        config = given_alex(alex_copy, "children/kit status: manual: blue",
                            lambda c: item(c, "children/kit").update(status={"manual": "blue"}))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 1)
        verdict("stderr", run.stderr, "children/kit", op="contains")

API (the whole of it):

- ``given_alex(alex_copy, mutation=None, edit=None)`` — the given step: a tmp copy of the world
  ``fixtures/alex`` (via conftest's ``alex_copy``), the world seed attached (circles.yaml +
  sha256 of every world file), then ``edit`` applied to the config as a plain dict (wire format,
  CONVENTIONS § Tests speak wire format) and the derived circles.yaml attached. ``mutation`` is
  the human sentence naming the turned knob AND its value — it is the step name, so it threads.
- ``ring(config, ring_id)`` / ``item(config, "ring/item")`` — navigate the config dict inside an
  ``edit`` (``KeyError`` on a ref the world lacks: an edit that misses is an arrange failure).
- ``when_bake(config, *flags, reference_date=FIXTURE_REFERENCE_DATE)`` — the ONE when step: the
  bake as a real subprocess; argv, stdout, stderr and data.json attached under it with host paths
  neutralised; returns a ``BakeRun``.
- ``verdict(claim, actual, expected, op="=")`` — one then step, ``Then: <claim> <op> <expected>``,
  wrapping the assertion so the step itself goes red / green. ``op``: ``=``, ``contains``,
  ``not contains``.
- ``BakeRun.warnings`` / ``.artifact_files`` — the artifact's build warnings as searchable text,
  and the files present in ``--out`` (``[]`` = nothing published).
- ``then_config_error(run, message)`` — the spec phrase "config error, bake fails" as its three
  claims (exit code = 1, stderr contains the message, no artifact written), each its own verdict.
- ``item_of(data, "ring/item")`` — read one item from a ``BakeRun.data`` artifact (for verdicts).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import allure
import yaml

REPO = Path(__file__).resolve().parent.parent
WORLD = "alex"
WORLD_DIR = REPO / "fixtures" / WORLD
# The fixture reference date (fixtures/alex/circles.yaml header, ⚖-R24): every dated example in
# the world is stated relative to it, so every bake case pins it (CIR-ADAPT-REFERENCE-DATE).
FIXTURE_REFERENCE_DATE = "2026-08-03"
BAKE_TIMEOUT_S = 60

Config = dict[str, Any]
# config path → the mutation sentence its given step named, so the when step that bakes that
# config carries the same value (CONVENTIONS: names thread the spec column's value).
_MUTATIONS: dict[Path, str] = {}


# ---------------------------------------------------------------------------- given

def world_seed() -> str:
    """The world's seed as text: a sha256 line per committed world file, then circles.yaml."""
    lines = [f"# world: {WORLD} — fixtures/{WORLD}/ (sha256, path)"]
    for path in sorted(p for p in WORLD_DIR.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(WORLD_DIR).as_posix()}")
    lines += ["", "# circles.yaml", (WORLD_DIR / "circles.yaml").read_text(encoding="utf-8")]
    return "\n".join(lines)


def ring(config: Config, ring_id: str) -> dict:
    """The ring dict ``ring_id`` of a config dict (KeyError when the world has none)."""
    for r in config["rings"]:
        if r.get("id") == ring_id:
            return r
    raise KeyError(f"world {WORLD} has no ring {ring_id!r}")


def item(config: Config, ref: str) -> dict:
    """The item dict at ``<ring-id>/<item-id>`` of a config dict (KeyError when absent)."""
    ring_id, item_id = ref.split("/")
    for i in ring(config, ring_id)["items"]:
        if i.get("id") == item_id:
            return i
    raise KeyError(f"world {WORLD} has no item {ref!r}")


def given_alex(
    alex_copy: Callable[..., Path],
    mutation: str | None = None,
    edit: Callable[[Config], None] | None = None,
) -> Path:
    """Given: the world ``alex`` in a tmp dir, optionally with one knob turned.

    ``mutation`` names the knob and its value (``"children/kit status: manual: blue"``) — it is
    the step name, so a parametrized value threads through it. ``edit`` mutates the config dict
    in place. Returns the tmp ``circles.yaml`` path (its directory is the world copy)."""
    if (mutation is None) != (edit is None):
        raise TypeError("given_alex: pass mutation and edit together (the name carries the edit)")
    name = f"Given: world {WORLD}" + (f", {mutation}" if mutation else " (unmodified)")
    with allure.step(name):
        allure.attach(world_seed(), name=f"world: {WORLD} — seed (sha256 + circles.yaml)",
                      attachment_type=allure.attachment_type.TEXT)
        config_path = alex_copy()
        if edit is not None:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            edit(config)
            derived = yaml.dump(config, allow_unicode=True, sort_keys=False)
            config_path.write_text(derived, encoding="utf-8")
            allure.attach(derived, name=f"circles.yaml (world: {WORLD}, {mutation})",
                          attachment_type=allure.attachment_type.YAML)
            _MUTATIONS[config_path] = mutation
    return config_path


# ---------------------------------------------------------------------------- when

@dataclass(frozen=True)
class BakeRun:
    """What the bake showed the world: its exit code, its console, its artifact."""

    exit_code: int
    stdout: str          # host paths neutralised (the tmp root reads as ".")
    stderr: str          # likewise
    out_dir: Path
    data: dict | None    # parsed <out>/data.json; None when the bake wrote none

    @property
    def warnings(self) -> str:
        """The artifact's build warnings, one ``<item-ref or ->: <message>`` line each ("" when none
        or no artifact) — a text a ``contains`` verdict can search."""
        return "\n".join(f"{w.get('item') or '-'}: {w['message']}"
                         for w in (self.data or {}).get("warnings", []))

    @property
    def artifact_files(self) -> list[str]:
        """The artifact files present in ``--out`` after the run (sorted names)."""
        return sorted(p.name for p in self.out_dir.glob("*")) if self.out_dir.is_dir() else []


def _neutral(text: str, root: Path) -> str:
    return text.replace(str(root.resolve()) + os.sep, "./").replace(str(root.resolve()), ".")


def when_bake(config: Path, *flags: str, reference_date: str | None = FIXTURE_REFERENCE_DATE) -> BakeRun:
    """When: the bake runs — ``python -m bake`` as a real subprocess, the action under test.

    cwd is the directory holding the world copy, so argv is relative (``alex/circles.yaml``,
    ``out``) and no host path reaches an attachment. When ``given_alex`` mutated this config, the
    step name repeats the mutation sentence, so the knob's value threads given → when → then. ``flags`` are extra CLI flags
    (``"--evaluate"``, ``"--stale-after-hours", "24"``); ``reference_date=None`` omits the flag."""
    root = config.parent.parent
    out = root / "out"
    argv = ["-m", "bake", "--config", config.relative_to(root).as_posix(), "--out", "out"]
    if reference_date is not None:
        argv += ["--reference-date", reference_date]
    argv += list(flags)
    shown = "python " + " ".join(argv)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [str(REPO), os.environ.get("PYTHONPATH")])))
    mutation = _MUTATIONS.get(config)
    step = f"When: {shown.removeprefix('python -m ')}" + (f" (world {WORLD}: {mutation})" if mutation else "")
    with allure.step(step):
        proc = subprocess.run([sys.executable, *argv], cwd=root, env=env,
                              capture_output=True, text=True, timeout=BAKE_TIMEOUT_S)
        stdout, stderr = _neutral(proc.stdout, root), _neutral(proc.stderr, root)
        allure.attach(f"$ {shown}\n# cwd: the tmp dir holding the world copy\n",
                      name="bake argv", attachment_type=allure.attachment_type.TEXT)
        allure.attach(stderr or "(empty)\n", name=f"bake stderr (exit code {proc.returncode})",
                      attachment_type=allure.attachment_type.TEXT)
        if stdout:
            allure.attach(stdout, name="bake stdout", attachment_type=allure.attachment_type.TEXT)
        data_path = out / "data.json"
        data = None
        if data_path.is_file():
            raw = data_path.read_text(encoding="utf-8")
            allure.attach(raw, name="out/data.json", attachment_type=allure.attachment_type.JSON)
            data = json.loads(raw)
    return BakeRun(exit_code=proc.returncode, stdout=stdout, stderr=stderr, out_dir=out, data=data)


# ---------------------------------------------------------------------------- then

def _shown(value: Any) -> str:
    """A value as a step name shows it: strings quoted, lists/dicts as JSON, the rest str()."""
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "=": lambda actual, expected: actual == expected,
    "contains": lambda actual, expected: expected in actual,
    "not contains": lambda actual, expected: expected not in actual,
}


def verdict(claim: str, actual: Any, expected: Any, *, op: str = "=") -> None:
    """Then: ``<claim> <op> <expected>`` — one claim, one step; the assertion inside it makes the
    step itself red / green. The step name carries the CLAIMED value; the actual one is in the
    assertion message when it differs."""
    check = _OPS[op]
    with allure.step(f"Then: {claim} {op} {_shown(expected)}"):
        assert check(actual, expected), f"{claim}: expected {op} {_shown(expected)}, actual {_shown(actual)}"


def then_config_error(run: BakeRun, message: str) -> None:
    """The spec phrase "config error, bake fails" as its three claims (CIR-DATA-VALIDATION: a
    failed bake publishes nothing): exit code 1, stderr names ``message``, no artifact in --out."""
    verdict("exit code", run.exit_code, 1)
    verdict("stderr", run.stderr, message, op="contains")
    verdict("artifact files in out/", run.artifact_files, [])


def item_of(data: dict, ref: str) -> dict:
    """The item dict at ``<ring-id>/<item-id>`` in a baked artifact (KeyError when absent)."""
    ring_id, item_id = ref.split("/")
    for r in data["rings"]:
        if r["id"] == ring_id:
            for i in r["items"]:
                if i["id"] == item_id:
                    return i
    raise KeyError(f"artifact has no item {ref!r}")
