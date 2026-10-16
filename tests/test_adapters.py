# Evidence for the adapter rules — freshness (dates in files) and command (the escape hatch).
#
# World: alex — every case starts from fixtures/alex (specs/data/adapters.md and
# specs/data/freshness.md: "World: alex") and turns at most one knob; the knob and its value name
# the given step. The system boundary these rules are stated against is the bake CLI with its
# adapters ON (`python -m bake … --evaluate`): what an adapter decided reaches the world only as
# the item's status / grey_reason / last_data_date / detail_line and the build warnings in
# out/data.json. Each labelled case reads given (world + knob, plus any file the knob needs,
# attached) → when (ONE bake run) → then (one verdict per claim) — tests/evidence_helpers.py,
# after allure-behavior-snippets CONVENTIONS § Prime rule of reporting. Each case cites its spec
# row as CIR-<AREA>-<NAME>#<row-id> (the case title the spec join matches).
#
# Expected values come from the spec rows and the fixture's committed dates (read below as the
# CONTRACT inputs), never from running the bake. Every bake pins the fixture reference date
# 2026-08-03 (⚖-R24); date-sensitive rows move the INJECTED reference date, never committed dates.
#
# The bake runs in a subprocess, so the ⚖-R21 leash (30 s per item, 5 min per bake —
# module constants in bake/adapters.py) cannot be monkeypatched from here. The timing rows shrink
# it with `given_leash` (tests/evidence_helpers.py): a tests-only `sitecustomize.py`, generated into
# the case's tmp dir and put on the bake's PYTHONPATH (`when_bake(..., env=)`), sets the constants
# before `python -m bake` runs its unchanged `main()`. The shrink is named in the given step (and so
# in the when step) and its source is attached — the run is the production CLI with the two
# numbers turned down, said so in the report. The production values themselves are pinned by an
# unlabelled unit guard below.
#
# The unlabelled tests at the bottom are unit guards (CONVENTIONS § Allure taxonomy): internals
# the CLI cannot show — exact integer ages, the token scanner's rejected list, the AdapterResult
# type, the ⚖-R21 constants, the default reference date under a frozen instant.

from __future__ import annotations

import hashlib
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import allure
import pytest

from bake.__main__ import default_reference_date
import bake.adapters as adapters_module
from bake.adapters import WARNING_MAX_CHARS, AdapterResult, calendar_age, scan_dates
from bake.config import load_config
from bake.resolve import resolve
from evidence_helpers import (
    BakeRun,
    given_alex,
    given_file,
    given_leash,
    given_script,
    item,
    item_of,
    then_grey_by_failure,
    verdict,
    warnings_for,
    when_bake,
)
from rules import rule

AlexCopy = Callable[..., Path]  # the `alex_copy` factory fixture (tests/conftest.py)
ALEX_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "alex"
ALEX_YAML = ALEX_DIR / "circles.yaml"
FIXTURE_REFERENCE_DATE = date(2026, 8, 3)
FIXTURE_GENERATED_AT = datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc)

# The fixture person's committed source dates (fixtures/alex/notes/*.md) — the CONTRACT inputs
# the expectations below are derived from, not rewritten.
SLEEP_NEWEST = "2026-08-01"      # notes/sleep-log.md: 2026-08-01, 2026-07-31, 2026-07-30
LABS_NEWEST = "2026-01-15"       # notes/labs.md
# circles.yaml: self/sleep yellow_after 7 / red_after 30; self/labs 100 / 190.
SLEEP_GUARDRAIL = "Lights out by 23:00 on weeknights"   # circles.yaml self/sleep guardrail
# The probe note the source-pointing cases write their row's literal input into.
PROBE = "notes/probe.md"


# ---------------------------------------------------------------------------- given (local)
# Arrange-only helpers (CONVENTIONS § The helper razor) for the two knobs these rows turn.

def sleep_source(source: str, yellow_after: int | None = None, red_after: int | None = None):
    """An ``edit`` for ``given_alex``: re-point self/sleep's freshness block (wire format)."""
    def edit(c: dict) -> None:
        freshness = item(c, "self/sleep")["status"]["freshness"]
        freshness["source"] = source
        if yellow_after is not None:
            freshness["yellow_after"] = yellow_after
        if red_after is not None:
            freshness["red_after"] = red_after
    return edit


def plants_command(alex_copy: AlexCopy, body: str, *args: str, note: str = "",
                   world: Callable[[Path], None] | None = None) -> Path:
    """Given: alex whose wider/plants runs ``./notes/plants-probe.sh *args`` with ``body``.
    ``world`` (e.g. a ``given_leash``) runs inside the same given step; ``note`` names it."""
    argv = ["./notes/plants-probe.sh", *args]
    config = given_alex(alex_copy, f"wider/plants command: {argv}, script body {body!r}{note}",
                        lambda c: item(c, "wider/plants").update(status={"command": argv}), world=world)
    given_script(config, "notes/plants-probe.sh", body)
    return config


def leashed(env: dict[str, str], **constants: float) -> Callable[[Path], None]:
    """A ``world`` knob for ``given_alex``: ``given_leash(**constants)`` inside the world's given
    step, its env overrides collected into ``env`` (for ``when_bake(..., env=env)``)."""
    return lambda world: env.update(given_leash(world / "circles.yaml", **constants))


# ---------------------------------------------------------------------------- then (local)
# CIR-DATA-FAILURE-IS-GREY's shape with the whole detail line claimed (CIR-DATA-DETAIL-LINE:
# "guardrail · status · … · reason"), for the two items these rows turn.

def then_sleep_failure(run: BakeRun) -> str:
    return then_grey_by_failure(run, "self/sleep", guardrail=SLEEP_GUARDRAIL, exact_detail=True)


def then_plants_failure(run: BakeRun) -> str:
    return then_grey_by_failure(run, "wider/plants", exact_detail=True)


# ===========================================================================
# CIR-ADAPT-FRESHNESS — dates in files (interface-level obligations)
# ===========================================================================

