# Evidence for the resolution rules and the baked artifact — status resolution, grey reasons,
# the failure algebra, the detail line, data.json's shape/determinism/exposure, the adapter
# contract's observable half, the reference date, and the P0 phase.
#
# World: alex — every case starts from fixtures/alex (the spec pages' declared world:
# specs/data/status-resolution.md, specs/data/data-json.md "World: alex") and turns at most one
# knob; the knob and its value name the given step. The system boundary these rules are stated
# against is the bake CLI (`python -m bake`): its exit code, its stderr, and the artifact it
# writes (out/data.json + out/index.html). Each labelled case reads given (world + knob) → when
# (ONE bake run) → then (one verdict per claim) — tests/evidence_helpers.py, after
# allure-behavior-snippets CONVENTIONS § Prime rule of reporting. Each case cites its spec row as
# CIR-<AREA>-<NAME>#<row-id> (tests/rules.py `case_title`).
#
# Dated rows move the injected reference date (`--reference-date`), never the committed notes
# (CIR-PROC-TEST-FIXTURES): self/sleep's newest entry is 2026-08-01 (yellow_after 7, red_after
# 30), self/labs' is 2026-01-15 (yellow_after 100, red_after 190). Expected values come from the
# spec rows and the fixture's own comments, never from running the bake.
#
# The unlabelled tests at the end of each section are unit guards on internals the CLI cannot
# reach (an injected clock, a monkeypatched adapter, a pure predicate) — CONVENTIONS § Allure
# taxonomy: they run in the suite but are never evidence.

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import allure
import pytest

import bake.adapters as adapters_module
import bake.resolve as resolve_module
from bake.__main__ import default_reference_date
from bake.config import load_config
from bake.emit import write_artifact
from bake.resolve import resolve, window_status
from evidence_helpers import (
    FIXTURE_REFERENCE_DATE,
    REPO,
    BakeRun,
    given_alex,
    item,
    item_of,
    then_config_error,
    verdict,
    when_bake,
)
from rules import rule

FIXTURES = REPO / "fixtures"
ALEX_YAML = FIXTURES / "alex" / "circles.yaml"
# Unit guards inject these into resolve() directly (the CLI stamps the real clock instead).
UNIT_REFERENCE_DATE = date(2026, 8, 3)
UNIT_GENERATED_AT = datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc)
AlexCopy = Callable[..., Path]  # the `alex_copy` factory fixture (tests/conftest.py)

# The item fields of the artifact — specs/data/data-json.md CIR-BAKE-ARTIFACT field table.
ITEM_FIELDS = sorted(["id", "label", "status", "grey_reason", "guardrail", "note", "link", "share",
                      "last_data_date", "detail_line", "detail_page"])
# The top-level fields — the same table (version … warnings).
TOP_LEVEL_FIELDS = sorted(["version", "spec_version", "person", "generated_at", "reference_date",
                           "timezone", "stale_after_hours", "rings", "warnings"])
PROBE = "./notes/plants-probe.sh"
# The spec tables' lights → the artifact's wire words (data-json.md CIR-BAKE-STATUS-VALUES, ⚖-R19).
# A phase's bake = the one entry point plus that phase's flags (CIR-PROC-BAKE-ONE-PATH).
PHASE_FLAGS = {"P0 build-time": (), "P1 nightly": ("--evaluate",)}
WIRE = {"🟢": "green", "🟡": "yellow", "🔴": "red", "⚪": "grey"}


# ===========================================================================
# Local helpers — given (arrange) and then (observe) only; the when is always when_bake
# ===========================================================================

def _items(run: BakeRun) -> dict[str, dict]:
    """Every item of a baked artifact, keyed by its `<ring>/<item>` ref, in artifact order."""
    return {f"{r['id']}/{i['id']}": i for r in run.data["rings"] for i in r["items"]}


def _raw(run: BakeRun) -> str:
    """out/data.json as the bytes the page's host serves (text)."""
    return (run.out_dir / "data.json").read_text(encoding="utf-8")


def _item_warnings(run: BakeRun, ref: str) -> list[str]:
    """The artifact's warning messages for one item ref."""
    return [w["message"] for w in run.data["warnings"] if w["item"] == ref]


def _masked_digest(raw: str) -> str:
    """sha256 of a data.json text with its generated_at value masked — CIR-BAKE-DETERMINISM's
    "byte-identical except generated_at" made comparable as one short value."""
    masked = re.sub(r'"generated_at": "[^"]*"', '"generated_at": "<masked>"', raw)
    return hashlib.sha256(masked.encode("utf-8")).hexdigest()[:16]


def _copy_then(alex_copy: AlexCopy, fn: Callable[[Path], None]) -> Callable[[], Path]:
    """An ``alex_copy`` that also applies a FILE-level knob (a script, a mode bit) to the copy, so
    given_alex performs it inside its given step."""
    def make() -> Path:
        config = alex_copy()
        fn(config.parent)
        return config
    return make


def given_plants_runs(alex_copy: AlexCopy, what: str, body: str) -> Path:
    """Given: world alex whose wider/plants `command:` runs a real /bin/sh probe script.

    ``what`` names the probe's behaviour (the step name threads it); ``body`` is the script."""
    def write_probe(world: Path) -> None:
        script = world / "notes" / "plants-probe.sh"
        script.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        script.chmod(0o755)
        allure.attach("#!/bin/sh\n" + body, name=f"notes/plants-probe.sh ({what})",
                      attachment_type=allure.attachment_type.TEXT)
    return given_alex(_copy_then(alex_copy, write_probe), f"wider/plants command: [{PROBE}] — {what}",
                      lambda c: item(c, "wider/plants").update(status={"command": [PROBE]}))


