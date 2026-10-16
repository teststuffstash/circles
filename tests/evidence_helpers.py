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

- ``given_alex(alex_copy, mutation=None, edit=None, *, world=None)`` — the given step: a tmp copy
  of the world ``fixtures/alex`` (via conftest's ``alex_copy``), the world seed attached
  (circles.yaml + sha256 of every world file), then the knob turned inside the step: ``world``
  (a FILE-level knob — a script, a mode bit — applied to the copy's directory) and/or ``edit``
  (applied to the config as a plain dict, wire format — CONVENTIONS § Tests speak wire format —
  and the derived circles.yaml attached). ``mutation`` is the human sentence naming the turned
  knob AND its value — it is the step name, so it threads; pass it exactly when a knob is turned.
- ``given_file(config, rel, text, executable=False)`` / ``given_script(config, rel, body)`` — a
  given step writing (and attaching) one extra file at ``<config-dir>/<rel>`` — a note's content,
  an executable ``/bin/sh`` script — the input a config edit alone cannot express.
- ``given_leash(config, **constants)`` — the bake's ⚖-R21 leash shrunk (a tests-only
  ``sitecustomize.py`` setting ``bake.adapters`` constants); returns the env overrides to hand to
  ``when_bake(..., env=)``.
- ``given_prior_bake(root, config, *flags, why, env=None)`` — an arrange-only bake that already
  published ``<root>/out`` (dies loudly on failure); returns its data.json text.
- ``ring(config, ring_id)`` / ``item(config, "ring/item")`` — navigate the config dict inside an
  ``edit`` (``KeyError`` on a ref the world lacks: an edit that misses is an arrange failure).
- ``when_bake(config, *flags, reference_date=FIXTURE_REFERENCE_DATE, env=None)`` — the ONE when
  step: the bake as a real subprocess; argv, stdout, stderr and data.json attached under it with
  host paths neutralised; ``env`` = explicit environment overrides for that subprocess (never
  ``monkeypatch.setenv``); returns a ``BakeRun``.
- ``verdict(claim, actual, expected, op="=")`` — one then step, ``Then: <claim> <op> <expected>``,
  wrapping the assertion so the step itself goes red / green. ``op``: ``=``, ``contains``,
  ``not contains``, ``!=``, ``>=``, ``<=``, ``>``, ``<`` (the browser tier's measured claims use
  the same implementation — tests/browser/browser_helpers.py ``then``).
- ``shown(value)`` — a value as a step name shows it (strings quoted, lists/dicts as JSON).
- ``BakeRun.warnings`` / ``.artifact_files`` / ``.raw`` — the artifact's build warnings as
  searchable text, the files present in ``--out`` (``[]`` = nothing published), and out/data.json
  as the text the page's host serves.
- ``warnings_for(run, ref)`` — the build-warning messages naming one item.
- ``masked_digest(raw)`` — a short sha256 of a data.json text with ``generated_at`` masked
  (CIR-BAKE-DETERMINISM's "byte-identical except generated_at" as one comparable value).
- ``then_config_error(run, message)`` — the spec phrase "config error, bake fails" as its three
  claims (exit code = 1, stderr contains the message, no artifact written), each its own verdict.
- ``then_grey_by_failure(run, ref, *, cause=None, guardrail=None, exact_detail=False,
  ships=False)`` — the spec phrase "⚪ + build warning, reason by-failure"
  (CIR-DATA-FAILURE-IS-GREY) as its claims; returns the warning text.
- ``item_of(data, "ring/item")`` — read one item from a ``BakeRun.data`` artifact (for verdicts).
"""

from __future__ import annotations

import hashlib
import json
import operator
import os
import re
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
    *,
    world: Callable[[Path], None] | None = None,
) -> Path:
    """Given: the world ``alex`` in a tmp dir, optionally with one knob turned.

    ``mutation`` names the knob and its value (``"children/kit status: manual: blue"``) — it is
    the step name, so a parametrized value threads through it. ``world`` applies a FILE-level
    knob to the copy's directory (a script, a mode bit — a mutation with no config edit); ``edit``
    mutates the config dict in place. A mutation sentence comes with at least one of them, and
    neither comes without it. Returns the tmp ``circles.yaml`` path (its directory is the world
    copy)."""
    if (mutation is None) != (edit is None and world is None):
        raise TypeError("given_alex: a mutation sentence names an edit and/or a world knob, and "
                        "every knob is named (the name carries the edit)")
    name = f"Given: world {WORLD}" + (f", {mutation}" if mutation else " (unmodified)")
    with allure.step(name):
        allure.attach(world_seed(), name=f"world: {WORLD} — seed (sha256 + circles.yaml)",
                      attachment_type=allure.attachment_type.TEXT)
        config_path = alex_copy()
        if world is not None:
            world(config_path.parent)
        if edit is not None:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            edit(config)
            derived = yaml.dump(config, allow_unicode=True, sort_keys=False)
            config_path.write_text(derived, encoding="utf-8")
            allure.attach(derived, name=f"circles.yaml (world: {WORLD}, {mutation})",
                          attachment_type=allure.attachment_type.YAML)
        if mutation is not None:
            _MUTATIONS[config_path] = mutation
    return config_path


def given_file(config: Path, rel: str, text: str, *, executable: bool = False) -> Path:
    """Given: a file at ``<config-dir>/<rel>`` holding ``text`` (attached), the world copy's
    extra input that a config edit alone cannot express (a note's content, a script)."""
    shown_text = text if len(text) <= 60 else text[:57] + "…"
    with allure.step(f"Given: {rel} holds {shown_text!r}" + (" (mode 0755)" if executable else "")):
        path = config.parent / rel
        path.write_text(text, encoding="utf-8")
        if executable:
            path.chmod(0o755)
        allure.attach(text, name=f"{rel} (world: {WORLD} copy)",
                      attachment_type=allure.attachment_type.TEXT)
    return path


def given_script(config: Path, rel: str, body: str) -> Path:
    """Given: an executable /bin/sh script at ``<config-dir>/<rel>`` running ``body``."""
    return given_file(config, rel, "#!/bin/sh\n" + body, executable=True)


def given_leash(config: Path, **constants: float) -> dict[str, str]:
    """Given: the bake's ⚖-R21 leash shrunk to ``constants`` (bake.adapters module constants).

    The bake runs in a subprocess, so its 30 s / 5 min constants cannot be monkeypatched from the
    test: a tests-only ``sitecustomize.py``, generated beside the world copy (``<tmp>/leash/``)
    and put on the bake's PYTHONPATH, sets them before ``python -m bake`` runs its unchanged
    ``main()``. Nothing in bake/ reads it — the run is the production CLI with the numbers turned
    down, and this step (its source attached) says so in the report. Returns the env overrides
    for ``when_bake(..., env=)``."""
    shown_constants = ", ".join(f"{k} = {v:g}" for k, v in constants.items())
    with allure.step(f"Given: bake leash shrunk: {shown_constants} (tests-only sitecustomize)"):
        site = config.parent.parent / "leash"
        site.mkdir()
        source = "import bake.adapters as a\n" + "".join(f"a.{k} = {v!r}\n" for k, v in constants.items())
        (site / "sitecustomize.py").write_text(source, encoding="utf-8")
        allure.attach(source, name="sitecustomize.py (leash)",
                      attachment_type=allure.attachment_type.TEXT)
    return {"PYTHONPATH": str(site)}


def _bake_env(env: dict[str, str] | None) -> dict[str, str]:
    """The bake subprocess's environment: the test process's, the repo root first on PYTHONPATH,
    then the explicit ``env`` overrides — a PYTHONPATH among them is joined AFTER the repo root
    (it adds a path, it never hides the bake)."""
    overrides = dict(env or {})
    extra = overrides.pop("PYTHONPATH", None)
    path = os.pathsep.join(filter(None, [str(REPO), extra, os.environ.get("PYTHONPATH")]))
    return {**os.environ, **overrides, "PYTHONPATH": path}


def given_prior_bake(root: Path, config: Path, *flags: str, why: str,
                     env: dict[str, str] | None = None) -> str:
    """Given: an earlier bake already published ``<root>/out`` — an arrange step that dies loudly
    on failure (CONVENTIONS § The helper razor). Returns that run's data.json text."""
    out = root / "out"
    argv = ["-m", "bake", "--config", str(config), "--out", str(out),
            "--reference-date", FIXTURE_REFERENCE_DATE, *flags]
    shown_config = (config.relative_to(REPO) if REPO in config.parents else config.relative_to(root))
    step = (f"bake --config {shown_config.as_posix()} --out out --reference-date {FIXTURE_REFERENCE_DATE} "
            + " ".join(flags))
    with allure.step(f"Given: a prior bake published out/ ({why}): {step.strip()}"):
        proc = subprocess.run([sys.executable, *argv], cwd=root, env=_bake_env(env),
                              capture_output=True, text=True, timeout=BAKE_TIMEOUT_S)
        assert proc.returncode == 0, f"arrange: the prior bake failed:\n{proc.stderr}"
        raw = (out / "data.json").read_text(encoding="utf-8")
        allure.attach(raw, name="prior out/data.json", attachment_type=allure.attachment_type.JSON)
    return raw


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
    def raw(self) -> str:
        """out/data.json as the text the page's host serves (raises when the bake wrote none)."""
        return (self.out_dir / "data.json").read_text(encoding="utf-8")

    @property
    def artifact_files(self) -> list[str]:
        """The artifact files present in ``--out`` after the run (sorted names)."""
        return sorted(p.name for p in self.out_dir.glob("*")) if self.out_dir.is_dir() else []


def _neutral(text: str, root: Path) -> str:
    return text.replace(str(root.resolve()) + os.sep, "./").replace(str(root.resolve()), ".")


def when_bake(config: Path, *flags: str, reference_date: str | None = FIXTURE_REFERENCE_DATE,
              env: dict[str, str] | None = None) -> BakeRun:
    """When: the bake runs — ``python -m bake`` as a real subprocess, the action under test.

    cwd is the directory holding the world copy, so argv is relative (``alex/circles.yaml``,
    ``out``) and no host path reaches an attachment. When ``given_alex`` mutated this config, the
    step name repeats the mutation sentence, so the knob's value threads given → when → then. ``flags`` are extra CLI flags
    (``"--evaluate"``, ``"--stale-after-hours", "24"``); ``reference_date=None`` omits the flag.
    ``env`` holds explicit environment overrides for the bake subprocess (a host ``TZ``, a token
    the bake must not pass on, ``given_leash``'s PYTHONPATH) — the test process's own environment
    is never mutated."""
    root = config.parent.parent
    out = root / "out"
    argv = ["-m", "bake", "--config", config.relative_to(root).as_posix(), "--out", "out"]
    if reference_date is not None:
        argv += ["--reference-date", reference_date]
    argv += list(flags)
    shown_argv = "python " + " ".join(argv)
    mutation = _MUTATIONS.get(config)
    step = f"When: {shown_argv.removeprefix('python -m ')}" + (f" (world {WORLD}: {mutation})" if mutation else "")
    with allure.step(step):
        proc = subprocess.run([sys.executable, *argv], cwd=root, env=_bake_env(env),
                              capture_output=True, text=True, timeout=BAKE_TIMEOUT_S)
        stdout, stderr = _neutral(proc.stdout, root), _neutral(proc.stderr, root)
        allure.attach(f"$ {shown_argv}\n# cwd: the tmp dir holding the world copy\n",
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

def shown(value: Any) -> str:
    """A value as a step name shows it: strings quoted, lists/dicts as JSON, the rest str()."""
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "=": operator.eq,
    "!=": operator.ne,
    "contains": lambda actual, expected: expected in actual,
    "not contains": lambda actual, expected: expected not in actual,
    # the ordering ops a measured claim needs (browser geometry, sizes)
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
}


def verdict(claim: str, actual: Any, expected: Any, *, op: str = "=") -> None:
    """Then: ``<claim> <op> <expected>`` — one claim, one step; the assertion inside it makes the
    step itself red / green. The step name carries the CLAIMED value; the actual one is in the
    assertion message when it differs."""
    check = _OPS[op]
    with allure.step(f"Then: {claim} {op} {shown(expected)}"):
        assert check(actual, expected), f"{claim}: expected {op} {shown(expected)}, actual {shown(actual)}"


def warnings_for(run: BakeRun, ref: str) -> list[str]:
    """The artifact's build-warning messages naming ``ref`` (``[]`` when none or no artifact)."""
    return [w["message"] for w in (run.data or {}).get("warnings", []) if w.get("item") == ref]


def masked_digest(raw: str) -> str:
    """sha256 of a data.json text with its generated_at value masked — CIR-BAKE-DETERMINISM's
    "byte-identical except generated_at" made comparable as one short value."""
    masked = re.sub(r'"generated_at": "[^"]*"', '"generated_at": "<masked>"', raw)
    return hashlib.sha256(masked.encode("utf-8")).hexdigest()[:16]


def then_config_error(run: BakeRun, message: str) -> None:
    """The spec phrase "config error, bake fails" as its three claims (CIR-DATA-VALIDATION: a
    failed bake publishes nothing): exit code 1, stderr names ``message``, no artifact in --out."""
    verdict("exit code", run.exit_code, 1)
    verdict("stderr", run.stderr, message, op="contains")
    verdict("artifact files in out/", run.artifact_files, [])


def then_grey_by_failure(run: BakeRun, ref: str, *, cause: str | None = None,
                         guardrail: str | None = None, exact_detail: bool = False,
                         ships: bool = False) -> str:
    """The spec phrase "⚪ + build warning, reason by-failure" (CIR-DATA-FAILURE-IS-GREY) for
    ``ref`` as its claims, one verdict each:

    - ``ships``: the page still ships (exit code 0);
    - always: the light is grey / by-failure with no data date, and exactly one warning names
      the item;
    - ``cause``: that warning contains the cause;
    - the detail line carries that same reason (⚖-R51) — ``exact_detail`` claims the whole line,
      CIR-DATA-DETAIL-LINE's "guardrail · status · … · reason" with nothing between
      (``guardrail · unmonitored · <warning>``; no guardrail → the line starts at the status);
      otherwise the line contains the warning.

    Returns the warning text ("" when there is none — the count verdict has already gone red)."""
    if guardrail is not None and not exact_detail:
        raise TypeError("then_grey_by_failure: guardrail is only claimed by the exact detail line")
    if ships:
        verdict("exit code", run.exit_code, 0)
    it = item_of(run.data, ref)
    verdict(f"{ref} status, grey_reason, last_data_date",
            [it["status"], it["grey_reason"], it["last_data_date"]], ["grey", "by-failure", None])
    messages = warnings_for(run, ref)
    verdict(f"warnings naming {ref}", len(messages), 1)
    message = messages[0] if messages else ""
    if cause is not None:
        verdict(f"{ref} warning", message, cause, op="contains")
    if exact_detail:
        prefix = f"{guardrail} · unmonitored · " if guardrail else "unmonitored · "
        verdict(f"{ref} detail_line", it["detail_line"], prefix + message)
    else:
        verdict(f"{ref} detail_line", it["detail_line"], message or "<no warning>", op="contains")
    return message


def item_of(data: dict, ref: str) -> dict:
    """The item dict at ``<ring-id>/<item-id>`` in a baked artifact (KeyError when absent)."""
    ring_id, item_id = ref.split("/")
    for r in data["rings"]:
        if r["id"] == ring_id:
            for i in r["items"]:
                if i["id"] == item_id:
                    return i
    raise KeyError(f"artifact has no item {ref!r}")
