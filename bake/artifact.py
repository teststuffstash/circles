"""Artifact building per CIR-BAKE-ARTIFACT.

Turns a validated config + resolved adapter results into the data.json artifact.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from bake.validate import BuildWarning, ConfigError
from bake.adapters import AdapterResult


# Display word mapping (CIR-RENDER-PALETTE, CIR-BAKE-STATUS-VALUES)
STATUS_TO_DISPLAY = {
    "green": "ok",
    "yellow": "attention",
    "red": "act",
    "grey": "unmonitored",
}


def build_artifact(
    config: dict,
    config_path: Path,
    reference_date: date,
    adapter_results: dict[str, AdapterResult],
    warnings: list[BuildWarning],
    generated_at: datetime | None = None,
) -> dict:
    """Build the data.json artifact (CIR-BAKE-ARTIFACT).

    Args:
        config: Validated config dict.
        config_path: Path to the config file (for resolving relative paths).
        reference_date: The injected reference date (CIR-ADAPT-REFERENCE-DATE).
        adapter_results: Map of "<ring_id>/<item_id>" -> AdapterResult.
        warnings: Build warnings collected during validation and resolution.
        generated_at: Timestamp for the bake. Defaults to now (UTC).

    Returns:
        The data.json artifact as a dict.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    timezone_name = config.get("timezone", "UTC")

    artifact: dict[str, Any] = {
        "version": 1,
        "spec_version": config.get("spec_version", 0),
        "person": config["person"],
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reference_date": reference_date.isoformat(),
        "timezone": timezone_name,
        "stale_after_hours": None,
        "rings": [],
        "warnings": [],
    }

    # Build rings
    for ring in config.get("rings", []):
        ring_id = ring["id"]
        ring_items = []

        for item in ring.get("items", []):
            item_id = item["id"]
            ref = f"{ring_id}/{item_id}"
            result = adapter_results.get(ref)

            item_artifact = _build_item_artifact(item, ref, result)
            ring_items.append(item_artifact)

        ring_artifact = {
            "id": ring_id,
            "label": ring["label"],
            "items": ring_items,
        }
        artifact["rings"].append(ring_artifact)

    # Build warnings
    for w in warnings:
        artifact["warnings"].append(w.to_dict())

    return artifact


def _build_item_artifact(
    item: dict,
    ref: str,
    result: AdapterResult | None,
) -> dict:
    """Build one item's artifact entry."""
    item_id = item["id"]

    # Determine status and grey_reason
    if result is None or (result.is_failure and not result.is_success):
        # No adapter or adapter failure -> grey
        status = "grey"
        if result is not None and result.failure_reason:
            grey_reason = "by-failure"
        else:
            grey_reason = "by-choice"
    else:
        status = result.status
        grey_reason = None

    # Compose detail_line (CIR-DATA-DETAIL-LINE, CIR-BAKE-DETAIL-FIELDS)
    detail_line = _compose_detail_line(
        guardrail=item.get("guardrail"),
        status=status,
        grey_reason=grey_reason,
        data_date=result.data_date if result else None,
        note=item.get("note"),
        failure_reason=result.failure_reason if result else None,
    )

    item_artifact = {
        "id": item_id,
        "label": item["label"],
        "status": status,
        "grey_reason": grey_reason,
        "guardrail": item.get("guardrail") or None,
        "note": item.get("note") or None,
        "link": item.get("link") or None,
        "share": item.get("share", 1),
        "last_data_date": result.data_date if result and result.data_date else None,
        "detail_line": detail_line,
        "detail_page": None,
    }

    return item_artifact


def _compose_detail_line(
    guardrail: str | None,
    status: str,
    grey_reason: str | None,
    data_date: str | None,
    note: str | None,
    failure_reason: str | None,
) -> str:
    """Compose the detail line (CIR-DATA-DETAIL-LINE, CIR-BAKE-DETAIL-FIELDS).

    Fixed order: guardrail · status_word · last_data_date · note · failure_reason
    """
    segments: list[str] = []

    # Guardrail (if present)
    if guardrail:
        segments.append(guardrail)

    # Status word
    if status == "grey" and grey_reason == "by-choice":
        # CIR-DATA-GREY-REASON#unmonitored-by-choice: detail line "not monitored"
        segments.append("not monitored")
    else:
        segments.append(STATUS_TO_DISPLAY.get(status, status))

    # Last data date
    if data_date:
        segments.append(f"last data {data_date}")

    # Note
    if note:
        segments.append(note)

    # Failure reason
    if failure_reason:
        segments.append(failure_reason)

    return " · ".join(segments)