def given_prior_bake(root: Path, config: Path, *flags: str, why: str,
                     env: dict[str, str] | None = None) -> str:
    """Given: an earlier bake already published ``<root>/out`` — an arrange step that dies loudly
    on failure (CONVENTIONS § The helper razor). Returns that run's data.json text."""
    out = root / "out"
    argv = ["-m", "bake", "--config", str(config), "--out", str(out),
            "--reference-date", FIXTURE_REFERENCE_DATE, *flags]
    shown_config = (config.relative_to(REPO) if REPO in config.parents else config.relative_to(root))
    shown = f"bake --config {shown_config.as_posix()} --out out --reference-date {FIXTURE_REFERENCE_DATE} " + " ".join(flags)
    run_env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [str(REPO), os.environ.get("PYTHONPATH")])))
    run_env.update(env or {})
    with allure.step(f"Given: a prior bake published out/ ({why}): {shown.strip()}"):
        proc = subprocess.run([sys.executable, *argv], cwd=root, env=run_env,
                              capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"arrange: the prior bake failed:\n{proc.stderr}"
        raw = (out / "data.json").read_text(encoding="utf-8")
        allure.attach(raw, name="prior out/data.json", attachment_type=allure.attachment_type.JSON)
    return raw


def then_grey_by_failure(run: BakeRun, ref: str, cause: str) -> None:
    """The spec phrase "⚪ + build warning, reason by-failure" (CIR-DATA-FAILURE-IS-GREY) as its
    claims: the page still ships, the light is grey/by-failure with no data date, exactly one
    warning names the item and the cause, and the detail line carries that same reason (⚖-R51)."""
    verdict("exit code", run.exit_code, 0)
    it = item_of(run.data, ref)
    verdict(f"{ref} status, grey_reason, last_data_date", [it["status"], it["grey_reason"], it["last_data_date"]],
            ["grey", "by-failure", None])
    messages = _item_warnings(run, ref)
    verdict(f"{ref} warning count", len(messages), 1)
    verdict(f"{ref} warning", messages[0] if messages else "", cause, op="contains")
    verdict(f"{ref} detail_line", it["detail_line"], messages[0] if messages else "<no warning>",
            op="contains")


# ===========================================================================
# CIR-DATA-STATUS-RESOLUTION — the canonical table
# ===========================================================================

class TestDataStatusResolution:
    """CIR-DATA-STATUS-RESOLUTION — the canonical table."""

    @rule("CIR-DATA-STATUS-RESOLUTION")
    def test_no_adapter_declared(self, alex_copy) -> None:
        """CIR-DATA-STATUS-RESOLUTION#no-adapter-declared — self/exercise has no status: →
        ⚪ unmonitored, reason by-choice."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        exercise = item_of(run.data, "self/exercise")
        verdict("self/exercise status, grey_reason", [exercise["status"], exercise["grey_reason"]],
                ["grey", "by-choice"])

    @rule("CIR-DATA-STATUS-RESOLUTION")
    @pytest.mark.parametrize("ref,light", [
        pytest.param("children/nova", "green", id="CIR-DATA-STATUS-RESOLUTION#manual-green"),
        pytest.param("partner/date-night", "yellow", id="CIR-DATA-STATUS-RESOLUTION#manual-yellow"),
        pytest.param("wider/friends", "red", id="CIR-DATA-STATUS-RESOLUTION#manual-red"),
    ])
    def test_manual_light(self, alex_copy, ref: str, light: str) -> None:
        """CIR-DATA-STATUS-RESOLUTION — `manual: <light>` resolves to that light, no grey reason.
        alex's children/nova is manual: green, partner/date-night yellow, wider/friends red."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        it = item_of(run.data, ref)
        verdict(f"{ref} status, grey_reason", [it["status"], it["grey_reason"]], [light, None])

    # self/sleep (newest 2026-08-01, yellow_after 7, red_after 30), adapter ON, the reference
    # date moved so the newest entry lands at the row's age.

    @rule("CIR-DATA-STATUS-RESOLUTION")
    def test_freshness_inside_window(self, alex_copy) -> None:
        """CIR-DATA-STATUS-RESOLUTION#freshness-inside-window — newest date 3d old (reference
        2026-08-04 vs 2026-08-01), yellow_after 7, red_after 30 → 🟢."""
        run = when_bake(given_alex(alex_copy), "--evaluate", reference_date="2026-08-04")
        verdict("exit code", run.exit_code, 0)
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep status, grey_reason", [sleep["status"], sleep["grey_reason"]], ["green", None])
        verdict("self/sleep last_data_date", sleep["last_data_date"], "2026-08-01")

    @rule("CIR-DATA-STATUS-RESOLUTION")
    def test_freshness_stale(self, alex_copy) -> None:
        """CIR-DATA-STATUS-RESOLUTION#freshness-stale — newest date 10d old (reference
        2026-08-11), yellow_after 7, red_after 30 → 🟡."""
        run = when_bake(given_alex(alex_copy), "--evaluate", reference_date="2026-08-11")
        verdict("exit code", run.exit_code, 0)
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep status, grey_reason", [sleep["status"], sleep["grey_reason"]], ["yellow", None])
        verdict("self/sleep detail_line", sleep["detail_line"], "attention · last data 2026-08-01", op="contains")

    @rule("CIR-DATA-STATUS-RESOLUTION")
    def test_freshness_very_stale(self, alex_copy) -> None:
        """CIR-DATA-STATUS-RESOLUTION#freshness-very-stale — newest date 45d old (reference
        2026-09-15: 30 + 15), yellow_after 7, red_after 30 → 🔴."""
        run = when_bake(given_alex(alex_copy), "--evaluate", reference_date="2026-09-15")
        verdict("exit code", run.exit_code, 0)
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep status, grey_reason", [sleep["status"], sleep["grey_reason"]], ["red", None])
        verdict("self/sleep detail_line", sleep["detail_line"], "act · last data 2026-08-01", op="contains")

    @rule("CIR-DATA-STATUS-RESOLUTION")
    def test_freshness_source_missing(self, alex_copy) -> None:
        """CIR-DATA-STATUS-RESOLUTION#freshness-source-missing — source: matches no file → ⚪ +
        build warning, reason by-failure."""
        config = given_alex(alex_copy, "self/sleep source: notes/absent.md",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(source="notes/absent.md"))
        then_grey_by_failure(when_bake(config, "--evaluate"), "self/sleep", "missing source")

    @rule("CIR-DATA-STATUS-RESOLUTION")
    def test_freshness_source_no_dates(self, alex_copy) -> None:
        """CIR-DATA-STATUS-RESOLUTION#freshness-source-no-dates — source file exists
        (notes/empty-log.md), zero parseable dates → ⚪ + build warning."""
        config = given_alex(alex_copy, "self/sleep source: notes/empty-log.md",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(source="notes/empty-log.md"))
        then_grey_by_failure(when_bake(config, "--evaluate"), "self/sleep", "no dates found")

    @rule("CIR-DATA-STATUS-RESOLUTION")
    def test_freshness_all_dates_future(self, alex_copy) -> None:
        """CIR-DATA-STATUS-RESOLUTION#freshness-all-dates-future — every parseable date is after
        the reference date → ⚪ + build warning (⚖-R8). Reference 2026-07-29: the sleep-log's
        07-30, 07-31 and 08-01 are all ahead of it."""
        run = when_bake(given_alex(alex_copy), "--evaluate", reference_date="2026-07-29")
        then_grey_by_failure(run, "self/sleep", "after the reference date")

    @rule("CIR-DATA-STATUS-RESOLUTION")
    def test_adapter_not_evaluated_this_phase(self, alex_copy) -> None:
        """CIR-DATA-STATUS-RESOLUTION#adapter-not-evaluated-this-phase — `command:` (and
        `freshness:`) under a P0 bake (no --evaluate) → ⚪ + warning "adapter not evaluated in
        this build", reason not-evaluated (⚖-R2, ⚖-R50)."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        items = _items(run)
        refs = ("self/sleep", "self/labs", "wider/plants")
        verdict("self/sleep, self/labs, wider/plants status + grey_reason",
                {ref: [items[ref]["status"], items[ref]["grey_reason"]] for ref in refs},
                {ref: ["grey", "not-evaluated"] for ref in refs})
        verdict("their warnings", {ref: _item_warnings(run, ref) for ref in refs},
                {ref: ["adapter not evaluated in this build"] for ref in refs})

    # The table's five config-error rows. The shared claim is the asymmetry the spec calls out: a
    # bad *config* fails the bake outright (nothing published), rather than degrading to ⚪ the
    # way a bad *command* does. Each is self/sleep's status: block replaced.
    @rule("CIR-DATA-STATUS-RESOLUTION")
    @pytest.mark.parametrize("status,message", [
        pytest.param({"manual": "green",
                      "freshness": {"source": "notes/sleep-log.md", "yellow_after": 7, "red_after": 30}},
                     "multiple adapter keys", id="CIR-DATA-STATUS-RESOLUTION#two-adapters-on-one-item"),
        pytest.param({}, "empty status block", id="CIR-DATA-STATUS-RESOLUTION#empty-status-block"),
        pytest.param({"manual": "amber"}, "not a valid manual value",
                     id="CIR-DATA-STATUS-RESOLUTION#manual-unknown-word"),
        pytest.param({"manual": "grey"}, "grey", id="CIR-DATA-STATUS-RESOLUTION#manual-declares-grey"),
        pytest.param({"sqlite": {"query": "SELECT 1"}}, "unknown adapter",
                     id="CIR-DATA-STATUS-RESOLUTION#unknown-adapter-key"),
    ])
    def test_config_error_fails_the_bake(self, alex_copy, status: dict, message: str) -> None:
        """CIR-DATA-STATUS-RESOLUTION — a config error fails the bake and publishes nothing; it
        never degrades to ⚪. The message locates the offending item (sleep)."""
        config = given_alex(alex_copy, f"self/sleep status: {status!r}",
                            lambda c: item(c, "self/sleep").update(status=status))
        run = when_bake(config)
        then_config_error(run, message)
        verdict("stderr", run.stderr, "sleep", op="contains")


# ===========================================================================
# CIR-DATA-GREY-REASON — one grey light, three reasons
# ===========================================================================

class TestDataGreyReason:
    """CIR-DATA-GREY-REASON — one grey light, three reasons."""

    @rule("CIR-DATA-GREY-REASON")
    def test_unmonitored_by_choice(self, alex_copy) -> None:
        """CIR-DATA-GREY-REASON#unmonitored-by-choice — self/exercise has no status: block and no
        note: → reason by-choice; detail line "unmonitored"."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        exercise = item_of(run.data, "self/exercise")
        verdict("self/exercise status, grey_reason", [exercise["status"], exercise["grey_reason"]],
                ["grey", "by-choice"])
        verdict("self/exercise detail_line", exercise["detail_line"], "unmonitored")

    @rule("CIR-DATA-GREY-REASON")
    def test_unmonitored_not_evaluated(self, alex_copy) -> None:
        """CIR-DATA-GREY-REASON#unmonitored-not-evaluated — freshness: (self/sleep) and command:
        (wider/plants) under a P0 bake → reason not-evaluated; detail line "unmonitored · not
        evaluated in this build" (plants has no guardrail, so the line is exactly that)."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        sleep, plants = item_of(run.data, "self/sleep"), item_of(run.data, "wider/plants")
        verdict("self/sleep status, grey_reason", [sleep["status"], sleep["grey_reason"]],
                ["grey", "not-evaluated"])
        verdict("wider/plants status, grey_reason", [plants["status"], plants["grey_reason"]],
                ["grey", "not-evaluated"])
        verdict("wider/plants detail_line", plants["detail_line"], "unmonitored · not evaluated in this build")
        verdict("self/sleep detail_line", sleep["detail_line"], "unmonitored · not evaluated in this build",
                op="contains")


# ===========================================================================
# CIR-DATA-FAILURE-IS-GREY — the failure algebra
# ===========================================================================

class TestDataFailureIsGrey:
    """CIR-DATA-FAILURE-IS-GREY — the failure algebra."""

    @rule("CIR-DATA-FAILURE-IS-GREY")
    def test_failure_never_red(self, alex_copy) -> None:
        """CIR-DATA-FAILURE-IS-GREY#failure-never-red — the plants command prints `red` and then
        exits 3: a failure, so ⚪ + warning — the printed red is never taken."""
        config = given_plants_runs(alex_copy, "prints red, exits 3", "echo red\nexit 3\n")
        run = when_bake(config, "--evaluate")
        then_grey_by_failure(run, "wider/plants", "3")
        verdict("grey items without a grey_reason",
                [ref for ref, i in _items(run).items() if i["status"] == "grey" and i["grey_reason"] is None], [])

    @rule("CIR-DATA-FAILURE-IS-GREY")
    def test_failure_never_green(self, alex_copy) -> None:
        """CIR-DATA-FAILURE-IS-GREY#failure-never-green — the plants command prints `green` and
        then exits 3: a failure, so ⚪ + warning — the printed green is never taken."""
        config = given_plants_runs(alex_copy, "prints green, exits 3", "echo green\nexit 3\n")
        then_grey_by_failure(when_bake(config, "--evaluate"), "wider/plants", "3")

    @rule("CIR-DATA-FAILURE-IS-GREY")
    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads mode-000 files")
    def test_unreadable_source_is_grey(self, alex_copy) -> None:
        """CIR-DATA-FAILURE-IS-GREY#unreadable-source-is-grey — source exists, permission denied
        → ⚪ + warning; never 🔴, never 🟢."""
        note: list[Path] = []

        def unreadable(world: Path) -> None:
            note.append(world / "notes" / "sleep-log.md")
            note[0].chmod(0o000)
        config = given_alex(_copy_then(alex_copy, unreadable), "notes/sleep-log.md mode 000 (config unchanged)",
                            lambda c: None)
        try:
            run = when_bake(config, "--evaluate")
        finally:
            note[0].chmod(0o644)
        then_grey_by_failure(run, "self/sleep", "unreadable source")
        verdict("self/sleep warning", _item_warnings(run, "self/sleep")[0], "notes/sleep-log.md", op="contains")

    @rule("CIR-DATA-FAILURE-IS-GREY")
    def test_warning_names_item(self, alex_copy) -> None:
        """CIR-DATA-FAILURE-IS-GREY#warning-names-item — the `plants` command exits 3 → the
        warning identifies cell `wider/plants` and the exit code; the light is ⚪."""
        config = given_plants_runs(alex_copy, "prints green, exits 3", "echo green\nexit 3\n")
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        plants = item_of(run.data, "wider/plants")
        verdict("wider/plants status, grey_reason", [plants["status"], plants["grey_reason"]], ["grey", "by-failure"])
        verdict("warnings", run.warnings, "wider/plants: command exited", op="contains")
        verdict("wider/plants warning", " | ".join(_item_warnings(run, "wider/plants")), "3", op="contains")


# ===========================================================================
# CIR-DATA-NO-AGGREGATION — no roll-up, ever
# ===========================================================================

class TestDataNoAggregation:
    """CIR-DATA-NO-AGGREGATION — no roll-up, ever."""

    @rule("CIR-DATA-NO-AGGREGATION")
    def test_inner_red_outer_untouched(self, alex_copy) -> None:
        """CIR-DATA-NO-AGGREGATION#inner-red-outer-untouched — self/sleep 🔴 (manual: red),
        partner/date-night 🟡 → the outer cells keep their own resolved colours (alex's manual
        lights: date-night yellow, nova/kit green, friends red)."""
        config = given_alex(alex_copy, "self/sleep status: manual: red",
                            lambda c: item(c, "self/sleep").update(status={"manual": "red"}))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        items = _items(run)
        verdict("self/sleep status", items["self/sleep"]["status"], "red")
        verdict("outer manual lights",
                {ref: items[ref]["status"] for ref in ("partner/date-night", "children/nova",
                                                       "children/kit", "wider/friends")},
                {"partner/date-night": "yellow", "children/nova": "green", "children/kit": "green",
                 "wider/friends": "red"})

    @rule("CIR-DATA-NO-AGGREGATION")
    def test_centre_carries_no_status(self, alex_copy) -> None:
        """CIR-DATA-NO-AGGREGATION#centre-carries-no-status — the artifact carries no light above
        the item: the top level is exactly data-json.md's field table (no status / aggregate /
        score), and a ring is id + label + items."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        verdict("top-level keys", sorted(run.data), TOP_LEVEL_FIELDS)
        verdict("ring keys", sorted({k for r in run.data["rings"] for k in r}), ["id", "items", "label"])


