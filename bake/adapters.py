# bake/adapters.py — the adapters that EVALUATE (P1, issue #33 slice A: freshness)
#
# An adapter is a named function from (its config block, the resolution context) to exactly
# one of: a status with a data date, or a failure (CIR-ADAPT-CONTRACT). It reads files, never
# writes, and never touches the clock — the reference date is injected
# (CIR-ADAPT-REFERENCE-DATE). Grey is not in an adapter's vocabulary: AdapterResult refuses
# to be constructed with it (CIR-ADAPT-CONTRACT#adapter-cannot-return-grey).
#
# Requirements owned:
#   CIR-ADAPT-FRESHNESS, CIR-DATA-SOURCE-PATH (evaluation rows), CIR-DATA-DATE-PARSE,
#   CIR-DATA-AGE-CALENDAR, CIR-DATA-FRESHNESS-EMPTY, CIR-DATA-FRESHNESS-FUTURE
#
# Command execution (CIR-ADAPT-COMMAND) lands in issue #33 slice B — not here.

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ---------------------------------------------------------------------------
# The adapter result — a light with a data date, or a failure. Never grey.
# ---------------------------------------------------------------------------

AdapterStatus = Literal["green", "yellow", "red"]
_ADAPTER_STATUSES = frozenset({"green", "yellow", "red"})


@dataclass(frozen=True)
class AdapterResult:
    """Exactly one of: (``status`` + ``data_date`` [+ ``note``]) or ``failure``.

    Build via :meth:`ok` / :meth:`failed`. ``__post_init__`` makes the other shapes —
    grey, both halves, neither half — unconstructible (CIR-ADAPT-CONTRACT).
    ``note`` is a non-fatal remark the caller surfaces as a build warning (a future date
    excluded, an impossible calendar date ignored) while the item still holds its light.
    """
    status: AdapterStatus | None = None
    data_date: date | None = None
    note: str | None = None
    failure: str | None = None

    def __post_init__(self) -> None:
        if self.failure is not None:
            if self.status is not None or self.data_date is not None or self.note is not None:
                raise ValueError("AdapterResult: a failure carries no status, date or note")
            if not self.failure.strip():
                raise ValueError("AdapterResult: a failure needs a plain-text reason")
            return
        if self.status not in _ADAPTER_STATUSES:
            # Grey (or anything else) is not an adapter answer — ⚪ comes only from
            # absence or failure (CIR-ADAPT-CONTRACT#adapter-cannot-return-grey).
            raise ValueError(
                f"AdapterResult: status must be one of {sorted(_ADAPTER_STATUSES)}, "
                f"got {self.status!r}"
            )
        if not isinstance(self.data_date, date):
            raise ValueError("AdapterResult: a status carries its data date")

    @classmethod
    def ok(cls, status: AdapterStatus, data_date: date, note: str | None = None) -> AdapterResult:
        return cls(status=status, data_date=data_date, note=note)

    @classmethod
    def failed(cls, reason: str) -> AdapterResult:
        return cls(failure=reason)


# ---------------------------------------------------------------------------
# CIR-DATA-DATE-PARSE — which date tokens count
# ---------------------------------------------------------------------------

# A full ISO-8601 calendar date, optionally followed by a time and offset (⚖-R27: ISO only).
# The lookarounds on [0-9A-Za-z] make an ISO-looking substring of a longer token a non-date:
# `v2026-08-01-rc1` (letter before) and `id=2026-08-013` (digit after) are ignored, while
# `- 2026-08-01 — 7h20m` and `2026-08-01T22:10:00+03:00` match whole
# (CIR-DATA-DATE-PARSE#date-iso-substring, #date-anywhere-in-line, #date-datetime-form).
_DATE_TOKEN_RE = re.compile(
    r"(?<![0-9A-Za-z])"
    r"(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})"
    r"(?:T(?P<hh>\d{2}):(?P<mm>\d{2})(?::(?P<ss>\d{2})(?:\.\d+)?)?"
    r"(?P<tz>Z|[+-]\d{2}:?\d{2})?)?"
    r"(?![0-9A-Za-z])"
)


