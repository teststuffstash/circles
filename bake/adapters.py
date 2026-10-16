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
#   CIR-ADAPT-COMMAND (execution rows), CIR-ADAPT-BUDGET (per-item timeout, process group,
#   minimal environment; the total budget is enforced by bake.resolve)

from __future__ import annotations

import os
import re
import signal
import subprocess
import threading
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


class _Unset:
    """Sentinel: a light whose adapter never said whether it has a data date."""
    def __repr__(self) -> str:
        return "<unset>"


_UNSET = _Unset()


@dataclass(frozen=True)
class AdapterResult:
    """Exactly one of: (``status`` + ``data_date`` [+ ``note``]) or ``failure``.

    Build via :meth:`ok` / :meth:`failed`. ``__post_init__`` makes the other shapes —
    grey, both halves, neither half — unconstructible (CIR-ADAPT-CONTRACT).
    ``data_date`` is optional per the contract, but must be STATED: a date, or an explicit
    ``None`` (a command can never set one, ⚖-R32); a light that leaves it unset is refused.
    ``note`` is a non-fatal remark the caller surfaces as a build warning (a future date
    excluded, an impossible calendar date ignored) while the item still holds its light.
    """
    status: AdapterStatus | None = None
    data_date: date | None | _Unset = _UNSET
    note: str | None = None
    failure: str | None = None

    def __post_init__(self) -> None:
        if self.failure is not None:
            if (self.status is not None or self.data_date not in (None, _UNSET)
                    or self.note is not None):
                raise ValueError("AdapterResult: a failure carries no status, date or note")
            if not self.failure.strip():
                raise ValueError("AdapterResult: a failure needs a plain-text reason")
            object.__setattr__(self, "data_date", None)
            return
        if self.status not in _ADAPTER_STATUSES:
            # Grey (or anything else) is not an adapter answer — ⚪ comes only from
            # absence or failure (CIR-ADAPT-CONTRACT#adapter-cannot-return-grey).
            raise ValueError(
                f"AdapterResult: status must be one of {sorted(_ADAPTER_STATUSES)}, "
                f"got {self.status!r}"
            )
        if self.data_date is not None and not isinstance(self.data_date, date):
            raise ValueError("AdapterResult: a status states its data date (a date, or None)")

    @classmethod
    def ok(
        cls, status: AdapterStatus, data_date: date | None, note: str | None = None,
    ) -> AdapterResult:
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
        try:
            resolved = candidate.resolve()
        except (RuntimeError, OSError):
            # A symlink loop among the glob hits is no file: skipped like any other non-file,
            # so the rest of the union is still judged (CIR-DATA-SOURCE-PATH#source-glob-symlink-loop).
            continue
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


# ---------------------------------------------------------------------------
# CIR-ADAPT-COMMAND / CIR-ADAPT-BUDGET — the escape hatch, on a leash
# ---------------------------------------------------------------------------

# ⚖-R21: fixed in v0, not configurable. Module constants so tests can shrink them
# (monkeypatch) without the production values ever being a knob.
COMMAND_TIMEOUT_SECONDS: float = 30.0   # per item (CIR-ADAPT-BUDGET#command-per-item-timeout)
BAKE_BUDGET_SECONDS: float = 300.0      # whole bake (CIR-ADAPT-BUDGET#bake-total-budget)

# How much stdout is kept to find the status word; the rest is drained and dropped so a
# chatty command can neither block on a full pipe nor balloon the bake's memory.
STDOUT_KEEP_BYTES = 64 * 1024
# The longest warning a command can produce, and the longest echo of its unknown word
# (CIR-BAKE-EXPOSURE#warning-text-is-bounded).
WARNING_MAX_CHARS = 200
_WORD_ECHO_MAX_CHARS = 32

# The command's whole environment (CIR-ADAPT-BUDGET#environment-not-inherited-wholesale):
# nothing from the bake's own environment — no tokens, no kubeconfig, no HOME — is passed
# through. PATH is a fixed system path; TZ is the config's zone (filled in per call) so a
# script's `date` agrees with the bake's calendar; LANG pins a UTF-8 locale.
COMMAND_PATH = "/usr/local/bin:/usr/bin:/bin"
COMMAND_LANG = "C.UTF-8"

_STATUS_WORDS = ("green", "yellow", "red")