# ===========================================================================
# CIR-DATA-RESOLUTION-TIME — statuses resolve at bake time only
# ===========================================================================

class TestDataResolutionTime:
    """CIR-DATA-RESOLUTION-TIME — statuses resolve at bake time only."""

    @rule("CIR-DATA-RESOLUTION-TIME")
    def test_p0_manual_roundtrip(self, alex_copy) -> None:
        """CIR-DATA-RESOLUTION-TIME#p0-manual-roundtrip — a P0 bake: alex's manual statuses pass
        through unchanged into the artifact."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        items = _items(run)
        verdict("manual lights", {ref: items[ref]["status"] for ref in
                                  ("children/nova", "children/kit", "partner/date-night", "wider/friends")},
                {"children/nova": "green", "children/kit": "green", "partner/date-night": "yellow",
                 "wider/friends": "red"})

    @rule("CIR-DATA-RESOLUTION-TIME")
    def test_one_reference_date_per_bake(self, alex_copy) -> None:
        """CIR-DATA-RESOLUTION-TIME#one-reference-date-per-bake — two freshness items (self/sleep,
        self/labs) in one evaluated bake both age against 2026-08-03: sleep age 2 ≤ 7 → 🟢, labs
        age 200 > 190 → 🔴 (the fixture's comments)."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("reference_date", run.data["reference_date"], "2026-08-03")
        items = _items(run)
        verdict("self/sleep, self/labs status + last_data_date",
                {ref: [items[ref]["status"], items[ref]["last_data_date"]] for ref in ("self/sleep", "self/labs")},
                {"self/sleep": ["green", "2026-08-01"], "self/labs": ["red", "2026-01-15"]})


def test_page_never_reevaluates_unit() -> None:
    """Unit guard (was CIR-DATA-RESOLUTION-TIME#page-never-reevaluates — a page-load claim the
    bake CLI cannot observe; the browser tier owns it): resolve() freezes a status into the dict."""
    artifact = resolve(load_config(ALEX_YAML), reference_date=UNIT_REFERENCE_DATE,
                       generated_at=UNIT_GENERATED_AT)
    assert artifact["rings"][0]["items"][0]["status"] is not None


# ===========================================================================
# CIR-DATA-DETAIL-LINE — what hover shows
# ===========================================================================

class TestDataDetailLine:
    """CIR-DATA-DETAIL-LINE — what hover shows."""

    @rule("CIR-DATA-DETAIL-LINE")
    def test_full_detail_line(self, alex_copy) -> None:
        """CIR-DATA-DETAIL-LINE#full-detail-line — guardrail + freshness adapter with a date →
        "guardrail · status · last data YYYY-MM-DD": self/sleep evaluated at 2026-08-03 reads
        "Lights out by 23:00 on weeknights · ok · last data 2026-08-01" (data-json.md's example).
        A manual item with a guardrail (partner/date-night) has no date segment."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("self/sleep detail_line", item_of(run.data, "self/sleep")["detail_line"],
                "Lights out by 23:00 on weeknights · ok · last data 2026-08-01")
        verdict("partner/date-night detail_line", item_of(run.data, "partner/date-night")["detail_line"],
                "Protected evening, twice a month · attention")

    @rule("CIR-DATA-DETAIL-LINE")
    def test_no_guardrail(self, alex_copy) -> None:
        """CIR-DATA-DETAIL-LINE#no-guardrail — children/nova has no guardrail → the line starts at
        the status: exactly "ok"."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        nova = item_of(run.data, "children/nova")
        verdict("children/nova guardrail", nova["guardrail"], None)
        verdict("children/nova detail_line", nova["detail_line"], "ok")

    @rule("CIR-DATA-DETAIL-LINE")
    def test_manual_item_has_no_data_date(self, alex_copy) -> None:
        """CIR-DATA-DETAIL-LINE#manual-item-has-no-data-date — children/nova is `manual: green` →
        no date field, no "last data" segment."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        nova = item_of(run.data, "children/nova")
        verdict("children/nova last_data_date", nova["last_data_date"], None)
        verdict("children/nova detail_line", nova["detail_line"], "last data", op="not contains")

    @rule("CIR-DATA-DETAIL-LINE")
    def test_detail_line_is_plain_text(self, alex_copy) -> None:
        """CIR-DATA-DETAIL-LINE#detail-line-is-plain-text — any item: a plain string, no markup."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("items whose detail_line is not a string or carries '<'",
                [ref for ref, i in _items(run).items()
                 if not isinstance(i["detail_line"], str) or "<" in i["detail_line"]], [])


# ===========================================================================
# CIR-BAKE-ARTIFACT — what a bake produces
# ===========================================================================

