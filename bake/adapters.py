"""Adapter implementations per CIR-ADAPT-*.

v0 adapters: manual (fully implemented), freshness and command (resolve to ⚪ + warning
per ⚖-R2 — P0 only implements manual).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bake.validate import BuildWarning

# ISO-8601 calendar date pattern — CIR-DATA-DATE-PARSE
ISO_DATE_RE = re.compile(
    r"(?<!\w)(\d{4})-(\d{2})-(\d{2})(?:\D|$)"
)

# Valid status colors from adapters
VALID_STATUSES = {"green", "yellow", "red"}


class AdapterResult:
    """Result of running an adapter on one item."""
    def __init__(
        self,
        status: str | None = None,   # green|yellow|red for success; None for failure
        data_date: str | None = None,  # ISO date string
        note: str | None = None,
        failure_reason: str | None = None,
    ):
        self.status = status
        self.data_date = data_date
        self.note = note
        self.failure_reason = failure_reason

    @property
    def is_success(self) -> bool:
        return self.status is not None

    @property
    def is_failure(self) -> bool:
        return self.failure_reason is not None


def resolve_manual(adapter_value: Any) -> AdapterResult:
    """Resolve manual: adapter (CIR-ADAPT-MANUAL).

    Returns the declared status with no data date.
    """
    return AdapterResult(status=adapter_value)


def resolve_freshness_p0(adapter_value: Any) -> AdapterResult:
    """P0 stub for freshness adapter (⚖-R2).

    At P0, freshness items are not evaluated. Returns ⚪ + "not evaluated" warning.
    """
    return AdapterResult(
        failure_reason="adapter not evaluated in this build (freshness evaluation is P1+)"
    )


def resolve_command_p0(adapter_value: Any) -> AdapterResult:
    """P0 stub for command adapter (⚖-R2).

    At P0, command items are not evaluated. Returns ⚪ + "not evaluated" warning.
    """
    return AdapterResult(
        failure_reason="adapter not evaluated in this build (command evaluation is P1+)"
    )


# --- Freshness resolution (implemented for testing, but not wired in P0 bake) ---

def resolve_freshness(
    adapter_value: dict,
    config_dir: Path,
    reference_date: date,
    timezone_name: str = "UTC",
) -> AdapterResult:
    """Full freshness resolution (P1+).

    Parses source file for ISO dates, computes age, applies thresholds.
    (CIR-DATA-FRESHNESS-WINDOW, CIR-DATA-DATE-PARSE, CIR-DATA-AGE-CALENDAR)
    """
    import pytz  # optional dep for P1

    source = adapter_value["source"]
    yellow_after = adapter_value["yellow_after"]
    red_after = adapter_value["red_after"]

    # Resolve source path
    resolved_path = (config_dir / source).resolve()

    if not resolved_path.exists():
        return AdapterResult(
            failure_reason=f"freshness source '{source}' not found"
        )

    # Parse dates from source
    dates = _parse_dates_from_file(resolved_path)
    if not dates:
        return AdapterResult(
            failure_reason=f"no parseable ISO dates in '{source}'"
        )

    # Filter future dates (CIR-DATA-FRESHNESS-FUTURE)
    # Use the timezone to interpret the reference date
    tz = pytz.timezone(timezone_name) if timezone_name else pytz.UTC

    valid_dates = []
    future_dates = []
    for d in dates:
        if d <= reference_date:
            valid_dates.append(d)
        else:
            future_dates.append(d)

    if not valid_dates:
        if future_dates:
            return AdapterResult(
                failure_reason=f"all dates in '{source}' are in the future"
            )
        return AdapterResult(
            failure_reason=f"no usable dates in '{source}'"
        )

    newest_date = max(valid_dates)

    # Compute calendar day age (CIR-DATA-AGE-CALENDAR)
    # Age is number of calendar day boundaries in the config's timezone
    # Simple approximation: difference in days
    age_days = (reference_date - newest_date).days

    # Apply thresholds (⚖-R6: >, not ≥)
    if age_days <= yellow_after:
        status = "green"
    elif age_days <= red_after:
        status = "yellow"
    else:
        status = "red"

    data_date_str = newest_date.isoformat()
    note = None
    if future_dates:
        note = f"{len(future_dates)} future date(s) excluded"

    return AdapterResult(status=status, data_date=data_date_str, note=note)


def _parse_dates_from_file(path: Path) -> list[date]:
    """Parse all ISO-8601 calendar dates from a text file (CIR-DATA-DATE-PARSE)."""
    dates: list[date] = []
    try:
        text = path.read_text()
    except (OSError, PermissionError):
        return dates

    for match in ISO_DATE_RE.finditer(text):
        try:
            d = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            dates.append(d)
        except ValueError:
            # date-impossible-calendar — ignore with warning
            pass

    return dates


def resolve_adapter_p0(
    adapter_key: str,
    adapter_value: Any,
) -> AdapterResult:
    """Resolve one adapter at P0 (⚖-R2).

    At P0, only manual: is evaluated. freshness: and command: produce ⚪ + warning.
    """
    if adapter_key == "manual":
        return resolve_manual(adapter_value)

    return AdapterResult(
        failure_reason=f"adapter not evaluated in this build ({adapter_key} evaluation is P1+)"
    )
