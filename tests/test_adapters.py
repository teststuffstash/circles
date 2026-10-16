# Tests for bake/adapters.py — the freshness adapter under `evaluate=True` (issue #33 slice A)
#
# Every decision-table row of every fully-owned requirement has a citing test, the row id
# (CIR-<AREA>-<NAME>#<row-id>) cited verbatim in the docstring's first line or the
# pytest.param id. Expected values are computed in comments FROM the inputs and the spec
# (specs/data/freshness.md, specs/data/adapters.md), never by running the code.
#
# Inputs come from fixtures/alex at runtime via the `alex_copy` factory (tests/conftest.py):
# a tmp copy with the sleep item's `source:` re-pointed. Fixture reference date = 2026-08-03;
# date-sensitive rows vary the INJECTED reference date, never the committed dates.

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import pytest

import bake.adapters as adapters_module
from bake.__main__ import default_reference_date
from bake.adapters import AdapterResult, calendar_age, scan_dates
from bake.config import load_config
from bake.resolve import resolve

from rules import rule

AlexCopy = Callable[..., Path]  # the `alex_copy` factory fixture (tests/conftest.py)
ALEX_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "alex"
ALEX_YAML = ALEX_DIR / "circles.yaml"
FIXTURE_REFERENCE_DATE = date(2026, 8, 3)
FIXTURE_GENERATED_AT = datetime(2026, 8, 3, 2, 0, 0, tzinfo=timezone.utc)

# The fixture person's committed source dates (fixtures/alex/notes/*.md) — read here as the
# CONTRACT inputs the expectations below are derived from, not rewritten.
SLEEP_NEWEST = date(2026, 8, 1)      # notes/sleep-log.md: 2026-08-01, 2026-07-31, 2026-07-30
SLEEP_OLDEST = date(2026, 7, 30)
LABS_NEWEST = date(2026, 1, 15)      # notes/labs.md
# circles.yaml thresholds: sleep yellow_after 7 / red_after 30; labs 100 / 190.


def _evaluate(config_path: Path, reference_date: date = FIXTURE_REFERENCE_DATE) -> dict:
    """Resolve *config_path* with the freshness adapter ON."""
    return resolve(
        load_config(config_path),
        reference_date=reference_date,
        generated_at=FIXTURE_GENERATED_AT,
        evaluate=True,
    )


def _item(artifact: dict, ring_id: str, item_id: str) -> dict:
    for ring in artifact["rings"]:
        if ring["id"] == ring_id:
            for item in ring["items"]:
                if item["id"] == item_id:
                    return item
    raise KeyError(f"{ring_id}/{item_id}")


def _warnings_for(artifact: dict, ref: str) -> list[str]:
    return [w["message"] for w in artifact["warnings"] if w["item"] == ref]


def _assert_grey_by_failure(artifact: dict, ref: str = "self/sleep") -> list[str]:
    """CIR-DATA-FAILURE-IS-GREY shape: ⚪ by-failure, no data date, one warning naming the item,
    and the failure text as the detail line's reason segment (⚖-R51)."""
    ring_id, item_id = ref.split("/")
    item = _item(artifact, ring_id, item_id)
    assert item["status"] == "grey"
    assert item["grey_reason"] == "by-failure"
    assert item["last_data_date"] is None
    messages = _warnings_for(artifact, ref)
    assert len(messages) == 1, messages
    assert messages[0] in item["detail_line"]
    assert item["detail_line"].startswith(item["guardrail"] + " · unmonitored · ")
    return messages


# ===========================================================================
# CIR-ADAPT-FRESHNESS — dates in files (interface-level obligations)
# ===========================================================================