class TestBakeArtifact:
    """CIR-BAKE-ARTIFACT — what a bake produces."""

    @rule("CIR-BAKE-ARTIFACT")
    def test_artifact_fixture_roundtrip(self, alex_copy) -> None:
        """CIR-BAKE-ARTIFACT#artifact-fixture-roundtrip — bake over fixtures/alex/circles.yaml:
        rings/items keep config order and ids; self/exercise is grey/by-choice, share 1, nulls
        for its absent fields; the top-level fields are data-json.md's example values."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        verdict("artifact files in out/", run.artifact_files, ["data.json", "index.html"])
        d = run.data
        verdict("version, spec_version, person, reference_date, timezone, stale_after_hours",
                [d["version"], d["spec_version"], d["person"], d["reference_date"], d["timezone"],
                 d["stale_after_hours"]],
                [1, 0, "Alex Example", "2026-08-03", "UTC", None])
        verdict("generated_at is RFC 3339 UTC (YYYY-MM-DDTHH:MM:SSZ)",
                bool(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", d["generated_at"])), True)
        verdict("items per ring", {r["id"]: [i["id"] for i in r["items"]] for r in d["rings"]}, {
            "self": ["sleep", "labs", "exercise"], "partner": ["date-night"],
            "children": ["nova", "kit"], "wider": ["friends", "plants"],
        })
        exercise = item_of(d, "self/exercise")
        verdict("self/exercise status, grey_reason, share, guardrail, note, link",
                [exercise[k] for k in ("status", "grey_reason", "share", "guardrail", "note", "link")],
                ["grey", "by-choice", 1, None, None, None])

    @rule("CIR-BAKE-ARTIFACT")
    def test_warnings_empty_array(self, alex_copy) -> None:
        """CIR-BAKE-ARTIFACT#warnings-empty-array — a fully healthy bake carries `warnings: []`.
        alex made healthy (the circles-zero-warnings.yaml variant): every monitored item manual
        (nothing unevaluated at P0); nova/kit already both declare share:; exercise's ⚪ by-choice
        is not a warning (CIR-DATA-STATUS-RESOLUTION#no-adapter-declared)."""
        def healthy(c):
            item(c, "self/sleep").update(status={"manual": "green"})
            item(c, "self/labs").update(status={"manual": "red"})
            item(c, "wider/plants").update(status={"manual": "yellow"})
        config = given_alex(alex_copy, "self/sleep, self/labs, wider/plants status: manual (green, red, yellow)",
                            healthy)
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("warnings key present", "warnings" in run.data, True)
        verdict("warnings", run.data["warnings"], [])


# ===========================================================================
# CIR-BAKE-STATUS-VALUES — wire values are not display words
# ===========================================================================

class TestBakeStatusValues:
    """CIR-BAKE-STATUS-VALUES — wire values are not display words. Each case bakes alex with the
    adapters ON, so every road to a light (manual, freshness, command, none) is in the artifact."""

    @rule("CIR-BAKE-STATUS-VALUES")
    def test_status_wire_vocabulary(self, alex_copy) -> None:
        """CIR-BAKE-STATUS-VALUES#status-wire-vocabulary — status is one of green|yellow|red|grey."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("statuses outside green|yellow|red|grey",
                {ref: i["status"] for ref, i in _items(run).items()
                 if i["status"] not in ("green", "yellow", "red", "grey")}, {})

    @rule("CIR-BAKE-STATUS-VALUES")
    def test_status_never_emoji(self, alex_copy) -> None:
        """CIR-BAKE-STATUS-VALUES#status-never-emoji — never 🟢🟡🔴⚪ anywhere in data.json."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        raw = _raw(run)
        verdict("light emoji in data.json", [e for e in ("🟢", "🟡", "🔴", "⚪") if e in raw], [])

    @rule("CIR-BAKE-STATUS-VALUES")
    def test_status_never_display_words(self, alex_copy) -> None:
        """CIR-BAKE-STATUS-VALUES#status-never-display-words — never ok/attention/act/unmonitored
        as a status value."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("statuses that are display words",
                {ref: i["status"] for ref, i in _items(run).items()
                 if i["status"] in ("ok", "attention", "act", "unmonitored")}, {})


# ===========================================================================
# CIR-BAKE-VERSION — artifact versioning
# ===========================================================================

class TestBakeVersion:
    """CIR-BAKE-VERSION — artifact versioning."""

    @rule("CIR-BAKE-VERSION")
    def test_version_recognized(self, alex_copy) -> None:
        """CIR-BAKE-VERSION#version-recognized — the bake's half of the row: it writes `version: 1`
        and the page beside it (that the page renders it is the browser tier's half)."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        verdict("version", run.data["version"], 1)
        verdict("artifact files in out/", run.artifact_files, ["data.json", "index.html"])


# ===========================================================================
# CIR-BAKE-GENERATED-AT — the honesty stamp (spec: no rows; unit guard only)
# ===========================================================================

def test_generated_at_present_unit() -> None:
    """Unit guard: generated_at is present and is an RFC 3339 UTC timestamp."""
    artifact = resolve(load_config(ALEX_YAML), reference_date=UNIT_REFERENCE_DATE,
                       generated_at=UNIT_GENERATED_AT)
    assert "generated_at" in artifact
    assert artifact["generated_at"].endswith("Z")
    assert "T" in artifact["generated_at"]


# ===========================================================================
# CIR-BAKE-STALE-SELF — the page's own freshness (the bake's half: the field)
# ===========================================================================

class TestBakeStaleSelf:
    """CIR-BAKE-STALE-SELF — the bake writes the threshold the page reads."""

    @rule("CIR-BAKE-STALE-SELF")
    def test_no_threshold_no_banner(self, alex_copy) -> None:
        """CIR-BAKE-STALE-SELF#no-threshold-no-banner — the bake's half of the row: a P0 bake (no
        --stale-after-hours) writes `stale_after_hours: null` (the banner half is the browser
        tier's)."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        verdict("stale_after_hours", run.data["stale_after_hours"], None)

    # No spec row states the flag itself (`--stale-after-hours N` → the field; bad N rejected):
    # these are unlabelled CLI guards, not evidence.

    def test_declared_cadence_lands_in_the_field(self, alex_copy) -> None:
        """--stale-after-hours 36 (the nightly bake's cadence) lands as integer 36."""
        run = when_bake(given_alex(alex_copy), "--evaluate", "--stale-after-hours", "36")
        verdict("exit code", run.exit_code, 0)
        verdict("stale_after_hours", run.data["stale_after_hours"], 36)

    @pytest.mark.parametrize("bad", [
        pytest.param("0", id="zero hours"),
        pytest.param("-1", id="negative hours"),
        pytest.param("1.5", id="fractional hours"),
        pytest.param("abc", id="not a number"),
    ])
    def test_bad_cadence_rejected(self, alex_copy, bad: str) -> None:
        """A non-positive or non-integer N fails the bake and publishes nothing."""
        run = when_bake(given_alex(alex_copy), f"--stale-after-hours={bad}")
        verdict("exit code is non-zero", run.exit_code != 0, True)
        verdict("stderr", run.stderr, "stale-after-hours", op="contains")
        verdict("artifact files in out/", run.artifact_files, [])


# ===========================================================================
# CIR-BAKE-WARNINGS — where build warnings surface
# ===========================================================================

class TestBakeWarnings:
    """CIR-BAKE-WARNINGS — where build warnings surface."""

    @rule("CIR-BAKE-WARNINGS")
    def test_warning_carries_cell_ref(self, alex_copy) -> None:
        """CIR-BAKE-WARNINGS#warning-carries-cell-ref — the plants command exits 1 →
        `{"item": "wider/plants", …}`."""
        config = given_plants_runs(alex_copy, "exits 1", "exit 1\n")
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("warning item refs", [w["item"] for w in run.data["warnings"]], "wider/plants", op="contains")

    @rule("CIR-BAKE-WARNINGS")
    def test_config_level_warning_has_null_item(self, alex_copy) -> None:
        """CIR-BAKE-WARNINGS#config-level-warning-has-null-item — an unknown top-level key →
        a warning `{"item": null, …}` naming the key."""
        config = given_alex(alex_copy, "top-level colour_scheme: dark (an unknown key)",
                            lambda c: c.update(colour_scheme="dark"))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("warnings", run.warnings, "-: unknown top-level key 'colour_scheme'", op="contains")
        verdict("every warning has item + message keys",
                all({"item", "message"} <= set(w) for w in run.data["warnings"]), True)


# ===========================================================================
# CIR-BAKE-DETAIL-FIELDS — structured fields and one composed line
# ===========================================================================

class TestBakeDetailFields:
    """CIR-BAKE-DETAIL-FIELDS — structured fields and one composed line."""

    @rule("CIR-BAKE-DETAIL-FIELDS")
    def test_detail_line_is_baked(self, alex_copy) -> None:
        """CIR-BAKE-DETAIL-FIELDS#detail-line-is-baked — every item carries a non-empty
        detail_line string."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("items without a non-empty detail_line string",
                [ref for ref, i in _items(run).items()
                 if not isinstance(i.get("detail_line"), str) or not i["detail_line"]], [])

    @rule("CIR-BAKE-DETAIL-FIELDS")
    def test_structured_fields_also_present(self, alex_copy) -> None:
        """CIR-BAKE-DETAIL-FIELDS#structured-fields-also-present — guardrail, status,
        last_data_date, note, grey_reason are individually present on every item."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        fields = ("guardrail", "status", "last_data_date", "note", "grey_reason")
        verdict("items missing a structured field",
                {ref: [f for f in fields if f not in i] for ref, i in _items(run).items()
                 if any(f not in i for f in fields)}, {})


# ===========================================================================
# CIR-ADAPT-CONTRACT — one adapter, one answer (the observable half)
# ===========================================================================

class TestAdaptContract:
    """CIR-ADAPT-CONTRACT — one adapter, one answer."""

    @rule("CIR-ADAPT-CONTRACT")
    def test_adapter_resolves_one_item(self, alex_copy) -> None:
        """CIR-ADAPT-CONTRACT#adapter-resolves-one-item — one `status:` block → exactly one status:
        alex's 8 config items bake to 8 artifact items, each with one status word."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        items = _items(run)
        verdict("artifact item count", len(items), 8)
        verdict("items without exactly one status word",
                [ref for ref, i in items.items() if i["status"] not in ("green", "yellow", "red", "grey")], [])

    @rule("CIR-ADAPT-CONTRACT")
    def test_adapter_never_reads_the_clock(self, alex_copy) -> None:
        """CIR-ADAPT-CONTRACT#adapter-never-reads-the-clock — the freshness adapter ages self/sleep
        against the injected 2026-08-04 (age 3 ≤ 7 → 🟢). Against the running day's calendar
        (any day after 2026-08-31) it would be 🔴 — the light shows which clock was read."""
        run = when_bake(given_alex(alex_copy), "--evaluate", reference_date="2026-08-04")
        verdict("exit code", run.exit_code, 0)
        verdict("reference_date", run.data["reference_date"], "2026-08-04")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep status, last_data_date", [sleep["status"], sleep["last_data_date"]],
                ["green", "2026-08-01"])

    @rule("CIR-ADAPT-CONTRACT")
    def test_adapter_unknown_name_is_config_error(self, alex_copy) -> None:
        """CIR-ADAPT-CONTRACT#adapter-unknown-name — status: {prometheus: …} on a build without it
        → config error."""
        config = given_alex(alex_copy, "self/exercise status: prometheus: {query: up}",
                            lambda c: item(c, "self/exercise").update(status={"prometheus": {"query": "up"}}))
        then_config_error(when_bake(config), "unknown adapter")

    @rule("CIR-ADAPT-CONTRACT")
    @pytest.mark.parametrize("word", [
        pytest.param("green", id="an adapter answering green is green, not grey"),
        pytest.param("yellow", id="an adapter answering yellow is yellow, not grey"),
        pytest.param("red", id="an adapter answering red is red, not grey"),
    ])
    def test_adapter_answer_is_never_grey(self, alex_copy, word: str) -> None:
        """CIR-ADAPT-CONTRACT#adapter-cannot-return-grey — every answer an adapter can give
        resolves to that non-grey light, with no grey reason (⚪ only from absence or failure)."""
        config = given_alex(alex_copy, f"children/nova status: manual: {word}",
                            lambda c: item(c, "children/nova").update(status={"manual": word}))
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        nova = item_of(run.data, "children/nova")
        verdict("children/nova status, grey_reason", [nova["status"], nova["grey_reason"]], [word, None])

    @rule("CIR-ADAPT-CONTRACT")
    def test_adapter_cannot_declare_grey(self, alex_copy) -> None:
        """CIR-ADAPT-CONTRACT#adapter-cannot-return-grey — grey is not expressible as an answer:
        the one adapter that states a light outright (manual: grey) is a config error."""
        config = given_alex(alex_copy, "children/nova status: manual: grey",
                            lambda c: item(c, "children/nova").update(status={"manual": "grey"}))
        then_config_error(when_bake(config), "grey")

    # Unlabelled (seat ruling 2026-10-16): the row's input is an adapter RAISING; a command exiting
    # 3 is a different input (that is CIR-DATA-FAILURE-IS-GREY). Kept as a boundary guard.
    def test_adapter_failure_is_isolated(self, alex_copy) -> None:
        """CIR-ADAPT-CONTRACT#adapter-failure-is-isolated — one of alex's adapters fails (the plants
        command exits 3): that item is ⚪ + warning; every other item resolves exactly as alex
        does at 2026-08-03 (sleep 🟢, labs 🔴, exercise ⚪ by-choice, the manual lights). The
        row's "raises an unexpected exception" input is not reachable through the CLI — the
        unit guard below drives it."""
        config = given_plants_runs(alex_copy, "exits 3", "exit 3\n")
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        items = _items(run)
        verdict("wider/plants status, grey_reason",
                [items["wider/plants"]["status"], items["wider/plants"]["grey_reason"]], ["grey", "by-failure"])
        verdict("wider/plants warning", " | ".join(_item_warnings(run, "wider/plants")), "3", op="contains")
        verdict("the other seven lights", {ref: items[ref]["status"] for ref in items if ref != "wider/plants"}, {
            "self/sleep": "green", "self/labs": "red", "self/exercise": "grey",
            "partner/date-night": "yellow", "children/nova": "green", "children/kit": "green",
            "wider/friends": "red",
        })


def test_adapter_raising_is_fenced_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit guard (CIR-ADAPT-CONTRACT#adapter-failure-is-isolated's exception input — only a
    monkeypatched adapter can raise): an adapter that RAISES is fenced into ⚪ by-failure for its
    own item; the others resolve normally, and the exception text (which may carry host paths) is
    not forwarded — only its class name is. At P0 nothing is evaluated, so nothing cascades."""
    config = load_config(ALEX_YAML)
    p0 = resolve(config, reference_date=UNIT_REFERENCE_DATE, generated_at=UNIT_GENERATED_AT)
    assert item_of(p0, "wider/plants")["status"] == "grey"
    assert item_of(p0, "wider/plants")["grey_reason"] == "not-evaluated"
    assert item_of(p0, "wider/friends")["status"] == "red"
    assert item_of(p0, "children/nova")["status"] == "green"

    def _explodes(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("/home/alex/secret/notes.md")

    monkeypatch.setattr(resolve_module, "evaluate_freshness", _explodes)
    exploded = resolve(config, reference_date=UNIT_REFERENCE_DATE, generated_at=UNIT_GENERATED_AT,
                       evaluate=True)
    sleep = item_of(exploded, "self/sleep")
    assert sleep["status"] == "grey"
    assert sleep["grey_reason"] == "by-failure"
    assert "adapter raised RuntimeError" in sleep["detail_line"]
    assert [w["message"] for w in exploded["warnings"] if w["item"] == "self/sleep"] == ["adapter raised RuntimeError"]
    assert item_of(exploded, "wider/friends")["status"] == "red"
    assert item_of(exploded, "children/nova")["status"] == "green"
    assert item_of(exploded, "partner/date-night")["status"] == "yellow"


def test_p0_never_runs_a_command_unit(tmp_path: Path) -> None:
    """Unit guard (was CIR-ADAPT-CONTRACT#adapter-never-writes — unproven: under --evaluate a
    command CAN write into the config dir, so the row is not evidence-backed): at P0, resolve()
    does not execute a `command:` — a script that would leave a marker leaves none."""
    import yaml

    script_path = tmp_path / "emit.sh"
    marker_path = tmp_path / "adapter-was-run.marker"
    script_path.write_text("#!/usr/bin/env bash\ntouch " + str(marker_path))
    script_path.chmod(0o755)
    data = {"person": "Test", "rings": [{"id": "a", "label": "A", "items": [
        {"id": "x", "label": "X", "status": {"command": [str(script_path)]}}]}]}
    config_path = tmp_path / "circles.yaml"
    config_path.write_text(yaml.dump(data))
    artifact = resolve(load_config(config_path), reference_date=UNIT_REFERENCE_DATE,
                       generated_at=UNIT_GENERATED_AT)
    assert not marker_path.exists(), f"Command adapter was executed — marker file exists at {marker_path}"
    assert item_of(artifact, "a/x")["status"] == "grey"
    assert item_of(artifact, "a/x")["grey_reason"] == "not-evaluated"


# ===========================================================================
# CIR-ADAPT-REFERENCE-DATE — one clock per bake, injected
# ===========================================================================

class TestAdaptReferenceDate:
    """CIR-ADAPT-REFERENCE-DATE — one clock per bake, injected."""

    @rule("CIR-ADAPT-REFERENCE-DATE")
    def test_reference_date_shared(self, alex_copy) -> None:
        """CIR-ADAPT-REFERENCE-DATE#reference-date-shared — two freshness items in one bake age
        against the one reference date: the artifact carries a single reference_date, no item
        carries its own, and both lights are the ones 2026-08-03 gives (sleep 🟢, labs 🔴)."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("reference_date", run.data["reference_date"], "2026-08-03")
        items = _items(run)
        verdict("items carrying their own reference_date", [ref for ref, i in items.items() if "reference_date" in i], [])
        verdict("self/sleep, self/labs status", {ref: items[ref]["status"] for ref in ("self/sleep", "self/labs")},
                {"self/sleep": "green", "self/labs": "red"})

    @rule("CIR-ADAPT-REFERENCE-DATE")
    def test_reference_date_injectable(self, alex_copy) -> None:
        """CIR-ADAPT-REFERENCE-DATE#reference-date-injectable — a fixed injected reference date
        makes the evaluated ages reproducible: a second bake at 2026-08-03 writes the same
        data.json as the first, generated_at aside."""
        config = given_alex(alex_copy)
        prior = given_prior_bake(config.parent.parent, config, "--evaluate", why="first evaluated bake at 2026-08-03")
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("data.json sha256 (generated_at masked)", _masked_digest(_raw(run)), _masked_digest(prior))
        verdict("self/sleep last_data_date", item_of(run.data, "self/sleep")["last_data_date"], "2026-08-01")

    @rule("CIR-ADAPT-REFERENCE-DATE")
    def test_reference_date_fixture_pinned(self, alex_copy) -> None:
        """CIR-ADAPT-REFERENCE-DATE#reference-date-fixture-pinned — a bake over fixtures/alex
        given the fixture reference date carries 2026-08-03, never the running day."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        verdict("reference_date", run.data["reference_date"], "2026-08-03")

    @rule("CIR-ADAPT-REFERENCE-DATE")
    @pytest.mark.parametrize("config_tz,host_tz", [
        # UTC−12 vs UTC+14: 26 h apart, so the two zones never share a calendar date.
        pytest.param("Pacific/Kiritimati", "Etc/GMT+12", id="config Pacific/Kiritimati, host TZ Etc/GMT+12"),
        pytest.param("omitted (UTC)", "Pacific/Kiritimati", id="config timezone omitted (UTC), host TZ Pacific/Kiritimati"),
    ])
    def test_reference_date_default_is_config_timezone(self, alex_copy, monkeypatch: pytest.MonkeyPatch,
                                                       config_tz: str, host_tz: str) -> None:
        """CIR-ADAPT-REFERENCE-DATE#reference-date-default-is-config-timezone — no injected date:
        today is the current instant's date in the config's `timezone:` (UTC when omitted); the
        host's TZ must not leak."""
        omitted = config_tz == "omitted (UTC)"
        if omitted:
            config = given_alex(alex_copy)
        else:
            config = given_alex(alex_copy, f"timezone: {config_tz}", lambda c: c.update(timezone=config_tz))
        with allure.step(f"Given: host TZ={host_tz} (the bake process's local zone)"):
            monkeypatch.setenv("TZ", host_tz)
        zone = ZoneInfo("UTC" if omitted else config_tz)
        before = datetime.now(zone).date().isoformat()
        run = when_bake(config, reference_date=None)
        if datetime.now(zone).date().isoformat() != before:
            pytest.skip("the config zone's calendar day rolled over during the bake")
        verdict("exit code", run.exit_code, 0)
        verdict(f"reference_date (today in config timezone {config_tz})", run.data["reference_date"], before)


def test_reference_date_crosses_midnight_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit guard (CIR-ADAPT-REFERENCE-DATE#reference-date-crosses-midnight — the bake's clock is
    not controllable from the CLI): resolution uses the reference date captured at bake start and
    never reaches around it to a wall clock that has since rolled over."""
    bake_start = datetime(2026, 8, 3, 23, 59, 59, tzinfo=timezone.utc)
    captured_date = bake_start.date()

    class _RolledOverClock:
        """The wall clock, already into the next day. Reading it is the defect."""

        @staticmethod
        def now(tz: Any = None) -> Any:
            raise AssertionError("resolution read the wall clock (now()) — it must use the "
                                 "reference date captured at bake start")

        @staticmethod
        def today() -> Any:
            raise AssertionError("resolution read the wall clock (today()) — it must use the "
                                 "reference date captured at bake start")

    monkeypatch.setattr(resolve_module, "datetime", _RolledOverClock)
    monkeypatch.setattr(resolve_module, "date", _RolledOverClock)

    config = load_config(ALEX_YAML)
    artifact = resolve(config, reference_date=captured_date, generated_at=bake_start)
    assert artifact["reference_date"] == "2026-08-03"
    assert artifact["generated_at"] == "2026-08-03T23:59:59Z"
    for ring in artifact["rings"]:
        for it in ring["items"]:
            assert "reference_date" not in it
            assert it["last_data_date"] is None or it["last_data_date"] <= "2026-08-03"
    later = resolve(config, reference_date=captured_date,
                    generated_at=datetime(2026, 8, 4, 0, 0, 1, tzinfo=timezone.utc))
    assert later["rings"] == artifact["rings"]
    assert later["reference_date"] == artifact["reference_date"]


def test_default_reference_date_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit guard on default_reference_date (a fixed instant, which the CLI cannot inject): at
    2026-08-03T22:30Z it is still 08-03 in UTC and Los Angeles (15:30 PDT) but already 08-04 in
    Auckland (10:30 NZST, UTC+12); a host running in Auckland does not move a UTC config's date."""
    now = datetime(2026, 8, 3, 22, 30, tzinfo=timezone.utc)
    assert default_reference_date("UTC", now) == date(2026, 8, 3)
    assert default_reference_date("America/Los_Angeles", now) == date(2026, 8, 3)
    assert default_reference_date("Pacific/Auckland", now) == date(2026, 8, 4)
    monkeypatch.setenv("TZ", "Pacific/Auckland")
    time.tzset()
    try:
        assert default_reference_date("UTC", now) == date(2026, 8, 3)
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()


# ===========================================================================
# CIR-ADAPT-NO-PAGE-LOGIC — the page is adapter-blind
# ===========================================================================

class TestAdaptNoPageLogic:
    """CIR-ADAPT-NO-PAGE-LOGIC — the page is adapter-blind: the artifact (all the page reads)
    carries no adapter vocabulary and one item shape whatever the adapter."""

    @rule("CIR-ADAPT-NO-PAGE-LOGIC")
    def test_page_has_no_adapter_vocabulary(self, alex_copy) -> None:
        """CIR-ADAPT-NO-PAGE-LOGIC#page-has-no-adapter-vocabulary — no item names the adapter that
        produced its status (no adapter / adapter_kind / adapter_name field)."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("item fields naming an adapter",
                sorted({k for i in _items(run).values() for k in i if k.startswith("adapter")}), [])

    @rule("CIR-ADAPT-NO-PAGE-LOGIC")
    def test_new_adapter_changes_no_page_code(self, alex_copy) -> None:
        """CIR-ADAPT-NO-PAGE-LOGIC#new-adapter-changes-no-page-code — the artifact shape is fixed
        regardless of adapter kind: manual, freshness, command and no-adapter items all carry
        exactly data-json.md's 11 item fields."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("items whose fields differ from the item table",
                {ref: sorted(i) for ref, i in _items(run).items() if sorted(i) != ITEM_FIELDS}, {})


# ===========================================================================
# CIR-BAKE-ATOMIC-WRITE — publishing discipline
# ===========================================================================

class TestBakeAtomicWrite:
    """CIR-BAKE-ATOMIC-WRITE — publishing discipline."""

    @rule("CIR-BAKE-ATOMIC-WRITE")
    def test_failed_bake_keeps_last_good(self, alex_copy) -> None:
        """CIR-BAKE-ATOMIC-WRITE#failed-bake-keeps-last-good — run N−1 (the unmodified world)
        published out/; run N fails validation (manual: amber) → run N−1's data.json is still
        there, byte-for-byte, beside its index.html."""
        config = given_alex(alex_copy, "self/sleep status: manual: amber (run N's config error)",
                            lambda c: item(c, "self/sleep").update(status={"manual": "amber"}))
        root = config.parent.parent
        prior = given_prior_bake(root, ALEX_YAML, why="run N−1 over the unmodified world alex")
        run = when_bake(config)
        verdict("exit code", run.exit_code, 1)
        verdict("artifact files in out/", run.artifact_files, ["data.json", "index.html"])
        verdict("out/data.json sha256", hashlib.sha256(_raw(run).encode()).hexdigest()[:16],
                hashlib.sha256(prior.encode()).hexdigest()[:16])

    @rule("CIR-BAKE-ATOMIC-WRITE")
    def test_write_artifact_is_world_readable(self, alex_copy) -> None:
        """CIR-BAKE-ATOMIC-WRITE#permissions-world-readable — data.json's file mode is 0o644 so
        non-root nginx-unprivileged can serve it (regression: tempfile.mkstemp creates 0o600)."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        verdict("out/data.json mode", oct(stat.S_IMODE((run.out_dir / "data.json").stat().st_mode)), "0o644")

    def test_write_artifact_creates_file(self, tmp_path: Path) -> None:
        """Unit guard: write_artifact creates data.json in the output directory."""
        artifact = resolve(load_config(ALEX_YAML), reference_date=UNIT_REFERENCE_DATE,
                           generated_at=UNIT_GENERATED_AT)
        out_path = write_artifact(artifact, tmp_path)
        assert out_path == tmp_path / "data.json"
        assert out_path.is_file()

    def test_write_artifact_is_valid_json(self, tmp_path: Path) -> None:
        """Unit guard: written data.json is valid JSON."""
        artifact = resolve(load_config(ALEX_YAML), reference_date=UNIT_REFERENCE_DATE,
                           generated_at=UNIT_GENERATED_AT)
        write_artifact(artifact, tmp_path)
        parsed = json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))
        assert parsed["version"] == 1
        assert parsed["person"] == "Alex Example"


# ===========================================================================
# CIR-BAKE-DETERMINISM — same inputs, same output
# ===========================================================================

class TestBakeDeterminism:
    """CIR-BAKE-DETERMINISM — same inputs, same output."""

    @rule("CIR-BAKE-DETERMINISM")
    def test_two_bakes_agree(self, alex_copy) -> None:
        """CIR-BAKE-DETERMINISM#two-bakes-agree — same config, same injected reference date →
        byte-identical artifact except generated_at."""
        config = given_alex(alex_copy)
        prior = given_prior_bake(config.parent.parent, config, why="first bake, same config + date")
        run = when_bake(config)
        verdict("exit code", run.exit_code, 0)
        verdict("data.json sha256 (generated_at masked)", _masked_digest(_raw(run)), _masked_digest(prior))

    @rule("CIR-BAKE-DETERMINISM")
    def test_ordering_is_stable(self, alex_copy) -> None:
        """CIR-BAKE-DETERMINISM#ordering-is-stable — rings and items in file order; warnings in
        item order (P0: sleep, labs, plants — their order in circles.yaml)."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        verdict("ring ids", [r["id"] for r in run.data["rings"]], ["self", "partner", "children", "wider"])
        verdict("self item ids", [i["id"] for i in run.data["rings"][0]["items"]], ["sleep", "labs", "exercise"])
        verdict("warning item order", [w["item"] for w in run.data["warnings"]],
                ["self/sleep", "self/labs", "wider/plants"])

    @rule("CIR-BAKE-DETERMINISM")
    def test_host_timezone_does_not_leak(self, alex_copy, monkeypatch: pytest.MonkeyPatch) -> None:
        """CIR-BAKE-DETERMINISM#host-timezone-does-not-leak — the evaluated bake under host
        TZ=Pacific/Auckland is identical (generated_at aside) to the one under TZ=UTC; the
        config's timezone: governs."""
        config = given_alex(alex_copy)
        prior = given_prior_bake(config.parent.parent, config, "--evaluate", why="evaluated, host TZ=UTC",
                                 env={"TZ": "UTC"})
        monkeypatch.setenv("TZ", "Pacific/Auckland")
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("data.json sha256 (generated_at masked)", _masked_digest(_raw(run)), _masked_digest(prior))
        verdict("self/sleep last_data_date (the evaluated artifact)",
                item_of(run.data, "self/sleep")["last_data_date"], "2026-08-01")

    def test_deterministic_output_unit(self, tmp_path: Path) -> None:
        """Unit guard: two resolve()+write_artifact() runs with an injected generated_at are
        byte-identical (no masking needed when the stamp is injected)."""
        config = load_config(ALEX_YAML)
        for name in ("a", "b"):
            write_artifact(resolve(config, reference_date=UNIT_REFERENCE_DATE,
                                   generated_at=UNIT_GENERATED_AT), tmp_path / name)
        assert (tmp_path / "a" / "data.json").read_bytes() == (tmp_path / "b" / "data.json").read_bytes()


# ===========================================================================
# CIR-BAKE-EXPOSURE — everything in the artifact is public
# ===========================================================================

class TestBakeExposure:
    """CIR-BAKE-EXPOSURE — everything in the artifact is public."""

    @rule("CIR-BAKE-EXPOSURE")
    def test_no_absolute_host_paths(self, alex_copy) -> None:
        """CIR-BAKE-EXPOSURE#no-absolute-host-paths — a missing source: the warning names the
        config-relative path `notes/absent.md`, and data.json never names the absolute directory
        the config was loaded from (nor any /home/ or /etc/ path)."""
        config = given_alex(alex_copy, "self/sleep source: notes/absent.md",
                            lambda c: item(c, "self/sleep")["status"]["freshness"].update(source="notes/absent.md"))
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("self/sleep warning", " | ".join(_item_warnings(run, "self/sleep")), "notes/absent.md", op="contains")
        raw = _raw(run)
        verdict("data.json names the config dir's absolute path", str(config.parent.resolve()) in raw, False)
        verdict("data.json", raw, "/home/", op="not contains")
        verdict("data.json", raw, "/etc/", op="not contains")

    @rule("CIR-BAKE-EXPOSURE")
    def test_no_source_content_in_the_artifact(self, alex_copy) -> None:
        """CIR-BAKE-EXPOSURE#no-source-content-in-the-artifact — from a freshness source only the
        date is carried: the evaluated artifact holds 2026-08-01 but none of the entries' own
        words (`7h20m`, `panel done, all fine …`) from notes/sleep-log.md and notes/labs.md."""
        config = given_alex(alex_copy)
        entry_words = [line.split("—", 1)[1].strip()
                       for note in ("sleep-log.md", "labs.md")
                       for line in (config.parent / "notes" / note).read_text(encoding="utf-8").splitlines()
                       if line.startswith("- ")]
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        raw = _raw(run)
        verdict("data.json", raw, "2026-08-01", op="contains")
        verdict("note entry words found in data.json", [w for w in entry_words if w in raw], [])

    @rule("CIR-BAKE-EXPOSURE")
    def test_command_stderr_not_passed_through(self, alex_copy, monkeypatch: pytest.MonkeyPatch) -> None:
        """CIR-BAKE-EXPOSURE#command-stderr-not-passed-through — the plants command prints a stack
        trace with paths and its env to stderr (the bake's env holds CIRCLES_SECRET): the warning
        is a bounded, sanitized summary — none of it reaches data.json."""
        body = ('echo "Traceback (most recent call last):" >&2\n'
                'echo "  File \\"$0\\", line 7, in /home/alex/bin/probe" >&2\n'
                'env >&2\nexit 1\n')
        config = given_plants_runs(alex_copy, "stack trace + env on stderr, exits 1", body)
        monkeypatch.setenv("CIRCLES_SECRET", "s3cret-value")
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        raw = _raw(run)
        verdict("stderr fragments found in data.json",
                [s for s in ("Traceback", "/home/alex", "PATH=", "CIRCLES_SECRET", "s3cret-value", "plants-probe.sh")
                 if s in raw], [])
        message = " | ".join(_item_warnings(run, "wider/plants"))
        verdict(f"wider/plants warning length ≤ {adapters_module.WARNING_MAX_CHARS}",
                0 < len(message) <= adapters_module.WARNING_MAX_CHARS, True)

    @rule("CIR-BAKE-EXPOSURE")
    @pytest.mark.parametrize("stream", [
        pytest.param("stderr", id="10 MB on stderr, command fails"),
        pytest.param("stdout-first-line", id="10 MB as the status word"),
    ])
    def test_warning_text_is_bounded(self, alex_copy, stream: str) -> None:
        """CIR-BAKE-EXPOSURE#warning-text-is-bounded — a command prints 10 MB (to stderr, or as
        its unknown status word) → ⚪, and the warning is truncated at a fixed cap, three orders of
        magnitude under the output; data.json stays small."""
        ten_mb = "head -c 10485760 /dev/zero | tr '\\0' 'x'"
        body = f"{ten_mb} >&2\nexit 1\n" if stream == "stderr" else f"{ten_mb}\necho\n"
        config = given_plants_runs(alex_copy, f"prints 10 MB ({stream})", body)
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("wider/plants status", item_of(run.data, "wider/plants")["status"], "grey")
        message = " | ".join(_item_warnings(run, "wider/plants"))
        cap = adapters_module.WARNING_MAX_CHARS
        verdict(f"wider/plants warning length ≤ cap {cap} < 10000", 0 < len(message) <= cap < 10_000, True)
        verdict("data.json size < 100000 bytes", len(_raw(run).encode()) < 100_000, True)


# ===========================================================================
# CIR-BAKE-PAGE-DOES-NOT-RESOLVE — the page renders, it never decides
# ===========================================================================

class TestBakePageDoesNotResolve:
    """CIR-BAKE-PAGE-DOES-NOT-RESOLVE — the page renders, it never decides."""

    @rule("CIR-BAKE-PAGE-DOES-NOT-RESOLVE")
    def test_page_contains_no_adapter_code(self, alex_copy) -> None:
        """CIR-BAKE-PAGE-DOES-NOT-RESOLVE#page-contains-no-adapter-code — the shipped page
        (out/index.html) carries none of resolution's inputs — no thresholds (yellow_after /
        red_after), no source paths, no command argv — so it has nothing to parse, compare or run."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        page = (run.out_dir / "index.html").read_text(encoding="utf-8")
        verdict("resolution inputs found in index.html",
                [s for s in ("yellow_after", "red_after", "notes/sleep-log.md", "notes/labs.md",
                             "plants-status.sh") if s in page], [])


# ===========================================================================
# CIR-DATA-FRESHNESS-WINDOW — thresholds and boundaries, through the bake
# ===========================================================================

class TestDataFreshnessWindow:
    """CIR-DATA-FRESHNESS-WINDOW — self/sleep (newest 2026-08-01, yellow_after 7, red_after 30)
    evaluated with the reference date moved so the newest entry is the row's age (⚖-R6 strict >)."""

    @rule("CIR-DATA-FRESHNESS-WINDOW")
    @pytest.mark.parametrize("reference,expected", [
        pytest.param("2026-08-07", "🟢", id="CIR-DATA-FRESHNESS-WINDOW#window-inside"),
        pytest.param("2026-08-08", "🟢", id="CIR-DATA-FRESHNESS-WINDOW#window-at-yellow-boundary"),
        pytest.param("2026-08-09", "🟡", id="CIR-DATA-FRESHNESS-WINDOW#window-just-past-yellow"),
        pytest.param("2026-08-30", "🟡", id="CIR-DATA-FRESHNESS-WINDOW#window-mid"),
        pytest.param("2026-08-31", "🟡", id="CIR-DATA-FRESHNESS-WINDOW#window-at-red-boundary"),
        pytest.param("2026-09-01", "🔴", id="CIR-DATA-FRESHNESS-WINDOW#window-just-past-red"),
        pytest.param("2026-09-15", "🔴", id="CIR-DATA-FRESHNESS-WINDOW#window-far-past-red"),
    ])
    def test_window_through_the_bake(self, alex_copy, reference: str, expected: str) -> None:
        """CIR-DATA-FRESHNESS-WINDOW — ages 6/7/8/29/30/31/45 days (reference − 2026-08-01); the
        spec's light (expected) is checked as its wire word (CIR-BAKE-STATUS-VALUES)."""
        run = when_bake(given_alex(alex_copy), "--evaluate", reference_date=reference)
        verdict("exit code", run.exit_code, 0)
        sleep = item_of(run.data, "self/sleep")
        verdict(f"self/sleep status (expected {expected})", sleep["status"], WIRE[expected])
        verdict("self/sleep last_data_date", sleep["last_data_date"], "2026-08-01")

    @pytest.mark.parametrize("age,yellow,red,expected", [
        (6, 7, 30, "green"), (7, 7, 30, "green"), (8, 7, 30, "yellow"), (29, 7, 30, "yellow"),
        (30, 7, 30, "yellow"), (31, 7, 30, "red"), (45, 7, 30, "red"),
    ])
    def test_window_predicate_unit(self, age: int, yellow: int, red: int, expected: str) -> None:
        """Unit guard on the pure predicate window_status (⚖-R6 strict `>`)."""
        assert window_status(age, yellow, red) == expected


# ===========================================================================
# CIR-ADAPT-MANUAL — hand-set light
# ===========================================================================

class TestAdaptManual:
    """CIR-ADAPT-MANUAL — hand-set light."""

    @rule("CIR-ADAPT-MANUAL")
    def test_manual_returns_declared_light(self, alex_copy) -> None:
        """CIR-ADAPT-MANUAL#manual-returns-declared-light — children/nova `manual: green` → 🟢,
        no data date."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        nova = item_of(run.data, "children/nova")
        verdict("children/nova status, last_data_date", [nova["status"], nova["last_data_date"]], ["green", None])

    @rule("CIR-ADAPT-MANUAL")
    def test_manual_has_no_data_date(self, alex_copy) -> None:
        """CIR-ADAPT-MANUAL#manual-has-no-data-date — any manual item (date-night, nova, kit,
        friends): no last_data_date, no "last data" segment in the detail line."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("exit code", run.exit_code, 0)
        items = _items(run)
        manual = ("partner/date-night", "children/nova", "children/kit", "wider/friends")
        verdict("manual items with a data date or a 'last data' segment",
                [ref for ref in manual if items[ref]["last_data_date"] is not None
                 or "last data" in items[ref]["detail_line"]], [])

    @rule("CIR-ADAPT-MANUAL")
    @pytest.mark.parametrize("phase", [
        pytest.param("P0 build-time", id="P0 build-time bake"),
        pytest.param("P1 nightly", id="P1 nightly bake (--evaluate)"),
    ])
    def test_manual_available_in_every_phase(self, alex_copy, phase: str) -> None:
        """CIR-ADAPT-MANUAL#manual-available-in-every-phase — partner/date-night `manual: yellow`
        resolves 🟡 in every phase's bake."""
        run = when_bake(given_alex(alex_copy), *PHASE_FLAGS[phase])
        verdict(f"exit code ({phase} bake)", run.exit_code, 0)
        verdict(f"partner/date-night status ({phase} bake)",
                item_of(run.data, "partner/date-night")["status"], "yellow")


# ===========================================================================
# CIR-PROC-PHASE-P0 — hand-set statuses on the existing pipeline
# ===========================================================================

class TestProcPhaseP0:
    """CIR-PROC-PHASE-P0 — hand-set statuses on the existing pipeline."""

    @rule("CIR-PROC-PHASE-P0")
    def test_p0_manual_end_to_end(self, alex_copy) -> None:
        """CIR-PROC-PHASE-P0#p0-manual-end-to-end — the bake's half (serving it from the image is
        the system tier's): a P0 bake writes the page + the artifact with alex's manual statuses."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        verdict("artifact files in out/", run.artifact_files, ["data.json", "index.html"])
        items = _items(run)
        verdict("manual lights", {ref: items[ref]["status"] for ref in
                                  ("children/nova", "children/kit", "partner/date-night", "wider/friends")},
                {"children/nova": "green", "children/kit": "green", "partner/date-night": "yellow",
                 "wider/friends": "red"})

    @rule("CIR-PROC-PHASE-P0")
    def test_p0_unevaluated_adapters_are_grey(self, alex_copy) -> None:
        """CIR-PROC-PHASE-P0#p0-unevaluated-adapters-are-grey — the fixture's freshness: (sleep,
        labs) and command: (plants) items → ⚪ + warning "adapter not evaluated in this build",
        grey_reason not-evaluated (⚖-R50)."""
        run = when_bake(given_alex(alex_copy))
        verdict("exit code", run.exit_code, 0)
        items = _items(run)
        refs = ("self/sleep", "self/labs", "wider/plants")
        verdict("status + grey_reason", {ref: [items[ref]["status"], items[ref]["grey_reason"]] for ref in refs},
                {ref: ["grey", "not-evaluated"] for ref in refs})
        verdict("warnings", {ref: _item_warnings(run, ref) for ref in refs},
                {ref: ["adapter not evaluated in this build"] for ref in refs})

    @rule("CIR-PROC-PHASE-P0")
    @pytest.mark.parametrize("phase", [
        pytest.param("P0 build-time", id="validates at P0 (build-time bake)"),
        pytest.param("P1 nightly", id="validates at P1 (--evaluate), no migration"),
    ])
    def test_p0_config_stays_valid(self, alex_copy, phase: str) -> None:
        """CIR-PROC-PHASE-P0#p0-config-stays-valid — the fixture config unchanged bakes at P0 and
        at P1."""
        run = when_bake(given_alex(alex_copy), *PHASE_FLAGS[phase])
        verdict(f"exit code ({phase} bake)", run.exit_code, 0)
        verdict("person, ring count", [run.data["person"], len(run.data["rings"])], ["Alex Example", 4])


# ===========================================================================
# CIR-PROC-BAKE-ONE-PATH — one bake, several triggers
# ===========================================================================

class TestProcBakeOnePath:
    """CIR-PROC-BAKE-ONE-PATH — one bake, several triggers."""

    @rule("CIR-PROC-BAKE-ONE-PATH")
    def test_bake_same_code_both_triggers(self, alex_copy) -> None:
        """CIR-PROC-BAKE-ONE-PATH#bake-same-code-both-triggers — the build-time run (no flag) and
        the scheduled run (--evaluate) are the same entry point differing only in configuration:
        the same artifact shape, the same rings/items, the same manual lights — only the
        evaluated items' lights differ."""
        config = given_alex(alex_copy)
        prior = json.loads(given_prior_bake(config.parent.parent, config, why="build-time trigger (P0)"))
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("top-level keys (scheduled = build-time)", sorted(run.data), sorted(prior))
        verdict("items per ring (scheduled = build-time)",
                {r["id"]: [i["id"] for i in r["items"]] for r in run.data["rings"]},
                {r["id"]: [i["id"] for i in r["items"]] for r in prior["rings"]})
        manual = ("partner/date-night", "children/nova", "children/kit", "wider/friends")
        verdict("manual lights (scheduled = build-time)",
                {ref: item_of(run.data, ref)["status"] for ref in manual},
                {ref: item_of(prior, ref)["status"] for ref in manual})


