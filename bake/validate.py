"""Config loading and validation per CIR-DATA-VALIDATION / CIR-DATA-SCHEMA-*.

Validates the full config before any adapter runs. A config error fails the bake
and publishes nothing (CIR-DATA-CONFIG-ERROR-FAILS).
"""

from __future__ import annotations

import re
import os
from pathlib import Path
from typing import Any

import yaml

# --- Exceptions ---

class ConfigError(Exception):
    """A defect in circles.yaml — fails the bake, publishes nothing."""
    def __init__(self, message: str, item_ref: str | None = None):
        self.message = message
        self.item_ref = item_ref
        super().__init__(message)


class BuildWarning:
    """A non-fatal finding — bake proceeds, warning surfaces in the artifact."""
    def __init__(self, message: str, item_ref: str | None = None):
        self.message = message
        self.item_ref = item_ref

    def to_dict(self) -> dict:
        return {"item": self.item_ref, "message": self.message}


# --- Constants ---

VALID_ADAPTERS = {"manual", "freshness", "command"}
MANUAL_VALUES = {"green", "yellow", "red"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
LINK_HTTPS_RE = re.compile(r"^https://")
LINK_HTTP_RE = re.compile(r"^http://")
LINK_ROOT_RELATIVE_RE = re.compile(r"^/")
DANGEROUS_SCHEMES = re.compile(r"^(javascript|data|vbscript):", re.IGNORECASE)
SCHEME_RELATIVE = re.compile(r"^//")


# --- Loading ---

def load_config(path: str | Path) -> dict:
    """Load and return the raw parsed config.

    Raises ConfigError on YAML parse failure.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    try:
        with open(path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML parse error: {e}")
    if not isinstance(config, dict):
        raise ConfigError("config must be a YAML mapping (top-level object)")
    return config


# --- Top-level validation ---

def validate_toplevel(config: dict, config_path: Path) -> list[BuildWarning]:
    """Validate top-level shape (CIR-DATA-SCHEMA-TOPLEVEL).

    Returns build warnings for unknown keys. Raises ConfigError on fatal issues.
    """
    warnings: list[BuildWarning] = []

    # person-missing
    if "person" not in config:
        raise ConfigError("'person' is required (CIR-DATA-SCHEMA-TOPLEVEL#person-missing)")

    # rings-empty
    rings = config.get("rings", [])
    if not isinstance(rings, list) or len(rings) == 0:
        raise ConfigError("'rings' must be a non-empty list (CIR-DATA-SCHEMA-TOPLEVEL#rings-empty)")

    # unknown-toplevel-key
    known_toplevel_keys = {"spec_version", "person", "timezone", "rings"}
    for key in config:
        if key not in known_toplevel_keys:
            warnings.append(BuildWarning(
                f"unknown top-level key '{key}' — ignored",
                item_ref=None
            ))

    return warnings


# --- Version validation ---

def validate_version(config: dict) -> None:
    """Validate spec_version (CIR-DATA-SCHEMA-VERSION).

    Raises ConfigError if the config declares a version the bake doesn't understand.
    """
    spec_version = config.get("spec_version", 0)
    if not isinstance(spec_version, int):
        raise ConfigError(f"'spec_version' must be an integer, got {type(spec_version).__name__}")
    if spec_version != 0:
        raise ConfigError(
            f"config spec_version={spec_version} is newer than this build (understands v0) "
            f"(CIR-DATA-SCHEMA-VERSION#version-from-the-future)"
        )


# --- Ring validation ---

def validate_rings(config: dict, config_path: Path) -> list[BuildWarning]:
    """Validate ring and item fields (CIR-DATA-SCHEMA-RING, CIR-DATA-SCHEMA-ITEM).

    Returns build warnings. Raises ConfigError on fatal issues.
    """
    warnings: list[BuildWarning] = []
    rings = config.get("rings", [])
    seen_ring_ids: set[str] = set()

    for ring_idx, ring in enumerate(rings):
        if not isinstance(ring, dict):
            raise ConfigError(f"ring at index {ring_idx} must be a mapping")

        # ring-id-slug
        ring_id = ring.get("id")
        if not isinstance(ring_id, str) or not SLUG_RE.match(ring_id):
            raise ConfigError(
                f"ring id must be a slug matching {SLUG_RE.pattern}, got {ring_id!r} "
                f"(CIR-DATA-SCHEMA-RING#ring-id-not-slug)"
            )

        # ring-id-duplicate
        if ring_id in seen_ring_ids:
            raise ConfigError(
                f"duplicate ring id '{ring_id}' (CIR-DATA-SCHEMA-RING#ring-id-duplicate)"
            )
        seen_ring_ids.add(ring_id)

        # ring-label-missing
        if "label" not in ring:
            raise ConfigError(
                f"ring '{ring_id}' is missing 'label' (CIR-DATA-SCHEMA-RING#ring-label-missing)"
            )

        # unknown ring keys
        known_ring_keys = {"id", "label", "items"}
        for key in ring:
            if key not in known_ring_keys:
                warnings.append(BuildWarning(
                    f"ring '{ring_id}': unknown key '{key}' — ignored",
                    item_ref=ring_id
                ))

        # empty-ring
        items = ring.get("items", [])
        if not isinstance(items, list):
            raise ConfigError(f"ring '{ring_id}': 'items' must be a list")
        if len(items) == 0:
            warnings.append(BuildWarning(
                f"ring '{ring_id}' has no items — renders as empty band",
                item_ref=ring_id
            ))

        # Validate items
        seen_item_ids: set[str] = set()
        for item_idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise ConfigError(f"ring '{ring_id}', item {item_idx}: must be a mapping")

            item_warnings = _validate_item(item, ring_id, seen_item_ids, config_path)
            warnings.extend(item_warnings)

    return warnings


def _validate_item(
    item: dict, ring_id: str, seen_item_ids: set[str], config_path: Path
) -> list[BuildWarning]:
    """Validate a single item (CIR-DATA-SCHEMA-ITEM, CIR-DATA-IDENTITY, etc.)."""
    warnings: list[BuildWarning] = []

    # id-missing
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id:
        raise ConfigError(
            f"ring '{ring_id}': item missing 'id' (CIR-DATA-IDENTITY#id-missing)"
        )

    # id-character-set
    if not SLUG_RE.match(item_id):
        raise ConfigError(
            f"ring '{ring_id}/item '{item_id}': id must match {SLUG_RE.pattern} "
            f"(CIR-DATA-IDENTITY#id-character-set)"
        )

    # id-with-space-or-slash
    if "/" in item_id or " " in item_id:
        raise ConfigError(
            f"ring '{ring_id}/item '{item_id}': id contains '/' or space — "
            f"the slash is the ref separator (CIR-DATA-IDENTITY#id-with-space-or-slash)"
        )

    # item-id-duplicate-in-ring
    if item_id in seen_item_ids:
        raise ConfigError(
            f"ring '{ring_id}': duplicate item id '{item_id}' "
            f"(CIR-DATA-SCHEMA-ITEM#item-id-duplicate-in-ring)"
        )
    seen_item_ids.add(item_id)

    # label-missing
    if "label" not in item:
        raise ConfigError(
            f"ring '{ring_id}/item '{item_id}': missing 'label'"
        )

    # unknown-item-key
    known_item_keys = {"id", "label", "guardrail", "note", "link", "share", "status"}
    for key in item:
        if key not in known_item_keys:
            warnings.append(BuildWarning(
                f"ring '{ring_id}/item '{item_id}': unknown key '{key}' — ignored",
                item_ref=f"{ring_id}/{item_id}"
            ))

    # link validation (CIR-DATA-SCHEMA-LINK)
    if "link" in item:
        _validate_link(item["link"], ring_id, item_id)

    # share validation (CIR-DATA-SHARE)
    if "share" in item:
        _validate_share(item["share"], ring_id, item_id)

    # status validation (CIR-DATA-SCHEMA-ADAPTER-SLOT)
    if "status" in item:
        _validate_status(item["status"], ring_id, item_id)

    return warnings


def _validate_link(link: Any, ring_id: str, item_id: str) -> None:
    """Validate link field (CIR-DATA-SCHEMA-LINK)."""
    ref = f"{ring_id}/{item_id}"

    if not isinstance(link, str):
        raise ConfigError(
            f"ring '{ref}': 'link' must be a string, got {type(link).__name__} "
            f"(CIR-DATA-SCHEMA-LINK)"
        )

    # Dangerous schemes
    if DANGEROUS_SCHEMES.match(link):
        raise ConfigError(
            f"ring '{ref}': dangerous link scheme in '{link}' "
            f"(CIR-DATA-SCHEMA-LINK#link-javascript-scheme)"
        )

    # Scheme-relative
    if SCHEME_RELATIVE.match(link):
        raise ConfigError(
            f"ring '{ref}': scheme-relative link '{link}' is not allowed "
            f"(CIR-DATA-SCHEMA-LINK#link-scheme-relative)"
        )

    # Valid: https://, http://, or root-relative /
    if LINK_HTTPS_RE.match(link) or LINK_HTTP_RE.match(link) or LINK_ROOT_RELATIVE_RE.match(link):
        return

    # Bare relative — rejected
    raise ConfigError(
        f"ring '{ref}': bare relative link '{link}' is ambiguous — use an absolute URL or "
        f"root-relative path (CIR-DATA-SCHEMA-LINK#link-bare-relative)"
    )


def _validate_share(share: Any, ring_id: str, item_id: str) -> None:
    """Validate share field (CIR-DATA-SHARE)."""
    ref = f"{ring_id}/{item_id}"

    if not isinstance(share, (int, float)):
        raise ConfigError(
            f"ring '{ref}': 'share' must be a number, got {type(share).__name__}"
        )

    if share <= 0:
        raise ConfigError(
            f"ring '{ref}': 'share' must be > 0, got {share} "
            f"(CIR-DATA-SHARE#share-zero)"
        )


def _validate_status(status: Any, ring_id: str, item_id: str) -> None:
    """Validate status block (CIR-DATA-SCHEMA-ADAPTER-SLOT)."""
    ref = f"{ring_id}/{item_id}"

    if not isinstance(status, dict):
        raise ConfigError(
            f"ring '{ref}': 'status' must be a mapping"
        )

    # empty-status-block
    if len(status) == 0:
        raise ConfigError(
            f"ring '{ref}': 'status' is empty — omit 'status:' instead "
            f"(CIR-DATA-STATUS-RESOLUTION#empty-status-block)"
        )

    # status-two-adapters
    if len(status) > 1:
        raise ConfigError(
            f"ring '{ref}': 'status' has {len(status)} adapters — exactly one allowed "
            f"(CIR-DATA-SCHEMA-ADAPTER-SLOT#status-two-adapters)"
        )

    adapter_key = next(iter(status.keys()))

    # status-unknown-adapter
    if adapter_key not in VALID_ADAPTERS:
        raise ConfigError(
            f"ring '{ref}': unknown adapter '{adapter_key}' — v0 adapters are: "
            f"{', '.join(sorted(VALID_ADAPTERS))} "
            f"(CIR-DATA-SCHEMA-ADAPTER-SLOT#status-unknown-adapter)"
        )

    adapter_value = status[adapter_key]

    if adapter_key == "manual":
        _validate_manual(adapter_value, ref)
    elif adapter_key == "freshness":
        _validate_freshness(adapter_value, ref)
    elif adapter_key == "command":
        _validate_command(adapter_value, ref)


def _validate_manual(value: Any, ref: str) -> None:
    """Validate manual adapter value (CIR-DATA-STATUS-MANUAL-VALUES)."""
    if not isinstance(value, str):
        raise ConfigError(
            f"ring '{ref}': 'manual' value must be a string, got {type(value).__name__}"
        )

    if value not in MANUAL_VALUES:
        raise ConfigError(
            f"ring '{ref}': 'manual: {value}' is not valid — use one of "
            f"{', '.join(sorted(MANUAL_VALUES))} "
            f"(CIR-DATA-SCHEMA-ADAPTER-SLOT#manual-invalid-word)"
        )


def _validate_freshness(value: Any, ref: str) -> None:
    """Validate freshness adapter config (CIR-DATA-FRESHNESS-THRESHOLDS)."""
    if not isinstance(value, dict):
        raise ConfigError(
            f"ring '{ref}': 'freshness' value must be a mapping"
        )

    # source is required
    if "source" not in value:
        raise ConfigError(
            f"ring '{ref}': 'freshness' requires 'source'"
        )

    source = value["source"]
    if not isinstance(source, str):
        raise ConfigError(
            f"ring '{ref}': 'freshness' source must be a string"
        )

    # threshold-missing
    if "yellow_after" not in value or "red_after" not in value:
        raise ConfigError(
            f"ring '{ref}': 'freshness' requires both 'yellow_after' and 'red_after' "
            f"(CIR-DATA-FRESHNESS-THRESHOLDS#threshold-missing)"
        )

    yellow_after = value["yellow_after"]
    red_after = value["red_after"]

    # threshold-fractional
    if not isinstance(yellow_after, int) or isinstance(yellow_after, bool):
        raise ConfigError(
            f"ring '{ref}': 'yellow_after' must be an integer, got {type(yellow_after).__name__} "
            f"(CIR-DATA-FRESHNESS-THRESHOLDS#threshold-fractional)"
        )
    if not isinstance(red_after, int) or isinstance(red_after, bool):
        raise ConfigError(
            f"ring '{ref}': 'red_after' must be an integer, got {type(red_after).__name__} "
            f"(CIR-DATA-FRESHNESS-THRESHOLDS#threshold-fractional)"
        )

    # threshold-zero
    if yellow_after < 1:
        raise ConfigError(
            f"ring '{ref}': 'yellow_after' must be ≥ 1, got {yellow_after} "
            f"(CIR-DATA-FRESHNESS-THRESHOLDS#threshold-zero)"
        )
    if red_after < 1:
        raise ConfigError(
            f"ring '{ref}': 'red_after' must be ≥ 1, got {red_after} "
            f"(CIR-DATA-FRESHNESS-THRESHOLDS#threshold-zero)"
        )

    # thresholds-equal or inverted
    if yellow_after >= red_after:
        raise ConfigError(
            f"ring '{ref}': 'yellow_after' ({yellow_after}) must be < 'red_after' ({red_after}) "
            f"(CIR-DATA-FRESHNESS-THRESHOLDS#thresholds-equal)"
        )


def _validate_command(value: Any, ref: str) -> None:
    """Validate command adapter config (CIR-ADAPT-COMMAND)."""
    if not isinstance(value, list):
        raise ConfigError(
            f"ring '{ref}': 'command' must be an argv array (list of strings), "
            f"not a string (CIR-ADAPT-COMMAND#command-argv-array-required)"
        )

    if len(value) == 0:
        raise ConfigError(
            f"ring '{ref}': 'command' array must not be empty"
        )

    for i, arg in enumerate(value):
        if not isinstance(arg, str):
            raise ConfigError(
                f"ring '{ref}': 'command' argument {i} must be a string, "
                f"got {type(arg).__name__}"
            )


# --- Mixed share detection ---

def detect_mixed_shares(config: dict) -> list[BuildWarning]:
    """Detect rings with mixed declared/undeclared shares (CIR-DATA-SHARE#shares-mixed).

    Returns build warnings.
    """
    warnings: list[BuildWarning] = []
    rings = config.get("rings", [])

    for ring in rings:
        ring_id = ring.get("id", "?")
        items = ring.get("items", [])
        has_declared = any("share" in item for item in items)
        has_undeclared = any("share" not in item for item in items)

        if has_declared and has_undeclared and len(items) > 1:
            warnings.append(BuildWarning(
                f"ring '{ring_id}' mixes declared and undeclared shares — "
                f"undeclared items default to weight 1",
                item_ref=ring_id
            ))

    return warnings


# --- Source path validation ---

def validate_source_paths(config: dict, config_path: Path) -> list[BuildWarning]:
    """Validate that freshness source paths resolve and don't escape the config dir.

    Returns build warnings for missing sources. Raises ConfigError for traversal/absolute paths.
    """
    warnings: list[BuildWarning] = []
    config_dir = config_path.resolve().parent

    rings = config.get("rings", [])
    for ring in rings:
        ring_id = ring.get("id", "?")
        for item in ring.get("items", []):
            item_id = item.get("id", "?")
            ref = f"{ring_id}/{item_id}"
            status = item.get("status", {})
            if not isinstance(status, dict):
                continue
            adapter_key = next(iter(status.keys())) if status else None
            if adapter_key != "freshness":
                continue
            adapter_value = status[adapter_key]
            if not isinstance(adapter_value, dict):
                continue
            source = adapter_value.get("source", "")
            if not isinstance(source, str):
                continue

            # source-parent-traversal
            resolved = (config_dir / source).resolve()
            try:
                resolved.relative_to(config_dir)
            except ValueError:
                raise ConfigError(
                    f"ring '{ref}': source '{source}' escapes the config directory "
                    f"(CIR-DATA-SOURCE-PATH#source-parent-traversal)"
                )

            # source-absolute-path
            if os.path.isabs(source):
                raise ConfigError(
                    f"ring '{ref}': absolute source path '{source}' is not allowed — "
                    f"use a path relative to the config directory "
                    f"(CIR-DATA-SOURCE-PATH#source-absolute-path)"
                )

            # source-path-missing (warning, not error — could be a glob)
            if "*" not in source and not resolved.exists():
                warnings.append(BuildWarning(
                    f"freshness source '{source}' not found",
                    item_ref=ref
                ))

    return warnings


# --- Main validation entry point ---

def validate(config: dict, config_path: Path) -> tuple[list[BuildWarning], list[BuildWarning]]:
    """Full config validation.

    Returns (config_errors_as_warnings, build_warnings).
    Config errors raise ConfigError; build warnings are returned.
    """
    all_warnings: list[BuildWarning] = []

    # Top-level
    all_warnings.extend(validate_toplevel(config, config_path))

    # Version
    validate_version(config)

    # Rings and items
    all_warnings.extend(validate_rings(config, config_path))

    # Mixed shares
    all_warnings.extend(detect_mixed_shares(config))

    # Source paths
    all_warnings.extend(validate_source_paths(config, config_path))

    return [], all_warnings