class TestAdaptFreshness:
    """CIR-ADAPT-FRESHNESS — dates in files."""

    @rule("CIR-ADAPT-FRESHNESS")
    def test_freshness_reads_never_executes(self, alex_copy: AlexCopy, tmp_path: Path) -> None:
        """CIR-ADAPT-FRESHNESS#freshness-reads-never-executes —
        a source: that is an executable script is read as text, not run."""
        # A copy of the fixture script under its own name: wider/plants legitimately RUNS
        # plants-status.sh under --evaluate (slice B), so the marker must belong to a
        # script that only the freshness source points at.
        config_path = alex_copy(sleep_source="notes/source-script.sh")
        # The fixture script prints `yellow`; give the copy a side effect that only
        # execution would produce.
        marker = tmp_path / "script-was-run.marker"
        notes = config_path.parent / "notes"
        script = notes / "source-script.sh"
        script.write_text((notes / "plants-status.sh").read_text() + f"touch {marker}\n")
        script.chmod(0o755)

        artifact = _evaluate(config_path)

        assert not marker.exists(), "the freshness adapter executed its source"
        # Read as text, the script holds no ISO date → ⚪ by-failure, never the `yellow`
        # the script would have printed.
        item = _item(artifact, "self", "sleep")
        assert item["status"] != "yellow"
        messages = _assert_grey_by_failure(artifact)
        assert "no dates found" in messages[0]

    @rule("CIR-ADAPT-FRESHNESS")
    def test_freshness_reports_its_data_date(self) -> None:
        """CIR-ADAPT-FRESHNESS#freshness-reports-its-data-date —
        newest date 2026-08-01 → last_data_date 2026-08-01, 'last data 2026-08-01' in the
        detail line."""
        item = _item(_evaluate(ALEX_YAML), "self", "sleep")
        assert item["last_data_date"] == SLEEP_NEWEST.isoformat()
        assert f"last data {SLEEP_NEWEST.isoformat()}" in item["detail_line"]

    @rule("CIR-ADAPT-FRESHNESS")
    def test_freshness_sandboxed_to_config_dir(self, alex_copy: AlexCopy, tmp_path: Path) -> None:
        """CIR-ADAPT-FRESHNESS#freshness-sandboxed-to-config-dir —
        a glob hit that resolves outside the config directory (a symlink out) is never
        read: missing source, and the warning names neither host path."""
        config_path = alex_copy(sleep_source="notes/esc*.md")
        outside = tmp_path / "outside-the-config-dir.md"
        shutil.copy(ALEX_DIR / "notes" / "sleep-log.md", outside)
        (config_path.parent / "notes" / "escape.md").symlink_to(outside)

        artifact = _evaluate(config_path)

        messages = _assert_grey_by_failure(artifact)
        assert "missing source" in messages[0]
        assert "notes/esc*.md" in messages[0]
        assert str(tmp_path) not in messages[0]


# ===========================================================================
# CIR-DATA-SOURCE-PATH — evaluation rows (config-error rows live in test_config.py)
# ===========================================================================