# ===========================================================================
# CIR-ADAPT-BUDGET — the bake's exit code (the process, not the resolver)
# ===========================================================================

class TestAdaptBudgetExitCode:
    """CIR-ADAPT-BUDGET — failed adapters publish with warnings; only config errors fail."""

    @rule("CIR-ADAPT-BUDGET")
    def test_bake_exit_code_only_for_config_errors(self, alex_copy) -> None:
        """CIR-ADAPT-BUDGET#bake-exit-code-only-for-config-errors — some adapters failed (plants
        prints red, exits 3), none was a config error → exit 0; the page is published with
        warnings."""
        config = given_plants_runs(alex_copy, "prints red, exits 3", "echo red\nexit 3\n")
        run = when_bake(config, "--evaluate")
        verdict("exit code", run.exit_code, 0)
        verdict("artifact files in out/", run.artifact_files, ["data.json", "index.html"])
        verdict("warning item refs", [w["item"] for w in run.data["warnings"]], "wider/plants", op="contains")


# ===========================================================================
# Unit guards — resolve() over the fixture, the artifact's types (never evidence)
# ===========================================================================

def _unit_artifact() -> dict:
    return resolve(load_config(ALEX_YAML), reference_date=UNIT_REFERENCE_DATE, generated_at=UNIT_GENERATED_AT)


