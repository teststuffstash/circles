"""Load and validate circles.yaml per CIR-DATA-VALIDATION, CIR-DATA-SCHEMA-*.

Config errors fail the bake (CIR-DATA-CONFIG-ERROR-FAILS). Unknown keys outside
status: produce build warnings. Unknown keys inside status: are config errors (⚖-R7).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ── slug pattern ──────────────────────────────────────────────────────────────
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
LINK_RE = re.compile(r"^https?://|^/")  # https? or root-relative (⚖-R16)


# ── domain types ──────────────────────────────────────────────────────────────
@dataclass
class ManualAdapter:
    value: str  # "green" | "yellow" | "red"


@dataclass
class FreshnessAdapter:
    source: str
    yellow_after: int
    red_after: int


@dataclass
class CommandAdapter:
    argv: list[str]


Adapter = ManualAdapter | FreshnessAdapter | CommandAdapter


@dataclass
class Item:
    id: str
    label: str
    ring_id: str
    guardrail: str | None = None
    note: str | None = None
    link: str | None = None
    share: int | float = 1
    status: Adapter | None = None  # None → ⚪ by-choice


@dataclass
class Ring:
    id: str
    label: str
    items: list[Item] = field(default_factory=list)


@dataclass
class Config:
    spec_version: int = 0
    person: str = ""
    timezone: str = "UTC"
    rings: list[Ring] = field(default_factory=list)


# ── validation result ─────────────────────────────────────────────────────────
@dataclass
class ConfigError:
    message: str
    item_ref: str | None = None  # <ring>/<item> or None for config-level


@dataclass
class BuildWarning:
    message: str
    item_ref: str | None = None


@dataclass
class ValidationResult:
    config: Config | None
    errors: list[ConfigError] = field(default_factory=list)
    warnings: list[BuildWarning] = field(default_factory=list)


# ── known adapter keys for v0 (⚖-R7 carve-out) ───────────────────────────────
KNOWN_ADAPTER_KEYS = frozenset({"manual", "freshness", "command"})


# ── load ──────────────────────────────────────────────────────────────────────
def load_config(path: str | Path) -> ValidationResult:
    """Load and validate a circles.yaml file.

    Returns a ValidationResult. If errors is non-empty the config is unusable
    (CIR-DATA-CONFIG-ERROR-FAILS — no artifact is written).
    """
    path = Path(path)
    errors: list[ConfigError] = []
    warnings: list[BuildWarning] = []

    if not path.exists():
        errors.append(ConfigError(f"config file not found: {path}"))
        return ValidationResult(config=None, errors=errors)

    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        errors.append(ConfigError(f"invalid YAML: {exc}"))
        return ValidationResult(config=None, errors=errors)

    if not isinstance(raw, dict):
        errors.append(ConfigError("config must be a YAML mapping"))
        return ValidationResult(config=None, errors=errors)

    # ── top-level unknown keys (CIR-DATA-VALIDATION#unknown-toplevel-key) ────
    TOPLEVEL_KEYS = frozenset({"spec_version", "person", "timezone", "rings"})
    for key in raw:
        if key not in TOPLEVEL_KEYS:
            warnings.append(BuildWarning(f"unknown top-level key: '{key}'"))

    # ── spec_version ──────────────────────────────────────────────────────────
    spec_version = raw.get("spec_version", 0)
    if not isinstance(spec_version, int) or spec_version < 0:
        errors.append(ConfigError("spec_version must be a non-negative integer"))
        # keep going so we collect all errors
    if spec_version > 0:
        errors.append(ConfigError(f"config is newer than this build (spec_version={spec_version}, understood=0)"))

    # ── person ────────────────────────────────────────────────────────────────
    person = raw.get("person")
    if not person or not isinstance(person, str):
        errors.append(ConfigError("person is required and must be a string"))

    # ── timezone ──────────────────────────────────────────────────────────────
    timezone = raw.get("timezone", "UTC")
    if not isinstance(timezone, str):
        errors.append(ConfigError("timezone must be a string"))

    # ── rings ─────────────────────────────────────────────────────────────────
    raw_rings = raw.get("rings")
    if not raw_rings:
        errors.append(ConfigError("rings is required (must be a non-empty list)"))
        return ValidationResult(config=None, errors=errors)
    if not isinstance(raw_rings, list):
        errors.append(ConfigError("rings must be a list"))
        return ValidationResult(config=None, errors=errors)
    if len(raw_rings) == 0:
        errors.append(ConfigError("rings: [] — nothing to draw (CIR-DATA-SCHEMA-TOPLEVEL#rings-empty)"))
        return ValidationResult(config=None, errors=errors)

    ring_ids: set[str] = set()
    rings: list[Ring] = []

    for ri, raw_ring in enumerate(raw_rings):
        if not isinstance(raw_ring, dict):
            errors.append(ConfigError(f"rings[{ri}] must be a mapping"))
            continue

        # unknown ring keys
        RING_KEYS = frozenset({"id", "label", "items"})
        for key in raw_ring:
            if key not in RING_KEYS:
                warnings.append(BuildWarning(f"unknown ring key: '{key}'"))

        # ring id
        rid = raw_ring.get("id")
        if not isinstance(rid, str) or not SLUG_RE.match(rid):
            errors.append(ConfigError(f"ring id must be a slug matching {SLUG_RE.pattern}"
                                      f" (got {rid!r})"))
            continue
        if rid in ring_ids:
            errors.append(ConfigError(f"duplicate ring id: {rid}"))
            continue
        ring_ids.add(rid)

        # ring label
        rlabel = raw_ring.get("label")
        if not rlabel or not isinstance(rlabel, str):
            errors.append(ConfigError(f"ring {rid}: label is required"))
            continue

        # ── items ─────────────────────────────────────────────────────────────
        raw_items = raw_ring.get("items", [])
        if not isinstance(raw_items, list):
            errors.append(ConfigError(f"ring {rid}: items must be a list"))
            continue

        item_ids: set[str] = set()
        items: list[Item] = []

        if len(raw_items) == 0:
            # empty ring → renders as empty band + warning (⚖-R13)
            warnings.append(BuildWarning(f"ring {rid} has no items — renders as empty band"))

        for ii, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, dict):
                errors.append(ConfigError(f"ring {rid}/items[{ii}] must be a mapping"))
                continue

            # unknown item keys (CIR-DATA-VALIDATION#unknown-item-key)
            ITEM_KEYS = frozenset({"id", "label", "guardrail", "note", "link", "share", "status"})
            for key in raw_item:
                if key not in ITEM_KEYS:
                    warnings.append(BuildWarning(f"ring {rid}/items[{ii}]: unknown key '{key}'"))

            # item id
            iid = raw_item.get("id")
            if not isinstance(iid, str) or not SLUG_RE.match(iid):
                errors.append(ConfigError(f"ring {rid}: item id must be a slug matching {SLUG_RE.pattern}"
                                          f" (got {iid!r})"))
                continue
            if iid in item_ids:
                errors.append(ConfigError(f"ring {rid}: duplicate item id: {iid}"))
                continue
            item_ids.add(iid)

            # item label
            ilabel = raw_item.get("label")
            if not ilabel or not isinstance(ilabel, str):
                errors.append(ConfigError(f"ring {rid}/{iid}: label is required"))

            # guardrail / note
            guardrail = raw_item.get("guardrail")
            if guardrail is not None and not isinstance(guardrail, str):
                errors.append(ConfigError(f"ring {rid}/{iid}: guardrail must be a string"))
            note = raw_item.get("note")
            if note is not None and not isinstance(note, str):
                errors.append(ConfigError(f"ring {rid}/{iid}: note must be a string"))

            # link (CIR-DATA-SCHEMA-LINK)
            link = raw_item.get("link")
            if link is not None:
                if not isinstance(link, str):
                    errors.append(ConfigError(f"ring {rid}/{iid}: link must be a string"))
                elif link.startswith("//"):
                    errors.append(ConfigError(f"ring {rid}/{iid}: scheme-relative links are not allowed"
                                              f" (got {link!r})"))
                elif not LINK_RE.match(link):
                    errors.append(ConfigError(f"ring {rid}/{iid}: link must be https?:// or root-relative path"
                                              f" (got {link!r})"))

            # share (CIR-DATA-SHARE)
            share = raw_item.get("share", 1)
            if not isinstance(share, (int, float)) or share <= 0:
                errors.append(ConfigError(f"ring {rid}/{iid}: share must be a positive number"))

            # status (CIR-DATA-SCHEMA-ADAPTER-SLOT)
            adapter = None
            raw_status = raw_item.get("status")
            if raw_status is not None:
                if not isinstance(raw_status, dict):
                    errors.append(ConfigError(f"ring {rid}/{iid}: status must be a mapping"))
                elif len(raw_status) == 0:
                    errors.append(ConfigError(f"ring {rid}/{iid}: status: {{}} — remove status: instead"))
                else:
                    # check for unknown adapter keys (⚖-R7 carve-out)
                    for sk in raw_status:
                        if sk not in KNOWN_ADAPTER_KEYS:
                            errors.append(ConfigError(f"ring {rid}/{iid}: unknown adapter key '{sk}'"
                                                      f" — v0 adapters: {', '.join(sorted(KNOWN_ADAPTER_KEYS))}"))
                    if len(raw_status) > 1:
                        errors.append(ConfigError(f"ring {rid}/{iid}: status has two adapters"
                                                  f" — at most one per item"))
                    else:
                        adapter = _parse_adapter(rid, iid, raw_status, errors)

            items.append(Item(
                id=iid,
                label=ilabel or "",
                ring_id=rid,
                guardrail=guardrail if isinstance(guardrail, str) else None,
                note=note if isinstance(note, str) else None,
                link=link if isinstance(link, str) else None,
                share=float(share) if isinstance(share, (int, float)) else 1,
                status=adapter,
            ))

        rings.append(Ring(id=rid, label=rlabel, items=items))

    if errors:
        return ValidationResult(config=None, errors=errors, warnings=warnings)

    return ValidationResult(
        config=Config(
            spec_version=int(spec_version),
            person=str(person or ""),
            timezone=str(timezone),
            rings=rings,
        ),
        warnings=warnings,
    )


def _parse_adapter(rid: str, iid: str, raw_status: dict, errors: list[ConfigError]) -> Adapter | None:
    """Parse the single adapter from status dict. Returns None if error."""
    for key, value in raw_status.items():
        if key == "manual":
            if not isinstance(value, str):
                errors.append(ConfigError(f"ring {rid}/{iid}: manual must be a string"))
                return None
            if value not in ("green", "yellow", "red"):
                errors.append(ConfigError(f"ring {rid}/{iid}: manual must be 'green', 'yellow', or 'red'"
                                          f" (got {value!r})"))
                return None
            return ManualAdapter(value=value)
        elif key == "freshness":
            if not isinstance(value, dict):
                errors.append(ConfigError(f"ring {rid}/{iid}: freshness must be a mapping"))
                return None
            source = value.get("source")
            if not isinstance(source, str):
                errors.append(ConfigError(f"ring {rid}/{iid}: freshness.source is required (string)"))
                return None
            # source must not escape the config dir (CIR-DATA-SOURCE-PATH)
            if source.startswith("/") or ".." in source.split("/"):
                errors.append(ConfigError(
                    f"ring {rid}/{iid}: freshness.source may not be absolute or escape the config dir"
                    f" (got {source!r})"
                ))
                return None
            yellow_after = value.get("yellow_after")
            red_after = value.get("red_after")
            if not isinstance(yellow_after, int) or yellow_after < 1:
                errors.append(ConfigError(f"ring {rid}/{iid}: freshness.yellow_after must be integer ≥ 1"))
                return None
            if not isinstance(red_after, int) or red_after < 1:
                errors.append(ConfigError(f"ring {rid}/{iid}: freshness.red_after must be integer ≥ 1"))
                return None
            if yellow_after >= red_after:
                errors.append(ConfigError(f"ring {rid}/{iid}: freshness.yellow_after must be < red_after"))
                return None
            return FreshnessAdapter(source=source, yellow_after=yellow_after, red_after=red_after)
        elif key == "command":
            if not isinstance(value, list) or len(value) == 0:
                errors.append(ConfigError(f"ring {rid}/{iid}: command must be a non-empty argv array"))
                return None
            if not all(isinstance(v, str) for v in value):
                errors.append(ConfigError(f"ring {rid}/{iid}: command argv entries must be strings"))
                return None
            return CommandAdapter(argv=value)
    return None