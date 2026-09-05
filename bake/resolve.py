# bake/resolve.py — turn a validated Config into the CIR-BAKE-ARTIFACT dict
#
# This module owns the resolution logic: every item's status, grey_reason, detail_line,
# and the artifact envelope. It does NOT read files, run commands, or touch the clock —
# those are adapter concerns (bake/adapters.py), called from here only under
# `evaluate=True` (the P1 nightly bake, issue #33). Command execution lands in issue #33
# slice B; until then `command:` resolves not-evaluated in every build.
#
# Requirements owned:
#   CIR-ADAPT-CONTRACT, CIR-ADAPT-REFERENCE-DATE, CIR-ADAPT-MANUAL, CIR-ADAPT-NO-PAGE-LOGIC
#   CIR-DATA-STATUS-RESOLUTION, CIR-DATA-STATUS-MANUAL-VALUES, CIR-DATA-GREY-REASON,
#   CIR-DATA-FAILURE-IS-GREY, CIR-DATA-NO-AGGREGATION, CIR-DATA-RESOLUTION-TIME,
#   CIR-DATA-DETAIL-LINE (⚖-R51), CIR-DATA-FRESHNESS-WINDOW (predicate + wiring)
#   CIR-BAKE-ARTIFACT, -STATUS-VALUES, -VERSION, -GENERATED-AT, -WARNINGS,
#   -DETAIL-FIELDS, -DETERMINISM, -EXPOSURE, -PAGE-DOES-NOT-RESOLVE
#   CIR-BAKE-STALE-SELF (stale_after_hours: null at P0)
#   CIR-PROC-BAKE-ONE-PATH, CIR-PROC-PHASE-P0

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from bake.adapters import AdapterResult, evaluate_freshness
from bake.config import Config, Item, Ring

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

Status = Literal["green", "yellow", "red", "grey"]
GreyReason = Literal["by-choice", "by-failure", "not-evaluated"]


@dataclass(frozen=True)
class ResolvedItem:
    """The resolved state of one item, ready for serialisation."""
    id: str
    label: str
    status: Status
    grey_reason: GreyReason | None
    guardrail: str | None
    note: str | None
    link: str | None
    share: float
    last_data_date: str | None  # ISO date string, or None
    detail_line: str
    detail_page: str | None  # P2 — always None at P0


@dataclass(frozen=True)
class ResolvedRing:
    id: str
    label: str
    items: tuple[ResolvedItem, ...]


@dataclass(frozen=True)
class ArtifactWarning:
    item: str | None
    message: str


# ---------------------------------------------------------------------------
# Status vocabulary — wire values (CIR-BAKE-STATUS-VALUES)
# ---------------------------------------------------------------------------

# Wire values are green|yellow|red|grey — never emoji, never display words (⚖-R19).
# Display words (ok|attention|act|unmonitored) belong to the page only.


# ---------------------------------------------------------------------------
# CIR-DATA-FRESHNESS-WINDOW — the boundary predicate (pure, unwired at P0)
# ---------------------------------------------------------------------------

def window_status(age_days: int, yellow_after: int, red_after: int) -> Status:
    """Return the status for *age_days* given the freshness thresholds.

    Implements ⚖-R6's strict `>` boundary:
      - age ≤ yellow_after  → 🟢
      - yellow_after < age ≤ red_after → 🟡
      - age > red_after     → 🔴

    A pure predicate: the freshness adapter (bake/adapters.py) calls it with the
    calendar age it computed, and resolve() reaches it only under `evaluate=True`
    (CIR-PROC-PHASE-P0#p0-unevaluated-adapters-are-grey keeps the P0 build clear of it).
    """
    if age_days <= yellow_after:
        return "green"
    if age_days <= red_after:
        return "yellow"
    return "red"


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def _resolve_manual(adapter_raw: dict) -> Status:
    """Resolve a manual adapter. Returns the declared status."""
    value = adapter_raw["manual"]
    # Already validated by config.py — must be green|yellow|red
    return value  # type: ignore[return-value]


def _resolve_not_evaluated() -> tuple[Status, GreyReason, str]:
    """Resolve an adapter this build deliberately does not run.

    Per CIR-PROC-PHASE-P0#p0-unevaluated-adapters-are-grey and ⚖-R50:
    the adapter is not evaluated in this build → ⚪ with grey_reason: not-evaluated.
    Reached for freshness: and command: without `evaluate`, and for command: even
    with it — command execution lands in issue #33 slice B.
    """
    return "grey", "not-evaluated", "adapter not evaluated in this build"


