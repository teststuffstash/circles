# bake/config.py  — the language is Python (⚖-R49); the repo already pins python@3.11 + uv
"""
Read + validate circles.yaml into a typed Config model.

Hard boundary: AdapterSpec.raw is validated, never *evaluated*. This module must not read a
source: file, must not run a command:, must not import a date/clock, and must not compute a
status. CIR-PROC-PHASE-P0#p0-config-stays-valid is exactly this: the fixture's freshness: and
command: blocks validate at P0 and evaluate at P1, with no config migration in between.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Any CIR-DATA-CONFIG-ERROR-FAILS condition. Message names the offending path + why."""


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Warning:
    item: str | None       # ring-qualified item id, or None for a config-level warning
    message: str


@dataclass(frozen=True)
class AdapterSpec:
    kind: Literal["manual", "freshness", "command"]
    raw: dict              # shape-validated here; NEVER evaluated in this module


@dataclass(frozen=True)
class Item:
    id: str                # ring-qualified, e.g. "self/sleep" (CIR-DATA-IDENTITY)
    label: str
    share: float           # EFFECTIVE weight after CIR-DATA-SHARE resolution
    guardrail: str | None
    note: str | None
    link: str | None
    adapter: AdapterSpec | None


@dataclass(frozen=True)
class Ring:
    id: str
    label: str
    items: tuple[Item, ...]   # authored order preserved (CIR-DATA-SCHEMA-RING)


@dataclass(frozen=True)
class Config:
    person: str
    timezone: str
    spec_version: int
    rings: tuple[Ring, ...]   # authored order preserved
    warnings: tuple[Warning, ...]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_KNOWN_ADAPTERS = frozenset({"manual", "freshness", "command"})
_MANUAL_VALUES = frozenset({"green", "yellow", "red"})
_KNOWN_ITEM_KEYS = frozenset({"id", "label", "share", "guardrail", "note", "link", "status"})
_KNOWN_TOPLEVEL_KEYS = frozenset({"person", "timezone", "spec_version", "rings"})


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_slug(value: str, label: str, path: str) -> None:
    """Validate that *value* is a valid slug.  ⚖-R52: specific checks first."""
    # Specific-before-general (⚖-R52): check for spaces and slashes first
    if " " in value:
        raise ConfigError(f"{path}: '{label}' contains a space — ids must be slugs "
                          f"(lowercase, digits, hyphens only)")
    if "/" in value:
        raise ConfigError(f"{path}: '{label}' contains '/' — the slash is the ring/item "
                          f"separator and is not allowed in ids")
    if not _SLUG_RE.match(value):
        raise ConfigError(f"{path}: '{label}' is not a valid slug — ids must match "
                          r"^[a-z0-9][a-z0-9-]*$")


def _validate_link(link: Any, path: str) -> None:
    """Validate a link value (CIR-DATA-SCHEMA-LINK)."""
    if not isinstance(link, str):
        raise ConfigError(f"{path}.link: must be a string, got {type(link).__name__}")
    if link.startswith("javascript:"):
        raise ConfigError(f"{path}.link: 'javascript:' scheme is not allowed")
    if link.startswith("data:"):
        raise ConfigError(f"{path}.link: 'data:' scheme is not allowed")
    if link.startswith("//"):
        raise ConfigError(f"{path}.link: scheme-relative URLs are not allowed")
    if link.startswith("/"):
        return  # root-relative — valid
    if link.startswith("https://") or link.startswith("http://"):
        return  # absolute http(s) — valid
    raise ConfigError(f"{path}.link: bare relative paths are not allowed; "
                      f"use an absolute https:// URL or a root-relative /path")


def _validate_manual(raw: dict, path: str) -> None:
    """Validate a manual adapter block (CIR-DATA-STATUS-MANUAL-VALUES)."""
    if "manual" not in raw:
        return
    value = raw["manual"]
    if not isinstance(value, str):
        raise ConfigError(f"{path}.status.manual: must be a string, got {type(value).__name__}")
    if value != value.lower():
        raise ConfigError(f"{path}.status.manual: '{value}' is not lowercase — "
                          f"manual values must be lowercase (green, yellow, red)")
    if value == "grey":
        raise ConfigError(f"{path}.status.manual: 'grey' is not a valid manual value — "
                          f"omit status: entirely to be unmonitored")
    if value not in _MANUAL_VALUES:
        raise ConfigError(f"{path}.status.manual: '{value}' is not a valid manual value — "
                          f"must be one of green, yellow, red")


