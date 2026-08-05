"""Build the baked artifact (data.json) per CIR-BAKE-ARTIFACT.

The artifact is a JSON structure matching the schema in specs/data/data-json.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from bake.config import BuildWarning, Config
from bake.resolve import ResolutionResult


@dataclass
class BakedArtifact:
    """The built artifact ready for serialization."""
    version: int = 1
    spec_version: int = 0
    person: str = ""
    generated_at: str = ""
    reference_date: str = ""
    timezone: str = "UTC"
    stale_after_hours: int | None = None  # null at P0 (⚖-R15)
    rings: list[dict[str, Any]] = None
    warnings: list[dict[str, str | None]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "spec_version": self.spec_version,
            "person": self.person,
            "generated_at": self.generated_at,
            "reference_date": self.reference_date,
            "timezone": self.timezone,
            "stale_after_hours": self.stale_after_hours,
            "rings": self.rings or [],
            "warnings": self.warnings or [],
        }


def build_artifact(
    config: Config,
    resolution: ResolutionResult,
    *,
    config_warnings: list[BuildWarning] | None = None,
    ref_date: date | None = None,
    now: datetime | None = None,
) -> BakedArtifact:
    """Build the artifact from validated config + resolved items.

    Args:
        config: The validated config.
        resolution: The resolution result.
        config_warnings: Build warnings from config validation.
        ref_date: The reference date to use (default: today UTC).
        now: The current time (default: now UTC).
    """
    if ref_date is None:
        ref_date = date.today()
    if now is None:
        now = datetime.now(timezone.utc)

    # Build rings structure, preserving config order (CIR-RENDER-RING-ORDER)
    ring_groups: dict[str, list[dict]] = {}
    for ring in config.rings:
        ring_groups[ring.id] = []

    for ri in resolution.items:
        ring_groups.setdefault(ri.ring_id, []).append({
            "id": ri.id,
            "label": ri.label,
            "status": ri.status,
            "grey_reason": ri.grey_reason,
            "guardrail": ri.guardrail,
            "note": ri.note,
            "link": ri.link,
            "share": ri.share,
            "last_data_date": ri.last_data_date,
            "detail_line": ri.detail_line,
            "detail_page": None,  # P2
        })

    rings = [
        {"id": ring.id, "label": ring.label, "items": ring_groups.get(ring.id, [])}
        for ring in config.rings
    ]

    # Build warnings list (CIR-BAKE-WARNINGS): resolution + config-level
    artifact_warnings: list[dict[str, str | None]] = []
    for w in resolution.warnings:
        artifact_warnings.append({"item": w.item_ref, "message": w.message})
    for w in (config_warnings or []):
        artifact_warnings.append({"item": w.item_ref, "message": w.message})

    return BakedArtifact(
        spec_version=config.spec_version,
        person=config.person,
        generated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        reference_date=ref_date.isoformat(),
        timezone=config.timezone,
        rings=rings,
        warnings=artifact_warnings,
    )


def serialize_artifact(artifact: BakedArtifact) -> str:
    """Serialize artifact to JSON string."""
    return json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False) + "\n"