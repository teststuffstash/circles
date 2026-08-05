"""Bake CLI — the entry point that turns circles.yaml into data.json.

Usage:
    circles-bake <config_path> [--reference-date YYYY-MM-DD] [--output-dir DIR]

At P0, this evaluates manual: adapters only. freshness: and command: adapters resolve
to ⚪ + "not evaluated" (⚖-R2).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from bake.validate import (
    load_config,
    validate,
    ConfigError,
    BuildWarning,
)
from bake.adapters import resolve_adapter_p0, AdapterResult
from bake.artifact import build_artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bake circles.yaml -> data.json")
    parser.add_argument("config_path", type=str, help="Path to circles.yaml")
    parser.add_argument(
        "--reference-date",
        type=str,
        default=None,
        help="Reference date (YYYY-MM-DD). Default: today's date (UTC). "
             "CIR-ADAPT-REFERENCE-DATE — never read the system clock for phase logic.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for data.json. Default: same directory as config.",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config_path)

    # Determine reference date
    if args.reference_date:
        try:
            ref_date = date.fromisoformat(args.reference_date)
        except ValueError:
            print(f"error: invalid reference date '{args.reference_date}' — use YYYY-MM-DD",
                  file=sys.stderr)
            return 1
    else:
        ref_date = date.today()

    # Load
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"config error: {e.message}", file=sys.stderr)
        return 1

    # Validate
    try:
        _, build_warnings = validate(config, config_path)
    except ConfigError as e:
        print(f"config error: {e.message}", file=sys.stderr)
        return 1

    # Resolve adapters (P0 mode — manual only, ⚖-R2)
    adapter_results: dict[str, AdapterResult] = {}

    for ring in config.get("rings", []):
        ring_id = ring["id"]
        for item in ring.get("items", []):
            item_id = item["id"]
            ref = f"{ring_id}/{item_id}"
            status = item.get("status")

            if status is None:
                # No adapter -> ⚪ by-choice (handled in artifact builder)
                continue

            adapter_key = next(iter(status.keys()))
            adapter_value = status[adapter_key]

            result = resolve_adapter_p0(adapter_key, adapter_value)
            adapter_results[ref] = result

            # If P0 un-evaluated, add warning
            if result.failure_reason:
                build_warnings.append(BuildWarning(
                    message=result.failure_reason,
                    item_ref=ref,
                ))

    # Build artifact
    generated_at = datetime.now(timezone.utc)
    artifact = build_artifact(
        config=config,
        config_path=config_path,
        reference_date=ref_date,
        adapter_results=adapter_results,
        warnings=build_warnings,
        generated_at=generated_at,
    )

    # Write output
    output_dir = Path(args.output_dir) if args.output_dir else config_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "data.json"

    with open(output_path, "w") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"baked: {output_path} (reference date: {ref_date})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())