def _parse_offset(tz_text: str) -> timezone:
    if tz_text == "Z":
        return timezone.utc
    sign = 1 if tz_text[0] == "+" else -1
    digits = tz_text[1:].replace(":", "")
    hours, minutes = int(digits[:2]), int(digits[2:])
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def scan_dates(text: str, tz_name: str) -> tuple[list[date], list[str]]:
    """Return (recognised local calendar dates, rejected impossible tokens) found in *text*.

    A datetime token with an offset is converted to the config timezone FIRST and then
    reduced to its calendar date (CIR-DATA-AGE-CALENDAR#age-datetime-reduced-to-local-date);
    one without an offset is already local. An impossible calendar date such as
    ``2026-02-30`` is rejected, and returned so the caller can name the file
    (CIR-DATA-DATE-PARSE#date-impossible-calendar).
    """
    zone = ZoneInfo(tz_name)
    found: list[date] = []
    rejected: list[str] = []
    for m in _DATE_TOKEN_RE.finditer(text):
        try:
            day = date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
            if m.group("hh") is not None:
                moment = datetime(
                    day.year, day.month, day.day,
                    int(m.group("hh")), int(m.group("mm")), int(m.group("ss") or 0),
                )
                if m.group("tz") is not None:
                    moment = moment.replace(tzinfo=_parse_offset(m.group("tz")))
                    day = moment.astimezone(zone).date()
                else:
                    day = moment.date()
        except ValueError:
            rejected.append(m.group(0))
            continue
        found.append(day)
    return found, rejected


# ---------------------------------------------------------------------------
# CIR-DATA-AGE-CALENDAR — age is calendar days
# ---------------------------------------------------------------------------

def calendar_age(source_date: date, reference_date: date) -> int:
    """Whole calendar-day boundaries between *source_date* and *reference_date*.

    Date subtraction never sees a clock, so a 23- or 25-hour local day is one day
    (CIR-DATA-AGE-CALENDAR#age-dst-spring-forward, #age-dst-fall-back). Negative means
    the source is after the reference date (CIR-DATA-FRESHNESS-FUTURE).
    """
    return (reference_date - source_date).days


# ---------------------------------------------------------------------------
# CIR-DATA-SOURCE-PATH — where sources are read from
# ---------------------------------------------------------------------------

_GLOB_CHARS = frozenset("*?[")


def _source_files(source: str, config_dir: Path) -> list[Path]:
    """Resolve ``source`` (path or glob) under *config_dir*; only contained regular files.

    Everything that resolves outside the config directory — a glob hit through a symlink,
    say — is dropped here, so nothing outside it is ever opened
    (CIR-ADAPT-FRESHNESS#freshness-sandboxed-to-config-dir).
    """
    root = config_dir.resolve()
    if _GLOB_CHARS & set(source):
        candidates = sorted(root.glob(source))
    else:
        candidates = [root / source]
    contained: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.is_file():
            contained.append(candidate)
    return contained


# ---------------------------------------------------------------------------
# CIR-ADAPT-FRESHNESS — the adapter
# ---------------------------------------------------------------------------

def evaluate_freshness(
    block: dict,
    config_dir: Path,
    reference_date: date,
    timezone: str,
) -> AdapterResult:
    """Evaluate one ``freshness:`` block (already shape-validated by bake.config).

    Reads the matched source files as text (never executes them), takes the newest
    calendar date across the union, and judges its age against the thresholds. Every
    failure names the config-relative ``source:`` string only — never a host path
    (CIR-BAKE-EXPOSURE#no-absolute-host-paths) and never source text
    (CIR-BAKE-EXPOSURE#no-source-content-in-the-artifact).
    """
    freshness = block["freshness"]
    source: str = freshness["source"]
    yellow_after: int = freshness["yellow_after"]
    red_after: int = freshness["red_after"]

    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return AdapterResult.failed(f"unknown timezone '{timezone}'")

    files = _source_files(source, config_dir)
    if not files:
        return AdapterResult.failed(f"missing source: {source}")

    root = config_dir.resolve()
    dates: list[date] = []
    notes: list[str] = []
    for path in files:
        rel = path.resolve().relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return AdapterResult.failed(f"unreadable source: {rel} ({type(e).__name__})")
        found, rejected = scan_dates(text, timezone)
        dates.extend(found)
        for token in rejected:
            notes.append(f"ignored impossible date {token} in {rel}")

    def _failed(reason: str) -> AdapterResult:
        # A failure still carries what was ignored on the way — the warning is the only
        # place the person learns their file held an impossible or future date.
        return AdapterResult.failed("; ".join([reason, *notes]))

    if not dates:
        return _failed(f"no dates found in source: {source}")

    # ⚖-R8: dates after the reference date are excluded with a warning, never clamped.
    future = sorted({d for d in dates if calendar_age(d, reference_date) < 0})
    past = [d for d in dates if calendar_age(d, reference_date) >= 0]
    for d in future:
        notes.append(f"ignored future date {d.isoformat()} in source: {source}")
    if not past:
        return _failed(
            f"every date in source {source} is after the reference date "
            f"{reference_date.isoformat()}"
        )

    from bake.resolve import window_status  # local: resolve imports this module

    newest = max(past)
    status = window_status(calendar_age(newest, reference_date), yellow_after, red_after)
    return AdapterResult.ok(status, newest, note="; ".join(notes) if notes else None)
