"""Status resolution at bake time (CIR-DATA-STATUS-RESOLUTION).

P0: only manual: adapters are evaluated. freshness: and command: items resolve to
⚪ + "not evaluated in this build" (⚖-R2). Items without a status: block → ⚪ by-choice.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from bake.config import (
    CommandAdapter,
    Config,
    FreshnessAdapter,
    Item,
    ManualAdapter,
    BuildWarning,
)


# ── resolved status ───────────────────────────────────────────────────────────
# Wire values per CIR-BAKE-STATUS-VALUES: green | yellow | red | grey
class StatusValue:
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GREY = "grey"


class GreyReason:
    BY_CHOICE = "by-choice"
    BY_FAILURE = "by-failure"


@dataclass
class ResolvedItem:
    """An item with its status resolved at bake time."""
    id: str
    label: str
    ring_id: str
    ring_label: str
    guardrail: str | None
    note: str | None
    link: str | None
    share: float
    status: str          # green | yellow | red | grey
    grey_reason: str | None   # by-choice | by-failure | not-evaluated | None
    last_data_date: str | None
    detail_line: str
    warnings: list[str]  # item-level warnings


@dataclass
class ResolutionResult:
    items: list[ResolvedItem]
    warnings: list[BuildWarning]


def resolve(config: Config) -> ResolutionResult:
    """Resolve all items in a config.

    In P0: only manual: adapters are evaluated. freshness:/command: resolve to
    ⚪ + "not evaluated in this build".
    """
    resolved: list[ResolvedItem] = []
    warnings: list[BuildWarning] = []

    for ring in config.rings:
        for item in ring.items:
            ri = _resolve_item(item, ring, config)
            resolved.append(ri)
            for w in ri.warnings:
                warnings.append(BuildWarning(
                    message=w,
                    item_ref=f"{ring.id}/{item.id}",
                ))

    return ResolutionResult(items=resolved, warnings=warnings)


def _resolve_item(item: Item, ring, config: Config) -> ResolvedItem:
    """Resolve one item's status."""
    adapter = item.status

    # No adapter → ⚪ by-choice (CIR-DATA-STATUS-RESOLUTION#no-adapter-declared).
    # Detail line "not monitored", plus note if present (CIR-DATA-GREY-REASON).
    if adapter is None:
        return _make_grey(
            item, ring, GreyReason.BY_CHOICE,
            word="not monitored",
            detail_text=item.note or None,
        )

    # Manual adapter (CIR-ADAPT-MANUAL)
    if isinstance(adapter, ManualAdapter):
        status = adapter.value
        word = _status_word(status)
        parts = _detail_parts(item, word)
        return ResolvedItem(
            id=item.id, label=item.label, ring_id=ring.id, ring_label=ring.label,
            guardrail=item.guardrail, note=item.note, link=item.link,
            share=item.share, status=status, grey_reason=None,
            last_data_date=None,
            detail_line=" · ".join(parts),
            warnings=[],
        )

    # Freshness / command → not evaluated in P0 (⚖-R2).
    # Wire grey_reason is by-choice|by-failure only (CIR-BAKE-ARTIFACT); the
    # "not evaluated in this build" phase road rides on by-failure with the
    # phase reason in the detail line + warning.
    if isinstance(adapter, (FreshnessAdapter, CommandAdapter)):
        kind = "freshness" if isinstance(adapter, FreshnessAdapter) else "command"
        ri = _make_grey(
            item, ring, GreyReason.BY_FAILURE,
            detail_text=f"not evaluated in this build ({kind} adapter)",
        )
        ri.warnings.append(f"{kind} adapter not evaluated in this build — ⚪")
        return ri

    # Should not reach here
    return _make_grey(item, ring, GreyReason.BY_FAILURE, detail_text="unknown adapter type")


def _make_grey(
    item: Item, ring,
    reason: str,
    word: str = "unmonitored",
    detail_text: str | None = None,
) -> ResolvedItem:
    """Create a grey resolved item.

    Args:
        item: The config item.
        ring: The config ring.
        reason: grey_reason wire value (by-choice | by-failure).
        word: Display word for the status (default "unmonitored").
        detail_text: Additional detail text (e.g. failure reason).
    """
    parts = _detail_parts(item, word)
    if detail_text:
        parts.append(detail_text)
    return ResolvedItem(
        id=item.id, label=item.label, ring_id=ring.id, ring_label=ring.label,
        guardrail=item.guardrail, note=item.note, link=item.link,
        share=item.share, status=StatusValue.GREY, grey_reason=reason,
        last_data_date=None,
        detail_line=" · ".join(parts),
        warnings=[],
    )


def _detail_parts(item: Item, word: str) -> list[str]:
    """Build the detail line segments (CIR-DATA-DETAIL-LINE)."""
    parts: list[str] = []
    if item.guardrail:
        parts.append(item.guardrail)
    parts.append(word)
    return parts


def _status_word(status: str) -> str:
    """Wire value → display word."""
    mapping = {
        "green": "ok",
        "yellow": "attention",
        "red": "act",
    }
    return mapping.get(status, status)