def _run_adapter(
    kind: str,
    raw: dict,
    *,
    config_dir: Path,
    reference_date: date,
    tz_name: str,
) -> AdapterResult:
    """Call the adapter for *kind*, fencing any unexpected exception into a failure.

    CIR-ADAPT-CONTRACT#adapter-failure-is-isolated: one adapter raising must not take
    the bake down. The exception's text is NOT forwarded — it may carry host paths
    (CIR-BAKE-EXPOSURE#no-absolute-host-paths); only its class name is.
    """
    try:
        if kind == "freshness":
            return evaluate_freshness(raw, config_dir, reference_date, tz_name)
        raise ValueError(f"no evaluator for adapter kind {kind!r}")
    except Exception as e:  # noqa: BLE001 — the isolation boundary
        return AdapterResult.failed(f"adapter raised {type(e).__name__}")


def _resolve_no_adapter() -> tuple[Status, GreyReason]:
    """Resolve an item with no adapter declared.

    Per CIR-DATA-STATUS-RESOLUTION#no-adapter-declared: ⚪ unmonitored, reason by-choice.
    """
    return "grey", "by-choice"


def _build_detail_line(
    status: Status,
    grey_reason: GreyReason | None,
    guardrail: str | None,
    note: str | None,
    last_data_date: str | None,
    failure_message: str | None = None,
) -> str:
    """Compose the detail line per CIR-BAKE-DETAIL-FIELDS and ⚖-R51.

    Order: guardrail · status_word · [last data YYYY-MM-DD] · [note] · [reason]

    Per ⚖-R51: the status word is always the display word 'unmonitored' for grey items,
    with the reason as its own following segment. For non-grey items, the display word
    is 'ok' / 'attention' / 'act'.
    """
    parts: list[str] = []

    # Guardrail (if present)
    if guardrail:
        parts.append(guardrail)

    # Status word (display vocabulary, not wire vocabulary — ⚖-R19)
    if status == "grey":
        parts.append("unmonitored")
    elif status == "green":
        parts.append("ok")
    elif status == "yellow":
        parts.append("attention")
    elif status == "red":
        parts.append("act")

    # Last data date (if present — manual items have none)
    if last_data_date:
        parts.append(f"last data {last_data_date}")

    # Note (if present)
    if note:
        parts.append(note)

    # Grey reason / failure message (⚖-R51: reason is its own segment)
    if grey_reason == "by-choice":
        pass  # No extra segment for deliberate unmonitored
    elif grey_reason == "by-failure" and failure_message:
        parts.append(failure_message)
    elif grey_reason == "not-evaluated":
        parts.append("not evaluated in this build")

    return " · ".join(parts)