def _validate_freshness(raw: dict, path: str, config_dir: Path) -> None:
    """Validate a freshness adapter block (CIR-DATA-FRESHNESS-THRESHOLDS)."""
    freshness = raw.get("freshness", {})
    if not isinstance(freshness, dict):
        raise ConfigError(f"{path}.status.freshness: must be a mapping")

    # source is required
    if "source" not in freshness:
        raise ConfigError(f"{path}.status.freshness: 'source' is required")

    source = freshness["source"]
    if not isinstance(source, str):
        raise ConfigError(f"{path}.status.freshness.source: must be a string, "
                          f"got {type(source).__name__}")

    # Source path validation (CIR-DATA-SOURCE-PATH — config-error rows only)
    # ⚖-R52: absolute path check is syntactic, runs before parent traversal
    if source.startswith("/"):
        raise ConfigError(f"{path}.status.freshness.source: '{source}' is an absolute path — "
                          f"sources must be relative to the config directory")

    if source.startswith(".."):
        raise ConfigError(f"{path}.status.freshness.source: '{source}' escapes the config "
                          f"directory — parent traversal is not allowed")

    # Normalize and check containment — catches non-literal escapes like
    # 'sub/../../etc/hosts' that don't start with '..' but resolve outside
    # the config directory (CIR-DATA-SOURCE-PATH).
    resolved = (config_dir / source).resolve()
    try:
        resolved.relative_to(config_dir)
    except ValueError:
        raise ConfigError(f"{path}.status.freshness.source: '{source}' escapes the config "
                          f"directory — parent traversal is not allowed")

    # Threshold validation
    for key in ("yellow_after", "red_after"):
        if key not in freshness:
            raise ConfigError(f"{path}.status.freshness: '{key}' is required")

    yellow = freshness["yellow_after"]
    red = freshness["red_after"]

    for key, val in [("yellow_after", yellow), ("red_after", red)]:
        if not isinstance(val, int) or isinstance(val, bool):
            raise ConfigError(f"{path}.status.freshness.{key}: must be an integer, "
                              f"got {type(val).__name__}")
        if val < 1:
            raise ConfigError(f"{path}.status.freshness.{key}: must be ≥ 1, got {val}")

    if not (yellow < red):
        raise ConfigError(f"{path}.status.freshness: yellow_after ({yellow}) must be "
                          f"strictly less than red_after ({red})")


def _validate_command(raw: dict, path: str, config_dir: Path) -> None:
    """Validate a command adapter block (CIR-ADAPT-COMMAND — config-error rows only)."""
    command = raw.get("command")
    if command is None:
        return

    if not isinstance(command, list):
        raise ConfigError(f"{path}.status.command: must be an array (argv), not a string — "
                          f"use `command: [\"./script.sh\"]`")

    if len(command) == 0:
        raise ConfigError(f"{path}.status.command: argv array must have at least one element")

    for i, arg in enumerate(command):
        if not isinstance(arg, str):
            raise ConfigError(f"{path}.status.command[{i}]: each argument must be a string, "
                              f"got {type(arg).__name__}")

    # argv[0] executable existence and executable bit at validation
    # (CIR-ADAPT-COMMAND#command-executable-exists-at-validation,
    #  CIR-ADAPT-COMMAND#command-executable-bit-at-validation)
    # These are filesystem stats, not evaluation — they are config-error rows in scope for P0.
    executable = Path(command[0])
    if not executable.is_absolute():
        executable = config_dir / executable

    if not executable.exists():
        raise ConfigError(f"{path}.status.command[0]: executable '{command[0]}' not found — "
                          f"resolved to '{executable}'")
    if not os.access(executable, os.X_OK):
        raise ConfigError(f"{path}.status.command[0]: executable '{command[0]}' is not "
                          f"executable — resolved to '{executable}'")