class TestAdaptFreshness:
    """CIR-ADAPT-FRESHNESS — dates in files."""

    @rule("CIR-ADAPT-FRESHNESS")
    def test_freshness_reads_never_executes(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-FRESHNESS#freshness-reads-never-executes — a source: that is an executable
        script is read as text, not run."""
        # Its own script (wider/plants legitimately RUNS plants-status.sh under --evaluate):
        # prints `yellow` and touches a marker next to circles.yaml — effects only execution has.
        config = given_alex(alex_copy, "self/sleep source: notes/source-script.sh",
                            sleep_source("notes/source-script.sh"))
        given_script(config, "notes/source-script.sh",
                     'echo yellow\ntouch "$(dirname "$0")/../script-was-run.marker"\n')
        run = when_bake(config, "--evaluate")
        verdict("script-was-run.marker exists", (config.parent / "script-was-run.marker").exists(), False)
        # Read as text, the script holds no ISO date → ⚪ by-failure, never the printed `yellow`.
        message = then_sleep_failure(run)
        verdict("self/sleep warning", message, "no dates found", op="contains")

    @rule("CIR-ADAPT-FRESHNESS")
    def test_freshness_reports_its_data_date(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-FRESHNESS#freshness-reports-its-data-date — newest date 2026-08-01 →
        last_data_date 2026-08-01, 'last data 2026-08-01' in the detail line."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep last_data_date", sleep["last_data_date"], SLEEP_NEWEST)
        verdict("self/sleep detail_line", sleep["detail_line"], f"last data {SLEEP_NEWEST}", op="contains")

    @rule("CIR-ADAPT-FRESHNESS")
    def test_freshness_sandboxed_to_config_dir(self, alex_copy: AlexCopy, tmp_path: Path) -> None:
        """CIR-ADAPT-FRESHNESS#freshness-sandboxed-to-config-dir — a glob hit that resolves
        outside the config directory (a symlink out) is never read: missing source, and the
        warning names neither host path."""
        config = given_alex(alex_copy, "self/sleep source: notes/esc*.md", sleep_source("notes/esc*.md"))
        # Outside the config dir: a copy of the sleep log (dated 2026-08-01 — 🟢 if it were read).
        outside = tmp_path / "outside-the-config-dir.md"
        with allure.step("Given: notes/escape.md → ../../outside-the-config-dir.md (a symlink out "
                         "of the config dir, onto a copy of notes/sleep-log.md)"):
            outside.write_text((ALEX_DIR / "notes" / "sleep-log.md").read_text(encoding="utf-8"),
                               encoding="utf-8")
            (config.parent / "notes" / "escape.md").symlink_to("../../outside-the-config-dir.md")
        run = when_bake(config, "--evaluate")
        message = then_sleep_failure(run)
        verdict("self/sleep warning", message, "missing source: notes/esc*.md", op="contains")
        verdict("warnings name the tmp root (a host path)", str(tmp_path) in run.warnings, False)


# ===========================================================================
# CIR-DATA-SOURCE-PATH — evaluation rows (config-error rows live in test_config.py)
# ===========================================================================

class TestDataSourcePathEvaluation:
    """CIR-DATA-SOURCE-PATH — where sources are read from (evaluation rows)."""

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_single_file(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-single-file — source: notes/sleep-log.md exists → its
        dates are read (newest 2026-08-01)."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep last_data_date", sleep["last_data_date"], SLEEP_NEWEST)
        verdict("self/sleep status", sleep["status"], "green")  # age 2 ≤ yellow_after 7

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_glob_union(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-glob-union — notes/lab-*.md matching 3 files → the newest
        date across the union wins."""
        config = given_alex(alex_copy, "self/sleep source: notes/lab-*.md", sleep_source("notes/lab-*.md"))
        notes = ALEX_DIR / "notes"
        # Three matches built from the fixture's own notes: newest dates 2026-01-15 (labs),
        # 2026-08-01 (sleep-log), none (empty-log) → union newest 2026-08-01.
        copies = {"notes/lab-1.md": "labs.md", "notes/lab-2.md": "sleep-log.md",
                  "notes/lab-3.md": "empty-log.md"}
        with allure.step("Given: 3 files match notes/lab-*.md — " +
                         ", ".join(f"{rel} = notes/{src}" for rel, src in copies.items())):
            texts = []
            for rel, src in copies.items():
                text = (notes / src).read_text(encoding="utf-8")
                (config.parent / rel).write_text(text, encoding="utf-8")
                texts.append(f"=== {rel} (copy of notes/{src})\n{text}")
            allure.attach("\n".join(texts), name="notes/lab-1.md, lab-2.md, lab-3.md (world: alex copy)",
                          attachment_type=allure.attachment_type.TEXT)
        run = when_bake(config, "--evaluate")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep last_data_date", sleep["last_data_date"], SLEEP_NEWEST)
        verdict("self/sleep status", sleep["status"], "green")  # age 2 ≤ 7

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_glob_no_match(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-glob-no-match — glob matches zero files → ⚪ + build
        warning (missing source)."""
        config = given_alex(alex_copy, "self/sleep source: notes/lab-*.md (no such files)",
                            sleep_source("notes/lab-*.md"))
        message = then_sleep_failure(when_bake(config, "--evaluate"))
        verdict("self/sleep warning", message, "missing source: notes/lab-*.md", op="contains")

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_path_missing(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-path-missing — path does not exist → ⚪ + build warning
        (missing source)."""
        config = given_alex(alex_copy, "self/sleep source: notes/absent.md", sleep_source("notes/absent.md"))
        message = then_sleep_failure(when_bake(config, "--evaluate"))
        verdict("self/sleep warning", message, "missing source: notes/absent.md", op="contains")

    @rule("CIR-DATA-SOURCE-PATH")
    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads mode-000 files")
    def test_source_unreadable(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-unreadable — file exists, permission denied → ⚪ + build
        warning."""
        config = given_alex(alex_copy)
        note = config.parent / "notes" / "sleep-log.md"
        with allure.step("Given: notes/sleep-log.md mode 0000 (exists, permission denied)"):
            note.chmod(0o000)
        try:
            run = when_bake(config, "--evaluate")
        finally:
            note.chmod(0o644)
        message = then_sleep_failure(run)
        verdict("self/sleep warning", message, "unreadable source: notes/sleep-log.md", op="contains")


    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_glob_symlink_loop(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-glob-symlink-loop — notes/l* matching notes/labs.md and a
        self-looping symlink notes/loop → the loop is skipped; labs is judged on its own dates."""
        def labs_glob(c):
            item(c, "self/labs")["status"]["freshness"].update(source="notes/l*")
        config = given_alex(alex_copy, "self/labs source: notes/l* (+ notes/loop → notes/loop)",
                            labs_glob, world=lambda d: (d / "notes" / "loop").symlink_to("loop"))
        run = when_bake(config, "--evaluate")
        labs = item_of(run.data, "self/labs")
        # notes/labs.md newest 2026-01-15, age 200 at 2026-08-03 > red_after 190 → 🔴.
        verdict("self/labs last_data_date", labs["last_data_date"], LABS_NEWEST)
        verdict("self/labs status", labs["status"], "red")
        verdict("warnings naming self/labs", warnings_for(run, "self/labs"), [])


# ===========================================================================
# CIR-DATA-DATE-PARSE — which date tokens count
# ===========================================================================

class TestDataDateParse:
    """CIR-DATA-DATE-PARSE — ISO-8601 only (⚖-R27). The row's literal input is the whole text
    of the sleep item's source; what the parser counted shows as the last-data date."""

    @rule("CIR-DATA-DATE-PARSE")
    @pytest.mark.parametrize("token,zone", [
        pytest.param("2026-08-01", "UTC", id="CIR-DATA-DATE-PARSE#date-iso-calendar"),
        pytest.param("- 2026-08-01 — 7h20m", "UTC", id="CIR-DATA-DATE-PARSE#date-anywhere-in-line"),
        pytest.param("## Session on 2026-08-01 (evening)", "UTC",
                     id="CIR-DATA-DATE-PARSE#date-heading-prose"),
        # 22:10 at +03:00 is 22:10 Europe/Tallinn (EEST = UTC+3) → local date 2026-08-01
        pytest.param("2026-08-01T22:10:00+03:00", "Europe/Tallinn",
                     id="CIR-DATA-DATE-PARSE#date-datetime-form"),
    ])
    def test_token_recognised(self, alex_copy: AlexCopy, token: str, zone: str) -> None:
        """A recognised token → last data 2026-08-01, 🟢 (age 2 ≤ yellow_after 7), no warning."""
        config = given_alex(alex_copy, f"timezone: {zone}, self/sleep source: {PROBE}",
                            lambda c: (c.update(timezone=zone), sleep_source(PROBE)(c)))
        given_file(config, PROBE, token + "\n")
        run = when_bake(config, "--evaluate")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep last_data_date", sleep["last_data_date"], "2026-08-01")
        verdict("self/sleep status", sleep["status"], "green")
        verdict("warnings naming self/sleep", warnings_for(run, "self/sleep"), [])

    @rule("CIR-DATA-DATE-PARSE")
    @pytest.mark.parametrize("token", [
        pytest.param("03/04/2026", id="CIR-DATA-DATE-PARSE#date-slash-format"),
        pytest.param("1 August 2026", id="CIR-DATA-DATE-PARSE#date-written-month"),
        pytest.param("v2026-08-01-rc1 and id=2026-08-013", id="CIR-DATA-DATE-PARSE#date-iso-substring"),
    ])
    def test_token_ignored(self, alex_copy: AlexCopy, token: str) -> None:
        """An ignored token leaves the source with no date → ⚪ by-failure, "no dates found"."""
        config = given_alex(alex_copy, f"self/sleep source: {PROBE}", sleep_source(PROBE))
        given_file(config, PROBE, token + "\n")
        message = then_sleep_failure(when_bake(config, "--evaluate"))
        verdict("self/sleep warning", message, f"no dates found in source: {PROBE}", op="contains")

    @rule("CIR-DATA-DATE-PARSE")
    def test_date_impossible_calendar(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-DATE-PARSE#date-impossible-calendar — 2026-02-30 is ignored, with a warning
        naming the (config-relative) file."""
        config = given_alex(alex_copy, "self/sleep source: notes/impossible.md",
                            sleep_source("notes/impossible.md"))
        given_file(config, "notes/impossible.md", "2026-02-30\n")
        run = when_bake(config, "--evaluate")
        # The source's only token is impossible → no usable date → ⚪, and the warning names
        # the token and the file relative to the config dir.
        message = then_sleep_failure(run)
        verdict("self/sleep warning names the token, the file",
                ["2026-02-30" in message, "notes/impossible.md" in message], [True, True])
        verdict("warnings name the config dir (a host path)", str(config.parent) in run.warnings, False)

    @rule("CIR-DATA-DATE-PARSE")
    def test_date_newest_wins(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-DATE-PARSE#date-newest-wins — the fixture's sleep-log holds 2026-08-01,
        2026-07-31, 2026-07-30 → last-data date 2026-08-01."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        verdict("self/sleep last_data_date", item_of(run.data, "self/sleep")["last_data_date"], "2026-08-01")

    @rule("CIR-DATA-DATE-PARSE")
    def test_date_none_parseable(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-DATE-PARSE#date-none-parseable — prose with no ISO dates
        (notes/empty-log.md) → ⚪ + warning, never 🟢."""
        config = given_alex(alex_copy, "self/sleep source: notes/empty-log.md",
                            sleep_source("notes/empty-log.md"))
        message = then_sleep_failure(when_bake(config, "--evaluate"))
        verdict("self/sleep warning", message, "no dates found in source: notes/empty-log.md", op="contains")


# ===========================================================================
# CIR-DATA-AGE-CALENDAR — age is calendar days in the config's timezone
# ===========================================================================
#
# data.json carries no age, only the light the age earns. Each case below therefore narrows the
# window to the age the row claims: with yellow_after Y / red_after Y+1 (the narrowest valid
# window, CIR-DATA-FRESHNESS-THRESHOLDS), 🟡 means age exactly Y+1 (≤ Y is 🟢, > Y+1 is 🔴, ⚖-R6).
# Ages 0 and 1 both sit under the smallest legal yellow_after (1), so those two rows pin
# "counted, not future, ≤ 1"; the exact integers are pinned by unit guards below.

TALLINN = "Europe/Tallinn"


def _probe_window(zone: str | None, token: str, yellow_after: int, red_after: int) -> tuple[str, Callable]:
    """(mutation sentence, edit) for: self/sleep reads only ``token`` under window Y/R."""
    sentence = (f"timezone: {zone}, " if zone else "") + (
        f"self/sleep source: {PROBE} holding {token!r}, yellow_after {yellow_after}, red_after {red_after}")

    def edit(c: dict) -> None:
        if zone:
            c["timezone"] = zone
        sleep_source(PROBE, yellow_after, red_after)(c)
    return sentence, edit


def given_probe(alex_copy: AlexCopy, token: str, yellow_after: int, red_after: int,
                zone: str | None = None) -> Path:
    config = given_alex(alex_copy, *_probe_window(zone, token, yellow_after, red_after))
    given_file(config, PROBE, f"- {token}\n")
    return config


class TestDataAgeCalendar:
    """CIR-DATA-AGE-CALENDAR — calendar-day boundaries, never (now − then) ÷ 86400."""

    # Unlabelled (seat ruling 2026-10-16): data.json carries no age and yellow_after ≥ 1, so the
    # CLI cannot tell age 0 from age 1 — partial pinning is not row evidence. The exact integers
    # are guarded by test_calendar_age_exact_integers.
    def test_age_same_day_is_zero(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-AGE-CALENDAR#age-same-day-is-zero — source 2026-08-03, reference 2026-08-03
        → 0: counted (not excluded as future, which age < 0 would be — ⚖-R8), 🟢 under
        yellow_after 1."""
        config = given_probe(alex_copy, "2026-08-03", 1, 2)
        run = when_bake(config, "--evaluate", reference_date="2026-08-03")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep last_data_date", sleep["last_data_date"], "2026-08-03")
        verdict("self/sleep status", sleep["status"], "green")
        verdict("warnings naming self/sleep", warnings_for(run, "self/sleep"), [])

    # Unlabelled (seat ruling 2026-10-16): data.json carries no age and yellow_after ≥ 1, so the
    # CLI cannot tell age 0 from age 1 — partial pinning is not row evidence. The exact integers
    # are guarded by test_calendar_age_exact_integers.
    def test_age_yesterday_is_one(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-AGE-CALENDAR#age-yesterday-is-one — source 2026-08-02, reference 2026-08-03
        → 1: 🟢 under yellow_after 1 (age 2 would be 🟡), counted (not future)."""
        config = given_probe(alex_copy, "2026-08-02", 1, 2)
        run = when_bake(config, "--evaluate", reference_date="2026-08-03")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep last_data_date", sleep["last_data_date"], "2026-08-02")
        verdict("self/sleep status", sleep["status"], "green")

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_dst_spring_forward(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-AGE-CALENDAR#age-dst-spring-forward — a 23-hour local day increments the age
        by 1, not 0."""
        # Europe/Tallinn springs forward at 03:00 on 2026-03-29 (EET → EEST): local day 03-29 is
        # 23 h long, so 2026-03-28 → 2026-03-30 spans 47 elapsed hours. Calendar days: 2 (a
        # 47 h ÷ 24 floor says 1). Window 1/2: age 2 → 🟡, age 1 → 🟢.
        config = given_probe(alex_copy, "2026-03-28", 1, 2, zone=TALLINN)
        run = when_bake(config, "--evaluate", reference_date="2026-03-30")
        verdict("self/sleep status", item_of(run.data, "self/sleep")["status"], "yellow")

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_dst_fall_back(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-AGE-CALENDAR#age-dst-fall-back — a 25-hour local day increments the age by
        1, not 2."""
        # Europe/Tallinn falls back at 04:00 on 2026-10-25 (EEST → EET): local day 10-25 is 25 h
        # long. Calendar days 10-25 → 10-26: 1 (a 25 h ÷ 24 ceiling says 2). Window 1/2: age 1 →
        # 🟢, age 2 → 🟡.
        config = given_probe(alex_copy, "2026-10-25", 1, 2, zone=TALLINN)
        run = when_bake(config, "--evaluate", reference_date="2026-10-26")
        verdict("self/sleep status", item_of(run.data, "self/sleep")["status"], "green")

    @rule("CIR-DATA-AGE-CALENDAR")
    @pytest.mark.parametrize("host_tz", [
        pytest.param("UTC", id="CIR-DATA-AGE-CALENDAR#age-host-zone-irrelevant host TZ=UTC"),
        pytest.param("Pacific/Auckland",
                     id="CIR-DATA-AGE-CALENDAR#age-host-zone-irrelevant host TZ=Pacific/Auckland"),
    ])
    def test_age_host_zone_irrelevant(self, alex_copy: AlexCopy, host_tz: str) -> None:
        """The same config baked under TZ=UTC and TZ=Pacific/Auckland yields identical ages —
        both runs against the same expected values: the fixture's own (sleep 2026-08-01, age 2
        → 🟢; labs 2026-01-15, age 200 → 🔴)."""
        config = given_alex(alex_copy)
        with allure.step(f"Given: the bake host's TZ={host_tz}"):
            host = {"TZ": host_tz}
        run = when_bake(config, "--evaluate", env=host)
        verdict("self/sleep last_data_date, status",
                [item_of(run.data, "self/sleep")[k] for k in ("last_data_date", "status")],
                [SLEEP_NEWEST, "green"])
        verdict("self/labs last_data_date, status",
                [item_of(run.data, "self/labs")[k] for k in ("last_data_date", "status")],
                [LABS_NEWEST, "red"])
        # Every other light is the fixture's own too (fixtures/alex/circles.yaml comments).
        verdict("lights", {f"{r['id']}/{i['id']}": i["status"] for r in run.data["rings"] for i in r["items"]}, {
            "self/sleep": "green", "self/labs": "red", "self/exercise": "grey",
            "partner/date-night": "yellow", "children/nova": "green", "children/kit": "green",
            "wider/friends": "red", "wider/plants": "yellow",
        })

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_datetime_reduced_to_local_date(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-AGE-CALENDAR#age-datetime-reduced-to-local-date — source
        2026-08-02T23:30:00Z with timezone Pacific/Auckland → local date 2026-08-03 → age 0 on a
        2026-08-03 reference."""
        # August is NZST (UTC+12): 23:30Z on 08-02 is 11:30 on 08-03 in Auckland. Age 0: counted
        # (a 08-04 reading would be future-excluded), 🟢.
        config = given_probe(alex_copy, "2026-08-02T23:30:00Z", 7, 30, zone="Pacific/Auckland")
        run = when_bake(config, "--evaluate", reference_date="2026-08-03")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep last_data_date", sleep["last_data_date"], "2026-08-03")
        verdict("self/sleep status", sleep["status"], "green")
        verdict("warnings naming self/sleep", warnings_for(run, "self/sleep"), [])

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_year_boundary(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-AGE-CALENDAR#age-year-boundary — reference 2026-01-02, source 2025-12-29 → 4."""
        # 29→30→31→(Jan)1→2: four boundaries. Window 3/4: age 4 → 🟡 (3 → 🟢, 5 → 🔴).
        config = given_probe(alex_copy, "2025-12-29", 3, 4)
        run = when_bake(config, "--evaluate", reference_date="2026-01-02")
        verdict("self/sleep status", item_of(run.data, "self/sleep")["status"], "yellow")


# ===========================================================================
# CIR-DATA-FRESHNESS-WINDOW — the wired end-to-end case (predicate rows: test_resolve.py)
# ===========================================================================

class TestDataFreshnessWindowWired:
    """CIR-DATA-FRESHNESS-WINDOW — the fixture's labs case through the bake."""

    @rule("CIR-DATA-FRESHNESS-WINDOW")
    def test_window_far_past_red(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-FRESHNESS-WINDOW#window-far-past-red — the fixture's labs item: 2026-01-15
        against 2026-08-03 is 200 days (16+28+31+30+31+30+31+3) > red_after 190 → 🔴."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        labs = item_of(run.data, "self/labs")
        verdict("self/labs status", labs["status"], "red")
        verdict("self/labs grey_reason", labs["grey_reason"], None)
        verdict("self/labs last_data_date", labs["last_data_date"], LABS_NEWEST)
        verdict("self/labs detail_line", labs["detail_line"], f"act · last data {LABS_NEWEST}", op="contains")


class TestFixtureDatesRelativeToReference:
    """CIR-PROC-TEST-FIXTURES — boundary rows move the reference date, not the notes."""

    @rule("CIR-PROC-TEST-FIXTURES")
    @pytest.mark.parametrize("reference,light", [
        # sleep newest 2026-08-01, yellow_after 7: 08-08 is age 7 → still 🟢 (⚖-R6) …
        pytest.param("2026-08-08", "green",
                     id="CIR-PROC-TEST-FIXTURES#dates-relative-to-injected-reference on the boundary"),
        # … and 08-09 is age 8 → 🟡.
        pytest.param("2026-08-09", "yellow",
                     id="CIR-PROC-TEST-FIXTURES#dates-relative-to-injected-reference one day past"),
    ])
    def test_dates_relative_to_injected_reference(self, alex_copy: AlexCopy, reference: str,
                                                  light: str) -> None:
        """The reference date is set so the sleep entry lands on (or just past) the
        yellow_after boundary; the committed note is untouched."""
        committed = ALEX_DIR / "notes" / "sleep-log.md"
        before = hashlib.sha256(committed.read_bytes()).hexdigest()
        run = when_bake(given_alex(alex_copy), "--evaluate", reference_date=reference)
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep status", sleep["status"], light)
        verdict("self/sleep last_data_date", sleep["last_data_date"], SLEEP_NEWEST)
        verdict("sha256 of the committed fixtures/alex/notes/sleep-log.md",
                hashlib.sha256(committed.read_bytes()).hexdigest(), before)


# ===========================================================================
# CIR-DATA-FRESHNESS-EMPTY — a source with no usable dates (⚖-R31)
# ===========================================================================

class TestDataFreshnessEmpty:
    """CIR-DATA-FRESHNESS-EMPTY — ⚪ + warning, never a guessed 🔴."""

    @rule("CIR-DATA-FRESHNESS-EMPTY")
    def test_source_file_empty(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-FRESHNESS-EMPTY#source-file-empty — file exists, zero bytes → ⚪ + build
        warning."""
        config = given_alex(alex_copy, "self/sleep source: notes/zero-bytes.md",
                            sleep_source("notes/zero-bytes.md"))
        given_file(config, "notes/zero-bytes.md", "")
        message = then_sleep_failure(when_bake(config, "--evaluate"))
        verdict("self/sleep warning", message, "no dates found", op="contains")

    @rule("CIR-DATA-FRESHNESS-EMPTY")
    def test_source_no_parseable_dates(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-FRESHNESS-EMPTY#source-no-parseable-dates — notes/empty-log.md (a heading,
        no dated lines) → ⚪ + build warning."""
        config = given_alex(alex_copy, "self/sleep source: notes/empty-log.md",
                            sleep_source("notes/empty-log.md"))
        message = then_sleep_failure(when_bake(config, "--evaluate"))
        verdict("self/sleep warning", message, "no dates found", op="contains")


# ===========================================================================
# CIR-DATA-FRESHNESS-FUTURE — dates after the reference date (⚖-R8)
# ===========================================================================

class TestDataFreshnessFuture:
    """CIR-DATA-FRESHNESS-FUTURE — future dates are excluded, never clamped to 🟢."""

    @rule("CIR-DATA-FRESHNESS-FUTURE")
    def test_future_date_mixed(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-FRESHNESS-FUTURE#future-date-mixed — notes/future-date.md holds 2099-01-01
        and 2026-08-01; at reference 2026-08-03 the future one is excluded with a warning and the
        last-data date is 2026-08-01."""
        config = given_alex(alex_copy, "self/sleep source: notes/future-date.md",
                            sleep_source("notes/future-date.md"))
        run = when_bake(config, "--evaluate")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep last_data_date", sleep["last_data_date"], "2026-08-01")
        verdict("self/sleep status", sleep["status"], "green")  # age 2 ≤ 7 — not pinned by 2099
        verdict("self/sleep grey_reason", sleep["grey_reason"], None)
        messages = warnings_for(run, "self/sleep")
        verdict("warnings naming self/sleep", len(messages), 1)
        verdict("self/sleep warning", messages[0], "2099-01-01", op="contains")
        verdict("self/sleep warning", messages[0], "notes/future-date.md", op="contains")

    @rule("CIR-DATA-FRESHNESS-FUTURE")
    def test_future_date_tomorrow(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-FRESHNESS-FUTURE#future-date-tomorrow — a source dated one day ahead of the
        reference date is excluded with a warning, not treated as age 0."""
        # Reference 2026-07-31: the sleep-log's 2026-08-01 is tomorrow → excluded; the newest
        # remaining entry is 2026-07-31 → age 0 → 🟢 with last data 2026-07-31.
        run = when_bake(given_alex(alex_copy), "--evaluate", reference_date="2026-07-31")
        sleep = item_of(run.data, "self/sleep")
        verdict("self/sleep last_data_date", sleep["last_data_date"], "2026-07-31")
        verdict("self/sleep status", sleep["status"], "green")
        messages = warnings_for(run, "self/sleep")
        verdict("warnings naming self/sleep", len(messages), 1)
        verdict("self/sleep warning", messages[0], "2026-08-01", op="contains")

    @rule("CIR-DATA-FRESHNESS-FUTURE")
    def test_future_dates_only(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-FRESHNESS-FUTURE#future-dates-only — every parseable date in the future → ⚪
        + build warning."""
        # Reference 2026-07-29: all three sleep-log entries (07-30, 07-31, 08-01) are ahead.
        run = when_bake(given_alex(alex_copy), "--evaluate", reference_date="2026-07-29")
        message = then_sleep_failure(run)
        verdict("self/sleep warning", message, "after the reference date", op="contains")


# ===========================================================================
# CIR-ADAPT-COMMAND — the escape hatch, executed (issue #33 slice B)
# ===========================================================================
#
# Every command row drives a REAL subprocess: a small /bin/sh script written into the world copy,
# wider/plants re-pointed to it. Expected lights come from specs/data/adapters.md §CIR-ADAPT-COMMAND.

class TestAdaptCommand:
    """CIR-ADAPT-COMMAND — argv, config dir, first-line status word, exit code dominates."""

    @rule("CIR-ADAPT-COMMAND")
    def test_command_prints_yellow(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-prints-yellow — the fixture's plants script prints `yellow`
        → 🟡 under --evaluate at the fixture reference date."""
        run = when_bake(given_alex(alex_copy), "--evaluate")
        plants = item_of(run.data, "wider/plants")
        verdict("wider/plants status", plants["status"], "yellow")
        verdict("wider/plants grey_reason", plants["grey_reason"], None)
        verdict("warnings naming wider/plants", warnings_for(run, "wider/plants"), [])
        # command-cannot-set-a-data-date, on the fixture key example itself.
        verdict("wider/plants last_data_date", plants["last_data_date"], None)

    @rule("CIR-ADAPT-COMMAND")
    def test_command_not_shell_interpreted(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-not-shell-interpreted — `["./x.sh", "a b", "*", "$HOME"]`
        arrives as three arguments, verbatim: no word split, no glob, no $VAR expansion."""
        with allure.step("Given: the bake's environment holds HOME=/should-not-expand"):
            host = {"HOME": "/should-not-expand"}
        config = plants_command(
            alex_copy,
            '[ "$#" = 3 ] && [ "$1" = "a b" ] && [ "$2" = "*" ] && [ "$3" = \'$HOME\' ] '
            "&& echo green && exit 0\nexit 9\n",
            "a b", "*", "$HOME",
        )
        run = when_bake(config, "--evaluate", env=host)
        # Verbatim argv → the script's own check passes → it prints green → 🟢 (else exit 9 → ⚪).
        verdict("wider/plants status", item_of(run.data, "wider/plants")["status"], "green")

    @rule("CIR-ADAPT-COMMAND")
    def test_command_cwd_is_config_dir(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-cwd-is-config-dir — `./notes/…` resolves, and the process
        runs, under <config-dir> wherever the bake itself was started."""
        # The bake is started from the config dir's PARENT (when_bake's cwd), so only a
        # command run under <config-dir> finds both files and prints green.
        config = plants_command(alex_copy, "[ -f ./circles.yaml ] && [ -f ./notes/plants-status.sh ] "
                                           "&& echo green && exit 0\nexit 9\n")
        run = when_bake(config, "--evaluate")
        verdict("wider/plants status", item_of(run.data, "wider/plants")["status"], "green")

    @rule("CIR-ADAPT-COMMAND")
    @pytest.mark.parametrize("body,light", [
        pytest.param("printf ' GREEN\\n'\n", "green",
                     id="CIR-ADAPT-COMMAND#command-stdout-trimmed-and-folded"),
        pytest.param("printf '\\n  \\nred\\n'\n", "red",
                     id="CIR-ADAPT-COMMAND#command-first-non-empty-line-wins"),
        pytest.param("echo yellow\ni=0\nwhile [ $i -lt 40 ]; do echo \"diag $i: green\"; "
                     "i=$((i+1)); done\n", "yellow",
                     id="CIR-ADAPT-COMMAND#command-extra-output-ignored"),
    ])
    def test_command_stdout_words(self, alex_copy: AlexCopy, body: str, light: str) -> None:
        """The first non-empty stdout line, trimmed and case-folded, is the light; the rest of
        stdout is free (rows cited per param)."""
        run = when_bake(plants_command(alex_copy, body), "--evaluate")
        verdict("wider/plants status", item_of(run.data, "wider/plants")["status"], light)
        verdict("warnings naming wider/plants", warnings_for(run, "wider/plants"), [])

    @rule("CIR-ADAPT-COMMAND")
    def test_command_unknown_word(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-unknown-word — prints `amber` → ⚪ + warning naming the word."""
        run = when_bake(plants_command(alex_copy, "echo amber\n"), "--evaluate")
        verdict("wider/plants warning", then_plants_failure(run), "amber", op="contains")

    @rule("CIR-ADAPT-COMMAND")
    def test_command_empty_stdout(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-empty-stdout — `""`, exit 0 → ⚪ + warning."""
        then_plants_failure(when_bake(plants_command(alex_copy, "exit 0\n"), "--evaluate"))

    @rule("CIR-ADAPT-COMMAND")
    def test_command_nonzero_exit_dominates(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-nonzero-exit-dominates — prints `red`, exits 1 → ⚪ +
        warning: the exit code wins over stdout (and a failure is never 🔴)."""
        run = when_bake(plants_command(alex_copy, "echo red\nexit 1\n"), "--evaluate")
        verdict("wider/plants warning", then_plants_failure(run), "1", op="contains")

    @rule("CIR-ADAPT-COMMAND")
    def test_command_stderr_not_on_the_page(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-stderr-not-on-the-page — a stack trace on stderr never
        reaches the warning, which stays a bounded summary."""
        body = ('echo "Traceback: File /home/alex/secret/probe.py line 3" >&2\n'
                'echo "PLANTS_API_TOKEN=hunter2" >&2\nexit 2\n')
        run = when_bake(plants_command(alex_copy, body), "--evaluate")
        message = then_plants_failure(run)
        stderr_words = ["Traceback", "/home/alex", "hunter2", "PLANTS_API_TOKEN"]
        leaked = {name: [w for w in stderr_words if w in (run.out_dir / name).read_text(encoding="utf-8")]
                  for name in ("data.json", "index.html")}
        verdict("stderr words found in out/data.json, out/index.html", leaked,
                {"data.json": [], "index.html": []})
        verdict(f"wider/plants warning length ≤ {WARNING_MAX_CHARS}", len(message) <= WARNING_MAX_CHARS, True)

    @rule("CIR-ADAPT-COMMAND")
    def test_command_cannot_set_a_data_date(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-cannot-set-a-data-date — even a script that prints a date
        after its word gets no "last data" segment (⚖-R32 rules the first word only)."""
        run = when_bake(plants_command(alex_copy, "echo green\necho date=2026-08-01\n"), "--evaluate")
        plants = item_of(run.data, "wider/plants")
        verdict("wider/plants status", plants["status"], "green")
        verdict("wider/plants last_data_date", plants["last_data_date"], None)
        verdict("wider/plants detail_line", plants["detail_line"], "last data", op="not contains")


# ===========================================================================
# CIR-ADAPT-BUDGET — time and blast radius
# ===========================================================================
#
# ⚖-R21 fixes 30 s per item and 5 min per bake; the timing rows shrink them with given_leash
# (never sleep for real) and an unlabelled unit guard pins the production values.

def _pid_alive(pid: int) -> bool:
    """True while *pid* exists and is not a zombie (a killed orphan may linger as Z)."""
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, ProcessLookupError):
        return False
    return state != "Z"


def _wait_dead(pid: int, within: float = 3.0) -> bool:
    end = time.monotonic() + within
    while time.monotonic() < end:
        if not _pid_alive(pid):
            return True
        time.sleep(0.05)
    return not _pid_alive(pid)


class TestAdaptBudget:
    """CIR-ADAPT-BUDGET — per-item timeout, process group, total budget, environment."""

    @rule("CIR-ADAPT-BUDGET")
    def test_command_per_item_timeout(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-BUDGET#command-per-item-timeout — a command sleeping past the per-item
        timeout is killed; ⚪ + warning naming the timeout."""
        leash: dict[str, str] = {}
        config = plants_command(alex_copy, "sleep 20\necho green\n",
                                note=" (leash: COMMAND_TIMEOUT_SECONDS 0.5)",
                                world=leashed(leash, COMMAND_TIMEOUT_SECONDS=0.5))
        started = time.monotonic()
        run = when_bake(config, "--evaluate", env=leash)
        elapsed = time.monotonic() - started
        verdict("wider/plants warning", then_plants_failure(run), "timed out", op="contains")
        # Killed at ~0.5 s, far short of the script's own 20 s.
        verdict("bake wall time < 10 s", elapsed < 10, True)

    @rule("CIR-ADAPT-BUDGET")
    @pytest.mark.parametrize("ends,light", [
        pytest.param("exits", "green", id="command exits, child lingers"),
        pytest.param("times out", "grey", id="command times out"),
    ])
    def test_command_children_killed(self, alex_copy: AlexCopy, ends: str, light: str) -> None:
        """CIR-ADAPT-BUDGET#command-children-killed — a child that would outlive its command is
        terminated with the process group, whether the command exits or times out."""
        # The script backgrounds a 60 s child, records its pid in child.pid (relative: the
        # command's cwd is the config dir), then exits with `green` or sleeps past the leash.
        tail = "echo green\n" if ends == "exits" else "sleep 20\n"
        leash = "" if ends == "exits" else " (leash: COMMAND_TIMEOUT_SECONDS 0.5)"
        env: dict[str, str] = {}
        knob = None if ends == "exits" else leashed(env, COMMAND_TIMEOUT_SECONDS=0.5)
        config = plants_command(alex_copy, 'sleep 60 >/dev/null 2>&1 &\necho $! > "$1"\n' + tail,
                                "child.pid", note=f", command {ends}{leash}", world=knob)
        run = when_bake(config, "--evaluate", env=env)
        child = int((config.parent / "child.pid").read_text().strip())
        verdict(f"the command's child (pid from child.pid) alive after the {ends} command",
                not _wait_dead(child), False)
        verdict("wider/plants status", item_of(run.data, "wider/plants")["status"], light)

    @rule("CIR-ADAPT-BUDGET")
    def test_bake_total_budget(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-BUDGET#bake-total-budget — many slow adapters: the bake ends within the
        total budget; every item left unresolved is ⚪ + warning."""
        slow = ["self/sleep", "self/labs", "wider/plants"]

        def edit(c: dict) -> None:
            for ref in slow:
                item(c, ref)["status"] = {"command": ["./notes/slow.sh"]}
        leash: dict[str, str] = {}
        config = given_alex(alex_copy, f"{', '.join(slow)} command: ['./notes/slow.sh'] "
                                       "(leash: BAKE_BUDGET_SECONDS 1)", edit,
                            world=leashed(leash, BAKE_BUDGET_SECONDS=1.0))
        given_script(config, "notes/slow.sh", "sleep 20\necho green\n")
        started = time.monotonic()
        run = when_bake(config, "--evaluate", env=leash)
        elapsed = time.monotonic() - started
        # Three 20 s commands under a 1 s budget: the bake ends near 1 s, not 60 s.
        verdict("bake wall time < 10 s", elapsed < 10, True)
        verdict("status, grey_reason of the slow items",
                {ref: [item_of(run.data, ref)["status"], item_of(run.data, ref)["grey_reason"]] for ref in slow},
                {ref: ["grey", "by-failure"] for ref in slow})
        verdict("warnings naming 'budget', per slow item",
                {ref: sum("budget" in m for m in warnings_for(run, ref)) for ref in slow},
                {ref: 1 for ref in slow})
        # Adapter-free cells still resolve: manual lights are not budgeted work.
        verdict("wider/friends status", item_of(run.data, "wider/friends")["status"], "red")

    @rule("CIR-ADAPT-BUDGET")
    def test_environment_not_inherited_wholesale(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-BUDGET#environment-not-inherited-wholesale — the bake's env holds a token;
        the command receives a minimal, explicit environment without it."""
        with allure.step("Given: the bake's environment holds CIRCLES_REGISTRY_TOKEN=s3cret-token "
                         "and KUBECONFIG=/home/alex/.kube/config"):
            host = {"CIRCLES_REGISTRY_TOKEN": "s3cret-token", "KUBECONFIG": "/home/alex/.kube/config"}
        config = plants_command(alex_copy, 'env > "$1"\necho green\n', "env.txt")
        run = when_bake(config, "--evaluate", env=host)
        seen = (config.parent / "env.txt").read_text()
        verdict("wider/plants status", item_of(run.data, "wider/plants")["status"], "green")
        # verdict()'s shape by hand, so the command's env.txt attaches under the claim it supports.
        with allure.step("Then: the command's env (env.txt) not contains 's3cret-token'"):
            allure.attach(seen, name="env.txt (the command's environment)",
                          attachment_type=allure.attachment_type.TEXT)
            assert "s3cret-token" not in seen, "the bake's token reached the command"
        names = {line.split("=", 1)[0] for line in seen.splitlines() if "=" in line}
        # /bin/sh itself adds PWD (and some shells SHLVL, _); everything else is the bake's
        # explicit set — no CIRCLES_REGISTRY_TOKEN, KUBECONFIG, HOME or PYTHONPATH.
        verdict("the command's env names (beyond the shell's own PWD/SHLVL/_/OLDPWD)",
                sorted(names - {"PWD", "SHLVL", "_", "OLDPWD"}), ["LANG", "PATH", "TZ"])
        verdict("the command's TZ", f"TZ={run.data['timezone']}" in seen.splitlines(), True)


# ===========================================================================
# Unlabelled unit guards — internals the CLI cases do not reach (CONVENTIONS § Allure taxonomy:
# unit tests stay unlabelled and are never evidence)
# ===========================================================================

def _elapsed_hours(start: datetime, end: datetime) -> float:
    """Real elapsed hours between two instants (the quantity a naive ÷ 86400 age would use)."""
    return (end.timestamp() - start.timestamp()) / 3600


@pytest.mark.parametrize("text,tz_name,found", [
    ("2026-08-01", "UTC", [date(2026, 8, 1)]),
    ("- 2026-08-01 — 7h20m", "UTC", [date(2026, 8, 1)]),
    ("## Session on 2026-08-01 (evening)", "UTC", [date(2026, 8, 1)]),
    ("2026-08-01T22:10:00+03:00", "Europe/Tallinn", [date(2026, 8, 1)]),
    ("03/04/2026", "UTC", []),
    ("1 August 2026", "UTC", []),
    ("v2026-08-01-rc1 and id=2026-08-013", "UTC", []),
])
def test_scan_dates_tokens(text: str, tz_name: str, found: list[date]) -> None:
    """scan_dates: the CIR-DATA-DATE-PARSE tokens → found dates, nothing rejected."""
    assert scan_dates(text, tz_name) == (found, [])


def test_scan_dates_impossible_calendar_is_rejected() -> None:
    """scan_dates: 2026-02-30 lands in the rejected list (the warning's source)."""
    assert scan_dates("2026-02-30", "UTC") == ([], ["2026-02-30"])


def test_scan_dates_datetime_reduced_in_the_config_zone() -> None:
    """scan_dates: the same instant is 08-03 in Auckland, 08-02 in UTC — the config's zone decides."""
    assert scan_dates("2026-08-02T23:30:00Z", "Pacific/Auckland") == ([date(2026, 8, 3)], [])
    assert scan_dates("2026-08-02T23:30:00Z", "UTC")[0] == [date(2026, 8, 2)]


def test_calendar_age_exact_integers() -> None:
    """calendar_age: the CIR-DATA-AGE-CALENDAR rows' exact integers (the CLI shows only lights)."""
    assert calendar_age(date(2026, 8, 3), date(2026, 8, 3)) == 0     # same day
    assert calendar_age(date(2026, 8, 2), date(2026, 8, 3)) == 1     # yesterday
    assert calendar_age(date(2025, 12, 29), date(2026, 1, 2)) == 4   # year boundary
    assert calendar_age(date(2026, 1, 15), FIXTURE_REFERENCE_DATE) == 200  # fixture labs
    assert calendar_age(date(2026, 8, 3), date(2026, 8, 2)) == -1    # future is negative


def test_calendar_age_across_dst() -> None:
    """calendar_age over Europe/Tallinn's 23 h and 25 h days counts days, not hours."""
    zone = ZoneInfo(TALLINN)
    # Spring forward 2026-03-29 (EET → EEST): 23 h day; 28→30 is 47 h.
    assert _elapsed_hours(datetime(2026, 3, 29, tzinfo=zone), datetime(2026, 3, 30, tzinfo=zone)) == 23
    assert _elapsed_hours(datetime(2026, 3, 28, tzinfo=zone), datetime(2026, 3, 30, tzinfo=zone)) == 47
    assert calendar_age(date(2026, 3, 29), date(2026, 3, 30)) == 1
    assert calendar_age(date(2026, 3, 28), date(2026, 3, 30)) == 2
    # Fall back 2026-10-25 (EEST → EET): 25 h day.
    assert _elapsed_hours(datetime(2026, 10, 25, tzinfo=zone), datetime(2026, 10, 26, tzinfo=zone)) == 25
    assert calendar_age(date(2026, 10, 25), date(2026, 10, 26)) == 1


def test_age_ignores_time_of_day() -> None:
    """CIR-DATA-AGE-CALENDAR#age-ignores-time-of-day as a unit guard: the row's input is the
    bake's wall-clock instant, which the CLI only exposes through --reference-date (that pins
    the day, so time of day cannot reach it). 00:05 and 23:55 local → the same reference date
    and identical rings."""
    zone = ZoneInfo(TALLINN)
    ref_early = default_reference_date(TALLINN, datetime(2026, 8, 3, 0, 5, tzinfo=zone))
    ref_late = default_reference_date(TALLINN, datetime(2026, 8, 3, 23, 55, tzinfo=zone))
    assert ref_early == ref_late == date(2026, 8, 3)
    assert calendar_age(date(2026, 8, 1), ref_early) == calendar_age(date(2026, 8, 1), ref_late) == 2
    config = load_config(ALEX_YAML)
    rings = [resolve(config, reference_date=r, generated_at=FIXTURE_GENERATED_AT, evaluate=True)["rings"]
             for r in (ref_early, ref_late)]
    assert rings[0] == rings[1]
    sleep = next(i for r in rings[0] if r["id"] == "self" for i in r["items"] if i["id"] == "sleep")
    assert sleep["status"] == "green"


@pytest.mark.parametrize("status", [
    pytest.param("grey", id="grey as a wire value"),
    pytest.param("unmonitored", id="grey as its display word"),
    pytest.param("", id="empty string"),
    pytest.param(None, id="no status at all"),
])
def test_adapter_result_cannot_be_grey(status: str | None) -> None:
    """AdapterResult (CIR-ADAPT-CONTRACT#adapter-cannot-return-grey's type-level half): grey, or
    any non-light, is not constructible as an adapter answer."""
    with pytest.raises(ValueError):
        AdapterResult(status=status, data_date=date(2026, 8, 1))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        AdapterResult.ok(status, date(2026, 8, 1))  # type: ignore[arg-type]
    # The two legal shapes, for contrast.
    assert AdapterResult.ok("green", date(2026, 8, 1)).failure is None
    assert AdapterResult.failed("missing source: x").status is None
    # A failure with a light, a light without a date, an empty failure: all rejected.
    with pytest.raises(ValueError):
        AdapterResult(status="green", data_date=date(2026, 8, 1), failure="x")
    with pytest.raises(ValueError):
        AdapterResult(status="green")
    with pytest.raises(ValueError):
        AdapterResult.failed("   ")


def test_budget_constants_are_the_ruling() -> None:
    """⚖-R21 (CIR-ADAPT-BUDGET): 30 s per item, 5 min per bake, fixed — the boundary cases
    shrink these via given_leash, so the production values are pinned here."""
    assert adapters_module.COMMAND_TIMEOUT_SECONDS == 30
    assert adapters_module.BAKE_BUDGET_SECONDS == 5 * 60