def command_environment(tz_name: str) -> dict[str, str]:
    """The minimal, explicit environment every ``command:`` runs with."""
    return {"PATH": COMMAND_PATH, "LANG": COMMAND_LANG, "TZ": tz_name}


def _bounded(message: str) -> str:
    return message if len(message) <= WARNING_MAX_CHARS else message[: WARNING_MAX_CHARS - 1] + "…"


def _echo_word(word: str) -> str:
    """A command-printed word made safe to quote in a public warning: printable, short."""
    clean = "".join(ch if ch.isprintable() else "?" for ch in word)
    if len(clean) > _WORD_ECHO_MAX_CHARS:
        clean = clean[: _WORD_ECHO_MAX_CHARS - 1] + "…"
    return clean


def _kill_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _drain(stream, keep: bytearray) -> None:
    """Read *stream* to EOF, keeping the first STDOUT_KEEP_BYTES bytes."""
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            room = STDOUT_KEEP_BYTES - len(keep)
            if room > 0:
                keep.extend(chunk[:room])
    except (OSError, ValueError):
        return


def evaluate_command(
    block: dict,
    config_dir: Path,
    tz_name: str,
    timeout: float | None = None,
    timeout_reason: str | None = None,
) -> AdapterResult:
    """Run one ``command:`` block (already shape-validated by bake.config).

    argv array, no shell (CIR-ADAPT-COMMAND#command-not-shell-interpreted); argv[0]
    resolves under, and the process runs in, the config directory
    (#command-cwd-is-config-dir). The first non-empty stdout line — trimmed and
    case-folded — must be green|yellow|red; a nonzero exit dominates whatever was printed
    (#command-nonzero-exit-dominates). stderr is discarded unread: it never reaches a
    warning (#command-stderr-not-on-the-page). A command never sets a data date (⚖-R32).

    The command runs in its own process group with a minimal environment; past *timeout*
    seconds (default COMMAND_TIMEOUT_SECONDS) the whole group is SIGKILLed, and the group
    is killed after a normal exit too, so no child outlives its command
    (CIR-ADAPT-BUDGET#command-per-item-timeout, #command-children-killed).
    *timeout_reason* replaces the timeout warning when the caller cut the leash shorter
    (the total bake budget).
    """
    argv: list[str] = list(block["command"])
    if timeout is None:
        timeout = COMMAND_TIMEOUT_SECONDS
    executable = Path(argv[0])
    if not executable.is_absolute():
        executable = config_dir / executable

    try:
        proc = subprocess.Popen(
            argv,
            executable=str(executable),
            cwd=str(config_dir),
            env=command_environment(tz_name),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # its own process group, pgid == pid
            close_fds=True,
        )
    except OSError as e:
        # The OS error text carries the host path — forward only its class name
        # (CIR-BAKE-EXPOSURE#no-absolute-host-paths).
        return AdapterResult.failed(f"command could not be started ({type(e).__name__})")

    kept = bytearray()
    reader = threading.Thread(target=_drain, args=(proc.stdout, kept), daemon=True)
    reader.start()
    timed_out = False
    try:
        proc.wait(timeout=max(timeout, 0.0))
    except subprocess.TimeoutExpired:
        timed_out = True
    finally:
        _kill_group(proc.pid)
        proc.wait()
        reader.join(timeout=5)
        if proc.stdout is not None:
            proc.stdout.close()

    if timed_out:
        reason = timeout_reason or f"command timed out after {timeout:g} s and was killed"
        return AdapterResult.failed(_bounded(reason))
    if proc.returncode < 0:
        return AdapterResult.failed(
            _bounded(f"command was killed by signal {-proc.returncode}"))
    if proc.returncode != 0:
        return AdapterResult.failed(_bounded(f"command exited with code {proc.returncode}"))

    text = bytes(kept).decode("utf-8", errors="replace")
    first = next((line.strip() for line in text.splitlines() if line.strip()), None)
    if first is None:
        return AdapterResult.failed("command printed no status (expected green, yellow or red)")
    word = first.casefold()
    if word not in _STATUS_WORDS:
        return AdapterResult.failed(_bounded(
            f"command printed unknown status '{_echo_word(first)}' "
            f"(expected green, yellow or red)"))
    return AdapterResult.ok(word, None)  # type: ignore[arg-type]  # never a data date (⚖-R32)