def _validate_status(raw: dict, path: str, config_dir: Path | None = None) -> AdapterSpec | None:
    """Validate a status block. Returns an AdapterSpec or None if absent."""
    status = raw.get("status")
    if status is None:
        return None

    if not isinstance(status, dict):
        raise ConfigError(f"{path}.status: must be a mapping")

    if len(status) == 0:
        raise ConfigError(f"{path}.status: empty status block — omit status: entirely "
                          f"to be unmonitored")

    # Count adapter keys
    adapter_keys = [k for k in status if k in _KNOWN_ADAPTERS]
    unknown_keys = [k for k in status if k not in _KNOWN_ADAPTERS]

    # Unknown status keys are config errors (CIR-DATA-VALIDATION)
    if unknown_keys:
        raise ConfigError(f"{path}.status: unknown adapter key(s): {', '.join(unknown_keys)} — "
                          f"the v0 adapter set is manual, freshness, command")

    if len(adapter_keys) == 0:
        raise ConfigError(f"{path}.status: no recognized adapter key — "
                          f"the v0 adapter set is manual, freshness, command")

    if len(adapter_keys) > 1:
        raise ConfigError(f"{path}.status: multiple adapter keys ({', '.join(adapter_keys)}) — "
                          f"exactly one adapter per item is allowed")

    kind = adapter_keys[0]

    if kind == "manual":
        _validate_manual(status, path)
    elif kind == "freshness":
        _validate_freshness(status, path, config_dir)
    elif kind == "command":
        if config_dir is None:
            raise ConfigError(f"{path}.status.command: config_dir is required for command validation")
        _validate_command(status, path, config_dir)

    return AdapterSpec(kind=kind, raw=status)  # type: ignore[arg-type]


def _validate_item(raw: dict, ring_id: str, index: int, config_dir: Path) -> tuple[Item, list[Warning]]:
    """Validate and build an Item from raw dict. Returns (Item, list_of_warnings)."""
    path = f"rings[{ring_id}].items[{index}]"
    item_warnings: list[Warning] = []

    # Unknown item keys → warning (CIR-DATA-VALIDATION)
    unknown_keys = [k for k in raw if k not in _KNOWN_ITEM_KEYS]
    for key in unknown_keys:
        item_warnings.append(Warning(
            item=f"{ring_id}/{raw.get('id', '?')}" if isinstance(raw.get('id'), str) else None,
            message=f"unknown item key '{key}' ignored",
        ))

    # id is required (CIR-DATA-IDENTITY)
    if "id" not in raw:
        raise ConfigError(f"{path}: 'id' is required")
    item_id = raw["id"]
    if not isinstance(item_id, str):
        raise ConfigError(f"{path}.id: must be a string, got {type(item_id).__name__}")
    _validate_slug(item_id, item_id, path)

    # label is required
    if "label" not in raw:
        raise ConfigError(f"{path}: 'label' is required")
    label = raw["label"]
    if not isinstance(label, str):
        raise ConfigError(f"{path}.label: must be a string, got {type(label).__name__}")

    # share (CIR-DATA-SHARE)
    share = 1.0
    if "share" in raw:
        raw_share = raw["share"]
        if not isinstance(raw_share, (int, float)) or isinstance(raw_share, bool):
            raise ConfigError(f"{path}.share: must be a number, got {type(raw_share).__name__}")
        if raw_share <= 0:
            raise ConfigError(f"{path}.share: must be > 0, got {raw_share}")
        share = float(raw_share)

    # Optional fields
    guardrail = raw.get("guardrail")
    if guardrail is not None and not isinstance(guardrail, str):
        raise ConfigError(f"{path}.guardrail: must be a string, got {type(guardrail).__name__}")

    note = raw.get("note")
    if note is not None and not isinstance(note, str):
        raise ConfigError(f"{path}.note: must be a string, got {type(note).__name__}")

    link = raw.get("link")
    if link is not None:
        _validate_link(link, path)

    adapter = _validate_status(raw, path, config_dir)

    return Item(
        id=item_id,
        label=label,
        share=share,
        guardrail=guardrail,
        note=note,
        link=link,
        adapter=adapter,
    ), item_warnings