def _resolve_item(
    item: Item,
    ring_id: str,
    *,
    config_dir: Path,
    reference_date: date,
    tz_name: str,
    evaluate: bool,
) -> tuple[ResolvedItem, ArtifactWarning | None]:
    """Resolve a single item to its artifact entry.

    Args:
        item: The item to resolve.
        ring_id: The id of the ring this item belongs to (for warning refs).
        config_dir: The root every adapter source resolves under.
        reference_date: The one injected date every adapter ages against.
        tz_name: The config's timezone (IANA name).
        evaluate: Run the freshness adapter (P1). False keeps the P0 behaviour.

    Returns (resolved_item, optional_warning).
    """
    warning: ArtifactWarning | None = None
    status: Status
    grey_reason: GreyReason | None = None
    last_data_date: str | None = None
    failure_message: str | None = None
    ref = f"{ring_id}/{item.id}"

    if item.adapter is None:
        # No adapter → ⚪ by-choice (CIR-DATA-STATUS-RESOLUTION#no-adapter-declared)
        status, grey_reason = _resolve_no_adapter()
    elif item.adapter.kind == "manual":
        # Manual adapter → declared status (CIR-ADAPT-MANUAL)
        status = _resolve_manual(item.adapter.raw)
    elif item.adapter.kind == "freshness" and evaluate:
        # P1: the freshness adapter answers, or fails into ⚪ by-failure
        # (CIR-ADAPT-FRESHNESS, CIR-DATA-FAILURE-IS-GREY)
        result = _run_adapter(
            "freshness", item.adapter.raw,
            config_dir=config_dir, reference_date=reference_date, tz_name=tz_name,
        )
        if result.failure is not None:
            status, grey_reason, failure_message = "grey", "by-failure", result.failure
            warning = ArtifactWarning(item=ref, message=result.failure)
        else:
            status = result.status  # type: ignore[assignment]  # never grey (AdapterResult)
            last_data_date = result.data_date.isoformat()  # type: ignore[union-attr]
            if result.note:
                warning = ArtifactWarning(item=ref, message=result.note)
    elif item.adapter.kind in ("freshness", "command"):
        # P0: not evaluated (CIR-PROC-PHASE-P0#p0-unevaluated-adapters-are-grey)
        status, grey_reason, failure_message = _resolve_not_evaluated()
        warning = ArtifactWarning(
            item=f"{ring_id}/{item.id}",
            message="adapter not evaluated in this build",
        )
    else:
        # Unknown adapter kind — should not happen with validated config
        status, grey_reason, failure_message = _resolve_not_evaluated()
        warning = ArtifactWarning(
            item=f"{ring_id}/{item.id}",
            message="adapter not evaluated in this build",
        )

    detail_line = _build_detail_line(
        status=status,
        grey_reason=grey_reason,
        guardrail=item.guardrail,
        note=item.note,
        last_data_date=last_data_date,
        failure_message=failure_message,
    )

    resolved = ResolvedItem(
        id=item.id,
        label=item.label,
        status=status,
        grey_reason=grey_reason,
        guardrail=item.guardrail,
        note=item.note,
        link=item.link,
        share=item.share,
        last_data_date=last_data_date,
        detail_line=detail_line,
        detail_page=None,  # P2
    )

    return resolved, warning





# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve(
    config: Config,
    *,
    reference_date: date,
    generated_at: datetime,
    evaluate: bool = False,
) -> dict:
    """Return the CIR-BAKE-ARTIFACT dict, exactly as serialised to data.json.

    Args:
        config: A validated Config from bake.config.load_config().
        reference_date: The single date every adapter ages against
            (CIR-ADAPT-REFERENCE-DATE). For fixture bakes this is 2026-08-03.
        generated_at: The UTC timestamp of the bake run.
        evaluate: False (the default, the image-build bake) leaves freshness: and
            command: items ⚪ not-evaluated. True (the nightly bake, issue #33)
            evaluates freshness: adapters; command execution lands in issue #33 slice B,
            so command: items stay not-evaluated either way.

    Returns:
        A dict matching the CIR-BAKE-ARTIFACT schema, ready for JSON serialisation.
    """
    resolved_rings: list[dict] = []
    all_warnings: list[dict] = []

    for ring in config.rings:
        resolved_items: list[dict] = []
        for item in ring.items:
            resolved, warning = _resolve_item(
                item, ring.id,
                config_dir=config.config_dir,
                reference_date=reference_date,
                tz_name=config.timezone,
                evaluate=evaluate,
            )
            if warning is not None:
                all_warnings.append({"item": warning.item, "message": warning.message})

            # Build the item dict per CIR-BAKE-ARTIFACT schema
            item_dict: dict = {
                "id": resolved.id,
                "label": resolved.label,
                "status": resolved.status,
                "grey_reason": resolved.grey_reason,
                "guardrail": resolved.guardrail,
                "note": resolved.note,
                "link": resolved.link,
                "share": resolved.share,
                "last_data_date": resolved.last_data_date,
                "detail_line": resolved.detail_line,
                "detail_page": resolved.detail_page,
            }
            resolved_items.append(item_dict)

        resolved_rings.append({
            "id": ring.id,
            "label": ring.label,
            "items": resolved_items,
        })

    # Add config-level warnings (CIR-BAKE-WARNINGS)
    for w in config.warnings:
        all_warnings.append({"item": w.item, "message": w.message})

    # Build the artifact (CIR-BAKE-ARTIFACT)
    artifact: dict = {
        "version": 1,
        "spec_version": config.spec_version,
        "person": config.person,
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reference_date": reference_date.isoformat(),
        "timezone": config.timezone,
        "stale_after_hours": None,  # P0: no cadence exists (CIR-BAKE-STALE-SELF)
        "rings": resolved_rings,
        "warnings": all_warnings,
    }

    return artifact