class TestDataSourcePathEvaluation:
    """CIR-DATA-SOURCE-PATH — where sources are read from (evaluation rows)."""

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_single_file(self) -> None:
        """CIR-DATA-SOURCE-PATH#source-single-file —
        source: notes/sleep-log.md exists → its dates are read (newest 2026-08-01)."""
        item = _item(_evaluate(ALEX_YAML), "self", "sleep")
        assert item["last_data_date"] == SLEEP_NEWEST.isoformat()
        # age 2 ≤ yellow_after 7 → 🟢
        assert item["status"] == "green"

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_glob_union(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-glob-union —
        notes/lab-*.md matching 3 files → the newest date across the union wins."""
        config_path = alex_copy(sleep_source="notes/lab-*.md")
        notes = config_path.parent / "notes"
        # Three matches built from the fixture's own notes: newest dates 2026-01-15
        # (labs), 2026-08-01 (sleep-log), none (empty-log) → union newest 2026-08-01.
        shutil.copy(notes / "labs.md", notes / "lab-1.md")
        shutil.copy(notes / "sleep-log.md", notes / "lab-2.md")
        shutil.copy(notes / "empty-log.md", notes / "lab-3.md")

        item = _item(_evaluate(config_path), "self", "sleep")
        assert item["last_data_date"] == SLEEP_NEWEST.isoformat()
        assert item["status"] == "green"  # age 2 ≤ 7

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_glob_no_match(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-glob-no-match — glob matches zero files → ⚪ +
        build warning (missing source)."""
        artifact = _evaluate(alex_copy(sleep_source="notes/lab-*.md"))
        messages = _assert_grey_by_failure(artifact)
        assert "missing source" in messages[0]
        assert "notes/lab-*.md" in messages[0]

    @rule("CIR-DATA-SOURCE-PATH")
    def test_source_path_missing(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-path-missing — path does not exist → ⚪ + build
        warning (missing source)."""
        artifact = _evaluate(alex_copy(sleep_source="notes/absent.md"))
        messages = _assert_grey_by_failure(artifact)
        assert "missing source" in messages[0]
        assert "notes/absent.md" in messages[0]

    @rule("CIR-DATA-SOURCE-PATH")
    @pytest.mark.skipif(os.geteuid() == 0, reason="root reads mode-000 files")
    def test_source_unreadable(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-SOURCE-PATH#source-unreadable — file exists, permission denied → ⚪ +
        build warning."""
        config_path = alex_copy()
        note = config_path.parent / "notes" / "sleep-log.md"
        note.chmod(0o000)
        try:
            artifact = _evaluate(config_path)
        finally:
            note.chmod(0o644)
        messages = _assert_grey_by_failure(artifact)
        assert "unreadable source" in messages[0]
        assert "notes/sleep-log.md" in messages[0]


# ===========================================================================
# CIR-DATA-DATE-PARSE — which date tokens count
# ===========================================================================

class TestDataDateParse:
    """CIR-DATA-DATE-PARSE — ISO-8601 only (⚖-R27)."""

    @rule("CIR-DATA-DATE-PARSE")
    @pytest.mark.parametrize("text,tz_name,expected", [
        pytest.param("2026-08-01", "UTC", [date(2026, 8, 1)],
                     id="CIR-DATA-DATE-PARSE#date-iso-calendar"),
        pytest.param("- 2026-08-01 — 7h20m", "UTC", [date(2026, 8, 1)],
                     id="CIR-DATA-DATE-PARSE#date-anywhere-in-line"),
        pytest.param("## Session on 2026-08-01 (evening)", "UTC", [date(2026, 8, 1)],
                     id="CIR-DATA-DATE-PARSE#date-heading-prose"),
        # 22:10 at +03:00 is 22:10 Europe/Tallinn (EEST = UTC+3) → local date 2026-08-01
        pytest.param("2026-08-01T22:10:00+03:00", "Europe/Tallinn", [date(2026, 8, 1)],
                     id="CIR-DATA-DATE-PARSE#date-datetime-form"),
        pytest.param("03/04/2026", "UTC", [],
                     id="CIR-DATA-DATE-PARSE#date-slash-format"),
        pytest.param("1 August 2026", "UTC", [],
                     id="CIR-DATA-DATE-PARSE#date-written-month"),
        pytest.param("v2026-08-01-rc1 and id=2026-08-013", "UTC", [],
                     id="CIR-DATA-DATE-PARSE#date-iso-substring"),
    ])
    def test_token_recognition(self, text: str, tz_name: str, expected: list[date]) -> None:
        """A row's literal input → exactly the dates the spec says are recognised."""
        found, rejected = scan_dates(text, tz_name)
        assert found == expected
        assert rejected == []

    @rule("CIR-DATA-DATE-PARSE")
    def test_date_impossible_calendar(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-DATE-PARSE#date-impossible-calendar — 2026-02-30 is ignored, with a
        warning naming the (config-relative) file."""
        found, rejected = scan_dates("2026-02-30", "UTC")
        assert found == []
        assert rejected == ["2026-02-30"]

        # End to end: a source holding only the row's token → no usable date → ⚪, and
        # the warning names the token and the file relative to the config dir.
        config_path = alex_copy(sleep_source="notes/impossible.md")
        (config_path.parent / "notes" / "impossible.md").write_text("2026-02-30\n")
        artifact = _evaluate(config_path)
        messages = _assert_grey_by_failure(artifact)
        assert "2026-02-30" in messages[0]
        assert "notes/impossible.md" in messages[0]
        assert str(config_path.parent) not in messages[0]

    @rule("CIR-DATA-DATE-PARSE")
    def test_date_newest_wins(self) -> None:
        """CIR-DATA-DATE-PARSE#date-newest-wins — the fixture's sleep-log holds 2026-07-30,
        2026-08-01, 2026-07-31 (in that file order) → last-data date 2026-08-01."""
        item = _item(_evaluate(ALEX_YAML), "self", "sleep")
        assert item["last_data_date"] == "2026-08-01"

    @rule("CIR-DATA-DATE-PARSE")
    def test_date_none_parseable(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-DATE-PARSE#date-none-parseable — prose with no ISO dates
        (notes/empty-log.md) → ⚪ + warning, never 🟢."""
        artifact = _evaluate(alex_copy(sleep_source="notes/empty-log.md"))
        item = _item(artifact, "self", "sleep")
        assert item["status"] != "green"
        messages = _assert_grey_by_failure(artifact)
        assert "no dates found" in messages[0]
        assert "notes/empty-log.md" in messages[0]


# ===========================================================================
# CIR-DATA-AGE-CALENDAR — age is calendar days in the config's timezone
# ===========================================================================

TALLINN = "Europe/Tallinn"


def _elapsed_hours(start: datetime, end: datetime) -> float:
    """Real elapsed hours between two instants (the quantity a naive ÷ 86400 age would use)."""
    return (end.timestamp() - start.timestamp()) / 3600


class TestDataAgeCalendar:
    """CIR-DATA-AGE-CALENDAR — calendar-day boundaries, never (now − then) ÷ 86400."""

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_same_day_is_zero(self) -> None:
        """CIR-DATA-AGE-CALENDAR#age-same-day-is-zero — source 2026-08-03, reference
        2026-08-03 → 0."""
        assert calendar_age(date(2026, 8, 3), date(2026, 8, 3)) == 0

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_yesterday_is_one(self) -> None:
        """CIR-DATA-AGE-CALENDAR#age-yesterday-is-one — source 2026-08-02, reference
        2026-08-03 → 1."""
        assert calendar_age(date(2026, 8, 2), date(2026, 8, 3)) == 1

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_ignores_time_of_day(self) -> None:
        """CIR-DATA-AGE-CALENDAR#age-ignores-time-of-day — a date-only source baked at 00:05
        or 23:55 local ages the same both times."""
        zone = ZoneInfo(TALLINN)
        # Both instants fall on local 2026-08-03; the sleep-log's newest entry is
        # 2026-08-01 → age 2 either way (and 🟢: 2 ≤ yellow_after 7).
        early = datetime(2026, 8, 3, 0, 5, tzinfo=zone)
        late = datetime(2026, 8, 3, 23, 55, tzinfo=zone)
        ref_early = default_reference_date(TALLINN, early)
        ref_late = default_reference_date(TALLINN, late)
        assert ref_early == ref_late == date(2026, 8, 3)
        assert calendar_age(SLEEP_NEWEST, ref_early) == calendar_age(SLEEP_NEWEST, ref_late) == 2
        config = load_config(ALEX_YAML)
        rings = [
            resolve(config, reference_date=r, generated_at=FIXTURE_GENERATED_AT, evaluate=True)["rings"]
            for r in (ref_early, ref_late)
        ]
        assert rings[0] == rings[1]
        assert _item({"rings": rings[0]}, "self", "sleep")["status"] == "green"

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_dst_spring_forward(self) -> None:
        """CIR-DATA-AGE-CALENDAR#age-dst-spring-forward — a 23-hour local day increments the
        age by 1, not 0."""
        zone = ZoneInfo(TALLINN)
        # Europe/Tallinn springs forward at 03:00 on 2026-03-29 (EET → EEST), so the
        # local day 2026-03-29 is 23 hours long: midnight 03-29 → midnight 03-30 is 23
        # elapsed hours, and midnight 03-28 → midnight 03-30 is 47.
        # (elapsed via timestamps: same-zone aware subtraction is wall-clock arithmetic)
        assert _elapsed_hours(datetime(2026, 3, 29, tzinfo=zone), datetime(2026, 3, 30, tzinfo=zone)) == 23
        assert _elapsed_hours(datetime(2026, 3, 28, tzinfo=zone), datetime(2026, 3, 30, tzinfo=zone)) == 47
        # Calendar days: 29→30 = 1 (a 23 h ÷ 24 floor would say 0); 28→30 = 2 (47 h → 1).
        assert calendar_age(date(2026, 3, 29), date(2026, 3, 30)) == 1
        assert calendar_age(date(2026, 3, 28), date(2026, 3, 30)) == 2

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_dst_fall_back(self) -> None:
        """CIR-DATA-AGE-CALENDAR#age-dst-fall-back — a 25-hour local day increments the age
        by 1, not 2."""
        zone = ZoneInfo(TALLINN)
        # Europe/Tallinn falls back at 04:00 on 2026-10-25 (EEST → EET), so the local day
        # 2026-10-25 is 25 hours long: midnight 10-25 → midnight 10-26 is 25 elapsed hours.
        assert _elapsed_hours(datetime(2026, 10, 25, tzinfo=zone), datetime(2026, 10, 26, tzinfo=zone)) == 25
        # Calendar days: 1 (a 25 h ÷ 24 ceiling would say 2).
        assert calendar_age(date(2026, 10, 25), date(2026, 10, 26)) == 1

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_host_zone_irrelevant(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CIR-DATA-AGE-CALENDAR#age-host-zone-irrelevant — the same config baked under
        TZ=UTC and TZ=Pacific/Auckland yields identical ages."""
        config = load_config(ALEX_YAML)
        rings_by_tz: dict[str, list] = {}
        for host_tz in ("UTC", "Pacific/Auckland"):
            monkeypatch.setenv("TZ", host_tz)
            time.tzset()
            try:
                artifact = resolve(
                    config, reference_date=FIXTURE_REFERENCE_DATE,
                    generated_at=FIXTURE_GENERATED_AT, evaluate=True,
                )
            finally:
                monkeypatch.delenv("TZ")
                time.tzset()
            rings_by_tz[host_tz] = artifact["rings"]
        assert rings_by_tz["UTC"] == rings_by_tz["Pacific/Auckland"]
        # And the ages are the fixture's: sleep 2026-08-01 (age 2 → 🟢), labs 2026-01-15
        # (age 200 → 🔴), under both host zones.
        for rings in rings_by_tz.values():
            assert _item({"rings": rings}, "self", "sleep")["last_data_date"] == "2026-08-01"
            assert _item({"rings": rings}, "self", "labs")["status"] == "red"

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_datetime_reduced_to_local_date(self) -> None:
        """CIR-DATA-AGE-CALENDAR#age-datetime-reduced-to-local-date — source
        2026-08-02T23:30:00Z with timezone Pacific/Auckland → local date 2026-08-03 → age 0
        on a 2026-08-03 reference."""
        # August is NZST (UTC+12): 23:30Z on 08-02 is 11:30 on 08-03 in Auckland.
        found, rejected = scan_dates("2026-08-02T23:30:00Z", "Pacific/Auckland")
        assert (found, rejected) == ([date(2026, 8, 3)], [])
        assert calendar_age(found[0], date(2026, 8, 3)) == 0
        # The same token read in UTC stays on 08-02 → age 1: the config's zone decides.
        assert scan_dates("2026-08-02T23:30:00Z", "UTC")[0] == [date(2026, 8, 2)]

    @rule("CIR-DATA-AGE-CALENDAR")
    def test_age_year_boundary(self) -> None:
        """CIR-DATA-AGE-CALENDAR#age-year-boundary — reference 2026-01-02, source
        2025-12-29 → 4."""
        # 29→30→31→(Jan)1→2: four boundaries.
        assert calendar_age(date(2025, 12, 29), date(2026, 1, 2)) == 4


# ===========================================================================
# CIR-DATA-FRESHNESS-WINDOW — the wired end-to-end case (predicate rows: test_resolve.py)
# ===========================================================================

class TestDataFreshnessWindowWired:
    """CIR-DATA-FRESHNESS-WINDOW — the fixture's labs case through resolve()."""

    @rule("CIR-DATA-FRESHNESS-WINDOW")
    def test_window_far_past_red(self) -> None:
        """CIR-DATA-FRESHNESS-WINDOW#window-far-past-red — the fixture's labs item:
        2026-01-15 against 2026-08-03 is 200 days (16+28+31+30+31+30+31+3) > red_after 190
        → 🔴."""
        assert calendar_age(LABS_NEWEST, FIXTURE_REFERENCE_DATE) == 200
        item = _item(_evaluate(ALEX_YAML), "self", "labs")
        assert item["status"] == "red"
        assert item["grey_reason"] is None
        assert item["last_data_date"] == "2026-01-15"
        assert "act · last data 2026-01-15" in item["detail_line"]


class TestFixtureDatesRelativeToReference:
    """CIR-PROC-TEST-FIXTURES — boundary rows move the reference date, not the notes."""

    @rule("CIR-PROC-TEST-FIXTURES")
    def test_dates_relative_to_injected_reference(self) -> None:
        """CIR-PROC-TEST-FIXTURES#dates-relative-to-injected-reference — the sleep item
        (newest 2026-08-01, yellow_after 7) at reference 2026-08-08 is age 7 → still 🟢
        (⚖-R6); at 2026-08-09 it is age 8 → 🟡. The committed note is untouched."""
        config = load_config(ALEX_YAML)
        before = (ALEX_DIR / "notes" / "sleep-log.md").read_bytes()
        at_boundary = resolve(config, reference_date=date(2026, 8, 8),
                              generated_at=FIXTURE_GENERATED_AT, evaluate=True)
        past_boundary = resolve(config, reference_date=date(2026, 8, 9),
                                generated_at=FIXTURE_GENERATED_AT, evaluate=True)
        assert _item(at_boundary, "self", "sleep")["status"] == "green"
        assert _item(past_boundary, "self", "sleep")["status"] == "yellow"
        assert _item(past_boundary, "self", "sleep")["last_data_date"] == "2026-08-01"
        assert (ALEX_DIR / "notes" / "sleep-log.md").read_bytes() == before


# ===========================================================================
# CIR-DATA-FRESHNESS-EMPTY — a source with no usable dates (⚖-R31)
# ===========================================================================

class TestDataFreshnessEmpty:
    """CIR-DATA-FRESHNESS-EMPTY — ⚪ + warning, never a guessed 🔴."""

    @rule("CIR-DATA-FRESHNESS-EMPTY")
    def test_source_file_empty(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-FRESHNESS-EMPTY#source-file-empty — file exists, zero bytes → ⚪ +
        build warning."""
        config_path = alex_copy(sleep_source="notes/zero-bytes.md")
        (config_path.parent / "notes" / "zero-bytes.md").write_bytes(b"")
        artifact = _evaluate(config_path)
        messages = _assert_grey_by_failure(artifact)
        assert "no dates found" in messages[0]
        assert _item(artifact, "self", "sleep")["status"] != "red"

    @rule("CIR-DATA-FRESHNESS-EMPTY")
    def test_source_no_parseable_dates(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-FRESHNESS-EMPTY#source-no-parseable-dates — notes/empty-log.md (a
        heading, no dated lines) → ⚪ + build warning."""
        artifact = _evaluate(alex_copy(sleep_source="notes/empty-log.md"))
        messages = _assert_grey_by_failure(artifact)
        assert "no dates found" in messages[0]
        assert _item(artifact, "self", "sleep")["status"] != "red"


# ===========================================================================
# CIR-DATA-FRESHNESS-FUTURE — dates after the reference date (⚖-R8)
# ===========================================================================

class TestDataFreshnessFuture:
    """CIR-DATA-FRESHNESS-FUTURE — future dates are excluded, never clamped to 🟢."""

    @rule("CIR-DATA-FRESHNESS-FUTURE")
    def test_future_date_mixed(self, alex_copy: AlexCopy) -> None:
        """CIR-DATA-FRESHNESS-FUTURE#future-date-mixed — notes/future-date.md holds
        2099-01-01 and 2026-08-01; at reference 2026-08-03 the future one is excluded with a
        warning and the last-data date is 2026-08-01."""
        artifact = _evaluate(alex_copy(sleep_source="notes/future-date.md"))
        item = _item(artifact, "self", "sleep")
        assert item["last_data_date"] == "2026-08-01"
        assert item["status"] == "green"  # age 2 ≤ 7 — the future line did not pin it
        assert item["grey_reason"] is None
        messages = _warnings_for(artifact, "self/sleep")
        assert len(messages) == 1
        assert "2099-01-01" in messages[0]
        assert "notes/future-date.md" in messages[0]

    @rule("CIR-DATA-FRESHNESS-FUTURE")
    def test_future_date_tomorrow(self) -> None:
        """CIR-DATA-FRESHNESS-FUTURE#future-date-tomorrow — a source dated one day ahead of
        the reference date is excluded with a warning, not treated as age 0."""
        # Reference 2026-07-31: the sleep-log's 2026-08-01 is tomorrow → excluded; the
        # newest remaining entry is 2026-07-31 → age 0 → 🟢 with last data 2026-07-31.
        artifact = _evaluate(ALEX_YAML, reference_date=date(2026, 7, 31))
        item = _item(artifact, "self", "sleep")
        assert item["last_data_date"] == "2026-07-31"
        assert item["status"] == "green"
        messages = _warnings_for(artifact, "self/sleep")
        assert len(messages) == 1
        assert "2026-08-01" in messages[0]

    @rule("CIR-DATA-FRESHNESS-FUTURE")
    def test_future_dates_only(self) -> None:
        """CIR-DATA-FRESHNESS-FUTURE#future-dates-only — every parseable date in the future
        → ⚪ + build warning."""
        # Reference 2026-07-29: all three sleep-log entries (07-30, 07-31, 08-01) are ahead.
        artifact = _evaluate(ALEX_YAML, reference_date=SLEEP_OLDEST.replace(day=29))
        messages = _assert_grey_by_failure(artifact)
        assert "after the reference date" in messages[0]
        assert _item(artifact, "self", "sleep")["status"] != "green"


# ===========================================================================
# AdapterResult — the CIR-ADAPT-CONTRACT shape, unrepresentable-grey half
# ===========================================================================

class TestAdapterResultShape:
    """CIR-ADAPT-CONTRACT — an adapter answers a light with a date, or fails. Never ⚪."""

    @rule("CIR-ADAPT-CONTRACT")
    @pytest.mark.parametrize("status", [
        pytest.param("grey", id="grey as a wire value"),
        pytest.param("unmonitored", id="grey as its display word"),
        pytest.param("", id="empty string"),
        pytest.param(None, id="no status at all"),
    ])
    def test_adapter_cannot_return_grey(self, status: str | None) -> None:
        """CIR-ADAPT-CONTRACT#adapter-cannot-return-grey — grey (or any non-light) is not
        constructible as an adapter answer."""
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


# ===========================================================================
# CIR-ADAPT-COMMAND — the escape hatch, executed (issue #33 slice B)
# ===========================================================================
#
# Every command row drives a REAL subprocess: a small /bin/sh script written into a tmp copy
# of fixtures/alex (the `commands` knob of `alex_copy` re-points one cell's status: to it).
# Expected lights come from the rows in specs/data/adapters.md §CIR-ADAPT-COMMAND.


def _script(config_path: Path, name: str, body: str) -> str:
    """Write an executable /bin/sh script under the copy's notes/; return its argv[0]."""
    path = config_path.parent / "notes" / name
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return f"./notes/{name}"


def _plants_command(alex_copy: AlexCopy, body: str, *args: str) -> Path:
    """A tmp alex whose wider/plants runs a script with *body* (and *args*)."""
    config_path = alex_copy(commands={"wider/plants": ["./notes/plants-probe.sh", *args]})
    _script(config_path, "plants-probe.sh", body)
    return config_path


def _plants(artifact: dict) -> dict:
    return _item(artifact, "wider", "plants")


def _plants_failure(artifact: dict) -> str:
    """CIR-DATA-FAILURE-IS-GREY shape for wider/plants (no guardrail): ⚪ by-failure, no
    data date, exactly one warning naming the cell, its text the detail line's reason."""
    plants = _plants(artifact)
    assert plants["status"] == "grey"
    assert plants["grey_reason"] == "by-failure"
    assert plants["last_data_date"] is None
    messages = _warnings_for(artifact, "wider/plants")
    assert len(messages) == 1, messages
    assert plants["detail_line"] == "unmonitored · " + messages[0]
    return messages[0]


class TestAdaptCommand:
    """CIR-ADAPT-COMMAND — argv, config dir, first-line status word, exit code dominates."""

    @rule("CIR-ADAPT-COMMAND")
    def test_command_prints_yellow(self) -> None:
        """CIR-ADAPT-COMMAND#command-prints-yellow — the fixture's plants script prints
        `yellow` → 🟡 under --evaluate at the fixture reference date."""
        artifact = _evaluate(ALEX_YAML)
        plants = _plants(artifact)
        assert plants["status"] == "yellow"
        assert plants["grey_reason"] is None
        assert _warnings_for(artifact, "wider/plants") == []

    @rule("CIR-ADAPT-COMMAND")
    def test_command_not_shell_interpreted(self, alex_copy: AlexCopy,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
        """CIR-ADAPT-COMMAND#command-not-shell-interpreted — `["./x.sh", "a b", "*", "$HOME"]`
        arrives as three arguments, verbatim: no word split, no glob, no $VAR expansion."""
        monkeypatch.setenv("HOME", "/should-not-expand")
        config_path = _plants_command(
            alex_copy,
            '[ "$#" = 3 ] && [ "$1" = "a b" ] && [ "$2" = "*" ] && [ "$3" = \'$HOME\' ] '
            "&& echo green && exit 0\nexit 9\n",
            "a b", "*", "$HOME",
        )
        # Verbatim argv → the script's own check passes → it prints green → 🟢.
        assert _plants(_evaluate(config_path))["status"] == "green"

    @rule("CIR-ADAPT-COMMAND")
    def test_command_cwd_is_config_dir(self, alex_copy: AlexCopy, tmp_path: Path,
                                       monkeypatch: pytest.MonkeyPatch) -> None:
        """CIR-ADAPT-COMMAND#command-cwd-is-config-dir — `./notes/…` resolves, and the
        process runs, under <config-dir> wherever the bake itself was started."""
        config_path = _plants_command(
            alex_copy, "[ -f ./circles.yaml ] && [ -f ./notes/plants-status.sh ] "
                       "&& echo green && exit 0\nexit 9\n")
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        # cwd == the config dir → both files found → green.
        assert _plants(_evaluate(config_path))["status"] == "green"

    @rule("CIR-ADAPT-COMMAND")
    @pytest.mark.parametrize(
        "body,expected",
        [
            pytest.param("printf ' GREEN\\n'\n", "green",
                         id="CIR-ADAPT-COMMAND#command-stdout-trimmed-and-folded"),
            pytest.param("printf '\\n  \\nred\\n'\n", "red",
                         id="CIR-ADAPT-COMMAND#command-first-non-empty-line-wins"),
            pytest.param("echo yellow\ni=0\nwhile [ $i -lt 40 ]; do echo \"diag $i: green\"; "
                         "i=$((i+1)); done\n", "yellow",
                         id="CIR-ADAPT-COMMAND#command-extra-output-ignored"),
        ],
    )
    def test_command_stdout_words(self, alex_copy: AlexCopy, body: str, expected: str) -> None:
        """The first non-empty stdout line, trimmed and case-folded, is the light; the rest
        of stdout is free (rows cited per param)."""
        artifact = _evaluate(_plants_command(alex_copy, body))
        assert _plants(artifact)["status"] == expected
        assert _warnings_for(artifact, "wider/plants") == []

    @rule("CIR-ADAPT-COMMAND")
    def test_command_unknown_word(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-unknown-word — prints `amber` → ⚪ + warning naming
        the word."""
        message = _plants_failure(_evaluate(_plants_command(alex_copy, "echo amber\n")))
        assert "amber" in message

    @rule("CIR-ADAPT-COMMAND")
    def test_command_empty_stdout(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-empty-stdout — `""`, exit 0 → ⚪ + warning."""
        _plants_failure(_evaluate(_plants_command(alex_copy, "exit 0\n")))

    @rule("CIR-ADAPT-COMMAND")
    def test_command_nonzero_exit_dominates(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-nonzero-exit-dominates — prints `red`, exits 1 →
        ⚪ + warning: the exit code wins over stdout (and a failure is never 🔴)."""
        message = _plants_failure(_evaluate(_plants_command(alex_copy, "echo red\nexit 1\n")))
        assert "1" in message

    @rule("CIR-ADAPT-COMMAND")
    def test_command_stderr_not_on_the_page(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-stderr-not-on-the-page — a stack trace on stderr
        never reaches the warning, which stays a bounded summary."""
        body = ('echo "Traceback: File /home/alex/secret/probe.py line 3" >&2\n'
                'echo "PLANTS_API_TOKEN=hunter2" >&2\nexit 2\n')
        artifact = _evaluate(_plants_command(alex_copy, body))
        message = _plants_failure(artifact)
        serialised = json.dumps(artifact)
        for leaked in ("Traceback", "/home/alex", "hunter2", "PLANTS_API_TOKEN"):
            assert leaked not in serialised
        assert len(message) <= adapters_module.WARNING_MAX_CHARS

    @rule("CIR-ADAPT-COMMAND")
    def test_command_cannot_set_a_data_date(self, alex_copy: AlexCopy) -> None:
        """CIR-ADAPT-COMMAND#command-cannot-set-a-data-date — even a script that prints a
        date after its word gets no "last data" segment (⚖-R32 rules the first word only)."""
        artifact = _evaluate(_plants_command(alex_copy, "echo green\necho date=2026-08-01\n"))
        plants = _plants(artifact)
        assert plants["status"] == "green"
        assert plants["last_data_date"] is None
        assert "last data" not in plants["detail_line"]
        # The fixture key example likewise carries none.
        assert _plants(_evaluate(ALEX_YAML))["last_data_date"] is None


# ===========================================================================
# CIR-ADAPT-BUDGET — time and blast radius
# ===========================================================================
#
# ⚖-R21 fixes 30 s per item and 5 min per bake; the tests shrink the module constants
# (never sleep for real) and assert the production values separately.

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
    def test_budget_constants_are_the_ruling(self) -> None:
        """CIR-ADAPT-BUDGET#command-per-item-timeout — ⚖-R21: 30 s per item, 5 min per
        bake, fixed (the other tests shrink these, so pin the production values here)."""
        assert adapters_module.COMMAND_TIMEOUT_SECONDS == 30
        assert adapters_module.BAKE_BUDGET_SECONDS == 5 * 60

    @rule("CIR-ADAPT-BUDGET")
    def test_command_per_item_timeout(self, alex_copy: AlexCopy,
                                      monkeypatch: pytest.MonkeyPatch) -> None:
        """CIR-ADAPT-BUDGET#command-per-item-timeout — a command sleeping past the per-item
        timeout is killed; ⚪ + warning naming the timeout."""
        monkeypatch.setattr(adapters_module, "COMMAND_TIMEOUT_SECONDS", 0.5)
        config_path = _plants_command(alex_copy, "sleep 20\necho green\n")
        started = time.monotonic()
        message = _plants_failure(_evaluate(config_path))
        # Killed at ~0.5 s, far short of the script's own 20 s.
        assert time.monotonic() - started < 10
        assert "timed out" in message

    @rule("CIR-ADAPT-BUDGET")
    @pytest.mark.parametrize("ends", [
        pytest.param("exits", id="command exits, child lingers"),
        pytest.param("times-out", id="command times out"),
    ])
    def test_command_children_killed(self, alex_copy: AlexCopy, tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch, ends: str) -> None:
        """CIR-ADAPT-BUDGET#command-children-killed — a child that would outlive its
        command is terminated with the process group, whether the command exits or times out."""
        monkeypatch.setattr(adapters_module, "COMMAND_TIMEOUT_SECONDS", 0.5)
        pid_file = tmp_path / "child.pid"
        tail = "echo green\n" if ends == "exits" else "sleep 20\n"
        config_path = _plants_command(
            alex_copy, 'sleep 60 >/dev/null 2>&1 &\necho $! > "$1"\n' + tail, str(pid_file))
        artifact = _evaluate(config_path)
        child = int(pid_file.read_text().strip())
        assert _wait_dead(child), f"child {child} outlived its command"
        expected = "green" if ends == "exits" else "grey"
        assert _plants(artifact)["status"] == expected

    @rule("CIR-ADAPT-BUDGET")
    def test_bake_total_budget(self, alex_copy: AlexCopy,
                               monkeypatch: pytest.MonkeyPatch) -> None:
        """CIR-ADAPT-BUDGET#bake-total-budget — many slow adapters: the bake ends within the
        total budget; every item left unresolved is ⚪ + warning."""
        monkeypatch.setattr(adapters_module, "BAKE_BUDGET_SECONDS", 1.0)
        config_path = alex_copy(commands={
            "self/sleep": ["./notes/slow.sh"],
            "self/labs": ["./notes/slow.sh"],
            "wider/plants": ["./notes/slow.sh"],
        })
        _script(config_path, "slow.sh", "sleep 20\necho green\n")
        started = time.monotonic()
        artifact = _evaluate(config_path)
        # Three 20 s commands under a 1 s budget: the bake ends near 1 s, not 60 s.
        assert time.monotonic() - started < 10
        for ring_id, item_id in (("self", "sleep"), ("self", "labs"), ("wider", "plants")):
            item = _item(artifact, ring_id, item_id)
            assert item["status"] == "grey"
            assert item["grey_reason"] == "by-failure"
            messages = _warnings_for(artifact, f"{ring_id}/{item_id}")
            assert len(messages) == 1 and "budget" in messages[0], messages
        # Adapter-free cells still resolve: manual lights are not budgeted work.
        assert _item(artifact, "wider", "friends")["status"] == "red"

    @rule("CIR-ADAPT-BUDGET")
    def test_environment_not_inherited_wholesale(self, alex_copy: AlexCopy, tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
        """CIR-ADAPT-BUDGET#environment-not-inherited-wholesale — the bake's env holds a
        token; the command receives a minimal, explicit environment without it."""
        monkeypatch.setenv("CIRCLES_REGISTRY_TOKEN", "s3cret-token")
        monkeypatch.setenv("KUBECONFIG", "/home/alex/.kube/config")
        env_dump = tmp_path / "env.txt"
        config_path = _plants_command(alex_copy, 'env > "$1"\necho green\n', str(env_dump))
        artifact = _evaluate(config_path)
        assert _plants(artifact)["status"] == "green"
        seen = env_dump.read_text()
        assert "s3cret-token" not in seen
        assert "CIRCLES_REGISTRY_TOKEN" not in seen
        assert "KUBECONFIG" not in seen
        assert "HOME=" not in seen
        names = {line.split("=", 1)[0] for line in seen.splitlines() if "=" in line}
        # /bin/sh itself adds PWD (and some shells SHLVL, _); everything else is ours.
        assert names - {"PWD", "SHLVL", "_", "OLDPWD"} == {"PATH", "LANG", "TZ"}
        assert f"TZ={artifact['timezone']}" in seen.splitlines()