def _validate_ring(raw: dict, index: int, config_dir: Path) -> tuple[Ring, list[Warning]]:
    """Validate and build a Ring from raw dict."""
    path = f"rings[{index}]"

    # id is required
    if "id" not in raw:
        raise ConfigError(f"{path}: 'id' is required")
    ring_id = raw["id"]
    if not isinstance(ring_id, str):
        raise ConfigError(f"{path}.id: must be a string, got {type(ring_id).__name__}")
    _validate_slug(ring_id, ring_id, path)

    # label is required
    if "label" not in raw:
        raise ConfigError(f"{path}: 'label' is required")
    label = raw["label"]
    if not isinstance(label, str):
        raise ConfigError(f"{path}.label: must be a string, got {type(label).__name__}")

    # items is required; may be empty (⚖-R13)
    if "items" not in raw:
        raise ConfigError(f"{path}: 'items' is required")
    raw_items = raw["items"]
    if not isinstance(raw_items, list):
        raise ConfigError(f"{path}.items: must be a list, got {type(raw_items).__name__}")

    items: list[Item] = []
    seen_ids: set[str] = set()
    ring_warnings: list[Warning] = []
    for i, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            raise ConfigError(f"{path}.items[{i}]: must be a mapping, "
                              f"got {type(raw_item).__name__}")
        item, item_warnings = _validate_item(raw_item, ring_id, i, config_dir)
        ring_warnings.extend(item_warnings)
        if item.id in seen_ids:
            raise ConfigError(f"{path}.items: duplicate item id '{item.id}' in ring '{ring_id}'")
        seen_ids.add(item.id)
        items.append(item)

    return Ring(id=ring_id, label=label, items=tuple(items)), ring_warnings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(path: Path) -> Config:
    """Read + validate. Raises ConfigError on any config error; non-fatal problems land in
    Config.warnings (CIR-DATA-VALIDATION)."""
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    if not path.is_file():
        raise ConfigError(f"config path is not a file: {path}")

    raw_text = path.read_text(encoding="utf-8")
    try:
        raw: dict[str, Any] = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML parse error in {path}: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top-level value must be a mapping, "
                          f"got {type(raw).__name__}")

    warnings: list[Warning] = []

    # Unknown top-level keys → warning (CIR-DATA-VALIDATION)
    unknown_toplevel = [k for k in raw if k not in _KNOWN_TOPLEVEL_KEYS]
    for key in unknown_toplevel:
        warnings.append(Warning(item=None, message=f"unknown top-level key '{key}' ignored"))

    # person is required (CIR-DATA-SCHEMA-TOPLEVEL)
    if "person" not in raw:
        raise ConfigError("top-level: 'person' is required")
    person = raw["person"]
    if not isinstance(person, str):
        raise ConfigError("top-level.person: must be a string, "
                          f"got {type(person).__name__}")

    # timezone (optional, default UTC)
    timezone = raw.get("timezone", "UTC")
    if not isinstance(timezone, str):
        raise ConfigError("top-level.timezone: must be a string, "
                          f"got {type(timezone).__name__}")

    # spec_version (optional, default 0)
    spec_version = raw.get("spec_version", 0)
    if not isinstance(spec_version, int) or isinstance(spec_version, bool):
        raise ConfigError("top-level.spec_version: must be an integer, "
                          f"got {type(spec_version).__name__}")
    if spec_version > 0:
        raise ConfigError(f"top-level.spec_version: config version {spec_version} is newer "
                          f"than this build (understands v0)")

    # rings is required and must be non-empty
    if "rings" not in raw:
        raise ConfigError("top-level: 'rings' is required")
    raw_rings = raw["rings"]
    if not isinstance(raw_rings, list):
        raise ConfigError("top-level.rings: must be a list, "
                          f"got {type(raw_rings).__name__}")
    if len(raw_rings) == 0:
        raise ConfigError("top-level.rings: must have at least one ring (nothing to draw)")

    config_dir = path.resolve().parent

    rings: list[Ring] = []
    seen_ring_ids: set[str] = set()
    for i, raw_ring in enumerate(raw_rings):
        if not isinstance(raw_ring, dict):
            raise ConfigError(f"rings[{i}]: must be a mapping, "
                              f"got {type(raw_ring).__name__}")
        ring, ring_warnings = _validate_ring(raw_ring, i, config_dir)
        warnings.extend(ring_warnings)
        if ring.id in seen_ring_ids:
            raise ConfigError(f"rings: duplicate ring id '{ring.id}'")
        seen_ring_ids.add(ring.id)

        # Empty ring → warning (⚖-R13)
        if len(ring.items) == 0:
            warnings.append(Warning(
                item=None,
                message=f"ring '{ring.id}' has no items — renders as an empty band",
            ))

        rings.append(ring)

    # CIR-DATA-SHARE: mixed share declaration warning
    for ring in rings:
        declared = sum(1 for item in ring.items if item.share != 1.0)
        undeclared = sum(1 for item in ring.items if item.share == 1.0)
        if declared > 0 and undeclared > 0:
            warnings.append(Warning(
                item=None,
                message=f"ring '{ring.id}' mixes declared and undeclared shares — "
                        f"undeclared items default to weight 1",
            ))

    return Config(
        person=person,
        timezone=timezone,
        spec_version=spec_version,
        rings=tuple(rings),
        warnings=tuple(warnings),
    )