def test_fixture_resolves_correctly_unit() -> None:
    """All eight items resolve to the expected P0 statuses at the fixture reference date."""
    a = _unit_artifact()
    expected = {
        "self/sleep": ("grey", "not-evaluated"), "self/labs": ("grey", "not-evaluated"),
        "self/exercise": ("grey", "by-choice"), "partner/date-night": ("yellow", None),
        "children/nova": ("green", None), "children/kit": ("green", None),
        "wider/friends": ("red", None), "wider/plants": ("grey", "not-evaluated"),
    }
    for ref, (status, reason) in expected.items():
        assert item_of(a, ref)["status"] == status, ref
        assert item_of(a, ref)["grey_reason"] == reason, ref


def test_artifact_has_required_fields_unit() -> None:
    """All required top-level fields are present."""
    a = _unit_artifact()
    for field in TOP_LEVEL_FIELDS:
        assert field in a, f"Missing required field: {field}"


def test_artifact_types_unit() -> None:
    """Field types match the schema."""
    a = _unit_artifact()
    assert isinstance(a["version"], int)
    assert isinstance(a["spec_version"], int)
    assert isinstance(a["person"], str)
    assert isinstance(a["generated_at"], str)
    assert isinstance(a["reference_date"], str)
    assert isinstance(a["timezone"], str)
    assert a["stale_after_hours"] is None
    assert isinstance(a["rings"], list)
    assert isinstance(a["warnings"], list)


def test_item_fields_unit() -> None:
    """Every item has the required fields with correct types."""
    for ring in _unit_artifact()["rings"]:
        for it in ring["items"]:
            assert isinstance(it["id"], str)
            assert isinstance(it["label"], str)
            assert it["status"] in ("green", "yellow", "red", "grey")
            assert it["grey_reason"] in (None, "by-choice", "by-failure", "not-evaluated")
            assert isinstance(it["share"], (int, float))
            assert isinstance(it["detail_line"], str)
            assert "detail_page" in it
